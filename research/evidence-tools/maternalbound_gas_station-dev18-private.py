# SPDX-License-Identifier: GPL-3.0-or-later
# Source format: CoilSnake CompressedGraphicsModule / actual GAS_STATION_LOAD.
"""Import pinned Redux gas-station BG1 art; preserve source-equal palettes."""
from maternalbound_dialogue import ConversionError
from maternalbound_graphics import asm_pointer, snes_offset

def convert_gas_station(rom, assets):
    from ebtools.hallz import get_compressed_data, decompress
    recipes=(('US/intro/gas_station.gfx.lzhal',0xF0F0,40448),
             ('US/intro/gas_station.arr.lzhal',0xF11B,2048))
    if b'\xa0\x00\x00\xa2\x00\xc0\xe2\x20' not in rom[0xF0F0:0xF130]:
        raise ConversionError('Pinned GAS_STATION_LOAD graphics upload changed')
    source=[];decoded={}
    def stream(site):
        pointer=asm_pointer(rom,site);at=snes_offset(pointer,len(rom))
        content=bytes(get_compressed_data(memoryview(rom)[at:min(at+65536,len(rom))]))
        return pointer,content,bytes(decompress(content))
    for key,site,expected in recipes:
        pointer,content,raw=stream(site)
        if key not in assets or len(raw)!=expected:
            raise ConversionError(f'Unreviewed source gas-station layout: {key}')
        decoded[key]=raw;assets[key]=content
        source.append(dict(asset=key,sourcePointer=pointer,decodedBytes=len(raw)))
    graphics=decoded[recipes[0][0]];arrangement=decoded[recipes[1][0]]
    max_tile=max(int.from_bytes(arrangement[j:j+2],'little')&1023 for j in range(0,2048,2))
    if max_tile>=len(graphics)//64:
        # Mode3 BG1 is8bpp,64 bytes per tile. No referenced tile may come from
        # the implicit zero padding beyond the decoded source graphics.
        raise ConversionError('Gas-station source exceeds decoded tile capacity')
    for key,site in (('intro/gas_station.pal.lzhal',0xF147),('intro/gas_station2.pal.lzhal',0xF3BA)):
        _,_,raw=stream(site)
        if len(raw)!=512 or raw!=bytes(decompress(assets[key])):
            raise ConversionError('Shared gas-station palette changed: '+key)
    return dict(assets=[x[0]for x in recipes],sourceConsumers=source,
                sourceMaximumArrangementTile=max_tile,graphicsUploadBytes=0xC000,
                arrangementUploadBytes=0x800,palettesVerifiedUnchanged=2,
                boundary='Art conversion only; actual consumer/cold/content-migration proof is separate')
