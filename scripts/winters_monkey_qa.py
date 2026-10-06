# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared native Winters progression checks, using independent scratch saves.

Exercises actual menus, Bubble Gum, rope movement, climbing and departure.
Fixtures prepare the story/location; they do not establish a full playthrough.
No ROM, game assets, personal save or soundtrack is included in the report.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

from check_jev_observer_parity import latest, local_scratch, sections
from redux_recovery_qa import write_state

ROOT = Path(__file__).resolve().parents[1]
FLAGS = (14, 22, 129, 311, 323, 334, 338)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('engine', 'assets', 'scratch'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--redux', action='store_true')
    a = p.parse_args()
    exe, pak, output = a.engine.resolve(), a.assets.resolve(), local_scratch(a.scratch)
    if output.exists():
        raise ValueError('Choose a fresh scratch directory; preserve earlier evidence.')
    output.mkdir(parents=True)
    sys.path.insert(0, str(ROOT/'native-source/src/vendor/tamp'))
    import tamp
    results = []
    env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')

    def run(name, source=None, stage=None, actions=(), frames=120):
        d = output/name
        d.mkdir()
        if source:
            shutil.copytree(source/'saves', d/'saves')
        (d/'fixture.ini').write_text('companion=1\nwidth=1280\nheight=720\nvolume=0\ninstant_text=1\nfast_forward_multiplier=16\n', encoding='utf-8')
        replay = '0 0000\n'+'\n'.join(f'{f} {mask:04x}' for f, mask in actions)+'\n'
        (d/'input.replay').write_text(replay, encoding='utf-8')
        cmd = [str(exe), '--assets', str(pak), '--session-dir', str(d), '--save', str(d/'fixture.srm'),
               '--config', str(d/'fixture.ini'), '--allow-redux-development', '--fast-forward',
               '--input-script', str(d/'input.replay'), '--frames', str(frames+20), '--capture-state', str(frames)]
        cmd += ['--load-state'] if source else ['--winters-monkey-fixture', str(stage)]
        proc = subprocess.run(cmd, env=env, capture_output=True, timeout=30)
        log = (proc.stdout+proc.stderr).decode(errors='replace')
        (d/'native.log').write_text(log, encoding='utf-8')
        if proc.returncode:
            raise RuntimeError(name+': '+log[-1200:])
        s = sections(latest(d), tamp)
        flags = {f: bool(s[4][(f-1)//8] & (1 << ((f-1)%8))) for f in FLAGS}
        state = {'party': list(s[2][122:128]), 'flags': flags,
                 'position': [struct.unpack_from('<H', s[2], off)[0] for off in (130, 134)]}
        return d, state, log

    def record(name, state, checks):
        if not all(checks.values()):
            raise AssertionError((name, state, checks))
        results.append({'test': name, 'checks': checks, 'passed': True})
        print(name+': PASS', flush=True)

    def presses(times, mask=0x20):
        return [(f, v) for t in times for f, v in ((t, mask), (t+1, 0))]

    before, s, log = run('before-cave', stage=0)
    record('before-cave', s, {'monkeyRemains': s['party'][:2] == [3, 9] and s['flags'][22],
                              'ropeNotSkipped': not s['flags'][311], 'departureNpcDormant': 'id=632 ' not in log})
    rope, s, _ = run('rope-site', stage=1)
    record('rope-site', s, {'ropeProximity': s['flags'][338], 'monkeyRemains': s['flags'][22]})
    if a.redux:
        inputs = presses([10], 0x40)+presses([30], 0x400)+presses([70, 130, 190])
    else:
        inputs = presses([10], 0x80)+presses([30], 0x400)+presses([70, 130, 190])
    used, s, _ = run('gum-and-rope', rope, actions=inputs+presses(range(280, 2050, 45)), frames=2200)
    record('gum-and-rope', s, {'ropeLowered': s['flags'][311], 'proximityCleared': not s['flags'][338],
                              'monkeyRemains': s['party'][:2] == [3, 9] and s['flags'][22]})
    climb, s, _ = run('climb', used, actions=[(10, 0x800), (120, 0)], frames=180)
    record('climb', s, {'reachedUpperLedge': s['position'][1] < 320, 'monkeyRemains': s['flags'][22]})
    exit_state, s, log = run('cave-exit', stage=2)
    record('cave-exit', s, {'monkeyWaitsAtExit': s['party'][:2] == [3, 9] and s['flags'][22],
                           'departureNpcActive': 'id=632 ' in log})
    departed, s, _ = run('normal-departure', exit_state, actions=[(10, 0x400), (50, 0)]+presses(range(200, 1900, 45)), frames=2000)
    record('normal-departure', s, {'monkeyLeft': s['party'][:2] == [3, 0] and not s['flags'][22],
                                 'ropeMilestoneRetained': s['flags'][311]})
    _, s, _ = run('departure-cold-reload', departed)
    record('departure-cold-reload', s, {'monkeyStaysGone': s['party'][:2] == [3, 0] and not s['flags'][22]})
    _, s, _ = run('old-broken-state', stage=3)
    record('old-broken-state', s, {'monkeyRecovered': s['party'][:2] == [3, 9] and s['flags'][22],
                                 'puzzleStillRequired': not s['flags'][311], 'positionRetained': s['position'] == [5029, 406]})

    # Turn a valid prepared checkpoint into impossible/irrelevant legacy
    # cases, exclusively inside scratch. Do not grant a companion if any
    # required acquisition/crossing/party condition is absent.
    for name, flag, enabled, leader in (
        ('without-gum', 323, False, 3), ('before-tessie', 129, False, 3),
        ('after-jeff-joins', 14, True, 3), ('different-leader', None, False, 1)):
        prepared = output/('prepared-'+name)
        prepared.mkdir(); shutil.copytree(rope/'saves', prepared/'saves')
        path = latest(prepared); blobs = sections(path, tamp)
        blobs[2][122:128] = bytes((leader, 0, 0, 0, 0, 0))
        # These negative fixtures exercise the repair predicate only. They
        # prepare a one-member logical roster and vary the required flag or
        # leader; the remaining unused entity data is not a playable save.
        blobs[2][150:156] = bytes((leader, 0, 0, 0, 0, 0))
        blobs[2][174] = blobs[2][175] = 1
        def setflag(f, value):
            index, mask = (f-1)//8, 1 << ((f-1)%8)
            if value: blobs[4][index] |= mask
            else: blobs[4][index] &= ~mask
        setflag(22, False)
        if flag: setflag(flag, enabled)
        write_state(path, blobs, tamp)
        _, s, _ = run(name, prepared)
        record(name, s, {'noStoryCompanionGranted': not s['flags'][22] and s['party'][1] == 0})

    report = {'status': 'experimental', 'edition': 'Redux' if a.redux else 'Original',
              'engineSha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
              'assetsSha256': hashlib.sha256(pak.read_bytes()).hexdigest(), 'tests': results,
              'limits': ['Prepared positions/story flags, real native menu and movement paths.',
                         'Does not establish a full story or randomized playthrough.']}
    (output/'results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
