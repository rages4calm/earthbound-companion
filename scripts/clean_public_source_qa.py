# SPDX-License-Identifier: GPL-3.0-or-later
"""Compile the pinned native foundation plus the complete public patch in isolation."""
import argparse,hashlib,json,os,subprocess,tarfile
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('upstream','tamp','patch','gcc','ninja','windres','sdl','scratch'):
  p.add_argument('--'+key,type=Path,required=True)
 p.add_argument('--base',default='76eacab54b05766b82c98da9c55d94d1236ece03')
 p.add_argument('--tamp-pin',default='32034abf367d6bf2ee7a25cce8f64482cb955a65')
 a=p.parse_args();a.scratch=a.scratch.resolve();a.scratch.mkdir(parents=True,exist_ok=False)
 source=a.scratch/'source';source.mkdir();build=a.scratch/'build'
 sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
 for repo,pin,dest,label in ((a.upstream,a.base,source,'foundation'),(a.tamp,a.tamp_pin,source/'src/vendor/tamp','tamp')):
  dest.mkdir(parents=True,exist_ok=True);archive=a.scratch/(label+'.tar')
  with archive.open('wb') as out:subprocess.run(['git','-C',str(repo.resolve()),'archive',pin],stdout=out,check=True)
  with tarfile.open(archive) as t:t.extractall(dest,filter='data')
 patch=a.patch.resolve()
 for args in (['--check'],[]):subprocess.run(['git','apply',*args,str(patch)],cwd=source,check=True,capture_output=True)
 assert not (source/'src/assets/items/items.json').exists()
 assert not list(source.rglob('*.pak'))
 env=dict(os.environ,PATH=str(a.gcc.resolve().parent)+os.pathsep+os.environ['PATH'])
 options={'CMAKE_BUILD_TYPE':'Release','CMAKE_C_COMPILER':a.gcc.resolve().as_posix(),'CMAKE_MAKE_PROGRAM':a.ninja.resolve().as_posix(),'CMAKE_RC_COMPILER':a.windres.resolve().as_posix(),'CMAKE_EXPORT_COMPILE_COMMANDS':'ON','EB_RUNTIME_ASSETS':'ON','EB_ENABLE_AUDIO':'ON','EB_ENABLE_VERIFY':'OFF','EB_QA_OBSERVER':'OFF','EB_VIEWPORT_WIDTH':'512','EB_VIEWPORT_HEIGHT':'256','SDL2_DIR':str(a.sdl.resolve())}
 steps=[('configure',['cmake','-S',str(source/'port/unix'),'-B',str(build),'-G','Ninja',*[f'-D{k}={v}' for k,v in options.items()]]),('build',['cmake','--build',str(build),'-j','8'])]
 for label,command in steps:
  if label=='build':
   for f in build.glob('CMakeFiles/*/CMakeRCCompiler.cmake'):f.write_text(f.read_text().replace(chr(92),'/'))
  with (a.scratch/(label+'.log')).open('wb') as out:r=subprocess.run(command,env=env,stdout=out,stderr=subprocess.STDOUT)
  if r.returncode:raise RuntimeError(f'{label} failed; see {a.scratch/(label+".log")}')
 f=build/'compile_commands.json';f.write_text(f.read_text().replace(chr(92)+chr(92),'/'))
 report=dict(passed=True,foundation=a.base,tamp=a.tamp_pin,patchSha256=sha(patch),nativeExeSha256=sha(build/'earthbound.exe'),freshCompilation=True,romOrExtractedAssetsUsed=False,productionSaveFilesTouched=False,limits=['Local compiler, SDL and Git object stores are supplied explicitly. This verifies public source composition and compilation, not automatic toolchain installation or bit-identical path-dependent build metadata.'])
 (a.scratch/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
