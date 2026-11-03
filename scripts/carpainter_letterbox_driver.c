/* Private-pack fixture: pinned Carpainter continuation and existing close tail. */
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "core/mode_stack.h"
#include "game/display_text.h"
#include "game/display_text_internal.h"
#include "game/maternalbound.h"
#include "game/overworld.h"
#include "game/battle.h"
#include "game/window.h"
#include "entity/entity.h"
#include "data/assets.h"
#include "platform/pc_options.h"
#include "snes/ppu.h"
extern int eb_platform_main(int,char**);
#define CHECK(c) do{if(!(c)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#c);return 10;}}while(0)
int main(int argc,char **argv){
    if(argc!=3)return 2;
    char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
    char *boot[]={"fixture","--assets",argv[1],"--session-dir",argv[2],"--save",save,
        "--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
    if(eb_platform_main(12,boot))return 2;
    if(!maternalbound_enabled()){
        for(unsigned off=0;off<32;off++)CHECK(!maternalbound_carpainter_refusal_cleanup(off));
        puts("PASS Original: Redux cleanup inactive (32 controls)");return 0;
    }
    uint32_t yes=maternalbound_resolve_entry(0xC98148u);
    uint32_t after=maternalbound_resolve_entry(0xC9817Au);
    uint32_t tail=maternalbound_carpainter_refusal_cleanup(yes-0x100000u);
    CHECK(tail==after-9);
    CHECK(!maternalbound_carpainter_refusal_cleanup(yes-0x100000u-1));
    CHECK(!maternalbound_carpainter_refusal_cleanup(yes-0x100000u+1));
    CHECK(!maternalbound_carpainter_refusal_cleanup(after-0x100000u));
    ert.disable_actionscript=1;entities.first_entity=-1;bt.battle_mode_flag=0;
    memset(&g_mode_stack,0,sizeof(g_mode_stack));
    for(unsigned hidden=0;hidden<2;hidden++)for(unsigned choice=0;choice<2;choice++){
        pc_options.disable_cinematic_letterbox=hidden;
        maternalbound_letterbox_start(12);maternalbound_effects_tick();
        ModeState parent={0};CHECK(dt_make_child_init(&parent,choice?tail:yes-1));
        unsigned delays=0,frames=0;
        for(unsigned limit=0;limit<8;limit++){
            StepResult r=mode_step_display_text(&parent);
            if(r.kind==STEP_POP)break;
            CHECK(r.kind==STEP_PUSH&&r.push_mode==GAME_MODE_TEXT_DELAY&&r.push_init);
            ModeState child=*r.push_init;
            CHECK(child.text_delay.remaining==(delays==0?145:13));
            for(unsigned t=0;t<180;t++){
                maternalbound_effects_tick();r=mode_step_text_delay(&child);
                if(r.kind==STEP_POP)break;
                CHECK(r.kind==STEP_CONTINUE);frames++;
                if(t==6){ModeState saved=child;memset(&child,0,sizeof(child));child=saved;}
            }
            CHECK(r.kind==STEP_POP);delays++;
        }
        CHECK(delays==2);CHECK(frames>=158);
        maternalbound_effects_tick();CHECK(!ow.redux_letterbox_active&&!ppu.tm_hdma_active);
        for(unsigned i=0;i<4;i++)maternalbound_effects_tick();
        CHECK(!ppu.tm_hdma_active);
    }
    /* A changed/newer cleanup suffix must not be redirected by this adapter. */
    const uint8_t *blob=ASSET_DATA(ASSET_DIALOGUE_DIALOGUE_BIN);
    size_t size=ASSET_SIZE(ASSET_DIALOGUE_DIALOGUE_BIN);uint8_t *copy=malloc(size);CHECK(copy);
    memcpy(copy,blob,size);copy[tail-0x100000u+4]=11;
    CHECK(maternalbound_bind_dialogue(copy,size));
    CHECK(!maternalbound_carpainter_refusal_cleanup(yes-0x100000u));
    CHECK(maternalbound_bind_dialogue(blob,size));free(copy);
    puts("PASS Redux: No and Yes share 145-frame wait and animated close; visible/hidden bars; scalar continuation round-trip; unrelated offsets and changed suffix controls");
    return 0;
}
