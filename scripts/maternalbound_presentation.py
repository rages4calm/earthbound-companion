# SPDX-License-Identifier: GPL-3.0-or-later
# Format adaptation based on CoilSnake's TitleScreenModule and Redux's title
# movements (Catador, Vittorio and contributors); see CREDITS.md.
"""Convert relocated Redux presentation data for the native renderer."""
import struct
import yaml
from maternalbound_dialogue import ConversionError
from maternalbound_graphics import asm_pointer, slice_rom, snes_offset


def convert_title(rom, assets):
    from ebtools.hallz import get_compressed_data, decompress
    families = (
        ("US/intro/title_screen.gfx.lzhal", 0xEBF2, 45056),
        ("US/intro/title_screen.arr.lzhal", 0xEC1D, 2048),
        ("US/intro/title_screen.pal.lzhal", 0xECC6, 512),
        ("US/intro/title_screen_letters.gfx.lzhal", 0xEC49, 32768),
        ("US/E1AE7C.bin.lzhal", 0x3F492, 32),
        ("US/E1AE83.bin.lzhal", 0xEC83, 448),
        ("US/E1AEFD.bin.lzhal", 0xEC9D, 640),
    )
    converted = []; dimensions = {}
    for key, instruction, expected in families:
        if key not in assets: raise ConversionError(f"Missing title asset: {key}")
        pointer = asm_pointer(rom, instruction)
        offset = snes_offset(pointer, len(rom))
        content = get_compressed_data(memoryview(rom)[offset:offset+65536])
        raw = decompress(content)
        if len(raw) != expected:
            raise ConversionError(f"Unexpected title layout {key}: {len(raw)} != {expected}")
        # The native title OBJ region has 512 tiles. CoilSnake stores 1024;
        # its unused upper tiles must be empty before that region is cropped.
        if "letters.gfx" in key and any(raw[16384:]):
            raise ConversionError("Title letters exceed the native OBJ VRAM region")
        assets[key] = bytes(content); converted.append(key); dimensions[key] = len(raw)
    if asm_pointer(rom, 0xED6B) != asm_pointer(rom, 0xECC6):
        raise ConversionError("Quick and normal title palette pointers disagree")
    if rom[0xA0FE] != 0xA9:
        raise ConversionError("Title sprite-layout bank loader changed")
    bank = rom[0xA0FF]
    maps = bytearray(); pointers = bytearray(); counts = []
    for index in range(9):
        pointer = struct.unpack_from("<H", rom, 0x21CF9D+index*2)[0]
        data = bytearray()
        for entry in range(9):
            row = slice_rom(rom, (bank<<16)+pointer+entry*5, 5)
            tile = struct.unpack_from("<H", row, 1)[0] & 1023
            if tile >= 512: raise ConversionError("Title spritemap uses an inaccessible OBJ tile")
            data.extend(row)
            if row[4] & 0x80: break
        else: raise ConversionError("Title spritemap exceeds nine native layout entries")
        pointers.extend(struct.pack("<H", 0xCE08+len(maps)))
        counts.append(len(data)//5)
        maps.extend(data); maps.extend(bytes(45-len(data)))
    key = "US/intro/title_screen_spritemaps.bin"
    assets[key] = bytes(maps+pointers); converted.append(key)
    return {"assets":converted,"decompressedBytes":dimensions,"letterLayouts":9,
            "layoutEntryCounts":counts,"relocatedLayoutBank":bank}


def convert_ending(rom, project, assets):
    """Follow CoilSnake CastModule/FontModule pointers; normalize dynamic names."""
    from ebtools.hallz import get_compressed_data, decompress
    converted=[]; dimensions={}
    compressed=(
        ("US/E1D6E1.gfx.lzhal",0x4E42E,True,1024),
        ("US/ending/cast_names.gfx.lzhal",0x4E446,True,10752),
        ("US/ending/cast_names.pal.lzhal",0x21E4E6,False,256),
        ("US/ending/credits_font.gfx.lzhal",0x4F1A7,True,3072),
        ("ending/E1E94A.bin.lzhal",0x21E94A,False,2304),
    )
    for key,at,relocated,expected in compressed:
        offset=snes_offset(asm_pointer(rom,at),len(rom)) if relocated else at
        content=bytes(get_compressed_data(memoryview(rom)[offset:offset+65536]))
        if key not in assets or len(decompress(content))!=expected:
            raise ConversionError(f"Invalid Redux ending graphic: {key}")
        assets[key]=content; converted.append(key); dimensions[key]=expected
    fixed=(
        ("US/ending/cast_sequence_formatting.bin",0x212EFA,144),
        ("ending/photographer_cfg.bin",0x212F8A,1984),
        ("ending/party_cast_tile_ids.bin",0x3FDB5,8),
        ("US/ending/cast_bg_palette.pal",0x21D815,32),
        ("ending/E1E924.bin",0x21E924,38),
        ("ending/credits_font.pal",0x21E914,16),
        ("sprite_group_palettes.pal",0x30000,256),
    )
    for key,offset,count in fixed:
        if key not in assets: raise ConversionError(f"Missing ending asset: {key}")
        assets[key]=slice_rom(rom,0xC00000+offset,count);converted.append(key)
    formatting=assets["US/ending/cast_sequence_formatting.bin"]
    for offset in (36,39,108):
        start,width=struct.unpack_from("<HB",formatting,offset)
        if not (1<=width<=26 and start<1024):
            raise ConversionError("Dynamic cast name exceeds native VWF capacity")
    names=yaml.safe_load((project/"Cast/dynamic_names.yml").read_text(encoding="utf-8"))
    blob=bytearray(b"MRCAST01")
    for name,character,instruction,custom in (("Paula's dad",1,0x4E915,0x4E8C7),
        ("Paula's mom",1,0x4E9B7,0x4E980),("Poo's master",3,0x4EA60,0x4EA22)):
        mode=names[name]["mode"]; text=names[name]["text"]
        if mode not in ("none","prefix","suffix") or len(text)>11 or any(not 32<=ord(x)<=126 for x in text):
            raise ConversionError(f"Invalid dynamic cast name: {name}")
        encoded=bytes(ord(x)+0x30 for x in text)+b"\0"
        at=custom+8 if mode=="prefix" else instruction
        pointer=asm_pointer(rom,at)
        if slice_rom(rom,pointer,len(encoded))!=encoded:
            raise ConversionError(f"Compiled dynamic cast name disagrees with project: {name}")
        blob.extend(struct.pack("<4B12s",("none","prefix","suffix").index(mode),character,len(text),0,encoded))
    key="US/ending/guardian_text.bin";assets[key]=bytes(blob);converted.append(key)
    return {"assets":converted,"decompressedBytes":dimensions,"dynamicNames":3,
            "validationBoundary":"Native cast and credits playback still require verification"}


def convert_special_text(rom, bridge, assets):
    labels = {(x["module"],x["name"]): x["snesAddress"] for x in bridge["labels"]}
    entries = [("flyover_texts",f"l_0x{address:06x}",f"US/{name}.bin") for address,name in (
        (0xE10B86,"flyover_intro1"),(0xE10B9C,"flyover_intro2"),(0xE10BC2,"flyover_intro3"),
        (0xE10BD2,"flyover_winters_intro1"),(0xE10BFD,"flyover_winters_intro2"),
        (0xE10C1B,"flyover_dalaam_intro1"),(0xE10C38,"flyover_dalaam_intro2"),(0xE10C61,"flyover_ending"))]
    entries += [("coffee_tea_sequences","l_0xe10000","US/coffee.bin"),
                ("coffee_tea_sequences","l_0xe10652","US/tea.bin")]
    converted = []; lengths = {}; commands = 0
    for module,label,key in entries:
        if (module,label) not in labels or key not in assets:
            raise ConversionError(f"Missing specialized text: {module}.{label}")
        start = snes_offset(labels[(module,label)],len(rom)); offset = start
        for _ in range(16384):
            if offset >= len(rom): raise ConversionError(f"Truncated flyover: {key}")
            op = rom[offset]; offset += 1
            if not op: break
            if op in (1,2,8):
                if offset >= len(rom): raise ConversionError(f"Truncated flyover operand: {key}")
                if op == 8 and not 1 <= rom[offset] <= 4:
                    raise ConversionError(f"Invalid party name in {key}")
                offset += 1; commands += 1
            elif op == 9: commands += 1
            elif op < 0x20 or op >= 0xD0:
                raise ConversionError(f"Unknown specialized text opcode {op:02X}: {key}")
        else: raise ConversionError(f"Unterminated flyover: {key}")
        assets[key] = bytes(rom[start:offset]); converted.append(key); lengths[key] = offset-start
    start = snes_offset(labels[("staff_text","l_0xe1413f")],len(rom)); offset = start
    rows = 0
    for _ in range(1000):
        if offset >= len(rom): raise ConversionError("Truncated staff text")
        op = rom[offset]; offset += 1
        if op == 255: break
        if op in (1,2):
            length = 0
            while offset < len(rom) and rom[offset]:
                offset += 1; length += 1
                if length > 32: raise ConversionError("Staff row exceeds native tilemap width")
            if offset >= len(rom): raise ConversionError("Unterminated staff row")
            offset += 1; rows += 1
        elif op == 3:
            if offset >= len(rom): raise ConversionError("Truncated staff spacing")
            offset += 1
        elif op != 4: raise ConversionError(f"Unknown staff opcode {op:02X}")
    else: raise ConversionError("Unterminated staff text")
    key = "US/ending/staff_text.bin"
    if key not in assets: raise ConversionError("Missing native staff asset")
    assets[key] = bytes(rom[start:offset]); converted.append(key); lengths[key] = offset-start
    return {"assets":converted,"scriptBytes":lengths,"flyoverControls":commands,"staffRows":rows,
            "validationBoundary":"Specialized binary formats validated; cutscene and ending runtime still required"}
