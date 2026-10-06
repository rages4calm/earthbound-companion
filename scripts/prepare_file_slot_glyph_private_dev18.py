# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepare a separate private source-backed file-slot label candidate.

No title/dialogue conversion, save schema, root source or owner data is changed.
The baseline must include the frozen title and pure file-slot occupancy fixes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from check_jev_observer_parity import local_scratch

ROOT = Path(__file__).resolve().parents[1]
FILES = ('src/intro/file_select.c', 'src/game/window.c')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for n in ('base', 'candidate', 'output'):
        ap.add_argument('--' + n, type=Path, required=True)
    a = ap.parse_args()
    for n, v in vars(a).items():
        setattr(a, n, v.resolve())
    a.candidate = local_scratch(a.candidate)
    if a.candidate.exists() or a.output.exists():
        raise ValueError('Fresh candidate/report required')
    shutil.copytree(a.base, a.candidate)
    edits = {}
    def replace(rel, old, new, count=1):
        p = a.candidate / rel
        s = p.read_text(encoding='utf-8')
        if s.count(old) != count:
            raise ValueError('Unexpected source site ' + rel)
        p.write_text(s.replace(old, new), encoding='utf-8', newline='')
        edits.setdefault(rel, []).append(dict(before=old, after=new, count=count))
    replace(FILES[0], 'static int fm_file_select_build(void) {', '''/* FILE_SELECT_MENU copies raw name glyphs into the source slot label.
 * This native menu stores ASCII labels, so keep reversible ASCII bytes while
 * retaining source-only high glyphs as single bytes. Only file-slot consumers
 * decode this bounded representation; ordinary dialogue conversion is unchanged. */
static char file_slot_label_byte(uint8_t glyph) {
    char ascii = eb_char_to_ascii(glyph);
    if (ascii_to_eb_char(ascii) == glyph) return ascii;
    return glyph >= 0x80 ? (char)glyph : ascii;
}

static int fm_file_select_build(void) {''')
    replace(FILES[0], 'name[i] = eb_char_to_ascii(maternalbound_character_name(0)[i]);', 'name[i] = file_slot_label_byte(maternalbound_character_name(0)[i]);', count=2)
    replace(FILES[1], 'void print_menu_items(void) {', '''/* Occupied file-slot labels preserve source name glyphs that lack an ASCII
 * equivalent. They are bounded, single-byte labels in the existing MenuItem;
 * slot userdata 1..3 and WINDOW_FILE_SELECT_MAIN identify both live and F6
 * restored consumers without changing the serialized struct. Empty/ASCII
 * labels and every other menu retain the existing ASCII contract. */
static bool menu_item_is_file_slot(const WindowInfo *w, const MenuItem *item) {
    return w->id == WINDOW_FILE_SELECT_MAIN &&
           item->userdata >= 1 && item->userdata <= SAVE_COUNT;
}

static uint8_t menu_item_label_glyph(const WindowInfo *w,
                                     const MenuItem *item, unsigned index) {
    uint8_t byte = (uint8_t)item->label[index];
    if (menu_item_is_file_slot(w, item) && byte >= 0x80) return byte;
    return ascii_to_eb_char(item->label[index]);
}

void print_menu_items(void) {''')
    replace(FILES[1], '        print_string(item->label);', '''        if (menu_item_is_file_slot(w, item)) {
            uint8_t glyphs[sizeof(item->label)] = {0};
            unsigned length = 0;
            while (length < sizeof(item->label) && item->label[length]) {
                glyphs[length] = menu_item_label_glyph(w, item, length);
                ++length;
            }
            print_eb_string(glyphs, (int)length);
        } else {
            print_string(item->label);
        }''')
    replace(FILES[1], 'uint8_t glyph = (ascii_to_eb_char(item->label[i]) - 0x50) & 0x7F;', 'uint8_t glyph = (menu_item_label_glyph(w, item, i) - 0x50) & 0x7F;')
    changes = []
    for p in (a.candidate / 'src').rglob('*'):
        if p.is_file():
            rel = p.relative_to(a.candidate).as_posix()
            if sha(p) != sha(a.base / rel):
                changes.append(dict(path=rel, baseSha256=sha(a.base/rel), candidateSha256=sha(p)))
    if sorted(r['path'] for r in changes) != sorted(FILES):
        raise ValueError('Unexpected additional source change')
    report = dict(format='private-file-slot-glyph-preparation-dev18-v1', base=str(a.base), candidate=str(a.candidate), changes=changes, exactEdits=edits, toolSha256=sha(Path(__file__)), allOtherSrcFilesByteIdentical=True, format16Unchanged=sha(a.base/'src/core/state_dump.c')==sha(a.candidate/'src/core/state_dump.c'), menuItemAndWindowInfoUnchanged=sha(a.base/'src/game/window.h')==sha(a.candidate/'src/game/window.h'), rootOrOwnerInputsModified=False)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(report=str(a.output), changes=changes)))

if __name__ == '__main__':
    main()
