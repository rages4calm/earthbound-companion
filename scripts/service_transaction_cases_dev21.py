# SPDX-License-Identifier: GPL-3.0-or-later
"""Source-selected C5E431, Tracy and retail preflight controls, both profiles."""
import argparse, copy, json, re
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native-source', type=Path, required=True)
    p.add_argument('--relocations', type=Path, required=True)
    p.add_argument('--pilot-fixtures', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--original', action='store_true')
    a = p.parse_args()
    defs = {n: int(v, 16) for n, v in re.findall(r'#define\s+(\w+)\s+0x([0-9a-fA-F]+)',
                (a.native_source / 'src/data/text_refs.h').read_text())}
    reloc = json.loads(a.relocations.read_text())['originalAddresses']
    entry = defs['MSG_SHOP1_CHECK_PARTY_HAS_ITEMS'] if a.original else reloc['C5E431']
    cases = []
    def bags(items, who=0):
        rows = [[0] * 14 for _ in range(4)]
        rows[who][:len(items)] = items
        return rows
    for label, ordinary, pool, party, expected in (
        ('empty', [], [], 1, 0), ('ordinary', [87], [], 1, 87),
        ('pool-only', [], [162], 1, 162), ('ordinary-priority', [87], [162], 1, 87),
        ('unique-two-pool', [], [166, 202], 1, 166),
        ('two-PC-second-ordinary', [], [], 2, 87), ('two-PC-pool-only', [], [162], 2, 162)):
        inv = bags(ordinary)
        if label == 'two-PC-second-ordinary':
            inv = bags([87], 1)
        for cold in (0, 5):
            cases.append(dict(id='source-preflight-' + label + ('-cold' if cold else ''),
                sourceEntry='C5E431', entry=entry, party=party, initialInventory=inv,
                initialPool=pool, plan=[], checkpoint=cold, expectedDelta=0,
                expectedInventory=inv, expectedSnapshot={'working': expected},
                expectedTransfer={'keyPool': pool + [0] * (64 - len(pool)), 'storage': [0] * 36,
                                  'queuedItems': [0] * 3},
                sourceContract={'callerUsesTruthinessOnly': True, 'ordinarySlotOneUnchanged': True,
                                'poolFirstFallbackForPCSelector': True}))
    pilots = json.loads(a.pilot_fixtures.read_text())
    for c in pilots:
        # Pilot source plans are retained; new cases add cold/negative capacity
        # and cancellation controls rather than rewriting frozen red artifacts.
        cases.append(copy.deepcopy(c))
        if c['id'] in ('tracy-pool-166-ordinary0', 'retail-pool-piggy-ordinary0'):
            cold = copy.deepcopy(c)
            cold['id'] += '-cold'
            cold['checkpoint'] = 3
            cases.append(cold)
    tracy = next(c for c in pilots if c['id'] == 'tracy-pool-166-ordinary0')
    for count in (2, 13, 14):
        c = copy.deepcopy(tracy)
        c.update(id=f'tracy-pooled-full-layout-{count}', initialInventory=bags([87] * count),
                 initialPool=[166], plan=[count, 1, 999], expectedInventory=bags([87] * count), checkpoint=3)
        cases.append(c)
    cancel = copy.deepcopy(tracy)
    cancel.update(id='tracy-pool-only-inventory-cancel', plan=[999, 999], soundCount=0,
                  expectedTransfer={'keyPool': [166] + [0] * 63, 'storage': [0] * 36},
                  expectedMenuCount={'2': 1})
    cases.append(cancel)
    full = copy.deepcopy(tracy)
    full.update(id='tracy-storage-full-pool-retained', initialStorage=[87] * 36, plan=[999], soundCount=0,
                expectedTransfer={'keyPool': [166] + [0] * 63, 'storage': [87] * 36},
                expectedMenuCount={'2': 0})
    cases.append(full)
    ordinary = copy.deepcopy(tracy)
    ordinary.update(id='tracy-ordinary-only-control', initialInventory=bags([87]), initialPool=[],
                    plan=[0, 1, 999], expectedInventory=bags([]),
                    expectedTransfer={'keyPool': [0] * 64, 'storage': [87] + [0] * 35})
    cases.append(ordinary)
    for c in cases:
        if c['id'].startswith('tracy-pool-196'):
            # A valid rejection needs the real inventory menu to have opened.
            c['expectedMenuCount'] = {'2': 1}
    a.output.write_text(json.dumps(cases, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(cases=len(cases), cold=sum(bool(c.get('checkpoint')) for c in cases), original=a.original)))


if __name__ == '__main__':
    main()
