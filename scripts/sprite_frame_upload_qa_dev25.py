# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare source sprite frames, normalized assets, and actual prepared uploads."""
import argparse
import hashlib
import json
import os
import struct
import subprocess
from pathlib import Path
import yaml

import battle_action_catalog_qa as helper
from build_maternalbound_pack import read_pack
from maternalbound_graphics import asm_pointer, snes_offset

ROOT=Path(__file__).resolve().parents[1]
DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "entity/entity.h"
#include "entity/sprite.h"
#include "game/maternalbound.h"
#include "snes/ppu.h"
#include "platform/platform.h"
extern int eb_platform_main(int argc,char **argv);
int main(int argc,char **argv){
 if(argc!=5)return2;
 char save[4096];snprintf(save,sizeof(save),"%s/private.srm",argv[2]);
 char *boot[]={"sprite-frame-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot))return3;
 if(maternalbound_enabled()!=(strcmp(argv[4],"Redux")==0))return4;
 load_sprite_data();printf("QA_GROUPS %u\n",sprite_grouping_ptr_count);
 FILE*f=fopen(argv[3],"rb");if(!f)return4;
 unsigned id,group,dir,frame,eight,surface,base;
 while(fscanf(f,"%u%u%u%u%u%u%u",&id,&group,&dir,&frame,&eight,&surface,&base)==7){
  uint32_t off=0;uint8_t size=load_sprite_group_properties(group,&off);
  const uint8_t*sg=sprite_grouping_data_buf+off;
  memset(&entities,0,sizeof(entities));
  entities.tile_heights[0]=sg[0];entities.byte_widths[0]=(uint16_t)sg[1]*2;
  entities.graphics_ptr_lo[0]=off+9;entities.graphics_sprite_bank[0]=sg[8];
  entities.vram_address[0]=base;entities.directions[0]=dir;entities.animation_frame[0]=frame;
  entities.use_8dir_sprites[0]=eight;entities.surface_flags[0]=surface;
  entities.current_displayed_sprites[0]=0xa55a;
  memset(ppu.vram,0xa5,sizeof(ppu.vram));unsigned result=render_entity_sprite(0);
  unsigned long long h=1469598103934665603ULL;int guard=1;
  for(unsigned n=0;n<sizeof(ppu.vram);n++)if(n<0x8000||n>=0xa000){if(ppu.vram[n]!=0xa5)guard=0;}
  for(unsigned n=0x8000;n<0xa000;n++)h=(h^ppu.vram[n])*1099511628211ULL;
  printf("QA_FRAME {\"id\":%u,\"return\":%u,\"size\":%u,\"width\":%u,\"height\":%u,\"displayFlags\":%u,\"guard\":%d,\"hash\":\"%016llx\"}\n",id,result,size,new_sprite_tile_width,new_sprite_tile_height,entities.current_displayed_sprites[0]&3,guard,h);
 }
 fclose(f);return0;
}
'''.replace('return2','return 2').replace('return3','return 3').replace('return4','return 4').replace('return0','return 0')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def h(data):return hashlib.sha256(data).hexdigest()
def fnv(data):
    value=1469598103934665603
    for byte in data:value=((value^byte)*1099511628211)&0xffffffffffffffff
    return f'{value:016x}'

def source_frame(rom,record,frame,mask):
    ptr=struct.unpack_from('<H',rom,record+9+frame*2)[0]
    width,height=rom[record+1]*2,rom[record]
    address=(rom[record+8]<<16)|(ptr&mask)
    start=snes_offset(address,len(rom));length=width*height
    if start+length>len(rom):raise ValueError('Source sprite outside ROM')
    return ptr,rom[start:start+length],width,height

def expected_upload(source,pointer,width,height,surface,base):
    dest=base;out=bytearray(b'\xa5'*8192);copied=False
    blank=0 if pointer&2 else (2 if surface==12 else 1 if surface==8 else 0)
    blank=min(blank,height)
    for row in range(height):
        data=bytes(width)if row<blank else source[(row-blank)*width:(row-blank+1)*width]
        copied|=row>=blank
        last=(dest+width//2-1)&65535
        if (last^dest)&256:
            boundary=(dest+256)&0xff00;first=(boundary-dest)*2
            writes=[(dest,data[:first]),(boundary+256,data[first:])]
        else:writes=[(dest,data)]
        for address,content in writes:
            at=address*2-0x8000
            if not 0<=at<=8192-len(content):raise ValueError('Prepared source write outside bounded OBJ region')
            out[at:at+len(content)]=content
        if not dest&256:dest=(dest+256)&65535
        else:
            nxt=(dest+((width+32)&0xffc0)//2)&65535
            dest=nxt if (nxt^dest)&256 else(nxt-256)&65535
    return dict(hash=fnv(out),value=dest,displayFlags=pointer&3 if copied else 0xa55a&3)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native-source','build','runtime','original-assets','redux-assets','original-rom','redux-rom','project','scratch','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.scratch=a.scratch.resolve()
    if a.scratch.exists()or not a.scratch.is_relative_to(ROOT/'_BuildScratch'):raise ValueError('Fresh private scratch required')
    a.scratch.mkdir(parents=True);helper.DRIVER=DRIVER;exe,production=helper.private_build(a)
    yamlfile=a.project/'sprite_groups.yml';metadata=yaml.safe_load(yamlfile.read_text(encoding='utf-8'))
    result=[];failures=[];assertions=0;inventories=[]
    def check(name,ok,details=None):
        nonlocal assertions
        assertions+=1
        if not ok:failures.append(dict(check=name,details=details))
    for profile,pack,rompath in [('Original',a.original_assets,a.original_rom),('Redux',a.redux_assets,a.redux_rom)]:
        rom=rompath.read_bytes();_,_,assets=read_pack(pack,a.native_source/'src/data/runtime_generated/asset_ids.h')
        table=assets['overworld_sprites/sprite_grouping_ptr_table.bin'];native=assets['overworld_sprites/sprite_grouping_data.bin'];count=len(table)//4
        srcbase=snes_offset(asm_pointer(rom,0x1DF9),len(rom))
        srcptr=[snes_offset(struct.unpack_from('<I',rom,srcbase+4*i)[0],len(rom))for i in range(count)]
        off=[(struct.unpack_from('<I',table,4*i)[0]&65535)-0x1a7f for i in range(count)]
        container=assets['overworld_sprites/banks/11.bin'];banks=[]
        if container[:8]==b'MRSPBN01':
            n,stride=struct.unpack_from('<II',container,8)
            banks=[container[16+i*stride:16+(i+1)*stride]for i in range(n)]
        else:banks=[assets[f'overworld_sprites/banks/{i}.bin']for i in range(11,16)]
        for palette in range(8):
            source_palette=rom[0x30000+palette*32:0x30000+(palette+1)*32]
            packed_palette=assets[f'overworld_sprites/palettes/{palette}.pal']
            check(f'{profile}palette{palette} source colors',source_palette==packed_palette,
                  dict(sourceSha256=h(source_palette),nativeSha256=h(packed_palette)))
        folder=a.scratch/profile.lower();folder.mkdir();cases=[];inventory=[];frame_count=0
        for group in range(count):
            n=((off[group+1]if group+1<count else len(native))-off[group]-9)//2
            if profile=='Redux':length=metadata[group]['Length']
            else:
                if n not in (8,9,16)and group!=0:raise ValueError('Unexpected Original source frame span')
                length=n if n in (8,9,16)else 0
            sg=native[off[group]:off[group]+9];source=rom[srcptr[group]:srcptr[group]+9]
            check(f'{profile}group{group} normalized header',sg[:8]==source[:8],dict(source=h(source[:8]),native=h(sg[:8])))
            check(f'{profile}group{group} frame capacity',length<=max(0,n),dict(activeFrames=length,storedSlots=n))
            inventory.append(dict(group=group,sourceFrames=length,storedSlots=max(0,n),width=source[1]*2,height=source[0],zeroLengthPlaceholder=length==0))
            for frame in range(length):
                ptr,gfx,width,height=source_frame(rom,srcptr[group],frame,0xfffc)
                packedptr=struct.unpack_from('<H',native,off[group]+9+frame*2)[0];bank=(sg[8]&63)-17
                packed=banks[bank][packedptr&0xfffc:(packedptr&0xfffc)+width*height]
                check(f'{profile}group{group}frame{frame} normalized source pixels',packed==gfx and packedptr&3==ptr&3,
                      dict(sourceSha256=h(gfx),nativeSha256=h(packed),sourceFlags=ptr&3,nativeFlags=packedptr&3))
                frame_count+=1
                modes=[(0,0x4000)]
                if frame==0:modes.extend([(8,0x40f0),(12,0x41f0)])
                # Standard 4-direction consumes frames0..7; 16-frame groups' diagonal tail uses8-direction.
                eight=int(frame>=8);direction=([0,2,4,6,1,3,5,7]if eight else[0,2,4,6])[frame//2]
                mask=0xfffe if eight else 0xfff0
                liveptr,livegfx,_,_=source_frame(rom,srcptr[group],frame,mask)
                for surface,base in modes:
                    cases.append(dict(group=group,frame=frame,direction=direction,eight=eight,surface=surface,base=base,
                        width=width,height=height,size=source[2],expected=expected_upload(livegfx,liveptr,width,height,surface,base)))
        casesfile=folder/'cases.tsv';casesfile.write_text(''.join(f'{i} {c["group"]} {c["direction"]} {c["frame"]%2} {c["eight"]} {c["surface"]} {c["base"]}\n'for i,c in enumerate(cases)))
        run=subprocess.run([str(exe.resolve()),str(pack.resolve()),str(folder.resolve()),str(casesfile.resolve()),profile],cwd=folder,
            env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=120)
        log=run.stdout+run.stderr;(folder/'native.log').write_bytes(log)
        rows=[json.loads(s.split(' ',1)[1])for s in run.stdout.decode(errors='replace').splitlines()if s.startswith('QA_FRAME ')]
        loaded=[int(s.split(' ',1)[1])for s in run.stdout.decode(errors='replace').splitlines()if s.startswith('QA_GROUPS ')]
        check(profile+' process',run.returncode==0,run.returncode)
        check(profile+' actual loaded grouping cardinality',loaded==[count],loaded)
        check(profile+' complete actual frame corpus',len(rows)==len(cases)and[r['id']for r in rows]==list(range(len(cases))),len(rows))
        for index,(case,row)in enumerate(zip(cases,rows)):
            expected=case['expected'];check(f'{profile}case{index} source VRAM',row['hash']==expected['hash'],dict(group=case['group'],frame=case['frame'],surface=case['surface'],expected=expected['hash'],actual=row['hash']))
            check(f'{profile}case{index} source return/flags',row['return']==expected['value']and row['displayFlags']==expected['displayFlags'],dict(expected=expected,actual=row))
            check(f'{profile}case{index} untouched guard/geometry',row['guard']==1 and row['width']==case['width']//32 and row['height']==case['height']and row['size']==case['size'],row)
        inventories.append(dict(profile=profile,groups=count,frames=frame_count,preparedUploads=len(cases),zeroLengthGroups=[r['group']for r in inventory if r['zeroLengthPlaceholder']],groupsInventory=inventory))
        result.append(dict(profile=profile,packSha256=sha(pack),romSha256=sha(rompath),nativeLogSha256=h(log),executedUploads=len(rows)))
    report=dict(format='source-sprite-frame-native-upload-dev25-v1',toolSha256=sha(__file__),allPassed=not failures,
        executedAssertions=assertions,skippedCases=0,failures=failures,production=production,profiles=result,inventory=inventories,
        pinnedReduxCommit=helper.PIN,projectMetadataSha256=sha(yamlfile),runtimeSha256={name:sha(a.runtime/name)for name in('player.exe','observer.exe')},sourceIdentities={str(path.relative_to(a.native_source)):sha(path)for path in[
            a.native_source/'src/entity/sprite.c',a.native_source/'src/entity/sprite.h',
            a.native_source/'asm/overworld/render_entity_sprite.asm',a.native_source/'asm/overworld/entity/render_entity_sprite_8dir.asm',
            a.native_source/'asm/system/dma/prepare_vram_copy_row_safe.asm']if path.exists()},
        ownerWrites=False,sharedSourceModified=False,
        limits=['Prepared scalar entity geometry and frame selection execute the unchanged production renderer. Natural actor allocation, OAM layout and story caller selection are separate coverage.',
            'Every Redux project-declared frame is compared; Original frame counts follow its contiguous8/9/16-slot records, excluding zero-length placeholder0.',
            'Source contracts are independently interpreted from retained assembly; this run does not execute the SNES CPU or certify audiovisual parity.',
            'Eight packed sprite palettes per profile are byte-checked against source. Their live palette/DSP/rendered color consumers are not executed here.',
            'Dry every frame plus shallow/deep first frame per nonempty group cover source graphics and water/boundary classes, not every cartesian surface/frame combination.',
            'VRAM FNV64 and untouched sentinel guards validate the prepared8192-byte OBJ region; packed/source frame bytes also receive SHA256 and direct equality.',
            'Public evidence includes numeric results and hashes only; no game pixels, ROM, saves or bytecode.',
            'Actual execution uses the identified player production library; observer executable hash records paired provenance only.'])
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(allPassed=report['allPassed'],executedAssertions=assertions,profiles=result,failures=failures[:8])))
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
