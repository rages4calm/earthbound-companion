# SPDX-License-Identifier: GPL-3.0-or-later
"""Observe the untouched USA GET_CHARACTER_ITEM routine on an explicit local ROM.

The reference executes the complete original routine and multiply helper, using
a private caller in emulator memory. Source assembly identifies byte-equal
functions; it does not supply the executed reference. No ROM bytes are exported.
The C5E431 script caller is reviewed separately and is not executed here.
"""
import argparse, hashlib, json, re, subprocess
from pathlib import Path
import snes_position_arithmetic_oracle as mapping
from check_jev_observer_parity import local_scratch


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('rom', 'oracle', 'ca65', 'ld65', 'native-source', 'project', 'scratch', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    image = a.rom.read_bytes()
    if len(image) != 0x300000 or hashlib.sha1(image).hexdigest() != mapping.US_SHA1:
        raise ValueError('Exact clean unheadered USA ROM required.')
    out = local_scratch(a.scratch)
    if out.exists():
        raise ValueError('Choose a fresh scratch directory.')
    out.mkdir(parents=True)
    saved = mapping.ROUTINES
    mapping.ROUTINES = (('MULT168', 'system/math/mult168.asm', 'far'),
                        ('GET_CHARACTER_ITEM', 'misc/get_character_item.asm', 'far'))
    try:
        globals_, known, evidence = mapping.identify(a, out, image)
    finally:
        mapping.ROUTINES = saved
    # Export the actual source structure size/field offsets through ca65,
    # rather than introducing an unchecked duplicate layout in the fixture.
    folder = out / 'source-mapping'
    source = folder / 'item-layout.asm'
    source.write_text('.INCLUDE "common.asm"\n.INCLUDE "config.asm"\n.INCLUDE "structs.asm"\n'
                      '.EXPORT ITEM_OFFSET, CHARACTER_SIZE\nITEM_OFFSET = char_struct::items\n'
                      'CHARACTER_SIZE = .SIZEOF(char_struct)\n.SEGMENT "CODE"\n.BYTE 0\n', encoding='utf-8')
    includes = ['--cpu', '65816', '-D', 'USA', '-I', folder / 'include-overlay',
                '-I', a.native_source / 'include', '-I', a.native_source / 'asm']
    mapping.run([a.ca65, *includes, source, '-o', source.with_suffix('.o')], source.with_suffix('.compile.log'))
    mapping.run([a.ld65, '-C', folder / 'code.cfg', '-o', source.with_suffix('.bin'),
                 '-Ln', source.with_suffix('.lbl'), source.with_suffix('.o')], source.with_suffix('.link.log'))
    layout = mapping.labels(source.with_suffix('.lbl'))
    item_base = globals_['PARTY_CHARACTERS'] - 0x7E0000 + layout['ITEM_OFFSET']
    stride = layout['CHARACTER_SIZE']
    cases = [(char, slot, item) for char in range(1, 7) for slot in range(1, 15)
             for item in (0, 87, 166, 196, 255)]
    stub = bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
    entry = 0xC0FF00 + len(stub)
    stub += bytes.fromhex('af02717eaaaf00717e22') + known['GET_CHARACTER_ITEM'].to_bytes(3, 'little')
    stub += bytes.fromhex('8f00707e7b8f08707e3b8f0a707e')
    finish = 0xC0FF00 + len(stub)
    stub += bytes((0x4C, entry & 255, (entry >> 8) & 255))
    samples = out / 'samples.tsv'
    lua = ['local output=assert(io.open(' + json.dumps(samples.resolve().as_posix()) + ',"wb"))',
           'local cases={' + ','.join('{' + ','.join(map(str, c)) + '}' for c in cases) + '}',
           'local mem=emu.memType.snesWorkRam',
           'local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256),mem) end',
           'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end', 'local index=0',
           'emu.addMemoryCallback(function() index=index+1;local c=assert(cases[index],"extra case");'
           'w16(0x7100,c[1]);w16(0x7102,c[2]);',
           f'for char=0,5 do for slot=0,13 do emu.write({item_base}+char*{stride}+slot,0,mem) end end',
           f'emu.write({item_base}+(c[1]-1)*{stride}+c[2]-1,c[3],mem)',
           f'end,emu.callbackType.exec,{entry})',
           'emu.addMemoryCallback(function() assert(r16(0x7008)==0x1000,"D canary");'
           'assert(r16(0x700a)==0x1fff,"stack canary");'
           'output:write(string.format("%d,%d\\n",index,r16(0x7000)));'
           'if index==#cases then output:flush();output:close();emu.log("CORPUS_COMPLETE");emu.breakExecution() end',
           f'end,emu.callbackType.exec,{finish})']
    script = out / 'oracle.lua'
    script.write_text('\n'.join(lua) + '\n', encoding='utf-8')
    run = subprocess.run([str(a.oracle.resolve()), str(a.rom.resolve()), '--home', str(out / 'oracle-home'),
                          '--frames', '1000', '--timeout', '60', '--lua-timeout', '10', '--lua-allow-io',
                          '--lua', str(script.resolve()), '--write-memory', 'SnesPrgRom:0xff00:' + stub.hex(),
                          '--set-pc', '0xc0ff00', '--cpu', 'Snes'], capture_output=True, timeout=70)
    (out / 'oracle.jsonl').write_bytes(run.stdout)
    (out / 'oracle.stderr').write_bytes(run.stderr)
    logs = [json.loads(line) for line in run.stdout.decode().splitlines()]
    events = [r for r in logs if r.get('event') == 'lua_log']
    end = logs[-1] if logs else {}
    if run.returncode or not end.get('ok') or end.get('reason') != 'debugger_break' or any(r['error_count'] for r in events):
        raise RuntimeError('Machine did not complete cleanly.')
    lines = samples.read_text().splitlines()
    if len(lines) != len(cases) or not any('CORPUS_COMPLETE' in r['text'] for r in events):
        raise RuntimeError('Incomplete corpus.')
    rows = []
    for i, (char, slot, item) in enumerate(cases, 1):
        found = re.fullmatch(r'(\d+),(\d+)', lines[i - 1])
        if not found or int(found[1]) != i:
            raise RuntimeError('Missing, duplicate or out-of-order sample.')
        actual = int(found[2])
        rows.append(dict(character=char, slot=slot, item=item, machine=actual, passed=actual == item))
    if sha(a.rom) != hashlib.sha256(image).hexdigest():
        raise RuntimeError('Owner ROM changed.')
    relative = ('ccscript/data/data_15.ccs', 'ccscript/data/data_20.ccs', 'ccscript/shops/ShopSys.ccs')
    refs = [{'path': 'native-source/asm/' + rel, 'sha256': sha(a.native_source / 'asm' / rel)}
            for rel in ('misc/get_character_item.asm', 'text/ccs/get_item_number.asm')]
    refs += [{'path': pth, 'sha256': sha(a.project / pth)} for pth in relative]
    report = dict(schemaVersion=1, toolVersion='dev20-original-inventory-slot-machine', allPassed=all(r['passed'] for r in rows),
                  executedMachineCases=len(rows), cases=rows, sourceReferences=refs,
                  romSha256=hashlib.sha256(image).hexdigest(), oracleSha256=sha(a.oracle),
                  oracleCoreSha256=sha(a.oracle.parent / 'MesenCore.dll'), sourceMapping=evidence,
                  sourceLayout=dict(characterSize=stride, itemOffset=layout['ITEM_OFFSET']),
                  helperScriptAddress='C5E431', helperScriptLength=37,
                  helperScriptSha256=hashlib.sha256(image[0x5E431:0x5E456]).hexdigest(),
                  stackAndDirectPageCanariesPassed=True, ownerRomUnchanged=True,
                  limits=['Untouched GET_CHARACTER_ITEM and MULT168 execution with prepared valid character/slot fields.',
                          'The C5E431 script and its callers are source-reviewed; their full original interpreter was not executed here.',
                          'Original has no native Key Pool. Pool-aware preflight is an explicit PC QoL adaptation, not a claimed SNES feature.',
                          'No source script bytes, ROM, emulator or game assets are included in this public report.'])
    a.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(allPassed=report['allPassed'], executedMachineCases=len(rows))))
    if not report['allPassed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
