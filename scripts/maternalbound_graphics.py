# SPDX-License-Identifier: GPL-3.0-or-later
# Native format/adaptation work based on MaternalBound Redux and CoilSnake.
# Upstream authors and source links are recorded in CREDITS.md.
"""Normalize relocated Redux sprite groups and fonts into native asset families."""
from __future__ import annotations
from pathlib import Path
import re
import struct
import yaml
from maternalbound_dialogue import ConversionError


def snes_offset(address: int, size: int) -> int:
    offset = address-0xC00000 if address >= 0xC00000 else address
    if address < 0x400000 or offset < 0 or offset >= size:
        raise ConversionError(f"Invalid HiROM/ExHiROM data address {address:06X}")
    return offset


def slice_rom(rom: bytes, address: int, size: int) -> bytes:
    offset = snes_offset(address,len(rom))
    data = rom[offset:offset+size]
    if len(data) != size:
        raise ConversionError(f"Truncated data at {address:06X}")
    return data


def asm_pointer(rom: bytes, at: int) -> int:
    if rom[at] != 0xA9 or rom[at+5] != 0xA9:
        raise ConversionError(f"Relocated pointer at C{at:05X} changed assembly layout")
    return int.from_bytes(rom[at+1:at+3],"little") | int.from_bytes(rom[at+6:at+8],"little") << 16


def convert_sprites(rom: bytes, project: Path, assets: dict):
    groups = yaml.safe_load((project/"sprite_groups.yml").read_text(encoding="utf-8"))
    count = len(groups)
    if sorted(groups) != list(range(count)) or count > 2000:
        raise ConversionError("Sprite group IDs must be contiguous and bounded")
    table = slice_rom(rom,asm_pointer(rom,0x1DF9),count*4)
    pointers = [struct.unpack_from("<I",table,i*4)[0] for i in range(count)]
    data = bytearray(); native_table = bytearray()
    banks = []; dedup = []
    total_frames = 0
    for i, pointer in enumerate(pointers):
        address = snes_offset(pointer,len(rom))
        next_address = snes_offset(pointers[i+1],len(rom)) if i+1<count else address+25
        span = next_address-address
        if span < 9 or (span-9)%2 or span > 41:
            raise ConversionError(f"Sprite group {i} has unexpected frame table size {span}")
        frame_count = (span-9)//2
        header = bytearray(rom[address:address+9])
        frame_size = header[0]*(header[1]>>4)*32
        frames = []
        for frame in range(frame_count):
            ptr = struct.unpack_from("<H",rom,address+9+frame*2)[0]
            graphics = slice_rom(rom,(header[8]<<16)|(ptr&0xFFFC),frame_size) if frame_size else b""
            frames.append((graphics,ptr&3))
        unique = set(graphics for graphics,_ in frames)
        choices = []
        for bank, (content,index) in enumerate(zip(banks,dedup)):
            required = sum(len(g) for g in unique if g not in index)
            if len(content)+required <= 65536:
                choices.append((required,bank))
        if choices:
            _, bank = min(choices)
        else:
            bank = len(banks)
            if bank >= 20 or sum(map(len,unique)) > 65536:
                raise ConversionError("Redux sprite group exceeds native bank-container capacity")
            banks.append(bytearray()); dedup.append({})
        header[8] = 0xD1+bank
        native_table.extend(struct.pack("<I",0xEF1A7F+len(data)))
        data.extend(header)
        for graphics, flags in frames:
            if graphics not in dedup[bank]:
                if len(banks[bank])%4:
                    raise ConversionError("Sprite frame allocation lost flag-bit alignment")
                dedup[bank][graphics] = len(banks[bank])
                banks[bank].extend(graphics)
            data.extend(struct.pack("<H",dedup[bank][graphics]|flags))
        total_frames += frame_count
    if len(data)+0x1A7F > 65536:
        raise ConversionError("Normalized sprite grouping data exceeds legacy pointer window")
    container = bytearray(struct.pack("<8sII",b"MRSPBN01",len(banks),65536))
    used_bytes = sum(map(len,banks))
    for bank in banks:
        container.extend(bank); container.extend(b"\0"*(65536-len(bank)))
    replacements = {
        "overworld_sprites/sprite_grouping_ptr_table.bin":bytes(native_table),
        "overworld_sprites/sprite_grouping_data.bin":bytes(data),
        "overworld_sprites/banks/11.bin":bytes(container)}
    for i in range(8):
        replacements[f"overworld_sprites/palettes/{i}.pal"] = slice_rom(rom,0xC30000+i*32,32)
    for key, value in replacements.items():
        if key not in assets: raise ConversionError(f"Sprite asset absent from native registry: {key}")
        assets[key] = value
    return {"assets":list(replacements),"spriteGroups":count,"spriteFrames":total_frames,
            "normalizedBanks":len(banks),"usedGraphicsBytes":used_bytes}


def convert_fonts(rom: bytes, assets: dict):
    converted = []
    for i, name in enumerate(("main","mrsaturn","battle","tiny","large")):
        widths, graphics, stride, height = struct.unpack_from("<IIHH",rom,0x3F054+i*12)
        expected = (8,8) if name == "tiny" else (16,16) if name == "battle" else (32,16)
        if (stride,height) != expected:
            raise ConversionError(f"Unexpected Redux font layout for {name}: {stride}/{height}")
        for ext, pointer, size in (("bin",widths,128),("gfx",graphics,128*stride)):
            key = f"US/fonts/{name}.{ext}"
            if key not in assets: raise ConversionError(f"Font asset absent from registry: {key}")
            assets[key] = slice_rom(rom,pointer,size); converted.append(key)
    return {"assets":converted,"fontFamilies":5,"charactersPerFont":128}


def convert_indexed_graphics(rom: bytes, project: Path, assets: dict):
    from ebtools.hallz import get_compressed_data, decompress
    converted = []
    empty_unused = []
    bg_rows = [rom[0xADCA1+i*17:0xADCA1+(i+1)*17] for i in range(327)]
    bg_graphic_count = max(row[0] for row in bg_rows)+1
    bg_palette_count = max(row[1] for row in bg_rows)+1
    bg_depths = {}
    for row in bg_rows:
        if row[0] in bg_depths and bg_depths[row[0]] != row[2]:
            raise ConversionError("A Redux battle background graphic has inconsistent bit depth")
        bg_depths[row[0]] = row[2]
    families = (
        (r"(?:US/)?battle_sprites/(\d+)\.gfx\.lzhal",asm_pointer(rom,0x2EE0B),5,True),
        (r"(?:US/)?battle_bgs/gfx/(\d+)\.gfx\.lzhal",asm_pointer(rom,0x2D1BA),4,True),
        (r"(?:US/)?battle_bgs/arrangements/(\d+)\.arr\.lzhal",asm_pointer(rom,0x2D2C1),4,True),
        (r"(?:US/)?battle_bgs/palettes/(\d+)\.pal",asm_pointer(rom,0x2D3BB),4,False),
        (r"(?:US/)?maps/gfx/(\d+)\.gfx\.lzhal",0xEF105B,4,True),
        (r"(?:US/)?maps/arrangements/(\d+)\.arr\.lzhal",0xEF10AB,4,True),
    )
    for pattern, address, stride, compressed in families:
        table = snes_offset(address,len(rom))
        matches = sorted((int(match[1]),key) for key in assets if (match:=re.fullmatch(pattern,key)))
        if [index for index,_ in matches] != list(range(len(matches))):
            raise ConversionError(f"Missing native graphic family members: {pattern}")
        for index, key in matches:
            # CoilSnake deduplicates backgrounds and shrinks these pointer
            # tables. Never parse bytes after the real table as pointers.
            if "battle_bgs/" in key and index >= (bg_palette_count if "/palettes/" in key else bg_graphic_count):
                assets[key] = b"\xFF" if compressed else bytes(len(assets[key]))
                converted.append(key); empty_unused.append(key)
                continue
            pointer = struct.unpack_from("<I",rom,table+index*stride)[0]
            try:
                offset = snes_offset(pointer,len(rom))
            except ConversionError as error:
                raise ConversionError(f"{key}, pointer-table row {index}: {error}") from error
            if compressed:
                content = get_compressed_data(memoryview(rom)[offset:offset+65536])
                unpacked = decompress(content)
                if len(unpacked) > 65536:
                    raise ConversionError(f"Oversized decompressed graphics: {key}")
                expected = None
                if "battle_bgs/gfx/" in key: expected = 512*8*bg_depths[index]
                elif "battle_bgs/arrangements/" in key: expected = 2048
                elif "maps/gfx/" in key: expected = 896*32
                elif "maps/arrangements/" in key: expected = 32768
                if expected is not None and len(unpacked) != expected:
                    raise ConversionError(f"{key}: decompressed {len(unpacked)} bytes, expected {expected}")
                if "battle_sprites/" in key:
                    kind = rom[table+index*stride+4]
                    expected = {1:512,2:1024,3:1024,4:2048,5:4096,6:8192}.get(kind)
                    if len(unpacked) != expected:
                        raise ConversionError(f"Battle sprite {index} size {len(unpacked)} disagrees with size enum {kind}")
            else:
                content = slice_rom(rom,pointer,len(assets[key]))
            assets[key] = bytes(content); converted.append(key)
    sprite_table = slice_rom(rom,asm_pointer(rom,0x2EE0B),550)
    assets["data/battle_sprites_pointers.bin"] = sprite_table
    converted.append("data/battle_sprites_pointers.bin")
    palette_base = asm_pointer(rom,0x2EF74)
    for key in list(assets):
        match = re.fullmatch(r"battle_sprites/palettes/(\d+)\.pal",key)
        if match:
            assets[key] = slice_rom(rom,palette_base+int(match[1])*32,32); converted.append(key)
    # Each tileset-combo owns the same number of 0xC0-byte palettes as its
    # native asset. CoilSnake replaces the physical pointer, not the numbering.
    settings = yaml.safe_load((project/"map_palette_settings.yml").read_text(encoding="utf-8"))
    palette_sets = {}
    for key in list(assets):
        match = re.fullmatch(r"(?:US/)?maps/palettes/(\d+)\.pal",key)
        if match:
            file = int(match[1]); count = len(settings[file])
            pointer = struct.unpack_from("<I",rom,0x2F10FB+file*4)[0]
            palette_sets[file] = (key,bytearray(slice_rom(rom,pointer,count*192)))
    for file,(key,content) in palette_sets.items():
        pending = list(range(0,len(content),192)); seen = {}
        for offset in pending:
            flag = struct.unpack_from("<H",content,offset)[0]
            if not flag: continue
            raw_pointer = struct.unpack_from("<H",content,offset+32)[0]
            if raw_pointer not in seen:
                next_offset = len(content)
                if next_offset//192 >= 2048:
                    raise ConversionError("Too many alternate map palettes")
                content.extend(slice_rom(rom,0xDA0000|raw_pointer,192))
                pending.append(next_offset); seen[raw_pointer] = next_offset//192
            # Native file number (5 bits) and palette-set number (11 bits).
            struct.pack_into("<H",content,offset+32,(file<<11)|seen[raw_pointer])
        assets[key] = bytes(content); converted.append(key)
    for key, offset, size in (("data/bg_data_table.bin",0xADCA1,5559),("data/bg_scrolling_table.bin",0xAF258,1200),
                             ("data/bg_distortion_table.bin",0xAF708,2295),("data/btl_entry_bg_table.bin",0xBD89A,1936)):
        if key not in assets or len(assets[key]) != size:
            raise ConversionError(f"Background table layout differs: {key}")
        assets[key] = rom[offset:offset+size]; converted.append(key)
    return {"assets":converted,"assetCount":len(converted),"unusedFamilySlotsCleared":empty_unused,
            "battleBackgroundGraphics":bg_graphic_count,"battleBackgroundPalettes":bg_palette_count}
