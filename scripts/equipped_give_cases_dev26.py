# SPDX-License-Identifier: GPL-3.0-or-later
"""Intentional equipped Give corrections with independent final-gear outcomes."""
import argparse
import copy
import json
from pathlib import Path
from build_maternalbound_pack import read_pack
from goods_equipment_cases_dev25 import generate as baseline


def generate(root,assets,original=False):
    cases=baseline(root,assets,original)
    _,_,pack=read_pack(assets,root/'native-source/src/data/runtime_generated/asset_ids.h');data=pack['data/item_configuration_table.bin']
    def bag(ids):return list(ids)+[0]*(14-len(ids))
    def derive(inv,eq,pc):
        rows=[data[inv[v-1]*39:(inv[v-1]+1)*39]if v else bytes(39)for v in eq]
        signed=lambda b:b-256 if b&128 else b;strength=32 if pc==3 else 31
        stats=[80+signed(rows[0][strength]),50+sum(signed(r[strength])for r in rows[1:]),23+signed(rows[1][33]),12+signed(rows[0][33]),24+signed(rows[2][33])+signed(rows[3][33])]
        if not all(0<=v<=255 for v in stats):raise ValueError('Fixture outside ordinary selected stat range')
        return dict(equipment=eq,stats=stats,missRate=rows[0][34],resistances=[min(3,((rows[1][34]>>bit)&3)+((rows[3][34]>>bit)&3))for bit in(0,2,4,6)]+[rows[2][34]])
    for case in cases:
        if 'sourceOddity'in case:
            case['correctsSourceOddity']=case.pop('sourceOddity');case['previousSourceFaithfulGear']=copy.deepcopy(case['expectedGear'])
            if case['id']=='source-oddity-self-give-full-equipped-bag':case['expectedGear'][0]['equipment'][0]=14
            case['expectedGear']=[derive(case['expectedInventory'][i],case['expectedGear'][i]['equipment'],i)for i in range(4)]
            case['scope']='Intentional QoL correction of recorded Original-source equipment location/stale derived fields; preserve exact transaction inventory and other state.'
    gear_ids=[[17,58,64,74],[28,58,64,78],[36,58,64,74],[35,63,73,87]]
    template=copy.deepcopy(cases[0]);extra=[]
    for pc in range(4):
        for size in (4,7,14):
            for slot in range(4):
                for self_give in (False,True):
                    target=pc if self_give else (pc+1)%4
                    inv=[bag(ids)for ids in gear_ids];inv[pc]=bag(gear_ids[pc]+[90]*(size-4));eq=[[1,2,3,4]for _ in range(4)]
                    out=copy.deepcopy(inv);moved=out[pc].pop(slot);out[pc].append(0)
                    first=out[target].index(0);out[target][first]=moved
                    final_eq=copy.deepcopy(eq)
                    for j in range(4):
                        if j==slot:final_eq[pc][j]=first+1 if self_give else 0
                        elif final_eq[pc][j]>slot+1:final_eq[pc][j]-=1
                    case=copy.deepcopy(template);case.update(id=f'qol-give-pc{pc+1}-size{size}-type{slot+1}-'+('self'if self_give else'other'),
                        initialInventory=inv,expectedInventory=out,initialEquipment=eq,
                        expectedInitialGear=[derive(inv[i],eq[i],i)for i in range(4)],expectedGear=[derive(out[i],final_eq[i],i)for i in range(4)],
                        plan=[1002,pc,1000+slot+1,1002,target,999],checkpoint=0,
                        scope='Complete Give for actual source-selected gear on all four PCs, four categories, partial/full giver bags; retain exact equipped item identity and independently derive final stats/miss/resistances.')
                    extra.append(case)
    cases.extend(extra)
    for pc in range(4):
        for slot in (0,1,2):
            id=f'qol-give-pc{pc+1}-size14-type{slot+1}-'+('self'if slot==0 else'other')
            peer=next(c for c in cases if c['id']==id);cold=copy.deepcopy(peer);cold['id']=id+'-cold';cold['warmPeer']=id;cold['checkpoint']=15
            cold['expectedCapturedGear']=copy.deepcopy(cold['expectedInitialGear']);cases.append(cold)
    for id in ('qol-give-pc4-size14-type1-self','qol-give-pc2-size14-type2-other'):
        peer=next(c for c in cases if c['id']==id);warm=copy.deepcopy(peer);warm['id']=id+'-nonempty-other-storage';warm['initialPool']=[177,196]
        warm['initialStorage']=[90,91];warm['initialQueue']=[[3,91]]
        warm['expectedTransfer'].update(keyPool=[177,196]+[0]*62,storage=[90,91]+[0]*34,queuedItems=[91,0,0],queuedSources=[3,0,0])
        cases.append(warm);cold=copy.deepcopy(warm);cold['id']=warm['id']+'-cold';cold['checkpoint']=15;cold['warmPeer']=warm['id']
        cold['expectedCapturedGear']=copy.deepcopy(cold['expectedInitialGear']);cases.append(cold)
    for case in cases:
        case['expectedEquipmentItemIDs']=[[case['expectedInventory'][pc][slot-1]if slot else 0 for slot in gear['equipment']]for pc,gear in enumerate(case['expectedGear'])]
    return cases


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--assets',type=Path,required=True);ap.add_argument('--original',action='store_true');ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();rows=generate(a.root.resolve(),a.assets.resolve(),a.original);a.output.write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(dict(cases=len(rows))))


if __name__=='__main__':main()
