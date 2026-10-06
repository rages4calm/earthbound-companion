# SPDX-License-Identifier: GPL-3.0-or-later
# Actual source LOAD/DISPLAY_ANIMATION_SEQUENCE_FRAME format, CoilSnake HAL codec.
"""Pinned Redux teleport art normalized to the existing native tile stride."""
from maternalbound_dialogue import ConversionError
from maternalbound_graphics import asm_pointer,snes_offset

def convert_sequence_animations(rom,assets):
    from ebtools.hallz import get_compressed_data,decompress,compress
    pointer=asm_pointer(rom,0x47AB0);at=snes_offset(pointer,len(rom));table=rom[at:at+56]
    if len(table)!=56 or any(table[:8]):
        raise ConversionError('Unreviewed animation sequence table')
    source_metadata=((0x1C10,6,3),(0x5A0,7,16),(0x390,8,8),(0xAA0,2,16),(0x40,3,8),(0x120,2,8))
    reviewed=[];teleport=None
    for i,(wanted_tiles,wanted_frames,wanted_delay)in enumerate(source_metadata,1):
        record=table[i*8:(i+1)*8];addr=int.from_bytes(record[:4],'little')
        tiles=int.from_bytes(record[4:6],'little');frames=record[6];delay=record[7]
        if (tiles,frames,delay)!=(wanted_tiles,wanted_frames,wanted_delay):
            raise ConversionError('Source animation metadata changed; review native adapter')
        start=snes_offset(addr,len(rom));stream=bytes(get_compressed_data(memoryview(rom)[start:min(start+65536,len(rom))]));raw=bytes(decompress(stream))
        if len(raw)!=tiles+8+frames*1792 or len(raw)>0x5000 or any(raw[tiles:tiles+2]):
            raise ConversionError('Source animation data exceeds reviewed layout')
        frame_data=raw[tiles+8:]
        max_tile=max(int.from_bytes(frame_data[j:j+2],'little')&1023 for j in range(0,len(frame_data),2))
        if max_tile>=tiles//16:
            raise ConversionError('Source animation arrangement exceeds decoded tiles')
        reviewed.append(dict(id=i,sourcePointer=addr,tileBytes=tiles,frames=frames,delay=delay,
                             decodedBytes=len(raw),maximumArrangementTile=max_tile))
        if i==3:teleport=raw
    key='graphics/animations/starman_jr_teleport.anim.lzhal'
    if key not in assets or len(bytes(decompress(assets[key])))!=0x3C0+8+8*1792:
        raise ConversionError('Native teleport donor layout changed')
    # Compiled source uses57 tiles; native metadata reserves60. Source arrangements
    # were checked above to reference only0..56. Insert3 zero tiles before the
    # source palette/frames; no C, registry, shared buffer or state-format change.
    normalized=teleport[:0x390]+bytes(0x30)+teleport[0x390:]
    if len(normalized)>0x5000:
        raise ConversionError('Normalized teleport animation exceeds native buffer')
    assets[key]=bytes(compress(normalized))
    return dict(assets=[key],sourceTablePointer=pointer,reviewedSourceRecords=reviewed,
                sourceTeleportTileBytes=0x390,nativeTeleportTileBytes=0x3C0,zeroPaddingBytes=0x30,
                paddingUnreferenced=True,sourceFrames=8,sourceDelay=8,
                retainedOtherSequences=5,
                boundary='Other retained sequences require separate source-image/runtime evidence; assignment counts are not conversion parity')
