# SPDX-License-Identifier: GPL-3.0-or-later
"""Reconcile bounded semantic evidence against the actual packed Redux catalog.

Coverage is callback membership with selected semantic branches, not a
conversion percentage. Input reports keep their own exact executed identities.
"""
import argparse
import collections
import json
from pathlib import Path
import re
import struct

from battle_action_catalog_qa import PIN, digest
from build_maternalbound_pack import read_pack


REPORTS = (
    ('research/redux-battle-action-coverage.json',
     'Prepared callbacks, selected elemental/status/recovery/shield/absorption branches; separate enemy initialization and real reward exit cases do not add active callbacks.'),
    ('research/redux-battle-action-coverage-dev15.json',
     'Prepared progression/item/status/stat callbacks; report entryPc boundaries distinguish staged prayers1–7 damage from complete cinematic entry.'),
    ('research/redux-battle-food-summon-coverage-dev15-v5.json',
     'Actual BS_ENTER group constructor and art/layout precede one comfortably fitting summon; selected group rows, seeded success/failure and cleared/bound transient entry pointers.'),
    ('research/redux-battle-food-coverage-dev15-v5.json',
     'Prepared food effects and exact condiment/removal rules; selected production description-to-consumption continuations stop before later status/turn handling.'),
    ('research/redux-battle-offense-up-dev15-v5.json',
     'Prepared Offense Up callback with ordinary/repeated/high-word states, NPC controls and independent clean/pinned machine arithmetic comparison.'),
    ('research/redux-battle-damage-coverage-dev16.json',
     'Prepared nonlethal Rockin/Starstorm callbacks with shields, dodge/status/guard, boss immunity and Giygas2 HP redirection; outer multi-target traversal and complete turns unevaluated.'),
)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets',type=Path,required=True)
    parser.add_argument('--native-source',type=Path,required=True)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    _,_,assets=read_pack(args.assets,args.native_source/'src/data/runtime_generated/asset_ids.h')
    data=assets['data/battle_action_table.bin']
    records=[struct.unpack('<BBBBII',data[p:p+12]) for p in range(0,len(data),12)]
    active={r[5] for r in records};pack_hash=digest(args.assets)
    source=args.native_source/'src/game/battle_actions.c'
    handlers={int(a,16):step if step!='NULL' else pure for a,pure,step in
        re.findall(r'\{ 0x([0-9A-F]+), (\w+), (\w+) \}',source.read_text())}
    handlers.update({int(a,16):pure for a,pure in
        re.findall(r'\{ 0x([0-9A-F]+), \(void\(\*\)\(void\)\)(\w+), NULL \}',source.read_text())})
    mapping=collections.defaultdict(list);report_index=[];noncatalog=[]
    for path,scope in REPORTS:
        file=args.root/path;report=json.loads(file.read_text())
        if report.get('reduxRevision')!=PIN or report.get('assetsSha256')!=pack_hash:
            raise ValueError('Evidence does not match pinned packed catalog: '+path)
        if not report.get('allPassed') or any(not row.get('passed') for row in report['cases']):
            raise ValueError('Evidence has failures/incomplete execution: '+path)
        grouped=collections.defaultdict(list)
        for row in report['cases']:
            function=row.get('function') or report.get('function')
            if function is None:continue
            callback=int(function,16)
            if callback in active:grouped[callback].append(row)
            else:noncatalog.append({'report':path,'function':function})
        report_index.append({'path':path,'sha256':digest(file),
            'runtimeSha256':report['runtimeSha256'],
            'executedPlayerLibrarySha256':report['privateBuild']['productionLibrarySha256'],
            'privateDriverSourceSha256':report['privateBuild']['driverSourceSha256'],
            'recordedCases':len(report['cases']),'activeCallbacksWithSelectedCases':len(grouped),
            'scope':scope,'limits':report.get('limits',[])})
        for callback,rows in grouped.items():
            evidence={'report':path,'selectedPassedCases':len(rows),'scope':scope}
            categories=collections.Counter(row['category'] for row in rows if 'category' in row)
            if categories:evidence['categories']=dict(categories)
            pcs=collections.Counter(str(row['entryPc']) for row in rows if 'entryPc' in row)
            if pcs:evidence['entryPcCases']=dict(pcs)
            routes=collections.Counter(row['route'] for row in rows if 'route' in row)
            if routes:evidence['routes']=dict(routes)
            groups=sorted({row['group'] for row in rows if 'group' in row})
            if groups:evidence['selectedGroups']=groups
            profiles=collections.Counter(row['profile']['name'] for row in rows if 'profile' in row)
            if profiles:evidence['profileCases']=dict(profiles)
            mapping[callback].append(evidence)
    def catalog_row(callback):
        return {'function':f'{callback:06X}','nativeHandler':handlers.get(callback,'unmapped current source'),
            'catalogActionIds':[i for i,row in enumerate(records) if row[5]==callback]}
    covered=[dict(catalog_row(f),evidence=mapping[f]) for f in sorted(mapping)]
    remaining=[catalog_row(f) for f in sorted(active-set(mapping))]
    result={'schemaVersion':1,'tool':'battle-semantic-coverage-ledger','reduxRevision':PIN,
        'assetsSha256':pack_hash,'packedBattleActionTableSha256':__import__('hashlib').sha256(data).hexdigest(),
        'catalogSource':'Owner-extracted pinned Redux assets; packed table membership is inventory, not semantic proof.',
        'nativeDispatchReviewSha256':digest(source),'nativeDispatchReviewRole':'Names from current review source; reports retain immutable executed library identities.',
        'packedActionRecords':len(records),'uniqueActiveCallbacks':len(active),
        'callbacksWithSelectedSemanticEvidence':len(covered),'callbacksWithoutSelectedSemanticEvidence':len(remaining),
        'covered':covered,'remaining':remaining,'reports':report_index,
        'noncatalogSemanticCallbacks':sorted({(r['report'],r['function']) for r in noncatalog}),
        'reproductionFlags':{'assets':str(args.assets),'native-source':str(args.native_source),'root':str(args.root),'output':str(args.output)},
        'limits':['Each listed callback has selected semantic cases only; all branches, all action-row variants and complete game behavior are not certified.',
            'Repeated/overlapping report cases are listed per callback and never added into a conversion percentage or a deduplicated total.',
            'Reports span exact dev14 v5, dev15 v3 and dev15 v5 libraries; older execution is never relabeled as current-release verification.',
            'Cold consumer, source hook inventories, UI/audio, collision and helper machine corpora are separate evidence and do not automatically add active callback coverage.',
            'No complete story/randomizer seed, full encounter AI/initiative or physical input/pixel/audio proof follows from this ledger.',
            'No owner ROM, extracted bytes, dialogue or save payload appears in the ledger.'],
        'fullConversionVerified':False,'fullPlaythroughVerified':False}
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('packedActionRecords','uniqueActiveCallbacks',
        'callbacksWithSelectedSemanticEvidence','callbacksWithoutSelectedSemanticEvidence')}))


if __name__=='__main__':main()
