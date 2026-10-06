# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual sequence-animation load/display consumers and decoded source frames.

Prepared animation IDs/frames exercise production consumers, not owning story
parents. Private ROM/render buffers are excluded from the public report.
"""
import argparse
import hashlib
import json
import os
import struct
import subprocess
from pathlib import Path

import battle_action_catalog_qa as helper
import battle_art_decode_qa_dev20 as art
from build_maternalbound_pack import read_pack
from maternalbound_graphics import asm_pointer,snes_offset

DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "core/mode_stack.h"
#include "core/memory.h"
#include "game/game_state.h"
#include "entity/entity.h"
#include "snes/ppu.h"
#include "platform/platform.h"
#include "data/assets.h"
#include "data/event_script_data.h"
#include "include/constants.h"
extern int eb_platform_main(int,char**);
extern int16_t callroutine_dispatch(uint32_t,int16_t,int16_t,uint16_t,uint16_t*);
static pixel_t frame[EB_VIEWPORT_HEIGHT][EB_VIEWPORT_WIDTH];
static const unsigned tiles[]={0,0x1c10,0x5a0,0x3c0,0xaa0,0x40,0x120};
static const unsigned counts[]={0,6,7,8,2,3,2};
static void scanline(int y,const pixel_t*p){if(y>=0&&y<EB_VIEWPORT_HEIGHT)memcpy(frame[y],p,sizeof(frame[y]));}
static void save(const char*folder,const char*kind,unsigned id,unsigned f,const void*p,size_t n){char path[4096];snprintf(path,sizeof(path),"%s/%s-%u-%u.raw",folder,kind,id,f);FILE*out=fopen(path,"wb");if(!out)exit(12);fwrite(p,1,n,out);fclose(out);}
int main(int argc,char**argv){
 if(argc!=3)return 2;char session[4096];snprintf(session,sizeof(session),"%s/fixture.srm",argv[2]);
 char*boot[]={"sequence-art-qa","--assets",argv[1],"--session-dir",argv[2],"--save",session,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot))return 3;platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 4;game_set_fast_forward(true);
 memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_WAIT_FRAMES;
 for(unsigned id=1;id<=6;id++){
  memset(ppu.vram,0,sizeof(ppu.vram));memset(ert.buffer,0,BUFFER_SIZE);memset(ert.palettes,0,sizeof(ert.palettes));memset(ppu.cgram,0,sizeof(ppu.cgram));
  ppu.bgmode=9;ppu.bg_sc[2]=VRAM_TEXT_LAYER_TILEMAP>>8;ppu.bg_nba[1]=VRAM_TEXT_LAYER_TILES>>12;ppu.bg_hofs[2]=0;ppu.tm=4;ppu.ts=0;ppu.inidisp=15;ppu.cgwsel=ppu.cgadsub=0;ppu.window_hdma_active=false;
  ppu.bg_viewport_fill[2]=BG_VIEWPORT_FILL;ppu.sprite_y_offset=ppu.bg_win_y_offset=EB_VIEWPORT_PAD_TOP;
  ert.current_entity_slot=0;entities.var[0][0]=id;entities.var[1][0]=0;
  uint16_t out=0xbeef;int16_t load=callroutine_dispatch(ROM_ADDR_LOAD_ANIMATION_SEQUENCE_FRAME,0,0,0,&out);
  if(load||out)return 20;save(argv[2],"buffer",id,0,ert.buffer,BUFFER_SIZE);
  for(unsigned f=0;f<counts[id];f++){
   entities.var[1][0]=f;out=0xbeef;int16_t delay=callroutine_dispatch(ROM_ADDR_DISPLAY_ANIMATION_SEQUENCE_FRAME,0,0,0,&out);if(out)return 21;
   sync_palettes_to_cgram();ppu_render_frame(scanline);save(argv[2],"frame",id,f,frame,sizeof(frame));save(argv[2],"vram",id,f,ppu.vram,sizeof(ppu.vram));save(argv[2],"palette",id,f,ppu.cgram,sizeof(ppu.cgram));
   printf("QA_FRAME {\"id\":%u,\"frame\":%u,\"nativeTileBytes\":%u,\"nativeCount\":%u,\"delay\":%d,\"width\":%u,\"height\":%u,\"bgYOffset\":%d,\"bgVofs\":%u,\"mode\":%u,\"tm\":%u,\"tileVramBytes\":%u,\"arrVramBytes\":%u}\n",id,f,tiles[id],counts[id],delay,EB_VIEWPORT_WIDTH,EB_VIEWPORT_HEIGHT,ppu.bg_win_y_offset,ppu.bg_vofs[2],ppu.bgmode,ppu.tm,VRAM_TEXT_LAYER_TILES*2,VRAM_TEXT_LAYER_TILEMAP*2);
  }
 }
 return 0;
}
'''


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render(gfx,arr,pal,vofs):
    # Independent SNES2bpp,32x32 map; source BG3 vertical offset is minus1.
    arr=arr.ljust(2048,b'\0');out=bytearray()
    for y in range(224):
        yy=(y+vofs)&255
        for x in range(256):
            word=int.from_bytes(arr[((yy//8)*32+x//8)*2:((yy//8)*32+x//8)*2+2],'little');tile=word&1023
            tx=7-x%8 if word&0x4000 else x%8;ty=7-yy%8 if word&0x8000 else yy%8;at=tile*16
            if at+16>len(gfx):raise ValueError('Source animation tile outside upload')
            color=((gfx[at+ty*2]>>(7-tx))&1)|(((gfx[at+ty*2+1]>>(7-tx))&1)<<1)
            index=((word>>10)&7)*4+color if color else 0
            if index*2+2>len(pal):raise ValueError('Source animation palette outside upload')
            w=int.from_bytes(pal[index*2:index*2+2],'little');out.extend((((w&0x7fe0)<<1)|(w&31)).to_bytes(2,'little'))
    return bytes(out)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native-source','build','runtime','assets','rom','scratch','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--redux',action='store_true');p.add_argument('--diagnostic',action='store_true')
    a=p.parse_args();a.scratch=a.scratch.resolve()
    if a.scratch.exists():raise ValueError('Fresh private scratch required')
    a.scratch.mkdir(parents=True);helper.DRIVER=DRIVER;exe,provenance=helper.private_build(a)
    _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h');rom=a.rom.read_bytes()
    table_ptr=asm_pointer(rom,0x47ab0);table_at=snes_offset(table_ptr,len(rom));table=rom[table_at:table_at+56]
    if len(table)!=56 or any(table[:8]):raise ValueError('Invalid source animation table')
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    cp=subprocess.run([str(exe),str(a.assets.resolve()),str(a.scratch)],env=env,capture_output=True,timeout=90)
    (a.scratch/'stdout.log').write_bytes(cp.stdout);(a.scratch/'stderr.log').write_bytes(cp.stderr)
    if cp.returncode:raise RuntimeError('Native animation consumer failed:'+str(cp.returncode)+cp.stderr.decode(errors='replace'))
    rows=[json.loads(line.split(' ',1)[1])for line in cp.stdout.decode(errors='replace').splitlines()if line.startswith('QA_FRAME ')]
    if len(rows)!=28:raise ValueError('Missing native frames')
    keys=['graphics/animations/lightning_reflect.anim.lzhal','graphics/animations/lightning_strike.anim.lzhal',
          'graphics/animations/starman_jr_teleport.anim.lzhal','graphics/animations/boom.anim.lzhal',
          'graphics/animations/zombies.anim.lzhal','US/graphics/animations/the_end.anim.lzhal']
    result=dict(toolSha256=digest(__file__),production=provenance,packSha256=digest(a.assets),romSha256=digest(a.rom),
                pinnedReduxCommit=art.PIN if a.redux else None,profile='Redux'if a.redux else'Original',
                runtimeExecuted=True,ownerWrites=False,fullVisualParityVerified=False,preparedCases=6,preparedFrames=28,skippedCases=0,
                sourceTablePointer=table_ptr,sourceTableSha256=art.h(table),sourceRecords=[],checks=[],sourceParityChecks=[],nativeRows=rows)
    def check(name,passed,**detail):result['checks'].append(dict(check=name,passed=bool(passed),**detail))
    for id,key in enumerate(keys,1):
        record=table[id*8:(id+1)*8];pointer=int.from_bytes(record[:4],'little');tile_bytes=int.from_bytes(record[4:6],'little');count=record[6];delay=record[7]
        source,_,_=art.strict_decode(rom[snes_offset(pointer,len(rom)):]);donor,_,_=art.strict_decode(assets[key],True)
        native_rows=[r for r in rows if r['id']==id];ntiles=native_rows[0]['nativeTileBytes'];ncount=native_rows[0]['nativeCount']
        if len(source)!=tile_bytes+8+count*1792 or len(donor)!=ntiles+8+ncount*1792:raise ValueError('Unexpected animation layout')
        frame_max_tiles=[max(int.from_bytes(source[tile_bytes+8+f*1792+j:tile_bytes+8+f*1792+j+2],'little')&1023 for j in range(0,1792,2))for f in range(count)]
        check(f'{id}-source-arrangements-in-bounds',all(x<tile_bytes//16 for x in frame_max_tiles),sourceTileCount=tile_bytes//16,maximumTileByFrame=frame_max_tiles)
        result['sourceRecords'].append(dict(id=id,asset=key,sourcePointer=pointer,sourceTileBytes=tile_bytes,sourceFrameCount=count,
            sourceDelay=delay,sourceDecodedBytes=len(source),sourceDecodedSha256=art.h(source),nativeTileBytes=ntiles,nativeFrameCount=ncount,
            nativeDecodedBytes=len(donor),nativeDecodedSha256=art.h(donor),sourceBytesEqual=source==donor,metadataLayoutEqual=tile_bytes==ntiles and count==ncount,maximumTileByFrame=frame_max_tiles))
        buffer=(a.scratch/f'buffer-{id}-0.raw').read_bytes();check(f'{id}-native-decompress',buffer[:len(donor)]==donor)
        check(f'{id}-source-frame-count',count==ncount)
        for row in native_rows:
            f=row['frame'];vram=(a.scratch/f'vram-{id}-{f}.raw').read_bytes();pal=(a.scratch/f'palette-{id}-{f}.raw').read_bytes();raw=(a.scratch/f'frame-{id}-{f}.raw').read_bytes()
            w=row['width'];x=(w-256)//2;y=row['bgYOffset'];actual=b''.join(raw[((yy*w+x)*2):((yy*w+x+256)*2)]for yy in range(y,y+224))
            gfx=vram[row['tileVramBytes']:row['tileVramBytes']+ntiles];arr=vram[row['arrVramBytes']:row['arrVramBytes']+1792]
            off=ntiles+8+f*1792
            check(f'{id}-{f}-native-upload',gfx==donor[:ntiles]and arr==donor[off:off+1792])
            check(f'{id}-{f}-native-render',actual==render(gfx,arr,pal,row['bgVofs']))
            check(f'{id}-{f}-source-delay',row['delay']==(0 if f+1==count else delay),native=row['delay'])
            sp=source[tile_bytes:tile_bytes+8].ljust(512,b'\0');sa=source[tile_bytes+8+f*1792:tile_bytes+8+(f+1)*1792]
            expected=render(source[:tile_bytes],sa,sp,65535)
            result['sourceParityChecks'].append(dict(check=f'{id}-{f}-source-art',passed=expected==actual,
                sourceSha256=art.h(expected),nativeSha256=art.h(actual),sourceNonBlackPixels=sum(expected[j:j+2]!=b'\0\0'for j in range(0,len(expected),2)),nativeNonBlackPixels=sum(actual[j:j+2]!=b'\0\0'for j in range(0,len(actual),2)),differingPixels=sum(expected[j:j+2]!=actual[j:j+2]for j in range(0,len(expected),2))))
    result['sourceIdentities']={x:digest(a.native_source/x)for x in ('src/entity/callroutine.c','src/snes/ppu_render.c','src/entity/entity.h','asm/misc/load_animation_sequence_frame.asm','asm/misc/display_animation_sequence_frame.asm','asm/data/animation_sequence_pointers.asm')}
    result['nativeExecutionPassed']=all(x['passed']for x in result['checks']);result['sourceParityPassed']=all(x['passed']for x in result['sourceParityChecks']);result['allPassed']=result['nativeExecutionPassed']and result['sourceParityPassed']
    result['executedAssertions']=len(result['checks'])+len(result['sourceParityChecks'])
    result['limits']=['Prepared real LOAD/DISPLAY_ANIMATION_SEQUENCE_FRAME dispatch for every valid frame of six configured sequences; owning CarPainter/Starman/Threed/ending parent timelines are not executed.',
        'Independent source table and 2bpp renderer compare actual centered BG3 with source vertical offset; shared retained data can use different tile packing if the visible frames and delays agree.',
        'No full story, sound scheduling, natural scene layering or global audiovisual parity claim.']
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({key:result[key]for key in ('nativeExecutionPassed','sourceParityPassed','allPassed','executedAssertions','preparedCases','preparedFrames','skippedCases')}))
    raise SystemExit(0 if result['allPassed']or(a.diagnostic and result['nativeExecutionPassed'])else 1)


if __name__=='__main__':main()
