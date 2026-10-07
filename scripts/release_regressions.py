# SPDX-License-Identifier: GPL-3.0-or-later
"""Run bounded release regressions with explicit private assets and fresh outputs."""
import argparse,hashlib,json,os,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('native-source','build','runtime','original-assets','redux-assets','project','msu-dir','scratch'):
  p.add_argument('--'+key,type=Path,required=True)
 p.add_argument('--clean-player',type=Path)
 a=p.parse_args();a.scratch=a.scratch.resolve();a.scratch.mkdir(parents=True,exist_ok=False)
 here=Path(__file__).resolve().parent;reports=[]
 packs={'original':a.original_assets.resolve(),'redux':a.redux_assets.resolve()}
 env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
 shared=('savestate','keyitems','joinlevel','screen-transitions','encounters','playtest-rewards','sfx-audio','bicycle-audio','sprint-collision','stairs','pc')
 redux=('redux-vm','redux-ai','redux-names','redux-motion','redux-audio','redux-psi','redux-movement','redux-battle-sprites','redux-combat','redux-battle-art')
 engines={'shipping':a.build.resolve()/'earthbound.exe'}
 if a.clean_player:engines['clean-source']=a.clean_player.resolve()
 jobs=[(engine,exe,edition,pack,check)for engine,exe in engines.items()for edition,pack in packs.items()for check in shared+(redux if edition=='redux' else ())]
 def run_native(job):
  engine,exe,edition,pack,check=job;folder=a.scratch/f'{engine}-{edition}-{check}';folder.mkdir()
  cmd=[str(exe),'--assets',str(pack),'--session-dir',str(folder),'--save',str(folder/'fixture.srm'),'--headless','--allow-redux-development','--selftest-'+check]
  if check in ('sfx-audio','bicycle-audio','redux-audio'):cmd+=['--msu-dir',str(a.msu_dir.resolve()),'--msu-name','eb_msu1']
  r=subprocess.run(cmd,cwd=folder,env=env,capture_output=True,timeout=120);log=r.stdout+r.stderr;(folder/'native.log').write_bytes(log)
  if r.returncode or b'PASS' not in log:raise RuntimeError(str(folder)+': '+log.decode(errors='replace')[-1800:])
  return dict(engine=engine,edition=edition,check=check,passed=True)
 with ThreadPoolExecutor(max_workers=2)as pool:reports.extend(pool.map(run_native,jobs))
 for edition,pack in packs.items():
  tools=('psi_viewport_qa.py','credits_photo_frame_qa.py','presentation_qa_dev26.py','lumine_scroll_qa_dev26.py','giygas_sprite_binding_qa.py','redux_prayer_cinematic_qa.py')
  for tool in tools:
   label=edition+'-'+tool.removesuffix('.py');out=a.scratch/(label+'.json');folder=a.scratch/label
   cmd=[sys.executable,str(here/tool),'--native-source',str(a.native_source.resolve()),'--build',str(a.build.resolve()),'--runtime',str(a.runtime.resolve()),'--assets',str(pack),'--scratch',str(folder),'--output',str(out)]
   if tool in ('credits_photo_frame_qa.py','redux_prayer_cinematic_qa.py'):
    cmd+=['--project',str(a.project.resolve())]
    if edition=='original':cmd+=['--original-profile']
   if tool=='credits_photo_frame_qa.py':cmd+=['--all-photos']
   r=subprocess.run(cmd,env=env,capture_output=True,timeout=240);(a.scratch/(label+'.log')).write_bytes(r.stdout+r.stderr)
   if r.returncode or not out.exists():raise RuntimeError(label+': '+(r.stdout+r.stderr).decode(errors='replace')[-1800:])
   q=json.loads(out.read_text());passed=q.get('passed',q.get('allPassed',False))
   if not passed:raise RuntimeError(label+' report failed')
   reports.append(dict(edition=edition,check=tool,passed=True,report=out.name))
 identities={key:hashlib.sha256(exe.read_bytes()).hexdigest() for key,exe in engines.items()}
 result=dict(passed=True,checks=reports,engineExecutableSha256=identities,executedChecks=len(reports),ownerSavesTouched=False,limits=['Prepared/copy-based native checks, not exhaustive campaign parity. Original does not have the Redux extended equipment/resistance preview; its shared blank-canvas path is checked. Input tests use simulated sources and do not claim physical-controller gameplay.'])
 (a.scratch/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=True,executedChecks=len(reports))))
if __name__=='__main__':main()
