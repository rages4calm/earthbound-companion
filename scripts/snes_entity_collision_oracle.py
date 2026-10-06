# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare entity collision geometry with untouched clean USA SNES routines.

Requires explicit local ROM, original/native sources, compiler and mesen-agent.
Only our test caller is written to temporary emulator memory; no ROM file,
owner save, asset pack or shared build is written. Grids are synthetic.
Function-only parity is not a complete game or movement compatibility claim.
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
from snes_movement_helpers_oracle import function, sha, US_SHA1

CATALOG=(
    ('check_entity_collision','check_entity_collision',0xC05CD7,0xC05D8B,
     'A=x, X=y, Y=entity slot; direction at caller DP+14; JSL/RTL'),
    ('check_top_edge','check_collision_tiles_horizontal',0xC05503,0xC0559C,
     'A=left x, X=size code; JSR/RTS'),
    ('check_bottom_edge','check_collision_tiles_vertical',0xC0559C,0xC05639,
     'A=left x, X=size code; JSR/RTS'),
    ('check_right_edge','accumulate_collision_flags_horizontal',0xC056D0,0xC05769,
     'A=top y, X=size code; JSR/RTS'),
    ('check_left_edge','accumulate_collision_flags_vertical',0xC05639,0xC056D0,
     'A=top y, X=size code; JSR/RTS'),
)
TABLES=(
    ('entity_collision_x_offset','entity_collision_x_offset',0xC42A1F),
    ('entity_collision_y_offset','entity_collision_y_offset',0xC42A41),
    ('sprite_hitbox_enable','sprite_hitbox_enable_table',0xC42AEB),
    ('entity_coll_h_count','entity_collision_width_table',0xC42AA7),
    ('entity_coll_v_count','entity_collision_height_table',0xC42AC9),
)
DISPATCH=((1,),(3,1),(3,),(2,3),(2,),(4,2),(4,),(1,4))
OUTPUTS=('returnWord','surfaceFlags','checkedLeftX','checkedTopY','ladderTileX','ladderTileY','selectedSlotSize')


def tables(source,rom,native_source):
    declarations=[];review=[]
    for native,original,address in TABLES:
        match=re.search(r'^(?:static )?const int16_t '+native+r'\[ENTITY_SIZE_COUNT\] = \{[^}]+\};',source,re.M)
        if not match:raise ValueError('Actual geometry table missing '+native)
        declaration=match.group();values=[int(v,0) for v in re.findall(r'0x[0-9A-Fa-f]+|\b\d+\b',declaration.split('{')[1])]
        original_values=list(struct.unpack_from('<17H',rom,address-0xC00000))
        if len(values)!=17 or values!=original_values:raise ValueError('Geometry table differs from original ROM: '+native)
        path=native_source/f'asm/data/overworld/{original}.asm'
        if original.upper()+':' not in path.read_text(encoding='utf-8'):raise ValueError('Original table label changed')
        declarations.append(declaration)
        review.append({'nativeTable':native,'originalLabel':original.upper(),'originalAddress':f'{address:06X}',
                       'EntriesCompared':17,'EveryEntryMatches':True,'ZeroEntryIndices':[i for i,v in enumerate(values) if not v],
                       'originalAsmPath':str(path.relative_to(native_source)).replace('\\','/'),'originalAsmSha256':sha(path),
                       'OriginalTableBytesSha256':hashlib.sha256(rom[address-0xC00000:address-0xC00000+34]).hexdigest()})
    return '\n'.join(declarations),review


def corpus():
    cases=[]
    def add(label,kind,x,y,size,slot=0,direction=0,initial=0xA5A5,pattern=0):
        if not 0<=size<17 or not 0<=slot<30:raise ValueError('Invalid fixture index')
        cases.append((label,(kind,x&65535,y&65535,size,slot,direction&65535,initial,pattern,0)))
    for pattern in range(4):
        for size in range(17):
            for xp in range(8):
                for yp in range(8):
                    x,y=104+xp,96+yp
                    for direction in range(8):add('all-sizes-tile-phases-directions',0,x,y,size,direction=direction,pattern=pattern)
                    for kind in range(1,5):
                        for initial in (0,0xA500,0xFFFF):
                            add('direct-edge-phases-flag-preservation',kind,x,y,size,initial=initial,pattern=pattern)
        for size in range(17):
            for x,y in ((0,0),(0,65535),(65535,0),(65535,65535),(32767,32767),(32768,32768),
                        (65528,65528),(65532,65532),(511,511),(512,512),(513,513),(0,32768),(32768,0),
                        (32760,32760),(32769,32769),(65529,65529)):
                for direction in range(8):add('coordinate-arithmetic-and-grid-wrap-boundaries',0,x,y,size,direction=direction,pattern=pattern)
                for kind in range(1,5):add('direct-edge-arithmetic-boundaries',kind,x,y,size,pattern=pattern)
        for slot in range(30):
            for size in range(17):
                for direction in range(8):add('all-entity-slot-indexing',0,153,177,size,slot,direction,pattern=pattern)
    # Original assembly explicitly returns without dispatch for other directions.
    for size in range(17):
        for direction in (8,255,32767,32768,65535):
            add('source-default-direction-no-edge-dispatch',0,105,97,size,29,direction,pattern=3)
    # Uniform grids separately verify every collision byte, including door,
    # ladder/stair/surface bits, without depending on nonuniform OR saturation.
    for flag in range(256):
        for size in range(17):
            for kind in range(5):
                add('all-collision-byte-flags-and-size-codes',kind,109,101,size,29,flag%8,0xA500,256+flag)
    return sorted(cases,key=lambda row:row[1][7])


def caller():
    # Own code only: native CPU, 16-bit registers, SP1FFF, DP1000, DBR7E.
    code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
    entry=0xC0FF00+len(code);code+=bytes.fromhex('af08717eaa')
    indirect=len(code);code+=bytes((0xFC,0,0))
    code+=bytes.fromhex('8f00707e7b8f08707e3b8f0a707e')
    finish=0xC0FF00+len(code);code+=bytes((0x4C,entry&255,(entry>>8)&255))
    starts=[]
    for kind,(_,_,address,_,_) in enumerate(CATALOG):
        starts.append(0xC0FF00+len(code))
        if kind==0:
            code+=bytes.fromhex('af04717eaaaf0c717ea8af02717e')
            code+=bytes((0x22,address&255,(address>>8)&255,(address>>16)&255,0x60))
        else:
            code+=bytes.fromhex('af06717eaa')
            code+=bytes.fromhex('af02717e') if kind in (1,2) else bytes.fromhex('af04717e')
            code+=bytes((0x20,address&255,(address>>8)&255,0xA9,0,0,0x60))
    table=0xC0FF00+len(code);code[indirect+1:indirect+3]=struct.pack('<H',table&65535)
    code+=b''.join(struct.pack('<H',at&65535) for at in starts)
    if len(code)>256:raise ValueError('Own caller exceeds isolated injection slot')
    return code,entry,finish


def native_probe(a,out,source,declarations,cases,trace):
    raw=''.join(function(source,row[0]) for row in CATALOG[1:])+function(source,CATALOG[0][0])
    helpers=raw
    if trace:
        if raw.count('ml.loaded_collision_tiles[idx]')!=8:raise ValueError('Review changed grid-read instrumentation')
        helpers=raw.replace('ml.loaded_collision_tiles[idx]','sample_tile(idx)')
    prefix='''#include "game/map_loader.h"
#include "game/overworld.h"
#include "entity/entity.h"
#include <stdio.h>
#include <string.h>
MapLoaderState ml;OverworldState ow;EntitySystem entities;
static uint16_t temp_entity_surface_flags;
static unsigned sampled[32],sample_count;
static unsigned char sample_tile(unsigned at){
 if(at>=4096||sample_count>=32){fprintf(stderr,"trace bounds");return 0;}
 sampled[sample_count++]=at;return ml.loaded_collision_tiles[at];
}
static unsigned char grid_byte(unsigned at,unsigned pattern){
 if(pattern>=256)return pattern-256;
 switch(pattern){
 case 0:return ((at^(at>>6))&1)?0x40:0;
 case 1:return 0x10|((at*11)&0x2f);
 case 2:return 0x80|((at*7+(at>>6))&0x70);
 default:return ((at*73)^(at>>3)^0x5a)&255;
 }
}
'''
    body=r'''
int main(int argc,char**argv){
 if(argc!=2)return 2;FILE*f=fopen(argv[1],"rb");if(!f)return 3;
 uint16_t h[9];unsigned prev=65535;
 while(fread(h,2,9,f)==9){
  if(h[0]>=5||h[3]>=17||h[4]>=30)return 4;
  if(prev!=h[7]){for(unsigned i=0;i<4096;i++)ml.loaded_collision_tiles[i]=grid_byte(i,h[7]);prev=h[7];}
  for(unsigned i=0;i<30;i++)entities.sizes[i]=(i*7+11)%17;
  entities.sizes[h[4]]=h[3];sample_count=0;
  ow.checked_collision_left_x=h[1];ow.checked_collision_top_y=h[2];
  ow.ladder_stairs_tile_x=0xBEEF;ow.ladder_stairs_tile_y=0xCAFE;
  temp_entity_surface_flags=h[6];uint16_t value=0;
  switch(h[0]){
   case 0:value=check_entity_collision((int16_t)h[1],(int16_t)h[2],h[4],(int16_t)h[5]);break;
   case 1:check_top_edge((int16_t)h[1],h[3]);break;
   case 2:check_bottom_edge((int16_t)h[1],h[3]);break;
   case 3:check_right_edge((int16_t)h[2],h[3]);break;
   case 4:check_left_edge((int16_t)h[2],h[3]);break;
  }
  printf("[[%u,%u,%u,%u,%u,%u,%u],[",value,temp_entity_surface_flags,
   (uint16_t)ow.checked_collision_left_x,(uint16_t)ow.checked_collision_top_y,
   (uint16_t)ow.ladder_stairs_tile_x,(uint16_t)ow.ladder_stairs_tile_y,(uint16_t)entities.sizes[h[4]]);
  for(unsigned i=0;i<sample_count;i++)printf("%s%u",i?",":"",sampled[i]);puts("]]");
 }int failed=ferror(f);fclose(f);return failed?4:0;
}
'''
    stem='native-trace' if trace else 'native-verbatim';c=out/(stem+'.c');c.write_text(prefix+declarations+'\n'+helpers+body,encoding='utf-8')
    inputs=out/'inputs.bin'
    if not inputs.exists():inputs.write_bytes(b''.join(struct.pack('<9H',*h) for _,h in cases))
    exe=out/(stem+'.exe');includes=[a.native_source/'src',a.native_source/'src/include',a.generated,a.native_source/'src/data/runtime_generated']
    cmd=[str(a.compiler.resolve()),'-std=c11','-O2','-DEB_VIEWPORT_WIDTH=512','-DEB_VIEWPORT_HEIGHT=256','-DUSA=1']
    cmd+=['-I'+str(path.resolve()) for path in includes]+[str(c),'-o',str(exe)]
    run=subprocess.run(cmd,capture_output=True,timeout=30);(out/(stem+'-compile.log')).write_bytes(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError('Native probe compilation failed')
    run=subprocess.run([str(exe),str(inputs)],capture_output=True,timeout=30)
    if run.returncode or run.stderr:raise RuntimeError('Native probe incomplete or trace bounds failed')
    (out/(stem+'-samples.jsonl')).write_bytes(run.stdout);rows=[json.loads(line) for line in run.stdout.decode().splitlines()]
    if len(rows)!=len(cases) or any(len(row)!=2 or len(row[0])!=7 for row in rows):raise RuntimeError('Native corpus incomplete')
    return rows,sha(exe),hashlib.sha256((declarations+raw).encode()).hexdigest()


def machine_reference(a,out,rom,cases):
    # Locate the eight actual LDA abs,X grid reads in the pinned clean code.
    # Only generic 65816 opcode/operand decoding is included in this tool.
    reads=[]
    for _,_,start,end,_ in CATALOG[1:]:
        sites=[at for at in range(start,end-2) if rom[at-0xC00000]==0xBD and
               struct.unpack_from('<H',rom,at-0xC00000+1)[0]==0xE000]
        if len(sites)!=2:raise ValueError('Original edge grid-read locations changed')
        reads.extend(sites)
    code,entry,finish=caller();samples=out/'machine-samples.jsonl'
    lua=['local output=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))','local cases={']
    lua+=['{'+','.join(map(str,h))+'},' for _,h in cases]
    lua+=['}','local mem=emu.memType.snesWorkRam',
          'local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256),mem) end',
          'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end',
          'local function gridbyte(at,p) if p>=256 then return p-256 end',
          ' if p==0 then if ((at~(at>>6))&1)~=0 then return 0x40 else return 0 end end',
          ' if p==1 then return 0x10|((at*11)&0x2f) end',
          ' if p==2 then return 0x80|((at*7+(at>>6))&0x70) end',
          ' return ((at*73)~(at>>3)~0x5a)&255 end',
          'w16(0x7200,0x55aa);local index=0;local prev=-1;local trace={};local calls={0,0,0,0,0}',
          'emu.addMemoryCallback(function()',
          ' index=index+1;local c=cases[index];assert(c,"ran beyond corpus");trace={}',
          ' if prev~=c[8] then for i=0,4095 do emu.write(0xe000+i,gridbyte(i,c[8]),mem) end;prev=c[8] end',
          ' for i=0,29 do w16(0x2b6e+i*2,(i*7+11)%17) end;w16(0x2b6e+c[5]*2,c[4])',
          ' w16(0x7108,c[1]*2);w16(0x7102,c[2]);w16(0x7104,c[3]);w16(0x7106,c[4]);w16(0x710c,c[5]);w16(0x100e,c[6])',
          ' w16(0x5dac,c[2]);w16(0x5dae,c[3]);w16(0x5da4,c[7]);w16(0x5da8,0xbeef);w16(0x5daa,0xcafe)',
          f'end,emu.callbackType.exec,{entry})']
    for kind,(_,_,address,_,_) in enumerate(CATALOG):
        lua.append(f'emu.addMemoryCallback(function() calls[{kind+1}]=calls[{kind+1}]+1 end,emu.callbackType.exec,{address})')
    for at in reads:
        lua+=['emu.addMemoryCallback(function()',
              ' local state=emu.getState();local x=state["cpu.x"];assert(type(x)=="number" and x>=0 and x<4096,"invalid original grid index")',
              ' trace[#trace+1]=x;assert(#trace<=32,"original trace overflow")',
              f'end,emu.callbackType.exec,{at})']
    lua+=['emu.addMemoryCallback(function()',
          ' assert(r16(0x7008)==0x1000,"direct page corrupted");assert(r16(0x700a)==0x1fff,"stack corrupted");assert(r16(0x7200)==0x55aa,"protected memory corrupted")',
          ' local c=cases[index];output:write(string.format("[%d,[%d,%d,%d,%d,%d,%d,%d],[%s]]\\n",index,r16(0x7000),r16(0x5da4),r16(0x5dac),r16(0x5dae),r16(0x5da8),r16(0x5daa),r16(0x2b6e+c[5]*2),table.concat(trace,",")))',
          ' if index==#cases then output:flush();output:close();emu.log("CORPUS_COMPLETE "..table.concat(calls,","));emu.breakExecution() end',
          f'end,emu.callbackType.exec,{finish})']
    script=out/'entity-collision.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
    cmd=[str(a.oracle.resolve()),str(a.rom.resolve()),'--home',str(out/'oracle-home'),'--frames','4000',
         '--timeout','60','--lua-timeout','15','--lua-allow-io','--lua',str(script),
         '--write-memory','SnesPrgRom:0xff00:'+code.hex(),'--set-pc','0xc0ff00','--cpu','Snes']
    run=subprocess.run(cmd,capture_output=True,timeout=75);(out/'machine-oracle.jsonl').write_bytes(run.stdout);(out/'machine-oracle.stderr').write_bytes(run.stderr)
    records=[json.loads(line) for line in run.stdout.decode().splitlines()];logs=[row for row in records if row['event']=='lua_log'];summary=records[-1] if records else {}
    if run.returncode or summary.get('event')!='summary' or not summary.get('ok') or summary.get('reason')!='debugger_break' or not logs or any(row['error_count'] for row in logs):
        raise RuntimeError('Original-machine reference incomplete; inspect machine-oracle.jsonl')
    completion=[row['text'] for row in logs if 'CORPUS_COMPLETE ' in row['text']]
    if len(completion)!=1:raise RuntimeError('Missing/duplicate completion gate')
    counts=list(map(int,completion[0].split('CORPUS_COMPLETE ')[1].strip().split(',')));expected=Counter()
    for _,h in cases:
        expected[h[0]]+=1
        if h[0]==0 and h[5]<8:
            for kind in DISPATCH[h[5]]:expected[kind]+=1
    if counts!=[expected[i] for i in range(5)]:raise RuntimeError('Actual helper entry calls differ from source dispatch')
    rows=[json.loads(line) for line in samples.read_text(encoding='utf-8').splitlines()]
    if [row[0] for row in rows]!=list(range(1,len(cases)+1)) or any(len(row)!=3 or len(row[1])!=7 for row in rows):
        raise RuntimeError('Machine corpus incomplete, malformed or out of order')
    return rows,counts,reads,sha(script),hashlib.sha256(code).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','oracle','compiler','native-source','generated','scratch'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--output',type=Path,help='Optional fresh metadata-only public report path.')
    p.add_argument('--batch-size',type=int,default=20000,help='Bounded original-machine batches (1..30000 cases).')
    a=p.parse_args();out=local_scratch(a.scratch)
    if not 1<=a.batch_size<=30000:raise ValueError('Keep machine batches bounded at 1..30000 cases')
    if out.exists() or (a.output and a.output.exists()):raise ValueError('Use fresh scratch/report filenames; existing evidence is preserved')
    for item in (a.rom,a.oracle,a.compiler):
        if not item.is_file():raise ValueError('Missing explicit input '+str(item))
    rom=a.rom.read_bytes()
    if len(rom)!=0x300000 or hashlib.sha1(rom).hexdigest()!=US_SHA1:raise ValueError('Exact clean unheadered USA ROM required')
    sourcepath=a.native_source/'src/game/map_loader.c';source=sourcepath.read_text(encoding='utf-8');declarations,tablereview=tables(source,rom,a.native_source)
    identities={'rom':sha(a.rom),'oracle':sha(a.oracle),'compiler':sha(a.compiler),'nativeSource':sha(sourcepath),
                'originalMacros':sha(a.native_source/'include/macros.asm'),'originalRamLayout':sha(a.native_source/'asm/bankconfig/common/ram.asm'),
                'nativeEntityHeader':sha(a.native_source/'src/entity/entity.h'),'nativeOverworldHeader':sha(a.native_source/'src/game/overworld.h')}
    if (a.oracle.parent/'MesenCore.dll').is_file():identities['oracleCore']=sha(a.oracle.parent/'MesenCore.dll')
    mapping=[]
    for native,original,start,end,abi in CATALOG:
        path=a.native_source/f'asm/overworld/collision/{original}.asm'
        if original.upper()+':' not in path.read_text(encoding='utf-8'):raise ValueError('Original function label changed')
        mapping.append({'nativeHelper':native,'originalLabel':original.upper(),'originalAddress':f'{start:06X}','endExclusive':f'{end:06X}',
                        'originalMachineBytesSha256':hashlib.sha256(rom[start-0xC00000:end-0xC00000]).hexdigest(),
                        'originalAsmPath':str(path.relative_to(a.native_source)).replace('\\','/'),'originalAsmSha256':sha(path),'abi':abi})
    out.mkdir(parents=True);cases=corpus();verbatim,vsha,bodysha=native_probe(a,out,source,declarations,cases,False)
    traced,tsha,_=native_probe(a,out,source,declarations,cases,True)
    if any(v[0]!=t[0] for v,t in zip(verbatim,traced)):raise RuntimeError('Trace instrumentation changed actual-source result')
    rows=[];counts=[0]*5;batches=[]
    for offset in range(0,len(cases),a.batch_size):
        batchout=out/f'machine-batch-{len(batches)+1:03}';batchout.mkdir()
        batch,bcount,reads,luasha,callersha=machine_reference(a,batchout,rom,cases[offset:offset+a.batch_size])
        rows.extend([i+offset,values,trace] for i,values,trace in batch)
        counts=[a+b for a,b in zip(counts,bcount)]
        batches.append({'FirstCase':offset+1,'LastCase':offset+len(batch),'ExecutedCases':len(batch),'CompleteOrderedCorpusVerified':True,
                        'ActualOriginalEntryCounts':bcount,'OracleLuaSha256':luasha,'OwnCallerSha256':callersha,
                        'OriginalSamplesSha256':sha(batchout/'machine-samples.jsonl'),'PrivateArtifactDirectory':batchout.name})
        print(json.dumps({'OriginalMachineBatchComplete':len(batches),'LastCase':offset+len(batch),'TotalCases':len(cases)}),flush=True)
    if rows[0][2]!=[780,780,781]:raise RuntimeError('Original trace calibration at known first fixture failed')
    combined=out/'machine-samples.jsonl';combined.write_text(''.join(json.dumps(row)+'\n' for row in rows),encoding='utf-8')
    diff=[]
    for i,values,trace in rows:
        if traced[i-1]==[values,trace]:continue
        label,h=cases[i-1];diff.append({'case':i,'helper':CATALOG[h[0]][0],'caseGroup':label,'input':list(h),
                                      'native':traced[i-1],'originalMachine':[values,trace]})
    for key,path in (('rom',a.rom),('oracle',a.oracle),('compiler',a.compiler),('nativeSource',sourcepath)):
        if identities[key]!=sha(path):raise RuntimeError('Audit input changed '+key)
    report={'format':'native-entity-collision-micro-oracle-v1','Passed':not diff,'ExecutedCases':len(cases),'SkippedCases':0,'MismatchCount':len(diff),
            'MismatchesByHelper':dict(Counter(d['helper'] for d in diff)),'MismatchExamples':diff[:40],
            'AllMismatchesPrivateArtifact':'native-mismatches.jsonl','OutputColumns':list(OUTPUTS),'ExactSampleTileSequenceCompared':True,
            'InputColumns':['kind','x','y','sizeCode','entitySlot','direction','initialSurfaceFlags','syntheticGridPattern','reserved'],
            'SizeCodesCovered':list(range(17)),'EntitySlotsCovered':list(range(30)),'ValidDirectionsCovered':list(range(8)),
            'All17EntriesOfAll5GeometryTablesMatch':True,'GeometryTables':tablereview,'HelperCatalog':mapping,
            'OriginalGridReadInstructionAddresses':[f'{at:06X}' for at in reads],
            'GlobalAddresses':{'entitySizes':'002B6E','surfaceFlags':'005DA4','checkedLeftX':'005DAC','checkedTopY':'005DAE','collisionGrid':'00E000',
                               'ladderTileX':'005DA8','ladderTileY':'005DAA'},
            'CaseGroups':dict(Counter(label for label,_ in cases)),'ActualOriginalEntryCalls':{row[0]:counts[i] for i,row in enumerate(CATALOG)},
            'TotalTileSamplesCompared':sum(len(row[2]) for row in rows),'InputIdentities':identities,'OriginalRomSha1':US_SHA1,
            'VerbatimActualBodiesAndTablesSha256':bodysha,'NativeVerbatimProbeSha256':vsha,'NativeTraceProbeSha256':tsha,
            'TraceInstrumentationResultParity':True,'OriginalMachineCodeExecuted':True,'OwnCallerSha256':callersha,'OriginalMachineBatches':batches,
            'SourceABI':{'OriginalDirectPageFrameBytes':20,'FourthParameterOffsetFromCallerDirectPage':14,
                         'OriginalEntitySizeEntryBytes':2,'NativeEntitySizeEntryBytes':1,'ValidSizeRangeVerified':[0,16]},
            'TraceCalibrationPassed':True,
            'InputSha256':sha(out/'inputs.bin'),'OriginalSamplesSha256':sha(out/'machine-samples.jsonl'),
            'StackAndDirectPageCanariesPassed':True,'ProtectedMemoryCanaryPassed':True,'CompleteOrderedCorpusVerified':True,
            'OwnerRomUnchanged':True,'OwnerSavesTouched':False,'SharedSourceEdited':False,'SharedBuildsEdited':False,
            'FullCollisionParityVerified':False,'FullCompatibilityVerified':False,'FullPlaythroughVerified':False,
            'Runner':{'path':'tools/snes_entity_collision_oracle.py','sha256':sha(Path(__file__)),
                      'ReproductionArguments':{'rom':'<local clean USA .sfc>','oracle':'<local mesen-agent.exe>','compiler':'<local gcc.exe>',
                                               'native-source':'native-source','generated':'build/companion/game_lib/generated',
                                               'scratch':'_BuildScratch/<fresh audit directory>','batch-size':a.batch_size,
                                               'output':'research/<fresh report filename>.json'}},
            'Limits':['Original clean USA machine code is compared with these five actual native C bodies compiled in isolation; no complete game executable or story parity is claimed.',
                      'Every size, slot, tile phase and valid direction is exercised with selected arithmetic/grid-wrap boundaries. All possible coordinate pairs, grids and initial flags are not exhaustive.',
                      'The original always samples a first tile even for zero width/height entries; table equality, read order/count and ORed flags are compared directly.',
                      'All 256 collision bytes are checked as values. Their gameplay effects, actual stairs/doors, sprite/NPC collision integration, sprint guards and collision-grid loading are outside this function audit.',
                      'Source-defined default direction returns are included; invalid entity slots/size indices are not invoked because the source indexes arrays without bounds checks.',
                      'Trace uses CPU X at each original LDA abs,X grid instruction and a separately result-checked native sample wrapper. Other CPU registers, scratch RAM and nonspecified helper return registers are not parity outputs.',
                      'No original ROM, game assets, original machine-byte copies or emulator are included in public tools/reports.']}
    (out/'native-mismatches.jsonl').write_text(''.join(json.dumps(d)+'\n' for d in diff),encoding='utf-8')
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('Passed','ExecutedCases','MismatchCount','MismatchesByHelper','TotalTileSamplesCompared')}),flush=True)
    if diff:raise SystemExit(1)


if __name__=='__main__':main()
