# SPDX-License-Identifier: GPL-3.0-or-later
# Pack format based on CoilSnake's MusicModule/musicpack; see CREDITS.md.
"""Read compiled Redux SPC packs with bank and ARAM bounds checks."""
import re
from maternalbound_dialogue import ConversionError
from maternalbound_graphics import snes_offset


def convert_audio(rom, assets):
    packs = sorted((int(m[1]),key) for key in assets
                   if (m := re.fullmatch(r"audiopacks/(\d+)\.ebm",key)))
    if [n for n,_ in packs] != list(range(len(packs))):
        raise ConversionError("Native audio pack registry is not contiguous")
    converted = []; total_blocks = 0; changed = 0
    for index, key in packs:
        # EarthBound audio pointers use bank first, then a little-endian word.
        at = 0x4F947+index*3
        pointer = (rom[at]<<16) | int.from_bytes(rom[at+1:at+3],"little")
        start = snes_offset(pointer,len(rom)); offset = start
        limit = min((start & ~0xFFFF)+65536,len(rom))
        blocks = 0
        while offset+2 <= limit:
            size = int.from_bytes(rom[offset:offset+2],"little"); offset += 2
            if not size: break
            if offset+2+size > limit:
                raise ConversionError(f"Audio pack {index} crosses its ROM bank")
            address = int.from_bytes(rom[offset:offset+2],"little"); offset += 2
            if address+size > 65536:
                raise ConversionError(f"Audio pack {index} overflows ARAM")
            offset += size; blocks += 1
            if blocks > 512: raise ConversionError(f"Audio pack {index} has excessive transfers")
        else: raise ConversionError(f"Audio pack {index} has no bank-bounded terminator")
        data = bytes(rom[start:offset]); changed += data != assets[key]
        assets[key] = data; converted.append(key); total_blocks += blocks
    key = "music/dataset_table.bin"
    size = len(assets[key]); dataset = rom[0x4F70A:0x4F70A+size]
    if size % 3 or len(dataset) != size or any(x >= len(packs) and x != 255 for x in dataset):
        raise ConversionError("Invalid Redux song/sample pack table")
    assets[key] = bytes(dataset); converted.append(key)
    return {"assets":converted,"audioPacks":len(packs),"transferBlocks":total_blocks,
            "packsReplaced":changed,"songRecords":size//3,
            "validationBoundary":"Structural conversion; SPC playback and MSU transitions require runtime checks"}
