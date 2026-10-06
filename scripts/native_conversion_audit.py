# SPDX-License-Identifier: GPL-3.0-or-later
"""Run the native subsystem audit against immutable local game packs.

Every requested case executes in a fresh scratch session. Missing inputs,
timeouts, missing result markers and diagnostic failures are failures, never
silent skips. This is a subsystem audit, not full-story/oracle equivalence.
"""
import argparse, hashlib, json, os, re, subprocess, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from check_jev_observer_parity import local_scratch

SHARED={
 'savestate':'save/cold-load/crash safety','keyitems':'key item storage/migration',
 'joinlevel':'party join level scaling','screen-transitions':'door fades/palettes',
 'encounters':'enemy contact/instant victories','playtest-rewards':'EXP/money rewards',
 'sfx-audio':'SPC effect delivery','bicycle-audio':'bicycle music lifecycle',
 'sprint-collision':'walking/sprint/cliff collision','stairs':'stair entry directions'}
REDUX={
 'redux-vm':'dialogue opcode dispatch','redux-ai':'enemy AI selectors',
 'redux-names':'expanded names/save migration','redux-motion':'running/stamina/sprite selection',
 'redux-audio':'SPC/MSU songs and Sound Stone transitions','redux-psi':'PSI configuration/animations',
 'redux-movement':'movement VM/teleport/bicycle/delivery',
 'redux-battle-sprites':'battle sprite renderer',
 'redux-combat':'battle calculations/actions/Tools/equipment/menu highlights',
 'redux-battle-art':'enemy art/backgrounds/PSI drawing'}
DIAGNOSTIC=re.compile(r'\b(?:FATAL|FAIL|unimplemented|unknown opcode|unknown bank)\b',re.I)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('player','observer','original-assets','redux-assets','msu-dir','scratch'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--workers',type=int,default=4,choices=range(1,9))
    a=p.parse_args();out=local_scratch(a.scratch)
    if out.exists():raise ValueError('Choose a fresh audit directory.')
    for path in (a.player,a.observer,a.original_assets,a.redux_assets):
        if not path.is_file():raise ValueError('Required immutable input missing: '+str(path))
    if not a.msu_dir.is_dir() or not list(a.msu_dir.glob('*.pcm')):raise ValueError('MSU input is required for this suite.')
    out.mkdir(parents=True)
    identities={key:hashlib.sha256(path.read_bytes()).hexdigest() for key,path in
                [('player',a.player),('observer',a.observer),('original',a.original_assets),('redux',a.redux_assets)]}
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    jobs=[(engine,exe,edition,pak,test,area) for engine,exe in [('player',a.player),('observer',a.observer)]
          for edition,pak in [('original',a.original_assets),('redux',a.redux_assets)]
          for test,area in {**SHARED,**(REDUX if edition=='redux' else {})}.items()]
    def execute(job):
        engine,exe,edition,pak,test,area=job;d=out/f'{engine}-{edition}-{test}';d.mkdir()
        cmd=[str(exe.resolve()),'--assets',str(pak.resolve()),'--session-dir',str(d),
             '--save',str(d/'fixture.srm'),'--allow-redux-development','--headless','--selftest-'+test]
        if test in ('sfx-audio','bicycle-audio','redux-audio'):
            cmd+=['--msu-dir',str(a.msu_dir.resolve()),'--msu-name','eb_msu1']
        started=time.monotonic();timeout=False
        try:
            proc=subprocess.run(cmd,cwd=d,env=env,capture_output=True,timeout=120)
            log=(proc.stdout+proc.stderr).decode(errors='replace');code=proc.returncode
        except subprocess.TimeoutExpired as error:
            log=((error.stdout or b'')+(error.stderr or b'')).decode(errors='replace');code=None;timeout=True
        (d/'native.log').write_text(log,encoding='utf-8')
        marker=bool(re.search(r'\bPASS\b',log));diagnostics=DIAGNOSTIC.findall(log)
        row={'engine':engine,'edition':edition,'test':test,'area':area,'exitCode':code,'timedOut':timeout,
             'resultMarkerSeen':marker,'diagnostics':diagnostics,'passed':code==0 and marker and not diagnostics,
             'seconds':round(time.monotonic()-started,3),'log':d.name+'/native.log'}
        print(d.name+': '+('PASS' if row['passed'] else 'FAIL'),flush=True);return row
    rows=[]
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for row in pool.map(execute,jobs):
            rows.append(row)
            (out/'partial-results.json').write_text(json.dumps(rows,indent=2)+'\n')
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    if identities!={key:sha(path) for key,path in
                     [('player',a.player),('observer',a.observer),('original',a.original_assets),('redux',a.redux_assets)]}:
        raise RuntimeError('An immutable audit input changed during the run.')
    report={'format':'native-subsystem-audit-v1','Passed':all(row['passed'] for row in rows),
            'RequestedCases':len(jobs),'ExecutedCases':len(rows),'SkippedCases':0,'Cases':rows,
            'EngineSha256':{key:identities[key] for key in ('player','observer')},
            'PackSha256':{key:identities[key] for key in ('original','redux')},
            'FullCompatibilityVerified':False,'FullPlaythroughVerified':False,'ReferenceEmulatorCompared':False,
            'Limits':['Prepared subsystem checks do not exercise every world/story branch.',
                      'Player/observer share game code; agreement is not an independent reference.',
                      'Renderer/audio checks do not establish visual parity or subjective listening quality.']}
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('Passed','RequestedCases','ExecutedCases','SkippedCases')}),flush=True)
    if not report['Passed']:raise SystemExit(1)

if __name__=='__main__':main()
