# SPDX-License-Identifier: GPL-3.0-or-later
"""Source-addressed selected ATM and hospital prerequisite fixtures."""
import argparse
import copy
import json
import re
from pathlib import Path

DOCTORS = [('onett', 'C90000', 'ONETT', 20), ('twoson', 'C90008', 'TWOSON', 30),
           ('happy', 'C90010', 'HAPPY_HOSPITAL', 35), ('threed', 'C9002B', 'THREED', 40),
           ('desert', 'C90033', 'DESERT', 45), ('fourside', 'C90067', 'FOURSIDE', 60),
           ('summers', 'C9006F', 'SUMMERS', 70), ('scaraba', 'C90077', 'SCARABA', 80),
           ('moonside', 'C9007F', 'MOONSIDE', 60)]
NURSES = [('onett', 'C9008D', 'ONETT', 50), ('twoson', 'C90095', 'TWOSON', 100),
          ('happy', 'C9009D', 'HAPPY_HOSPITAL', 110), ('threed', 'C900BD', 'THREED', 120),
          ('desert', 'C900C5', 'DESERT', 135), ('fourside', 'C900CD', 'FOURSIDE', 150),
          ('summers', 'C900D5', 'SUMMERS', 180), ('scaraba', 'C900DD', 'SCARABA', 200),
          ('moonside', 'C900E8', 'MOONSIDE', 150)]
HEALERS = [('onett', 'C916A3', 'ONETT', [70, 60, 50]),
           ('twoson', 'C916AF', 'TWOSON', [80, 70, 60]),
           ('threed', 'C916BB', 'THREED', [90, 80, 70]),
           ('desert', 'C916C7', 'DESERT', [100, 90, 80]),
           ('fourside', 'C916D3', 'FOURSIDE', [100, 90, 80]),
           ('summers', 'C916DF', 'SUMMERS', [120, 110, 100]),
           ('scaraba', 'C916EB', 'SCARABA', [150, 140, 130]),
           ('moonside', 'C916F7', 'MOONSIDE', [100, 90, 80])]


def party_state():
    return [dict(hp=100, pp=50, status=[0] * 7) for _ in range(4)]


def expected_party(p):
    return [dict(hpTarget=c['hp'], ppTarget=c['pp'], status=c['status']) for c in p]


def generate(root, original=False, pilot=False, native_source=None, relocations=None):
    native_source = native_source or root / '_BuildScratch/audit-dev17-v4-complete-source'
    relocations = relocations or root / '_BuildScratch/maternalbound-native-dialogue-expanded/dialogue-relocations.json'
    mapping = json.loads(relocations.read_text())['originalAddresses']
    refs = (native_source / 'src/data/text_refs.h').read_text()
    aliases = {n: int(v, 16) for n, v in re.findall(r'#define\s+(\w+)\s+0x([0-9A-F]+)u', refs)}
    cases = []

    def entry(addr, alias):
        return aliases[alias] if original else mapping[addr]

    def add(id, address, alias, plan, party=1, initial=None, final=None, money=1000, delta=0,
            bank=0, final_bank=None, numbers=None, number_results=None, checkpoint=0, sound=37,
            sound_count=0, flags=None, pool=None, scope=''):
        initial = copy.deepcopy(initial or party_state())
        final = copy.deepcopy(final or initial)
        numbers = numbers or []
        row = dict(id=id, sourceEntry=address, nativeAlias=alias, entry=entry(address, alias), plan=plan,
                   party=party, money=money, bank=bank, initialParty=initial,
                   initialFlags=flags or {}, initialPool=pool or [], expectedDelta=delta,
                   expectedInitialService=dict(wallet=money, bank=bank, party=expected_party(initial)),
                   expectedService=dict(wallet=money + delta, bank=bank if final_bank is None else final_bank,
                                        party=expected_party(final), numberPlanUsed=len(numbers),
                                        serviceFlags=[0] * 11, moonsideFlag=0),
                   numbers=numbers, checkpoint=checkpoint, numberSelectMode=2,
                   sound=sound, soundCount=sound_count, expectedPlanUsed=len(plan), scope=scope)
        row['expectedInventory'] = [[0] * 14 for _ in range(4)]
        row['expectedTransfer'] = dict(storage=[0] * 36, queuedItems=[0] * 3, queuedSources=[0] * 3,
                                       keyPool=(pool or []) + [0] * (64 - len(pool or [])))
        row['expectedAwakePCs'] = [pc for pc in range(4) if initial[pc]['status'][0] == 1 and final[pc]['status'][0] == 0]
        if number_results is not None:
            row['expectedNumberResults'] = number_results
        cases.append(row)

    def atm(id, plan, money, bank, numbers, delta=0, final_bank=None, checkpoint=0, card=True,
            sound=116, sound_count=0, scope=''):
        add(id, 'C680A6', 'MSG_GLOBAL_CASHDISPENSER', plan, money=money, bank=bank,
            numbers=numbers, number_results=[-1 if n == 99999999 else n for n in numbers],
            delta=delta, final_bank=final_bank, checkpoint=checkpoint, sound=sound, sound_count=sound_count,
            pool=[177] if card else [], flags={'781': 1, '784': int(card)} if not original else {}, scope=scope)

    atm('atm-withdraw-five-digits', [0], 1000, 90000, [12345], 12345, 77655, sound_count=1,
        scope='Real five-digit selector and successful withdrawal from source ATM card caller.')
    atm('atm-deposit-five-digits-cold', [1], 50000, 100000, [23456], -23456, 123456,
        checkpoint=1, sound=118, sound_count=1,
        scope='Fresh-process actual number selector and successful five-digit deposit.')
    p = party_state(); p[0] = dict(hp=40, pp=7, status=[6, 0, 1, 1, 0, 1, 0])
    q = copy.deepcopy(p); q[0]['status'][0] = 0
    add('doctor-onett-sunstroke', 'C90000', 'MSG_SHOP2_DOCTOR_ONETT', [0], initial=p, final=q,
        delta=-20, sound_count=1, scope='Illness only is cured; HP/PP and unrelated afflictions persist.')
    add('doctor-moonside-poison-cold', 'C9007F', 'MSG_SHOP2_DOCTOR_MOONSIDE', [1], initial=p, final=q,
        delta=-60, sound_count=1, checkpoint=6, scope='Actual source-inverted Yes selection and wrapper cleanup.')
    p = party_state(); p[1] = dict(hp=0, pp=3, status=[1, 2, 1, 1, 0, 1, 0])
    q = copy.deepcopy(p); q[1] = dict(hp=100, pp=50, status=[0, 0, 1, 1, 0, 0, 0])
    add('nurse-onett-revive-cold', 'C9008D', 'MSG_SHOP2_NURSE_ONETT', [1, 0], party=2,
        initial=p, final=q, delta=-50, sound_count=1, checkpoint=5,
        scope='Actual character selection, bill, revival and fresh-process character child restore.')
    add('nurse-moonside-revive', 'C900E8', 'MSG_SHOP2_NURSE_MOONSIDE', [1, 1], party=2,
        initial=p, final=q, delta=-150, sound_count=1,
        scope='Actual source-inverted bill and nurse wrapper cleanup.')
    if pilot:
        return cases
    atm('atm-no-card', [], 1000, 90000, [], card=False,
        scope='Actual ATM card guard refuses entry without the source prerequisite.')
    atm('atm-initial-menu-cancel', [999], 1234, 3456, [], scope='Cancel transaction before numeric input.')
    atm('atm-withdraw-empty-bank', [0], 1000, 0, [], scope='Zero bank balance refuses numeric input.')
    atm('atm-withdraw-full-wallet', [0], 99999, 80000, [], scope='Full wallet refuses numeric input.')
    atm('atm-deposit-full-bank', [1], 99999, 9999999, [], scope='Full account refuses numeric input.')
    for selection, name in [(0, 'withdraw'), (1, 'deposit')]:
        for number, suffix in [(0, 'zero'), (99999999, 'cancel')]:
            atm('atm-' + name + '-' + suffix, [selection], 90000, 10000, [number],
                checkpoint=1 if suffix == 'cancel' else 0, scope='Zero/cancel numeric return leaves both balances unchanged.')
    atm('atm-withdraw-excess-retry', [0], 1000, 10000, [10001, 9999], 9999, 1,
        sound_count=1, scope='Requested amount above bank balance is rejected before a valid retry.')
    atm('atm-deposit-insufficient-cash-retry', [1], 1000, 3000, [1001, 999], -999, 3999,
        sound=118, sound_count=1, scope='Requested deposit above wallet is rejected before a valid retry.')
    atm('atm-withdraw-wallet-exact-limit', [0], 99000, 3000, [999], 999, 2001,
        sound_count=1, scope='A withdrawal reaching exactly 99,999 succeeds.')
    atm('atm-deposit-bank-exact-limit', [1], 1000, 9999000, [999], -999, 9999999,
        sound=118, sound_count=1, scope='A deposit reaching exactly 9,999,999 succeeds.')
    if not original:
        atm('atm-withdraw-wallet-overflow-refund-retry-cold', [0], 99000, 3000, [2000, 999], 999, 2001,
            checkpoint=1, sound_count=1, scope='Rejected withdrawal is fully refunded before the second real numeric input; cold restore after rollback.')
        cases[-1]['captureNumberIndex'] = 1
        cases[-1]['expectedCapturedService'] = dict(wallet=99000, bank=3000, numberPlanUsed=1)
        atm('atm-deposit-bank-overflow-refusal', [1], 1000, 9999000, [1000],
            sound=118, scope='Deposit exceeding source account cap is rejected without any balance mutation.')
    # Price and character coverage are separate from the four curable illnesses.
    for index, (town, addr, alias, cost) in enumerate(DOCTORS):
        for illness in range(4, 8):
            target = (index + illness) % 4
            p = party_state(); p[target] = dict(hp=37, pp=9, status=[illness, 2, 1, 1, 0, 1, 0])
            q = copy.deepcopy(p); q[target]['status'][0] = 0
            add(f'doctor-{town}-illness{illness}-pc{target+1}', addr, 'MSG_SHOP2_DOCTOR_' + alias,
                [int(town == 'moonside'), target], party=4, initial=p, final=q, delta=-cost,
                checkpoint=5 if illness == 4 else 0, sound_count=1,
                scope='Active source wrapper price; selected party member only, curable primary illness only.')
    for primary, secondary, name in [(0, 0, 'healthy'), (1, 0, 'unconscious'), (2, 0, 'diamond'),
                                     (3, 0, 'numb'), (0, 1, 'mushroom'), (0, 2, 'possessed')]:
        p = party_state(); p[0]['status'] = [primary, secondary, 0, 0, 0, 1, 0]
        add('doctor-refuses-' + name, 'C90000', 'MSG_SHOP2_DOCTOR_ONETT', [0], initial=p,
            scope='Source doctor refuses this condition without charging or clearing homesickness.')
    p = party_state(); p[1] = dict(hp=37, pp=9, status=[5, 0, 0, 0, 0, 0, 0])
    for id, plan, money in [('insufficient-cash', [0], 19), ('decline', [1], 1000),
                            ('menu-cancel', [999], 1000), ('character-cancel', [0, 999], 1000)]:
        add('doctor-' + id, 'C90000', 'MSG_SHOP2_DOCTOR_ONETT', plan, party=2, initial=p, money=money,
            scope='Source refusal/cancellation preserves every character and both balances.')
    for index, (town, addr, alias, cost) in enumerate(NURSES):
        target = index % 4
        p = party_state(); p[target] = dict(hp=0, pp=3, status=[1, 2, 1, 1, 0, 1, 0])
        q = copy.deepcopy(p); q[target] = dict(hp=100, pp=50, status=[0, 0, 1, 1, 0, 0, 0])
        add('nurse-' + town + '-revive-pc' + str(target + 1), addr, 'MSG_SHOP2_NURSE_' + alias,
            [target, int(town == 'moonside')], party=4, initial=p, final=q, delta=-cost, sound_count=1,
            checkpoint=6 if index % 2 == 0 else 0,
            scope='Active source nurse fee, chosen unconscious member, target HP/PP restoration and exact status groups.')
    p = party_state(); p[1] = dict(hp=0, pp=3, status=[1, 2, 1, 1, 0, 1, 0])
    for id, plan, money in [('healthy-selection', [0], 1000), ('character-cancel', [999], 1000),
                            ('decline-bill', [1, 1], 1000), ('cancel-bill', [1, 999], 1000),
                            ('insufficient-cash', [1, 0], 49)]:
        add('nurse-' + id, 'C9008D', 'MSG_SHOP2_NURSE_ONETT', plan, party=2, initial=p, money=money,
            scope='Source nurse refusal leaves patient unconscious, money and all statuses unchanged.')
    add('nurse-no-patient', 'C9008D', 'MSG_SHOP2_NURSE_ONETT', [0], party=2,
        scope='Source scan with no unconscious active member explains service without charging.')
    for index, (town, addr, alias, costs) in enumerate(HEALERS):
        for treatment, (group, status) in enumerate([(0, 2), (0, 3), (1, 2)]):
            target = (index + treatment) % 4
            p = party_state(); p[target] = dict(hp=37, pp=9, status=[0, 0, 1, 1, 0, 1, 0]); p[target]['status'][group] = status
            q = copy.deepcopy(p); q[target]['status'][group] = 0
            yes = int(town == 'moonside')
            add(f'healer-{town}-treatment{treatment}-pc{target+1}', addr, 'MSG_SHOP2_HEALER_' + alias,
                [yes, treatment, yes, target], party=4, initial=p, final=q, delta=-costs[treatment], sound_count=1,
                checkpoint=5 if treatment == 2 else 0,
                scope='Active healer wrapper price and selected diamond/numb/possessed condition only; treatment flags cleared.')
    for treatment in range(3):
        group, status = [(0, 2), (0, 3), (1, 2)][treatment]
        p = party_state(); p[1]['status'][group] = status
        for id, plan, money in [('decline-service', [1], 1000), ('cancel-treatment', [0, 999], 1000),
                                ('decline-bill', [0, treatment, 1], 1000), ('cancel-character', [0, treatment, 0, 999], 1000),
                                ('insufficient-cash', [0, treatment, 0], HEALERS[0][3][treatment]-1)]:
            add(f'healer-{treatment}-{id}', 'C916A3', 'MSG_SHOP2_HEALER_ONETT', plan,
                party=2, initial=p, money=money, scope='Cancellation/refusal preserves character, cash and clears source treatment flags.')
        q = copy.deepcopy(p); q[1]['status'][group] = 0
        add(f'healer-{treatment}-wrong-patient-retry', 'C916A3', 'MSG_SHOP2_HEALER_ONETT',
            [0, treatment, 0, 0, 1], party=2, initial=p, final=q, delta=-HEALERS[0][3][treatment], sound_count=1,
            scope='Wrong chosen member is rejected before real character-menu retry; charge once for matching member.')
    for town, addr, alias, costs in [HEALERS[0], HEALERS[-1]]:
        p = party_state(); p[0]['status'][1] = p[2]['status'][1] = 1
        q = copy.deepcopy(p); q[0]['status'][1] = q[2]['status'][1] = 0
        add('healer-' + town + '-sell-two-mushrooms', addr, 'MSG_SHOP2_HEALER_' + alias,
            [0, int(town != 'moonside')], party=4, initial=p, final=q, delta=100, sound_count=2,
            scope='Actual mushroom-sale parent clears each active mushroom and pays 50 each; subsequent service declined.')
        add('healer-' + town + '-decline-mushrooms', addr, 'MSG_SHOP2_HEALER_' + alias,
            [1, int(town != 'moonside')], party=4, initial=p,
            scope='Actual mushroom sale is declined and subsequent service declined; no mutation.')
    p = party_state(); p[0]['status'][0] = 7
    q = copy.deepcopy(p); q[0]['status'][0] = 0
    add('doctor-exact-cash', 'C90000', 'MSG_SHOP2_DOCTOR_ONETT', [0], initial=p, final=q,
        money=20, delta=-20, sound_count=1, scope='Exact treatment fee succeeds and leaves zero cash.')
    p = party_state(); p[1] = dict(hp=0, pp=0, status=[1, 0, 0, 0, 0, 0, 0])
    q = copy.deepcopy(p); q[1] = dict(hp=100, pp=50, status=[0] * 7)
    add('nurse-exact-cash', 'C9008D', 'MSG_SHOP2_NURSE_ONETT', [1, 0], party=2, initial=p, final=q,
        money=50, delta=-50, sound_count=1, scope='Exact revival fee succeeds and leaves zero cash.')
    add('nurse-benched-patient-excluded', 'C9008D', 'MSG_SHOP2_NURSE_ONETT', [0], initial=p,
        scope='Unconscious unjoined/inactive character does not satisfy active-party patient scan.')
    p = party_state(); p[1]['status'][0] = 2
    q = copy.deepcopy(p); q[1]['status'][0] = 0
    add('healer-exact-cash', 'C916A3', 'MSG_SHOP2_HEALER_ONETT', [0, 0, 0, 1], party=2, initial=p, final=q,
        money=70, delta=-70, sound_count=1, scope='Exact source fee cures selected diamond condition and leaves zero cash.')
    for treatment in range(3):
        add('healer-wrong-single-treatment' + str(treatment), 'C916A3', 'MSG_SHOP2_HEALER_ONETT',
            [0, treatment, 0], scope='Single-member wrong condition returns without charge or character retry.')
    return cases


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path.cwd())
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--native-source', type=Path)
    ap.add_argument('--relocations', type=Path)
    ap.add_argument('--original', action='store_true')
    ap.add_argument('--pilot', action='store_true')
    a = ap.parse_args()
    cases = generate(a.root, a.original, a.pilot, a.native_source, a.relocations)
    a.output.write_text(json.dumps(cases, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(cases=len(cases), original=a.original)))


if __name__ == '__main__':
    main()
