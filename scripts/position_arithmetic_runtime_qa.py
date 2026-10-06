# SPDX-License-Identifier: GPL-3.0-or-later
"""Call frozen production movement code with independent original-machine data.

Only fresh private scratch files are modified. An existing local function's
symbol is made global in a COPIED production object/library; its compiled text
must remain byte-identical. There is no source rebuild or shared-build edit.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from check_jev_observer_parity import local_scratch
from snes_position_arithmetic_oracle import corpus
from snes_movement_helpers_oracle import sha


DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include "game_main.h"
#include "game/position_buffer.h"
#include "game/game_state.h"
#include "game/overworld.h"
#include "game/settings.h"
#include "game/maternalbound.h"
#include "core/memory.h"
extern int eb_platform_main(int argc,char**argv);
/* Only symbol visibility changes in a private object copy. The production
 * function's ABI and compiled instructions remain byte-identical. */
extern int32_t adjust_position(int16_t,uint16_t,int32_t,const int32_t*);
int main(int argc,char**argv){
 if(argc!=5)return 2;unsigned redux=atoi(argv[4]);char save[4096];snprintf(save,sizeof(save),"%s/private.srm",argv[2]);
 char *boot[]={"position-native-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,
  "--allow-redux-development","--headless","--frames","1",redux?"--redux-battle-fixture":"--inspect-shuffle","0"};
 unsigned n=sizeof(boot)/sizeof(boot[0]);if(!redux)n--;
 if(eb_platform_main(n,boot)!=0||maternalbound_enabled()!=(redux!=0))return 3;
 engine_sprint_speed=SPRINT_SPEED_OFF;velocity_store();
 printf("VELOCITY_NATIVE [");for(int axis=0;axis<2;axis++)for(int i=0;i<112;i++){if(axis||i)printf(",");printf("%u",(uint32_t)(axis?pb.v_speeds[i]:pb.h_speeds[i]));}puts("]");
 FILE*f=fopen(argv[3],"r");if(!f)return 4;unsigned index,kind,style,dir,surface,status,demo,pos,pad,pending;
 while(fscanf(f,"%u %u %u %u %u %u %u %u %u %u",&index,&kind,&style,&dir,&surface,&status,&demo,&pos,&pad,&pending)==10){
  game_state.walking_style=style;game_state.party_status=status;ow.demo_frames_left=demo;core.pad1_held=pad;ow.pending_interactions=pending;
  uint32_t value=kind==0?(uint16_t)map_input_to_direction(style):(uint32_t)adjust_position(dir,surface,(int32_t)pos,kind==1?pb.h_speeds:pb.v_speeds);
  printf("POSITION_NATIVE [%u,%u]\n",index,value);
 }fclose(f);return 0;
}
'''


def private_build(a):
    build=a.build.resolve();out=a.scratch;native=a.native_source.resolve()
    if sha(build/'earthbound.exe')!=sha(a.runtime/'player.exe'):
        raise ValueError('Frozen production build does not match supplied player runtime')
    commands=json.loads((build/'compile_commands.json').read_text(encoding='utf-8'))
    entry=next(row for row in commands if row['file'].endswith('/port/unix/main.c'))
    if '"' in entry['command'] or "'" in entry['command']:raise ValueError('Review quoted compiler arguments')
    flags=entry['command'].split();compiler=Path(flags[0]);toolchain=compiler.parent
    def run(command,name,working=build):
        result=subprocess.run(list(map(str,command)),cwd=working,capture_output=True,timeout=30)
        (out/name).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(name+': '+result.stderr.decode(errors='replace'))
        return result
    library=build/'game_lib/libearthbound_game.a';copiedlib=out/library.name
    originalhash=sha(library);shutil.copy2(library,copiedlib)
    member='position_buffer.c.obj';originalobj=out/member
    # Extract directly to a private file: Windows ar stdout may use text
    # mode, so piping a COFF member can alter linefeed bytes.
    run([toolchain/'ar.exe','x',library,member],'extract-object.log',out)
    textbefore=out/'adjust-text-before.bin';textafter=out/'adjust-text-after.bin'
    run([toolchain/'objcopy.exe','--dump-section','.text$adjust_position='+str(textbefore),originalobj],'text-before.log')
    if not textbefore.exists() or not textbefore.stat().st_size:raise ValueError('Existing production body not identified')
    run([toolchain/'objcopy.exe','--globalize-symbol','adjust_position',originalobj],'globalize-symbol.log')
    run([toolchain/'objcopy.exe','--dump-section','.text$adjust_position='+str(textafter),originalobj],'text-after.log')
    if textbefore.read_bytes()!=textafter.read_bytes():raise RuntimeError('Compiled production body changed')
    run([toolchain/'ar.exe','r',copiedlib,originalobj],'replace-private-member.log')
    source=out/'position-runtime-driver.c';source.write_text(DRIVER,encoding='utf-8');obj=out/'position-runtime-driver.c.obj'
    flags[flags.index('-o')+1]=str(obj);flags[flags.index('-c')+1]=str(source)
    run(flags,'compile-driver.log')
    ninja=(build/'build.ninja').read_text(encoding='utf-8')
    match=re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_Release (.*?)\n(.*?)(?=\n\n)',ninja,re.M|re.S)
    objects=match[1].split(' | ',1)[0].split()
    libraries=re.search(r'^  LINK_LIBRARIES = (.*)$',match[2],re.M)[1].split()
    main_object=next(token for token in objects if token.replace('\\','/').endswith('/main.c.obj'))
    copiedmain=out/'platform_main.c.obj';shutil.copy2(build/main_object,copiedmain)
    run([toolchain/'objcopy.exe','--redefine-sym','main=eb_platform_main',copiedmain],'rename-main.log')
    objects=[str(copiedmain) if token==main_object else str(build/token) for token in objects]
    indices=[i for i,v in enumerate(libraries) if v.replace('\\','/').endswith('game_lib/libearthbound_game.a')]
    if len(indices)!=1:raise ValueError('Unknown production library link layout')
    libraries[indices[0]]=str(copiedlib)
    exe=out/'position-native-driver.exe'
    run([compiler,'-O3','-DNDEBUG',obj,*objects,'-o',exe,'-Wl,--major-image-version,0,--minor-image-version,0',*libraries],'link-driver.log')
    shutil.copy2(a.runtime/'SDL2.dll',out/'SDL2.dll')
    if sha(library)!=originalhash:raise RuntimeError('Frozen library changed during preparation')
    return exe,{'productionExecutableSha256':sha(build/'earthbound.exe'),'productionLibrarySha256':originalhash,
                'PrivateSymbolVisibilityOnly':True,'ProductionAdjustTextByteIdentical':True,'ProductionAdjustTextSha256':sha(textbefore),
                'PrivateLibrarySha256':sha(copiedlib),'DriverSourceSha256':sha(source),'DriverExecutableSha256':sha(exe),
                'SharedBuildEdited':False,'SharedSourceEdited':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','runtime','native-source','original-assets','redux-assets','machine-review','machine-scratch','scratch','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--diagnostic',action='store_true')
    a=p.parse_args();a.scratch=local_scratch(a.scratch);evidence=local_scratch(a.machine_scratch)
    if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch and report required')
    machine=json.loads(a.machine_review.read_text(encoding='utf-8'))
    if machine.get('format')!='native-position-arithmetic-micro-oracle-v1' or not machine.get('Passed'):
        raise ValueError('Complete passing independent machine review required')
    samples=evidence/'original-machine/samples.jsonl';speeds=evidence/'original-machine/velocity.json'
    if sha(samples)!=machine['OriginalMachineEvidence']['SamplesSha256'] or sha(speeds)!=machine['OriginalMachineEvidence']['VelocitySampleSha256']:
        raise ValueError('Independent samples differ from completed review')
    reference=[json.loads(line) for line in samples.read_text(encoding='utf-8').splitlines()];velocity=json.loads(speeds.read_text(encoding='utf-8'));cases=corpus()
    if len(reference)!=len(cases) or [r[0] for r in reference]!=list(range(1,len(cases)+1)):
        raise ValueError('Complete ordered source corpus required')
    inputhashes={'originalAssets':sha(a.original_assets),'reduxAssets':sha(a.redux_assets)}
    a.scratch.mkdir(parents=True);exe,buildmeta=private_build(a);modes=[]
    environment=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    for mode,pack in (('original',a.original_assets),('redux',a.redux_assets)):
        # Original full corpus; Redux common arithmetic comparator excludes
        # its deliberately faster bicycle table. Neither asserts full Redux
        # running/Skip Sandwich source semantics; sprint is disabled here.
        indices=[i+1 for i,c in enumerate(cases) if mode=='original' or c['kind']=='input' or c['style']!=3]
        out=a.scratch/mode;out.mkdir();session=out/'session';session.mkdir();inputs=out/'cases.tsv';kinds={'input':0,'h':1,'v':2}
        inputs.write_text(''.join(' '.join(map(str,(i,kinds[cases[i-1]['kind']],cases[i-1]['style'],cases[i-1]['direction'],cases[i-1]['surface'],cases[i-1]['status'],cases[i-1]['demo'],cases[i-1]['position'],cases[i-1]['pad'],cases[i-1]['pending'])))+'\n' for i in indices),encoding='utf-8')
        result=subprocess.run([str(exe),str(pack.resolve()),str(session),str(inputs),'1' if mode=='redux' else '0'],cwd=session,env=environment,capture_output=True,timeout=30)
        log=out/'driver.log';log.write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(mode+': actual production driver failed '+str(result.returncode))
        lines=result.stdout.decode(errors='replace').splitlines()
        rows=[json.loads(v[len('POSITION_NATIVE '):]) for v in lines if v.startswith('POSITION_NATIVE ')]
        observed_velocity=[json.loads(v[len('VELOCITY_NATIVE '):]) for v in lines if v.startswith('VELOCITY_NATIVE ')]
        if [r[0] for r in rows]!=indices or len(observed_velocity)!=1 or len(observed_velocity[0])!=224:
            raise RuntimeError('Actual production corpus incomplete')
        differences=[{'case':cases[i-1],'index':i,'originalMachine':reference[i-1][1],'actualProduction':v} for i,v in rows if v!=reference[i-1][1]]
        checked=[i for i in range(224) if mode=='original' or (i%112)//8!=3]
        velocitydiff=[{'index':i,'originalMachine':velocity[i],'actualProduction':observed_velocity[0][i]} for i in checked if velocity[i]!=observed_velocity[0][i]]
        modes.append({'mode':mode,'ExecutedCases':len(indices),'NativeMismatchCount':len(differences),'NativeMismatches':differences,
                      'VelocityEntriesCompared':len(checked),'VelocityMismatchCount':len(velocitydiff),'VelocityMismatches':velocitydiff,
                      'DeliberateReduxBicycleArithmeticCasesExcluded':len(cases)-len(indices),'DriverLogSha256':sha(log)})
    if sha(a.build/'game_lib/libearthbound_game.a')!=buildmeta['productionLibrarySha256'] or sha(a.runtime/'player.exe')!=buildmeta['productionExecutableSha256']:
        raise RuntimeError('Frozen production input changed during run')
    if any(sha(path)!=inputhashes[key] for key,path in (('originalAssets',a.original_assets),('reduxAssets',a.redux_assets))):
        raise RuntimeError('Owner asset pack changed during run')
    report={'format':'native-position-arithmetic-production-review-v1','Passed':all(not row['NativeMismatchCount'] and not row['VelocityMismatchCount'] for row in modes),
            'ImmutableNativeBuild':buildmeta,'RuntimeSha256':{name:sha(a.runtime/name) for name in ('player.exe','observer.exe')},'Modes':modes,
            'IndependentOriginalMachineReview':{'path':a.machine_review.as_posix(),'sha256':sha(a.machine_review)},'InputIdentities':inputhashes,
            'OwnerSavesTouched':False,'SharedSourceEdited':False,'SharedBuildsEdited':False,'SprintDisabledInPreparedTests':True,
            'Runner':{'path':'tools/position_arithmetic_runtime_qa.py','sha256':sha(Path(__file__))},
            'FullPlaythroughVerified':False,'FullReduxMovementParityVerified':False,
            'Limits':['Private copied production object changes symbol visibility only; original adjust_position compiled text must remain identical. Actual production input/velocity code and game globals are linked unchanged.',
                      'Original mode compares every prepared source-machine context. Redux common arithmetic excludes intentional bicycle speeds; original-comparator skip tests verify the native adapter, not full pinned Redux running semantics.',
                      'Prepared direct helper inputs establish numerical behavior; collision traversal, follower timing, live sprint, controllers and legal story progress are separate tests. This runner does not invoke physical F6 or cold restoration.']}
    (a.scratch/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'Passed':report['Passed'],'Modes':[{k:r[k] for k in ('mode','ExecutedCases','NativeMismatchCount','VelocityEntriesCompared','VelocityMismatchCount')} for r in modes]}),flush=True)
    if not report['Passed'] and not a.diagnostic:raise SystemExit(1)


if __name__=='__main__':main()
