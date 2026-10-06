# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare party trail helpers and screen movement with untouched USA SNES code.

Explicit local inputs only. The original source is reassembled to identify
complete byte-equal routines; the oracle executes the owner's unchanged ROM
with a private caller in emulator memory. Production native functions come
from an immutable supplied build. Only fresh private scratch and a new JSON
report are written. ROMs, asset packs, saves and shared builds are untouched.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess

import snes_position_arithmetic_oracle as identity
from check_jev_observer_parity import local_scratch
from snes_movement_helpers_oracle import sha, US_SHA1


ROUTINES = (
    ('FOLLOWER_SPACING_THRESHOLDS','data/overworld/follower_spacing_thresholds.asm','data'),
    ('FOLLOWER_DIAGONAL_SPACING_THRESHOLDS','data/overworld/follower_diagonal_spacing_thresholds.asm','data'),
    ('CHECK_FOLLOWER_VERTICAL_DISTANCE','overworld/party/check_follower_vertical_distance.asm','near'),
    ('CHECK_FOLLOWER_HORIZONTAL_DISTANCE','overworld/party/check_follower_horizontal_distance.asm','near'),
    ('CHECK_FOLLOWER_DIAGONAL_DISTANCE','overworld/party/check_follower_diagonal_distance.asm','near'),
    ('FOLLOWER_DISTANCE_CHECK_TABLE','data/overworld/follower_distance_check_table.asm','data'),
    ('UPDATE_PARTY_SPRITE_POSITION','overworld/party/update_party_sprite_position.asm','near'),
    ('GET_PREVIOUS_POSITION_INDEX','overworld/get_previous_position_index.asm','near'),
    ('GET_DISTANCE_TO_PARTY_MEMBER','overworld/party/get_distance_to_party_member.asm','far'),
    ('ADJUST_PARTY_MEMBER_VISIBILITY','overworld/party/adjust_party_member_visibility.asm','far'),
)


def corpus():
    cases=[]
    def add(kind,group,**v):
        row=dict(kind=kind,group=group,char=1,prev=64,current=32,spacing=12,
                 flags=0,order=0,direction=2,notAligned=0,leaderSlot=23,slot=24,
                 ordinal=1,absX=500,absY=600,leaderX=483,leaderY=600,
                 screenX=80,screenY=90,leaderScreenX=63,leaderScreenY=90,
                 bgX=420,bgY=510)
        row.update(v);cases.append(row)
    for order in range(4):
        for char in (0,1,2,3,6,9):
            for prev in (0,1,15,16,127,128,239,254,255):
                add('previous','valid-party-permutations-and-wrap-ends',order=order,char=char,prev=prev,current=0)
    for prev in range(256):
        for current in range(256):
            add('distance','complete-8bit-circular-index-pairs',prev=prev,current=current)
    for current in range(256):
        for distance in (0,1,11,12,13,23,24,25,29,30,31,33,34,35,39,40,41,255):
            for spacing in (0,12,24,30,34,40):
                for flags in (0x0555,0x9555):
                    add('visibility','normal-stair-ladder-rope-and-npc-size-spacing',
                        prev=(current+distance)&255,current=current,spacing=spacing,flags=flags)
    cardinal=[0,17,32,47,62,77];diagonal=[0,11,22,32,43,54]
    for direction in range(8):
        for ordinal in range(1,6):
            target=(diagonal if direction&1 else cardinal)[ordinal]
            for delta in (target-2,target-1,target,target+1,target+2,target+3):
                for flags in (0,0x1000,0x1800,0x4000):
                    for notAligned in (0,1):
                        # Both signs, cardinal alignment, diagonal slopes and
                        # previous screen coordinates one pixel behind abs.
                        for sign in (-1,1):
                            x=500;y=600;lx=x;ly=y
                            if direction in (2,6):lx=x+sign*delta
                            elif direction in (0,4):ly=y+sign*delta
                            else:lx=x+sign*delta;ly=y+sign*delta
                            add('screen','aligned-follower-screen-spacing',direction=direction,ordinal=ordinal,
                                flags=flags,notAligned=notAligned,absX=x,absY=y,leaderX=lx,leaderY=ly,
                                screenX=79,screenY=89,leaderScreenX=lx-420,leaderScreenY=ly-510)
    # Explicit shortcut guards: leader itself, facing differs, aligned cardinals.
    for direction in range(8):
        add('screen','leader-screen-callback-guard',direction=direction,slot=23)
        add('screen','screen-direction-mismatch-guard',direction=direction,notAligned=2)
    return cases


ORDERS=((0,1,2,3,6,9),(2,0,3,1,9,6),(9,6,3,2,1,0),(3,9,0,6,2,1))
FIELDS=('char','prev','current','spacing','flags','order','direction','notAligned','leaderSlot','slot',
        'ordinal','absX','absY','leaderX','leaderY','screenX','screenY','leaderScreenX','leaderScreenY','bgX','bgY')
KINDS={'previous':0,'distance':1,'visibility':2,'screen':3}


def machine(a,out,rom,globals_,mapping,cases):
    out.mkdir();samples=out/'samples.jsonl'
    # Own native-mode caller, A/X/Y16, DBR7E, DP1800, SP1FFF. Direct-page
    # addresses remain inside bank zero's first8KiB WRAM mirror. Callbacks
    # use current slot*2 at DP+88, while C helpers use CURRENT_ENTITY_SLOT.
    # Visibility's fourth parameter (advance=2) is caller DP+14.
    code=bytearray.fromhex('78d818fbc230a2ff1f9aa900185be220a97e48abc230')
    entry=0xC0FF00+len(code);code.extend(bytes.fromhex('af00717e'))
    branches=[]
    for kind in range(4):
        code.extend((0xC9,kind,0,0xF0,0));branches.append(len(code)-1)
    code.append(0);starts=[];jumps=[]
    def call(name,far):
        address=mapping[name]
        if far:code.extend((0x22,)+tuple(address.to_bytes(3,'little')))
        else:
            if address>>16!=0xC0:raise ValueError('Original near callback bank changed')
            code.extend((0x20,address&255,(address>>8)&255))
    for kind,name in enumerate(('GET_PREVIOUS_POSITION_INDEX','GET_DISTANCE_TO_PARTY_MEMBER',
                                'ADJUST_PARTY_MEMBER_VISIBILITY','UPDATE_PARTY_SPRITE_POSITION')):
        starts.append(0xC0FF00+len(code))
        if kind==2:code.extend(bytes.fromhex('af02717eaaaf04717ea8af06717e'))
        elif kind!=3:code.extend(bytes.fromhex('af06717e'))
        call(name,kind in (1,2));code.extend(bytes.fromhex('8f06707e'))
        code.extend((0x4C,0,0));jumps.append(len(code)-2)
    finish=0xC0FF00+len(code);code.extend(bytes.fromhex('7b8f08707e3b8f0a707e'))
    sampled=0xC0FF00+len(code);code.extend((0x4C,entry&255,(entry>>8)&255))
    for at,start in zip(branches,starts):
        delta=start-(0xC0FF00+at+1)
        if not -128<=delta<=127:raise ValueError('Caller branch out of range')
        code[at]=delta&255
    for at in jumps:code[at:at+2]=(finish&65535).to_bytes(2,'little')
    w=lambda key:globals_[key]&65535
    lua=['local output=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))','local cases={']
    lua+=['{'+','.join(map(str,(KINDS[c['kind']],*(c[k] for k in FIELDS))))+'},' for c in cases]
    lua+=['}','local orders={{0,1,2,3,6,9},{2,0,3,1,9,6},{9,6,3,2,1,0},{3,9,0,6,2,1}}',
          'local mem=emu.memType.snesWorkRam','local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256)%256,mem) end',
          'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end','local index=0;local calls={0,0,0,0};w16(0xe800,0x55aa)',
          'local function partyIndex(char) if char<4 then return char elseif char==6 then return 4 elseif char==9 then return 5 else error("invalid char") end end',
          'emu.addMemoryCallback(function()',
          ' index=index+1;local c=assert(cases[index],"past corpus");w16(0x7100,c[1]);w16(0x7102,c[5]);w16(0x7104,c[4]);w16(0x7106,c[2]);w16(0x180e,2)',
          f' local game={w("GAME_STATE")};local chars={w("PARTY_CHARACTERS")};local order=orders[c[7]+1]',
          ' for i=0,5 do w16('+str(w('CHOSEN_FOUR_PTRS'))+'+2*i,chars+95*i);w16(chars+95*i+61,c[3]) end',
          ' for i,id in ipairs(order) do emu.write(game+150+i-1,id+1,mem);w16(game+162+2*(i-1),22+i);w16('+str(w('ENTITY_SCRIPT_VAR1_TABLE'))+'+2*(22+i),partyIndex(id)) end',
          ' for i,id in ipairs(order) do if id==c[2] then if i>1 then w16(chars+95*partyIndex(order[i-1])+61,c[3]) end end end',
          ' w16(chars+95*partyIndex(c[2])+61,c[4]);w16('+str(w('CURRENT_PARTY_MEMBER_TICK'))+',chars+95*partyIndex(c[2]));w16('+str(w('CURRENT_ENTITY_SLOT'))+',c[11])',
          ' w16('+str(w('ENTITY_SCRIPT_VAR7_TABLE'))+'+2*c[11],c[6]);w16(0x1888,2*c[11]);w16('+str(w('CURRENT_LEADING_PARTY_MEMBER_ENTITY'))+',2*c[10])',
          ' w16('+str(w('CURRENT_LEADER_DIRECTION'))+',c[8]);w16('+str(w('ENTITY_DIRECTIONS'))+'+2*c[11],(c[9]==2 and (c[8]+1)%8 or c[8]))',
          ' w16('+str(w('NOT_MOVING_IN_SAME_DIRECTION_FACED'))+',c[9]==1 and 1 or 0);w16('+str(w('ENTITY_SCRIPT_VAR5_TABLE'))+'+2*c[11],2*c[12])',
          ' w16('+str(w('ENTITY_ABS_X_TABLE'))+'+2*c[11],c[13]);w16('+str(w('ENTITY_ABS_Y_TABLE'))+'+2*c[11],c[14]);w16('+str(w('ENTITY_ABS_X_TABLE'))+'+2*c[10],c[15]);w16('+str(w('ENTITY_ABS_Y_TABLE'))+'+2*c[10],c[16])',
          ' w16('+str(w('ENTITY_SCREEN_X_TABLE'))+'+2*c[11],c[17]);w16('+str(w('ENTITY_SCREEN_Y_TABLE'))+'+2*c[11],c[18]);w16('+str(w('ENTITY_SCREEN_X_TABLE'))+'+2*c[10],c[19]);w16('+str(w('ENTITY_SCREEN_Y_TABLE'))+'+2*c[10],c[20])',
          ' w16('+str(w('BG1_X_POS'))+',c[21]);w16('+str(w('BG1_Y_POS'))+',c[22])',
          f'end,emu.callbackType.exec,{entry})']
    for i,name in enumerate(('GET_PREVIOUS_POSITION_INDEX','GET_DISTANCE_TO_PARTY_MEMBER','ADJUST_PARTY_MEMBER_VISIBILITY','UPDATE_PARTY_SPRITE_POSITION')):
        lua.append(f'emu.addMemoryCallback(function() calls[{i+1}]=calls[{i+1}]+1 end,emu.callbackType.exec,{mapping[name]})')
    counts=Counter(c['kind'] for c in cases)
    lua+=['emu.addMemoryCallback(function()',
          ' assert(r16(0x7008)==0x1800 and r16(0x700a)==0x1fff,"CPU frame corrupted");assert(r16(0xe800)==0x55aa,"protected RAM corrupted")',
          ' local c=cases[index];local value=c[1]==3 and 0 or r16(0x7006)',
          f' output:write(string.format("[%d,%d,%d,%d,%d]\\n",index,value,r16({w("ENTITY_SCRIPT_VAR7_TABLE")}+2*c[11]),r16({w("ENTITY_SCREEN_X_TABLE")}+2*c[11]),r16({w("ENTITY_SCREEN_Y_TABLE")}+2*c[11])))',
          f' if index==#cases then assert(calls[1]=={counts["previous"]+counts["distance"]+counts["visibility"]} and calls[2]=={counts["distance"]+counts["visibility"]} and calls[3]=={counts["visibility"]} and calls[4]=={counts["screen"]},"call count differs");output:flush();output:close();emu.log("PARTY_FOLLOW_CORPUS_COMPLETE "..index);emu.breakExecution() end',
          f'end,emu.callbackType.exec,{sampled})']
    script=out/'party.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
    r=subprocess.run([str(a.oracle.resolve()),str(a.rom.resolve()),'--home',str(out/'oracle-home'),
                      '--frames','10000','--timeout','60','--lua-timeout','10','--lua-allow-io','--lua',str(script),
                      '--write-memory','SnesPrgRom:0xff00:'+code.hex(),'--set-pc','0xc0ff00','--cpu','Snes'],capture_output=True,timeout=70)
    (out/'oracle.jsonl').write_bytes(r.stdout);(out/'oracle.stderr').write_bytes(r.stderr)
    events=[json.loads(line) for line in r.stdout.decode().splitlines()];logs=[e for e in events if e['event']=='lua_log']
    if r.returncode or not events[-1].get('ok') or events[-1].get('reason')!='debugger_break' or any(e['error_count'] for e in logs):raise RuntimeError('Original corpus failed')
    if sum('PARTY_FOLLOW_CORPUS_COMPLETE ' in e['text'] for e in logs)!=1:raise RuntimeError('Original completion missing/duplicated')
    rows=[json.loads(line) for line in samples.read_text(encoding='utf-8').splitlines()]
    if [r[0] for r in rows]!=list(range(1,len(cases)+1)):raise RuntimeError('Original corpus incomplete/unordered')
    return rows,dict(ExecutedCases=len(cases),ExpectedHelperCalls=dict(counts),CompleteOrderedCorpusVerified=True,
                      StackDirectPageAndProtectedRamCanariesPassed=True,OriginalFullFunctionsUnmodified=True,
                      OriginalMachineAccumulator16=True,OwnCallerSha256=hashlib.sha256(code).hexdigest(),LuaSha256=sha(script),SamplesSha256=sha(samples))


DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game/position_buffer.h"
#include "game/game_state.h"
#include "game/overworld.h"
#include "game/maternalbound.h"
#include "entity/entity.h"
#include "entity/callroutine_internal.h"
#include "snes/ppu.h"
#include "platform/platform.h"
#include "include/constants.h"
extern int eb_platform_main(int,char**);
extern void call_move_callback(int16_t);
static const unsigned orders[4][6]={{0,1,2,3,6,9},{2,0,3,1,9,6},{9,6,3,2,1,0},{3,9,0,6,2,1}};
static unsigned party_index(unsigned character){return character<4?character:character==6?4:5;}
int main(int argc,char**argv){
 if(argc!=5)return 2;char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 char*boot[]={"party-follow-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,
  "--allow-redux-development","--headless","--frames","1",atoi(argv[4])?"--redux-battle-fixture":"--inspect-shuffle","0"};
 if(eb_platform_main(atoi(argv[4])?13:12,boot))return 3;
 FILE*f=fopen(argv[3],"r");if(!f)return 4;char line[4096];
 while(fgets(line,sizeof(line),f)){
  unsigned v[32],n=0;for(char*p=strtok(line," \t\r\n");p&&n<32;p=strtok(NULL," \t\r\n"))v[n++]=strtoul(p,NULL,10);
  if(n!=23)return 5;unsigned index=v[0],kind=v[1],c=v[2],prev=v[3],current=v[4],spacing=v[5],flags=v[6],order=v[7],dir=v[8],aligned=v[9],leader=v[10],slot=v[11],ordinal=v[12];
  memset(&entities,0,sizeof(entities));memset(party_characters,0,sizeof(CharStruct)*TOTAL_PARTY_COUNT);
  for(unsigned i=0;i<6;i++){unsigned id=orders[order][i];game_state.party_order[i]=id+1;
   game_state.party_entity_slots[2*i]=23+i;game_state.party_entity_slots[2*i+1]=0;entities.var[1][23+i]=party_index(id);}
  for(unsigned i=0;i<6;i++)if(orders[order][i]==c&&i)party_characters[party_index(orders[order][i-1])].position_index=prev;
  party_characters[party_index(c)].position_index=current;
  entities.var[7][slot]=flags;entities.var[5][slot]=2*ordinal;entities.move_callback[slot]=CB_MOVE_PARTY_SPRITE;
  ow.current_leading_party_member_entity=leader;ow.current_leader_direction=dir;ow.not_moving_in_same_direction_faced=aligned==1;
  entities.directions[slot]=aligned==2?(dir+1)%8:dir;
  entities.abs_x[slot]=v[13];entities.abs_y[slot]=v[14];entities.abs_x[leader]=v[15];entities.abs_y[leader]=v[16];
  entities.screen_x[slot]=v[17];entities.screen_y[slot]=v[18];entities.screen_x[leader]=v[19];entities.screen_y[leader]=v[20];
  ppu.bg_hofs[0]=v[21];ppu.bg_vofs[0]=v[22];unsigned value=0;
  if(kind==0)value=get_distance_to_party_member(c,0);else if(kind==1)value=get_distance_to_party_member(c,current);
  else if(kind==2)value=adjust_party_member_visibility(slot,c,current,spacing);else call_move_callback(slot);
  printf("PARTY_NATIVE [%u,%u,%u,%u,%u]\n",index,value,(uint16_t)entities.var[7][slot],(uint16_t)entities.screen_x[slot],(uint16_t)entities.screen_y[slot]);
 }fclose(f);return 0;
}
'''


def native(a,out,cases,mode):
    from party_follow_private_build import private_build
    out.mkdir();exe,built=private_build(a,out,DRIVER)
    source=a.original_assets if mode=='original' else a.redux_assets
    session=out/'session';session.mkdir();inputs=out/'cases.tsv'
    inputs.write_text(''.join(' '.join(map(str,(i+1,KINDS[c['kind']],*(c[k] for k in FIELDS))))+'\n' for i,c in enumerate(cases)),encoding='utf-8')
    env=os.environ.copy();env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    r=subprocess.run([str(exe),str(source.resolve()),str(session.resolve()),str(inputs.resolve()),str(int(mode=='redux'))],capture_output=True,env=env,timeout=60)
    (out/'native.log').write_bytes(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError('Production driver failed: '+r.stderr.decode(errors='replace'))
    rows=[json.loads(line[len('PARTY_NATIVE '):]) for line in r.stdout.decode(errors='replace').splitlines() if line.startswith('PARTY_NATIVE ')]
    if [v[0] for v in rows]!=list(range(1,len(cases)+1)):raise RuntimeError('Production corpus incomplete/unordered')
    return rows,dict(ProductionLibrarySha256=sha(a.build/'game_lib/libearthbound_game.a'),
                     ProductionExecutableSha256=sha(a.build/'earthbound.exe'),ProbeSha256=sha(exe),DriverSourceSha256=built['DriverSourceSha256'],
                     PrivateLinkEvidence=built,
                     PreparedPreviousLookupUsesActualDistanceWithCurrentZero=True,NativeLogSha256=sha(out/'native.log'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','oracle','ca65','ld65','native-source','build','runtime','original-assets','redux-assets','scratch','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--diagnostic',action='store_true',help='Preserve completed differences; incomplete calls still fail.')
    p.add_argument('--corrected-callback-source',type=Path,help='Compile only actual reviewed callbacks.c into a copied private archive; production library stays frozen.')
    p.add_argument('--previous-report',type=Path,help='Link the preserved completed320-screen-difference red baseline.')
    a=p.parse_args();out=local_scratch(a.scratch);a.build=a.build.resolve();a.native_source=a.native_source.resolve()
    if out.exists() or a.output.exists():raise ValueError('Use fresh scratch and report paths')
    a.scratch=out;a.runtime=a.runtime.resolve();rom=a.rom.read_bytes()
    if len(rom)!=0x300000 or hashlib.sha1(rom).hexdigest()!=US_SHA1:raise ValueError('Exact clean USA ROM required')
    if sha(a.build/'earthbound.exe')!=sha(a.runtime/'player.exe'):raise ValueError('Frozen build/runtime mismatch')
    identities={name:sha(path) for name,path in (('originalRom',a.rom),('originalAssets',a.original_assets),('reduxAssets',a.redux_assets),
                ('productionLibrary',a.build/'game_lib/libearthbound_game.a'),('player',a.runtime/'player.exe'),('observer',a.runtime/'observer.exe'),
                ('positionSource',a.native_source/'src/game/position_buffer.c'),('callbackSource',a.native_source/'src/entity/callbacks.c'))}
    out.mkdir(parents=True)
    # These two source fragments inherit A16 from preceding vertical code
    # in the real bank. Set that assembler width in a private include wrapper;
    # this emits no instructions, and full unmasked ROM byte equality gates it.
    wrappers=out/'identification-wrappers';wrappers.mkdir();routines=[]
    for name,relative,abi in ROUTINES:
        if name in ('CHECK_FOLLOWER_HORIZONTAL_DISTANCE','CHECK_FOLLOWER_DIAGONAL_DISTANCE','GET_DISTANCE_TO_PARTY_MEMBER'):
            wrapper=wrappers/(name.lower()+'.asm')
            if name=='GET_DISTANCE_TO_PARTY_MEMBER':
                body=(a.native_source/'asm'/relative).read_text(encoding='utf-8')
                operand='JSR GET_PREVIOUS_POSITION_INDEX'
                if body.count(operand)!=1:raise ValueError('Original near dependency source changed')
                wrapper.write_text('.A16\n'+body.replace(operand,'JSR .LOWORD(GET_PREVIOUS_POSITION_INDEX)'),encoding='utf-8')
            else:
                original_relative=os.path.relpath(a.native_source/'asm'/relative,wrappers).replace('\\','/')
                wrapper.write_text('.A16\n.INCLUDE "'+original_relative+'"\n',encoding='utf-8')
            routines.append((name,'../identification-wrappers/'+wrapper.name,abi))
        else:routines.append((name,relative,abi))
    old=identity.ROUTINES;identity.ROUTINES=tuple(routines)
    try:globals_,mapping,evidence=identity.identify(a,out,rom)
    finally:identity.ROUTINES=old
    for record,(name,relative,abi) in zip(evidence[2:],ROUTINES):
        if record['symbol']!=name:raise RuntimeError('Source identification order changed')
        if name in ('CHECK_FOLLOWER_HORIZONTAL_DISTANCE','CHECK_FOLLOWER_DIAGONAL_DISTANCE','GET_DISTANCE_TO_PARTY_MEMBER'):
            record['PrivateAssemblerWidthWrapper']=record['originalSource'];record['originalSource']=relative
            if name=='GET_DISTANCE_TO_PARTY_MEMBER':record['PrivateNearDependencyOperandLowWordAdaptation']=True
    cases=corpus();reference,ometa=machine(a,out/'original-machine',rom,globals_,mapping,cases);modes=[]
    for mode in ('original','redux'):
        actual,nmeta=native(a,out/(mode+'-native'),cases,mode)
        differences=[dict(cases[i],index=i+1,OriginalMachine=ref[1:],ActualNative=got[1:]) for i,(ref,got) in enumerate(zip(reference,actual)) if ref!=got]
        modes.append(dict(mode=mode,ExecutedCases=len(cases),NativeMismatchCount=len(differences),MismatchGroups=dict(Counter(c['kind'] for c in differences)),
                          NativeMismatches=differences,CompiledProductionEvidence=nmeta))
    for name,path in (('originalRom',a.rom),('originalAssets',a.original_assets),('reduxAssets',a.redux_assets),
                      ('productionLibrary',a.build/'game_lib/libearthbound_game.a'),('player',a.runtime/'player.exe'),('observer',a.runtime/'observer.exe'),
                      ('positionSource',a.native_source/'src/game/position_buffer.c'),('callbackSource',a.native_source/'src/entity/callbacks.c')):
        if sha(path)!=identities[name]:raise RuntimeError('Immutable input changed during audit: '+name)
    previous=None
    if a.previous_report:
        red=json.loads(a.previous_report.read_text(encoding='utf-8'))
        if red.get('format')!='native-party-follow-review-v1' or red.get('Passed') is not False or any(m['NativeMismatchCount']!=320 for m in red['Modes']):raise ValueError('Unexpected red baseline')
        for key in ('originalRom','originalAssets','reduxAssets','productionLibrary','player','observer'):
            if red['InputIdentities'][key]!=identities[key]:raise ValueError('Red immutable inputs differ')
        previous=dict(path=a.previous_report.as_posix(),sha256=sha(a.previous_report),NativeMismatchCounts=[m['NativeMismatchCount'] for m in red['Modes']])
    report=dict(format='native-party-follow-review-v1',Passed=not any(m['NativeMismatchCount'] for m in modes),
                PreservedRedBaseline=previous,PrivateCorrectedCallbackSourceRequested=bool(a.corrected_callback_source),
                InputIdentities=identities,SourceMapping=evidence,OriginalMachineEvidence=ometa,Modes=modes,
                CountsByKind=dict(Counter(c['kind'] for c in cases)),Runner=dict(path='tools/snes_party_follow_oracle.py',sha256=sha(Path(__file__)),
                IdentificationTool=dict(path='tools/snes_position_arithmetic_oracle.py',sha256=sha(Path(identity.__file__)))),
                OwnerSavesTouched=False,OwnerRomsAndPacksUnchanged=True,SharedSourceEdited=False,SharedBuildsEdited=False,
                FullPlaythroughVerified=False,FullPartyCollisionParityVerified=False,
                Limits=['Function contexts use valid party IDs and entity slots; arbitrary event/story reachability is not certified.',
                        'Visibility advance parameter is2, as supplied by the normal full follower caller; helper calls do not validate the complete follower sprite/assets tick.',
                        'Screen callback runs A16 as required by RUN_ACTIONSCRIPT_FRAME. Original assembly declares A8 for one deliberate immediate encoding; runtime consumes its following CLC byte as the high byte of AND#1800.',
                        'Screen comparisons concern visual coordinates only, and do not demonstrate an absolute-position collision blocker.',
                        'Redux uses original pure circular helper and screen expectations here; deliberate Redux graphics/run adaptations and natural traversal are outside this bounded audit.'])
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(Passed=report['Passed'],CountsByKind=report['CountsByKind'],Modes=[{k:m[k] for k in ('mode','ExecutedCases','NativeMismatchCount','MismatchGroups')} for m in modes])),flush=True)
    if not report['Passed'] and not a.diagnostic:raise SystemExit(1)


if __name__=='__main__':main()
