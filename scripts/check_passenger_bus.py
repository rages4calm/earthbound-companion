"""Focused passenger bus selection checks using private assets and a cached Windows build.

No owner saves or installed files are opened. Requires an unused output folder.
"""
import argparse, importlib.util, json, os, subprocess
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('native-source','build','assets','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--entity-source',type=Path,help='Optional pre-fix source for negative control')
    a=parser.parse_args()
    if a.output.exists(): raise ValueError('Choose a fresh output directory')
    a.output.mkdir(parents=True)
    spec=importlib.util.spec_from_file_location('fixture',Path(__file__).with_name('check_native_render_lifecycle.py'))
    f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
    f.N=a.native_source.resolve();f.B=a.build.resolve();f.W=a.output.resolve()
    source=Path(__file__).with_name('passenger_bus_driver.c').read_text(encoding='utf-8')
    if a.entity_source: source+='\n#include "'+a.entity_source.resolve().as_posix()+'"\n'
    exe=f.build('driver',source);session=f.W/'session';session.mkdir()
    r=subprocess.run([str(exe),str(a.assets.resolve()),str(session)],capture_output=True,
        env=dict(os.environ,SDL_AUDIODRIVER='dummy',SDL_VIDEODRIVER='dummy'),timeout=90)
    (f.W/'native.log').write_bytes(r.stdout+r.stderr)
    receipt={'passed':r.returncode==0,'exitCode':r.returncode,'output':r.stdout.decode(errors='replace'),
        'fullPlaythroughVerified':False,'ownerDataWritten':False,
        'scope':'Real bus actor selection, boarding coordinate callroutine and post-fare movement/camera script on isolated actors; not a full bus journey'}
    (f.W/'result.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt));raise SystemExit(r.returncode)

if __name__=='__main__':main()
