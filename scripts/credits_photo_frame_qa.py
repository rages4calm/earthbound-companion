# SPDX-License-Identifier: GPL-3.0-or-later
"""Check every credits photo frame through the real prepared ending transaction.
Use redux_ending_transaction_qa --help arguments, including --all-photos.
"""
from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parent))
import redux_ending_transaction_qa as qa
trace=r'''
#undef NDEBUG
#include <assert.h>
#undef assert
#define assert(c) do {if(!(c)){fprintf(stderr,"QA_FAIL %s line %d\n",#c,__LINE__);exit(7);}} while(0)
#include "core/decomp.h"
static pixel_t picture[EB_VIEWPORT_HEIGHT][EB_VIEWPORT_WIDTH];
static unsigned photo_samples[32],checks;
static void collect(int y,const pixel_t*p){memcpy(picture[y],p,sizeof(picture[y]));}
static void photo_check(EndingState*s){
 if((s->phase!=EN_CR_SLIDE && s->phase!=EN_CR_SCROLLWAIT) || s->photo_idx>=32 || photo_samples[s->photo_idx])return;
 uint8_t expected[2304];const uint8_t*data=ASSET_DATA(ASSET_ENDING_E1E94A_BIN_LZHAL);
 assert(decomp(data,ASSET_SIZE(ASSET_ENDING_E1E94A_BIN_LZHAL),expected,sizeof(expected))==sizeof(expected));
 assert(!memcmp(expected+1792,ppu.vram+0x4000,512));checks++;photo_samples[s->photo_idx]++;
 printf("PHOTO_FRAME_PASS %u\n",s->photo_idx);
 ppu_render_frame(collect);char n[100];snprintf(n,sizeof(n),"photo-%02u.ppm",s->photo_idx);
 FILE*f=fopen(n,"wb");fprintf(f,"P6\n%d %d\n255\n",EB_VIEWPORT_WIDTH,EB_VIEWPORT_HEIGHT);
 for(unsigned y=0;y<EB_VIEWPORT_HEIGHT;y++)for(unsigned x=0;x<EB_VIEWPORT_WIDTH;x++){
  uint32_t c=pixel_to_rgb888(picture[y][x]);unsigned char rgb[]={c>>16,c>>8,c};fwrite(rgb,1,3,f);
 }fclose(f);
}
'''
qa.DRIVER=qa.DRIVER.replace('int main(int argc,char **argv){',trace+'\nint main(int argc,char **argv){').replace('unsigned ep=g_mode_stack.state[top].ending.phase;','photo_check(&g_mode_stack.state[top].ending);unsigned ep=g_mode_stack.state[top].ending.phase;').replace('audio_shutdown();return','printf("PHOTO_CHECKS %u\\n",checks);assert(checks==32);audio_shutdown();return')
qa.main()
from PIL import Image
scratch=Path(sys.argv[sys.argv.index('--scratch')+1])
for p in (scratch/'session').glob('photo-*.ppm'):Image.open(p).save(p.with_suffix('.png'))
report=Path(sys.argv[sys.argv.index('--output')+1])
result=json.loads(report.read_text());result['capturedPhotoScenes']=32
result['additionalNativeFrameAssertions']=32
result['runtimeSourceQualification']='Execution is bound to the supplied production executable/library hashes; current reference source hashes do not replace that runtime identity.'
report.write_text(json.dumps(result,indent=2)+'\n')
