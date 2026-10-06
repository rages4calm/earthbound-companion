# SPDX-License-Identifier: GPL-3.0-or-later
"""Cold-load real private phone saves and run full timed-item transformations.

Uses source-defined inventories and prepared successful file-menu outcomes.
Actual production save/load, finalization and 6000 party-leader ticks execute.
No title-menu traversal, phone conversation or game-over claim is made here.
"""
import argparse,json,os,subprocess
from pathlib import Path
from build_maternalbound_pack import read_pack
from check_jev_observer_parity import local_scratch
from party_follow_private_build import private_build
from snes_movement_helpers_oracle import sha
from timed_item_lifecycle_qa import DRIVER as BASE

DRIVER=BASE[:BASE.index('int main(int argc,char **argv)')]
DRIVER=DRIVER.replace('static void snapshot','static unsigned who;\nstatic void snapshot').replace('party_characters[0].items[0]','party_characters[who-1].items[0]')
DRIVER+=r'''
int main(int argc,char **argv){
 if(argc!=7)return 2;
 unsigned redux=atoi(argv[3]),item=atoi(argv[4]);who=atoi(argv[5]);if(who<1||who>4)return 3;
 char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 char*boot[]={"cold-timed-item","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1",redux?"--redux-battle-fixture":"--inspect-shuffle","0"};
 unsigned n=sizeof(boot)/sizeof(boot[0]);if(!redux)n--;
 if(eb_platform_main(n,boot)||maternalbound_enabled()!=(redux!=0))return 4;
 rng_seed(0x12345678);
 if(!strcmp(argv[6],"prepare")){
  ItemTransformSaveState empty={0};item_transform_savestate_unpack(&empty);
  game_state.party_count=game_state.player_controlled_party_count=1;memset(game_state.party_members,0,6);game_state.party_members[0]=who;
  for(unsigned i=0;i<6;i++)memset(party_characters[i].items,0,14);
  game_state.text_speed=3;game_state.leader_x_coord=2112;game_state.leader_y_coord=1768;
  if(item)give_item_to_specific_character(who,item);
  if(!save_game(0))return 5;snapshot("saved");return 0;
 }
 if(strcmp(argv[6],"continue"))return 6;
 snapshot("cold-before");ModeState menu={0};menu.file_menu.phase=FM_SUBMENU_RESULT;menu.file_menu.selected=1;menu.file_menu.result_ready=1;menu.file_menu.result=1;
 StepResult result=mode_step_file_menu(&menu);if(result.kind!=STEP_POP||result.pop_result!=1)return 7;snapshot("continued");
 if(game_state.party_members[0]!=who||party_characters[who-1].items[0]!=item)return 8;
 initialize_overworld_state();ow.enemy_spawns_enabled=0;ow.npc_spawns_enabled=0;ow.battle_mode=0;ow.enemy_has_been_touched=0;ow.battle_swirl_countdown=0;ow.disabled_transitions=0;
 ow.dad_phone_timer=1687;ow.enable_auto_sector_music_changes=0;game_state.camera_mode=0;pc_options.no_dad_calls=1;pc_options.no_homesickness=1;
 ItemTransformSaveState before,after;item_transform_savestate_pack(&before);
 ow.disabled_transitions=1;for(unsigned frame=0;frame<120;frame++)update_overworld_frame(23);item_transform_savestate_pack(&after);
 if(memcmp(&before,&after,sizeof(before)))return 9;ow.disabled_transitions=0;
 unsigned previous=party_characters[who-1].items[0];
 for(unsigned frame=1;frame<=6000;frame++){
  core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=0;update_overworld_frame(23);
  unsigned current=party_characters[who-1].items[0];if(current!=previous){char tag[50];snprintf(tag,sizeof(tag),"frame-%u",frame);snapshot(tag);previous=current;}
 }
 snapshot("final");return 0;
}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','runtime','native-source','original-assets','redux-assets','scratch','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.scratch=local_scratch(a.scratch)
    if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch/output required')
    a.scratch.mkdir(parents=True)
    files=[Path(__file__),Path(__file__).with_name('timed_item_lifecycle_qa.py'),a.original_assets,a.redux_assets,a.native_source/'src/intro/file_select.c',a.native_source/'src/game/inventory.c',a.native_source/'src/game/inventory.h',a.native_source/'src/game/overworld.c',a.native_source/'asm/intro/file_select_menu_loop.asm',a.native_source/'asm/data/timed_item_transformation_table.asm',a.native_source/'asm/overworld/process_item_transformations.asm']
    inputs={str(x):sha(x) for x in files};exe,build=private_build(a,a.scratch,DRIVER)
    rows=[];env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    for mode,pack in [('original',a.original_assets),('redux',a.redux_assets)]:
        table=read_pack(pack,a.native_source/'src/data/runtime_generated/asset_ids.h')[2]['data/timed_item_transformation_table.bin']
        egg,chick,chicken=table[0],table[3],table[8]
        assert len(table)==20 and table[5]==chick and table[10]==chicken and table[4]==50 and table[9]==44
        for who in range(1,5):
            for item,label in [(egg,'egg'),(chick,'chick'),(chicken,'chicken'),(0,'empty')]:
                session=a.scratch/f'{mode}-{who}-{label}';session.mkdir()
                def run(action):
                    q=subprocess.run([str(exe),str(pack.resolve()),str(session),str(int(mode=='redux')),str(item),str(who),action],cwd=session,env=env,capture_output=True,timeout=45)
                    (session/(action+'.log')).write_bytes(q.stdout+q.stderr)
                    if q.returncode:raise RuntimeError(str(session)+': '+action+' '+str(q.returncode)+' '+q.stderr.decode(errors='replace')[-1500:])
                    return [json.loads(s[len('ITEM_TIMELINE '):]) for s in q.stdout.decode(errors='replace').splitlines() if s.startswith('ITEM_TIMELINE ')]
                saved=run('prepare');phone=session/'fixture.srm';saved_hash=sha(phone);states=run('continue')
                assert sha(phone)==saved_hash and saved[0]['item']==item
                assert states[0]['tag']=='cold-before' and states[0]['active']==0 and not any(states[0]['slots'])
                assert states[1]['tag']=='continued' and states[-1]['tag']=='final'
                # Bootstrap inventory differs by profile's prepared entry.
                # Assert the actual Continue result separately from it.
                expected=[item]+([chick,chicken] if item==egg else [chicken] if item==chick else [])+[chicken if item else 0]
                assert [s['item'] for s in states[1:]]==expected,(mode,who,item,states)
                assert states[1]['active']==bool(item)
                if item:
                    offset={egg:0,chick:4,chicken:8}[item]
                    assert states[1]['check']==60 and states[1]['slots'][offset+3]==table[offset//4*5+4]
                # PROCESS_ITEM_TRANSFORMATIONS walks slots in source order.
                # Egg becomes Chick in slot 0; its newly initialized slot 1
                # is decremented during the same once-per-second pass.
                if item==egg:assert [s['tag'] for s in states[2:-1]]==['frame-3000','frame-5580']
                if item==chick:assert states[2]['tag']=='frame-2640'
                rows.append(dict(Mode=mode,Character=who,StartItemLabel=label,Passed=True,PrivatePhoneSaveSha256=saved_hash,PrivatePhoneSaveUnchanged=True,FreshProcesses=2,DisabledTransitionFrames=120,PartyCallbackFrames=6000,States=states))
    if any(sha(Path(f))!=h for f,h in inputs.items()):raise RuntimeError('Immutable input changed')
    report=dict(Passed=True,Format='timed-item-cold-file-continue-qa-v1',Cases=len(rows),Inputs=inputs,Build=build,Rows=rows,OwnerSavesTouched=False,SharedBuildEdited=False,FullPlaythroughVerified=False,PreparedMenuOutcome=True,SourceRequirement='FILE_SELECT_MENU_LOOP @FINALIZE_AND_START invokes INIT_ALL_ITEM_TRANSFORMATIONS. Timed source table specifies Egg50 and Chick44 seconds, processing every60 enabled party ticks. Source-ordered processing decrements newly initialized Chick in the same Egg transformation pass: Egg frame3000, Chicken frame5580. A Chick loaded directly becomes Chicken at frame2640.',Limits=['Two actual fresh processes per case use a real private phone save. Successful Continue outcome and solo party inventories are prepared; actual save/load, finalization, overworld initialization, transition guard and party-leader callbacks execute. Full title/menu input, phone conversation, game-over, natural item acquisition and exact audio parity are excluded.'])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'Passed':True,'Cases':len(rows),'ColdProcesses':len(rows)*2}),flush=True)
if __name__=='__main__':main()
