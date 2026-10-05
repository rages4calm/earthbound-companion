# SPDX-License-Identifier: GPL-3.0-or-later
# Native format/adaptation work based on MaternalBound Redux and CoilSnake.
# Upstream authors and source links are recorded in CREDITS.md.
"""Build a local-only Redux development pack with checked native entry points.

This is an integration fixture, not a redistributable or supported game profile.
Original ROM assets, Redux dialogue and game tables never leave the local machine.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

from maternalbound_dialogue import BLOB_BASE, ConversionError, without_comments
from maternalbound_graphics import convert_sprites, convert_fonts, convert_windows, convert_battle_art, convert_indexed_graphics
from maternalbound_events import convert_events
from maternalbound_world import convert_world
from maternalbound_encounters import convert_encounters
from maternalbound_presentation import convert_title, convert_special_text, convert_ending
from maternalbound_audio import convert_audio
from maternalbound_psi import convert_psi
from audit_redux_movement import audit as audit_movement

BASE = 0x100000
MAGIC = b"MRDXNV01"


def read_pack(path: Path, ids: Path):
    entries = re.findall(r"^\s+(ASSET_\w+), /\* (.*?) \*/", ids.read_text(), re.M)
    raw = path.read_bytes()
    magic, version, count, layout = struct.unpack_from("<4sII32s", raw)
    wanted = hashlib.sha256("\n".join(x[0] for x in entries).encode()).digest()
    if magic != b"EBPK" or version != 1 or count != len(entries) or layout != wanted:
        raise ConversionError("Donor asset pack does not match native asset registry")
    start = 44 + count * 8
    assets = {}
    for i, (_, name) in enumerate(entries):
        offset, length = struct.unpack_from("<II", raw, 44+i*8)
        if start+offset+length > len(raw):
            raise ConversionError("Truncated donor pack")
        assets[name] = raw[start+offset:start+offset+length]
    return entries, raw[:44], assets


def write_pack(path: Path, entries, header: bytes, assets: dict):
    index = bytearray()
    body = bytearray()
    for _, name in entries:
        body.extend(b"\0" * (-len(body) % 4))
        content = assets[name]
        index.extend(struct.pack("<II", len(body), len(content)))
        body.extend(content)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + index + body)


def convert_game_tables(doc, rom: bytes, assets: dict, relocation: dict, bridge: dict, native: Path):
    native_actions = {int(x,16) for x in re.findall(r"\{ 0x([0-9A-F]+),", (native/"src/game/battle_actions.c").read_text())}
    pointers = {int(key,16):value for key,value in relocation["originalAddresses"].items()}
    pointers.update({int(key,16):value for key,value in relocation["compiledAddresses"].items()})
    converted = []
    relocated = 0
    unresolved = []
    layouts = {"item_configuration_table": (39, (35,)), "enemy_configuration_table": (94, (45,49)),
               "npc_config_table": (17,(9,)), "store_table":(7,()),
               "battle_action_table":(12,(4,)),"psi_ability_table":(15,(11,)),
               "psi_name_table":(25,()),"npc_ai_table":(2,()),
               "consolation_item_table":(9,()),"condiment_table":(7,()),
               "timed_item_transformation_table":(5,())}
    for entry in doc.dumpEntries:
        if entry.name not in layouts:
            continue
        name = f"{entry.subdir}/{entry.name}.{entry.extension}"
        if name not in assets:
            raise ConversionError(f"Game table missing from registry: {name}")
        source = entry.offset
        length = entry.size
        if entry.name == "store_table":
            modules=[x for x in bridge["modules"] if x["name"]=="expand_shops"]
            labels={x["name"]:x["snesAddress"] for x in bridge["labels"] if x["module"]=="expand_shops"}
            if len(modules)!=1 or set(labels)!={"NewShopTable","CustomShops"}:
                raise ConversionError("Missing expanded shop-table exports")
            module=modules[0]
            source=labels["NewShopTable"]-0xC00000;length=module["size"]
            if source!=module["rom_offset"] or labels["CustomShops"]-labels["NewShopTable"]!=66*7 or length!=69*7:
                raise ConversionError("Expanded shop table differs from the pinned 69-shop layout")
            if rom[0x19DF7]!=0xBF or int.from_bytes(rom[0x19DF8:0x19DFB],"little")!=labels["NewShopTable"]:
                raise ConversionError("Shop loader does not reference the exported expanded table")
            if hashlib.sha256(rom[source:source+length]).hexdigest().upper()!=module["compiled_sha256"].upper():
                raise ConversionError("Expanded shop content differs from its linked module")
        if entry.name == "battle_action_table":
            labels = [x for x in bridge["labels"] if x["module"] == "Extended_Battle_Action_Table" and x["name"] == "BattleAction_Table"]
            lucky = [x for x in bridge["labels"] if x["module"] == "lucky_sandwich_revamp" and x["name"] == "Lucky_Sandwich_Action"]
            if len(labels) != 1 or len(lucky) != 1:
                raise ConversionError("Missing expanded battle-action exports")
            source = labels[0]["snesAddress"] - 0xC00000
            length = 320 * 12
        if entry.name == "npc_config_table":
            # CoilSnake ExpandedTablesModule relocates this table and updates
            # a split LDA-immediate pointer in LoadNPCs at C023E5.
            at = 0x23E5
            if rom[at] != 0xA9 or rom[at+5] != 0xA9:
                raise ConversionError("NPC table pointer no longer has its pinned assembly layout")
            source = (int.from_bytes(rom[at+1:at+3],"little") |
                      int.from_bytes(rom[at+6:at+8],"little") << 16)-0xC00000
        if entry.name == "psi_name_table":
            # ExpandedTablesModule frees the original name table and patches
            # GET_PSI_NAME's split immediate pointer. The freed bytes may now
            # contain scripts, so the dump configuration is not its address.
            at = 0x1C423
            code = rom[at:at+10]
            if (len(code) != 10 or code[0] != 0xA9 or code[3] != 0x85 or
                    code[5] != 0xA9 or code[8] != 0x85 or code[9] != code[4]+2):
                raise ConversionError("PSI name loader differs from its pinned pointer layout")
            pointer = int.from_bytes(code[1:3], "little") | int.from_bytes(code[6:8], "little") << 16
            source = pointer-0xC00000 if pointer >= 0xC00000 else pointer
            if source < 0 or source+length > len(rom):
                raise ConversionError("Relocated PSI names exceed the compiled ROM")
        raw = bytearray(rom[source:source+length])
        if entry.name == "psi_name_table":
            for row in range(length//25):
                text = raw[row*25:(row+1)*25].split(b"\0", 1)
                if len(text) != 2 or not text[0] or any(c < 0x50 or c > 0xAE for c in text[0]):
                    raise ConversionError(f"Invalid relocated PSI name {row+1}")
        stride, fields = layouts[entry.name]
        if source < 0 or len(raw) != length or length % stride:
            raise ConversionError(f"Invalid table bounds: {name}")
        if entry.name=="battle_action_table":
            for start in range(0,len(raw),stride):
                function = int.from_bytes(raw[start+8:start+12], "little")
                if start//stride == 318 and function == lucky[0]["snesAddress"]:
                    raw[start+8:start+12] = (0xC2FFF0).to_bytes(4,"little")
                elif start//stride == 319 and function == 0xC2B27D:
                    pass # Existing food handler; description refills stamina.
                elif function not in native_actions:
                    raise ConversionError(f"Battle action {start//stride} needs a native routine adapter: {function:06X}")
        for start in range(0,len(raw),stride):
            active_fields = fields + ((13,) if entry.name == "npc_config_table" and raw[start] == 3 else ())
            for field in active_fields:
                offset = start+field
                pointer = int.from_bytes(raw[offset:offset+4],"little")
                if not pointer:
                    continue
                target = pointers.get(pointer)
                if target is None:
                    unresolved.append({"table":entry.name,"row":start//stride,"field":field,"pointer":f"{pointer:06X}"})
                else:
                    raw[offset:offset+4] = target.to_bytes(4,"little")
                    relocated += 1
        assets[name] = bytes(raw)
        converted.append({"asset":name,"records":len(raw)//stride,"sourceOffset":source})
    if unresolved:
        raise ConversionError(f"Unmapped table script pointers ({len(unresolved)}): " + json.dumps(unresolved[:12]))
    return converted, relocated


def convert_auxiliary_tables(rom,assets,relocation):
    pointers={int(k,16):v for k,v in relocation["originalAddresses"].items()}
    pointers.update({int(k,16):v for k,v in relocation["compiledAddresses"].items()})
    specs=(("attract_mode_txt",0x3FD8D,10,4,((0,4),)),
           ("telephone_contacts_table",0x157A8F,7,31,((27,4),)),
           ("timed_delivery_table",0x15F645,10,20,((10,3),(13,3))),
           ("psi_teleport_dest_table",0x157880,17,31,()),
           ("status_equip_window_text_8_13",0x45C1C,1,107,()),
           ("status_equip_text",0x45B4D,1,195,()))
    converted=[];relocated=0
    for name,offset,count,stride,fields in specs:
        key=f"data/{name}.bin"
        if key not in assets: raise ConversionError(f"Missing auxiliary asset {key}")
        raw=bytearray(rom[offset:offset+count*stride])
        if len(raw)!=count*stride: raise ConversionError(f"Truncated auxiliary table {key}")
        for row in range(count):
            for field,width in fields:
                pos=row*stride+field;value=int.from_bytes(raw[pos:pos+width],"little")
                if not value: continue
                target=pointers.get(value)
                if target is None: raise ConversionError(f"Unmapped {name} text {row}: {value:06X}")
                raw[pos:pos+width]=target.to_bytes(width,"little");relocated+=1
        assets[key]=bytes(raw);converted.append(key)
    return {"assets":converted,"relocatedTextPointers":relocated,
            "telephoneContacts":7,"deliveryEvents":10,"teleportDestinations":17,"attractScenes":10}


def build(args):
    native = args.native_source.resolve()
    sys.path.insert(0, str(native))
    from ebtools.config import load_dump_doc
    doc = load_dump_doc(native/"earthbound.yml")
    bridge = json.loads(args.bridge.read_text())
    report = json.loads((args.converted_directory/"dialogue-report.json").read_text())
    relocation = json.loads((args.converted_directory/"dialogue-relocations.json").read_text())
    text = (args.converted_directory/"dialogue.bin").read_bytes()
    rom = args.compiled_rom.read_bytes()
    sha = lambda data: hashlib.sha256(data).hexdigest().upper()
    if sha(rom) != bridge["roms"]["compiled"]["sha256"] or sha(rom) != report["compiledRomSha256"]:
        raise ConversionError("Compiled ROM differs from source inventory")
    if sha(text) != report["blobSha256"] or sha(text) != relocation["blobSha256"]:
        raise ConversionError("Dialogue content differs from its conversion report")
    for key in ("failedLabelSpans", "unresolvedPointerFields", "ambiguousOriginalAliases"):
        if report["counts"][key]:
            raise ConversionError(f"Cannot build with unresolved conversion: {key}")
    entries, header, assets = read_pack(args.base_assets, native/"src/data/runtime_generated/asset_ids.h")
    definitions = {name:int(addr,16) for name,addr in re.findall(r"#define\s+(MSG_\w+)\s+0x([0-9a-fA-F]+)[uU]?", (native/"src/data/text_refs.h").read_text())}
    original_names = {}
    blocks = {entry.name:entry for entry in doc.dumpEntries}
    for block, labels in doc.renameLabels.items():
        entry = blocks.get(block)
        if entry:
            for offset, name in labels.items():
                original_names[name] = entry.offset+0xC00000+offset
    aliases = {int(key,16):value for key,value in relocation["originalAddresses"].items()}
    mapping = {}
    missing = []
    for name, old in definitions.items():
        original = original_names.get(name)
        target = aliases.get(original)
        if target is not None:
            if old in mapping and mapping[old] != target:
                raise ConversionError(f"Ambiguous native entry {name}")
            mapping[old] = target
        else:
            missing.append(name)
    used = set()
    for folder in (native/"src/game", native/"src/intro", native/"src/entity"):
        for path in folder.rglob("*.c"):
            used.update(set(re.findall(r"\bMSG_\w+\b",without_comments(path.read_text(encoding="utf-8")))) & definitions.keys())
    required_missing = sorted(used & set(missing))
    if required_missing:
        raise ConversionError("Unmapped native game entries: " + ", ".join(required_missing))
    # Reserved native-only entry IDs, outside the legacy text symbol range.
    # Names resolve against the pinned compiler exports, never guessed addresses.
    exports = {}
    for source, module, label in ((0x2FFF00, "keyitems", "Key_Items_Prep"),
                                  (0x2FFF08, "tools", "Tools_Prep_Overworld"),
                                  (0x2FFF10, "battle_text", "Spy_Speed")):
        labels = [x for x in bridge["labels"] if x["module"] == module and x["name"] == label]
        if len(labels) != 1 or source in definitions.values() or source in mapping:
            raise ConversionError(f"Missing or overlapping native export: {module}.{label}")
        target = relocation["compiledAddresses"].get(f'{labels[0]["snesAddress"]:06X}')
        if target is None:
            raise ConversionError(f"Native export was not converted: {module}.{label}")
        mapping[source] = target
        exports[module+"."+label] = {"nativeId":source,"target":target}
    determiner_labels = [x for x in bridge["labels"] if x["module"] == "item_determiners" and x["name"] == "determiner_table"]
    if len(determiner_labels) != 1:
        raise ConversionError("Missing item determiner table")
    offset = determiner_labels[0]["snesAddress"]-0xC00000
    determiners = rom[offset:offset+254]
    if len(determiners) != 254 or any(x < 1 or x > 5 for x in determiners):
        raise ConversionError("Invalid item determiner table")
    dialogue = bytearray(assets["dialogue/dialogue.bin"])
    pad = BLOB_BASE-BASE
    if len(dialogue) > pad:
        raise ConversionError("Donor dialogue overlaps reserved Redux range")
    dialogue.extend(b"\0" * (pad-len(dialogue)))
    dialogue.extend(text)
    dialogue_end = len(dialogue)
    map_offset = len(dialogue)
    legacy_mapping_count=len(mapping)-len(exports)
    # Movement/queued interactions retain typed SNES text-address operands.
    # Bind every compiler-proven text boundary, including rewritten original
    # entries, to the native text blob. These keys are data identifiers only.
    rom_entries={int(key,16):value for key,value in relocation["originalAddresses"].items()}
    rom_entries.update({int(key,16):value for key,value in relocation["compiledAddresses"].items()})
    if any(source<0xC00000 or source>0xFFFFFF or target<BLOB_BASE or target-BASE>=dialogue_end
           for source,target in rom_entries.items()):
        raise ConversionError("ROM-address text mapping exceeds its native dialogue bounds")
    mapping.update(rom_entries)
    for source, target in sorted(mapping.items()):
        dialogue.extend(struct.pack("<II",source,target))
    determiner_offset = len(dialogue)
    dialogue.extend(determiners)
    dialogue.extend(struct.pack("<8s6I",MAGIC,2,map_offset,len(mapping),determiner_offset,len(determiners),dialogue_end))
    assets["dialogue/dialogue.bin"] = bytes(dialogue)
    tables, table_pointers = convert_game_tables(doc,rom,assets,relocation,bridge,native)
    ai_labels = [x for x in bridge["labels"] if x["module"] == "enemy_ai" and x["name"] == "EnemyAiTable"]
    if len(ai_labels) != 1:
        raise ConversionError("Missing enemy AI table export")
    ai_source = ai_labels[0]["snesAddress"]-0xC00000
    enemy_count = len(assets["data/enemy_configuration_table.bin"])//94
    ai_table = bytearray(struct.pack("<8sI", b"MRDXAI01", enemy_count))
    ai_scripts = 0
    for enemy in range(enemy_count):
        at = ai_source+enemy*4
        if at < 0 or at+4 > len(rom):
            raise ConversionError("Truncated enemy AI table")
        pointer = int.from_bytes(rom[at:at+4], "little")
        target = relocation["compiledAddresses"].get(f"{pointer:06X}") if pointer else 0
        if target is None:
            raise ConversionError(f"Unmapped enemy AI entry {enemy}: {pointer:06X}")
        ai_table.extend(struct.pack("<I", target))
        ai_scripts += bool(target)
    assets["data/enemy_configuration_table.bin"] += ai_table
    sprites = convert_sprites(rom,args.project,assets)
    fonts = convert_fonts(rom,assets)
    windows = convert_windows(rom,assets)
    graphics = convert_indexed_graphics(rom,args.project,assets)
    battle_art = convert_battle_art(rom,assets)
    title = convert_title(rom,assets)
    special_text = convert_special_text(rom,bridge,assets)
    ending = convert_ending(rom,args.project,assets)
    audio = convert_audio(rom,assets)
    psi = convert_psi(rom,assets)
    events = convert_events(rom,bridge,assets)
    movement_audit = audit_movement(assets,args.native_source)
    if not movement_audit["Passed"]:
        raise ConversionError("Native movement audit failed: "+"; ".join(movement_audit["Errors"]))
    events["reachableBytecodeAudit"] = {key:value for key,value in movement_audit.items() if key!="Calls"}
    world = convert_world(rom,assets,relocation)
    auxiliary=convert_auxiliary_tables(rom,assets,relocation)
    animation_tables=bytearray(b"MRWALK01")
    for name in ("extra_animation_sprite_table","extra_animation_sprite_table_running1","extra_animation_sprite_table_running2"):
        labels=[x for x in bridge["labels"] if x["module"]=="four_frames_run" and x["name"]==name]
        if len(labels)!=1: raise ConversionError(f"Missing sprite variant export: {name}")
        offset=labels[0]["snesAddress"]-0xC00000
        data=rom[offset:offset+17*8*2]
        if len(data)!=272 or any(x >= 483 and x != 0xFFFF for x in struct.unpack("<136H",data)):
            raise ConversionError(f"Invalid sprite variants: {name}")
        animation_tables.extend(data)
    assets["data/playable_character_graphics_table.bin"] += animation_tables
    encounters = convert_encounters(rom,assets)
    names = [x for x in bridge["labels"] if x["module"] == "dont_care_names" and x["name"] == "dont_care_names"]
    if len(names) != 1: raise ConversionError("Missing expanded naming table")
    names_offset = names[0]["snesAddress"]-0xC00000
    names_data = rom[names_offset:names_offset+7*7*11]
    if len(names_data) != 539 or any(names_data[i*11+10] for i in range(49)):
        raise ConversionError("Invalid expanded naming table")
    assets["US/data/dont_care_names.bin"] = names_data
    write_pack(args.output, entries, header, assets)
    record = {"format":"maternalbound-native-pack-report-v1", "status":"development-only",
        "packSha256":sha(args.output.read_bytes()),"compiledRomSha256":sha(rom),"dialogueSha256":sha(text),
        "legacyEntryMappings":legacy_mapping_count,"romAddressTextMappings":len(rom_entries),"nativeExports":exports,"requiredNativeEntries":len(used),"requiredUnmappedEntries":required_missing,
        "unusedUnmappedEntryCount":len(missing),"dialogueBytes":len(dialogue),
        "convertedAssets":["dialogue/dialogue.bin", "US/data/dont_care_names.bin"]+[x["asset"] for x in tables]+sprites["assets"]+fonts["assets"]+windows["assets"]+graphics["assets"]+battle_art["assets"]+title["assets"]+special_text["assets"]+ending["assets"]+audio["assets"]+psi["assets"]+events["assets"]+world["assets"]+auxiliary["assets"]+encounters["assets"],"convertedTables":tables,
        "sprites":sprites,"fonts":fonts,"windows":windows,"indexedGraphics":graphics,"battleArt":battle_art,"title":title,"specialText":special_text,"ending":ending,"audio":audio,"psiEffects":psi,"events":events,"world":world,"encounters":encounters,
        "auxiliaryTables":auxiliary,"enemyAi":{"records":enemy_count,"scriptedEnemies":ai_scripts,"sourceOffset":ai_source},
        "spriteVariants":{"tables":4,"characters":17,"entries":544},
        "expandedNaming":{"defaultEntries":49,"stride":11,"characterLimit":6,"foodLimit":10},
        "relocatedTablePointers":table_pointers,"remainingIntegration":["Remaining assembly-only QoL and bug fixes", "Later gameplay and cutscene validation", "Individual tool combat effects and complete MSU transitions", "Player-ROM setup for the pinned profile", "Full story and randomized playthrough validation"]}
    args.output.with_suffix(".report.json").write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps(record,indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("base-assets","native-source","bridge","converted-directory","compiled-rom","project","output"):
        parser.add_argument("--"+option,required=True,type=Path)
    build(parser.parse_args())


if __name__ == "__main__":
    main()
