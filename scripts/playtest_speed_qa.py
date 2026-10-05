# SPDX-License-Identifier: MIT
"""Check amplified rewards and timed playback using isolated save copies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'native-source/src/vendor/tamp'))
import tamp
from check_jev_observer_parity import sections, latest, canonical_pointer, pointer_layout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('production', 'observer', 'previous', 'original-assets', 'redux-assets', 'owner-saves', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if not output.is_relative_to(root / '_BuildScratch') or output.exists():
        raise ValueError('Use a fresh isolated output below _BuildScratch.')
    output.mkdir(parents=True)
    env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
    env['PATH'] = str(root / 'tools/SDL2-2.32.10/x86_64-w64-mingw32/bin') + ';' + str(root / 'tools/mingw64/bin') + ';' + env['PATH']
    rows = []
    def run(exe, pack, folder, extra):
        start = time.perf_counter()
        result = subprocess.run([str(exe.resolve()), '--assets', str(pack.resolve()), '--session-dir', str(folder),
                                 '--save', str(folder / 'fixture.srm'), '--config', str(folder / 'fixture.ini'),
                                 '--allow-redux-development', *extra], env=env, capture_output=True, timeout=30)
        elapsed = time.perf_counter() - start
        text = (result.stdout + result.stderr).decode(errors='replace')
        (folder / 'native.log').write_text(text, encoding='utf-8')
        if result.returncode:
            raise RuntimeError(f'{folder.name}: exit {result.returncode}: {text[-1000:]}')
        return elapsed, text
    for edition in ('original', 'redux'):
        pack = getattr(args, edition + '_assets')
        folder = output / (edition + '-rewards');folder.mkdir()
        (folder / 'fixture.ini').write_text('exp_multiplier=16\nmoney_multiplier=16\nfast_forward_multiplier=16\n')
        _, text = run(args.production, pack, folder, ['--headless', '--selftest-playtest-rewards'])
        if '128 normal/instant victory' not in text or 'overflow guards PASS' not in text:
            raise RuntimeError('Reward fixture did not finish.')
        rows.append({'case': folder.name, 'victoryAndPartySplitCases': 128, 'passed': True})
    for label, config, expected in (
        ('default', '', 'experience=1x money=1x fast-forward=3x'),
        ('high', 'exp_multiplier=16\nmoney_multiplier=16\nfast_forward_multiplier=8\n', 'experience=16x money=16x fast-forward=8x'),
        ('invalid', 'exp_multiplier=17\nmoney_multiplier=-1\nfast_forward_multiplier=0\n', 'experience=1x money=1x fast-forward=3x'),
    ):
        folder=output/('config-'+label);folder.mkdir()
        (folder/'fixture.ini').write_text(config)
        _, text=run(args.production,args.original_assets,folder,['--headless','--frames','2'])
        if expected not in text: raise RuntimeError('Native parser settings differ: '+text[-1000:])
        rows.append({'case':folder.name,'passed':True})
    pointers=pointer_layout(root/'native-source',root/'tools/mingw64/bin/gcc.exe',output)
    owner_before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.owner_saves.iterdir() if p.is_file()}
    baseline=None
    for label, exe, multiplier, enabled in (
        ('previous-normal',args.previous,3,False),
        ('updated-normal',args.production,3,False),
        ('turbo-3',args.production,3,True),
        ('turbo-8',args.production,8,True),
        ('turbo-16',args.production,16,True),
    ):
        folder=output/label;folder.mkdir()
        shutil.copytree(args.owner_saves,folder/'saves')
        (folder/'fixture.ini').write_text(f'width=640\nheight=480\nvolume=0\nexp_multiplier=4\nmoney_multiplier=4\nfast_forward_multiplier={multiplier}\n')
        (folder/'input.replay').write_text('0 0\n')
        extra=['--windowed','--load-state','--input-script',str(folder/'input.replay'),'--frames','960','--capture-state','360']
        if enabled: extra.append('--fast-forward')
        elapsed, _ = run(exe,args.redux_assets,folder,extra)
        observed=output/(label+'-observer');observed.mkdir()
        shutil.copytree(args.owner_saves,observed/'saves')
        shutil.copy2(folder/'fixture.ini',observed/'fixture.ini')
        run(args.observer,args.redux_assets,observed,[*extra,'--qa-observation',str(observed/'observation.json')])
        observation=json.loads((observed/'observation.json').read_text())
        records=[dict(record,section=8) for record in observation['volatileWindowPointers']]+pointers
        blobs=[sections(latest(path),tamp) for path in (folder,observed)]
        for blob in blobs:
            for record in records: canonical_pointer(blob,record)
        if blobs[0]!=blobs[1]:
            different=[tag for tag in set(blobs[0])|set(blobs[1]) if blobs[0].get(tag)!=blobs[1].get(tag)]
            raise RuntimeError(f'{label}: player/observer mismatch in sections {different}')
        if baseline is None: baseline=blobs[0]
        different=[tag for tag in set(baseline)|set(blobs[0]) if baseline.get(tag)!=blobs[0].get(tag)]
        row={'case':label,'targetMultiplier':multiplier if enabled else 1,'elapsedSeconds':round(elapsed,3),
             'playerObserverSerializedMatch':True,'differentSectionsFromNormal':different,
             'position':observation['position'],'party':observation['party'],'eventFlags':observation['eventFlags']}
        rows.append(row)
        print(json.dumps({k:v for k,v in row.items() if k not in ('party','eventFlags')}),flush=True)
    if owner_before!={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.owner_saves.iterdir() if p.is_file()}:
        raise RuntimeError('Owner saves changed.')
    report={'Passed':True,'Cases':rows,'OwnerSavesUnchanged':True,'StateFormat':16,'FullPlaythroughVerified':False,
            'Limits':['Timed dummy-renderer playback is a bounded copied-save replay, not every game scene or a hardware speed guarantee.',
                      'Amplified experience changes combat balance; story/full combat combinations remain unverified.']}
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__': main()
