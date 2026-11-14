
#include "game/display_text.c"
#include "data/assets.h"
#include "game/map_loader.h"
#include "game/overworld.h"
#include "entity/entity.h"
#include "platform/pc_options.h"
#include <stdio.h>
extern int eb_platform_main(int,char**);
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL %d: %s\n",__LINE__,#x);return 10;}}while(0)
int main(int argc,char**argv){char*boot[]={"fixture","--assets",argv[1],"--session-dir",argv[2],"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};CHECK(!eb_platform_main(10,boot));
 text_system_init();display_text_init();window_system_init();entity_system_init();map_loader_init();pc_options.instant_text=1;
 game_state.party_count=game_state.player_controlled_party_count=4;for(int i=0;i<4;i++){game_state.party_members[i]=game_state.party_order[i]=i+1;party_characters[i].level=20;}party_ever_joined_mask=15;
 const NpcConfig*n=(const NpcConfig*)ASSET_DATA(ASSET_DATA_NPC_CONFIG_TABLE_BIN);unsigned count=0;
 for(unsigned id=0;id<1584;id++){
  if(n[id].type!=2 || (n[id].item==0 || n[id].item>=256 || is_key_item_type(n[id].item) || n[id].item==135 || n[id].item==195 || n[id].item==253))continue;

  for(unsigned who=0;who<4;who++)memset(party_characters[who].items,0,ITEM_INVENTORY_SIZE);memset(key_items_pool,0,sizeof(key_items_pool));close_all_windows();create_window(WINDOW_TEXT_STANDARD);event_flag_clear(n[id].event_flag);event_flag_set(781);ow.interacting_npc_id=id;dt.current_interacting_event_flag=n[id].event_flag;set_working_memory(n[id].item);set_argument_memory(0);
  ModeState init={0};CHECK(dt_make_child_init(&init,n[id].text_pointer));memset(&g_mode_stack,0,sizeof(g_mode_stack));mode_push(GAME_MODE_DISPLAY_TEXT,&init);
  for(unsigned tick=0;tick<10000&&g_mode_stack.depth;tick++){
   unsigned d=g_mode_stack.depth-1;unsigned mode=g_mode_stack.mode[d];
   if(mode==GAME_MODE_TEXT_PROMPT||mode==GAME_MODE_TEXT_DELAY){mode_pop(0);continue;}
   set_instant_printing();StepResult r=mode_dispatch_step(mode,&g_mode_stack.state[d]);if(r.kind==STEP_PUSH)mode_push(r.push_mode,r.push_init);else if(r.kind==STEP_POP)mode_pop(r.pop_result);
  }
  CHECK(!g_mode_stack.depth);CHECK(party_characters[0].items[0]==n[id].item);count++;
 }
 CHECK(count>0);printf("PASS %u ordinary item-box scripts; Redux=%d\n",count,maternalbound_enabled());return 0;}
