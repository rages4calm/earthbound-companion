# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded real name-producer/window/highlight controls on immutable archives."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from types import SimpleNamespace
import party_name_parents_qa_dev19 as parents
import redux_naming_qa as naming
from build_maternalbound_pack import read_pack
ROOT=Path(__file__).resolve().parents[1]
C=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "core/mode_stack.h"
#include "core/memory.h"
#include "game/battle.h"
#include "game/game_state.h"
#include "game/display_text.h"
#include "game/display_text_internal.h"
#include "game/window.h"
#include "game/text.h"
#include "game/maternalbound.h"
#include "game/overworld.h"
#include "entity/entity.h"
#include "snes/ppu.h"
#include "platform/platform.h"
extern int eb_platform_main(int,char**);
static void fresh(unsigned count){
 game_state.party_count=game_state.player_controlled_party_count=count;game_state.current_party_members=(1u<<count)-1;
 memset(game_state.party_order,0,6);memset(game_state.party_members,0,6);for(unsigned c=0;c<count;c++)game_state.party_order[c]=game_state.party_members[c]=c+1;
 update_party();initialize_overworld_state();window_system_init();init_used_bg2_tile_map();text_setup_bg3();text_upload_font_tiles();text_load_window_gfx();text_load_flavour_palette(0);create_window(WINDOW_TEXT_STANDARD);
 memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_NONE;
}
static void flush(void){for(unsigned i=0;i<3;i++)host_process_frame();}
static void rows(const char*test,const char*stage,WindowInfo*w){
 printf("CONTROL {\"test\":\"%s\",\"stage\":\"%s\",\"window\":%u,\"width\":%u,\"height\":%u,\"padding\":%u,\"rows\":[",test,stage,w->id,w->width,w->height,character_padding);
 unsigned width=w->width-2;
 for(unsigned i=0;i<w->menu_count;i++){
  MenuItem*t=&w->menu_items[i];unsigned tx=t->text_x+1,ty=t->text_y*2,end=width;if(i+1<w->menu_count&&w->menu_items[i+1].text_y==t->text_y)end=w->menu_items[i+1].text_x;
  printf("%s{\"id\":%u,\"x\":%u,\"label\":[",i?",":"",t->userdata,t->text_x);for(unsigned j=0;j<sizeof(t->label)&&t->label[j];j++)printf("%s%u",j?",":"",(uint8_t)t->label[j]);
  printf("],\"columns\":[");for(unsigned x=tx;x<end;x++){printf("%s\"",x==tx?"":",");for(unsigned y=0;y<2;y++){unsigned tile=w->content_tilemap[(ty+y)*width+x]&0x3ff;for(unsigned b=0;b<16;b++)printf("%02x",ppu.vram[0xc000+tile*16+b]);}printf("\"");}
  printf("],\"attributes\":[");for(unsigned x=tx;x<end;x++){printf("%s[",x==tx?"":",");for(unsigned y=0;y<2;y++)printf("%s%u",y?",":"",(w->content_tilemap[(ty+y)*width+x]>>10)&7);printf("]");}printf("]}");
 }printf("]}\n");fflush(stdout);
}
int main(int argc,char**argv){
 if(argc!=4)return 2;char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);char*boot[]={"party-name-controls","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};if(eb_platform_main(12,boot))return 3;
 platform_max_frames=0;platform_input_shutdown();platform_input_init();game_set_fast_forward(true);
 FILE*f=fopen(argv[3],"r");if(!f)return 4;for(unsigned c=0;c<4;c++){unsigned n,g;uint8_t name[7]={0};if(fscanf(f,"%u",&n)!=1||n>(unsigned)maternalbound_name_capacity())return 5;for(unsigned i=0;i<n;i++){if(fscanf(f,"%u",&g)!=1)return 6;name[i]=g;}maternalbound_set_character_name(c,name,n);}fclose(f);
 for(unsigned count=1;count<=4;count++)for(unsigned producer=0;producer<2;producer++){
  fresh(count);uint16_t id;ModeState init={0};if(producer==0)id=char_select_overworld_prepare(NULL);else party_selector_overworld_prepare(1,&init,&id);flush();WindowInfo*w=get_window(id);if(!w)return 7;char label[60];snprintf(label,sizeof(label),"producer%u-party%u",producer,count);rows(label,"rendered",w);
  for(unsigned i=0;i<w->menu_count;i++){highlight_menu_item(w,i,6,true);flush();rows(label,"highlight",w);highlight_menu_item(w,i,0,false);}flush();rows(label,"cleared",w);
 }
 /* The existing hybrid title producer/renderer remains distinct. */
 fresh(1);char title[7];eb_to_title_buf(maternalbound_character_name(0),maternalbound_name_capacity(),title,sizeof(title));set_window_title(WINDOW_TEXT_STANDARD,title,-1);flush();WindowInfo*w=get_window(WINDOW_TEXT_STANDARD);printf("TITLE {\"bytes\":[");for(unsigned i=0;w->title[i];i++)printf("%s%u",i?",":"",(uint8_t)w->title[i]);printf("],\"vram\":\"");for(unsigned i=0;i<512;i++)printf("%02x",ppu.vram[0xc000+(0x2e0+(w->title_slot-1)*16)*16+i]);printf("\"}\n");
 /* Synthetic high bytes stay generic ASCII on unrelated windows/userdata. */
 unsigned windows[]={WINDOW_TEXT_STANDARD,WINDOW_INVENTORY,WINDOW_FILE_SELECT_MAIN,41,42,43,51};unsigned ids[]={1,1,0,0,5,6,8};
 for(unsigned i=0;i<7;i++){fresh(1);create_window(windows[i]);char label[]={ 'A',(char)0xb0,'Z',0};add_menu_item(label,ids[i],0,0);print_menu_items();flush();char test[50];snprintf(test,sizeof(test),"generic-%u-id%u",windows[i],ids[i]);rows(test,"rendered",get_window(windows[i]));}
 fresh(1);game_state.party_members[0]=PARTY_MEMBER_KING;memset(game_state.pet_name,0,sizeof(game_state.pet_name));memcpy(game_state.pet_name,maternalbound_character_name(0),5);uint16_t pet_window;ModeState pet_init={0};party_selector_overworld_prepare(1,&pet_init,&pet_window);flush();rows("source-pet-branch","rendered",get_window(pet_window));highlight_menu_item(get_window(pet_window),0,6,true);rows("source-pet-branch","highlight",get_window(pet_window));
 printf("HPPP {\"namePlane1\":\"");for(unsigned c=0;c<4;c++)for(unsigned tile=0;tile<4;tile++)for(unsigned y=0;y<16;y++)printf("%02x",ert.buffer[0x2a00+c*64+tile*16+(y<8?y*2:(y-8)*2+256)+1]);printf("\"}\n");
 printf("STRUCTURES {\"MenuItem\":%zu,\"WindowInfo\":%zu,\"WindowSystemState\":%zu}\n",sizeof(MenuItem),sizeof(WindowInfo),sizeof(WindowSystemState));return 0;
}
'''

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in ('source','builds','runtime','original-assets','redux-assets','scratch','output'):ap.add_argument('--'+n,type=Path,required=True)
 ap.add_argument('--pilot',action='store_true');a=ap.parse_args()
 for n,v in vars(a).items():
  if isinstance(v,Path):setattr(a,n,v.resolve())
 if a.scratch.exists()or a.output.exists():raise ValueError('Fresh paths required')
 a.scratch.mkdir(parents=True);results=[]
 for mode in (('player',)if a.pilot else('player','observer')):
  link=a.scratch/(mode+'-link');link.mkdir();parents.gear.base.helper.DRIVER=C;exe,proof=parents.gear.base.helper.private_build(SimpleNamespace(build=a.builds/mode,scratch=link,native_source=a.source,runtime=a.runtime))
  for profile,pack in [('original',a.original_assets),('redux',a.redux_assets)]:
   if a.pilot and profile=='original':continue
   _,_,assets=read_pack(pack,a.source/'src/data/runtime_generated/asset_ids.h')
   for kind in (('mixed',)if a.pilot else('ascii','mixed','accent')if profile=='redux'else('ascii',)):
    folder=a.scratch/(mode+'-'+profile+'-'+kind);folder.mkdir();names=parents.names_for(profile,kind);path=folder/'names.txt';path.write_text('\n'.join(' '.join(map(str,[len(n),*n]))for n in names),encoding='ascii')
    p=subprocess.run([str(exe),str(pack),str(folder),str(path)],cwd=folder,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=120);(folder/'native.log').write_bytes(p.stdout+p.stderr);events=[]
    for line in p.stdout.decode(errors='replace').splitlines():
     if line.startswith(('CONTROL ','TITLE ','STRUCTURES ','HPPP ')):
      t,v=line.split(' ',1);events.append(dict(type=t,actual=json.loads(v)))
    observations=[]
    for e in events:
     if e['type']!='CONTROL':continue
     v=e['actual'];ob=[]
     for row in v['rows']:
      glyphs=names[row['id']-1] if v['test'].startswith('producer') else names[0][:5] if v['test']=='source-pet-branch' else [0x71,0x50,0x8a]
      cols=naming.raster_tiles(glyphs,assets['US/fonts/main.bin'],assets['US/fonts/main.gfx'],v['padding']);got=[bytes.fromhex(x)for x in row['columns'][:len(cols)]]
      ob.append(dict(id=row['id'],raw=row['label'],expectedGlyphs=glyphs,pixelsMatch=got==cols,expectedColumns=len(cols),actualSha256=hashlib.sha256(b''.join(got)).hexdigest(),expectedSha256=hashlib.sha256(b''.join(cols)).hexdigest(),attributes=row['attributes'],positions=row['x']))
     observations.append(dict(test=v['test'],stage=v['stage'],window=v['window'],width=v['width'],height=v['height'],rows=ob,pixelsMatch=all(x['pixelsMatch']for x in ob)))
    highlight=[]
    if profile=='redux':
     by={}
     for o in observations:
      if o['stage']=='highlight':
       at=by.get(o['test'],0);by[o['test']]=at+1;ok=True
       for i,r in enumerate(o['rows']):
        count=r['expectedColumns'];ok &= all(a==([6,6]if i==at and j<count else[0,0])for j,a in enumerate(r['attributes']))
       highlight.append(dict(test=o['test'],selected=at,sourceMeasuredPaletteColumnsMatch=ok))
    title=[e['actual']for e in events if e['type']=='TITLE'];struct=[e['actual']for e in events if e['type']=='STRUCTURES']
    row=dict(build=mode,profile=profile,names=kind,preparedNames=names,exit=p.returncode,link=proof,packSha256=parents.gear.base.helper.digest(pack),observations=observations,highlights=highlight,titleControl=title,structures=struct,hpppControl=[e['actual']for e in events if e['type']=='HPPP'],passed=p.returncode==0 and len(observations)==35 and all(o['pixelsMatch']for o in observations)and all(x['sourceMeasuredPaletteColumnsMatch']for x in highlight))
    # 8 producer cases: rendered+cleared+sum1..4 highlights per producer=36;
    # plus seven unrelated-window controls =43 observations.
    row['passed']=p.returncode==0 and len(observations)==45 and all(o['pixelsMatch']for o in observations)and all(x['sourceMeasuredPaletteColumnsMatch']for x in highlight)
    results.append(row);print(json.dumps(dict(case=folder.name,exit=p.returncode,rows=len(observations),passed=row['passed'],failures=[o['test']+'-'+o['stage']for o in observations if not o['pixelsMatch']][:8],highlightFailures=[x for x in highlight if not x['sourceMeasuredPaletteColumnsMatch']][:3])),flush=True)
 report=dict(toolVersion='dev19-party-name-label-bounded-controls-v2',toolSha256=parents.gear.base.helper.digest(Path(__file__)),results=results,allPassed=all(r['passed']for r in results),rootOrOwnerInputsModified=False,limits=['Direct actual native producer/window/render/highlight API contracts with prepared names and party counts1..4. These are bounded unit/integration controls, not extra naturally reached story parents.','Generic exclusions intentionally contain a synthetic high byte; existing ASCII fallback is an independently expected space. The real ordinary parent suite covers legal source names, actual D-pad input and selected save16 cold continuations.','Title and structure controls are compared to the red baseline separately; no tiny-title/file-slot redesign or new save fields.'])
 a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(report=str(a.output),allPassed=report['allPassed'])))
if __name__=='__main__':main()
