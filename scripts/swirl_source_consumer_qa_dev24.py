# SPDX-License-Identifier: GPL-3.0-or-later
"""Source-resolved swirl HDMA frames through actual init/update consumers.

Prepared animation entries cover the six stored sequences, every frame, forward
and reverse and all8 window flags. This is a mask/data test, not full encounters.
"""
import argparse,hashlib,json,os,struct,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
from build_maternalbound_pack import read_pack
from maternalbound_graphics import snes_offset

DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "game/oval_window.h"
#include "platform/platform.h"
#include "snes/ppu.h"
extern int eb_platform_main(int,char**);
static uint8_t image[224][32];
static void renderline(int y,const pixel_t*p){if(y<EB_VIEWPORT_PAD_TOP||y>=EB_VIEWPORT_PAD_TOP+224)return;unsigned yy=y-EB_VIEWPORT_PAD_TOP;for(unsigned x=0;x<256;x++)if(p[EB_VIEWPORT_PAD_LEFT+x])image[yy][x/8]|=1u<<(x&7);}
static void save(const char*folder,unsigned type,unsigned opts,unsigned id){char path[4096];snprintf(path,sizeof(path),"%s/mask-%u-%u-%u.raw",folder,type,opts,id);FILE*f=fopen(path,"wb");if(!f)exit(12);for(unsigned i=0;i<EB_VIEWPORT_HEIGHT;i++){uint8_t b[]={ppu.wh0_table[i],ppu.wh1_table[i],ppu.wh2_table[i],ppu.wh3_table[i]};fwrite(b,1,4,f);}fclose(f);memset(image,0,sizeof(image));ppu_render_frame(renderline);snprintf(path,sizeof(path),"%s/image-%u-%u-%u.raw",folder,type,opts,id);f=fopen(path,"wb");if(!f)exit(13);fwrite(image,1,sizeof(image),f);fclose(f);}
int main(int argc,char**argv){if(argc!=3)return 2;char session[4096];snprintf(session,sizeof(session),"%s/fixture.srm",argv[2]);char*boot[]={"swirl-qa","--assets",argv[1],"--session-dir",argv[2],"--save",session,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot))return 3;
 for(unsigned type=1;type<=6;type++)for(unsigned opts=0;opts<8;opts++){
  memset(ppu.vram,0,sizeof(ppu.vram));memset(ppu.cgram,0,sizeof(ppu.cgram));for(unsigned y=0;y<8;y++)ppu.vram[y*2]=255;ppu.cgram[1]=31;ppu.inidisp=15;ppu.bgmode=1;ppu.tm=1;ppu.ts=0;ppu.cgwsel=ppu.cgadsub=0;ppu.bg_sc[0]=0x20;ppu.bg_nba[0]=0;ppu.bg_hofs[0]=ppu.bg_vofs[0]=0;ppu.bg_win_y_offset=EB_VIEWPORT_PAD_TOP;ppu.bg_viewport_fill[0]=BG_VIEWPORT_FILL;
  ppu.wh2=255;ppu.wh3=0;ppu.window2_hdma_active=false;memset(ppu.wh2_table,255,sizeof(ppu.wh2_table));memset(ppu.wh3_table,0,sizeof(ppu.wh3_table));init_swirl_effect(type,opts);unsigned ticks=0,frames=0;
  OvalWindowSaveState state={0};oval_window_savestate_pack(&state);
  while(state.frames_until_next_swirl_update&&++ticks<1000){OvalWindowSaveState before={0},after={0};oval_window_savestate_pack(&before);update_swirl_effect();oval_window_savestate_pack(&after);state=after;
   if(after.swirl_frames_left<before.swirl_frames_left){unsigned id=opts&1?after.swirl_hdma_table_id:before.swirl_hdma_table_id;save(argv[2],type,opts,id);frames++;
    printf("QA_MASK {\"type\":%u,\"options\":%u,\"frameId\":%u,\"tick\":%u,\"height\":%u,\"padTop\":%u,\"window1Active\":%u,\"window2Active\":%u,\"w12sel\":%u,\"w34sel\":%u,\"wobjsel\":%u,\"tmw\":%u,\"wbglog\":%u}\n",type,opts,id,ticks,EB_VIEWPORT_HEIGHT,EB_VIEWPORT_PAD_TOP,ppu.window_hdma_active,ppu.window2_hdma_active,ppu.w12sel,ppu.w34sel,ppu.wobjsel,ppu.tmw,ppu.wbglog);
   }
  }
  printf("QA_SEQUENCE {\"type\":%u,\"options\":%u,\"ticks\":%u,\"frames\":%u,\"activeAtExit\":%u,\"window1ActiveAtExit\":%u,\"window2ActiveAtExit\":%u}\n",type,opts,ticks,frames,state.frames_until_next_swirl_update,ppu.window_hdma_active,ppu.window2_hdma_active);
  if(ticks>=1000)return 4;
 }
 return 0;
}
'''

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def h(b):return hashlib.sha256(b).hexdigest()

def decode(b):
    if not b or b[0]not in (1,4):raise ValueError('Unsupported HDMA register mode')
    width=2 if b[0]==1 else 4;at=1;rows=[]
    while True:
        if at>=len(b):raise ValueError('Unterminated HDMA table')
        count=b[at];at+=1
        if not count:break
        n=count&127
        if not n:raise ValueError('128-line HDMA not supported by compiled swirl format')
        if count&128:
            for _ in range(n):
                if at+width>len(b):raise ValueError('Truncated HDMA table')
                rows.append(tuple(b[at:at+width]) if width==4 else(*b[at:at+2],255,0));at+=width
        else:
            if at+width>len(b):raise ValueError('Truncated HDMA table')
            row=tuple(b[at:at+width])if width==4 else(*b[at:at+2],255,0);rows.extend([row]*n);at+=width
        if len(rows)>224:raise ValueError('HDMA table beyond224 source scanlines')
    if len(rows)!=224:raise ValueError(('Unexpected HDMA source rows',len(rows)))
    return rows,at

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native-source','build','runtime','assets','rom','project','coilsnake','scratch','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--redux',action='store_true');p.add_argument('--diagnostic',action='store_true');a=p.parse_args();a.scratch=a.scratch.resolve()
    if a.scratch.exists()or a.output.exists():raise ValueError('Fresh immutable evidence required')
    a.scratch.mkdir(parents=True);helper.DRIVER=DRIVER;exe,production=helper.private_build(a)
    _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h');rom=a.rom.read_bytes();table=rom[0xEDD41:0xEDD41+28]
    if len(table)!=28:raise ValueError('Source primary table out of bounds')
    source_ranges=[]
    for type in range(1,7):
        speed,first,count,unused=table[type*4:type*4+4]
        source_ranges.append(dict(type=type,speed=speed,firstFrame=first,frameCount=count))
    if sum(x['frameCount']for x in source_ranges)!=126:raise ValueError('Source animation cardinality changed')
    source=[]
    if a.redux:
        pointer=int.from_bytes(rom[0x4AA8F:0x4AA92],'little')
        if int.from_bytes(rom[0x4AA95:0x4AA98],'little')!=pointer+2 or int.from_bytes(rom[0x4AADC:0x4AADF],'little')!=pointer or int.from_bytes(rom[0x4AAE4:0x4AAE7],'little')!=pointer+2:raise ValueError('Relocated source pointer call sites disagree')
        offset=snes_offset(pointer,len(rom));pointers=[int.from_bytes(rom[offset+i*4:offset+i*4+4],'little')for i in range(126)]
    else:pointer=0xCEDC45;pointers=[0xCE0000|int.from_bytes(rom[0xEDC45+i*2:0xEDC45+i*2+2],'little')for i in range(126)]
    for id,ptr in enumerate(pointers):
        off=snes_offset(ptr,len(rom));raw=rom[off:off+1100];rows,used=decode(raw);donor,dused=decode(assets[f'swirls/{id}.swirl']);source.append(dict(id=id,sourcePointer=ptr,sourceMode=raw[0],sourceBytes=used,sourceSha256=h(raw[:used]),nativeMode=assets[f'swirls/{id}.swirl'][0],nativeBytes=dused,nativeSha256=h(assets[f'swirls/{id}.swirl'][:dused]),decodedRowsEqual=rows==donor,secondWindowActiveRows=sum(r[2]<=r[3]for r in rows),_rows=rows,_donor=donor))
    cp=subprocess.run([str(exe),str(a.assets.resolve()),str(a.scratch)],env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=90);(a.scratch/'native.log').write_bytes(cp.stdout+cp.stderr)
    frames=[json.loads(line.split(' ',1)[1])for line in cp.stdout.decode(errors='replace').splitlines()if line.startswith('QA_MASK ')];sequences=[json.loads(line.split(' ',1)[1])for line in cp.stdout.decode(errors='replace').splitlines()if line.startswith('QA_SEQUENCE ')]
    checks=[]
    def check(name,passed,**detail):checks.append(dict(check=name,passed=bool(passed),**detail))
    check('native-exit-zero',cp.returncode==0);check('all8options-sixsequences',len(sequences)==48);check('all126frames-eightoptions',len(frames)==1008)
    for row in sequences:
        spec=source_ranges[row['type']-1];check(f"sequence-{row['type']}-{row['options']}",row['frames']==spec['frameCount'] and row['ticks']==spec['frameCount']*spec['speed']+1 and not row['activeAtExit'],**row)
    frame_checks=[]
    for row in frames:
        type,opts,id=row['type'],row['options'],row['frameId'];actual=(a.scratch/f'mask-{type}-{opts}-{id}.raw').read_bytes();height,pad=row['height'],row['padTop'];arr=list(struct.iter_unpack('4B',actual));native=arr[pad:pad+224];src=source[id]['_rows'];donor=source[id]['_donor'];mode=source[id]['sourceMode']
        firstequal=all(n[:2]==s[:2]for n,s in zip(native,src));secondequal=mode==1 or(row['window2Active']and all(n[2:]==s[2:]for n,s in zip(native,src)))
        expected=bytearray(224*32)
        for yy,(a1,b1,a2,b2)in enumerate(src):
            for x in range(256):
                inside1=a1<=x<=b1;inside2=a2<=x<=b2
                # SET_WINDOW_MASK uses OR for non-inverted windows(options2)
                # and AND of the inverted windows otherwise(options0).
                masked=False if opts&4 else(inside1 or inside2)if opts&2 else(not inside1 and not inside2)
                if not masked:expected[yy*32+x//8]|=1<<(x&7)
        native_image=(a.scratch/f'image-{type}-{opts}-{id}.raw').read_bytes()
        frame_checks.append(dict(type=type,options=opts,frameId=id,sourceMode=mode,sourceRowsEqualToDonor=src==donor,firstWindowMatchesSource=firstequal,secondWindowMatchesSource=bool(secondequal),sourceCompositeMaskMatchesNative=bytes(expected)==native_image,sourceCompositeMaskSha256=h(expected),nativeCompositeMaskSha256=h(native_image),differingMaskedPixels=sum((x^y).bit_count()for x,y in zip(expected,native_image)),secondWindowActiveRows=source[id]['secondWindowActiveRows'],
                                differingFirstWindowRows=sum(n[:2]!=s[:2]for n,s in zip(native,src)),differingSecondWindowRows=sum(n[2:]!=s[2:]for n,s in zip(native,src)),sourceRowsSha256=h(bytes(x for r in src for x in r)),nativeRowsSha256=h(actual[pad*4:(pad+224)*4])))
    for x in source:x.pop('_rows');x.pop('_donor')
    result=dict(toolSha256=sha(__file__),production=production,packSha256=sha(a.assets),romSha256=sha(a.rom),pinnedReduxCommit=helper.PIN if a.redux else None,profile='Redux'if a.redux else'Original',runtimeExecuted=True,
                sourcePointerTable=pointer,sourcePrimaryTableSha256=h(table),sourceRanges=source_ranges,sourceRecords=source,checks=checks,frameChecks=frame_checks,
                sourceIdentities={x:sha(a.native_source/x)for x in ('src/game/oval_window.c','src/snes/ppu_render.c','asm/misc/init_swirl_effect.asm','asm/misc/update_swirl_effect.asm','asm/data/battle/swirl_pointers.asm')},
                compilerIdentities={x:sha(a.coilsnake/x)for x in ('coilsnake/modules/eb/SwirlModule.py','coilsnake/model/eb/swirls.py')},
                allNativeTimelinesPassed=all(x['passed']for x in checks),allSourceFirstWindowsPassed=all(x['firstWindowMatchesSource']for x in frame_checks),allSourceSecondWindowsPassed=all(x['secondWindowMatchesSource']for x in frame_checks),allSourceMaskRenderPassed=all(x['sourceCompositeMaskMatchesNative']for x in frame_checks),
                executedAssertions=len(checks)+3*len(frame_checks),preparedSequences=6,preparedFrames=126,optionVariants=8,skippedCases=0,
                limits=['Actual init/update source metadata, timing, forward/reverse frames and window masks plus uniform-color BG1 production renderer; complete battle-swirl parent and color math are not executed.',
                        'Compiled Redux four-byte relocated pointer table is checked at allfour actual patch consumers against independent CoilSnake source; Original source retains two-byte CE table.',
                        'A mode4 second-window mismatch is consumer evidence, distinct from relocated raw repacking or pack omissions.'],ownerWrites=False)
    result['allPassed']=result['allNativeTimelinesPassed']and result['allSourceFirstWindowsPassed']and result['allSourceSecondWindowsPassed']and result['allSourceMaskRenderPassed'];a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:result[k]for k in ('allPassed','allNativeTimelinesPassed','allSourceFirstWindowsPassed','allSourceSecondWindowsPassed','allSourceMaskRenderPassed','executedAssertions')}));raise SystemExit(0 if result['allPassed']or a.diagnostic else 1)

if __name__=='__main__':main()
