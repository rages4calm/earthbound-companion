# SPDX-License-Identifier: GPL-3.0-or-later
"""Create a separate private complete title-producer candidate from proposal1.

Only exact ASCII-to-title conversion sites are replaced. General dialogue and
menu label conversions remain byte-identical. No shared source is edited.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from check_jev_observer_parity import local_scratch

ROOT = Path(__file__).resolve().parents[1]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base', type=Path, required=True)
    ap.add_argument('--candidate', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args(); a.base = a.base.resolve(); a.candidate = local_scratch(a.candidate.resolve())
    if a.candidate.exists() or a.output.exists(): raise ValueError('Fresh private candidate/report required')
    shutil.copytree(a.base, a.candidate)
    edits = {}
    def replace(rel, old, new, count=1):
        path = a.candidate / rel; text = path.read_text(encoding='utf-8')
        if text.count(old) != count: raise ValueError(f'Unexpected site count {rel}: {text.count(old)} != {count}')
        path.write_text(text.replace(old, new), encoding='utf-8', newline='')
        edits.setdefault(rel, []).append(dict(before=old, after=new, sites=count))
    replace('src/game/text.h', 'char eb_char_to_title_byte(uint8_t eb_char);', 'char eb_char_to_title_byte(uint8_t eb_char);\n/* Bounded EB-to-title-only string conversion; leaves ordinary text unchanged. */\nint eb_to_title_buf(const uint8_t *src, int max_len, char *dst, int capacity);')
    replace('src/game/text.c', 'uint8_t title_byte_to_eb_char(char title_byte) {', '''int eb_to_title_buf(const uint8_t *src, int max_len, char *dst, int capacity) {
    int copied = 0;
    if (!dst || capacity <= 0) return 0;
    if (src) {
        for (int i = 0; i < max_len && src[i] && copied + 1 < capacity; i++)
            dst[copied++] = eb_char_to_title_byte(src[i]);
    }
    dst[copied] = '\\0';
    return copied;
}

uint8_t title_byte_to_eb_char(char title_byte) {''')
    for rel, expression in (
        ('src/game/text.c', 'maternalbound_character_name(char_idx)[j]'),
        ('src/game/battle.c', 'maternalbound_character_name_of(ch)[j]'),
        ('src/game/battle_psi.c', 'maternalbound_character_name(char_idx)[j]'),
        ('src/game/display_text.c', 'maternalbound_character_name_of(c)[i]')):
        replace(rel, 'name_buf[' + ('i' if expression.endswith('[i]') else 'j') + '] = eb_char_to_ascii(' + expression + ');', 'name_buf[' + ('i' if expression.endswith('[i]') else 'j') + '] = eb_char_to_title_byte(' + expression + ');')
    for rel in ('src/game/battle.c', 'src/game/display_text_menus.c'):
        replace(rel, 'eb_to_ascii_buf(maternalbound_character_name(char_idx), maternalbound_name_capacity(), name_buf);', 'eb_to_title_buf(maternalbound_character_name(char_idx), maternalbound_name_capacity(), name_buf, sizeof(name_buf));')
    for source, maximum in (('status_equip_text_14', '(int)status_equip_text_14_size'), ('status_equip_text_7', '(int)status_equip_text_7_size'), ('phone_call_text_data', '(int)phone_call_text_size')):
        replace('src/game/display_text_menus.c', f'eb_to_ascii_buf({source}, {maximum}, title_buf);', f'eb_to_title_buf({source}, {maximum}, title_buf, sizeof(title_buf));')
    replace('src/game/text.c', 'eb_to_ascii_buf(title_src, ETEXT11_STRIDE, title_buf);', 'eb_to_title_buf(title_src, ETEXT11_STRIDE, title_buf, sizeof(title_buf));')
    rows = []
    for path in a.candidate.rglob('*'):
        if path.is_file():
            rel = path.relative_to(a.candidate); old = a.base / rel
            if sha(old) != sha(path): rows.append(dict(path=str(rel).replace('\\','/'), baseSha256=sha(old), candidateSha256=sha(path)))
    expected = sorted(edits)
    if sorted(r['path'] for r in rows) != expected: raise ValueError('Unexpected source changes')
    report = dict(format='private-complete-title-producers-preparation-dev18-v1', base=str(a.base), candidate=str(a.candidate), changedFiles=rows, exactTitleOnlySites=edits, toolSha256=sha(Path(__file__)), rootSourceModified=False, limits=['Build, direct producer, ordinary input, cold rendering tests remain separate requirements. This preparation is not gameplay proof.', 'The existing five-file proposal is copied unchanged as input; only direct title producer conversions and a bounded helper are added.'])
    a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(report=str(a.output), changedFiles=len(rows))))

if __name__ == '__main__': main()
