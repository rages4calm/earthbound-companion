# SPDX-License-Identifier: GPL-3.0-or-later
"""Check the production Lumine scroll against an independent pixel canvas.

Links a private driver to the unchanged production library. Uses packed font
glyphs to paint the complete text into a non-circular canvas, then samples
2x2 pixel cells according to the US DECODE_PLANAR_TILEMAP assembly. Verifies
every playback frame including legacy packed lower phases, BG1 horizontal wrap, retained work-buffer tail, and
Original/Redux name capacities. No player files are written.
"""
import argparse,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
DRIVER=helper.DRIVER[:helper.DRIVER.index('static unsigned pump(void)')]+r'''
#include <stddef.h>
#include "data/event_script_data.h"
#include "snes/ppu.h"
#include "include/constants.h"
extern int16_t callroutine_dispatch(uint32_t,int16_t,int16_t,uint16_t,uint16_t*);
static unsigned char canvas[2048][16];
static unsigned char decoded[943][8];
static unsigned char runtime_before[sizeof(ert)];
static unsigned char vram_before[VRAM_SIZE];
static void fail(const char *what,unsigned a,unsigned b){fprintf(stderr,"FAIL %s %u %u\n",what,a,b);exit(5);}
static unsigned paint(unsigned ch,unsigned x){
 if(ch<0x50)return x;
 unsigned idx=(ch-0x50)&127;
 const unsigned char*g=font_get_glyph(FONT_ID_NORMAL,idx);if(!g)return x;
 unsigned w=font_get_width(FONT_ID_NORMAL,idx)+character_padding,h=font_get_height(FONT_ID_NORMAL);
 if(w>16||h>16||x+16>2048)fail("font bounds",w,h);
 unsigned end=x+w;
 /* US BLIT_VWF_GLYPH clears a fresh tile and writes its overflow only
  * when the supplied advance crosses a tile boundary. Model that on a
  * linear pixel canvas, without the native circular/packed buffers. */
 while(w){
  unsigned step=w>8?8:w,old=x/8,next=(x+step)/8;
  if(x%8==0)memset(canvas+old*8,0,8*16);
  if(next!=old)memset(canvas+next*8,0,8*16);
  for(unsigned y=0;y<h;y++)for(unsigned dx=0;dx<8;dx++)
   if((x+dx)/8==old||next!=old)canvas[x+dx][y]|=!(g[y]&(128>>dx));
  x+=step;w-=step;g+=h;
 }
 return end;
}
int main(int argc,char**argv){
 if(argc!=3)return 2;
 char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 char*boot[]={"lumine-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot)!=0)return 3;
 const unsigned char*t=ASSET_DATA(ASSET_DATA_TEXT_LUMINE_HALL_TEXT_BIN);
 if(!t||ASSET_SIZE(ASSET_DATA_TEXT_LUMINE_HALL_TEXT_BIN)<215)return 4;
 const char*names[]={"","i","Ness","iiiii","WWWWW","WiWiWi"};
 for(unsigned test=0;test<6;test++){
  unsigned len=strlen(names[test]);if(len>maternalbound_name_capacity())len=maternalbound_name_capacity();
  unsigned char encoded[7]={0};
  for(unsigned i=0;i<len;i++)encoded[i]=ascii_to_eb_char(names[test][i]);
  maternalbound_set_character_name(0,encoded,len);
  unsigned char*name=maternalbound_character_name(0);
  memset(canvas,0,sizeof(canvas));memset(decoded,0,sizeof(decoded));unsigned pixels=0;
  for(unsigned i=0;i<4;i++)pixels=paint(t[i],pixels);
  for(unsigned i=0;i<len;i++)pixels=paint(name[i],pixels);
  for(unsigned i=4;i<215;i++)pixels=paint(t[i],pixels);
  unsigned columns=215+len,rows=29+columns*4+30;
  for(unsigned column=0;column<columns;column++)for(unsigned pair=0;pair<4;pair++)for(unsigned y=0;y<8;y++){
   unsigned x=column*8+pair*2;
   decoded[29+column*4+pair][y]=canvas[x][2*y]*2+canvas[x+1][2*y]+canvas[x][2*y+1]*8+canvas[x+1][2*y+1]*4;
  }
  ert.current_entity_slot=0;entities.var[0][0]=entities.var[1][0]=0;
  memset(ert.buffer,0xA5,BUFFER_SIZE);memcpy(runtime_before,&ert,sizeof(ert));
  uint16_t pc=0;callroutine_dispatch(ROM_ADDR_LOAD_CHARACTER_PORTRAIT_SCREEN,0,0,0,&pc);
  if(memcmp(runtime_before,&ert,offsetof(EntityRuntimeState,buffer)))fail("runtime header overwritten",test,0);
  unsigned used=0x2000+rows*8;
  for(unsigned i=used;i<BUFFER_SIZE;i++)if(ert.buffer[i]!=0xA5)fail("buffer tail overwritten",test,i);
  if((unsigned)entities.var[0][0]!=((pixels/8)*4+30)*2)fail("scroll duration",pixels,entities.var[0][0]);
  unsigned frames=entities.var[0][0]+1;
  for(unsigned i=0;i<rows*8;i++)ert.buffer[0x2000+i]=(ert.buffer[0x2000+i]&0xf0)|0xf;
  for(unsigned frame=0;frame<frames;frame++){
   memset(ppu.vram,0xA5,VRAM_SIZE);memcpy(vram_before,ppu.vram,VRAM_SIZE);
   int result=callroutine_dispatch(ROM_ADDR_ADVANCE_TILEMAP_ANIMATION_FRAME,0,0,0,&pc);
   if(result!=(frame+1==frames))fail("completion",frame,result);
   for(unsigned y=0;y<8;y++)for(unsigned column=0;column<30;column++){
    unsigned row=frame/2+column;unsigned a=row<rows?decoded[row][y]:0,b=row?decoded[row-1][y]:0;
    unsigned bits=frame%2?a:row?((a>>1)&5)|((b<<1)&10):0,word=0xC10+bits;
    unsigned at=2+(y*30+column)*2;
    if((unsigned)ert.buffer[at]+ert.buffer[at+1]*256u!=word){fprintf(stderr,"row=%u a=%u b=%u expected=%u actual=%u\n",row,a,b,word,ert.buffer[at]+ert.buffer[at+1]*256u);fail("pixel canvas mismatch",frame,y*30+column);}
    unsigned x=(40+column)%64,base=x>=32?0x3C00:0x3800;
    unsigned vr=2*(base+(12+y)*32+x%32);
    if((unsigned)ppu.vram[vr]+ppu.vram[vr+1]*256u!=word)fail("BG1 wrap mismatch",frame,y*30+column);
    vram_before[vr]=word;vram_before[vr+1]=word>>8;
   }
   if(memcmp(vram_before,ppu.vram,VRAM_SIZE))fail("unrelated VRAM changed",frame,0);
  }
  printf("QA_LUMINE {\"case\":%u,\"nameLength\":%u,\"pixels\":%u,\"frames\":%u,\"viewportWordsCompared\":%u,\"bufferTailPreserved\":true,\"bg1WrapAndUnrelatedVramPassed\":true}\n",test,len,pixels,frames,frames*240);
 }
 return 0;
}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('native-source','build','runtime','assets','scratch','output'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();a.scratch=a.scratch.resolve();a.scratch.mkdir(parents=True,exist_ok=False)
 helper.DRIVER=DRIVER;exe,proof=helper.private_build(a)
 r=subprocess.run([str(exe),str(a.assets.resolve()),str(a.scratch)],cwd=a.scratch,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=60)
 log=a.scratch/'native.log';log.write_bytes(r.stdout+r.stderr);assert r.returncode==0,(r.stdout+r.stderr)[-1600:]
 cases=[json.loads(s[10:]) for s in r.stdout.decode(errors='replace').splitlines() if s.startswith('QA_LUMINE ')]
 assert len(cases)==6
 report=dict(version='0.5.0-redux-dev.26',passed=True,privateBuild=proof,packSha256=helper.digest(a.assets),logSha256=helper.digest(log),cases=cases,
  comparison='Independent full-length glyph pixel canvas sampled as US 2x2 planar cells; every production scroll frame and BG1 destination checked.',
  limits=['Prepared callroutine fixtures, not a complete story or hardware/audio playthrough. Natural copied-checkpoint replay and cold continuation are separate.'],fullPlaythroughVerified=False)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(passed=True,cases=len(cases),words=sum(c['viewportWordsCompared'] for c in cases))))
if __name__=='__main__':main()
