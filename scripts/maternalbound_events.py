# SPDX-License-Identifier: GPL-3.0-or-later
# Native format/adaptation work based on MaternalBound Redux and CoilSnake.
# Upstream authors and source links are recorded in CREDITS.md.
"""Normalize Redux movement-script banks for the native C interpreter.

No 65816 instructions are executed. Custom assembly calls use explicit native
adapters, including the title glow and compiler-private movement helpers.
"""
import hashlib
import struct
from maternalbound_dialogue import ConversionError
from maternalbound_graphics import snes_offset

# Compiler-private routines in the hash-verified movscr_codes module. The
# offsets and byte bodies identify the pinned assembly, never executable PC
# instructions. Native IDs replace typed movement CALLROUTINE operands only.
MOVEMENT_ADAPTERS = (
    (0xCA, 0xBF0100, "distance-from-player", "A6 88 AD 77 98 38 FD 8E 0B 10 04 49 FF FF 1A 85 8C AD 7B 98 38 FD CA 0B 10 04 49 FF FF 1A 18 65 8C 6B", 0),
    (0xEC, 0xBF0101, "result-greater", "B7 80 C8 C8 84 94 DD 16 15 A9 00 00 B0 01 1A 6B", 2),
    (0xFC, 0xBF0102, "ceil-movement-speed", "A6 88 BD 32 2B 3A 09 FF 00 1A EB 29 FF 00 6B", 0),
    (0x10B, 0xBF0103, "maximum-result", "B7 80 C8 C8 84 94 DD 16 15 B0 03 BD 16 15 6B", 2),
    (0x11A, 0xBF0104, "mosaic-fade-in", "B7 80 C8 C8 48 B7 80 C8 C8 AA B7 80 C8 C8 84 94 A8 68 5C CE 87 C0", 6),
    (0x130, 0xBF0105, "refresh-current-frame", "A4 88 B9 F2 10 8D 92 28 5C C4 A4 C0", 0),
)


def convert_events(rom, bridge, assets):
    from ebtools.parsers.original_movement_banks import decode_original_movement_banks
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
    for index in range(788,799):
        pointer = int.from_bytes(table[index*3:index*3+3], "little")
        if pointer != labels[("m2_title_screen_movements", f"Script_{index}")]:
            raise ConversionError(f"Unexpected Redux title movement entry {index}")
    regions = []
    for key, bank, base in (("US/events/bank_c3_scripts_combined.bin", 0xC3, 0),
                            ("US/events/bank_c4_scripts.bin", 0xC4, 0x0E24)):
        content = assets[key]
        if bank == 0xC3:
            original_regions = decode_original_movement_banks(content)
            if original_regions is not None:
                content = original_regions[0]
        size = len(content)
        offset = snes_offset((bank << 16)|base, len(rom))
        regions.append((bank, base, bytes(rom[offset:offset+size])))
    # These original event scripts live outside the large C3/naming banks.
    # Keep fade controllers available even when the intro was skipped.
    regions.append((0xC4,0x2172,bytes(rom[0x42172:0x42972])))
    mini_ghost=bytes(rom[0xAD8A:0xAD9F])
    if mini_ghost!=bytes.fromhex("23 39 A0 25 6B A2 06 08 3B 00 42 A8 A4 C0 F1 8A 77 C0 19 98 AD"):
        raise ConversionError("Mini-ghost movement differs from its pinned native call layout")
    regions.append((0xC0,0xAD8A,mini_ghost))
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
    title_addresses = sorted(value for (module, _), value in labels.items() if module == "m2_title_screen_movements")
    start = title_addresses[0]
    end = min(x["snesAddress"] for x in bridge["labels"] if x["snesAddress"] > title_addresses[-1])
    if start >> 16 != (end-1) >> 16:
        raise ConversionError("Title movement scripts cross a bank boundary")
    content = bytearray(rom[snes_offset(start,len(rom)):snes_offset(end,len(rom))])
    copy_palette_call = b"\x42"+labels[("m2_title_screen_movements","ASM_copy_2_into_high_buffer")].to_bytes(3,"little")
    if content.count(copy_palette_call) != 1:
        raise ConversionError("Expected exactly one title glow palette routine")
    content = content.replace(copy_palette_call,b"\x42\x0D\x00\xBF")
    regions.append((start>>16,start&0xFFFF,bytes(content)))
    # Include task routines in full, including compiler-private labels. The
    # bridge records exact module boundaries and hashes from the linked ROM.
    included_modules=[]
    for name in ("movscr_codes", "moldyman_initial_frame_fix"):
        module=next(x for x in bridge["modules"] if x["name"]==name)
        start=module["snes_address"]; size=module["size"]
        content=bytes(rom[module["rom_offset"]:module["rom_offset"]+size])
        if not size or start>>16 != (start+size-1)>>16:
            raise ConversionError(f"Redux movement module {name} crosses a bank")
        if len(content)!=size or hashlib.sha256(content).hexdigest().upper()!=module["compiled_sha256"].upper():
            raise ConversionError(f"Redux movement module {name} differs from its bridge hash")
        if name=="moldyman_initial_frame_fix":
            target=labels[(name,"Moldyman_Frame_Fix")]
            hook=rom[0x3A6CE:0x3A6D2]
            if hook!=b"\x03"+target.to_bytes(3,"little") or size!=17:
                raise ConversionError("Moldyman movement hook differs from the pinned source")
            if content!=b"\x42\x85\xA6\xC0\x80\x01\x3B\x00\x42\x51\xA6\xC0\x08\x03\xD4\xA6\xC3":
                raise ConversionError("Moldyman movement body differs from its typed native call layout")
        regions.append((start>>16,start&0xFFFF,content))
        included_modules.append({"name":name,"snesAddress":start,"bytes":size,"sha256":module["compiled_sha256"]})
    for index in range(1,899):
        pointer=int.from_bytes(table[index*3:index*3+3],"little")
        if not any((bank<<16)+base<=pointer<(bank<<16)+base+len(data) for bank,base,data in regions):
            raise ConversionError(f"Movement script {index} points outside the included native regions: {pointer:06X}")
    movement_module=next(x for x in bridge["modules"] if x["name"]=="movscr_codes")
    adapters=[]
    for offset,native_id,name,expected,extra in MOVEMENT_ADAPTERS:
        address=movement_module["snes_address"]+offset
        location=movement_module["rom_offset"]+offset
        body=bytes.fromhex(expected)
        if rom[location:location+len(body)]!=body:
            raise ConversionError(f"Private movement helper {name} differs from its pinned assembly")
        old=b"\x42"+address.to_bytes(3,"little")
        new=b"\x42"+native_id.to_bytes(3,"little")
        replacements_count=0
        adapted=[]
        for bank,base,data in regions:
            # These bytecode commands have exact call sites in movement-only
            # regions. Do not replace addresses inside the module's ASM bodies.
            prefix=0x13C if (bank<<16)+base==movement_module["snes_address"] else 0
            code=data[prefix:]
            replacements_count+=code.count(old)
            adapted.append((bank,base,data[:prefix]+code.replace(old,new)))
        regions=adapted
        adapters.append({"name":name,"sourceAddress":address,"nativeId":native_id,"extraBytes":extra,"calls":replacements_count})
    container = bytearray(struct.pack("<8sI",b"MRMVBN01",len(regions)))
    for bank, base, data in regions:
        container.extend(struct.pack("<BBHI",bank,0,base,len(data)))
        container.extend(data)
    replacements = {"US/events/event_script_pointers.bin":bytes(table),
                    "US/events/bank_c3_scripts_combined.bin":bytes(container),
                    "US/intro/title_screen_scripts.bin":bytes(rom[0x42172:0x42172+2048])}
    assets.update(replacements)
    return {"assets":list(replacements),"movementScriptPointers":899,"customScriptIds":[895,896,897,898],
            "resolvedNonzeroMovementPointers":898,
            "regions":[{"bank":bank,"base":base,"bytes":len(data)} for bank,base,data in regions],
            "titleMovementIds":list(range(788,799)),"nativeMovementAdapters":["instant-letterbox","title-glow-palette"],
            "verifiedMovementModules":included_modules,
            "privateMovementAdapters":adapters,
            "deferred":["Full story and cutscene playthrough validation"]}
