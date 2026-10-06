# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze exact full-courier green evidence, dependencies and diagnostic limits."""
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
    files = [
        'tools/escargo_courier_qa_dev22.py','tools/escargo_courier_cases_dev22.py',
        'tools/write_escargo_manifest_dev22.py',
        'tools/barter_delivery_qa_dev20.py','tools/shop_transaction_qa_dev18.py',
        'tools/transaction_menu_replay_dev20.py','tools/battle_action_catalog_qa.py',
        'tools/build_maternalbound_pack.py','research/escargo-courier-dev22-evidence.md',
        'research/inventory-selector-dev22-v4-refresh-manifest.json']
    ledger = []
    for profile in ('original','redux'):
        name = f'research/{profile}-escargo-courier-dev22-v4-final-r2.json'
        fixture = f'research/{profile}-escargo-courier-fixtures-dev22-v4-final-r2.json'
        r = json.loads((root/name).read_text())
        fixtures = json.loads((root/fixture).read_text())
        rows = r['cases']
        cold = sum(bool(c['fixture'].get('checkpoint')) for c in rows)
        failures = sum(c['fixture']['worldFixture'].get('expectedInteractionType',8)==10 for c in rows)
        if not r['allPassed'] or len(rows)!=36 or cold!=9 or failures!=2:
            raise ValueError('Incomplete full source-parent corpus: '+name)
        if [c['fixture'] for c in rows]!=fixtures:
            raise ValueError('Fixture report differs: '+name)
        for c in rows:
            if c['errors'] or not c['passed'] or c['nativeExit']:
                raise ValueError('Unexpected retained failure: '+c['fixture']['id'])
            expected_stages=['capture','resume'] if c['fixture'].get('checkpoint') else ['warm']
            if [s['stage'] for s in c['stages']]!=expected_stages or any(s['exit'] for s in c['stages']):
                raise ValueError('Unqualified real continuation: '+c['fixture']['id'])
        ledger.append(dict(profile=profile,report=name,fixtures=fixture,
            selectedParentSequences=36,naturalCourierArrivalVisitDeparture=34,
            naturalRouteFailureRefund=2,coldContinuationsIncluded=9,
            assetsSha256=r['assetsSha256'],runtimeSha256=r['runtimeSha256'],
            privateBuild=r['privateBuild'],sourceReferences=r['executedSourceReferences']))
        files.extend([name,fixture])
    runtime=ledger[0]['runtimeSha256']
    if any(row['runtimeSha256']!=runtime for row in ledger):
        raise ValueError('Mixed runtime identities')
    text=(root/'research/escargo-courier-dev22-evidence.md').read_text()
    for value in (*runtime.values(),*(row['assetsSha256'] for row in ledger),
                  ledger[0]['privateBuild']['productionLibrarySha256']):
        if value not in text:
            raise ValueError('Evidence prose omits exact execution identity: '+value)
    source=root/'_BuildScratch/audit-dev17-v4-complete-source'
    project=root/'_BuildScratch/MaternalBound-Redux/Project'
    source_proof=[dict(path=str(path.relative_to(source)).replace('\\','/'),sha256=digest(path))
        for path in (source/'asm/misc/give_item_to_specific_character.asm',
                     source/'asm/misc/remove_item_from_inventory.asm',
                     source/'src/entity/callroutine_movement.c',
                     source/'src/entity/opcodes.c',source/'src/game_main.c') if path.is_file()]
    pinned_proof=[dict(path=path,sha256=digest(project/path)) for path in
        ('npc_config_table.yml','map_sprites.yml','map_doors.yml','timed_delivery_table.yml',
         'ccscript/data/data_19.ccs','ccscript/data/data_22.ccs','ccscript/data/data_36.ccs')]
    diagnostics=[]
    for profile in ('original','redux'):
        for suffix in ('v4','v4-final'):
            name=f'research/{profile}-escargo-courier-dev22-{suffix}.json'
            r=json.loads((root/name).read_text())
            diagnostics.append(dict(path=name,sha256=digest(root/name),
                selectedCases=len(r['cases']),failedExpectedCases=[
                    dict(id=c['fixture']['id'],errors=c['errors']) for c in r['cases'] if not c['passed']],
                status='Pre-entry QoL classification or source refund ordering expectation; no production defect established.'))
            files.append(name)
    report=dict(schemaVersion=1,toolVersion='dev22-full-escargo-parent-freeze',
        frozenRuntime='dev17-v4',reduxRevision='897d00833f4a08a0a92f106abf631629a6a6a041',
        sourceParentSequences=72,coldContinuationsIncluded=18,
        naturalCourierArrivalVisitDeparture=68,naturalRouteFailureRefund=4,
        nativeProductionChanged=False,verifiedLedger=ledger,
        sourceProof=source_proof,pinnedProof=pinned_proof,
        preservedDiagnostics=diagnostics,
        previousTransactionManifest=dict(path=files[9],sha256=digest(root/files[9]),
            historicalEscargoLimitSupersededOnlyBySelectedNewCorpus=True),
        files=[dict(path=name,sha256=digest(root/name),bytes=(root/name).stat().st_size)
               for name in files],
        limits=[
            'Cold counts are included in parent counts. Source-parent counts are selected cases, not product-feature counts or all-route coverage.',
            'Original controls use Original packed scripts with the native shared key-pool QoL retained; they are not an untouched SNES behavior proof.',
            'Real QCT starts at QCT_TEXT after a source-derived pre-entry world fixture. All subsequent phone/door/courier/transaction/departure dispatch and platform input run normally.',
            'Private library-linked driver executes these cases; observer identity is recorded but not separately executed.',
            'Runtime reports prove native numeric state, source-selected outcomes and actual SFX requests. No full playthrough, all service/route, render or audible-delivery claim.',
            'Readonly courier timer fields refer to delivery table index1; do not infer pickup-index2 timer assertions from them.',
            'Diagnostic expectation failures are not red evidence for a native defect. Earlier missing NPC/input prerequisites are private pilot diagnostics, not full courier failures.'])
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(manifestSha256=digest(a.output),files=len(files),parents=72,cold=18)))


if __name__=='__main__':
    main()
