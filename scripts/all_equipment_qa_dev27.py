# SPDX-License-Identifier: GPL-3.0-or-later
"""All packed equipment pairs: compact battle consumers or complete Equip parents."""
import json
from pathlib import Path
import sys
import goods_equipment_qa_dev25 as gear
import battle_equipment_qa_dev16 as consumer
import equipment_private_build_dev27 as build
from all_equipment_cases_dev27 import inventory_summary
from build_maternalbound_pack import read_pack

old_driver=gear.driver_source


def driver_source(original):
    source=old_driver(original)
    # Same real replay pulses, bounded file length. Equip menu transactions
    # need only a few hundred input frames between choices, not100000 dumps.
    if 'frame<100000'not in source:raise ValueError('Frozen replay boundary changed')
    return source.replace('frame<100000','frame<8192').replace('verbose_level=2','verbose_level=0')


def main():
    output=Path(sys.argv[sys.argv.index('--output')+1]);assets=Path(sys.argv[sys.argv.index('--assets')+1])
    native=Path(sys.argv[sys.argv.index('--native-source')+1]);executed=Path(sys.argv[sys.argv.index('--executed-source')+1])
    _,_,pack=read_pack(assets,native/'src/data/runtime_generated/asset_ids.h');enumeration=inventory_summary(pack['data/item_configuration_table.bin'])
    compact='--consumer'in sys.argv;failure=0;gear.base.helper.private_build=build.private_build
    if compact:
        sys.argv.remove('--consumer');i=sys.argv.index('--executed-source');del sys.argv[i:i+2]
        if '--pilot'not in sys.argv:sys.argv.append('--pilot') # All item/PC/missing/bonus pairs, one RNG seed each.
        try:consumer.main()
        except SystemExit as e:
            if e.code not in(0,1):raise
            failure=e.code
        r=json.loads(output.read_text());r['compactSingleSeed']=True;r['executedSourceSnapshot']=str(executed)
        r['executedSourceReferences']=r.pop('sourceReferences')
    else:
        gear.driver_source=driver_source
        try:gear.main()
        except SystemExit as e:
            if e.code not in(0,1):raise
            failure=e.code
        r=json.loads(output.read_text())
        for row in r['cases']:
            snapshots=[e['actual']for e in row['events']if e['type']=='QA_GEAR'and e['actual']['stage']=='after-entry']
            bags=[e['actual']['inventory']for e in row['events']if e['type']=='QA_SNAP'and e['actual']['stage']=='after-entry']
            expected_count=2 if row['fixture']['checkpoint']else 1
            if len(snapshots)!=expected_count or len(bags)!=expected_count:raise ValueError('Incomplete parent final snapshots')
            actual=[[bags[-1][pc][s-1]if 1<=s<=14 else 0 for s in snapshots[-1]['party'][pc]['equipment']]for pc in range(4)]
            wanted=row['fixture']['expectedEquipmentItemIDs'];row['equippedItemIdentity']=dict(actual=actual,expected=wanted,passed=actual==wanted)
            if actual!=wanted:row['errors'].append('Final equipped item identity differs from selected actual bag slot')
            row['passed']=not row['errors']
        r['coldContinuationsIncluded']=sum(bool(row['fixture']['checkpoint'])for row in r['cases'])
    r.update(toolVersion='dev27-all-active-equipment-'+('compact-consumer'if compact else'complete-parent'),packedEquipmentInventory=enumeration,
             limits=(['All packed equipment IDs/four PCs/missing controls/stat bonuses through complete real weapon/armor callbacks and weapon attack child; one serialized RNG seed per combination.',
                      'Independent source formulas cover selected ordinary stat ranges, Poo alternate modifiers, equipment identity, miss rate and resistance coefficients. No whole battle turn/full encounter claim.']if compact else
                     ['Every packed equipment/PC eligibility pair through actual full Equip menu/category/item parent and real platform replay; excluded IDs are checked absent, never forced as a menu result.',
                      'Sixteen full14-slot duplicate-item cases plus sixteen captured production item-menu states restored fresh and compared with warm parents. Final item identity, five stats, miss rate, stored resistances, full inventory, wallet, effects, pool/storage/queue and window closure are asserted.',
                      'Prepared source-prerequisite party/bag/gear; no arbitrary malformed-save/stat-boundary, delivered title/pixel/audio/physical controller or natural map/story reachability proof.'])+
                     ['Only unchanged frozen player library executes; observer hash is provenance. Neither source/pack/owner save nor shared build changes. Private dev26 intentional Give correction is separate and is not integrated.',
                      'Counts are execution/selected branch coverage, not independent full original-machine/full conversion/full playthrough certification.'])
    r['allPassed']=not failure and all(row['passed']for row in r['cases']);output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(cases=len(r['cases']),passed=sum(row['passed']for row in r['cases']),compact=compact,equipmentIDs=enumeration['equipmentItems'])))
    if not r['allPassed']and '--diagnostic'not in sys.argv:raise SystemExit(1)


if __name__=='__main__':main()
