# SPDX-License-Identifier: GPL-3.0-or-later
"""Trace real party screen callbacks during ordinary copied-save walking.

The immutable production library is linked to a read-only callback wrapper
in a private probe. Its normal SDL/game loop loads an explicit private QA
checkpoint and ordinary replay inputs. Each reachable pre/post callback state
is compared with the untouched USA machine routine. No owner save, ROM,
asset pack, production source or shared build is modified.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import hashlib

from check_jev_observer_parity import local_scratch
from snes_movement_helpers_oracle import sha,US_SHA1
import snes_party_follow_oracle as follow
import snes_position_arithmetic_oracle as identity
from party_follow_private_build import private_build as link_private


DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include "core/memory.h"
#include "game/overworld.h"
#include "entity/entity.h"
#include "entity/callroutine_internal.h"
#include "snes/ppu.h"
extern int eb_platform_main(int,char**);
extern void __real_call_move_callback(int16_t);
static FILE*trace;
void __wrap_call_move_callback(int16_t slot){
 unsigned v[20],record=entities.move_callback[slot]==CB_MOVE_PARTY_SPRITE;
 int16_t lead=(int16_t)ow.current_leading_party_member_entity;
 if(record && (lead<0||lead>=MAX_ENTITIES))exit(8);
 if(record){
  v[0]=core.frame_counter;v[1]=slot;v[2]=lead;v[3]=(uint16_t)entities.var[5][slot];
  v[4]=(uint16_t)entities.var[7][slot];v[5]=ow.current_leader_direction;v[6]=(uint16_t)entities.directions[slot];
  v[7]=ow.not_moving_in_same_direction_faced;v[8]=(uint16_t)entities.abs_x[slot];v[9]=(uint16_t)entities.abs_y[slot];
  v[10]=(uint16_t)entities.abs_x[lead];v[11]=(uint16_t)entities.abs_y[lead];
  v[12]=(uint16_t)entities.screen_x[slot];v[13]=(uint16_t)entities.screen_y[slot];
  v[14]=(uint16_t)entities.screen_x[lead];v[15]=(uint16_t)entities.screen_y[lead];
  v[16]=ppu.bg_hofs[0];v[17]=ppu.bg_vofs[0];v[18]=entities.screen_pos_callback[slot];v[19]=entities.var[0][slot];
 }
 __real_call_move_callback(slot);
 if(record){fprintf(trace,"[");for(unsigned i=0;i<20;i++)fprintf(trace,"%s%u",i?",":"",v[i]);
  fprintf(trace,",%u,%u]\n",(uint16_t)entities.screen_x[slot],(uint16_t)entities.screen_y[slot]);}
}
int main(int argc,char**argv){
 if(argc!=6)return 2;trace=fopen(argv[5],"wb");if(!trace)return 3;
 char save[4096],cfg[4096],input[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 snprintf(cfg,sizeof(cfg),"%s/fixture.ini",argv[2]);snprintf(input,sizeof(input),"%s/input.replay",argv[2]);
 char*boot[]={"party-reachable-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,
  "--config",cfg,"--allow-redux-development","--skip-intro","--load-state","--headless",
  "--input-script",input,"--frames",argv[3],"--capture-state",argv[4],"--fast-forward"};
 int result=eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot);fclose(trace);return result;
}
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('checkpoint','assets','rom','oracle','ca65','ld65','native-source','build','runtime','scratch','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--corrected-callback-source',type=Path,help='Compile actual corrected callbacks.c in a copied private archive only.')
    p.add_argument('--previous-report',type=Path,help='Link the preserved ordinary replay66-difference red evidence.')
    a=p.parse_args();out=local_scratch(a.scratch);checkpoint=local_scratch(a.checkpoint)
    if out.exists() or a.output.exists():raise ValueError('Fresh scratch/report required')
    if not checkpoint.is_dir() or not (checkpoint/'saves').is_dir():raise ValueError('Explicit copied QA checkpoint required')
    a.native_source=a.native_source.resolve();a.build=a.build.resolve();a.runtime=a.runtime.resolve()
    if sha(a.build/'earthbound.exe')!=sha(a.runtime/'player.exe'):raise ValueError('Frozen build/runtime differs')
    rom=a.rom.read_bytes()
    if len(rom)!=0x300000 or hashlib.sha1(rom).hexdigest()!=US_SHA1:raise ValueError('Clean USA ROM required')
    sourcefiles=sorted((checkpoint/'saves').glob('*'));sourcehashes={f.name:sha(f) for f in sourcefiles if f.is_file()}
    inputs={'rom':sha(a.rom),'assets':sha(a.assets),'player':sha(a.runtime/'player.exe'),'observer':sha(a.runtime/'observer.exe'),
            'productionLibrary':sha(a.build/'game_lib/libearthbound_game.a')}
    out.mkdir(parents=True);exe,buildmeta=link_private(a,out,DRIVER,wrap=True)
    traces=[];cases=[];env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    for direction,pad in enumerate((0x0800,0x0900,0x0100,0x0500,0x0400,0x0600,0x0200,0x0a00)):
        folder=out/f'ordinary-direction{direction}';folder.mkdir();shutil.copytree(checkpoint/'saves',folder/'saves')
        if (checkpoint/'settings.dat').exists():shutil.copy2(checkpoint/'settings.dat',folder/'settings.dat')
        srm=checkpoint/'fixture.srm'
        if not srm.exists():srm=checkpoint/'saves/earthbound.srm'
        if srm.exists():shutil.copy2(srm,folder/'fixture.srm')
        (folder/'fixture.ini').write_text('companion=1\nwidth=640\nheight=480\nvolume=0\nno_dad_calls=1\nno_homesickness=1\nfast_forward_multiplier=16\n',encoding='utf-8')
        # Walk down to leave the bed first, then try ordinary cardinal/diagonal
        # inputs. No coordinate, event, party, inventory or history mutation.
        (folder/'input.replay').write_text(f'0 0\n10 0400\n45 0000\n55 {pad:04x}\n130 0\n',encoding='utf-8')
        trace=folder/'callback.jsonl'
        r=subprocess.run([str(exe),str(a.assets.resolve()),str(folder),'220','160',str(trace)],capture_output=True,env=env,timeout=30)
        (folder/'native.log').write_bytes(r.stdout+r.stderr)
        if r.returncode or b'PC replay checkpoint:' not in r.stderr:raise RuntimeError('Ordinary replay did not complete')
        rows=[json.loads(line) for line in trace.read_text(encoding='utf-8').splitlines()]
        if not rows:raise RuntimeError('Read-only link wrapper saw no party callback')
        for number,row in enumerate(rows):
            if len(row)!=22:raise RuntimeError('Malformed callback trace')
            frame,slot,leader,spacing,flags,ldir,fdir,unaligned,ax,ay,lx,ly,sx,sy,lsx,lsy,bgx,bgy,poscallback,char,*actual=row
            if spacing%2 or spacing>10 or ldir>7 or fdir>7:raise RuntimeError('Unsupported observed real party callback')
            # NOP screen callbacks are canonical party EVENT2 behavior. Other
            # types are still captured, but their later effect is outside scope.
            c=dict(kind='screen',group='ordinary-copied-owner-save-reachable-state',char=1,prev=64,current=32,spacing=12,
                flags=flags,order=0,direction=ldir,notAligned=1 if unaligned else 2 if fdir!=ldir else 0,
                leaderSlot=leader,slot=slot,ordinal=spacing//2,absX=ax,absY=ay,leaderX=lx,leaderY=ly,
                screenX=sx,screenY=sy,leaderScreenX=lsx,leaderScreenY=lsy,bgX=bgx,bgY=bgy)
            cases.append(c);traces.append(dict(routeDirection=direction,routeSample=number,frame=frame,char=char,
                positionCallback=poscallback,actual=actual,traceSha256=sha(trace)))
    # Reuse source identification on fresh private wrappers without touching
    # the release-frozen identity tool. This lookup only needs the screen graph.
    wrappers=out/'identification-wrappers';wrappers.mkdir();routines=[]
    for name,relative,abi in follow.ROUTINES[:7]:
        if name in ('CHECK_FOLLOWER_HORIZONTAL_DISTANCE','CHECK_FOLLOWER_DIAGONAL_DISTANCE'):
            wrapper=wrappers/(name.lower()+'.asm');rel=os.path.relpath(a.native_source/'asm'/relative,wrappers).replace('\\','/')
            wrapper.write_text('.A16\n.INCLUDE "'+rel+'"\n',encoding='utf-8');routines.append((name,'../identification-wrappers/'+wrapper.name,abi))
        else:routines.append((name,relative,abi))
    # machine() has all four callback gates, so identify circular helpers too.
    for name,relative,abi in follow.ROUTINES[7:]:
        if name=='GET_DISTANCE_TO_PARTY_MEMBER':
            wrapper=wrappers/(name.lower()+'.asm');body=(a.native_source/'asm'/relative).read_text(encoding='utf-8')
            if body.count('JSR GET_PREVIOUS_POSITION_INDEX')!=1:raise ValueError('Original near dependency changed')
            wrapper.write_text('.A16\n'+body.replace('JSR GET_PREVIOUS_POSITION_INDEX','JSR .LOWORD(GET_PREVIOUS_POSITION_INDEX)'),encoding='utf-8')
            routines.append((name,'../identification-wrappers/'+wrapper.name,abi))
        else:routines.append((name,relative,abi))
    old=identity.ROUTINES;identity.ROUTINES=tuple(routines)
    try:globals_,mapping,mappingmeta=identity.identify(a,out,rom)
    finally:identity.ROUTINES=old
    reference,ometa=follow.machine(a,out/'original-machine',rom,globals_,mapping,cases)
    differences=[]
    for i,(c,trace,ref) in enumerate(zip(cases,traces,reference)):
        if ref[-2:]!=trace['actual']:differences.append(dict(c,Trace=trace,OriginalMachineScreen=ref[-2:],ActualNativeScreen=trace['actual']))
    if sourcehashes!={f.name:sha(f) for f in sourcefiles if f.is_file()}:raise RuntimeError('Copied source checkpoint changed')
    for key,path in (('rom',a.rom),('assets',a.assets),('player',a.runtime/'player.exe'),('observer',a.runtime/'observer.exe'),('productionLibrary',a.build/'game_lib/libearthbound_game.a')):
        if sha(path)!=inputs[key]:raise RuntimeError('Immutable input changed')
    previous=None
    if a.previous_report:
        red=json.loads(a.previous_report.read_text(encoding='utf-8'))
        if red.get('format')!='party-follow-ordinary-reachability-review-v1' or red['NativeMismatchCount']!=66 or red['SourceSaveHashes']!=sourcehashes:raise ValueError('Unexpected ordinary red baseline')
        if red['ImmutableInputs']!=inputs:raise ValueError('Ordinary red immutable inputs differ')
        previous=dict(path=a.previous_report.as_posix(),sha256=sha(a.previous_report),NativeMismatchCount=red['NativeMismatchCount'])
    report=dict(format='party-follow-ordinary-reachability-review-v1',OrdinaryReplayCompleted=True,MatchedSourceCallback=not differences,
        PreservedRedBaseline=previous,PrivateCorrectedCallbackSourceRequested=bool(a.corrected_callback_source),
        ReplayRoutes=8,ObservedPartyCallbackStates=len(cases),NativeMismatchCount=len(differences),NativeMismatches=differences,
        MismatchesByDirection=dict(Counter(d['direction'] for d in differences)),SourceSaveHashes=sourcehashes,
        CopiedSourceCheckpointUnchanged=True,OwnerSavesTouched=False,ImmutableInputs=inputs,PrivateProductionProbe=buildmeta,
        OriginalMachineEvidence=ometa,SourceMapping=mappingmeta,FullPlaythroughVerified=False,CollisionBlockerDemonstrated=False,
        Limits=['Ordinary input routes start from an explicitly copied hotel checkpoint; no party/coordinate/event/history mutation.',
                'Read-only linker callback wrapper observes existing production game-loop callbacks; it does not change their arguments, result or timing rules.',
                'Original callback comparisons use each observed live pre-call geometry. They verify visual screen spacing, not entire story or collision parity.',
                'A confirmed screen mismatch may be hidden by a subsequent non-NOP screen callback; positionCallback IDs are included with each observation.'],
        Runner=dict(path='tools/party_follow_reachability_qa.py',sha256=sha(Path(__file__)),
                    FollowOracleSha256=sha(Path(follow.__file__)),IdentificationToolSha256=sha(Path(identity.__file__))))
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('OrdinaryReplayCompleted','ObservedPartyCallbackStates','NativeMismatchCount','MismatchesByDirection')}),flush=True)


if __name__=='__main__':main()
