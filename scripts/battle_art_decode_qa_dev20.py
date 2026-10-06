# SPDX-License-Identifier: GPL-3.0-or-later
"""Private packed battle-art and PSI frame consumer audit.

This independent strict HAL decoder validates only real selected pack streams.
The native driver links an immutable library. ROM bytes, decoded art and test
checkpoints remain private; the public report contains numeric/hash evidence.
"""
import argparse, collections, hashlib, json, os, re, struct, subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
from build_maternalbound_pack import read_pack

PIN='897d00833f4a08a0a92f106abf631629a6a6a041'
ROOT=Path(__file__).resolve().parents[1]

DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "core/mode_stack.h"
#include "core/memory.h"
#include "game/battle.h"
#include "game/battle_internal.h"
#include "game/battle_bg.h"
#include "game/oval_window.h"
#include "game/game_state.h"
#include "game/overworld.h"
#include "game/window.h"
#include "game/maternalbound.h"
#include "entity/entity.h"
#include "snes/ppu.h"
#include "platform/platform.h"
#include "data/assets.h"
#include "core/decomp.h"
extern int eb_platform_main(int,char**);
static unsigned long long hash(const unsigned char*d,size_t n){unsigned long long v=1469598103934665603ULL;for(size_t i=0;i<n;i++){v^=d[i];v*=1099511628211ULL;}return v;}
static void save(const char*folder,const char*kind,unsigned id,const void*p,size_t n){char path[4096];snprintf(path,sizeof(path),"%s/%s-%u.raw",folder,kind,id);FILE*f=fopen(path,"wb");if(!f)exit(12);fwrite(p,1,n,f);fclose(f);}
int main(int argc,char**argv){
 if(argc!=4)return 2;
 char session[4096];snprintf(session,sizeof(session),"%s/fixture.srm",argv[2]);
 char*boot[]={"art-qa","--assets",argv[1],"--session-dir",argv[2],"--save",session,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot))return 3;
 platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 4;game_set_fast_forward(true);
 entity_system_init();bt.battle_mode_flag=1;
 if(strcmp(argv[3],"backgrounds")==0){
  unsigned count=ASSET_SIZE(ASSET_DATA_BG_DATA_TABLE_BIN)/17;
  for(unsigned id=0;id<count;id++){
   memset(&bt,0,sizeof(bt));bt.battle_mode_flag=1;memset(&ppu,0,sizeof(ppu));memset(ppu.vram,0xa5,sizeof(ppu.vram));
   battle_bg_init();load_battle_bg(id,0,0);
   save(argv[2],"background-vram",id,ppu.vram,sizeof(ppu.vram));save(argv[2],"background-palette",id,loaded_bg_data_layer1.palette2,32);
   printf("QA_BG {\"id\":%u,\"bitdepth\":%u,\"targetLayer\":%u,\"vramFNV\":\"%016llx\",\"paletteFNV\":\"%016llx\",\"bgMode\":%u,\"layerConfig\":%u}\n",id,loaded_bg_data_layer1.bitdepth,loaded_bg_data_layer1.target_layer,hash(ppu.vram,sizeof(ppu.vram)),hash((unsigned char*)loaded_bg_data_layer1.palette2,32),ppu.bgmode,bt.current_layer_config);
  }
 }else if(strcmp(argv[3],"decode")==0){
  for(unsigned family=0;family<2;family++)for(unsigned id=0;id<103;id++){
   int aid=family?ASSET_BATTLE_BGS_ARRANGEMENTS(id):ASSET_BATTLE_BGS_GRAPHICS(id);unsigned char buf[65536+64];memset(buf,0x5a,sizeof(buf));
   size_t n=decomp(ASSET_DATA(aid),ASSET_SIZE(aid),buf+32,65536);unsigned guards=1;for(unsigned i=0;i<32;i++)guards&=buf[i]==0x5a&&buf[65536+32+i]==0x5a;
   printf("QA_DECODE {\"family\":%u,\"id\":%u,\"bytes\":%zu,\"fnv\":\"%016llx\",\"guards\":%u}\n",family,id,n,hash(buf+32,n),guards);
  }
 }else if(strcmp(argv[3],"psi")==0){
  enemy_config_table=(const EnemyData*)ASSET_DATA(ASSET_DATA_ENEMY_CONFIGURATION_TABLE_BIN);
  unsigned count=maternalbound_enabled()?68:34;
  for(unsigned bits=2;bits<=4;bits+=2)for(unsigned id=0;id<count;id++){
   memset(&bt,0,sizeof(bt));bt.battle_mode_flag=1;bt.current_battle_group=7;memset(&psi_animation_state,0,sizeof(psi_animation_state));memset(&ppu,0,sizeof(ppu));
   battle_bg_init();load_enemy_battle_sprites();load_battle_bg(bits==2?0:1,0,0);setup_battle_enemy_sprites();window_system_init();reset_swirl_update_timer();
   unsigned ids[]={69,86,224};
   for(unsigned i=0;i<3;i++){Battler*b=&bt.battlers_table[8+i];battle_init_enemy_stats(b,ids[i]);b->consciousness=1;b->ally_or_enemy=1;b->row=i==2;b->sprite_x=96+i*32;b->sprite_y=i==2?120:144;b->vram_sprite_index=find_battle_sprite_for_enemy(ids[i]);}
   bt.current_target=battler_to_offset(&bt.battlers_table[8]);bt.current_attacker=0;
   show_psi_animation(id);unsigned total=psi_animation_state.total_frames,hold=psi_animation_state.frame_hold_frames,ticks=0,seen=0,cleared=0,bounds=1;
   unsigned char before[65536];memcpy(before,ppu.vram,sizeof(before));
   ModeState wait={0};wait.battle_wait.kind=BW_PSI_ANIM;
   printf("QA_PSI_START {\"id\":%u,\"bitdepth\":%u,\"frames\":%u,\"hold\":%u,\"paletteBase\":%u,\"gfxFNV\":\"%016llx\",\"targets\":[%u,%u,%u,%u],\"offset\":[%d,%d]}\n",id,bits,total,hold,psi_animation_state.displayed_palette,hash(ppu.vram,bits==2?4096:8192),bt.psi_animation_enemy_targets[0],bt.psi_animation_enemy_targets[1],bt.psi_animation_enemy_targets[2],bt.psi_animation_enemy_targets[3],bt.psi_animation_x_offset,bt.psi_animation_y_offset);
   while(++ticks<3000){
    unsigned prev=psi_animation_state.frame_data;StepResult step=mode_step_battle_wait(&wait);
    if(step.kind==STEP_POP)break;
    if(step.kind!=STEP_CONTINUE)return 16;
    if(psi_animation_state.frame_data!=prev){
     unsigned char low[1024];unsigned high=1;for(unsigned i=0;i<1024;i++){low[i]=ppu.vram[0xb000+i*2];high&=ppu.vram[0xb001+i*2]==0x30;}
     printf("QA_PSI_FRAME {\"id\":%u,\"bitdepth\":%u,\"frame\":%u,\"tick\":%u,\"fnv\":\"%016llx\",\"highBytes\":%u,\"palette\":[%u,%u,%u,%u],\"oamCount\":%u}\n",id,bits,prev,ticks,hash(low,1024),high,ert.palettes[psi_animation_state.displayed_palette],ert.palettes[psi_animation_state.displayed_palette+1],ert.palettes[psi_animation_state.displayed_palette+2],ert.palettes[psi_animation_state.displayed_palette+3],ert.oam_write_index);seen++;
    }
    bounds&=memcmp(before+8192,ppu.vram+8192,0xb000-8192)==0&&memcmp(before+0xb800,ppu.vram+0xb800,65536-0xb800)==0;
    if(!psi_animation_state.time_until_next_frame){cleared=1;for(unsigned i=0;i<2048;i++)cleared&=ppu.vram[0xb000+i]==0;}
    core.frame_counter++;core.nmi_count++;
   }
   printf("QA_PSI_END {\"id\":%u,\"bitdepth\":%u,\"ticks\":%u,\"frames\":%u,\"remaining\":%u,\"inactive\":%u,\"cleared\":%u,\"vramBounds\":%u,\"oamCount\":%u,\"bgPaletteRestored\":%u}\n",id,bits,ticks,seen,psi_animation_state.total_frames,!is_psi_animation_active(),cleared,bounds,ert.oam_write_index,memcmp(loaded_bg_data_layer1.palette,loaded_bg_data_layer1.palette2,32)==0);
   if(ticks>=3000)return 17;
  }
 }else return 5;
 return 0;
}
'''

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def h(data):return hashlib.sha256(data).hexdigest()
def fnv(data):
    value=1469598103934665603
    for byte in data:value=((value^byte)*1099511628211)&((1<<64)-1)
    return f'{value:016x}'

def strict_decode(data, native_container=False):
    """DECOMP grammar with an explicit native-container backwards-zero clamp.

    Repacked streams may encode one repeated byte after reverse-copy reaches
    position zero. Native C/ebtools define that bounded adaptation; source ROM
    streams are decoded separately without the adaptation.
    """
    out=bytearray();cursor=0;commands=collections.Counter()
    def read():
        nonlocal cursor
        if cursor>=len(data):raise ValueError('Truncated HAL input')
        value=data[cursor];cursor+=1;return value
    while True:
        command=read()
        if command==255:break
        if command>=224:op=(command>>2)&7;length=((command&3)<<8|read())+1
        else:op=command>>5;length=(command&31)+1
        commands[op]+=1
        if op==0:out.extend(read()for _ in range(length))
        elif op==1:out.extend(bytes([read()])*length)
        elif op==2:out.extend(bytes((read(),read()))*length)
        elif op==3:
            value=read();out.extend((value+i)&255 for i in range(length))
        elif op in (4,5,6):
            ref=read()<<8|read()
            for _ in range(length):
                if not 0<=ref<len(out):raise ValueError(f'Invalid HAL backreference {ref}/{len(out)}')
                value=out[ref]
                if op==5:value=int(f'{value:08b}'[::-1],2)
                out.append(value)
                if op==6 and ref==0 and native_container:
                    commands['backwardZeroClampReads']+=1
                else:ref+=-1 if op==6 else 1
        else:raise ValueError('Unsupported HAL command7 in actual stream')
        if len(out)>1024*1024:raise ValueError('Unexpected HAL output size')
    return bytes(out),dict(commands),cursor

def source_entries(native):
    text=(native/'earthbound.yml').read_text()
    rows={}
    for block in text.split('- subdir: ')[1:]:
        match=re.match(r"([^\n]+)\n\s+name: ['\"]?([^'\"\n]+)['\"]?\n\s+offset: (0x[\da-fA-F]+)\n\s+size: (\d+)\n\s+extension: (\w+)\n\s+compressed: (true|false)",block)
        if match:
            folder,name,offset,size,extension,compressed=match.groups()
            rows[f'{folder}/{name}.{extension}']=(int(offset,16),int(size),compressed=='true')
    return rows

def psi_parts(assets,redux):
    cfg=assets['data/psi_anim_cfg.bin'];count=68 if redux else 34
    if redux:
        at=count*12
        assert struct.unpack_from('<8sHHI',cfg,at)==(b'MRPSIX01',68,10,146)
        items=[]
        for i in range(146):
            offset,length=struct.unpack_from('<II',cfg,at+16+i*8)
            assert offset>=at+16+146*8 and offset+length<=len(cfg)
            items.append(cfg[offset:offset+length])
        return cfg[:count*12],items[:10],items[10:78],items[78:]
    def family(folder):
        pairs=sorted((int(k.split('/')[-1].split('.')[0]),v)for k,v in assets.items()if k.startswith('psianims/'+folder+'/'))
        assert [i for i,_ in pairs]==list(range(len(pairs)))
        return [v for _,v in pairs]
    return cfg,family('gfx'),family('arrangements'),family('palettes')

def inspect(assets,redux,rom,entries,private):
    profile='Redux'if redux else'Original';private.mkdir(parents=True)
    checks=[];streams=[];decoded={}
    def check(name,passed,**details):checks.append(dict(check=name,passed=bool(passed),**details))
    families=('battle_bgs/graphics/','battle_bgs/arrangements/')
    bgcfg=assets['data/bg_data_table.bin'];active_graphics=max(bgcfg[i]for i in range(0,len(bgcfg),17))+1
    palette_widths={}
    for i in range(0,len(bgcfg),17):palette_widths[bgcfg[i+1]]=max(palette_widths.get(bgcfg[i+1],0),1<<bgcfg[i+2])
    def pointer_table(at):
        assert rom[at]==0xA9 and rom[at+5]==0xA9
        address=int.from_bytes(rom[at+1:at+3],'little')|int.from_bytes(rom[at+6:at+8],'little')<<16
        return address-0xC00000 if address>=0xC00000 else address
    graphics_table=pointer_table(0x2D1BA)if redux else None
    arrangements_table=pointer_table(0x2D2C1)if redux else None
    palettes_table=pointer_table(0x2D3BB)if redux else None
    for name,data in assets.items():
        if not name.startswith(families):continue
        raw,commands,consumed=strict_decode(data,True);decoded[name]=raw
        key=name.removesuffix('.lzhal');index=int(name.split('/')[-1].split('.')[0]);offset=None
        if not redux:offset=entries[key][0]
        elif index<active_graphics:
            table=graphics_table if '/graphics/'in name else arrangements_table
            address=struct.unpack_from('<I',rom,table+index*4)[0]
            offset=address-0xC00000 if address>=0xC00000 else address
        if offset is not None:
            original,_,_=strict_decode(rom[offset:])
            check(profile.lower()+'-source-decode-'+name,raw==original,sourceOffset=offset)
        streams.append(dict(asset=name,compressedSha256=h(data),decodedSha256=h(raw),decodedFNV=fnv(raw),decodedBytes=len(raw),commands=commands,consumedBytes=consumed))
        (private/(name.replace('/','_')+'.raw')).write_bytes(raw)
    records=[];cfg=assets['data/bg_data_table.bin'];scroll=assets['data/bg_scrolling_table.bin'];dist=assets['data/bg_distortion_table.bin']
    for index in range(len(cfg)//17):
        r=cfg[index*17:(index+1)*17];gfx,pi,bpp=r[:3]
        graphics=decoded[f'battle_bgs/graphics/{gfx}.gfx.lzhal'];arr=decoded[f'battle_bgs/arrangements/{gfx}.arr.lzhal'];pal=assets[f'battle_bgs/palettes/{pi}.pal']
        words=struct.unpack('<'+str(len(arr)//2)+'H',arr);tilemax=max(x&1023 for x in words)
        records.append(dict(index=index,graphics=gfx,palette=pi,bitdepth=bpp,graphicsBytes=len(graphics),arrangementBytes=len(arr),paletteBytes=len(pal),maxTile=tilemax,tileCount=len(graphics)//(bpp*8),scrolling=list(r[9:13]),distortion=list(r[13:17])))
        check(f'background-record-{index}',bpp in(2,4)and len(arr)==2048 and len(pal)==palette_widths[pi]*2 and len(graphics)%(bpp*8)==0 and tilemax<len(graphics)//(bpp*8)and all(x*10+10<=len(scroll)for x in r[9:13])and all(x*17+17<=len(dist)for x in r[13:17]),record=records[-1])
        source_palette_offset=entries[f'battle_bgs/palettes/{pi}.pal'][0]if not redux else struct.unpack_from('<I',rom,palettes_table+pi*4)[0]
        if source_palette_offset>=0xC00000:source_palette_offset-=0xC00000
        source_palette=rom[source_palette_offset:source_palette_offset+palette_widths[pi]*2]
        source_gfx_offset=entries[f'battle_bgs/graphics/{gfx}.gfx'][0]if not redux else struct.unpack_from('<I',rom,graphics_table+gfx*4)[0]
        if source_gfx_offset>=0xC00000:source_gfx_offset-=0xC00000
        source_gfx,_,_=strict_decode(rom[source_gfx_offset:]);colors=set()
        for tile in {x&1023 for x in words}:
            base=tile*bpp*8
            for y in range(8):
                for x in range(8):colors.add(sum(((source_gfx[base+y*2+(p%2)+(p//2)*16]>>(7-x))&1)<<p for p in range(bpp)))
        records[-1]['usedPixelColorIndices']=sorted(colors)
        check(f'background-palette-source-{index}',pal==source_palette,palette=pi,sourceOffset=source_palette_offset,expectedBytes=len(source_palette),actualBytes=len(pal),usedPixelColorIndices=sorted(colors))
        (private/f'source-bg-palette-{index}.raw').write_bytes(source_palette[:(1<<bpp)*2])
    pcfg,gfxs,arrs,pals=psi_parts(assets,redux);animations=[];gfxwords=(0x2E19,0x4599,0x38AA,0x5FB1,0x3141,0x4C3F,0x3FDE,0x548C,0x5A9D,0x62A1)if redux else(0xAC25,0xB613,0xDB27,0xE31D)
    for i,data in enumerate(gfxs):
        raw,commands,consumed=strict_decode(data,True);source,_,_=strict_decode(rom[0xC0000+gfxwords[i]:])
        check(f'psi-graphics-source-{i}',0<len(raw)<=4096 and len(raw)%16==0 and raw==source,decodedBytes=len(raw),commands=commands)
        (private/f'psi-gfx-{i}.raw').write_bytes(raw)
        streams.append(dict(asset=f'psi-graphics-{i}',compressedSha256=h(data),decodedSha256=h(raw),decodedFNV=fnv(raw),decodedBytes=len(raw),commands=commands,consumedBytes=consumed))
    for i,blob in enumerate(arrs):
        r=pcfg[i*12:(i+1)*12];word,hold,period,lo,hi,frames,target,start,duration,rgb=struct.unpack('<H8BH',r)
        gfx=word if redux else gfxwords.index(word)
        per,total,bundles=struct.unpack_from('<BBH',blob);offsets=struct.unpack_from(f'<{bundles+1}H',blob,4);begin=4+(bundles+1)*2
        assert per==8 and total>=frames and bundles==(total+7)//8 and offsets[0]==0 and offsets[-1]==len(blob)-begin
        raw=bytearray();bundle_info=[]
        for j in range(bundles):
            part=blob[begin+offsets[j]:begin+offsets[j+1]];out,commands,consumed=strict_decode(part,True)
            check(f'psi-{i}-bundle-{j}',len(out)==min(8,total-j*8)*1024 and consumed==len(part),decodedBytes=len(out),commands=commands)
            raw.extend(out);bundle_info.append(dict(index=j,compressedBytes=len(part),decodedBytes=len(out),decodedSha256=h(out),commands=commands))
        if redux:
            sourcecfg=rom[0x320000+i*12:0x320000+(i+1)*12];normalized=bytearray(sourcecfg);struct.pack_into('<H',normalized,0,gfxwords.index(struct.unpack_from('<H',sourcecfg)[0]))
            pointer=int.from_bytes(rom[0x320400+i*4:0x320404+i*4],'little');sourcearr,_,_=strict_decode(rom[pointer-0xC00000:]);sourcepal=rom[0x320600+i*8:0x320608+i*8]
        else:
            normalized=rom[entries['data/psi_anim_cfg.bin'][0]+i*12:entries['data/psi_anim_cfg.bin'][0]+(i+1)*12]
            sourcearr,_,_=strict_decode(rom[entries[f'psianims/arrangements/{i}.arr'][0]:]);sourcepal=rom[entries[f'psianims/palettes/{i:02d}.pal'][0]:entries[f'psianims/palettes/{i:02d}.pal'][0]+8]
        gfxraw=(private/f'psi-gfx-{gfx}.raw').read_bytes()
        check(f'psi-{i}-source',bytes(normalized)==r and sourcearr==raw and sourcepal==pals[i]and hold>0 and lo<=hi<4 and target<=3 and max(raw[:frames*1024])<len(gfxraw)//16,frames=frames,gfx=gfx,target=target,palettePeriod=period,maxDisplayedTile=max(raw[:frames*1024]),graphicsTiles=len(gfxraw)//16)
        (private/f'psi-frames-{i}.raw').write_bytes(raw);(private/f'psi-pal-{i}.raw').write_bytes(pals[i])
        animations.append(dict(index=i,gfx=gfx,hold=hold,period=period,lower=lo,upper=hi,frames=frames,packedFrames=total,unusedPackedTailFrames=total-frames,target=target,start=start,duration=duration,rgb=rgb,frameSha256=h(raw),frameFNV=[fnv(raw[x:x+1024])for x in range(0,len(raw),1024)],palette=list(struct.unpack('<4H',pals[i])),bundles=bundle_info))
    return dict(profile=profile,checks=checks,streams=streams,backgroundRecords=records,psiAnimations=animations,allPassed=all(c['passed']for c in checks))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--assets',type=Path,required=True);p.add_argument('--redux',action='store_true');p.add_argument('--rom',type=Path,required=True)
    p.add_argument('--scratch',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--native-source',type=Path,default=ROOT/'native-source');p.add_argument('--structural-only',action='store_true')
    p.add_argument('--build',type=Path,default=ROOT/'_BuildScratch/audit-dev16-v9-build/companion');p.add_argument('--runtime',type=Path,default=ROOT/'_BuildScratch/audit-dev16-v9-runtime')
    a=p.parse_args();a.scratch=a.scratch.resolve()
    if a.scratch.exists():raise ValueError('Fresh private scratch required')
    a.scratch.mkdir(parents=True)
    _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h')
    result=inspect(assets,a.redux,a.rom.read_bytes(),source_entries(a.native_source),a.scratch/'decoded')
    source_files=('src/core/decomp.c','src/game/battle_bg.c','src/game/battle_psi.c','src/game/battle_wait.c','src/game/battle_ui.c','asm/system/decomp.asm','asm/battle/show_psi_animation.asm','earthbound.yml')
    result.update(toolSha256=digest(__file__),packSha256=digest(a.assets),romSha256=digest(a.rom),pinnedReduxCommit=PIN if a.redux else None,runtimeExecuted=False,fullVisualParityVerified=False,sourceIdentities={name:digest(a.native_source/name)for name in source_files if (a.native_source/name).exists()},skippedCases=0,ownerWrites=False)
    if not a.structural_only:
        helper.DRIVER=DRIVER
        exe,provenance=helper.private_build(a);result['nativeProvenance']=provenance;result['runtimeExecuted']=True
        env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy');result['nativeRuns']=[]
        for kind in ('decode','backgrounds','psi'):
            folder=a.scratch/kind;folder.mkdir()
            cp=subprocess.run([str(exe),str(a.assets.resolve()),str(folder),kind],env=env,capture_output=True,timeout=90)
            (folder/'stdout.log').write_bytes(cp.stdout);(folder/'stderr.log').write_bytes(cp.stderr)
            rows=[dict(event=line.split(' ',1)[0],**json.loads(line.split(' ',1)[1]))for line in cp.stdout.decode(errors='replace').splitlines()if line.startswith(('QA_BG ','QA_DECODE ','QA_PSI_'))]
            result['nativeRuns'].append(dict(kind=kind,exitCode=cp.returncode,rows=rows,stdoutSha256=digest(folder/'stdout.log'),stderrSha256=digest(folder/'stderr.log')))
            if cp.returncode or (kind!='psi'and len(rows)!=(206 if kind=='decode' else 327)):raise RuntimeError('Native rows incomplete: '+str(len(rows))+' '+cp.stderr.decode(errors='replace'))
        for row in result['nativeRuns'][0]['rows']:
            name=f"battle_bgs/{'arrangements'if row['family']else'graphics'}/{row['id']}.{'arr'if row['family']else'gfx'}.lzhal"
            expected=next(x for x in result['streams']if x['asset']==name)
            result['checks'].append(dict(check='native-decode-'+name,passed=row['guards']==1 and row['fnv']==expected['decodedFNV']and row['bytes']==expected['decodedBytes'],native=row))
        source=a.rom.read_bytes();cfg=assets['data/bg_data_table.bin']
        at=0x2D1BA;table=(int.from_bytes(source[at+1:at+3],'little')|int.from_bytes(source[at+6:at+8],'little')<<16)-0xC00000 if a.redux else None
        for row in result['nativeRuns'][1]['rows']:
            i=row['id'];record=result['backgroundRecords'][i];gfx=record['graphics'];name=f'battle_bgs/graphics/{gfx}.gfx'
            if a.redux:
                address=struct.unpack_from('<I',source,table+gfx*4)[0];offset=address-0xC00000 if address>=0xC00000 else address
            else:offset=source_entries(a.native_source)[name][0]
            raw,_,_=strict_decode(source[offset:]);actual=(a.scratch/'backgrounds'/f'background-vram-{i}.raw').read_bytes()[0x2000:0x2000+min(len(raw),8192)]
            result['checks'].append(dict(check=f'native-background-source-graphics-{i}',passed=actual==raw[:8192],graphics=gfx,comparedBytes=len(actual),expectedSha256=h(raw[:8192]),actualSha256=h(actual)))
            palexpected=(a.scratch/'decoded'/f'source-bg-palette-{i}.raw').read_bytes();palactual=(a.scratch/'backgrounds'/f'background-palette-{i}.raw').read_bytes()[:len(palexpected)]
            result['checks'].append(dict(check=f'native-background-source-palette-{i}',passed=palactual==palexpected,palette=record['palette'],comparedBytes=len(palexpected),expectedSha256=h(palexpected),actualSha256=h(palactual),usedPixelColorIndices=record['usedPixelColorIndices']))
        result['allPassed']=all(c['passed']for c in result['checks'])
        for bits in (2,4):
            for anim in result['psiAnimations']:
                rows=[x for x in result['nativeRuns'][2]['rows']if x['id']==anim['index']and x['bitdepth']==bits];starts=[x for x in rows if x['event']=='QA_PSI_START'];ends=[x for x in rows if x['event']=='QA_PSI_END'];frames=[x for x in rows if x['event']=='QA_PSI_FRAME']
                passed=len(starts)==len(ends)==1 and len(frames)==anim['frames']
                if passed:
                    gfx=(a.scratch/'decoded'/f"psi-gfx-{anim['gfx']}.raw").read_bytes().ljust(4096,b'\0')
                    if bits==4:gfx=b''.join(gfx[i:i+16]+bytes(16)for i in range(0,4096,16))
                    start=starts[0];passed&=start['frames']==anim['frames']and start['hold']==anim['hold']and start['paletteBase']==(48 if bits==2 else 64)and start['gfxFNV']==fnv(gfx)
                    end=ends[0];passed&=end['ticks']==anim['frames']*anim['hold']+2 and end['remaining']==0 and end['inactive']==end['cleared']==end['vramBounds']==end['bgPaletteRestored']==1 and end['oamCount']<=128
                    for i,x in enumerate(frames):
                        palette=list(anim['palette']);lo,hi=anim['lower'],anim['upper'];cycle=hi-lo+1
                        rotation=((x['tick']-1)//anim['period'])%cycle if anim['period'] else 0
                        for j in range(cycle):palette[lo+j]=anim['palette'][lo+(j-rotation)%cycle]
                        passed&=x['frame']==i and x['fnv']==anim['frameFNV'][i]and x['highBytes']==1 and x['oamCount']<=128 and x['palette']==palette
                result['checks'].append(dict(check=f"native-psi-{bits}bpp-{anim['index']}",passed=bool(passed),start=starts,end=ends,observedFrames=len(frames)))
        result['allPassed']=all(c['passed']for c in result['checks'])
        result['runtimeIdentities']={name:digest(a.runtime/name)for name in ('player.exe','observer.exe')}
    result['executedAssertions']=len(result['checks'])
    result['nativeExecutedCases']=0 if a.structural_only else 206+327+len(result['psiAnimations'])*2
    result['nativeRenderedPsiFrames']=0 if a.structural_only else sum(x['frames']for x in result['psiAnimations'])*2
    result['coverageLimits']=[
        'All 327 packed background records execute load_battle_bg independently; this does not rerun every configured two-layer natural encounter or full special Giygas render path.',
        'Every packed PSI effect plays both 2bpp and 4bpp through show_psi_animation and actual BW_PSI_ANIM steps with prepared real enemy sprite data; this does not prove every ability-to-animation routing or natural battle action.',
        'Decoded source bytes, uploaded graphics and palettes, every played arrangement/palette frame, bounded OAM count, protected VRAM and timer/cleanup state are asserted; no full visual parity or heard audio claim.',
        'Repacked HAL backwards-copy at position zero uses the documented native clamp; original ROM streams are independently decoded without that adaptation.',
        'Original animation 20 retains ten source-backed packed tail frames unused by its configured playback length; unused Redux background graphics slots retain explicit empty streams.',
    ]
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(profile=result['profile'],checks=len(result['checks']),passed=result['allPassed'],streams=len(result['streams']),backgrounds=len(result['backgroundRecords']),animations=len(result['psiAnimations']))))
    raise SystemExit(0 if result['allPassed']else 1)

if __name__=='__main__':main()
