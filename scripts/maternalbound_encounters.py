# SPDX-License-Identifier: GPL-3.0-or-later
# Native format/adaptation work based on MaternalBound Redux and CoilSnake.
# Upstream authors and source links are recorded in CREDITS.md.
"""Checked native relocation of Redux battle groups and event-dependent music.

Formats follow CoilSnake EnemyModule/MapEnemyModule/MapMusicModule and the native
readers. This tool reads only local owner-provided game data.
"""
import struct
from maternalbound_dialogue import ConversionError
from maternalbound_graphics import slice_rom, snes_offset

def convert_encounters(rom:bytes, assets:dict):
    converted=[]
    def put(name,value):
        key="data/"+name+".bin"
        if key not in assets: raise ConversionError("Missing native encounter asset: "+key)
        assets[key]=bytes(value);converted.append(key)
    def u16(at):
        if at < 0 or at+2>len(rom): raise ConversionError("Truncated encounter record")
        return struct.unpack_from("<H",rom,at)[0]

    table=bytearray(slice_rom(rom,0xD0C60D,484*8));groups=bytearray();dedup={};entries=0
    for row in range(484):
        pointer=struct.unpack_from("<I",table,row*8)[0]
        if pointer not in dedup:
            start=at=snes_offset(pointer,len(rom));count=0
            while rom[at]!=255:
                amount=rom[at];enemy=u16(at+1)
                # Redux retains zero-amount entries in several battle groups.
                if enemy>=231 or count>=128:
                    raise ConversionError(f"Invalid battle-group row {row}")
                at+=3;count+=1
            dedup[pointer]=0xD0D52D+len(groups)
            groups.extend(rom[start:at+1]);entries+=count
        struct.pack_into("<I",table,row*8,dedup[pointer])
    put("btl_entry_ptr_table",table);put("enemy_battle_groups_table",groups)

    placement=slice_rom(rom,0xD01880,40960)
    if any(value>=203 for value, in struct.iter_unpack("<H",placement)):
        raise ConversionError("Map encounter grid references a missing group")
    put("map_enemy_placement",placement)
    table=bytearray(slice_rom(rom,0xD0B880,203*4));groups=bytearray();dedup={}
    for row in range(203):
        pointer=struct.unpack_from("<I",table,row*4)[0]
        if pointer not in dedup:
            start=at=snes_offset(pointer,len(rom))
            if at+4>len(rom): raise ConversionError("Truncated encounter-group header")
            rates=rom[at+2:at+4];at+=4
            for rate in rates:
                if rate>100: raise ConversionError("Invalid encounter-group rate")
                if not rate: continue
                probability=0;subentries=0
                while probability<8:
                    slots=rom[at];group=u16(at+1)
                    if slots>8 or group>=484 or subentries>=128:
                        raise ConversionError(f"Invalid map encounter subgroup {row}")
                    probability+=slots;at+=3;subentries+=1
                if probability!=8: raise ConversionError("Encounter probabilities do not sum to eight")
            dedup[pointer]=0xD0BBAC+len(groups);groups.extend(rom[start:at])
        struct.pack_into("<I",table,row*4,dedup[pointer])
    put("enemy_placement_groups_ptr_table",table);put("enemy_placement_groups",groups)

    # CoilSnake moves the pointer table, while music lists stay in bank CF.
    address=int.from_bytes(rom[0x6939:0x693C],"little")
    source=snes_offset(address,len(rom));table=bytearray();music=bytearray();dedup={};music_entries=0
    for row in range(165):
        pointer=u16(source+row*2)
        if pointer not in dedup:
            start=at=snes_offset(0xCF0000|pointer,len(rom));count=0
            if row==0:
                # The pinned upstream zone-zero list contains stale code bytes
                # rather than valid music records. Its terminal default is
                # silence. Repair only this exact known list, recorded below.
                known=((45582,201),(33401,49306),(945,33284),(51631,0),(2816,34561),(256,0),(0,0))
                expected=b"".join(struct.pack("<HH",*value) for value in known)
                if rom[start:start+len(expected)]!=expected:
                    raise ConversionError("Unknown zone-zero music layout; re-audit before conversion")
                dedup[pointer]=0x5A39+len(music);music.extend(bytes(4));music_entries+=1
                table.extend(struct.pack("<H",dedup[pointer]));continue
            while True:
                flag=u16(at);track=u16(at+2)
                if track>191 or (flag&0x7FFF)>1023 or count>=1024:
                    raise ConversionError(f"Invalid event-music row {row}")
                at+=4;count+=1
                if not flag: break
            dedup[pointer]=0x5A39+len(music)
            if dedup[pointer]+at-start>0x8000: raise ConversionError("Normalized music lists exceed native pointer window")
            music.extend(rom[start:at]);music_entries+=count
        table.extend(struct.pack("<H",dedup[pointer]))
    put("overworld_event_music_ptr_table",table);put("overworld_event_music_table",music)
    return {"assets":converted,"battleGroups":484,"battleGroupEntries":entries,
            "mapEncounterGroups":203,"musicZones":165,"eventMusicEntries":music_entries,
            "explicitRepairs":["Pinned invalid music-zone-zero record replaced with its silence default"]}
