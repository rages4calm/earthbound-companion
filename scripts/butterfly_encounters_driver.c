/* Isolated native regressions. Asset tables come from the user's private pack. */
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <string.h>
#include "game/game_state.h"
#include "game/overworld.h"
#include "game/overworld_internal.h"
#include "game/battle.h"
#include "game/map_loader.h"
#include "game/maternalbound.h"
#include "entity/entity.h"
#include "entity/pathfinding.h"
#include "entity/sprite.h"
#include "core/math.h"
#include "data/assets.h"
#include "include/constants.h"
extern int eb_platform_main(int,char**);
extern int16_t callroutine_dispatch(uint32_t,int16_t,int16_t,uint16_t,uint16_t*);
extern void dispatch_tick_callback(uint32_t,int16_t);
extern void call_move_callback(int16_t);
#define CHECK(c) do { if(!(c)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#c);return 10;} }while(0)
int main(int argc,char **argv) {
    if(argc!=3)return 2;
    char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
    char *boot[]={"fixture","--assets",argv[1],"--session-dir",argv[2],"--save",save,
        "--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
    if(eb_platform_main(12,boot))return 2;
    CHECK(map_loader_init());load_enemy_spawn_data();
    memset(&ow,0,sizeof(ow));ow.enemy_spawns_enabled=1;
    event_flag_clear(EVENT_FLAG_MONSTER_OFF);event_flag_clear(EVENT_FLAG_WIN_GIEGU);
    /* This corner has no regular encounters in either supported pack. */
    for(unsigned y=0;y<5;y++)for(unsigned x=0;x<9;x++)CHECK(get_map_enemy_placement(x,y)==0);
    unsigned horizontal=1+(EB_VIEWPORT_WIDTH+63)/64;
    spawn_horizontal(0,0);CHECK(ow.enemy_spawn_counter==horizontal);
    ow.enemy_spawn_counter=0;spawn_vertical(0,0);CHECK(ow.enemy_spawn_counter==5);
    ow.enemy_spawn_counter=0;ow.enemy_spawns_enabled=0;
    spawn_horizontal(0,0);spawn_vertical(0,0);CHECK(ow.enemy_spawn_counter==0);
    ow.enemy_spawns_enabled=1;event_flag_set(EVENT_FLAG_MONSTER_OFF);
    spawn_horizontal(0,0);spawn_vertical(0,0);CHECK(ow.enemy_spawn_counter==0);
    event_flag_clear(EVENT_FLAG_MONSTER_OFF);event_flag_set(EVENT_FLAG_WIN_GIEGU);
    spawn_horizontal(0,0);spawn_vertical(0,0);CHECK(ow.enemy_spawn_counter==0);
    event_flag_clear(EVENT_FLAG_WIN_GIEGU);

    /* Find a real encounter-zero sector which permits butterflies, then use
     * flat cached terrain to isolate the real creation/duplicate-removal path. */
    const uint8_t *attrs=ASSET_DATA(ASSET_DATA_PER_SECTOR_ATTRIBUTES_BIN);
    int bx=-1,by=-1;
    for(unsigned y=1;y<159&&bx<0;y++)for(unsigned x=1;x<127;x++){
        unsigned category=read_u16_le(attrs+(y/2)*64+(x/4)*2)&7;
        if(get_map_enemy_placement(x,y)==0&&(category==0||category==2||category==4||category==5)){
            bx=x;by=y;break;
        }
    }
    CHECK(bx>=0);
    entity_system_init();clear_overworld_spritemaps();memset(sprite_vram_table,0,sizeof(sprite_vram_table));
    memset(ml.loaded_collision_tiles,0,sizeof(ml.loaded_collision_tiles));
    ml.screen_left_x=bx*8;ml.screen_top_y=by*8;
    ow.overworld_enemy_count=0;ow.overworld_enemy_maximum=20;
    ow.enemy_spawn_range_width=ow.enemy_spawn_range_height=8;rng_seed(0x56781234);
    for(unsigned i=0;i<4096&&!ow.magic_butterfly_spawned;i++){
        ow.enemy_spawn_counter=15;attempt_enemy_spawn(bx,by,0);
    }
    CHECK(ow.magic_butterfly_spawned==1);CHECK(ow.overworld_enemy_count==1);
    int butterfly=-1;
    for(int i=0;i<23;i++)if(entities.script_table[i]>=0&&entities.enemy_ids[i]==ENEMY_MAGIC_BUTTERFLY)butterfly=i;
    CHECK(butterfly>=0);
    for(unsigned i=0;i<128;i++){ow.enemy_spawn_counter=15;attempt_enemy_spawn(bx,by,0);}
    CHECK(ow.overworld_enemy_count==1);remove_entity(butterfly);CHECK(!ow.magic_butterfly_spawned);

    /* Exercise all regular multi-enemy group compositions with actual per-mode
     * sprite sizes. Drive native path movement/contact, not a mocked join list. */
    const uint8_t *ptr=ASSET_DATA(ASSET_DATA_BTL_ENTRY_PTR_TABLE_BIN);
    const uint8_t *groups=ASSET_DATA(ASSET_DATA_ENEMY_BATTLE_GROUPS_TABLE_BIN);
    unsigned tested=0;
    for(unsigned g=0;g<ENEMY_GROUP_BOSS_START;g++){
        uint32_t rp=ptr[g*8]|ptr[g*8+1]<<8|ptr[g*8+2]<<16;
        const uint8_t *gp=groups+rp-0xD0D52D;int ids[8],n=0;
        for(int e=0;e<4&&gp[0]!=255;e++,gp+=3)
            for(unsigned c=0;c<gp[0]&&n<8;c++)ids[n++]=read_u16_le(gp+1);
        if(n<2)continue;
        memset(&bt,0,sizeof(bt));memset(&ow,0,sizeof(ow));entity_system_init();
        memset(ml.loaded_collision_tiles,0,sizeof(ml.loaded_collision_tiles));
        game_state.camera_mode=game_state.walking_style=0;game_state.party_count=1;
        game_state.current_party_members=24;write_u16_le(game_state.party_entity_slots,24);
        entities.script_table[24]=2;entities.abs_x[24]=entities.abs_y[24]=512;entities.sizes[24]=0;
        game_state.leader_x_coord=game_state.leader_y_coord=512;
        for(int i=0;i<n;i++){
            uint32_t off;entities.script_table[i]=19;
            entities.sizes[i]=load_sprite_group_properties(enemy_config_table[ids[i]].overworld_sprite,&off);
            entities.abs_x[i]=512+i*16;entities.abs_y[i]=512;entities.enemy_ids[i]=ids[i];
            entities.npc_ids[i]=0x8000+g;entities.movement_speeds[i]=0x200;entities.move_callback[i]=3;
        }
        bt.touched_enemy=0;ert.enemy_pathfinding_target_entity=24;initiate_enemy_encounter();
        for(int t=0;t<120;t++)for(int i=1;i<n;i++){
            if(entities.tick_callback_hi[i]&0xC000)continue;
            ert.current_entity_slot=i;dispatch_tick_callback(0xC0D7F7,i);call_move_callback(i);
            uint16_t pc=0;callroutine_dispatch(0xC0D5B0,i,0,0,&pc);
        }
        CHECK(bt.enemies_in_battle==n);tested++;
    }
    printf("PASS: horizontal/vertical encounter-zero scans; spawn suppression; real butterfly creation, duplicate suppression and removal; %u native multi-enemy groups; Redux=%d\n",tested,maternalbound_enabled());
    return 0;
}
