# SPDX-License-Identifier: GPL-3.0-or-later
"""Check numeric/header consumers without ROM, ebtools or extracted JSON.

Explicit local inputs; generated headers/caller stay in a fresh private scratch
directory. The public metadata report contains hashes/counts and proof limits.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def asm_ids(path, kind):
    text = path.read_text(encoding='utf-8-sig')
    # Independent narrow extraction of the explicit checked-in symbol table.
    section = re.search(r'^\.ENUM ' + kind + r'\s*$(.*?)^\.ENDENUM\s*$', text, re.M | re.S)
    if not section:
        raise ValueError('Missing complete source enum: ' + str(path))
    rows = re.findall(r'^\s*([A-Z][A-Z0-9_]*)\s*=\s*(\$[0-9A-Fa-f]+|\d+)\s*$', section.group(1), re.M)
    return {kind + '_' + name: int(value[1:], 16) if value.startswith('$') else int(value, 10) for name, value in rows}


def header_ids(path, kind):
    text = path.read_text(encoding='utf-8-sig')
    pattern = r'\b(ITEM_\w+)\s*=\s*(0x[0-9a-fA-F]+|\d+)' if kind == 'ITEM' else r'^#define\s+(MUSIC_\w+)\s+(\d+)\s*$'
    return {name: int(value, 0) for name, value in re.findall(pattern, text, re.M)
            if name not in ('ITEM_ID_COUNT', 'MUSIC_TRACK_COUNT')}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('generator', 'items-source', 'music-source', 'baseline-headers', 'gcc', 'scratch', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    args = p.parse_args()
    if args.scratch.exists() or args.output.exists():
        raise ValueError('Fresh scratch/output required')
    args.scratch.mkdir(parents=True)
    args.scratch = args.scratch.resolve()
    result = subprocess.run([sys.executable, str(args.generator), '--items-source', str(args.items_source),
                             '--music-source', str(args.music_source), '--output-dir', str(args.scratch / 'headers')],
                            capture_output=True, text=True, encoding='utf-8')
    if result.returncode:
        raise ValueError('Source generator failed: ' + result.stderr)
    source = {'ITEM': asm_ids(args.items_source, 'ITEM'), 'MUSIC': asm_ids(args.music_source, 'MUSIC')}
    baseline = {}; generated = {}; comparisons = {}
    for kind, filename, count in [('ITEM', 'items_generated.h', 254), ('MUSIC', 'music_generated.h', 192)]:
        baseline[kind] = header_ids(args.baseline_headers / filename, kind)
        generated[kind] = header_ids(args.scratch / 'headers' / filename, kind)
        if len(source[kind]) != count or generated[kind] != source[kind]:
            raise ValueError('Generated IDs differ from all explicit source IDs: ' + kind)
        if any(source[kind].get(name) != value for name, value in baseline[kind].items()):
            raise ValueError('An existing generated gameplay ID changed: ' + kind)
        comparisons[kind] = {'sourceIDsCompared': count, 'existingHeaderIDsCompared': len(baseline[kind]),
                             'existingIDMismatches': 0,
                             'additionalSourceDefinedIDs': {name: value for name, value in source[kind].items() if name not in baseline[kind]}}
    hashes = {name: sha(args.scratch / 'headers' / name) for name in ('items_generated.h', 'music_generated.h')}
    mtimes = {name: (args.scratch / 'headers' / name).stat().st_mtime_ns for name in hashes}
    again = subprocess.run([sys.executable, str(args.generator), '--items-source', str(args.items_source),
                            '--music-source', str(args.music_source), '--output-dir', str(args.scratch / 'headers')],
                           capture_output=True, text=True, encoding='utf-8')
    if again.returncode or any(sha(args.scratch / 'headers' / name) != value for name, value in hashes.items()) or any((args.scratch / 'headers' / name).stat().st_mtime_ns != value for name, value in mtimes.items()):
        raise ValueError('Identical source should not rewrite generated headers')
    legacy_dir = args.scratch / 'legacy-cp1252-headers'
    legacy_dir.mkdir()
    for name in hashes:
        old = (args.baseline_headers / name).read_text(encoding='utf-8-sig').encode('cp1252')
        if b'\x97' not in old:
            raise ValueError('Expected historical CP1252 em-dash comment: ' + name)
        (legacy_dir / name).write_bytes(old)
    legacy = subprocess.run([sys.executable, str(args.generator), '--items-source', str(args.items_source),
                             '--music-source', str(args.music_source), '--output-dir', str(legacy_dir)],
                            capture_output=True, text=True, encoding='utf-8')
    if legacy.returncode or any(sha(legacy_dir / name) != value for name, value in hashes.items()):
        raise ValueError('Stale CP1252 generated headers were not replaced safely')
    caller = ['#define ITEMS_INCLUDE_NAMES', '#define MUSIC_INCLUDE_NAMES', '#include "items_generated.h"',
              '#include "music_generated.h"', '#include <stdio.h>', '#include <string.h>']
    for kind in ('ITEM', 'MUSIC'):
        caller += [f'_Static_assert({name} == {value}, "source numeric ID");' for name, value in source[kind].items()]
    caller += ['_Static_assert(ITEM_ID_COUNT == 254, "item diagnostics count");',
               '_Static_assert(MUSIC_TRACK_COUNT == 192, "music diagnostics count");', 'int main(void) {']
    for kind, array in [('ITEM', 'ITEM_ID_NAMES'), ('MUSIC', 'MUSIC_TRACK_NAMES')]:
        caller += [f'    if (strcmp({array}[{value}], "{name}")) return 1;' for name, value in source[kind].items()]
    caller += ['    puts("254 item and192 music constants/name-array consumers: PASS");', '    return 0;', '}']
    caller_path = args.scratch / 'constants_consumer.c'
    caller_path.write_text('\n'.join(caller) + '\n', encoding='utf-8')
    compile_result = subprocess.run([str(args.gcc), '-std=c11', '-Wall', '-Wextra', '-Werror', '-I', str(args.scratch / 'headers'),
                                     str(caller_path), '-o', str(args.scratch / 'constants_consumer.exe')],
                                    capture_output=True, text=True, encoding='utf-8')
    if compile_result.returncode:
        raise ValueError('Header consumer compilation failed: ' + compile_result.stderr)
    consumer = subprocess.run([str(args.scratch / 'constants_consumer.exe')], capture_output=True, text=True, encoding='utf-8')
    if consumer.returncode:
        raise ValueError('Compiled diagnostic arrays differ from source symbols')
    bad_cases = [
        ('duplicate-item-symbol', 'ITEM', lambda text: text.replace('FRANKLIN_BADGE', 'NONE', 1)),
        ('duplicate-item-value', 'ITEM', lambda text: text.replace('FRANKLIN_BADGE = $01', 'FRANKLIN_BADGE = $00', 1)),
        ('missing-music-entry', 'MUSIC', lambda text: re.sub(r'^\s*GIYGAS_WEAKENED = 191\s*$', '', text, flags=re.M)),
        ('unterminated-music-enum', 'MUSIC', lambda text: text.replace('.ENDENUM', '', 1)),
    ]
    negatives = []
    for label, kind, alter in bad_cases:
        directory = args.scratch / label; directory.mkdir()
        items = directory / 'items.asm'; music = directory / 'music.asm'
        items.write_text(args.items_source.read_text(encoding='utf-8-sig'), encoding='utf-8')
        music.write_text(args.music_source.read_text(encoding='utf-8-sig'), encoding='utf-8')
        bad = items if kind == 'ITEM' else music
        original = bad.read_text(encoding='utf-8'); changed = alter(original)
        if changed == original:
            raise ValueError('Negative control did not alter input: ' + label)
        bad.write_text(changed, encoding='utf-8')
        run = subprocess.run([sys.executable, str(args.generator), '--items-source', str(items), '--music-source', str(music),
                              '--output-dir', str(directory / 'headers')], capture_output=True, text=True, encoding='utf-8')
        passed = run.returncode != 0 and not (directory / 'headers').exists()
        if not passed:
            raise ValueError('Malformed enum accepted or partial output emitted: ' + label)
        negatives.append({'case': label, 'rejectedBeforeAnyHeaderOutput': True})
    inputs = {str(path.resolve()): sha(path) for path in (args.generator, args.items_source, args.music_source,
                                                       args.baseline_headers / 'items_generated.h', args.baseline_headers / 'music_generated.h', args.gcc)}
    report = {'format': 'runtime-source-constants-header-qa-v1', 'Passed': True,
              'sourceComparisons': comparisons, 'generatedHeaderSha256': hashes,
              'compiledConsumerNumericStaticAssertions': 446, 'compiledConsumerDiagnosticNameComparisons': 446,
              'consumerOutput': consumer.stdout.strip(), 'identicalRegenerationPreservedBytesAndMtimes': True,
              'bothLegacyCp1252GeneratedHeadersSafelyReplaced': True,
              'malformedInputNegativeControls': negatives, 'inputs': inputs,
              'runnerSha256': sha(Path(__file__)), 'ROMOrExtractedGameJsonRead': False,
              'gameDataRecordsWritten': False, 'sharedBuildModified': False,
              'limits': ['Source-defined numeric constants and diagnostics are checked; no gameplay or full story is run.',
                         'All254 existing Item and191 historical Music IDs match; source-defined MUSIC_GIYGAS_WEAKENED191 expands diagnostics to192 entries.',
                         'Diagnostic strings are source symbols, not extracted in-game text. Runtime packs still provide actual records.',
                         'The separate clean-build report records actual CMake/gen_struct_info/whole native executable compilation.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'Passed': True, 'numericIDs': 446, 'compiledNameComparisons': 446, 'negativeControls': len(negatives)}))


if __name__ == '__main__':
    main()
