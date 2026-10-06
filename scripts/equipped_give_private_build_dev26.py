# SPDX-License-Identifier: GPL-3.0-or-later
"""Link the narrowly corrected inventory object into a copied frozen archive."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import battle_action_catalog_qa as helper

candidate_source = None


def private_build(a):
    build=a.build.resolve();out=a.scratch.resolve();native=a.native_source.resolve();candidate=Path(candidate_source).resolve()
    library=build/'game_lib/libearthbound_game.a';original_hash=helper.digest(library)
    if helper.digest(build/'earthbound.exe')!=helper.digest(a.runtime/'player.exe'):raise ValueError('Frozen player/build mismatch')
    commands=json.loads((build/'compile_commands.json').read_text());main_entry=next(r for r in commands if r['file'].endswith('/port/unix/main.c'))
    old_native=main_entry['file'].replace('\\','/').removesuffix('/port/unix/main.c');old_build=main_entry['directory'].replace('\\','/')
    def flags_for(entry):
        if '"'in entry['command']or "'"in entry['command']:raise ValueError('Review quoted compiler flags')
        flags=entry['command'].split()
        return [f.replace('\\','/').replace(old_native,native.as_posix()).replace(old_build,build.as_posix())for f in flags]
    flags=flags_for(main_entry);compiler=Path(flags[0]);ar=compiler.parent/'ar.exe'
    def run(cmd,name,cwd=build):
        r=subprocess.run(list(map(str,cmd)),cwd=cwd,capture_output=True,timeout=120);(out/name).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(name+': '+r.stderr.decode(errors='replace'))
        return r.stdout
    before_source=helper.digest(candidate);entry=next(r for r in commands if r['file'].endswith('/game/inventory.c'))
    cflags=flags_for(entry);obj=out/'inventory.c.obj';cflags[cflags.index('-c')+1]=str(candidate);cflags[cflags.index('-o')+1]=str(obj)
    run(cflags,'compile-private-inventory.log')
    copied=out/'private-inventory.a';shutil.copy2(library,copied);run([ar,'r',copied,obj],'replace-private-inventory.log')
    members=run([ar,'t',library],'original-members.log').decode().splitlines()
    if len(members)!=len(set(members)):raise ValueError('Duplicate archive member names require separate review')
    original_dir=out/'original-members';corrected_dir=out/'corrected-members';original_dir.mkdir();corrected_dir.mkdir()
    run([ar,'x',library],'extract-original-members.log',original_dir);run([ar,'x',copied],'extract-corrected-members.log',corrected_dir)
    orig={p.name:helper.digest(p)for p in original_dir.iterdir()if p.is_file()};changed={p.name:helper.digest(p)for p in corrected_dir.iterdir()if p.is_file()}
    if orig.keys()!=changed.keys()or sorted(orig)!=sorted(members):raise ValueError('Archive members changed')
    diffs=[name for name in orig if orig[name]!=changed[name]]
    if diffs!=['inventory.c.obj']:raise ValueError('Unexpected private archive changes: '+str(diffs))
    source=out/'battle_action_driver.c';source.write_text(helper.DRIVER,encoding='utf-8');driver_obj=out/'battle_action_driver.c.obj'
    flags[flags.index('-o')+1]=str(driver_obj);flags[flags.index('-c')+1]=str(source);run(flags,'compile-driver.log')
    match=re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_Release (.*?)\n(.*?)(?=\n\n)',(build/'build.ninja').read_text(),re.M|re.S)
    objects=match[1].split(' | ',1)[0].split();libs=re.search(r'^  LINK_LIBRARIES = (.*)$',match[2],re.M)[1].split()
    main=next(v for v in objects if v.replace('\\','/').endswith('/main.c.obj'));main_copy=out/'platform_main.c.obj';shutil.copy2(build/main,main_copy)
    run([compiler.parent/'objcopy.exe','--redefine-sym','main=eb_platform_main',main_copy],'rename-main.log')
    objects=[str(main_copy)if v==main else str(build/v)for v in objects]
    indices=[i for i,v in enumerate(libs)if v.replace('\\','/').endswith('game_lib/libearthbound_game.a')]
    if len(indices)!=1:raise ValueError('Unknown archive link layout')
    libs[indices[0]]=str(copied);exe=out/'battle-action-driver.exe'
    run([compiler,'-O3','-DNDEBUG',driver_obj,*objects,'-o',exe,'-Wl,--major-image-version,0,--minor-image-version,0',*libs],'link-driver.log')
    shutil.copy2(a.runtime/'SDL2.dll',out/'SDL2.dll')
    if helper.digest(library)!=original_hash or helper.digest(candidate)!=before_source:raise ValueError('Frozen input changed during build')
    return exe,dict(driverSourceSha256=helper.digest(source),executableSha256=helper.digest(exe),productionExecutableSha256=helper.digest(build/'earthbound.exe'),
                    productionLibrarySha256=original_hash,platformMainObjectSha256=helper.digest(build/main),sharedBuildModified=False,sharedSourceModified=False,
                    method='Private inventory.c object in copied frozen archive; all other archive members, platform objects and production routines unchanged.',
                    correctedInventory=dict(path=str(candidate),sha256=before_source,replacedMember='inventory.c.obj',originalObjectSha256=orig['inventory.c.obj'],
                                            correctedObjectSha256=changed['inventory.c.obj'],privateLibrarySha256=helper.digest(copied),
                                            archiveMemberCount=len(members),otherMembersByteIdentical=True),
                    includeSourceSnapshot=str(native),includeBuildSnapshot=str(build))
