# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepare isolated gas-station art importer without altering shared sources."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
IMPORTER='''# SPDX-License-Identifier: GPL-3.0-or-later
# Source format: CoilSnake CompressedGraphicsModule / actual GAS_STATION_LOAD.
"""Import pinned Redux gas-station BG1 art; preserve source-equal palettes."""
from maternalbound_dialogue import ConversionError
from maternalbound_graphics import asm_pointer, snes_offset

def convert_gas_station(rom, assets):
    from ebtools.hallz import get_compressed_data, decompress
    recipes=(('US/intro/gas_station.gfx.lzhal',0xF0F0,40448),
             ('US/intro/gas_station.arr.lzhal',0xF11B,2048))
    if b'\\xa0\\x00\\x00\\xa2\\x00\\xc0\\xe2\\x20' not in rom[0xF0F0:0xF130]:
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
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline-candidate',type=Path,required=True)
    p.add_argument('--scratch',type=Path,required=True)
    a=p.parse_args();a.scratch=a.scratch.resolve();a.baseline_candidate=a.baseline_candidate.resolve()
    if not a.scratch.is_relative_to(ROOT/'_BuildScratch')or a.scratch.exists():
        raise ValueError('Fresh private candidate required')
    baseline=a.baseline_candidate/'tools/build_maternalbound_pack.py'
    if sha(baseline)!='e04d6632c11e09596a3470198585a701a8b6130f4ba7bb90d4136244debc1b9c':
        raise ValueError('Expected frozen Town Map candidate builder')
    a.scratch.mkdir(parents=True);tools=a.scratch/'tools'
    shutil.copytree(a.baseline_candidate/'tools',tools)
    module=tools/'maternalbound_gas_station.py';module.write_text(IMPORTER,encoding='utf-8')
    builder=tools/'build_maternalbound_pack.py';text=builder.read_text(encoding='utf-8')
    import_needle='from maternalbound_town_maps import convert_town_maps\n'
    call_needle='    town_maps = convert_town_maps(rom,assets)\n'
    for needle in (import_needle,call_needle):
        if text.count(needle)!=1:
            raise ValueError('Frozen builder boundary changed')
    text=text.replace(import_needle,import_needle+'from maternalbound_gas_station import convert_gas_station\n')
    text=text.replace(call_needle,call_needle+'    gas_station = convert_gas_station(rom,assets)\n')
    text=text.replace('+town_maps["assets"]+audio["assets"]','+town_maps["assets"]+gas_station["assets"]+audio["assets"]')
    text=text.replace('"townMaps":town_maps,"audio":audio','"townMaps":town_maps,"gasStation":gas_station,"audio":audio')
    builder.write_text(text,encoding='utf-8')
    result=dict(toolSha256=sha(__file__),baselineBuilderSha256=sha(baseline),candidateBuilderSha256=sha(builder),
                newImporterSha256=sha(module),unchangedNativeCandidate=str(a.baseline_candidate/'native-source'),
                sharedNativeModified=False,sharedConverterModified=False,ownerWrites=False,releaseCandidate=False)
    (a.scratch/'preparation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':
    main()
