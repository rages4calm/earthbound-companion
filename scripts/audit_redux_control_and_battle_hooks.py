# SPDX-License-Identifier: GPL-3.0-or-later
"""Review five pinned modules against compiled writes and native bindings.

This is a source/data review. It does not claim complete module semantics,
every input/scene branch or a full story/randomized playthrough.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

from build_maternalbound_pack import read_pack
from maternalbound_dialogue import without_comments

PIN = '897d00833f4a08a0a92f106abf631629a6a6a041'
ROM_SHA = 'c2a2fc98c7e6518b797959ffadf24ca4db8b4d7745ed3a9eb92eee106db1d0ab'

# Each entry records the exact reviewed opcode/operand prefix. Hook targets
# resolve through the pinned compiler map rather than invented addresses.
WRITES = {
    'new_controls': {
        0xC4D6E2: '2900a0', 0xC0B8E3: '294000', 0xC0B8F1: '290090',
        0xC13CC6: '290090', 0xC0B907: '290020', 0xC0B915: '29a000',
        0xC13CED: ('5c', 'Town_Map_Check', 'eaeaeaeaea'),
        0xC13199: 'eaeaeaeaeaea', 0xC1324D: '227942c0',
        0xC13493: 'c90700', 0xC134E1: 'c90600', 0xC134E6: 'c90100',
        0xC134F3: 'c90200', 0xC13503: 'c90400',
        0xC13C3E: 'eaeaeaeaeaeaea', 0xC13C5D: 'd013',
        0xC13C6D: 'd0034c8f3ca9010020ee04ea',
    },
    'fast_terrain': {0xC03AE3: '06', 0xC02F45: 'eaeaea', 0xC031CD: 'eaeaea'},
    'offense_defense_psi_buff': {
        0xC27D34: ('a8b9320029ff008510b92600850e22', '_Find3Over8', ''),
        0xC27DF0: ('22', '_Find3Over8', ''),
        0xC27D96: '4a4a4aea', 0xC27E47: '4a4a4aea',
        0xC27DBE: ('22', 'DefenseUpCapMult7', 'eaea'),
        0xC27E6F: ('22', 'DefenseDownCapMult5Div2', 'ea'),
    },
    'expanded_spy_action': {0xC28798: ('5c', 'Spy_Expansion', 'eaea')},
    'cast_coloured_text': {
        0xC4E48D: 'a90802',
        0xC4E4C0: ('22', 'cast_window_flavor_palette_mixup', ''),
    },
}

REVIEW = {
    'new_controls': {
        'nativeDecision': 'Native input routes implement X pause, B/Start HP/PP, Select map and A/L Talk/Check. Companion controller remapping translates physical buttons to these virtual buttons. The Town Map uses flag 511. Empty checks defer window creation; actual presents open the register-bearing window before assigning reward registers. PC menu uses native userdata and Goods/Equip/PSI/Status/Keys/Tools plus Save/Set Up/Quit, rather than copying the SNES menu indexes or column widths.',
        'bindings': [('src/game_main.c', 'maternalbound_enabled() ? PAD_X : PAD_A'),
                     ('src/game_main.c', 'maternalbound_enabled() ? (PAD_B | PAD_START) : PAD_CANCEL'),
                     ('src/game_main.c', 'maternalbound_enabled() ? PAD_SELECT : PAD_X'),
                     ('src/game_main.c', 'maternalbound_enabled() ? PAD_CONFIRM : PAD_L'),
                     ('src/game/town_map.c', '!event_flag_get(MATERNALBOUND_FLAG_TOWN_MAP)'),
                     ('src/game/text.c', 'add_menu_item("Goods",2,0,0)'),
                     ('src/game/text.c', 'add_menu_item("Tools",11,6,2)'),
                     ('src/game/overworld_interaction.c', 'if (!maternalbound_enabled()) create_window(WINDOW_TEXT_STANDARD)'),
                     ('src/game/overworld_interaction.c', 'if (maternalbound_enabled() && text_ptr != 0)'),
                     ('src/game/text.c', 'maternalbound_enabled() ? (PAD_B | PAD_START) : PAD_CANCEL')],
        'limits': 'Prior ordinary Talk/Check, pause, PSI and present cases cover specific branches. Every map location, mapped physical controller layout, special door text and all menu branches remain unverified. Native map dismissal also accepts confirm and X as PC convenience.',
        'evidence': ['validation/native-check-menu-dev5.json', 'validation/native-redux-gifts-dev5.json', 'validation/native-redux-menus.json'],
    },
    'fast_terrain': {
        'nativeDecision': 'The active source changes small-party/Lost Underworld walking style from 10 to 6 and permits running outside normal walking style. Native map entry selects style 6 for Redux and the position adjuster permits Redux running with nonstandard styles/water. The swamp no-slowdown patch is commented out upstream and is not an active target. The sprite selector still receives style 10 in the small-party path independently of the global movement-speed style.',
        'bindings': [('src/game/overworld.c', 'maternalbound_enabled() ? WALKING_STYLE_SLOWER : WALKING_STYLE_SLOWEST'),
                     ('src/game/position_buffer.c', '(maternalbound_enabled() || (ws == WALKING_STYLE_NORMAL && !water))'),
                     ('src/game/position_buffer.c', 'maternalbound_enabled() ? maternalbound_running()')],
        'limits': 'Native movement/stamina checks do not demonstrate ordinary Lost Underworld, water, ropes or every special movement path.',
        'evidence': ['validation/native-runtime-regressions-dev6.json'],
    },
    'offense_defense_psi_buff': {
        'nativeDecision': 'The assembled _Find3Over8 helper doubles its input then shifts four times: base/8 for Offense Up and current/8 for Offense Down. Its stale 37.5-percent comments are not the active code. Native offense-up cap is base*17/8; offense-down retains base*3/4. Defense changes current stats by 1/8 and caps at base*7/4 or base*5/8. The native original profile retains its original formulas.',
        'bindings': [('src/game/battle_calc.c', 'redux ? target->base_offense >> 3 : target->offense >> 4'),
                     ('src/game/battle_calc.c', '(uint16_t)target->base_offense * 17'),
                     ('src/game/battle_calc.c', 'target->offense >> (maternalbound_enabled() ? 3 : 4)'),
                     ('src/game/battle_calc.c', 'target->defense >> (redux ? 3 : 4)'),
                     ('src/game/battle_calc.c', 'target->base_defense * (redux ? 7 : 5)'),
                     ('src/game/battle_calc.c', '(uint16_t)target->base_defense * 5')],
        'limits': 'Production calculation fixtures cover representative increments, repeated caps and zero-current cases. Exhaustive stat combinations, all PSI UI/action branches and 65816 status-register parity are not claimed.',
        'evidence': ['validation/native-runtime-regressions-dev6.json'],
    },
    'expanded_spy_action': {
        'nativeDecision': 'Native Spy enters saved stage 10 after Defense, displays the converted Spy Speed text with the target speed, then returns to the original vulnerability and item path. It derives the target from serialized battle state on each step.',
        'bindings': [('src/game/battle_actions.c', 'st->pc = maternalbound_enabled() ? 10 : 2'),
                     ('src/game/battle_actions.c', 'case 10: /* Redux expanded Spy: Speed follows Defense. */'),
                     ('src/game/battle_actions.c', 'false, true, tgt->speed')],
        'limits': 'A prepared four-member Spiteful Crow battle shows Offense 5, Defense 3 and Speed 77, awards one Cookie to Jeff and returns to the battle menu with cold restores between 21 input stages. All 21 player/observer states match and a production cold render shows Speed at 1080p. Ordinary story encounters, other enemies, full inventory, itemless and other resistance/theft branches remain unverified.',
        'evidence': ['validation/native-redux-spy-dev6.json', 'validation/native-jev-spy-parity-dev6.json', 'validation/native-redux-spy-render-dev6.json'],
    },
    'cast_coloured_text': {
        'nativeDecision': 'Native Redux cast setup retains flavour colors in palette zero, copies the cast background into palette one and clears colors zero/three, matching the active patch. This is conditional on the Redux profile.',
        'bindings': [('src/game/ending.c', 'memcpy(ert.palettes+(maternalbound_enabled() ? 4 : 0), pal, BPP2PALETTE_SIZE * 4)'),
                     ('src/game/ending.c', 'if (maternalbound_enabled()) ert.palettes[0]=ert.palettes[3]=0')],
        'limits': 'Existing prepared cast and cold-restore scenes are bounded evidence. Ordinary ending progression, every window flavour and named-guardian/photo acquisition remain unverified.',
        'evidence': ['validation/native-redux-ending.json'],
    },
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'native-source', 'bridge', 'compiled-rom', 'assets', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    upstream = a.project.parent
    if subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip() != PIN:
        raise ValueError('Upstream changed; repeat manual review.')
    rom = a.compiled_rom.read_bytes()
    if hashlib.sha256(rom).hexdigest() != ROM_SHA:
        raise ValueError('Compiled content differs from review.')
    bridge = json.loads(a.bridge.read_text(encoding='utf-8-sig'))
    labels = {(x['module'],x['name']):x['snesAddress'] for x in bridge['labels']}
    # CCScript does not export this underscore-prefixed helper. Resolve its
    # address from the compiled Offense Down JSL, then verify the full helper
    # and the separate Offense Up caller. Do not invent a symbol-map label.
    down = 0xC27DF0-0xC00000
    if rom[down] != 0x22:
        raise ValueError('Expected Offense Down long call.')
    private_helper = int.from_bytes(rom[down+1:down+4],'little')
    if not 0xC00000 <= private_helper <= 0xFFFFFF-9:
        raise ValueError('Private helper outside reviewed ROM.')
    labels[('offense_defense_psi_buff','_Find3Over8')] = private_helper
    sources = {m['name']:m['source'] for m in bridge['modules']}
    _,_,assets = read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h')
    blob = assets['dialogue/dialogue.bin']
    magic,version,offset,count,*_ = struct.unpack_from('<8s6I',blob,len(blob)-32)
    if magic != b'MRDXNV01' or version != 2:
        raise ValueError('Expected exact mapped Redux dialogue.')
    mapping = dict(struct.iter_unpack('<II',blob[offset:offset+count*8]))
    rows=[]
    for module,writes in WRITES.items():
        relative = sources[module]
        data = (a.project/relative).read_bytes()
        expected_source = subprocess.check_output(['git','-C',str(upstream),'show','HEAD:Project/'+relative])
        if data.replace(b'\r\n',b'\n') != expected_source.replace(b'\r\n',b'\n'):
            raise ValueError('Module differs from pin: '+module)
        addresses = [int(x,16) for x in re.findall(r'ROM\[(0[xX][0-9a-fA-F]+)\]\s*=',without_comments(data.decode('utf-8-sig')))]
        if len(addresses) != len(writes) or set(addresses) != set(writes):
            raise ValueError('Active literal writes changed: '+module)
        byte_checks=[]
        for address,spec in writes.items():
            if isinstance(spec,tuple):
                opcode,label,suffix=spec
                expected=bytes.fromhex(opcode)+labels[(module,label)].to_bytes(3,'little')+bytes.fromhex(suffix)
            else: expected=bytes.fromhex(spec)
            actual=rom[address-0xC00000:address-0xC00000+len(expected)]
            if actual != expected:
                raise ValueError(f'Compiled prefix mismatch {module}:{address:06X} actual={actual.hex()} expected={expected.hex()}')
            byte_checks.append({'address':f'{address:06X}','checkedBytes':len(expected),'compiledPrefixMatches':True})
        refs=[]
        review=REVIEW[module]
        for path,anchor in review['bindings']:
            text=(a.native_source/path).read_text(encoding='utf-8')
            at=text.find(anchor)
            if at<0:raise ValueError('Native binding missing: '+path+': '+anchor)
            refs.append({'path':path,'line':text[:at].count('\n')+1,'anchor':anchor})
        rows.append({'module':module,'source':relative,'sourceSha256':hashlib.sha256(data).hexdigest(),
                     'activeLiteralWrites':len(addresses),'compiledChecks':byte_checks,'nativeReferences':refs,
                     **{k:v for k,v in review.items() if k!='bindings'}})
    helper=labels[('offense_defense_psi_buff','_Find3Over8')]
    if rom[helper-0xC00000:helper-0xC00000+9] != bytes.fromhex('850465044a4a4a4a6b'):
        raise ValueError('Offense helper algorithm changed.')
    spy=labels[('battle_text','Spy_Speed')]
    if not mapping.get(spy) or mapping.get(0x2FFF10) != mapping[spy]:
        raise ValueError('Native Spy Speed alias does not point to converted text.')
    result={'Passed':True,'upstreamCommit':PIN,'compiledRomSha256':ROM_SHA,
            'reviewedModules':len(rows),'activeLiteralWritesReviewed':sum(x['activeLiteralWrites'] for x in rows),
            'offenseHelperBytesVerified':True,'privateHelperAddressFromCallSite':f'{private_helper:06X}',
            'spySpeedAliasVerified':True,'modules':rows,
            'fullModuleSemanticParityClaimed':False,'fullPlaythroughVerified':False,
            'limits':['Exactly these five source modules and compiled prefixes; not the remaining all-module audit.',
                      'Native anchors tie manual decisions to code; symbol presence alone does not prove semantic parity.',
                      'Runtime evidence retains the engine identities and coverage limits of its original reports.']}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='modules'},indent=2))


if __name__ == '__main__': main()
