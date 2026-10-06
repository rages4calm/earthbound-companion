# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual original/pinned KO skip branch and epilogue, with prepared ABI caller."""
import argparse,hashlib,json,subprocess
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in('rom','oracle','scratch','output'):ap.add_argument('--'+n,type=Path,required=True)
 ap.add_argument('--redux',action='store_true');a=ap.parse_args()
 identities={False:'a8fe2226728002786d68c27ddddf0b90a894db52e4dfe268fdf72a68cae5f02e',True:'c2a2fc98c7e6518b797959ffadf24ca4db8b4d7745ed3a9eb92eee106db1d0ab'}
 identity=sha(a.rom)
 if identity!=identities[a.redux]:raise ValueError('Unreviewed ROM')
 if a.scratch.exists():raise ValueError('Fresh private scratch required')
 a.scratch.mkdir(parents=True);s=a.scratch.resolve();b=a.rom.read_bytes()
 if b[0x27a07:0x27a10]!=bytes.fromhex('ad92aaf0034c927c')+bytes([0xa9]):raise ValueError('Reviewed branch changed')
 if b[0x27c92:0x27c96]!=bytes.fromhex('c2202b6b'):raise ValueError('Reviewed epilogue changed')
 rows=[]
 for value in(0,1,2,65535):
  work=s/str(value);work.mkdir();sample=work/'sample.txt'
  stub=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
  stub+=bytes([0xa9,value&255,value>>8,0x8d,0x92,0xaa])
  # Actual skip branch expects the PHD/local-frame ABI already established.
  # JSL to a private trampoline; PHD then JMP actual untouched branch.
  call=0xc2ff00+len(stub);tramp=call+4+10+3
  stub+=bytes([0x22,tramp&255,(tramp>>8)&255,0xc2])+bytes.fromhex('7b8f08707e3b8f0a707e');finish=0xc2ff00+len(stub)
  stub+=bytes([0x4c,finish&255,(finish>>8)&255,0x0b,0x4c,0x07,0x7a])
  lua='\n'.join(['local out=assert(io.open('+json.dumps(sample.as_posix())+',"wb"))',
   'local function r16(a)return emu.read(a,emu.memType.snesWorkRam)+256*emu.read(a+1,emu.memType.snesWorkRam)end',
   'emu.addMemoryCallback(function()out:write("death");out:close();emu.breakExecution()end,emu.callbackType.exec,0xc27a0f)',
   'emu.addMemoryCallback(function()out:write("return:"..r16(0x7008)..":"..r16(0x700a));out:close();emu.breakExecution()end,emu.callbackType.exec,'+str(finish)+')'])
  script=work/'oracle.lua';script.write_text(lua+'\n',encoding='utf-8')
  command=[str(a.oracle.resolve()),str(a.rom.resolve()),'--home',str(work/'home'),'--frames','1000','--timeout','60','--lua-timeout','10','--lua-allow-io','--lua',str(script),'--write-memory','SnesPrgRom:0x2ff00:'+stub.hex(),'--set-pc','0xc2ff00','--cpu','Snes']
  run=subprocess.run(command,capture_output=True,timeout=70);(work/'oracle.jsonl').write_bytes(run.stdout);(work/'stderr.log').write_bytes(run.stderr)
  logs=[json.loads(l)for l in run.stdout.decode().splitlines()];end=logs[-1]if logs else{};observed=sample.read_text()if sample.exists()else''
  expected='death'if not value else'return:4096:8191'
  rows.append(dict(skipFlag=value,observed=observed,expected=expected,passed=run.returncode==0 and end.get('ok')and end.get('reason')=='debugger_break'and observed==expected,canariesChecked=bool(value)))
 report=dict(schemaVersion=1,toolVersion='dev17-ko-skip-machine',reference='pinned-redux-machine'if a.redux else'clean-original-machine',romSha256=identity,oracleSha256=sha(a.oracle),oracleCoreSha256=sha(a.oracle.parent/'MesenCore.dll'),branchAddress='C27A07',branchBodySha256=hashlib.sha256(b[0x27a07:0x27a10]).hexdigest(),returnEpilogueAddress='C27C92',returnEpilogueSha256=hashlib.sha256(b[0x27c92:0x27c96]).hexdigest(),cases=rows,allPassed=all(r['passed']for r in rows),ownerRomUnchanged=sha(a.rom)==identity,limits=['Actual untouched LDA skip flag, conditional jump and original KO return epilogue. Private temporary ABI trampoline establishes PHD; prepared flag values0/1/2/65535.','Zero control breaks at death path entry. Nonzero controls return with direct-page1000/stack1FFF canaries. Complete KO/final action/damage/animation and natural reachability are not proved by this machine snippet.','No child routine stub or machine-body edit. Only reset/caller/trampoline is patched in ephemeral emulator ROM memory; owner ROM remains unchanged.'])
 a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(reference=report['reference'],passed=sum(r['passed']for r in rows),cases=len(rows),failures=[r for r in rows if not r['passed']])))
 if not report['allPassed']or not report['ownerRomUnchanged']:raise SystemExit(1)
if __name__=='__main__':main()
