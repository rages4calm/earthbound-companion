# SPDX-License-Identifier: GPL-3.0-or-later
"""Source-selected complete Goods Give/Drop and equipment transactions."""
import argparse
import copy
import json
from pathlib import Path
from build_maternalbound_pack import read_pack


def generate(root, assets, original=False, pilot=False):
    _, _, pack = read_pack(assets, root / 'native-source/src/data/runtime_generated/asset_ids.h')
    items = pack['data/item_configuration_table.bin']
    cases = []

    def bag(*ids):
        return list(ids) + [0] * (14 - len(ids))

    def stats(inv, eq, pc):
        # Original CALC_RESISTANCES and RECALC_CHARACTER_POSTMATH_* contracts.
        # Selected ordinary totals stay within both profiles' clamp ranges.
        row = lambda slot: items[inv[eq[slot]-1]*39:(inv[eq[slot]-1]+1)*39] if eq[slot] else bytes(39)
        signed = lambda byte: byte - 256 if byte & 128 else byte
        gear = [row(i) for i in range(4)]
        strength = 32 if pc == 3 else 31
        values = [80+signed(gear[0][strength]), 50+sum(signed(g[strength]) for g in gear[1:]),
                  23+signed(gear[1][33]), 12+signed(gear[0][33]), 24+signed(gear[2][33])+signed(gear[3][33])]
        if not all(0 <= v <= 255 for v in values):
            raise ValueError('Fixture falls outside selected ordinary stat range: '+str(values))
        special = [g[34] for g in gear]
        resist = [min(3, ((special[1] >> bit) & 3)+((special[3] >> bit) & 3)) for bit in (0, 2, 4, 6)] + [special[2]]
        return dict(equipment=eq, stats=values, missRate=gear[0][34], resistances=resist)

    def add(id, plan, inv, out=None, eq=None, final_eq=None, statuses=None, checkpoint=0, scope='', party=4):
        eq = copy.deepcopy(eq or [[0]*4 for _ in range(4)])
        final_eq = copy.deepcopy(final_eq if final_eq is not None else eq)
        out = copy.deepcopy(out if out is not None else inv)
        initial_party = [dict(level=1 if i == 0 else 0, hp=100, pp=50, maxHP=100, maxPP=50,
                              status=(statuses or {}).get(i, [0]*7)) for i in range(4)]
        for p in initial_party:
            if p['status'][0] == 1: p['hp'] = 0
        effects = [dict(hpTarget=p['hp'], ppTarget=50, status=p['status']) for p in initial_party]
        case = dict(id=id, entry=0, sourceRoutine='OPEN_MENU', party=party, plan=plan, checkpoint=checkpoint,
                    money=1000, expectedDelta=0, initialParty=initial_party, initialInventory=inv,
                    expectedInventory=out, initialEquipment=eq, expectedInitialGear=[stats(inv[i],eq[i],i) for i in range(4)],
                    expectedGear=[stats(out[i],final_eq[i],i) for i in range(4)], expectedInitialEffect=effects,
                    expectedEffect=effects, expectedActionCount=0,
                    expectedTransfer=dict(storage=[0]*36,queuedItems=[0]*3,queuedSources=[0]*3,keyPool=[0]*64), scope=scope)
        cases.append(case)
        return case

    inv = [bag(17, 18, 58, 64, 74), bag(90), bag(), bag()]
    eq = [[1,3,4,5],[0]*4,[0]*4,[0]*4]
    out = [bag(18,58,64,74),bag(90,17),bag(),bag()]
    add('give-equipped-weapon-other', [1002,0,1001,1002,1,999], inv, out, eq,
        [[0,2,3,4],[0]*4,[0]*4,[0]*4], scope='Actual Give to PC2 unequips source weapon and compacts all three remaining equipment locations; recipient retains gear.')
    out = [bag(18,58,64,74,17),bag(90),bag(),bag()]
    add('give-equipped-weapon-self', [1002,0,1001,1002,0,999], inv, out, eq,
        [[5,2,3,4],[0]*4,[0]*4,[0]*4], scope='Actual self Give reorders to bag tail; all equipment item identities and stats remain the same.')
    add('drop-equipped-weapon', [1002,0,1001,1003,999], inv,
        [bag(18,58,64,74),bag(90),bag(),bag()], eq, [[0,2,3,4],[0]*4,[0]*4,[0]*4],
        scope='Actual packed Drop removes equipment through TAKE_FROM_LOCATION; recalculates weapon stats and compacts all remaining slots.')
    equip_tail=[999,999,999] if original else [999,999]
    add('equip-ness-weapon-cold-menu', [1004,0,1001,1002]+equip_tail, inv, eq=eq,
        final_eq=[[2,3,4,5],[0]*4,[0]*4,[0]*4], checkpoint=12,
        scope='Complete Equip parent, fresh process at actual item menu; chooses second actual bag slot then backs out of the whole pause menu.')
    add('equipment-none-weapon', [1004,0,1001,66535]+equip_tail, inv, eq=eq,
        final_eq=[[0,3,4,5],[0]*4,[0]*4,[0]*4], scope='Real None option clears equipment without removing inventory and recalculates stats.')
    if pilot: return cases

    # Source ten Give message cases, using actual parent state and real recipient.
    for giver_dead in (False,True):
        for target_dead in (False,True):
            for full in (False,True):
                inv = [bag(90,17,58,64,74),bag(*([91]*14 if full else [91])),bag(),bag()]
                eq = [[2,3,4,5],[0]*4,[0]*4,[0]*4]
                out = copy.deepcopy(inv); feq = copy.deepcopy(eq)
                if not full:
                    out[0]=bag(17,58,64,74);out[1]=bag(91,90);feq[0]=[1,2,3,4]
                status={0:[int(giver_dead),0,0,0,0,0,0],1:[int(target_dead),0,0,0,0,0,0]}
                add(f'give-{int(giver_dead)}-{int(target_dead)}-full{int(full)}', [1002,0,1001,1002,1,999],inv,out,eq,feq,status,
                    scope='Exact source alive/unconscious giver/recipient plus full/available bag branch; failure preserves all slots and gear.')
    for aff in (1,2):
        inv=[bag(90,17),bag(),bag(),bag()];out=[bag(17,90),bag(),bag(),bag()]
        add('give-self-primary-'+str(aff),[1002,0,1001,1002,0,999],inv,out,[[2,0,0,0],[0]*4,[0]*4,[0]*4],
            [[1,0,0,0],[0]*4,[0]*4,[0]*4],{0:[aff,0,0,0,0,0,0]},scope='Source self rearrangement remains allowed while unconscious/diamondized; preserves equipment item identity.')
    inv=[bag(90,17,58,64,74),bag(),bag(),bag()];eq=[[2,3,4,5],[0]*4,[0]*4,[0]*4]
    add('give-target-cancel',[1002,0,1001,1002,999,999,999,999,999],inv,eq=eq,scope='Actual recipient B then back out of action/inventory/giver/pause; no mutation.')
    add('drop-middle-equipped-body',[1002,0,1003,1003,999],inv,[bag(90,17,64,74),bag(),bag(),bag()],eq,
        [[2,0,3,4],[0]*4,[0]*4,[0]*4],scope='Actual packed Drop of BODY clears speed/defense/resistance contributions and compacts later gear.')
    add('drop-before-all-equipment',[1002,0,1001,1003,999],inv,[bag(17,58,64,74),bag(),bag(),bag()],eq,
        [[1,2,3,4],[0]*4,[0]*4,[0]*4],scope='Ordinary Drop before equipped slots compacts gear indices while preserving every gear item and stat.')
    for gear_slot in range(1,4):
        inv=[bag(17,58,64,74),bag(90),bag(),bag()];eq=[[1,2,3,4],[0]*4,[0]*4,[0]*4]
        itemid=inv[0][gear_slot];out=copy.deepcopy(inv);out[0]=bag(*(inv[0][:gear_slot]+inv[0][gear_slot+1:4]));out[1]=bag(90,itemid)
        feq=copy.deepcopy(eq);feq[0][gear_slot]=0
        for j in range(4):
            if feq[0][j]>gear_slot+1:feq[0][j]-=1
        given=add('give-equipped-type'+str(gear_slot+1),[1002,0,1000+gear_slot+1,1002,1,999],inv,out,eq,feq,
            scope='Actual Give removes equipped BODY/ARMS/OTHER contribution and compacts remaining equipment indices; recipient bag appends only the selected item.')
        # Original SWAP compacts items before CHANGE_EQUIPPED_* but adjusts
        # later equipment indices after that call. Its recalculation therefore
        # reads the compacted bag using these intermediate equipment locations.
        intermediate=copy.deepcopy(eq[0]);intermediate[gear_slot]=0
        transient=stats(out[0],intermediate,0)
        if transient['stats']!=given['expectedGear'][0]['stats']or transient['resistances']!=given['expectedGear'][0]['resistances']:
            given['recalculatedGearAfterSourceOddity']=copy.deepcopy(given['expectedGear'][0])
            given['expectedGear'][0]['stats']=transient['stats'];given['expectedGear'][0]['resistances']=transient['resistances']
            given['sourceOddity']='Source different-PC Give recalculates before remaining equipment locations compact; stored stats/resistances can differ from final equipment item identities.'
        out[1]=bag(90)
        add('drop-equipped-type'+str(gear_slot+1),[1002,0,1000+gear_slot+1,1003,999],inv,out,eq,feq,
            scope='Actual packed Drop removes equipped BODY/ARMS/OTHER and commits source defense/speed/luck/resistance recalculation.')
        feq=copy.deepcopy(eq);feq[0][gear_slot]=0
        add('equipment-none-type'+str(gear_slot+1),[1004,0,1000+gear_slot+1,66535]+equip_tail,inv,eq=eq,final_eq=feq,
            scope='Actual None option clears BODY/ARMS/OTHER contribution while every inventory slot is preserved.')
    inv=[bag(),bag(),bag(),bag(35)];eq=[[0]*4 for _ in range(4)];eq[3][0]=1
    add('drop-zero-price-Poo-weapon-refused',[1002,3,1001,1003,999],inv,eq=eq,
        scope='Source Drop checks selling price; zero-priced equipped Poo weapon remains in bag and equipped. No removal/recalculation occurs.')
    inv=[bag(17,58,64,74,*([90]*10)),bag(91),bag(),bag()];eq=[[1,2,3,4],[0]*4,[0]*4,[0]*4]
    out=[bag(17,58,64,74,*([90]*9)),bag(91,90),bag(),bag()]
    add('give-last-slot-from-full-bag',[1002,0,1014,1002,1,999],inv,out,eq,
        scope='Actual Give selects last ordinary slot of full fourteen-item bag; no equipment position changes and exactly one item moves.')

    # The real equipment menu must reject incompatible items and preserve bags.
    gearsets = [(0,[17,18,28,49,58,56,64,70,74,81]),(1,[28,17,49,58,56,64,70,78,81]),
                (2,[36,17,49,58,56,64,70,74,81]),(3,[35,17,49,63,58,73,64,87,74])]
    for pc,ids in gearsets:
        inv=[bag()for _ in range(4)];inv[pc]=bag(*ids)
        for subtype,itemid in [(1,ids[0]),(2,{0:56,1:56,2:56,3:63}[pc]),(3,73 if pc==3 else 70),(4,87 if pc==3 else 81)]:
            slot=ids.index(itemid)+1;feq=[[0]*4 for _ in range(4)];feq[pc][subtype-1]=slot
            r=add(f'equip-pc{pc+1}-type{subtype}',[1004,pc,1000+subtype,1000+slot]+equip_tail,inv,final_eq=feq,
                  scope='Actual character/category/item menus choose source usable equipment; exact signed modifiers, Poo alternate parameters, miss rate and five resistance fields.')
            options=[j+1 for j,id in enumerate(ids)if items[id*39+25]>>4==1 and ((items[id*39+25]>>2)&3)+1==subtype and items[id*39+28]&(1<<pc)]
            r['expectedMenus']=[dict(window=7,ids=options+[65535])]
    inv=[bag(17,18,58,64,74),bag(),bag(),bag()];eq=[[1,3,4,5],[0]*4,[0]*4,[0]*4]
    add('equip-item-cancel',[1004,0,1001,999]+equip_tail,inv,eq=eq,scope='B at actual item choice leaves previous gear/stat state intact.')
    for subtype,itemid in [(1,17),(2,56),(3,70),(4,81)]:
        inv=[bag(itemid),bag(),bag(),bag()];eq=[[0]*4 for _ in range(4)];feq=copy.deepcopy(eq);feq[0][subtype-1]=1
        add(f'goods-use-equipment-type{subtype}',[1002,0,1001,1001],inv,eq=eq,final_eq=eq if original else feq,
            scope='Original Goods Use gives an informational message without equipping; active Redux redirects the packed equipment text/helper to commit equipment without inventory consumption.')
        # Original says already equipped; pinned Redux unequips through its
        # ASM_Unequip source hook instead. Both are explicit source outcomes.
        add(f'goods-use-equipped-type{subtype}',[1002,0,1001,1001],inv,eq=feq,final_eq=feq if original else eq,
            scope='Original already-equipped refusal versus active Redux Goods Use unequip; exact equipment/stat/miss/resistance change and intact bag.')
    inv=[bag(28),bag(),bag(),bag()]
    add('goods-use-wrong-carrier-equipment',[1002,0,1001,1001],inv,
        scope='Original informational message; Redux actual packed helper refuses Ness equipping Paula-only item. Bag/gear/stat state unchanged.')
    inv=[bag(17,58,64,74,*([90]*10)),bag(),bag(),bag()];eq=[[1,2,3,4],[0]*4,[0]*4,[0]*4]
    out=[bag(58,64,74,*([90]*10),17),bag(),bag(),bag()];feq=[[13,1,2,3],[0]*4,[0]*4,[0]*4]
    r=add('source-oddity-self-give-full-equipped-bag',[1002,0,1001,1002,0,999],inv,out,eq,feq,
          scope='Original FIND_EMPTY_INVENTORY_SLOT returns13 for full14-slot bags; self Give copies that value after appending at14, leaving equipped item location13 and previously stored weapon stats. Source oddity reproduced distinctly from native mismatch.')
    r['expectedGear'][0]=copy.deepcopy(r['expectedInitialGear'][0]);r['expectedGear'][0]['equipment']=feq[0]
    r['sourceOddity']='Original and pinned full-bag self-Give preserve an off-by-one equipped-item location and stale weapon stats; not a conversion mismatch.'
    # Scalar role guards are tested by real menu offerings, not selecting IDs
    # that the source intentionally excludes.
    for id in ('give-equipped-weapon-other','give-equipped-weapon-self','drop-equipped-weapon','give-target-cancel','drop-middle-equipped-body','equip-item-cancel',
               'goods-use-equipment-type1','goods-use-equipped-type2','goods-use-wrong-carrier-equipment',
               'give-equipped-type3','drop-equipped-type4','equipment-none-type2','drop-zero-price-Poo-weapon-refused','give-last-slot-from-full-bag'):
        peer=next(c for c in cases if c['id']==id);cold=copy.deepcopy(peer);cold['id']=id+'-cold';cold['warmPeer']=id
        cold['checkpoint']=13 if id=='give-target-cancel' else 15 if id.startswith('give') else 14 if id.startswith('drop') else 16 if id.startswith('goods-use') else 12
        cases.append(cold)
    # Add warm peer for the selected equip cold case.
    peer=next(c for c in cases if c['id']=='equip-ness-weapon-cold-menu');warm=copy.deepcopy(peer)
    warm['id']='equip-ness-weapon-warm';warm['checkpoint']=0;peer['warmPeer']=warm['id'];cases.append(warm)
    for case in cases:
        if case['checkpoint']:case['expectedCapturedGear']=copy.deepcopy(case['expectedInitialGear'])
    return cases


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--assets',type=Path,required=True)
    ap.add_argument('--original',action='store_true');ap.add_argument('--pilot',action='store_true');ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();rows=generate(a.root.resolve(),a.assets.resolve(),a.original,a.pilot)
    a.output.write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(cases=len(rows))))


if __name__=='__main__':main()
