# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared retained story roots through real CC spawns and movement children.

Uses unchanged frozen production objects. The fixtures supply actual actors and
map/controller prerequisites, not a completed surrounding story transaction.
"""
import argparse, hashlib, json, os, re, subprocess
from pathlib import Path
import battle_action_catalog_qa as frozen
from build_maternalbound_pack import read_pack
from check_jev_observer_parity import local_scratch

DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "game/game_state.h"
#include "game/overworld.h"
#include "game/battle.h"
#include "game/audio.h"
#include "game/map_loader.h"
#include "game/maternalbound.h"
#include "game/window.h"
#include "game/flyover.h"
#include "game/display_text.h"
#include "game/display_text_internal.h"
#include "entity/entity.h"
#include "entity/sprite.h"
#include "core/state_dump.h"
#include "core/mode_stack.h"
#include "core/memory.h"
#include "data/assets.h"
#include "data/event_script_data.h"
#include "platform/platform.h"
#include "platform/pc_options.h"
#include "snes/ppu.h"
extern int eb_platform_main(int argc,char **argv);
static unsigned steps,host,visited[256],direction_bits,locations_seen,moved;
static int actor,startx,starty;
static void world(unsigned x,unsigned y){
    game_state.party_count=game_state.player_controlled_party_count=1;
    game_state.current_party_members=1;game_state.party_npc_1=game_state.party_npc_2=0;
    for(unsigned i=0;i<6;i++)game_state.party_members[i]=game_state.party_order[i]=i==0?1:0;
    memset(&party_characters[0],0,sizeof(party_characters[0]));
    party_characters[0].level=30;party_characters[0].max_hp=party_characters[0].current_hp=party_characters[0].current_hp_target=300;
    party_characters[0].max_pp=party_characters[0].current_pp=party_characters[0].current_pp_target=100;
    memset(event_flags,0,sizeof(event_flags));event_flag_set(11);
    game_state.leader_x_coord=x;game_state.leader_y_coord=y;
    initialize_overworld_state();load_title_screen_script_data();
    bt.battle_mode_flag=ow.battle_mode=0;ppu.inidisp=15;
    pc_options.no_dad_calls=pc_options.no_homesickness=true;
    /* A prepared cutscene context holds unrelated ambient actors. Otherwise
     * their own legitimate YIELD_TO_TEXT signals can finish this actor's wait.
     * The retained script/child tasks run with their normal callbacks enabled. */
    for(unsigned i=0;i<MAX_ENTITIES;i++)if(entities.script_table[i]>=0)entities.tick_callback_hi[i]|=0xc000;
    memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_NONE;
}
static void snapshot(const char *tag,unsigned event,unsigned stage){
    int s=actor>=0?entities.script_index[actor]:-1;
    printf("QA_STAGE {\"tag\":\"%s\",\"event\":%u,\"stage\":%u,\"depth\":%u,\"steps\":%u,\"host\":%u,\"actor\":%d,\"position\":[%d,%d],\"direction\":%d,\"pending\":%u,\"teleport\":[%u,%u],\"postCallback\":%u,\"postBound\":%u,\"psiDestination\":%u,\"psiStyle\":%u,\"leaderDirection\":%u,\"script\":%d,\"eventTable\":%d,\"pc\":%u,\"bank\":%u,\"sleep\":%d,\"tm\":%u,\"bg3\":%u,\"bg34\":%u,\"paletteUpload\":%u}\n",
        tag,event,stage,g_mode_stack.depth,steps,host,actor,actor>=0?entities.abs_x[actor]:-1,actor>=0?entities.abs_y[actor]:-1,
        actor>=0?entities.directions[actor]:-1,ow.pending_interactions,ow.current_teleport_destination_x,ow.current_teleport_destination_y,
        ow.post_teleport_callback_id,ow.post_teleport_callback==undraw_flyover_text,ow.psi_teleport_destination,ow.psi_teleport_style,game_state.leader_direction,
        s,actor>=0?entities.script_table[actor]:-1,s>=0?scripts.pc[s]:0,s>=0?scripts.pc_bank[s]:255,s>=0?scripts.sleep_frames[s]:-1,
        ppu.tm,ppu.bg_sc[2],ppu.bg_nba[1],ert.palette_upload_mode);
}
static void pump(void){
    unsigned before=steps;
    while(g_mode_stack.depth>1 && steps-before<12000){
        unsigned top=g_mode_stack.depth-1,mode=g_mode_stack.mode[top];visited[mode]=1;steps++;
        StepResult r=mode_dispatch_step((GameMode)mode,&g_mode_stack.state[top]);
        if(r.kind==STEP_PUSH)mode_push(r.push_mode,r.push_init);
        else if(r.kind==STEP_POP)mode_pop(r.pop_result);
        else{host_process_frame();host++;}
        if(actor>=0 && entities.script_table[actor]>=0){
            direction_bits|=1u<<(entities.directions[actor]&7);
            moved|=entities.abs_x[actor]!=startx || entities.abs_y[actor]!=starty;
        }
        for(unsigned i=0;i<8;i++)if(ml.loaded_your_sanctuary_locations[i])locations_seen|=1u<<i;
    }
}
static void wait_yield(void){ModeState m={0};mode_push(GAME_MODE_ACTIONSCRIPT_WAIT,&m);pump();}
static void wait_frames(unsigned n){ModeState m={0};m.wait_frames.phase=WF_FRAME;m.wait_frames.remaining=n;mode_push(GAME_MODE_WAIT_FRAMES,&m);pump();}
int main(int argc,char **argv){
    if(argc!=12)return 2;
    unsigned original=atoi(argv[3]),event=atoi(argv[4]),kind=atoi(argv[5]),sub=atoi(argv[6]),id=atoi(argv[7]);
    unsigned offset=atoi(argv[8]),x=atoi(argv[9]),y=atoi(argv[10]),nyield=atoi(argv[11]);
    char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
    char *boot[]={"event-wram-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,
        "--allow-redux-development","--headless","--frames","1",original?"--inspect-shuffle":"--redux-battle-fixture","0"};
    if(eb_platform_main(sizeof(boot)/sizeof(boot[0])-(original?1:0),boot)!=0 || maternalbound_enabled()==original)return 3;
    platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 4;
    game_set_fast_forward(true);audio_init();world(x,y);
    unsigned stop=event==670?2:1,first=0,consumed=0,queue_before=0,queue_after=0;
    if(kind==2){
        if(!state_dump_load_slots())return 5;
        actor=sub==0xf1?find_entity_by_npc_id(id):-1;
        if(sub==21)for(unsigned i=0;i<MAX_ENTITIES;i++)if(entities.script_table[i]==event && entities.sprite_ids[i]==id){actor=i;break;}
        first=stop;
        snapshot("cold-restored",event,first);
    }else{
        ow.pending_interactions=(event==110 || event==224 || event==778)?1:0;
        ow.entity_prepared_x=x;ow.entity_prepared_y=y;ow.entity_prepared_direction=6;
        if(sub==0xf1){
            const uint8_t *npc=ASSET_DATA(ASSET_DATA_NPC_CONFIG_TABLE_BIN);
            unsigned initial=npc[id*17+4]|npc[id*17+5]<<8;
            int existing=find_entity_by_npc_id(id);if(existing>=0)deactivate_entity(existing);
            if(create_prepared_entity_npc(id,initial)<0)return 6;
        }
        ScriptReader reader={TEXT_SRC_DIALOGUE,offset,offset+7,-1};ModeState child={0};GameMode mode=GAME_MODE_NONE;uint8_t resume=0;uint16_t aux=0;
        if(cc_1f_dispatch(&reader,&child,&mode,&resume,&aux))return 7;
        consumed=reader.ptr_off-offset;queue_before=ow.entity_creation_queue_length;
        if(queue_before)flush_entity_creation_queue();queue_after=ow.entity_creation_queue_length;
        actor=sub==0xf1?find_entity_by_npc_id(id):-1;
        if(sub==21)for(unsigned i=0;i<MAX_ENTITIES;i++)if(entities.script_table[i]==event && entities.sprite_ids[i]==id){actor=i;break;}
        int bank=-1;uint16_t pc=0;int scr=actor>=0?entities.script_index[actor]:-1;
        if(actor<0 || scr<0 || !resolve_script_id(event,&bank,&pc) || scripts.pc[scr]!=pc || scripts.pc_bank[scr]!=bank)return 8;
        snapshot("spawned",event,0);
    }
    startx=actor>=0?entities.abs_x[actor]:-1;starty=actor>=0?entities.abs_y[actor]:-1;
    if(event==777 || event==778)wait_frames(4);
    for(unsigned stage=first;stage<nyield;stage++){
        wait_yield();snapshot("yield",event,stage+1);
        if(g_mode_stack.depth!=1)return 9;
        if(kind==1 && stage+1==stop){if(!state_dump_save_slots())return 10;snapshot("saved",event,stage+1);}
    }
    if(event==670)wait_frames(2);
    if(event==351){
        snapshot("callback-installed",event,1);
        /* Deliberately give BG3 a flyover configuration. The retained callback
         * is consumed by the ordinary teleport production sequence, not by a
         * direct invocation of undraw_flyover_text in the harness. */
        ppu.bg_sc[2]=0x60;ppu.bg_nba[1]=(ppu.bg_nba[1]&0xf0)|3;
        ModeState teleport={0};teleport.teleport_to.phase=TT_BEGIN;teleport.teleport_to.dest_id=0;
        mode_push(GAME_MODE_TELEPORT_TO,&teleport);pump();
    }
    snapshot("final",event,nyield);
    printf("QA_SUMMARY {\"event\":%u,\"kind\":%u,\"consumed\":%u,\"queueBefore\":%u,\"queueAfter\":%u,\"depth\":%u,\"moved\":%u,\"directions\":%u,\"sanctuaryLocations\":%u,\"modes\":[",
        event,kind,consumed,queue_before,queue_after,g_mode_stack.depth,moved,direction_bits,locations_seen);
    unsigned comma=0;for(unsigned i=0;i<256;i++)if(visited[i])printf("%s%u",comma++?",":"",i);printf("]}\n");
    audio_shutdown();return 0;
}
'''

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def commands(assets,event):
    b=assets['dialogue/dialogue.bin'];out=[]
    for i in range(len(b)-6):
        if b[i]!=31 or b[i+1] not in (0x15,0xf1):continue
        if int.from_bytes(b[i+4:i+6],'little')==event:
            out.append({'offset':i+1,'sub':b[i+1],'id':int.from_bytes(b[i+2:i+4],'little'),'param':b[i+6] if b[i+1]==21 else None})
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('build','native-source','runtime','assets','original-assets','scratch','project','frozen-source','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--diagnostic',action='store_true');a=p.parse_args();a.scratch=local_scratch(a.scratch)
    if a.scratch.exists():raise ValueError('Fresh private scratch required.')
    a.scratch.mkdir(parents=True);frozen.DRIVER=DRIVER;exe,build=frozen.private_build(a)
    pin=subprocess.check_output(['git','-C',str(a.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=frozen.PIN:raise ValueError('Unexpected Redux source pin')
    executed=[];failures=[];assertions=0
    def check(name,ok,detail):
        nonlocal assertions
        assertions+=1
        if not ok:failures.append({'check':name,'detail':detail})
        return bool(ok)
    specs=[(109,0x1a90,0x2188,1),(110,0x1ff0,0x1d68,1),(222,0x1b40,0x0188,1),(224,0x1dd0,0x00d8,2),
           (298,0x0510,0x1600,1),(351,7568,360,1),(670,0x0500,0x2730,3),(777,7568,360,0),(778,7568,360,0)]
    for profile,pak in (('Original',a.original_assets),('Redux',a.assets)):
        assets=read_pack(pak,a.native_source/'src/data/runtime_generated/asset_ids.h')[2]
        for event,x,y,yields in specs:
            callers=commands(assets,event)
            if not callers:raise ValueError(f'Actual dialogue caller missing {profile} EVENT{event}')
            c=callers[0];folder=a.scratch/(profile.lower()+'-'+str(event));folder.mkdir()
            def run(kind):
                args=[str(exe.resolve()),str(pak.resolve()),str(folder.resolve()),str(int(profile=='Original')),str(event),str(kind),str(c['sub']),str(c['id']),str(c['offset']),str(x),str(y),str(yields)]
                r=subprocess.run(args,cwd=folder,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=180)
                log=r.stdout.decode(errors='replace')+'\n'+r.stderr.decode(errors='replace');(folder/f'native-{kind}.log').write_text(log,encoding='utf-8')
                rows=[json.loads(line.split(' ',1)[1]) for line in log.splitlines() if line.startswith('QA_STAGE ')];summaries=[json.loads(line.split(' ',1)[1]) for line in log.splitlines() if line.startswith('QA_SUMMARY ')]
                check(f'{profile} EVENT{event} process{kind}',r.returncode==0,{'returnCode':r.returncode,'tail':log[-1600:] if r.returncode else None})
                warnings=[line for line in log.splitlines() if re.search(r'unhandled|unknown|unimplemented|FATAL',line,re.I)]
                check(f'{profile} EVENT{event} no interpreter fallback{kind}',not warnings,warnings)
                return rows,summaries[0] if summaries else {}
            rows,summary=run(1 if event in (224,351,670) else 0)
            finals=[r for r in rows if r['tag']=='final'];final=finals[0] if finals else {}
            check(f'{profile} EVENT{event} complete',final.get('depth')==1 and summary.get('depth')==1,{'final':final,'summary':summary})
            check(f'{profile} EVENT{event} actual caller consumed',summary.get('consumed')==(6 if c['sub']==21 else 5) and summary.get('queueAfter')==0,summary)
            if event in (109,110,222,224,298,670):check(f'{profile} EVENT{event} actual movement',summary.get('moved')==1,summary)
            ys=[r for r in rows if r['tag']=='yield'];check(f'{profile} EVENT{event} source yields',len(ys)==yields and all(r['depth']==1 for r in ys),ys)
            if event in (109,110,222,224,777,778):
                value=1 if event in (109,222,777) else 0
                check(f'{profile} EVENT{event} pending scalar',final.get('pending')==value,final)
                if event==224:check(profile+' EVENT224 lock remains until second walk',len(ys)==2 and ys[0]['pending']==1 and ys[1]['pending']==0,ys)
            if event==298:check(profile+' EVENT298 teleport scalar',final.get('teleport')==[695,886] and final.get('position')==[856,6104],final)
            if event==351:
                installed=[r for r in rows if r['tag']=='callback-installed'];check(profile+' EVENT351 callback installed',len(installed)==1 and installed[0]['postCallback']==1 and installed[0]['postBound']==1,installed)
                check(profile+' EVENT351 all rotating directions',summary.get('directions')==255,summary)
                check(profile+' EVENT351 callback consumed by real teleport',final.get('postCallback')==0 and final.get('postBound')==0 and final.get('bg3')==0x7c and final.get('bg34',0)&15==6,final)
            if event==670:check(profile+' EVENT670 source destination/departure',final.get('psiDestination')==(14 if profile=='Original' else 7) and final.get('psiStyle')==5 and final.get('leaderDirection')==2 and final.get('position')==[1264,9928],final)
            if event in (777,778):check(f'{profile} EVENT{event} child35 deallocated',final.get('eventTable')==-1 and final.get('sleep',0)<0,final)
            executed.append({'profile':profile,'event':event,'kind':'full-prepared-root-and-retained-children','caller':{'subcode':c['sub'],'actorId':c['id'],'param':c['param']},'stages':rows,'summary':summary})
            if event in (224,351,670):
                coldrows,coldsummary=run(2);cf=next((r for r in coldrows if r['tag']=='final'),{})
                keys=('depth','position','direction','pending','teleport','postCallback','postBound','psiDestination','psiStyle','leaderDirection','script','eventTable','pc','bank','sleep','tm','bg3','bg34')
                check(f'{profile} EVENT{event} cold final semantic equivalence',all(final.get(k)==cf.get(k) for k in keys),{k:[final.get(k),cf.get(k)] for k in keys if final.get(k)!=cf.get(k)})
                restored=next((r for r in coldrows if r['tag']=='cold-restored'),{});saved=next((r for r in rows if r['tag']=='saved'),{})
                check(f'{profile} EVENT{event} cold saved state equivalence',all(saved.get(k)==restored.get(k) for k in keys),{k:[saved.get(k),restored.get(k)] for k in keys if saved.get(k)!=restored.get(k)})
                executed.append({'profile':profile,'event':event,'kind':'separate-process-private-checkpoint-continuation','stages':coldrows,'summary':coldsummary})
    files=('src/entity/opcodes.c','src/entity/script.c','src/entity/callroutine.c','src/entity/callroutine_movement.c','src/game/display_text_cc.c','src/game/door.c','src/game/overworld_interaction.c')
    source={n:sha(a.native_source/n) for n in files}
    reference_files=['asm/data/events/scripts/'+f'{event:03}.asm' for event,_,_,_ in specs]
    reference_files+=['asm/data/events/scripts/035.asm','asm/data/events/C30295.asm','asm/data/events/C3AB59.asm','asm/system/undraw_flyover_text.asm','asm/overworld/teleport.asm']
    original_root=a.native_source.parent/'_BuildScratch/upstream'
    references={n:sha(original_root/n) for n in reference_files if (original_root/n).is_file()}
    report={'format':'event-wram-consumer-qa-v1','Passed':not failures,'allPassed':not failures,'executedCases':len(executed),'executedAssertions':assertions,'skippedCases':0,'failures':failures,'cases':executed,'privateBuild':build,'runtimeSha256':{n:sha(a.runtime/n) for n in ('player.exe','observer.exe')},'packSha256':{'Original':sha(a.original_assets),'Redux':sha(a.assets)},'sourceSha256':source,'frozenFullPatchSha256':sha(a.frozen_source/'native-companion.patch'),'originalReferenceSha256':references,'pinnedReduxRevision':pin,'toolSha256':sha(Path(__file__)),'ownerSavesTouched':False,'sharedBuildModified':False,'limits':['Actual retained dialogue CC1F15 or CC1FF1 spawns/reassigns the appropriate actor and native ACTIONSCRIPT_WAIT executes full roots and called movement/task children to real yields. Prepared scene coordinates/controllers are supplied; surrounding story dialogue/progression is not claimed.','Immediate script777/778 despawn executes through real WAIT_FRAMES instead of inventing a nonexistent text yield.','Source-script351 installs the callback; the actual full TELEPORT_TO sequence consumes it, including in a different process after a private checkpoint restore.','Only the bounded named WRAM consumer families are tested here. Other scalar reads/writes, every story scene and universal interpreter semantics remain outside scope.','Observer hash is paired provenance; private caller links player production objects. No ROM, asset, bytecode or save content is in the public report.']}
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:report[k] for k in ('Passed','executedCases','executedAssertions','skippedCases')}));print(json.dumps(failures[:15]))
    if failures and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
