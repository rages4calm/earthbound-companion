# SPDX-License-Identifier: GPL-3.0-or-later
"""Append a strict v4 transaction refresh without changing frozen v3 proof."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    root = a.root
    old_name = 'research/inventory-selector-dev21-final-manifest.json'
    old = json.loads((root / old_name).read_text())
    for entry in old['files']:
        if digest(root / entry['path']) != entry['sha256']:
            raise ValueError('Frozen v3 dependency changed: ' + entry['path'])
    ledger, files = [], [old_name, 'tools/write_inventory_selector_refresh_dev22.py']
    for profile in ('original', 'redux'):
        for kind, stem, count, cold in (
            ('monkey', 'monkey-barter-dev20', 101, 16),
            ('services', 'service-selector-dev21', 28, 12)):
            suffix = '-finalpack' if profile == 'redux' else ''
            name = f'research/{profile}-{stem}-v4{suffix}.json'
            r = json.loads((root / name).read_text())
            observed_cold = sum(bool(c['fixture'].get('checkpoint')) for c in r['cases'])
            if not r['allPassed'] or len(r['cases']) != count or observed_cold != cold:
                raise ValueError('Incomplete strict refresh: ' + name)
            before = next(row for row in old['verifiedLedger']
                          if row['profile'] == profile and row['scope'] == kind)
            old_report = json.loads((root / before['report']).read_text())
            if r['executedSourceReferences'] != old_report['executedSourceReferences']:
                raise ValueError('Transaction source changed: ' + name)
            if r['assetsSha256'] != before['assetsSha256']:
                raise ValueError('Transaction pack changed: ' + name)
            ledger.append(dict(profile=profile, scope=kind, report=name,
                               selectedCases=count, coldContinuationsIncluded=cold,
                               runtimeSha256=r['runtimeSha256'],
                               librarySha256=r['privateBuild']['productionLibrarySha256'],
                               assetsSha256=r['assetsSha256'],
                               transactionSourceByteIdenticalToV3=True))
            files.append(name)
    r = dict(schemaVersion=1, toolVersion='dev22-v4-inventory-transaction-refresh',
             frozenRuntime='dev17-v4', parentSequences=258,
             coldContinuationsIncluded=56, verifiedLedger=ledger,
             previousManifest=dict(path=old_name, sha256=digest(root / old_name),
                                   filesVerified=len(old['files'])),
             retainedV3ApiEvidence=[row for row in old['verifiedLedger'] if row['scope'] == 'api'],
             files=[dict(path=name, sha256=digest(root / name), bytes=(root / name).stat().st_size)
                    for name in files],
             limits=['Only the selected complete Monkey and service source-parent sequences were rerun on v4.',
                     'The separate API corpus retains its executed v3 identity. It is not relabelled as a v4 execution.',
                     'Cold counts are included in parent counts. Sound requests are not audible delivery proof.',
                     'Complete Escargo courier arrival, departure and delivery transactions remain unqualified.'])
    a.output.write_text(json.dumps(r, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(manifestSha256=digest(a.output), files=len(files), parents=258, cold=56)))


if __name__ == '__main__':
    main()
