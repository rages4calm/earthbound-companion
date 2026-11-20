"""ROM-free check of native arguments emitted by both Companion launchers."""
import argparse,json,os,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--native',type=Path,required=True);p.add_argument('--output',type=Path)
a=p.parse_args();exe=a.native.resolve()
with tempfile.TemporaryDirectory(prefix='eb-launch-contract-') as directory:
    ss=Path(directory)
    args=[str(exe),'--session-dir',str(ss),'--assets',str(ss/'unused.pak'),'--log-file',str(ss/'game.log'),'--achievements-dir',str(ss/'Achievements'),'--achievement-shuffle','--no-achievements','--allow-redux-development','--load-state','--selftest-pc']
    r=subprocess.run(args,capture_output=True,env=dict(os.environ,SDL_AUDIODRIVER='dummy',SDL_VIDEODRIVER='dummy'),timeout=45)
    result=dict(passed=r.returncode==0,exitCode=r.returncode,output=(r.stdout+r.stderr).decode(errors='replace'),scope='Launcher arguments plus ROM-free input/audio selftests; no gameplay assets or owner saves')
    if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result));raise SystemExit(0 if result['passed'] else 1)
