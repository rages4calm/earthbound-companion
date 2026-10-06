# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare native collision-pattern source with the clean ROM's 65816 routine.

Development only: requires an owner-provided US ROM and mesen-agent. It injects
a small test caller into the emulator's temporary ROM memory, leaving the real
collision routines untouched. No ROM, game assets or emulator is distributed.
The native probe compiles the actual production helper bodies in isolation;
this is a function comparison, not full-game frame or binary equivalence.
"""
import argparse, hashlib, json, re, struct, subprocess
from pathlib import Path
from check_jev_observer_parity import local_scratch

ROOT=Path(__file__).resolve().parents[1]
US_SHA1='d67a8ef36ef616bc39306aa1b486e1bd3047815a'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def function(text,name):
    start=re.search(r'^static [^\n]+ '+name+r'\(',text,re.M).start()
    opening=text.index('{',start);depth=1;end=opening+1
    while depth:
        if text[end]=='{':depth+=1
        if text[end]=='}':depth-=1
        end+=1
    return text[start:end]+'\n'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','oracle','compiler','native-source','generated','scratch'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--previous-probe',type=Path,help='Optional recorded pre-fix native probe; differences must be reproduced.')
    a=p.parse_args();out=local_scratch(a.scratch)
    if out.exists():raise ValueError('Choose fresh scratch output; preserve prior evidence.')
    for item in (a.rom,a.oracle,a.compiler):
        if not item.is_file():raise ValueError('Required input missing: '+str(item))
    rom=a.rom.read_bytes()
    if len(rom)!=0x300000 or hashlib.sha1(rom).hexdigest()!=US_SHA1:
        raise ValueError('This routine-address catalog requires the exact clean unheadered EarthBound USA ROM.')
    source=a.native_source/'src/game/map_loader.c';text=source.read_text(encoding='utf-8')
    identities={'rom':sha(a.rom),'oracle':sha(a.oracle),'nativeSource':sha(source),'compiler':sha(a.compiler)}
    if (a.oracle.parent/'MesenCore.dll').is_file():identities['oracleCore']=sha(a.oracle.parent/'MesenCore.dll')
    if a.previous_probe:identities['previousProbe']=sha(a.previous_probe)
    out.mkdir(parents=True)
    helpers=''.join(function(text,name) for name in ('get_collision_tile_and_check_ladder','check_collision_tile_pattern'))
    tables='\n'.join(re.search(r'^static const int16_t '+name+r'\[6\] = [^;]+;',text,re.M).group()
                     for name in ('collision_x_offsets','collision_y_offsets'))
    prefix='#include "game/map_loader.h"\n#include "game/overworld.h"\n#include "core/log.h"\n#include <stdio.h>\nMapLoaderState ml;OverworldState ow;\nstatic uint16_t set_temp_entity_surface_flags,temp_entity_surface_flags;\n'
    main_c=r'''
int main(int argc,char**argv){
 if(argc!=2)return 2;FILE*f=fopen(argv[1],"rb");if(!f)return 3;
 uint16_t h[7];while(fread(h,2,7,f)==7){
  if(fread(ml.loaded_collision_tiles,1,4096,f)!=4096)return 4;
  ow.checked_collision_left_x=h[0];ow.checked_collision_top_y=h[1];
  set_temp_entity_surface_flags=h[3];temp_entity_surface_flags=h[4];
  ow.ladder_stairs_tile_x=h[5];ow.ladder_stairs_tile_y=h[6];
  uint16_t v=check_collision_tile_pattern(h[2]);
  printf("[%u,%u,%u,%u]\n",v,temp_entity_surface_flags,(uint16_t)ow.ladder_stairs_tile_x,(uint16_t)ow.ladder_stairs_tile_y);
 }int failed=ferror(f);fclose(f);return failed?4:0;
}
'''
    probe=out/'probe.c';probe.write_text(prefix+tables+'\n'+helpers+main_c,encoding='utf-8')
    exe=out/'probe.exe'
    includes=[a.native_source/'src',a.native_source/'src/include',a.generated,a.native_source/'src/data/runtime_generated']
    cmd=[str(a.compiler.resolve()),'-std=c11','-O2','-DEB_VIEWPORT_WIDTH=512','-DEB_VIEWPORT_HEIGHT=256','-DUSA=1']
    cmd+=['-I'+str(path.resolve()) for path in includes]+[str(probe),'-o',str(exe)]
    build=subprocess.run(cmd,capture_output=True,timeout=30);(out/'compile.log').write_bytes(build.stdout+build.stderr)
    if build.returncode:raise RuntimeError('Native probe compilation failed; inspect compile.log.')
    coords=[(105,97),(104,96),(111,103),(513,513),(0,0),(32770,32770),(65530,65530)]
    patterns=[(0,0,0,0,0,0),(0xc0,0x10,8,0x90,4,0x20),(0xff,)*6,(0x10,)*6,
              (0x80,0,0x40,0,0x80,0),(1,2,4,8,16,32),(0x40,0x80,0xc0,0x50,0x90,0xd0),(0x0c,8,4,0x20,0x30,0)]
    cases=[]
    for x,y in coords:
        for mask in (*range(64),0x80,0xffff):
            for flags in patterns:
                for control in (0,1,2):
                    grid=bytearray(4096)
                    for dx,dy,flag in zip((-8,0,7,-8,0,7),(0,0,0,7,7,7),flags):
                        tx=((x+dx)&65535)>>3;ty=((y+dy)&65535)>>3
                        grid[(ty&63)*64+(tx&63)]=flag
                    cases.append((x,y,mask,control,0xa5a5,0xbeef,0xcafe,grid))
    inputs=out/'inputs.bin';inputs.write_bytes(b''.join(struct.pack('<7H',*c[:7])+c[7] for c in cases))
    def native_rows(binary):
        run=subprocess.run([str(binary.resolve()),str(inputs)],capture_output=True,timeout=30)
        if run.returncode:raise RuntimeError('Native probe execution failed.')
        rows=[json.loads(line) for line in run.stdout.decode().splitlines()]
        if len(rows)!=len(cases) or any(len(row)!=4 for row in rows):raise RuntimeError('Incomplete native corpus output.')
        return rows
    native=native_rows(exe)
    # Native CPU mode, 16-bit A/X/Y, stack1FFF, separate direct-page1000,
    # DBR7E. JSR calls original C05769; original helper C054C9 remains intact.
    # RAM2 starts7EB800, plus palette2048 and tileset8192 => collision7EE000.
    stub=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
    entry=0xc0ff00+len(stub)
    stub+=bytes.fromhex('af00717e2069578f00707e7b8f08707e3b8f0a707e')
    finish=0xc0ff00+len(stub);stub+=bytes([0x4c,entry&255,(entry>>8)&255])
    samples=out/'oracle-samples.tsv'
    lua=['local output=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))','local cases = {']
    for case in cases:
        cells=[(i,v) for i,v in enumerate(case[7]) if v]
        lua.append('{'+','.join(map(str,case[:7]))+', {'+','.join('{'+str(i)+','+str(v)+'}' for i,v in cells)+'}},')
    lua+=['}', 'local mem=emu.memType.snesWorkRam',
          'local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256),mem) end',
          'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end',
          'for i=0,4095 do emu.write(0xe000+i,0,mem) end','local index=0;local previous={}',
          'emu.addMemoryCallback(function()',
          ' index=index+1;local c=cases[index];assert(c,"ran beyond corpus")',
          ' for _,pair in ipairs(previous) do emu.write(0xe000+pair[1],0,mem) end',
          ' for _,pair in ipairs(c[8]) do emu.write(0xe000+pair[1],pair[2],mem) end;previous=c[8]',
          ' w16(0x5dac,c[1]);w16(0x5dae,c[2]);w16(0x7100,c[3]);w16(0x5db4,c[4]);w16(0x5da4,c[5]);w16(0x5da8,c[6]);w16(0x5daa,c[7])',
          f'end,emu.callbackType.exec,{entry})','emu.addMemoryCallback(function()',
          ' assert(r16(0x7008)==0x1000,"direct page corrupted");assert(r16(0x700a)==0x1fff,"stack corrupted")',
          ' output:write(string.format("%d,%d,%d,%d,%d\\n",index,r16(0x7000),r16(0x5da4),r16(0x5da8),r16(0x5daa)))',
          ' if index==#cases then output:flush();output:close();emu.log("CORPUS_COMPLETE");emu.breakExecution() end',
          f'end,emu.callbackType.exec,{finish})']
    script=out/'collision.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
    cmd=[str(a.oracle.resolve()),str(a.rom.resolve()),'--home',str(out/'oracle-home'),'--frames','1000',
         '--timeout','60','--lua-timeout','10','--lua-allow-io','--lua',str(script),'--write-memory','SnesPrgRom:0xff00:'+stub.hex(),
         '--set-pc','0xc0ff00','--cpu','Snes']
    run=subprocess.run(cmd,capture_output=True,timeout=70)
    (out/'oracle.jsonl').write_bytes(run.stdout);(out/'oracle.stderr').write_bytes(run.stderr)
    records=[json.loads(line) for line in run.stdout.decode().splitlines()]
    logs=[row for row in records if row['event']=='lua_log'];summary=records[-1] if records else {}
    if run.returncode or summary.get('event')!='summary' or not summary.get('ok') or summary.get('reason')!='debugger_break' or not logs or any(row['error_count'] for row in logs):
        raise RuntimeError('Reference did not complete cleanly; inspect oracle.jsonl and oracle.stderr.')
    values=[]
    for line in samples.read_text(encoding='utf-8').splitlines():
        m=re.fullmatch(r'(\d+),(\d+),(\d+),(\d+),(\d+)',line)
        if not m:raise RuntimeError('Malformed oracle sample.')
        values.append((int(m[1]),list(map(int,m.groups()[1:]))))
    if [i for i,_ in values]!=list(range(1,len(cases)+1)) or not any('CORPUS_COMPLETE' in row['text'] for row in logs):
        raise RuntimeError('Missing, duplicate or truncated oracle samples.')
    diffs=[{'case':i,'input':list(cases[i-1][:7]),'native':native[i-1],'reference':ref} for i,ref in values if native[i-1]!=ref]
    old=native_rows(a.previous_probe) if a.previous_probe else None
    red=[i for i,ref in values if old is not None and old[i-1]!=ref]
    if a.previous_probe and not red:raise RuntimeError('Requested pre-fix regression was not reproduced.')
    after={'rom':sha(a.rom),'oracle':sha(a.oracle),'nativeSource':sha(source),'compiler':sha(a.compiler)}
    if any(identities[k]!=after[k] for k in after):raise RuntimeError('An immutable audit input changed.')
    report={'format':'snes-collision-micro-oracle-v1','Passed':not diffs,'ExecutedCases':len(cases),'SkippedCases':0,
            'Mismatches':diffs,'InputSha256':sha(inputs),'InputIdentities':identities,
            'CompiledNativeHelpersSha256':hashlib.sha256((tables+helpers).encode()).hexdigest(),
            'ProbeSha256':sha(exe),'PreviousProbeMismatchCount':len(red) if old is not None else None,
            'PreviousProbeMismatchedCases':red,'OriginalMachineCodeExecuted':True,'StackAndDirectPageCanariesPassed':True,
            'OwnerRomUnchanged':True,'FullCompatibilityVerified':False,'FullPlaythroughVerified':False,
            'Limits':['Two original 65816 helpers compared with actual isolated native helper bodies, not a full game binary.',
                      'Prepared grid, coordinate, mask and surface-control corpus; no story/NPC/swept-guard comparison.',
                      'Development reference emulator is separate from the native player and absent from player releases.']}
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('Passed','ExecutedCases','SkippedCases','PreviousProbeMismatchCount')}),flush=True)
    if not report['Passed']:raise SystemExit(1)

if __name__=='__main__':main()
