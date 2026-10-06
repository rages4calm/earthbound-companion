# SPDX-License-Identifier: GPL-3.0-or-later
"""Build complete title candidates in new private player/observer directories."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from check_jev_observer_parity import local_scratch

ROOT = Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('source','builds','runtime','output'): ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args()
    for n,v in vars(a).items(): setattr(a,n,v.resolve())
    a.builds=local_scratch(a.builds); a.runtime=local_scratch(a.runtime)
    if a.builds.exists() or a.runtime.exists() or a.output.exists(): raise ValueError('Fresh private build/runtime/report required')
    a.builds.mkdir(); a.runtime.mkdir()
    cmake=ROOT/'native-source/.venv/Lib/site-packages/cmake/data/bin/cmake.exe'
    env=dict(os.environ,PATH=str(ROOT/'tools/mingw64/bin')+os.pathsep+os.environ['PATH'])
    def build(mode):
        directory=a.builds/mode
        commands=[['-S',str(a.source/'port/unix'),'-B',str(directory),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DCMAKE_C_COMPILER='+str(ROOT/'tools/mingw64/bin/gcc.exe'),'-DCMAKE_MAKE_PROGRAM='+str(ROOT/'tools/mingw64/bin/ninja.exe'),'-DSDL2_DIR='+str(ROOT/'tools/SDL2-2.32.10/x86_64-w64-mingw32/lib/cmake/SDL2'),'-DEB_RUNTIME_ASSETS=ON','-DEB_QA_OBSERVER='+('ON' if mode=='observer' else 'OFF')], ['--build',str(directory),'--target','earthbound','-j4']]
        for index,command in enumerate(commands):
            proc=subprocess.run([str(cmake),*command],env=env,capture_output=True,timeout=360)
            (a.builds/(mode+('-configure.log' if index==0 else '-build.log'))).write_bytes(proc.stdout+proc.stderr)
            if proc.returncode: raise RuntimeError(mode+' build failed; inspect private logs')
        shutil.copy2(directory/'earthbound.exe',a.runtime/(mode+'.exe'))
        return dict(mode=mode,commands=[[str(cmake),*r] for r in commands],executableSha256=sha(a.runtime/(mode+'.exe')),archiveSha256=sha(directory/'game_lib/libearthbound_game.a'),cmakeCacheSha256=sha(directory/'CMakeCache.txt'),compileCommandsSha256=sha(directory/'compile_commands.json'))
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(build,('player','observer')))
    shutil.copy2(ROOT/'_BuildScratch/audit-dev17-v4-runtime/SDL2.dll',a.runtime/'SDL2.dll')
    report=dict(format='private-complete-title-builds-dev18-v1',source=str(a.source),builds=str(a.builds),runtime=str(a.runtime),results=results,toolSha256=sha(Path(__file__)),rootBuildsModified=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)

if __name__=='__main__':main()
