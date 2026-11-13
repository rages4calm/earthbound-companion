/* Private-pack, isolated VM item handoff regression checks. */
#include "game/display_text.c"
#include "game/display_text_internal.h"
#include "game/inventory.h"
#include <stdio.h>
extern int eb_platform_main(int,char**);
#define CHECK(x) do {if(!(x)){fprintf(stderr,"FAIL %d: %s\n",__LINE__,#x);return 10;}}while(0)
static void dispatch(uint8_t sub,uint8_t who,uint8_t item){
 static uint8_t bytes[3];bytes[0]=sub;bytes[1]=who;bytes[2]=item;
 dialogue_blob=bytes;dialogue_blob_size=sizeof(bytes);
 ScriptReader r={TEXT_SRC_DIALOGUE,0,sizeof(bytes),-1};cc_1d_dispatch(&r);
}
int main(int argc,char**argv){
 char*boot[]={"fixture","--assets",argv[1],"--session-dir",argv[2],"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};CHECK(!eb_platform_main(10,boot));
 text_system_init();window_system_init();create_window(WINDOW_TEXT_STANDARD);
 game_state.player_controlled_party_count=3;game_state.party_count=3;game_state.party_members[0]=1;game_state.party_members[1]=2;game_state.party_members[2]=3;
 unsigned cases=0;
 /* Literal and independent zero operands for both award opcodes. Imported-
  * style unset joined flags keep the key in inventory; joined routes to pool. */
 for(int pool=0;pool<2;pool++)for(int opcode=0;opcode<2;opcode++)for(int target=1;target<=3;target++)for(int form=0;form<4;form++){
  memset(key_items_pool,0,sizeof(key_items_pool));memset(party_characters,0,sizeof(party_characters));party_ever_joined_mask=pool?7:0;
  unsigned item=174;set_argument_memory((form&1)?target:0);set_working_memory((form&2)?item:0);
  dispatch(opcode?0x0e:0,(form&1)?0:target,(form&2)?0:item);
  CHECK(get_working_memory()==target);
  if(pool)CHECK(key_items_pool[0]==item);else CHECK(party_characters[target-1].items[0]==item);
  if(opcode){CHECK(get_argument_memory()==KEY_ITEMS_POOL_USE_SLOT_SENTINEL);CHECK(get_character_item(target,(uint16_t)get_argument_memory())==item);}
  cases++;
 }
 /* Reproduce the courier handoff: recipient retained in argument memory,
  * subsequent flag check leaves working memory zero. */
 memset(key_items_pool,0,sizeof(key_items_pool));memset(party_characters,0,sizeof(party_characters));party_ever_joined_mask=0;
 set_argument_memory(1);set_working_memory(0);dispatch(0x0e,0,174);CHECK(party_characters[0].items[0]==174);
 /* Keep the existing last-slot receipt fix and full-inventory behavior. */
 for(int slot=0;slot<ITEM_INVENTORY_SIZE;slot++){
  memset(party_characters[0].items,42,ITEM_INVENTORY_SIZE);party_characters[0].items[slot]=0;set_argument_memory(1);set_working_memory(0);dispatch(0x0e,0,1);
  CHECK(get_working_memory()==1&&get_argument_memory()==slot+1);CHECK(party_characters[0].items[slot]==1);
 }
 memset(party_characters[0].items,42,ITEM_INVENTORY_SIZE);set_argument_memory(1);set_working_memory(0);dispatch(0x0e,0,1);CHECK(get_working_memory()==0&&get_argument_memory()==0);
 if(maternalbound_enabled()){
  CHECK(display_text_init());close_all_windows();create_window(WINDOW_TEXT_STANDARD);
  memset(party_characters[0].items,0,ITEM_INVENTORY_SIZE);memset(key_items_pool,0,sizeof(key_items_pool));party_ever_joined_mask=0;
  event_flag_clear(781);set_argument_memory(1);set_working_memory(0);set_instant_printing();
  ModeState courier={0};CHECK(dt_make_child_init(&courier,0xC7A63E));
  for(int step=0;step<8&&!party_characters[0].items[0];step++)mode_step_display_text(&courier);
  CHECK(party_characters[0].items[0]==174);
 }
 printf("PASS: %u register cases, Zombie Paper handoff with zero working memory, all14 receipt slots, full-inventory refusal; Redux=%d\n",cases,maternalbound_enabled());return 0;
}

