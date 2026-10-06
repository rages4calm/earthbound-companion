# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze private intentional equipment correction, red controls and provenance."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
from equipped_give_cases_dev26 import generate
from goods_equipment_qa_dev25 import driver_source


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();root=a.root
    files=['tools/equipped_give_qa_dev26.py','tools/equipped_give_cases_dev26.py','tools/equipped_give_private_build_dev26.py','tools/prepare_equipped_give_qol_dev26.py','tools/write_equipped_give_manifest_dev26.py',
           'tools/goods_equipment_qa_dev25.py','tools/goods_equipment_cases_dev25.py','tools/overworld_use_qa_dev24.py','tools/barter_delivery_qa_dev20.py',
           'tools/shop_transaction_qa_dev18.py','tools/transaction_menu_replay_dev20.py','tools/battle_action_catalog_qa.py','tools/build_maternalbound_pack.py','tools/maternalbound_dialogue.py',
           'research/equipped-give-qol-dev26-evidence.md','research/goods-equipment-dev25-final-manifest.json','research/goods-equipment-source-contracts-dev25.json']
    ledger=[];baseline_source=root/'_BuildScratch/audit-dev17-v4-complete-source/src/game/inventory.c';candidate=None
    for profile,assets in [('original',root/'EarthBound Companion/Game/assets.pak'),('redux',root/'_BuildScratch/art-decode-dev20-final-fixed-redux.pak')]:
        path=f'research/{profile}-equipped-give-qol-dev26-private-final.json';fixture=f'research/{profile}-equipped-give-fixtures-dev26-private-final.json';red_path=f'research/{profile}-equipped-give-qol-dev26-v4-red.json'
        report=json.loads((root/path).read_text());f=json.loads((root/fixture).read_text());rows=report['cases'];red=json.loads((root/red_path).read_text())
        if not report['allPassed']or len(rows)!=183 or sum(bool(r['fixture']['checkpoint'])for r in rows)!=29:raise ValueError('Strict final corpus incomplete')
        if f!=[r['fixture']for r in rows]or f!=generate(root,assets,profile=='original'):raise ValueError('Fixture generator/report drift')
        driver_sha=hashlib.sha256(driver_source(profile=='original').replace('\n','\r\n').encode()).hexdigest()
        if driver_sha!=report['privateBuild']['driverSourceSha256']:raise ValueError('Executed driver drift')
        for row in rows:
            expected=['capture','resume']if row['fixture']['checkpoint']else['warm']
            if row['errors']or not row['passed']or row['nativeExit']or[s['stage']for s in row['stages']]!=expected or any(s['exit']for s in row['stages'])or not row['equippedItemIdentity']['passed']:raise ValueError('Failed real native stage/postcondition')
        for field in('warmColdComparisons','warmColdGearComparisons'):
            if len(report[field])!=29 or not all(p['passed']for p in report[field]):raise ValueError('Continuation proof incomplete')
        replacement=report['privateBuild']['correctedInventory'];actual=Path(replacement['path'])
        if sha(actual)!=replacement['sha256']or replacement['archiveMemberCount']!=84 or not replacement['otherMembersByteIdentical']:raise ValueError('Private candidate/member identity mismatch')
        if candidate is not None and sha(actual)!=sha(candidate):raise ValueError('Mixed private source candidates')
        candidate=actual
        if red['allPassed']or len(red['cases'])!=6 or sum(row['passed']for row in red['cases'])!=2 or any(row['nativeExit']or any(s['exit']for s in row['stages'])for row in red['cases']):raise ValueError('Expected baseline red controls incomplete')
        ids={row['fixture']['id']for row in red['cases']if not row['passed']}
        if ids!={'give-equipped-type2','give-equipped-type3','source-oddity-self-give-full-equipped-bag','give-equipped-type3-cold'}:raise ValueError('Unexpected red failures')
        ledger.append(dict(profile=profile,report=path,fixtures=fixture,baselineRedReport=red_path,greenParents=183,coldIncluded=29,warmColdComparisons=29,
                           baselineRedParents=6,expectedRedFailures=4,unchangedRedControls=2,runtimeSha256=report['runtimeSha256'],assetsSha256=report['assetsSha256'],privateBuild=report['privateBuild']))
        files.extend([path,fixture,red_path])
    old=baseline_source.read_text().replace('\r\n','\n');new=candidate.read_text().replace('\r\n','\n')
    start='void swap_item_into_equipment(';end='/* TAKE_ITEM_FROM_SPECIFIC_CHARACTER:'
    oi,ni=old.index(start),new.index(start);oe,ne=old.index(end,oi),new.index(end,ni)
    if old[:oi]!=new[:ni]or old[oe:]!=new[ne:]:raise ValueError('Candidate changes outside leased function')
    patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/src/game/inventory.c',tofile='b/src/game/inventory.c'))
    patch_path=root/'research/equipped-give-qol-dev26-candidate.patch';patch_path.write_text(patch,encoding='utf-8')
    provenance=dict(baselineSourceSha256=sha(baseline_source),candidateSourceSha256=sha(candidate),candidatePath=str(candidate),leasedFunction='swap_item_into_equipment',
                    outsideFunctionTextIdentical=True,lineEndingNormalizationOnlyOutsideFunction=True,patchSha256=sha(patch_path),globalFindEmptyHelperUnchanged=True,sharedSourceModified=False)
    provenance_path=root/'research/equipped-give-qol-dev26-provenance.json';provenance_path.write_text(json.dumps(provenance,indent=2)+'\n')
    files.extend(['research/equipped-give-qol-dev26-candidate.patch','research/equipped-give-qol-dev26-provenance.json'])
    text=(root/files[14]).read_text()
    for value in(*ledger[0]['runtimeSha256'].values(),*(r['assetsSha256']for r in ledger),ledger[0]['privateBuild']['productionLibrarySha256'],sha(baseline_source),sha(candidate),ledger[0]['privateBuild']['correctedInventory']['privateLibrarySha256']):
        if value not in text:raise ValueError('Missing prose identity')
    result=dict(schemaVersion=1,toolVersion='dev26-private-intentional-equipped-give-freeze',baseRuntime='dev17-v4',intentionalSourceBugCorrection=True,
                fullParents=366,coldContinuationsIncluded=58,warmColdComparisons=58,baselineRedParents=12,expectedRedFailures=8,unchangedRedControls=4,
                productionChanged=False,sharedBuildChanged=False,ownerSaveChanged=False,verifiedLedger=ledger,candidateProvenance=provenance,
                frozenSourceFaithfulProof=dict(path=files[15],sha256=sha(root/files[15])),
                files=[dict(path=p,sha256=sha(root/p),bytes=(root/p).stat().st_size)for p in files],
                limits=['Private-only intentional Original-source QoL correction. Frozen parity evidence is unchanged; production integration/full-build checks are not yet performed.',
                        'Actual prepared complete parents and production children/menus/platform input/serialization. No post-entry outcome injection or natural reachability claim.',
                        'Cold/comparison counts are included in parent totals. Source review is not original CPU execution; no all-items/stat-boundaries/malformed-save/pixels/audio/observer/full-playthrough claim.'])
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(manifestSha256=sha(a.output),files=len(files),parents=366,cold=58,comparisons=58,baselineRed=12,expectedRedFailures=8)))


if __name__=='__main__':main()
