# SPDX-License-Identifier: GPL-3.0-or-later
"""Link actual complete candidate archives and call real title-producing APIs.

No game objects, instructions, source data, or title arguments are substituted.
Only a copied platform main symbol is renamed for the private driver. Raw
source glyph rendering is an encoding control, not a full original CPU oracle.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from check_jev_observer_parity import local_scratch

ROOT=Path(__file__).resolve().parents[1]
DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game/game_state.h"
#include "game/maternalbound.h"
#include "game/window.h"
#include "game/text.h"
#include "game/display_text.h"
#include "game/battle.h"
#include "data/assets.h"
#include "core/mode_stack.h"
#include "snes/ppu.h"
#include "include/constants.h"
extern int eb_platform_main(int,char**);
extern void show_character_inventory(uint16_t,uint16_t);
static void setup(unsigned who){
 window_system_init();init_used_bg2_tile_map();text_setup_bg3();text_load_window_gfx();vwf_init();
 memset(game_state.party_members,0,sizeof(game_state.party_members));game_state.party_count=1;game_state.player_controlled_party_count=1;game_state.party_members[0]=who;
 game_state.auto_fight_enable=0;
 for(unsigned c=0;c<4;c++){memset(party_characters[c].afflictions,0,sizeof(party_characters[c].afflictions));memset(party_characters[c].equipment,0,sizeof(party_characters[c].equipment));memset(party_characters[c].items,0,sizeof(party_characters[c].items));party_characters[c].items[0]=ITEM_COOKIE;party_characters[c].items[1]=ITEM_HAMBURGER;party_characters[c].level=99;party_characters[c].current_hp=party_characters[c].max_hp=100;party_characters[c].current_pp=party_characters[c].max_pp=100;}
}
static void observe(unsigned producer,unsigned who,const uint8_t*expected,unsigned count,WindowInfo*w){
 if(!w||!w->active||!w->title_slot){printf("MISSING [%u,%u]\n",producer,who);return;}
 unsigned loss=strlen(w->title)!=count;
 for(unsigned i=0;i<count;i++){unsigned b=(uint8_t)w->title[i];unsigned g=b>=128?b:ascii_to_eb_char((char)b);loss+=g!=expected[i];}
 unsigned tile=0x2E0+(w->title_slot-1)*16,base=VRAM_TEXT_LAYER_TILES*2+tile*16;uint8_t actual[256];memcpy(actual,ppu.vram+base,256);
 unsigned columns=vwf_render_to_fixed_tiles(expected,count,FONT_ID_TINY,tile),diff=0;for(unsigned i=0;i<256;i++)diff+=actual[i]!=ppu.vram[base+i];
 printf("PRODUCER [%u,%u,%u,%u,%u,%u,%u,%u,%u]\n",producer,who,count,w->id,loss,diff,w->title_tile_count,columns,w->menu_count);
}
static void named(unsigned producer,unsigned who,const uint8_t*name,unsigned length){
 setup(who);maternalbound_set_character_name(who-1,name,length);ModeState s={0};unsigned id=0;
 switch(producer){
 case 0:inventory_get_item_name(who,WINDOW_INVENTORY);id=WINDOW_INVENTORY;break;
 case 1:show_character_inventory(WINDOW_INVENTORY,who);id=WINDOW_INVENTORY;break;
 case 2:display_status_window(who);id=WINDOW_STATUS_MENU;break;
 case 3:s.equip_menu.phase=EQ_ENTER;mode_step_equip_menu(&s);id=WINDOW_EQUIP_MENU;break;
 case 4:display_character_psi_list(who);id=WINDOW_TEXT_STANDARD;break;
 case 5:s.battle_menu.phase=BM_ENTER;s.battle_menu.char_id=who;mode_step_battle_menu(&s);for(unsigned i=0;i<8;i++)if(win.windows[i].active&&win.windows[i].title_slot)id=win.windows[i].id;break;
 default:exit(5);
 }
 unsigned count=length<(unsigned)maternalbound_name_capacity()?length:maternalbound_name_capacity();observe(producer,who,name,count,get_window(id));
}
static unsigned read16(const uint8_t*p){return p[0]|p[1]<<8;}
static void asset_title(unsigned producer,unsigned slot){
 setup(1);ModeState s={0};const uint8_t*expected=NULL;unsigned max=0,id=0;
 if(producer==6){s.equip_menu.phase=EQ_SLOT_RESULT;s.equip_menu.result_ready=1;s.equip_menu.result=slot;s.equip_menu.equip_char=1;mode_step_equip_menu(&s);expected=ASSET_DATA(ASSET_DATA_STATUS_EQUIP_WINDOW_TEXT_8_13_BIN)+60+(slot-1)*8;max=8;id=WINDOW_EQUIP_MENU_ITEMLIST;}
 if(producer==7){const uint8_t*table=ASSET_DATA(ASSET_DATA_PSI_TELEPORT_DEST_TABLE_BIN);size_t size=ASSET_SIZE(ASSET_DATA_PSI_TELEPORT_DEST_TABLE_BIN);for(size_t p=31;p+31<=size&&table[p];p+=31)event_flag_set(read16(table+p+25));s.teleport_menu.phase=TPM_ENTER;mode_step_teleport_menu(&s);expected=ASSET_DATA(ASSET_DATA_STATUS_EQUIP_WINDOW_TEXT_14_BIN);max=3;id=WINDOW_PHONE_MENU;}
 if(producer==8){game_state.escargo_express_items[0]=ITEM_COOKIE;s.escargo_menu.phase=EEM_ENTER;mode_step_escargo_menu(&s);expected=ASSET_DATA(ASSET_DATA_STATUS_EQUIP_WINDOW_TEXT_7_BIN);max=ASSET_SIZE(ASSET_DATA_STATUS_EQUIP_WINDOW_TEXT_7_BIN);if(max>=WINDOW_TITLE_SIZE)max=WINDOW_TITLE_SIZE-1;id=WINDOW_ESCARGO_EXPRESS_ITEM;}
 if(producer==9){const uint8_t*table=ASSET_DATA(ASSET_DATA_TELEPHONE_CONTACTS_TABLE_BIN);size_t size=ASSET_SIZE(ASSET_DATA_TELEPHONE_CONTACTS_TABLE_BIN);for(size_t p=31;p+31<=size&&table[p];p+=31)event_flag_set(read16(table+p+25));s.telephone_menu.phase=TPH_ENTER;mode_step_telephone_menu(&s);expected=ASSET_DATA(ASSET_DATA_PHONE_CALL_TEXT_BIN);max=5;id=WINDOW_EQUIP_MENU_ITEMLIST;}
 unsigned count=0;while(count<max&&expected[count])count++;observe(producer,slot,expected,count,get_window(id));
}
int main(int argc,char**argv){
 if(argc!=5)return 2;char save[4096];snprintf(save,sizeof(save),"%s/private.srm",argv[2]);char*boot[]={"private-title-producers","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};if(eb_platform_main(12,boot)||maternalbound_enabled()!=(atoi(argv[3])!=0))return 3;
 FILE*f=fopen(argv[4],"r");if(!f)return 4;unsigned code;
 while(fscanf(f,"%u",&code)==1){uint8_t single[2]={code,0};for(unsigned who=1;who<=4;who++)for(unsigned producer=0;producer<6;producer++)named(producer,who,single,1);}
 fclose(f);uint8_t mixed[7]={0x79,0xB0,0xC0,0x60,0xB8,0xB9,0};uint8_t ascii[7]={0x71,0x91,0x60,0x79,0xA3,0xA4,0};for(unsigned who=1;who<=4;who++)for(unsigned producer=0;producer<6;producer++){named(producer,who,maternalbound_enabled()?mixed:ascii,maternalbound_name_capacity());}
 for(unsigned slot=1;slot<=4;slot++)asset_title(6,slot);for(unsigned producer=7;producer<=9;producer++)asset_title(producer,0);
 return 0;
}
'''

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def link(source,build,runtime,out):
    out.mkdir();archive=build/'game_lib/libearthbound_game.a';before=sha(archive)
    commands=json.loads((build/'compile_commands.json').read_text(encoding='utf-8'));entry=next(r for r in commands if r['file'].endswith('/port/unix/main.c'))
    if any('"' in r['command'] or "'" in r['command'] for r in commands):raise ValueError('Review quoted compiler flags')
    argv=entry['command'].split();compiler=Path(argv[0]);driver=out/'driver.c';driver.write_text(DRIVER,encoding='utf-8');obj=out/'driver.c.obj';argv[argv.index('-c')+1]=str(driver);argv[argv.index('-o')+1]=str(obj)
    def run(args,name):
        proc=subprocess.run(list(map(str,args)),cwd=build,capture_output=True,timeout=45);(out/name).write_bytes(proc.stdout+proc.stderr)
        if proc.returncode:raise RuntimeError(name+': '+proc.stderr.decode(errors='replace'))
    run(argv,'driver-compile.log')
    ninja=(build/'build.ninja').read_text(encoding='utf-8');m=re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_Release (.*?)\n(.*?)(?=\n\n)',ninja,re.M|re.S);platform=m[1].split(' | ',1)[0].split();libs=re.search(r'^  LINK_LIBRARIES = (.*)$',m[2],re.M)[1].split();main=next(v for v in platform if v.replace('\\','/').endswith('/main.c.obj'));copied=out/'main-renamed.c.obj';shutil.copy2(build/main,copied);run([compiler.parent/'objcopy.exe','--redefine-sym','main=eb_platform_main',copied],'rename-main.log');platform=[str(copied) if v==main else str(build/v) for v in platform];exe=out/'private-title-producers.exe';run([compiler,'-O3','-DNDEBUG',obj,*platform,'-o',exe,*libs],'link.log');shutil.copy2(runtime/'SDL2.dll',out/'SDL2.dll')
    if before!=sha(archive):raise ValueError('Complete candidate archive changed')
    return exe,dict(archiveSha256=before,privateExeSha256=sha(exe),driverSha256=sha(driver),sourceObjectOverrides=False,mainRenameOnly=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('source','builds','runtime','original-assets','redux-assets','red','scratch','output'):ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args()
    for n,v in vars(a).items():setattr(a,n,v.resolve())
    a.scratch=local_scratch(a.scratch)
    if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch/report required')
    a.scratch.mkdir();red=json.loads(a.red.read_text(encoding='utf-8'));codes=[0x79,0x91,0x60]+red['sourceLiteralGridGlyphs'];results=[]
    for mode in ('player','observer'):
        build=a.builds/mode;exe,identity=link(a.source,build,a.runtime,a.scratch/(mode+'-link'))
        if sha(build/'earthbound.exe')!=sha(a.runtime/(mode+'.exe')):raise ValueError('Complete candidate executable mismatch')
        for profile,pack in (('original',a.original_assets),('redux',a.redux_assets)):
            directory=a.scratch/(mode+'-'+profile);directory.mkdir();inp=directory/'codes.txt';casecodes=codes if profile=='redux' else codes[:3];inp.write_text('\n'.join(map(str,casecodes))+'\n',encoding='ascii');proc=subprocess.run([str(exe),str(pack),str(directory),str(int(profile=='redux')),str(inp)],cwd=exe.parent,env=dict(os.environ,SDL_AUDIODRIVER='dummy',SDL_VIDEODRIVER='dummy'),capture_output=True,timeout=60);log=directory/'native.log';log.write_bytes(proc.stdout+proc.stderr)
            if proc.returncode:raise RuntimeError('Actual producer failed: '+str(log))
            rows=[];missing=[]
            for line in proc.stdout.decode(errors='replace').splitlines():
                if line.startswith('PRODUCER '):rows.append(json.loads(line[9:]))
                if line.startswith('MISSING '):missing.append(json.loads(line[8:]))
            expected=(len(casecodes)+1)*4*6+7
            if len(rows)+len(missing)!=expected:raise ValueError('Actual producer corpus incomplete')
            errors=[r for r in rows if r[4] or r[5] or r[6]!=r[7]]
            results.append(dict(build=mode,profile=profile,packSha256=sha(pack),linkedArchive=identity,completeExecutableSha256=sha(a.runtime/(mode+'.exe')),records=rows,missing=missing,errors=errors,nativeLogSha256=sha(log),Passed=not errors and not missing))
            print(json.dumps(dict(completed=mode+'-'+profile,cases=len(rows),errors=len(errors),missing=len(missing))),flush=True)
    report=dict(format='actual-complete-candidate-title-producers-dev18-v1',toolSha256=sha(Path(__file__)),results=results,allPassed=all(r['Passed'] for r in results),producerIds=['inventory_get_item_name','show_character_inventory','display_status_window','mode_step_equip_menu EQ_ENTER (actual private display_equipment_menu child)','display_character_psi_list','mode_step_battle_menu BM_ENTER','mode_step_equip_menu EQ_SLOT_RESULT, four actual packed category titles','mode_step_teleport_menu TPM_ENTER','mode_step_escargo_menu EEM_ENTER','mode_step_telephone_menu TPH_ENTER'],limits=['Actual complete player and observer archives are linked without source/object/instruction overrides. A copied platform main symbol is renamed for the private driver.', 'Legal name glyphs, source Cookie/Hamburger IDs, single-player party member, level99 and zero afflictions are prepared prerequisites. This is direct producer API coverage, not natural whole-story/battle reachability.', 'Asset title parents use packed source tables and source event flags to retain real selectable lists; no fabricated assets/title arguments are supplied.', 'Expected glyph identity follows raw source name/title bytes. Native raw tiny rendering is a same-renderer encoding control; independent source-font VRAM and fresh-process continuation are separate complete-executable tests.', 'No physical gameplay controller, story effects, targeting/equipping transactions, full pixel CPU renderer, every UI name label or new save format is claimed.'],rootOrOwnerInputsModified=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(allPassed=report['allPassed'],output=str(a.output),sha256=sha(a.output))))

if __name__=='__main__':main()
