# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare native position arithmetic/input with untouched clean USA SNES code.

Requires explicit local ROM, original source, ca65/ld65, native compiler and
mesen-agent paths. Reassembles the original source ONLY to identify byte-equal
original routines and ABI/global addresses. Those original routines execute
from the unchanged owner ROM in isolated emulator memory, with an own caller.
Only fresh scratch files are written. No assets, ROM code, or commercial data
are embedded in this public runner; generated original blobs stay private.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

from check_jev_observer_parity import local_scratch
from snes_movement_helpers_oracle import sha, US_SHA1


ROUTINES = (
    ('MULT16', 'system/math/mult16.asm', 'far'),
    ('MULT32', 'system/math/mult32.asm', 'far'),
    ('VELOCITY_STORE', 'overworld/velocity_store.asm', 'far'),
    ('MAP_INPUT_TO_DIRECTION', 'overworld/map_input_to_direction.asm', 'far'),
    ('ADJUST_POSITION_HORIZONTAL', 'overworld/adjust_position_horizontal.asm', 'near'),
    ('ADJUST_POSITION_VERTICAL', 'overworld/adjust_position_vertical.asm', 'near'),
)


def run(command, out, timeout=30):
    result = subprocess.run(list(map(str, command)), capture_output=True, timeout=timeout)
    out.write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f'{out.name}: return {result.returncode}: ' + result.stderr.decode(errors='replace'))
    return result


def labels(path):
    return {name: int(address, 16) for address, name in
            re.findall(r'^al ([0-9A-Fa-f]+) \.?(\w+)$', path.read_text(encoding='utf-8'), re.M)}


def find_unique(rom, blob, name):
    index = rom.find(blob)
    if index < 0 or rom.find(blob, index + 1) >= 0:
        raise ValueError(f'{name}: reassembled complete routine is not uniquely byte-equal in clean ROM')
    return index + 0xC00000


def identify(a, scratch, rom):
    out = scratch / 'source-mapping'
    out.mkdir()
    # This checked-in include uses an empty .DEFINE parameter list rejected
    # by current ca65. Normalize only that unused sprite-size constant in a
    # private include overlay; no original function or shared file changes.
    overlay=out/'include-overlay';overlay.mkdir()
    enums=(a.native_source/'include/enums.asm').read_text(encoding='utf-8')
    old='.DEFINE SPRITE_PALETTES_SIZE() (NUM_SPRITE_PALETTES) * 16'
    if enums.count(old)!=1:raise ValueError('Review changed original enum compatibility syntax')
    (overlay/'enums.asm').write_text(enums.replace(old,'.DEFINE SPRITE_PALETTES_SIZE NUM_SPRITE_PALETTES * 16'),encoding='utf-8')
    (overlay/'common.asm').write_bytes((a.native_source/'include/common.asm').read_bytes())
    ram = a.native_source / 'asm/bankconfig/common/ram.asm'
    cfg = out / 'ram.cfg'
    cfg.write_text('MEMORY { BSS: start=$7E0000,size=$B800,type=rw,define=yes,file=""; '
                   'RAM2: start=$7EB800,size=$14800,type=rw,file=""; }\n'
                   'SEGMENTS { RAM1:load=BSS,type=bss;RAM2:load=RAM2,type=bss; }\n',encoding='utf-8')
    include = ['--cpu', '65816', '-D', 'USA', '-I', overlay, '-I', a.native_source / 'include', '-I', a.native_source / 'asm']
    run([a.ca65, *include, ram, '-o', out/'ram.o', '-l', out/'ram.lst'], out/'ram-compile.log')
    run([a.ld65, '-C', cfg, '-o', out/'ram.bin', '-Ln', out/'ram.lbl', out/'ram.o'], out/'ram-link.log')
    globals_ = labels(out/'ram.lbl')
    for name in ('GAME_STATE','PAD_STATE','PENDING_INTERACTIONS','DEMO_FRAMES_LEFT',
                 'HORIZONTAL_MOVEMENT_SPEEDS','VERTICAL_MOVEMENT_SPEEDS'):
        if name not in globals_ or not 0x7E0000 <= globals_[name] < 0x7EB800:
            raise ValueError('Original RAM layout not identified: ' + name)
    prelude = '.INCLUDE "common.asm"\n.INCLUDE "config.asm"\n.INCLUDE "structs.asm"\n'
    prelude += ''.join(f'.IMPORT {name}: absolute\n'
                       for name, value in globals_.items() if not name.startswith('__'))
    prelude += '.IMPORT __BSS_START__: absolute\n'
    cfg = out/'code.cfg'
    cfg.write_text('SYMBOLS {\n' + ''.join(f'{name}:type=export,value=${value & 0xffff:04X};\n'
                    for name,value in globals_.items() if not name.startswith('__')) +
                   '__BSS_START__:type=export,value=$0000;\n}\n'
                   'MEMORY { ROM:start=$C00000,size=$10000,type=ro,file=%O; }\n'
                   'SEGMENTS { CODE:load=ROM,type=ro; }\n',encoding='utf-8')
    def locate(obj,blobpath,symbol):
        blob=blobpath.read_bytes()
        try:address=find_unique(rom,blob,symbol)
        except ValueError:
            # Internal absolute JMP targets depend on the unknown entry
            # address. Identify their relocation bytes by two independently
            # linked starts, find one complete masked candidate, then relink
            # at that address and require complete unmasked byte equality.
            reloc=set();basecfg=cfg.read_text(encoding='utf-8')
            for delta in (1,256):
                shifted=out/f'{symbol.lower()}-identify-{delta}.cfg'
                shifted.write_text(basecfg.replace('start=$C00000',f'start=${0xC00000+delta:06X}'),encoding='utf-8')
                shiftedblob=out/f'{symbol.lower()}-identify-{delta}.bin'
                run([a.ld65,'-C',shifted,'-o',shiftedblob,obj],shifted.with_suffix('.log'))
                altered=shiftedblob.read_bytes()
                if len(altered)!=len(blob):raise ValueError('Original source relocation changed routine length')
                reloc.update(i for i,(x,y) in enumerate(zip(blob,altered)) if x!=y)
            if not reloc:raise
            pattern=b''.join(b'.' if i in reloc else re.escape(bytes((value,))) for i,value in enumerate(blob))
            candidates=list(re.finditer(pattern,rom,re.S))
            if len(candidates)!=1:raise ValueError(symbol+': original relocated candidate is not unique')
            address=candidates[0].start()+0xC00000
            located=out/(symbol.lower()+'-located.cfg')
            located.write_text(basecfg.replace('start=$C00000',f'start=${address:06X}'),encoding='utf-8')
            run([a.ld65,'-C',located,'-o',blobpath,obj],located.with_suffix('.log'))
            blob=blobpath.read_bytes()
            if rom[address-0xC00000:address-0xC00000+len(blob)]!=blob:
                raise ValueError(symbol+': complete relocated source bytes differ from original ROM')
        return blob,address
    mapping = {}; evidence = []
    # Assemble source data only as an identification aid, never an oracle.
    for symbol, relative in (('MOVEMENT_SPEEDS','data/map/movement_speeds.asm'),
                             ('ALLOWED_INPUT_DIRECTIONS','data/map/allowed_input_directions.asm')):
        source = out/(symbol.lower()+'.asm')
        source.write_text(prelude + '.SEGMENT "CODE"\n.INCLUDE "' + relative + '"\n',encoding='utf-8')
        obj=source.with_suffix('.o'); blobpath=source.with_suffix('.bin')
        run([a.ca65,*include,source,'-o',obj],source.with_suffix('.compile.log'))
        run([a.ld65,'-C',cfg,'-o',blobpath,obj],source.with_suffix('.link.log'))
        blob,address=locate(obj,blobpath,symbol)
        mapping[symbol]=address
        if symbol=='MOVEMENT_SPEEDS':mapping['MOVEMENT_SPEEDS_DIAGONAL']=address+14*4
        evidence.append({'symbol':symbol,'address':f'{address:06X}','originalSource':relative,
                         'byteEqualLength':len(blob),'byteEqualSha256':sha(blobpath)})
    for symbol, relative, abi in ROUTINES:
        source=out/(symbol.lower()+'.asm')
        source.write_text(prelude + ''.join(f'{name} := ${value:06X}\n' for name,value in mapping.items()) +
                          '.SEGMENT "CODE"\n.INCLUDE "'+relative+'"\n',encoding='utf-8')
        obj=source.with_suffix('.o'); blobpath=source.with_suffix('.bin')
        run([a.ca65,*include,source,'-o',obj,'-l',source.with_suffix('.lst')],source.with_suffix('.compile.log'))
        run([a.ld65,'-C',cfg,'-o',blobpath,obj],source.with_suffix('.link.log'))
        blob,address=locate(obj,blobpath,symbol)
        mapping[symbol]=address
        evidence.append({'symbol':symbol,'address':f'{address:06X}','abi':abi,'originalSource':relative,
                         'byteEqualLength':len(blob),'byteEqualSha256':sha(blobpath)})
    return globals_,mapping,evidence


def native_body(text,name):
    found=re.search(r'^(?:static )?[\w* ]+\b'+re.escape(name)+r'\([^;{]*\)\s*\{',text,re.M)
    if not found:raise ValueError('Actual native definition missing: '+name)
    end=found.end();depth=1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[found.start():end]+'\n'


def corpus():
    cases=[]
    def add(kind,label,**values):
        row={'kind':kind,'group':label,'style':0,'direction':0,'surface':0,'status':0,
             'demo':0,'position':0,'pad':0,'pending':0}
        row.update(values);cases.append(row)
    for style in range(14):
        for pad in range(16):
            for pending in (0,1,65535):
                for extra in (0,0xF0FF):
                    add('input','all-valid-styles-dpad-combinations-and-blocking',style=style,pad=(pad<<8)|extra,pending=pending)
    for style in range(14):
        for direction in range(8):
            for axis in ('h','v'):
                for surface in (0,4,8,12):
                    for status in (0,3):
                        for demo in (0,1):
                            add(axis,'all-style-direction-terrain-demo-skip-combinations',style=style,direction=direction,
                                surface=surface,status=status,demo=demo,position=0x00408000)
    for direction in range(8):
        for axis in ('h','v'):
            for surface in (0,8,12,0xFFFF):
                for status in (0,3,0x0103):
                    for position in (0,1,0x0000FFFF,0x7FFFFFF0,0x80000001,0xFFFF0000,0xFFFFFFFF):
                        add(axis,'fractional-sign-wrap-and-party-status-low-byte',direction=direction,surface=surface,
                            status=status,position=position)
    return cases


def machine(a,out,rom,globals_,mapping,cases):
    out.mkdir(); samples=out/'samples.jsonl'; velocities=out/'velocity.json'
    # Own caller, native mode, A/X/Y16, SP1FFF, DP1000, DBR7E. Original
    # position routines receive their 32-bit third argument at caller DP+14
    # and return the 32-bit result at caller DP+6, per original source macros.
    code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
    def jsl(symbol):code.extend((0x22,)+tuple(mapping[symbol].to_bytes(3,'little')))
    jsl('VELOCITY_STORE'); vel_done=0xC0FF00+len(code)
    entry=vel_done
    code.extend(bytes.fromhex('af00717e')); branches=[]
    for kind in range(3):
        code.extend((0xC9,kind,0,0xF0,0));branches.append(len(code)-1)
    code.append(0)
    starts=[]; jumps=[]
    # Input: A=style. Near position: A=direction, X=surface.
    for kind,symbol in enumerate(('MAP_INPUT_TO_DIRECTION','ADJUST_POSITION_HORIZONTAL','ADJUST_POSITION_VERTICAL')):
        starts.append(0xC0FF00+len(code))
        if kind==0:
            code.extend(bytes.fromhex('af02717e'));jsl(symbol);code.extend(bytes.fromhex('8f06707e'))
        else:
            code.extend(bytes.fromhex('af04717eaaaf02717e'))
            if mapping[symbol]>>16!=0xC0:raise ValueError('Unexpected original near routine bank')
            code.extend((0x20,mapping[symbol]&255,(mapping[symbol]>>8)&255))
        code.extend((0x4C,0,0));jumps.append(len(code)-2)
    finish=0xC0FF00+len(code)
    code.extend(bytes.fromhex('7b8f08707e3b8f0a707e'))
    sampled=0xC0FF00+len(code)
    code.extend((0x4C,entry&255,(entry>>8)&255))
    for branch,start in zip(branches,starts):
        distance=start-(0xC0FF00+branch+1)
        if not -128<=distance<=127:raise ValueError('Caller branch exceeds range')
        code[branch]=distance&255
    for at in jumps:code[at:at+2]=(finish&65535).to_bytes(2,'little')
    work=lambda name:globals_[name]&65535
    lua=['local output=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))',
         'local velocity=assert(io.open('+json.dumps(velocities.as_posix())+',"wb"))','local cases={']
    kinds={'input':0,'h':1,'v':2}
    lua+=['{'+','.join(str(v) for v in (kinds[c['kind']],c['style'],c['direction'],c['surface'],c['status'],c['demo'],c['position'],c['pad'],c['pending']))+'},' for c in cases]
    lua+=['}','local mem=emu.memType.snesWorkRam',
          'local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256)%256,mem) end',
          'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end',
          'local function r32(a) return r16(a)+65536*r16(a+2) end',
          'local index=0;local calls={0,0,0};local initialized=0;w16(0x7200,0x55aa)',
          'emu.addMemoryCallback(function() if initialized~=0 then return end;initialized=1;velocity:write("[")',
          f' for axis,base in ipairs({{{work("HORIZONTAL_MOVEMENT_SPEEDS")},{work("VERTICAL_MOVEMENT_SPEEDS")}}}) do',
          '  for i=0,111 do if axis~=1 or i~=0 then velocity:write(",") end;velocity:write(string.format("%.0f",r32(base+i*4))) end end',
          ' velocity:write("]\\n");velocity:flush();velocity:close()',
          f'end,emu.callbackType.exec,{vel_done})',
          'emu.addMemoryCallback(function()',
          ' index=index+1;local c=assert(cases[index],"past corpus");w16(0x7100,c[1]);w16(0x7102,c[1]==0 and c[2] or c[3]);w16(0x7104,c[4])',
          f' w16({work("GAME_STATE")}+142,c[2]);w16({work("GAME_STATE")}+75,c[5]);w16({work("DEMO_FRAMES_LEFT")},c[6]);w16({work("PAD_STATE")},c[8]);w16({work("PENDING_INTERACTIONS")},c[9])',
          ' w16(0x100e,c[7]%65536);w16(0x1010,math.floor(c[7]/65536));w16(0x1006,0xa5a5);w16(0x1008,0x5a5a)',
          f'end,emu.callbackType.exec,{entry})']
    # vel_done equals entry. Keep the one-shot dump callback registered so
    # deleting a callback cannot interfere with the next callback at entry.
    for i,symbol in enumerate(('MAP_INPUT_TO_DIRECTION','ADJUST_POSITION_HORIZONTAL','ADJUST_POSITION_VERTICAL')):
        lua.append(f'emu.addMemoryCallback(function() calls[{i+1}]=calls[{i+1}]+1 end,emu.callbackType.exec,{mapping[symbol]})')
    counts=Counter(c['kind'] for c in cases)
    lua+=['emu.addMemoryCallback(function()',
          ' assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"CPU frame corrupted");assert(r16(0x7200)==0x55aa,"protected RAM corrupted")',
          ' local value=cases[index][1]==0 and r16(0x7006) or r32(0x1006);output:write(string.format("[%d,%.0f]\\n",index,value))',
          f' if index==#cases then assert(initialized==1 and calls[1]=={counts["input"]} and calls[2]=={counts["h"]} and calls[3]=={counts["v"]},"call count differs");output:flush();output:close();emu.log("POSITION_CORPUS_COMPLETE "..index);emu.breakExecution() end',
          f'end,emu.callbackType.exec,{sampled})']
    script=out/'position.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
    result=subprocess.run([str(a.oracle.resolve()),str(a.rom.resolve()),'--home',str(out/'oracle-home'),
                           '--frames','10000','--timeout','60','--lua-timeout','10','--lua-allow-io','--lua',str(script),
                           '--write-memory','SnesPrgRom:0xff00:'+code.hex(),'--set-pc','0xc0ff00','--cpu','Snes'],capture_output=True,timeout=70)
    (out/'oracle.jsonl').write_bytes(result.stdout);(out/'oracle.stderr').write_bytes(result.stderr)
    records=[json.loads(line) for line in result.stdout.decode().splitlines()]
    logs=[r for r in records if r['event']=='lua_log']
    if result.returncode or not records[-1].get('ok') or records[-1].get('reason')!='debugger_break' or any(r['error_count'] for r in logs):
        raise RuntimeError('Original machine corpus did not complete')
    if sum('POSITION_CORPUS_COMPLETE ' in r['text'] for r in logs)!=1:raise RuntimeError('Completion marker missing/duplicated')
    rows=[json.loads(line) for line in samples.read_text(encoding='utf-8').splitlines()]
    if [r[0] for r in rows]!=list(range(1,len(cases)+1)):raise RuntimeError('Original machine corpus incomplete/unordered')
    speeds=json.loads(velocities.read_text(encoding='utf-8'))
    if len(speeds)!=224:raise RuntimeError('Original velocity table incomplete')
    return rows,speeds,{'ExecutedCases':len(cases),'HelperCalls':dict(counts),'VelocityStoreCalls':1,
                        'CompleteOrderedCorpusVerified':True,'StackDirectPageAndProtectedRamCanariesPassed':True,
                        'OriginalSourceReassemblyUsedForIdentificationOnly':True,'OwnCallerSha256':hashlib.sha256(code).hexdigest(),
                        'LuaSha256':sha(script),'SamplesSha256':sha(samples),'VelocitySampleSha256':sha(velocities)}


def native(a,out,cases,text):
    out.mkdir()
    start=text.index('static const int32_t movement_speeds_cardinal')
    end=text.index('/* MUSHROOMIZATION_DIRECTION_REMAP_TABLES',start)
    arrays='\n'.join(re.findall(r'^#define (?:NUM_WALKING_STYLES|NUM_DIRECTIONS)\s+[^\n]+',text,re.M))+'\n'+text[start:end]
    bodies=''.join(native_body(text,n) for n in ('velocity_store','map_input_to_direction','adjust_position'))
    prefix='''#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include "game/position_buffer.h"
#include "game/game_state.h"
#include "game/overworld.h"
#include "core/memory.h"
#include "game/settings.h"
#include "include/pad.h"
PositionBufferState pb;GameState game_state;OverworldState ow;CoreState core;
uint8_t engine_sprint_speed=SPRINT_SPEED_OFF;
#define WALKING_STYLE_NORMAL 0
static bool maternalbound_enabled(void){return false;}
static bool maternalbound_running(void){return false;}
'''
    driver=r'''
int main(int argc,char**argv){if(argc!=2)return 2;velocity_store();
 printf("VELOCITY [");for(int axis=0;axis<2;axis++)for(int i=0;i<112;i++){if(axis||i)printf(",");printf("%u",(uint32_t)(axis?pb.v_speeds[i]:pb.h_speeds[i]));}puts("]");
 FILE*f=fopen(argv[1],"r");if(!f)return 3;unsigned index,kind,style,dir,surface,status,demo,pos,pad,pending;
 while(fscanf(f,"%u %u %u %u %u %u %u %u %u %u",&index,&kind,&style,&dir,&surface,&status,&demo,&pos,&pad,&pending)==10){
  game_state.walking_style=style;game_state.party_status=status;ow.demo_frames_left=demo;core.pad1_held=pad;ow.pending_interactions=pending;
  uint32_t value=kind==0?(uint16_t)map_input_to_direction(style):(uint32_t)adjust_position(dir,surface,(int32_t)pos,kind==1?pb.h_speeds:pb.v_speeds);
  printf("[%u,%u]\n",index,value);
 }fclose(f);return 0;}
'''
    c=out/'native-position.c';c.write_text(prefix+arrays+bodies+driver,encoding='utf-8')
    inputs=out/'cases.tsv';kinds={'input':0,'h':1,'v':2}
    inputs.write_text(''.join(' '.join(map(str,(i+1,kinds[row['kind']],row['style'],row['direction'],row['surface'],row['status'],row['demo'],row['position'],row['pad'],row['pending'])))+'\n' for i,row in enumerate(cases)),encoding='utf-8')
    exe=out/'native-position.exe'
    command=[a.compiler,'-O2','-std=c11','-DUSA=1','-DEB_VIEWPORT_WIDTH=512','-DEB_VIEWPORT_HEIGHT=256']
    command+=['-I'+str(p.resolve()) for p in (a.native_source/'src',a.native_source/'src/include',a.generated,a.native_source/'src/data/runtime_generated')]
    run([*command,c,'-o',exe],out/'compile.log')
    result=run([exe,inputs],out/'samples.jsonl')
    lines=result.stdout.decode().splitlines();speeds=json.loads(lines[0][len('VELOCITY '):]);rows=[json.loads(v) for v in lines[1:]]
    if [row[0] for row in rows]!=list(range(1,len(cases)+1)):raise RuntimeError('Actual native corpus incomplete')
    return rows,speeds,{'ProbeSha256':sha(exe),'ActualBodiesSha256':hashlib.sha256(bodies.encode()).hexdigest(),
                        'ActualArraysSha256':hashlib.sha256(arrays.encode()).hexdigest(),
                        'OriginalModeAndSprintOffForced':True,'SprintAndReduxBehaviorOutsideThisOracle':True}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','oracle','ca65','ld65','compiler','native-source','generated','scratch','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--diagnostic',action='store_true',help='Retain genuine arithmetic mismatch evidence; incomplete runs still fail.')
    p.add_argument('--previous-report',type=Path,help='Link the preserved completed arithmetic red baseline by exact identity.')
    a=p.parse_args();out=local_scratch(a.scratch)
    if out.exists() or a.output.exists():raise ValueError('Use fresh scratch and report paths')
    rom=a.rom.read_bytes()
    if len(rom)!=0x300000 or hashlib.sha1(rom).hexdigest()!=US_SHA1:raise ValueError('Requires exact clean USA ROM')
    source=a.native_source/'src/game/position_buffer.c';sourcehash=sha(source);text=source.read_text(encoding='utf-8')
    out.mkdir(parents=True);globals_,mapping,identification=identify(a,out,rom);cases=corpus()
    original,ospeeds,ometadata=machine(a,out/'original-machine',rom,globals_,mapping,cases)
    actual,nspeeds,nmetadata=native(a,out/'actual-native',cases,text)
    differences=[dict(cases[i],index=i+1,originalMachine=reference[1],actualNative=observed[1])
                 for i,(reference,observed) in enumerate(zip(original,actual)) if reference!=observed]
    speed_differences=[{'index':i,'originalMachine':x,'actualNative':y} for i,(x,y) in enumerate(zip(ospeeds,nspeeds)) if x!=y]
    if a.rom.read_bytes()!=rom or sha(source)!=sourcehash:raise RuntimeError('ROM or actual native source changed during audit')
    previous=None
    if a.previous_report:
        red=json.loads(a.previous_report.read_text(encoding='utf-8'))
        if (red.get('format')!='native-position-arithmetic-micro-oracle-v1' or red.get('Passed') is not False
            or red.get('ExecutedCases')!=len(cases) or red.get('NativeMismatchCount')!=1496 or red.get('VelocityMismatchCount')!=0):
            raise ValueError('Review changed arithmetic baseline before linking it')
        if red['InputIdentities']['rom']!=sha(a.rom):raise ValueError('Baseline ROM differs')
        previous={'path':a.previous_report.as_posix(),'sha256':sha(a.previous_report),'ExecutedCases':red['ExecutedCases'],
                  'NativeMismatchCount':red['NativeMismatchCount'],'VelocityMismatchCount':red['VelocityMismatchCount']}
    report={'format':'native-position-arithmetic-micro-oracle-v1','Passed':not differences and not speed_differences,
            'ExecutedCases':len(cases),'NativeMismatchCount':len(differences),'NativeMismatches':differences,
            'MismatchGroups':dict(Counter(row['group'] for row in differences)),
            'VelocityTableEntries':224,'VelocityMismatchCount':len(speed_differences),'VelocityMismatches':speed_differences,
            'SourceMapping':identification,'GlobalAddresses':{n:f'{globals_[n]:06X}' for n in ('GAME_STATE','PAD_STATE','PENDING_INTERACTIONS','DEMO_FRAMES_LEFT','HORIZONTAL_MOVEMENT_SPEEDS','VERTICAL_MOVEMENT_SPEEDS')},
            'OriginalMachineEvidence':ometadata,'CompiledActualNativeEvidence':nmetadata,
            'SourceIncludeSyntaxAdaptation':{'PrivateOnly':True,'SharedIncludesUnchanged':True,
                 'Change':'Unused SPRITE_PALETTES_SIZE empty parameter-list define normalized for current ca65; common.asm copied verbatim into that overlay.',
                 'OriginalEnumsSha256':sha(a.native_source/'include/enums.asm')},
            'InputIdentities':{'rom':sha(a.rom),'nativeSource':sourcehash,'oracle':sha(a.oracle),'oracleCore':sha(a.oracle.parent/'MesenCore.dll'),
                               'ca65':sha(a.ca65),'ld65':sha(a.ld65),'compiler':sha(a.compiler)},
            'Runner':{'path':'tools/snes_position_arithmetic_oracle.py','sha256':sha(Path(__file__))},
            'OwnerRomsAndSavesUnchanged':True,'SharedSourceEdited':False,'SharedBuildsEdited':False,
            'FullPlaythroughVerified':False,'FullMovementParityVerified':False,
            'Limits':['Untouched original full functions execute original multiply helpers and use their original velocity tables; reassembly only establishes byte-equal identity and address.',
                      'Native original-mode functions/arrays are copied verbatim into an isolated probe. Redux enabled and running decisions are forced false and sprint off; their deliberate adapters are outside this original oracle.',
                      'Covers valid styles0..13, directions0..7, all16 dpad combinations, pending-interaction blocking, terrain/demo/skip arithmetic, fractional and32bit wrap samples.',
                      'Does not assert legal story reachability of every style/surface combination, full collision traversal, followers, stairs transitions, input-device mapping or sprint/Redux animation parity.']}
    if previous:report['PreservedRedBaseline']=previous
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:report[key] for key in ('Passed','ExecutedCases','NativeMismatchCount','VelocityMismatchCount','MismatchGroups')}),flush=True)
    if not report['Passed'] and not a.diagnostic:raise SystemExit(1)


if __name__=='__main__':main()
