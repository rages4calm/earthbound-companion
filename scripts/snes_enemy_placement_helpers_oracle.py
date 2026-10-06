# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare placement/direction helpers with actual Original and pinned Redux CPU.

Requires explicit local ROMs, packs, immutable native build/runtime, source and
tool paths. Only a fresh private scratch directory is written. Full original
source bodies must identify uniquely and byte-equal before machine execution.
Public reports contain hashes/counts, never game tables or original ROM bytes.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess

from build_maternalbound_pack import read_pack
from check_jev_observer_parity import local_scratch
from party_follow_private_build import private_build
from snes_movement_helpers_oracle import sha, US_SHA1
import snes_position_arithmetic_oracle as mapping

CATALOG = (
    ('GET_MAP_ENEMY_PLACEMENT', 'overworld/get_map_enemy_placement.asm', 'MAP_ENEMY_PLACEMENT'),
    ('CAN_ENEMY_RUN_IN_DIRECTION', 'overworld/can_enemy_run_in_direction.asm', 'ENEMY_CONFIGURATION_TABLE'),
)

DRIVER = r'''
#define SDL_MAIN_HANDLED
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include "game/overworld.h"
#include "game/battle.h"
extern int eb_platform_main(int,char**);
int main(int argc,char**argv){
 if(argc!=5)return 2;char save[4096];snprintf(save,sizeof(save),"%s/private.srm",argv[2]);
 char*boot[]={"placement-helpers-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1",atoi(argv[4])?"--redux-battle-fixture":"--inspect-shuffle","0"};
 if(eb_platform_main(atoi(argv[4])?13:12,boot))return 3;
 get_map_enemy_placement(0,0);if(!enemy_config_table)return 4;
 if(sizeof(EnemyData)!=94||offsetof(EnemyData,run_flag)!=32)return 5;
 FILE*f=fopen(argv[3],"r");if(!f)return 6;unsigned index,kind,a,b;
 while(fscanf(f,"%u %u %u %u",&index,&kind,&a,&b)==4){
  if(kind>1||(kind==1&&b>=231))return 7;
  unsigned value=kind?can_enemy_run_in_direction(a,b):get_map_enemy_placement(a,b);
  printf("ENEMY_HELPER [%u,%u]\n",index,value);
 }fclose(f);return 0;
}
'''


def identify(a,out,original,redux):
    previous=mapping.ROUTINES
    try:
        mapping.ROUTINES=(('MULT168','system/math/mult168.asm','far'),)
        globals_,addresses,proof=mapping.identify(a,out,original)
    finally:
        mapping.ROUTINES=previous
    folder=out/'source-mapping'
    base=(folder/'mult168.asm').read_text(encoding='utf-8').split('MOVEMENT_SPEEDS :=',1)[0]
    known=''.join(f'{k} := ${v:06X}\n' for k,v in addresses.items())
    include=['--cpu','65816','-D','USA','-I',folder/'include-overlay','-I',a.native_source/'include','-I',a.native_source/'asm']
    modes={'original':{},'redux':{}}
    multiplier=next(row for row in proof if row['symbol']=='MULT168')
    pos=addresses['MULT168']-0xC00000;n=multiplier['byteEqualLength']
    if original[pos:pos+n]!=redux[pos:pos+n]:
        raise ValueError('Pinned Redux changes MULT168; separate identification required')
    multiplier['ReduxFunctionByteEqual']=True
    for symbol,relative,table in CATALOG:
        def assemble(pointer,suffix):
            source=folder/(symbol.lower()+suffix+'.asm');obj=source.with_suffix('.o');blob=source.with_suffix('.bin')
            source.write_text(base+known+f'{table} := ${pointer:06X}\n'+'.SEGMENT "CODE"\n.A16\n.I16\n.INCLUDE "'+relative+'"\n',encoding='utf-8')
            mapping.run([a.ca65,*include,source,'-o',obj],source.with_suffix('.compile.log'))
            mapping.run([a.ld65,'-C',folder/'code.cfg','-o',blob,obj],source.with_suffix('.link.log'))
            return blob
        initial=assemble(0xC00000,'-placeholder').read_bytes()
        altered=assemble(0xC10101,'-relocation').read_bytes()
        offsets=[i for i,(x,y) in enumerate(zip(initial,altered)) if x!=y]
        if len(initial)!=len(altered) or len(offsets)!=3 or offsets!=list(range(offsets[0],offsets[0]+3)):
            raise ValueError('Expected exactly one far data-table operand relocation')
        pattern=b''.join(b'.' if i in offsets else re.escape(bytes((v,))) for i,v in enumerate(initial))
        candidates=list(re.finditer(pattern,original,re.S))
        if len(candidates)!=1:raise ValueError('Complete masked source helper is not uniquely located: '+symbol)
        pos=candidates[0].start();address=0xC00000+pos;actual=original[pos:pos+len(initial)]
        pointer=int.from_bytes(actual[offsets[0]:offsets[0]+3],'little');verified=assemble(pointer,'-verified')
        if mapping.find_unique(original,verified.read_bytes(),symbol)!=address:
            raise ValueError('Complete unmasked source helper differs')
        redux_actual=redux[pos:pos+len(initial)]
        if any(x!=y for i,(x,y) in enumerate(zip(actual,redux_actual)) if i not in offsets):
            raise ValueError('Pinned Redux changes helper instructions outside table relocation: '+symbol)
        redux_pointer=int.from_bytes(redux_actual[offsets[0]:offsets[0]+3],'little')
        redux_verified=assemble(redux_pointer,'-redux-verified')
        if redux_verified.read_bytes()!=redux_actual:raise ValueError('Full pinned Redux helper byte equality failed')
        for mode,romptr in (('original',pointer),('redux',redux_pointer)):
            modes[mode][symbol]={'address':address,'pointer':romptr}
        proof.append({'symbol':symbol,'address':f'{address:06X}','abi':'far A=x/surface, X=y for map, Y=enemy for direction; A/X/Y16',
                      'originalSource':relative,'byteEqualLength':len(actual),'byteEqualSha256':sha(verified),
                      'ReduxByteEqualSha256':sha(redux_verified),'TableOperandBytes':offsets,
                      'OriginalTablePointer':f'{pointer:06X}','ReduxTablePointer':f'{redux_pointer:06X}',
                      'AllInstructionsByteEqualBetweenModes':True})
    return globals_,modes,proof


def packed_review(a,modes,roms):
    ids=a.native_source/'src/data/runtime_generated/asset_ids.h';reviews={};values={}
    for mode,pack in (('original',a.original_assets),('redux',a.redux_assets)):
        _,_,assets=read_pack(pack,ids)
        grid=assets['data/map_enemy_placement.bin'];enemy=assets['data/enemy_configuration_table.bin']
        if len(grid)!=40960:raise ValueError('Map placement grid dimensions changed')
        if mode=='original' and len(enemy)!=231*94:raise ValueError('Original enemy record count changed')
        if mode=='redux':
            if enemy.find(b'MRDXAI01')!=231*94 or struct.unpack_from('<I',enemy,231*94+8)[0]!=231:
                raise ValueError('Redux enemy footer/count changed')
        def romoffset(pointer):
            # Tables here are original/pinned HiROM upper banks, never LoROM guesses.
            if not 0xC00000<=pointer<0xC00000+len(roms[mode]):raise ValueError('Unexpected ROM table mapping')
            return pointer-0xC00000
        grid_at=romoffset(modes[mode]['GET_MAP_ENEMY_PLACEMENT']['pointer'])
        enemy_at=romoffset(modes[mode]['CAN_ENEMY_RUN_IN_DIRECTION']['pointer'])
        original_grid=roms[mode][grid_at:grid_at+40960]
        if grid!=original_grid:raise ValueError('Actual packed full placement grid differs from machine referenced table')
        run=bytes(enemy[i*94+32] for i in range(231))
        source_run=bytes(roms[mode][enemy_at+i*94+32] for i in range(231))
        if run!=source_run:raise ValueError('Packed enemy run flags differ from source-machine records')
        values[mode]=(grid,run)
        reviews[mode]={'GridBytes':len(grid),'GridCells':20480,'PackedFullGridEqualsMachineReferencedTable':True,
                       'GridSha256':hashlib.sha256(grid).hexdigest(),'EnemyRecords':231,'EnemyRecordBytes':94,
                       'RunFlagOffset':32,'EveryPackedRunFlagEqualsSourceMachine':True,
                       'RunFlagSha256':hashlib.sha256(run).hexdigest(),'RunFlagDistribution':dict(Counter(run)),
                       'EncounterIdDistributionCount':len(set(struct.unpack('<20480H',grid))),
                       'ReduxAiFooterPresent':mode=='redux'}
    return reviews,values


def corpus():
    cases=[('map','all-actual-map-cells',x,y) for y in range(160) for x in range(128)]
    boundaries=(0,1,126,127,128,129,158,159,160,161,255,256,32767,32768,65534,65535)
    cases.extend(('map','unsigned-and-map-edge-boundaries',x,y) for x in boundaries for y in boundaries)
    flags=sorted({low|high for low in range(16) for high in (0,0xF0,0xFF00,0x8000,0x4000,0xFFF0)})
    cases.extend(('direction','all-enemy-records-selected-full-word-surface-flags',surface,enemy)
                 for enemy in range(231) for surface in flags)
    return cases


def machine(a,out,mode,helpers,rows):
    out.mkdir();samples=out/'samples.jsonl';code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
    entry=0xC0FF00+len(code)
    # Own dispatch reads kind, then loads source-defined argument registers.
    code+=bytes.fromhex('af04717ec90000f0');branch=len(code);code.append(0)
    code+=bytes.fromhex('af02717ea8af00717e')+bytes((0x22,))+helpers['CAN_ENEMY_RUN_IN_DIRECTION']['address'].to_bytes(3,'little')
    code.append(0x80);jump=len(code);code.append(0)
    mapstart=len(code);code+=bytes.fromhex('af02717eaaaf00717e')+bytes((0x22,))+helpers['GET_MAP_ENEMY_PLACEMENT']['address'].to_bytes(3,'little')
    join=len(code);code[branch]=mapstart-(branch+1);code[jump]=join-(jump+1)
    code+=bytes.fromhex('8f00707e7b8f08707e3b8f0a707e');finish=0xC0FF00+len(code)
    code+=bytes((0x4C,entry&255,entry>>8&255));counts=Counter(row[0] for row in rows)
    lua=['local output=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))',
         'local rows={'+','.join('{'+','.join(map(str,(0 if k=='map' else 1,x,y)))+'}' for k,_,x,y in rows)+'}',
         'local mem=emu.memType.snesWorkRam','local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256)%256,mem) end',
         'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end',
         'local index=0;local mapcalls=0;local dircalls=0;w16(0x7200,0x55aa)',
         'emu.addMemoryCallback(function() index=index+1;local r=assert(rows[index],"past corpus");w16(0x7104,r[1]);w16(0x7100,r[2]);w16(0x7102,r[3]) end,emu.callbackType.exec,'+str(entry)+')',
         'emu.addMemoryCallback(function() assert(rows[index][1]==0,"wrong helper");mapcalls=mapcalls+1 end,emu.callbackType.exec,'+str(helpers['GET_MAP_ENEMY_PLACEMENT']['address'])+')',
         'emu.addMemoryCallback(function() assert(rows[index][1]==1,"wrong helper");dircalls=dircalls+1 end,emu.callbackType.exec,'+str(helpers['CAN_ENEMY_RUN_IN_DIRECTION']['address'])+')',
         'emu.addMemoryCallback(function() assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"CPU frame corrupt");assert(r16(0x7200)==0x55aa,"protected RAM corrupt");output:write(string.format("[%d,%d]\\n",index,r16(0x7000)));',
         'if index==#rows then assert(mapcalls=='+str(counts['map'])+' and dircalls=='+str(counts['direction'])+',"helper count differs");output:flush();output:close();emu.log("ENEMY_HELPERS_COMPLETE "..index);emu.breakExecution() end end,emu.callbackType.exec,'+str(finish)+')']
    script=out/'helpers.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
    rom=a.rom if mode=='original' else a.redux_rom
    proc=subprocess.run([str(a.oracle.resolve()),str(rom.resolve()),'--home',str(out/'oracle-home'),'--frames','5000','--timeout','60','--lua-timeout','10','--lua-allow-io','--lua',str(script),'--write-memory','SnesPrgRom:0xff00:'+code.hex(),'--set-pc','0xc0ff00','--cpu','Snes'],capture_output=True,timeout=70)
    (out/'oracle.jsonl').write_bytes(proc.stdout);(out/'oracle.stderr').write_bytes(proc.stderr)
    events=[json.loads(x) for x in proc.stdout.decode().splitlines()];logs=[r for r in events if r['event']=='lua_log']
    if proc.returncode or not events[-1].get('ok') or events[-1].get('reason')!='debugger_break' or any(r['error_count'] for r in logs):raise ValueError('Original helper corpus incomplete')
    if sum('ENEMY_HELPERS_COMPLETE '+str(len(rows)) in r['text'] for r in logs)!=1:raise ValueError('Exact machine completion marker missing')
    got=[json.loads(x) for x in samples.read_text(encoding='utf-8').splitlines()]
    if [r[0] for r in got]!=list(range(1,len(rows)+1)):raise ValueError('Incomplete/unordered original samples')
    return got,{'Calls':len(got),'CallsByHelper':dict(counts),'StackDirectPageProtectedRamPassed':True,
                'CompleteOrderedCorpusVerified':True,'CallerSha256':hashlib.sha256(code).hexdigest(),
                'LuaSha256':sha(script),'SamplesSha256':sha(samples),'OriginalMachineCodeExecuted':True}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','redux-rom','oracle','ca65','ld65','native-source','build','runtime','original-assets','redux-assets','scratch','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.scratch=local_scratch(a.scratch);a.native_source=a.native_source.resolve();a.build=a.build.resolve();a.runtime=a.runtime.resolve()
    if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch/output required')
    rom=a.rom.read_bytes();redux=a.redux_rom.read_bytes()
    if len(rom)!=0x300000 or hashlib.sha1(rom).hexdigest()!=US_SHA1:raise ValueError('Exact clean USA ROM required')
    if len(redux)!=0x600000 or hashlib.sha256(redux).hexdigest()!='c2a2fc98c7e6518b797959ffadf24ca4db8b4d7745ed3a9eb92eee106db1d0ab':raise ValueError('Exact pinned Redux ROM required')
    files=(a.rom,a.redux_rom,a.oracle,a.ca65,a.ld65,a.original_assets,a.redux_assets,a.runtime/'player.exe',a.runtime/'observer.exe',a.build/'game_lib/libearthbound_game.a',a.native_source/'src/game/overworld_spawn.c',a.native_source/'src/game/battle.h',a.native_source/'include/structs.asm',a.native_source/'include/enums.asm',a.native_source/'include/macros.asm',a.native_source/'asm/system/math/mult168.asm',*[a.native_source/'asm'/row[1] for row in CATALOG],Path(__file__),Path(mapping.__file__))
    inputs={str(path):sha(path) for path in files};a.scratch.mkdir(parents=True)
    globals_,helpers,proof=identify(a,a.scratch,rom,redux)
    tables,packed=packed_review(a,helpers,{'original':rom,'redux':redux});rows=corpus();modes=[]
    for mode,assets in (('original',a.original_assets),('redux',a.redux_assets)):
        reference,meta=machine(a,a.scratch/('machine-'+mode),mode,helpers[mode],rows)
        out=a.scratch/('native-'+mode);out.mkdir();exe,built=private_build(a,out,DRIVER);session=out/'session';session.mkdir()
        cases=out/'cases.tsv';cases.write_text(''.join(f'{i+1} {int(k=="direction")} {x} {y}\n' for i,(k,_,x,y) in enumerate(rows)),encoding='utf-8')
        proc=subprocess.run([str(exe),str(assets.resolve()),str(session),str(cases),str(int(mode=='redux'))],capture_output=True,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),timeout=30)
        (out/'native.log').write_bytes(proc.stdout+proc.stderr)
        if proc.returncode:raise ValueError('Native production helper corpus failed')
        got=[json.loads(x[len('ENEMY_HELPER '):]) for x in proc.stdout.decode(errors='replace').splitlines() if x.startswith('ENEMY_HELPER ')]
        if [r[0] for r in got]!=list(range(1,len(rows)+1)):raise ValueError('Native ordered corpus incomplete')
        grid,flags=packed[mode];pack_errors=[]
        for i,(kind,_,x,y) in enumerate(rows):
            expected=struct.unpack_from('<H',grid,y*256+x*2)[0] if kind=='map' and x<128 and y<160 else 0 if kind=='map' else (0 if flags[y]&({0:4,4:2,8:1,12:1}[x&12]) else 128)
            if reference[i][1]!=expected:pack_errors.append(i+1)
        if pack_errors:raise ValueError('Actual machine result differs from byte-proven packed table at '+str(pack_errors[:10]))
        diff=[{'Index':i+1,'Helper':rows[i][0],'Group':rows[i][1],'Input':[rows[i][2],rows[i][3]],'ActualSourceMachine':r[1],'ActualProductionNative':n[1]} for i,(r,n) in enumerate(zip(reference,got)) if r!=n]
        modes.append({'Mode':mode,'ExecutedCases':len(rows),'MismatchCount':len(diff),'MismatchesByHelper':dict(Counter(r['Helper'] for r in diff)),'FirstMismatches':diff[:25],'MachineEvidence':meta,'NativeEvidence':built,'EveryMachineResultMatchesActualPackData':True})
    if any(sha(Path(path))!=value for path,value in inputs.items()):raise ValueError('Immutable audit input changed')
    report={'format':'snes-enemy-placement-direction-oracle-v1','Passed':not any(r['MismatchCount'] for r in modes),'CasesPerMode':len(rows),'CaseGroups':dict(Counter(r[1] for r in rows)),'SourceProof':proof,'PackedTableEvidence':tables,'Modes':modes,'InputIdentities':inputs,'OwnerSavesTouched':False,'SharedSourceEdited':False,'SharedBuildEdited':False,'FullStoryVerified':False,'Limits':['Every valid 128x160 map-placement cell and all 231 enemy records are checked. Selected full-word flags/boundaries are covered, not all 65536 squared coordinates.','These two helpers are tested directly with actual packs and production archive; whole spawning, pathfinding, encounters, RNG ordering and door/stair integration are separate.','Neither original nor native direction helper has an enemy_id range guard. Invalid IDs are not executed: native out-of-range array access is undefined, not a meaningful parity fixture.','Native missing-assets fallbacks are deliberate host-side guards and cannot match an original ROM that always supplies its tables; missing/corrupt pack behavior is outside this corpus.','Native map >=128 or >=160 guards exactly match source unsigned BCS comparisons. Actual run_flag record layout and all values are byte-proven independently of the formulas.','No ROM bytes, original tables, packs or saves are distributed by this runner or report.']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'Passed':report['Passed'],'CasesPerMode':len(rows),'Modes':[{k:r[k] for k in ('Mode','ExecutedCases','MismatchCount')} for r in modes]}),flush=True)
    if not report['Passed']:raise SystemExit(1)


if __name__=='__main__':main()
