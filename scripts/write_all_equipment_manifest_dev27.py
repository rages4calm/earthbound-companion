# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze strict equipment source, real consumer and complete parent evidence."""
import argparse
import hashlib
import json
from pathlib import Path
from all_equipment_cases_dev27 import generate
from all_equipment_qa_dev27 import driver_source
from battle_equipment_qa_dev16 import driver_source as consumer_source


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();root=a.root;files=['tools/all_equipment_qa_dev27.py','tools/all_equipment_cases_dev27.py','tools/all_equipment_source_dev27.py',
        'tools/equipment_private_build_dev27.py','tools/write_all_equipment_manifest_dev27.py','tools/goods_equipment_qa_dev25.py','tools/goods_equipment_cases_dev25.py',
        'tools/goods_equipment_source_review_dev25.py','tools/overworld_use_qa_dev24.py','tools/overworld_use_source_review_dev24.py','tools/barter_delivery_qa_dev20.py',
        'tools/shop_transaction_qa_dev18.py','tools/transaction_menu_replay_dev20.py','tools/battle_action_catalog_qa.py','tools/battle_action_catalog_qa_dev15.py',
        'tools/battle_equipment_qa_dev16.py','tools/build_maternalbound_pack.py','tools/maternalbound_dialogue.py',
        'research/all-equipment-source-contracts-dev27-final.json','research/all-equipment-dev27-evidence.md']
    source=json.loads((root/files[18]).read_text());ledger=[]
    if not source['allPassed']or len(source['checks'])!=279 or not all(c['passed']for c in source['checks']):raise ValueError('Source contract review incomplete')
    for profile,assets in [('original',root/'EarthBound Companion/Game/assets.pak'),('redux',root/'_BuildScratch/swirl-import-dev18-candidate3/map-gas-teleport-swirl-candidate.pak')]:
        report=f'research/{profile}-all-equipment-parents-dev27-final2.json';fixture=f'research/{profile}-all-equipment-fixtures-dev27-final2.json';compact=f'research/{profile}-all-equipment-consumers-dev27-final.json'
        r=json.loads((root/report).read_text());f=json.loads((root/fixture).read_text());c=json.loads((root/compact).read_text());rows=r['cases']
        if not r['allPassed']or len(rows)!=372 or r['coldContinuationsIncluded']!=16:raise ValueError('Complete parent corpus incomplete')
        if f!=[x['fixture']for x in rows]or f!=generate(root,assets,profile=='original'):raise ValueError('Final fixture generator drift')
        expected_sha=hashlib.sha256(driver_source(profile=='original').replace('\n','\r\n').encode()).hexdigest()
        if r['privateBuild']['driverSourceSha256']!=expected_sha:raise ValueError('Executed parent driver drift')
        for row in rows:
            expected=['capture','resume']if row['fixture']['checkpoint']else['warm']
            if row['nativeExit']or row['errors']or not row['passed']or not row['equippedItemIdentity']['passed']or[s['stage']for s in row['stages']]!=expected or any(s['exit']for s in row['stages']):raise ValueError('Failed parent/stage/postcondition')
        for key in('warmColdComparisons','warmColdGearComparisons'):
            if len(r[key])!=16 or not all(x['passed']for x in r[key]):raise ValueError('Cold comparison incomplete')
        if not c['allPassed']or c['nativeExitCode']or len(c['cases'])!=1360 or c['semanticCoverage']['completedCases']!=1360 or any(not x['passed']or x['errors']for x in c['cases']):raise ValueError('Compact production consumer incomplete')
        expected_sha=hashlib.sha256(consumer_source(profile=='original').replace('\n','\r\n').encode()).hexdigest()
        if c['privateBuild']['driverSourceSha256']!=expected_sha:raise ValueError('Executed consumer driver drift')
        for key in('runtimeSha256','assetsSha256','packedEquipmentInventory'):
            if r[key]!=c[key]:raise ValueError('Mixed source/runtime/pack enumeration')
        for result in(r,c):
            if result['privateBuild']['sharedSourceModified']or result['privateBuild']['sharedBuildModified']:raise ValueError('Nonprivate build')
        inventory=r['packedEquipmentInventory']
        if inventory['equipmentItems']!=85 or inventory['eligibleItemPCPairs']!=202 or inventory['excludedItemPCPairs']!=138:raise ValueError('Packed coverage inventory changed')
        if source['inventories'][profile]['equipmentItemIDs']!=inventory['equipmentItemIDs']:raise ValueError('Source inventory mismatch')
        ledger.append(dict(profile=profile,parentReport=report,fixtures=fixture,compactConsumerReport=compact,completeParents=372,coldIncluded=16,warmColdComparisons=16,
                           compactConsumers=1360,packedEquipmentInventory=inventory,runtimeSha256=r['runtimeSha256'],assetsSha256=r['assetsSha256'],
                           parentPrivateBuild=r['privateBuild'],consumerPrivateBuild=c['privateBuild']))
        files.extend([report,fixture,compact])
    text=(root/files[19]).read_text()
    for value in(*ledger[0]['runtimeSha256'].values(),*(x['assetsSha256']for x in ledger),ledger[0]['parentPrivateBuild']['productionLibrarySha256']):
        if value not in text:raise ValueError('Missing evidence identity')
    result=dict(schemaVersion=1,toolVersion='dev27-all-packed-equipment-freeze',baseRuntime='dev18-v2',completeParents=744,coldContinuationsIncluded=32,warmColdComparisons=32,
                compactConsumerExecutions=2720,sourceChecks=279,productionModified=False,ownerSaveModified=False,dev26IntentionalGivePatchIntegrated=False,verifiedLedger=ledger,
                files=[dict(path=f,sha256=sha(root/f),bytes=(root/f).stat().st_size)for f in files],
                limits=['All actual packed equipment IDs/PC eligibility pairs, selected normal-range consumer and complete Equip parent semantics. Packed membership is not natural story availability.',
                        'Cold executions are included in parent totals. Compact callbacks overlap previous coverage; counts are not a completion percentage.',
                        'Prepared source prerequisites and actual production dispatcher/platform input/serialization; no substituted post-entry outcomes. No original CPU/full-conversion/full-playthrough/pixels/audio/controller claim.'])
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(manifestSha256=sha(a.output),files=len(files),parents=744,cold=32,compactConsumers=2720,sourceChecks=279)))


if __name__=='__main__':main()
