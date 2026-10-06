# SPDX-License-Identifier: GPL-3.0-or-later
"""Source-selected complete pause-menu item and PSI lifecycle fixtures."""
import argparse
import copy
import json
import struct
from pathlib import Path
from build_maternalbound_pack import read_pack


def generate(root, assets, original=False, pilot=False):
    _, _, pack = read_pack(assets, root / 'native-source/src/data/runtime_generated/asset_ids.h')
    items = pack['data/item_configuration_table.bin']; actions = pack['data/battle_action_table.bin']
    psi = pack['data/psi_ability_table.bin']; cases = []

    def fresh():
        return [dict(level=1 if c == 0 else 0, hp=100, pp=50, maxHP=100, maxPP=50, status=[0]*7) for c in range(4)]

    def add(id, plan, initial=None, final=None, inventory=None, final_inventory=None, party=4,
            checkpoint=0, scope='', expected_actions=None):
        p = copy.deepcopy(initial or fresh()); q = copy.deepcopy(final or p)
        inv = copy.deepcopy(inventory or [[0]*14 for _ in range(4)])
        exp = copy.deepcopy(final_inventory if final_inventory is not None else inv)
        r = dict(id=id, entry=0, sourceRoutine='OPEN_MENU', plan=plan, party=party,
                 initialParty=p, initialInventory=inv, expectedInventory=exp, money=1000,
                 checkpoint=checkpoint, expectedDelta=0,
                 expectedInitialEffect=[dict(hpTarget=c['hp'], ppTarget=c['pp'], status=c['status']) for c in p],
                 expectedEffect=[dict(hpTarget=c['hp'], ppTarget=c['pp'], status=c['status']) for c in q],
                 expectedTransfer=dict(storage=[0]*36, queuedItems=[0]*3, queuedSources=[0]*3, keyPool=[0]*64),
                 scope=scope)
        if expected_actions is not None: r['expectedActions'] = expected_actions
        cases.append(r); return r

    def item(id, item_id, status, final_status, target=1, checkpoint=0, party=4, cancel=False, hp=100,
             final_hp=None, scope='', giver=0, usable=True):
        p = fresh(); p[target]['status'] = status; p[target]['hp'] = hp
        q = copy.deepcopy(p); q[target]['status'] = final_status
        if final_hp is not None: q[target]['hp'] = final_hp
        inv = [[0]*14 for _ in range(4)]; inv[giver][0] = item_id
        out = copy.deepcopy(inv); out[giver][0] = 0 if items[item_id*39+28]&128 and not cancel and usable else item_id
        plan = [1002] + ([giver] if party>1 else []) + [1001,1001] + ([999] if cancel else [1000+target+1] if party>1 and usable else [])
        if cancel: plan += [999,999,999,999]  # action, inventory, giver, pause
        r = add(id, plan, p, q, inv, out, party, checkpoint, scope)
        action = struct.unpack_from('<H', items, item_id*39+29)[0]
        r['packedItemContract'] = dict(id=item_id, type=items[item_id*39+25], flags=items[item_id*39+28], action=action,
                                      direction=actions[action*12], target=actions[action*12+1], callback=struct.unpack_from('<I', actions, action*12+8)[0])
        r['expectedActionCount']=int(usable and not cancel)
        return r

    item('wet-towel-sunstroke-full-parent',127,[6,0,1,1,0,1,0],[0,0,1,1,0,1,0],scope='Wet towel cures primary sunstroke only; actual chosen PC2 and one item consumed.')
    item('refreshing-herb-poison-cold-target',128,[5,0,1,1,0,1,0],[0,0,1,1,0,1,0],checkpoint=7,scope='Fresh process before real target child; herb clears primary poison only.')
    item('secret-herb-paralysis-full-parent',129,[3,0,1,1,0,1,0],[0,0,1,1,0,1,0],scope='Secret herb cures paralysis and preserves unrelated groups.')
    item('horn-of-life-revive-cold-child',130,[1,2,1,1,0,1,1],[0]*7,hp=0,final_hp=100,checkpoint=9,scope='Actual revival child serialized; all affliction groups clear and target HP becomes maximum.')
    item('herb-target-cancel-full-parent',128,[5,0,0,0,0,0,0],[5,0,0,0,0,0,0],cancel=True,scope='Target cancel then back out of all parent menus; no item or status mutation.')

    def ability(id, ability_id, status, final_status, target=1, checkpoint=0, hp=100, final_hp=None,
                caster=0, cancel=False, insufficient=False, party=4, scope=''):
        p = fresh(); p[caster]['level'] = 99
        if caster!=0: p[0]['level']=1
        p[target]['status'] = status; p[target]['hp'] = hp
        action = struct.unpack_from('<H', psi, ability_id*15+4)[0]; cost=actions[action*12+3]
        if insufficient: p[caster]['pp']=cost-1
        q = copy.deepcopy(p); q[target]['status']=final_status
        if final_hp is not None:q[target]['hp']=final_hp
        if not cancel and not insufficient:q[caster]['pp']-=cost
        plan=[1003,1000+ability_id]
        if insufficient:plan += [999,999]  # ability, pause
        elif cancel:plan += [999,999,999]  # target, ability, pause
        elif actions[action*12+1]==1 and party>1:plan += [1000+target+1]
        r=add(id,plan,p,q,party=party,checkpoint=checkpoint,scope=scope)
        r['packedPsiContract']=dict(id=ability_id,action=action,ppCost=cost,direction=actions[action*12],target=actions[action*12+1],callback=struct.unpack_from('<I',actions,action*12+8)[0])
        r['expectedActionCount']=0 if cancel or insufficient else party if actions[action*12+1]==4 else 1
        return r

    ability('psi-healing-alpha-cold-action',27,[7,0,1,1,0,1,0],[0,0,1,1,0,1,0],checkpoint=8,scope='Actual Ness Healing alpha chosen from menu; cold effect then writeback and exact PP cost.')
    ability('psi-lifeup-alpha-clamp-full-parent',23,[0]*7,[0]*7,hp=90,final_hp=100,scope='Minimum source alpha recovery exceeds missing10; clamps actual PC2 HP target to100.')
    ability('psi-healing-beta-insufficient-pp',28,[5,0,0,0,0,0,0],[5,0,0,0,0,0,0],insufficient=True,scope='Insufficient PP shows refusal and retries ability; cancel leaves PP/status unchanged.')
    ability('psi-healing-target-cancel',28,[5,0,0,0,0,0,0],[5,0,0,0,0,0,0],cancel=True,scope='Actual target B cancellation; then ability/pause cancellation. No PP or status mutation.')
    if pilot: return cases
    # Source priorities clear only the first matching condition. These are
    # explicit Original assembly contracts, not expectations read from native.
    cures=[('cold',[7,0,1,1,0,1,0],0),('sunstroke',[6,0,1,1,0,1,0],0),
           ('sleep',[0,0,1,1,0,1,0],2)]
    fallback_cures=[(name,aff[:3]+[0]+aff[4:],group) for name,aff,group in cures]
    beta=[('poison',[5,0,2,1,0,1,0],0),('nausea',[4,0,2,1,0,1,0],0),
          ('crying',[0,0,2,1,0,1,0],2),('strange',[0,0,0,1,0,1,0],3),*fallback_cures]
    gamma=[('paralysis',[3,0,2,1,0,1,0],0),('diamondized',[2,0,2,1,0,1,0],0),*beta]
    for label,ability_id,item_id,conditions,caster in [('alpha',27,127,cures,0),('beta',28,128,beta,0),('gamma',29,129,gamma,0),('omega',30,130,gamma,3)]:
        for name,aff,group in conditions:
            after=aff.copy();after[group]=0
            item('item-'+label+'-'+name,item_id,aff.copy(),after.copy(),scope='Source first matching cure only, explicit priority order; unrelated groups retained.')
            ability('psi-'+label+'-'+name,ability_id,aff.copy(),after.copy(),caster=caster,scope='Source first matching cure only; actual menu target and exact PP cost.')
        aff=[0,2,0,0,1,1,0]
        item('item-'+label+'-no-effect-consumes',item_id,aff.copy(),aff.copy(),scope='No matching source condition: item still consumed before callback; status unchanged.')
        ability('psi-'+label+'-no-effect-charges',ability_id,aff.copy(),aff.copy(),caster=caster,scope='No matching source condition: PP still charged before callback; status unchanged.')
    for target in range(4):
        item('horn-revive-pc'+str(target+1),130,[1,2,1,1,1,1,1],[0]*7,target=target,hp=0,final_hp=100,giver=(target+1)%4,scope='Other awake holder uses Horn; actual chosen PC revived, all groups cleared.')
        if target!=3:
            ability('psi-omega-revive-pc'+str(target+1),30,[1,2,1,1,1,1,1],[0]*7,target=target,hp=0,final_hp=100,caster=3,scope='Poo Healing omega revival clears all groups on the chosen PC.')
    for seed in range(1,25):
        for kind in ('item','psi'):
            r=item('gamma-revive-'+kind+'-'+str(seed),129,[1,2,1,1,1,1,1],[1,2,1,1,1,1,1],hp=0,scope='Source SUCCESS_255 actual pre-action draw <192 revives to maxHP/4; failure still consumes item.') if kind=='item' else ability('gamma-revive-'+kind+'-'+str(seed),29,[1,2,1,1,1,1,1],[1,2,1,1,1,1,1],hp=0,scope='Source SUCCESS_255 actual pre-action draw <192 revives to maxHP/4; failure still charges PP.')
            r['seed']=seed*0x9e3779b9 & 0xffffffff;r['sourceGammaRevival']=1
    for aid in (23,24,25):
        ability('psi-lifeup-'+str(aid)+'-KO-blocked',aid,[1,0,0,0,0,0,0],[1,0,0,0,0,0,0],hp=0,final_hp=0,scope='Lifeup cannot revive an unconscious target; selected PSI still costs PP.')
        ability('psi-lifeup-'+str(aid)+'-clamp',aid,[0]*7,[0]*7,hp=90,final_hp=100,scope='Minimum source amount exceeds missing10; selected target only clamps to maxHP.')
    p=fresh();p[0]['level']=99
    for i in range(4):p[i]['hp']=90-i
    q=copy.deepcopy(p)
    for i in range(4):q[i]['hp']=100
    q[0]['pp']-=actions[35*12+3]
    r=add('psi-lifeup-omega-all-party',[1003,1026],p,q,scope='Source ALL ally Lifeup omega dispatches once for every PC; clamps each HP and charges caster once.')
    r['expectedActionCount']=4
    cold=copy.deepcopy(r);cold['id']='psi-lifeup-omega-midparty-cold';cold['checkpoint']=10;cold['warmPeer']=r['id']
    cap=copy.deepcopy(p);cap[0]['hp']=cap[1]['hp']=100;cap[0]['pp']=q[0]['pp']
    cold['expectedCapturedEffect']=[dict(hpTarget=c['hp'],ppTarget=c['pp'],status=c['status'])for c in cap]
    cases.append(cold)
    p=copy.deepcopy(p);p[1]['hp']=0;p[1]['status'][0]=1
    q=copy.deepcopy(q);q[1]['hp']=0;q[1]['status'][0]=1
    r=add('psi-lifeup-omega-all-party-KO-guard',[1003,1026],p,q,scope='All-party Lifeup continues past unconscious PC without revival, heals awake PCs and charges caster once.');r['expectedActionCount']=4
    item('bazooka-wrong-user-refusal',133,[0]*7,[0]*7,usable=False,scope='Jeff-only flag: Ness use is refused without item/effect mutation.')
    item('bazooka-jeff-battle-only-refusal',133,[0]*7,[0]*7,giver=2,usable=False,scope='Actual Jeff goods selection passes usable-by check but battle-only context refuses overworld use.')
    # CLC; SBC has a borrow: 4-primary-1>0 suppresses Use for1/2, while
    # primary3 can use Goods. Preserve exact source rather than prose guesses.
    for aff in (1,2,3):
        p=fresh();p[0]['status'][0]=aff
        if aff==1:p[0]['hp']=0
        inv=[[128]+[0]*13]+[[0]*14 for _ in range(3)]
        r=add('goods-holder-'+str(aff)+'-use-guard',[1002,0,1001,999,999,999,999],p,p,inv,inv,scope='Exact source Goods menu primary-state guard; then back out without transaction.')
        r['expectedActionCount']=0;r['expectedMenus']=[dict(window=3,ids=[2,3,4] if aff<3 else [1,2,3,4])]
    item('solo-herb-auto-target',128,[5,0,0,0,0,0,0],[0]*7,target=0,party=1,scope='Single member Goods bypasses both character and target selectors; consumes once and cures.')
    ability('solo-psi-auto-target',27,[7,0,0,0,0,0,0],[0]*7,target=0,party=1,scope='Single PSI-capable member auto-targets self and charges exact PP cost.')
    for aff in (1,2):
        p=fresh();p[0]['level']=99;p[0]['status'][0]=aff
        if aff==1:p[0]['hp']=0
        r=add('psi-caster-'+str(aff)+'-unavailable',[999],p,p,scope='Source affliction block leaves no PSI-capable user; command menu must omit PSI.')
        r['expectedActionCount']=0;r['expectedAbsentMenuIDs']=[dict(window=0,id=3)]
    p=fresh();p[0]['level']=p[3]['level']=99;p[1]['status'][0]=5
    q=copy.deepcopy(p);q[1]['status'][0]=0;q[3]['pp']-=actions[37*12+3]
    r=add('psi-multiple-users-Poo-selected',[1003,3,1028,1002],p,q,scope='Actual multiple-user character selector chooses Poo; Healing beta cures PC2 and charges only Poo.');r['expectedActionCount']=1
    for id in ('wet-towel-sunstroke-full-parent','secret-herb-paralysis-full-parent','horn-revive-pc4','psi-lifeup-omega-all-party','psi-beta-poison','bazooka-jeff-battle-only-refusal'):
        peer=next(r for r in cases if r['id']==id)
        if id.startswith('bazooka'):continue  # no target/action child exists on refusal
        cold=copy.deepcopy(peer);cold['id']=id+'-cold';cold['checkpoint']=8;cold['warmPeer']=id;cases.append(cold)
    for id, checkpoint in [('herb-target-cancel-full-parent',7),('psi-healing-beta-insufficient-pp',11),('psi-multiple-users-Poo-selected',7)]:
        peer=next(r for r in cases if r['id']==id);cold=copy.deepcopy(peer);cold['id']=id+'-cold';cold['checkpoint']=checkpoint;cold['warmPeer']=id;cases.append(cold)
    return cases


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--assets',type=Path,required=True)
    ap.add_argument('--original',action='store_true');ap.add_argument('--pilot',action='store_true');ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();rows=generate(a.root.resolve(),a.assets.resolve(),a.original,a.pilot)
    a.output.write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(cases=len(rows))))


if __name__=='__main__':main()
