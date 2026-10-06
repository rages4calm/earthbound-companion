# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared Egg -> real game-over choice -> resume/file menu -> leader ticks.

Every case starts a new private process. Timers are created by actual give-item,
never by writing their snapshots/counts. The driver observes the real text/menu
children, feeds source-visible A/Right pulses through the platform replay reader,
and runs unchanged production consumers from a matching immutable library.
"""
import argparse,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
from build_maternalbound_pack import read_pack

def driver_source(original):
 s=helper.DRIVER[:helper.DRIVER.index('static unsigned pump(void)')]
 s=s.replace('#include "game/battle.h"','#include "game/battle.h"\n#include "game/audio.h"\n#include "platform/pc_options.h"\n#include "data/event_script_data.h"\n#include "intro/file_select.h"')
 s+=r'''
#define EVENT_FLAG_NOCONTINUE_SELECTED 475
static char replay_path[4096];static unsigned choice,menu_count,steps;static unsigned phase_seen[64];
static void replay(unsigned right){
 FILE*f=fopen(replay_path,"w");if(!f)exit(10);
 for(unsigned i=0;i<100000;i++)fprintf(f,"%u %04x\n",i,(right&&i==2)?PAD_RIGHT:(i>=4&&i%4==1)?PAD_A:0);
 fclose(f);pc_input_script_path=replay_path;platform_input_shutdown();if(!platform_input_init())exit(11);
 core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=0;
}
static unsigned pump(void){
 unsigned selected=0;steps=0;memset(phase_seen,0,sizeof(phase_seen));
 while(g_mode_stack.depth>1 && ++steps<30000){
  unsigned top=g_mode_stack.depth-1,mode=g_mode_stack.mode[top];ModeState*st=&g_mode_stack.state[top];
  if(mode==GAME_MODE_GAME_OVER && st->game_over.phase<64)phase_seen[st->game_over.phase]++;
  if(mode==GAME_MODE_SELECTION_MENU && st->selection_menu.phase==SM_SETUP){
   WindowInfo*w=get_window(win.current_focus_window);printf("QA_MENU {\"window\":%u,\"options\":[",win.current_focus_window);
   if(w)for(unsigned j=0;j<w->menu_count;j++)printf("%s{\"id\":%u,\"label\":\"%s\",\"x\":%u,\"y\":%u}",j?",":"",w->menu_items[j].userdata,w->menu_items[j].label,w->menu_items[j].text_x,w->menu_items[j].text_y);printf("]}\n");fflush(stdout);
   if(!selected++){replay(choice);}menu_count++;
  }
  core.pad1_pressed=platform_input_get_pad_new();core.pad1_held=platform_input_get_pad();core.pad1_autorepeat=core.pad1_pressed;
  StepResult r=mode_dispatch_step((GameMode)mode,st);
  if(r.kind==STEP_PUSH)mode_push(r.push_mode,r.push_init);else if(r.kind==STEP_POP)mode_pop(r.pop_result);else host_process_frame();
 }
 return steps;
}
static void snap(const char*name){
 ItemTransformSaveState t={0};item_transform_savestate_pack(&t);
 printf("QA_TIMER {\"stage\":\"%s\",\"active\":%u,\"check\":%u,\"slots\":[",name,t.item_transformations_loaded,t.time_until_next_item_transformation_check);
 for(unsigned i=0;i<16;i++)printf("%s%u",i?",":"",t.loaded_transformations[i]);printf("],\"items\":[");for(unsigned i=0;i<14;i++)printf("%s%u",i?",":"",party_characters[0].items[i]);
 printf("],\"hp\":%u,\"hpTarget\":%u,\"pp\":%u,\"money\":%u,\"x\":%u,\"y\":%u,\"noContinue\":%u,\"partyCount\":%u,\"playerCount\":%u,\"partyMembers\":[%u,%u,%u,%u],\"keyPool\":[",party_characters[0].current_hp,party_characters[0].current_hp_target,party_characters[0].current_pp,(unsigned)game_state.money_carried,game_state.leader_x_coord,game_state.leader_y_coord,event_flag_get(EVENT_FLAG_NOCONTINUE_SELECTED),game_state.party_count,game_state.player_controlled_party_count,game_state.party_members[0],game_state.party_members[1],game_state.party_members[2],game_state.party_members[3]);for(unsigned j=0;j<KEY_ITEMS_POOL_SIZE;j++)printf("%s%u",j?",":"",key_items_pool[j]);printf("]}\n");fflush(stdout);
}
int main(int argc,char**argv){
 if(argc!=6)return 2;char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);snprintf(replay_path,sizeof(replay_path),"%s/input.replay",argv[2]);
 char*boot[]={"gameover-egg-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--redux-battle-fixture","0"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot)!=0||!maternalbound_enabled())return 3;
 platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 4;game_set_fast_forward(true);audio_init();load_title_screen_script_data();
 memset(&bt,0,sizeof(bt));game_state.party_count=game_state.player_controlled_party_count=1;game_state.current_party_members=1;memset(game_state.party_order,0,6);memset(game_state.party_members,0,6);game_state.party_order[0]=game_state.party_members[0]=1;
 game_state.party_npc_1=game_state.party_npc_2=0;game_state.party_npc_1_hp=game_state.party_npc_2_hp=0;game_state.money_carried=101;game_state.text_speed=3;
 CharStruct*c=&party_characters[0];c->max_hp=c->current_hp=c->current_hp_target=100;c->max_pp=c->current_pp=c->current_pp_target=50;memset(c->items,0,14);memset(c->afflictions,0,7);
 if(game_state.favourite_thing[1]==0){game_state.favourite_thing[0]='P';game_state.favourite_thing[1]='S';game_state.favourite_thing[2]='I';game_state.favourite_thing[3]=0;}
 migrate_key_items_to_pool(1);update_party();initialize_overworld_state();window_system_init();init_used_bg2_tile_map();text_setup_bg3();text_upload_font_tiles();text_load_window_gfx();text_load_flavour_palette(0);
 ow.battle_mode=0;ow.disabled_transitions=0;ow.enemy_has_been_touched=ow.battle_swirl_countdown=0;ow.mini_ghost_entity_id=-1;ow.respawn_x=game_state.leader_x_coord;ow.respawn_y=game_state.leader_y_coord;
 rng_seed(strtoul(argv[5],NULL,10));unsigned egg=strtoul(argv[4],NULL,10);snap("before-give");unsigned given=give_item_to_character(1,egg);snap("after-give");if(!given)return 6;
 current_save_slot=1;if(!save_game(0))return 7;snap("phone-saved");
 c->current_hp=c->current_hp_target=0;c->afflictions[0]=1;
 memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_NONE;choice=strtoul(argv[3],NULL,10);replay(0);menu_count=0;
 ModeState go={0};go.game_over.phase=GO_ENTER;mode_push(GAME_MODE_GAME_OVER,&go);pump();int result=mode_child_result();snap("game-over-completed");
 printf("QA_GAMEOVER {\"steps\":%u,\"depth\":%u,\"result\":%d,\"menus\":%u,\"phases\":[",steps,g_mode_stack.depth,result,menu_count);unsigned n=0;for(unsigned i=0;i<64;i++)if(phase_seen[i])printf("%s%u",n++?",":"",i);printf("]}\n");fflush(stdout);
 if(g_mode_stack.depth!=1)return 8;
 if(result!=0){choice=0;replay(0);file_menu_setup();ModeState fm={0};fm.file_menu.phase=FM_FADEIN_WAIT;mode_push(GAME_MODE_FILE_MENU,&fm);pump();snap("file-continue-completed");printf("QA_FILE {\"steps\":%u,\"depth\":%u,\"result\":%d,\"menus\":%u}\n",steps,g_mode_stack.depth,mode_child_result(),menu_count);fflush(stdout);if(g_mode_stack.depth!=1)return 9;}
 /* A timer test only: neutral-pad actual partyLeaderTick consumer, no writes to
  * loaded timers/count/check. Source map conditions restored by normal caller
  * setup for file Continue; not a whole intro/reboot lifecycle certification. */
 ow.battle_mode=0;ow.disabled_transitions=0;ow.enemy_has_been_touched=ow.battle_swirl_countdown=0;game_state.camera_mode=0;core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=0;audio_invalidate_music_cache();
 for(unsigned i=0;i<6000;i++){update_overworld_frame(0);core.frame_counter++;core.nmi_count++;if(i==2999)snap("leader-tick-3000");}snap("leader-tick-6000");audio_shutdown();return 0;
}
'''
 if original:s=s.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"').replace('||!maternalbound_enabled()','||maternalbound_enabled()')
 return s

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in('build','native-source','assets','runtime','scratch','output','project'):ap.add_argument('--'+n,type=Path,required=True)
 ap.add_argument('--original',action='store_true');ap.add_argument('--seeds',type=int,default=1);ap.add_argument('--diagnostic',action='store_true');ap.add_argument('--executed-source',type=Path);a=ap.parse_args()
 if a.scratch.exists():raise ValueError('Fresh private scratch required')
 a.scratch.mkdir(parents=True);helper.DRIVER=driver_source(a.original);exe,build=helper.private_build(a)
 _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h');table=assets['data/timed_item_transformation_table.bin'];egg,_,_,chick,time=table[:5];chicken=table[8];rows=[]
 for seed in range(1,a.seeds+1):
  for choice in range(2):
   session=(a.scratch/f'seed-{seed}-choice-{choice}').resolve();session.mkdir();run=subprocess.run([str(exe),str(a.assets.resolve()),str(session),str(choice),str(egg),str(seed*0x9e3779b9&0xffffffff)],cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=90)
   log=session/'native.log';log.write_bytes(run.stdout+run.stderr);timers={};events=[];errors=[]
   for line in run.stdout.decode(errors='replace').splitlines():
    for prefix in('QA_TIMER ','QA_GAMEOVER ','QA_FILE ','QA_MENU '):
     if line.startswith(prefix):
      r=json.loads(line[len(prefix):]);events.append(dict(type=prefix.strip(),actual=r))
      if prefix=='QA_TIMER ':timers[r['stage']]=r
   if run.returncode:errors.append(f'nativeExit:{run.returncode}')
   after=timers.get('after-give',{});end=timers.get('leader-tick-6000',{});go=next((e['actual']for e in events if e['type']=='QA_GAMEOVER'),{})
   if after.get('active')!=1 or not after.get('slots') or after['slots'][3]!=time:errors.append('Actual give-item did not start source Egg timer')
   # Original's active counter is cleared by game over while the retained Egg
   # slot stays valid, so even source file-select reconciliation leaves the
   # original counter guard shut. Redux explicitly removes that known stop.
   expected=egg if a.original else chicken
   if go.get('result')!=(0 if choice==0 else -1):errors.append('Actual comeback text choice did not take the expected source path')
   if not end or end['items'][0]!=expected:errors.append(f'6000 leader ticks item:{end.get("items")} expected:{expected}')
   rows.append(dict(seed=seed,inputChoice=choice,expectedItem=expected,passed=not errors,errors=errors,events=events,logSha256=helper.digest(log),nativeExitCode=run.returncode))
 refs=['src/game/inventory.c','src/game/overworld.c','src/game/overworld_palette.c','src/game_main.c','src/intro/file_select.c','asm/misc/initialize_game_over_screen.asm','asm/misc/play_comeback_sequence.asm','asm/overworld/spawn.asm','asm/intro/file_select_menu_loop.asm','asm/overworld/update_overworld_frame.asm','asm/data/timed_item_transformation_table.asm']
 report=dict(schemaVersion=1,toolVersion='dev17-gameover-egg',privateBuild=build,runtimeSha256={n:helper.digest(a.runtime/n)for n in('player.exe','observer.exe')},assetsSha256=helper.digest(a.assets),reduxRevision=helper.PIN,originalPack=a.original,reviewedSourceReferences=[dict(path=p,sha256=helper.digest(a.native_source/p),role='Current review text; not an assertion that this complete file matches the immutable executed library')for p in refs],reduxTimerGuardSource=dict(path='ccscript/bugfixes/item_transformations_fix.ccs',sha256=helper.digest(a.project/'ccscript/bugfixes/item_transformations_fix.ccs')),cases=rows,allPassed=all(r['passed']for r in rows),limits=['Prepared one-member party using actual joined-party migration/update constructors, actual give Egg and isolated real phone-save API, deliberate zero HP/unconscious then GAME_OVER GO_ENTER. Actual text/choice/menu children and platform-replay input; no owner data writes.','Text Yes sets source NoContinue flag and resumes at respawn; text No then confirmation returns reboot result, followed by actual file-menu setup/selection/Continue load, without complete intro/reboot parent execution. Subsequent 6000 neutral partyLeaderTick consumer calls are bounded timer proof, not a roaming/render/physical-controller or full-playthrough test.','Reviewed whole-file source identities can differ from immutable executed library; runtime/library hashes are execution provenance. Original retained Egg is source expected on both same-process game-over paths because active counter clears while slots remain valid; Redux removes original active-counter guard. No timer snapshot/count writes in driver.'],fullConversionVerified=False,fullPlaythroughVerified=False)
 if a.executed_source:
  report['executedSourceReferences']=[dict(path=p,sha256=helper.digest(a.executed_source/p),role='Root-frozen source snapshot corresponding to executed runtime/library')for p in refs if(a.executed_source/p).is_file()]
  report['executedSourceSnapshot']=str(a.executed_source)
 report['reproductionFlags']={n:str(getattr(a,n.replace('-','_')))for n in('build','native-source','assets','runtime','scratch','output','project','seeds')}
 a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(cases=len(rows),passed=sum(r['passed']for r in rows),firstFailures=[dict(seed=r['seed'],choice=r['inputChoice'],errors=r['errors'])for r in rows if not r['passed']][:2])))
 if not report['allPassed']and not a.diagnostic:raise SystemExit(1)
if __name__=='__main__':main()
