# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare actual compiled Redux party screen hook with an immutable native build.

Explicit local ROM/pack/source/build paths are required. Original source bodies
and the pinned CCScript hook are fully byte-verified before executing untouched
Redux ROM code with an own caller. All writes stay in fresh private scratch.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from check_jev_observer_parity import local_scratch
from snes_movement_helpers_oracle import sha, US_SHA1
import snes_party_follow_oracle as follow
import snes_position_arithmetic_oracle as identity


def identify(a, out, original, redux):
    wrappers = out / 'identification-wrappers'; wrappers.mkdir()
    routines = []
    for name, relative, abi in follow.ROUTINES[:7]:
        if name in ('CHECK_FOLLOWER_HORIZONTAL_DISTANCE', 'CHECK_FOLLOWER_DIAGONAL_DISTANCE'):
            wrapper = wrappers / (name.lower() + '.asm')
            relative_original = os.path.relpath(a.native_source / 'asm' / relative, wrappers).replace('\\', '/')
            wrapper.write_text('.A16\n.INCLUDE "' + relative_original + '"\n', encoding='utf-8')
            routines.append((name, '../identification-wrappers/' + wrapper.name, abi))
        else:
            routines.append((name, relative, abi))
    old = identity.ROUTINES; identity.ROUTINES = tuple(routines)
    try:
        globals_, mapping, proof = identity.identify(a, out, original)
    finally:
        identity.ROUTINES = old
    bridge = json.loads(a.bridge.read_text(encoding='utf-8'))
    if bridge['source']['revision'] != '897d00833f4a08a0a92f106abf631629a6a6a041' or bridge['roms']['compiled']['sha256'].lower() != hashlib.sha256(redux).hexdigest():
        raise ValueError('Pinned compiled Redux bridge identity differs')
    module = next(r for r in bridge['modules'] if r['name'] == 'party_member_diagonal_fix')
    source = a.project / module['source']; source_hash = sha(source)
    source_record = next(r for r in bridge['sourceGraph']['files'] if r['path'] == module['source'])
    if source_hash.upper() != source_record['sha256']:
        raise ValueError('Pinned source file differs from compiled bridge')
    if 'import "bugfixes/party_member_diagonal_fix.ccs"' not in (a.project / 'ccscript/main.ccs').read_text(encoding='utf-8'):
        raise ValueError('Pinned diagonal fix is not active')
    labels = {r['name']: r['snesAddress'] for r in bridge['labels'] if r['module'] == module['name']}
    if sorted(labels) != ['dirDiagonal', 'dirHorizontal', 'dirVertical', 'newDirectionalUpdateCheck', 'updateDirectionalIndexFuncList']:
        raise ValueError('Pinned hook label layout changed')
    # A literal ca65 transcription of this small pinned DSL module serves ONLY
    # as a byte-identification gate. The actual compiled ROM executes below.
    # Its JSL_RTS macro is PHK/PER+6/PEA(bank RTL-1)/JML/RTS, as source defines.
    asm = r'''
.SEGMENT "CODE"
.A16
.I16
.EXPORT newDirectionalUpdateCheck,updateDirectionalIndexFuncList,dirVertical,dirHorizontal,dirDiagonal
newDirectionalUpdateCheck:
JSR (.LOWORD(updateDirectionalIndexFuncList),X)
ASL
JML $80A290
updateDirectionalIndexFuncList:
.WORD .LOWORD(dirVertical),.LOWORD(dirDiagonal),.LOWORD(dirHorizontal),.LOWORD(dirDiagonal)
.WORD .LOWORD(dirVertical),.LOWORD(dirDiagonal),.LOWORD(dirHorizontal),.LOWORD(dirDiagonal)
dirVertical:
PHK
PER *+9
PEA $0049
JML $C0A2B7
RTS
dirHorizontal:
PHK
PER *+9
PEA $0049
JML $C0A2E1
RTS
dirDiagonal:
LDA $1A42
ASL
TAX
LDA $0B8E,X
SEC
SBC a:$0031
SEC
SBC $0B16,X
BPL :+
EOR #$FFFF
INC
:
CMP #2
BMI :+
LDA #1
RTS
:
LDA $0BCA,X
SEC
SBC a:$0033
SEC
SBC $0B52,X
BPL :+
EOR #$FFFF
INC
:
CMP #2
BMI :+
LDA #1
RTS
:
LDA #0
RTS
'''
    folder = out / 'redux-source-proof'; folder.mkdir()
    asmfile = folder / 'hook.asm'; asmfile.write_text(asm, encoding='utf-8')
    cfg = folder / 'hook.cfg'; cfg.write_text(f'MEMORY {{ ROM:start=${module["snes_address"]:06X},size=$10000,type=ro,file=%O; }}\nSEGMENTS {{ CODE:load=ROM,type=ro; }}\n', encoding='utf-8')
    obj = folder / 'hook.o'; blob = folder / 'hook.bin'; lbl = folder / 'hook.lbl'
    identity.run([a.ca65, '--cpu', '65816', asmfile, '-o', obj], folder / 'compile.log')
    identity.run([a.ld65, '-C', cfg, '-o', blob, '-Ln', lbl, obj], folder / 'link.log')
    actual = redux[module['rom_offset']:module['rom_offset'] + module['size']]
    if blob.read_bytes() != actual or sha(blob).upper() != module['compiled_sha256']:
        raise ValueError('Complete pinned module bytes do not match transcription')
    emitted = identity.labels(lbl)
    if any(emitted.get(name) != address for name, address in labels.items()):
        raise ValueError('Complete hook labels differ from compiled source mapping')
    update = next(r for r in proof if r['symbol'] == 'UPDATE_PARTY_SPRITE_POSITION')
    at = int(update['address'], 16) - 0xC00000
    expected = bytearray(original[at:at + update['byteEqualLength']])
    offset = 0xA28C - 0xA26B
    expected[offset:offset + 4] = bytes((0x5C,)) + labels['newDirectionalUpdateCheck'].to_bytes(3, 'little')
    if redux[at:at + len(expected)] != expected:
        raise ValueError('Redux party routine differs outside its reviewed active hook')
    for record in proof:
        if record['symbol'] in ('UPDATE_PARTY_SPRITE_POSITION', 'MOVEMENT_SPEEDS', 'ALLOWED_INPUT_DIRECTIONS'):
            continue
        addr = int(record['address'], 16) - 0xC00000; length = record['byteEqualLength']
        if redux[addr:addr + length] != original[addr:addr + length]:
            raise ValueError('Additional active dependency differs: ' + record['symbol'])
    for name, address in (('CURRENT_ENTITY_SLOT', 0x1A42), ('ENTITY_ABS_X_TABLE', 0x0B8E), ('ENTITY_ABS_Y_TABLE', 0x0BCA),
                          ('ENTITY_SCREEN_X_TABLE', 0x0B16), ('ENTITY_SCREEN_Y_TABLE', 0x0B52), ('BG1_X_POS', 0x31), ('BG1_Y_POS', 0x33)):
        if globals_[name] & 65535 != address:
            raise ValueError('Pinned hook global ABI differs from mapped original RAM: ' + name)
    proof.append({'symbol': 'party_member_diagonal_fix', 'address': f'{module["snes_address"]:06X}',
                  'byteEqualLength': len(actual), 'byteEqualSha256': sha(blob),
                  'PinnedSourceSha256': source_hash, 'ActiveImportVerified': True,
                  'CompleteCompiledModuleByteEqual': True, 'PatchAddress': 'C0A28C',
                  'ActualSourceLabels': {k: f'{v:06X}' for k, v in labels.items()}})
    return globals_, mapping, proof


def machine(a, out, globals_, mapping, cases, mode='redux'):
    out.mkdir(); samples = out / 'samples.jsonl'
    w = lambda key: globals_[key] & 65535
    code = bytearray.fromhex('78d818fbc230a2ff1f9aa900185be220a97e48abc230')
    entry = 0xC0FF00 + len(code)
    code.extend((0x20, mapping['UPDATE_PARTY_SPRITE_POSITION'] & 255, mapping['UPDATE_PARTY_SPRITE_POSITION'] >> 8 & 255))
    code.extend(bytes.fromhex('7b8f08707e3b8f0a707e'))
    finish = 0xC0FF00 + len(code); code.extend((0x5C, entry & 255, entry >> 8 & 255, entry >> 16))
    fields = follow.FIELDS
    lua = ['local output=assert(io.open(' + json.dumps(samples.as_posix()) + ',"wb"))',
           'local rows={' + ','.join('{' + ','.join(map(str, (c[k] for k in fields))) + '}' for c in cases) + '}',
           'local mem=emu.memType.snesWorkRam',
           'local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256)%256,mem) end',
           'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end',
           'local index=0;local calls=0;w16(0xe800,0x55aa)',
           'emu.addMemoryCallback(function() index=index+1;local c=assert(rows[index],"past corpus");',
           f'w16({w("CURRENT_ENTITY_SLOT")},c[10]);w16(0x1888,2*c[10]);'
           f'w16({w("CURRENT_LEADING_PARTY_MEMBER_ENTITY")},2*c[9]);w16({w("CURRENT_LEADER_DIRECTION")},c[7]);'
           f'w16({w("NOT_MOVING_IN_SAME_DIRECTION_FACED")},c[8]==1 and 1 or 0);'
           f'w16({w("ENTITY_DIRECTIONS")}+2*c[10],c[8]==2 and (c[7]+1)%8 or c[7]);'
           f'w16({w("ENTITY_SCRIPT_VAR7_TABLE")}+2*c[10],c[5]);w16({w("ENTITY_SCRIPT_VAR5_TABLE")}+2*c[10],2*c[11]);',
           f'w16({w("ENTITY_ABS_X_TABLE")}+2*c[10],c[12]);w16({w("ENTITY_ABS_Y_TABLE")}+2*c[10],c[13]);'
           f'w16({w("ENTITY_ABS_X_TABLE")}+2*c[9],c[14]);w16({w("ENTITY_ABS_Y_TABLE")}+2*c[9],c[15]);'
           f'w16({w("ENTITY_SCREEN_X_TABLE")}+2*c[10],c[16]);w16({w("ENTITY_SCREEN_Y_TABLE")}+2*c[10],c[17]);'
           f'w16({w("ENTITY_SCREEN_X_TABLE")}+2*c[9],c[18]);w16({w("ENTITY_SCREEN_Y_TABLE")}+2*c[9],c[19]);'
           f'w16({w("BG1_X_POS")},c[20]);w16({w("BG1_Y_POS")},c[21]);end,emu.callbackType.exec,{entry})',
           f'emu.addMemoryCallback(function() calls=calls+1 end,emu.callbackType.exec,{mapping["UPDATE_PARTY_SPRITE_POSITION"]})',
           'emu.addMemoryCallback(function() local c=rows[index];assert(r16(0x7008)==0x1800 and r16(0x700a)==0x1fff,"CPU frame corrupt");'
           'assert(r16(0xe800)==0x55aa,"protected RAM corrupt");'
           f'output:write(string.format("[%d,0,%d,%d,%d]\\n",index,r16({w("ENTITY_SCRIPT_VAR7_TABLE")}+2*c[10]),r16({w("ENTITY_SCREEN_X_TABLE")}+2*c[10]),r16({w("ENTITY_SCREEN_Y_TABLE")}+2*c[10])));'
           'if index==#rows then assert(calls==#rows,"call count differs");output:flush();output:close();emu.log("REDUX_PARTY_SCREEN_COMPLETE "..index);emu.breakExecution() end '
           f'end,emu.callbackType.exec,{finish})']
    # The pinned hook intentionally JMLs to bank80's retail continuation.
    # RTS keeps that bank. Mirror ONLY our private caller at the corresponding
    # expanded-ROM location, and use JML to re-enter C0 for the next call so
    # every sample executes the patched C0 entry rather than the retail mirror.
    lua.append(lua[-1].replace(f',emu.callbackType.exec,{finish})', f',emu.callbackType.exec,{finish-0x400000})'))
    script = out / 'redux-party.lua'; script.write_text('\n'.join(lua) + '\n', encoding='utf-8')
    rom = a.redux_rom if mode == 'redux' else a.rom
    mirror = ['--write-memory', 'SnesPrgRom:0x40ff00:' + code.hex()] if mode == 'redux' else []
    proc = subprocess.run([str(a.oracle.resolve()), str(rom.resolve()), '--home', str(out / 'oracle-home'),
                           '--frames', '5000', '--timeout', '60', '--lua-timeout', '10', '--lua-allow-io', '--lua', str(script),
                           '--write-memory', 'SnesPrgRom:0xff00:' + code.hex(), *mirror,
                           '--set-pc', '0xc0ff00', '--cpu', 'Snes'], capture_output=True, timeout=70)
    (out / 'oracle.jsonl').write_bytes(proc.stdout); (out / 'oracle.stderr').write_bytes(proc.stderr)
    events = [json.loads(x) for x in proc.stdout.decode().splitlines()]; logs = [r for r in events if r['event'] == 'lua_log']
    if proc.returncode or not events[-1].get('ok') or events[-1].get('reason') != 'debugger_break' or any(r['error_count'] for r in logs):
        raise ValueError('Actual Redux machine corpus incomplete')
    if sum('REDUX_PARTY_SCREEN_COMPLETE ' + str(len(cases)) in r['text'] for r in logs) != 1:
        raise ValueError('Missing exact Redux completion marker')
    got = [json.loads(x) for x in samples.read_text(encoding='utf-8').splitlines()]
    if [r[0] for r in got] != list(range(1, len(cases) + 1)):
        raise ValueError('Redux samples incomplete/out of order')
    return got, {'Calls': len(got), 'StackDirectPageProtectedRamPassed': True, 'CallerSha256': hashlib.sha256(code).hexdigest(),
                 'LuaSha256': sha(script), 'SamplesSha256': sha(samples), 'ActualCompiledReduxCodeExecuted': mode == 'redux',
                 'OwnCallerMirroredForPinnedBank80Return': mode == 'redux', 'EverySampleReentersC0Entry': True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('rom', 'redux-rom', 'project', 'bridge', 'oracle', 'ca65', 'ld65', 'native-source', 'build', 'runtime',
                 'original-assets', 'redux-assets', 'scratch', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--corrected-callback-source', type=Path)
    p.add_argument('--previous-report', type=Path)
    p.add_argument('--diagnostic', action='store_true')
    a = p.parse_args(); a.scratch = local_scratch(a.scratch)
    a.native_source = a.native_source.resolve(); a.build = a.build.resolve(); a.runtime = a.runtime.resolve()
    if a.scratch.exists() or a.output.exists():
        raise ValueError('Fresh scratch/output required')
    original = a.rom.read_bytes(); redux = a.redux_rom.read_bytes()
    if len(original) != 0x300000 or hashlib.sha1(original).hexdigest() != US_SHA1:
        raise ValueError('Exact clean USA ROM required')
    inputs = {str(path): sha(path) for path in (a.rom, a.redux_rom, a.bridge, a.project / 'ccscript/main.ccs',
               a.project / 'ccscript/bugfixes/party_member_diagonal_fix.ccs', a.build / 'game_lib/libearthbound_game.a',
               a.runtime / 'player.exe', a.runtime / 'observer.exe', a.original_assets, a.redux_assets,
               a.native_source / 'src/entity/callbacks.c', Path(__file__), Path(follow.__file__), Path(identity.__file__))}
    a.scratch.mkdir(parents=True); globals_, mapping, proof = identify(a, a.scratch, original, redux)
    cases = [r for r in follow.corpus() if r['kind'] == 'screen']
    seed = cases[0]
    for direction in range(8):
        for ordinal in range(1, 6):
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    c = dict(seed, direction=direction, ordinal=ordinal, flags=0, notAligned=0,
                             group='predicted-screen-speed-transition-threshold', screenX=80 + dx, screenY=90 + dy,
                             leaderX=500 - 11 * ordinal, leaderY=600 - 11 * ordinal,
                             leaderScreenX=80 - 11 * ordinal, leaderScreenY=90 - 11 * ordinal)
                    cases.append(c)
    modes = []; differences = []
    for mode in ('original', 'redux'):
        reference, meta = machine(a, a.scratch / ('actual-' + mode + '-machine'), globals_, mapping, cases, mode)
        native, nmeta = follow.native(a, a.scratch / ('native-' + mode), cases, mode)
        diff = [dict(cases[i], Index=i + 1, Mode=mode, ActualSourceMachine=ref[1:], ActualNative=got[1:])
                for i, (ref, got) in enumerate(zip(reference, native)) if ref != got]
        differences.extend(diff)
        modes.append({'Mode': mode, 'ExecutedCases': len(cases), 'NativeMismatchCount': len(diff),
                      'MismatchesByDirection': dict(Counter(r['direction'] for r in diff)),
                      'MachineEvidence': meta, 'NativeEvidence': nmeta})
    previous = None
    if a.previous_report:
        red = json.loads(a.previous_report.read_text(encoding='utf-8'))
        if red.get('format') != 'redux-party-screen-micro-oracle-v1' or red['Passed'] or not red['NativeMismatchCount']:
            raise ValueError('Expected preserved completed Redux red evidence')
        previous = {'Path': a.previous_report.as_posix(), 'Sha256': sha(a.previous_report), 'NativeMismatchCount': red['NativeMismatchCount']}
    if any(sha(Path(path)) != value for path, value in inputs.items()):
        raise ValueError('Immutable input changed during audit')
    report = {'format': 'redux-party-screen-micro-oracle-v1', 'Passed': not differences, 'ExecutedCases': len(cases),
              'NativeMismatchCount': len(differences), 'MismatchesByDirection': dict(Counter(r['direction'] for r in differences)),
              'NativeMismatches': differences, 'SourceProof': proof, 'Modes': modes,
              'InputIdentities': inputs, 'PreservedRedBaseline': previous, 'OwnerSavesTouched': False, 'SharedBuildChanged': False,
              'Limits': ['Actual pinned Redux hook and Original cardinal dependencies execute unchanged; Original-only screen equality is not Redux parity.',
                         'Prepared aligned/unaligned and screen-distance contexts include synthetic speed-transition geometry; full story coverage remains false.',
                         'These checks concern screen-coordinate smoothing only; entity absolute movement and collision are not changed.']}
    a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('Passed', 'ExecutedCases', 'NativeMismatchCount', 'MismatchesByDirection')}), flush=True)
    if not report['Passed'] and not a.diagnostic:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
