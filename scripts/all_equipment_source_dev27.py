# SPDX-License-Identifier: GPL-3.0-or-later
"""All active equipment numeric rows and selected independent Original/pinned flows."""
import json
from pathlib import Path
import sys
import goods_equipment_source_review_dev25 as review
from all_equipment_cases_dev27 import equipment_ids,inventory_summary
from build_maternalbound_pack import read_pack


def main():
    output=Path(sys.argv[sys.argv.index('--output')+1]);native=Path(sys.argv[sys.argv.index('--native-source')+1])
    packs=[]
    for flag in('--original-assets','--redux-assets'):
        path=Path(sys.argv[sys.argv.index(flag)+1]);_,_,p=read_pack(path,native/'src/data/runtime_generated/asset_ids.h')
        packs.append(p['data/item_configuration_table.bin'])
    review.ITEMS=sorted(set(equipment_ids(packs[0]))|set(equipment_ids(packs[1])))
    review.main();r=json.loads(output.read_text())
    path='asm/text/menu/layout_menu_options.asm';text=(native/path).read_text()
    r['sourceReferences'].append(dict(path=path,sha256=review.sha(native/path)))
    r['checks'].append(dict(id='source-paginated-More-userdata-zero',passed=review.ordered(text,['@OPTIONS_EXHAUSTED:',
        'LOADPTR MENU_OVERFLOW_TEXT','LDX #0','TXA','JSL ADD_MENU_ITEM_FAR','STZ MENU_OPTIONS + menu_option::page,X'])))
    r.update(toolVersion='dev27-all-active-equipment-source',toolSha256=review.sha(__file__),
             sourceReviewDependency=dict(path='tools/goods_equipment_source_review_dev25.py',sha256=review.sha(review.__file__)),
             inventories=dict(original=inventory_summary(packs[0]),redux=inventory_summary(packs[1])),
             limits=['All actual active equipment numeric type/cost/flags/parameters corroborated against clean owner Original ROM and pinned Redux YAML; no game text/ROM payload redistributed.',
                     'Selected ordered Original/pinned flow tokens establish eligibility, category/None/equipment mutation and stat/miss/resistance consumers. This is bounded source/bytecode review, not original SNES CPU execution or exhaustive branch reachability.',
                     'Normal prepared stats avoid Original -1/256 carry-boundary oddities and Redux upper clamps. Intentional dev26 Give correction is separate and unchanged parity source remains held.'])
    r['allPassed']=all(c['passed']for c in r['checks']);output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(checks=len(r['checks']),equipmentIDs=len(review.ITEMS))))
    if not r['allPassed']:raise SystemExit(1)


if __name__=='__main__':main()
