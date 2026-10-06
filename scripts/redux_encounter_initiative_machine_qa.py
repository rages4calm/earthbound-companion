# SPDX-License-Identifier: GPL-3.0-or-later
"""Execute real contact/init-encounter initiative prefixes on both local CPUs.

The complete Original/pinned bodies are uniquely byte-proven first. The actual
CPU runs contact, camera/palette helpers, direction, division and initiative,
then stops at the actual swirl entry. A private native wrapper observes that
same entry. Later swirl/pathfinding/combat are explicitly excluded. No original
routine bytes, ROM files, assets, owner saves or shared builds are changed.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from check_jev_observer_parity import local_scratch
from snes_movement_helpers_oracle import sha, US_SHA1
import redux_contact_phone_hook_qa as contact
import snes_direction_approach_oracle as direction
import snes_position_arithmetic_oracle as mapping


DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#include "game/overworld.h"
#include "game/battle.h"
#include "game/maternalbound.h"
#include "game/door.h"
#include "game/position_buffer.h"
#include "entity/entity.h"
#include "data/assets.h"
#include "data/event_script_data.h"
extern int eb_platform_main(int,char**);
extern int platform_max_frames;
extern void platform_input_init(void);
extern int16_t callroutine_dispatch(uint32_t,int16_t,int16_t,uint16_t,uint16_t*);
static jmp_buf done;
static unsigned current;
static unsigned captured;
void __wrap_battle_swirl_sequence(void){
 captured++;
 printf("ENCOUNTER [%u,%u,%u,%u,%u,%u,%u]\n",current,(uint16_t)ert.enemy_pathfinding_target_entity,
  (uint16_t)bt.touched_enemy,ow.enemy_has_been_touched,(uint16_t)bt.battle_initiative,
  ow.battle_swirl_countdown,(uint16_t)bt.current_battle_group);
 longjmp(done,1);
}
int main(int argc,char**argv){
 if(argc!=5)return 2;unsigned redux=atoi(argv[4]);char save[4096];snprintf(save,sizeof(save),"%s/private.srm",argv[2]);
 char*boot[]={"encounter-initiative-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,
  "--allow-redux-development","--headless","--frames","1","--inspect-shuffle","0"};
 if(eb_platform_main(12,boot)||maternalbound_enabled()!=(redux!=0))return 3;
 platform_max_frames=0;platform_input_init();
 const EnemyData*enemy=(const EnemyData*)ASSET_DATA(ASSET_DATA_ENEMY_CONFIGURATION_TABLE_BIN);
 if(!enemy||!enemy[1].event_script||ASSET_SIZE(ASSET_DATA_BTL_ENTRY_PTR_TABLE_BIN)<16)return 4;
 FILE*f=fopen(argv[3],"r");if(!f)return 5;
 unsigned leader,player,x,y,tx,ty,em,lf;
 while(fscanf(f,"%u %u %u %u %u %u %u %u %u",&current,&leader,&player,&x,&y,&tx,&ty,&em,&lf)==9){
  memset(&ow,0,sizeof(ow));memset(&bt,0,sizeof(bt));memset(&dr,0,sizeof(dr));
  game_state.camera_mode=1;game_state.walking_style=0;game_state.current_party_members=leader;game_state.leader_direction=lf;
  pb.camera_mode_3_frames_left=0;pb.camera_mode_backup=9;
  for(unsigned i=0;i<30;i++){entities.collided_objects[i]=-1;entities.tick_callback_hi[i]=0x1200+i;}
  entities.enemy_ids[0]=1;entities.script_table[0]=enemy[1].event_script;entities.npc_ids[0]=1;
  entities.abs_x[0]=x;entities.abs_y[0]=y;entities.moving_directions[0]=em;
  entities.abs_x[24]=x-5;entities.abs_y[24]=y+2;
  entities.abs_x[leader]=tx;entities.abs_y[leader]=ty;
  ert.current_entity_slot=0;ert.enemy_pathfinding_target_entity=7;bt.touched_enemy=-1;
  if(player)entities.collided_objects[23]=0;else entities.collided_objects[0]=leader;
  uint16_t pc=65535;int value=callroutine_dispatch(ROM_ADDR_HANDLE_ENEMY_CONTACT,0,0,0,&pc);
  if(value!=1||pc!=0||bt.touched_enemy!=0)return 6;
  unsigned old=captured;
  if(!setjmp(done))initiate_enemy_encounter();
  if(captured!=old+1)return 7;
 }
 fclose(f);return 0;
}
'''


def identify_init(a,out,original,redux,known):
    folder=out/'source-mapping'
    base=(folder/'movement_speeds.asm').read_text(encoding='utf-8').split('.SEGMENT "CODE"',1)[0]
    include=['--cpu','65816','-D','USA','-I',folder/'include-overlay','-I',a.native_source/'include','-I',a.native_source/'asm']
    relative='overworld/initiate_enemy_encounter.asm';externals=('CALCULATE_DIRECTION_FROM_POSITIONS','DIVISION16S_DIVISOR_POSITIVE','BTL_ENTRY_PTR_TABLE','BATTLE_SWIRL_SEQUENCE','FIND_PATH_TO_PARTY')
    def assemble(values,start,suffix):
        source=folder/('init_encounter'+suffix+'.asm');obj=source.with_suffix('.o');blob=source.with_suffix('.bin');lbl=source.with_suffix('.lbl')
        source.write_text(base+''.join(f'{k} := ${v:06X}\n' for k,v in values.items())+'.SEGMENT "CODE"\n.A16\n.I16\n.INCLUDE "'+relative+'"\n.EXPORT INIT_FRAME_SIZE\nINIT_FRAME_SIZE := @STACKSIZE\n',encoding='utf-8')
        cfg=source.with_suffix('.cfg');cfg.write_text((folder/'code.cfg').read_text(encoding='utf-8').replace('start=$C00000',f'start=${start:06X}'),encoding='utf-8')
        mapping.run([a.ca65,*include,source,'-o',obj,'-l',source.with_suffix('.lst')],source.with_suffix('.compile.log'))
        mapping.run([a.ld65,'-C',cfg,'-o',blob,'-Ln',lbl,obj],source.with_suffix('.link.log'))
        return blob,source.with_suffix('.lst'),lbl
    placeholder={k:0xC00000 for k in externals};first,_,_=assemble(placeholder,0xC00000,'-placeholder');data=first.read_bytes();relocs={};mask=set()
    for name in externals:
        positions=[]
        for byte in range(3):
            altered,_,_=assemble(dict(placeholder,**{name:0xC00000^(1<<(8*byte))}),0xC00000,f'-reloc-{name}-{byte}')
            offsets=[i for i,(x,y) in enumerate(zip(data,altered.read_bytes())) if x!=y]
            if not offsets:raise ValueError('Missing actual source external operand '+name)
            positions.append(offsets);mask.update(offsets)
        relocs[name]=positions
    for delta in (1,256):
        altered,_,_=assemble(placeholder,0xC00000+delta,'-base'+str(delta))
        if altered.stat().st_size!=len(data):raise ValueError('Original source function length changed')
        mask.update(i for i,(x,y) in enumerate(zip(data,altered.read_bytes())) if x!=y)
    pattern=b''.join(b'.' if i in mask else re.escape(bytes((v,))) for i,v in enumerate(data))
    candidates=list(re.finditer(pattern,original,re.S))
    if len(candidates)!=1:raise ValueError('Complete Original init body candidate not unique')
    pos=candidates[0].start();address=0xC00000+pos;modes={};proof=[]
    for mode,rom in (('original',original),('redux',redux)):
        actual=rom[pos:pos+len(data)];values={}
        for name,positions in relocs.items():
            b=[]
            for offsets in positions:
                unique={actual[i] for i in offsets}
                if len(unique)!=1:raise ValueError('Repeated source operands disagree: '+name)
                b.append(unique.pop())
            values[name]=int.from_bytes(bytes(b),'little')
        full,lst,lbl=assemble(values,address,'-'+mode+'-verified')
        if full.read_bytes()!=actual:raise ValueError('Full unmasked init body differs from original source in '+mode)
        if mode=='original' and mapping.find_unique(rom,actual,'INITIATE_ENEMY_ENCOUNTER')!=address:raise ValueError('Complete Original init body not unique')
        for symbol in ('CALCULATE_DIRECTION_FROM_POSITIONS','DIVISION16S_DIVISOR_POSITIVE'):
            if values[symbol]!=known[symbol]:raise ValueError('Actual initiative uses a different byte-proven helper')
        frame=mapping.labels(lbl)['INIT_FRAME_SIZE']
        modes[mode]=dict(Address=address,Dependencies=values,SourceFrameBytes=frame)
        proof.append(dict(Mode=mode,Symbol='INITIATE_ENEMY_ENCOUNTER',Address=f'{address:06X}',Source=relative,
                          FullUnmaskedByteEqualLength=len(actual),FullBodySha256=sha(full),FrameBytes=frame,
                          ActualObservationPoint='Entry to BATTLE_SWIRL_SEQUENCE, after initiative/countdown/group setup',
                          Dependencies={k:f'{v:06X}' for k,v in values.items()}))
    return modes,proof


def corpus():
    rows=[]
    boundaries=((2,-5),(-5,-2),(-2,5),(5,2),(-3,-7),(3,7),(-7,3),(7,-3))
    controls=((0,-8),(8,0),(0,8),(-8,0),(8,-8),(-8,-8),(8,8),(-8,8),(0,0))
    for leader in (24,25,26,27):
        for player in (0,1):
            for dx,dy in boundaries:
                for em,lf in ((1,2),):rows.append(('ordinary-source-sector-boundaries',leader,player,1024,1024,1024+dx,1024+dy,em,lf))
            for dx,dy in controls if leader in (26,27) and player==1 else ():
                for em,lf in ((0,0),(8,0)):
                    rows.append(('cardinal-diagonal-coincident-stationary-controls',leader,player,1024,1024,1024+dx,1024+dy,em,lf))
    return rows


def machine_single(a,out,mode,g,contact_functions,init,rows):
    out.mkdir();samples=out/'samples.jsonl';code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230');entry=0xC0FF00+len(code)
    code+=bytes((0x22,))+contact_functions['HANDLE_ENEMY_CONTACT']['address'].to_bytes(3,'little')
    code+=bytes.fromhex('8f00707e7b8f08707e3b8f0a707e');contact_done=0xC0FF00+len(code)
    code+=bytes((0x22,))+init['Address'].to_bytes(3,'little')+bytes((0x00,))
    at=lambda name:g[name]&65535;gs=at('GAME_STATE')
    zero=('BATTLE_MODE','BATTLE_MODE_FLAG','USING_DOOR','BATTLE_SWIRL_COUNTDOWN','ENEMY_HAS_BEEN_TOUCHED','PLAYER_MOVEMENT_FLAGS','PLAYER_INTANGIBILITY_FRAMES','CAMERA_MODE_3_FRAMES_LEFT','OVERWORLD_STATUS_SUPPRESSION')
    captures=[at(n) for n in ('ENEMY_PATHFINDING_TARGET_ENTITY','TOUCHED_ENEMY','ENEMY_HAS_BEEN_TOUCHED','BATTLE_INITIATIVE','BATTLE_SWIRL_COUNTDOWN','CURRENT_BATTLE_GROUP')]
    lua=['local output=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))',
         'local rows={'+','.join('{'+','.join(map(str,row[1:]))+'}' for row in rows)+'}',
         'local mem=emu.memType.snesWorkRam','local function w16(a,v) v=v%65536;emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256),mem) end',
         'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end',
         'local index=0;local contacts=0;local inits=0;local fine=0;local div=0;local lastfine=0;local lastdiv=0',
         'local cap={'+','.join(map(str,captures))+'}',
         'emu.addMemoryCallback(function() index=index+1;local r=assert(rows[index],"past corpus");local leader,player,x,y,tx,ty,em,lf=table.unpack(r);'+
         ''.join(f'w16({at(n)},0);' for n in zero)+f'w16({at("ENEMY_PATHFINDING_TARGET_ENTITY")},7);w16({at("TOUCHED_ENEMY")},65535);w16({at("CAMERA_MODE_BACKUP")},9);'+
         f'w16({gs+148},leader);w16({gs+142},0);w16({gs+176},1);w16({gs+138},lf);w16({at("CURRENT_ENTITY_SLOT")},0);'+
         f'for i=0,29 do w16({at("ENTITY_COLLIDED_OBJECTS")}+2*i,65535);w16({at("ENTITY_TICK_CALLBACK_HIGH")}+2*i,0x1200+i) end;'+
         f'w16({at("ENTITY_ENEMY_IDS")},1);w16({at("ENTITY_NPC_IDS")},1);w16({at("ENTITY_ABS_X_TABLE")},x);w16({at("ENTITY_ABS_Y_TABLE")},y);w16({at("ENTITY_MOVING_DIRECTIONS")},em);'+
         f'w16({at("ENTITY_ABS_X_TABLE")}+48,x-5);w16({at("ENTITY_ABS_Y_TABLE")}+48,y+2);w16({at("ENTITY_ABS_X_TABLE")}+leader*2,tx);w16({at("ENTITY_ABS_Y_TABLE")}+leader*2,ty);'+
         f'if player==1 then w16({at("ENTITY_COLLIDED_OBJECTS")}+46,0) else w16({at("ENTITY_COLLIDED_OBJECTS")},leader) end;w16(0x7200,0x55aa);lastfine=fine;lastdiv=div end,emu.callbackType.exec,{entry})',
         f'emu.addMemoryCallback(function() contacts=contacts+1 end,emu.callbackType.exec,{contact_functions["HANDLE_ENEMY_CONTACT"]["address"]})',
         f'emu.addMemoryCallback(function() inits=inits+1 end,emu.callbackType.exec,{init["Address"]})',
         f'emu.addMemoryCallback(function() fine=fine+1 end,emu.callbackType.exec,{init["Dependencies"]["CALCULATE_DIRECTION_FROM_POSITIONS"]})',
         f'emu.addMemoryCallback(function() div=div+1 end,emu.callbackType.exec,{init["Dependencies"]["DIVISION16S_DIVISOR_POSITIVE"]})',
         'emu.addMemoryCallback(function() assert(r16(0x7000)==1,"contact did not initiate");assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"contact frame corrupt");lastfine=fine;lastdiv=div end,emu.callbackType.exec,'+str(contact_done)+')',
         'emu.addMemoryCallback(function() local state=emu.getState();'+
         f'assert(state["cpu.d"]=={0x1000-init["SourceFrameBytes"]} and state["cpu.sp"]==0x1ff7,"original init frame corrupt");assert(r16(0x7200)==0x55aa,"protected RAM corrupt");'+
         'local expected=rows[index][7]==8 and 0 or 1;assert(fine-lastfine==expected and div-lastdiv==expected,"source stationary/helper flow differs "..index.." "..fine.." "..lastfine.." "..div.." "..lastdiv);'+
         'local result={index};for _,addr in ipairs(cap) do result[#result+1]=r16(addr) end;output:write("["..table.concat(result,",").."]\\n");'+
         'assert(index==1 and #rows==1 and contacts==1 and inits==1,"source integration calls differ");output:flush();output:close();emu.log("ENCOUNTER_PREFIX_COMPLETE "..index);emu.breakExecution() end,emu.callbackType.exec,'+str(init['Dependencies']['BATTLE_SWIRL_SEQUENCE'])+')']
    got,meta=contact.run_machine(a,out,mode,lua,code,rows,samples,'ENCOUNTER_PREFIX_COMPLETE '+str(len(rows)))
    meta.update(ObservationPoint='Actual BATTLE_SWIRL_SEQUENCE entry',ContactAndInitiateCallsEach=len(rows),OriginalRoutineBytesUnchanged=True,
                LaterSwirlAndBattleExecuted=False,StateResetMethod='One fresh oracle process per prepared contact; no save-state or CPU mutation during original execution',
                StateApiPrimaryDocumentation='https://github.com/SourMesen/Mesen2/blob/master/UI/Debugger/Documentation/LuaDocumentation.json')
    return got,meta


def machine(a,out,mode,g,contact_functions,init,rows):
    out.mkdir();values=[];evidence=[]
    for index,row in enumerate(rows):
        got,proof=machine_single(a,out/f'case-{index+1:04d}',mode,g,contact_functions,init,[row])
        if len(got)!=1 or got[0][0]!=1:raise ValueError('Single original prefix was incomplete')
        values.append([index+1]+got[0][1:]);evidence.append(proof)
    samples=out/'samples.jsonl';samples.write_text(''.join(json.dumps(row)+'\n' for row in values),encoding='utf-8')
    return values,dict(Calls=len(values),ContactAndInitiateCallsEach=len(rows),ActualUntouchedOriginalOrPinnedFullBodies=True,
                        AllCompleteOrderedPrefixes=True,AllFrameAndProtectedRamGuardsPassed=True,SamplesSha256=sha(samples),
                        ObservationPoint='Actual BATTLE_SWIRL_SEQUENCE entry',LaterSwirlAndBattleExecuted=False,
                        StateResetMethod='Fresh isolated oracle process per contact; original CPU execution is never redirected or patched',
                        PerCaseEvidence=evidence)


def native(a,out,mode,rows):
    out.mkdir();saved=direction.DRIVER
    try:direction.DRIVER=DRIVER;exe,built=direction.build_native(a,out)
    finally:direction.DRIVER=saved
    commands=json.loads((a.build/'compile_commands.json').read_text(encoding='utf-8'));entry=next(r for r in commands if r['file'].endswith('/port/unix/main.c'));compiler=Path(entry['command'].split()[0])
    ninja=(a.build/'build.ninja').read_text(encoding='utf-8');m=re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_Release (.*?)\n(.*?)(?=\n\n)',ninja,re.M|re.S)
    objects=m[1].split(' | ',1)[0].split();libs=re.search(r'^  LINK_LIBRARIES = (.*)$',m[2],re.M)[1].split();main=next(v for v in objects if v.replace('\\','/').endswith('/main.c.obj'))
    objects=[str(out/'platform-main.c.obj') if v==main else str(a.build/v) for v in objects]
    if a.corrected_entity_source:libs=[str(out/'corrected-private-libearthbound_game.a') if v.replace('\\','/').endswith('game_lib/libearthbound_game.a') else v for v in libs]
    command=[compiler,'-O3','-DNDEBUG',out/'party_driver.c.obj',*objects,'-o',exe,'-Wl,--wrap=battle_swirl_sequence','-Wl,--major-image-version,0,--minor-image-version,0',*libs]
    result=subprocess.run(list(map(str,command)),cwd=a.build,capture_output=True,timeout=30);(out/'link-swirl-observer.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise ValueError('Native swirl-entry observer link failed')
    built.update(ExecutableSha256=sha(exe),ReadOnlySwirlEntryObserver=True,LaterSwirlAndBattleExecuted=False,ActualProductionInitiateFunctionExecuted=True)
    cases=out/'cases.tsv';cases.write_text(''.join(f'{i+1} '+' '.join(map(str,row[1:]))+'\n' for i,row in enumerate(rows)),encoding='utf-8');session=out/'session';session.mkdir()
    assets=a.original_assets if mode=='original' else a.redux_assets
    result=subprocess.run([str(exe),str(assets.resolve()),str(session),str(cases),str(int(mode=='redux'))],capture_output=True,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),timeout=40)
    (out/'native.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise ValueError('Actual native encounter prefix failed: '+str(result.returncode)+' '+result.stderr.decode(errors='replace')[-1200:])
    got=[json.loads(line[10:]) for line in result.stdout.decode(errors='replace').splitlines() if line.startswith('ENCOUNTER ')]
    if [row[0] for row in got]!=list(range(1,len(rows)+1)):raise ValueError('Actual native prefixes incomplete/unordered')
    return got,built


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('rom','redux-rom','oracle','ca65','ld65','native-source','build','runtime','original-assets','redux-assets','scratch','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--corrected-entity-source',type=Path);p.add_argument('--pilot-count',type=int,default=0)
    a=p.parse_args();a.scratch=local_scratch(a.scratch);a.native_source=a.native_source.resolve();a.build=a.build.resolve();a.runtime=a.runtime.resolve()
    if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch/output required')
    original=a.rom.read_bytes();redux=a.redux_rom.read_bytes()
    if len(original)!=0x300000 or hashlib.sha1(original).hexdigest()!=US_SHA1:raise ValueError('Exact clean USA ROM required')
    if len(redux)!=0x600000 or hashlib.sha256(redux).hexdigest()!='c2a2fc98c7e6518b797959ffadf24ca4db8b4d7745ed3a9eb92eee106db1d0ab':raise ValueError('Exact pinned Redux ROM required')
    files=(a.rom,a.redux_rom,a.original_assets,a.redux_assets,a.runtime/'player.exe',a.runtime/'observer.exe',a.build/'game_lib/libearthbound_game.a',a.native_source/'src/entity/entity.c',a.native_source/'src/game/overworld_spawn.c',Path(__file__),Path(contact.__file__),Path(direction.__file__))
    inputs={str(path):sha(path) for path in files};a.scratch.mkdir(parents=True)
    ident=a.scratch/'contact-identification';ident.mkdir();g,contacts,contact_proof=contact.identify(a,ident,original,redux)
    angle=a.scratch/'direction-identification';angle.mkdir();known,direction_proof=direction.identify(a,angle,original,redux)
    inits,init_proof=identify_init(a,ident,original,redux,known);rows=corpus()
    if a.pilot_count:rows=rows[:a.pilot_count]
    modes=[]
    for mode in ('original','redux'):
        expected,proof=machine(a,a.scratch/('machine-'+mode),mode,g,contacts,inits[mode],rows)
        got,built=native(a,a.scratch/('native-'+mode),mode,rows)
        differences=[dict(Index=i+1,Input=list(rows[i][1:]),ActualCpuPrefix=s,ActualNativePrefix=n) for i,(s,n) in enumerate(zip(expected,got)) if s!=n]
        modes.append(dict(Mode=mode,Cases=len(rows),MismatchCount=len(differences),FirstMismatches=differences[:24],
                          InitiativeDistribution=dict(Counter(row[4] for row in expected)),TargetDistribution=dict(Counter(row[1] for row in expected)),
                          ActualCpuEvidence=proof,NativeEvidence=built))
    if {path:sha(Path(path)) for path in inputs}!=inputs:raise ValueError('Input/shared source changed during actual integration proof')
    report=dict(Schema='redux-actual-encounter-prefix-v1',EvidenceComplete=True,Passed=all(mode['MismatchCount']==0 for mode in modes),
                PilotOnly=bool(a.pilot_count),FullPlaythroughVerified=False,FullConversionVerified=False,Inputs=inputs,
                SourceProof=dict(Contact=contact_proof,Direction=direction_proof,Initiate=init_proof),Cases=len(rows),CaseGroups=dict(Counter(row[0] for row in rows)),Modes=modes,
                EntryPrerequisites='Prepared source contact flags and collided entity result; both player and enemy contact routes, Ness/Paula/Jeff/Poo active leader, pack-valid enemy/script and battle-group1. Positive nearby pixel positions and selected facing pairs around source sector boundaries.',
                ExecutedScope='Actual contact callback then actual initiate_enemy_encounter through first swirl entry, including actual CPU lookup/division, actual facing branches, countdown and group setup; no copied initiative formula.',
                Limitations=['Geometric collision producing the prepared collided-object result is excluded.',
                             'The swirl visual routine, subsequent pathfinding/marking and combat completion are excluded by the observation checkpoint.',
                             'No natural story route or owner movement blocker causal claim.'],
                SharedBuildEdited=False,OwnerSavesTouched=False,RunnerEditedSharedSource=False,ReproductionFlags={k:str(v) for k,v in vars(a).items()})
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(Output=str(a.output),Cases=len(rows),PilotOnly=bool(a.pilot_count),Modes=[dict(Mode=m['Mode'],MismatchCount=m['MismatchCount']) for m in modes])))


if __name__=='__main__':main()
