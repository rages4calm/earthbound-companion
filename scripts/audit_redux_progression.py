"""Bind a conservative native Story Shuffle policy to a verified Redux content pack.

Keeps the converted story, flags, maps, doors, encounter groups, prices, rewards,
item behavior and all protected item sources intact. This is a preservation
audit, not the EarthBound.app randomizer's shuffled-world logic.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct
from build_maternalbound_pack import read_pack


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("assets","pack-report","dialogue-report","original-policy","native-source","output-policy","output-report"):
        p.add_argument("--"+name,required=True,type=Path)
    args=p.parse_args()
    pack=args.assets.read_bytes()
    report=json.loads(args.pack_report.read_text(encoding="utf-8-sig"))
    dialogue=json.loads(args.dialogue_report.read_text(encoding="utf-8-sig"))
    original=json.loads(args.original_policy.read_text(encoding="utf-8-sig"))
    digest=hashlib.sha256(pack).hexdigest()
    if digest.upper()!=report["packSha256"].upper(): raise RuntimeError("Pack differs from its conversion report")
    if dialogue["blobSha256"].upper()!=report["dialogueSha256"].upper(): raise RuntimeError("Dialogue differs from pack report")
    counts=dialogue["counts"]
    for field in ("failedLabelSpans","unresolvedPointerFields","ambiguousOriginalAliases"):
        if counts[field]: raise RuntimeError(f"Unaudited dialogue: {field}")
    _,_,assets=read_pack(args.assets,args.native_source/"src/data/runtime_generated/asset_ids.h")
    items=assets["data/item_configuration_table.bin"]
    enemies=assets["data/enemy_configuration_table.bin"]
    shops=assets["data/store_table.bin"]
    enemy_size=231*94
    if len(items)!=254*39 or len(enemies)!=enemy_size+12+231*4 or len(shops)!=69*7: raise RuntimeError("Unexpected Redux table layout")
    if enemies[enemy_size:enemy_size+8]!=b"MRDXAI01" or struct.unpack_from("<I",enemies,enemy_size+8)[0]!=231:
        raise RuntimeError("Invalid Redux enemy-AI extension")
    item_reasons=defaultdict(set);enemy_reasons=defaultdict(set)
    # Retain the original story's conservative dynamic-argument protections,
    # then add dependencies from the rewritten story and its new menus.
    for item in original["ProtectedItems"]: item_reasons[item].add("Conservative original-story dependency")
    for enemy in original["ProtectedEnemies"]: enemy_reasons[enemy].add("Conservative original scripted-battle dependency")
    dependencies=dialogue["progressionDependencies"]
    for entry in dependencies["items"]:
        if not 0<entry["id"]<254: raise RuntimeError("Invalid literal item dependency")
        item_reasons[entry["id"]].update(entry["reasons"])
    # Key items, transformations and quest helpers cannot enter replacement
    # pools even if a source script passes their IDs through registers.
    for item in range(1,254):
        if items[item*39+25]&0x3C==0x38: item_reasons[item].add("Key-item category")
    transformations=assets["data/timed_item_transformation_table.bin"]
    if len(transformations)%5: raise RuntimeError("Invalid transformation records")
    for offset in range(0,len(transformations),5):
        for field in (0,3):
            item=transformations[offset+field]
            if item: item_reasons[item].add("Timed transformation source or result")
    for item in (0x11,0x1B,0x5A,0x5D,0x5F,0x7F,0x8C,0xA6,0xB8,0xBE,0xE0):
        item_reasons[item].add("Early weapon, Casey bat exclusion or dynamic Monkey Cave request")
    pointers=assets["data/btl_entry_ptr_table.bin"]
    groups=assets["data/enemy_battle_groups_table.bin"]
    for entry in dependencies["scriptedBattleGroups"]:
        group=entry["id"]
        if group*8+8>len(pointers): raise RuntimeError(f"Invalid scripted group {group}")
        # Encounter converter normalizes these to the native table base.
        offset=struct.unpack_from("<I",pointers,group*8)[0]-0xD0D52D
        while True:
            if not 0<=offset<len(groups): raise RuntimeError(f"Invalid group pointer {group}")
            if groups[offset]==0xFF: break
            if offset+3>len(groups): raise RuntimeError("Truncated group")
            enemy=struct.unpack_from("<H",groups,offset+1)[0]
            if not 0<enemy<231: raise RuntimeError("Invalid scripted enemy")
            enemy_reasons[enemy].add(f"Redux scripted battle {group}: "+", ".join(entry["modules"]))
            offset+=3
    for enemy in range(1,231):
        if enemies[enemy*94+86]: enemy_reasons[enemy].add("Boss/death-sound flag")
    state_source=(args.native_source/"src/core/state_dump.c").read_text(encoding="utf-8")
    version=int(re.search(r"#define STATE_DUMP_VERSION (\d+)",state_source)[1])
    crc=int(re.search(r"crc = \(crc >> 1\) \^ \((0x[0-9A-F]+)u",state_source)[1],16)
    policy={"ContentId":"maternalbound-redux-897d0083","DisplayName":"MaternalBound Redux (native development)",
            "BaseHash":digest,"ProtectedItems":sorted(item_reasons),"ProtectedEnemies":sorted(enemy_reasons),
            "SaveStateVersion":version,"SaveStateCrcPolynomial":crc}
    audit={**policy,"CompiledRomSha256":report["compiledRomSha256"],"DialogueSha256":dialogue["blobSha256"],
           "ConvertedSpans":counts["convertedLabelSpans"],"DecodedOperations":dependencies["decodedOperations"],
           "LiteralScriptedGroups":len(dependencies["scriptedBattleGroups"]),"ShopRows":69,
           "Items":[{"Id":item,"Reasons":sorted(reasons)} for item,reasons in sorted(item_reasons.items())],
           "Enemies":[{"Id":enemy,"Reasons":sorted(reasons)} for enemy,reasons in sorted(enemy_reasons.items())],
           "Status":"Development content-specific preservation policy; generator validation pending",
           "Limits":["No new item order or world topology is generated.","No full randomized playthrough verified.",
                     "Pinned source revision only; a changed content pack requires a new audit."]}
    for path,data in ((args.output_policy,policy),(args.output_report,audit)):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"items":len(item_reasons),"enemies":len(enemy_reasons),"operations":dependencies["decodedOperations"],
                      "scriptedGroups":audit["LiteralScriptedGroups"],"packSha256":digest},indent=2))


if __name__=="__main__": main()
