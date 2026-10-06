# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify native virtual selector access, actual CC adapters and private save APIs."""
import argparse,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
from build_maternalbound_pack import read_pack

C_MAIN=r'''
#include "core/state_dump.h"
#include "game/display_text_internal.h"
#include "game/audio.h"
#include "data/event_script_data.h"
static void fixture(unsigned active,unsigned joined,unsigned full){
 memset(&bt,0,sizeof(bt));memset(key_items_pool,0,sizeof(key_items_pool));memset(game_state.party_members,0,6);memset(game_state.party_order,0,6);memset(game_state.escargo_express_items,0,36);memset(game_state.unknownB6,0,3);memset(game_state.unknownB8,0,3);
 party_ever_joined_mask=joined;game_state.party_npc_1=game_state.party_npc_2=0;unsigned count=0;
 for(unsigned c=0;c<4;c++){memset(party_characters[c].items,0,14);memset(party_characters[c].equipment,0,4);memset(party_characters[c].afflictions,0,7);party_characters[c].current_hp=party_characters[c].max_hp=100;party_characters[c].current_pp=party_characters[c].max_pp=50;
  if(active&(1u<<c)){game_state.party_order[count]=game_state.party_members[count]=c+1;count++;if(full)for(unsigned s=0;s<14;s++)give_item_to_specific_character(c+1,87);}}
 game_state.party_count=game_state.player_controlled_party_count=count;game_state.current_party_members=active;update_party();
 g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_OVERWORLD;g_mode_stack.state[0].overworld.phase=OWP_LOOP_START;
}
static unsigned operand(unsigned sub,unsigned length){
 const unsigned char*p=ASSET_DATA(ASSET_DIALOGUE_DIALOGUE_BIN);size_t size=ASSET_SIZE(ASSET_DIALOGUE_DIALOGUE_BIN);for(size_t i=0;i+length<size;i++){if(p[i]!=sub)continue;unsigned j=1;for(;j<=length&&p[i+j]==0;j++);if(j==length+1)return i;}exit(20);
}
static void cc(unsigned group,unsigned sub,unsigned character,unsigned slot){
 unsigned length=2,off=operand(sub,length);ScriptReader r={TEXT_SRC_DIALOGUE,off,ASSET_SIZE(ASSET_DIALOGUE_DIALOGUE_BIN),-1};ModeState child={0};GameMode mode=0;uint8_t resume=0;uint16_t window=0;uint32_t arg=0;set_working_memory(character);set_argument_memory(slot);
 if(group==0x19)cc_19_dispatch(&r);else cc_1d_dispatch(&r);
 if(r.ptr_off!=off+3)exit(21);
}
int main(int argc,char**argv){
 if(argc!=3)return 2;char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);char*boot[]={"selection-bridge-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--redux-battle-fixture","0"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot)!=0||!maternalbound_enabled())return 3;platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 4;audio_init();load_title_screen_script_data();
 const unsigned activeMasks[]={1,4,15,0,2,1,4},joinedMasks[]={1,4,15,15,0,15,15},characters[]={0,1,2,3,4,5,6,255,65535};
 for(unsigned scene=0;scene<7;scene++)for(unsigned item=1;item<256;item++){
  fixture(activeMasks[scene],joinedMasks[scene],scene==2);key_items_give(item);unsigned loc=0x100+item;
  for(unsigned ci=0;ci<9;ci++){unsigned c=characters[ci],a=get_character_item(c,loc),b=get_character_item(c,loc);printf("QA_ACCESS {\"scene\":%u,\"active\":%u,\"joined\":%u,\"item\":%u,\"character\":%u,\"reads\":[%u,%u],\"pool\":%u}\n",scene,activeMasks[scene],joinedMasks[scene],item,c,a,b,key_items_find(item));}
 }
 for(unsigned item=1;item<256;item++)if(is_key_item_type(item)){
  unsigned loc=0x100+item;fixture(1,1,0);give_item_to_character(1,item);party_characters[0].items[0]=87;party_characters[0].items[1]=item;party_characters[0].equipment[0]=1;
  unsigned a=get_character_item(1,loc),b=get_character_item(1,loc),eq=check_item_equipped(1,loc),equip=equip_item(1,loc),taken=remove_item_from_inventory(1,loc),again=get_character_item(1,loc);
  printf("QA_REMOVE {\"item\":%u,\"reads\":[%u,%u],\"checkEquipped\":%u,\"equip\":%u,\"taken\":%u,\"after\":%u,\"bag\":[%u,%u],\"equipment\":%u}\n",item,a,b,eq,equip,taken,again,party_characters[0].items[0],party_characters[0].items[1],party_characters[0].equipment[0]);
  fixture(1,1,0);give_item_to_character(1,202==item?166:202);give_item_to_character(1,item);unsigned removeOther=key_items_remove(202==item?166:202);unsigned stable=get_character_item(1,loc);printf("QA_STABLE {\"item\":%u,\"removedOther\":%u,\"read\":%u}\n",item,removeOther,stable);
  fixture(1,1,0);give_item_to_character(1,item);cc(0x1d,0x0c,1,loc);unsigned status=get_working_memory();cc(0x19,0x1c,1,loc);printf("QA_QUEUE {\"item\":%u,\"storageStatus\":%u,\"queue\":%u,\"source\":%u,\"pool\":%u}\n",item,status,game_state.unknownB6[0],game_state.unknownB8[0],key_items_find(item));
  fixture(1,1,0);give_item_to_character(1,item);unsigned stored=escargo_express_move(1,loc);printf("QA_STORE_API {\"item\":%u,\"result\":%u,\"stored\":%u,\"pool\":%u}\n",item,stored,game_state.escargo_express_items[0],key_items_find(item));
 }
 for(unsigned c=0;c<9;c++)for(unsigned s=0;s<19;s++){
  const unsigned slots[]={0,15,255,256,512,65534,0x101,0x102,0x103,0x104,0x105,0x106,0x107,0x108,0x109,0x10a,0x10b,0x10c,0x10d};fixture(1,1,0);party_characters[0].items[0]=87;for(unsigned e=0;e<4;e++)party_characters[0].equipment[e]=s%14+1;unsigned loc=slots[s],a=get_character_item(characters[c],loc),b=check_item_equipped(characters[c],loc),e=equip_item(characters[c],loc),rm=remove_item_from_inventory(characters[c],loc);printf("QA_GUARD {\"character\":%u,\"slot\":%u,\"get\":%u,\"check\":%u,\"equip\":%u,\"remove\":%u,\"bag\":%u}\n",characters[c],loc,a,b,e,rm,party_characters[0].items[0]);
 }
 for(unsigned route=0;route<2;route++)for(unsigned active=1;active<=15;active+=14)for(unsigned full=0;full<2;full++){
  fixture(active,active,full);give_item_to_character(1,166);give_item_to_character(1,202);unsigned before=get_character_item(1,0x1a6);current_save_slot=1;bool saved=route?state_dump_save_slots():save_game(0);key_items_remove(166);key_items_remove(202);bool loaded=route?state_dump_load_slots():load_game(0);unsigned a=get_character_item(1,0x1a6),b=get_character_item(1,0x1a6),rm=remove_item_from_inventory(1,0x1a6);printf("QA_SAVE {\"route\":%u,\"active\":%u,\"full\":%u,\"save\":%u,\"load\":%u,\"before\":%u,\"reads\":[%u,%u],\"remove\":%u,\"banana\":%u,\"map\":%u,\"ordinary0\":%u}\n",route,active,full,saved,loaded,before,a,b,rm,key_items_find(166),key_items_find(202),party_characters[0].items[0]);
 }
 for(unsigned scene=0;scene<7;scene++)for(unsigned ci=0;ci<9;ci++){
  fixture(activeMasks[scene],joinedMasks[scene],scene==2);key_items_give(87);key_items_give(166);key_items_give(202);unsigned c=characters[ci],first=key_items_pool_first_selectable(c),again=key_items_pool_first_selectable(c);
  printf("QA_PREFLIGHT_POOL {\"active\":%u,\"joined\":%u,\"character\":%u,\"reads\":[%u,%u],\"owned\":[%u,%u,%u]}\n",activeMasks[scene],joinedMasks[scene],c,first,again,key_items_find(87),key_items_find(166),key_items_find(202));
 }
 for(unsigned ordinary=0;ordinary<2;ordinary++){
  fixture(1,1,0);give_item_to_character(1,166);if(ordinary)give_item_to_specific_character(1,87);unsigned direct=get_character_item(1,1);cc(0x19,0x19,1,1);
  printf("QA_UNRELATED_SLOT_ONE {\"ordinary\":%u,\"direct\":%u,\"ccItem\":%u,\"ccCharacter\":%u,\"pool\":%u}\n",ordinary,direct,(unsigned)get_argument_memory(),(unsigned)get_working_memory(),key_items_find(166));
 }
 fixture(1,1,0);printf("QA_EMPTY_PREFLIGHT_POOL {\"read\":%u}\n",key_items_pool_first_selectable(1));
 key_items_set_use_in_progress(166);unsigned a=get_character_item(1,0xffff),b=get_character_item(1,0xffff);printf("QA_USE_SENTINEL {\"reads\":[%u,%u]}\n",a,b);audio_shutdown();return 0;
}
'''

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in('build','native-source','assets','runtime','scratch','output','project','executed-source'):ap.add_argument('--'+n,type=Path,required=True)
 ap.add_argument('--original',action='store_true');ap.add_argument('--diagnostic',action='store_true');a=ap.parse_args()
 if a.scratch.exists():raise ValueError('Fresh private scratch required')
 a.scratch.mkdir(parents=True);s=helper.DRIVER.split('static unsigned pump(void)',1)[0]+C_MAIN
 if a.original:s=s.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"').replace('||!maternalbound_enabled()','||maternalbound_enabled()')
 helper.DRIVER=s;exe,build=helper.private_build(a);session=a.scratch/'session';session.mkdir()
 p=subprocess.run([str(exe),str(a.assets.resolve()),str(session.resolve())],cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=120);(session/'native.log').write_bytes(p.stdout+p.stderr)
 _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h');table=assets['data/item_configuration_table.bin'];rows=[]
 def key(i):return i<len(table)//39 and(table[i*39+25]&0x3c)==0x38 and not(table[i*39+28]&16)and(i!=203 or a.original)
 for line in p.stdout.decode(errors='replace').splitlines():
  if not line.startswith('QA_'):continue
  kind,raw=line.split(' ',1);r=json.loads(raw);errors=[];item=r.get('item',0)
  if kind=='QA_PREFLIGHT_POOL':
   c=r['character'];want=166 if 1<=c<=4 and r['active']&(1<<(c-1))and r['joined']&(1<<(c-1))else 0
   if r['reads']!=[want,want]or r['owned']!=[87,166,202]:errors.append('Read-only preflight pool eligibility or non-key exclusion differs')
  elif kind=='QA_UNRELATED_SLOT_ONE':
   want=87 if r['ordinary']else 0
   if r['direct']!=want or r['ccItem']!=want or r['ccCharacter']!=1 or r['pool']!=166:errors.append('Unrelated ordinary slot one read was reinterpreted or consumed pool')
  elif kind=='QA_EMPTY_PREFLIGHT_POOL':
   if r['read']!=0:errors.append('Empty pool preflight must return zero')
  elif kind=='QA_ACCESS':
   c=r['character'];want=item if 1<=c<=4 and r['active']&(1<<(c-1))and r['joined']&(1<<(c-1))and key(item)else 0
   if r['reads']!=[want,want]or r['pool']!=item:errors.append('Active/joined/packed key guard or repeat read changed ownership')
  elif kind=='QA_REMOVE':
   if r['reads']!=[item,item]or r['checkEquipped']or r['equip']or r['taken']!=1 or r['after']or r['bag']!=[87,item]or r['equipment']!=1:errors.append('Virtual take altered ordinary slots/equipment or read protocol')
  elif kind=='QA_STABLE':
   if r['read']!=item:errors.append('Pool compaction changed stable selected item')
  elif kind=='QA_QUEUE':
   if r['storageStatus']!=int(bool(table[item*39+28]&64))or r['queue']!=item or r['source']!=1 or r['pool']:errors.append('Real CC1D0C/CC191C virtual location failed')
  elif kind=='QA_STORE_API':
   if r['result']!=1 or r['stored']!=item or r['pool']:errors.append('Ordinary storage API bridge changed ownership')
  elif kind=='QA_GUARD':
   if any(r[f]for f in('get','check','equip'))or r['remove']!=r['character']or r['bag']!=87:errors.append('Invalid/synthetic virtual location escaped slot guards')
  elif kind=='QA_SAVE':
   if not r['save']or not r['load']or r['before']!=166 or r['reads']!=[166,166]or r['remove']!=1 or r['banana']or r['map']!=202 or r['ordinary0']!=(87 if r['full']else 0):errors.append('Phone/F6 native save API did not preserve bridge/pool/bags')
  elif kind=='QA_USE_SENTINEL':
   if r['reads']!=[166,0]:errors.append('Existing one-shot Use sentinel changed')
  else:errors.append('Unknown evidence')
  rows.append(dict(kind=kind,actual=r,passed=not errors,errors=errors))
 refs=['src/game/inventory.c','src/game/inventory.h','src/game/display_text_menus.c','src/game/display_text_cc.c','src/game/game_state.c','src/core/state_dump.c']
 expected_rows=16065+4*sum(key(i)for i in range(1,256))+171+8+1+66
 report=dict(schemaVersion=1,expectedRowCount=expected_rows,toolVersion='dev21-key-pool-selection-bridge',privateBuild=build,nativeExitCode=p.returncode,runtimeSha256={n:helper.digest(a.runtime/n)for n in('player.exe','observer.exe')},assetsSha256=helper.digest(a.assets),originalPack=a.original,reduxRevision=helper.PIN,executedSourceReferences=[dict(path=n,sha256=helper.digest(a.executed_source/n))for n in refs],cases=rows,allPassed=p.returncode==0 and len(rows)==expected_rows and all(r['passed']for r in rows),limits=['Direct production APIs plus actual packed operand dispatchers; not complete gameplay callers. All 255 nonzero byte item IDs with active/joined/invalid-character controls are tested in a privately constructed pool; non-key pool entries are negative fixtures, not claimed reachable ownership.','Legacy bag+pool same-item shape is explicitly constructed before APIs. Stable virtual ID survives pool compaction; it does not identify a mutable pool index.','Storage API intentionally bypasses source CANNOT_STORE guard; actual CC1D0C source guard is checked separately. Source parent scripts remain responsible for permission.','Private phone/F6 save APIs round-trip in one process; actual fresh-process captured menu continuation is covered in the separate Monkey reports. Existing Use sentinel remains one-shot. No owner assets/saves modified.'],fullConversionVerified=False)
 a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(cases=len(rows),passed=sum(r['passed']for r in rows),nativeExit=p.returncode,failures=[r for r in rows if not r['passed']][:3])))
 if not report['allPassed']and not a.diagnostic:raise SystemExit(1)
if __name__=='__main__':main()
