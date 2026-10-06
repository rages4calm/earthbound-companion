# SPDX-License-Identifier: GPL-3.0-or-later
"""Source Keys membership, real bag/selector APIs and old phone/F6 recovery.

Prerequisites are prepared before testing. Links the complete immutable native
library with unchanged production handlers. Optional owner inputs are copied.
"""
import argparse, json, os, re, shutil, subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
from inventory_transform_pool_qa_dev18 import driver_source as transform_driver
from build_maternalbound_pack import read_pack

def driver_source(original):
 s=transform_driver(original).split('int main(int argc,char**argv){',1)[0]
 s+=r'''
static void observe(const char*stage,unsigned item){
 printf("QA_STORAGE {\"stage\":\"%s\",\"item\":%u,\"quantity\":%u,\"pool\":[",stage,item,quantity(item));
 for(unsigned i=0;i<KEY_ITEMS_POOL_SIZE;i++)printf("%s%u",i?",":"",key_items_pool[i]);
 printf("],\"bags\":[");for(unsigned p=0;p<4;p++){printf("%s[",p?",":"");for(unsigned i=0;i<14;i++)printf("%s%u",i?",":"",party_characters[p].items[i]);printf("]");}
 printf("],\"equipment\":[");for(unsigned p=0;p<4;p++){printf("%s[",p?",":"");for(unsigned i=0;i<4;i++)printf("%s%u",i?",":"",party_characters[p].equipment[i]);printf("]");}
 printf("],\"position\":[%u,%u]}\n",game_state.leader_x_coord,game_state.leader_y_coord);
}
static void previews(void){
 for(unsigned p=0;p<game_state.player_controlled_party_count;p++){
  unsigned member=game_state.party_members[p];show_character_inventory(2,member);WindowInfo*w=get_window(2);
  printf("QA_PREVIEW {\"member\":%u,\"items\":[",member);
  if(w)for(unsigned i=0;i<w->menu_count;i++)printf("%s%u",i?",":"",get_character_item(member,w->menu_items[i].userdata));printf("]}\n");
 }
}
int main(int argc,char**argv){
 if(argc!=8)return 2;char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 char*boot[]={"membership-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--redux-battle-fixture","0"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot)!=0)return 3;
 platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 7;game_set_fast_forward(true);audio_init();load_title_screen_script_data();unsigned kind=atoi(argv[3]),item=atoi(argv[4]),free=atoi(argv[5]),party=atoi(argv[6]);
 current_save_slot=1;
 if(kind==4){if(!state_dump_load_slots())return 4;observe("owner-loaded",204);idle(1);observe("owner-recovered",204);previews();audio_shutdown();return 0;}
 if(kind==0){printf("QA_CLASS [");for(unsigned i=0;i<256;i++)printf("%s%u",i?",":"",is_key_item_type(i));printf("]\n");audio_shutdown();return 0;}
 memset(&bt,0,sizeof(bt));memset(key_items_pool,0,sizeof(key_items_pool));party_ever_joined_mask=0;
 game_state.party_count=game_state.player_controlled_party_count=party;game_state.current_party_members=(1u<<party)-1;
 memset(game_state.party_order,0,6);memset(game_state.party_members,0,6);game_state.party_npc_1=game_state.party_npc_2=0;
 for(unsigned p=0;p<4;p++){memset(party_characters[p].items,0,14);memset(party_characters[p].equipment,0,4);if(p<party){game_state.party_order[p]=game_state.party_members[p]=p+1;migrate_key_items_to_pool(p+1);}}
 update_party();initialize_overworld_state();window_system_init();init_used_bg2_tile_map();text_setup_bg3();text_upload_font_tiles();text_load_window_gfx();text_load_flavour_palette(0);ow.mini_ghost_entity_id=-1;
 if(kind==1){give_item_to_character(1,item);give_item_to_character(1,item);migrate_key_items_to_pool(1);observe("two-given",item);previews();take_item_from_character(1,item);observe("one-taken",item);audio_shutdown();return 0;}
 for(unsigned p=0;p<party;p++)for(unsigned i=0;i<14-free;i++)give_item_to_character(p+1,90);
 key_items_give(item);key_items_give(202);observe("legacy-created",item);
 g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_OVERWORLD;g_mode_stack.state[0].overworld.phase=OWP_LOOP_START;
 if(kind==2){if(!save_game(0)||!load_game(0))return 5;observe("phone-loaded",item);}
 else{if(!state_dump_save_slots()||!state_dump_load_slots())return 6;observe("f6-loaded",item);
  g_mode_stack.depth=2;g_mode_stack.mode[1]=GAME_MODE_NONE;update_overworld_frame(0);observe("menu-guard",item);
  g_mode_stack.depth=1;ow.battle_mode=1;update_overworld_frame(0);observe("battle-guard",item);ow.battle_mode=0;}
 idle(1);observe("idle",item);
 if(!free){printf("QA_PENDING {\"find\":%u,\"selected\":%u}\n",find_item_in_inventory2(0xff,item),get_character_item(1,KEY_ITEMS_POOL_SELECTION_SLOT_BASE+item));take_item_from_character(1,90);idle(1);observe("space-recovered",item);}
 previews();audio_shutdown();return 0;
}
'''
 if original:s=s.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"')
 return s

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in ('build','native-source','assets','runtime','scratch','output','project'):ap.add_argument('--'+n,type=Path,required=True)
 ap.add_argument('--owner',type=Path);ap.add_argument('--only-owner',action='store_true');ap.add_argument('--original',action='store_true');ap.add_argument('--diagnostic',action='store_true');a=ap.parse_args()
 assert not a.scratch.exists();a.scratch.mkdir(parents=True);helper.DRIVER=driver_source(a.original);exe,build=helper.private_build(a)
 keysfile=a.project/'ccscript/redux/keyitems.ccs';defs=a.project/'ccscript/definitions/items.ccs'
 definitions={n:int(v,0) for n,v in re.findall(r'(?m)^\s*define\s+(\w+)\s*=\s*(0x[0-9A-Fa-f]+|\d+)',defs.read_text(encoding='utf-8'))}
 names=set(re.findall(r'use_help_submenu\((\w+),',keysfile.read_text(encoding='utf-8')));ids={definitions[n] for n in names}
 _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h');data=assets['data/item_configuration_table.bin']
 expected=[int(i<len(data)//39 and (data[i*39+25]&0x3c)==0x38 and not (data[i*39+28]&0x10) and (a.original or i in ids)) for i in range(256)]
 ordinary=[i for i in range(1,len(data)//39) if (data[i*39+25]&0x3c)==0x38 and not (data[i*39+28]&0x10) and i not in ids and i!=203]
 tests=[(0,0,14,1)]+([] if a.original else [(1,i,14,3) for i in ordinary]+[(k,i,f,p) for k in (2,3) for i in (166,197,201,204) for f in (0,1) for p in (1,3)])
 if a.only_owner:tests=[]
 if a.owner and not a.original:tests.append((4,204,14,3))
 rows=[]
 for index,t in enumerate(tests):
  session=a.scratch/f'case-{index}';session.mkdir()
  if t[0]==4:shutil.copytree(a.owner,session/'saves')
  run=subprocess.run([str(exe),str(a.assets.resolve()),str(session.resolve()),*map(str,t),'0'],cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=60)
  log=session/'native.log';log.write_bytes(run.stdout+run.stderr);events=[];errors=[]
  for line in run.stdout.decode(errors='replace').splitlines():
   if line.startswith(('QA_CLASS ','QA_STORAGE ','QA_PREVIEW ','QA_PENDING ')):
    kind,value=line.split(' ',1);events.append(dict(type=kind,actual=json.loads(value)))
  states={e['actual']['stage']:e['actual'] for e in events if e['type']=='QA_STORAGE'}
  if run.returncode:errors.append('nativeExit:'+str(run.returncode))
  k,item,free,party=t
  if k==0:
   observed=next((e['actual'] for e in events if e['type']=='QA_CLASS'),[])
   if observed!=expected:errors.append('sourceKeysClassification:'+str([i for i in range(min(len(observed),256)) if observed[i]!=expected[i]]))
  elif k==1:
   for stage,n in (('two-given',2),('one-taken',1)):
    s=states.get(stage,{})
    if s.get('quantity')!=n or not s.get('bags') or s['bags'][0].count(item)!=n or item in s['pool']:errors.append(stage+': wrong ordinary bag/count')
   for e in events:
    if e['type']=='QA_PREVIEW' and e['actual']['items'].count(item)!=(2 if e['actual']['member']==1 else 0):errors.append('wrong per-character shop preview')
  elif k in (2,3):
   for stage,s in states.items():
    if sum(b.count(item) for b in s['bags'])+s['pool'].count(item)!=1 or 202 not in s['pool']:errors.append(stage+': lost item/map')
   s=states.get('space-recovered' if not free else 'idle',{})
   if not s or item in s['pool'] or s['bags'][0].count(item)!=1:errors.append('old-save recovery did not reach regular bag')
   for stage in ('menu-guard','battle-guard'):
    if stage in states and states[stage]!=dict(states['f6-loaded'],stage=stage):errors.append(stage+': changed transient inventory')
   for e in events:
    if e['type']=='QA_PENDING' and (not e['actual']['find'] or e['actual']['selected']!=item):errors.append('full-bag item became inaccessible to scripts')
  else:
   before=states.get('owner-loaded',{});after=states.get('owner-recovered',{})
   if not after or 204 in after['pool'] or 197 in after['pool'] or after['bags'][0].count(204)!=1 or after['bags'][0].count(197)!=1:errors.append('owner recovery failed')
   if before and after and (before['equipment']!=after['equipment'] or before['position']!=after['position']):errors.append('owner equipment/position changed')
   for e in events:
    if e['type']=='QA_PREVIEW' and e['actual']['items'].count(204)!=(1 if e['actual']['member']==1 else 0):errors.append('owner shop ghost row remains')
  rows.append(dict(values=t,passed=not errors,errors=errors,events=events,logSha256=helper.digest(log)))
 report=dict(toolVersion='dev20-source-keys-membership',privateBuild=build,assetsSha256=helper.digest(a.assets),reduxRevision=helper.PIN,originalPack=a.original,sourceKeys=[dict(name=n,id=definitions[n]) for n in sorted(names)],pinnedSources=[dict(path=p.relative_to(a.project).as_posix(),sha256=helper.digest(p)) for p in (keysfile,defs)],ordinaryKeyCategoryIds=ordinary,cases=rows,allPassed=all(r['passed'] for r in rows),limits=['Prepared API/save/selector fixtures; no complete story or full shop transaction coverage. Old save inputs copied, owner files never changed.','All256 native classifications compared to packed categories and pinned Redux Keys membership. Original category policy remains a separate control.','Shared legacy pool has no original owner metadata; recovery uses first free active PC bag. Full parties retain items and allow source selectors/find/take until a slot becomes available.'],fullPlaythroughVerified=False)
 a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(cases=len(rows),passed=sum(r['passed'] for r in rows),failures=[dict(values=r['values'],errors=r['errors']) for r in rows if not r['passed']][:4])))
 if not report['allPassed'] and not a.diagnostic:raise SystemExit(1)
if __name__=='__main__':main()
