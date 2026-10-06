# SPDX-License-Identifier: GPL-3.0-or-later
"""Review remaining pinned Redux feature modules and native bindings.

This is a source/data audit, not a complete story playthrough or an independent
SNES comparison. Missing semantic evidence is retained explicitly as a gap.
Only metadata and hashes are written; local ROM/assets are never published.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

from build_maternalbound_pack import read_pack
from maternalbound_dialogue import without_comments
from audit_redux_movement import audit as movement_audit

PIN = '897d00833f4a08a0a92f106abf631629a6a6a041'
ROM_SHA = 'c2a2fc98c7e6518b797959ffadf24ca4db8b4d7745ed3a9eb92eee106db1d0ab'
MODULES = {
 'ccexpand': ('expansion', 'native-command-dispatch',
   'Active CCExpand slots use typed native handlers; helper stack/WRAM assembly is replaced. Empty SwirlDisplayRGB is not claimed implemented.',
   [('src/game/display_text_cc.c','bool cc_1a_dispatch'),('src/game/display_text_cc.c','case 14:'),('src/game/display_text_cc.c','case 0x21:')]),
 'dont_care_names': ('expansion', 'converted-table-native-reader',
   'All 49 eleven-byte entries are retained; the native reader derives the stride from the asset length.',
   [('src/intro/file_select.c','static const uint8_t *get_dont_care_name')]),
 'expand_shops': ('expansion', 'converted-table-native-reader',
   'The linked 69-shop table, including custom shops 66-68, is imported and read by native shop menus. Bulk purchase/dialogue semantics belong to the separate shop audit.',
   [('src/game/display_text_menus.c','store_table_data')]),
 'expand_text_windows': ('expansion', 'converted-geometry-native-ownership',
   'All 62 geometries are retained. Converted script IDs 53-61 become 64-72 to avoid PC settings IDs; native PC command/naming/file windows intentionally retain their own geometry. SNES byte-sized existence-table patches do not apply to the C window structures.',
   [('src/game/maternalbound.c','maternalbound_script_window'),('src/game/maternalbound.c','maternalbound_window_config'),('src/game/window.c','maternalbound_window_config')]),
 'favorite_food': ('expansion', 'native-capacity-and-save-adapter',
   'Ten food glyphs use tagged spare save bytes; the original six-byte GameState field remains ABI stable. Naming and text expansion use the enlarged capacity. Default-width limits remain source defined.',
   [('src/game/maternalbound.c','maternalbound_food_capacity'),('src/game/game_state.c','redux_food_extra'),('src/game/display_text.c','case 4: return maternalbound_food_capacity()')]),
 'four_frames_run': ('redux', 'converted-tables-native-animation',
   'Three 17-by-8 source tables supplement the original table. Native animation toggles VAR4 and chooses running/walking, pajamas, ghost, ladder, rope, robot and tiny variants. Source tables are checked separately from bounded runtime animation fixtures.',
   [('src/game/maternalbound.c','maternalbound_sprite_variant'),('src/entity/callroutine_movement.c','entities.var[4]'),('src/game/position_buffer.c','maternalbound_motion_selftest')]),
 'movement_reloc': ('redux', 'converted-pointer-table',
   'All 899 pointer entries (898 nonzero) are retained, including custom IDs 895-898; pointer validity is not complete scene execution.',
   [('src/data/event_script_data.c','resolve_script_address'),('src/entity/opcodes.c','case OP_SHORTJUMP:')]),
 'movscr_codes': ('redux', 'native-bytecode-and-typed-helpers',
   'Long tasks/result-store/result-load and six typed helpers are implemented. Destructor opcode 34 and destructor callbacks are not adapted; pinned sources and reachable-bytecode checks currently show no active use, so this is an unused-library gap rather than verified gameplay parity.',
   [('src/entity/opcodes.c','Redux\'s m_task_long'),('src/entity/opcodes.c','Redux reserves the top two bytes'),('src/entity/callroutine.c','ROM_ADDR_REDUX_DISTANCE_FROM_PLAYER')]),
 'naming_screen_table': ('redux', 'native-source-table-adapter',
   'The pinned six-row upper/lower keyboard and glyph selection/cursor stops are represented directly in native code, retaining the existing pack identity and converted font. Every native glyph is compared with the compiled character-offset table. Redux grid glyphs use naming-only fixed tiles 0x200-0x26F so labels cannot spill into the text tilemap at tile 0x380; actual glyph pixels/ranges are checked separately by ordinary-input runtime QA.',
   [('src/intro/file_select.c','kb_redux_upper_grid'),('src/intro/file_select.c','kb_redux_lower_grid'),('src/intro/file_select.c','kb_redux_row_stops'),('src/intro/file_select.c','static void kb_write_redux_char')]),
 'run_patch': ('redux', 'native-running-adapter',
   'Native input uses Y, inversion flag 56, stamina availability and run flag 65. Unlike the source inverted branch, the native tick maintains flag 65 for either inversion state; this is an explicit PC consistency adaptation.',
   [('src/game/maternalbound.c','bool maternalbound_running'),('src/game/maternalbound.c','event_flag_set(65)'),('src/game/position_buffer.c','maternalbound_running()')]),
 'run_stamina_mechanic': ('redux', 'native-timers-and-effects',
   'Native eight-bit timer arithmetic retains primary 191, secondary 143, fifteen-second capacity and eight-second exhaustion delay, plus source movement high-byte eligibility and sweat overlays. Attract-mode initialization is reviewed separately from ordinary play.',
   [('src/game/maternalbound.c','maternalbound_stamina_update'),('src/game/maternalbound.c','entities.var[7][entity] & 0xFF00'),('src/game/position_buffer.c','entities.overlay_flags[entity_offset]')]),
 'select_changes_letters_in_naming_screen': ('redux', 'native-input',
   'Select toggles case without removing entered glyphs; B retains backspace.',
   [('src/intro/file_select.c','pressed & PAD_SELECT'),('src/intro/file_select.c','maternalbound_enabled() ? PAD_B : PAD_CANCEL')]),
 'six_letters': ('redux', 'native-capacity-save-and-render-adapter',
   'The first five letters retain retail offsets and tagged extra save bytes store the sixth. Native menus, dialogue, battle HP/name spacing, Lumine Hall and ending readers use the expanded name. Default-width forty-pixel input limit is retained. These bindings are not an exhaustive rendering oracle.',
   [('src/game/maternalbound.c','maternalbound_name_capacity'),('src/game/game_state.c','redux_name_magic'),('src/intro/file_select.c','get_text_pixel_width(FONT_ID_NORMAL,s->eb_name,s->name_pos)>40'),('src/entity/callroutine.c','lcps_name_len < maternalbound_name_capacity()'),('src/game/ending.c','maternalbound_character_name')]),
 'reset_routine': ('redux', 'native-root-reset',
   'Dad and Gauss good-night scripts use stable adapter 16, requesting a deferred root reset rather than executing 65816 reset code. Owner saves are not written by the reset; live branch evidence is recorded separately in redux-reset-runtime-review.json.',
   [('src/game/display_text_cc.c','case 16: host_request_reset()'),('src/game_main.c','if (action == ROOT_ACTION_RESET)')]),
 'debug_fixes': ('redux', 'developer-only-partial-native-adapter',
   'Kirby boot debugger graphics, controls and several original boot-debug fixes are not fully adapted. Native developer menus and converted dialogue are separate. No normal-story parity claim is made from their existence.',
   [('src/game_main.c','mode_step_debug_menu')]),
 'debug_menu_enabler': ('debug', 'release-disabled-boot-hook',
   'Pinned DEBUG_BUILD is zero, disabling the boot L/R debugger hook. Native developer menu activation remains an explicit host option; its presence is not equivalent to wholesale Kirby debugger conversion.',
   [('src/game_main.c','ow.debug_flag = 1;')]),
}


def sha(data): return hashlib.sha256(data).hexdigest()


def naming_matrices(rom, labels):
    table = labels[('naming_screen_table','character_table')]-0xC00000
    offsets = rom[table:table+84]
    if len(offsets) != 84: raise ValueError('Truncated naming character table')
    matrices = {}
    for name in ('main_capital','main_small','player_capital','player_small'):
        base = labels[('naming_screen_table',name)]-0xC00000
        matrices[name] = [[255 if offset == 255 else rom[base+offset]
                           for offset in offsets[row*14:(row+1)*14]] for row in range(6)]
    if matrices['main_capital'] != matrices['player_capital'] or matrices['main_small'] != matrices['player_small']:
        raise ValueError('Standalone and new-game glyph tables differ; review both keyboards')
    return matrices


def native_matrix(text, name):
    block = text.split(name+'[KB_REDUX_GRID_ROWS][KB_GRID_COLS] = {',1)[1].split('};',1)[0]
    values = [int(value,16) for value in re.findall(r'0x([0-9A-Fa-f]{2})',block)]
    if len(values) != 84: raise ValueError('Malformed native naming matrix: '+name)
    return [values[row*14:(row+1)*14] for row in range(6)]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('project','native-source','bridge','compiled-rom','assets','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args(); upstream=a.project.parent
    if subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()!=PIN:
        raise ValueError('Review the module map after an upstream revision change')
    rom=a.compiled_rom.read_bytes()
    if sha(rom)!=ROM_SHA: raise ValueError('Compiled ROM differs from the reviewed pinned content')
    bridge=json.loads(a.bridge.read_text(encoding='utf-8-sig'))
    if bridge['source']['revision']!=PIN or bridge['roms']['compiled']['sha256'].lower()!=ROM_SHA:
        raise ValueError('Bridge source/compiled-ROM identity mismatch')
    labels={(row['module'],row['name']):row['snesAddress'] for row in bridge['labels']}
    _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h')
    main_source=(a.project/'ccscript/main.ccs').read_text(encoding='utf-8-sig')
    clean_main=without_comments(main_source); rows=[]
    for module,(folder,kind,note,bindings) in MODULES.items():
        relative=f'ccscript/{folder}/{module}.ccs'; path=a.project/relative; source=path.read_bytes()
        pinned=subprocess.check_output(['git','-C',str(upstream),'show','HEAD:Project/'+relative])
        if source.replace(b'\r\n',b'\n')!=pinned.replace(b'\r\n',b'\n'):
            raise ValueError('Pinned source changed: '+relative)
        activation=f'import "{folder}/{module}.ccs"'
        if activation not in clean_main:raise ValueError('Module no longer active in main.ccs: '+module)
        clean=without_comments(source.decode('utf-8-sig')); refs=[]
        for relative_native,anchor in bindings:
            text=(a.native_source/relative_native).read_text(encoding='utf-8');at=text.find(anchor)
            if at<0:raise ValueError('Missing native binding: '+relative_native+': '+anchor)
            refs.append({'path':relative_native,'line':text[:at].count('\n')+1,'anchor':anchor})
        writes=re.findall(r'^\s*ROM(?:TBL)?\[([^\]\n]+)\]',clean,re.M)
        rows.append({'module':module,'source':relative,'sourceSha256':sha(source),
                     'activation':{'path':'ccscript/main.ccs','line':main_source[:main_source.index(activation)].count('\n')+1},
                     'syntacticRomWriteSites':len(writes),'writeExpressions':writes,
                     'classification':kind,'reviewDecision':note,'nativeReferences':refs})
    checks=[]
    def equal(name,actual,wanted):
        if actual!=wanted:raise ValueError('Converted/source data mismatch: '+name)
        checks.append({'name':name,'bytes':len(actual),'sha256':sha(actual),'compiledAndConvertedMatch':True})
    def span(module,label,size):
        at=labels[(module,label)]-0xC00000;return rom[at:at+size]
    equal('49 eleven-byte default names',assets['US/data/dont_care_names.bin'],span('dont_care_names','dont_care_names',539))
    equal('69 seven-item shop rows',assets['data/store_table.bin'],span('expand_shops','NewShopTable',483))
    equal('62 window configurations',assets['US/graphics/text_window_flavour_palettes.pal'][464:],span('expand_text_windows','NewWindowTable',496))
    variants=assets['data/playable_character_graphics_table.bin']
    if variants[272:280]!=b'MRWALK01' or len(variants)!=1096:raise ValueError('Invalid animation table container')
    for index,name in enumerate(('extra_animation_sprite_table','extra_animation_sprite_table_running1','extra_animation_sprite_table_running2')):
        equal(name,variants[280+index*272:280+(index+1)*272],span('four_frames_run',name,272))
    if rom[0x93DA]!=0xBF:raise ValueError('Movement table pointer loader changed')
    at=int.from_bytes(rom[0x93DB:0x93DE],'little')-0xC00000
    equal('899 movement pointers',assets['US/events/event_script_pointers.bin'],rom[at:at+2697])
    keyboard=(a.native_source/'src/intro/file_select.c').read_text(encoding='utf-8')
    matrices=naming_matrices(rom,labels)
    for kind,name in (('main_capital','kb_redux_upper_grid'),('main_small','kb_redux_lower_grid')):
        if native_matrix(keyboard,name)!=matrices[kind]:raise ValueError('Native naming glyphs differ from pinned compiled selection table: '+kind)
    width_ptr,gfx_ptr,stride,height=struct.unpack_from('<IIHH',rom,0x3F054)
    equal('normal font glyph widths',assets['US/fonts/main.bin'],rom[width_ptr-0xC00000:width_ptr-0xC00000+128])
    equal('normal font glyph bitmaps',assets['US/fonts/main.gfx'],rom[gfx_ptr-0xC00000:gfx_ptr-0xC00000+128*stride])
    glyphs=sorted({value for matrix in (matrices['main_capital'],matrices['main_small']) for row in matrix for value in row if value!=255})
    widths=assets['US/fonts/main.bin']; graphics=assets['US/fonts/main.gfx']
    if any(not (0x50<=g<0xD0) or not widths[g-0x50] or not any(graphics[(g-0x50)*stride:(g-0x50+1)*stride]) for g in glyphs if g!=0x50):
        raise ValueError('Selectable non-space glyph has absent font data')
    if height!=16 or any(widths[g-0x50]+1>8 for g in glyphs):
        raise ValueError('Pinned naming grid no longer fits its fixed one-column glyph budget')
    source=(a.project/'ccscript/debug/debug_menu_enabler.ccs').read_text(encoding='utf-8-sig')
    if not re.search(r'^define DEBUG_BUILD = 0$',source,re.M):raise ValueError('Pinned boot-debug activation changed')
    movement=movement_audit(assets,a.native_source)
    destructor_calls=[]
    for record in bridge['sourceGraph']['files']:
        relative=record['path'];clean=without_comments((a.project/relative).read_text(encoding='utf-8-sig'))
        for number,line in enumerate(clean.splitlines(),1):
            if re.search(r'^\s*m_ondestroy\b',line):destructor_calls.append({'path':relative,'line':number})
    if destructor_calls or movement['Opcodes'].get('34',0):
        raise ValueError('Unadapted destructor opcode is active; this cannot be classified as an unused library feature')
    result={'format':'redux-remaining-feature-review-v1','Passed':True,'upstreamCommit':PIN,
            'compiledRomSha256':sha(rom),'packSha256':sha(a.assets.read_bytes()),
            'reviewedModules':len(rows),'classificationCounts':dict(Counter(row['classification'] for row in rows)),
            'modules':rows,'dataChecks':checks,
            'namingKeyboard':{'compiledGlyphMatricesMatchNative':True,'selectableUpperCells':sum(g!=255 for row in matrices['main_capital'] for g in row),
                             'selectableLowerCells':sum(g!=255 for row in matrices['main_small'] for g in row),
                             'uniqueGlyphsWithConvertedFontData':len(glyphs),'alphabetRow':5,'digitRow':4,
                             'convertedFontHeight':height,'selectableGlyphsFitSingleColumns':True,
                             'fixedGridVramTiles':['200','26F'],'cursorTiles':['28D','29D'],'nameDisplayFirstTile':'2E0','textTilemapFirstTile':'380',
                             'standaloneAndNewGameGlyphTablesMatch':True,'runtimeParityVerifiedByThisScript':False},
            'movementLibrary':{'staticReachabilityPassed':movement['Passed'],'reachableInstructions':movement['Instructions'],
                               'reachableDestructorOpcodes':movement['Opcodes'].get('34',0),'activeSourceDestructorCalls':destructor_calls},
            'unadaptedOrUnverified':[{'module':'movscr_codes','feature':'m_ondestroy opcode and callback lifecycle','normalGameplayUseFound':False},
                                    {'module':'debug_fixes/debug_menu_enabler','feature':'Kirby boot debugger wholesale parity','bootHookEnabledInPinnedRelease':False},
                                    {'module':'reset_routine','feature':'Dad and Gauss good-night dialogue paths and reset continuation in a live scene','nativeAdapterPresent':True,'livePathsVerifiedByThisScript':False,'runtimeReview':'research/redux-reset-runtime-review.json'}],
            'fullSemanticParityClaimed':False,'fullPlaythroughVerified':False,
            'limits':['Write counts are syntactic inventory, including macro definitions; they are not counts of instantiated patches.',
                      'Native references and exact converted data are evidence of adapters, not every gameplay branch.',
                      'No emulator oracle, complete story/randomized playthrough, audio listening or visual pixel parity is performed by this script.']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:result[key] for key in ('Passed','reviewedModules','namingKeyboard','movementLibrary','fullSemanticParityClaimed')},indent=2))


if __name__=='__main__':main()
