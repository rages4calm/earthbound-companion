# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze selected inventory-selector checkpoint files and exact proof counts."""
import argparse, hashlib, json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    files = [
        'tools/barter_delivery_qa_dev20.py', 'tools/barter_delivery_cases_dev20.py',
        'tools/transaction_menu_replay_dev20.py', 'tools/menu_geometry_full_bag_red_dev20.py',
        'tools/service_transaction_qa_dev21.py', 'tools/service_transaction_cases_dev21.py',
        'tools/key_pool_selection_qa_dev21.py', 'tools/snes_inventory_slot_oracle_dev20.py',
        'tools/catalog_inventory_selection_callers_dev21.py',
        'tools/write_inventory_selector_manifest_dev21.py',
        'tools/shop_transaction_qa_dev18.py', 'tools/battle_action_catalog_qa.py',
        'tools/build_maternalbound_pack.py', 'tools/check_jev_observer_parity.py',
        'tools/snes_position_arithmetic_oracle.py', 'tools/snes_movement_helpers_oracle.py',
        'research/barter-selector-dev20-v9-red-manifest.json',
        'research/barter-selector-dev20-v1-red-manifest.json',
        'research/original-inventory-slot-machine-dev20.json',
        'research/inventory-selector-source-catalog-dev21.json',
        'research/inventory-selector-finalpack-comparison-dev21.json',
        'research/inventory-selector-dev21-evidence.md',
    ]
    for profile in ('redux', 'original'):
        files += [f'research/{profile}-monkey-barter-fixtures-dev20-final.json',
                  f'research/{profile}-service-selector-fixtures-dev21.json']
    ledger = []
    for profile in ('redux', 'original'):
        suffix = '-finalpack' if profile == 'redux' else ''
        for kind, tool, expected, cold in (
            ('monkey', 'monkey-barter-dev20', 101, 16),
            ('services', 'service-selector-dev21', 28, 12),
            ('api', 'key-selector-dev21', 16475 if profile == 'redux' else 16479, 0)):
            relative = f'research/{profile}-{tool}-v3{suffix}.json'
            report = json.loads((a.root / relative).read_text())
            actual_cold = sum(bool(r.get('fixture', {}).get('checkpoint')) for r in report['cases'])
            if not report['allPassed'] or len(report['cases']) != expected or actual_cold != cold:
                raise ValueError('Final strict report is incomplete: ' + relative)
            ledger.append(dict(profile=profile, scope=kind, report=relative, selectedCases=expected,
                               coldContinuationsIncluded=cold, runtimeSha256=report['runtimeSha256'],
                               librarySha256=report['privateBuild']['productionLibrarySha256'],
                               assetsSha256=report['assetsSha256']))
            files.append(relative)
    # Bind the older pack refresh separately without relabelling it as final.
    files += ['research/redux-monkey-barter-dev20-v3.json',
              'research/redux-service-selector-dev21-v3.json',
              'research/redux-key-selector-dev21-v3.json']
    for nested in ('research/barter-selector-dev20-v9-red-manifest.json',
                   'research/barter-selector-dev20-v1-red-manifest.json'):
        for item in json.loads((a.root / nested).read_text())['files']:
            if sha(a.root / item['path']) != item['sha256']:
                raise ValueError('Frozen red dependency changed: ' + item['path'])
            if item['path'] not in files:
                files.append(item['path'])
    report = dict(schemaVersion=1, toolVersion='dev21-inventory-selector-checkpoint-manifest',
                  frozenRuntime='dev17-v3', verifiedLedger=ledger,
                  selectedParentSequences=258, coldContinuationsIncluded=56,
                  boundedApiObservationsSeparateAndOverlapping=32954,
                  originalMachineSlotCasesSeparate=420,
                  files=[dict(path=f, sha256=sha(a.root / f), bytes=(a.root / f).stat().st_size) for f in files],
                  limits=['Exact selected sequence/API proof, not every inventory consumer or branch.',
                          'Cold counts are included in parent counts. API rows overlap semantic behaviors and are not additional complete transactions.',
                          'Escargo arrival/exit delivery parent remains an unqualified fixture prerequisite gap, not a reported native defect.'])
    a.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(files=len(files), manifestSha256=sha(a.output), parentSequences=258, cold=56)))


if __name__ == '__main__':
    main()
