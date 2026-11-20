"""Private-asset regressions for spawn transitions, sprite binding and drop odds."""
import argparse,importlib.util,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ('native-source','build','original-assets','redux-assets','output'):p.add_argument('--'+n,type=Path,required=True)
p.add_argument('--before-overworld',type=Path)
p.add_argument('--before-battle-ui',type=Path)
a=p.parse_args();root=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('fixture',root/'check_native_render_lifecycle.py');f=importlib.util.module_from_spec(s);s.loader.exec_module(f)
f.N=a.native_source.resolve();f.B=a.build.resolve();f.W=a.output.resolve();f.W.mkdir(exist_ok=False,parents=True)
source=(root/'issues17_19_driver.c').read_text(encoding='utf-8');results=[]
for name in ('spawns','battle'):
    prefix='#define CHECK_SPAWNS\n' if name=='spawns' else '#include "'+(f.N/'src/game/battle.c').as_posix()+'"\n'
    if name=='spawns' and a.before_overworld:prefix+='#include "'+a.before_overworld.resolve().as_posix()+'"\n'
    if name=='battle' and a.before_battle_ui:prefix+='#include "'+a.before_battle_ui.resolve().as_posix()+'"\n'
    exe=f.build(name,prefix+source)
    for mode,pak in (('original',a.original_assets),('redux',a.redux_assets)):
        ss=f.W/(name+'-'+mode);ss.mkdir()
        r=subprocess.run([str(exe),str(pak.resolve()),str(ss)],capture_output=True,env=dict(os.environ,SDL_AUDIODRIVER='dummy',SDL_VIDEODRIVER='dummy'),timeout=90)
        (f.W/(name+'-'+mode+'.log')).write_bytes(r.stdout+r.stderr)
        result=dict(test=name,mode=mode,exitCode=r.returncode,output=r.stdout.decode(errors='replace')[-600:],error=r.stderr.decode(errors='replace')[-150:] if r.returncode else '')
        print(json.dumps(result),flush=True);results.append(result)
(f.W/'results.json').write_text(json.dumps(dict(checks=results,ownerDataWritten=False,fullPlaythroughVerified=False),indent=2)+'\n',encoding='utf-8')
raise SystemExit(0 if all(r['exitCode']==0 for r in results) else 1)
