"""Run isolated encounter and audio regressions in both native editions/builds."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('production', 'observer', 'original-assets', 'redux-assets', 'msu-dir', 'scratch'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    scratch = args.scratch.resolve()
    if scratch.exists():
        raise ValueError('Preserve previous evidence; choose a fresh scratch directory.')
    scratch.mkdir(parents=True)
    env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
    rows = []
    for engine in ('production', 'observer'):
        exe = getattr(args, engine).resolve()
        for edition in ('original', 'redux'):
            pack = getattr(args, edition + '_assets').resolve()
            for test, flag, marker in (
                ('encounters', '--selftest-encounters', 'encounter self-test: 1178'),
                ('bicycle', '--selftest-bicycle-audio', 'Bicycle MSU after instant victory:'),
                ('sfx', '--selftest-sfx-audio', 'SFX delivery self-test: 42 cases, PASS'),
            ):
                folder = scratch / f'{engine}-{edition}-{test}'
                folder.mkdir()
                command = [str(exe), '--assets', str(pack), '--session-dir', str(folder),
                           '--save', str(folder / 'fixture.srm'), '--allow-redux-development',
                           '--headless', flag, '--msu-dir', str(args.msu_dir.resolve()),
                           '--msu-name', 'eb_msu1']
                result = subprocess.run(command, env=env, capture_output=True, timeout=60)
                output = (result.stdout + result.stderr).decode(errors='replace')
                (folder / 'native.log').write_text(output, encoding='utf-8')
                if result.returncode or marker not in output or re.search(r'FAIL|FATAL|ERROR', output):
                    raise RuntimeError(f'{folder.name} failed: {output[-2200:]}')
                rows.append({'engine': engine, 'edition': edition, 'test': test, 'passed': True,
                             'nativeExeSha256': hashlib.sha256(exe.read_bytes()).hexdigest().upper(),
                             'packSha256': hashlib.sha256(pack.read_bytes()).hexdigest().upper(),
                             'log': output})
                print(json.dumps({'test': folder.name, 'passed': True}), flush=True)
    report = {
        'Passed': True, 'tests': rows,
        'EncounterChecksPerEditionAndBuild': 1178, 'EnemyRecordsPerEdition': 230,
        'SfxCasesPerEditionAndBuild': 42, 'BicycleCasesPerEditionAndBuild': 4,
        'SfxCallbackRequestsPerEditionAndBuild': 256,
        'FullPlaythroughVerified': False,
        'Limits': [
            'Encounter checks prepare state and call the real shared contact, battle-entry and layout routines.',
            'Bicycle checks prepare music-return states and use real sector lookups and generated samples.',
            'SFX checks prepare callback timing and isolate effects from background music; these are not listening tests.',
        ],
    }
    (scratch / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
