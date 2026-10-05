# SPDX-License-Identifier: MIT
"""Replay archived ordinary inputs in production and observer builds.

Only independent copies below _BuildScratch are written. No TypeSafe request
is made. Process addresses rebuilt on load are canonicalized, preserving NULL
versus non-NULL; all other serialized bytes and the phone save must match.
"""
from __future__ import annotations
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


def local_scratch(path):
    original = Path(path).absolute()
    if any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction())
           for p in (original, *original.parents)):
        raise ValueError('Scratch paths cannot be redirected.')
    path = original.resolve()
    if not path.is_relative_to(ROOT / '_BuildScratch') or path == ROOT / '_BuildScratch':
        raise ValueError('Use an isolated directory below _BuildScratch.')
    return path


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def latest(folder):
    return max((folder / 'saves').glob('quicksave_1.bin.*'),
               key=lambda p: struct.unpack_from('<I', p.read_bytes(), 8)[0])


def sections(path, tamp):
    header = path.read_bytes()
    if header[:4] != b'EBSD' or struct.unpack_from('<H', header, 4)[0] != 16:
        raise ValueError('This replay is reviewed for state format 16.')
    data, offset, out = tamp.decompress(header[20:]), 0, {}
    while offset < len(data):
        tag = struct.unpack_from('<H', data, offset)[0];offset += 2
        if tag == 0xffff:
            if offset != len(data):
                raise ValueError('Trailing state data.')
            return out
        size = struct.unpack_from('<I', data, offset)[0];offset += 4
        if tag in out or offset + size > len(data):
            raise ValueError('Malformed state sections.')
        out[tag] = bytearray(data[offset:offset + size]);offset += size
    raise ValueError('State terminator missing.')


def pointer_layout(native, compiler, output):
    source = output / 'psi-pointer-layout.c'
    source.write_text('''#include <stdio.h>
#include <stddef.h>
#include "game/oval_window.h"
int main(void) {
 printf("%zu %zu %zu %zu %zu\\n", sizeof(PsiAnimationState),
 offsetof(PsiAnimationState,arr_bundled_data),sizeof(((PsiAnimationState*)0)->arr_bundled_data),
 offsetof(PsiAnimationState,arr_bundle_buf),sizeof(((PsiAnimationState*)0)->arr_bundle_buf));
 return 0;
}
''', encoding='utf-8')
    exe = output / 'psi-pointer-layout.exe'
    subprocess.run([str(compiler), '-std=c2x', '-I', str(native / 'src'), str(source), '-o', str(exe)], check=True, capture_output=True, timeout=60)
    values = [int(x) for x in subprocess.check_output([str(exe)], text=True, timeout=10).split()]
    if values != [88, 64, 8, 80, 8]:
        raise ValueError('PSI layout changed; review exclusions before replay.')
    rebind = (native / 'src/game/battle_psi.c').read_text(encoding='utf-8')
    for anchor in ('psi_animation_state.arr_bundle_buf = ert.buffer;',
                   'psi_animation_state.arr_bundled_data = psi_asset(1,anim_id,&size);'):
        if anchor not in rebind:
            raise ValueError('PSI pointer rebind implementation changed.')
    return [{'section': 20, 'offset': offset, 'bytes': 8, 'field': name}
            for offset, name in ((64, 'arr_bundled_data'), (80, 'arr_bundle_buf'))]


def canonical_pointer(blob, record):
    tag, start, size = record['section'], record['offset'], record['bytes']
    if size != 8 or start < 0 or start + size > len(blob[tag]):
        raise ValueError('Invalid pointer exclusion.')
    # Preserve pointer presence: ignoring a NULL/non-NULL change could conceal
    # a real logic difference. Only the address of an existing binding varies.
    value = int(any(blob[tag][start:start + size]))
    blob[tag][start:start + size] = value.to_bytes(size, 'little')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--production', type=Path, default=ROOT / 'build/companion/earthbound.exe')
    parser.add_argument('--observer', type=Path, default=ROOT / 'build/jev-qa/earthbound.exe')
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--native-source', type=Path, default=ROOT / 'native-source')
    parser.add_argument('--compiler', type=Path, default=ROOT / 'tools/mingw64/bin/gcc.exe')
    args = parser.parse_args()
    output = local_scratch(args.output)
    if output.exists():
        raise ValueError('Preserve prior evidence; choose a fresh output.')
    output.mkdir(parents=True)
    sys.path.insert(0, str(args.native_source.resolve() / 'src/vendor/tamp'))
    import tamp
    psi = pointer_layout(args.native_source.resolve(), args.compiler.resolve(), output)
    env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
    rows = []
    for evidence_path in args.run:
        evidence = local_scratch(evidence_path)
        run = json.loads((evidence / 'run.json').read_text(encoding='utf-8'))
        if sha(args.observer) != run['nativeExeSha256'] or sha(args.assets) != run['assetsSha256']:
            raise ValueError('Replay runtime differs from archived evidence.')
        steps = sorted(p for p in evidence.iterdir() if p.is_dir() and p.name.isdigit())
        if not steps or [int(p.name) for p in steps] != list(range(len(steps))):
            raise ValueError('An unbroken archived run beginning with step zero is required.')
        case = output / evidence.name;case.mkdir()
        sessions = []
        # Captured pre-step data is immutable evidence. Do not depend on the
        # source run's later state or reuse an already advanced session.
        for label in ('baseline', 'observed'):
            folder = case / label;folder.mkdir()
            shutil.copytree(steps[0] / 'before-saves', folder / 'saves')
            if (steps[0] / 'before.srm').exists():
                shutil.copy2(steps[0] / 'before.srm', folder / 'fixture.srm')
            shutil.copy2(evidence / 'fixture.ini', folder / 'fixture.ini')
            sessions.append(folder)
        for expected in steps:
            index = int(expected.name)
            capture = json.loads((expected / 'step.json').read_text(encoding='utf-8'))['action']['settle']
            for observed, folder in enumerate(sessions):
                exe = args.observer if observed else args.production
                command = [str(exe.resolve()), '--assets', str(args.assets.resolve()),
                           '--session-dir', str(folder), '--save', str(folder / 'fixture.srm'),
                           '--config', str(folder / 'fixture.ini'), '--allow-redux-development',
                           '--skip-intro', '--load-state', '--headless', '--input-script',
                           str(expected / 'inputs.replay'), '--frames', str(capture + 400),
                           '--capture-state', str(capture)]
                if observed:
                    command += ['--qa-observation', str(folder / 'observation.json')]
                result = subprocess.run(command, cwd=folder, env=env, capture_output=True, timeout=30)
                (folder / f'{index:04d}.log').write_bytes(result.stdout + result.stderr)
                result.check_returncode()
            blobs = [sections(latest(folder), tamp) for folder in sessions]
            observation = json.loads((sessions[1] / 'observation.json').read_text(encoding='utf-8'))
            windows = [dict(record, section=8) for record in observation['volatileWindowPointers']]
            for record in windows + psi:
                for blob in blobs:
                    canonical_pointer(blob, record)
            if blobs[0] != blobs[1]:
                differing = [tag for tag in set(blobs[0]) | set(blobs[1]) if blobs[0].get(tag) != blobs[1].get(tag)]
                raise RuntimeError(f'State mismatch at {evidence.name} step {index}: sections {differing}')
            if (sessions[0] / 'fixture.srm').read_bytes() != (sessions[1] / 'fixture.srm').read_bytes():
                raise RuntimeError('Phone save differs.')
            rows.append({'case': evidence.name, 'step': index, 'serializedSectionsMatch': True, 'phoneSaveBytesMatch': True})
    report = {'Passed': True, 'Checkpoints': rows, 'baselineEngineSha256': sha(args.production),
              'observedEngineSha256': sha(args.observer), 'packSha256': sha(args.assets),
              'Exclusions': [
                  {'section': 8, 'fields': ['WindowInfo.content_tilemap', 'WindowInfo.cursor_move_callback']},
                  {'section': 20, 'fields': ['PsiAnimationState.arr_bundled_data', 'PsiAnimationState.arr_bundle_buf'], 'offsets': [64, 80]}],
              'NullPointerPresenceCompared': True, 'PSIPointerLayoutCompilerVerified': True,
              'ExclusionReason': 'Process addresses rebuilt from saved IDs, offsets and the entity staging buffer on every load. Every other serialized byte, including animation timing, palette and bundle identity, must match.',
              'FullPlaythroughVerified': False}
    (output / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'Passed': True, 'matchingStateCheckpoints': len(rows)}))


if __name__ == '__main__':
    main()
