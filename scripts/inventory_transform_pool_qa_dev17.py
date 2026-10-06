# SPDX-License-Identifier: GPL-3.0-or-later
"""Packed item/shop classification, duplicate items and legacy timer-pool recovery."""
import argparse,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
from inventory_gameover_lifecycle_qa_dev17 import driver_source as gameover_driver
from build_maternalbound_pack import read_pack

def driver_source(original):
 s=gameover_driver(original).split('int main(int argc,char**argv){',1)[0]
 s=s.replace('#include "game/battle.h"','#include "game/battle.h"\n#include "core/state_dump.h"\n#include "game/display_text_internal.h"')
 s+=r'''
static unsigned quantity(unsigned item){
 /* Borrow an unmodified packed 10/00 operand pair. Only the CC1A10 API reads it;
  * this is dispatcher parity input, not a claimed story call site. */
 const unsigned char*p=ASSET_DATA(ASSET_DIALOGUE_DIALOGUE_BIN);size_t size=ASSET_SIZE(ASSET_DIALOGUE_DIALOGUE_BIN),i=0;
 while(i+1<size && !(p[i]==0x10&&p[i+1]==0))i++;if(i+1>=size)exit(20);
 uint32_t olda=get_argument_memory(),oldw=get_working_memory();set_argument_memory(item);set_working_memory(0xffffffffu);
 ScriptReader r={TEXT_SRC_DIALOGUE,i,size,-1};ModeState child={0};GameMode mode=0;uint8_t resume=0;uint16_t window=0;uint32_t arg=0;
 if(cc_1a_dispatch(&r,&child,&mode,&resume,&window,&arg)||r.ptr_off!=i+2)exit(21);
 unsigned q=get_working_memory();set_argument_memory(olda);set_working_memory(oldw);return q;
}
static void counts(const char*stage){
 unsigned inv[3]={0},pool[3]={0};unsigned ids[3]={92,168,169};
 for(unsigned j=0;j<3;j++){for(unsigned p=0;p<4;p++)for(unsigned i=0;i<14;i++)inv[j]+=party_characters[p].items[i]==ids[j];for(unsigned i=0;i<KEY_ITEMS_POOL_SIZE;i++)pool[j]+=key_items_pool[i]==ids[j];}
 printf("QA_COUNTS {\"stage\":\"%s\",\"inventory\":[%u,%u,%u],\"pool\":[%u,%u,%u],\"quantity\":[%u,%u,%u],\"mapOwned\":%u,\"batQuantity\":%u,\"find\":[%u,%u,%u]}\n",stage,inv[0],inv[1],inv[2],pool[0],pool[1],pool[2],quantity(92),quantity(168),quantity(169),key_items_find(202)!=0,quantity(1),find_item_in_inventory2(0xff,92),find_item_in_inventory2(0xff,168),find_item_in_inventory2(0xff,169));fflush(stdout);snap(stage);
}
static void idle(unsigned frames){
 g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_OVERWORLD;g_mode_stack.state[0].overworld.phase=OWP_LOOP_START;
 ow.battle_mode=0;ow.disabled_transitions=0;ow.enemy_has_been_touched=ow.battle_swirl_countdown=0;game_state.camera_mode=0;core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=0;
 for(unsigned i=0;i<frames;i++){update_overworld_frame(0);core.frame_counter++;core.nmi_count++;}
}
int main(int argc,char**argv){
 if(argc!=9)return 2;char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);snprintf(replay_path,sizeof(replay_path),"%s/input.replay",argv[2]);
 char*boot[]={"transform-pool-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--redux-battle-fixture","0"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot)!=0||!maternalbound_enabled())return 3;
 platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 4;game_set_fast_forward(true);audio_init();load_title_screen_script_data();
 unsigned kind=strtoul(argv[3],NULL,10),item=strtoul(argv[4],NULL,10),free_slots=strtoul(argv[5],NULL,10),party=strtoul(argv[6],NULL,10),seed=strtoul(argv[7],NULL,10),route=strtoul(argv[8],NULL,10);
 memset(&bt,0,sizeof(bt));game_state.party_count=game_state.player_controlled_party_count=party;game_state.current_party_members=(1u<<party)-1;memset(game_state.party_order,0,6);memset(game_state.party_members,0,6);game_state.party_npc_1=game_state.party_npc_2=0;
 memset(key_items_pool,0,sizeof(key_items_pool));party_ever_joined_mask=0;
 for(unsigned p=0;p<4;p++){CharStruct*c=&party_characters[p];memset(c->items,0,14);memset(c->afflictions,0,7);c->max_hp=c->current_hp=c->current_hp_target=100;c->max_pp=c->current_pp=c->current_pp_target=50;if(p<party){game_state.party_order[p]=game_state.party_members[p]=p+1;migrate_key_items_to_pool(p+1);}}
 update_party();initialize_overworld_state();window_system_init();init_used_bg2_tile_map();text_setup_bg3();text_upload_font_tiles();text_load_window_gfx();text_load_flavour_palette(0);rng_seed(seed);ow.mini_ghost_entity_id=-1;
 if(kind==0){printf("QA_CLASS [");for(unsigned i=0;i<256;i++)printf("%s%u",i?",":"",is_key_item_type(i));printf("]\n");audio_shutdown();return 0;}
 if(kind==1){
  unsigned target=route?0xff:1;unsigned a=give_item_to_character(target,item),b=give_item_to_character(target,item);counts("two-given");
  unsigned taken=take_item_from_character(target,item);counts("one-taken");printf("QA_API {\"give\":[%u,%u],\"take\":%u}\n",a,b,taken);idle(6000);counts("normal-tick-6000");audio_shutdown();return 0;
 }
 /* Valid old-build storage shape: the old public pool insertion helper accepted
  * these two source key-category records. Private phone/F6 save only. */
 for(unsigned p=0;p<party;p++)for(unsigned i=0;i<14-free_slots;i++)if(!give_item_to_character(p+1,1))return 5;
 key_items_give(168);key_items_give(169);key_items_give(202);counts("legacy-created");current_save_slot=1;
 if(game_state.favourite_thing[1]==0){game_state.favourite_thing[0]='P';game_state.favourite_thing[1]='S';game_state.favourite_thing[2]='I';game_state.favourite_thing[3]=0;}
 g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_OVERWORLD;g_mode_stack.state[0].overworld.phase=OWP_LOOP_START;
 if(kind==2){if(!save_game(0))return 6;memset(key_items_pool,0,sizeof(key_items_pool));memset(party_characters[0].items,0,14);if(!load_game(0))return 7;counts("phone-loaded");
  choice=0;replay(0);file_menu_setup();ModeState fm={0};fm.file_menu.phase=FM_FADEIN_WAIT;mode_push(GAME_MODE_FILE_MENU,&fm);pump();if(g_mode_stack.depth!=1||mode_child_result()!=1)return 8;counts("file-finalized");
 }else{if(!state_dump_save_slots())return 9;memset(key_items_pool,0,sizeof(key_items_pool));memset(party_characters[0].items,0,14);if(!state_dump_load_slots())return 10;counts("f6-loaded");
  g_mode_stack.depth=2;g_mode_stack.mode[1]=GAME_MODE_NONE;update_overworld_frame(0);counts("menu-guard");g_mode_stack.depth=1;ow.battle_mode=1;update_overworld_frame(0);counts("battle-guard");ow.battle_mode=0;
 }
 idle(1);counts("idle-recovered");
 if(!free_slots){unsigned a=take_item_from_character(0xff,1),b=take_item_from_character(0xff,1);printf("QA_SPACE {\"take\":[%u,%u]}\n",a,b);idle(1);counts("space-recovered");}
 idle(6000);counts("legacy-tick-6000");audio_shutdown();return 0;
}
'''
 if original:s=s.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"').replace('||!maternalbound_enabled()','||maternalbound_enabled()')
 return s

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in('build','native-source','assets','runtime','scratch','output','project'):ap.add_argument('--'+n,type=Path,required=True)
 ap.add_argument('--original',action='store_true');ap.add_argument('--diagnostic',action='store_true');ap.add_argument('--seeds',type=int,default=1);ap.add_argument('--executed-source',type=Path);a=ap.parse_args()
 if a.scratch.exists():raise ValueError('Fresh private scratch required')
 a.scratch.mkdir(parents=True);helper.DRIVER=driver_source(a.original);exe,build=helper.private_build(a)
 _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h');data=assets['data/item_configuration_table.bin'];shops=assets['data/store_table.bin'];tests=[(0,0,14,1,1,0)]
 for seed in range(1,a.seeds+1):
  for item in(92,168,169):
   for route in(0,1):tests.append((1,item,14,1,seed,route))
  for kind in(2,3):
   for party in(1,4):
    for free in(0,1,2,14):tests.append((kind,168,free,party,seed,0))
 rows=[];classifier=[]
 for i,t in enumerate(tests):
  session=(a.scratch/f'case-{i}').resolve();session.mkdir();run=subprocess.run([str(exe),str(a.assets.resolve()),str(session),*map(str,t)],cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=90)
  log=session/'native.log';log.write_bytes(run.stdout+run.stderr);events=[];counts={};errors=[]
  for line in run.stdout.decode(errors='replace').splitlines():
   for prefix in('QA_CLASS ','QA_COUNTS ','QA_TIMER ','QA_API ','QA_SPACE ','QA_MENU '):
    if line.startswith(prefix):
     r=json.loads(line[len(prefix):]);events.append(dict(type=prefix.strip(),actual=r))
     if prefix=='QA_COUNTS ':counts[r['stage']]=r
     if prefix=='QA_CLASS ':classifier=r
  if run.returncode:errors.append(f'nativeExit:{run.returncode}')
  kind,item,free,party,seed,route=t
  if kind==0:
   expected=[int(i<len(data)//39 and(data[i*39+25]&0x3c)==0x38 and not(data[i*39+28]&0x10))for i in range(256)]
   if classifier!=expected:errors.append('Packed all256-item classification differs')
  elif kind==1:
   j=(92,168,169).index(item)
   for stage,n in [('two-given',2),('one-taken',1)]:
    r=counts.get(stage,{})
    if not r or r['inventory'][j]!=n or r['pool'][j]!=0 or r['quantity'][j]!=n:errors.append(f'{stage}: duplicate/count/storage mismatch')
   r=counts.get('normal-tick-6000',{})
   if not r or r['inventory']!=[0,0,1] or r['pool']!=[0,0,0]:errors.append('Ordinary source timer did not finish with one Chicken')
  else:
   for stage,r in counts.items():
    if stage=='legacy-tick-6000':
     capacity=min(2,free*party if free else 2)
     if r['inventory']!=[0,0,capacity]or r['pool']!=[0,0,2-capacity]or r['quantity'][2]!=2:errors.append('Legacy Chick/Chicken timer or duplicate/full-bag preservation differs')
    elif sum(r['inventory'])+sum(r['pool'])!=2:errors.append(f'{stage}: lost legacy transforming items')
    if not r['mapOwned']:errors.append(f'{stage}: ordinary Town Map key ownership changed')
    bat_expected=(14-free)*party-(2 if not free and stage in('space-recovered','legacy-tick-6000')else 0)
    if r['batQuantity']!=bat_expected:errors.append(f'{stage}: unrelated regular items changed')
   r=counts.get('idle-recovered',{})
   capacity=free*party
   if not r or sum(r['inventory'])!=min(2,capacity)or sum(r['pool'])!=max(2-capacity,0):errors.append('Idle recovery destination/full-inventory retry mismatch')
   for stage in('menu-guard','battle-guard'):
    r=counts.get(stage)
    if r and(r['inventory']!=[0,0,0]or r['pool']!=[0,1,1]):errors.append(f'{stage}: unsafe modal recovery changed storage')
   if 'legacy-tick-6000'not in counts:errors.append('Missing complete legacy continuation')
  rows.append(dict(values=t,passed=not errors,errors=errors,events=events,nativeExitCode=run.returncode,logSha256=helper.digest(log)))
 shoprows=[dict(shop=i,items=list(shops[i*7:i*7+7]),classifiedKeys=[item for item in shops[i*7:i*7+7]if item and classifier and classifier[item]],transformingCategoryItems=[item for item in shops[i*7:i*7+7]if item and(data[item*39+25]&0x3c)==0x38 and(data[item*39+28]&0x10)])for i in range(len(shops)//7)]
 refs=['src/game/inventory.c','src/game/game_state.c','src/game/overworld.c','src/core/state_dump.c','src/intro/file_select.c','src/game/display_text_cc.c','asm/misc/give_item_to_specific_character.asm','asm/inventory/start_item_transformation.asm','asm/data/timed_item_transformation_table.asm']
 report=dict(schemaVersion=1,toolVersion='dev17-transform-pool',privateBuild=build,runtimeSha256={n:helper.digest(a.runtime/n)for n in('player.exe','observer.exe')},assetsSha256=helper.digest(a.assets),reduxRevision=helper.PIN,originalPack=a.original,reviewedSourceReferences=[dict(path=p,sha256=helper.digest(a.native_source/p),role='Current review source, immutable library/runtime identifies executed code')for p in refs],nativeClassifier=classifier,packedItemRecords=len(data)//39,shopRows=shoprows,cases=rows,allPassed=all(r['passed']for r in rows),reproductionFlags={n:str(getattr(a,n.replace('-','_')))for n in('build','native-source','assets','runtime','scratch','output','project','seeds')},limits=[f'All256 native byte-ID classification calls ({len(data)//39} packed items and2 invalid IDs) and unchanged{len(shoprows)}-row packed shop mapping are classification proof, not complete UI/purchase/sale/script behavior. Only Chick168/Chicken169 match key-category+TRANSFORM in supplied packs.','Prepared active party via actual constructors. Actual give/take/find, duplicates and CC1A10 dispatcher quantity; packed10/00 operand pair read as the extension API, not a story call-site claim. Real phone/F6 save/load writes fresh private sessions only. Legacy pool shape created through old public pool insertion helper.','Actual file-menu Continue finalization for phone; actual idle-root partyLeaderTick consumer for F6 and full-inventory retry. Timer slots/count never injected. One/four active PCs and0/1/2/14 free slots perbag. Full bags retain overflow; one-slot one-player bag permits only one Chicken in inventory and safely keeps the other in the pool. Modal/battle guard checks are direct consumer guards, not full menus/battles. No owner saves/ROM/packs modified.','6000 neutral leader callback ticks prove selected inventory timers, not complete story/full-game gameplay. Source-reviewed/native-tested semantics, no independent entire original-machine inventory execution.'],fullConversionVerified=False,fullPlaythroughVerified=False)
 if a.executed_source:
  report['executedSourceReferences']=[dict(path=p,sha256=helper.digest(a.executed_source/p),role='Root-frozen source snapshot corresponding to executed runtime/library')for p in refs if(a.executed_source/p).is_file()]
  report['executedSourceSnapshot']=str(a.executed_source)
 a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(cases=len(rows),passed=sum(r['passed']for r in rows),shops=len(shoprows),firstFailures=[dict(values=r['values'],errors=r['errors'])for r in rows if not r['passed']][:2])))
 if not report['allPassed']and not a.diagnostic:raise SystemExit(1)
if __name__=='__main__':main()
