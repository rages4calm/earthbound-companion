# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare dissolve-slot RNG consumer with untouched original CPU execution.

Only fresh private scratch is written. Actual original full-function bytes and
RAM globals gate the oracle; no owner ROM, assets, saves or build are modified.
The selected contexts have zero fade entries, so this checks RNG/slot selection
without claiming sprite blending or VRAM parity.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from check_jev_observer_parity import local_scratch
from snes_movement_helpers_oracle import sha, US_SHA1
import snes_stat_growth_oracle as stat
import snes_position_arithmetic_oracle as mapping
from party_follow_private_build import private_build

DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "core/math.h"
#include "entity/entity.h"
#include "entity/buffer_layout.h"
#include "include/binary.h"
extern int eb_platform_main(int,char**);
extern void cr_animate_entity_tile_merge(void);
int main(int argc,char**argv){
 if(argc!=5)return 2;char save[4096];snprintf(save,sizeof(save),"%s/private.srm",argv[2]);
 char*boot[]={"tile-merge-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1",atoi(argv[4])?"--redux-battle-fixture":"--inspect-shuffle","0"};
 if(eb_platform_main(atoi(argv[4])?13:12,boot))return 3;
 FILE*f=fopen(argv[3],"r");if(!f)return 4;unsigned index,seed,pattern;
 while(fscanf(f,"%u %u %u",&index,&seed,&pattern)==3){
  rng_state.a=seed&65535;rng_state.b=seed>>16;ert.entity_fade_states_length=0;
  unsigned before[64];for(unsigned i=0;i<64;i++){before[i]=pattern==0?0:pattern==1?(i%2==0):(i!=(seed%64));write_u16_le(ert.buffer+BUF_TILE_MERGE_SLOTS+2*i,before[i]);}
  write_u16_le(ert.buffer+BUF_TILE_MERGE_SLOTS+128,0x55aa);cr_animate_entity_tile_merge();
  unsigned changed=0,picked=65535;for(unsigned i=0;i<64;i++)if(read_u16_le(ert.buffer+BUF_TILE_MERGE_SLOTS+2*i)!=before[i]){changed++;picked=i;}
  if(changed!=1||read_u16_le(ert.buffer+BUF_TILE_MERGE_SLOTS+128)!=0x55aa)return 5;
  printf("TILE_MERGE [%u,%u,%u,%u]\n",index,picked,rng_state.a,rng_state.b);
 }fclose(f);return 0;
}
'''


def identify(a,out,rom):
 globals_,addresses,proof,_,_=stat.identify(a,out,rom)
 folder=out/'source-mapping';base=(folder/'rand.asm').read_text(encoding='utf-8').split('MOVEMENT_SPEEDS :=',1)[0]
 base=base.replace('.IMPORT BUFFER: absolute\n','')+f'BUFFER := ${globals_["BUFFER"]:06X}\n'
 known=''.join(f'{k} := ${v:06X}\n' for k,v in addresses.items())
 # Native's C4CED8 comment is a candidate only; full original source byte
 # equality below establishes it. Unreached upload/blend calls are relocated
 # by their original operands, and the entire body is checked without masks.
 candidate=0xC4CED8;cfg=folder/'tile.cfg';cfg.write_text((folder/'code.cfg').read_text(encoding='utf-8').replace('start=$C00000',f'start=${candidate:06X}'),encoding='utf-8')
 include=['--cpu','65816','-D','USA','-I',folder/'include-overlay','-I',a.native_source/'include','-I',a.native_source/'asm']
 def assemble(values,suffix):
  src=folder/('tile'+suffix+'.asm');obj=src.with_suffix('.o');blob=src.with_suffix('.bin')
  src.write_text(base+known+''.join(f'{k} := ${v:06X}\n' for k,v in values.items())+'.SEGMENT "CODE"\n.A16\n.I16\n.INCLUDE "overworld/entity/animate_entity_tile_merge.asm"\n',encoding='utf-8')
  mapping.run([a.ca65,*include,src,'-o',obj],src.with_suffix('.compile.log'));mapping.run([a.ld65,'-C',cfg,'-o',blob,obj],src.with_suffix('.link.log'));return blob
 names=('MERGE_SPRITE_TILE_PAIR','UPLOAD_ENTITY_SPRITE_TO_VRAM');placeholder={k:0xC00000 for k in names}
 first=assemble(placeholder,'-placeholder');data=first.read_bytes();actual=rom[candidate-0xC00000:candidate-0xC00000+len(data)];resolved={};mask=set()
 for i,name in enumerate(names):
  altered=assemble(dict(placeholder,**{name:0xC10101}),f'-reloc{i}').read_bytes()
  offsets=[n for n,(x,y) in enumerate(zip(data,altered)) if x!=y]
  if len(offsets)!=3 or offsets!=list(range(offsets[0],offsets[0]+3)):raise ValueError('Original tile external relocation changed')
  mask.update(offsets);resolved[name]=int.from_bytes(actual[offsets[0]:offsets[0]+3],'little')
 if any(x!=y for i,(x,y) in enumerate(zip(data,actual)) if i not in mask):raise ValueError('Full original tile candidate differs outside external operands')
 blob=assemble(resolved,'-verified')
 if blob.read_bytes()!=actual:raise ValueError('Complete unmasked original tile body differs')
 if a.redux_rom.read_bytes()[candidate-0xC00000:candidate-0xC00000+len(actual)]!=actual:raise ValueError('Pinned Redux changes tile function; separate oracle needed')
 proof.append({'symbol':'ANIMATE_ENTITY_TILE_MERGE','address':f'{candidate:06X}','originalSource':'overworld/entity/animate_entity_tile_merge.asm','byteEqualLength':len(actual),'byteEqualSha256':sha(blob),'ReduxFunctionByteEqual':True,'UnreachedOriginalExternalCalls':{k:f'{v:06X}' for k,v in resolved.items()}})
 return globals_,addresses,proof,candidate


def machine(a,out,globals_,address,rows):
 out.mkdir();samples=out/'samples.jsonl';ga=globals_['RAND_A']&65535;gb=globals_['RAND_B']&65535;length=globals_['ENTITY_FADE_STATES_LENGTH']&65535
 code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230');entry=0xc0ff00+len(code)
 code+=bytes((0x22,))+address.to_bytes(3,'little')+bytes.fromhex('7b8f08707e3b8f0a707e');finish=0xc0ff00+len(code);code+=bytes((0x4c,entry&255,entry>>8&255))
 lua=['local out=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))','local rows={'+','.join('{'+','.join(map(str,r))+'}' for r in rows)+'}',
 'local mem=emu.memType.snesWorkRam','local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256)%256,mem) end','local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end','local index=0;local calls=0;local before={}',
 'emu.addMemoryCallback(function() index=index+1;local r=assert(rows[index],"past corpus");'+f'w16({ga},r[1]%65536);w16({gb},math.floor(r[1]/65536));w16({length},0);'
 'for i=0,63 do local v=r[2]==0 and 0 or r[2]==1 and (i%2==0 and 1 or 0) or r[2]==2 and (i~=r[1]%64 and 1 or 0) or 0;before[i]=v;w16(0x17f00+2*i,v) end;w16(0x17f80,0x55aa) end,emu.callbackType.exec,'+str(entry)+')',
 f'emu.addMemoryCallback(function() calls=calls+1 end,emu.callbackType.exec,{address})',
 'emu.addMemoryCallback(function() assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"CPU frame corrupt");assert(r16(0x17f80)==0x55aa,"protected RAM corrupt");local changed=0;local picked=-1;for i=0,63 do if r16(0x17f00+2*i)~=before[i] then changed=changed+1;picked=i end end;assert(changed==1,"slot count differs");'+f'out:write(string.format("[%d,%d,%d,%d]\\n",index,picked,r16({ga}),r16({gb})));'
 'if index==#rows then assert(calls==#rows,"call count differs");out:flush();out:close();emu.log("TILE_MERGE_COMPLETE "..index);emu.breakExecution() end end,emu.callbackType.exec,'+str(finish)+')']
 script=out/'tile.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
 proc=subprocess.run([str(a.oracle.resolve()),str(a.rom.resolve()),'--home',str(out/'oracle-home'),'--frames','5000','--timeout','60','--lua-timeout','10','--lua-allow-io','--lua',str(script),'--write-memory','SnesPrgRom:0xff00:'+code.hex(),'--set-pc','0xc0ff00','--cpu','Snes'],capture_output=True,timeout=70)
 (out/'oracle.jsonl').write_bytes(proc.stdout);(out/'oracle.stderr').write_bytes(proc.stderr);events=[json.loads(x) for x in proc.stdout.decode().splitlines()];logs=[r for r in events if r['event']=='lua_log']
 if proc.returncode or not events[-1].get('ok') or events[-1].get('reason')!='debugger_break' or any(r['error_count'] for r in logs):raise ValueError('Original tile execution incomplete')
 if sum('TILE_MERGE_COMPLETE '+str(len(rows)) in r['text'] for r in logs)!=1:raise ValueError('Original tile completion missing')
 got=[json.loads(x) for x in samples.read_text(encoding='utf-8').splitlines()]
 if [r[0] for r in got]!=list(range(1,len(rows)+1)):raise ValueError('Original tile samples incomplete')
 return got,{'Calls':len(got),'StackDirectPageProtectedRamPassed':True,'CallerSha256':hashlib.sha256(code).hexdigest(),'LuaSha256':sha(script),'SamplesSha256':sha(samples)}


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('rom','redux-rom','oracle','ca65','ld65','native-source','build','runtime','original-assets','redux-assets','scratch','output'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--corrected-callback-source',type=Path);p.add_argument('--previous-report',type=Path);p.add_argument('--diagnostic',action='store_true');a=p.parse_args();a.scratch=local_scratch(a.scratch);a.native_source=a.native_source.resolve();a.build=a.build.resolve();a.runtime=a.runtime.resolve()
 if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch/output required')
 rom=a.rom.read_bytes()
 if len(rom)!=0x300000 or hashlib.sha1(rom).hexdigest()!=US_SHA1:raise ValueError('Exact clean USA ROM required')
 files=(a.rom,a.redux_rom,a.oracle,a.ca65,a.ld65,a.original_assets,a.redux_assets,a.runtime/'player.exe',a.runtime/'observer.exe',a.build/'game_lib/libearthbound_game.a',a.native_source/'src/entity/callbacks.c',Path(__file__),Path(stat.__file__))
 inputs={str(path):sha(path) for path in files};a.scratch.mkdir(parents=True);globals_,addresses,proof,address=identify(a,a.scratch,rom)
 rows=[((0x56781234+n*0x01010301)&0xffffffff,pattern) for n in range(512) for pattern in range(3)]
 expected,meta=machine(a,a.scratch/'original-machine',globals_,address,rows);modes=[]
 for mode,assets in (('original',a.original_assets),('redux',a.redux_assets)):
  out=a.scratch/mode;out.mkdir();exe,built=private_build(a,out,DRIVER);session=out/'session';session.mkdir();cases=out/'cases.tsv';cases.write_text(''.join(f'{i+1} {seed} {pattern}\n' for i,(seed,pattern) in enumerate(rows)),encoding='utf-8')
  proc=subprocess.run([str(exe),str(assets.resolve()),str(session),str(cases),str(int(mode=='redux'))],capture_output=True,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),timeout=30);(out/'native.log').write_bytes(proc.stdout+proc.stderr)
  if proc.returncode:raise ValueError('Native tile consumer failed')
  got=[json.loads(x[len('TILE_MERGE '):]) for x in proc.stdout.decode(errors='replace').splitlines() if x.startswith('TILE_MERGE ')]
  if [r[0] for r in got]!=list(range(1,len(rows)+1)):raise ValueError('Native tile corpus incomplete')
  diff=[{'Index':i+1,'Input':rows[i],'OriginalMachine':ref,'ActualNative':v} for i,(ref,v) in enumerate(zip(expected,got)) if ref!=v]
  modes.append({'Mode':mode,'Calls':len(got),'MismatchCount':len(diff),'FirstMismatches':diff[:20],'PrivateBuildEvidence':built})
 previous=None
 if a.previous_report:
  red=json.loads(a.previous_report.read_text(encoding='utf-8'))
  if red.get('format')!='tile-merge-rng-micro-oracle-v1' or red['Passed']:raise ValueError('Expected completed red tile evidence')
  previous={'Path':a.previous_report.as_posix(),'Sha256':sha(a.previous_report),'MismatchCounts':[r['MismatchCount'] for r in red['Modes']]}
 if any(sha(Path(path))!=value for path,value in inputs.items()):raise ValueError('Immutable input changed')
 report={'format':'tile-merge-rng-micro-oracle-v1','Passed':not any(r['MismatchCount'] for r in modes),'SourceProof':proof,'MachineEvidence':meta,'Modes':modes,'InputIdentities':inputs,'PreservedRedBaseline':previous,'OwnerSavesTouched':False,'SharedBuildEdited':False,'Limits':['Actual original full function runs with zero active fade entries; unused upload/blend helpers are not executed.','RNG state transition, slot selection and occupied-slot wrap are compared; sprite blend/VRAM fidelity and full fade timelines remain unverified.','Redux original function is byte-identical here; native profile checks use actual pack loading.']}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'Passed':report['Passed'],'Modes':[{k:r[k] for k in ('Mode','Calls','MismatchCount')} for r in modes]}),flush=True)
 if not report['Passed'] and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
