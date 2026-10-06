# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze source/render swirl evidence and isolated dev.18 proposal identities."""
import argparse
import difflib
import hashlib
import json
import shutil
from pathlib import Path

from build_maternalbound_pack import read_pack

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_IDS = [1047,1051,1053,1055,1059,1081,1083,1086,1087,1088,1090,
    1091,1092,1094,1095,1096,1098,1099,1100,1102,1103,1104,1105,1106,
    1107,1108,1109,1110,1111,1112,1119]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def identity(path):
    path = Path(path).resolve()
    return dict(path=str(path.relative_to(ROOT)).replace('\\', '/'), sha256=sha(path))

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def patch(before, after, relative, output):
    text = ''.join(difflib.unified_diff(
        before.read_text(encoding='utf-8').splitlines(True),
        after.read_text(encoding='utf-8').splitlines(True),
        fromfile='a/'+relative, tofile='b/'+relative))
    if not text:
        raise ValueError('Proposal patch is empty: '+relative)
    output.write_text(text, encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-baseline', type=Path, required=True)
    parser.add_argument('--tools-baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    args = parser.parse_args()
    oldnative, oldtools, candidate = (
        args.native_baseline.resolve(), args.tools_baseline.resolve(),
        args.candidate.resolve())
    if not all(p.is_relative_to(ROOT/'_BuildScratch') for p in
               (oldnative, oldtools, candidate)):
        raise ValueError('Private scratch paths required')
    output = ROOT/'research/swirl-consumer-dev24-dev17-v4-manifest.json'
    archive = ROOT/'research/evidence-tools'
    module = archive/'maternalbound_swirls-dev18-private.py'
    nativepatch = archive/'swirl-dev18-private-native.patch'
    builderpatch = archive/'swirl-dev18-private-builder.patch'
    oldoval = archive/'oval_window-dev17-v4-swirl-baseline.c'
    if any(p.exists() for p in (output,module,nativepatch,builderpatch,oldoval)):
        raise ValueError('Refusing to overwrite frozen evidence')
    paths = {key:ROOT/path for key,path in {
        'originalRed':'research/original-swirl-consumer-dev24-v4-red-review.json',
        'reduxRed':'research/redux-swirl-consumer-dev24-v4-red-review.json',
        'projectSource':'research/redux-swirl-project-source-dev24-review.json',
        'originalPrivateGreen':'research/original-swirl-consumer-dev24-private-dev18-review.json',
        'reduxPrivateGreen':'research/redux-swirl-consumer-dev24-private-dev18-review.json',
        'originalActualParent':'research/original-swirl-full-parent-dev24-private-dev18-review.json',
        'reduxActualParent':'research/redux-swirl-full-parent-dev24-private-dev18-review.json',
        'actualColdParents':'research/swirl-transition-cold-dev24-private-dev18-review.json',
    }.items()}
    reports = {key:read(path) for key,path in paths.items()}
    qa = ROOT/'tools/swirl_source_consumer_qa_dev24.py'
    for key in ('originalRed','reduxRed','originalPrivateGreen','reduxPrivateGreen'):
        if reports[key]['toolSha256']!=sha(qa) or reports[key]['executedAssertions']!=3075:
            raise ValueError('Six-sequence consumer proof identity/count changed')
    for key in ('originalRed','reduxRed'):
        if reports[key]['allPassed'] or not reports[key]['allNativeTimelinesPassed']:
            raise ValueError('Expected bounded rendering/data red finding missing')
    if not reports['originalRed']['allSourceFirstWindowsPassed']:
        raise ValueError('Original first-window control unexpectedly failed')
    for key in reports.keys()-{'originalRed','reduxRed'}:
        if not reports[key]['allPassed']:
            raise ValueError('Private/source control failed: '+key)
    cold = reports['actualColdParents']
    if cold['toolSha256']!=sha(ROOT/'tools/swirl_transition_cold_qa_dev24.py'):
        raise ValueError('Cold proof tool changed')
    if (cold['executedAssertions'],cold['processes'],cold['coldCases'])!=(136,12,4):
        raise ValueError('Actual cold parent proof incomplete')
    if reports['projectSource']['toolSha256']!=sha(ROOT/'tools/swirl_project_source_addendum_dev24.py'):
        raise ValueError('Independent source proof tool changed')
    ids = candidate/'native-source/src/data/runtime_generated/asset_ids.h'
    oldpack = ROOT/'_BuildScratch/sequence-animation-import-dev18-candidate1/map-gas-teleport-candidate.pak'
    newpack = candidate/'map-gas-teleport-swirl-candidate.pak'
    basepack = ROOT/'_BuildScratch/art-decode-dev20-final-fixed-redux.pak'
    entries,header,before = read_pack(oldpack,ids)
    entries2,header2,after = read_pack(newpack,ids)
    baseentries,baseheader,baseline = read_pack(basepack,ids)
    changes=[];cumulative=[]
    for index,(symbol,key) in enumerate(entries):
        row = dict(id=index,symbol=symbol,asset=key)
        if before[key]!=after[key]:
            changes.append(dict(**row,oldBytes=len(before[key]),newBytes=len(after[key]),
                oldSha256=hashlib.sha256(before[key]).hexdigest(),
                newSha256=hashlib.sha256(after[key]).hexdigest()))
        if baseline[key]!=after[key]:
            cumulative.append(row)
    if not entries==entries2==baseentries or not header==header2==baseheader or len(entries)!=1174:
        raise ValueError('Native asset namespace/header changed')
    if [row['id'] for row in changes]!=EXPECTED_IDS or len(cumulative)!=41:
        raise ValueError('Unexpected asset changes')
    recipe = read(candidate/'map-gas-teleport-swirl-candidate.report.json')['swirls']
    if len(recipe['reviewedFrames'])!=126 or len(recipe['assets'])!=31:
        raise ValueError('Source importer inventory incomplete')
    oldsource = oldnative/'src/game/oval_window.c'
    newsource = candidate/'native-source/src/game/oval_window.c'
    runtime = read(candidate/'runtime-provenance.json')
    if sha(oldsource)!=runtime['baselineSourceSha256'] or sha(newsource)!=runtime['candidateSourceSha256']:
        raise ValueError('Actual compiled source identity changed')
    if sha(candidate/'runtime/player.exe')!=runtime['playerSha256'] or sha(candidate/'build/game_lib/libearthbound_game.a')!=runtime['librarySha256']:
        raise ValueError('Private actual runtime/library changed')
    oldbuilder = oldtools/'build_maternalbound_pack.py'
    newbuilder = candidate/'tools/build_maternalbound_pack.py'
    archive.mkdir(parents=True,exist_ok=True)
    shutil.copy2(candidate/'tools/maternalbound_swirls.py',module)
    shutil.copy2(oldsource,oldoval)
    patch(oldsource,newsource,'native-source/src/game/oval_window.c',nativepatch)
    patch(oldbuilder,newbuilder,'tools/build_maternalbound_pack.py',builderpatch)
    red_summary={}
    for key in ('originalRed','reduxRed'):
        frames=reports[key]['frameChecks']
        red_summary[key]=dict(
            sourceMode4Frames=len({f['frameId'] for f in frames if f['sourceMode']==4}),
            changedSourceVsDonorFrames=sorted({f['frameId'] for f in frames if not f['sourceRowsEqualToDonor']}),
            actualMaskRenderFailures=sum(not f['sourceCompositeMaskMatchesNative'] for f in frames),
            differingMaskedPixels=sum(f['differingMaskedPixels'] for f in frames))
    record=dict(checkpoint='dev.17-v4 red evidence / isolated private dev.18 proposal',
        toolSha256=sha(__file__),evidenceReports={key:identity(path) for key,path in paths.items()},
        evidenceTools=[identity(ROOT/'tools'/name) for name in (
            'swirl_source_consumer_qa_dev24.py','swirl_project_source_addendum_dev24.py',
            'swirl_transition_cold_qa_dev24.py','prepare_private_swirl_dev18.py',
            'battle_full_encounter_qa_dev18.py','freeze_swirl_evidence_dev24.py')],
        pinnedReduxCommit=reports['reduxRed']['pinnedReduxCommit'],
        compiledRomSha256=reports['reduxRed']['romSha256'],
        baselineProduction=reports['reduxRed']['production'],confirmedRed=red_summary,
        confirmedDefects=['Native swirl DMAP4 parser discarded WH2/WH3 and never enabled the second HDMA window.',
            '31 retained Original swirl payloads differ semantically from pinned Redux source masks at the actual relocated four-byte pointer table.'],
        independentSourceProof='All126 compiled Redux masks equal the pinned source PNGs; six source sequence metadata contracts also agree (132 assertions).',
        privateProposal=dict(privateOnly=True,releaseCandidate=False,
            baselineDev17PackSha256=sha(basepack),baselineMapGasTeleportPackSha256=sha(oldpack),
            proposedPackSha256=sha(newpack),namespaceAndHeaderUnchanged=True,registrySha256=sha(ids),
            incrementalChangedAssetCount=31,incrementalChangedAssetIds=EXPECTED_IDS,
            incrementalChangedAssets=changes,cumulativeChangedAssetCount=41,
            cumulativeChangedAssets=cumulative,unchangedComparedWithDev17=1133,
            sourceRecipe=recipe,importer=identity(module),nativePatch=identity(nativepatch),
            builderPatch=identity(builderpatch),archivedBaselineNativeSource=identity(oldoval),
            baselineBuilderSha256=sha(oldbuilder),candidateBuilderSha256=sha(newbuilder),
            nativeRuntime=runtime),
        nativeChangeScope='Only private oval_window.c: decode/apply both HDMA windows, clear second window at existing stop/auto-restore sites, rebuild already-consumed active frame caches after F6 restore without advancing timing or changing serialized size.',
        actualRenderScope='Actual native PPU renders uniform BG1 against independent source Boolean two-window composites for126 frames across8 option variants in each profile. No mode or render callback stub replaces the consumers.',
        actualParentScope='Four scripted encounter groups1/48/448/471 in each profile run BS_ENTER through swirl, battle, menu/AI, KO, rewards and overworld cleanup. Four separate regular/boss prepared parents additionally compare immediate first/second window cold-restored masks and completed gameplay state.',
        executedConsumerAssertionsGreen=6150,executedIndependentSourceAssertions=132,
        executedColdAssertions=136,actualFullParentCases=8,actualColdPreparedParents=4,
        actualColdProcesses=4,actualWarmAndColdProcesses=12,skippedCases=0,
        allPrivateControlsPassed=True,
        limits=['Prepared encounter parties are level99 and surrounding overworld/enemy state is staged; this is not a natural campaign playthrough.',
            'All six animation types execute as prepared sequences; actual full encounter parents cover regular and boss transition types only.',
            'Cold proof uses same new candidate content. Cross-version/cross-content checkpoint migration and stale completed held masks with zero timer are not certified.',
            'Only active per-line HDMA caches are reconstructed; no serialized field/section/version size changes.',
            'Uniform BG1 window rendering proves mask composition, not complete hardware audiovisual or color-math parity.',
            'Root must integrate the narrow native patch into current source, regenerate coherent assets and reverify final shipping identities and content migration.',
            'The private observer filename is an untested player alias. Executed private production player/library identities are recorded.',
            'Public evidence includes hashes/recipes/code/results only, no ROM, extracted assets, saves or soundtrack bytes.'],
        ownerWrites=False,redistributableGameAssetsIncluded=False,sharedSourcesModifiedByThisTask=False)
    output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(manifest=identity(output),proposedPackSha256=sha(newpack),
        incrementalChangedAssetIds=EXPECTED_IDS,nativePatch=identity(nativepatch),
        importer=identity(module),builderPatch=identity(builderpatch),allPassed=True)))

if __name__=='__main__':
    main()
