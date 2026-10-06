# SPDX-License-Identifier: GPL-3.0-or-later
"""Execute original/pinned Bomb party-adjacency control flow with narrow stubs.

The real BOMB_COMMON machine body is untouched. Only variance, damage and name
children are replaced in temporary emulator memory to inspect neighbor calls.
This is adjacency proof, not full original-machine damage/RNG/gameplay proof.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in('rom','oracle','scratch','output'):ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--redux',action='store_true');a=ap.parse_args()
    identities={False:'a8fe2226728002786d68c27ddddf0b90a894db52e4dfe268fdf72a68cae5f02e',True:'c2a2fc98c7e6518b797959ffadf24ca4db8b4d7745ed3a9eb92eee106db1d0ab'}
    identity=sha(a.rom)
    if identity!=identities[a.redux]:raise ValueError('Unreviewed owner ROM')
    if a.scratch.exists():raise ValueError('Fresh private scratch required')
    s=a.scratch.resolve();s.mkdir(parents=True);cases=[(slot,next_member)for slot in range(4)for next_member in range(18)]
    body=a.rom.read_bytes()[0x2a658:0x2a818]
    clean=Path(r'E:\Consoles\snes\EarthBound (USA)\EarthBound (USA).sfc').read_bytes()[0x2a658:0x2a818]
    if body!=clean:raise ValueError('Bomb body changed from reviewed instructions')
    stub=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230');entry=0xc2ff00+len(stub)
    stub+=bytes.fromhex('a95a002058a67b8f08707e3b8f0a707e');finish=0xc2ff00+len(stub);stub+=bytes((0x4c,entry&255,(entry>>8)&255))
    sample=s/'samples.tsv'
    lua=['local output=assert(io.open('+json.dumps(sample.as_posix())+',"wb"))',
         'local cases={'+','.join('{'+','.join(map(str,c))+'}'for c in cases)+'}',
         'local mem=emu.memType.snesWorkRam;local index=0;local calls={}',
         'local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256),mem) end',
         'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end',
         'emu.addMemoryCallback(function() index=index+1;local c=assert(cases[index]);calls={};',
         'for i=0,5 do emu.write(0x986f+i,i<4 and i+1 or 0,mem);w16(0x9fac+78*i,i+1);emu.write(0x9fac+78*i+14,0,mem) end',
         'emu.write(0x986f+c[1]+1,c[2],mem);w16(0xa972,0x9fac+c[1]*78)',f'end,emu.callbackType.exec,{entry})',
         'emu.addMemoryCallback(function() calls[#calls+1]=r16(0xa972) end,emu.callbackType.exec,0xc28125)',
         'emu.addMemoryCallback(function() assert(r16(0x7008)==0x1000,"D canary");assert(r16(0x700a)==0x1fff,"stack canary");',
         'output:write(index..":"..table.concat(calls,",")..":"..r16(0xa972).."\\n");if index==#cases then output:flush();output:close();emu.log("CORPUS_COMPLETE");emu.breakExecution() end',f'end,emu.callbackType.exec,{finish})']
    script=s/'oracle.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
    command=[str(a.oracle.resolve()),str(a.rom.resolve()),'--home',str(s/'oracle-home'),'--frames','1000','--timeout','60','--lua-timeout','10','--lua-allow-io','--lua',str(script),'--write-memory','SnesPrgRom:0x2ff00:'+stub.hex(),'--write-memory','SnesPrgRom:0x26a44:60','--write-memory','SnesPrgRom:0x28125:60','--write-memory','SnesPrgRom:0x23d05:6b','--set-pc','0xc2ff00','--cpu','Snes']
    run=subprocess.run(command,capture_output=True,timeout=70);(s/'oracle.jsonl').write_bytes(run.stdout);(s/'oracle.stderr').write_bytes(run.stderr)
    logs=[json.loads(l)for l in run.stdout.decode().splitlines()];events=[r for r in logs if r.get('event')=='lua_log'];end=logs[-1]if logs else{}
    if run.returncode or not end.get('ok')or end.get('reason')!='debugger_break'or any(r['error_count']for r in events):raise RuntimeError('Machine failed')
    lines=sample.read_text().splitlines()
    if len(lines)!=len(cases)or not any('CORPUS_COMPLETE'in r['text']for r in events):raise RuntimeError('Incomplete corpus')
    rows=[]
    for i,(slot,next_member)in enumerate(cases,1):
        m=re.fullmatch(r'(\d+):([\d,]+):(\d+)',lines[i-1])
        if not m or int(m[1])!=i:raise RuntimeError('Missing/out-of-order machine case')
        calls=[(int(v)-0x9fac)//78 for v in m[2].split(',')];expected=[slot]+([slot-1]if slot else[])+([slot+1]if 1<=next_member<=4 else[])
        rows.append(dict(slot=slot,rightMember=next_member,machineDamageTargetSlots=calls,sourceExpectedSlots=expected,targetRestored=int(m[3])==0x9fac+slot*78,sourceMatched=calls==expected))
    if sha(a.rom)!=identity:raise RuntimeError('Owner ROM changed')
    report=dict(schemaVersion=1,toolVersion='dev16-bomb-adjacency-machine',reference='pinned-redux-machine'if a.redux else'clean-original-machine',romSha256=identity,oracleSha256=sha(a.oracle),oracleCoreSha256=sha(a.oracle.parent/'MesenCore.dll'),untouchedBodyAddress='C2A658',untouchedBodySha256=hashlib.sha256(body).hexdigest(),stubbedChildren=['C26A44 variance RTS','C28125 damage RTS','C23D05 target-name RTL'],executedMachineCases=len(rows),cases=rows,sourceMismatchCount=sum(not r['sourceMatched']or not r['targetRestored']for r in rows),stackAndDirectPageCanariesPassed=True,ownerRomUnchanged=True,limits=['Actual unchanged original/pinned BOMB_COMMON party-adjacency instructions; variance, damage and name children intentionally stubbed only in temporary emulator memory.','Prepared slots0..3 and right member IDs0..17 include synthetic membership. Damage values, RNG consumption, enemy adjacency, art, full actions and natural battles not proved.','Dev-only oracle excluded from player; no owner ROM/asset/save payload included.'])
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(reference=report['reference'],cases=len(rows),sourceMismatchCount=report['sourceMismatchCount'])))
    if report['sourceMismatchCount']:raise SystemExit(1)

if __name__=='__main__':main()
