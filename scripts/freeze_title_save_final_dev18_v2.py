# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze new final-runtime title/save/menu proofs without relabeling old proofs.

Reads complete immutable shipping identities and copies two compact local-only
phone prerequisites. No source/build, ROM/pack, owner save or old report mutation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
PROOFS={
 'directTitles':'research/title-producers-dev18-v2-final-review.json',
 'titleCold':'research/title-cold-dev18-v2-final-review.json',
 'titleMenuParents':'research/title-menu-parents-dev18-v2-final-review.json',
 'occupancy':'research/file-select-occupancy-dev18-v2-final-recorded-review.json',
 'slotGlyphs':'research/file-slot-glyph-dev18-v2-final-review.json',
 'namingCancelBackdrop':'research/file-slot-backdrop-dev18-v2-final-review.json',
}
TOOLS=('tools/redux_title_producers_qa_dev18.py','tools/redux_title_cold_qa_dev18.py','tools/redux_title_menu_parents_dev18.py','tools/file_select_occupancy_qa_dev18.py','tools/file_select_cold_qa_dev18.py','tools/file_slot_glyph_qa_dev18.py','tools/file_slot_backdrop_qa_dev18.py','tools/run_final_occupancy_dev18_v2.py','tools/freeze_title_save_final_dev18_v2.py')
EXPECTED={
 'player.exe':'3b467f471acd6bb5aa0cb29b96d89790be3097d8d0c5dd114ce2f128895d6292',
 'observer.exe':'033ed02642e0fc2cb61e2244de40c1b918f6b8e17635fb0c86eb7c11f92aeb92',
 'player.archive':'6a2ea279a762df4c3a887eda7580e09c8034da55f08fb7f9059eb404c949d411',
 'observer.archive':'384bf3becec85a5ed3f531bf0fd2a0f1785c658475f5d71cc4dd63ebaba80283',
 'redux.pak':'d9a772d10aff68bdf93c077cda640d42b835884d6834bb18bf0d43c3800f57bb',
 'original.pak':'01af4f4b590d9e83937b772399ee60a9181e2384e13c1567c94dfc92101b5549',
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('source','builds','runtime','original-assets','redux-assets','original-phone-seed','redux-phone-seed','fixtures','output'):ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args()
    for n,v in vars(a).items():setattr(a,n,v.resolve())
    if a.output.exists() or a.fixtures.exists():raise ValueError('Fresh final metadata/compact fixture folder required')
    scratch=(ROOT/'_BuildScratch').resolve()
    if not a.fixtures.is_relative_to(scratch):raise ValueError('Phone fixtures must stay private in workspace scratch')
    identities={}
    for mode in ('player','observer'):
        exe=a.runtime/(mode+'.exe');archive=a.builds/mode/'game_lib/libearthbound_game.a'
        if sha(exe)!=EXPECTED[mode+'.exe'] or sha(exe)!=sha(a.builds/mode/'earthbound.exe') or sha(archive)!=EXPECTED[mode+'.archive']:raise ValueError('Final complete runtime/archive identity mismatch')
        identities[mode]=dict(executableSha256=sha(exe),archiveSha256=sha(archive),compileCommandsSha256=sha(a.builds/mode/'compile_commands.json'),cmakeCacheSha256=sha(a.builds/mode/'CMakeCache.txt'))
    packs={name:dict(path=str(pack),sha256=sha(pack)) for name,pack in [('original',a.original_assets),('redux',a.redux_assets)]}
    if any(packs[name]['sha256']!=EXPECTED[name+'.pak'] for name in packs):raise ValueError('Final pack identity mismatch')
    reports={name:json.loads((ROOT/path).read_text(encoding='utf-8')) for name,path in PROOFS.items()}
    if not all(r['allPassed'] for r in reports.values()):raise ValueError('Final selected-runtime proof failed')
    receipt_path=ROOT/'research/file-select-occupancy-dev18-v2-final-invocation.json'
    receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
    if not receipt['allInputsBytePreserved'] or receipt['report']['sha256']!=sha(ROOT/PROOFS['occupancy']):raise ValueError('Actual occupancy invocation receipt mismatch')
    for mode in ('player','observer'):
        if receipt['inputsBefore'][mode+'-executable']['sha256']!=identities[mode]['executableSha256'] or receipt['inputsBefore'][mode+'-archive']['sha256']!=identities[mode]['archiveSha256']:raise ValueError('Occupancy receipt uses stale runtime')
    if any(receipt['inputsBefore'][profile+'-assets']['sha256']!=packs[profile]['sha256'] for profile in packs):raise ValueError('Occupancy receipt uses stale pack')
    # Every result must name the actual final profile pack. For each report,
    # validate its complete/archive identity at its published nesting level.
    for name,r in reports.items():
        for row in r['results']:
            mode=row['build'];profile=row['profile']
            if name!='occupancy' and row['packSha256']!=packs[profile]['sha256']:raise ValueError('Report uses stale pack: '+name)
            executable=row.get('completeExecutableSha256',row.get('executableSha256',r.get('completeCandidateBinaries',{}).get(mode)))
            archive=row.get('archiveSha256',row.get('linkedArchive',{}).get('archiveSha256',row.get('purePeek',{}).get('link',{}).get('archiveSha256')))
            if executable is not None and executable!=identities[mode]['executableSha256']:raise ValueError('Report uses stale executable: '+name)
            if archive is not None and archive!=identities[mode]['archiveSha256']:raise ValueError('Report uses stale archive: '+name)
    for mode,row in reports['titleCold']['completeCandidateBuilds'].items():
        if any(row[key]!=identities[mode][key] for key in ('executableSha256','archiveSha256')):raise ValueError('Cold titles use stale complete binaries')
    adopted={}
    for manifest in ('research/title-producers-dev18-private-final-manifest.json','research/file-select-cold-dev18-private-final-manifest.json','research/file-slot-glyph-dev18-private-final-manifest.json'):
        for row in json.loads((ROOT/manifest).read_text(encoding='utf-8'))['sourceChanges']:adopted[row['path']]=row['candidateSha256']
    for rel,expected in adopted.items():
        if sha(a.source/rel)!=expected:raise ValueError('Final adopted source changed: '+rel)
    a.fixtures.mkdir();fixtures=[]
    for name,phone in [('original-native-phone',a.original_phone_seed),('redux-mixed-native-phone',a.redux_phone_seed)]:
        target=a.fixtures/(name+'.srm');shutil.copy2(phone,target)
        if sha(phone)!=sha(target) or target.stat().st_size!=8192:raise ValueError('Compact private phone fixture copy failed')
        fixtures.append(dict(name=name,originalPath=str(phone),compactPrivatePath=str(target),sha256=sha(target),bytes=target.stat().st_size,localOnlyNotForPublication=True))
    direct=reports['directTitles'];cold=reports['titleCold'];parents=reports['titleMenuParents'];occ=reports['occupancy'];glyph=reports['slotGlyphs'];back=reports['namingCancelBackdrop']
    report=dict(format='final-shipping-title-save-menu-proof-manifest-dev18-v2',source=str(a.source),runtime=str(a.runtime),builds=str(a.builds),completeRuntimeIdentities=identities,packs=packs,adoptedSourceIdentities=adopted,allAdoptedSourceIdentitiesMatchFrozenProposals=True,proofs=[dict(name=name,path=path,sha256=sha(ROOT/path),allSelectedChecksPassed=True) for name,path in PROOFS.items()],tools=[dict(path=p,sha256=sha(ROOT/p)) for p in TOOLS],compactPrivateFixtures=fixtures,coverage=dict(directActualTitleProducerRecords=sum(len(r['records']) for r in direct['results']),actualGoodsTitleWarmColdPairs=len(cold['results']),actualPaulaSourceTitleWarmColdPairs=sum('paulaSourceTitle' in r for r in cold['results']),actualEquipmentStatusWarmColdPairs=len(parents['results']),occupancyWarmColdChecksumFixturePairs=len(occ['results']),directPureOccupancyComparisons=sum(len(r['purePeek']['records']) for r in occ['results']),occupiedNormalPhoneContinueControls=sum(r['normalPhoneContinue'] is not None for r in occ['results']),actualSlotListWarmColdPairs=len(glyph['results']),sourceGlyphAndIndependentVramSlotObservations=sum(len(r['warm'])+len(r['cold']) for r in glyph['results']),actualSlotConfirmInputs=sum(len(r['actualInputSelections']) for r in glyph['results']),actualNamingCancelBackdropWarmColdPairs=len(back['results']),bothCompleteExecutablesAndProfiles=True),allPassed=True,priorPrivateRedGreenManifestsPreserved=[dict(path=p,sha256=sha(ROOT/p)) for p in ('research/title-producers-dev18-private-final-manifest.json','research/file-select-cold-dev18-private-final-manifest.json','research/file-slot-glyph-dev18-private-final-manifest.json')],disposableAfterMetadataFreeze=['Raw complete capture logs and repeated private state dumps for these final suites may be deleted after metadata/compact phone fixtures are frozen; tools recreate their own scratch from explicit inputs.','Keep source/runtime/archive snapshots, metadata, tool identities and the two private phone fixtures needed for reproducibility.'],limits=['These are newly executed final complete player/observer/archive comparisons against the exact final Redux pack; old red/private proposal proofs retain their original hashes and labels.', 'Direct title producers, prepared source Paula entry and legal/private name prerequisites are qualified separately from ordinary command menus and real file-menu inputs. No full natural playthrough is claimed.', 'Captured title/menu/font VRAM and selection resume use the production format16/F6 writer and fresh processes. Physical F6/controller hardware and original CPU whole-screen rendering are outside scope.', 'Pure phone occupancy follows first-valid checksum-copy/sentinel source behavior without live mutations; damaged headers/empty copies are explicitly private fixtures. Copy/Delete transaction coverage is not exhaustive.', 'Root source/builds, owner saves, commercial ROM/pack inputs and older proof manifests are untouched by these tools. Compact SRAM fixtures remain local and are not public release assets.'],rootOrOwnerInputsModified=False)
    report['occupancyInvocationReceipt']=dict(path=str(receipt_path.relative_to(ROOT)),sha256=sha(receipt_path),allExplicitPackRuntimeInputsBytePreserved=True)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(report=str(a.output),sha256=sha(a.output),coverage=report['coverage'],allPassed=True)))

if __name__=='__main__':main()
