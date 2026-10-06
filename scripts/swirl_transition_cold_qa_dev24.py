# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual BS_ENTER→swirl→battle→cleanup with source-timed mid-swirl cold saves.

Adapts the unchanged existing full encounter fixture, and only observes/saves
mid-source animation. No branch results, callback PCs or completion flags set.
"""
import argparse,hashlib,json,os,shutil,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
from battle_full_encounter_qa_dev18 import driver_source
BASE_DRIVER=helper.DRIVER

OBSERVERS=r'''
static unsigned qa_kind,qa_saved;
static void qa_mask(const char*tag){
 char path[4096];snprintf(path,sizeof(path),"%s/%s.raw",qa_folder,tag);FILE*f=fopen(path,"wb");if(!f)exit(21);
 for(unsigned i=0;i<EB_VIEWPORT_HEIGHT;i++){uint8_t r[]={ppu.wh0_table[i],ppu.wh1_table[i],ppu.wh2_table[i],ppu.wh3_table[i]};fwrite(r,1,4,f);}fclose(f);
 OvalWindowSaveState s={0};oval_window_savestate_pack(&s);printf("QA_CHECKPOINT {\"tag\":\"%s\",\"depth\":%u,\"top\":%u,\"cursor\":%u,\"left\":%u,\"countdown\":%u,\"window1\":%u,\"window2\":%u}\n",tag,g_mode_stack.depth,g_mode_stack.mode[g_mode_stack.depth-1],s.swirl_hdma_table_id,s.swirl_frames_left,s.frames_until_next_swirl_update,ppu.window_hdma_active,ppu.window2_hdma_active);
}
'''

def source(original):
    helper.DRIVER=BASE_DRIVER
    s=driver_source(original)
    s=s.replace('#include "game/audio.h"','#include "game/audio.h"\n#include "game/oval_window.h"\n#include "core/state_dump.h"\n#include "snes/ppu.h"')
    s=s.replace('static unsigned pump(void){','static const char*qa_folder;\n'+OBSERVERS+'\nstatic unsigned pump(void){')
    s=s.replace('  StepResult r=mode_dispatch_step((GameMode)mode,state);','''  OvalWindowSaveState oval={0};oval_window_savestate_pack(&oval);
  if(qa_kind==1&&!qa_saved&&mode==GAME_MODE_BATTLE_WAIT&&state->battle_wait.kind==BW_SWIRL_UPDATE&&ppu.window2_hdma_active&&oval.swirl_frames_left==(bt.current_battle_group>=448?19:20)){
   if(!state_dump_save_slots())return30001;qa_saved=1;qa_mask("saved");
  }
  StepResult r=mode_dispatch_step((GameMode)mode,state);''')
    s=s.replace('if(argc!=4)return 2;','if(argc!=5)return 2;qa_kind=atoi(argv[4]);qa_folder=argv[2];')
    s=s.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"')
    s=s.replace('audio_init();load_title_screen_script_data();','audio_init();if(qa_kind!=2)load_title_screen_script_data();')
    s=s.replace('  game_state=base_game;','  if(qa_kind!=2){game_state=base_game;')
    s=s.replace('  mode_push(GAME_MODE_BATTLE_SCRIPTED,&encounter);pump();','''  mode_push(GAME_MODE_BATTLE_SCRIPTED,&encounter);
  }else{if(!state_dump_load_slots())return22;qa_mask("restored");}
  pump();
  printf("QA_CLEANUP {\\\"window1\\\":%u,\\\"window2\\\":%u,\\\"tmw\\\":%u,\\\"tsw\\\":%u}\\n",ppu.window_hdma_active,ppu.window2_hdma_active,ppu.tmw,ppu.tsw);''')
    # Keep literal C tokens separate; the typed fixture is compiled exactly once.
    s=s.replace('return30001','return 30001').replace('return22','return 22')
    return s

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('native-source','build','runtime','original-assets','redux-assets','scratch','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.scratch=a.scratch.resolve()
    if a.scratch.exists()or a.output.exists():raise ValueError('Fresh private evidence required')
    a.scratch.mkdir(parents=True);root=a.scratch;rows=[];provenance=[];env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    for profile,pak in (('Original',a.original_assets),('Redux',a.redux_assets)):
        a.scratch=root/profile.lower();a.scratch.mkdir();helper.DRIVER=source(profile=='Original');exe,build=helper.private_build(a);provenance.append(dict(profile=profile,**build))
        for group in (1,448):
            previous={}
            for kind,label in ((0,'warm'),(1,'checkpoint'),(2,'cold')):
                folder=a.scratch/f'{group}-{label}';folder.mkdir()
                if kind==2:shutil.copytree(previous[1]/'saves',folder/'saves')
                (folder/'input.replay').write_text(''.join(f'{i} {"80"if i%2==0 else"0"}\n'for i in range(50000)))
                cases=folder/'cases.tsv';cases.write_text(f'0 {group} 17 4 9999 255 255 0 0\n')
                cp=subprocess.run([str(exe.resolve()),str(pak.resolve()),str(folder.resolve()),str(cases.resolve()),str(kind)],cwd=folder,env=env,capture_output=True,timeout=90);(folder/'native.log').write_bytes(cp.stdout+cp.stderr)
                logs=cp.stdout.decode(errors='replace').splitlines();final=next((json.loads(x.split(' ',1)[1])for x in logs if x.startswith('QA_ENCOUNTER ')),{});cleanup=next((json.loads(x.split(' ',1)[1])for x in logs if x.startswith('QA_CLEANUP ')),{})
                stages=[json.loads(x.split(' ',1)[1])for x in logs if x.startswith('QA_CHECKPOINT ')]
                checks=dict(nativeExitZero=cp.returncode==0,completeParentReturned=final.get('depth')==1,realBattleTurns=final.get('turns',0)>0,realMenuChoices=final.get('menuChoices',0)>0,battleWon=final.get('result')==0,secondWindowCleanup=cleanup.get('window2')==0)
                if kind==1:checks['naturalModeCheckpointWritten']=any(x['tag']=='saved'and x['window1']and x['window2']and x['top']==11 for x in stages)and(folder/'saves').exists()
                if kind==2:
                    checks['strictBootstrapRestore']=any(x['tag']=='restored'and x['window1']and x['window2']for x in stages)
                    checks['identicalFirstRestoredMasks']=sha(folder/'restored.raw')==sha(previous[1]/'saved.raw')if(folder/'restored.raw').exists()else False
                    for field in ('depth','result','postBattleFlag','overworldBattleMode','statusSuppression','intangibility','bank','battleMoney','battleExpPerSurvivor','itemDrop','partyExp','partyStatus','enemyStates'):
                        checks['sameFinal.'+field]=final.get(field)==previous['final'].get(field)
                rows.append(dict(profile=profile,group=group,continuation=label,packSha256=sha(pak),nativeExit=cp.returncode,checks=checks,passed=all(checks.values()),checkpointStages=stages,final=final,cleanup=cleanup))
                if kind==0:previous['final']=final
                previous[kind]=folder
    result=dict(toolSha256=sha(__file__),baseFixtureToolSha256=sha(Path(__file__).with_name('battle_full_encounter_qa_dev18.py')),production=provenance,rows=rows,allPassed=all(x['passed']for x in rows),executedAssertions=sum(len(x['checks'])for x in rows),preparedCases=4,processes=12,coldCases=4,skippedCases=0,
                limits=['Prepared actual scripted groups1and448 cover normal/boss swirl parents then real battle menus, turns, KO, rewards and cleanup. No natural overworld collision entry or allsix-special-swirl scene parents claim.',
                        'F6 is saved at actual third loaded swirl frame; bootstrap-only cold state restoration compares both immediately restored HDMA masks then full battle results, party/progression and final second-window cleanup.',
                        'Frame-data source/mask renderer proof remains separate; this fixture does not capture every composite battle image/audio frame. Observer private alias is not tested.'],ownerWrites=False)
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:result[k]for k in ('allPassed','executedAssertions','preparedCases','processes','coldCases','skippedCases')}));raise SystemExit(0 if result['allPassed']else 1)
if __name__=='__main__':main()
