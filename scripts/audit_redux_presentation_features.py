# SPDX-License-Identifier: GPL-3.0-or-later
"""Source-backed review of six active Redux presentation/audio modules.

Checks the pinned compiler output and reproduces selected converters in memory.
The report contains hashes, addresses, references and bounded QA evidence only;
it never writes ROM, asset, soundtrack or save data. A mapped patch is a review
unit, not proof that every gameplay path using it has been executed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REVISION = '897d00833f4a08a0a92f106abf631629a6a6a041'
HOOKS = {
    'Bowspr': ('C2F8F9','C01D82','C08139','C085D3','C085EC','C085FE',
               'C085CE','C085D9','C0866C','C085F6','C0DB1D','C0FFE0'),
    'm3sprites': ('C2C544','C2C3A4','C2C75B','C29302','C29388','C229FF',
                  'C22907','C18B80','C2044C','C21404','C2FFCC','C2026E',
                  'C20295','C2DD9A','C1DDCE','C1DDD5','C2617D','C04A83','C12CAB'),
    'm2_title_screen_movements': ('EF04E9','EF04F1','C42286','C0EDF6'),
    'optimize_text_rendering': ('C44B3A','C44E61'),
    'multichar_bike': ('C3E0C8','C3E100','C02C71','C0B7D0','C051F0','C3EE4F',
                      'C078F2','C03C66','C03C8E','C03CBD','C03D25','C03D63'),
    'msu1': ('C4FBF4','C4FD12','C0AC0C','C0834E'),
}


def sha(data): return hashlib.sha256(data).hexdigest().upper()


def strip_comments(text):
    """Preserve line numbers while removing CCS source comments."""
    text=re.sub(r'/\*.*?\*/',lambda m:'\n'*m.group().count('\n'),text,flags=re.S)
    return re.sub(r'//[^\n]*','',text)


def reference(path, needle, project=False):
    content=path.read_text(encoding='utf-8')
    lines=content.splitlines()
    found=[i+1 for i,line in enumerate(lines) if needle in line]
    if not found: raise ValueError(f'Reviewed semantic reference changed: {path.name}: {needle}')
    line=found[0]
    if project:
        return {'path':'Project/ccscript/redux/'+path.name,'line':line,
                'url':f'https://github.com/ShadowOne333/MaternalBound-Redux/blob/{REVISION}/Project/ccscript/redux/{path.name}#L{line}'}
    return {'path':path.relative_to(ROOT).as_posix(),'line':line}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',type=Path,default=ROOT/'_BuildScratch/MaternalBound-Redux/Project')
    p.add_argument('--compiled-rom',type=Path,default=ROOT/'_BuildScratch/MaternalBound-Redux/Mother 2.sfc')
    p.add_argument('--bridge',type=Path,default=ROOT/'research/maternalbound-native-bridge.json')
    p.add_argument('--original-assets',type=Path,required=True)
    p.add_argument('--redux-assets',type=Path,required=True)
    p.add_argument('--native-source',type=Path,default=ROOT/'native-source')
    p.add_argument('--output',type=Path,default=ROOT/'research/redux-presentation-feature-review.json')
    for name in ('ui-results','observer-ui-results','baseline-ui-results','audio-results','scene-results','selftests'):
        p.add_argument('--'+name,type=Path)
    a=p.parse_args()
    project,native=a.project.resolve(),a.native_source.resolve()
    revision=subprocess.check_output(['git','-C',str(project.parent),'rev-parse','HEAD'],text=True).strip()
    if revision!=REVISION: raise ValueError('Active Redux source is not the reviewed revision.')
    bridge=json.loads(a.bridge.read_text(encoding='utf-8-sig'))
    if bridge['source']['revision']!=REVISION: raise ValueError('Bridge source revision differs.')
    rom=a.compiled_rom.read_bytes()
    if sha(rom)!=bridge['roms']['compiled']['sha256'].upper(): raise ValueError('Compiled ROM differs from bridge.')
    source={}
    modules=[]
    for name,wanted in HOOKS.items():
        path=project/'ccscript/redux'/f'{name}.ccs'
        text=path.read_text(encoding='utf-8')
        pinned=subprocess.check_output(['git','-C',str(project.parent),'show',f'{REVISION}:Project/ccscript/redux/{name}.ccs']).decode('utf-8')
        if text.replace('\r\n','\n')!=pinned.replace('\r\n','\n'):
            raise ValueError(f'Module differs from pinned source: {name}')
        clean=strip_comments(text)
        defines={k:int(v,16) for k,v in re.findall(r'define\s+(\w+)\s*=\s*(0x[0-9A-Fa-f]+)',clean)}
        writes=[]
        for match in re.finditer(r'ROM\[\s*(0x[0-9a-fA-F]+|\w+)\s*\]\s*=',clean):
            expression=match.group(1)
            address=int(expression,16) if expression.lower().startswith('0x') else defines.get(expression)
            if address is None: raise ValueError(f'Unresolved literal write: {name}: {expression}')
            writes.append({'address':f'{address:06X}','sourceLine':clean[:match.start()].count('\n')+1})
        if sorted(x['address'] for x in writes)!=sorted(wanted):
            raise ValueError(f'Active ROM-write inventory changed: {name}: {writes}')
        compiled=next(x for x in bridge['modules'] if x['name']==name)
        body=rom[compiled['rom_offset']:compiled['rom_offset']+compiled['size']]
        if len(body)!=compiled['size'] or sha(body)!=compiled['compiled_sha256'].upper():
            raise ValueError(f'Compiled module slice differs: {name}')
        source[name]=path
        modules.append({'name':name,'pinnedSourceSha256':sha(pinned.replace('\r\n','\n').encode()),
                        'compiledModuleBytes':compiled['size'],'compiledModuleSha256':sha(body),
                        'activeLiteralWrites':writes})

    # Regenerate into a private in-memory dictionary and compare the native
    # pack. The pointer/layout checks in these production converters remain
    # enabled, including every movement root and exact private helper body.
    sys.path.insert(0,str(native))
    from build_maternalbound_pack import read_pack
    from maternalbound_presentation import convert_title
    from maternalbound_graphics import convert_fonts
    from maternalbound_events import convert_events
    ids=native/'src/data/runtime_generated/asset_ids.h'
    _,_,donor=read_pack(a.original_assets,ids)
    _,_,installed=read_pack(a.redux_assets,ids)
    conversions=[]
    for name,converter in (('title',lambda:convert_title(rom,donor)),
                           ('fonts',lambda:convert_fonts(rom,donor)),
                           ('movement',lambda:convert_events(rom,bridge,donor))):
        result=converter()
        families=[]
        for key in result['assets']:
            if donor[key]!=installed[key]: raise ValueError(f'Native pack conversion mismatch: {key}')
            families.append({'name':key,'bytes':len(donor[key]),'sha256':sha(donor[key])})
        conversions.append({'family':name,'matchedPackAssets':families,
                            'converterValidation':{k:v for k,v in result.items() if k!='assets'}})

    # Compare whether tracks loop, independently of the PCM header's loop
    # address. The source table also contains extended IDs beyond this pack.
    msu_clean=strip_comments(source['msu1'].read_text(encoding='utf-8'))
    table=msu_clean.split('track_table:',1)[1]
    flags=[int(x,16) for row in re.findall(r'"\[([^\]]+)\]"',table) for x in row.split()]
    if len(flags)!=256 or any(x not in (1,3) for x in flags): raise ValueError('Unexpected MSU repeat table.')
    msu_native=native/'port/unix/platform/msu_audio.c'
    native_one_shots=[int(x) for x in re.findall(r'\d+',msu_native.read_text().split('one_shots[] = {',1)[1].split('};',1)[0])]
    if native_one_shots!=[i for i,flag in enumerate(flags) if flag==1]:
        raise ValueError('Native track loop policy differs from source.')

    # Machine assertions tie the materially changed source bytes to the
    # native semantics reviewed below. They are intentionally separate from
    # runtime evidence: a passing string assertion alone is not a feature test.
    for address,expected in ((0xC2026E,b'\xA0\xB2\x80'),(0xC20295,b'\xA0\xB2\x80'),
                             (0xC2DD9A,b'\x80\x00\x80\x00'),
                             (0xC3E0C8,(0x1EEEE).to_bytes(4,'little')),
                             (0xC3E100,(0x165D5).to_bytes(4,'little'))):
        offset=address-0xC00000
        if rom[offset:offset+len(expected)]!=expected:
            raise ValueError(f'Reviewed patch operand differs at {address:06X}')

    def upstream(module,needle): return reference(source[module],needle,True)
    def code(path,needle): return reference(native/path,needle)
    def binding(module,addresses,meaning,refs,adaptation=None,remaining=None):
        result={'module':module,'writes':addresses,'sourceMeaning':meaning,'nativeReferences':refs,
                'evidenceLevel':'semantic-code-review-and-compiled-source-check'}
        if adaptation: result['platformAdaptation']=adaptation
        if remaining: result['unverifiedLiveBranches']=remaining
        return result
    bs='src/game/maternalbound_battle_sprites.c'
    bindings=[
        binding('Bowspr',list(HOOKS['Bowspr']),
            'Custom battle object rendering, priority and SNES tile/palette/DMA allocation.',
            [upstream('Bowspr','ROM[0xC2F8F9]'),code(bs,'bool maternalbound_battle_sprites_line'),
             code(bs,'priority[x]=4')],
            'Active m3sprites consumer uses priority0. The native scanline compositor reads normalized sprite frames directly and overlays enemy OBJ while BG3 text retains higher priority. General Bowspr priorities1..3, sorting, VRAM/DMA thresholds and palette allocation are not ported APIs because the active consumer does not need them.',
            ['Full overlap/palette comparison for all enemy/front-row/back-row combinations.']),
        binding('m3sprites',['C2044C','C21404','C2FFCC'],
            'Keep battle HP/PP boxes and odometers at row19 regardless of selected member.',
            [upstream('m3sprites','handle_windows:'),code('src/game/window.c','static uint16_t hppp_row_for_character'),
             code('src/game/window.c','void update_hppp_meter_tiles')]),
        binding('m3sprites',['C2026E','C20295'],
            'Relocate AUTO clear/render operand from RAM8272 to80B2.',
            [upstream('m3sprites','ROM[0xC2026E]'),code('src/game/window.c','? 0x2B4')],
            'Original BG2-buffer base7DFE maps RAM80B2 to native offset2B4, row10 column26; the original offset474 remains row17 column26.'),
        binding('m3sprites',['C2DD9A'],
            'Remove only off-phase UNDRAW_HP_PP_WINDOW call; leave duration and redraw behavior intact.',
            [upstream('m3sprites','ROM[0xC2DD9A]'),code('src/game/battle_ui.c','if (!maternalbound_enabled())')]),
        binding('m3sprites',['C1DDCE','C1DDD5','C12CAB'],
            'Animate selected party portraits and raise conscious members during victory.',
            [upstream('m3sprites','new_raise_routine:'),upstream('m3sprites','you_won_ram_set:'),
             code(bs,'bool wanted=s->victory'),code('src/game/battle.c','maternalbound_battle_sprites_victory();')],
            'Native frames use their own four-member visibility masks and y168-to152 anchors rather than free_ram bits and Bowspr objects.'),
        binding('m3sprites',['C2617D','C04A83'],
            'Clear portrait state before new encounters and after battle exit.',
            [upstream('m3sprites','before_battle_hj:'),code(bs,'void maternalbound_battle_sprites_reset'),
             code('src/game/battle.c','Redux before_battle_hj'),code(bs,'!bt.battle_mode_flag')],
            'Explicit shared BTL_BEGIN reset hardens prepared stale/cold checkpoints. Natural sequential battles already cleared state in baseline; this is not a naturally reproduced user crash.'),
        binding('m3sprites',['C2C544','C2C3A4','C2C75B','C29302','C29388','C229FF','C22907','C18B80'],
            'Reset/rebuild Bowspr allocation during Giygas scenes, Poo return, temporary-party changes, and defer teddy reward updates.',
            [upstream('m3sprites','giygas_fix_1:'),upstream('m3sprites','barf_fix_1:'),
             upstream('m3sprites','special_fix_1:'),code(bs,'static uint16_t character_group'),
             code('src/game/inventory.c','static void update_teddy_bear_party')],
            'The direct PC compositor has no shared SNES Bowspr entity/VRAM allocation to end or rebuild; it reads current battlers, character mode and controlled-party count each frame. Native inventory still performs teddy updates immediately, so the source deferral is not literally reproduced.',
            ['Giygas prayer/phase5/death portrait hiding/reset timing.',
             'Master Barf live Poo-joins encounter and portrait repositioning.',
             'Flying Man/teddy death and teddy-as-battle-reward party refresh.']),
        binding('m2_title_screen_movements',list(HOOKS['m2_title_screen_movements']),
            'Title letter movement, timed reveal, glowing Mother/2 palettes and no transient blank/reload on A.',
            [upstream('m2_title_screen_movements','ROM[0xEF04E9]'),
             code('src/intro/title_screen.c','StepResult mode_step_title_screen'),
             code('src/entity/callroutine.c','case 0xBF000D:'),
             code('src/entity/callroutine_palette.c','entities.var[3][offset] == 3')],
            'Eleven Script788..798 movement pointers and full relocated regions are regenerated and matched to the native pack; typed palette-copy call becomes explicit native BF000D, and var3 selects the separate gradient buffer.',
            ['Exact title frame/pixel alignment and glow cadence versus source.',
             'Press-A-at-every-reveal-phase transient blank comparison.']),
        binding('optimize_text_rendering',list(HOOKS['optimize_text_rendering']),
            'Optimized VWF blit and character width/padding handling.',
            [upstream('optimize_text_rendering','ROM[0xC44B3A]'),
             code('src/game/text.c','void blit_vwf_glyph'),code('src/game/text.c','void vwf_render_character')],
            'The native renderer performs glyph masking, row/bitplane writes, tile-boundary clearing, and width+padding advances in C. It does not reproduce 65816 cycle optimizations. Five fonts with128 glyphs each are regenerated and byte-matched to the native pack.',
            ['All glyphs/fonts at every pixel offset, wide-glyph strip and tile-boundary pixel comparison.']),
        binding('multichar_bike',list(HOOKS['multichar_bike']),
            'Leader-aware sidecar sprites, follower hiding, faster bike speeds, post-battle/death/revive/mushroom refresh.',
            [upstream('multichar_bike','Post_Battle_Refresh:'),code('src/game/overworld.c','void get_on_bicycle'),
             code('src/game/overworld.c','static void maternalbound_refresh_bicycle'),
             code('src/game/position_buffer.c','cardinal=0x1EEEE;diagonal=0x165D5;')],
            'Native leader slots24..27 and sidecar groups477..480 replace assembly entity offsets. Hiding uses native DRAW_DISABLED; explicit refresh rebuilds status-aware party entities. Single-party Ness bike7 behavior is also in the active source.',
            ['All temporary-party compositions, sectors/doors/indoor dismounts and post-battle audio/story combinations.']),
        binding('msu1',list(HOOKS['msu1']),
            'MSU music request/stop/fades with SPC fallback and source loop policy.',
            [upstream('msu1','setFadeFlag:'),upstream('msu1','track_table:'),
             code('port/unix/platform/msu_audio.c','void pc_msu_command'),
             code('src/game/audio.c','platform_audio_msu_play')],
            'SDL PCM mixing replaces SNES MSU registers and NMI. Source256-track repeat flags match exactly. Native fades are continuous audio-sample ramps: fast240/255 per second, slow120/255, quarter/full180/255; source uses per-NMI integer steps and cutoff thresholds. Audible fade duration can differ slightly; bit-exact NMI envelope parity is not claimed.',
            ['Listening to every soundtrack and sound effect.',
             'Every story/bicycle/boss transition and extended IDs192..255 playback.',
             'Exact per-frame fade-envelope comparison.']),
    ]
    covered={name:[] for name in HOOKS}
    for group in bindings: covered[group['module']]+=group['writes']
    for name,values in covered.items():
        if sorted(values)!=sorted(HOOKS[name]): raise ValueError(f'Unreviewed or duplicate literal patch in {name}')
    evidence={}
    for key in ('ui_results','observer_ui_results','baseline_ui_results','audio_results','scene_results'):
        path=getattr(a,key)
        if path:
            report=json.loads(path.read_text(encoding='utf-8-sig'))
            if report['packSha256'].upper()!=sha(a.redux_assets.read_bytes()):
                raise ValueError(f'Runtime evidence used a different Redux pack: {key}')
            if key in ('ui_results','observer_ui_results') and not report['fixedExpectationsEnforced']:
                raise ValueError(f'Fixed runtime assertions were not enforced: {key}')
            evidence[key]={'reportSha256':sha(path.read_bytes()),'nativeExeSha256':report['nativeExeSha256'],
                           'report':report}
    if a.selftests:
        evidence['selftests']=json.loads(a.selftests.read_text(encoding='utf-8-sig'))
    ui=evidence.get('ui_results',{}).get('report')
    observer=evidence.get('observer_ui_results',{}).get('report')
    if ui and observer and ui['rows']!=observer['rows']:
        raise ValueError('Player/observer semantic UI observations differ.')
    native_paths={ref['path'] for group in bindings for ref in group['nativeReferences'] if 'url' not in ref}
    output={
        'format':'redux-presentation-feature-review-v1','status':'bounded-source-and-runtime-audit',
        'sourceRevision':REVISION,'compiledRomSha256':sha(rom),
        'originalPackSha256':sha(a.original_assets.read_bytes()),'reduxPackSha256':sha(a.redux_assets.read_bytes()),
        'counts':{'reviewedModules':6,'activeLiteralWrites':sum(len(x) for x in HOOKS.values()),
                  'matchedConvertedAssets':sum(len(x['matchedPackAssets']) for x in conversions),
                  'sourceLoopFlagsChecked':len(flags)},
        'modules':modules,'convertedDataChecks':conversions,'semanticBindings':bindings,
        'nativeReferenceFileHashes':[{ 'path':path,'sha256':sha((ROOT/path).read_bytes())} for path in sorted(native_paths)],
        'fixedSourceGaps':[
            {'feature':'Stationary Redux battle HP/PP boxes and odometer rows',
             'baseline':'Selected member top row18/digit row21; other members19/22.',
             'fixed':'All members top row19/digit row22 through real menus and rolling updates.'},
            {'feature':'Redux AUTO indicator placement and cancellation',
             'baseline':'Rendered at row17 column26.',
             'fixed':'Rendered at row10 column26; B cancellation clears the same location through a subsequent real battle text push.'},
            {'feature':'Redux damage box blink suppression',
             'baseline':'Off phase undraws the damaged HP/PP box.',
             'fixed':'Redux retains its box during the same off phase; Original still undraws.'},
            {'feature':'Explicit portrait reset on cold shared battle entry',
             'baseline':'Prepared stale victory survives BTL_BEGIN, raises all4 portraits despite Ness selection.',
             'fixed':'Shared BTL_BEGIN reset removes prepared victory; only selected Ness is raised.',
             'qualification':'Natural exit/new-entry also passed baseline. Prepared state hardening is not a naturally reproduced user bug.'},
        ],
        'msuSourcePolicy':{'repeatFlags':256,'oneShotIds':native_one_shots},'runtimeEvidence':evidence,
        'playerObserverUiObservationsMatch':bool(ui and observer),
        'scopeLimits':[
            'Literal patch coverage and converter byte matches do not establish full story or visual/audio parity.',
            'This review covers six active modules at the pinned revision; other Redux modules are reviewed separately.',
            'No source hook is considered implemented merely because a symbol or label exists.',
            'Remaining branches listed above are unverified, rather than silently classified as passed.',
            'Prepared fixture mutations are scratch-only and do not represent owner story progress.',
            'Report contains hashes/references only; no ROM, graphics, PCM, asset pack or save data is included.',
        ]}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(a.output),'counts':output['counts'],'evidence':list(evidence)},indent=2))


if __name__=='__main__': main()
