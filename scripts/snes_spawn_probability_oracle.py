# SPDX-License-Identifier: GPL-3.0-or-later
"""Execute the complete original MULT168 used by enemy spawn probability.

The exact source body must reassemble byte-equal to the owner ROM. A private
caller tests all byte rolls against MULT168(100), XBA, AND255. No ROM file is
changed and no original code/data belongs in distributed validation reports.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path
from check_jev_observer_parity import local_scratch
from snes_movement_helpers_oracle import sha, US_SHA1
import snes_position_arithmetic_oracle as mapping

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('rom','oracle','native-source','ca65','ld65','scratch','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.scratch=local_scratch(a.scratch)
 if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch/output required')
 rom=a.rom.read_bytes()
 if len(rom)!=0x300000 or hashlib.sha1(rom).hexdigest()!=US_SHA1:raise ValueError('Exact clean USA ROM required')
 files=[a.rom,a.oracle,a.ca65,a.ld65,Path(__file__),Path(mapping.__file__),a.native_source/'asm/system/math/mult168.asm',a.native_source/'asm/overworld/attempt_enemy_spawn.asm']
 identities={str(x):sha(x) for x in files};a.scratch.mkdir(parents=True)
 mapping.ROUTINES=(('MULT168','system/math/mult168.asm','far'),)
 globals_,addresses,proof=mapping.identify(a,a.scratch,rom)
 # Source-defined consumer operations immediately after the true multiplier.
 code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
 entry=0xc0ff00+len(code);code+=bytes.fromhex('af00717ea06400')+bytes((0x22,))+addresses['MULT168'].to_bytes(3,'little')
 code+=bytes.fromhex('8f02707eeb29ff008f00707e7b8f08707e3b8f0a707e');finish=0xc0ff00+len(code);code+=bytes((0x4c,entry&255,entry>>8&255))
 samples=a.scratch/'samples.jsonl'
 lua=['local output=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))','local mem=emu.memType.snesWorkRam','local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256)%256,mem) end','local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end','local index=0;local calls=0;w16(0x7200,0x55aa)',f'emu.addMemoryCallback(function() assert(index<256,"past corpus");w16(0x7100,index);index=index+1 end,emu.callbackType.exec,{entry})',f'emu.addMemoryCallback(function() calls=calls+1 end,emu.callbackType.exec,{addresses["MULT168"]})','emu.addMemoryCallback(function() assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"CPU frame corrupted");assert(r16(0x7200)==0x55aa,"protected RAM corrupted");output:write(string.format("[%d,%d,%d]\\n",index-1,r16(0x7000),r16(0x7002)));if index==256 then assert(calls==256,"call count differs");output:flush();output:close();emu.log("SPAWN_PROBABILITY_COMPLETE "..calls);emu.breakExecution() end',f'end,emu.callbackType.exec,{finish})']
 script=a.scratch/'spawn-probability.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
 q=subprocess.run([str(a.oracle.resolve()),str(a.rom.resolve()),'--home',str(a.scratch/'oracle-home'),'--frames','1000','--timeout','60','--lua-timeout','10','--lua-allow-io','--lua',str(script),'--write-memory','SnesPrgRom:0xff00:'+code.hex(),'--set-pc','0xc0ff00','--cpu','Snes'],capture_output=True,timeout=70)
 (a.scratch/'oracle.jsonl').write_bytes(q.stdout);(a.scratch/'oracle.stderr.log').write_bytes(q.stderr)
 if q.returncode or b'SPAWN_PROBABILITY_COMPLETE 256' not in q.stdout:raise RuntimeError('Incomplete original multiplication oracle')
 if b'warning' in q.stdout.lower() or b'warning' in q.stderr.lower():raise RuntimeError('Original oracle warning')
 rows=[json.loads(s) for s in samples.read_text(encoding='utf-8').splitlines()]
 if [r[0] for r in rows]!=list(range(256)):raise ValueError('Ordered original corpus incomplete')
 errors=[{'roll':raw,'scaled':scaled,'product':product,'expectedScaled':raw*100>>8} for raw,scaled,product in rows if scaled!=raw*100>>8 or product!=raw*100]
 if any(sha(Path(p))!=v for p,v in identities.items()):raise RuntimeError('Immutable input changed')
 report={'format':'snes-spawn-probability-micro-oracle-v1','Passed':not errors,'ExecutedCalls':256,'SkippedCalls':0,'MismatchCount':len(errors),'FirstMismatches':errors[:12],'OldModuloDisagreements':sum(raw%100!=scaled for raw,scaled,product in rows),'SourceMapping':proof,'InputIdentities':identities,'StackDirectPageProtectedRamPassed':True,'CompleteCallCountsAndOrderPassed':True,'SamplesSha256':sha(samples),'CallerSha256':hashlib.sha256(code).hexdigest(),'LuaSha256':sha(script),'OwnerRomUnchanged':True,'Limits':['Actual original multiplication and source-defined postprocessing, not the whole enemy spawn routine or story RNG ordering.','Butterfly probability uses a different source modulo100 operation; this correction applies to ordinary enemy spawning.']}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:report[k] for k in ('Passed','ExecutedCalls','MismatchCount','OldModuloDisagreements')}),flush=True)
 if not report['Passed']:raise SystemExit(1)

if __name__=='__main__':main()
