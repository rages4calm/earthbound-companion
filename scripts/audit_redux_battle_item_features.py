# SPDX-License-Identifier: GPL-3.0-or-later
"""Review six pinned Redux battle/item modules against native source and data.

The report contains source hashes, addresses, counts and review decisions only.
Owner-provided ROM/pack bytes and isolated runtime logs stay on the local machine.
Catalog/dispatch reachability is not complete action semantics or a playthrough.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess

from build_maternalbound_pack import read_pack
from maternalbound_dialogue import without_comments
from maternalbound_graphics import slice_rom
from maternalbound_psi import convert_psi, GFX_WORDS

PIN = '897d00833f4a08a0a92f106abf631629a6a6a041'
ROM_SHA = 'c2a2fc98c7e6518b797959ffadf24ca4db8b4d7745ed3a9eb92eee106db1d0ab'
MODULES = {
    'better_condiment_search': ('redux',
        'Native food searches try the first compatible condiment, then Delisauce 126, then any condiment. Delisauce matches any food row during consumption; ordinary EarthBound retains its first-condiment search.',
        [('src/game/inventory.c', 'for (int pass = 0; pass < 3; pass++)'),
         ('src/game/battle_actions.c', '(maternalbound_enabled() && condiment_id == 126)')],
        'Production inventory fixtures exercise compatible-condiment priority, Delisauce fallback and no-condiment on food rows; runtimeChecks records execution. Consumption messages, incompatible sauces, inventory compaction and every food/condiment pairing are not exhaustive.'),
    'lucky_sandwich_revamp': ('redux',
        'The shared Lucky Sandwich item 226 now routes to action 318. The native action preserves five conditional sequential RNG draws for six outcomes: variable 60/240 HP, full HP, variable 5/20 PP, or full HP+PP. Full recovery yields through separate text children.',
        [('src/game/battle_actions.c', 'btlact_redux_lucky_sandwich_step'),
         ('tools/build_maternalbound_pack.py', 'if start//stride == 318')],
        'The production action fixture iterates 4096 seeds, requires all six outcomes and checks recovery targets; runtimeChecks records execution. This is not a distribution proof or every ordinary shop/use/target/text continuation.'),
    'item_quantity': ('redux',
        'CC 1A 10 reads a literal byte or the low 16 bits of argument memory, scans four party positions until zero/non-player, and counts all 14 inventory slots including zeros. Native shared key storage adds one pooled possession for a nonzero item as an explicit adaptation.',
        [('src/game/display_text_cc.c', 'CC_ItemQuantity reads one literal byte'),
         ('src/game/display_text.c', 'Exact item_quantity.ccs dispatcher operands')],
        'The actual-dispatcher fixture defines 19 cases for empty slots, high argument bits, literal precedence, slot endpoints, reordered party, party boundaries and native pooled keys; runtimeChecks records execution. The pinned source has no call sites for this command; this closes unused API parity, not a reproduced story blocker.'),
    'Extended_Battle_Action_Table': ('expansion',
        'All 320 packed actions retain their four targeting/type/PP fields, relocated text and native function mappings. Lucky Sandwich action 318 uses a stable native address; Skip Sandwich action 319 retains the food handler and converted stamina-restoring description. A mapped handler does not establish every action branch.',
        [('tools/build_maternalbound_pack.py', 'Missing expanded battle-action exports'),
         ('src/game/battle_actions.c', 'static const BattleActionEntry btlact_dispatch_table[]')],
        'Packed-record equivalence, converted descriptions and dispatch reachability are checked for every row. Complete 320-action execution, all targets, statuses, reflected effects, RNG and story battle outcomes remain unverified.'),
    'Extended_PSI_Animations': ('expansion',
        'The normalized native MRPSIX01 container retains 68 configuration rows, ten tilesets, 68 arrangement streams and 68 palettes. Effect IDs 54..87 subtract 20; original special effects 35..53 remain distinct. Invalid out-of-range IDs are rejected as a native bounds adaptation.',
        [('tools/maternalbound_psi.py', 'def convert_psi('),
         ('src/game/battle_psi.c', 'effect_id>=54'),
         ('src/game/battle_psi.c', 'psi_animation_savestate_rebind();')],
        'The 2bpp production fixture requires all 68 effects to complete configured frames and pointer rebinds; runtimeChecks records execution. This is not rendered-image comparison, all 4bpp backgrounds, all enemy target layouts or every cold save during an effect.'),
    'm3_defend_roller': ('redux',
        'Actual hooks halve normal HP rolling after a battler begins its own guarding turn; battle start and round end clear the snapshot flags. Despite the module title mentioning HP/PP, its C21139/C211C3 hook sites are HP increase/decrease; PP remains 0x19000. Native indexing uses the real battler ID.',
        [('src/game/battle.c', 'static int32_t hp_roll_speed(unsigned slot)'),
         ('src/game/battle.c', 'bt.redux_roller_active[attacker->id] = attacker->guarding'),
         ('src/game/battle.c', 'memset(bt.redux_roller_active,0,sizeof(bt.redux_roller_active))'),
         ('src/game/battle.c', 'bool maternalbound_roller_selftest(void)')],
        'Direct production roller fixtures exercise reordered character identity, guarding, overworld, stacked slowdown and unchanged PP; runtimeChecks records execution. Actual turn timing is source-reviewed; all initiative/status/death/round-end and ordinary combat combinations remain unverified.'),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_block(text, name):
    match = re.search(r'ROM\[' + re.escape(name) + r'\]\s*=\s*\{(.*?)\n\}', text, re.S)
    if not match:
        raise ValueError('Missing source block: ' + name)
    return match.group(1)


def numeric_defines(text):
    return {name: int(value, 0) for name, value in re.findall(
        r'^\s*define\s+(\w+)\s*=\s*(0[xX][\da-fA-F]+|\d+)\s*$', text, re.M)}


def source_data(text, defines, length):
    result = bytearray()
    for kind, operand in re.findall(r'^\s*(byte|short|long)\s+([\w]+)\s*$', text, re.M):
        value = defines[operand] if operand in defines else int(operand, 0)
        result.extend(value.to_bytes({'byte': 1, 'short': 2, 'long': 4}[kind], 'little'))
        if len(result) == length:
            return bytes(result)
        if len(result) > length:
            raise ValueError('Source row count changed.')
    raise ValueError('Source data shorter than expected.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'native-source', 'bridge', 'compiled-rom', 'assets', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('player', 'observer', 'scratch'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--previous-quantity-exe', type=Path,
                        help='Private final-build variant with the previous CC 1A10 adapter and new 19-case fixture.')
    args = parser.parse_args()
    if any((args.player, args.observer, args.scratch)) and not all((args.player, args.observer, args.scratch)):
        parser.error('Runtime checks require --player, --observer and fresh --scratch together.')
    if args.previous_quantity_exe and not args.scratch:
        parser.error('--previous-quantity-exe requires the isolated runtime checks.')
    upstream = args.project.parent
    actual_pin = subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
    if actual_pin != PIN:
        raise ValueError('Redux revision changed; repeat the manual review.')

    def pinned(relative):
        actual = (args.project / relative).read_bytes()
        expected = subprocess.check_output(['git', '-C', str(upstream), 'show', 'HEAD:Project/' + relative])
        if actual.replace(b'\r\n', b'\n') != expected.replace(b'\r\n', b'\n'):
            raise ValueError('Source differs from pin: ' + relative)
        return actual

    active_main = without_comments(pinned('ccscript/main.ccs').decode('utf-8-sig'))
    bridge = json.loads(args.bridge.read_text(encoding='utf-8-sig'))
    if bridge['source']['revision'] != PIN:
        raise ValueError('Compiler label inventory does not match the reviewed revision.')
    labels = {(row['module'], row['name']): row['snesAddress'] for row in bridge['labels']}
    rom = args.compiled_rom.read_bytes()
    if digest(rom) != ROM_SHA:
        raise ValueError('Compiled ROM differs from the reviewed source/link map.')
    _, _, assets = read_pack(args.assets, args.native_source / 'src/data/runtime_generated/asset_ids.h')
    rows = []
    cleans = {}
    for module, (category, decision, references, limits) in MODULES.items():
        relative = f'ccscript/{category}/{module}.ccs'
        if f'import "{category}/{module}.ccs"' not in active_main:
            raise ValueError('Reviewed module is no longer directly enabled: ' + module)
        content = pinned(relative)
        clean = without_comments(content.decode('utf-8-sig'))
        cleans[module] = clean
        refs = []
        for path, anchor in references:
            base = args.native_source if path.startswith('src/') else Path(__file__).resolve().parent.parent
            text = (base / path).read_text(encoding='utf-8')
            at = text.find(anchor)
            if at < 0:
                raise ValueError('Manual-review reference missing: ' + path + ': ' + anchor)
            refs.append({'path': path, 'line': text[:at].count('\n') + 1, 'anchor': anchor,
                         'fileSha256': digest((base / path).read_bytes())})
        rows.append({'module': module, 'source': relative, 'sourceSha256': digest(content),
                     'activeRomWriteExpressions': re.findall(r'^\s*ROM\[([^]\n]+)\]', clean, re.M),
                     'nativeDecision': decision, 'nativeReferences': refs, 'targetedCoverageAndLimits': limits})

    hook_checks = []
    for module, address, opcode, label, suffix in (
        ('better_condiment_search', 0xC1DB33, '5c', 'find_condiment', ''),
        ('better_condiment_search', 0xC2B1E2, '5c', 'apply_sauce', ''),
        ('m3_defend_roller', 0xC2569A, '22', 'turnStartRollerHook_patch', 'eaeaeaeaeaea'),
        ('m3_defend_roller', 0xC26088, '22', 'roundEndHook_patch', ''),
        ('m3_defend_roller', 0xC24A45, '22', 'clearRollerActiveFlagsPatch', 'eaea'),
        ('m3_defend_roller', 0xC2FFD1, '22', 'getHPPPMeterSpeedPatch', '60'),
    ):
        expected = bytes.fromhex(opcode) + labels[module, label].to_bytes(3, 'little') + bytes.fromhex(suffix)
        if slice_rom(rom, address, len(expected)) != expected:
            raise ValueError(f'Compiled hook differs: {module}:{address:06X}')
        hook_checks.append({'module': module, 'address': f'{address:06X}', 'checkedBytes': len(expected), 'matches': True})
    for address in (0xC21139, 0xC211C3):
        if slice_rom(rom, address, 3) != bytes.fromhex('20d1ff'):
            raise ValueError('Defend roller springboard changed.')
        hook_checks.append({'module': 'm3_defend_roller', 'address': f'{address:06X}', 'checkedBytes': 3, 'matches': True})
    if slice_rom(rom, labels['ccexpand', 'CodeTable'] + 0x10 * 4, 4) != labels['item_quantity', 'CC_ItemQuantity'].to_bytes(4, 'little'):
        raise ValueError('Compiled CC 1A10 does not route to the reviewed function.')

    table = assets['data/battle_action_table.bin']
    linked = slice_rom(rom, labels['Extended_Battle_Action_Table', 'BattleAction_Table'], 320 * 12)
    if len(table) != 320 * 12:
        raise ValueError('Native battle-action count changed.')
    blob = assets['dialogue/dialogue.bin']
    magic, version, offset, count, *_ = struct.unpack_from('<8s6I', blob, len(blob) - 32)
    if magic != b'MRDXNV01' or version != 2:
        raise ValueError('Expected mapped Redux dialogue.')
    mappings = dict(struct.iter_unpack('<II', blob[offset:offset + count * 8]))
    native_dispatch = {int(x, 16) for x in re.findall(r'\{ 0x([0-9A-F]+),',
        (args.native_source / 'src/game/battle_actions.c').read_text(encoding='utf-8'))}
    for action in range(320):
        at = action * 12
        if table[at:at + 4] != linked[at:at + 4]:
            raise ValueError(f'Action {action}: direction/target/type/PP differs.')
        original_text, original_function = struct.unpack_from('<II', linked, at + 4)
        text, function = struct.unpack_from('<II', table, at + 4)
        if text != mappings.get(original_text, original_text):
            raise ValueError(f'Action {action}: converted text does not match the source mapping.')
        expected_function = 0xC2FFF0 if action == 318 else original_function
        if function != expected_function or function not in native_dispatch:
            raise ValueError(f'Action {action}: no matching native function.')
    items = assets['data/item_configuration_table.bin']
    if struct.unpack_from('<H', items, 226 * 39 + 29)[0] != 318:
        raise ValueError('Lucky Sandwich is not bound to its combined action.')
    purchase_source = without_comments(pinned('ccscript/data/data_15.ccs').decode('utf-8-sig'))
    if not re.search(r'l_0xc5e3bc:\s*eob\b', purchase_source):
        raise ValueError('Lucky Sandwich purchase randomization has not been disabled.')
    quantity_calls = []
    for path in sorted((args.project / 'ccscript').rglob('*.ccs')):
        if path.name == 'item_quantity.ccs':
            continue
        clean = without_comments(path.read_text(encoding='utf-8-sig'))
        if re.search(r'\bitem_quantity\s*\(|\[1A 10(?: |\])', clean, re.I):
            quantity_calls.append(path.relative_to(args.project).as_posix())
    if quantity_calls:
        raise ValueError('Item quantity now has source call sites; re-review its story coverage.')

    psi_source = cleans['Extended_PSI_Animations']
    psi_defines = numeric_defines(psi_source)
    configs = source_data(source_block(psi_source, 'PSI_Config_Table'), psi_defines, 68 * 12)
    if configs != slice_rom(rom, 0xF20000, 68 * 12):
        raise ValueError('Linked PSI configurations differ from the pinned source.')
    normalized_configs = bytearray(configs)
    for index in range(68):
        word = struct.unpack_from('<H', configs, index * 12)[0]
        struct.pack_into('<H', normalized_configs, index * 12, GFX_WORDS.index(word))
    if assets['data/psi_anim_cfg.bin'][:68 * 12] != normalized_configs:
        raise ValueError('Native PSI config differs after the explicit graphics-index normalization.')
    palette = source_data(source_block(psi_source, 'PSI_Palette_Table'), psi_defines, 68 * 8)
    if palette != slice_rom(rom, 0xF20600, 68 * 8):
        raise ValueError('Linked PSI palettes differ from the pinned source.')
    rebuilt_assets = {'data/psi_anim_cfg.bin': b''}
    psi_conversion = convert_psi(rom, rebuilt_assets)
    if rebuilt_assets['data/psi_anim_cfg.bin'] != assets['data/psi_anim_cfg.bin']:
        raise ValueError('Native PSI container does not reproduce the linked source graphics/arrangements/palettes.')

    runtime = []
    quantity_regression = None
    if args.scratch:
        if args.scratch.exists():
            raise ValueError('Use a fresh scratch path; preserve prior runtime evidence.')
        args.scratch.mkdir(parents=True)
        env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
        tests = (('combat', '--selftest-redux-combat', 'Redux production HP roller:'),
                 ('psi', '--selftest-redux-psi', 'Redux native PSI playback: 68 effects,'),
                 ('vm', '--selftest-redux-vm', 'Redux item quantity dispatcher: 19 cases checked'))
        for engine in ('player', 'observer'):
            exe = getattr(args, engine).resolve()
            for name, flag, marker in tests:
                folder = args.scratch / f'{engine}-{name}'
                folder.mkdir()
                result = subprocess.run([str(exe), '--assets', str(args.assets.resolve()),
                    '--session-dir', str(folder.resolve()), '--save', str((folder / 'fixture.srm').resolve()),
                    '--allow-redux-development', '--headless', flag], env=env, capture_output=True, timeout=60)
                log = (result.stdout + result.stderr).decode(errors='replace')
                (folder / 'native.log').write_text(log, encoding='utf-8')
                passed = not result.returncode and marker in log and not re.search(r'FAIL|FATAL|ERROR|case \d+ failed', log)
                runtime.append({'engine': engine, 'test': name, 'nativeExeSha256': digest(exe.read_bytes()),
                    'passed': passed, 'exitCode': result.returncode, 'requiredMarkerPresent': marker in log,
                    'verificationMarkers': [line for line in log.splitlines() if re.search(r'PASS|checks:|cases checked', line)]})
                print(json.dumps({'engine': engine, 'test': name, 'passed': passed}), flush=True)

        if args.previous_quantity_exe:
            exe = args.previous_quantity_exe.resolve()
            folder = args.scratch / 'previous-quantity-adapter'
            folder.mkdir()
            result = subprocess.run([str(exe), '--assets', str(args.assets.resolve()),
                '--session-dir', str(folder.resolve()), '--save', str((folder / 'fixture.srm').resolve()),
                '--allow-redux-development', '--headless', '--selftest-redux-vm'],
                env=env, capture_output=True, timeout=60)
            log = (result.stdout + result.stderr).decode(errors='replace')
            (folder / 'native.log').write_text(log, encoding='utf-8')
            failures = re.findall(r'Redux item quantity case (\d+) failed: got (\d+) expected (\d+)', log)
            expected = [(2, 0, 4), (3, 0, 50), (4, 0, 50), (10, 0, 24),
                        (12, 0, 12), (15, 7, 4), (16, 0, 50), (18, 0, 1)]
            observed = [tuple(map(int, row)) for row in failures]
            passed = result.returncode == 1 and observed == expected and \
                'Redux item quantity dispatcher: 19 cases checked' in log
            quantity_regression = {'variant': 'private final-build variant containing the previous CC 1A10 adapter',
                'nativeExeSha256': digest(exe.read_bytes()), 'oldExitCode': result.returncode,
                'oldCasesFailed': [{'index': i, 'got': got, 'expected': wanted} for i, got, wanted in observed],
                'eightOldFailuresReproduced': passed,
                'allNineteenNewCasesPassBothBuilds': all(row['passed'] for row in runtime if row['test'] == 'vm'),
                'storyFailureClaimed': False}
            print(json.dumps({'test': 'previous-quantity-adapter', 'expectedFailuresReproduced': passed}), flush=True)

    report = {'format': 'redux-battle-item-feature-review-v1', 'upstreamCommit': PIN,
        'compiledRomSha256': ROM_SHA, 'packSha256': digest(args.assets.read_bytes()),
        'status': 'source-data-review-with-bounded-runtime-checks', 'reviewedModules': len(rows),
        'sourceAndDataChecksPassed': True,
        'compiledHookChecks': hook_checks, 'expandedActionsChecked': 320,
        'allPackedActionFieldsAndDispatchesMatch': True, 'luckySandwichPurchaseStubVerified': True,
        'quantityStoryCallSites': quantity_calls, 'quantityDispatcherCases': 19,
        'quantityRegression': quantity_regression,
        'psiConfigurationsComparedToSource': 68, 'psiPalettesComparedToSource': 68,
        'psiContainerReproducesLinkedData': True, 'psiAnimations': psi_conversion['animations'],
        'psiFrames': psi_conversion['frames'], 'psiTilesets': psi_conversion['tilesets'],
        'runtimeChecks': runtime, 'runtimeChecksPassed': bool(runtime) and all(row['passed'] for row in runtime),
        'modules': rows, 'fullModuleSemanticParityClaimed': False, 'fullPlaythroughVerified': False,
        'limits': ['Exact six active pinned modules; source/data checks do not validate all action branches.',
            'Runtime checks invoke production functions in isolated prepared states; they do not establish an ordinary full playthrough.',
            'Matching dispatch addresses establishes reachability only; complete 320-action execution remains separate.',
            'No game ROM, asset data, dialogue payload or player save is written into this public report.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('reviewedModules', 'expandedActionsChecked',
        'psiAnimations', 'psiFrames', 'runtimeChecksPassed', 'fullModuleSemanticParityClaimed')}, indent=2))
    if (runtime and not report['runtimeChecksPassed']) or \
            (quantity_regression and not quantity_regression['eightOldFailuresReproduced']):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
