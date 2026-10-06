# SPDX-License-Identifier: GPL-3.0-or-later
"""Source-backed production CC audio consumers against an immutable build.

The private driver reads existing packed command operands, calls the real
ScriptReader/CC dispatcher and links the frozen production library. A linker
wrapper records SFX requests and forwards every call unchanged. No scripts,
asset bytes, owner saves, production sources or shared builds are changed.
"""
import argparse,hashlib,json,os,re,shutil,struct,subprocess
from pathlib import Path
from build_maternalbound_pack import read_pack
from check_jev_observer_parity import local_scratch

PIN='897d00833f4a08a0a92f106abf631629a6a6a041'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()

DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "core/mode_stack.h"
#include "game/audio.h"
#include "game/display_text.h"
#include "game/display_text_internal.h"
#include "game/map_loader.h"
#include "game/maternalbound.h"
#include "game/overworld.h"
#include "platform/platform.h"
#include "data/assets.h"
extern int eb_platform_main(int argc,char **argv);
static unsigned tracking,sfx_count,sfx_last;
void __real_play_sfx(uint16_t id);
void __wrap_play_sfx(uint16_t id) {
    if(tracking){sfx_count++;sfx_last=id;}
    __real_play_sfx(id);
}
int main(int argc,char **argv) {
    if(argc!=5)return 2;
    char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
    char *boot[]={"audio-consumer-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,
        "--allow-redux-development","--headless","--frames","1","--redux-battle-fixture","0"};
    int count=sizeof(boot)/sizeof(boot[0]);
    if(atoi(argv[4])) {boot[count-2]="--inspect-shuffle";count--;}
    if(eb_platform_main(count,boot)!=0)return 3;
    game_set_fast_forward(true); /* callback is muted, deterministic manual sampling */
    /* Headless startup deliberately omits the host audio device. Bind the
     * actual SPC engine explicitly; otherwise music-state0 is a fixture
     * omission, unrelated to the production CC bookkeeping defect. */
    audio_init();
    const uint8_t *blob=ASSET_DATA(ASSET_DIALOGUE_DIALOGUE_BIN);
    size_t size=ASSET_SIZE(ASSET_DIALOGUE_DIALOGUE_BIN);
    FILE *input=fopen(argv[3],"r");if(!input)return 4;
    unsigned id,offset,length,argument,initial;
    while(fscanf(input,"%u %u %u %u %u",&id,&offset,&length,&argument,&initial)==5) {
        if(offset+length>size)return 5;
        change_music((uint16_t)initial);
        if(get_current_music()!=initial)return 6;
        ml.current_map_music_track=31;ml.next_map_music_track=32;
        set_argument_memory(argument);
        ScriptReader reader={TEXT_SRC_DIALOGUE,offset,offset+length,-1};
        ModeState child={0};GameMode mode=GAME_MODE_NONE;uint8_t resume=0;uint16_t aux=0;
        sfx_count=sfx_last=0;tracking=1;
        bool pushed=cc_1f_dispatch(&reader,&child,&mode,&resume,&aux);
        tracking=0;
        printf("QA_AUDIO {\"id\":%u,\"profileRedux\":%u,\"subcommand\":%u,\"readerConsumed\":%u,\"pushed\":%u,\"music\":%u,\"currentMapMusic\":%u,\"nextMapMusic\":%u,\"sfxCalls\":%u,\"lastSfx\":%u}\n",
            id,maternalbound_enabled(),blob[offset],reader.ptr_off-offset,pushed,
            get_current_music(),ml.current_map_music_track,ml.next_map_music_track,sfx_count,sfx_last);
    }
    fclose(input);audio_shutdown();return 0;
}
'''

def private_build(args):
    build=args.build.resolve();scratch=args.scratch.resolve()
    runtime_hashes={digest(args.runtime/name) for name in ('player.exe','observer.exe')}
    if digest(build/'earthbound.exe') not in runtime_hashes:raise ValueError('Build/runtime identity differs')
    source=scratch/'audio_consumer_driver.c';source.write_text(DRIVER,encoding='utf-8')
    commands=json.loads((build/'compile_commands.json').read_text())
    entry=next(row for row in commands if row['file'].endswith('/port/unix/main.c'))
    if '"' in entry['command'] or "'" in entry['command']:raise ValueError('Review quoted compiler flags')
    flags=entry['command'].split();obj=scratch/'audio_consumer_driver.c.obj'
    flags[flags.index('-o')+1]=str(obj);flags[flags.index('-c')+1]=str(source)
    def run(command,name):
        result=subprocess.run(command,cwd=build,capture_output=True,timeout=120)
        (scratch/name).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(name+': '+result.stderr.decode(errors='replace'))
    run(flags,'compile.log')
    ninja=(build/'build.ninja').read_text()
    match=re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_Release (.*?)\n(.*?)(?=\n\n)',ninja,re.M|re.S)
    objects=match[1].split(' | ',1)[0].split();libraries=re.search(r'^  LINK_LIBRARIES = (.*)$',match[2],re.M)[1].split()
    main=next(token for token in objects if token.replace('\\','/').endswith('/main.c.obj'))
    copied=scratch/'platform_main.c.obj';shutil.copy2(build/main,copied)
    run([str(Path(flags[0]).parent/'objcopy.exe'),'--redefine-sym','main=eb_platform_main',str(copied)],'rename.log')
    objects=[str(copied) if token==main else str(build/token) for token in objects]
    exe=scratch/'audio-consumer-driver.exe'
    run([flags[0],'-O3','-DNDEBUG',str(obj),*objects,'-o',str(exe),'-Wl,--wrap=play_sfx',
         '-Wl,--major-image-version,0,--minor-image-version,0',*libraries],'link.log')
    shutil.copy2(args.runtime/'SDL2.dll',scratch/'SDL2.dll')
    return exe,{'driverSourceSha256':digest(source),'executableSha256':digest(exe),
        'productionExecutableSha256':digest(build/'earthbound.exe'),
        'productionLibrarySha256':digest(build/'game_lib/libearthbound_game.a'),
        'platformMainObjectSha256':digest(build/main),'sharedBuildModified':False,'sharedSourceModified':False,
        'method':'Private driver linked to unchanged frozen production library and copied platform objects; SFX wrapper forwards unchanged.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','native-source','runtime','assets','original-assets','scratch','project','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--diagnostic',action='store_true')
    a=p.parse_args();a.scratch=local_scratch(a.scratch)
    if a.scratch.exists():raise ValueError('Fresh private scratch required')
    pin=subprocess.check_output(['git','-C',str(a.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=PIN:raise ValueError('Unreviewed source revision')
    a.scratch.mkdir(parents=True);exe,evidence=private_build(a)
    cases=[];fixtures=[]
    for profile,pack in (('Redux',a.assets),('Original',a.original_assets)):
        assets=read_pack(pack,a.native_source/'src/data/runtime_generated/asset_ids.h')[2]
        blob=assets['dialogue/dialogue.bin']
        def operand(pattern):
            offset=blob.find(pattern)
            if offset<0:raise ValueError(f'{profile}: required existing operand missing {pattern.hex()}')
            return offset+1,len(pattern)-1
        # These byte offsets select isolated real dispatcher operands, not a
        # claim that a raw pattern identifies a reachable story entry point.
        music_dyn=operand(bytes((31,0,0,0)));music_literal=operand(bytes((31,0,0,5)))
        sound_dyn=operand(bytes((31,2,0)));sound_literal=operand(bytes((31,2,12)))
        tests=[]
        def add(name,location,arg,initial,expected):
            tests.append({'name':name,'values':[len(tests),*location,arg,initial],'expected':expected})
        for track in (5,11,82,160,191):
            add(f'Music argument-memory {track}',music_dyn,track,82,
                {'music':track,'currentMapMusic':track,'nextMapMusic':track,'readerConsumed':3,'pushed':0})
        add('Music literal5',music_literal,99,82,
            {'music':5,'currentMapMusic':5,'nextMapMusic':5,'readerConsumed':3,'pushed':0})
        for sound in (0,5,12,120):
            add(f'Sound argument-memory {sound}',sound_dyn,sound,82,
                {'sfxCalls':1,'lastSfx':sound,'readerConsumed':2,'pushed':0})
        add('Sound literal12',sound_literal,99,82,
            {'sfxCalls':1,'lastSfx':12,'readerConsumed':2,'pushed':0})
        session=a.scratch/profile.lower();session.mkdir()
        inputs=session/'cases.tsv';inputs.write_text('\n'.join(' '.join(map(str,t['values'])) for t in tests)+'\n')
        result=subprocess.run([str(exe),str(pack.resolve()),str(session),str(inputs),str(int(profile=='Original'))],cwd=session,
            env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=120)
        (session/'runtime.log').write_bytes(result.stdout+result.stderr)
        rows={r['id']:r for r in (json.loads(line[9:]) for line in result.stdout.decode(errors='replace').splitlines() if line.startswith('QA_AUDIO '))}
        if result.returncode or len(rows)!=len(tests):raise RuntimeError(f'nativeExit={result.returncode}, rows={len(rows)} '+result.stderr.decode(errors='replace')[-2200:])
        for i,test in enumerate(tests):
            actual=rows[i];errors=[f'{key}: got {actual[key]} expected {value}' for key,value in test['expected'].items() if actual[key]!=value]
            cases.append({'profile':profile,'name':test['name'],'operandOffset':test['values'][1],
                'argumentMemory':test['values'][3],'expected':test['expected'],'actual':actual,'passed':not errors,'errors':errors})
        fixtures.append({'profile':profile,'packSha256':digest(pack),'existingOperandLocations':
            {'musicDynamic':music_dyn,'musicLiteral5':music_literal,'soundDynamic':sound_dyn,'soundLiteral12':sound_literal}})
    refs=['src/game/display_text_cc.c','src/game/display_text.c','src/game/audio.c','src/game/map_loader.c',
          'asm/text/ccs/play_music.asm','asm/text/ccs/play_sfx.asm','asm/battle/set_map_music.asm',
          'asm/audio/play_sound_and_update_meters.asm']
    report={'format':'redux-audio-consumer-qa-v1','sourceRevision':pin,'privateBuild':evidence,
      'runtimeSha256':{name:digest(a.runtime/name) for name in ('player.exe','observer.exe')},
      'sourceFiles':{path:digest(a.native_source/path) for path in refs},'fixtures':fixtures,'cases':cases,
      'sourceExpectations':[
          {'consumer':'CC_1F_00','native':'src/game/display_text_cc.c:cc_1f_dispatch case0x00',
           'source':'asm/text/ccs/play_music.asm -> asm/battle/set_map_music.asm',
           'semantics':'Resolve zero through argument memory, call CHANGE_MUSIC, then write CURRENT_MAP_MUSIC_TRACK and NEXT_MAP_MUSIC_TRACK in that order.'},
          {'consumer':'CC_1F_02','native':'src/game/display_text_cc.c:cc_1f_dispatch case0x02',
           'source':'asm/text/ccs/play_sfx.asm -> asm/audio/play_sound_and_update_meters.asm',
           'semantics':'Resolve a zero operand through argument memory before forwarding the sound request.',
           'unverified':'The source also updates HP/PP meters and renders; exact host-yield and meter/SFX timing parity is outside this argument-forwarding test.'}],
      'allPassed':all(x['passed'] for x in cases),'executedCases':len(cases),
      'passedCases':sum(x['passed'] for x in cases),'failedCases':sum(not x['passed'] for x in cases),'skippedCases':0,
      'executedAssertions':sum(len(x['expected']) for x in cases),
      'passedAssertions':sum(sum(x['actual'][key]==value for key,value in x['expected'].items()) for x in cases),
      'failedAssertions':sum(sum(x['actual'][key]!=value for key,value in x['expected'].items()) for x in cases),
      'diagnosticMode':a.diagnostic,'fixturePrerequisites':['Reviewed one-frame bootstrap binds immutable text assets.',
          'Explicit production audio_init binds the SPC engine omitted by headless host startup.'],
      'limits':['Isolated production CC consumers with existing packed operands; preceding story/event execution is not claimed.',
                'Audio commands execute in a private driver linked to the frozen production library; observer hashes identify the paired build, not a separate audio execution.',
                'SFX request argument forwarding is measured; audible quality and every story/music transition are not verified.',
                'Full source-level HP/PP meter/render and SFX scheduling parity remains unverified.',
                'Literal ka-ching12 passed; this audit does not establish the cause of the earlier shopping sound report.',
                'Raw byte-pattern fixture locations are not an inventory of reachable script calls.']}
    (a.scratch/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:report[key] for key in ('allPassed','executedCases','passedCases','failedCases','skippedCases')},indent=2))
    if not report['allPassed'] and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
