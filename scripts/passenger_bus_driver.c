/* Isolated real-pack selection/boarding/departure checks; no campaign save. */
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <string.h>
#include "core/mode_stack.h"
#include "data/assets.h"
#include "data/event_script_data.h"
#include "entity/entity.h"
#include "entity/sprite.h"
#include "game/overworld.h"
#include "game/map_loader.h"
#include "game/game_state.h"
#include "game/display_text.h"
#include "game/maternalbound.h"
#include "game/audio.h"
extern int eb_platform_main(int,char**);
extern int cr_bank_idx;
extern int16_t cr_movement_cmd_store_sprite_pos(int16_t,int16_t,uint16_t,uint16_t*);
#define CHECK(c) do{if(!(c)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#c);return 10;}}while(0)
int main(int argc,char **argv){
    if(argc!=3)return 2;
    char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
    char *boot[]={"fixture","--assets",argv[1],"--session-dir",argv[2],"--save",save,
        "--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
    if(eb_platform_main(12,boot))return 2;
    const NpcConfig *npc=(const NpcConfig*)ASSET_DATA(ASSET_DATA_NPC_CONFIG_TABLE_BIN);
    CHECK(ASSET_SIZE(ASSET_DATA_NPC_CONFIG_TABLE_BIN)>585*sizeof(*npc));
    CHECK(npc[584].sprite==205&&npc[584].event_script==595);
    static const uint8_t operand[]={205,0};
    int operand_bank=register_script_bank(operand,sizeof(operand),0,0xA0);CHECK(operand_bank>=0);
    audio_init();unsigned cases=0;
    /* Passenger arrival/route scripts from all three towns and both directions. */
    static const unsigned routes[]={64,66,67,68,69,70,202,203,204,205,206,207,208,209,
        454,455,456,457,458,459,460,461,462,463,464};
    static const int slots[]={0,7,20};
    for(unsigned route=0;route<sizeof(routes)/sizeof(routes[0]);route++)
    for(unsigned ti=0;ti<3;ti++)for(unsigned pi=0;pi<3;pi++){
        if(ti==pi)continue;
        int traffic=slots[ti],passenger=slots[pi],walker=22;
        entity_system_init();clear_overworld_spritemaps();memset(sprite_vram_table,0,sizeof(sprite_vram_table));
        memset(&ow,0,sizeof(ow));game_state.party_count=0;
        CHECK(create_entity(205,595,traffic,6000,9080)==traffic);entities.npc_ids[traffic]=584;
        CHECK(create_entity(205,routes[route],passenger,5552,9000)==passenger);
        CHECK(create_entity(106,73,walker,5500,9010)==walker);
        CHECK(entities.npc_ids[passenger]==0xFFFFu);
        CHECK(find_entity_by_sprite_id(205)==passenger);
        uint16_t traffic_pc=scripts.pc[entities.script_index[traffic]];
        uint8_t traffic_bank=scripts.pc_bank[entities.script_index[traffic]];
        cr_bank_idx=operand_bank;uint16_t out_pc=0;
        cr_movement_cmd_store_sprite_pos(walker,entities.script_index[walker],0,&out_pc);
        CHECK(out_pc==2&&entities.var[6][walker]==5552&&entities.var[7][walker]==9000);
        /* Actual post-fare script: change bus movement, hide party, set bus
         * music, and refocus camera. All must choose the same passenger bus. */
        ModeState text={0};CHECK(dt_make_child_init(&text,maternalbound_enabled()?0xC78536u:0x1454D2u));
        CHECK(mode_step_display_text(&text).kind==STEP_POP);
        int bank;uint16_t offset;CHECK(resolve_script_id(203,&bank,&offset));
        int ps=entities.script_index[passenger];
        CHECK(scripts.pc[ps]==offset&&scripts.pc_bank[ps]==bank);
        CHECK(ow.camera_focus_entity==passenger&&game_state.camera_mode==2);
        CHECK(scripts.pc[entities.script_index[traffic]]==traffic_pc);
        CHECK(scripts.pc_bank[entities.script_index[traffic]]==traffic_bank);
        CHECK(entities.abs_x[traffic]==6000&&entities.abs_y[traffic]==9080);
        /* Free/inactive slots cannot steal the bus target. */
        entities.script_table[passenger]=-1;CHECK(find_entity_by_sprite_id(205)==traffic);
        entities.script_table[traffic]=-1;CHECK(find_entity_by_sprite_id(205)==-1);
        cases++;
    }
    entity_system_init();entities.sprite_ids[1]=106;entities.sprite_ids[4]=106;
    entities.script_table[1]=entities.script_table[4]=73;
    CHECK(find_entity_by_sprite_id(106)==1);CHECK(find_entity_by_sprite_id(9999)==-1);
    audio_shutdown();printf("PASS: %u bus configurations; real boarding-position callroutine and post-fare movement/camera script; traffic unchanged; inactive/ordinary sprite controls; Redux=%d\n",cases,maternalbound_enabled());
    return 0;
}
