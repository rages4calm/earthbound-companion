# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze only the separate three-file cold file-select occupancy correction."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FILES=('src/game/game_state.c','src/game/game_state.h','src/intro/file_select.c')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('base','candidate','patch','manifest'):ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args()
    for n,v in vars(a).items():setattr(a,n,v.resolve())
    if a.patch.exists() or a.manifest.exists():raise ValueError('Fresh patch/manifest required')
    red=ROOT/'research/file-select-cold-dev18-focused-red.json';green=ROOT/'research/file-select-occupancy-dev18-private-green.json';r=json.loads(red.read_text(encoding='utf-8'));g=json.loads(green.read_text(encoding='utf-8'))
    if r['allSourceExpectedPassed'] or not r['allExternalPhoneControlsPassed'] or not g['allPassed']:raise ValueError('Required meaningful red/green controls missing')
    changed=[]
    for p in (a.candidate/'src').rglob('*'):
        if p.is_file():
            rel=p.relative_to(a.candidate).as_posix()
            if sha(p)!=sha(a.base/rel):changed.append(rel)
    if sorted(changed)!=sorted(FILES):raise ValueError('Files changed beyond three-file proposal')
    title=json.loads((ROOT/'research/title-producers-dev18-private-final-manifest.json').read_text(encoding='utf-8'))
    if any(sha(a.candidate/r['path'])!=r['candidateSha256'] for r in title['sourceChanges']):raise ValueError('Frozen title proposal changed')
    patch=[];rows=[]
    for rel in FILES:
        old=(a.base/rel).read_text(encoding='utf-8');new=(a.candidate/rel).read_text(encoding='utf-8');patch.append('diff --git a/'+rel+' b/'+rel+'\n');patch.extend(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/'+rel,tofile='b/'+rel,n=3));rows.append(dict(path=rel,baseSha256=sha(a.base/rel),candidateSha256=sha(a.candidate/rel),rootAtFreezeSha256=sha(ROOT/'native-source'/rel),rootStillBase=sha(ROOT/'native-source'/rel)==sha(a.base/rel)))
    a.patch.parent.mkdir(parents=True,exist_ok=True);a.patch.write_text(''.join(patch),encoding='utf-8',newline='')
    proofnames=('research/file-select-cold-dev18-focused-red.json','research/file-select-cold-dev18-private-preparation.json','research/file-select-cold-dev18-private-builds.json','research/file-select-occupancy-dev18-private-green.json','research/title-producers-dev18-private-final-manifest.json')
    tools=('tools/file_select_cold_qa_dev18.py','tools/file_select_occupancy_qa_dev18.py','tools/prepare_file_select_private_dev18.py','tools/freeze_file_select_private_dev18.py','tools/build_title_private_dev18.py','tools/redux_title_cold_qa_dev18.py','tools/redux_title_producers_qa_dev18.py')
    report=dict(format='private-pure-phone-file-select-final-manifest-dev18-v1',base=str(a.base),candidate=str(a.candidate),patch=dict(path=str(a.patch),sha256=sha(a.patch)),sourceChanges=rows,allOtherSrcFilesByteIdentical=True,frozenTitleProposalUnchanged=True,format16AndSaveLayoutUnchanged=sha(a.base/'src/core/state_dump.c')==sha(a.candidate/'src/core/state_dump.c'),proofs=[dict(path=p,sha256=sha(ROOT/p)) for p in proofnames],tools=[dict(path=p,sha256=sha(ROOT/p)) for p in tools],coverage=dict(focusedRedSequences=4,externalPhoneContinuousPositiveControls=4,greenWarmColdFixturePairs=len(g['results']),greenDirectPurePeekCalls=sum(len(r['purePeek']['records']) for r in g['results']),greenOccupiedNormalContinueControls=sum(r['normalPhoneContinue'] is not None for r in g['results']),twoProfilesAndBothCompleteExecutables=True),limits=['Pure peek uses existing ADD/XOR checksum implementations and first-valid-copy favourite_thing[1] source contract, not a second guessed formula. No live state loading/migration occurs in the peek.', 'Mutable unsaved file-menu side-data review is source-backed and qualified. Selected slot-choice/Copy availability warm/cold branches are tested; all file-menu phases, actual Copy/Delete transactions and missing/replaced external files are not exhaustive.', 'The three-file patch is separate from the frozen eight-file title patch. Ordinary file-slot label extended glyph loss remains a distinct source-backed gap; no global dialogue/menu encoding or save format is changed.', 'Private complete binaries/source only. Root Town Map/importer changes must be preserved when integrating these exact three files; final shipping combined binaries require refreshed controls.'],rootOrOwnerInputsModified=False)
    a.manifest.parent.mkdir(parents=True,exist_ok=True);a.manifest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(manifest=str(a.manifest),sha256=sha(a.manifest),patchSha256=sha(a.patch),sourceChanges=rows)))

if __name__=='__main__':main()
