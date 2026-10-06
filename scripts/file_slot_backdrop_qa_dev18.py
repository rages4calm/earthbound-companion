# SPDX-License-Identifier: GPL-3.0-or-later
"""Reach the second file-slot producer through real new-game cancellation.

Copies only the latest real capture and unchanged phone bytes from separately
reported actual empty-slot controls. No modes, windows, labels or VRAM edits.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
from check_jev_observer_parity import latest, local_scratch
import redux_title_cold_qa_dev18 as qa
import file_slot_glyph_qa_dev18 as glyph

ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('source','builds','runtime','parent-scratch','parent-report','original-assets','redux-assets','scratch','output'):
        ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args()
    for n,v in vars(a).items():setattr(a,n,v.resolve())
    a.scratch=local_scratch(a.scratch)
    if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch/report required')
    a.scratch.mkdir();sys.path.insert(0,str(a.source/'src/vendor/tamp'));import tamp
    l=glyph.compile_layout(a.source,a.builds/'player',a.scratch);parent=json.loads(a.parent_report.read_text(encoding='utf-8'));results=[]
    for mode in ('player','observer'):
        exe=a.runtime/(mode+'.exe')
        if qa.sha(exe)!=qa.sha(a.builds/mode/'earthbound.exe'):raise ValueError('Immutable full executable mismatch')
        for profile,pack in [('original',a.original_assets),('redux',a.redux_assets)]:
            label='one-six-two-empty' if profile=='redux' else 'one-ascii-two-empty'
            row=next(r for r in parent['results'] if r['build']==mode and r['profile']==profile and r['case']==label)
            old=a.parent_scratch/(mode+'-'+profile+'-'+label)/'actual-slot-list'
            previous=latest(old)
            if row['executableSha256']!=qa.sha(exe) or row['packSha256']!=qa.sha(pack):raise ValueError('Parent source identity differs')
            session=glyph.Session(exe,pack,a.scratch/(mode+'-'+profile),l,tamp)
            (session.folder/'saves').mkdir();shutil.copy2(previous,session.folder/'saves/quicksave_1.bin.0');shutil.copy2(old/'fixture.srm',session.folder/'fixture.srm');phone=qa.sha(session.folder/'fixture.srm')
            _,_,assets=qa.read_pack(pack,a.source/'src/data/runtime_generated/asset_ids.h');session.qa_assets=assets
            session.step('actual-empty-slot-cascade-before-naming',wait=25)
            stages=[]
            for attempt in range(12):
                stages.append(dict(modes=session.last['modes'],activeWindows=[r['id'] for r in session.last['titles']]))
                if session.last['keyboard']:break
                session.step('actual-confirm-new-game-cascade-'+str(attempt),[qa.naming.CONFIRM],wait=65)
            if not session.last['keyboard'] or session.last['keyboard']['target']!=0:raise ValueError('Actual first naming keyboard not reached')
            session.clear();session.step('actual-back-out-first-name-empty-buffer',[qa.naming.B],wait=90)
            warm=glyph.observe(session,row['preparedNames'])
            if not any(r['id']==50 for r in session.last['titles']):raise ValueError('Source FM_NG_NAMING_RESULT cancellation backdrop not reached')
            capture=qa.sha(latest(session.folder));session.step('fresh-f6-restore-naming-cancel-backdrop',wait=35);cold=glyph.observe(session,row['preparedNames']);stable=warm==cold
            flavour=next(r for r in session.last['titles'] if r['id']==50);before=flavour['currentOption'];session.step('actual-flavour-down-after-cold-backdrop',[qa.naming.DOWN],wait=40);after=next(r for r in session.last['titles'] if r['id']==50)['currentOption'];continued=glyph.observe(session,row['preparedNames'])
            sourcepass=all(r['sourceGlyphsMatch'] and r['sourceFontColumnsMatch'] for r in warm+cold+continued)
            samephone=phone==qa.sha(session.folder/'fixture.srm')
            result=dict(build=mode,profile=profile,executableSha256=qa.sha(exe),archiveSha256=qa.sha(a.builds/mode/'game_lib/libearthbound_game.a'),packSha256=qa.sha(pack),parentActualCaptureSha256=qa.sha(previous),parentReportSha256=qa.sha(a.parent_report),sourceCascadeStages=stages,actualCancellationCapturedSha256=capture,warm=warm,cold=cold,freshF6LabelVramAndHighlightPreserved=stable,ordinaryFlavourCursorAfterCold=dict(before=before,after=after,moved=before!=after),externalPhoneBytesPreserved=samephone,stateVersion=session.last['stateVersion'],sourceExpectedPassed=sourcepass,Passed=sourcepass and stable and samephone and before!=after and session.last['stateVersion']==16)
            results.append(result);print(json.dumps(dict(completed=mode+'-'+profile,sourceExpectedPassed=sourcepass,Passed=result['Passed'])),flush=True)
    report=dict(format='actual-naming-cancel-file-slot-backdrop-dev18-v1',toolSha256=qa.sha(Path(__file__)),dependencies={p:qa.sha(ROOT/p) for p in ('tools/file_slot_glyph_qa_dev18.py','tools/redux_title_cold_qa_dev18.py')},results=results,allPassed=all(r['Passed'] for r in results),limits=['Real empty-slot selection and ordinary new-game setting Confirm inputs reach the first naming keyboard; erasing/default-cancel then B executes FM_NG_NAMING_RESULT and file_select_menu_display_only. No production mode/window/name/label/pixel edit or direct builder call is made.', 'Initial private slot names derive the separately reported native phone writer prerequisites; name acquisition/story progression is excluded.', 'Captured actual title/font/menu state is restored through production format16/F6 load in a fresh process; physical F6 is not synthesized.', 'Whole-screen source CPU renderer and all file-menu branches remain outside scope. Private complete builds only; root and owner files untouched.'],rootOrOwnerInputsModified=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(report=str(a.output),allPassed=report['allPassed'],sha256=qa.sha(a.output))))

if __name__=='__main__':main()
