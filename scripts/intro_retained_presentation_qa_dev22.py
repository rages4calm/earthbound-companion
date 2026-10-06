# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared native intro art consumers compared with decoded pinned source.

Raw buffers stay in private scratch. Actual uploads and source-image equality
are separate assertions, so tile repacking is not classified as a defect.
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
from maternalbound_graphics import asm_pointer, snes_offset

DRIVER = r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "core/mode_stack.h"
#include "core/memory.h"
#include "intro/logo_screen.h"
#include "intro/gas_station.h"
#include "game/battle_bg.h"
#include "game/game_state.h"
#include "game/fade.h"
#include "entity/entity.h"
#include "snes/ppu.h"
#include "platform/platform.h"
#include "data/assets.h"
#include "data/event_script_data.h"
extern int eb_platform_main(int,char**);
extern int16_t callroutine_dispatch(uint32_t,int16_t,int16_t,uint16_t,uint16_t*);
static pixel_t frame[EB_VIEWPORT_HEIGHT][EB_VIEWPORT_WIDTH];
static void scanline(int y,const pixel_t*p){if(y>=0&&y<EB_VIEWPORT_HEIGHT)memcpy(frame[y],p,sizeof(frame[y]));}
static void save(const char*folder,const char*kind,unsigned id,const void*p,size_t n){char path[4096];snprintf(path,sizeof(path),"%s/%s-%u.raw",folder,kind,id);FILE*f=fopen(path,"wb");if(!f)exit(12);fwrite(p,1,n,f);fclose(f);}
static void snapshot(const char*folder,const char*kind,unsigned id,unsigned frames){
 char name[64];snprintf(name,sizeof(name),"%s-vram",kind);save(folder,name,id,ppu.vram,sizeof(ppu.vram));
 snprintf(name,sizeof(name),"%s-palette",kind);save(folder,name,id,ert.palettes,sizeof(ert.palettes));
 snprintf(name,sizeof(name),"%s-cgram",kind);save(folder,name,id,ppu.cgram,sizeof(ppu.cgram));
 ppu_render_frame(scanline);snprintf(name,sizeof(name),"%s-frame",kind);save(folder,name,id,frame,sizeof(frame));
 printf("QA_CAPTURE {\"kind\":\"%s\",\"id\":%u,\"frames\":%u,\"width\":%u,\"height\":%u,\"bgYOffset\":%d,\"brightness\":%u,\"mode\":%u,\"tm\":%u,\"ts\":%u,\"bgSc\":[%u,%u,%u],\"bgNba\":[%u,%u],\"bgHofs\":[%u,%u,%u],\"bgVofs\":[%u,%u,%u],\"colorMath\":%u,\"cgwsel\":%u}\n",kind,id,frames,EB_VIEWPORT_WIDTH,EB_VIEWPORT_HEIGHT,ppu.bg_win_y_offset,ppu.inidisp,ppu.bgmode,ppu.tm,ppu.ts,ppu.bg_sc[0],ppu.bg_sc[1],ppu.bg_sc[2],ppu.bg_nba[0],ppu.bg_nba[1],ppu.bg_hofs[0],ppu.bg_hofs[1],ppu.bg_hofs[2],ppu.bg_vofs[0],ppu.bg_vofs[1],ppu.bg_vofs[2],ppu.cgadsub,ppu.cgwsel);
}
static void root(void){memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_WAIT_FRAMES;core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=0;}
static int step(unsigned*frames){unsigned t=g_mode_stack.depth-1;StepResult r=mode_dispatch_step(g_mode_stack.mode[t],&g_mode_stack.state[t]);if(r.kind==STEP_PUSH)mode_push(r.push_mode,r.push_init);else if(r.kind==STEP_POP)mode_pop(r.pop_result);else{host_process_frame();(*frames)++;core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=0;}return r.kind;}
int main(int argc,char**argv){
 if(argc!=4)return 2;char session[4096];snprintf(session,sizeof(session),"%s/fixture.srm",argv[2]);
 char*boot[]={"intro-art-qa","--assets",argv[1],"--session-dir",argv[2],"--save",session,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot))return 3;platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 4;game_set_fast_forward(true);
 if(!strcmp(argv[3],"logos")){
  root();memset(ppu.vram,0,sizeof(ppu.vram));memset(ert.palettes,0,sizeof(ert.palettes));memset(ppu.cgram,0,sizeof(ppu.cgram));ppu.cgadsub=ppu.cgwsel=0;
  ModeState state={0};state.intro_logo.phase=LG_LOAD;mode_push(GAME_MODE_INTRO_LOGO,&state);unsigned captured=0,steps=0,frames=0;
  while(g_mode_stack.depth>1&&++steps<2000){
   unsigned t=g_mode_stack.depth-1;IntroLogoState*s=&g_mode_stack.state[t].intro_logo;
   if(g_mode_stack.mode[t]==GAME_MODE_INTRO_LOGO&&s->phase==LG_HOLD&&(ppu.inidisp&15)==15&&!(captured&(1<<s->logo_idx))){snapshot(argv[2],"logos",s->logo_idx,frames);captured|=1<<s->logo_idx;}
   step(&frames);
  }
  printf("QA_EXIT {\"kind\":\"logos\",\"steps\":%u,\"frames\":%u,\"captured\":%u,\"depth\":%u,\"result\":%d}\n",steps,frames,captured,g_mode_stack.depth,g_mode_stack.child_result[0]);
  if(g_mode_stack.depth!=1||captured!=7||g_mode_stack.child_result[0]!=0)return 20;
 }else if(!strcmp(argv[3],"overlays")){
  for(unsigned id=0;id<2;id++){
   root();memset(ppu.vram,0,sizeof(ppu.vram));memset(ert.palettes,0,sizeof(ert.palettes));memset(ppu.cgram,0,sizeof(ppu.cgram));
   ppu.bgmode=9;ppu.bg_sc[2]=0x7c;ppu.bg_nba[1]=6;ppu.bg_hofs[2]=ppu.bg_vofs[2]=0;ppu.tm=4;ppu.ts=0;ppu.inidisp=15;ppu.cgwsel=ppu.cgadsub=0;ppu.window_hdma_active=false;
   ppu.bg_viewport_fill[2]=BG_VIEWPORT_FILL;ppu.sprite_y_offset=ppu.bg_win_y_offset=EB_VIEWPORT_PAD_TOP;
   uint16_t out=0xbeef;int16_t result=callroutine_dispatch(id?ROM_ADDR_DECOMP_NINTENDO_PRESENTATION:ROM_ADDR_DECOMP_ITOI_PRODUCTION,0,0,0,&out);
   sync_palettes_to_cgram();snapshot(argv[2],"overlays",id,0);
   printf("QA_EXIT {\"kind\":\"overlays\",\"id\":%u,\"result\":%d,\"outPc\":%u}\n",id,result,out);if(result||out)return 21;
  }
 }else if(!strcmp(argv[3],"gas")){
  root();memset(ppu.vram,0,sizeof(ppu.vram));memset(ert.palettes,0,sizeof(ert.palettes));memset(ppu.cgram,0,sizeof(ppu.cgram));ppu.inidisp=0x80;
  ModeState parent={0};parent.init_intro.phase=II_GAS;mode_push(GAME_MODE_INIT_INTRO,&parent);unsigned steps=0,frames=0,captured=0,flashSeen=0;
  step(&frames);if(g_mode_stack.depth!=3||g_mode_stack.mode[2]!=GAME_MODE_GAS_STATION)return 22;
  snapshot(argv[2],"gas",0,frames);
  while(g_mode_stack.depth>2&&++steps<5000){
   unsigned t=g_mode_stack.depth-1;
   if(g_mode_stack.mode[t]==GAME_MODE_GAS_STATION){GasStationState*s=&g_mode_stack.state[t].gas_station;
    if(s->phase==GS_PH3&&!captured){snapshot(argv[2],"gas",1,frames);captured=1;}
    if(s->phase==GS_PH4)flashSeen=1;
   }
   step(&frames);
  }
  snapshot(argv[2],"gas",2,frames);
  printf("QA_EXIT {\"kind\":\"gas\",\"steps\":%u,\"frames\":%u,\"captured\":%u,\"flashSeen\":%u,\"depth\":%u,\"result\":%d,\"tm\":%u,\"ts\":%u,\"spriteYOffset\":%d,\"bgYOffset\":%d,\"bg2Fill\":%u}\n",steps,frames,captured,flashSeen,g_mode_stack.depth,g_mode_stack.child_result[1],ppu.tm,ppu.ts,ppu.sprite_y_offset,ppu.bg_win_y_offset,ppu.bg_viewport_fill[1]);
  if(g_mode_stack.depth!=2||!captured||!flashSeen||g_mode_stack.child_result[1]!=0)return 23;
 }else return 5;return 0;
}
'''


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decode(data):
    return art.strict_decode(data, True)[0]


def source_stream(rom, site):
    pointer = asm_pointer(rom, site)
    return art.strict_decode(rom[snes_offset(pointer, len(rom)):])[0]


def bgr565(data):
    return b''.join((((w & 0x7fe0) << 1) | (w & 31)).to_bytes(2, 'little') for (w,) in struct.iter_unpack('<H', data))


def pixels(gfx, arr, pal, depth):
    if depth not in (2, 8):
        raise ValueError('Unreviewed source bitdepth')
    out = bytearray()
    for y in range(224):
        for x in range(256):
            word = int.from_bytes(arr[((y//8)*32+x//8)*2:((y//8)*32+x//8)*2+2], 'little')
            tile = word & 1023
            xx = 7-x%8 if word & 0x4000 else x%8
            yy = 7-y%8 if word & 0x8000 else y%8
            at = tile * depth * 8
            if at+depth*8 > len(gfx):
                raise ValueError('Source tile reference exceeds actual upload')
            color = sum(((gfx[at+yy*2+p%2+(p//2)*16] >> (7-xx)) & 1) << p for p in range(depth))
            index = (((word >> 10) & 7)*4+color) if color and depth == 2 else color
            if index*2+2 > len(pal):
                raise ValueError('Source palette reference exceeds actual data')
            out.extend(pal[index*2:index*2+2])
    return bgr565(out)


def crop(raw, row):
    w = row['width']; x = (w-256)//2; y = row['bgYOffset']
    if y < 0 or y+224 > row['height']:
        raise ValueError('Native source crop outside frame')
    return b''.join(raw[((yy*w+x)*2):((yy*w+x+256)*2)] for yy in range(y, y+224))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('native-source', 'build', 'runtime', 'assets', 'rom', 'scratch', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--redux', action='store_true'); p.add_argument('--diagnostic', action='store_true')
    a = p.parse_args(); a.scratch = a.scratch.resolve()
    if a.scratch.exists():
        raise ValueError('Fresh isolated scratch required')
    a.scratch.mkdir(parents=True); helper.DRIVER = DRIVER
    exe, provenance = helper.private_build(a)
    _, _, assets = read_pack(a.assets, a.native_source/'src/data/runtime_generated/asset_ids.h')
    rom = a.rom.read_bytes()
    result = dict(toolSha256=digest(__file__), production=provenance, packSha256=digest(a.assets), romSha256=digest(a.rom),
                  pinnedReduxCommit=art.PIN if a.redux else None, profile='Redux' if a.redux else 'Original',
                  runtimeExecuted=True, ownerWrites=False, fullVisualParityVerified=False, nativeRuns=[], checks=[], sourceParityChecks=[], compiledConsumers=[])
    def check(name, passed, **detail):
        result['checks'].append(dict(check=name, passed=bool(passed), **detail))
    def sourcecheck(name, source, actual, **detail):
        result['sourceParityChecks'].append(dict(check=name, passed=source == actual, sourceSha256=art.h(source), nativeSha256=art.h(actual),
                                               differingPixels=sum(source[i:i+2] != actual[i:i+2] for i in range(0, min(len(source), len(actual)), 2)), **detail))
    def consumer(asset, site, upload_bytes, depth=None):
        raw=source_stream(rom,site)
        result['compiledConsumers'].append(dict(asset=asset,loadPointerSite=site,sourcePointer=asm_pointer(rom,site),
            decodedBytes=len(raw),decodedSha256=art.h(raw),uploadBytes=upload_bytes,bitdepth=depth))
    env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
    folders = {}
    for kind in ('logos', 'overlays', 'gas'):
        folder = a.scratch/kind; folder.mkdir(); folders[kind] = folder
        cp = subprocess.run([str(exe), str(a.assets.resolve()), str(folder), kind], env=env, capture_output=True, timeout=150)
        (folder/'stdout.log').write_bytes(cp.stdout); (folder/'stderr.log').write_bytes(cp.stderr)
        rows = [dict(event=line.split(' ', 1)[0], **json.loads(line.split(' ', 1)[1])) for line in cp.stdout.decode(errors='replace').splitlines() if line.startswith(('QA_CAPTURE ', 'QA_EXIT '))]
        result['nativeRuns'].append(dict(kind=kind, exitCode=cp.returncode, rows=rows, stdoutSha256=digest(folder/'stdout.log'), stderrSha256=digest(folder/'stderr.log')))
        if cp.returncode:
            a.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
            raise RuntimeError('Incomplete native '+kind+': '+str(cp.returncode)+' '+cp.stderr.decode(errors='replace'))
    source_gfx = bytearray(0x8000); source_arr = bytearray(0x800); source_pal = bytearray(512)
    logo_sets = [('US/intro/logos/nintendo', 'intro/logos/nintendo.pal.lzhal', 0xeea3, 0xeebb, 0xeed3),
                 ('intro/logos/ape', 'intro/logos/ape.pal.lzhal', 0xeefb, 0xef13, 0xef2b),
                 ('intro/logos/halken', 'intro/logos/halken.pal.lzhal', 0xef52, 0xef6a, 0xef82)]
    for i, (base, palette, gsite, asite, psite) in enumerate(logo_sets):
        folder = folders['logos']; row = next(x for x in result['nativeRuns'][0]['rows'] if x['event']=='QA_CAPTURE' and x['id']==i)
        vram = (folder/f'logos-vram-{i}.raw').read_bytes(); pal = (folder/f'logos-cgram-{i}.raw').read_bytes()
        actual = crop((folder/f'logos-frame-{i}.raw').read_bytes(), row)
        g = decode(assets[base+'.gfx.lzhal']); ar = decode(assets[base+'.arr.lzhal']); pa = decode(assets[palette])
        check(f'logo-{i}-native-uploads', vram[:len(g)]==g and vram[0x8000:0x8000+len(ar)]==ar and pal[:len(pa)]==pa)
        check(f'logo-{i}-native-render', actual == pixels(vram[:0x8000], vram[0x8000:0x8800], pal, 2))
        sg = source_stream(rom, gsite); sa = source_stream(rom, asite); sp = source_stream(rom, psite)
        consumer(base+'.gfx.lzhal',gsite,0x8000,2);consumer(base+'.arr.lzhal',asite,0x800);consumer(palette,psite,512)
        source_gfx[:len(sg)] = sg; source_arr[:len(sa)] = sa; source_pal[:len(sp)] = sp
        sourcecheck(f'logo-{i}-source-base-art', pixels(source_gfx, source_arr, source_pal, 2), actual,
                    sourceDecodedBytes=dict(graphics=len(sg), arrangement=len(sa), palette=len(sp)),
                    scope='Actual timed native logo parent with real mosaic-fade children; source buffers retain prior source logo data beyond each decoded stream.')
    for i, (base, gsite, asite) in enumerate((('produced_by_itoi',0x4dd73,0x4dd3a),('nintendo_presentation',0x4de1b,0x4dde2))):
        folder = folders['overlays']; row = next(x for x in result['nativeRuns'][1]['rows'] if x['event']=='QA_CAPTURE' and x['id']==i)
        vram = (folder/f'overlays-vram-{i}.raw').read_bytes(); pal = (folder/f'overlays-cgram-{i}.raw').read_bytes()
        actual = crop((folder/f'overlays-frame-{i}.raw').read_bytes(), row)
        key='intro/attract/'+base; g=decode(assets[key+'.gfx.lzhal']); ar=decode(assets[key+'.arr.lzhal']); pa=bytearray(decode(assets['intro/attract/nintendo_itoi.pal.lzhal'])); pa[:2]=b'\0\0'
        arranged = b''.join((w|0x2000).to_bytes(2,'little') for(w,)in struct.iter_unpack('<H',ar))
        check(f'overlay-{i}-native-uploads', vram[0xc000:0xc400]==g[:0x400] and vram[0xf800:]==arranged and pal[:len(pa)]==pa)
        check(f'overlay-{i}-native-render', actual == pixels(vram[0xc000:0xc400], vram[0xf800:], pal, 2))
        sg=source_stream(rom,gsite); sa=source_stream(rom,asite)
        upload_window = rom[gsite:gsite+64]
        if b'\xa0\x00\x60\xa2\x00\x04\xe2\x20' not in upload_window:
            raise ValueError('Pinned source overlay upload no longer matches reviewed 0x400 bytes')
        palette_site=gsite+upload_window.index(b'\x22\x16\x86\xc0')+4
        sp=bytearray(source_stream(rom,palette_site)); sp[:2]=b'\0\0'
        consumer(key+'.gfx.lzhal',gsite,0x400,2);consumer(key+'.arr.lzhal',asite,0x800);consumer('intro/attract/nintendo_itoi.pal.lzhal',palette_site,512)
        sourcecheck(f'overlay-{i}-source-base-art', pixels(sg[:0x400],sa,sp,2),actual,
                    sourceDecodedBytes=dict(graphics=len(sg),arrangement=len(sa),palette=len(sp)),sourceGraphicsUploadBytes=0x400,
                    uploadInstructionWindowSha256=art.h(upload_window),
                    scope='Actual CALLROUTINE dispatch; prepared source BG3 register layout, isolated art rather than owning attract parent.')
    folder=folders['gas']; row=next(x for x in result['nativeRuns'][2]['rows'] if x['event']=='QA_CAPTURE' and x['id']==1)
    vram=(folder/'gas-vram-1.raw').read_bytes(); pal=(folder/'gas-cgram-1.raw').read_bytes(); actual=crop((folder/'gas-frame-1.raw').read_bytes(),row)
    g=decode(assets['US/intro/gas_station.gfx.lzhal']); ar=decode(assets['US/intro/gas_station.arr.lzhal'])
    check('gas-native-uploads',vram[:len(g)]==g and vram[0xf000:0xf800]==ar)
    check('gas-native-render',actual==pixels(vram[:0xc000],vram[0xf000:0xf800],pal,8))
    sg=source_stream(rom,0xf0f0); sa=source_stream(rom,0xf11b); sp=bytearray(source_stream(rom,0xf147)); sp[:2]=b'\0\0'
    consumer('US/intro/gas_station.gfx.lzhal',0xf0f0,0xc000,8);consumer('US/intro/gas_station.arr.lzhal',0xf11b,0x800);consumer('intro/gas_station.pal.lzhal',0xf147,512)
    sourcecheck('gas-source-base-art',pixels(sg.ljust(0xc000,b'\0'),sa,sp,8),actual,
                sourceDecodedBytes=dict(graphics=len(sg),arrangement=len(sa),palette=len(sp)),
                scope='Actual init_intro II_GAS setup and 236+480 production frames to GS_PH3; source BG1 after palette-fade completion. Dynamic static/color-math frames excluded from independent art comparison.')
    exitrow=next(x for x in result['nativeRuns'][2]['rows'] if x['event']=='QA_EXIT')
    check('gas-full-native-child-cleanup',exitrow['depth']==2 and exitrow['result']==0 and exitrow['flashSeen']==1 and exitrow['tm']==0 and exitrow['ts']==0 and exitrow['spriteYOffset']==0 and exitrow['bgYOffset']==0 and exitrow['bg2Fill']==0,native=exitrow)
    result['sourceIdentities']={x:digest(a.native_source/x)for x in ('src/intro/logo_screen.c','src/intro/gas_station.c','src/intro/init_intro.c','src/entity/callroutine_screen.c','src/entity/callroutine.c','src/snes/ppu_render.c','asm/intro/logo_screen_load.asm','asm/intro/gas_station_load.asm','asm/intro/decomp_itoi_production.asm','asm/intro/decomp_nintendo_presentation.asm')}
    result['preparedCases']=6;result['skippedCases']=0;result['executedAssertions']=len(result['checks'])+len(result['sourceParityChecks'])
    result['nativeExecutionPassed']=all(x['passed']for x in result['checks']);result['sourceParityPassed']=all(x['passed']for x in result['sourceParityChecks']);result['allPassed']=result['nativeExecutionPassed']and result['sourceParityPassed']
    result['limits']=['Prepared real logo parent and gas child complete through timed frames/native fades/scripts; complete boot-to-file-selection intro is outside this tool.',
        'Produced/Presented art uses actual CALLROUTINE dispatch with prepared BG3 registers; natural attract scene actors/parent timeline are not executed.',
        'Independent art comparisons cover centered source 256x224 base layers at full brightness, not all audiovisual timing, dynamic overlays, modern shaders or gutters.',
        'Decoded or uploaded byte differences alone do not prove a missing semantic conversion.']
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({x:result[x]for x in ('nativeExecutionPassed','sourceParityPassed','allPassed','executedAssertions','preparedCases','skippedCases')}))
    raise SystemExit(0 if result['allPassed']or(a.diagnostic and result['nativeExecutionPassed'])else 1)


if __name__=='__main__':
    main()
