# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only linkage using the matching immutable source and build includes."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import battle_action_catalog_qa as helper


def private_build(a):
    build=a.build.resolve();out=a.scratch.resolve();native=a.native_source.resolve()
    library=build/'game_lib/libearthbound_game.a';before=helper.digest(library)
    if helper.digest(build/'earthbound.exe')!=helper.digest(a.runtime/'player.exe'):
        raise ValueError('Frozen player/build mismatch')
    commands=json.loads((build/'compile_commands.json').read_text())
    entry=next(r for r in commands if r['file'].endswith('/port/unix/main.c'))
    old_native=entry['file'].replace('\\','/').removesuffix('/port/unix/main.c')
    old_build=entry['directory'].replace('\\','/')
    if '"'in entry['command']or "'"in entry['command']:raise ValueError('Review quoted flags')
    flags=[f.replace('\\','/').replace(old_native,native.as_posix()).replace(old_build,build.as_posix())for f in entry['command'].split()]
    compiler=Path(flags[0]);source=out/'equipment_driver.c';obj=out/'equipment_driver.c.obj'
    source.write_text(helper.DRIVER,encoding='utf-8')
    flags[flags.index('-o')+1]=str(obj);flags[flags.index('-c')+1]=str(source)
    def run(cmd,name):
        r=subprocess.run(list(map(str,cmd)),cwd=build,capture_output=True,timeout=120)
        (out/name).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(name+': '+r.stderr.decode(errors='replace'))
    run(flags,'compile-driver.log')
    match=re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_Release (.*?)\n(.*?)(?=\n\n)',(build/'build.ninja').read_text(),re.M|re.S)
    objects=match[1].split(' | ',1)[0].split();libs=re.search(r'^  LINK_LIBRARIES = (.*)$',match[2],re.M)[1].split()
    main=next(v for v in objects if v.replace('\\','/').endswith('/main.c.obj'));copied=out/'platform_main.c.obj'
    shutil.copy2(build/main,copied)
    run([compiler.parent/'objcopy.exe','--redefine-sym','main=eb_platform_main',copied],'rename-main.log')
    objects=[str(copied)if v==main else str(build/v)for v in objects];exe=out/'equipment-driver.exe'
    run([compiler,'-O3','-DNDEBUG',obj,*objects,'-o',exe,'-Wl,--major-image-version,0,--minor-image-version,0',*libs],'link-driver.log')
    shutil.copy2(a.runtime/'SDL2.dll',out/'SDL2.dll')
    if helper.digest(library)!=before:raise ValueError('Frozen library changed')
    return exe,dict(driverSourceSha256=helper.digest(source),executableSha256=helper.digest(exe),productionExecutableSha256=helper.digest(build/'earthbound.exe'),
                    productionLibrarySha256=before,platformMainObjectSha256=helper.digest(build/main),sharedBuildModified=False,sharedSourceModified=False,
                    method='Private driver linked to unchanged frozen player library/platform objects; copied main renamed only.',
                    includeSourceSnapshot=str(native),includeBuildSnapshot=str(build))
