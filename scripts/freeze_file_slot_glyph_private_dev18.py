# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze the separate two-file file-slot label proposal and actual proofs."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FILES=('src/intro/file_select.c','src/game/window.c')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('base','candidate','patch','manifest'):ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args()
    for n,v in vars(a).items():setattr(a,n,v.resolve())
    if a.patch.exists() or a.manifest.exists():raise ValueError('Fresh patch/manifest required')
    names=('research/file-slot-glyph-dev18-private-red-v2.json','research/file-slot-glyph-dev18-private-green-v2.json','research/file-slot-glyph-dev18-backdrop-red.json','research/file-slot-glyph-dev18-backdrop-green.json')
    red,green,backred,backgreen=[json.loads((ROOT/p).read_text(encoding='utf-8')) for p in names]
    if red['allPassed'] or backred['allPassed'] or not green['allPassed'] or not backgreen['allPassed']:raise ValueError('Meaningful source-backed red/green missing')
    tool=ROOT/'tools/file_slot_glyph_qa_dev18.py';backtool=ROOT/'tools/file_slot_backdrop_qa_dev18.py'
    if any(r['toolSha256']!=sha(tool) for r in (red,green)) or any(r['toolSha256']!=sha(backtool) for r in (backred,backgreen)):raise ValueError('Frozen runner identity drifted')
    changed=[]
    for p in (a.candidate/'src').rglob('*'):
        if p.is_file():
            rel=p.relative_to(a.candidate).as_posix()
            if sha(p)!=sha(a.base/rel):changed.append(rel)
    if sorted(changed)!=sorted(FILES):raise ValueError('Changes outside two-file lease')
    title=json.loads((ROOT/'research/title-producers-dev18-private-final-manifest.json').read_text(encoding='utf-8'))
    occupancy=json.loads((ROOT/'research/file-select-cold-dev18-private-final-manifest.json').read_text(encoding='utf-8'))
    if any(sha(a.candidate/r['path'])!=r['candidateSha256'] for r in title['sourceChanges']):raise ValueError('Frozen eight-file title proposal changed')
    if any(sha(a.candidate/r['path'])!=r['candidateSha256'] for r in occupancy['sourceChanges'] if r['path']!='src/intro/file_select.c'):raise ValueError('Frozen pure occupancy helper changed')
    ascii_controls=[]
    for r in green['results']:
        if r['profile']=='original' or r['case']=='width-boundary-ascii':
            old=next(v for v in red['results'] if all(v[k]==r[k] for k in ('build','profile','case')))
            unchanged=old['warm']==r['warm'] and old['cold']==r['cold'] and old['actualInputSelections']==r['actualInputSelections']
            if not unchanged:raise ValueError('Original/ASCII rendering control changed')
            ascii_controls.append(dict(build=r['build'],profile=r['profile'],case=r['case'],warmColdRenderingAndSelectionsByteIdentical=True))
    for r in backgreen['results']:
        if r['profile']=='original':
            old=next(v for v in backred['results'] if v['build']==r['build'] and v['profile']==r['profile'])
            if old['warm']!=r['warm'] or old['cold']!=r['cold']:raise ValueError('Original backdrop rendering changed')
    patch=[];changes=[]
    for rel in FILES:
        old=(a.base/rel).read_text(encoding='utf-8');new=(a.candidate/rel).read_text(encoding='utf-8')
        patch.append('diff --git a/'+rel+' b/'+rel+'\n');patch.extend(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/'+rel,tofile='b/'+rel,n=3))
        changes.append(dict(path=rel,baseSha256=sha(a.base/rel),candidateSha256=sha(a.candidate/rel),rootAtFreezeSha256=sha(ROOT/'native-source'/rel),rootStillBase=sha(ROOT/'native-source'/rel)==sha(a.base/rel)))
    a.patch.parent.mkdir(parents=True,exist_ok=True);a.patch.write_text(''.join(patch),encoding='utf-8',newline='')
    proofs=(*names,'research/file-slot-glyph-dev18-private-preparation.json','research/file-slot-glyph-dev18-private-builds.json','research/title-producers-dev18-private-final-manifest.json','research/file-select-cold-dev18-private-final-manifest.json')
    tools=('tools/prepare_file_slot_glyph_private_dev18.py','tools/file_slot_glyph_qa_dev18.py','tools/file_slot_backdrop_qa_dev18.py','tools/freeze_file_slot_glyph_private_dev18.py','tools/build_title_private_dev18.py','tools/redux_title_cold_qa_dev18.py','tools/file_select_cold_qa_dev18.py','tools/redux_title_producers_qa_dev18.py','tools/redux_naming_qa.py')
    source_refs=('asm/intro/file_select_menu.asm','asm/text/print_menu_items.asm','asm/text/set_file_select_text_highlight.asm')
    pinned_refs=('ccscript/redux/naming_screen_table.ccs','ccscript/redux/six_letters.ccs','ccscript/bugfixes/text_highlights_fix.ccs')
    report=dict(format='private-file-slot-glyph-final-manifest-dev18-v1',base=str(a.base),candidate=str(a.candidate),patch=dict(path=str(a.patch),sha256=sha(a.patch)),sourceChanges=changes,allOtherSrcFilesByteIdentical=True,frozenTitleAndPureOccupancyHelpersUnchanged=True,format16Unchanged=sha(a.base/'src/core/state_dump.c')==sha(a.candidate/'src/core/state_dump.c'),windowInfoAndMenuItemUnchanged=sha(a.base/'src/game/window.h')==sha(a.candidate/'src/game/window.h'),proofs=[dict(path=p,sha256=sha(ROOT/p)) for p in proofs],tools=[dict(path=p,sha256=sha(ROOT/p)) for p in tools],originalSourceRefs=[dict(path=p,sha256=sha(a.base/p)) for p in source_refs],pinnedReduxSourceRefs=[dict(path=p,sha256=sha(ROOT/'_BuildScratch/MaternalBound-Redux/Project'/p)) for p in pinned_refs],asciiControls=ascii_controls,coverage=dict(warmColdActualSlotListPairs=len(green['results']),slotListSourceGlyphAndIndependentVramObservations=sum(len(r['warm'])+len(r['cold']) for r in green['results']),actualSlotConfirmInputs=sum(len(r['actualInputSelections']) for r in green['results']),namingCancellationBackdropWarmColdParents=len(backgreen['results']),meaningfulRedSlotListPairs=sum(not r['Passed'] for r in red['results']),meaningfulRedNamingCancellationBackdrops=sum(not r['Passed'] for r in backred['results']),bothCompletePlayerObserverAndBothProfiles=True,allNineteenExtendedPinnedKeyboardGlyphsIncluded=True,sourceLegalSixCharacterFortyPixelBoundaryIncluded=True),limits=['A bounded reversible slot-label representation preserves high source-only EB glyphs; only file-select main slot userdata1..3 consumers decode it. Every other label and dialogue path keeps its existing ASCII contract.', 'The actual normal slot builder and naming-cancellation display-only builder are exercised with ordinary input. Names/occupied slots are private prerequisites written through native name/save APIs, not natural story progress or a new complete keyboard-entry proof.', 'Expected pixels use the packed source main-font bytes with an independent compositor. Highlight tests cover actual measured columns, trailing columns and real Confirm/cancel, but no original CPU whole-screen file-menu renderer is claimed.', 'Original and selected ASCII controls have identical warm/cold rendered source columns and selections across old/new candidate binaries. Existing already-lossy captured file-menu labels recover only after the builder reruns.', 'No new save fields, MenuItem/WindowInfo layout, asset content identity, ROM/pack or owner data changes. Complete shipping combined binaries require refreshed controls after root integration.'],rootOrOwnerInputsModified=False)
    a.manifest.parent.mkdir(parents=True,exist_ok=True);a.manifest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(manifest=str(a.manifest),sha256=sha(a.manifest),patchSha256=sha(a.patch),sourceChanges=changes,coverage=report['coverage'])))

if __name__=='__main__':main()
