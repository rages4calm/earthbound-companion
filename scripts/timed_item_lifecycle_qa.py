# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise real file-Continue and party-leader timed-item consumers privately.

The selected Continue result is a prepared menu entry prerequisite. The real
production load, finalization and per-frame party callback execute; this does
not claim a complete phone conversation, title-menu traversal or game over.
"""
import argparse, json, os, subprocess
from pathlib import Path
from build_maternalbound_pack import read_pack
from check_jev_observer_parity import local_scratch
from party_follow_private_build import private_build
from snes_movement_helpers_oracle import sha

DRIVER = r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "game/game_state.h"
#include "game/inventory.h"
#include "game/overworld.h"
#include "game/maternalbound.h"
#include "game/display_text.h"
#include "core/math.h"
#include "core/memory.h"
#include "core/mode_stack.h"
#include "intro/file_select.h"
#include "platform/pc_options.h"
extern int eb_platform_main(int,char**);
extern void update_overworld_frame(int16_t);
static void snapshot(const char *tag){
 ItemTransformSaveState t={0};item_transform_savestate_pack(&t);
 printf("ITEM_TIMELINE {\"tag\":\"%s\",\"item\":%u,\"active\":%u,\"check\":%u,\"slots\":[",tag,party_characters[0].items[0],t.item_transformations_loaded,t.time_until_next_item_transformation_check);
 for(unsigned i=0;i<16;i++)printf("%s%u",i?",":"",t.loaded_transformations[i]);puts("]}");fflush(stdout);
}
int main(int argc,char **argv){
 if(argc!=5)return 2;unsigned redux=atoi(argv[3]),egg=atoi(argv[4]);char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 char*boot[]={"timed-item-lifecycle","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1",redux?"--redux-battle-fixture":"--inspect-shuffle","0"};
 unsigned n=sizeof(boot)/sizeof(boot[0]);if(!redux)n--;
 if(eb_platform_main(n,boot)||maternalbound_enabled()!=(redux!=0))return 3;
 game_state.party_count=game_state.player_controlled_party_count=1;memset(game_state.party_members,0,6);game_state.party_members[0]=1;
 for(unsigned i=0;i<6;i++)memset(party_characters[i].items,0,14);
 game_state.text_speed=3;game_state.leader_x_coord=2112;game_state.leader_y_coord=1768;
 ItemTransformSaveState empty={0};item_transform_savestate_unpack(&empty);rng_seed(0x12345678);
 give_item_to_specific_character(1,egg);snapshot("given");
 if(!save_game(0))return 4;
 memset(party_characters[0].items,0,14);item_transform_savestate_unpack(&empty);
 ModeState menu={0};menu.file_menu.phase=FM_SUBMENU_RESULT;menu.file_menu.selected=1;menu.file_menu.result_ready=1;menu.file_menu.result=1;
 StepResult result=mode_step_file_menu(&menu);
 if(result.kind!=STEP_POP||result.pop_result!=1)return 5;snapshot("continued");
 initialize_overworld_state();
 ow.enemy_spawns_enabled=0;ow.npc_spawns_enabled=0;ow.battle_mode=0;ow.enemy_has_been_touched=0;ow.battle_swirl_countdown=0;ow.disabled_transitions=0;
 ow.dad_phone_timer=1687;ow.enable_auto_sector_music_changes=0;game_state.camera_mode=0;pc_options.no_dad_calls=1;pc_options.no_homesickness=1;
 unsigned previous=party_characters[0].items[0];
 for(unsigned frame=1;frame<=6000;frame++){
  core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=0;update_overworld_frame(23);
  unsigned item=party_characters[0].items[0];if(item!=previous){char tag[50];snprintf(tag,sizeof(tag),"frame-%u",frame);snapshot(tag);previous=item;}
 }
 snapshot("final");return 0;
}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','runtime','native-source','original-assets','redux-assets','scratch','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--diagnostic',action='store_true')
    a=p.parse_args();a.scratch=local_scratch(a.scratch)
    if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch/output required')
    a.scratch.mkdir(parents=True)
    files=[Path(__file__),a.original_assets,a.redux_assets,a.native_source/'src/intro/file_select.c',a.native_source/'src/game/inventory.c',a.native_source/'src/game/overworld.c',a.native_source/'asm/intro/file_select_menu_loop.asm',a.native_source/'asm/data/timed_item_transformation_table.asm',a.native_source/'asm/overworld/process_item_transformations.asm']
    inputs={str(x):sha(x) for x in files};exe,build=private_build(a,a.scratch,DRIVER)
    rows=[];env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    for mode,pack in [('original',a.original_assets),('redux',a.redux_assets)]:
        assets=read_pack(pack,a.native_source/'src/data/runtime_generated/asset_ids.h')[2]
        table=assets['data/timed_item_transformation_table.bin']
        egg,chick,chicken=table[0],table[3],table[8]
        assert len(table)==20 and table[5]==chick and table[10]==chicken and table[4]==50 and table[9]==44
        session=a.scratch/mode;session.mkdir()
        q=subprocess.run([str(exe),str(pack.resolve()),str(session),str(int(mode=='redux')),str(egg)],cwd=session,env=env,capture_output=True,timeout=45)
        (session/'native.log').write_bytes(q.stdout+q.stderr)
        if q.returncode:raise RuntimeError(mode+': '+str(q.returncode)+' '+q.stderr.decode(errors='replace')[-1500:])
        states=[json.loads(s[len('ITEM_TIMELINE '):]) for s in q.stdout.decode(errors='replace').splitlines() if s.startswith('ITEM_TIMELINE ')]
        assert states and states[0]['tag']=='given' and states[1]['tag']=='continued' and states[-1]['tag']=='final'
        expected=[egg,egg,chick,chicken,chicken]
        mismatch=[dict(Field='itemSequence',Expected=expected,Actual=[s['item'] for s in states])] if [s['item'] for s in states]!=expected else []
        if states[1]['active']!=1 or states[1]['slots'][3]!=50:mismatch.append(dict(Field='fileContinueTimer',Expected=dict(active=1,eggCountdown=50),Actual=states[1]))
        rows.append(dict(Mode=mode,Passed=not mismatch,SourceTable=list(table),States=states,Mismatches=mismatch))
    if any(sha(Path(f))!=h for f,h in inputs.items()):raise RuntimeError('Immutable input changed')
    report=dict(Passed=all(r['Passed'] for r in rows),Format='timed-item-file-continue-qa-v1',Inputs=inputs,Build=build,Modes=rows,OwnerSavesTouched=False,SharedBuildEdited=False,FullPlaythroughVerified=False,PreparedMenuOutcome=True,SourceRequirement='FILE_SELECT_MENU_LOOP @FINALIZE_AND_START closes all windows then calls INIT_ALL_ITEM_TRANSFORMATIONS before starting the overworld.',Limits=['File-menu selected Continue outcome is prepared; actual native load_game, finalization, initialize_overworld_state and 6000 production party-leader callbacks execute. Full title/menu input, phone conversation, game-over and exact timing/audio parity are excluded.'])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'Passed':report['Passed'],'Modes':[{k:r[k] for k in ('Mode','Passed','Mismatches')} for r in rows]}),flush=True)
    if not report['Passed'] and not a.diagnostic:raise SystemExit(1)
if __name__=='__main__':main()
