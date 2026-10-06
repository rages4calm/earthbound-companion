# SPDX-License-Identifier: GPL-3.0-or-later
"""Run source-selected shop text, menus and transactions in an isolated process.

The driver links an immutable production library. Selection plans become actual
platform replay button pulses, never menu-result/register/inventory injections.
Fixture inventory/cash are established before the entry script. Reports retain
addresses, IDs and numeric outcomes, rather than copied game dialogue.
"""
import argparse,json,os,re,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import battle_action_catalog_qa as helper
from build_maternalbound_pack import read_pack

def driver_source(original):
 s=helper.DRIVER[:helper.DRIVER.index('static unsigned pump(void)')]
 s+='\n#include "game/audio.h"\n#include "platform/pc_options.h"\n#include "data/event_script_data.h"\n#include "core/log.h"\n'
 s+=r'''
static char replay_path[4096],continuation_path[4096];static unsigned plan[40],plan_count,plan_pos,quantity,steps,menus,numbers,chars,capture_kind,captured;
static unsigned choose(void){return plan_pos<plan_count?plan[plan_pos++]:999;}
static void replay(unsigned direction,unsigned moves,unsigned cancel){
 FILE*f=fopen(replay_path,"w");if(!f)exit(10);
 unsigned last=10+moves*8;
 for(unsigned i=0;i<100000;i++){
  unsigned key=0;
  if(i>=5&&i<5+moves*8&&(i-5)%8==0)key=direction;
  else if(i>=last&&(i-last)%8==0)key=cancel?PAD_B:PAD_A;
  fprintf(f,"%u %04x\n",i,key);
 }
 fclose(f);pc_input_script_path=replay_path;platform_input_shutdown();if(!platform_input_init())exit(11);
 core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=0;
}
static void replay_number(unsigned value){
 FILE*f=fopen(replay_path,"w");if(!f)exit(10);unsigned units=value%10,tens=(value/10)%10,left=5+units*8,last=left+8+tens*8+10;
 for(unsigned i=0;i<100000;i++){
  unsigned key=0;
  if(i>=5&&i<5+units*8&&(i-5)%8==0)key=PAD_UP;
  else if(tens&&i==left)key=PAD_LEFT;
  else if(tens&&i>=left+8&&i<left+8+tens*8&&(i-left-8)%8==0)key=PAD_UP;
  else if(i>=last&&(i-last)%8==0)key=PAD_A;
  fprintf(f,"%u %04x\n",i,key);
 }
 fclose(f);pc_input_script_path=replay_path;platform_input_shutdown();if(!platform_input_init())exit(11);core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=0;
}
static void snap(const char*stage){
 printf("QA_SNAP {\"stage\":\"%s\",\"wallet\":%u,\"depth\":%u,\"working\":%u,\"argument\":%u,\"inventory\":[",stage,(unsigned)game_state.money_carried,g_mode_stack.depth,(unsigned)get_working_memory(),(unsigned)get_argument_memory());
 for(unsigned i=0;i<4;i++){printf("%s[",i?",":"");for(unsigned j=0;j<14;j++)printf("%s%u",j?",":"",party_characters[i].items[j]);printf("]");}
 printf("],\"equipment\":[");for(unsigned i=0;i<4;i++){printf("%s[",i?",":"");for(unsigned j=0;j<4;j++)printf("%s%u",j?",":"",party_characters[i].equipment[j]);printf("]");}
 printf("],\"flags\":[%u,%u,%u,%u,%u,%u]}\n",event_flag_get(224),event_flag_get(225),event_flag_get(656),event_flag_get(657),event_flag_get(658),event_flag_get(659));fflush(stdout);
}
static void pump(void){
 steps=menus=numbers=chars=0;unsigned number_depth=0,char_depth=0;
 while(g_mode_stack.depth>1 && ++steps<50000){
  unsigned top=g_mode_stack.depth-1,mode=g_mode_stack.mode[top];ModeState*st=&g_mode_stack.state[top];
  if(capture_kind && ((capture_kind==1&&mode==GAME_MODE_NUMBER_SELECT)||(capture_kind==2&&mode==GAME_MODE_SELECTION_MENU&&st->selection_menu.phase==SM_SETUP&&win.current_focus_window==12))){
   host_request_capture();host_root_boundary();if(host_capture_status()!=HOST_CAPTURE_COMMITTED)exit(12);
   FILE*f=fopen(continuation_path,"w");if(!f)exit(13);fprintf(f,"%u",plan_pos);fclose(f);captured=1;snap("captured");break;
  }
  if(mode==GAME_MODE_SELECTION_MENU && st->selection_menu.phase==SM_SETUP){
   unsigned pick=choose();WindowInfo*w=get_window(win.current_focus_window);unsigned direction=PAD_DOWN,moves=0,initial=0;
   if(w){initial=win.restore_menu_backup?win.menu_backup_selected_option:w->selected_option;if(initial>=w->menu_count)initial=0;}
   printf("QA_MENU {\"index\":%u,\"pick\":%u,\"initial\":%u,\"window\":%u,\"options\":[",menus++,pick,initial,win.current_focus_window);
   if(w){for(unsigned j=0;j<w->menu_count;j++)printf("%s{\"id\":%u,\"x\":%u,\"y\":%u}",j?",":"",w->menu_items[j].userdata,w->menu_items[j].text_x,w->menu_items[j].text_y);
    if(pick<w->menu_count){MenuItem*from=&w->menu_items[initial],*to=&w->menu_items[pick];
     if(to->text_y==from->text_y){direction=pick>=initial?PAD_RIGHT:PAD_LEFT;}else direction=pick>=initial?PAD_DOWN:PAD_UP;moves=pick>=initial?pick-initial:initial-pick;}}
   printf("]}\n");fflush(stdout);replay(direction,pick==999?0:moves,pick==999);
  }
  if(mode==GAME_MODE_NUMBER_SELECT && !number_depth){number_depth=g_mode_stack.depth;numbers++;printf("QA_NUMBER {\"quantity\":%u,\"digits\":%u}\n",quantity,st->number_select.max_digits);fflush(stdout);replay_number(quantity);}
  if(mode==GAME_MODE_CHAR_SELECT && !char_depth){char_depth=g_mode_stack.depth;chars++;unsigned pick=choose();printf("QA_CHAR {\"pick\":%u,\"phase\":%u}\n",pick,st->char_select.phase);fflush(stdout);replay(PAD_RIGHT,pick==999?0:pick,pick==999);}
  core.pad1_pressed=platform_input_get_pad_new();core.pad1_held=platform_input_get_pad();core.pad1_autorepeat=core.pad1_pressed;
  StepResult r=mode_dispatch_step((GameMode)mode,st);
  if(r.kind==STEP_PUSH)mode_push(r.push_mode,r.push_init);
  else if(r.kind==STEP_POP){printf("QA_POP {\"mode\":%u,\"result\":%d}\n",mode,r.pop_result);if(mode==GAME_MODE_NUMBER_SELECT)number_depth=0;if(mode==GAME_MODE_CHAR_SELECT)char_depth=0;mode_pop(r.pop_result);}
  else {unsigned trace=verbose_level;verbose_level=0;host_process_frame();verbose_level=trace;}
 }
 printf("QA_END {\"steps\":%u,\"menus\":%u,\"numbers\":%u,\"chars\":%u,\"planUsed\":%u,\"depth\":%u,\"mode\":%u}\n",steps,menus,numbers,chars,plan_pos,g_mode_stack.depth,g_mode_stack.mode[g_mode_stack.depth-1]);fflush(stdout);
}
int main(int argc,char**argv){
 setvbuf(stdout,NULL,_IOLBF,65536);setvbuf(stderr,NULL,_IOFBF,65536);
 if(argc!=5)return 2;unsigned entry,money,party,free_slots,free_second,seed,flag,item,olditem,checkpoint;
 FILE*f=fopen(argv[3],"r");if(!f)return 3;
 if(fscanf(f,"%u %u %u %u %u %u %u %u %u %u %u %u",&entry,&money,&party,&free_slots,&free_second,&seed,&flag,&item,&olditem,&quantity,&plan_count,&checkpoint)!=12)return 4;
 for(unsigned i=0;i<plan_count&&i<40;i++)if(fscanf(f,"%u",&plan[i])!=1)return 5;fclose(f);
 char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);snprintf(replay_path,sizeof(replay_path),"%s/input.replay",argv[2]);snprintf(continuation_path,sizeof(continuation_path),"%s/continuation.txt",argv[2]);
 char*boot[]={"shop-transaction-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--redux-battle-fixture","0"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot)!=0||!maternalbound_enabled())return 6;
 platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 7;game_set_fast_forward(true);audio_init();load_title_screen_script_data();verbose_level=2;
 memset(&bt,0,sizeof(bt));game_state.party_count=game_state.player_controlled_party_count=party;game_state.current_party_members=party;memset(game_state.party_order,0,6);memset(game_state.party_members,0,6);
 memset(key_items_pool,0,KEY_ITEMS_POOL_SIZE);game_state.party_npc_1=game_state.party_npc_2=0;game_state.money_carried=money;game_state.text_speed=3;
 for(unsigned i=0;i<4;i++){CharStruct*c=&party_characters[i];memset(c->items,0,14);memset(c->equipment,0,4);memset(c->afflictions,0,7);c->max_hp=c->current_hp=c->current_hp_target=100;c->max_pp=c->current_pp=c->current_pp_target=50;
  if(i<party){game_state.party_order[i]=game_state.party_members[i]=i+1;unsigned free=i?free_second:free_slots;for(unsigned j=0;j<14-free;j++)give_item_to_character(i+1,90);if(i==0&&item)give_item_to_character(i+1,item);if(olditem){give_item_to_character(i+1,olditem);change_equipped_weapon(i+1,1);}migrate_key_items_to_pool(i+1);}}
 update_party();initialize_overworld_state();window_system_init();init_used_bg2_tile_map();text_setup_bg3();text_upload_font_tiles();text_load_window_gfx();text_load_flavour_palette(0);create_window(WINDOW_TEXT_STANDARD);
 if(flag)event_flag_set(flag);rng_seed(seed);ow.battle_mode=0;ow.disabled_transitions=0;ow.enemy_has_been_touched=ow.battle_swirl_countdown=0;
 memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_NONE;replay(0,0,0);snap("before-entry");
 if(strcmp(argv[4],"resume")==0){host_request_load();host_root_boundary();if(host_capture_status()!=HOST_CAPTURE_COMMITTED)return 14;FILE*f=fopen(continuation_path,"r");if(!f||fscanf(f,"%u",&plan_pos)!=1)return 15;fclose(f);snap("cold-loaded");}
 else {ModeState text={0};if(!dt_make_child_init(&text,entry))return 8;mode_push(GAME_MODE_DISPLAY_TEXT,&text);if(strcmp(argv[4],"capture")==0)capture_kind=checkpoint;}
 pump();snap("after-entry");audio_shutdown();return captured||g_mode_stack.depth==1?0:9;
}
'''
 if original:s=s.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"').replace('||!maternalbound_enabled()','||maternalbound_enabled()')
 return s

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in('build','native-source','assets','runtime','scratch','output','project','cases'):ap.add_argument('--'+n,type=Path,required=True)
 ap.add_argument('--original',action='store_true');ap.add_argument('--diagnostic',action='store_true');ap.add_argument('--executed-source',type=Path,required=True);ap.add_argument('--jobs',type=int,default=3);a=ap.parse_args()
 if a.scratch.exists():raise ValueError('Fresh private scratch required')
 a.scratch.mkdir(parents=True);helper.DRIVER=driver_source(a.original);exe,build=helper.private_build(a)
 _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h');items=assets['data/item_configuration_table.bin'];shops=assets['data/store_table.bin'];rows=[]
 def execute_case(case):
  session=(a.scratch/case['id']).resolve();session.mkdir();cfg=session/'case.txt';plan=case['plan']
  vals=[case['entry'],case.get('money',80000),case.get('party',1),case.get('freeSlots',14),case.get('freeSlotsSecond',case.get('freeSlots',14)),case.get('seed',1234567),case.get('flag',0),case.get('item',0),case.get('oldItem',0),case.get('quantity',3),len(plan),case.get('checkpoint',0),*plan];cfg.write_text(' '.join(map(str,vals)),encoding='utf-8')
  base=[str(exe),str(a.assets.resolve()),str(session),str(cfg)];env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy');cold=bool(case.get('checkpoint'));stages=['capture','resume']if cold else['warm'];stage_runs=[]
  with(session/'native-events.log').open('wb')as log,(session/'native-trace.log').open('wb')as trace:
   for stage in stages:
    run=subprocess.run([*base,stage],cwd=session,env=env,stdout=log,stderr=trace,timeout=180);stage_runs.append(dict(stage=stage,exit=run.returncode))
    if run.returncode:break
  (session/'native.log').write_bytes((session/'native-events.log').read_bytes()+b'\nNATIVE_TRACE_SEPARATE_STREAM\n'+(session/'native-trace.log').read_bytes())
  (session/'execution-status.json').write_text(json.dumps(stage_runs,indent=2)+'\n',encoding='utf-8')
  return case,session,stage_runs,run
 with ThreadPoolExecutor(max_workers=max(1,min(4,a.jobs)))as pool:results=list(pool.map(execute_case,json.loads(a.cases.read_text())))
 for case,session,stage_runs,run in results:
  raw=(session/'native.log').read_text(errors='replace');events=[]
  for line in raw.splitlines():
   if line.startswith('QA_'):
    p,v=line.split(' ',1);events.append(dict(type=p,actual=json.loads(v)))
  snaps={e['actual']['stage']:e['actual']for e in events if e['type']=='QA_SNAP'};errors=[]
  if run.returncode:errors.append('nativeExit:'+str(run.returncode))
  if case.get('checkpoint') and (not any(e['type']=='QA_SNAP'and e['actual']['stage']=='captured'for e in events)or not any(e['type']=='QA_SNAP'and e['actual']['stage']=='cold-loaded'for e in events)):errors.append('Actual fresh-process capture/restore did not complete')
  requests=list(map(int,re.findall(r'sfx: request (\d+)',raw)))
  before=snaps.get('before-entry',{});after=snaps.get('after-entry',{})
  if 'expectedDelta' in case:
   if after.get('wallet',0)-before.get('wallet',0)!=case['expectedDelta']:errors.append('Source wallet delta mismatch')
  if 'expectedItem' in case:
   target=case['expectedItem'];want=case.get('expectedCount',0);actual=sum(x==target for bag in after.get('inventory',[])[:case.get('party',1)]for x in bag)-sum(x==target for bag in before.get('inventory',[])[:case.get('party',1)]for x in bag)
   if actual!=want:errors.append(f'Source item delta mismatch: {actual} != {want}')
  if after and any(203 in bag for bag in after['inventory']):errors.append('Bulk preflight dummy203 leaked')
  if after and after['flags'][2:]!=[0,0,0,0]:errors.append('Shop entry did not clear configuration/temp flags')
  if 'stock' in case:
   actual=[e['actual']['options']for e in events if e['type']=='QA_MENU'and e['actual']['window']==12]
   if not actual or [v['id']for v in actual[0]]!=case['stock']:errors.append('Actual selected guarded stock differs')
  if 'sound' in case and requests.count(case['sound'])!=case.get('soundCount',case.get('expectedCount',1)):errors.append('Actual transaction sound request count differs')
  if 'expectedEquipment' in case and after.get('equipment')!=case['expectedEquipment']:errors.append('Actual purchased/equipped state differs')
  if 'expectedInventory' in case and after.get('inventory')!=case['expectedInventory']:errors.append('Actual complete inventory differs')
  row=dict(fixture=case,nativeExit=run.returncode,stages=stage_runs,events=events,soundRequests=requests,logSha256=helper.digest(session/'native.log'),eventStreamSha256=helper.digest(session/'native-events.log'),traceStreamSha256=helper.digest(session/'native-trace.log'),errors=errors,passed=not errors)
  rows.append(row);print(json.dumps(dict(id=case['id'],exit=run.returncode,errors=errors,walletDelta=after.get('wallet',0)-before.get('wallet',0),inventory=after.get('inventory'),end=[e['actual']for e in events if e['type']=='QA_END'])),flush=True)
 refs=['src/game/display_text.c','src/game/display_text_cc.c','src/game/display_text_menus.c','src/game/inventory.c','src/game/audio.c','src/game/window.c','src/game/text.c','src/core/mode_stack.h']
 report=dict(schemaVersion=1,toolVersion='dev18-selected-shop-transactions',privateBuild=build,runtimeSha256={n:helper.digest(a.runtime/n)for n in('player.exe','observer.exe')},assetsSha256=helper.digest(a.assets),reduxRevision=helper.PIN,nativeBaseRevision='76eacab54b05766b82c98da9c55d94d1236ece03',originalPack=a.original,executedSourceSnapshot=str(a.executed_source),executedSourceReferences=[dict(path=p,sha256=helper.digest(a.executed_source/p))for p in refs if(a.executed_source/p).is_file()],pinnedSource=[dict(path=p,sha256=helper.digest(a.project/p))for p in('ccscript/shops/ShopMain.ccs','ccscript/shops/ShopSys.ccs','ccscript/shops/shops_fourside.ccs','ccscript/expansion/expand_shops.ccs','ccscript/main.ccs','ccscript/shops/bulk_buy_vanilla.ccs','ccscript/data/data_15.ccs','ccscript/definitions/flags.ccs')],cases=rows,allPassed=all(r['passed']for r in rows),limits=['Selected source-entry transactions only: expected wallet/item/equipment changes, source-selected stock, dummy cleanup and configuration flags are asserted where recorded in each fixture. Actual packed entry text and production children, platform replay buttons, private source-prerequisite party/cash fixtures; not every transaction branch, natural NPC/story reachability, physical controllers or pixels.','Sound request trace proves actual play_sfx requests with initialized production audio; not heard/delivered/queue-completion proof.','Cold tests capture actual number/store child states through production capture and restore in a fresh process; not every possible serialized shop phase.','Active source imports ShopSys; shops/bulk_buy_vanilla.ccs is commented out and is not tested as an enabled feature.'],fullConversionVerified=False,fullPlaythroughVerified=False)
 a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 if not report['allPassed']and not a.diagnostic:raise SystemExit(1)
if __name__=='__main__':main()
