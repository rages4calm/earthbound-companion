# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only focused file-select F6 warm/cold controls with identical phone data.

Uses complete immutable executables, real phone Save/menu input and real F6
capture writer. Only private phone files are copied; no serialized state edits.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
from check_jev_observer_parity import latest,local_scratch
import redux_title_cold_qa_dev18 as qa

ROOT=Path(__file__).resolve().parents[1]

def first_rows(last=800):
    result=[(0,0)]
    for f in (200,400,600,800):result.extend(((f,qa.naming.CONFIRM),(f+2,0)))
    if last>800:result.extend(((1400,qa.naming.CONFIRM),(1402,0)))
    if last>1400:result.extend(((1600,qa.naming.CONFIRM),(1602,0)))
    return result

def boot_case(exe,pack,parent,label,phone,l,tamp,rows,capture,assets):
    session=qa.Session(exe,pack,parent/label,l,tamp);session.qa_assets=assets
    shutil.copy2(phone,session.folder/'fixture.srm');before=qa.sha(session.folder/'fixture.srm')
    session.run(label,rows,capture,load=False)
    if before!=qa.sha(session.folder/'fixture.srm'):raise ValueError('Phone file changed during source menu input')
    return session

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('source','builds','runtime','original-assets','redux-assets','redux-phone-seed','scratch','output'):ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args()
    for n,v in vars(a).items():setattr(a,n,v.resolve())
    a.scratch=local_scratch(a.scratch)
    if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch/report required')
    a.scratch.mkdir();sys.path.insert(0,str(a.source/'src/vendor/tamp'));import tamp
    l=qa.layout(a.source,ROOT/'tools/mingw64/bin/gcc.exe',a.builds/'player',a.scratch);results=[]
    for mode in ('player','observer'):
        exe=a.runtime/(mode+'.exe')
        if qa.sha(exe)!=qa.sha(a.builds/mode/'earthbound.exe'):raise ValueError('Immutable complete executable mismatch')
        for profile,pack in (('original',a.original_assets),('redux',a.redux_assets)):
            parent=a.scratch/(mode+'-'+profile);parent.mkdir();_,_,assets=qa.read_pack(pack,a.source/'src/data/runtime_generated/asset_ids.h')
            if profile=='original':
                seed=qa.Session(exe,pack,parent/'ordinary-phone-seed',l,tamp);seed.qa_assets=assets;qa.new_original_world(seed)
                seed.step('actual-open-command-menu-for-phone-save',[0x80],wait=40)
                seed.step('actual-native-phone-save',[qa.naming.DOWN]*3+[qa.naming.CONFIRM],wait=50)
                seed.step('actual-return-world-after-phone-save',[qa.naming.B],wait=50)
                if seed.last['modes']!=[l['worldMode']] or seed.last['names'][0][:4]!=[0x7E,0x95,0xA3,0xA3]:raise ValueError('Actual Original phone Save prerequisites failed')
                phone=seed.folder/'fixture.srm'
            else:phone=a.redux_phone_seed
            phone_hash=qa.sha(phone)
            normal=boot_case(exe,pack,parent,'continuous-phone-continue',phone,l,tamp,first_rows(1600),2200,assets)
            if normal.last['modes']!=[l['worldMode']] or normal.last['partyCount']!=1:raise ValueError('Same-byte continuous phone Continue control failed')
            warm=boot_case(exe,pack,parent,'warm-slot-select',phone,l,tamp,first_rows(1400),1450,assets)
            cold=boot_case(exe,pack,parent,'f6-at-source-slot-select',phone,l,tamp,first_rows(),1300,assets)
            captured=dict(cold.last);before_state=latest(cold.folder);savedhash=qa.sha(before_state);shutil.copy2(before_state,cold.folder/'frozen-file-select-before-cold.bin')
            before_phone=qa.sha(cold.folder/'fixture.srm');path=str((cold.folder/'fixture.srm').resolve());cold.step('fresh-f6-restore-select-same-slot',[qa.naming.CONFIRM],wait=130)
            phone_preserved=before_phone==qa.sha(cold.folder/'fixture.srm')==phone_hash
            expected_submenu=any(r['id']==20 for r in warm.last['titles'])
            cold_submenu=any(r['id']==20 for r in cold.last['titles'])
            cold_newgame=any(r['id']==24 for r in cold.last['titles']) and cold.last['partyCount']==0 and all(not any(n) for n in cold.last['names'])
            if not expected_submenu or not phone_preserved:raise ValueError('Focused source/menu/phone controls invalid')
            results.append(dict(build=mode,profile=profile,executableSha256=qa.sha(exe),archiveSha256=qa.sha(a.builds/mode/'game_lib/libearthbound_game.a'),packSha256=qa.sha(pack),phoneSave=dict(sourcePath=str(phone),sameColdProcessPath=path,sha256=phone_hash,bytesPreservedThroughout=phone_preserved),continuousPhoneContinueControl=dict(worldModes=normal.last['modes'],partyCount=normal.last['partyCount'],names=normal.last['names'],Passed=True),warmActualSlotSelection=warm.last,beforeF6Cold=captured,afterF6Cold=cold.last,sourceSubmenuReachedWarm=expected_submenu,sourceSubmenuReachedCold=cold_submenu,wrongNewGameBranchAfterCold=cold_newgame,capturedF6Sha256=savedhash,sourceExpectedPassed=expected_submenu and cold_submenu))
            print(json.dumps(dict(completed=mode+'-'+profile,warmSubmenu=expected_submenu,coldSubmenu=cold_submenu,coldNewGame=cold_newgame,phonePreserved=phone_preserved)),flush=True)
    report=dict(format='actual-complete-file-select-f6-focused-dev18-v1',toolSha256=qa.sha(Path(__file__)),titleRunnerSha256=qa.sha(Path(qa.__file__)),sourceFileSelectSha256=qa.sha(a.source/'src/intro/file_select.c'),sourceStateDumpSha256=qa.sha(a.source/'src/core/state_dump.c'),results=results,allSourceExpectedPassed=all(r['sourceExpectedPassed'] for r in results),allExternalPhoneControlsPassed=all(r['phoneSave']['bytesPreservedThroughout'] and r['continuousPhoneContinueControl']['Passed'] for r in results),sourceBackedSideDataReview=[dict(symbol='save_files_present[SAVE_COUNT]',mutable=True,serialized=False,consumers=['FM_SELECT_RESULT','fm_submenu_build Copy availability','file_select_menu_display_only detail loop'],producer='fm_file_select_build and file_select_menu_display_only via load_game(slot) && favourite_thing[1] !=0',coldRisk='Fresh child-selection restore bypasses these producers; zero-initialized flag array can route occupied slot to new-game setup.'),dict(symbol='dont_care_names_data/hp_meter_speeds_data/naming_prompts_data/initial_stats_data',mutable=True,serialized=False,coldGuard='ensure_file_select_assets() called by source consumers; prior asset self-heal tests retain separate proof.'),dict(symbol='two function-local slot_labels[3][32]',mutable=True,serialized=False,coldRisk='Only builder scratch; add_menu_item copies label bytes into serialized MenuItem. Not read after selection yield.'),dict(symbol='fm_child_init/ngn_child_init',mutable=True,serialized=False,coldRisk='Per-dispatch scratch copied immediately by STEP_PUSH_INIT. Live phase/state is serialized in ModeStack; no post-child stale scratch dependency identified.'),dict(symbol='speed_names, keyboard grids/stops, naming sprite source tables',mutable=False,serialized=False,coldRisk='Constant source tables; no mutable cross-process state.')],minimalImplementationProposal='Replace the derived file-slot presence cache dependency at resumed branch/Copy decisions with a pure phone-slot occupancy peek using the same two-copy ADD/XOR checksum validation and favourite_thing[1] contract as load_game. Read into local SaveBlock; avoid invoking state-mutating load_game or changing format16. Exact implementation requires coordinated game_state.c/h and file_select.c lease.',limits=['Complete private immutable player/observer with identical source phone bytes before/after each process. Continuous phone Continue and warm slot selection are positive controls; cold uses actual F6 writer and fresh production --load-state then real Confirm.', 'No injected mode/window/title/name/state edits for focused controls. Original phone seed is generated through actual ordinary new-game naming and native command Save; Redux seed derives from earlier ordinary-input native phone proof.', 'This is a native cold file-select side-data defect; not an original SNES or Redux patch defect and not an explanation of movement/stairs/hotel issues.', 'Physical F6 key is not synthesized; capture-state enters the same production F6 save path. Copy/Delete/Config and every file-menu phase require follow-up coverage before a fix is complete.'],rootOrOwnerInputsModified=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(allSourceExpectedPassed=report['allSourceExpectedPassed'],allExternalPhoneControlsPassed=report['allExternalPhoneControlsPassed'],report=str(a.output),sha256=qa.sha(a.output))))

if __name__=='__main__':main()
