# SPDX-License-Identifier: GPL-3.0-or-later
"""Source-derived full Escargo delivery and pickup parent fixtures.

Only pre-entry party, ordinary/pool inventory, cash and contact prerequisites are
prepared. The runner reaches the real phone and courier using packed map data.
"""
import argparse
import copy
import json
import re
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native-source', type=Path, required=True)
    p.add_argument('--relocations', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--original', action='store_true')
    p.add_argument('--pilot', action='store_true')
    a = p.parse_args()
    reloc = json.loads(a.relocations.read_text())['originalAddresses']
    defs = {n: int(v, 16) for n, v in re.findall(r'#define\s+(\w+)\s+0x([0-9a-fA-F]+)',
             (a.native_source / 'src/data/text_refs.h').read_text())}
    # QCT resolves the actual loaded phone NPC; this entry is provenance only.
    entry = defs['MSG_SHOP3_PHONE_BOOTH_PAID'] if a.original else reloc['C6803D']
    world = dict(phoneNpc=13, leaderX=7800, leaderY=1528, direction=0,
                 exitX=7920, exitY=1512, destinationX=1600, destinationY=1136,
                 sourceDoorType=2, sourceDoorDataOffset=1856,
                 source='Packed NPC13 plus adjacent 8px pre-entry leader; packed exit door type2/data1856. Actual phone, door and courier must qualify the fixture.')
    items = [87, 90, 93]
    cases = []
    def bags(row):
        return [row + [0] * (14-len(row))] + [[0]*14 for _ in range(3)]
    def transfer(storage, pool=()):
        return dict(storage=list(storage)+[0]*(36-len(storage)), queuedItems=[0]*3,
                    queuedSources=[0]*3, deliveryFlags=[0]*4,
                    keyPool=list(pool)+[0]*(64-len(pool)))
    def case(name, inv, storage, plan, out, remaining, delta=-19, pool=(), pool_out=(), **kw):
        c = dict(id=name, sourceEntry='C6803D', entry=entry,
                 initialInventory=bags(inv), initialStorage=list(storage),
                 initialPool=list(pool), initialFlags={'201':1}, plan=list(plan),
                 expectedInventory=bags(out), expectedTransfer=transfer(remaining,pool_out),
                 expectedInitialSnapshot={'inventory':bags(inv)},
                 expectedInitialTransfer={'keyPool':list(pool)+[0]*(64-len(pool))},
                 expectedDelta=delta, worldFixture=world,
                 sourceContract={'phoneCharge':1, 'courierCharge':18,
                                 'preEntryOnly':True, 'transactionSource':'data19:C636E5/C642A3/C63EB0'})
        c.update(kw)
        cases.append(c)
        return c
    # Request 1/2/3 items through actual storage menus. Queue removal compacts
    # storage; refunds append undelivered entries through the source store API.
    phone = {1:[0,1,0,1,0], 2:[0,1,0,0,0,1,0], 3:[0,1,0,0,0,0,0,0]}
    for n in (1,2,3):
        for free in (0,1,2,14):
            count = min(n,free)
            inv = [224]*(14-free)
            case(f'deliver-{n}-free-{free}', inv, items[:n], phone[n]+[0],
                 inv+items[:count], items[count:n], -19 if count else -1,
                 sound=118, soundCount=1 if count else 0)
    case('deliver-three-insufficient-cash', [], items, phone[3]+[0], [], items,
         -1, money=18, sound=118, soundCount=0)
    case('deliver-three-decline-return', [], items, phone[3]+[1,0], [], items,
         -1, sound=118, soundCount=0)
    # Normal pickup has separate first menu, retry and final confirmation paths.
    case('pickup-one', items, [], [0,0,0,0,1,0], items[1:], items[:1], sound=118)
    case('pickup-three', items, [], [0,0,0,0,0,0,0,0,0], [], items, sound=118)
    case('pickup-decline-bill', items, [], [0,0,1], items, [], -1, sound=118, soundCount=0)
    case('pickup-cancel-inventory', items, [], [0,0,0,999], items, [], -1, sound=118, soundCount=0)
    case('pickup-insufficient-cash', items, [], [0,0,0], items, [], -1,
         money=18, sound=118, soundCount=0)
    case('pickup-capacity-one', items, [87]*35, [0,0,0,0,0], items[1:], [87]*36, sound=118)
    # Unique key-pool QoL is intentional in both native profiles. Original
    # controls execute Original packed scripts; they do not disable that QoL.
    inv = [224]*14
    if a.original:
        case('pickup-pooled-banana-original-control', [], [], [0,0,0,0,1,0], [], [166],
             pool=[166],sound=118)
        # The native project's shared key-pool QoL applies to Original Sound
        # Stone too; do not mistake that pre-entry classification for a source
        # storage rejection bug. This remains an Original packed script control.
        case('pickup-sound-stone-rejected', [], [], [0,0,0,0,999], [], [], -1,
             pool=[196],pool_out=[196],sound=118,soundCount=0)
    else:
        case('pickup-pooled-banana-full-bag', inv, [], [0,0,0,14,1,0], inv, [166],
             pool=[166], sound=118)
        case('pickup-pooled-sound-stone-rejected', [], [], [0,0,0,0,999], [], [], -1,
             pool=[196], pool_out=[196], sound=118, soundCount=0)
    retry = case('pickup-reconfirm-return', items, [], [0,0,0,0,1,1,999], items[1:]+items[:1], [], -1,
                 sound=118, soundCount=0)
    retry['sourceContract']['refundOrder']='C64155 GIVE_AND_RETURN_LOCATION places removed item in first free ordinary slot; it does not restore the old slot ordering.'
    # Multiple active PCs: source delivery chooses the first actual free receiver.
    c = case('deliver-first-PC-full-second-free', [224]*14, [87], phone[1]+[0],
             [224]*14, [], party=2, sound=118)
    c['expectedInventory'][1][0] = 87
    c = case('pickup-second-PC', [], [], [0,0,0,1,0,1,0], [], [87], party=2, sound=118)
    c['initialInventory'][1][0] = 87
    c['expectedInitialSnapshot']['inventory'][1][0] = 87
    for name, checkpoints in (('deliver-1-free-14',(6,8,9)),
                              ('pickup-one',(6,7,8,9)),
                              ('pickup-pooled-banana-full-bag' if not a.original else 'pickup-pooled-banana-original-control',(7,)),
                              ('deliver-three-decline-return',(8,))):
        parent = next(c for c in cases if c['id']==name)
        for checkpoint in checkpoints:
            c = copy.deepcopy(parent)
            c['id'] += f'-cold-{checkpoint}'
            c['checkpoint'] = checkpoint
            cases.append(c)
    for label,pickup in (('deliver',False),('pickup',True)):
        c = case(label+'-unreachable-room-source-failure',items if pickup else [],[] if pickup else items,
                 [0,0] if pickup else phone[3],items if pickup else [],[] if pickup else items,
                 -1,sound=118,soundCount=0)
        c['worldFixture']=dict(world,exitX=0,exitY=0,expectedInteractionType=10)
        c['sourceContract']['failure']='Source delivery attempt exhaustion schedules actual PROCESS_INTERACTION type10; C64515/C6451A return delivery queue and clear pending flags.'
    if a.pilot:
        names={'deliver-3-free-1','pickup-one','pickup-three','deliver-1-free-14-cold-6',
               'pickup-one-cold-7','deliver-1-free-14-cold-8','pickup-one-cold-9'}
        cases = [c for c in cases if c['id'] in names]
    a.output.write_text(json.dumps(cases,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(cases=len(cases),cold=sum(bool(c.get('checkpoint')) for c in cases),original=a.original)))


if __name__=='__main__':
    main()
