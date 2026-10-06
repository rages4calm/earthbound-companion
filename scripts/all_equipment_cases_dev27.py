# SPDX-License-Identifier: GPL-3.0-or-later
"""Every packed equipment/PC menu pair, with independent normal-range effects."""
import argparse
import collections
import copy
import json
from pathlib import Path
from build_maternalbound_pack import read_pack


def equipment_ids(items):
    return [i for i in range(1,len(items)//39)if items[i*39+25]&0x3c in(16,20,24,28)]


def stats(items,inv,eq,pc):
    rows=[items[inv[s-1]*39:(inv[s-1]+1)*39]if s else bytes(39)for s in eq]
    signed=lambda v:v-256 if v>=128 else v
    strength=32 if pc==3 else 31
    totals=[80+signed(rows[0][strength]),50+sum(signed(r[strength])for r in rows[1:]),
            23+signed(rows[1][33]),12+signed(rows[0][33]),24+signed(rows[2][33])+signed(rows[3][33])]
    # The corpus deliberately avoids Original's -1/256 carry-boundary oddities
    # and Redux's upper-limit changes. Negative ordinary totals <=-2 clamp0.
    if any(v>255 or v==-1 for v in totals):raise ValueError('Unevaluated boundary '+str(totals))
    special=[r[34]for r in rows]
    return dict(equipment=eq,stats=[max(v,0)for v in totals],missRate=special[0],
                resistances=[min(3,((special[1]>>b)&3)+((special[3]>>b)&3))for b in(0,2,4,6)]+[special[2]])


def generate(root,assets,original=False,pilot=False):
    _,_,pack=read_pack(assets,root/'native-source/src/data/runtime_generated/asset_ids.h')
    items=pack['data/item_configuration_table.bin'];ids=equipment_ids(items);cases=[]
    loadouts=[[next(i for i in ids if items[i*39+25]&0x3c==cat and items[i*39+28]&(1<<pc))for cat in(16,20,24,28)]for pc in range(4)]
    def add(item,pc,full=False):
        category=(items[item*39+25]&0x0c)//4;usable=bool(items[item*39+28]&(1<<pc))
        inv=[row+[0]*10 for row in loadouts];eq=[[1,2,3,4]for _ in range(4)];final_eq=copy.deepcopy(eq)
        if full:
            inv[pc]=[item]*14;eq[pc]=[0]*4;eq[pc][category]=3;selected=14
        else:inv[pc][4]=item;selected=5
        final_eq=copy.deepcopy(eq)
        if usable:final_eq[pc][category]=selected
        effects=[dict(hpTarget=100,ppTarget=50,status=[0]*7)for _ in range(4)]
        plan=[1004,pc,1000+category+1,1000+selected if usable else 999]+([999]*3 if original else[999]*2)
        options=[j+1 for j,id in enumerate(inv[pc])if id and items[id*39+25]&0x3c==16+4*category and items[id*39+28]&(1<<pc)]
        case=dict(id=f'equip-item{item}-pc{pc+1}'+('-full14-duplicate'if full else''),entry=0,sourceRoutine='OPEN_MENU',party=4,plan=plan,checkpoint=0,
                  money=1000,expectedDelta=0,initialParty=[dict(level=1 if c==0 else 0,hp=100,pp=50,maxHP=100,maxPP=50,status=[0]*7)for c in range(4)],
                  initialInventory=inv,expectedInventory=copy.deepcopy(inv),initialEquipment=eq,
                  expectedInitialGear=[stats(items,inv[c],eq[c],c)for c in range(4)],expectedGear=[stats(items,inv[c],final_eq[c],c)for c in range(4)],
                  expectedInitialEffect=effects,expectedEffect=copy.deepcopy(effects),expectedActionCount=0,
                  expectedTransfer=dict(storage=[0]*36,queuedItems=[0]*3,queuedSources=[0]*3,keyPool=[0]*64),expectedMenus=[dict(window=7,ids=options+[65535]+([0]if full else[]))],
                  expectedEquipmentItemIDs=[[inv[c][s-1]if s else 0 for s in final_eq[c]]for c in range(4)],
                  packedEquipmentContract=dict(item=item,pc=pc+1,exactType=items[item*39+25],category=category+1,flags=items[item*39+28],usable=usable,sourceOverflowOption=full),
                  scope='Complete real Equip/category/item parent. Select actual eligible slot or cancel when excluded; exact menu offerings, final gear/stat/miss/resistance and intact inventories.')
        cases.append(case);return case
    for item in(ids[:2]if pilot else ids):
        for pc in range(4):add(item,pc)
    for pc in range(4):
        for cat in range(4):
            # Latest eligible source item in each category, fourteen duplicates,
            # previous slot3 selected. Real menu navigation chooses slot14.
            item=next(i for i in reversed(ids)if items[i*39+25]&0x3c==16+4*cat and items[i*39+28]&(1<<pc))
            warm=add(item,pc,True);cold=copy.deepcopy(warm);cold['id']+='-cold';cold['checkpoint']=12;cold['warmPeer']=warm['id']
            cold['expectedCapturedGear']=copy.deepcopy(cold['expectedInitialGear']);cases.append(cold)
    return cases


def inventory_summary(items):
    ids=equipment_ids(items)
    return dict(packedItemRows=len(items)//39,equipmentItemIDs=ids,equipmentItems=len(ids),exactTypes=dict(collections.Counter(items[i*39+25]for i in ids)),
                eligibleItemPCPairs=sum(bool(items[i*39+28]&(1<<pc))for i in ids for pc in range(4)),excludedItemPCPairs=sum(not bool(items[i*39+28]&(1<<pc))for i in ids for pc in range(4)))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--assets',type=Path,required=True)
    p.add_argument('--original',action='store_true');p.add_argument('--pilot',action='store_true');p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();cases=generate(a.root.resolve(),a.assets.resolve(),a.original,a.pilot)
    a.output.write_text(json.dumps(cases,indent=2)+'\n');print(json.dumps(dict(cases=len(cases),cold=sum(bool(c['checkpoint'])for c in cases))))


if __name__=='__main__':main()
