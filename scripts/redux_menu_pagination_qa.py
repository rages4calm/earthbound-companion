# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare production menu geometry with actual local CPU layout evidence.

An explicit private-corrected-objects run recompiles the leased window source
and unchanged CC source into a private copy only. Local inputs/saves stay intact.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

from check_jev_observer_parity import local_scratch
import redux_two_string_menu_qa as linker


DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "game/game_state.h"
#include "game/maternalbound.h"
#include "game/window.h"
#include "game/text.h"
#include "game/display_text.h"
#include "game/display_text_internal.h"
#include "include/pad.h"
extern int eb_platform_main(int,char**);
static uint16_t pad;
extern uint16_t __real_platform_input_get_pad_new(void);
uint16_t __wrap_platform_input_get_pad_new(void){return pad;}
extern void __real_play_sfx(uint16_t);
void __wrap_play_sfx(uint16_t id){__real_play_sfx(id);}
extern uint8_t __real_script_read_byte(ScriptReader*);
extern uint32_t __real_script_read_dword(ScriptReader*);
uint8_t __wrap_script_read_byte(ScriptReader*r){return __real_script_read_byte(r);}
uint32_t __wrap_script_read_dword(ScriptReader*r){return __real_script_read_dword(r);}
static WindowInfo*setup(unsigned id,unsigned count){
 window_system_init();init_used_bg2_tile_map();text_setup_bg3();text_load_window_gfx();vwf_init();clear_vwf_indent_new_line();
 memset(&dt,0,sizeof(dt));dt.instant_printing=1;dt.enable_word_wrap=1;create_window(id);set_window_focus(id);WindowInfo*w=get_window(id);if(!w)exit(10);
 for(unsigned i=0;i<count;i++){add_menu_item("A",i+1,0,0);w->menu_items[i].type=1;}return w;
}
static void record(unsigned index,unsigned method,WindowInfo*w){
 printf("LAYOUT [%u,%u,%u,%u,%u,[",index,method,w->menu_count,w->menu_page_number,w->selected_option);
 for(unsigned i=0;i<w->menu_count;i++){if(i)printf(",");MenuItem*m=&w->menu_items[i];printf("[%u,%u,%u,%u]",m->text_x,m->text_y,m->page,m->type);}puts("]]");
}
int main(int argc,char**argv){
 if(argc!=5)return 2;char save[4096];snprintf(save,sizeof(save),"%s/private.srm",argv[2]);
 char*boot[]={"pagination-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
 if(eb_platform_main(12,boot)||maternalbound_enabled()!=(atoi(argv[3])!=0))return 3;
 FILE*f=fopen(argv[4],"r");if(!f)return 4;unsigned index=0,h,wid,cols,count,ty;
 char progresspath[4096];snprintf(progresspath,sizeof(progresspath),"%s/progress.txt",argv[2]);FILE*progress=fopen(progresspath,"w");if(!progress)return 6;
 while(fscanf(f,"%u %u %u %u %u",&h,&wid,&cols,&count,&ty)==5){
  index++;for(unsigned method=0;method<3;method++){
   WindowInfo*w=setup(2,count);w->height=h;w->width=wid;w->content_tilemap_size=(h-2)*(wid-2);if(w->content_tilemap_size>WINDOW_TILEMAP_MAX)return 5;w->text_y=ty;
   fprintf(progress,"layout %u %u %u %u %u\n",index,method,h,cols,count);fflush(progress);
   if(method==0)open_window_and_print_menu(cols,0);else layout_and_print_menu_at_selection(cols,0,method==1?count-1:65535);
   record(index,method,w);
  }
 }fclose(f);
 for(unsigned id=0;id<=WINDOW_FILE_SELECT_TWEAKS;id++){
  fprintf(progress,"window %u\n",id);fflush(progress);WindowInfo*w=setup(id,1);unsigned h=w->height,wid=w->width;open_window_and_print_menu(1,0);
  printf("WINDOW [%u,%u,%u,%u,%u,%u]\n",id,h,wid,w->menu_count,w->menu_items[0].text_y,w->menu_items[0].page);
 }
 const unsigned caps[]={24,64,78,79};
 for(unsigned k=0;k<4;k++)for(unsigned method=0;method<2;method++){
  fprintf(progress,"capacity %u %u\n",k,method);fflush(progress);unsigned count=caps[k];WindowInfo*w=setup(2,count);w->menu_items[count-1].userdata=0x1a6;
  if(method)layout_and_print_menu_at_selection(2,0,count-1);else open_window_and_print_menu(2,0);
  unsigned invalid=0;for(unsigned i=0;i<count;i++)invalid+=w->menu_items[i].text_y>=7||!w->menu_items[i].page;
  printf("CAPACITY [%u,%u,%u,%u,%u,%u,%u]\n",count,method,w->menu_count,invalid,w->menu_items[count-1].userdata,w->menu_items[count].text_y,w->menu_page_number);
 }
 for(unsigned height=0;height<=6;height++)for(unsigned method=0;method<2;method++){
  fprintf(progress,"guard %u %u\n",height,method);fflush(progress);WindowInfo*w=setup(2,8);w->height=height;w->menu_items[0].text_y=77;w->menu_items[0].page=88;
  if(method)layout_and_print_menu_at_selection(2,0,0);else open_window_and_print_menu(2,0);
  printf("GUARD [%u,%u,%u,%u,%u]\n",height,method,w->menu_count,w->menu_items[0].text_y,w->menu_items[0].page);
 }
 return 0;
}
'''


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native-source','build','runtime','original-assets','redux-assets','cpu','scratch','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--private-corrected-objects',action='store_true')
    p.add_argument('--skip-short-guards',action='store_true',help='Skip invalid short-window controls on the old unguarded baseline; not ordinary gameplay coverage.')
    a=p.parse_args()
    for key,value in vars(a).items():
        if isinstance(value,Path):setattr(a,key,value.resolve())
    a.scratch=local_scratch(a.scratch)
    if a.scratch.exists()or a.output.exists():raise ValueError('Fresh scratch/report required')
    cpu=json.loads(a.cpu.read_text(encoding='utf-8'))
    if not cpu['completed']or len(cpu['profiles'])!=2:raise ValueError('Completed actual CPU reference required')
    a.scratch.mkdir(parents=True);folder=a.scratch/'driver';folder.mkdir()
    linker.DRIVER=DRIVER.replace('height<=6','height<=0')if a.skip_short_guards else DRIVER
    if a.skip_short_guards:
        linker.DRIVER=linker.DRIVER.replace('for(unsigned height=0;height<=0;height++)','for(unsigned height=0;height<0;height++)')
    linkargs=a
    if a.private_corrected_objects:
        # Keep another worker's live CC source out of this leased-window proof.
        # The reused linker compiles two files; its CC input is byte-identical
        # to the frozen archive source, only window.c is the proposed change.
        sourcecopy=a.scratch/'leased-source';(sourcecopy/'src/game').mkdir(parents=True)
        snapshot=a.build.parent.parent/a.build.parent.name.replace('-build','-source')
        shutil.copy2(a.native_source/'src/game/window.c',sourcecopy/'src/game/window.c')
        shutil.copy2(snapshot/'src/game/display_text_cc.c',sourcecopy/'src/game/display_text_cc.c')
        linkargs=SimpleNamespace(**vars(a));linkargs.native_source=sourcecopy
    exe,link=linker.private_driver(linkargs,folder)
    link['onlyProposedFunctionalChange']='src/game/window.c'if a.private_corrected_objects else None
    rows=[]
    for reference,assets in zip(cpu['profiles'],(a.original_assets,a.redux_assets)):
        mode=reference['profile'];session=a.scratch/mode;session.mkdir()
        casefile=session/'cases.txt';casefile.write_text('\n'.join(' '.join(str(c[n])for n in ('height','width','columns','count','textY'))for c in reference['cases'])+'\n',encoding='utf-8')
        env=dict(os.environ,SDL_AUDIODRIVER='dummy',SDL_VIDEODRIVER='dummy')
        proc=subprocess.run([str(exe),str(assets),str(session),str(int(mode=='redux')),str(casefile)],cwd=folder,env=env,capture_output=True,timeout=90)
        log=session/'native.log';log.write_bytes(proc.stdout+proc.stderr)
        if proc.returncode:raise ValueError(mode+' native driver failed; inspect private log')
        records={kind:[]for kind in ('LAYOUT','WINDOW','CAPACITY','GUARD','BUTTON')}
        for line in proc.stdout.decode(errors='replace').splitlines():
            kind,_,payload=line.partition(' ')
            if kind in records:records[kind].append(json.loads(payload))
        if len(records['LAYOUT'])!=3*reference['count']or len(records['CAPACITY'])!=8 or len(records['GUARD'])!=(0 if a.skip_short_guards else 14) or records['BUTTON']:
            raise ValueError('Incomplete native corpus')
        differences=[]
        for record in records['LAYOUT']:
            index,method,count,page,selected,geometry=record;expected=reference['results'][index-1]
            wantpage=expected[2][reference['cases'][index-1]['count']-1][2]if method==1 else 1
            if count!=expected[1]or geometry!=expected[2]or page!=wantpage:
                differences.append({'index':index,'method':method,'expected':expected,'actual':record,'expectedPage':wantpage})
        capacityerrors=[r for r in records['CAPACITY']if r[2]!=r[0]+1 or r[3]or r[4]!=0x1a6 or r[5]!=6]
        guarderrors=[r for r in records['GUARD']if r[2:]!=[8,77,88]]
        buttonerrors=[r for r in records['BUTTON']if r[2]!=14 or r[4]!=0x1a6 or r[5]!=2 or r[6]!=2]
        rows.append({'profile':mode,'assetsSha256':sha(assets),'actualCpuLayoutCases':reference['count'],
                     'nativeLayoutCases':len(records['LAYOUT']),'geometryDifferences':differences,
                     'capacityErrors':capacityerrors,'guardErrors':guarderrors,'buttonErrors':buttonerrors,
                     'records':records,'nativeLogSha256':sha(log)})
    report={'format':'native-menu-pagination-behavior-v1','toolSha256':sha(Path(__file__)),
            'linkToolSha256':sha(Path(linker.__file__)),'actualCpuReport':{'path':str(a.cpu),'sha256':sha(a.cpu)},
            'productionLink':link,'runtimeSha256':{name:sha(a.runtime/name)for name in ('player.exe','observer.exe')},
            'currentWindowSourceSha256':sha(a.native_source/'src/game/window.c'),'profiles':rows,
            'allPassed':all(not r['geometryDifferences']and not r['capacityErrors']and not r['guardErrors']and not r['buttonErrors']for r in rows),
            'ownerSavesOrInputPacksModified':False,'invalidShortGuardsExcluded':a.skip_short_guards,
            'standaloneButtonPhaseExcluded':'Initial standalone movement-phase fixture lacked entity/frame prerequisites and timed out; it is not credited as passing. Actual parent/button proof is recorded separately by barter QA.',
            'limits':['Own prepared menu records and geometry only; actual button phases are separately proved by real Monkey-parent QA, not this standalone driver.',
                      'Actual original/pinned CPU layout records independently reference546 native geometry cases per profile; selected-page behavior is source-selected item page.',
                      'All configured native window IDs tested with one item; arbitrary counts in every window and invalid columns are not exhausted.',
                      'Native24/64/78/79 record pagination capacity controls preserve16bit virtual userdata;80items has no remaining overflow slot and is outside supported pooled selector bound78.',
                      'Height0..6 oversized fixture guards characterize native safety, not source-loop parity for invalid short source windows.',
                      'Complete real Monkey-parent warm/cold actual-button delivery remains separately owned by barter QA.']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([(r['profile'],len(r['geometryDifferences']),len(r['buttonErrors']))for r in rows]))


if __name__=='__main__':main()
