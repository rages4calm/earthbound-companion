# SPDX-License-Identifier: GPL-3.0-or-later
"""Trace ordinary Redux follower walking/run transitions against its actual hook.

The caller supplies an already copied QA checkpoint, never owner live saves.
Read-only callback observation and ordinary input replay use a privately linked
immutable production library (or an explicit private callbacks replacement).
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import shutil
import subprocess
from check_jev_observer_parity import local_scratch
from snes_movement_helpers_oracle import sha, US_SHA1
import hashlib
import party_follow_reachability_qa as ordinary
import redux_party_screen_oracle as oracle
from party_follow_private_build import private_build


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('checkpoint','assets','rom','redux-rom','project','bridge','oracle','ca65','ld65','native-source','build','runtime','scratch','output'):
  p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--corrected-callback-source',type=Path);p.add_argument('--previous-report',type=Path)
 a=p.parse_args();a.scratch=local_scratch(a.scratch);checkpoint=local_scratch(a.checkpoint);a.native_source=a.native_source.resolve();a.build=a.build.resolve();a.runtime=a.runtime.resolve()
 if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch/output required')
 if not checkpoint.is_dir() or not (checkpoint/'saves').is_dir():raise ValueError('Explicit copied QA checkpoint required')
 rom=a.rom.read_bytes();redux=a.redux_rom.read_bytes()
 if len(rom)!=0x300000 or hashlib.sha1(rom).hexdigest()!=US_SHA1:raise ValueError('Exact clean USA ROM required')
 files=(a.rom,a.redux_rom,a.assets,a.bridge,a.build/'game_lib/libearthbound_game.a',a.runtime/'player.exe',a.runtime/'observer.exe',a.native_source/'src/entity/callbacks.c',a.native_source/'src/include/pad.h',Path(__file__),Path(oracle.__file__),Path(ordinary.__file__))
 identities={str(path):sha(path) for path in files};sourcehashes={f.name:sha(f) for f in (checkpoint/'saves').iterdir() if f.is_file()}
 if '#define PAD_Y      (1 << 14)' not in (a.native_source/'src/include/pad.h').read_text(encoding='utf-8'):raise ValueError('Source run-input bit changed')
 a.scratch.mkdir(parents=True)
 # Extend only our QA observer's columns with read-only actual pad, leader
 # velocity and Redux run-state measurements. Production arguments stay intact.
 driver=ordinary.DRIVER.replace('#include "snes/ppu.h"','#include "snes/ppu.h"\n#include "game/maternalbound.h"')
 driver=driver.replace('unsigned v[20]','unsigned v[24]').replace('for(unsigned i=0;i<20;i++)','for(unsigned i=0;i<24;i++)')
 anchor='v[16]=ppu.bg_hofs[0];v[17]=ppu.bg_vofs[0];v[18]=entities.screen_pos_callback[slot];v[19]=entities.var[0][slot];'
 if driver.count(anchor)!=1:raise ValueError('Read-only trace driver layout changed')
 driver=driver.replace(anchor,anchor+'\n  v[20]=core.pad1_held;v[21]=(uint16_t)entities.delta_x[lead];v[22]=(uint16_t)entities.delta_y[lead];v[23]=maternalbound_running();')
 exe,built=private_build(a,a.scratch,driver,wrap=True);traces=[];cases=[];routes=[];env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
 for direction,pad in enumerate((0x0800,0x0900,0x0100,0x0500,0x0400,0x0600,0x0200,0x0a00)):
  folder=a.scratch/f'ordinary-direction{direction}';folder.mkdir();shutil.copytree(checkpoint/'saves',folder/'saves')
  if (checkpoint/'settings.dat').exists():shutil.copy2(checkpoint/'settings.dat',folder/'settings.dat')
  srm=checkpoint/'fixture.srm'
  if not srm.exists():srm=checkpoint/'saves/earthbound.srm'
  if srm.exists():shutil.copy2(srm,folder/'fixture.srm')
  (folder/'fixture.ini').write_text('companion=1\nwidth=640\nheight=480\nvolume=0\nno_dad_calls=1\nno_homesickness=1\nfast_forward_multiplier=16\n',encoding='utf-8')
  # Leave the bed, walk normally, then hold/release Y twice. No mutation of
  # party/event/history/position/stamina flags is used to make this reachable.
  (folder/'input.replay').write_text(f'0 0\n10 0400\n45 0000\n55 {pad:04x}\n80 {pad|0x4000:04x}\n100 {pad:04x}\n110 {pad|0x4000:04x}\n130 0\n',encoding='utf-8')
  trace=folder/'callback.jsonl';proc=subprocess.run([str(exe),str(a.assets.resolve()),str(folder),'220','160',str(trace)],capture_output=True,env=env,timeout=30);(folder/'native.log').write_bytes(proc.stdout+proc.stderr)
  if proc.returncode or b'PC replay checkpoint:' not in proc.stderr:raise ValueError('Ordinary run replay incomplete')
  rows=[json.loads(x) for x in trace.read_text(encoding='utf-8').splitlines()]
  if not rows:raise ValueError('No party callback observations')
  routes.append({'Direction':direction,'ObservedCallbacks':len(rows),'RunStateValues':sorted(set(r[23] for r in rows)),'ActualPadYCallbacks':sum(bool(r[20]&0x4000) for r in rows),'LeaderVelocityPairs':sorted(set(tuple(r[21:23]) for r in rows)),'TraceSha256':sha(trace)})
  for number,row in enumerate(rows):
   if len(row)!=26:raise ValueError('Malformed extended party observation')
   frame,slot,leader,spacing,flags,ldir,fdir,unaligned,ax,ay,lx,ly,sx,sy,lsx,lsy,bgx,bgy,poscallback,char,padheld,vx,vy,running,*actual=row
   if spacing%2 or spacing>10 or ldir>7 or fdir>7:raise ValueError('Unsupported real party context')
   cases.append(dict(kind='screen',group='ordinary-copied-redux-save-run-transition',char=1,prev=64,current=32,spacing=12,flags=flags,order=0,direction=ldir,notAligned=1 if unaligned else 2 if fdir!=ldir else 0,leaderSlot=leader,slot=slot,ordinal=spacing//2,absX=ax,absY=ay,leaderX=lx,leaderY=ly,screenX=sx,screenY=sy,leaderScreenX=lsx,leaderScreenY=lsy,bgX=bgx,bgY=bgy))
   traces.append({'Route':direction,'RouteSample':number,'Frame':frame,'Character':char,'PositionCallback':poscallback,'PadHeld':padheld,'LeaderVelocity':[vx,vy],'Running':running,'Actual':actual})
 globals_,addresses,proof=oracle.identify(a,a.scratch,rom,redux);expected,mmeta=oracle.machine(a,a.scratch/'actual-redux-machine',globals_,addresses,cases)
 differences=[{'Input':cases[i],'Trace':traces[i],'ActualCompiledReduxScreen':r[-2:]} for i,r in enumerate(expected) if r[-2:]!=traces[i]['Actual']]
 if sourcehashes!={f.name:sha(f) for f in (checkpoint/'saves').iterdir() if f.is_file()}:raise ValueError('Copied QA checkpoint changed')
 if any(sha(Path(path))!=value for path,value in identities.items()):raise ValueError('Immutable input changed')
 previous=None
 if a.previous_report:
  red=json.loads(a.previous_report.read_text(encoding='utf-8'))
  if red.get('format')!='redux-party-follow-run-reachability-v1' or not red['NativeMismatchCount'] or red['SourceSaveHashes']!=sourcehashes:raise ValueError('Unexpected completed ordinary red evidence')
  previous={'Path':a.previous_report.as_posix(),'Sha256':sha(a.previous_report),'NativeMismatchCount':red['NativeMismatchCount']}
 report={'format':'redux-party-follow-run-reachability-v1','Passed':not differences,'ObservedCallbacks':len(cases),'NativeMismatchCount':len(differences),'MismatchesByDirection':dict(Counter(r['Input']['direction'] for r in differences)),'NativeMismatches':differences,'Routes':routes,'SourceSaveHashes':sourcehashes,'InputIdentities':identities,'PrivateBuildEvidence':built,'SourceProof':proof,'ActualReduxMachineEvidence':mmeta,'PreservedRedBaseline':previous,'OwnerSavesTouched':False,'FullPlaythroughVerified':False,'Limits':['Ordinary walk/run inputs in eight directions start from a copied owner hotel checkpoint; no progress, party or geometry mutation.','Actual run-input/run-state/velocity observations are reported; the input sequence alone does not prove uninterrupted sprint or that every route traversed its intended space.','Only party screen-coordinate callback parity is tested; stairs/collision, final rendered sprite positions and story coverage remain separate.']}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:report[k] for k in ('Passed','ObservedCallbacks','NativeMismatchCount','MismatchesByDirection')}),flush=True)

if __name__=='__main__':main()
