# SPDX-License-Identifier: GPL-3.0-or-later
# Native format/adaptation work based on MaternalBound Redux and CoilSnake.
# Upstream authors and source links are recorded in CREDITS.md.
"""Convert relocated Redux world tables without retaining physical ROM layouts."""
import re
import struct
from maternalbound_dialogue import ConversionError
from maternalbound_graphics import snes_offset, slice_rom


def convert_world(rom, assets, relocation):
    converted = []
    pointers = {int(key,16):value for key,value in relocation["originalAddresses"].items()}
    pointers.update({int(key,16):value for key,value in relocation["compiledAddresses"].items()})
    def put(key, value):
        if key not in assets: raise ConversionError(f"Missing world asset: {key}")
        assets[key] = bytes(value); converted.append(key)
    def u16(offset): return struct.unpack_from("<H",rom,offset)[0]
    def u32(offset): return struct.unpack_from("<I",rom,offset)[0]
    def relocate(raw, offset):
        value = struct.unpack_from("<I",raw,offset)[0]
        if not value: return 0
        if value not in pointers: raise ConversionError(f"Unmapped world dialogue pointer {value:06X}")
        struct.pack_into("<I",raw,offset,pointers[value]); return 1
    fixed = (("global_map_tilesetpalette_data",0x17A800,2560),("per_sector_attributes",0x17B200,5120),
             ("tileset_table",0x2F101B,64),("per_sector_music",0x1CD637,2560),
             ("per_sector_town_map",0x2FA70F,7680),("initial_stats",0x15F5F5,80),
             ("exp_table",0x158F49,1600),("stats_growth_vars",0x15EA5B,28),
             ("playable_character_graphics_table",0x3F2B5,272),("character_sizes",0x3E09A,34),
             ("hotspot_coordinates",0x15F2FB,448),("teleport_destination_table",0x15EBAB,1872))
    for name,offset,size in fixed:
        put(f"data/{name}.bin",rom[offset:offset+size])
    table = snes_offset(int.from_bytes(rom[0xA1DB:0xA1DE],"little"),len(rom))
    for i in range(8):
        keys = [key for key in assets if re.fullmatch(rf"(?:US/)?maps/tiles/chunk_{i+1:02d}\.bin",key)]
        if len(keys) != 1: raise ConversionError("Ambiguous map tile chunk")
        put(keys[0],slice_rom(rom,u32(table+i*4),10240))
    put("maps/tiles/chunk_09.bin",rom[0x175000:0x175000+10240])
    put("maps/tiles/chunk_10.bin",rom[0x178000:0x178000+10240])

    # Deduplicated collision records retain their low-word offsets in D8.
    # Pointer arrays are normalized to 1024 entries per drawing tileset.
    collision_arrays = bytearray(b"MRCOLL01")
    for i in range(20):
        collision_arrays.extend(slice_rom(rom,u32(0x2F117B+i*4),2048))
    put("data/map/collision_pointers_blob.bin",collision_arrays)
    put("data/map/collision_arrangement_table.bin",rom[0x180000:0x190000])
    for i in range(20*1024):
        ptr = struct.unpack_from("<H",collision_arrays,8+i*2)[0]
        if ptr+16 > 65536: raise ConversionError("Collision arrangement pointer exceeds D8")

    # NPC sector lists retain the engine's established Y/X record order, but
    # their physical bank-CF allocation is normalized to the original base.
    npc_ptrs = bytearray(); npc_data = bytearray(); npc_entries = 0
    source = snes_offset(int.from_bytes(rom[0x2261:0x2264],"little"),len(rom))
    for i in range(1280):
        ptr = u16(source+i*2)
        if not ptr: npc_ptrs.extend(b"\0\0"); continue
        offset = 0xF0000|ptr; count = u16(offset)
        if count > 1024 or offset+2+count*4 > 0x100000:
            raise ConversionError("Invalid NPC placement list")
        data = rom[offset:offset+2+count*4]
        if len(npc_data)+len(data)+0x6BE7 > 65536:
            raise ConversionError("NPC placements exceed native pointer window")
        npc_ptrs.extend(struct.pack("<H",0x6BE7+len(npc_data))); npc_data.extend(data)
        for row in range(count):
            if struct.unpack_from("<H",data,2+row*4)[0] >= 1584:
                raise ConversionError("NPC placement references an absent configuration")
        npc_entries += count
    put("data/sprite_placement_ptr_table.bin",npc_ptrs)
    put("data/sprite_placement_table.bin",npc_data)

    event_table = snes_offset(int.from_bytes(rom[0x70D:0x710],"little"),len(rom))
    event_bank = rom[0x704]
    event_ptrs = bytearray(); event_data = bytearray(); changes = 0
    for i in range(20):
        ptr = u16(event_table+i*2)
        offset = snes_offset((event_bank<<16)|ptr,len(rom))
        event_ptrs.extend(struct.pack("<H",len(event_data)))
        for _ in range(1024):
            flag = u16(offset)
            if not flag:
                event_data.extend(b"\0\0"); break
            count = u16(offset+2)
            if count > 1024: raise ConversionError("Oversized map event change list")
            end = offset+4+count*4
            raw = rom[offset:end]
            if len(raw) != 4+count*4: raise ConversionError("Truncated map event changes")
            for pos in range(4,len(raw),2):
                if struct.unpack_from("<H",raw,pos)[0] >= 1024:
                    raise ConversionError("Map event replacement references an absent block")
            event_data.extend(raw); offset=end; changes+=count
        else: raise ConversionError("Unterminated map event changes")
        if len(event_data)>65535: raise ConversionError("Map event data exceeds native pointer window")
    put("maps/event_control_ptr_table.bin",event_ptrs)
    put("maps/tile_event_control_table.bin",event_data)

    door_ptrs = bytearray(); door_configs = bytearray(); destinations = bytearray()
    relocated = 0; door_count = 0; seen = {}
    for i in range(1280):
        pointer = u32(0x100000+i*4)
        # CoilSnake's shared empty area is stored as a physical ROM offset.
        # Accept that exact zero-count representation, never a populated area.
        if pointer < 0x400000:
            if pointer+2 > len(rom) or u16(pointer) != 0:
                raise ConversionError("A physical door pointer is not an empty area")
            offset = pointer
        else:
            offset = snes_offset(pointer,len(rom))
        count = u16(offset)
        if count > 1024: raise ConversionError("Oversized door area")
        raw = bytearray(rom[offset:offset+2+count*5])
        if len(raw) != 2+count*5: raise ConversionError("Truncated door area")
        door_ptrs.extend(struct.pack("<I",0xCF264F+len(door_configs)))
        for row in range(count):
            pos=2+row*5; kind=raw[pos+2]; ptr=struct.unpack_from("<H",raw,pos+3)[0]
            if kind > 6: raise ConversionError("Invalid compiled door type")
            if kind in (1,3,4): continue  # rope/ladder and stairs store scalar directions
            size = 6 if kind==0 else 11 if kind==2 else 4
            if ptr+size > 0x8000: raise ConversionError("Door destination exceeds engine low-word range")
            if (ptr,kind) not in seen:
                entry = bytearray(rom[0xF0000+ptr:0xF0000+ptr+size])
                relocated += relocate(entry,2 if kind==0 else 0)
                if len(destinations)<ptr+size: destinations.extend(bytes(ptr+size-len(destinations)))
                for at in range(ptr,ptr+size):
                    if at in seen and seen[at] != entry[at-ptr]:
                        raise ConversionError("Overlapping incompatible door destinations")
                    seen[at] = entry[at-ptr]
                destinations[ptr:ptr+size]=entry; seen[(ptr,kind)] = True
            door_count += 1
        door_configs.extend(raw)
    put("maps/door_pointer_table.bin",door_ptrs)
    put("maps/door_config_table.bin",door_configs)
    put("maps/door_data.bin",destinations)
    put("maps/screen_transition_config.bin",rom[0x101400:0x101400+408])
    return {"assets":converted,"npcPlacements":npc_entries,"doorDestinations":door_count,
            "relocatedDoorDialoguePointers":relocated,"eventBlockReplacements":changes,
            "collisionBlocksPerTileset":1024}
