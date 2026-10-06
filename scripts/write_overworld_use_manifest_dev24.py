# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze source-selected full pause-menu effects with exact immutable identity."""
import argparse
import hashlib
import json
from pathlib import Path
from overworld_use_cases_dev24 import generate
from overworld_use_qa_dev24 import driver_source


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();root=a.root
    files=['tools/overworld_use_qa_dev24.py','tools/overworld_use_cases_dev24.py','tools/overworld_use_source_review_dev24.py','tools/write_overworld_use_manifest_dev24.py',
           'tools/barter_delivery_qa_dev20.py','tools/shop_transaction_qa_dev18.py','tools/transaction_menu_replay_dev20.py','tools/battle_action_catalog_qa.py',
           'tools/build_maternalbound_pack.py','tools/maternalbound_dialogue.py','research/overworld-use-dev24-evidence.md','research/overworld-use-source-contracts-dev24.json']
    ledger=[]
    for profile,assets in [('original',root/'EarthBound Companion/Game/assets.pak'),('redux',root/'_BuildScratch/art-decode-dev20-final-fixed-redux.pak')]:
        path=f'research/{profile}-overworld-use-dev24-v4-final.json';fixture=f'research/{profile}-overworld-use-fixtures-dev24-v4-final.json'
        report=json.loads((root/path).read_text());f=json.loads((root/fixture).read_text());rows=report['cases']
        if not report['allPassed'] or len(rows)!=155 or sum(bool(r['fixture']['checkpoint'])for r in rows)!=12:raise ValueError('Strict full-parent corpus incomplete')
        if f!=[r['fixture']for r in rows] or f!=generate(root,assets,profile=='original'):raise ValueError('Fixture generator/report drift')
        # private_build.write_text used Windows newline translation; compare
        # exact executed bytes, not a UTF-8/LF normalization of the C string.
        driver_sha=hashlib.sha256(driver_source(profile=='original').replace('\n','\r\n').encode()).hexdigest()
        if driver_sha!=report['privateBuild']['driverSourceSha256']:raise ValueError('Executed private driver drift')
        for r in rows:
            expected=['capture','resume']if r['fixture']['checkpoint']else['warm']
            if r['errors'] or not r['passed'] or r['nativeExit'] or [s['stage']for s in r['stages']]!=expected or any(s['exit']for s in r['stages']):raise ValueError('Failed native stage')
        parity=report['warmColdComparisons']
        if len(parity)!=9 or not all(p['passed']for p in parity):raise ValueError('Continuation comparison incomplete')
        gamma={kind:{'success':sum(r['sourceGammaExpectation']['randomByte']<192 for r in rows if r['fixture']['id'].startswith('gamma-revive-'+kind)),
                     'failure':sum(r['sourceGammaExpectation']['randomByte']>=192 for r in rows if r['fixture']['id'].startswith('gamma-revive-'+kind))}for kind in ('item','psi')}
        if any(v['success']==0 or v['failure']==0 or sum(v.values())!=24 for v in gamma.values()):raise ValueError('Both source probability branches not exercised')
        ledger.append(dict(profile=profile,report=path,fixtures=fixture,selectedFullPauseParents=155,coldContinuationsIncluded=12,warmColdComparisons=9,
                           gammaRevivalOutcomes=gamma,assetsSha256=report['assetsSha256'],runtimeSha256=report['runtimeSha256'],privateBuild=report['privateBuild'],executedSourceReferences=report['executedSourceReferences']))
        files.extend([path,fixture])
    contract=json.loads((root/files[11]).read_text())
    if not contract['allPassed'] or len(contract['checks'])!=69 or any(not c['passed']for c in contract['checks']) or contract['toolSha256']!=sha(root/files[2]):raise ValueError('Source contract evidence drift')
    if ledger[0]['runtimeSha256']!=ledger[1]['runtimeSha256']:raise ValueError('Mixed runtime identities')
    text=(root/files[10]).read_text()
    for value in (*ledger[0]['runtimeSha256'].values(),*(r['assetsSha256']for r in ledger),ledger[0]['privateBuild']['productionLibrarySha256']):
        if value not in text:raise ValueError('Prose identity missing')
    result=dict(schemaVersion=1,toolVersion='dev24-complete-selected-overworld-use-freeze',frozenRuntime='dev17-v4',pinnedReduxCommit='897d00833f4a08a0a92f106abf631629a6a6a041',
                selectedFullPauseParents=310,coldContinuationsIncluded=24,warmColdComparisons=18,independentSourceChecks=69,nativeProductionChanged=False,
                verifiedLedger=ledger,sourceContractReport=dict(path=files[11],sha256=sha(root/files[11])),
                files=[dict(path=p,sha256=sha(root/p),bytes=(root/p).stat().st_size)for p in files],
                limits=['Prepared source-prerequisite full pause parents; actual production menus, target/effect children and platform replay input. No post-entry result/state or completion injection; no natural controller/map/story reachability proof.',
                        'Cold counts are included in parent counts; comparisons/checks are separate evidence units. No complete item/PSI family or conversion percentage claim.',
                        'Gamma expected success uses a non-consuming peek of actual serialized RNG and original strict threshold; separate Original ROM/pinned metadata/control-token review is not SNES CPU execution.',
                        'Exact target HP/PP/status and inventory/pool/storage/queue are checked. Frame counters/current roller progress, pixels/audio delivery, observer execution and full playthrough remain unproved.',
                        'Qualified pilot fixture priority, primary-status and nonyielding capture assumptions are documented; no native defect or production change established. Existing frozen reports are unchanged.'])
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(manifestSha256=sha(a.output),files=len(files),parents=310,cold=24,comparisons=18,sourceChecks=69)))


if __name__=='__main__':main()
