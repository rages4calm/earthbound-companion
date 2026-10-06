# SPDX-License-Identifier: GPL-3.0-or-later
"""Source-backed battle PSI category checks, with read-only copied F6 input."""
import argparse, json, os, shutil, subprocess
from pathlib import Path
import battle_action_catalog_qa as helper

def driver(original):
    prefix=helper.DRIVER.split('static unsigned pump(void)',1)[0]
    return prefix+r'''
#include "core/state_dump.h"
#include "game/audio.h"
#include "data/event_script_data.h"
#include <stddef.h>
static void observe(const char*stage,unsigned character){
 WindowInfo*w=get_window(WINDOW_PSI_CATEGORY);
 printf("QA {\"stage\":\"%s\",\"character\":%u,\"level\":%u,\"depth\":%u,\"available\":[",stage,character,party_characters[character-1].level,g_mode_stack.depth);
 for(unsigned i=1;i<=3;i++)printf("%s%u",i>1?",":"",check_psi_category_available(i,character));
 printf("],\"window\":%u,\"page\":%u,\"current\":%u,\"items\":[",w!=NULL,w?w->menu_page_number:0,w?w->current_option:0);
 if(w)for(unsigned i=0;i<w->menu_count;i++){MenuItem*m=&w->menu_items[i];printf("%s{\"label\":\"%s\",\"id\":%u,\"y\":%u,\"page\":%u,\"type\":%u}",i?",":"",m->label,m->userdata,m->text_y,m->page,m->type);}
 printf("]}\n");fflush(stdout);
}
int main(int argc,char**argv){
 if(argc!=4)return 2;char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 char*boot[]={"psi-category-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--redux-battle-fixture","0"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot)!=0)return 3;
 platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 7;game_set_fast_forward(true);audio_init();load_title_screen_script_data();
 current_save_slot=1;
 printf("QA_LAYOUT {\"windows\":%zu,\"windowSize\":%zu,\"active\":%zu,\"id\":%zu,\"count\":%zu,\"current\":%zu,\"menu\":%zu,\"menuSize\":%zu,\"userdata\":%zu,\"itemPage\":%zu}\n",offsetof(WindowSystemState,windows),sizeof(WindowInfo),offsetof(WindowInfo,active),offsetof(WindowInfo,id),offsetof(WindowInfo,menu_count),offsetof(WindowInfo,current_option),offsetof(WindowInfo,menu_items),sizeof(MenuItem),offsetof(MenuItem,userdata),offsetof(MenuItem,page));
 if(atoi(argv[3])){
  if(!state_dump_load_slots())return 4;
  printf("QA_PARTY {\"sum\":%u,\"levels\":[%u,%u,%u,%u]}\n",sum_alive_party_levels(),party_characters[0].level,party_characters[1].level,party_characters[2].level,party_characters[3].level);
  observe("copied-save-loaded",2);text_menus_resume_repaint();observe("copied-save-repainted",2);
  /* Separate prepared enemy consumer: does not simulate a roaming AI script. */
  const uint8_t*groups=ASSET_DATA(ASSET_DATA_BTL_ENTRY_PTR_TABLE_BIN);unsigned group=0;
  while(group<ASSET_SIZE(ASSET_DATA_BTL_ENTRY_PTR_TABLE_BIN)/8 && (groups[group*8+4]||groups[group*8+5]))group++;
  if(group==ASSET_SIZE(ASSET_DATA_BTL_ENTRY_PTR_TABLE_BIN)/8)return 8;
  ert.current_entity_slot=0;entities.npc_ids[0]=group|0x8000;entities.enemy_ids[0]=98;
  unsigned fleeing=0;for(unsigned value=0;value<256;value++){entities.weak_enemy_value[0]=value;fleeing+=check_enemy_should_flee()!=0;}
  printf("QA_FLEE {\"enemy\":98,\"level\":%u,\"partySum\":%u,\"spawnValueCount\":256,\"fleeCount\":%u,\"noFleeCount\":%u,\"runFlagOverride\":false}\n",enemy_config_table[98].level,sum_alive_party_levels(),fleeing,256-fleeing);
 }else{
  unsigned levels[]={1,10,30,60,99},members[]={1,2,4};
  for(unsigned p=0;p<3;p++)for(unsigned l=0;l<5;l++){
   unsigned ch=members[p];party_characters[ch-1].level=levels[l];game_state.party_members[p]=ch;win.battle_menu_current_character_id=p;
   window_system_init();init_used_bg2_tile_map();text_setup_bg3();text_upload_font_tiles();text_load_window_gfx();text_load_flavour_palette(0);
   memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_NONE;
   ModeState m={0};m.battle_psi_menu.char_id=ch;m.battle_psi_menu.phase=BP_OPEN;
   StepResult r=mode_step_battle_psi_menu(&m);if(r.kind!=STEP_PUSH||r.push_mode!=GAME_MODE_SELECTION_MENU)return 5;
   observe("fresh-menu",ch);
  }
 }
 audio_shutdown();return 0;
}
'''.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"' if original else '"--redux-battle-fixture","0"')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('build','native-source','assets','runtime','scratch','output','project'): ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--owner',type=Path);ap.add_argument('--original',action='store_true');ap.add_argument('--baseline',action='store_true')
    a=ap.parse_args();a.scratch.mkdir(parents=True,exist_ok=False)
    helper.DRIVER=driver(a.original);exe,identity=helper.private_build(a)
    session=a.scratch/'session';session.mkdir()
    if a.owner:shutil.copytree(a.owner/'saves',session/'saves')
    result=subprocess.run([str(exe),str(a.assets.resolve()),str(session.resolve()),str(int(bool(a.owner)))],cwd=session,
        env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=60)
    log=a.scratch/'native.log';log.write_bytes(result.stdout+result.stderr)
    rows=[json.loads(s[3:]) for s in result.stdout.decode(errors='replace').splitlines() if s.startswith('QA ')]
    for row in rows:
        row['passed']=row['items']==[dict(label=name,id=i+1,y=i,page=1,type=2) for i,name in enumerate(('Offense','Recover','Assist'))] and row['page']==1
    report=dict(privateBuild=identity,originalPack=a.original,assetsSha256=helper.digest(a.assets),nativeExit=result.returncode,
        copiedOwnerInput=bool(a.owner),cases=rows,allPassed=result.returncode==0 and bool(rows) and all(r['passed'] for r in rows if r['stage']!='copied-save-loaded'),
        sourceReference='asm/battle/battle_psi_menu.asm: category loop CMP #$0003 and ADD_MENU_ITEM_NO_POSITION',
        limits=['Category layout and availability in prepared levels or an unchanged copied F6 state. Does not certify full battles or story progression.'],fullPlaythroughVerified=False)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(rows=len(rows),allPassed=report['allPassed'],exit=result.returncode,first=rows[:2])))
    if not a.baseline and not report['allPassed']:raise SystemExit(1)
if __name__=='__main__':main()
