# SPDX-License-Identifier: GPL-3.0-or-later
"""Review the pinned redux_changes module's literal/native hooks.

This is deliberately narrower than a complete patch audit. Source references
and retained bytes do not prove every live scene or complete Redux parity.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
from build_maternalbound_pack import read_pack

PIN = '897d00833f4a08a0a92f106abf631629a6a6a041'
ROM_SHA = 'c2a2fc98c7e6518b797959ffadf24ca4db8b4d7745ed3a9eb92eee106db1d0ab'
REVIEW = {
 0xC2381F: ('native-menu', 'The Transform command uses column 11 in the native battle menu.', [('src/game/battle.c', 'add_menu_item(maternalbound_enabled()?"Transform":"Mirror"')]),
 0xC1C415: ('native-name-data', 'The favorite-thing field is addressed through the native game-state structure, independently of SNES WRAM offsets.', [('src/game/display_text.c', 'game_state.favourite_thing')]),
 0xC1FE3D: ('native-name-rendering', 'The native renderer explicitly prints the P glyph in the PK prefix.', [('src/game/display_text.c', "const uint8_t prefix[]={ 'P'+0x30,'K'+0x30,' '+0x30 }")]),
 0xC1FE42: ('native-name-rendering', 'The native renderer explicitly prints the K glyph in the PK prefix.', [('src/game/display_text.c', "const uint8_t prefix[]={ 'P'+0x30,'K'+0x30,' '+0x30 }")]),
 0xC37CD1: ('converted-movement-data', 'The monkey event retains destination 7 inside the converted C3 movement bank.', [('src/entity/opcodes.c', 'WRAM_GLOBAL(0x9F3F, ow.psi_teleport_destination)')]),
 0xC292A0: ('native-gameplay', 'The Clumsy Robot action reads the flag from Redux teleport destination 15.', [('src/game/battle_actions.c', '(maternalbound_enabled() ? 15 : 13) * 31')]),
 0xC490F6: ('native-gameplay', 'The Piggy Nose distance query finds Redux truffle sprite 440.', [('src/game/display_text_cc.c', 'find_entity_by_sprite_id(maternalbound_enabled() ? 440 : 376)')]),
 0xC292DE: ('native-gameplay', 'The unused Clumsy Robot smoke branch selects Redux teleport destination 8.', [('src/game/battle_actions.c', 'ow.psi_teleport_destination = maternalbound_enabled() ? 8 : 13')]),
 0xC38753: ('converted-movement-data', 'The reduced flash controller stores 3 in entity variable 0; the native interpreter executes that retained movement command.', [('src/entity/opcodes.c', 'case OP_SET_VAR:'), ('src/entity/callroutine.c', 'apply_palette_brightness_all(entities.var[0][entity_offset])')]),
 0xC39F67: ('converted-movement-data', 'The second reduced flash controller stores 11 in entity variable 0; its patched bytes are retained in the C3 bank.', [('src/entity/opcodes.c', 'case OP_SET_VAR:')]),
 0xC39F75: ('converted-movement-data', 'The patched bytes form variable-callback ADD with a signed -1 operand, within the command beginning at C39F73; they are not a separate 65816 COP executed by the PC.', [('src/entity/opcodes.c', 'case 0x14:'), ('src/entity/opcodes.c', 'case 2: *target += param; break;')]),
 0xC24FFB: ('native-gameplay', 'Redux turn ordering uses 25-percent speed variance instead of the original 50-percent function.', [('src/game/battle.c', 'maternalbound_enabled() ? battle_25pct_variance(b->speed)')]),
 0xC4DE78: ('native-map-data', 'The sanctuary display swaps Milky Well and Rainy Circle by selecting the corresponding source records in native code.', [('src/game/map_loader.c', 'if(maternalbound_enabled() && (source_idx==2 || source_idx==3)) source_idx^=1')]),
 0xC05284: ('native-timer-adaptation', 'The native timer uses 2531 ticks for Redux and 1687 for original EarthBound, including the post-call reset.', [('src/game/overworld.c', 'ow.dad_phone_timer = maternalbound_enabled() ? 2531 : 1687'), ('src/game/overworld_interaction.c', 'ow.dad_phone_timer = maternalbound_enabled() ? 2531 : 1687')]),
 0xC3E964: ('native-menu-layout-adaptation', 'The PC menu has its own columns, shorter Keys label and Save/Set Up/Quit rows. It does not reproduce the SNES seven-tile-column table literally.', [('src/game/text.c', 'add_menu_item("Keys",10,0,2)'), ('src/game/text.c', 'add_menu_item("Equip",4,6,0)')]),
}
# Exact typed movement commands around four literal writes. These include
# unchanged operand bytes to verify command boundaries, not just patch bytes.
MOVEMENT = {
 0xC37CD1: (0xC37CCE, '15 3f 9f 07 00'),
 0xC38753: (0xC38753, '0e 00 03 00'),
 0xC39F67: (0xC39F67, '0e 00 0b 00'),
 0xC39F75: (0xC39F73, '14 00 02 ff ff'),
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'native-source', 'compiled-rom', 'assets', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    upstream = a.project.parent
    if subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip() != PIN:
        raise ValueError('Repeat review after an upstream pin change.')
    source = a.project / 'ccscript/redux/redux_changes.ccs'
    expected = subprocess.check_output(['git', '-C', str(upstream), 'show', 'HEAD:Project/ccscript/redux/redux_changes.ccs'])
    data = source.read_bytes()
    if data.replace(b'\r\n', b'\n') != expected.replace(b'\r\n', b'\n'):
        raise ValueError('Source differs from the pinned module.')
    clean = re.sub(r'/\*.*?\*/|//[^\n]*', '', data.decode('utf-8-sig'), flags=re.S)
    addresses = [int(x, 16) for x in re.findall(r'^\s*ROM\[(0[xX][0-9a-fA-F]+)\]', clean, re.M)]
    if len(addresses) != len(REVIEW) or set(addresses) != set(REVIEW):
        raise ValueError('Active writes changed; do not silently infer coverage.')
    rom = a.compiled_rom.read_bytes()
    if hashlib.sha256(rom).hexdigest() != ROM_SHA:
        raise ValueError('Compiled ROM differs from the reviewed content.')
    _, _, assets = read_pack(a.assets, a.native_source / 'src/data/runtime_generated/asset_ids.h')
    raw = assets['US/events/bank_c3_scripts_combined.bin']
    magic, count = struct.unpack_from('<8sI', raw)
    if magic != b'MRMVBN01':
        raise ValueError('Expected converted Redux movement bank.')
    cursor, regions = 12, []
    for _ in range(count):
        bank, reserved, base, size = struct.unpack_from('<BBHI', raw, cursor)
        cursor += 8
        if reserved or size > 0x10000-base or cursor+size > len(raw):
            raise ValueError('Malformed movement container.')
        regions.append(((bank << 16) + base, raw[cursor:cursor+size]))
        cursor += size
    if cursor != len(raw):
        raise ValueError('Trailing movement data.')
    rows = []
    for address in addresses:
        kind, note, bindings = REVIEW[address]
        refs = []
        for path, anchor in bindings:
            native = (a.native_source / path).read_text(encoding='utf-8')
            at = native.find(anchor)
            if at < 0:
                raise ValueError('Missing review binding: ' + path + ': ' + anchor)
            refs.append({'path': path, 'line': native[:at].count('\n')+1, 'anchor': anchor})
        row = {'address': f'{address:06X}', 'classification': kind, 'reviewDecision': note, 'nativeReferences': refs}
        if address in MOVEMENT:
            command, expected_hex = MOVEMENT[address]
            expected_bytes = bytes.fromhex(expected_hex)
            compiled = rom[command-0xC00000:command-0xC00000+len(expected_bytes)]
            converted = next((block[command-base:command-base+len(expected_bytes)] for base, block in regions
                              if base <= command and command+len(expected_bytes) <= base+len(block)), None)
            if compiled != expected_bytes or converted != compiled:
                raise ValueError(f'Changed or missing retained movement command at {command:06X}.')
            row['retainedMovementCommand'] = {'address': f'{command:06X}', 'bytes': len(compiled), 'compiledAndConvertedMatch': True}
        row['limits'] = 'Targeted fixtures and source/data checks; every live story branch remains unverified.'
        rows.append(row)
    record = {'format': 'redux-general-hooks-review-v1', 'status': 'manual-source-and-retained-data-review',
              'upstreamCommit': PIN, 'module': 'ccscript/redux/redux_changes.ccs',
              'sourceSha256': hashlib.sha256(data).hexdigest(), 'compiledRomSha256': ROM_SHA,
              'packSha256': hashlib.sha256(a.assets.read_bytes()).hexdigest(), 'activeWritesReviewed': len(rows),
              'retainedMovementCommandsChecked': len(MOVEMENT), 'symbolPresenceProvesBehavior': False,
              'completePatchAudit': False, 'fullPlaythroughVerified': False, 'reviews': rows}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: record[key] for key in ('activeWritesReviewed', 'retainedMovementCommandsChecked', 'completePatchAudit')}))


if __name__ == '__main__':
    main()
