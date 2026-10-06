# SPDX-License-Identifier: GPL-3.0-or-later
"""Private immutable-library linker for the party-follow audit runners."""
import json
from pathlib import Path
import re
import shutil
import subprocess
from snes_movement_helpers_oracle import sha


def private_build(a,out,driver,wrap=False):
    build=a.build.resolve();native=a.native_source.resolve()
    if sha(build/'earthbound.exe')!=sha(a.runtime/'player.exe'):raise ValueError('Frozen build/runtime mismatch')
    library=build/'game_lib/libearthbound_game.a';originalhash=sha(library)
    commands=json.loads((build/'compile_commands.json').read_text(encoding='utf-8'))
    entry=next(r for r in commands if r['file'].endswith('/port/unix/main.c'))
    if '"' in entry['command'] or "'" in entry['command']:raise ValueError('Review quoted compile flags')
    flags=entry['command'].split();compiler=Path(flags[0]);source=out/'party_driver.c';source.write_text(driver,encoding='utf-8');obj=source.with_suffix('.c.obj')
    flags[flags.index('-o')+1]=str(obj);flags[flags.index('-c')+1]=str(source)
    def run(cmd,name,cwd=build):
        r=subprocess.run(list(map(str,cmd)),cwd=cwd,capture_output=True,timeout=30);(out/name).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(name+': '+r.stderr.decode(errors='replace'))
    replacement=None;copiedlib=None
    if getattr(a,'corrected_callback_source',None):
        corrected=a.corrected_callback_source.resolve()
        if corrected!=native/'src/entity/callbacks.c':raise ValueError('Only the reviewed actual callbacks.c source may be compiled')
        correctedhash=sha(corrected);centry=next(r for r in commands if r['file'].endswith('/entity/callbacks.c'))
        if '"' in centry['command'] or "'" in centry['command']:raise ValueError('Review quoted callback compiler flags')
        cflags=centry['command'].split();cobj=out/'callbacks.c.obj';cflags[cflags.index('-o')+1]=str(cobj)
        cflags[cflags.index('-c')+1]=str(corrected);run(cflags,'compile-callbacks.log')
        copiedlib=out/'libearthbound_game.a';shutil.copy2(library,copiedlib)
        run([compiler.parent/'ar.exe','r',copiedlib,cobj],'replace-private-callbacks.log')
        original_members=out/'original-members';corrected_members=out/'corrected-members';original_members.mkdir();corrected_members.mkdir()
        run([compiler.parent/'ar.exe','x',library],'extract-original-members.log',original_members)
        run([compiler.parent/'ar.exe','x',copiedlib],'extract-corrected-members.log',corrected_members)
        original_files={f.name:sha(f) for f in original_members.iterdir() if f.is_file()}
        corrected_files={f.name:sha(f) for f in corrected_members.iterdir() if f.is_file()}
        if original_files.keys()!=corrected_files.keys():raise RuntimeError('Private archive membership changed')
        differences=[name for name in original_files if original_files[name]!=corrected_files[name]]
        if differences!=['callbacks.c.obj']:raise RuntimeError('Unexpected private object changes: '+str(differences))
        if sha(corrected)!=correctedhash:raise RuntimeError('Callback source changed during private compilation')
        replacement=dict(ActualSourcePath=corrected.as_posix(),SourceSha256=correctedhash,
                         ReplacedMember='callbacks.c.obj',OriginalObjectSha256=original_files['callbacks.c.obj'],
                         CorrectedObjectSha256=corrected_files['callbacks.c.obj'],PrivateLibrarySha256=sha(copiedlib),
                         ArchiveMembersCompared=len(original_files),OtherArchiveMembersByteIdentical=True)
    run(flags,'compile-driver.log');ninja=(build/'build.ninja').read_text(encoding='utf-8')
    m=re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_Release (.*?)\n(.*?)(?=\n\n)',ninja,re.M|re.S)
    objects=m[1].split(' | ',1)[0].split();libs=re.search(r'^  LINK_LIBRARIES = (.*)$',m[2],re.M)[1].split()
    main=next(v for v in objects if v.replace('\\','/').endswith('/main.c.obj'));copied=out/'platform-main.c.obj';shutil.copy2(build/main,copied)
    run([compiler.parent/'objcopy.exe','--redefine-sym','main=eb_platform_main',copied],'rename-main.log')
    objects=[str(copied) if v==main else str(build/v) for v in objects]
    if copiedlib:
        at=[i for i,v in enumerate(libs) if v.replace('\\','/').endswith('game_lib/libearthbound_game.a')]
        if len(at)!=1:raise ValueError('Unknown game archive link layout')
        libs[at[0]]=str(copiedlib)
    exe=out/'party-driver.exe';wrapper=['-Wl,--wrap=call_move_callback'] if wrap else []
    run([compiler,'-O3','-DNDEBUG',obj,*objects,'-o',exe,*wrapper,'-Wl,--major-image-version,0,--minor-image-version,0',*libs],'link-driver.log')
    shutil.copy2(a.runtime/'SDL2.dll',out/'SDL2.dll')
    if sha(library)!=originalhash:raise RuntimeError('Frozen production library changed')
    return exe,dict(ExecutableSha256=sha(exe),DriverSourceSha256=sha(source),ProductionLibrarySha256=originalhash,
                    UntouchedProductionLibraryLinked=replacement is None,PrivateCorrectedCallbackReplacement=replacement,
                    ReadOnlyPrePostCallbackWrapper=wrap,SamePlatformMainAndGameLoop=True,
                    SharedSourceEditedByBuilder=False,SharedBuildEdited=False,
                    Builder=dict(path='tools/party_follow_private_build.py',sha256=sha(Path(__file__))))
