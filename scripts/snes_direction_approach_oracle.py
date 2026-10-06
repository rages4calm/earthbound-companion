# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only fine/encounter direction audit against untouched local SNES CPUs.

All inputs are explicit local files. Original source is assembled only to prove
complete unchanged machine-body identities. The oracle executes those bodies
from local Original/pinned Redux ROMs, never a Python angle formula. Own callers
and private logs are the only generated artifacts; no ROM is changed or bundled.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

from check_jev_observer_parity import local_scratch
from party_follow_private_build import private_build
from snes_movement_helpers_oracle import sha, US_SHA1
import snes_position_arithmetic_oracle as mapping


DRIVER = r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdint.h>
#include "entity/entity.h"
int main(int argc,char**argv){
 if(argc!=2)return 2;FILE*f=fopen(argv[1],"r");if(!f)return 3;
 unsigned i,x,y,tx,ty;
 while(fscanf(f,"%u %u %u %u %u",&i,&x,&y,&tx,&ty)==5)
  printf("DIRECTION [%u,%u,%u]\n",i,calculate_direction_fine((int16_t)x,(int16_t)y,(int16_t)tx,(int16_t)ty),
   (uint16_t)calculate_direction_8((int16_t)x,(int16_t)y,(int16_t)tx,(int16_t)ty));
 fclose(f);return 0;
}
'''


def build_native(a,out):
    exe,proof=private_build(a,out,DRIVER)
    if not a.corrected_entity_source:return exe,proof
    source=a.corrected_entity_source.resolve()
    if source!=a.native_source/'src/entity/entity.c':raise ValueError('Only actual reviewed entity.c replacement allowed')
    commands=json.loads((a.build/'compile_commands.json').read_text(encoding='utf-8'))
    entry=next(r for r in commands if r['file'].endswith('/entity/entity.c'))
    if '"' in entry['command'] or "'" in entry['command']:raise ValueError('Review quoted entity compile flags')
    flags=entry['command'].split();compiler=Path(flags[0]);obj=out/'entity.c.obj'
    flags[flags.index('-o')+1]=str(obj);flags[flags.index('-c')+1]=str(source)
    def run(cmd,name,cwd=None):
        result=subprocess.run(list(map(str,cmd)),cwd=cwd or a.build,capture_output=True,timeout=30)
        (out/name).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise ValueError(name+': '+result.stderr.decode(errors='replace'))
    source_hash=sha(source);run(flags,'compile-corrected-entity.log')
    lib=a.build/'game_lib/libearthbound_game.a';lib_hash=sha(lib);copied=out/'corrected-private-libearthbound_game.a';shutil.copy2(lib,copied)
    run([compiler.parent/'ar.exe','r',copied,obj],'replace-private-entity.log')
    old=out/'original-members';new=out/'corrected-members';old.mkdir();new.mkdir()
    run([compiler.parent/'ar.exe','x',lib],'extract-original.log',old)
    run([compiler.parent/'ar.exe','x',copied],'extract-corrected.log',new)
    old_hashes={p.name:sha(p) for p in old.iterdir() if p.is_file()};new_hashes={p.name:sha(p) for p in new.iterdir() if p.is_file()}
    if old_hashes.keys()!=new_hashes.keys() or [k for k in old_hashes if old_hashes[k]!=new_hashes[k]]!=['entity.c.obj']:
        raise ValueError('Private replacement changed unexpected archive members')
    ninja=(a.build/'build.ninja').read_text(encoding='utf-8')
    match=re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_Release (.*?)\n(.*?)(?=\n\n)',ninja,re.M|re.S)
    objects=match[1].split(' | ',1)[0].split();libs=re.search(r'^  LINK_LIBRARIES = (.*)$',match[2],re.M)[1].split()
    main=next(v for v in objects if v.replace('\\','/').endswith('/main.c.obj'))
    objects=[str(out/'platform-main.c.obj') if v==main else str(a.build/v) for v in objects]
    indices=[i for i,v in enumerate(libs) if v.replace('\\','/').endswith('game_lib/libearthbound_game.a')]
    if len(indices)!=1:raise ValueError('Unexpected production library link layout')
    libs[indices[0]]=str(copied)
    run([compiler,'-O3','-DNDEBUG',out/'party_driver.c.obj',*objects,'-o',exe,
         '-Wl,--major-image-version,0,--minor-image-version,0',*libs],'link-corrected-private.log')
    if sha(source)!=source_hash or sha(lib)!=lib_hash:raise ValueError('Actual source or frozen library changed during private proof')
    proof.update(ExecutableSha256=sha(exe),UntouchedProductionLibraryLinked=False,
                 PrivateCorrectedEntityReplacement=dict(ActualSourcePath=str(source),SourceSha256=source_hash,PrivateLibrarySha256=sha(copied),
                      ChangedMembers=['entity.c.obj'],ArchiveMembersCompared=len(old_hashes),OtherMembersByteIdentical=True,
                      OriginalObjectSha256=old_hashes['entity.c.obj'],CorrectedObjectSha256=new_hashes['entity.c.obj']))
    return exe,proof


def identify(a,out,rom,redux):
    saved=mapping.ROUTINES
    try:
        mapping.ROUTINES=()
        globals_,known,proof=mapping.identify(a,out,rom)
    finally:
        mapping.ROUTINES=saved
    folder=out/'source-mapping'
    prelude=(folder/'movement_speeds.asm').read_text(encoding='utf-8').split('.SEGMENT "CODE"',1)[0]
    include=['--cpu','65816','-D','USA','-I',folder/'include-overlay','-I',a.native_source/'include','-I',a.native_source/'asm']
    catalog=(('DIRECTION_OFFSET_TABLE','data/math/direction_offset_table.asm',None),
             ('ATAN2_LOOKUP_TABLE','data/math/atan2_lookup_table.asm',None),
             ('DIVISION16S','system/math/division16s.asm',None),
             ('CALCULATE_DIRECTION_FROM_POSITIONS','misc/calculate_direction_from_positions.asm',0xC41EFF))
    for symbol,relative,candidate in catalog:
        source=folder/(symbol.lower()+'.asm');obj=source.with_suffix('.o');blob=source.with_suffix('.bin')
        extra='.EXPORT DIVISION16S_DIVISOR_POSITIVE\n' if symbol=='DIVISION16S' else ''
        source.write_text(prelude+''.join(f'{k} := ${v:06X}\n' for k,v in known.items())+
                          '.SEGMENT "CODE"\n.A16\n.I16\n.EXPORT '+symbol+'\n'+extra+
                          '.INCLUDE "'+relative+'"\n',encoding='utf-8')
        mapping.run([a.ca65,*include,source,'-o',obj,'-l',source.with_suffix('.lst')],source.with_suffix('.compile.log'))
        cfg=folder/'code.cfg'
        if candidate:
            # Source's documented address is only a candidate. Full unmasked
            # body equality and uniqueness, below, are mandatory acceptance.
            cfg=source.with_suffix('.cfg')
            cfg.write_text((folder/'code.cfg').read_text(encoding='utf-8').replace('start=$C00000',f'start=${candidate:06X}'),encoding='utf-8')
        lbl=source.with_suffix('.lbl')
        mapping.run([a.ld65,'-C',cfg,'-o',blob,'-Ln',lbl,obj],source.with_suffix('.link.log'))
        body=blob.read_bytes();address=mapping.find_unique(rom,body,symbol)
        if candidate and address!=candidate:raise ValueError('Source candidate does not match complete original body')
        pos=address-0xC00000
        if redux[pos:pos+len(body)]!=body:raise ValueError('Pinned Redux changes direction body; separate hook proof needed')
        known[symbol]=address
        if symbol=='DIVISION16S':
            source_labels=mapping.labels(lbl)
            known['DIVISION16S_DIVISOR_POSITIVE']=address+source_labels['DIVISION16S_DIVISOR_POSITIVE']-source_labels['DIVISION16S']
        proof.append(dict(Symbol=symbol,Source=relative,SourceSha256=sha(a.native_source/'asm'/relative),Address=f'{address:06X}',
                          CompleteUnmaskedUniqueByteEqualLength=len(body),CompleteBodySha256=sha(blob),PinnedReduxBodyByteIdentical=True,
                          EntryIndexWidthExplicitly16=True))
    return known,proof


def corpus():
    rows=[]
    # Ordinary local map coordinates; all relative pixels in a 129px square.
    for dx in range(-64,65):
        for dy in range(-64,65):rows.append(('ordinary-local-pixel-vectors',1024,1024,1024+dx,1024+dy))
    # Normalization and narrow sector boundaries at longer distances.
    for x in range(1,513):
        for threshold in (0,13,38,64,92,121,153,190,232,282,345,427,541,715,1021,1723,5181):
            y=(x*threshold)//256
            for step in (-1,0,1):
                if y+step<0 or y+step>8191:continue
                for sx,sy in ((1,1),(1,-1),(-1,1),(-1,-1)):
                    rows.append(('source-ratio-bin-boundaries',8192,8192,8192+sx*x,8192+sy*(y+step)))
    # Full 16-bit differences are deliberately distinct from ordinary maps.
    bounds=(0,1,255,256,32767,32768,32769,65534,65535)
    rows.extend(('synthetic-wrapped-coordinate-boundaries',x,y,tx,ty)
                for x in bounds for y in bounds for tx,ty in ((0,0),(32767,32768),(65535,65535)))
    # Keep ordered, deduplicated inputs with the first, more ordinary group.
    seen=set();unique=[]
    for row in rows:
        if row[1:] not in seen:unique.append(row);seen.add(row[1:])
    return unique


def machine(a,out,mode,addresses,rows):
    out.mkdir();samples=out/'samples.jsonl'
    code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
    entry=0xC0FF00+len(code)
    # A=fromX, X=fromY, Y=toX, caller DP+0E=toY, as read by actual function.
    code+=bytes.fromhex('af02717eaaaf04717ea8af00717e')
    code+=bytes((0x22,))+addresses['CALCULATE_DIRECTION_FROM_POSITIONS'].to_bytes(3,'little')
    code+=bytes.fromhex('8f00707ea0002018690010')
    code+=bytes((0x22,))+addresses['DIVISION16S_DIVISOR_POSITIVE'].to_bytes(3,'little')
    code+=bytes.fromhex('8f02707e7b8f08707e3b8f0a707e');finish=0xC0FF00+len(code)
    code+=bytes((0x4C,entry&255,entry>>8&255))
    lua=['local output=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))',
         'local rows={'+','.join('{'+','.join(map(str,row[1:]))+'}' for row in rows)+'}',
         'local mem=emu.memType.snesWorkRam',
         'local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256)%256,mem) end',
         'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end',
         'local index=0;local finecalls=0;local quantcalls=0;w16(0x7200,0x55aa)',
         'emu.addMemoryCallback(function() index=index+1;local r=assert(rows[index],"past corpus");w16(0x7100,r[1]);w16(0x7102,r[2]);w16(0x7104,r[3]);w16(0x100e,r[4]) end,emu.callbackType.exec,'+str(entry)+')',
         'emu.addMemoryCallback(function() finecalls=finecalls+1 end,emu.callbackType.exec,'+str(addresses['CALCULATE_DIRECTION_FROM_POSITIONS'])+')',
         'emu.addMemoryCallback(function() quantcalls=quantcalls+1 end,emu.callbackType.exec,'+str(addresses['DIVISION16S_DIVISOR_POSITIVE'])+')',
         'emu.addMemoryCallback(function() assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"CPU frame corrupt");assert(r16(0x7200)==0x55aa,"protected RAM corrupt");output:write(string.format("[%d,%d,%d]\\n",index,r16(0x7000),r16(0x7002)));',
         'if index==#rows then assert(finecalls==#rows and quantcalls==#rows,"call counts differ");output:flush();output:close();emu.log("DIRECTION_ORACLE_COMPLETE "..index);emu.breakExecution() end end,emu.callbackType.exec,'+str(finish)+')']
    script=out/'direction.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
    rom=a.rom if mode=='original' else a.redux_rom
    result=subprocess.run([str(a.oracle.resolve()),str(rom.resolve()),'--home',str(out/'oracle-home'),'--frames','20000','--timeout','60','--lua-timeout','10','--lua-allow-io','--lua',str(script),'--write-memory','SnesPrgRom:0xff00:'+code.hex(),'--set-pc','0xc0ff00','--cpu','Snes'],capture_output=True,timeout=70)
    (out/'oracle.jsonl').write_bytes(result.stdout);(out/'oracle.stderr').write_bytes(result.stderr)
    events=[json.loads(line) for line in result.stdout.decode().splitlines()];logs=[r for r in events if r['event']=='lua_log']
    if result.returncode or not events[-1].get('ok') or events[-1].get('reason')!='debugger_break' or any(r['error_count'] for r in logs):raise ValueError('Actual direction oracle did not complete')
    if sum('DIRECTION_ORACLE_COMPLETE '+str(len(rows)) in r['text'] for r in logs)!=1:raise ValueError('Exact completion marker missing')
    got=[json.loads(line) for line in samples.read_text(encoding='utf-8').splitlines()]
    if [r[0] for r in got]!=list(range(1,len(rows)+1)):raise ValueError('Actual CPU samples incomplete or unordered')
    if any(r[2]>7 for r in got):raise ValueError('Actual unsigned quantization outside eight directions')
    return got,dict(Calls=len(got),FineAndActualDivisionCallsEach=len(got),ActualUntouchedRomBodyExecuted=True,
                    StackDirectPageProtectedRamPassed=True,OrderedCompleteCorpusVerified=True,CallerSha256=hashlib.sha256(code).hexdigest(),
                    LuaSha256=sha(script),SamplesSha256=sha(samples))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','redux-rom','oracle','ca65','ld65','native-source','build','runtime','scratch','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--corrected-entity-source',type=Path,help='Privately replace exactly the actual reviewed entity.c object; never a shared build.')
    a=p.parse_args();a.native_source=a.native_source.resolve();a.build=a.build.resolve();a.runtime=a.runtime.resolve();a.scratch=local_scratch(a.scratch)
    if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch/output required')
    original=a.rom.read_bytes();redux=a.redux_rom.read_bytes()
    if len(original)!=0x300000 or hashlib.sha1(original).hexdigest()!=US_SHA1:raise ValueError('Exact clean USA ROM required')
    if len(redux)!=0x600000 or hashlib.sha256(redux).hexdigest()!='c2a2fc98c7e6518b797959ffadf24ca4db8b4d7745ed3a9eb92eee106db1d0ab':raise ValueError('Exact pinned Redux ROM required')
    files=(a.rom,a.redux_rom,a.oracle,a.ca65,a.ld65,a.runtime/'player.exe',a.runtime/'observer.exe',a.build/'game_lib/libearthbound_game.a',
           a.native_source/'src/entity/entity.c',a.native_source/'src/game/overworld_spawn.c',a.native_source/'asm/overworld/initiate_enemy_encounter.asm',
           a.native_source/'include/macros.asm',Path(__file__),Path(mapping.__file__))
    inputs={str(path):sha(path) for path in files};a.scratch.mkdir(parents=True)
    addresses,proof=identify(a,a.scratch,original,redux);rows=corpus()
    out=a.scratch/'production';out.mkdir();exe,built=build_native(a,out)
    cases=out/'cases.tsv';cases.write_text(''.join(f'{i+1} '+' '.join(map(str,row[1:]))+'\n' for i,row in enumerate(rows)),encoding='utf-8')
    result=subprocess.run([str(exe),str(cases)],capture_output=True,timeout=30);(out/'native.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise ValueError('Actual untouched production direction helper failed')
    native=[json.loads(line[len('DIRECTION '):]) for line in result.stdout.decode().splitlines() if line.startswith('DIRECTION ')]
    if [r[0] for r in native]!=list(range(1,len(rows)+1)):raise ValueError('Production corpus incomplete/unordered')
    modes=[];references={}
    for mode in ('original','redux'):
        reference,meta=machine(a,a.scratch/('machine-'+mode),mode,addresses,rows);references[mode]=reference
        differences=[dict(Index=i+1,Group=rows[i][0],Positions=list(rows[i][1:]),ActualCpuFine=s[1],ProductionFine=n[1],
                          ActualCpuEightWay=s[2],ProductionEightWay=n[2]) for i,(s,n) in enumerate(zip(reference,native)) if s!=n]
        eight=[row for row in differences if row['ActualCpuEightWay']!=row['ProductionEightWay']]
        modes.append(dict(Mode=mode,Cases=len(rows),FineMismatchCount=sum(s[1]!=n[1] for s,n in zip(reference,native)),
                          EightWayMismatchCount=len(eight),EightWayMismatchGroups=dict(Counter(r['Group'] for r in eight)),
                          FirstEightWayMismatches=eight[:32],FirstFineMismatches=differences[:16],MachineEvidence=meta))
    if references['original']!=references['redux']:raise ValueError('Identical byte-proven machine functions produced differing results')
    if {path:sha(Path(path)) for path in inputs}!=inputs:raise ValueError('Input/shared source changed during audit')
    report=dict(Schema='native-direction-approach-machine-audit-v1',EvidenceComplete=True,NativeEquivalent=all(m['FineMismatchCount']==0 for m in modes),
                FullConversionVerified=False,FullPlaythroughVerified=False,Inputs=inputs,SourceProof=proof,
                Cases=len(rows),CaseGroups=dict(Counter(r[0] for r in rows)),ProductionEvidence=built,Modes=modes,
                BothModesActualMachineResultsIdentical=True,NativeSourceEdited=False,SharedBuildEdited=False,OwnerSavesTouched=False,
                Reachability='Ordinary pixel vectors use legal positive local map coordinates; synthetic 16-bit boundaries are separately labeled. This is function-level input reachability, not a recorded real contact route.',
                Downstream='initiate_enemy_encounter in both source and native consumes the tested eight-way enemy-to-target direction for facing/initiative. Fine helpers also serve scripted facing/pursuit. Full swirl/combat/AI outcomes are not exercised here.',
                Limitations=['Exact helper/direction quantization only; no complete encounter pipeline comparison.',
                             'No natural collision trajectory or real map contact geometry asserted by this prepared input corpus.',
                             'No claim that these differences caused owner hotel/stairs blockers.'],
                ReproductionFlags={key:str(value) for key,value in vars(a).items()})
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(Output=str(a.output),EvidenceComplete=True,Cases=len(rows),Modes=[{k:m[k] for k in ('Mode','FineMismatchCount','EightWayMismatchCount')} for m in modes])))


if __name__=='__main__':main()
