/* Focused private-asset regressions; no ROM or save data embedded. */
#include <stdio.h>
#include <string.h>
#include "core/memory.h"
#include "core/math.h"
#include "game/game_state.h"
#include "game/overworld.h"
#include "game/map_loader.h"
#include "game/overworld_internal.h"
#include "game/battle.h"
#include "game/window.h"
#include "game/text.h"
#include "entity/entity.h"
#include "entity/sprite.h"
#include "data/assets.h"
#include "snes/ppu.h"
#include "include/constants.h"
extern int eb_platform_main(int,char**);
#define CHECK(x) do {if(!(x)){fprintf(stderr,"FAIL %d: %s\n",__LINE__,#x);return 10;}} while(0)
int main(int argc,char **argv) {
    CHECK(argc==3);
    char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
    char *args[]={"fixture","--assets",argv[1],"--session-dir",argv[2],"--save",save,
        "--allow-redux-development","--no-achievements","--headless","--frames","1","--inspect-shuffle"};
    CHECK(!eb_platform_main(sizeof(args)/sizeof(args[0]),args));
#ifdef CHECK_SPAWNS
    CHECK(map_loader_init());load_enemy_spawn_data();
    int coords[][2]={{106,38},{57,85},{65,85},{57,89},{65,89}};
    unsigned total_major=0;
    for(unsigned k=0;k<5;k++) {
        unsigned major=0;
        for(unsigned trial=0;trial<64;trial++) {
            entity_system_init();clear_overworld_spritemaps();memset(sprite_vram_table,0,sizeof(sprite_vram_table));
            ow.enemy_spawns_enabled=1;ow.overworld_enemy_maximum=10;
            /* Live enemies in the room being left: actual removal used to wrap
             * zero to 65534, then suppress every destination spawn attempt. */
            int e0=create_entity(enemy_config_table[142].overworld_sprite,19,-1,0,0);
            int e1=create_entity(enemy_config_table[142].overworld_sprite,19,-1,0,0);
            CHECK(e0>=0 && e1>=0);entities.npc_ids[e0]=entities.npc_ids[e1]=0x8001;
            ow.overworld_enemy_count=2;
            game_state.leader_x_coord=coords[k][0]*64+32;
            game_state.leader_y_coord=coords[k][1]*64+32;
            rng_seed(0x56781234u+trial*0x10203u);
            load_map_at_position(game_state.leader_x_coord,game_state.leader_y_coord);
            CHECK(ow.overworld_enemy_count<=10);
            unsigned live=0;
            for(int e=0;e<MAX_ENTITIES;e++)if(entities.script_table[e]>=0 && (entities.npc_ids[e]&0xf000)==0x8000) {
                live++;if(entities.enemy_ids[e]==143)major++;
            }
            CHECK(live==ow.overworld_enemy_count);
            clear_all_enemies();CHECK(ow.overworld_enemy_count==0);
        }
        CHECK(major>0);total_major+=major;
    }
    /* Repair an older snapshot with the impossible wrapped count. */
    entity_system_init();int e=create_entity(enemy_config_table[142].overworld_sprite,19,-1,0,0);CHECK(e>=0);entities.npc_ids[e]=0x8001;
    ow.overworld_enemy_count=65535;overworld_savestate_rebind();CHECK(ow.overworld_enemy_count==1);
    ow.overworld_enemy_count=0;remove_entity(e);CHECK(ow.overworld_enemy_count==0);
    printf("PASS: 320 real Fire Spring room-entry spawn scans, %u Major Psychic Psychos; removal count, old-state recovery\n",total_major);
#else
    memset(&bt,0,sizeof(bt));
    bt.current_battle_sprites_allocated=2;
    bt.current_battle_sprite_enemy_ids[0]=1;bt.current_battle_sprite_enemy_ids[1]=68;
    Battler *b=&bt.battlers_table[FIRST_ENEMY_INDEX];battle_init_enemy_stats(b,68);
    b->consciousness=1;b->ally_or_enemy=1;b->sprite=1;b->row=0;b->sprite_x=100;b->sprite_y=100;b->vram_sprite_index=1;
    bt.battle_spritemaps[1]=0x21;bt.battle_spritemaps[4]=0x80;
    bt.battle_spritemaps[81]=0x45;bt.battle_spritemaps[84]=0x80;
    render_all_battle_sprites();CHECK(b->vram_sprite_index==1 && ppu.oam[0].tile==0x45);
    /* ENEMY_EXTENDER changes the AI id, leaving the loaded sprite allocation. */
    b->id=185;render_all_battle_sprites();CHECK(b->vram_sprite_index==1 && ppu.oam[0].tile==0x45);
    /* Pokey/Devil's Machine repacking still rebinds a found id to slot zero. */
    b->id=68;bt.current_battle_sprites_allocated=1;bt.current_battle_sprite_enemy_ids[0]=68;
    render_all_battle_sprites();CHECK(b->vram_sprite_index==0 && ppu.oam[0].tile==0x21);
    /* Both actual drop paths, deterministic real RNG, every rarity tier;
     * only Sword of Kings receives the owner-approved one-tier increase. */
    static EnemyData configs[NUM_ENEMIES];memcpy(configs,enemy_config_table,sizeof(configs));enemy_config_table=configs;
    text_system_init();window_system_init();memset(&bt,0,sizeof(bt));
    bt.enemies_in_battle=1;bt.enemies_in_battle_ids[0]=68;
    battle_init_enemy_stats(&bt.battlers_table[FIRST_ENEMY_INDEX],68);
    memset(game_state.party_members,0,sizeof(game_state.party_members));event_flag_clear(EVENT_FLAG_BUNBUN);
    unsigned checks=0;
    for(unsigned item=0;item<2;item++)for(unsigned rate=0;rate<8;rate++)for(unsigned seed=1;seed<=128;seed++) {
        configs[68].item_dropped=item?35:1;configs[68].item_drop_rate=rate;
        unsigned effective=rate+(item && rate<6);unsigned mask=effective<7 ? 0x7f>>effective : 0;
        rng_seed(seed);rand_limit(1);unsigned expected=(rand_byte()&mask)?0:configs[68].item_dropped;
        rng_seed(seed);iw_roll_drop();CHECK(bt.item_dropped==expected);
        BattleRoutineState state={0};rng_seed(seed);btl_prep(&state);CHECK(bt.item_dropped==expected);
        close_all_windows();checks+=2;
    }
    printf("PASS: native sprite binding and OAM for extended Starman and repacked slots; %u actual normal/instant drop rolls\n",checks);
#endif
    return 0;
}
