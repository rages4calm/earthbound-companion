# SPDX-License-Identifier: GPL-3.0-or-later
"""Private-only intentional equipped Give correction, using complete real parents."""
import json
from pathlib import Path
import sys
import goods_equipment_qa_dev25 as gear
import equipped_give_private_build_dev26 as build


def main():
    private_source=None
    if '--private-inventory-source'in sys.argv:
        i=sys.argv.index('--private-inventory-source');private_source=Path(sys.argv[i+1]);del sys.argv[i:i+2]
        build.candidate_source=private_source;gear.base.helper.private_build=build.private_build
    output=Path(sys.argv[sys.argv.index('--output')+1]);failure=0
    try:gear.main()
    except SystemExit as e:
        if e.code not in(0,1):raise
        failure=e.code
    r=json.loads(output.read_text())
    for row in r['cases']:
        final=[e['actual']for e in row['events']if e['type']=='QA_GEAR'and e['actual']['stage']=='after-entry'][-1]
        inv=[e['actual']['inventory']for e in row['events']if e['type']=='QA_SNAP'and e['actual']['stage']=='after-entry'][-1]
        actual=[[inv[pc][slot-1]if 1<=slot<=14 else 0 for slot in final['party'][pc]['equipment']]for pc in range(4)]
        want=row['fixture']['expectedEquipmentItemIDs'];row['equippedItemIdentity']=dict(actual=actual,expected=want,passed=actual==want)
        if actual!=want:row['errors'].append('Actual equipped item identities differ after complete transaction')
        row['passed']=not row['errors']
    if private_source:
        # All other native references are the immutable executed snapshot;
        # inventory.c is explicitly the single private compiled replacement.
        for ref in r['executedSourceReferences']:
            if ref['path']=='src/game/inventory.c':ref.update(path=str(private_source.resolve()),sha256=gear.base.helper.digest(private_source),privateReplacement=True)
    r.update(toolVersion='dev26-private-intentional-equipped-give-qol',intentionalSourceBugCorrection=True,privateCorrectedInventory=bool(private_source),
             limits=['Selected actual complete Goods/Equip parents on copied frozen library, optionally replacing only the reviewed inventory.c object privately. Input and production child/menu/serialization implementations remain real. No shared source/build or owner save changes.',
                     'Intentional Original-source bug correction: actual equipped item identity and independently derived final effective stats/miss/resistances. Frozen dev25 preserves source-faithful oddities; this result does not relabel missing Redux or original parity.',
                     'Prepared normal contiguous bag fixtures; no natural NPC/controller/story reachability, every item/stat/malformed save, observer execution, delivered pixels/audio or full playthrough proof.'])
    r['allPassed']=not failure and all(row['passed']for row in r['cases']);output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(cases=len(r['cases']),passed=sum(row['passed']for row in r['cases']),failures=[dict(id=row['fixture']['id'],errors=row['errors'])for row in r['cases']if not row['passed']][:12])))
    if not r['allPassed']and '--diagnostic'not in sys.argv:raise SystemExit(1)


if __name__=='__main__':main()
