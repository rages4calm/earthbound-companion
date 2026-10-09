# SPDX-License-Identifier: GPL-3.0-or-later
"""Build platform-local private-ROM conversion helpers from pinned tools."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

def run(*args, cwd=None):
    subprocess.run(args, check=True, cwd=cwd)

def clone(url, revision, target):
    if target.exists(): raise ValueError('Use a fresh helper tool directory')
    run('git','clone','--no-checkout',url,str(target))
    run('git','-C',str(target),'checkout','--detach',revision)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    repo=Path(__file__).resolve().parents[1]
    work=args.work.resolve();work.mkdir(parents=True,exist_ok=True)
    cs=work/'CoilSnake';ccc=work/'CCScript';writer=work/'CCScriptWriter'
    clone('https://github.com/pk-hack/CoilSnake.git','346cfc753644bc3703b6fc4eaa0a5d6bdcb9bb4a',cs)
    clone('https://github.com/charasyn/ccscript_legacy.git','cecd6a44baf88f3e6de86938b4052502b4c53366',ccc)
    clone('https://github.com/pk-hack/CCScriptWriter.git','f7e290a68f99511b96dbc704eda6b21edc161faa',writer)
    run('git','-C',str(ccc),'apply','--check',str(repo/'patches/ccscript-cxx17.patch'))
    run('git','-C',str(ccc),'apply',str(repo/'patches/ccscript-cxx17.patch'))
    run(sys.executable,'-m','pip','install','setuptools','setuptools-scm','Pillow','PyYAML','pyinstaller')
    run(sys.executable,'-m','pip','install','--no-deps',str(ccc),str(writer),str(cs))
    run(sys.executable,'-m','pip','install',str(repo/'native-source'))
    run('pyinstaller','--noconfirm',str(repo/'scripts/redux_setup.spec'),cwd=repo)
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    suffix='.exe' if sys.platform=='win32' else ''
    shutil.copy2(repo/'dist'/('redux-setup'+suffix),output/('redux-setup'+suffix))
    run(str(output/('redux-setup'+suffix)),'--help')
    notices=output/'Licenses';notices.mkdir(exist_ok=True)
    for name,tool in [('CoilSnake',cs),('CCScript',ccc),('CCScriptWriter',writer)]:
        found=False
        for file in tool.iterdir():
            if file.is_file() and file.name.lower().startswith(('license','copying')):
                shutil.copy2(file,notices/(name+'-'+file.name));found=True
        if not found: raise ValueError('Missing tool license: '+name)
    shutil.copy2(cs/'coilsnake/util/eb/exhal/COPYING.txt',notices/'Exhal-COPYING.txt')

if __name__=='__main__':main()
