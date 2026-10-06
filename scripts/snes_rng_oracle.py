# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare the native serialized RNG with actual untouched clean USA RAND.

Reassembly identifies the exact routine/global addresses; only a private caller
is injected into emulator memory. No owner ROM, pack, source or build is edited.
This proves selected generator states, not whole-game RNG call ordering.
"""
import argparse, hashlib, json, os, subprocess
from pathlib import Path
import snes_position_arithmetic_oracle as mapping_tool
from snes_movement_helpers_oracle import function, sha, US_SHA1
from check_jev_observer_parity import local_scratch

def corpus(pilot=False):
    rows=[]
    for low_a in range(16 if pilot else 256):
        for low_b in range(16 if pilot else 256):
            rows.append((low_a,low_b,1,'all-low-byte-products'))
    boundaries=(0,1,0xff,0x100,0x7fff,0x8000,0x8001,0xff00,0xfffe,0xffff)
    for a in boundaries:
        for b in boundaries:rows.append((a,b,16,'full-width-boundary-sequences'))
    rows.extend(((0x1234,0x5678,1024,'reset-sequence'),(0,0,128,'raw-zero-state-sequence')))
    return rows

def machine(a,out,globals_,mapping,rows):
    out.mkdir();samples=out/'samples.jsonl'
    # Own caller sets native A/X/Y16, SP1FFF, DP1000 and DBR7E.
    code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
    entry=0xc0ff00+len(code)
    code+=bytes((0x22,))+mapping['RAND'].to_bytes(3,'little')
    code+=bytes.fromhex('8f00707e7b8f08707e3b8f0a707e')
    finish=0xc0ff00+len(code)
    code+=bytes((0x4c,entry&255,entry>>8&255))
    ga,gb=globals_['RAND_A']&65535,globals_['RAND_B']&65535
    lua=['local output=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))',
      'local rows={'+','.join('{'+','.join(map(str,row[:3]))+'}' for row in rows)+'}',
      'local mem=emu.memType.snesWorkRam',
      'local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256),mem) end',
      'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end',
      'local index=0;local step=0;local calls=0;w16(0x7200,0x55aa)',
      'emu.addMemoryCallback(function()',
      ' if index==0 or step==rows[index][3] then index=index+1;step=0;local row=assert(rows[index],"past corpus");',
      f' w16({ga},row[1]);w16({gb},row[2]);end',
      f'end,emu.callbackType.exec,{entry})',
      'emu.addMemoryCallback(function() calls=calls+1 end,emu.callbackType.exec,'+str(mapping['RAND'])+')',
      'emu.addMemoryCallback(function()',
      ' step=step+1;assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"CPU frame corrupted");assert(r16(0x7200)==0x55aa,"protected RAM corrupted")',
      f' output:write(string.format("[%d,%d,%d,%d,%d]\\n",index,step,r16(0x7000),r16({ga}),r16({gb})))',
      ' if index==#rows and step==rows[index][3] then output:flush();output:close();emu.log("RNG_CORPUS_COMPLETE "..calls);emu.breakExecution() end',
      f'end,emu.callbackType.exec,{finish})']
    script=out/'rng.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
    p=subprocess.run([str(a.oracle.resolve()),str(a.rom.resolve()),'--home',str(out/'oracle-home'),'--frames','1000','--timeout','60','--lua-timeout','10','--lua-allow-io','--lua',str(script),'--write-memory','SnesPrgRom:0xff00:'+code.hex(),'--set-pc','0xc0ff00','--cpu','Snes'],capture_output=True,timeout=70)
    (out/'oracle.jsonl').write_bytes(p.stdout);(out/'oracle.stderr').write_bytes(p.stderr)
    records=[json.loads(x) for x in p.stdout.decode().splitlines()]
    logs=[r for r in records if r['event']=='lua_log']
    expected=sum(row[2] for row in rows)
    if p.returncode or not records[-1].get('ok') or records[-1].get('reason')!='debugger_break' or any(r['error_count'] for r in logs):raise RuntimeError('Original RNG execution incomplete')
    if sum('RNG_CORPUS_COMPLETE '+str(expected) in r['text'] for r in logs)!=1:raise RuntimeError('Original RNG completion/call count missing')
    got=[json.loads(x) for x in samples.read_text().splitlines()]
    wanted=[(index,step) for index,row in enumerate(rows,1) for step in range(1,row[2]+1)]
    if [tuple(r[:2]) for r in got]!=wanted:raise RuntimeError('Original samples incomplete/out of order')
    return got,{'ExecutedCalls':expected,'StackDirectPageProtectedRamPassed':True,'CompleteOrderedCorpusVerified':True,'OwnCallerSha256':hashlib.sha256(code).hexdigest(),'LuaSha256':sha(script),'SamplesSha256':sha(samples)}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','oracle','ca65','ld65','compiler','native-source','scratch','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--pilot',action='store_true');a=p.parse_args()
    out=local_scratch(a.scratch)
    if out.exists():raise ValueError('Use a fresh scratch directory')
    rom=a.rom.read_bytes()
    if len(rom)!=0x300000 or hashlib.sha1(rom).hexdigest()!=US_SHA1:raise ValueError('Exact clean unheadered USA ROM required')
    source=a.native_source/'src/core/math.c'
    identities={str(path):sha(path) for path in (a.rom,a.oracle,a.ca65,a.ld65,a.compiler,source,Path(__file__),Path(mapping_tool.__file__))}
    out.mkdir(parents=True)
    mapping_tool.ROUTINES=(('RAND','system/math/rand.asm','far'),)
    globals_,mapping,reference=mapping_tool.identify(a,out,rom)
    native=out/'rng.c';exe=out/'rng.exe'
    native.write_text('#include "core/math.h"\n#include <stdbool.h>\n#include <stdio.h>\nRNGState rng_state;\n'+function(source.read_text(encoding='utf-8'),'rng_next_byte')+r'''
int main(void){unsigned a,b,n,index=0;while(scanf("%u %u %u",&a,&b,&n)==3){++index;rng_state.a=a;rng_state.b=b;for(unsigned step=1;step<=n;++step){unsigned result=rng_next_byte();printf("[%u,%u,%u,%u,%u]\n",index,step,result,rng_state.a,rng_state.b);}}return 0;}
''',encoding='utf-8')
    compiled=subprocess.run([str(a.compiler),'-std=c2x','-O2','-I',str(a.native_source/'src'),str(native),'-o',str(exe)],capture_output=True,timeout=40)
    (out/'compile.log').write_bytes(compiled.stdout+compiled.stderr)
    if compiled.returncode:raise RuntimeError('Actual native RNG probe did not compile')
    rows=corpus(a.pilot);machine_rows=[];evidence=[]
    for start in range(0,len(rows),10000):
        batch=rows[start:start+10000]
        got,meta=machine(a,out/f'machine-{start}',globals_,mapping,batch)
        for r in got:r[0]+=start
        machine_rows.extend(got);evidence.append(meta)
    proc=subprocess.run([str(exe)],input='\n'.join(' '.join(map(str,r[:3])) for r in rows).encode(),capture_output=True,timeout=40)
    if proc.returncode:raise RuntimeError('Native RNG execution failed')
    native_rows=[json.loads(x) for x in proc.stdout.decode().splitlines()]
    if len(native_rows)!=len(machine_rows):raise RuntimeError('Native sample count differs')
    mismatches=[{'index':i+1,'native':n,'originalMachine':m} for i,(n,m) in enumerate(zip(native_rows,machine_rows)) if n!=m]
    if any(sha(Path(path))!=value for path,value in identities.items()):raise RuntimeError('Immutable input changed')
    report={'Passed':not mismatches,'RequestedCalls':len(native_rows),'ExecutedCalls':len(machine_rows),'SkippedCalls':0,'Mismatches':len(mismatches),'FirstMismatches':mismatches[:12],'Identities':identities,'SourceMapping':reference,'OriginalGlobals':{name:f'{globals_[name]:06X}' for name in ('RAND_A','RAND_B')},'MachineBatches':evidence,'NativeFunctionSha256':hashlib.sha256(function(source.read_text(encoding='utf-8'),'rng_next_byte').encode()).hexdigest(),'OwnerRomUnchanged':True,'Pilot':a.pilot,'Limits':['Selected state and sequence generator equivalence; not all four-billion RNG states.','Actual native source compiled in isolation; not production binary execution.','Generator correctness does not establish consumers or complete RNG call ordering.','Temporary caller only; actual original RAND and hardware multiply run unchanged.']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('Passed','ExecutedCalls','Mismatches')}),flush=True)
    if not report['Passed']:raise SystemExit(1)

if __name__=='__main__':main()
