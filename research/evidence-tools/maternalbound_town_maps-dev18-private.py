# SPDX-License-Identifier: GPL-3.0-or-later
# Source formats from CoilSnake CompressedGraphicsModule/TownMapIconModule.
"""Checked pinned Redux Town Map art; preserves already matching shared tables."""
from maternalbound_dialogue import ConversionError
from maternalbound_graphics import asm_pointer, slice_rom, snes_offset

def convert_town_maps(rom, assets):
    from ebtools.hallz import get_compressed_data, decompress, compress
    if asm_pointer(rom,0x4D56A)!=0xE02190 or rom[0x4D625:0x4D628]!=bytes((0xA2,0x00,0x60)):
        raise ConversionError("Pinned Town Map table/upload consumer changed")
    pointers=slice_rom(rom,0xE02190,24)
    converted=[]; source=[]
    def compressed(pointer,expected,key):
        start=snes_offset(pointer,len(rom))
        stream=bytes(get_compressed_data(memoryview(rom)[start:min(start+65536,len(rom))]))
        raw=bytes(decompress(stream))
        if len(raw)!=expected or key not in assets:
            raise ConversionError(f"Invalid source Town Map layout: {key}")
        assets[key]=stream;converted.append(key)
        source.append(dict(asset=key,sourcePointer=pointer,decodedBytes=len(raw)))
        return raw
    for i in range(6):
        key=("US/"if i in(2,4)else"")+f"town_maps/{i}.bin.lzhal"
        pointer=int.from_bytes(pointers[i*4:i*4+4],"little")
        raw=compressed(pointer,0x6840,key)
        words=[int.from_bytes(raw[j:j+2],"little")for j in range(0x40,0x840,2)]
        if any((w&1023)>=512 or ((w>>10)&7)>=2 for w in words) or any(raw[0x4840:]):
            raise ConversionError(f"Town Map {i} exceeds the reviewed native512-tile adaptation")
        # Source reserves768 tiles, but the upper256 are zero and no source
        # arrangement references them. Native shared buffer holds20KB. Keep
        # source-visible512 tiles; the consumer reproduces the zero-tail clear.
        assets[key]=bytes(compress(raw[:0x4840]))
        source[-1]["nativeNormalizedDecodedBytes"]=0x4840
    compressed(asm_pointer(rom,0x4D62F),0x2400,"US/town_maps/label.gfx.lzhal")
    if assets["town_maps/icon.pal"]!=slice_rom(rom,asm_pointer(rom,0x4D5C4),64):
        raise ConversionError("Town Map shared icon palette changed; review before importing")
    placement_table=asm_pointer(rom,0x4D464);table=slice_rom(rom,placement_table,24);placement=bytearray()
    for i in range(6):
        pointer=int.from_bytes(table[i*4:i*4+4],"little");at=snes_offset(pointer,len(rom));start=at
        for _ in range(256):
            if at>=len(rom):raise ConversionError("Town Map icon placement exceeds ROM")
            if rom[at]==255:break
            if at+5>len(rom):raise ConversionError("Truncated Town Map icon placement")
            at+=5
        else:raise ConversionError("Unterminated Town Map icon placement")
        placement.extend(rom[start:at+1])
    if placement!=assets["town_maps/icon_placement.bin"]:
        raise ConversionError("Town Map shared icon placement changed; review before importing")
    for key,pointer,length in (("town_maps/icon_spritemaps.bin",0xE1F203,585),
        ("town_maps/icon_spritemap_ptrs.bin",asm_pointer(rom,0x4D44F),46),
        ("town_maps/icon_animation_flags.bin",0xE1F47A,23),("town_maps/mapping.bin",0xEFC50F,12)):
        if assets[key]!=slice_rom(rom,pointer,length):
            raise ConversionError(f"Town Map shared table changed: {key}")
    return dict(assets=converted,sourceConsumers=source,maps=6,labelTileBytes=0x2400,
                mapTileUploadBytes=0x6000,nativeMapTileCopyBytes=0x4000,nativeMapZeroTailBytes=0x2000,sharedTablesVerifiedUnchanged=6,
                boundary="Source imports only; native render, save/content identity and setup migration require separate verification")
