# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepare a narrowly reviewed inventory.c QoL candidate in a private directory."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def replace_once(text,old,new):
    if text.count(old)!=1:raise ValueError('Reviewed source boundary changed')
    return text.replace(old,new,1)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True)
    a=ap.parse_args()
    if a.output_dir.exists():raise ValueError('Use a fresh private source directory')
    original=a.source.read_bytes();text=original.decode().replace('\r\n','\n')
    old='''                uint16_t new_pos = find_empty_inventory_slot(target_char_id);
                party_characters[src_idx].equipment[eq] = (uint8_t)new_pos;'''
    new='''                /* Native QoL: the moved item is now the last ordinary bag
                 * entry. FIND_EMPTY_INVENTORY_SLOT preserves an original
                 * off-by-one bound for full bags. Count the actual appended
                 * ordinary entries, including a full fourteen-slot bag. */
                uint16_t new_pos = 0;
                while (new_pos < ITEM_INVENTORY_SIZE &&
                       party_characters[src_idx].items[new_pos] != 0)
                    new_pos++;
                party_characters[src_idx].equipment[eq] = (uint8_t)new_pos;'''
    text=replace_once(text,old,new)
    old='''        for (int eq = 0; eq < EQUIP_COUNT; eq++) {
            uint8_t eq_val = party_characters[src_idx].equipment[eq];
            if (eq_val == item_slot) {
                /* Unequip: set equipment slot to 0 */
                switch (eq) {
                case EQUIP_WEAPON: change_equipped_weapon(source_char_id, 0); break;
                case EQUIP_BODY:   change_equipped_body(source_char_id, 0); break;
                case EQUIP_ARMS:   change_equipped_arms(source_char_id, 0); break;
                case EQUIP_OTHER:  change_equipped_other(source_char_id, 0); break;
                }
                break;
            }
        }'''
    new='''        int removed_equipment = -1;
        for (int eq = 0; eq < EQUIP_COUNT; eq++) {
            uint8_t eq_val = party_characters[src_idx].equipment[eq];
            if (eq_val == item_slot) {
                /* Defer the category's stat recalculation until all remaining
                 * equipment locations refer to the already-compacted bag. */
                party_characters[src_idx].equipment[eq] = 0;
                removed_equipment = eq;
                break;
            }
        }'''
    text=replace_once(text,old,new)
    old='''        /* Adjust remaining equipment indices above removed position */
        for (int eq = 0; eq < EQUIP_COUNT; eq++) {
            uint8_t eq_val = party_characters[src_idx].equipment[eq];
            if (eq_val > item_slot) {
                party_characters[src_idx].equipment[eq] = eq_val - 1;
            }
        }
    }

}'''
    new='''        /* Adjust remaining equipment indices above removed position */
        for (int eq = 0; eq < EQUIP_COUNT; eq++) {
            uint8_t eq_val = party_characters[src_idx].equipment[eq];
            if (eq_val > item_slot) {
                party_characters[src_idx].equipment[eq] = eq_val - 1;
            }
        }
        switch (removed_equipment) {
        case EQUIP_WEAPON: change_equipped_weapon(source_char_id, 0); break;
        case EQUIP_BODY:   change_equipped_body(source_char_id, 0); break;
        case EQUIP_ARMS:   change_equipped_arms(source_char_id, 0); break;
        case EQUIP_OTHER:  change_equipped_other(source_char_id, 0); break;
        default: break;
        }
    }

}'''
    text=replace_once(text,old,new)
    # Normalize input only for text comparison; write candidate UTF-8/LF once.
    target=a.output_dir/'src/game/inventory.c';target.parent.mkdir(parents=True)
    target.write_bytes(text.replace('\r\n','\n').encode())
    meta=dict(schemaVersion=1,sourcePath=str(a.source.resolve()),sourceSha256=hashlib.sha256(original).hexdigest(),
              candidatePath=str(target.resolve()),candidateSha256=sha(target),editedFunction='swap_item_into_equipment',
              intentionalSourceBugCorrection=True,sharedSourceEdited=False,
              preservedGlobalHelper='find_empty_inventory_slot',changes=['Self-Give derives equipped location from actual post-append ordinary bag tail.',
                                                                        'Cross-PC Give delays only the removed equipment category recalculation until other locations compact.'])
    (a.output_dir/'candidate.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta))


if __name__=='__main__':main()
