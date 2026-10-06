# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify the owner-ROM Original movement container without distributing data."""
import argparse
import contextlib
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

from build_maternalbound_pack import read_pack


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('native-source', 'rom', 'fresh-pack', 'legacy-pack', 'expected-redux', 'compiled-rom',
                 'project', 'bridge', 'converted-directory', 'setup-log', 'scratch', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    if a.scratch.exists():
        raise ValueError('Use a fresh private scratch directory.')
    a.scratch.mkdir(parents=True)
    sys.path.insert(0, str(a.native_source.resolve()))
    from ebtools.cli.pack_all import pack_all
    from ebtools.parsers.original_movement_banks import decode_original_movement_banks, extract_original_movement_banks
    ids = a.native_source / 'src/data/runtime_generated/asset_ids.h'
    entries, header, fresh = read_pack(a.fresh_pack, ids)
    old_entries, old_header, old = read_pack(a.legacy_pack, ids)
    raw = a.rom.read_bytes()
    if len(raw) == 0x300200:
        raw = raw[512:]
    if len(raw) != 0x300000 or hashlib.sha256(raw).hexdigest().upper() != 'A8FE2226728002786D68C27DDDDF0B90A894DB52E4DFE268FDF72A68CAE5F02E':
        raise ValueError('Expected the supported owner-provided USA ROM.')
    key = 'US/events/bank_c3_scripts_combined.bin'
    c3, ghost = decode_original_movement_banks(fresh[key])
    extracted = extract_original_movement_banks(raw[0x30000:0x3E012], raw)
    donor_c3, donor_ghost = decode_original_movement_banks(extracted)
    checks = []

    def check(name, expected, actual):
        checks.append({'name': name, 'expected': expected, 'actual': actual, 'passed': actual == expected})

    check('Existing asset layout/header and IDs preserved', True, entries == old_entries and header == old_header)
    changed = sorted(k for k in fresh if fresh[k] != old[k])
    check('Fresh actual setup changes only the C3 asset key', [key], changed)
    check('Production setup retains exact previously remapped C3 content', True, c3 == old[key])
    check('Ghost extracted from supported donor pointer region', True, ghost == donor_ghost == raw[0xAD8A:0xAD9F])
    check('Pinned Redux and owner Original ghost bytecode agree', True, ghost == a.compiled_rom.read_bytes()[0xAD8A:0xAD9F])
    check('Real setup CLI completed', True, 'Done! Wrote' in a.setup_log.read_text() and 'Packed 1174 assets' in a.setup_log.read_text())

    for mode in ('container-raw', 'container-json', 'legacy-raw'):
        directory = a.scratch / mode
        binary = directory / 'bin' / 'US' / 'events'
        assets = directory / 'assets'
        binary.mkdir(parents=True)
        assets.mkdir()
        (binary / 'bank_c3_scripts_combined.bin').write_bytes(donor_c3 if mode == 'legacy-raw' else extracted)
        edited = bytearray(donor_c3)
        if mode == 'container-json':
            # Private schema/override test only; no claim that this arbitrary
            # changed byte is a playable mod. The donor ghost must survive it.
            edited[0] ^= 1
            target = assets / 'locale/events/bank_c3_scripts.json'
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(list(edited)))
        out = directory / 'packed'
        refs = directory / 'refs'
        refs.mkdir()
        log = io.StringIO()
        with contextlib.redirect_stdout(log):
            pack_all(assets_dir=assets, output_dir=out, bin_dir=directory/'bin',
                     yaml_config=a.native_source/'earthbound.yml', commondata=a.native_source/'commondefs.yml',
                     text_refs_dir=refs)
        (directory/'pack-all.log').write_text(log.getvalue())
        packed = (out/key).read_bytes()
        decoded = decode_original_movement_banks(packed)
        if mode == 'legacy-raw':
            check('Legacy naked C3 pack-all stays naked and unchanged', True, decoded is None and packed == donor_c3)
        else:
            check(mode+' exact C3 body', True, decoded is not None and decoded[0] == bytes(edited))
            check(mode+' donor ghost retained', True, decoded is not None and decoded[1] == donor_ghost)

    rebuilt = a.scratch / 'rebuilt-redux.pak'
    command = [sys.executable, str(Path(__file__).with_name('build_maternalbound_pack.py').resolve()),
               '--base-assets', str(a.fresh_pack.resolve()), '--native-source', str(a.native_source.resolve()),
               '--bridge', str(a.bridge.resolve()), '--converted-directory', str(a.converted_directory.resolve()),
               '--compiled-rom', str(a.compiled_rom.resolve()), '--project', str(a.project.resolve()), '--output', str(rebuilt.resolve())]
    run = subprocess.run(command, capture_output=True, timeout=180)
    (a.scratch/'redux-build.stdout.log').write_bytes(run.stdout)
    (a.scratch/'redux-build.stderr.log').write_bytes(run.stderr)
    check('Actual Redux builder succeeds using new Original base container', 0, run.returncode)
    check('Actual rebuilt Redux pack stays byte-identical', True, rebuilt.exists() and rebuilt.read_bytes() == a.expected_redux.read_bytes())
    passed = all(c['passed'] for c in checks)
    report = {'format':'original-movement-pack-qa-v1','Passed':passed,'allPassed':passed,
              'executedCases':4,'executedAssertions':len(checks),'skippedCases':0,'checks':checks,
              'freshOriginalPackSha256':digest(a.fresh_pack),'legacyOriginalPackSha256':digest(a.legacy_pack),
              'expectedReduxPackSha256':digest(a.expected_redux),'rebuiltReduxPackSha256':digest(rebuilt) if rebuilt.exists() else None,
              'ownerRomSha256':hashlib.sha256(raw).hexdigest().upper(),'compiledReduxRomSha256':digest(a.compiled_rom),
              'ghostRegion':{'address':'C0AD8A','bytes':21,'sha256':hashlib.sha256(ghost).hexdigest().upper()},
              'assetCount':len(entries),'layoutHeaderSha256':hashlib.sha256(header).hexdigest().upper(),
              'setupLogSha256':digest(a.setup_log),'toolSha256':digest(Path(__file__)),
              'sourceFiles':{str(p.relative_to(a.native_source)):digest(p) for p in [a.native_source/'ebtools/cli/extract.py',
                  a.native_source/'ebtools/cli/pack_all.py',a.native_source/'ebtools/parsers/original_movement_banks.py']},
              'reduxCompatibilitySourceSha256':digest(Path(__file__).with_name('maternalbound_events.py')),
              'limits':['Only hashes, addresses and assertions are public; ROM, extracted assets, bytecode, JSON arrays and rebuilt packs remain private.',
                        'JSON override check verifies schema/data preservation, not playability of an arbitrary edited movement instruction.',
                        'Legacy naked C3 remains readable but cannot supply Original EVENT786 until locally regenerated from the owner ROM.',
                        'These extraction checks do not establish complete event interpreter semantics or full gameplay parity.']}
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'allPassed':passed,'assertions':len(checks),'failed':[c for c in checks if not c['passed']]}))
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
