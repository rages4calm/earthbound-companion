# SPDX-License-Identifier: GPL-3.0-or-later
"""Link frozen production trigonometry and the real static transition preparer.

Only a copied original object symbol's visibility is globalized. Its tested code
section is byte-identical; no production handler/data is recompiled or replaced.
Actual config entries and packs stay read only, with private boot/save paths.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from check_jev_observer_parity import local_scratch


DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "game/game_state.h"
#include "game/maternalbound.h"
#include "game/door.h"
#include "game/battle_bg.h"
#include "core/math.h"
#include "core/mode_stack.h"
#include "data/assets.h"
#include "snes/ppu.h"
extern int eb_platform_main(int,char**);
extern bool qa_prepare(uint8_t,uint8_t,ModeState*) __asm__("screen_transition_prepare.part.0");
int main(int argc,char**argv){
 if(argc!=5)return 2;char save[4096];snprintf(save,sizeof(save),"%s/private.srm",argv[2]);
 char*boot[]={"transition-production-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
 if(eb_platform_main(12,boot)||maternalbound_enabled()!=(atoi(argv[3])!=0))return 3;
 FILE*f=fopen(argv[4],"r");if(!f)return 4;unsigned speed,d,x,y,index=0;
 while(fscanf(f,"%u %u %u %u",&speed,&d,&x,&y)==4){
  uint8_t angle=(uint8_t)(d+128);int16_t sx=cosine_sine((int16_t)speed,angle),sy=cosine_func((int16_t)speed,angle);
  printf("TRIG [%u,%u,%u]\n",++index,(uint32_t)((int32_t)sx*256),(uint32_t)((int32_t)sy*256));
 }fclose(f);
 const ScreenTransitionConfig*cfg=(const ScreenTransitionConfig*)ASSET_DATA(ASSET_MAPS_SCREEN_TRANSITION_CONFIG_BIN);
 if(ASSET_SIZE(ASSET_MAPS_SCREEN_TRANSITION_CONFIG_BIN)!=34*12)return 5;
 const uint16_t pos[][2]={{0,0},{1,65535},{32767,32768},{32768,32767},{65535,1}};
 for(unsigned id=0;id<34;id++)for(unsigned mode=0;mode<2;mode++)for(unsigned p=0;p<5;p++){
  ModeState state={0};ppu.bg_hofs[0]=pos[p][0];ppu.bg_vofs[0]=pos[p][1];bool ok=qa_prepare(id,mode,&state);
  printf("PREPARE [%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u]\n",id,mode,p,cfg[id].scroll_speed,(unsigned)cfg[id].direction*4,pos[p][0],pos[p][1],(uint32_t)dr.transition_x_velocity,(uint32_t)dr.transition_y_velocity,(uint32_t)dr.transition_x_accum,(uint32_t)dr.transition_y_accum);
  if(!ok)return 6;
 }
 printf("TABLE [");for(unsigned i=0;i<256;i++)printf("%s%u",i?",":"",(uint8_t)sine_table[i]);puts("]");
 return 0;
}
'''


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def linked(a,out):
    build=a.build;library=build/'game_lib/libearthbound_game.a';before=sha(library)
    if sha(build/'earthbound.exe')!=sha(a.runtime/'player.exe'):raise ValueError('Frozen runtime/build identity mismatch')
    commands=json.loads((build/'compile_commands.json').read_text(encoding='utf-8'));entry=next(r for r in commands if r['file'].endswith('/port/unix/main.c'))
    if '"'in entry['command']or "'"in entry['command']:raise ValueError('Review quoted compiler flags')
    flags=entry['command'].split();compiler=Path(flags[0]);bin=compiler.parent
    def run(argv,name):
        proc=subprocess.run(list(map(str,argv)),cwd=build,capture_output=True,timeout=30);(out/name).write_bytes(proc.stdout+proc.stderr)
        if proc.returncode:raise ValueError(name+': '+proc.stderr.decode(errors='replace'))
        return proc.stdout
    members=run([bin/'ar.exe','t',library],'members.log').decode().splitlines()
    if members.count('door.c.obj')!=1:raise ValueError('Production door object is not unique')
    # Direct extraction avoids the Windows stdout text translation of ar p.
    extract=subprocess.run([str(bin/'ar.exe'),'x',str(library),'door.c.obj'],cwd=out,capture_output=True,timeout=30)
    (out/'extract-door.log').write_bytes(extract.stdout+extract.stderr)
    if extract.returncode:raise ValueError('Direct production member extraction failed')
    obj=out/'door-visibility.c.obj';(out/'door.c.obj').rename(obj)
    orig=out/'door-original.c.obj';shutil.copy2(obj,orig)
    section='.text$screen_transition_prepare.part.0';rawbefore=out/'prepare-before.bin';rawafter=out/'prepare-after.bin'
    run([bin/'objcopy.exe','--dump-section',section+'='+str(rawbefore),orig],'dump-before.log')
    run([bin/'objcopy.exe','--globalize-symbol','screen_transition_prepare.part.0',obj],'globalize.log')
    run([bin/'objcopy.exe','--dump-section',section+'='+str(rawafter),obj],'dump-after.log')
    if rawbefore.read_bytes()!=rawafter.read_bytes():raise ValueError('Tested production instructions changed')
    dis=run([bin/'objdump.exe','-dr','--disassemble=screen_transition_prepare.part.0',orig],'prepare-abi.log').decode()
    if not all(s in dis for s in ('movzbl %cl,%ecx','mov    %edx,%esi','mov    %r8,%rbx')):raise ValueError('Review changed compiler-split Win64 source ABI')
    source=out/'driver.c';source.write_text(DRIVER,encoding='utf-8');driverobj=source.with_suffix('.c.obj')
    flags[flags.index('-c')+1]=str(source);flags[flags.index('-o')+1]=str(driverobj);run(flags,'compile.log')
    ninja=(build/'build.ninja').read_text(encoding='utf-8');m=re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_Release (.*?)\n(.*?)(?=\n\n)',ninja,re.M|re.S)
    objects=m[1].split(' | ',1)[0].split();libraries=re.search(r'^  LINK_LIBRARIES = (.*)$',m[2],re.M)[1].split()
    main=next(v for v in objects if v.replace('\\','/').endswith('/main.c.obj'));copied=out/'main-renamed.c.obj';shutil.copy2(build/main,copied)
    run([bin/'objcopy.exe','--redefine-sym','main=eb_platform_main',copied],'rename-main.log')
    objects=[str(copied)if v==main else str(build/v)for v in objects];exe=out/'production.exe'
    run([compiler,'-O3','-DNDEBUG',driverobj,obj,*objects,'-o',exe,'-Wl,--major-image-version,0,--minor-image-version,0',*libraries],'link.log')
    shutil.copy2(a.runtime/'SDL2.dll',out/'SDL2.dll')
    if sha(library)!=before:raise ValueError('Production archive changed')
    return exe,dict(unchangedProductionLibrarySha256=before,originalDoorObjectSha256=sha(orig),visibilityOnlyDoorObjectSha256=sha(obj),testedPrepareCodeSectionSha256=sha(rawbefore),testedPrepareCodeSectionBytes=len(rawbefore.read_bytes()),testedPrepareInstructionsUnchanged=True,productionHandlersRecompiled=False,productionDataPatched=False,privateDriverSha256=sha(source),privateExeSha256=sha(exe),staticPreparerAbi='compiler-split part.0 Win64 RCX=transition byte, RDX=mode byte, R8=ModeState pointer, verified actual disassembly against source call-site contract')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('build','runtime','original-assets','redux-assets','cpu','scratch','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    for n,v in vars(a).items():setattr(a,n,v.resolve())
    a.scratch=local_scratch(a.scratch)
    if a.scratch.exists()or a.output.exists():raise ValueError('Fresh scratch/report required')
    reference=json.loads(a.cpu.read_text(encoding='utf-8'))
    if not reference['allCurrentPassed']:raise ValueError('Source CPU final-green reference required')
    a.scratch.mkdir(parents=True);out=a.scratch/'link';out.mkdir();exe,link=linked(a,out)
    results=[]
    for cpu,pack in zip(reference['profiles'],(a.original_assets,a.redux_assets)):
        mode=cpu['profile'];folder=a.scratch/mode;folder.mkdir();cases=cpu['cpu']['cases'];inputfile=folder/'cases.txt'
        inputfile.write_text('\n'.join(' '.join(str(c[n])for n in ('speed','direction','x','y'))for c in cases)+'\n',encoding='utf-8')
        env=dict(os.environ,SDL_AUDIODRIVER='dummy',SDL_VIDEODRIVER='dummy')
        proc=subprocess.run([str(exe),str(pack),str(folder),str(int(mode=='redux')),str(inputfile)],cwd=out,env=env,capture_output=True,timeout=60)
        log=folder/'native.log';log.write_bytes(proc.stdout+proc.stderr)
        if proc.returncode:raise ValueError(mode+' production test failed; inspect private log')
        records={k:[]for k in ('TRIG','PREPARE','TABLE')}
        for line in proc.stdout.decode(errors='replace').splitlines():
            k,_,v=line.partition(' ')
            if k in records:records[k].append(json.loads(v))
        if len(records['TRIG'])!=len(cases)or len(records['PREPARE'])!=340 or len(records['TABLE'])!=1:raise ValueError('Production corpus incomplete')
        tm=[i for i,(a,b)in enumerate(zip(records['TRIG'],cpu['cpu']['results']),1)if a[1:]!=b[1:3]]
        bykey={(c['speed'],c['direction']%256,c['x'],c['y']):r[1:]for c,r in zip(cases,cpu['cpu']['results'])}
        pm=[]
        for index,row in enumerate(records['PREPARE'],1):
            key=(row[3],row[4]%256,row[5],row[6])
            if key not in bykey or row[7:]!=bykey[key]:pm.append(dict(index=index,actual=row,expected=bykey.get(key)))
        tablehash=hashlib.sha256(bytes(records['TABLE'][0])).hexdigest();actualtable=next(e['sha256']for e in reference['sourceMapping']if e['symbol']=='SINE_LOOKUP_TABLE')
        results.append(dict(profile=mode,assetsSha256=sha(pack),productionTrigonometryCases=len(cases),trigMismatchIndices=tm,actualPackedPrepareCases=340,prepareMismatches=pm,productionSineTableSha256=tablehash,sourceTableMatches=tablehash==actualtable,records=records,nativeLogSha256=sha(log)))
    report=dict(format='frozen-transition-scroll-production-v1',toolSha256=sha(Path(__file__)),actualCpuReference=dict(path=str(a.cpu),sha256=sha(a.cpu)),productionLink=link,runtimeSha256={n:sha(a.runtime/n)for n in ('player.exe','observer.exe')},profiles=results,allPassed=all(not r['trigMismatchIndices']and not r['prepareMismatches']and r['sourceTableMatches']for r in results),ownerSavesBuildOrInputPacksModified=False,limits=['4616 cases/profile directly call actual production COSINE helpers/table; arbitrary synthetic angles/signed speeds are helper API controls, not all real parent-config paths.', '340 cases/profile call unchanged code of the real frozen compiler-split screen_transition_prepare through private symbol visibility only; actual34packed configurations, two modes and5BG positions. Outer type-boundary guard, subsequent frames/palette rendering/audio delivery/map streaming are outside this preparer observation.', 'The CPU reference fully executes untouched Original/pinned INIT. Update arithmetic remains source-prefix/body evidence in that report, not an actual production map-streaming comparison here.'])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([(r['profile'],len(r['trigMismatchIndices']),len(r['prepareMismatches']),r['sourceTableMatches'])for r in results]))


if __name__=='__main__':main()
