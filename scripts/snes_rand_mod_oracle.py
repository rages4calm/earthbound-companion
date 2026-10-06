# SPDX-License-Identifier: GPL-3.0-or-later
"""Execute untouched original RAND_MOD, including its wrapped zero divisor.

Reassembly identifies complete byte-equal original math bodies and globals.
The only injected code is a private caller. No ROM or native source is edited.
"""
import argparse, hashlib, json, re, subprocess
from pathlib import Path
from check_jev_observer_parity import local_scratch
from snes_movement_helpers_oracle import sha, US_SHA1
import snes_position_arithmetic_oracle as mapping

def identify(a,out,rom):
 mapping.ROUTINES=(('RAND','system/math/rand.asm','far'),)
 globals_,addresses,evidence=mapping.identify(a,out,rom)
 folder=out/'source-mapping'
 # Preserve the same reviewed macro/RAM identification context, then bind
 # the already identified absolute code entries for these complete bodies.
 base=(folder/'rand.asm').read_text(encoding='utf-8').split('MOVEMENT_SPEEDS :=',1)[0]
 includes=['--cpu','65816','-D','USA','-I',folder/'include-overlay','-I',a.native_source/'include','-I',a.native_source/'asm']
 for symbol,relative in (('DIVISION16S','system/math/division16s.asm'),('MODULUS16','system/math/modulus16.asm'),('RAND_MOD','system/math/rand_mod.asm')):
  source=folder/(symbol.lower()+'.asm');obj=source.with_suffix('.o');blob=source.with_suffix('.bin')
  source.write_text(base+''.join(f'{k} := ${v:06X}\n' for k,v in addresses.items())+'.SEGMENT "CODE"\n.A16\n.I16\n.INCLUDE "'+relative+'"\n',encoding='utf-8')
  mapping.run([a.ca65,*includes,source,'-o',obj,'-l',source.with_suffix('.lst')],source.with_suffix('.compile.log'))
  mapping.run([a.ld65,'-C',folder/'code.cfg','-o',blob,obj],source.with_suffix('.link.log'))
  addresses[symbol]=mapping.find_unique(rom,blob.read_bytes(),symbol)
  evidence.append({'symbol':symbol,'address':f'{addresses[symbol]:06X}','originalSource':relative,'byteEqualLength':blob.stat().st_size,'byteEqualSha256':sha(blob)})
  if symbol=='DIVISION16S':
   listing=source.with_suffix('.lst').read_text(encoding='utf-8');matches=re.findall(r'^([0-9A-F]{6})r\s+\d+\s+DIVISION16S_DIVISOR_POSITIVE:\s*$',listing,re.M)
   if len(matches)!=1:raise ValueError('Original division entry alias not identified')
   offset=int(matches[0],16);addresses['DIVISION16S_DIVISOR_POSITIVE']=addresses[symbol]+offset
   evidence.append({'symbol':'DIVISION16S_DIVISOR_POSITIVE','address':f'{addresses["DIVISION16S_DIVISOR_POSITIVE"]:06X}','identifiedWithinByteEqualRoutine':symbol,'offset':offset})
 return globals_,addresses,evidence

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('rom','oracle','ca65','ld65','native-source','rng-review','scratch','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();a.scratch=local_scratch(a.scratch)
 if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch/output required')
 rom=a.rom.read_bytes()
 if len(rom)!=0x300000 or hashlib.sha1(rom).hexdigest()!=US_SHA1:raise ValueError('Exact clean USA ROM required')
 review=json.loads(a.rng_review.read_text(encoding='utf-8'))
 if not review['Passed'] or review['Mismatches'] or review['Pilot']:raise ValueError('Reviewed original generator comparison required')
 identities={str(x):sha(x) for x in (a.rom,a.oracle,a.ca65,a.ld65,a.rng_review,Path(__file__),Path(mapping.__file__))}
 a.scratch.mkdir(parents=True);globals_,addresses,proof=identify(a,a.scratch,rom)
 rows=[]
 for limit in range(256):
  for seed in range(1,17):rows.append((limit,(0x56781234+seed*0x01010301)&0xffffffff))
 for limit in (256,257,511,32767,32768,65534,65535):
  for seed in range(256):rows.append((limit,(0x12345678+seed*0x0193030b)&0xffffffff))
 # Own native-mode caller, A/X/Y16, SP1FFF, DP1000, DBR7E.
 code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
 entry=0xc0ff00+len(code);code+=bytes.fromhex('af00717e')+bytes((0x22,))+addresses['RAND_MOD'].to_bytes(3,'little')
 code+=bytes.fromhex('8f00707e7b8f08707e3b8f0a707e');finish=0xc0ff00+len(code)
 code+=bytes((0x4c,entry&255,entry>>8&255))
 ga,gb=globals_['RAND_A']&65535,globals_['RAND_B']&65535;samples=a.scratch/'samples.jsonl'
 lua=['local output=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))','local rows={'+','.join('{'+','.join(map(str,r))+'}' for r in rows)+'}',
  'local mem=emu.memType.snesWorkRam','local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256)%256,mem) end','local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end',
  'local index=0;local calls=0;local randcalls=0;local raw=0;w16(0x7200,0x55aa)',
  'emu.addMemoryCallback(function() index=index+1;local r=assert(rows[index],"past corpus");w16(0x7100,r[1]);'+f'w16({ga},r[2]%65536);w16({gb},math.floor(r[2]/65536)) end,emu.callbackType.exec,{entry})',
  f'emu.addMemoryCallback(function() calls=calls+1 end,emu.callbackType.exec,{addresses["RAND_MOD"]})',
  f'emu.addMemoryCallback(function() randcalls=randcalls+1 end,emu.callbackType.exec,{addresses["RAND"]})',
  # Read the real RAND return at the immediately following TAX/LDX stage.
  # RAND_MOD source mapping proves the JSL call, whose following instruction
  # offset is found in the full byte-equal body rather than assumed.
 ]
 blob=(a.scratch/'source-mapping/rand_mod.bin').read_bytes();call=bytes((0x22,))+addresses['RAND'].to_bytes(3,'little')
 if blob.count(call)!=1:raise ValueError('Original RAND call site not unique')
 afterrand=addresses['RAND_MOD']+blob.index(call)+4
 # Original hardware returned RAND is also inferable from the independent
 # sampled state formula; capture CPU A using the documented state API.
 lua += [f'emu.addMemoryCallback(function() raw=emu.getState()["cpu.a"] end,emu.callbackType.exec,{afterrand})',
  'emu.addMemoryCallback(function() assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"CPU frame corrupted");assert(r16(0x7200)==0x55aa,"protected RAM corrupted");',
  f' output:write(string.format("[%d,%d,%d,%d,%d]\\n",index,r16(0x7000),raw,r16({ga}),r16({gb})))',
  ' if index==#rows then assert(calls==#rows and randcalls==#rows,"call count differs");output:flush();output:close();emu.log("RAND_MOD_COMPLETE "..calls);emu.breakExecution() end',f'end,emu.callbackType.exec,{finish})']
 script=a.scratch/'rand-mod.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
 q=subprocess.run([str(a.oracle.resolve()),str(a.rom.resolve()),'--home',str(a.scratch/'oracle-home'),'--frames','1000','--timeout','60','--lua-timeout','10','--lua-allow-io','--lua',str(script),'--write-memory','SnesPrgRom:0xff00:'+code.hex(),'--set-pc','0xc0ff00','--cpu','Snes'],capture_output=True,timeout=70)
 (a.scratch/'oracle.jsonl').write_bytes(q.stdout);(a.scratch/'oracle.stderr').write_bytes(q.stderr)
 events=[json.loads(x) for x in q.stdout.decode().splitlines()];logs=[r for r in events if r['event']=='lua_log']
 if q.returncode or not events[-1].get('ok') or events[-1].get('reason')!='debugger_break' or any(r['error_count'] for r in logs):raise RuntimeError('Original machine execution incomplete')
 if sum('RAND_MOD_COMPLETE '+str(len(rows)) in r['text'] for r in logs)!=1:raise ValueError('Exact completion marker missing')
 got=[json.loads(x) for x in samples.read_text(encoding='utf-8').splitlines()]
 if [r[0] for r in got]!=list(range(1,len(rows)+1)):raise ValueError('Incomplete/out-of-order corpus')
 mismatches=[{'index':i,'bound':rows[i-1][0],'rawRand':raw,'originalResult':value,'expected':raw%(rows[i-1][0]+1)} for i,value,raw,ra,rb in got if value!=raw%(rows[i-1][0]+1)]
 if any(sha(Path(path))!=value for path,value in identities.items()):raise RuntimeError('Immutable input changed')
 report={'format':'snes-rand-mod-micro-oracle-v1','Passed':not mismatches,'ExecutedCalls':len(got),'SkippedCalls':0,'MismatchCount':len(mismatches),'FirstMismatches':mismatches[:12],'WrappedZeroDivisorCases':sum(r[0]==65535 for r in rows),'SourceMapping':proof,'InputIdentities':identities,'StackDirectPageProtectedRamPassed':True,'CompleteCallCountsAndOrderPassed':True,'SamplesSha256':sha(samples),'CallerSha256':hashlib.sha256(code).hexdigest(),'LuaSha256':sha(script),'OwnerRomUnchanged':True,'Limits':['Actual original RAND_MOD/RAND/division execution in prepared CPU contexts; not full consumer or story call ordering.','The inclusive-maximum65535 source wraps divisor to zero and returns the original byte; the widened native expression preserves that result.']}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:report[k] for k in ('Passed','ExecutedCalls','MismatchCount','WrappedZeroDivisorCases')}),flush=True)
 if not report['Passed']:raise SystemExit(1)

if __name__=='__main__':main()
