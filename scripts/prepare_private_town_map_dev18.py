# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepare an isolated Town Map importer/source candidate from frozen dev.17.

Does not modify shared converter/native source, frozen builds, or owner profiles.
The candidate is deliberately outside release/setup/content migration policy.
"""
import argparse, hashlib, json, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
IMPORTER='''# SPDX-License-Identifier: GPL-3.0-or-later
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
'''

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--scratch',type=Path,required=True)
    a=p.parse_args();a.scratch=a.scratch.resolve();a.source=a.source.resolve()
    if a.scratch.exists():raise ValueError('Fresh private candidate required')
    if not a.scratch.is_relative_to(ROOT/'_BuildScratch'):raise ValueError('Candidate must stay inside _BuildScratch')
    a.scratch.mkdir(parents=True);native=a.scratch/'native-source';shutil.copytree(a.source,native)
    tools=a.scratch/'tools';tools.mkdir()
    for file in (ROOT/'tools').glob('*.py'):shutil.copy2(file,tools/file.name)
    archive=ROOT/'research/evidence-tools';archive.mkdir(parents=True,exist_ok=True)
    old={}
    for name in ('maternalbound_graphics.py','build_maternalbound_pack.py'):
        source=ROOT/'tools'/name;target=archive/(source.stem+'-dev17-v4.py')
        if target.exists()and target.read_bytes()!=source.read_bytes():raise ValueError('Existing archive differs')
        if not target.exists():shutil.copy2(source,target)
        old[name]=dict(sha256=sha(source),archive=str(target.relative_to(ROOT)))
    importer=tools/'maternalbound_town_maps.py';importer.write_text(IMPORTER,encoding='utf-8')
    builder=tools/'build_maternalbound_pack.py';text=builder.read_text()
    needle='from maternalbound_psi import convert_psi\n'
    if text.count(needle)!=1:raise ValueError('Pinned builder import boundary changed')
    text=text.replace(needle,needle+'from maternalbound_town_maps import convert_town_maps\n')
    needle='    ending = convert_ending(rom,args.project,assets)\n'
    if text.count(needle)!=1:raise ValueError('Pinned builder family boundary changed')
    text=text.replace(needle,needle+'    town_maps = convert_town_maps(rom,assets)\n')
    text=text.replace('+ending["assets"]+audio["assets"]','+ending["assets"]+town_maps["assets"]+audio["assets"]')
    text=text.replace('"ending":ending,"audio":audio','"ending":ending,"townMaps":town_maps,"audio":audio')
    builder.write_text(text,encoding='utf-8')
    town=native/'src/game/town_map.c';before=town.read_bytes();text=before.decode('utf-8')
    newline='\r\n'if b'\r\n'in before else'\n'
    needle='    /* Upload tile data: BUFFER+$840 → VRAM $0000, $4000 bytes */\n    memcpy(&ppu.vram[0x0000], ert.buffer + 0x840, 0x4000);'
    needle=needle.replace('\n',newline)
    if text.count(needle)!=1:raise ValueError('Frozen Town Map upload boundary changed')
    replacement='''    /* Pinned Redux C4D625 uploads $6000 tile bytes. The importer proves
     * its extra $2000 are zero and no arrangement references tiles above511.
     * Native's shared buffer holds20KB, so retain the bounded $4000 tile copy
     * and reproduce the source zero tail directly in VRAM. Original unchanged. */
    _Static_assert(0x6000 <= sizeof(ppu.vram), "Town Map tile upload exceeds VRAM");
    _Static_assert(0x840 + 0x4000 <= BUFFER_SIZE, "Town Map tile read exceeds buffer");
    memcpy(&ppu.vram[0x0000], ert.buffer + 0x840, 0x4000);
    if (maternalbound_enabled())
        memset(&ppu.vram[0x4000], 0, 0x2000);'''
    town.write_bytes(text.replace(needle,replacement.replace('\n',newline)).encode('utf-8'))
    result=dict(toolSha256=sha(Path(__file__)),baselineSource=str(a.source),baselineTownMapSha256=hashlib.sha256(before).hexdigest(),
                candidateTownMapSha256=sha(town),archivedConverters=old,newImporterSha256=sha(importer),candidateBuilderSha256=sha(builder),
                sharedNativeModified=False,sharedConverterModified=False,ownerWrites=False,releaseCandidate=False,
                candidateFiles=['native-source/src/game/town_map.c','tools/build_maternalbound_pack.py','tools/maternalbound_town_maps.py'])
    (a.scratch/'preparation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
