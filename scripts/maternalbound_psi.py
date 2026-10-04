# SPDX-License-Identifier: GPL-3.0-or-later
# Redux Extended_PSI_Animations and upstream ebtools streaming format.
# Authors and upstream links are listed in CREDITS.md.
"""Normalize all 68 Redux PSI effects into a bounded native streaming container."""
import struct
from maternalbound_dialogue import ConversionError
from maternalbound_graphics import asm_pointer, slice_rom, snes_offset

COUNT=68
GFX_WORDS=(0x2E19,0x4599,0x38AA,0x5FB1,0x3141,0x4C3F,0x3FDE,0x548C,0x5A9D,0x62A1)


def bundle_frames(raw):
    from ebtools.hallz import compress
    count=len(raw)//1024
    chunks=[bytes(compress(raw[start:start+8192])) for start in range(0,len(raw),8192)]
    offsets=[0]
    for data in chunks: offsets.append(offsets[-1]+len(data))
    if offsets[-1]>65535: raise ConversionError("PSI bundle exceeds native offset width")
    return struct.pack("<BBH",8,count,len(chunks))+struct.pack(f"<{len(offsets)}H",*offsets)+b"".join(chunks)


def convert_psi(rom,assets):
    from ebtools.hallz import get_compressed_data, decompress
    key="data/psi_anim_cfg.bin"
    if key not in assets: raise ConversionError("Missing native PSI configuration")
    if int.from_bytes(rom[0x2E154:0x2E157],"little")!=0xF20000 or int.from_bytes(rom[0x2E1BB:0x2E1BE],"little")!=0xF20000:
        raise ConversionError("Redux PSI configuration loader changed")
    if asm_pointer(rom,0x2E461)!=0xF20400 or asm_pointer(rom,0x2E2F4)!=0xF20600:
        raise ConversionError("Redux PSI arrangement/palette loaders changed")
    configs=bytearray(slice_rom(rom,0xF20000,COUNT*12))
    def compressed(pointer):
        offset=snes_offset(pointer,len(rom))
        return bytes(get_compressed_data(memoryview(rom)[offset:offset+65536]))
    entries=[]; sources=[]; total_frames=0
    for word in GFX_WORDS:
        data=compressed(0xCC0000+word)
        if len(decompress(data))!=4096: raise ConversionError("Unexpected PSI tileset size")
        entries.append(data); sources.append(0xCC0000+word)
    for index in range(COUNT):
        start=index*12
        word=struct.unpack_from("<H",configs,start)[0]
        if word not in GFX_WORDS: raise ConversionError(f"Unknown PSI tileset {word:04X}")
        struct.pack_into("<H",configs,start,GFX_WORDS.index(word))
        frame_hold,palette_period,lower,upper,frames,target=configs[start+2:start+8]
        # A zero palette period intentionally disables cycling after the
        # initial upload (Redux's Sing Melody effects).
        if not frame_hold or lower>upper or upper>3 or not frames or target>3:
            raise ConversionError(f"Invalid PSI configuration {index}")
        pointer=int.from_bytes(slice_rom(rom,0xF20400+index*4,4),"little")
        raw=bytes(decompress(compressed(pointer)))
        if len(raw)!=frames*1024: raise ConversionError(f"PSI {index} frame count differs from config")
        entries.append(bundle_frames(raw)); sources.append(pointer); total_frames+=frames
    for index in range(COUNT):
        entries.append(bytes(slice_rom(rom,0xF20600+index*8,8)))
    # Config remains at offset zero; a typed directory replaces hardcoded bank
    # addresses without expanding the global native asset registry.
    directory_start=COUNT*12+16
    cursor=directory_start+len(entries)*8
    directory=bytearray()
    for data in entries:
        directory.extend(struct.pack("<II",cursor,len(data))); cursor+=len(data)
    assets[key]=bytes(configs)+struct.pack("<8sHHI",b"MRPSIX01",COUNT,len(GFX_WORDS),len(entries))+directory+b"".join(entries)
    return {"assets":[key],"animations":COUNT,"tilesets":len(GFX_WORDS),"frames":total_frames,
            "format":"MRPSIX01","bytes":len(assets[key]),"sourcePointers":sources,
            "limits":["Native playback and battle integration require separate verification."]}
