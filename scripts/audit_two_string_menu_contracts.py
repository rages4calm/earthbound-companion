# SPDX-License-Identifier: GPL-3.0-or-later
"""Join independent source CPU contracts to immutable native menu evidence.

This report contains identities, measured values and source references only.
It reuses the checked191-file pinned graph; it does not rebuild an inventory,
modify game sources, extract a ROM/pack, or publish game payloads.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from maternalbound_dialogue import without_comments


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def references(root, relative, anchor):
    p = root / relative; lines = p.read_text(encoding='utf-8-sig').splitlines()
    found = [{'path': relative, 'line': i+1} for i, line in enumerate(lines) if anchor in line]
    if not found: raise ValueError('Missing source anchor: ' + relative + ':' + anchor)
    return found


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('cpu', 'red', 'green', 'native-source', 'redux-source', 'bridge', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--production-green', action='store_true', help='The green report links a new immutable production archive with no source-object overrides.')
    a = p.parse_args()
    if a.output.exists(): raise ValueError('Fresh output report required')
    cpu = json.loads(a.cpu.read_text(encoding='utf-8')); red = json.loads(a.red.read_text(encoding='utf-8')); green = json.loads(a.green.read_text(encoding='utf-8'))
    bridge = json.loads(a.bridge.read_text(encoding='utf-8'))
    if not cpu['completed'] or red['link']['productionObjectsRecompiledOrReplaced'] or (not a.production_green and not green['link']['privateSourceObjectOverrides']):
        raise ValueError('Require completed actual CPU, frozen red and explicit private corrected-object green')
    if a.production_green and green['link']['productionObjectsRecompiledOrReplaced']:
        raise ValueError('Production green must not replace production objects')
    if not a.production_green and red['link']['unchangedProductionLibrarySha256'] != green['link']['unchangedProductionLibrarySha256']:
        raise ValueError('Private correction must use identical frozen baseline archive')
    if a.production_green:
        expected = {relative:sha(a.native_source/relative) for relative in ('src/game/window.c','src/game/display_text_cc.c')}
        if green['link']['frozenSourceSnapshotIdentities']!=expected:
            raise ValueError('Production green source snapshot must match both authorized final menu files')
    rows = []
    for cm, rm, gm in zip(cpu['profiles'], red['profiles'], green['profiles']):
        if cm['profile'] != rm['profile'] or rm['profile'] != gm['profile'] or rm['assetsSha256'] != gm['assetsSha256']:
            raise ValueError('CPU/native profile or asset identity mismatch')
        pairs = [(c, r) for c, r in zip(cm['cases'], cm['results']) if c['kind']=='width' and c['force']==0]
        if len(pairs)!=540 or len(gm['widthRecords'])!=540: raise ValueError('Width comparison incomplete')
        widths = [{'case': c, 'actualCpu': r[2], 'native': n[4]} for (c,r),n in zip(pairs,gm['widthRecords']) if r[2]!=n[4]]
        highlight = [r[2] for c,r in zip(cm['cases'],cm['results']) if c['kind']=='highlight']
        if len(highlight)!=60 or len(gm['highlightRecords'])!=60: raise ValueError('Highlight comparison incomplete')
        hdiff = [i+1 for i,(r,n) in enumerate(zip(highlight,gm['highlightRecords'])) if r!=n[3]]
        menu = [r for c,r in zip(cm['cases'],cm['results']) if c['kind']=='menu']
        if any(r[2:5]!=[1,1,1] for r in menu): raise ValueError('Actual source menu defaults differ')
        if any(r[3:6]!=[1,1,1] for r in gm['operandRecords']): raise ValueError('Private correction does not match source defaults')
        if any(r[8] or r[9] for r in gm['renderRecords']) or any(r[3] or r[4] or r[5]!=r[6] for r in gm['multirowRecords']):
            raise ValueError('Corrected rendering/indent corpus still differs')
        realred = [r for r in rm['packedSelectionRecords'] if r[0]==0]; realgreen = [r for r in gm['packedSelectionRecords'] if r[0]==0]
        if len(realred)!=2 or len(realgreen)!=2 or any(r[7:]!=[0,0] for r in realred) or any(r[7:]!=[1,1] for r in realgreen):
            raise ValueError('Real packed-choice confirmation sound proof changed')
        rows.append({'profile':cm['profile'],'actualCpuCounts':cm['counts'],'fontWidthCases':540,'fontWidthMismatches':widths,
                     'actualCpuHighlightSetClearCases':60,'highlightMismatchIndices':hdiff,
                     'frozenRenderLossCases':rm['leftLabelPixelLossCases'],'privateCorrectedRenderLossCases':gm['leftLabelPixelLossCases'],
                     'multirowPageIndentCases':30,'frozenMultirowDifferences':sum(r[3]!=0 for r in rm['multirowRecords']),
                     'privateCorrectedMultirowDifferences':0,'packedChoiceConfirmCases':2,'frozenConfirmSfxCalls':0,'privateCorrectedConfirmSfxCalls':2,
                     'originalModeExtendedApiIsNativeRegressionOnly':cm['profile']=='original'})
    source_calls = []
    for row in bridge['sourceGraph']['files']:
        path = a.redux_source / row['path']
        if sha(path).upper()!=row['sha256'].upper(): raise ValueError('Pinned source changed: '+row['path'])
        for i,line in enumerate(without_comments(path.read_text(encoding='utf-8-sig')).splitlines()):
            if re.search(r'\bcall\(data_36\.l_0xc7dd4f\)',line): source_calls.append({'path':row['path'],'line':i+1})
    native_hits=[]
    for path in (a.native_source/'src').rglob('*'):
        if path.suffix not in ('.c','.h') or 'vendor' in path.parts: continue
        for i,line in enumerate(path.read_text(encoding='utf-8').splitlines()):
            if 'right_label' in line: native_hits.append({'path':path.relative_to(a.native_source).as_posix(),'line':i+1,'usage':'write' if 'memcpy(item->right_label' in line else 'declaration' if re.search(r'char right_label\[',line) else 'read'})
    writes=[r for r in native_hits if r['usage']=='write']
    if len(writes)!=1 or writes[0]['path']!='src/game/display_text_cc.c': raise ValueError('Review changed right-label writer graph')
    proposal = {
        'files':['src/game/window.c','src/game/display_text_cc.c'],
        'changes':['Set type/page/sound_effect=1 only for CC19-created items, preserving generic native menu userdata/type semantics.',
                   'Draw right labels in a second pass using SET_TEXT_PIXEL_POSITION screen coordinates; save/clear/restore VWF indent exactly as the pinned helper does.'],
        'genericAddMenuItemUnchanged':True,'virtualInventoryUserdataPreserved':True,
        'wideRightStringBoundsFallback':'Existing native width>edge clamp to0 retained; oversized-label source underflow is not proven useful gameplay behavior.',
        'remainingBoundaryQualification':'Pinned dispatcher caps right text at30; native safe buffer accepts31. No active named caller established, and this bounded dormant API difference is outside the approved narrow correction.'}
    report={'format':'two-string-menu-source-native-review-v1','status':'actual-production-green' if a.production_green else 'source-corrected-private-green-production-freeze-pending',
            'evidenceInputs':{str(v):sha(v) for v in (a.cpu,a.red,a.green,a.bridge)},'toolSha256':sha(Path(__file__)),
            'unchangedFrozenArchive':red['link']['unchangedProductionLibrarySha256'],'privateCorrectedObjects':green['link']['privateSourceObjectOverrides'],
            'greenArchiveSha256':green['link']['unchangedProductionLibrarySha256'],'greenUsesPrivateObjectOverrides':not a.production_green,
            'comparisons':rows,'sourceRefs':{
                'defaults':references(a.native_source,'asm/text/menu/add_menu_option.asm','LDA #1'),
                'screenPosition':references(a.native_source,'asm/text/set_text_pixel_position.asm','SET_TEXT_PIXEL_POSITION:'),
                'sourceRightPass':references(a.redux_source,'ccscript/essential/cc_load_two_str.ccs','JSL(SET_TEXT_PIXEL_X)'),
                'sourceCommonChoiceBuilder':references(a.redux_source,'ccscript/data/data_36.ccs','l_0xc7dd4f:'),
                'sourceCommonChoiceSelection':references(a.redux_source,'ccscript/data/data_36.ccs','l_0xc7dd5e:'),
                'nativeOrdinaryInterpreter':references(a.native_source,'src/game/display_text.c','case 0x19: cc_19_dispatch(r);'),
                'nativeConfirm':references(a.native_source,'src/game/window.c','play_sfx(sel->sound_effect);')},
            'commonChoicePinnedCallSites':source_calls,'commonChoicePinnedCallCount':len(source_calls),
            'rightStringGraph':{'onlyNativeWriter':writes[0],'allNativeOccurrences':native_hits,
                               'extendedNamedPinnedInvocations':red['extendedMacroInvocations'],
                               'claim':'The extended macro API has no named source calls and no separate direct native C member writer. Whole-window/menu state copy or deserialization can retain previous API-populated strings. Raw encoded invocation/save reachability has not been exhaustively proved absent.'},
            'productionImplementation':proposal,'productionCSourceChangedOnlyByAuthorizedLease':True,
            'fullPlaythroughVerified':False,'fullMenuSourceParityVerified':False,
            'limits':['Real installed Original common entry0x17654B and Redux source alias0xC7DD4F are read unwrapped; CC19 loads and CC1C07 layouts execute production functions. Prepared SM_MAIN primed input phase then confirms the two actual choices.',
                      'Full choice parent/story and initial overworld setup/navigation are excluded; exploratory uninitialized full-frame setup timed out and is not credited as passing coverage.',
                      'Right-string raster references use the native existing screen-position API, independently qualified by actual full source CPU position chains, real font widths and actual Redux right-edge helper.',
                      'Original has no source two-string API. Those90 raster/30 multirow cases are native adapter regression controls; only Redux source contracts establish extended behavior.',
                      'Highlight CPU fixtures initialize both retail word-indexed and Redux byte-indexed existence entries; the earlier incomplete prerequisites are not a native defect.',
                      'No full SNES glyph raster comparison, hover script execution, cold restored menu continuation, all labels/fonts/width boundaries, or frontend/controller hardware input claim.',
                      ('Actual production green links the final immutable archive without source-object overrides. Broader sanitizer/subsystem regression remains root-owned.' if a.production_green else 'Private corrected green replaces exactly two objects in a copied frozen archive. Final combined production build and sanitizer regression remain root-owned.')]}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'commonChoicePinnedCallCount':len(source_calls),'comparisons':[{k:v for k,v in r.items() if k in ('profile','fontWidthCases','fontWidthMismatches','actualCpuHighlightSetClearCases','highlightMismatchIndices','privateCorrectedRenderLossCases','privateCorrectedMultirowDifferences')} for r in rows]}))


if __name__=='__main__': main()
