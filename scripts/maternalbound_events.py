# SPDX-License-Identifier: GPL-3.0-or-later
# Native format/adaptation work based on MaternalBound Redux and CoilSnake.
# Upstream authors and source links are recorded in CREDITS.md.
"""Normalize Redux movement-script banks for the native C interpreter.

No 65816 instructions are executed. Custom assembly calls require explicit
native adapters; the title-screen assembly adapters are still a separate port.
"""
import struct
from maternalbound_dialogue import ConversionError
from maternalbound_graphics import snes_offset


def convert_events(rom, bridge, assets):
    labels = {(x["module"], x["name"]): x["snesAddress"] for x in bridge["labels"]}
    # The compiler does not export underscore-prefixed labels. Read the
    # verified long-indexed LDA operands patched by movement_reloc instead.
    if rom[0x93D5] != 0xBF or rom[0x93DA] != 0xBF:
        raise ConversionError("Movement pointer loader differs from its pinned assembly layout")
    pointer = int.from_bytes(rom[0x93DB:0x93DE],"little")
    if int.from_bytes(rom[0x93D6:0x93D9],"little") != pointer+2:
        raise ConversionError("Movement pointer low/high loads disagree")
    source = snes_offset(pointer, len(rom))
    # ID zero plus 894 original and four custom scripts. Verify every custom
    # pointer against the compiler's exported labels instead of assuming order.
    table = bytearray(rom[source:source+899*3])
    for index, name in enumerate(("StarmanJr_Smoke", "PostWarp_Letterbox", "Jeff_Dup", "Rope_Camera_Pan"), 895):
        value = int.from_bytes(table[index*3:index*3+3], "little")
        if value != labels[("cutscenes", name)]:
            raise ConversionError(f"Movement pointer {index} differs from the pinned Redux source")
    original = assets["US/events/event_script_pointers.bin"]
    # Title movement relies on three additional assembly implementations. Keep
    # this development fixture's title explicit in the conversion report.
    table[788*3:799*3] = original[788*3:799*3]
    regions = []
    for key, bank, base in (("US/events/bank_c3_scripts_combined.bin", 0xC3, 0),
                            ("US/events/bank_c4_scripts.bin", 0xC4, 0x0E24)):
        size = len(assets[key])
        offset = snes_offset((bank << 16)|base, len(rom))
        regions.append((bank, base, bytes(rom[offset:offset+size])))
    cutscene_addresses = sorted(value for (module, _), value in labels.items() if module == "cutscenes")
    start = cutscene_addresses[0]
    end = min(x["snesAddress"] for x in bridge["labels"] if x["snesAddress"] > cutscene_addresses[-1])
    if start >> 16 != (end-1) >> 16:
        raise ConversionError("Custom movement scripts cross a bank boundary")
    content = bytearray(rom[snes_offset(start,len(rom)):snes_offset(end,len(rom))])
    instant_call = b"\x42"+labels[("cc_effects","instantLetterbox")].to_bytes(3,"little")
    if content.count(instant_call) != 1:
        raise ConversionError("Expected exactly one typed instant-letterbox movement call")
    # A reserved native routine ID, independent of compiler placement.
    content = content.replace(instant_call, b"\x42\x0C\x00\xBF")
    regions.append((start>>16, start&0xFFFF, bytes(content)))
    container = bytearray(struct.pack("<8sI",b"MRMVBN01",len(regions)))
    for bank, base, data in regions:
        container.extend(struct.pack("<BBHI",bank,0,base,len(data)))
        container.extend(data)
    replacements = {"US/events/event_script_pointers.bin":bytes(table),
                    "US/events/bank_c3_scripts_combined.bin":bytes(container)}
    assets.update(replacements)
    return {"assets":list(replacements),"movementScriptPointers":899,"customScriptIds":[895,896,897,898],
            "regions":[{"bank":bank,"base":base,"bytes":len(data)} for bank,base,data in regions],
            "deferred":["Redux title movement assembly", "Remaining custom movement routines and relocated dialogue operands"]}
