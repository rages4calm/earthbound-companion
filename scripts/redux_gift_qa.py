# SPDX-License-Identifier: GPL-3.0-or-later
"""Replay present interactions locally without calling Jev or editing saves.

The cash case changes one NPC item field in an isolated asset fixture, and is
explicitly reported as prepared coverage rather than normal story progress.
"""
import argparse
import json
from pathlib import Path
import shutil
import struct
from types import SimpleNamespace
from build_maternalbound_pack import read_pack, write_pack
from jev_gameplay_runner import initialize, observe_step, load_run, sha

ROOT = Path(__file__).resolve().parents[1]


def interaction(source, engine, assets, name, flag, expected_item=None, expected_cash=None):
    run_path = ROOT / '_BuildScratch/jev-runs' / name
    initialize(SimpleNamespace(directory=run_path, checkpoint=source, native_exe=engine,
                               assets=assets, fixture_checkpoint=expected_cash is not None))
    folder, run = load_run(run_path)
    state = observe_step(folder, run, {'button': None, 'frames': 1, 'settle': 140}, 0)
    initial = state
    dialogue = []
    for index in range(1, 13):
        state = observe_step(folder, run, {'button': 'confirm', 'frames': 1, 'settle': 400}, index, state)
        dialogue += [w['text'] for w in state['windows'] if w['text'] and w['textSource'] == 'rendered_this_batch']
        if index > 1 and state['modeNames'] == ['OVERWORLD']:
            break
    else:
        raise RuntimeError('Gift conversation did not return to roaming.')
    member = lambda d: next(p for p in d['party'] if p['id'] == 1)
    before, after = member(initial)['items'], member(state)['items']
    bit = lambda d: bool(d['eventFlags'][(flag-1)//8] & (1 << ((flag-1)%8)))
    result = {'case': name, 'ordinaryInputsOnly': True, 'preparedAssetFixture': expected_cash is not None,
              'nativeExeSha256': run['nativeExeSha256'], 'packSha256': run['assetsSha256'],
              'initialPosition': initial['position'], 'finalPosition': state['position'],
              'eventFlag': flag, 'flagBefore': bit(initial), 'flagAfter': bit(state),
              'itemCountBefore': before.count(expected_item) if expected_item is not None else None,
              'itemCountAfter': after.count(expected_item) if expected_item is not None else None,
              'itemId': expected_item, 'cashBefore': initial['cash'], 'cashAfter': state['cash'],
              'expectedCash': expected_cash, 'reportedEmpty': any('it was empty' in t for t in dialogue),
              'returnedToRoaming': state['modeNames'] == ['OVERWORLD'], 'windowsAfter': len(state['windows'])}
    if bit(initial):
        raise ValueError('This test requires an unopened present.')
    result['giftDelivered'] = (after.count(expected_item) == before.count(expected_item)+1 if expected_item is not None
                               else state['cash'] == initial['cash']+expected_cash)
    # A normal second check must not grant the gift a second time.
    repeat = state
    for index in range(index+1, index+13):
        state = observe_step(folder, run, {'button': 'confirm', 'frames': 1, 'settle': 400}, index, state)
        if state['modeNames'] == ['OVERWORLD'] and index > 1:
            break
    else:
        raise RuntimeError('Repeat gift conversation did not return to roaming.')
    result['repeatReturnedToRoaming'] = state['modeNames'] == ['OVERWORLD']
    result['repeatDidNotDuplicate'] = member(state)['items'] == member(repeat)['items'] and state['cash'] == repeat['cash']
    (folder / 'gift-result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--assets', type=Path, required=True)
    p.add_argument('--before-exe', type=Path, required=True)
    p.add_argument('--fixed-exe', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--first-check-batch', type=Path, required=True, help='Archived batch before checking unopened NPC 1414; includes before-saves and before.srm.')
    p.add_argument('--second-check-batch', type=Path, required=True, help='Archived batch before checking unopened NPC 1415; includes before-saves and before.srm.')
    a = p.parse_args();output = a.output.resolve()
    if not output.is_relative_to(ROOT/'_BuildScratch') or output.exists():
        raise ValueError('Use a fresh scratch output.')
    output.mkdir(parents=True)
    rows = []
    cases = ((1414, 807, 224, a.first_check_batch),
             (1415, 808, 111, a.second_check_batch))
    for npc, flag, item, captured in cases:
        captured = captured.resolve()
        if not captured.is_relative_to(ROOT/'_BuildScratch'):
            raise ValueError('Only copied QA batches may be replayed.')
        source = output/f'checkpoint-{npc}';source.mkdir()
        shutil.copytree(captured/'before-saves', source/'saves')
        shutil.copy2(captured/'before.srm', source/'fixture.srm')
        row_before = interaction(source, a.before_exe.resolve(), a.assets.resolve(), f'{output.name}-before-{npc}', flag, expected_item=item)
        row_fixed = interaction(source, a.fixed_exe.resolve(), a.assets.resolve(), f'{output.name}-fixed-{npc}', flag, expected_item=item)
        if row_before['giftDelivered'] or not row_before['reportedEmpty']:
            raise RuntimeError('Previous engine did not reproduce the lost gift.')
        if not row_fixed['giftDelivered'] or not row_fixed['flagAfter'] or row_fixed['reportedEmpty'] or not row_fixed['repeatDidNotDuplicate']:
            raise RuntimeError('Fixed engine failed item gift or repeat protection.')
        rows += [row_before, row_fixed]
    entries, header, assets = read_pack(a.assets, ROOT/'native-source/src/data/runtime_generated/asset_ids.h')
    changed = bytearray(assets['data/npc_config_table.bin']);struct.pack_into('<I', changed, 1415*17+13, 256+123)
    assets['data/npc_config_table.bin'] = bytes(changed)
    fixture = output/'prepared-cash-gift.pak';write_pack(fixture, entries, header, assets)
    cash = interaction(output/'checkpoint-1415', a.fixed_exe.resolve(), fixture, f'{output.name}-fixed-cash', 808, expected_cash=123)
    if not cash['giftDelivered'] or not cash['flagAfter'] or not cash['repeatDidNotDuplicate']:
        raise RuntimeError('Cash gift failed.')
    rows.append(cash)
    report = {'Passed': True, 'format': 'redux-gift-replay-v1', 'cases': rows, 'TypeSafeRequests': 0,
              'OwnerSavesWritten': False, 'FullPlaythroughVerified': False,
              'PreparedCashFixture': 'Only NPC 1415 item field differs: 256+123 means a $123 gift. This is a test of cash semantics, not a story reward claim.'}
    (output/'results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'Passed': True, 'actualPresentsFixed': 2, 'preparedCashGiftPassed': True, 'TypeSafeRequests': 0}))


if __name__ == '__main__':
    main()
