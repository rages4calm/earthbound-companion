# SPDX-License-Identifier: GPL-3.0-or-later
"""Focused native render/lifecycle fixtures using a cached Windows MinGW/Ninja build.

Requires your own compatible Original or pinned Redux assets.pak. Writes only a
new disposable output directory. Native source, build and owner data stay intact.
The fixture launcher copy permits Original; this does not change shipped guards.
"""
import argparse,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
def build(name,source,library=None):
 d=W/name;d.mkdir(exist_ok=True)
 commands=json.loads((B/'compile_commands.json').read_text(encoding='utf-8'))
 flags=next(c for c in commands if c['file'].replace('\\','/').endswith('/port/unix/main.c'))['command'].split()
 def run(args,label):
  p=subprocess.run(args,cwd=B,capture_output=True,timeout=90)
  (d/(label+'.log')).write_bytes(p.stdout+p.stderr)
  if p.returncode:raise RuntimeError(label+': '+p.stderr.decode(errors='replace')[-1800:])
 def compile(path,obj):
  f=flags.copy();f[f.index('-o')+1]=str(obj);f[f.index('-c')+1]=str(path);run(f,obj.stem)
 main=(N/'port/unix/main.c').read_text(encoding='utf-8').replace('if(!maternalbound_enabled() || !redux_development) {','if(!redux_development) {')
 (d/'main.c').write_text(main,encoding='utf-8');compile(d/'main.c',d/'main.obj')
 run([str(Path(flags[0]).parent/'objcopy.exe'),'--redefine-sym','main=eb_platform_main',str(d/'main.obj')],'rename-main')
 (d/'driver.c').write_text(source,encoding='utf-8');compile(d/'driver.c',d/'driver.obj')
 ninja=(B/'build.ninja').read_text(encoding='utf-8');m=re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_Release (.*?)\n(.*?)(?=\n\n)',ninja,re.M|re.S)
 objects=[str(d/'main.obj') if x.replace('\\','/').endswith('/main.c.obj') else str(B/x) for x in m[1].split(' | ',1)[0].split()]
 libs=re.search(r'^  LINK_LIBRARIES = (.*)$',m[2],re.M)[1].split()
 if library:libs=[str(library) if x=='game_lib/libearthbound_game.a' else x for x in libs]
 exe=d/'driver.exe';run([flags[0],str(d/'driver.obj'),*objects,'-o',str(exe),*libs],'link');shutil.copy2(B/'SDL2.dll',d/'SDL2.dll');return exe

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('native-source','build','assets','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();N=a.native_source.resolve();B=a.build.resolve();W=a.output.resolve()
 if os.name!='nt':raise SystemExit('This driver builder expects a Windows MinGW/Ninja cache.')
 if W.exists():raise SystemExit('Choose a new disposable output directory.')
 if not a.assets.is_file():raise SystemExit('Missing owner-supplied assets.pak.')
 W.mkdir(parents=True);source=Path(__file__).with_name('native_render_lifecycle_driver.c').read_text(encoding='utf-8')
 exe=build('driver',source);session=W/'session';session.mkdir()
 (session/'fixture.ini').write_text('companion=1\nvolume=0\nfast_forward_multiplier=16\n',encoding='utf-8')
 result=subprocess.run([str(exe),str(a.assets.resolve()),str(session)],env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=120)
 (W/'native.log').write_bytes(result.stdout+result.stderr)
 receipt={'passed':result.returncode==0,'output':result.stdout.decode(errors='replace'),'nativeExeSHA256':hashlib.sha256((B/'earthbound.exe').read_bytes()).hexdigest(),'driverSHA256':hashlib.sha256(source.encode()).hexdigest(),'ownerDataWritten':False,'fullPlaythroughVerified':False}
 (W/'results.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt));raise SystemExit(result.returncode)
