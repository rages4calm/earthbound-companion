# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze eight title-only source diffs and exact private proof identities."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
FILES=('src/game/battle.c','src/game/battle_psi.c','src/game/display_text.c','src/game/display_text_cc.c','src/game/display_text_menus.c','src/game/text.c','src/game/text.h','src/game/window.h')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('base','candidate','patch','manifest'):ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args()
    for n,v in vars(a).items():setattr(a,n,v.resolve())
    if a.patch.exists() or a.manifest.exists():raise ValueError('Fresh patch/manifest required')
    proof_names=('research/title-cold-dev18-private-fivefile-red.json','research/title-producers-dev18-private-preparation.json','research/title-producers-dev18-private-builds.json','research/title-producers-dev18-private-cold-green.json','research/title-producers-dev18-private-direct-green.json','research/title-producers-dev18-private-menu-parents-green2.json')
    proofs=[dict(path=p,sha256=sha(ROOT/p)) for p in proof_names]
    for p in proof_names[3:]:
        if not json.loads((ROOT/p).read_text(encoding='utf-8'))['allPassed']:raise ValueError('Private proof is not green: '+p)
    changed=[]
    for p in (a.candidate/'src').rglob('*'):
        if p.is_file():
            rel=p.relative_to(a.candidate).as_posix()
            if sha(p)!=sha(a.base/rel):changed.append(rel)
    if sorted(changed)!=sorted(FILES):raise ValueError('Source changes outside eight title files')
    strip=lambda t:re.sub(r'/\*.*?\*/|//[^\n]*','',t,flags=re.S)
    if strip((a.base/'src/game/window.h').read_text(encoding='utf-8'))!=strip((a.candidate/'src/game/window.h').read_text(encoding='utf-8')):raise ValueError('WindowInfo tokens changed')
    if sha(a.base/'src/core/state_dump.c')!=sha(a.candidate/'src/core/state_dump.c'):raise ValueError('Save schema changed')
    patch=[];rows=[];calls=[]
    for rel in FILES:
        old=(a.base/rel).read_text(encoding='utf-8');new=(a.candidate/rel).read_text(encoding='utf-8')
        patch.append('diff --git a/'+rel+' b/'+rel+'\n')
        patch.extend(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/'+rel,tofile='b/'+rel,n=3))
        rows.append(dict(path=rel,baseSha256=sha(a.base/rel),candidateSha256=sha(a.candidate/rel),rootAtFreezeSha256=sha(ROOT/'native-source'/rel),rootStillBase=sha(ROOT/'native-source'/rel)==sha(a.base/rel)))
    for p in (a.candidate/'src').rglob('*.c'):
        rel=p.relative_to(a.candidate).as_posix()
        for line,text in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
            if 'set_window_title(' in text and not text.lstrip().startswith('void set_window_title('):
                calls.append(dict(path=rel,line=line,sourceCall=text.strip(),classification='unchanged literal ASCII' if re.search(r'set_window_title\([^,]+,\s*"',text) else 'title-only source encoding'))
    if len(calls)!=16:raise ValueError('Title call graph changed; review every caller')
    a.patch.parent.mkdir(parents=True,exist_ok=True);a.patch.write_text(''.join(patch),encoding='utf-8',newline='')
    tools=('tools/prepare_title_producers_private_dev18.py','tools/build_title_private_dev18.py','tools/redux_title_cold_qa_dev18.py','tools/redux_title_producers_qa_dev18.py','tools/redux_title_menu_parents_dev18.py','tools/freeze_title_producers_dev18.py','tools/redux_naming_qa.py','tools/redux_recovery_qa.py','tools/check_jev_observer_parity.py','tools/build_maternalbound_pack.py')
    report=dict(format='private-complete-title-producer-proposal-manifest-dev18-v1',base=str(a.base),candidate=str(a.candidate),sourceChanges=rows,patch=dict(path=str(a.patch),sha256=sha(a.patch)),allOtherSrcFilesByteIdentical=True,windowInfoDeclarationTokensUnchanged=True,format16SourceUnchanged=True,titleCallGraph=calls,sourceCallGraphLimit='All sixteen direct native set_window_title call sites are accounted for: twelve source-title conversions and four unchanged ASCII literal sites. This is title-only accounting, not every name display or all Redux hooks.',proofs=proofs,tools=[dict(path=p,sha256=sha(ROOT/p)) for p in tools],coverage=dict(directProducerCasesPerBuild={'original':103,'redux':559},completeExecutableGoodsColdContinuations=4,completeExecutablePaulaSourceEntryColdContinuations=2,ordinaryEquipmentStatusColdParents=8,originalAsciiControls=True,oldLossyCapturedTitlesAutomaticallyRecovered=False,fullStoryVerified=False),limits=['Private complete proposed player/observer and matching archives only; root integration/shipping binaries require their own final identity checks.', 'Original source raw title contracts and actual converted fonts define glyph identity. Independent font compositor and same-renderer raw controls do not constitute a complete untouched original CPU text-rendering oracle.', 'Existing saves keep format16 and WindowInfo byte layout. Previously captured question-mark titles cannot recover lost title bytes until the source menu/title is reopened; stored character names remain intact.', 'Source syntax/caller accounting is separate from measured behavior; direct producer prerequisites are prepared, selected ordinary parents are exercised, and no whole-story/all-UI/full-Redux parity is claimed.'],rootOrOwnerInputsModified=False)
    a.manifest.parent.mkdir(parents=True,exist_ok=True);a.manifest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(manifest=str(a.manifest),sha256=sha(a.manifest),patchSha256=sha(a.patch),sourceChanges=rows)))

if __name__=='__main__':main()
