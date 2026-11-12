import importlib.util, subprocess, os, json, argparse
from pathlib import Path
a=argparse.ArgumentParser(description="Focused native checks for issues 12-14; private packs, isolated sessions.")
for option in ('native-source','build','original-assets','redux-assets','output'):a.add_argument('--'+option,type=Path,required=True)
a.add_argument('--before-root',type=Path,help='Optional pre-fix source tree for negative controls')
a=a.parse_args();R=Path(__file__).resolve().parents[1];N=a.native_source.resolve();B=a.build.resolve();W=a.output.resolve()
if W.exists():raise ValueError('Use a fresh output directory')
W.mkdir(parents=True)
T=a.before_root.resolve() if a.before_root else N
spec=importlib.util.spec_from_file_location('f',R/'scripts/check_native_render_lifecycle.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f);f.N=N;f.B=B;f.W=W
pre=r'''
#include <stdio.h>
#include <string.h>
#include "core/mode_stack.h"
#include "game/game_state.h"
#include "game/window.h"
#include "game/text.h"
#include "game/display_text.h"
#include "game/battle.h"
#include "game/battle_bg.h"
#include "game/maternalbound.h"
#include "entity/entity.h"
#include "entity/sprite.h"
#include "intro/file_select.h"
#include "include/binary.h"
#include "snes/ppu.h"
extern int eb_platform_main(int,char**);
#define CHECK(x) do {if(!(x)){fprintf(stderr,"FAIL %d: %s\n",__LINE__,#x);return 10;}}while(0)
int boot(char**argv){char*args[]={"f","--assets",argv[1],"--session-dir",argv[2],"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};return eb_platform_main(10,args);}
'''
sources={
'psi': '\n#include "'+(T/'src/game/text.c').as_posix()+'"\n'+r'''
int main(int argc,char**argv){CHECK(!boot(argv));text_system_init();window_system_init();game_state.party_count=1;game_state.party_members[0]=1;party_characters[0].level=99;overworld_selected_psi_user=1;CHECK(ensure_battle_psi_table());unsigned count=0;
for(unsigned id=1;id<PSI_MAX_ENTRIES && battle_psi_table[id].name;id++){if(!(battle_psi_table[id].usability & PSI_USE_OVERWORLD))continue;create_window(WINDOW_TEXT_STANDARD);display_character_psi_list(1);set_focus_text_cursor(0,(battle_psi_table[id].menu_y+1)%3);display_psi_ability_details(0,id);WindowInfo*w=get_window(WINDOW_TEXT_STANDARD);CHECK(w && w->text_y==battle_psi_table[id].menu_y);close_all_windows();count++;}printf("PASS PSI: %u ability rows restored independently of target cursor\n",count);return 0;}
''',
'sprite':r'''
int main(int argc,char**argv){CHECK(!boot(argv));load_sprite_data();unsigned count=0;for(unsigned g=0;g<sprite_grouping_ptr_count;g++){uint32_t off;load_sprite_group_properties(g,&off);unsigned length=(g==476?16:8);for(unsigned i=0;i<length;i++){unsigned p=off+9+2*i;if(p+2>sprite_grouping_data_size)break;unsigned raw=read_u16_le(sprite_grouping_data_buf+p),got=sprite_frame_pointer(p);if(maternalbound_enabled()&&g==476&&(i==6||i==7)){CHECK(got==(read_u16_le(sprite_grouping_data_buf+p-8)^1));CHECK(sprite_frame_pointer(off+21)!=sprite_frame_pointer(off+23));}else CHECK(got==raw);count++;}}printf("PASS sprite: %u pointers; Tony west two mirrored east frames; other descriptors unchanged\n",count);return 0;}
''',
'naming':r'''
int main(int argc,char**argv){CHECK(!boot(argv));text_system_init();text_setup_bg3();window_system_init();entity_system_init();for(int target=NAME_TARGET_M2_PLAYER;target<=NAME_TARGET_EB_PLAYER;target++){close_all_windows();create_window(WINDOW_NAMING_PROMPT);ModeState s;text_input_prepare(&s,target,target==NAME_TARGET_EB_PLAYER?24:12,-1,WINDOW_NAMING_PROMPT,1,NULL);battle_bg_load(BATTLEBG_GAS_STATION);loaded_bg_data_layer1.horizontal_velocity=256;loaded_bg_data_layer1.scrolling_duration_left=1000;int old=loaded_bg_data_layer1.horizontal_position;for(int t=0;t<90;t++){CHECK(mode_step_text_input(&s).kind==STEP_CONTINUE);CHECK(loaded_bg_data_layer1.horizontal_position==old);uint16_t*map=(uint16_t*)win.bg2_buffer;for(int i=0;i<32*28;i++){unsigned tile=map[i]&0x3ff;CHECK(tile<0x380);}}}puts("PASS naming: both in-game targets, 90 frames each; stale background held; tile references below tilemap");return 0;}
'''}
receipts=[]
for name,src in sources.items():
 if a.before_root and name=='sprite':src='\n#include "'+(T/'src/entity/sprite.c').as_posix()+'"\nuint16_t sprite_frame_pointer(uint32_t o){return read_u16_le(sprite_grouping_data_buf+o); }\n'+src
 if a.before_root and name=='naming':src='\n#include "'+(T/'src/intro/file_select.c').as_posix()+'"\n'+src
 exe=f.build('test-'+name,pre+src)
 for mode,pak in [('original',a.original_assets.resolve()),('redux',a.redux_assets.resolve())]:
  session=W/(name+'-'+mode);session.mkdir(exist_ok=True);r=subprocess.run([str(exe),str(pak),str(session)],capture_output=True,env=dict(os.environ,SDL_AUDIODRIVER='dummy',SDL_VIDEODRIVER='dummy'),timeout=90);out=r.stdout.decode(errors='replace');err=r.stderr.decode(errors='replace');(W/(name+'-'+mode+'.log')).write_text(out+err,encoding='utf-8');print(name,mode,r.returncode,out[-200:]);receipts.append(dict(test=name,mode=mode,exitCode=r.returncode,output=out[-400:]));
(W/'checks.json').write_text(json.dumps(receipts,indent=2),encoding='utf-8')

raise SystemExit(0 if all(x["exitCode"]==0 for x in receipts) else 1)
