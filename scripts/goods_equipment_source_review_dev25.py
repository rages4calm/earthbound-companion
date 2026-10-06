# SPDX-License-Identifier: GPL-3.0-or-later
"""Independent selected Original ROM and active Redux equipment contracts."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
import maternalbound_dialogue as dialogue
from build_maternalbound_pack import read_pack
from overworld_use_source_review_dev24 import bounded_yaml

ITEMS = [17,18,28,35,36,49,56,58,63,64,70,73,74,78,81,87,90,91]
FLAGS = {'ness can use':1,'paula can use':2,'jeff can use':4,'poo can use':8,
         'item can be transformed':16,'cannot be given away':32,'cannot be dropped':64,'item disappears when used':128}


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ordered(text,tokens):
    pos=0
    for token in tokens:
        found=text.find(token,pos)
        if found<0:return False
        pos=found+len(token)
    return True


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('native-source','project','original-assets','redux-assets','rom','output'):ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args();checks=[];references=[];spans=[];rom=a.rom.read_bytes()
    _,_,original=read_pack(a.original_assets,a.native_source/'src/data/runtime_generated/asset_ids.h')
    _,_,redux=read_pack(a.redux_assets,a.native_source/'src/data/runtime_generated/asset_ids.h')
    check=lambda id,passed:checks.append(dict(id=id,passed=bool(passed)))
    text=(a.native_source/'earthbound.yml').read_text();m=re.search(r"name: 'item_configuration_table'\s+offset: (0x[\dA-F]+)\s+size: (\d+)",text,re.I)
    offset,size=int(m[1],16),int(m[2]);raw=rom[offset:offset+size]
    spans.append(dict(table='item_configuration_table',offset=offset,size=size,rawSha256=hashlib.sha256(raw).hexdigest()))
    for item in ITEMS:
        src=raw[item*39:(item+1)*39];pack=original['data/item_configuration_table.bin'][item*39:(item+1)*39]
        check('original-selected-item-'+str(item)+'-numeric',src[25:35]==pack[25:35])
        src=bounded_yaml(a.project/'item_configuration_table.yml',item);pack=redux['data/item_configuration_table.bin'][item*39:(item+1)*39]
        check('redux-selected-item-'+str(item)+'-type-price-flags',pack[25]==src['Type']and struct.unpack_from('<H',pack,26)[0]==src['Cost']and not(set(src['Misc Flags'])-set(FLAGS))and pack[28]==sum(FLAGS[x]for x in src['Misc Flags']))
        check('redux-selected-item-'+str(item)+'-signed-parameters',list(pack[31:35])==src['Argument'])
    flows={
        'asm/inventory/equipment/equipment_change_menu.asm':[
            ('menu-filters-type-category-and-user',['JSR GET_ITEM_TYPE','CMP #2','JSL GET_ITEM_SUBTYPE','CMP @LOCAL05','JSL CHECK_ITEM_USABLE_BY']),
            ('none-clear-and-real-equip',['CPX #.LOWORD(-1)','@UNEQUIP_WEAPON:','JSL CHANGE_EQUIPPED_WEAPON','@UNEQUIP_BODY:','JSL CHANGE_EQUIPPED_BODY','@UNEQUIP_ARMS:','JSL CHANGE_EQUIPPED_ARMS','@UNEQUIP_OTHER:','JSL CHANGE_EQUIPPED_OTHER','@EQUIP_SELECTED:','CPX #0','JSR EQUIP_ITEM'])],
        'asm/battle/swap_item_into_equipment.asm':[
            ('self-give-equipment-empty-location',['BNEL @DIFFERENT_CHARACTER','EQUIPMENT_SLOT::WEAPON','JSL FIND_EMPTY_INVENTORY_SLOT','STA (@LOCAL01)']),
            ('source-give-recalculates-before-index-adjustment',['@AFTER_COMPACT:','JSL GIVE_ITEM_TO_CHARACTER','@DIFFERENT_CHARACTER:','JSL CHANGE_EQUIPPED_WEAPON','JSL CHANGE_EQUIPPED_BODY','JSL CHANGE_EQUIPPED_ARMS','JSL CHANGE_EQUIPPED_OTHER','@AFTER_EQUIP_CHANGE:','@AFTER_ADJUST_BODY_POST:'])],
        'asm/battle/find_empty_inventory_slot.asm':[
            ('source-full-bag-thirteen-bound',['@LOOP_TEST:','LDA #14','CLC','SBC @VIRTUAL02','BRANCHLTEQS @DONE','@DONE:','LDA @LOCAL00'])],
        'asm/misc/change_equipped_weapon.asm':[
            ('weapon-commit-recalculates',['STA __BSS_START__,X','JSL RECALC_CHARACTER_POSTMATH_OFFENSE','JSL RECALC_CHARACTER_POSTMATH_GUTS','JSL RECALC_CHARACTER_MISS_RATE'])],
        'asm/misc/change_equipped_body.asm':[
            ('body-commit-recalculates',['JSL RECALC_CHARACTER_POSTMATH_DEFENSE','JSL RECALC_CHARACTER_POSTMATH_SPEED','JSL CALC_RESISTANCES'])],
        'asm/misc/change_equipped_arms.asm':[
            ('arms-commit-recalculates',['JSL RECALC_CHARACTER_POSTMATH_DEFENSE','JSL RECALC_CHARACTER_POSTMATH_LUCK','JSL CALC_RESISTANCES'])],
        'asm/misc/change_equipped_other.asm':[
            ('other-commit-recalculates',['JSL RECALC_CHARACTER_POSTMATH_DEFENSE','JSL RECALC_CHARACTER_POSTMATH_LUCK','JSL CALC_RESISTANCES'])],
        'asm/misc/recalc_character_postmath_offense.asm':[
            ('poo-alternate-weapon-modifier',['CMP #PARTY_MEMBER::POO - 1','LDX #1','item_parameters::strength'])],
        'asm/misc/recalc_character_postmath_defense.asm':[
            ('poo-alternate-defense-modifier',['CMP #PARTY_MEMBER::POO - 1','LDA #1','item_parameters::strength'])],
        'asm/battle/recalc_character_miss_rate.asm':[
            ('weapon-special-is-missrate',['EQUIPMENT_SLOT::WEAPON','item_parameters::special','char_struct::miss_rate'])],
        'asm/text/ccs/get_item_sell_price.asm':[
            ('drop-half-cost-protection',['item::cost','LSR','JSR SET_WORKING_MEMORY'])],
        'ccscript/redux/goods_menu_equip.ccs':[
            ('active-use-hijack',['ROM[0xC7C742] = goto(newUse)','newUse:','can_equip_item_at_location(0,0)','goto_if_false(_cant_equip)','item_at_location_is_equipped(0,0)','goto_if_true(_unequip)','set(UsingEquipmentCheckFlag)']),
            ('unequip-item-not-consumed',['_unequip:','load_registers','unequip(0,0)','sound(SND_UNKNOWN)']),
            ('all-unequip-categories',['_weapon:','JSL\t(CHANGE_EQUIPPED_WEAPON)','_body:','JSL\t(CHANGE_EQUIPPED_BODY)','_arms:','JSL\t(CHANGE_EQUIPPED_ARMS)','_other:','JSL\t(CHANGE_EQUIPPED_OTHER)'])],
        'ccscript/redux/new_stats_equipment.ccs':[
            ('source-closes-gameplay-window',['ROM[0xC1AA68] = JSL (Equip_Routine_Edit1)','Equip_Routine_Edit1:','LDA_i (1)','JSL (0xC3E521)']),
            ('source-exit-reopen-is-commented',['Close_Equipment_Window:','JSL (Open_Money_Window)','JSL (0xC1DD3B)','//JSL (0xC134A7)'])]
    }
    for path,contracts in flows.items():
        base=a.project if path.startswith('ccscript/')else a.native_source
        text=(base/path).read_text();references.append(dict(path=path,sha256=sha(base/path)))
        for id,tokens in contracts:check('source-flow-'+id,ordered(text,tokens))
    main=(a.project/'ccscript/main.ccs').read_text()
    check('pinned-main-active-goods-equip','import "redux/goods_menu_equip.ccs"'in main)
    check('pinned-main-active-expanded-equipment','import "redux/new_stats_equipment.ccs"'in main)
    doc,specs,expansions=dialogue.load_native(a.native_source);specs[(0x1C,0x11)]=('zero_width_space',())
    for start,end,label in [(0xC7C742,0xC7C761,'equipment-use-informational'),(0xC7C609,0xC7C655,'drop-caller')]:
        d=dialogue.relocate_bytes(rom[start-0xC00000:end-0xC00000],specs,expansions)
        spans.append(dict(label=label,start=start,endExclusive=end,rawSha256=hashlib.sha256(rom[start-0xC00000:end-0xC00000]).hexdigest(),opcodeCounts=dict(d.opcodes)))
        if label=='equipment-use-informational':
            check('original-Goods-Use-equipment-no-mutation',d.operations==[('add_item_id_to_work_memory',[0,0]),('print_item_name',[0]),('halt_without_prompt',[]),('end_block',[])])
        else:
            operations=[op[0]for op in d.operations]
            check('original-Drop-guard-before-take',operations.index('get_sell_price_of_item')<operations.index('jump_if_false')<operations.index('take_item_from_character_2'))
            check('original-Drop-bubblegum-guard',('test_if_workmem_true',[104])in d.operations)
    result=dict(schemaVersion=1,toolVersion='dev25-selected-goods-equipment-source',toolSha256=sha(__file__),
                pinnedReduxCommit='897d00833f4a08a0a92f106abf631629a6a6a041',ownerRomSha256=sha(a.rom),nativeSnapshot=str(a.native_source),
                originalPackSha256=sha(a.original_assets),reduxPackSha256=sha(a.redux_assets),sourceReferences=references,
                pinnedTables=[dict(path=p,sha256=sha(a.project/p))for p in ('ccscript/main.ccs','item_configuration_table.yml')],
                originalSpans=spans,checks=checks,allPassed=all(c['passed']for c in checks),
                limits=['Selected original ROM numeric item rows and locally parsed original dialogue control opcodes; pinned source numeric rows and ordered assembly tokens. No original SNES CPU execution, ROM/dialogue payload or complete source-branch proof.',
                        'The full-bag self-Give equipment-location oddity is source-consistent and recorded separately; selected parent/native tests do not establish all item IDs, stat boundary values or natural reachability.'])
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(checks=len(checks),failed=[c for c in checks if not c['passed']])))
    if not result['allPassed']:raise SystemExit(1)


if __name__=='__main__':main()
