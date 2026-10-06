# SPDX-License-Identifier: GPL-3.0-or-later
"""Complete private executable title/menu captures and fresh-process restores.

Every candidate execution uses a fresh private session. Capture-state requests
the production F6 root/save-slot path. Prepared source-entry readers and legal
raw names are the only injected prerequisites; no titles, windows or VRAM are
injected. Reports contain metadata only. No shared builds or owner writes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from build_maternalbound_pack import read_pack
from check_jev_observer_parity import latest, local_scratch, sections
from redux_recovery_qa import write_state
import redux_naming_qa as naming

ROOT = Path(__file__).resolve().parents[1]
MIXED = [0x79, 0xB0, 0xC0, 0x60, 0xB8, 0xB9]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def layout(source, compiler, build, out):
    base = naming.compile_layout(source, compiler, out)
    c = out / 'title-layout.c'; exe = out / 'title-layout.exe'
    c.write_text(r'''#include <stdio.h>
#include <stddef.h>
#include "core/mode_stack.h"
#include "game/window.h"
#include "game/game_state.h"
#define F(T,N) printf("\"" #T "." #N "\":%zu,",offsetof(T,N))
int main(void){printf("{"); F(WindowInfo,title);F(WindowInfo,title_slot);
F(WindowInfo,title_tile_count);F(WindowInfo,menu_count);F(WindowInfo,current_option);
F(WindowInfo,selected_option);F(WindowInfo,menu_page_number);F(WindowInfo,menu_items);
F(DisplayTextModeState,phase);F(DisplayTextModeState,reader);
F(ScriptReader,source);F(ScriptReader,ptr_off);F(ScriptReader,end_off);F(ScriptReader,prefix_off);
F(CharStruct,items);
printf("\"displayMode\":%u,\"textEnter\":%u,\"dialogueSource\":%u,\"worldMode\":%u}",GAME_MODE_DISPLAY_TEXT,DT_ENTER,TEXT_SRC_DIALOGUE,GAME_MODE_OVERWORLD);
return 0;}''', encoding='utf-8')
    proc = subprocess.run([str(compiler), '-std=c2x', '-I', str(source / 'src'), '-I', str(build / 'game_lib/generated'), str(c), '-o', str(exe)], capture_output=True, timeout=45)
    if proc.returncode:
        raise RuntimeError(proc.stderr.decode(errors='replace'))
    base.update(json.loads(subprocess.check_output([str(exe)], timeout=10)))
    return base


def tiny_tiles(glyphs, widths, graphics, padding):
    """Independent inverted1bpp source-font compositor; tiny8x8 only."""
    indices = [g - 0x50 for g in glyphs]
    if any(not 0 <= i < len(widths) for i in indices) or len(graphics) != len(widths) * 8:
        raise ValueError('Unexpected tiny glyph/storage domain')
    pixels = sum(widths[i] + padding for i in indices)
    columns = (pixels + 7) // 8
    result = bytearray([255] * (columns * 16)); x = 0
    for i in indices:
        for y, bits in enumerate(graphics[i * 8:i * 8 + 8]):
            for bit in range(8):
                at = x + bit
                if not bits & (128 >> bit) and at < columns * 8:
                    result[(at // 8) * 16 + y * 2 + 1] &= 255 ^ (128 >> (at % 8))
        x += widths[i] + padding
    return bytes(result), columns


def decode_title(raw):
    # Relevant literal ASCII letters/digits from source names and high-bit
    # title encoding. No candidate decoder calls are used as expected output.
    return [b if b >= 0x80 else b + 0x30 for b in raw]


class Session(naming.Session):
    def read(self):
        result = super().read()
        blobs = sections(latest(self.folder), self.tamp); self.blobs = blobs
        w, ppu, l = blobs[8], blobs[10], self.layout
        titles = []
        for i in range(8):
            at = l['WindowSystemState.windows'] + i * l['WindowInfo.size']
            if not w[at + l['WindowInfo.active']]:
                continue
            raw = bytes(w[at + l['WindowInfo.title']:at + l['WindowInfo.title'] + 23]).split(b'\0', 1)[0]
            slot = w[at + l['WindowInfo.title_slot']]
            count = w[at + l['WindowInfo.title_tile_count']]
            base = l['PPUState.vram'] + 0xC000 + (0x2E0 + (slot - 1) * 16) * 16 if slot else 0
            vr = bytes(ppu[base:base + count * 16]) if slot else b''
            titles.append(dict(id=w[at + l['WindowInfo.id']], raw=list(raw), glyphs=decode_title(raw), slot=slot, columns=count, tinyVramSha256=hashlib.sha256(vr).hexdigest(), menuCount=w[at + l['WindowInfo.menu_count']], currentOption=w[at + l['WindowInfo.current_option']], selectedOption=w[at + l['WindowInfo.selected_option']], page=w[at + l['WindowInfo.menu_page_number']]))
        result['titles'] = titles; result['stateVersion'] = struct.unpack_from('<H', latest(self.folder).read_bytes(), 4)[0]
        ms = blobs[21]; result['actualDisplayReaders'] = []
        for index, mode in enumerate(result['modes']):
            if mode == l['displayMode']:
                at = l['ModeStack.state'] + index * l['ModeState.size'] + l['DisplayTextModeState.reader']
                result['actualDisplayReaders'].append(struct.unpack_from('<I', ms, at + l['ScriptReader.ptr_off'])[0])
        return result


def copy_world(session, phone):
    shutil.copy2(phone, session.folder / 'fixture.srm')
    rows = [(0, 0)]
    for f in (200, 400, 600, 800, 1400, 1600):
        rows.extend(((f, naming.CONFIRM), (f + 2, 0)))
    session.run('fresh-source-phone-load', rows, 2200, load=False)
    # File-select builds load occupied slots while still waiting for input;
    # names/party alone therefore cannot prove Continue reached the world.
    if session.last['modes'] != [session.layout['worldMode']]:
        raise ValueError('Actual file-select Continue did not reach world root')
    if session.last['partyCount'] != 1:
        raise ValueError('Phone fixture did not load its actual world')


def new_original_world(session):
    naming.bootstrap(session)
    for target in range(7):
        if target:
            for attempt in range(25):
                k = session.last['keyboard']
                if k and k['target'] == target:
                    break
                session.step('next-original-prompt', [naming.CONFIRM], wait=100)
            else:
                raise ValueError('Original naming prompt was not reached')
        session.clear()
        session.step('source-original-default', session.navigate((0, 6), naming.RETAIL_STOPS) + [naming.CONFIRM])
        session.step('commit-original-default', [naming.START], wait=100)
    session.step('finish-original-opening', [naming.CONFIRM], wait=4000)
    if session.last['partyCount'] != 1:
        raise ValueError('Original opening did not reach world')


def clone_scene(source, target, label):
    target.mkdir()
    for name in ('saves', 'fixture.srm'):
        p = source / name
        if p.is_dir():
            shutil.copytree(p, target / name)
        elif p.exists():
            shutil.copy2(p, target / name)
    return label


def raw_names(session, names):
    state = latest(session.folder); blobs = sections(state, session.tamp); l = session.layout
    for who, name in enumerate(names):
        at = who * l['CharStruct.size'] + l['CharStruct.name']
        blobs[3][at:at + 5] = bytes(name[:5]); blobs[45][who] = name[5] if len(name) == 6 else 0
    write_state(state, blobs, session.tamp)


def inventory_prerequisite(session, source):
    # Both starting world fixtures may have no ordinary items. Source constants
    # provide ordinary Cookie/Hamburger IDs; their acquisition is excluded.
    text = (source / 'include/constants/items.asm').read_text(encoding='utf-8')
    items = [int(re.search(r'\b' + name + r'\s*=\s*\$([0-9A-F]+)', text)[1], 16) for name in ('COOKIE', 'HAMBURGER')]
    state = latest(session.folder); blobs = sections(state, session.tamp)
    at = session.layout['CharStruct.items']; blobs[3][at:at + 2] = bytes(items)
    write_state(state, blobs, session.tamp)
    session.step('prepared-source-ordinary-item-entry', wait=30)
    return items


def source_parent(session, assets, entry):
    state = latest(session.folder); blobs = sections(state, session.tamp); l = session.layout
    dialogue = assets['dialogue/dialogue.bin']; footer = dialogue[-32:]
    if footer[:8] != b'MRDXNV01':
        raise ValueError('Missing actual relocated source labels')
    mapoff, count = struct.unpack_from('<II', footer, 12)
    mapping = dict(struct.unpack_from('<II', dialogue, mapoff + i * 8) for i in range(count))
    ms = blobs[21]; depth = ms[l['ModeStack.depth']]
    if depth != 1:
        raise ValueError('Expected ordinary world root before prepared source child')
    ms[l['ModeStack.depth']] = depth + 1; ms[l['ModeStack.mode'] + depth] = l['displayMode']
    at = l['ModeStack.state'] + depth * l['ModeState.size']; ms[at:at + l['ModeState.size']] = bytes(l['ModeState.size'])
    ms[at + l['DisplayTextModeState.phase']] = l['textEnter']; reader = at + l['DisplayTextModeState.reader']
    ms[reader + l['ScriptReader.source']] = l['dialogueSource']
    struct.pack_into('<IIi', ms, reader + l['ScriptReader.ptr_off'], mapping[entry] - 0x100000, len(dialogue), -1)
    write_state(state, blobs, session.tamp)


def observe(session, expected, title_id=None):
    candidates = [r for r in session.last['titles'] if r['slot'] and (title_id is None or r['id'] == title_id)]
    if not candidates:
        raise ValueError('No expected active titled window')
    row = next((r for r in candidates if r['glyphs'] == expected), candidates[-1])
    assets = session.qa_assets
    bitmap, columns = tiny_tiles(expected, assets['US/fonts/tiny.bin'], assets['US/fonts/tiny.gfx'], session.blobs[31][0])
    return dict(title=row, expectedGlyphs=expected, expectedTinyVramSha256=hashlib.sha256(bitmap).hexdigest(), sourceGlyphsMatch=row['glyphs'] == expected, independentTinyTilesMatch=row['tinyVramSha256'] == hashlib.sha256(bitmap).hexdigest() and row['columns'] == columns, format16=session.last['stateVersion'] == 16)


def cold_pair(session, expected, title_id=None, do_input=True):
    before = observe(session, expected, title_id)
    session.step('fresh-process-f6-title-menu-resume', wait=30)
    after = observe(session, expected, title_id)
    item = dict(before=before, after=after, titleMenuAndTinyVramPreserved=before['title'] == after['title'], realCaptureSlotSha256=sha(latest(session.folder)))
    if do_input:
        previous = after['title']['currentOption']
        session.step('real-down-after-cold-menu', [naming.DOWN], wait=30)
        moved = observe(session, expected, title_id)
        item['ordinaryDownAfterCold'] = dict(previous=previous, current=moved['title']['currentOption'], titleGlyphsPreserved=moved['sourceGlyphsMatch'], tinyTilesPreserved=moved['independentTinyTilesMatch'])
    item['Passed'] = all(before[k] and after[k] for k in ('sourceGlyphsMatch', 'independentTinyTilesMatch', 'format16')) and item['titleMenuAndTinyVramPreserved']
    return item


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for n in ('source', 'player-build', 'observer-build', 'runtime', 'original-assets', 'redux-assets', 'redux-phone-seed', 'scratch', 'output'):
        ap.add_argument('--' + n, type=Path, required=True)
    ap.add_argument('--compiler', type=Path, default=ROOT / 'tools/mingw64/bin/gcc.exe')
    a = ap.parse_args()
    for k, v in vars(a).items():
        setattr(a, k, v.resolve())
    a.scratch = local_scratch(a.scratch)
    if a.scratch.exists() or a.output.exists():
        raise ValueError('Preserve evidence: fresh output and scratch required')
    a.scratch.mkdir(); sys.path.insert(0, str(a.source / 'src/vendor/tamp')); import tamp
    l = layout(a.source, a.compiler, a.player_build, a.scratch)
    source_baseline = ROOT / '_BuildScratch/audit-dev17-v4-complete-source'
    # Both structs have identical preprocessing/token declarations; no changes
    # to format16 or fields are allowed by this title-only proposal.
    strip = lambda t: re.sub(r'/\*.*?\*/|//[^\n]*', '', t, flags=re.S)
    same_window = strip((a.source / 'src/game/window.h').read_text(encoding='utf-8')) == strip((source_baseline / 'src/game/window.h').read_text(encoding='utf-8'))
    if not same_window or '#define STATE_DUMP_VERSION 16 ' not in (a.source / 'src/core/state_dump.c').read_text(encoding='utf-8'):
        raise ValueError('Title proposal changed save schema/WindowInfo')
    results = []; build_ids = {}
    for build_name in ('player', 'observer'):
        build = getattr(a, build_name + '_build'); exe = a.runtime / (build_name + '.exe')
        if sha(exe) != sha(build / 'earthbound.exe'):
            raise ValueError('Candidate full executable/build mismatch')
        build_ids[build_name] = dict(executableSha256=sha(exe), archiveSha256=sha(build / 'game_lib/libearthbound_game.a'), cmakeCacheSha256=sha(build / 'CMakeCache.txt'), compileCommandsSha256=sha(build / 'compile_commands.json'))
        for profile, pack in (('original', a.original_assets), ('redux', a.redux_assets)):
            parent = a.scratch / (build_name + '-' + profile); parent.mkdir()
            base = Session(exe, pack, parent / 'world', l, tamp)
            _, _, assets = read_pack(pack, a.source / 'src/data/runtime_generated/asset_ids.h'); base.qa_assets = assets
            if profile == 'redux':
                copy_world(base, a.redux_phone_seed)
                if base.last['names'][0] != MIXED:
                    raise ValueError('Source/input-proved mixed name lost at fresh phone load')
            else:
                new_original_world(base)
            fixture_items = inventory_prerequisite(base, a.source)
            # Pinned Redux maps command menu to X and starts at Goods;
            # retail maps it to A and starts at Talk-to, one Down from Goods.
            base.step('ordinary-command-menu', [0x40 if profile == 'redux' else 0x80], wait=40)
            base.step('ordinary-goods-choice', ([naming.DOWN] if profile == 'original' else []) + [naming.CONFIRM], wait=40)
            expected = MIXED if profile == 'redux' else [g for g in base.last['names'][0][:5] if g]
            menu = cold_pair(base, expected, 2)
            result = dict(build=build_name, profile=profile, packSha256=sha(pack), inventoryTitle=menu, sourceDefinedPreparedItemIds=fixture_items)
            # Real relocated Paula call starts at its actual complete script
            # entry; native text/prompt/title dispatcher runs without wrappers.
            if profile == 'redux':
                base.step('exit-goods', [naming.B, naming.B], wait=60)
                variants = [MIXED, [0x7A, 0xB1, 0xC1, 0x61, 0xB9, 0xB8], [0x7B, 0xB2, 0xC2, 0x62, 0xB8, 0xB9], [0x7C, 0xB3, 0xC3, 0x63, 0xB9, 0xB8]]
                raw_names(base, variants); source_parent(base, assets, 0xC68CC3)
                base.step('full-actual-paula-title-parent', wait=40)
                for attempt in range(30):
                    if any(r['slot'] for r in base.last['titles']):
                        break
                    base.step('source-text-before-title', [naming.CONFIRM], wait=40)
                else:
                    raise ValueError('Actual pinned Paula source title not reached')
                result['paulaSourceTitle'] = cold_pair(base, variants[1], 1, False)
                previous_readers = list(base.last['actualDisplayReaders'])
                base.step('real-source-text-after-cold-title', [naming.CONFIRM], wait=40)
                result['sourceParentContinuedAfterCold'] = previous_readers != base.last['actualDisplayReaders']
                if not result['sourceParentContinuedAfterCold']:
                    raise ValueError('Actual source parent failed to advance after cold input')
                result['preparedNames'] = variants
            results.append(result)
            print(json.dumps({'completed': build_name + '-' + profile, 'inventoryPassed': menu['Passed']}), flush=True)
    report = dict(format='private-full-executable-title-cold-dev18-v1', completeCandidateBuilds=build_ids, candidateSource=str(a.source), sourceIdentities={p: sha(a.source / p) for p in ('src/game/text.c', 'src/game/text.h', 'src/game/display_text.c', 'src/game/display_text_cc.c', 'src/game/window.h', 'src/game/display_text_menus.c', 'src/core/state_dump.c')}, windowInfoDeclarationUnchanged=same_window, format16Unchanged=True, results=results, allPassed=all(r['inventoryTitle']['Passed'] and r.get('paulaSourceTitle', {}).get('Passed', True) for r in results), inputSeed=dict(path=str(a.redux_phone_seed), sha256=sha(a.redux_phone_seed), originatingOrdinaryNamingProof='research/redux-naming-runtime-review.json'), toolSha256=sha(Path(__file__)), runnerDependencies={str(Path(naming.__file__).relative_to(ROOT)): sha(Path(naming.__file__)), 'tools/redux_recovery_qa.py': sha(ROOT / 'tools/redux_recovery_qa.py')}, limits=['Complete proposed player and observer binaries execute real input replay, text/menu interpreter and capture/save/load code. Capture-state enters the same production root writer as F6; physical keyboard/controller F6 is not synthesized.', 'Redux mixed name1 comes from a private ordinary-input-proved phone seed; other character names and a full source-parent reader are prepared from exact public layout/source entry prerequisites, not naturally acquired story states.', 'Window title/menu state and actual tiny-font VRAM are captured through format16 and restored in fresh processes. Independent font compositor validates source glyph contributions; this is not an original CPU whole-screen renderer oracle.', 'Original uses ordinary new-game default naming and actual X/Goods input controls; it does not exercise Redux-only extended title commands.', 'Candidate private source/build/runtime only. No root source, owner save, commercial ROM/pack or old frozen report is changed.'], rootOrOwnerInputsModified=False)
    a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'allPassed': report['allPassed'], 'report': str(a.output), 'sha256': sha(a.output)}))


if __name__ == '__main__':
    main()
