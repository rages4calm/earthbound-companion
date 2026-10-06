# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify selected service contracts from pinned scripts and owner ROM metadata.

Publishes addresses, hashes, numeric operands and check outcomes only. Original
bytecode is parsed locally; this is not original-machine execution evidence.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import maternalbound_dialogue as dialogue
from status_service_cases_dev23 import DOCTORS, NURSES, HEALERS


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'native-source', 'rom', 'output'):
        ap.add_argument('--' + name, type=Path, required=True)
    a = ap.parse_args()
    doc, specs, expansions = dialogue.load_native(a.native_source)
    # Original CC1C/11 has no Redux character operand.
    specs[(0x1C, 0x11)] = ('zero_width_space', ())
    rom = a.rom.read_bytes()
    checks, spans = [], []
    source = {i: (a.project / f'ccscript/data/data_{i}.ccs').read_text() for i in (18, 22, 47, 48, 49)}
    original_labels = {}
    for block in doc.dumpEntries:
        if block.name not in doc.renameLabels:
            continue
        for offset, name in doc.renameLabels[block.name].items():
            original_labels[name] = block.offset + offset + 0xC00000

    def check(name, passed):
        checks.append(dict(id=name, passed=bool(passed)))

    def decoded(start, end):
        raw = rom[start - 0xC00000:end - 0xC00000]
        d = dialogue.relocate_bytes(raw, specs, expansions)
        spans.append(dict(start=f'{start:06X}', endExclusive=f'{end:06X}',
                          rawSha256=hashlib.sha256(raw).hexdigest(),
                          opcodeCounts=dict(d.opcodes)))
        return d

    def pinned_label(module, address):
        pattern = re.compile(r'^l_0x' + address.lower() + r':\s*$', re.M)
        at = pattern.search(source[module])
        if not at:
            raise ValueError('Missing pinned entry ' + address)
        rest = source[module][at.end():]
        following = re.search(r'^\w+:', rest, re.M)
        return rest[:following.start()] if following else rest

    for kind, rows in [('doctor', DOCTORS), ('nurse', NURSES)]:
        for index, (town, address, alias, price) in enumerate(rows):
            native_name = 'MSG_SHOP2_' + kind.upper() + '_' + alias
            check(kind + '-' + town + '-original-label', original_labels[native_name] == int(address, 16))
            check(kind + '-' + town + '-pinned-price', bool(re.search(r'counter\(\s*' + str(price) + r'\s*\)', pinned_label(47, address))))
            start = int(address, 16)
            end = int(rows[index + 1][1], 16) if index + 1 < len(rows) else (0xC9008D if kind == 'doctor' else 0xC900F9)
            d = decoded(start, end)
            check(kind + '-' + town + '-original-price', ('store_to_argmem', [price]) in d.operations)
            callee = 0xC90FEC if kind == 'doctor' else 0xC9128D
            check(kind + '-' + town + '-original-callee', any(p[1] == callee and p[2] == 'call_text' for p in d.pointers))
            if town == 'moonside':
                check(kind + '-moonside-original-inversion-bracket',
                      ('set_event_flag', [659]) in d.operations and ('clear_event_flag', [659]) in d.operations)
    for index, (town, address, alias, prices) in enumerate(HEALERS):
        check('healer-' + town + '-original-label', original_labels['MSG_SHOP2_HEALER_' + alias] == int(address, 16))
        for treatment, base in enumerate([0xC91745, 0xC91799, 0xC917ED]):
            start = base + index * 3
            d = decoded(start, start + 3)
            check(f'healer-{town}-price{treatment}-original', d.operations == [('store_to_argmem', [prices[treatment]]), ('end_block', [])])
            check(f'healer-{town}-price{treatment}-pinned', bool(re.search(r'counter\(\s*' + str(prices[treatment]) + r'\s*\)', pinned_label(49, f'{start:06X}'))))
    guard = decoded(0xC680A6, 0xC680C2)
    check('atm-original-card-caller-label', original_labels['MSG_GLOBAL_CASHDISPENSER'] == 0xC680A6)
    check('atm-original-card-guard', ('check_if_character_has_item', [255, 177]) in guard.operations)
    check('atm-original-card-jump', any(p[1] == 0xC62D30 for p in guard.pointers))
    check('atm-redux-card-guard', 'FLG_NESS_KI' in pinned_label(22, 'C680A6') and 'ATM_Start' in pinned_label(22, 'C680A6'))
    atm = decoded(0xC62D30, 0xC63029)
    check('atm-original-five-digits', ('create_number_selector', [5]) in atm.operations)
    check('atm-original-normal-sounds', ('play_sound', [116]) in atm.operations and ('play_sound', [118]) in atm.operations)
    check('atm-redux-refund-before-retry', bool(re.search(r'_maxed_out_cash:\s*deposit\(0\)[\s\S]*?goto\(_withdraw\)', source[18])))
    check('atm-redux-account-preflight', 'check_deposit_money(0)' in source[18])
    check('atm-redux-wallet-preflight', 'try_give_money(0)' in source[18])
    main = (a.project / 'ccscript/main.ccs').read_text()
    for module in ('try_give_money', 'try_deposit_money'):
        check('active-' + module, bool(re.search(r'^import "bugfixes/' + module + r'\.ccs"', main, re.M)))
    doctor = decoded(0xC91259, 0xC9128D)
    nurse = decoded(0xC91345, 0xC913A4)
    check('doctor-original-exact-status-group', [v for n, v in doctor.operations if n == 'inflict_status'] == [[0, 1, 1]])
    check('nurse-original-exact-status-groups', [v for n, v in nurse.operations if n == 'inflict_status'] == [[0, 1, 1], [0, 2, 1], [0, 6, 1]])
    check('nurse-original-hp-pp-target-treatment', ('recover_hp_percent', [0, 100]) in nurse.operations and ('recover_pp_percent', [0, 100]) in nurse.operations)
    # Report exact parsed command names so future reviews do not confuse group
    # 1-based script encodings with native 0-based affliction slots.
    service_ops = {kind: [list(op) for op in d.operations if any(word in op[0] for word in ('status', 'hp', 'pp', 'wallet', 'sound'))]
                   for kind, d in [('doctor', doctor), ('nurse', nurse)]}
    refs = ('ccscript/main.ccs', 'ccscript/data/data_18.ccs', 'ccscript/data/data_22.ccs',
            'ccscript/data/data_47.ccs', 'ccscript/data/data_48.ccs', 'ccscript/data/data_49.ccs',
            'ccscript/bugfixes/try_give_money.ccs', 'ccscript/bugfixes/try_deposit_money.ccs')
    result = dict(schemaVersion=1, toolSha256=sha(__file__), originalRomSha256=sha(a.rom),
                  pinnedReduxCommit='897d00833f4a08a0a92f106abf631629a6a6a041',
                  pinnedSource=[dict(path=p, sha256=sha(a.project / p)) for p in refs],
                  nativeConfigSha256=sha(a.native_source / 'earthbound.yml'),
                  parserSha256=sha(Path(dialogue.__file__)),
                  checks=checks, originalSourceSpans=spans, originalMutationCommands=service_ops,
                  allPassed=all(c['passed'] for c in checks),
                  limits=['Original locally parsed bytecode and pinned textual source contracts; no original-machine execution, dialogue payload or ROM bytes are included.',
                          'Validates selected wrapper entry identity, price, callees, ATM five-digit/cap-preflight contracts and exact parsed treatment commands. It does not prove native transactions; those are in the separate real-dispatch reports.'])
    a.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(checks=len(checks), passed=sum(c['passed'] for c in checks), failures=[c['id'] for c in checks if not c['passed']])))
    if not result['allPassed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
