# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare native stat-growth source against untouched original CPU execution.

All inputs are explicit local paths. Reassembly identifies complete original
function bodies and the actual modifier-table pointer, then the owner ROM runs
unchanged in isolated emulator memory with only our caller injected. Fresh
scratch holds generated blobs and samples; no owner save, pack or ROM is written.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

from check_jev_observer_parity import local_scratch
from snes_movement_helpers_oracle import sha, US_SHA1
import snes_position_arithmetic_oracle as mapping
import snes_rand_mod_oracle as rand_mapping
from build_maternalbound_pack import read_pack


def identify(a, out, rom):
    previous = mapping.ROUTINES
    try:
        globals_, addresses, evidence = rand_mapping.identify(a, out, rom)
    finally:
        mapping.ROUTINES = previous
    folder = out / 'source-mapping'
    base = (folder / 'rand.asm').read_text(encoding='utf-8').split('MOVEMENT_SPEEDS :=', 1)[0]
    include = ['--cpu', '65816', '-D', 'USA', '-I', folder / 'include-overlay',
               '-I', a.native_source / 'include', '-I', a.native_source / 'asm']

    def assemble(symbol, relative, extra='', suffix=''):
        source = folder / (symbol.lower() + suffix + '.asm')
        source.write_text(base + ''.join(f'{k} := ${v:06X}\n' for k, v in addresses.items() if k != symbol) +
                          extra + '.SEGMENT "CODE"\n.A16\n.I16\n.INCLUDE "' + relative + '"\n',
                          encoding='utf-8')
        obj = source.with_suffix('.o'); blob = source.with_suffix('.bin')
        mapping.run([a.ca65, *include, source, '-o', obj, '-l', source.with_suffix('.lst')],
                    source.with_suffix('.compile.log'))
        mapping.run([a.ld65, '-C', folder / 'code.cfg', '-o', blob, obj], source.with_suffix('.link.log'))
        return blob

    for symbol, relative in (('MULT16', 'system/math/mult16.asm'),
                             ('MODULUS16S', 'system/math/modulus16s.asm'),
                             ('DIVISION16', 'system/math/division16.asm'),
                             ('STATS_GROWTH_VARS', 'data/stats_growth_vars.asm')):
        blob = assemble(symbol, relative)
        addresses[symbol] = mapping.find_unique(rom, blob.read_bytes(), symbol)
        evidence.append({'symbol': symbol, 'address': f'{addresses[symbol]:06X}',
                         'originalSource': relative, 'byteEqualLength': blob.stat().st_size,
                         'byteEqualSha256': sha(blob)})
    # Four bytes alone need not be unique. Locate the pointer through the whole
    # actual function, relink at that pointer, and require full unmasked equality.
    relative = 'text/calculate_stat_gain.asm'
    first = assemble('CALCULATE_STAT_GAIN', relative, 'STAT_GAIN_MODIFIER_TABLE := $C00000\n', '-placeholder')
    second = assemble('CALCULATE_STAT_GAIN', relative, 'STAT_GAIN_MODIFIER_TABLE := $C10101\n', '-placeholder2')
    data, altered = first.read_bytes(), second.read_bytes()
    offsets = [i for i, (x, y) in enumerate(zip(data, altered)) if x != y]
    if len(data) != len(altered) or len(offsets) != 3 or offsets != list(range(offsets[0], offsets[0] + 3)):
        raise ValueError('Modifier pointer relocation changed unexpectedly')
    pattern = b''.join(b'.' if i in offsets else re.escape(bytes((v,))) for i, v in enumerate(data))
    matches = list(re.finditer(pattern, rom, re.S))
    if len(matches) != 1:
        raise ValueError('Complete original stat function candidate is not unique')
    entry = matches[0].start()
    pointer = int.from_bytes(rom[entry + offsets[0]:entry + offsets[0] + 3], 'little')
    addresses['STAT_GAIN_MODIFIER_TABLE'] = pointer
    table = assemble('STAT_GAIN_MODIFIER_TABLE', 'data/stat_gain_modifier_table.asm')
    table_data = table.read_bytes()
    if rom[pointer - 0xC00000:pointer - 0xC00000 + len(table_data)] != table_data:
        raise ValueError('Original function points to a different modifier table')
    blob = assemble('CALCULATE_STAT_GAIN', relative)
    addresses['CALCULATE_STAT_GAIN'] = mapping.find_unique(rom, blob.read_bytes(), 'CALCULATE_STAT_GAIN')
    if addresses['CALCULATE_STAT_GAIN'] != entry + 0xC00000:
        raise ValueError('Relinked original entry differs')
    evidence.extend(({'symbol': 'STAT_GAIN_MODIFIER_TABLE', 'address': f'{pointer:06X}',
                      'originalSource': 'data/stat_gain_modifier_table.asm',
                      'pointerResolvedFromCompleteOriginalFunction': True,
                      'byteEqualLength': len(table_data), 'byteEqualSha256': sha(table)},
                     {'symbol': 'CALCULATE_STAT_GAIN', 'address': f'{addresses["CALCULATE_STAT_GAIN"]:06X}',
                      'originalSource': relative, 'byteEqualLength': blob.stat().st_size,
                      'byteEqualSha256': sha(blob), 'abi': 'near; A=old level; caller DP+14 decimal (0x0e)=growth, +15 decimal (0x0f)=base'}))
    return globals_, addresses, evidence, table_data, (folder / 'stats_growth_vars.bin').read_bytes()


def machine(a, out, globals_, addresses, rows):
    out.mkdir(); samples = out / 'samples.jsonl'
    start = (addresses['CALCULATE_STAT_GAIN'] & 0xFF0000) | 0xFF00
    # Native mode, A/X/Y16, SP1FFF, caller DP1000, DBR7E. A near JSR stays
    # within the original function bank. DP parameters follow the source frame.
    code = bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
    entry = start + len(code)
    code += bytes.fromhex('af00717e') + bytes((0x20, addresses['CALCULATE_STAT_GAIN'] & 255,
                                            addresses['CALCULATE_STAT_GAIN'] >> 8 & 255))
    code += bytes.fromhex('8f00707e7b8f08707e3b8f0a707e')
    finish = start + len(code)
    code += bytes((0x4C, entry & 255, entry >> 8 & 255))
    for record in a.source_proof:
        if 'byteEqualLength' in record:
            pos = int(record['address'], 16)
            if max(pos, start) < min(pos + record['byteEqualLength'], start + len(code)):
                raise ValueError('Private caller overlaps an executed original body/table')
    ga, gb = globals_['RAND_A'] & 65535, globals_['RAND_B'] & 65535
    diagnostics = out / 'intermediates.jsonl'
    lua = ['local output=assert(io.open(' + json.dumps(samples.as_posix()) + ',"wb"))',
           'local debug=assert(io.open(' + json.dumps(diagnostics.as_posix()) + ',"wb"))',
           'local rows={' + ','.join('{' + ','.join(map(str, r)) + '}' for r in rows) + '}',
           'local mem=emu.memType.snesWorkRam',
           'local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256)%256,mem) end',
           'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end',
           'local index=0;local calls=0;local randcalls=0;local previous=0;local roll=-1;local cycle=-1;local product=-1;w16(0x7200,0x55aa)',
           'emu.addMemoryCallback(function() index=index+1;local r=assert(rows[index],"past corpus");'
           'w16(0x7100,r[2]);emu.write(0x100e,r[1],mem);emu.write(0x100f,r[3],mem);'
           f'w16({ga},r[4]%65536);w16({gb},math.floor(r[4]/65536));previous=randcalls;roll=-1;cycle=-1;product=-1 end,emu.callbackType.exec,{entry})',
           f'emu.addMemoryCallback(function() calls=calls+1 end,emu.callbackType.exec,{addresses["CALCULATE_STAT_GAIN"]})',
           f'emu.addMemoryCallback(function() randcalls=randcalls+1 end,emu.callbackType.exec,{addresses["RAND"]})',
           'emu.addMemoryCallback(function() assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"CPU frame corrupted");'
           'assert(r16(0x7200)==0x55aa,"protected RAM corrupted");'
           f'output:write(string.format("[%d,%d,%d,%d,%d]\\n",index,r16(0x7000),r16({ga}),r16({gb}),randcalls-previous));'
           'debug:write(string.format("[%d,%d,%d,%d]\\n",index,roll,cycle,product));'
           'if index==#rows then assert(calls==#rows,"call count differs");output:flush();output:close();debug:flush();debug:close();'
           'emu.log("STAT_GROWTH_COMPLETE "..calls);emu.breakExecution() end '
           f'end,emu.callbackType.exec,{finish})']
    calc = (a.scratch / 'source-mapping/calculate_stat_gain.bin').read_bytes()
    for name, variable, last in (('RAND_MOD', 'roll', False), ('MODULUS16S', 'cycle', False), ('MULT16', 'product', True)):
        call = bytes((0x22,)) + addresses[name].to_bytes(3, 'little')
        at = calc.rfind(call) if last else calc.find(call)
        if at < 0 or (not last and calc.count(call) != 1):
            raise ValueError('Original intermediate call site not identified')
        lua.append(f'emu.addMemoryCallback(function() {variable}=emu.getState()["cpu.a"] end,emu.callbackType.exec,{addresses["CALCULATE_STAT_GAIN"]+at+4})')
    script = out / 'stat-growth.lua'; script.write_text('\n'.join(lua) + '\n', encoding='utf-8')
    proc = subprocess.run([str(a.oracle.resolve()), str(a.rom.resolve()), '--home', str(out / 'oracle-home'),
                           '--frames', '2000', '--timeout', '60', '--lua-timeout', '10', '--lua-allow-io',
                           '--lua', str(script), '--write-memory', f'SnesPrgRom:{start-0xC00000:#x}:' + code.hex(),
                           '--set-pc', hex(start), '--cpu', 'Snes'], capture_output=True, timeout=70)
    (out / 'oracle.jsonl').write_bytes(proc.stdout); (out / 'oracle.stderr').write_bytes(proc.stderr)
    events = [json.loads(x) for x in proc.stdout.decode().splitlines()]
    logs = [r for r in events if r['event'] == 'lua_log']
    if proc.returncode or not events or not events[-1].get('ok') or events[-1].get('reason') != 'debugger_break' or any(r['error_count'] for r in logs):
        raise RuntimeError('Original stat machine execution incomplete')
    if sum('STAT_GROWTH_COMPLETE ' + str(len(rows)) in r['text'] for r in logs) != 1:
        raise ValueError('Exact machine completion marker missing')
    got = [json.loads(x) for x in samples.read_text(encoding='utf-8').splitlines()]
    if [r[0] for r in got] != list(range(1, len(rows) + 1)):
        raise ValueError('Incomplete/out-of-order machine corpus')
    return got, {'Calls': len(got), 'ProtectedRamAndStackDirectPagePassed': True,
                 'CallerSha256': hashlib.sha256(code).hexdigest(), 'LuaSha256': sha(script), 'SamplesSha256': sha(samples),
                 'IntermediatesSha256': sha(diagnostics)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('rom', 'oracle', 'ca65', 'ld65', 'compiler', 'native-source', 'rng-review',
                 'original-pack', 'redux-pack', 'scratch', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--pilot', action='store_true')
    a = p.parse_args(); a.scratch = local_scratch(a.scratch)
    if a.scratch.exists() or a.output.exists():
        raise ValueError('Fresh scratch/output required')
    rom = a.rom.read_bytes()
    if len(rom) != 0x300000 or hashlib.sha1(rom).hexdigest() != US_SHA1:
        raise ValueError('Exact clean USA ROM required')
    reviewed = json.loads(a.rng_review.read_text(encoding='utf-8'))
    if not reviewed['Passed'] or reviewed['Mismatches'] or reviewed['Pilot']:
        raise ValueError('Completed actual original generator review required')
    source = a.native_source / 'src/game/inventory.c'; rng_source = a.native_source / 'src/core/math.c'
    ids = a.native_source / 'src/data/runtime_generated/asset_ids.h'
    identities = {str(path): sha(path) for path in (a.rom, a.oracle, a.ca65, a.ld65, a.compiler,
                  source, rng_source, a.rng_review, a.original_pack, a.redux_pack, ids, Path(__file__),
                  Path(mapping.__file__), Path(rand_mapping.__file__))}
    a.scratch.mkdir(parents=True)
    globals_, addresses, proof, modifiers, growth = identify(a, a.scratch, rom)
    a.source_proof = proof
    packs = []
    for mode, path in (('original', a.original_pack), ('redux', a.redux_pack)):
        _, _, assets = read_pack(path, ids)
        packed_growth = assets['data/stats_growth_vars.bin']
        packed_modifiers = assets['data/stat_gain_modifier_table.bin']
        if packed_growth != growth or packed_modifiers != modifiers:
            raise ValueError(mode + ': packed stat tables differ from original; requires a separate source oracle')
        packs.append({'Mode': mode, 'PackSha256': sha(path),
                      'GrowthTableSha256': hashlib.sha256(packed_growth).hexdigest(),
                      'ModifierTableSha256': hashlib.sha256(packed_modifiers).hexdigest(),
                      'OriginalTablesByteEqual': True})
    body = mapping.native_body(source.read_text(encoding='utf-8'), 'calculate_stat_gain')
    rng_body = mapping.native_body(rng_source.read_text(encoding='utf-8'), 'rng_next_byte')
    native = a.scratch / 'stat-growth.c'; exe = native.with_suffix('.exe')
    native.write_text('#include "core/math.h"\n#include <stdio.h>\nRNGState rng_state;\n' + rng_body +
                      '\nstatic unsigned calls;\nstatic uint8_t counted_rng(void){++calls;return rng_next_byte();}\n'
                      '#define rng_next_byte counted_rng\nstatic const uint8_t modifier_table[]={' +
                      ','.join(map(str, modifiers)) + '};\nstatic const uint8_t *stat_gain_mod_data=modifier_table;\n' + body + r'''
int main(void){unsigned growth,level,base,seed,index=0;while(scanf("%u %u %u %u",&growth,&level,&base,&seed)==4){++index;rng_state.a=seed&65535;rng_state.b=seed>>16;calls=0;uint16_t result=(uint16_t)calculate_stat_gain(growth,base,level);printf("[%u,%u,%u,%u,%u]\n",index,result,rng_state.a,rng_state.b,calls);}return 0;}
''', encoding='utf-8')
    mapping.run([a.compiler, '-std=c2x', '-O2', '-I', a.native_source / 'src', native, '-o', exe], a.scratch / 'compile.log')
    coefficients = sorted(set(growth))
    levels = (1, 2, 3, 9, 10, 11, 98) if a.pilot else range(1, 99)
    bases = (0, 1, 2, 3, 12, 99, 255) if a.pilot else range(256)
    # These contexts supply all four modifier residues; verify actual machine
    # RAND_MOD returns in intermediates, rather than trusting a seed formula.
    seeds = (0x01010101, 0x00010010, 0x56781234, 0xFFFF0001)
    rows = [(g, level, base, seed) for g in coefficients for level in levels for base in bases
            for seed in (seeds if g * level - (base - 2) * 10 > 0 else seeds[:1])]
    expected = subprocess.run([str(exe)], input='\n'.join(' '.join(map(str, r)) for r in rows).encode(),
                              capture_output=True, timeout=40)
    if expected.returncode:
        raise RuntimeError('Native stat probe failed')
    native_rows = [json.loads(x) for x in expected.stdout.decode().splitlines()]
    (a.scratch / 'native-samples.jsonl').write_bytes(expected.stdout)
    got = []; batches = []; intermediates = []
    for offset in range(0, len(rows), 40000):
        batch, meta = machine(a, a.scratch / f'machine-{offset}', globals_, addresses, rows[offset:offset + 40000])
        for r in batch:
            r[0] += offset
        got.extend(batch); batches.append(meta)
        debug = [json.loads(x) for x in (a.scratch / f'machine-{offset}/intermediates.jsonl').read_text(encoding='utf-8').splitlines()]
        if [r[0] for r in debug] != list(range(1, len(batch) + 1)):
            raise ValueError('Intermediate samples incomplete/out of order')
        for r in debug:
            r[0] += offset
        intermediates.extend(debug)
        print(json.dumps({'MachineCallsCompleted': len(got), 'Requested': len(rows)}), flush=True)
    if len(native_rows) != len(got):
        raise ValueError('Native/original sample counts differ')
    mismatches = [{'Index': i + 1, 'Input': rows[i], 'Native': n, 'OriginalMachine': m}
                  for i, (n, m) in enumerate(zip(native_rows, got)) if n != m]
    counts = Counter('negative' if (d := g * level - (base - 2) * 10) < 0 else
                     'zero' if d == 0 else 'one' if d == 1 else 'positive-above-one'
                     for g, level, base, _ in rows)
    edge_calls = [{'Input': rows[i], 'OriginalMachine': m} for i, m in enumerate(got)
                  if rows[i][0] * rows[i][1] - (rows[i][2] - 2) * 10 in (0, 1)]
    residues = sorted(set(r[1] for r in intermediates if r[1] >= 0))
    if residues != [0, 1, 2, 3]:
        raise ValueError('Positive corpus did not cover every actual RAND_MOD(3) result')
    if any(sha(Path(path)) != value for path, value in identities.items()):
        raise ValueError('Immutable audit input changed')
    report = {'format': 'snes-stat-growth-micro-oracle-v1', 'Passed': not mismatches,
              'ExecutedCalls': len(got), 'SkippedCalls': 0, 'MismatchCount': len(mismatches),
              'FirstMismatches': mismatches[:24], 'Pilot': a.pilot, 'UniquePackedGrowthCoefficients': coefficients,
              'LegalOldLevels': list(levels), 'AllBaseByteValues': not a.pilot,
              'DifferenceGroups': dict(counts), 'ZeroAndOnePointSamples': edge_calls[:24],
              'ActualRandModResiduesCovered': residues,
              'MismatchBaseStatCounts': dict(Counter(rows[r['Index'] - 1][2] for r in mismatches)),
              'BaseStatAtLeastTwoMismatchCount': sum(rows[r['Index'] - 1][2] >= 2 for r in mismatches),
              'FirstMismatchIntermediates': [intermediates[r['Index'] - 1] for r in mismatches[:24]],
              'OnePointDifferenceConsumesExactlyOneRand': all(m[4] == 1 for i, m in enumerate(got)
                  if rows[i][0] * rows[i][1] - (rows[i][2] - 2) * 10 == 1),
              'NonPositiveDifferenceConsumesNoRand': all(m[4] == 0 for i, m in enumerate(got)
                  if rows[i][0] * rows[i][1] - (rows[i][2] - 2) * 10 <= 0),
              'PackTables': packs, 'SourceMapping': proof, 'MachineBatches': batches,
              'InputIdentities': identities, 'NativeProbeSha256': sha(exe),
              'NativeStatFunctionSha256': hashlib.sha256(body.encode()).hexdigest(),
              'NativeRngFunctionSha256': hashlib.sha256(rng_body.encode()).hexdigest(),
              'OwnerRomAndPacksUnchanged': True,
              'Limits': ['Actual untouched original CALCULATE_STAT_GAIN/RAND/math/table execution in prepared CPU contexts.',
                         'Native stat helper and serialized generator compiled from actual source in isolation; this report does not execute a production game binary.',
                         'Redux pack uses the same growth/modifier tables here; surrounding Redux caps and level-up semantics are outside this helper proof.',
                         'Base byte values include synthetic combinations that need not arise during an ordinary unmodified playthrough.',
                         'Four seeded RNG contexts per positive difference; not all four-billion generator states or full story call ordering.',
                         'LEVEL_UP_CHAR, low-level vitality/IQ simple branch, stat recalculation and HP/PP stages are not executed by this helper-only corpus.']}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('Passed', 'ExecutedCalls', 'MismatchCount', 'DifferenceGroups')}), flush=True)
    if not report['Passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
