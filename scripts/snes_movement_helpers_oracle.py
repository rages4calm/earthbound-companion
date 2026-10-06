# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare isolated native movement helpers with actual clean USA SNES code.

Explicit local ROM, mesen-agent, compiler and source inputs are required. Only
a small test caller is installed in the emulator's temporary memory. The owner
ROM and original helpers are never written. All grids are synthetic test data;
this script contains no ROM assets or original machine-code byte sequences.
Results are helper parity evidence, not full-game or full-playthrough parity.
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

US_SHA1='d67a8ef36ef616bc39306aa1b486e1bd3047815a'
CATALOG=(
    ('get_collision_at_pixel',0xC05FD1,0xC05FF6,'A=x, X=y; RTS, original C direct-page frame'),
    ('test_collision_north',0xC057E8,0xC0583C,'no parameters; RTS'),
    ('test_collision_south',0xC0583C,0xC05890,'no parameters; RTS'),
    ('test_collision_west',0xC05890,0xC059EF,'no parameters; RTS, original C direct-page frame'),
    ('test_collision_east',0xC059EF,0xC05B4E,'no parameters; RTS, original C direct-page frame'),
    ('test_collision_diagonal',0xC05B4E,0xC05B7B,'A=direction 1,3,5,7; RTS, original C direct-page frame'),
)
DEPENDENCIES=(('get_collision_tile_and_check_ladder',0xC054C9,0xC05503),
              ('check_collision_tile_pattern',0xC05769,0xC057E8))


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def function(text,name):
    match=re.search(r'^(?:static )?[^\n]+ '+re.escape(name)+r'\(',text,re.M)
    if not match:raise ValueError('Missing actual native function '+name)
    start=match.start();opening=text.index('{',start);depth=1;end=opening+1
    while depth:
        if text[end]=='{':depth+=1
        if text[end]=='}':depth-=1
        end+=1
    return text[start:end]+'\n'


def tile_index(x,y):
    # Synthetic fixture placement, not a replacement oracle. Both actual
    # implementations independently consume the same prepared collision grid.
    return ((((y&65535)>>3)&63)*64)+(((x&65535)>>3)&63)


def corpus():
    cases=[]
    def add(label,kind,x,y,arg,grid,control=0):
        cells=sorted(grid.items())
        cases.append((label,(kind,x&65535,y&65535,arg,control,0xA5A5,0xBEEF,0xCAFE),cells))
    values=(0,1,3,4,7,8,9,15,16,511,512,513,32760,32767,32768,32769,65528,65531,65532,65535)
    flags=(0,1,4,8,0x10,0x20,0x40,0x80,0x90,0xD0,0xFF)
    for x in values:
        for y in values:
            for flag in flags:
                add('pixel-coordinate-boundaries',0,x,y,0,{tile_index(x,y+4):flag})
    for flag in range(256):add('pixel-all-byte-flags',0,105,97,0,{tile_index(105,101):flag},control=0xFFFF)
    offsets=((-8,0),(0,0),(7,0),(-8,7),(0,7),(7,7))
    def point_grid(x,y,mask,surface):
        grid={}
        for i,(dx,dy) in enumerate(offsets):
            at=tile_index(x+dx,y+dy)
            grid[at]=grid.get(at,0)|surface|(0x40 if mask&(1<<i) else 0)
        return grid
    def all_directions(label,x,y,grid,control=0):
        for kind in range(1,5):add(label,kind,x,y,0,grid,control)
        for direction in (1,3,5,7):add(label,5,x,y,direction,grid,control)
    for xphase in range(8):
        for yphase in range(8):
            x,y=104+xphase,96+yphase
            for mask in range(64):
                for surface in (0,0x10):
                    all_directions('all-tile-phases-primary-wall-masks',x,y,point_grid(x,y,mask,surface))
            # Independent west/east outer corners and extended check tiles.
            # Some fixture points alias naturally at particular tile phases.
            for kind,sign,primary in ((3,-1,(0,1,8,9)),(4,1,(0,4,0x20,0x24))):
                for mask in primary:
                    for outside in range(16):
                        grid=point_grid(x,y,mask,0x10)
                        points=((sign*4,-2),(sign*4,9),(sign*12,0),(sign*12,7))
                        for i,(dx,dy) in enumerate(points):
                            at=tile_index(x+dx,y+dy)
                            grid[at]=grid.get(at,0)|(0xC0 if outside&(1<<i) else 0)
                        add('cardinal-corner-and-extended-check',kind,x,y,0,grid)
    boundary=((0,0),(0,65535),(65535,0),(65535,65535),(32767,32767),(32768,32768),
              (65532,65532),(511,511),(512,512),(513,513))
    for x,y in boundary:
        for mask in range(64):
            for control in (0,1,2,0xFFFF):
                all_directions('wrapped-coordinate-and-surface-control',x,y,point_grid(x,y,mask,0x90),control)
    return cases


def caller():
    # Own caller only: native CPU, A/X/Y16, SP1FFF, DP1000, DBR7E. Every
    # original routine is called with JSR and returns through its real RTS.
    code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
    entry=0xC0FF00+len(code)
    code+=bytes.fromhex('af08717eaa')
    indirect=len(code);code+=bytes((0xFC,0,0))
    code+=bytes.fromhex('8f00707e7b8f08707e3b8f0a707e')
    finish=0xC0FF00+len(code)
    code+=bytes((0x4C,entry&255,(entry>>8)&255))
    starts=[]
    for kind,(_,address,_,_) in enumerate(CATALOG):
        starts.append(0xC0FF00+len(code))
        if kind==0:code+=bytes.fromhex('af04717eaaaf02717e')
        elif kind==5:code+=bytes.fromhex('af06717e')
        code+=bytes((0x20,address&255,(address>>8)&255,0x60))
    table=0xC0FF00+len(code)
    code[indirect+1:indirect+3]=struct.pack('<H',table&65535)
    code+=b''.join(struct.pack('<H',at&65535) for at in starts)
    if len(code)>256:raise ValueError('Caller would exceed private injection space')
    return code,entry,finish


def native_probe(a,out,source,cases):
    names=[row[0] for row in DEPENDENCIES]+[row[0] for row in CATALOG]
    helpers=''.join(function(source,name) for name in names)
    tables='\n'.join(re.search(r'^static const (?:u?int16_t) '+name+r'\[\d+\] = [^;]+;',source,re.M).group()
                     for name in ('collision_x_offsets','collision_y_offsets','diagonal_masks'))
    prefix='#include "game/map_loader.h"\n#include "game/overworld.h"\n#include "core/log.h"\n#include <stdio.h>\n#include <string.h>\nMapLoaderState ml;OverworldState ow;\nstatic uint16_t set_temp_entity_surface_flags,temp_entity_surface_flags;\n'
    body=r'''
int main(int argc,char**argv){
 if(argc!=2)return 2;FILE*f=fopen(argv[1],"rb");if(!f)return 3;
 uint16_t h[9];while(fread(h,2,9,f)==9){
  memset(ml.loaded_collision_tiles,0,4096);
  for(unsigned i=0;i<h[8];i++) {uint16_t at;unsigned char value;
   if(fread(&at,2,1,f)!=1||fread(&value,1,1,f)!=1||at>=4096)return 4;
   ml.loaded_collision_tiles[at]=value;
  }
  ow.checked_collision_left_x=h[1];ow.checked_collision_top_y=h[2];
  set_temp_entity_surface_flags=h[4];temp_entity_surface_flags=h[5];
  ow.ladder_stairs_tile_x=h[6];ow.ladder_stairs_tile_y=h[7];
  uint16_t value;
  switch(h[0]){
   case 0:value=get_collision_at_pixel((int16_t)h[1],(int16_t)h[2]);break;
   case 1:value=test_collision_north();break;case 2:value=test_collision_south();break;
   case 3:value=test_collision_west();break;case 4:value=test_collision_east();break;
   case 5:value=test_collision_diagonal((int16_t)h[3]);break;default:return 5;
  }
  printf("[%u,%u,%u,%u,%u,%u,%u]\n",value,temp_entity_surface_flags,
   (uint16_t)ow.ladder_stairs_tile_x,(uint16_t)ow.ladder_stairs_tile_y,
   (uint16_t)ow.checked_collision_left_x,(uint16_t)ow.checked_collision_top_y,set_temp_entity_surface_flags);
 }int failed=ferror(f);fclose(f);return failed?4:0;
}
'''
    c=out/'native-probe.c';c.write_text(prefix+tables+'\n'+helpers+body,encoding='utf-8')
    inputs=out/'inputs.bin'
    inputs.write_bytes(b''.join(struct.pack('<9H',*h,len(cells))+b''.join(struct.pack('<HB',i,v) for i,v in cells) for _,h,cells in cases))
    exe=out/'native-probe.exe'
    includes=[a.native_source/'src',a.native_source/'src/include',a.generated,a.native_source/'src/data/runtime_generated']
    cmd=[str(a.compiler.resolve()),'-std=c11','-O2','-DEB_VIEWPORT_WIDTH=512','-DEB_VIEWPORT_HEIGHT=256','-DUSA=1']
    cmd+=['-I'+str(path.resolve()) for path in includes]+[str(c),'-o',str(exe)]
    run=subprocess.run(cmd,capture_output=True,timeout=30);(out/'compile.log').write_bytes(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError('Native probe compilation failed; inspect compile.log')
    run=subprocess.run([str(exe),str(inputs)],capture_output=True,timeout=30)
    if run.returncode:raise RuntimeError('Native probe did not complete')
    (out/'native-samples.jsonl').write_bytes(run.stdout)
    rows=[json.loads(line) for line in run.stdout.decode().splitlines()]
    if len(rows)!=len(cases) or any(len(row)!=7 for row in rows):raise RuntimeError('Native sample corpus incomplete')
    return rows,exe,inputs,hashlib.sha256((tables+helpers).encode()).hexdigest()


def machine_reference(a,out,cases):
    code,entry,finish=caller();samples=out/'machine-samples.csv'
    lua=['local output=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))','local cases={']
    for _,h,cells in cases:
        lua.append('{'+','.join(map(str,h))+',{'+','.join('{'+str(i)+','+str(v)+'}' for i,v in cells)+'}},')
    lua+=['}','local mem=emu.memType.snesWorkRam',
          'local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256),mem) end',
          'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end',
          'for i=0,4095 do emu.write(0xe000+i,0,mem) end',
          'w16(0x7200,0x55aa);local index=0;local previous={};local calls={0,0,0,0,0,0}',
          'emu.addMemoryCallback(function()',
          ' index=index+1;local c=cases[index];assert(c,"ran beyond corpus")',
          ' for _,p in ipairs(previous) do emu.write(0xe000+p[1],0,mem) end',
          ' for _,p in ipairs(c[9]) do emu.write(0xe000+p[1],p[2],mem) end;previous=c[9]',
          ' w16(0x7108,c[1]*2);w16(0x7102,c[2]);w16(0x7104,c[3]);w16(0x7106,c[4])',
          ' w16(0x5dac,c[2]);w16(0x5dae,c[3]);w16(0x5db4,c[5]);w16(0x5da4,c[6]);w16(0x5da8,c[7]);w16(0x5daa,c[8])',
          f'end,emu.callbackType.exec,{entry})']
    for kind,(_,address,_,_) in enumerate(CATALOG):
        lua.append(f'emu.addMemoryCallback(function() calls[{kind+1}]=calls[{kind+1}]+1 end,emu.callbackType.exec,{address})')
    lua+=['emu.addMemoryCallback(function()',
          ' assert(r16(0x7008)==0x1000,"direct page corrupted");assert(r16(0x700a)==0x1fff,"stack corrupted");assert(r16(0x7200)==0x55aa,"protected memory corrupted")',
          ' output:write(string.format("%d,%d,%d,%d,%d,%d,%d,%d\\n",index,r16(0x7000),r16(0x5da4),r16(0x5da8),r16(0x5daa),r16(0x5dac),r16(0x5dae),r16(0x5db4)))',
          ' if index==#cases then output:flush();output:close();emu.log("CORPUS_COMPLETE "..table.concat(calls,","));emu.breakExecution() end',
          f'end,emu.callbackType.exec,{finish})']
    script=out/'movement-helpers.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
    cmd=[str(a.oracle.resolve()),str(a.rom.resolve()),'--home',str(out/'oracle-home'),'--frames','4000',
         '--timeout','60','--lua-timeout','15','--lua-allow-io','--lua',str(script),
         '--write-memory','SnesPrgRom:0xff00:'+code.hex(),'--set-pc','0xc0ff00','--cpu','Snes']
    run=subprocess.run(cmd,capture_output=True,timeout=75)
    (out/'machine-oracle.jsonl').write_bytes(run.stdout);(out/'machine-oracle.stderr').write_bytes(run.stderr)
    records=[json.loads(line) for line in run.stdout.decode().splitlines()]
    logs=[row for row in records if row['event']=='lua_log'];summary=records[-1] if records else {}
    if run.returncode or summary.get('event')!='summary' or not summary.get('ok') or summary.get('reason')!='debugger_break' or not logs or any(row['error_count'] for row in logs):
        raise RuntimeError('Machine reference incomplete; inspect machine-oracle.jsonl')
    completion=[row['text'] for row in logs if 'CORPUS_COMPLETE ' in row['text']]
    if len(completion)!=1:raise RuntimeError('Missing or duplicate corpus completion')
    counts=list(map(int,completion[0].split('CORPUS_COMPLETE ')[1].strip().split(',')))
    expected=Counter(h[0] for _,h,_ in cases)
    if counts!=[expected[i] for i in range(6)]:raise RuntimeError('Actual original entry counts differ from corpus')
    values=[]
    for line in samples.read_text(encoding='utf-8').splitlines():
        if not re.fullmatch(r'\d+(,\d+){7}',line):raise RuntimeError('Malformed machine sample')
        row=list(map(int,line.split(',')));values.append((row[0],row[1:]))
    if [i for i,_ in values]!=list(range(1,len(cases)+1)):raise RuntimeError('Missing, duplicate or truncated machine samples')
    return values,counts,sha(script),hashlib.sha256(code).hexdigest()


def pixel_wrap_candidate(a,out,source,cases,values):
    """Optional isolated proposed correction, preserving the actual source
    baseline and every original-machine sample. Never edits shared C files."""
    old='    int16_t tile_y = (y + 4) >> 3;\n    int16_t tile_x = x >> 3;'
    new='    uint16_t py = (uint16_t)((uint16_t)y + 4u);\n    int16_t tile_y = (int16_t)(py >> 3);\n    int16_t tile_x = (int16_t)((uint16_t)x >> 3);'
    if source.count(old)!=1:raise ValueError('Review proposed pixel correction after source change')
    candidate=out/'isolated-pixel-wrap-candidate';candidate.mkdir()
    native,exe,inputs,bodysha=native_probe(a,candidate,source.replace(old,new),cases)
    bad=[i for i,ref in values if native[i-1]!=ref]
    result={'Passed':not bad,'ExecutedCases':len(values),'MismatchCount':len(bad),
            'CompiledIsolatedCandidateSha256':sha(exe),'CandidateBodiesSha256':bodysha,'InputSha256':sha(inputs),
            'ExistingActualMachineSamplesSha256':sha(out/'machine-samples.csv'),
            'SharedNativeSourceEdited':False,'SharedBuildsEdited':False,'ShippedFixClaimed':False,
            'proposedChange':'Cast x to uint16; wrap y+4 to uint16; use logical shifts before recording ladder tile coordinates.'}
    (candidate/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def previous_rows(binary,inputs,count):
    run=subprocess.run([str(binary.resolve()),str(inputs)],capture_output=True,timeout=30)
    if run.returncode:raise RuntimeError('Recorded previous probe failed to execute')
    rows=[json.loads(line) for line in run.stdout.decode().splitlines()]
    if len(rows)!=count or any(len(row)!=7 for row in rows):raise RuntimeError('Recorded previous probe does not implement this corpus ABI')
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','oracle','compiler','native-source','generated','scratch'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--output',type=Path,help='Optional metadata-only review JSON, outside immutable release reports.')
    p.add_argument('--pixel-wrap-candidate',action='store_true',help='Additionally compare a proposed uint16 pixel correction in a private probe; never edits actual native source.')
    p.add_argument('--previous-probe',type=Path,help='Recorded pre-fix native probe using this input ABI; its failures must reproduce against the new actual-machine corpus.')
    a=p.parse_args();out=local_scratch(a.scratch)
    if out.exists():raise ValueError('Use fresh isolated scratch; prior evidence is retained')
    if a.output and a.output.exists():raise ValueError('Choose a new review filename; existing reviews are preserved')
    for item in (a.rom,a.oracle,a.compiler):
        if not item.is_file():raise ValueError('Required local input missing: '+str(item))
    rom=a.rom.read_bytes()
    if len(rom)!=0x300000 or hashlib.sha1(rom).hexdigest()!=US_SHA1:raise ValueError('Exact unheadered clean EarthBound USA ROM required')
    sourcepath=a.native_source/'src/game/map_loader.c';source=sourcepath.read_text(encoding='utf-8')
    identities={'rom':sha(a.rom),'oracle':sha(a.oracle),'compiler':sha(a.compiler),'nativeSource':sha(sourcepath)}
    if a.previous_probe:
        if not a.previous_probe.is_file():raise ValueError('Recorded previous probe missing')
        identities['previousProbe']=sha(a.previous_probe)
    if (a.oracle.parent/'MesenCore.dll').is_file():identities['oracleCore']=sha(a.oracle.parent/'MesenCore.dll')
    mapping=[]
    for name,start,end,abi in CATALOG:
        path=a.native_source/f'asm/overworld/collision/{name}.asm';assembly=path.read_text(encoding='utf-8')
        if name.upper()+':' not in assembly:raise ValueError('Original source label changed '+name)
        mapping.append({'helper':name,'originalAddress':f'{start:06X}','endExclusive':f'{end:06X}',
                        'originalMachineBytesSha256':hashlib.sha256(rom[start-0xC00000:end-0xC00000]).hexdigest(),
                        'originalAsmPath':str(path.relative_to(a.native_source)).replace('\\','/'),'originalAsmSha256':sha(path),'abi':abi})
    out.mkdir(parents=True);cases=corpus()
    native,probe,inputs,bodysha=native_probe(a,out,source,cases)
    values,counts,luasha,callersha=machine_reference(a,out,cases)
    candidate=pixel_wrap_candidate(a,out,source,cases,values) if a.pixel_wrap_candidate else None
    previous=previous_rows(a.previous_probe,inputs,len(cases)) if a.previous_probe else None
    previous_bad=[i for i,ref in values if previous is not None and previous[i-1]!=ref]
    if a.previous_probe and not previous_bad:raise RuntimeError('Requested recorded pre-fix failures were not reproduced')
    differences=[];mismatch_counts=Counter();labels=Counter(label for label,_,_ in cases)
    for i,ref in values:
        if native[i-1]==ref:continue
        label,h,cells=cases[i-1];name=CATALOG[h[0]][0];mismatch_counts[name]+=1
        differences.append({'case':i,'helper':name,'sourceCaseGroup':label,'input':list(h),
                            'syntheticGridCells':cells,'native':native[i-1],'originalMachine':ref})
    immutable={'rom':sha(a.rom),'oracle':sha(a.oracle),'compiler':sha(a.compiler),'nativeSource':sha(sourcepath)}
    if any(identities[k]!=immutable[k] for k in immutable):raise RuntimeError('An immutable audit input changed')
    report={'format':'native-movement-helper-micro-oracle-dev15-v1','Passed':not differences,'ExecutedCases':len(cases),'SkippedCases':0,
            'MismatchCount':len(differences),'MismatchesByHelper':dict(mismatch_counts),'MismatchExamples':differences[:80],
            'AllMismatchesPrivateArtifact':'native-mismatches.jsonl','OutputColumns':['returnWord','surfaceFlags','ladderTileX','ladderTileY','checkedLeftX','checkedTopY','surfaceControl'],
            'InputIdentities':identities,'OriginalRomSha1':US_SHA1,'HelperCatalog':mapping,
            'CaseGroups':dict(labels),'ActualOriginalEntryCalls':{row[0]:counts[i] for i,row in enumerate(CATALOG)},
            'CompiledActualNativeHelpersSha256':bodysha,'NativeProbeSha256':sha(probe),'InputSha256':sha(inputs),
            'PreviousProbeMismatchCount':len(previous_bad) if previous is not None else None,
            'PreviousProbeMismatchedCases':previous_bad,
            'OracleLuaSha256':luasha,'OwnCallerSha256':callersha,'OriginalMachineCodeExecuted':True,
            'StackAndDirectPageCanariesPassed':True,'ProtectedMemoryCanaryPassed':True,'CompleteOrderedCorpusVerified':True,
            'OwnerRomUnchanged':True,'OwnerSavesTouched':False,'SharedSourceEdited':False,'SharedBuildsEdited':False,
            'FullCompatibilityVerified':False,'FullPlaythroughVerified':False,
            'IsolatedPixelWrapCandidate':candidate,
            'ReturnAndSurfaceFlagsMatchAcrossCorpus':all(native[i-1][:2]==ref[:2] for i,ref in values),
            'MismatchColumns':dict(Counter(('returnWord','surfaceFlags','ladderTileX','ladderTileY','checkedLeftX','checkedTopY','surfaceControl')[n]
                                          for row in differences for n,(v,w) in enumerate(zip(row['native'],row['originalMachine'])) if v!=w)),
            'Runner':{'path':'tools/snes_movement_helpers_oracle.py','sha256':sha(Path(__file__))},
            'Limits':['Verbatim actual native helper bodies compiled in isolation, compared with untouched original 65816 routines; this is not full native executable or story parity.',
                      'Collision grids are synthetic. All sub-tile phases and primary wall masks, corners, wrapping and selected flag/control boundaries are exercised; all possible world grids are not exhaustive.',
                      'Ladder/stairs/door-bit observation is compared as a side effect. Actual stair walking, door transitions, NPC collisions, sprint swept guards and event-script execution are outside this helper audit.',
                      'Diagonal directions are restricted to valid source callers 1,3,5,7; invalid out-of-range directions are not invoked.',
                      'No original ROM, extracted game assets, machine-code copies or emulator are included in the public script/report.']}
    (out/'native-mismatches.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in differences),encoding='utf-8')
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:report[key] for key in ('Passed','ExecutedCases','SkippedCases','MismatchCount','MismatchesByHelper','PreviousProbeMismatchCount')}),flush=True)
    if differences:raise SystemExit(1)


if __name__=='__main__':main()
