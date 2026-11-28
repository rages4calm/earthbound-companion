/* Actual native config accessor, with private Original/Redux assets. */
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <string.h>
#include "game/map_loader.c"
extern int eb_platform_main(int,char**);
#define CHECK(c) do { if(!(c)){fprintf(stderr,"FAIL %d: %s\n",__LINE__,#c);return 10;} }while(0)
static int visible(const NpcConfig *c,int belch) {
    return c->appearance_style==0 || (((c->appearance_style-2)^((c->event_flag==71)?belch:0))&1);
}
int main(int argc,char **argv) {
    if(argc!=3)return 2;
    char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
    char *boot[]={"fixture","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
    if(eb_platform_main(12,boot))return 2;
    CHECK(map_loader_init());
    for(unsigned id=0;id<npc_config_table_count;id++) {
        const NpcConfig raw=npc_config_table[id];const NpcConfig *actual=get_npc_config(id);
        NpcConfig expected=raw;
        if(id==526&&raw.event_flag==71&&raw.appearance_style==1)expected.appearance_style=0;
        if(id==563&&raw.event_flag==610&&raw.appearance_style==2)expected.event_flag=71;
        CHECK(!memcmp(actual,&expected,sizeof(expected)));
        CHECK(!memcmp(&raw,&npc_config_table[id],sizeof(raw)));
    }
    CHECK(visible(get_npc_config(526),0)&&visible(get_npc_config(526),1));
    CHECK(!visible(get_npc_config(563),0)&&visible(get_npc_config(563),1));
    CHECK(get_npc_config_event_flag(563)==71);
    CHECK(get_npc_config(65535)==NULL);
    /* Modified records outside the two known bad retail gates stay exact. */
    NpcConfig custom[564]={0};custom[526].event_flag=42;custom[526].appearance_style=2;
    custom[563].event_flag=610;custom[563].appearance_style=1;
    npc_config_table=custom;npc_config_table_count=564;
    CHECK(get_npc_config(526)==&custom[526]);CHECK(get_npc_config(563)==&custom[563]);
    puts("PASS: every NPC record checked; both Belch states; read-only assets; custom gates preserved");
    return 0;
}
