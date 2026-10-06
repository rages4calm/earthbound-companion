# SPDX-License-Identifier: GPL-3.0-or-later
"""Real packed Starman appearance prefix, EVENT622, and bootstrap-only cold replay.

Stops on the first naturally completed movement wait before the later dialogue
and boss battle. Uses source hotspot43 for position, prepared Ness and local data.
No animation PC, completion signal or branch result is injected after entry.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import battle_action_catalog_qa as helper
from redux_story_cutscene_parent_qa import original_ref
from build_maternalbound_pack import read_pack

DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "core/mode_stack.h"
#include "core/state_dump.h"
#include "core/memory.h"
#include "game/game_state.h"
#include "game/display_text.h"
#include "game/window.h"
#include "game/text.h"
#include "game/overworld.h"
#include "game/maternalbound.h"
#include "game/audio.h"
#include "entity/entity.h"
#include "platform/platform.h"
#include "platform/pc_options.h"
#include "snes/ppu.h"
extern int eb_platform_main(int,char**);
static unsigned steps,frames,waits,signals,actor_seen,frame_mask;
static int actor(void){for(unsigned i=0;i<MAX_ENTITIES;i++)if(entities.script_table[i]==622)return i;return -1;}
static void observe(void){int a=actor();if(a>=0){actor_seen=1;if(entities.var[0][a]==3&&entities.var[1][a]>=0&&entities.var[1][a]<8)frame_mask|=1u<<entities.var[1][a];}}
static void snapshot(const char*tag){int a=actor(),s=a<0?-1:entities.script_index[a];
 printf("QA_PARENT {\"tag\":\"%s\",\"steps\":%u,\"frames\":%u,\"depth\":%u,\"top\":%u,\"waits\":%u,\"signals\":%u,\"actorSeen\":%u,\"frameMask\":%u,\"actor\":%d,\"spriteId\":%u,\"actorXY\":[%d,%d],\"var1\":%d,\"pc\":%u,\"bank\":%u,\"scriptSleep\":%d,\"state\":%u,\"bgVofs\":%u,\"pending\":%u,\"xy\":[%u,%u],\"party\":[",
 tag,steps,frames,g_mode_stack.depth,g_mode_stack.mode[g_mode_stack.depth-1],waits,signals,actor_seen,frame_mask,a,a<0?0:entities.sprite_ids[a],a<0?0:entities.abs_x[a],a<0?0:entities.abs_y[a],a<0?0:entities.var[1][a],s<0?0:scripts.pc[s],s<0?0:scripts.pc_bank[s],s<0?0:scripts.sleep_frames[s],ert.actionscript_state,ppu.bg_vofs[2],ow.pending_interactions,game_state.leader_x_coord,game_state.leader_y_coord);
 for(unsigned i=0;i<6;i++)printf("%s%u",i?",":"",game_state.party_members[i]);
 printf("],\"flags\":[");unsigned comma=0;for(unsigned i=1;i<EVENT_FLAG_COUNT;i++)if(event_flag_get(i))printf("%s%u",comma++?",":"",i);puts("]}");
}
int main(int argc,char**argv){
 if(argc!=8)return 2;unsigned kind=atoi(argv[3]);bool original=atoi(argv[4]);uint32_t entry=strtoul(argv[5],0,16);unsigned x=atoi(argv[6]),y=atoi(argv[7]);
 char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 char*boot[]={"starman-parent-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot)||maternalbound_enabled()==original)return 3;
 platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 4;game_set_fast_forward(true);audio_init();pc_options.no_dad_calls=pc_options.no_homesickness=true;
 if(kind==2){if(!state_dump_load_slots())return 5;snapshot("cold-restored");}
 else{
  memset(event_flags,0,sizeof(event_flags));event_flag_set(11);game_state.party_count=game_state.player_controlled_party_count=1;game_state.current_party_members=1;
  game_state.party_npc_1=game_state.party_npc_2=game_state.party_npc_1_id_copy=game_state.party_npc_2_id_copy=0;
  for(unsigned i=0;i<6;i++)game_state.party_members[i]=game_state.party_order[i]=i==0?1:0;
  for(unsigned i=0;i<4;i++){memset(&party_characters[i],0,sizeof(party_characters[i]));party_characters[i].current_hp=party_characters[i].current_hp_target=party_characters[i].max_hp=100;party_characters[i].level=1;}
  game_state.leader_x_coord=x;game_state.leader_y_coord=y;initialize_overworld_state();ppu.inidisp=15;ow.battle_mode=0;
  window_system_init();init_used_bg2_tile_map();text_setup_bg3();text_upload_font_tiles();text_load_window_gfx();text_load_flavour_palette(0);create_window(WINDOW_TEXT_STANDARD);set_window_focus(WINDOW_TEXT_STANDARD);dt.instant_printing=0;
  memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_NONE;
  ModeState text={0};if(!dt_make_child_init(&text,entry))return 6;mode_push(GAME_MODE_DISPLAY_TEXT,&text);
 }
 unsigned saved=0,completed=0;
 while(++steps<5000&&!completed){
  unsigned top=g_mode_stack.depth-1;GameMode mode=g_mode_stack.mode[top];core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=0;observe();
  if(mode==GAME_MODE_ACTIONSCRIPT_WAIT&&g_mode_stack.state[top].actionscript_wait.phase==0){waits++;snapshot("wait-entry");}
  unsigned before=ert.actionscript_state;StepResult r=mode_dispatch_step(mode,&g_mode_stack.state[top]);if(!before&&ert.actionscript_state)signals++;
  if(r.kind==STEP_PUSH)mode_push(r.push_mode,r.push_init);else if(r.kind==STEP_POP){mode_pop(r.pop_result);if(mode==GAME_MODE_ACTIONSCRIPT_WAIT)completed=1;}else{host_process_frame();frames++;}
  observe();int a=actor();
  if(kind==1&&!saved&&a>=0&&entities.var[0][a]==3&&entities.var[1][a]==2&&g_mode_stack.mode[g_mode_stack.depth-1]==GAME_MODE_ACTIONSCRIPT_WAIT){if(!state_dump_save_slots())return 7;saved=1;snapshot("saved");}
 }
 snapshot("appearance-completed");audio_shutdown();return !completed?8:kind==1&&!saved?9:0;
}
'''

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native-source','build','runtime','original-assets','redux-assets','original-rom','project','scratch','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.scratch=a.scratch.resolve()
    if a.scratch.exists()or a.output.exists():raise ValueError('Fresh private evidence required')
    a.scratch.mkdir(parents=True);helper.DRIVER=DRIVER;exe,production=helper.private_build(a)
    entries,_,assets=read_pack(a.original_assets,a.native_source/'src/data/runtime_generated/asset_ids.h')
    coords=assets['data/hotspot_coordinates.bin'][43*8:44*8];xy=[(int.from_bytes(coords[i:i+2],'little')+int.from_bytes(coords[i+4:i+6],'little'))*4 for i in (0,2)]
    if len(coords)!=8:raise ValueError('Source hotspot43 absent')
    source_prefix=a.original_rom.read_bytes()[0x67501:0x67529];spawn_at=source_prefix.index(bytes((31,21)))
    original_spawn=int.from_bytes(source_prefix[spawn_at+2:spawn_at+4],'little')
    if original_spawn!=303 or int.from_bytes(source_prefix[spawn_at+4:spawn_at+6],'little')!=622 or source_prefix[spawn_at+6]!=1:raise ValueError('Original source spawn contract changed')
    redux_source=a.project/'ccscript/data/data_22.ccs'
    if 'sprite2_spawn(481,622,1)'not in redux_source.read_text(encoding='utf-8'):raise ValueError('Pinned Redux appearance actor contract changed')
    rows=[];env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    for profile,pak in (('Original',a.original_assets),('Redux',a.redux_assets)):
        entry=original_ref(a.native_source,0xC67501)if profile=='Original'else 0xC67501;previous={}
        for kind,label in ((0,'warm'),(1,'checkpoint'),(2,'cold')):
            folder=a.scratch/(profile.lower()+'-'+label);folder.mkdir()
            if kind==2:shutil.copytree(previous[1]/'saves',folder/'saves')
            cp=subprocess.run([str(exe.resolve()),str(pak.resolve()),str(folder),str(kind),str(int(profile=='Original')),f'{entry:X}',*map(str,xy)],env=env,capture_output=True,timeout=90)
            (folder/'native.log').write_bytes(cp.stdout+cp.stderr)
            stages=[json.loads(line.split(' ',1)[1])for line in cp.stdout.decode(errors='replace').splitlines()if line.startswith('QA_PARENT ')]
            final=next((x for x in stages if x['tag']=='appearance-completed'),{})
            checks=dict(nativeExitZero=cp.returncode==0,naturallyCompleted=0<final.get('steps',0)<5000,returnedToPackedText=final.get('depth')==2 and final.get('top')==28,
                        actualActor622=final.get('actor',-1)>=0,sourceSpriteId=final.get('spriteId')==(original_spawn if profile=='Original'else 481),sourceLastAnimationFrame=final.get('var1')==7,
                        completionSignalConsumed=final.get('state')==0,partyPreserved=final.get('party')==[1,0,0,0,0,0],flagsPreserved=final.get('flags')==[11])
            if kind!=2:checks.update(exactOneSourceWait=final.get('waits')==1,signalProduced=final.get('signals')==1,allEightFramesObserved=final.get('frameMask')==255)
            if kind==1:checks['realMidFrameCheckpoint']=any(x['tag']=='saved'and x['var1']==2 and x['top']==5 for x in stages)
            if kind==2:
                checks['bootstrapOnlyRestore']=any(x['tag']=='cold-restored'for x in stages)
                for field in ('depth','top','spriteId','actorXY','var1','pc','bank','scriptSleep','state','bgVofs','party','flags','xy','pending'):checks['sameFinal.'+field]=final.get(field)==previous['baseline'].get(field)
            rows.append(dict(profile=profile,continuation=label,packSha256=sha(pak),entryReference=f'{entry:X}',nativeExit=cp.returncode,checks=checks,passed=all(checks.values()),stages=stages))
            if kind==0:previous['baseline']=final
            previous[kind]=folder
    result=dict(toolSha256=sha(__file__),production=production,sourceHotspot43Sha256=hashlib.sha256(coords).hexdigest(),preparedLeaderXY=xy,rows=rows,
                originalRomSha256=sha(a.original_rom),originalSourceEntryPrefixSha256=hashlib.sha256(source_prefix).hexdigest(),originalSourceSpawnSprite=original_spawn,
                reduxAppearanceSourceSha256=sha(redux_source),pinnedReduxCommit=helper.PIN,
                runtimeExecuted=True,preparedCases=2,processes=6,coldCases=2,skippedCases=0,executedAssertions=sum(len(x['checks'])for x in rows),allPassed=all(x['passed']for x in rows),
                sourceIdentities={x:sha(a.native_source/x)for x in ('asm/data/events/scripts/622.asm','asm/data/events/C33C1D.asm','src/game/display_text_cc.c','src/entity/callroutine.c','src/core/state_dump.c')},
                limits=['Real packed C67501 entry creates its actual source sprite and runs complete EVENT622 appearance until the first WAIT_FOR_ACTIONSCRIPT naturally returns.',
                        'Surrounding quest/party are prepared: Ness only at source hotspot43 midpoint. Later capsule/smoke, dialogue, boss combat and full quest are not executed.',
                        'Checkpoint is saved naturally at animation frame2; each cold child bootstraps assets only, loads the state and runs the remaining real appearance without injected completion.',
                        'Prepared raw-frame art/render proofs are separate; parent evidence asserts sequencing/cleanup and cold state, not every composite visual frame.'],ownerWrites=False)
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:result[k]for k in ('allPassed','executedAssertions','preparedCases','processes','coldCases','skippedCases')}));raise SystemExit(0 if result['allPassed']else 1)

if __name__=='__main__':main()
