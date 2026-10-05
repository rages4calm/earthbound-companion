# SPDX-License-Identifier: MIT
"""Reproduce a captured cliff crossing and verify an isolated position recovery.

Requires an owner-provided state and local asset pack. All writes stay in a
fresh _BuildScratch directory. No owner save is edited, and no game data is
included in the public report.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'native-source/src/vendor/tamp'))
import tamp
from check_jev_observer_parity import sections, latest
from redux_recovery_qa import write_state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'assets', 'settings', 'previous', 'player', 'observer', 'collision', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / '_BuildScratch') or output.exists():
        raise ValueError('Use a fresh output below _BuildScratch.')
    output.mkdir(parents=True)
    source_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.source/'saves').iterdir()}
    original = sections(latest(args.source), tamp)
    collision = bytes.fromhex(json.loads(args.collision.read_text())['collisionHex'])
    x, y = 4681, 1743  # Clear position in this capture's actual pre-crossing history.
    history = [struct.unpack_from('<hhBBBB', original[11], i*8)[:2] for i in range(256)]
    if (x, y) not in history:
        raise ValueError('This fixture is specific to the reviewed cliff capture.')
    for dx, dy in ((-8, 0), (0, 0), (7, 0), (-8, 7), (0, 7), (7, 7)):
        if collision[(((y+dy)>>3)&63)*64 + (((x+dx)>>3)&63)] & 0xC0:
            raise ValueError('The reviewed recovery footprint is blocked.')
    env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
    env['PATH'] = str(ROOT/'tools/SDL2-2.32.10/x86_64-w64-mingw32/bin') + ';' + str(ROOT/'tools/mingw64/bin') + ';' + env['PATH']
    rows = []
    for label, exe, replay, frames, capture in (
        ('old-crossing', args.previous, '0 0\n30 0x4800\n38 0x4200\n140 0\n', 170, 150),
        ('fixed-player-crossing', args.player, '0 0\n30 0x4800\n38 0x4200\n140 0\n', 170, 150),
        ('fixed-observer-crossing', args.observer, '0 0\n30 0x4800\n38 0x4200\n140 0\n', 170, 150),
        ('recovered-player', args.player, '0 0\n4 0x0400\n5 0\n', 90, 45),
        ('recovered-observer', args.observer, '0 0\n4 0x0400\n5 0\n', 90, 45),
        ('recovered-egress', args.observer, '0 0\n4 0x4400\n60 0\n', 90, 75),
    ):
        folder = output / label; folder.mkdir()
        shutil.copytree(args.source/'saves', folder/'saves')
        path = latest(folder); blobs = sections(path, tamp); gs = blobs[2]
        # Reposition only the party and its trailing history; preserve story,
        # inventory, HP/PP, experience, money and the normal phone save.
        struct.pack_into('<HHHHHHHHH', gs, 128, 0, x, 0, y, 0, 4, 0, 0, 1)
        blobs[11][:2048] = struct.pack('<hhBBBB', x, y, 0, 0, 4, 0)*256
        for i in range(6):
            struct.pack_into('<H', blobs[3], i*95+61, 0)
        write_state(path, blobs, tamp)
        shutil.copy2(args.settings, folder/'settings.dat')
        (folder/'fixture.ini').write_text('width=1280\nheight=720\nvolume=0\ninstant_text=1\nno_homesickness=1\nno_dad_calls=1\nfast_forward_multiplier=16\n')
        (folder/'input.replay').write_text(replay)
        command = [str(exe.resolve()), '--assets', str(args.assets.resolve()), '--session-dir', str(folder),
                   '--save', str(folder/'fixture.srm'), '--config', str(folder/'fixture.ini'), '--load-state',
                   '--allow-redux-development', '--frames', str(frames), '--capture-state', str(capture),
                   '--dump-frame', str(capture+10), '--input-script', str(folder/'input.replay'), '--fast-forward']
        if exe == args.observer:
            command += ['--qa-observation', str(folder/'observation.json')]
        process = subprocess.run(command, env=env, capture_output=True, timeout=30)
        (folder/'native.log').write_bytes(process.stdout+process.stderr)
        if process.returncode:
            raise RuntimeError(f'{label}: {process.returncode}: {process.stderr.decode(errors="replace")[-1000:]}')
        end = sections(latest(folder), tamp)
        position = [struct.unpack_from('<H', end[2], offset)[0] for offset in (130, 134)]
        trail = [struct.unpack_from('<hhBBBB', end[11], i*8)[:2] for i in range(256)]
        bad = [p for p in trail if collision[(((p[1]+4)>>3)&63)*64+((p[0]>>3)&63)] & 0xC0]
        row = {'case': label, 'position': position, 'solidFootprintHistoryEntries': len(bad), 'exit': 0}
        if label.startswith('recovered-'):
            original_party, end_party = bytearray(original[3]), bytearray(end[3])
            for i in range(6):
                for data in (original_party, end_party): data[i*95+61:i*95+63] = b'\0\0'
            if original_party != end_party or original[4] != end[4]:
                raise RuntimeError('Recovery changed party stats/inventory or story flags.')
            # These fields precede coordinates and include wallet, bank and inventories.
            if original[2][:128] != end[2][:128]:
                raise RuntimeError('Recovery changed player data.')
            if (folder/'saves/earthbound.srm').read_bytes() != (args.source/'saves/earthbound.srm').read_bytes():
                raise RuntimeError('Phone save changed.')
            row['progressPreserved'] = True
        print(json.dumps(row), flush=True); rows.append(row)
    if rows[0]['solidFootprintHistoryEntries'] == 0:
        raise RuntimeError('The archived engine did not reproduce the cliff crossing.')
    if any(row['solidFootprintHistoryEntries'] for row in rows[1:]):
        raise RuntimeError('The corrected engine entered a blocked tile.')
    if rows[-1]['position'][1] <= y+24:
        raise RuntimeError('The recovered party cannot leave the cliff approach.')
    if source_hashes != {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.source/'saves').iterdir()}:
        raise RuntimeError('Source state changed.')
    report = {'Passed': True, 'Cases': rows, 'SourceSavesUnchanged': True, 'FullPlaythroughVerified': False}
    (output/'results.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__': main()
