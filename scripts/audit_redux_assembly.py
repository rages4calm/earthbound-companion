# SPDX-License-Identifier: GPL-3.0-or-later
"""Account for dialogue-excluded Redux spans against explicit native work.

This ledger checks source identity and references. Classification and symbol
presence are not semantic equivalence or a completed gameplay playthrough.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

# Review decisions for the pinned source. Never silently classify a new module.
COVERAGE = {
 "ShopSys": ("native-command", "32-bit register comparison replaces the assembly helper.", [("src/game/maternalbound.c","maternalbound_registers_equal")]),
 "goods_menu_equip": ("native-command", "Register comparison and typed unequip adapter; selected categories checked by native equipment tests.", [("src/game/display_text_cc.c","case 17:"),("src/game/inventory.c","maternalbound_equipment_selftest")]),
 "data_19": ("native-timed-hook", "Delivery routine opens the 14-frame letterbox before music and dismount; modal continuation uses saved scalar state.", [("src/entity/script.c","AS_CHILD_DELIVERY_LETTERBOX"),("src/entity/callroutine.c","actionscript_request_delivery_letterbox")]),
 "data_24": ("native-adapter", "Three HP box modes use stable native adapter IDs 6, 7 and 8.", [("src/game/display_text_cc.c","case 6: case 7: case 8:")]),
 "item_determiners": ("native-command-and-data", "Determiner operands use the checked 254-byte converted table, not SNES assembly.", [("src/game/maternalbound.c","maternalbound_item_determiner")]),
 "keyitems": ("native-menu", "Native pause-menu continuation closes converted windows after the Key Items script.", [("src/game/text.c","case PM_KEY_ITEMS_RESUME:")]),
 "tools": ("native-menu", "Native pause and battle menus implement appearance, closing, targeting and eleven flag devices.", [("src/game/text.c","MATERNALBOUND_ENTRY_TOOLS"),("src/game/battle.c","redux_battle_tools")]),
 "new_stats_equipment": ("native-menu", "C equipment previews and stat/resistance display replace this entire assembly routine family; 340 item/character previews checked.", [("src/game/text.c","display_redux_equipment_stats"),("src/game/inventory.c","maternalbound_equipment_selftest")]),
 "window_titles": ("native-command", "Typed title commands, character affixes and remapped native window IDs replace assembly rendering calls.", [("src/game/display_text_cc.c","maternalbound_script_window"),("src/game/display_text.c","maternalbound_title_content_selftest")]),
 "psi_battle_anims": ("native-adapter", "Stable adapter 9 reads the production battle-mode flag.", [("src/game/display_text_cc.c","case 9: result = bt.battle_mode_flag;")]),
 "coffee_tea_sequences": ("separate-format-converter", "Coffee and tea use the checked presentation converter and actual native scene replays.", [("src/game/flyover.c","FO_COFFEETEA")] ),
 "flyover_texts": ("separate-format-converter", "Eight narrated scenes use the presentation converter and native narration interpreter.", [("src/game/flyover.c","FO_SCRIPT")] ),
 "staff_text": ("separate-format-converter", "Credits use their own data/font conversion, ending interpreter and 32 photo-branch fixture.", [("src/game/ending.c","maternalbound_enabled")]),
 "debug_menu_enabler": ("developer-parity-unverified", "Pinned DEBUG_BUILD is zero. Boot/debug-only assembly is not claimed implemented wholesale; debug dialogue conversion does not imply boot-menu parity.", []),
 "diamond": ("developer-parity-unverified", "Developer dialogue uses native window/text operations. Original debugger helper assembly is not claimed implemented wholesale.", []),
 "psi_anims": ("developer-parity-unverified", "Debug-only group 422 fast-exit hook is not normal story PSI behavior. Native PSI animation validation is separate.", []),
}


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ("bridge","dialogue-report","project","native-source","output"):
  p.add_argument("--"+name,type=Path,required=True)
 a=p.parse_args();bridge=json.loads(a.bridge.read_text(encoding="utf-8-sig"));dialogue=json.loads(a.dialogue_report.read_text(encoding="utf-8-sig"))
 sources=[];patch_sites=[]
 for record in bridge["sourceGraph"]["files"]:
  path=a.project/record["path"];data=path.read_bytes();expected=record["sha256"].lower()
  if hashlib.sha256(data).hexdigest()!=expected:
   normalized=data.replace(b"\r\n",b"\n")
   if hashlib.sha256(normalized).hexdigest()!=expected:
    normalized=normalized.replace(b"\n",b"\r\n")
   if hashlib.sha256(normalized).hexdigest()!=expected: raise RuntimeError("Source identity mismatch: "+record["path"])
  source=data.decode("utf-8-sig")
  clean=re.sub(r"/\*.*?\*/|//[^\n]*", "",source,flags=re.S)
  sites=re.findall(r"^\s*ROM\[([^]\n]+)\]",clean,re.M)
  sources.append({"path":record["path"],"sha256":record["sha256"],"syntacticRomWriteSites":len(sites)})
  for site in sites: patch_sites.append({"source":record["path"],"expression":site.strip()})
 rows=[]
 for excluded in dialogue["excluded"]:
  name=excluded["module"]
  if name not in COVERAGE: raise RuntimeError("Unreviewed excluded module: "+name)
  kind,note,bindings=COVERAGE[name];refs=[]
  for relative,needle in bindings:
   source=(a.native_source/relative).read_text(encoding="utf-8")
   at=source.find(needle)
   if at<0: raise RuntimeError("Native reference missing: "+relative+": "+needle)
   refs.append({"path":relative,"line":source[:at].count("\n")+1,"symbolOrAnchor":needle})
  rows.append({**excluded,"nativeClassification":kind,"reviewDecision":note,"nativeReferences":refs})
 debug=(a.project/"ccscript/debug/debug_menu_enabler.ccs").read_text(encoding="utf-8-sig")
 if not re.search(r"^define DEBUG_BUILD = 0\s*$",debug,re.M): raise RuntimeError("Pinned debug activation changed")
 record={"format":"redux-excluded-span-ledger-v1","status":"structural-accounting-not-full-compatibility",
  "compiledRomSha256":dialogue["compiledRomSha256"],"convertedDialogueSha256":dialogue["blobSha256"],
  "reachableSourceFilesChecked":len(sources),"excludedSpansAccounted":len(rows),
  "classificationCounts":dict(Counter(row["nativeClassification"] for row in rows)),
  "unclassifiedExcludedSpans":[],"excludedSpanLedger":rows,"sourceInventory":sources,"syntacticRomWriteSites":patch_sites,
  "limitations":["ROM write sites are syntax inventory, including definitions; counts do not prove instantiated patch coverage.",
   "Symbol references validate the review map, not every branch of each native implementation.",
   "Developer/debug parity, complete ROM-patch semantics and full story/randomized playthroughs remain unverified."]}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"sourceFiles":len(sources),"excludedSpansAccounted":len(rows),"unclassified":0,"completeCompatibilityVerified":False}))

if __name__=="__main__":main()
