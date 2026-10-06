# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze complete selected Goods/equipment proof with faithful source oddities."""
import argparse
import hashlib
import json
from pathlib import Path
from goods_equipment_cases_dev25 import generate
from goods_equipment_qa_dev25 import driver_source


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();root=a.root
    files=['tools/goods_equipment_qa_dev25.py','tools/goods_equipment_cases_dev25.py','tools/goods_equipment_source_review_dev25.py','tools/write_goods_equipment_manifest_dev25.py',
           'tools/overworld_use_qa_dev24.py','tools/overworld_use_source_review_dev24.py','tools/barter_delivery_qa_dev20.py','tools/shop_transaction_qa_dev18.py',
           'tools/transaction_menu_replay_dev20.py','tools/battle_action_catalog_qa.py','tools/build_maternalbound_pack.py','tools/maternalbound_dialogue.py',
           'research/goods-equipment-dev25-evidence.md','research/goods-equipment-source-contracts-dev25.json']
    ledger=[]
    for profile,assets in [('original',root/'EarthBound Companion/Game/assets.pak'),('redux',root/'_BuildScratch/art-decode-dev20-final-fixed-redux.pak')]:
        path=f'research/{profile}-goods-equipment-dev25-v4-final.json';fixture=f'research/{profile}-goods-equipment-fixtures-dev25-v4-final.json'
        report=json.loads((root/path).read_text());f=json.loads((root/fixture).read_text());rows=report['cases']
        if not report['allPassed']or len(rows)!=71 or sum(bool(r['fixture']['checkpoint'])for r in rows)!=15:raise ValueError('Strict parent corpus incomplete')
        if f!=[r['fixture']for r in rows]or f!=generate(root,assets,profile=='original'):raise ValueError('Fixture generator/report drift')
        driver_sha=hashlib.sha256(driver_source(profile=='original').replace('\n','\r\n').encode()).hexdigest()
        if driver_sha!=report['privateBuild']['driverSourceSha256']:raise ValueError('Executed driver byte identity drift')
        for row in rows:
            expected=['capture','resume']if row['fixture']['checkpoint']else['warm']
            if row['errors']or not row['passed']or row['nativeExit']or[s['stage']for s in row['stages']]!=expected or any(s['exit']for s in row['stages']):raise ValueError('Failed native stage')
        for field in ('warmColdComparisons','warmColdGearComparisons'):
            if len(report[field])!=15 or not all(p['passed']for p in report[field]):raise ValueError('Continuation comparison incomplete')
        oddities=[row['fixture']['id']for row in rows if row['fixture'].get('sourceOddity')]
        if len(oddities)!=4:raise ValueError('Source oddities not explicitly represented')
        ledger.append(dict(profile=profile,report=path,fixtures=fixture,fullParents=71,coldContinuationsIncluded=15,warmColdComparisons=15,
                           sourceOddityCaseIDs=oddities,assetsSha256=report['assetsSha256'],runtimeSha256=report['runtimeSha256'],
                           privateBuild=report['privateBuild'],executedSourceReferences=report['executedSourceReferences']))
        files.extend([path,fixture])
    contract=json.loads((root/files[13]).read_text())
    if not contract['allPassed']or len(contract['checks'])!=77 or any(not c['passed']for c in contract['checks'])or contract['toolSha256']!=sha(root/files[2]):raise ValueError('Source review drift')
    if ledger[0]['runtimeSha256']!=ledger[1]['runtimeSha256']:raise ValueError('Mixed runtime identities')
    text=(root/files[12]).read_text()
    for value in (*ledger[0]['runtimeSha256'].values(),*(r['assetsSha256']for r in ledger),ledger[0]['privateBuild']['productionLibrarySha256']):
        if value not in text:raise ValueError('Evidence prose missing identity')
    result=dict(schemaVersion=1,toolVersion='dev25-selected-full-goods-equipment-freeze',frozenRuntime='dev17-v4',
                pinnedReduxCommit='897d00833f4a08a0a92f106abf631629a6a6a041',fullPauseParents=142,coldContinuationsIncluded=30,warmColdComparisons=30,
                independentSourceChecks=77,sourceOddityExecutionsIncluded=8,nativeProductionChanged=False,verifiedLedger=ledger,
                sourceContractReport=dict(path=files[13],sha256=sha(root/files[13])),
                files=[dict(path=p,sha256=sha(root/p),bytes=(root/p).stat().st_size)for p in files],
                limits=['Prepared actual complete pause parents; production menus/children/text/input, no post-entry outcome injection or natural reachability claim.',
                        'Selected callbacks and gear IDs/ordinary stats only; no complete conversion/family percentage. Cold and oddity counts are included in parent totals.',
                        'Source-faithful equipment-location/stale-stat oddities are explicit unresolved behaviors, not desired-correctness or native mismatch claims.',
                        'No original CPU execution, copyrighted payload, observer execution, delivered pixel/audio or full playthrough claim. Existing proofs and shared source/build remain unchanged.'])
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(manifestSha256=sha(a.output),files=len(files),parents=142,cold=30,comparisons=30,sourceChecks=77,sourceOdditiesIncluded=8)))


if __name__=='__main__':main()
