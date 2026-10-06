# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only source/registry converter-family review with a private traced build.

Assignment counts describe importer execution, not gameplay or conversion parity.
ROM bytes and private regenerated packs never enter the public JSON report.
"""
import argparse
import ast
import collections
import contextlib
import hashlib
import inspect
import io
import json
import re
import sys
import yaml
import struct
from pathlib import Path
from types import SimpleNamespace

import build_maternalbound_pack as builder
import battle_art_decode_qa_dev20 as art
from maternalbound_graphics import asm_pointer, snes_offset

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TracedAssets(dict):
    def __init__(self, values):
        super().__init__(values)
        self.writes = []

    def __setitem__(self, key, value):
        frames = inspect.stack(context=0)
        producer = next((x for x in frames if x.function.startswith('convert_') or x.function == 'build'), None)
        old = self.get(key)
        self.writes.append(dict(asset=key, producer=producer.function if producer else 'unknown',
                                file=Path(producer.filename).name if producer else None,
                                line=producer.lineno if producer else None,
                                oldBytes=len(old) if old is not None else None, newBytes=len(value),
                                oldSha256=art.h(old) if old is not None else None, newSha256=art.h(value)))
        super().__setitem__(key, value)

    def update(self, values=(), **kwargs):
        for key, value in dict(values, **kwargs).items():
            self[key] = value


def regex_inventory(paths, registry):
    output = []
    for path in paths:
        tree = ast.parse(path.read_text())
        candidates = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == 're' and node.func.attr in ('fullmatch','match') and node.args:
                candidates.append((node.lineno, node.args[0], 're.'+node.func.attr))
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'families' for t in node.targets) and isinstance(node.value, (ast.List, ast.Tuple)):
                for entry in node.value.elts:
                    if isinstance(entry, ast.Tuple) and entry.elts and isinstance(entry.elts[0], ast.Constant) and isinstance(entry.elts[0].value, str) and '(' in entry.elts[0].value:
                        candidates.append((entry.lineno, entry.elts[0], 'indexed families tuple'))
        for line, pattern, origin in candidates:
            row = dict(file=path.name, line=line, origin=origin, expression=ast.unparse(pattern))
            if isinstance(pattern, ast.Constant) and isinstance(pattern.value, str):
                regex = pattern.value
                # Dialogue's address parsers do not select registry assets.
                is_registry = any(x in regex for x in ('audiopacks/','battle_sprites/','battle_bgs/','maps/'))
                row['registrySelector'] = is_registry
                if is_registry:
                    matches = [x for x in registry if re.fullmatch(regex, x)]
                    row.update(pattern=regex, matchedCount=len(matches), matchedAssets=matches, zeroMatches=len(matches)==0)
            else:
                row['dynamicPatternReviewRequired'] = True
            output.append(row)
    return output


def town_pixels(raw):
    """Independent 4bpp/32x28 town-map base image, excluding OBJ labels/icons."""
    if len(raw)<0x4840:
        raise ValueError('Truncated town map base data')
    palette = [int.from_bytes(raw[i:i+2],'little') & 0x7FFF for i in range(0,64,2)]
    output=bytearray()
    for y in range(224):
        for x in range(256):
            word=int.from_bytes(raw[64+((y//8)*32+x//8)*2:66+((y//8)*32+x//8)*2],'little')
            tile=word&1023;px=7-x%8 if word&0x4000 else x%8;py=7-y%8 if word&0x8000 else y%8
            pos=0x840+tile*32
            if pos+32>len(raw):raise ValueError('Map arrangement references missing graphics')
            color=sum(((raw[pos+py*2+(plane%2)+(plane//2)*16]>>(7-px))&1)<<plane for plane in range(4))
            index=((word>>10)&7)*16+color if color else 0
            if index>=len(palette):raise ValueError('Map arrangement references absent palette')
            output.extend(palette[index].to_bytes(2,'little'))
    return bytes(output)


def relocated_presentation_inventory(rom, assets, written, native, coilsnake):
    rows=[]
    def add(key, pointer, family, compressed=True, size=None, pointerSite=None, pixel=False):
        offset=snes_offset(pointer,len(rom))
        expected=art.strict_decode(rom[offset:])[0] if compressed else rom[offset:offset+size]
        actual=art.strict_decode(assets[key],True)[0] if compressed else assets[key]
        row=dict(asset=key,family=family,sourcePointer=pointer,sourceOffset=offset,sourcePointerLoadOffset=pointerSite,
                 importerAssigned=key in written,sourceBytes=len(expected),nativePackedDecodedBytes=len(actual),
                 sourceSha256=art.h(expected),nativeDecodedSha256=art.h(actual),sourceBytesEqual=expected==actual,
                 sourceBytesEqualWithZeroTailPadding=expected.ljust(max(len(expected),len(actual)),b'\0')==actual.ljust(max(len(expected),len(actual)),b'\0'))
        if pixel:
            source_pixels=town_pixels(expected);native_pixels=town_pixels(actual)
            words=[int.from_bytes(expected[i:i+2],'little')for i in range(64,64+1792,2)]
            row.update(sourceBasePixelSha256=art.h(source_pixels),nativeBasePixelSha256=art.h(native_pixels),
                       differingBasePixels=sum(source_pixels[i:i+2]!=native_pixels[i:i+2]for i in range(0,len(source_pixels),2)),
                       sourceMaxDisplayedTile=max(x&1023 for x in words),sourceExtraMapTileTailAllZero=not any(expected[0x4840:]),
                       pixelComparisonScope='Independent source-layout base image, 256x224, SNES BGR15 colors, excluding dynamic OBJ labels/icons/player marker.')
        rows.append(row)
    for i in range(6):
        key=('US/'if i in(2,4)else'')+f'town_maps/{i}.bin.lzhal'
        add(key,int.from_bytes(rom[0x202190+i*4:0x202194+i*4],'little'),'town maps',pointerSite=0x202190+i*4,pixel=True)
    specs=[
        ('US/town_maps/label.gfx.lzhal',0x4D62F,'town map labels',True,None),
        ('town_maps/icon.pal',0x4D5C4,'town map labels palette',False,64),
        ('E1CFAF.gfx.lzhal',0x4C32F,'game over tiles',True,None),
        ('E1D5E8.arr.lzhal',0x4C388,'game over arrangements',True,None),
        ('E1D4F4.pal.lzhal',0x4C3C3,'game over palette',True,None),
        ('US/graphics/sound_stone.gfx.lzhal',0x4ACF0,'Sound Stone tiles',True,None),
        ('US/intro/logos/nintendo.gfx.lzhal',0xEEA3,'Nintendo logo',True,None),
        ('US/intro/logos/nintendo.arr.lzhal',0xEEBB,'Nintendo logo',True,None),
        ('intro/logos/nintendo.pal.lzhal',0xEED3,'Nintendo logo',True,None),
        ('intro/logos/ape.gfx.lzhal',0xEEFB,'APE logo',True,None),
        ('intro/logos/ape.arr.lzhal',0xEF13,'APE logo',True,None),
        ('intro/logos/ape.pal.lzhal',0xEF2B,'APE logo',True,None),
        ('intro/logos/halken.gfx.lzhal',0xEF52,'HALKEN logo',True,None),
        ('intro/logos/halken.arr.lzhal',0xEF6A,'HALKEN logo',True,None),
        ('intro/logos/halken.pal.lzhal',0xEF82,'HALKEN logo',True,None),
        ('intro/attract/produced_by_itoi.gfx.lzhal',0x4DD73,'Produced by logo',True,None),
        ('intro/attract/produced_by_itoi.arr.lzhal',0x4DD3A,'Produced by logo',True,None),
        ('intro/attract/nintendo_presentation.gfx.lzhal',0x4DE1B,'Presented by logo',True,None),
        ('intro/attract/nintendo_presentation.arr.lzhal',0x4DDE2,'Presented by logo',True,None),
        ('US/intro/gas_station.gfx.lzhal',0xF0F0,'Gas station',True,None),
        ('US/intro/gas_station.arr.lzhal',0xF11B,'Gas station',True,None),
        ('intro/gas_station.pal.lzhal',0xF147,'Gas station palette',True,None),
        ('intro/gas_station2.pal.lzhal',0xF3BA,'Gas station flash palette',True,None),
    ]
    for key,at,family,compressed,size in specs:
        add(key,asm_pointer(rom,at),family,compressed,size,pointerSite=at)
    placement_table=asm_pointer(rom,0x4D464);placement_blob=bytearray();placement_rows=[]
    for i in range(6):
        pointer=int.from_bytes(rom[snes_offset(placement_table,len(rom))+i*4:snes_offset(placement_table,len(rom))+i*4+4],'little')
        start=at=snes_offset(pointer,len(rom));entries=[]
        while rom[at]!=255:
            if at+5>len(rom)or len(entries)>=256:raise ValueError('Invalid source town icon placement')
            x,y,icon,flag=int(rom[at]),int(rom[at+1]),int(rom[at+2]),int.from_bytes(rom[at+3:at+5],'little')
            entries.append(dict(x=x,y=y,icon=icon,eventFlag=flag&32767,inverted=bool(flag&32768)))
            at+=5
        placement_blob.extend(rom[start:at+1]);placement_rows.append(dict(map=i,sourcePointer=pointer,entries=entries))
    key='town_maps/icon_placement.bin';rows.append(dict(asset=key,family='town map icon placement',importerAssigned=key in written,
                                                      sourcePointer=placement_table,sourcePointerLoadOffset=0x4D464,
                                                      sourceBytes=len(placement_blob),nativePackedBytes=len(assets[key]),
                                                      sourceSha256=art.h(placement_blob),nativeSha256=art.h(assets[key]),sourceBytesEqual=placement_blob==assets[key],maps=placement_rows))
    # The actual active icon draw pointer load remains E1F44C. Other retained
    # icon tables below are direct fixed-address source reads in this caller.
    ptr=asm_pointer(rom,0x4D44F)
    add('town_maps/icon_spritemap_ptrs.bin',ptr,'town map icon spritemap pointers',False,46,pointerSite=0x4D44F)
    for key,pointer,size in (('town_maps/icon_spritemaps.bin',0xE1F203,585),
                              ('town_maps/icon_animation_flags.bin',0xE1F47A,23),
                              ('town_maps/mapping.bin',0xEFC50F,12)):
        add(key,pointer,'town map retained icon/player tables',False,size)
    source_files=['src/game/town_map.c','src/game/overworld_palette.c','src/entity/sprite.c','src/game/battle_psi.c','src/game/maternalbound.c',
                  'asm/overworld/load_town_map_data.asm','asm/overworld/map/render_town_map_icons.asm']
    return dict(sourcePointerConsumers=rows,
                compiledTownMapBgUploadInstruction=dict(romOffset=0x4D625,bytes=rom[0x4D625:0x4D62F].hex(),transferBytes=int.from_bytes(rom[0x4D626:0x4D628],'little'),
                    meaning='LDX immediate transfer count followed by COPY_TO_VRAM3; source data tail is zero and current displayed arrangements stay below tile512.'),
                sourceIdentities={x:digest(native/x)for x in source_files},
                primaryCompilerModuleIdentities={x:digest(coilsnake/x)for x in ('coilsnake/modules/eb/CompressedGraphicsModule.py','coilsnake/modules/eb/TownMapIconModule.py','coilsnake/modules/eb/DeathScreenModule.py','coilsnake/modules/eb/SoundStoneModule.py','coilsnake/model/eb/graphics.py')},
                runtimeExecuted=False)


def donor_length_review(rom,assets,project,report):
    """Independent bounded checks for importer lengths derived from donor data."""
    songs=yaml.safe_load((project/'Music/songs.yml').read_text())
    groups=yaml.safe_load((project/'sprite_groups.yml').read_text())
    photo=yaml.safe_load((project/'photographer_cfg_table.yml').read_text())
    last=groups[max(groups)]
    palette_settings=yaml.safe_load((project/'map_palette_settings.yml').read_text())
    result=[dict(family='SPC song dataset',importer='maternalbound_audio.py:36',donorDerivedBytes=len(assets['music/dataset_table.bin']),
                 independentProjectRecords=len(songs),compiledSourceOffset=0x4F70A,
                 compatible=len(assets['music/dataset_table.bin'])==len(songs)*3,
                 meaning='Donor record span remains compatible with all pinned project songs; existing playback proof is separate.'),
            dict(family='final overworld sprite group',importer='maternalbound_graphics.py:46',assumedHeaderAndFramesBytes=25,
                 independentLastGroup=max(groups),independentLastFrameCount=last['Length'],compatible=25==9+last['Length']*2,
                 meaning='Last grouping end derives from donor-shaped assumption; pinned final group has eight frames and is compatible.'),
            dict(family='photographer configuration',importer='maternalbound_presentation.py:93',fixedSourceBytes=1984,
                 independentProjectRecords=len(photo),nativeRecordBytes=62,compatible=len(photo)*62==1984),
            dict(family='map palette settings',importer='maternalbound_graphics.py:255',independentDrawingPaletteSets=len(palette_settings),
                 meaning='Importer derives each source span from pinned project palette rows rather than donor byte length.'),
            dict(family='unreferenced battle background slots',importer='maternalbound_graphics.py:210',
                 compiledConfiguredGraphics=report['indexedGraphics']['battleBackgroundGraphics'],registryGraphics=103,
                 compiledConfiguredPalettes=report['indexedGraphics']['battleBackgroundPalettes'],registryPalettes=114,
                 meaning='Only slots beyond source configured maxima retain donor-shaped zero palette spans or empty compressed streams. No active configured background references those slots.'),
            dict(family='indexed raw palette branch',importer='maternalbound_graphics.py:237',
                 meaning='Actual raw indexed family is battle background palettes; depth-specific source lengths now take the corrected branch. Other hypothetical donor-length raw indexed families currently match zero entries.')]
    fonts=[]
    for i,name in enumerate(('main','mrsaturn','battle','tiny','large')):
        widths,gfx,stride,height=struct.unpack_from('<IIHH',rom,0x3F054+i*12)
        for ext,pointer,size in (('bin',widths,128),('gfx',gfx,128*stride)):
            key=f'US/fonts/{name}.{ext}';start=snes_offset(pointer,len(rom));raw=rom[start:start+size]
            fonts.append(dict(asset=key,sourcePointer=pointer,sourceBytes=size,packedBytes=len(assets[key]),sourceSha256=art.h(raw),
                              packedSha256=art.h(assets[key]),sourceEqual=raw==assets[key],stride=stride,height=height))
    return dict(reviewedUses=result,activeFontRecords=fonts,allBoundedCompatibilityChecksPassed=all(x.get('compatible',True)for x in result)and all(x['sourceEqual']for x in fonts),
                limits='Lengths and source bytes only; no complete story or audiovisual parity inferred from these checks.')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--coilsnake-source',type=Path,default=ROOT/'_BuildScratch/CoilSnake')
    for name in ('native-source','base-assets','redux-assets','compiled-rom','original-rom','bridge','converted-directory','project','scratch','output'):
        p.add_argument('--'+name, required=True, type=Path)
    a = p.parse_args()
    a.scratch = a.scratch.resolve()
    if a.scratch.exists():
        raise ValueError('Fresh private scratch required')
    a.scratch.mkdir(parents=True)
    sys.path.insert(0, str(a.native_source.resolve()))
    from ebtools.config import load_dump_doc
    from ebtools.parsers import PARSERS, FULL_ROM_PARSERS
    doc = load_dump_doc(a.native_source/'earthbound.yml')
    entries, _, original = builder.read_pack(a.base_assets, a.native_source/'src/data/runtime_generated/asset_ids.h')
    _, _, expected = builder.read_pack(a.redux_assets, a.native_source/'src/data/runtime_generated/asset_ids.h')
    trace = TracedAssets(original)
    read_pack = builder.read_pack
    builder.read_pack = lambda *unused: (entries, read_pack(a.base_assets,a.native_source/'src/data/runtime_generated/asset_ids.h')[1],trace)
    build_args = SimpleNamespace(**vars(a))
    build_args.output = a.scratch/'traced-regenerated.pak'
    try:
        with contextlib.redirect_stdout(io.StringIO()) as output:
            builder.build(build_args)
        (a.scratch/'build.log').write_text(output.getvalue())
    finally:
        builder.read_pack = read_pack
    build_report = json.loads(build_args.output.with_suffix('.report.json').read_text())
    registry = [name for _,name in entries]
    owners = collections.defaultdict(list)
    for row in trace.writes:
        owners[row['producer']].append(row)
    stages = []
    for name, writes in owners.items():
        assets = sorted({x['asset'] for x in writes})
        stages.append(dict(producer=name, assignmentCount=len(writes), distinctRegistryAssets=len(assets),
                           outsideRegistryAssets=[x for x in assets if x not in registry], assets=assets,
                           sizeChanges=[x for x in writes if x['oldBytes']!=x['newBytes']]))
    written = {x['asset'] for x in trace.writes}
    dump_map = collections.defaultdict(list)
    parser_counts = collections.Counter()
    for entry in doc.dumpEntries:
        path = '/'.join(x for x in (entry.subdir, entry.name+'.'+entry.extension+('.lzhal' if entry.compressed else '')) if x)
        dump_map[path].append(entry)
        parser_counts['fullRom:'+entry.extension if entry.extension in FULL_ROM_PARSERS else 'parser:'+entry.extension if entry.extension in PARSERS else 'rawCompressed' if entry.compressed else 'rawUncompressed'] += 1
    compiled = a.compiled_rom.read_bytes()
    donor = a.original_rom.read_bytes()
    untransformed = []
    for key in registry:
        if key in written:
            continue
        row = dict(asset=key, donorBytes=len(original[key]), donorSha256=art.h(original[key]))
        configs = dump_map.get(key, [])
        row['matchingOriginalDumpEntries'] = len(configs)
        if len(configs)==1:
            entry = configs[0]
            row.update(originalDumpOffset=entry.offset, originalDumpSize=entry.size, compressed=entry.compressed)
            try:
                if entry.compressed:
                    left,_,_=art.strict_decode(donor[entry.offset:])
                    right,_,_=art.strict_decode(compiled[entry.offset:])
                else:
                    left=donor[entry.offset:entry.offset+entry.size]
                    right=compiled[entry.offset:entry.offset+entry.size]
                row.update(fixedExtractionSourceEqual=left==right, originalSourceSha256=art.h(left),compiledFixedSourceSha256=art.h(right),sourceBytes=len(left))
                row['status']='fixed-extraction-source-equal' if left==right else 'fixed-extraction-source-different-review-required'
            except Exception as e:
                row.update(status='fixed-extraction-decode-failed-review-required', error=str(e))
        else:
            row['status']='derived-or-nonunique-extraction-review-required'
        untransformed.append(row)
    modules = sorted({ROOT/'tools/build_maternalbound_pack.py',*(Path(x.__code__.co_filename) for name,x in vars(builder).items() if name.startswith('convert_') and callable(x))})
    patterns = regex_inventory(modules, registry)
    rebuilt_equal = all(trace[key]==expected[key] for key in registry)
    changed = [key for key in registry if trace[key]!=original[key]]
    zero = [x for x in patterns if x.get('registrySelector') and x.get('zeroMatches')]
    presentation=relocated_presentation_inventory(compiled,trace,written,a.native_source,a.coilsnake_source)
    lengths=donor_length_review(compiled,trace,a.project,build_report)
    for row in untransformed:
        if row['asset'].startswith('psianims/'):
            row['consumerClassification']='shadowed by Redux MRPSIX01 config container; battle_psi.c psi_asset selects it before legacy families'
        elif re.fullmatch(r'overworld_sprites/banks/1[2-5]\.bin',row['asset']):
            row['consumerClassification']='shadowed by MRSPBN01 in bank11 asset; sprite.c selects its bank directory before Original bank files'
    result = dict(
        toolSha256=digest(Path(__file__)), pinnedReduxCommit=art.PIN,
        compiledRomSha256=digest(a.compiled_rom), originalRomSha256=digest(a.original_rom),
        basePackSha256=digest(a.base_assets), expectedReduxPackSha256=digest(a.redux_assets),
        regeneratedPackSha256=digest(build_args.output), regeneratedAssetsEqualToExpectedPack=rebuilt_equal,
        registrySha256=digest(a.native_source/'src/data/runtime_generated/asset_ids.h'), registryAssets=len(registry),
        importerAssignedDistinctAssets=len(written), importerAssignmentCount=len(trace.writes),
        assignedButByteIdenticalToDonor=sum(trace[key]==original[key] for key in written),
        changedBytesAssets=len(changed), unassignedDonorAssets=len(untransformed),
        converterSourceIdentities={str(path.relative_to(ROOT)):digest(path) for path in modules},
        importerStages=stages, registryRegexSelectors=patterns, silentlyZeroMatchSelectors=zero,
        sourceParserInventory=dict(parser_counts), sourceDumpEntryCount=len(doc.dumpEntries),
        unassignedDonorAssetReview=untransformed, assignmentTrace=trace.writes,
        compiledConsumerCardinalities={key:build_report[key] for key in ('sprites','fonts','windows','indexedGraphics','battleArt','title','specialText','ending','audio','psiEffects','events','world','encounters','auxiliaryTables','enemyAi','spriteVariants','expandedNaming')},
        relocatedPresentationSourceAudit=presentation,
        unassignedSourceByteDifferenceConsumers=[x['asset']for x in presentation['sourcePointerConsumers']if not x['sourceBytesEqual']and not x['importerAssigned']],
        donorDerivedLengthReview=lengths,
        extractionExtensionInventory=dict(collections.Counter(x.extension for x in doc.dumpEntries)),
        claims=dict(runtimeExecuted=False, fullConversionVerified=False, ownerWrites=False),
        limits=[
            'Assignments and regex matches prove importer execution only, not source correctness or native runtime parity.',
            'Untouched data compared at the Original extraction address is a triage result; relocated consumers may deliberately use another source address. A difference is not yet a confirmed missing conversion.',
            'Legacy registry assets may be shadowed by typed Redux containers; source consumer references must be reviewed before classifying them as intentionally shared or unused.',
            'Parser counts enumerate extraction recipes, not unique native assets; duplicate/generated entries and source-only scripts are separate from the asset registry.',
        ],
        auditPassed=rebuilt_equal and not zero and lengths['allBoundedCompatibilityChecksPassed'],
    )
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key:result[key] for key in ('auditPassed','registryAssets','importerAssignedDistinctAssets','changedBytesAssets','unassignedDonorAssets','regeneratedAssetsEqualToExpectedPack')}))
    raise SystemExit(0 if result['auditPassed'] else 1)


if __name__=='__main__':
    main()
