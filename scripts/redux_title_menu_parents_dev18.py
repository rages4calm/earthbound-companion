# SPDX-License-Identifier: GPL-3.0-or-later
"""Real ordinary Equipment/Status title parents and fresh F6 continuation.

Clones only private prepared world saves, uses actual menu controls, and checks
captured title glyphs/VRAM through the complete proposed executables. No mode,
window, reader, title, glyph or VRAM is injected for these parent paths.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
from build_maternalbound_pack import read_pack
from check_jev_observer_parity import latest, local_scratch
import redux_title_cold_qa_dev18 as qa

ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('source','builds','runtime','original-assets','redux-assets','redux-phone-seed','scratch','output'):ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args()
    for n,v in vars(a).items():setattr(a,n,v.resolve())
    a.scratch=local_scratch(a.scratch)
    if a.scratch.exists() or a.output.exists():raise ValueError('Fresh output and scratch required')
    a.scratch.mkdir();sys.path.insert(0,str(a.source/'src/vendor/tamp'));import tamp
    l=qa.layout(a.source,ROOT/'tools/mingw64/bin/gcc.exe',a.builds/'player',a.scratch);results=[]
    for mode in ('player','observer'):
        exe=a.runtime/(mode+'.exe')
        if qa.sha(exe)!=qa.sha(a.builds/mode/'earthbound.exe'):raise ValueError('Complete executable/build mismatch')
        for profile,pack in (('original',a.original_assets),('redux',a.redux_assets)):
            parent=a.scratch/(mode+'-'+profile);parent.mkdir();world=qa.Session(exe,pack,parent/'world',l,tamp)
            _,_,assets=read_pack(pack,a.source/'src/data/runtime_generated/asset_ids.h');world.qa_assets=assets
            if profile=='redux':qa.copy_world(world,a.redux_phone_seed)
            else:qa.new_original_world(world)
            qa.inventory_prerequisite(world,a.source)
            if world.last['modes']!=[l['worldMode']]:raise ValueError('Prepared entry is not real world root')
            expected=qa.MIXED if profile=='redux' else [g for g in world.last['names'][0][:5] if g]
            for branch,windowid,buttons in (
                ('equipment',6,[qa.naming.RIGHT] if profile=='redux' else [qa.naming.RIGHT,qa.naming.DOWN,qa.naming.DOWN]),
                ('status',8,[qa.naming.RIGHT,qa.naming.DOWN] if profile=='redux' else [qa.naming.DOWN,qa.naming.DOWN])):
                scene=qa.Session(exe,pack,parent/branch,l,tamp);scene.qa_assets=assets
                shutil.copy2(world.folder/'fixture.srm',scene.folder/'fixture.srm')
                shutil.copytree(world.folder/'saves',scene.folder/'saves')
                scene.step('actual-open-command-menu',[0x40 if profile=='redux' else 0x80],wait=40)
                scene.step('actual-'+branch+'-menu-choice',buttons+[qa.naming.CONFIRM],wait=50)
                pair=qa.cold_pair(scene,expected,windowid,branch=='equipment')
                before=list(scene.last['modes']);scene.step('actual-cancel-after-cold-title',[qa.naming.B],wait=50)
                continued=before!=scene.last['modes']
                if not continued:raise ValueError('Actual ordinary menu did not cancel after cold input')
                row=dict(build=mode,profile=profile,branch=branch,packSha256=qa.sha(pack),completeExecutableSha256=qa.sha(exe),archiveSha256=qa.sha(a.builds/mode/'game_lib/libearthbound_game.a'),buttons=buttons+[qa.naming.CONFIRM],titleAndCold=pair,ordinaryCancelAfterCold=dict(beforeModes=before,afterModes=scene.last['modes'],continued=continued),Passed=pair['Passed'] and continued)
                if branch=='equipment':row['Passed'] &= pair['ordinaryDownAfterCold']['previous']!=pair['ordinaryDownAfterCold']['current']
                results.append(row);print(json.dumps(dict(completed=mode+'-'+profile+'-'+branch,Passed=row['Passed'])),flush=True)
    report=dict(format='actual-complete-title-menu-parents-dev18-v1',toolSha256=qa.sha(Path(__file__)),titleRunnerSha256=qa.sha(Path(qa.__file__)),results=results,allPassed=all(r['Passed'] for r in results),limits=['Complete candidate player/observer execute actual command controls and Equipment/Status source parents. Only existing private world save prerequisites (name/source Cookie88/Hamburger90 acquisition) are prepared.', 'Menu choices, titles, selected option movement, F6 capture writer, fresh process reload and cancel continuation are executed without C wrappers or injected menu/title/VRAM.', 'Original is created by ordinary new-game default naming; Redux mixed legal six-letter name comes from earlier private ordinary-input phone proof. Broader natural story progression, every parent branch, equipment transactions/status effects, physical F6 key and original CPU whole-screen rendering remain outside this test.'],rootOrOwnerInputsModified=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(allPassed=report['allPassed'],report=str(a.output),sha256=qa.sha(a.output))))

if __name__=='__main__':main()
