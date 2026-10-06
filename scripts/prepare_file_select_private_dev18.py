# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepare a separate private pure phone occupancy/file-select candidate."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from check_jev_observer_parity import local_scratch

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('base','candidate','output'):ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args()
    for n,v in vars(a).items():setattr(a,n,v.resolve())
    a.candidate=local_scratch(a.candidate)
    if a.candidate.exists() or a.output.exists():raise ValueError('Fresh candidate/report required')
    shutil.copytree(a.base,a.candidate);edits={}
    def replace(rel,old,new):
        p=a.candidate/rel;text=p.read_text(encoding='utf-8')
        if text.count(old)!=1:raise ValueError('Unexpected source site '+rel)
        p.write_text(text.replace(old,new),encoding='utf-8',newline='');edits.setdefault(rel,[]).append(dict(before=old,after=new))
    replace('src/game/game_state.h','bool load_game(int slot);','bool load_game(int slot);\n/* Check phone-slot occupancy without applying/migrating live game state. */\nbool save_game_slot_occupied(int slot);')
    replace('src/game/game_state.c','/* fuzzy pickles. thats it thats the comment */\nbool save_game(int slot) {','''/* File-menu occupancy uses the same first-valid-copy ADD/XOR checks and
 * favourite-thing sentinel as load_game()/FILE_SELECT_MENU. A cold F6 restore
 * can resume after the slot-list builder, so its derived static presence flags
 * are unavailable. Inspect a local block rather than loading it into live
 * GameState/characters/event flags or performing inventory migrations. */
bool save_game_slot_occupied(int slot) {
    if (slot < 0 || slot >= SAVE_COUNT) return false;
    SaveBlock block;
    for (int copy = 0; copy < SAVE_COPY_COUNT; copy++) {
        size_t offset = (size_t)(slot * SAVE_COPY_COUNT + copy) * sizeof(SaveBlock);
        if (platform_save_read(&block, offset, sizeof(block)) != sizeof(block))
            continue;
        if (block.header.checksum == compute_add_checksum(&block) &&
            block.header.checksum_complement == compute_xor_checksum(&block))
            return block.game_state.favourite_thing[1] != 0;
    }
    return false;
}

/* fuzzy pickles. thats it thats the comment */
bool save_game(int slot) {''')
    replace('src/intro/file_select.c','if (i != (current_save_slot - 1) && !save_files_present[i]) {','if (i != (current_save_slot - 1) && !save_game_slot_occupied(i)) {')
    replace('src/intro/file_select.c','if (save_files_present[slot]) {','/* Presence is derived from phone data; do not trust builder-only\n             * flags after a fresh-process restore of the selection child. */\n            if (save_game_slot_occupied(slot)) {')
    changed=[]
    for p in (a.candidate/'src').rglob('*'):
        if p.is_file():
            rel=p.relative_to(a.candidate).as_posix()
            if sha(p)!=sha(a.base/rel):changed.append(dict(path=rel,baseSha256=sha(a.base/rel),candidateSha256=sha(p)))
    if sorted(r['path'] for r in changed)!=sorted(edits):raise ValueError('Other source files changed')
    report=dict(format='private-pure-phone-file-select-preparation-dev18-v1',base=str(a.base),candidate=str(a.candidate),changes=changed,exactEdits=edits,toolSha256=sha(Path(__file__)),titleProposalFilesUnchanged=True,format16Unchanged=sha(a.base/'src/core/state_dump.c')==sha(a.candidate/'src/core/state_dump.c'),rootModified=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(report=str(a.output),changes=changed)))

if __name__=='__main__':main()
