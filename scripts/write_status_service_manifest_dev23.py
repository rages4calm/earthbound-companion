# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze exact selected service transactions and independent source checks."""
import argparse
import hashlib
import json
from pathlib import Path

from status_service_cases_dev23 import generate


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    root = a.root
    files = ['tools/status_service_qa_dev23.py', 'tools/status_service_cases_dev23.py',
             'tools/status_service_source_review_dev23.py', 'tools/write_status_service_manifest_dev23.py',
             'tools/barter_delivery_qa_dev20.py', 'tools/shop_transaction_qa_dev18.py',
             'tools/transaction_menu_replay_dev20.py', 'tools/battle_action_catalog_qa.py',
             'tools/build_maternalbound_pack.py', 'tools/maternalbound_dialogue.py',
             'research/status-service-dev23-evidence.md', 'research/status-service-source-contracts-dev23.json']
    ledger = []
    source = root / '_BuildScratch/audit-dev17-v4-complete-source'
    for profile, wanted_cases, wanted_cold in [('original', 133, 27), ('redux', 135, 28)]:
        name = f'research/{profile}-status-services-dev23-v4-final-r2.json'
        fixture = f'research/{profile}-status-service-fixtures-dev23-v4-final-r2.json'
        r = json.loads((root / name).read_text())
        f = json.loads((root / fixture).read_text())
        rows = r['cases']
        cold = sum(bool(c['fixture']['checkpoint']) for c in rows)
        if not r['allPassed'] or len(rows) != wanted_cases or cold != wanted_cold:
            raise ValueError('Incomplete strict corpus ' + name)
        if [c['fixture'] for c in rows] != f or f != generate(root, profile == 'original'):
            raise ValueError('Reported/generator fixture drift ' + name)
        for c in rows:
            stages = ['capture', 'resume'] if c['fixture']['checkpoint'] else ['warm']
            if c['errors'] or not c['passed'] or c['nativeExit'] or [s['stage'] for s in c['stages']] != stages or any(s['exit'] for s in c['stages']):
                raise ValueError('Failed native continuation ' + c['fixture']['id'])
        families = {prefix: sum(c['fixture']['id'].startswith(prefix + '-') for c in rows)
                    for prefix in ('atm', 'doctor', 'nurse', 'healer')}
        ledger.append(dict(profile=profile, report=name, fixtures=fixture,
                           selectedParentTransactions=wanted_cases, coldContinuationsIncluded=cold,
                           selectedByFamily=families, assetsSha256=r['assetsSha256'],
                           runtimeSha256=r['runtimeSha256'], privateBuild=r['privateBuild'],
                           executedSourceReferences=r['executedSourceReferences']))
        files.extend([name, fixture])
    contract = json.loads((root / files[11]).read_text())
    if not contract['allPassed'] or len(contract['checks']) != 144 or any(not c['passed'] for c in contract['checks']):
        raise ValueError('Source contract review incomplete')
    if contract['toolSha256'] != sha(root / files[2]):
        raise ValueError('Source review tool drift')
    runtime = ledger[0]['runtimeSha256']
    if any(row['runtimeSha256'] != runtime for row in ledger):
        raise ValueError('Mixed runtime identity')
    text = (root / files[10]).read_text()
    for value in (*runtime.values(), *(row['assetsSha256'] for row in ledger),
                  ledger[0]['privateBuild']['productionLibrarySha256']):
        if value not in text:
            raise ValueError('Prose execution identity missing')
    extra = ('src/game/display_text.c', 'src/game/text.c', 'src/game/window.h',
             'asm/battle/heal_character_hp.asm', 'asm/battle/heal_character_pp.asm',
             'asm/misc/increase_wallet_balance.asm', 'asm/misc/atm_deposit.asm',
             'asm/text/ccs/test_has_enough_money.asm', 'asm/text/ccs/test_atm_has_enough_money.asm')
    result = dict(schemaVersion=1, toolVersion='dev23-selected-service-freeze',
                  frozenRuntime='dev17-v4', pinnedReduxCommit='897d00833f4a08a0a92f106abf631629a6a6a041',
                  selectedParentTransactions=268, coldContinuationsIncluded=55,
                  independentSourceChecks=144, nativeProductionChanged=False,
                  verifiedLedger=ledger,
                  sourceContractReport=dict(path=files[11], sha256=sha(root / files[11])),
                  additionalExecutedSourceReferences=[dict(path=p, sha256=sha(source / p)) for p in extra],
                  files=[dict(path=p, sha256=sha(root / p), bytes=(root / p).stat().st_size) for p in files],
                  limits=['Cold counts are included in selected parent counts. Source checks, transactions and wrappers are distinct evidence units, not a feature count or complete conversion percentage.',
                          'Prepared real packed text parents and production menu/number/capture/restore dispatch. Initial state is source-prerequisite fixture setup; no post-entry result/register/state or completion injection. No natural NPC lifecycle proof.',
                          'Nurse target HP/PP restoration and awakened nonzero HP are asserted. Final rolling-meter visual settling and outer NPC caller cleanup are not asserted.',
                          'Original packed control scripts retain native key-pool QoL. Original ATM overflow and every item-use ATM caller remain outside this corpus.',
                          'Specified sounds prove play_sfx requests only; observer identity is recorded but not separately executed; no pixels, physical input or audible-delivery proof.',
                          'Initial source alias, window-size and ordinal-capture pilot errors are documented fixture diagnostics, not production defects. Frozen prior transaction evidence is unchanged.'])
    a.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(manifestSha256=sha(a.output), files=len(files), parents=268, cold=55, sourceChecks=144)))


if __name__ == '__main__':
    main()
