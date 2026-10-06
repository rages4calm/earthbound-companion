# SPDX-License-Identifier: GPL-3.0-or-later
"""Inventory active movement operands that native handlers silently bound-check.

This is structural donor-bytecode evidence, not proof of opcode semantics.
The original all-root CFG analysis is reused without changing its shipped tool.
"""
import argparse
import hashlib
import inspect
import json
import re
import struct
import sys
from pathlib import Path
import audit_redux_movement as movement
from build_maternalbound_pack import read_pack


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def inventory(pack, native, redux):
    fn = inspect.getsource(movement.audit)
    replacements = {
        'def audit(assets, native_source):':'def audit(assets, native_source, redux):',
        'sizes.update({0x32:0,0x33:0})':'\n    if redux: sizes.update({0x32:0,0x33:0})',
        'if opcode in (0x03,0x04,0x31):':'if opcode in ((0x03,0x04,0x31) if redux else (0x03,0x04)):',
        '    opcodes=Counter(op for addr,op in opcodes.items() if addr in reachable)':
        '    operand_records=[(addr,op,read(addr+1,sizes[op] if sizes[op]!=255 else 1)) for addr,op in opcodes.items() if addr in reachable]\n    opcodes=Counter(op for addr,op in opcodes.items() if addr in reachable)',
        'return {"Roots":len(roots),':'return {"OperandRecords":operand_records,"Roots":len(roots),'
    }
    for old, new in replacements.items():
        if fn.count(old) != 1:
            raise ValueError('Upstream traversal changed; review adaptation: '+old)
        fn = fn.replace(old,new)
    scope = dict(vars(movement))
    exec(fn,scope)
    if not redux:
        from ebtools.parsers.original_movement_banks import decode_original_movement_banks
        raw = pack['US/events/bank_c3_scripts_combined.bin']
        regions = decode_original_movement_banks(raw)
        actual = [(0xC3,0,regions[0] if regions else raw),
                  (0xC4,0x0E24,pack['US/events/bank_c4_scripts.bin']),
                  (0xC4,0x2172,pack['US/intro/title_screen_scripts.bin'])]
        if regions:
            actual.append((0xC0,0xAD8A,regions[1]))
        container = bytearray(struct.pack('<8sI',b'MRMVBN01',len(actual)))
        for bank, base, data in actual:
            container.extend(struct.pack('<BBHI',bank,0,base,len(data)))
            container.extend(data)
        pack = dict(pack)
        pack['US/events/bank_c3_scripts_combined.bin'] = bytes(container)
    result = scope['audit'](pack,native,redux)
    records = result.pop('OperandRecords')
    evidence = []
    for address, opcode, args in records:
        def bounded(kind,value,limit):
            evidence.append({'address':f'{address:06X}','opcode':f'{opcode:02X}',
                             'kind':kind,'value':value,'exclusiveUpperBound':limit,'accepted':value<limit})
        if opcode in (0x0E,0x14,0x1F,0x20,0x21,0x26):
            bounded('entity-variable-index',args[0],8)
        if opcode in (0x0D,0x18):
            bounded('callback-operation-index',args[2],4)
        elif opcode == 0x14:
            bounded('callback-operation-index',args[1],4)
        elif opcode == 0x27:
            bounded('callback-operation-index',args[0],4)
        if opcode in range(0x31,0x39) and not (redux and opcode in (0x31,0x32,0x33)):
            bounded('background-layer-index',args[0],4)
        elif opcode == 0x3A:
            bounded('background-layer-index',args[0],4)
    result['silentBoundChecks'] = evidence
    result['rejectedActiveOperands'] = [r for r in evidence if not r['accepted']]
    source = (native/'src/entity/callroutine.c').read_text()
    header = (native/'src/data/event_script_data.h').read_text()
    definitions = {name:int(value,16) for name,value in re.findall(r'#define (ROM_ADDR_\w+)\s+(0x[0-9A-Fa-f]+)',header)}
    known = source.split('known_callroutine_addrs[]',1)[1].split('};',1)[0]
    addresses = {definitions[n] for n in re.findall(r'ROM_ADDR_\w+',known)}
    collisions = {f'{word:04X}':sorted(f'{addr:06X}' for addr in addresses if addr&0xFFFF==word)
                  for word in {addr&0xFFFF for addr in addresses}
                  if len({addr for addr in addresses if addr&0xFFFF==word})>1}
    result['knownCallroutineLowWordRecovery'] = {'addresses':len(addresses),'ambiguousLowWords':collisions}
    result['Passed'] = result['Passed'] and not result['rejectedActiveOperands'] and not collisions
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('native-source','original-assets','redux-assets','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a = p.parse_args()
    sys.path.insert(0,str(a.native_source.resolve()))
    ids = a.native_source/'src/data/runtime_generated/asset_ids.h'
    records = {}
    for profile,path in (('Original',a.original_assets),('Redux',a.redux_assets)):
        pack = read_pack(path,ids)[2]
        records[profile] = inventory(pack,a.native_source,profile=='Redux')
        records[profile]['packSha256'] = digest(path)
    passed = all(r['Passed'] for r in records.values())
    out = {'format':'event-interpreter-operand-inventory-v1','Passed':passed,'allPassed':passed,
           'structuralRoots':sum(r['Roots'] for r in records.values()),
           'executedRuntimeCases':0,'boundedOperandSites':sum(len(r['silentBoundChecks']) for r in records.values()),
           'profiles':records,'toolSha256':digest(Path(__file__)),
           'traversalDependencySha256':digest(Path(movement.__file__)),
           'sourceFiles':{name:digest(a.native_source/name) for name in ('src/entity/opcodes.c','src/entity/callroutine.c','src/data/event_script_data.h')},
           'limits':['All nonzero pointer roots and conservative CFG branches are scanned; this is not a dynamic story trace.',
                     'No opcode semantic parity or full interpreter completion claim follows from recognized operands.',
                     'Silent bounds covered: eight entity variables, four callback operations and four background layers; other native conditional fallbacks need separate source/runtime verification.',
                     'Known callroutine bank-zero recovery is checked for low-word ambiguity, not for any claim that a dropped bank byte is correct game data.',
                     'No ROM byte arrays or assets are included. Values in bounded operands are only indices and callback-operation IDs.']}
    a.output.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'allPassed':passed,'roots':out['structuralRoots'],'boundedOperands':out['boundedOperandSites'],
                      'rejected':{p:r['rejectedActiveOperands'] for p,r in records.items()}}))
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
