# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze source-backed retained animation review and narrow teleport proposal."""
import argparse
import difflib
import hashlib
import json
import shutil
from pathlib import Path

from build_maternalbound_pack import read_pack

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def identity(path):return dict(path=str(Path(path).resolve().relative_to(ROOT)).replace('\\','/'),sha256=sha(path))
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline-candidate',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True)
    a=p.parse_args();old=a.baseline_candidate.resolve();new=a.candidate.resolve()
    if not all(x.is_relative_to(ROOT/'_BuildScratch')for x in (old,new)):raise ValueError('Private candidate paths only')
    output=ROOT/'research/sequence-animation-dev23-dev17-v4-manifest.json'
    if output.exists():raise ValueError('Refusing to overwrite frozen manifest')
    paths={key:ROOT/path for key,path in {
        'reduxRed':'research/redux-sequence-animation-dev23-v4-red-review.json',
        'originalControl':'research/original-sequence-animation-dev23-v4-control-review.json',
        'reduxPrivateGreen':'research/redux-sequence-animation-dev23-private-dev18-review.json',
        'introControl':'research/redux-intro-retained-dev23-teleport-control-review.json',
        'mapControl':'research/redux-map-retained-dev23-teleport-control-review.json',
        'actualAppearanceParent':'research/starman-appearance-parent-dev23-private-dev18-review.json',
    }.items()}
    reports={key:read(path)for key,path in paths.items()}
    source_tool=ROOT/'tools/sequence_animation_consumer_qa_dev23.py'
    for key in ('reduxRed','originalControl','reduxPrivateGreen'):
        if reports[key]['toolSha256']!=sha(source_tool)or reports[key]['executedAssertions']!=130:raise ValueError('Animation proof tool changed')
    red=reports['reduxRed'];failed=[x for x in red['sourceParityChecks']if not x['passed']]
    if not red['nativeExecutionPassed']or red['allPassed']or [x['check']for x in failed]!=[f'3-{f}-source-art'for f in range(4,8)]:raise ValueError('Unexpected retained-art red findings')
    if not all(reports[key]['allPassed']for key in reports if key!='reduxRed'):raise ValueError('Final controls must all pass')
    if reports['actualAppearanceParent']['toolSha256']!=sha(ROOT/'tools/starman_appearance_parent_qa_dev23.py'):raise ValueError('Appearance proof tool changed')
    ids=ROOT/'_BuildScratch/presentation-import-dev18-candidate3/native-source/src/data/runtime_generated/asset_ids.h'
    oldpak=old/'town-map-gas-candidate.pak';newpak=new/'map-gas-teleport-candidate.pak';basepak=ROOT/'_BuildScratch/art-decode-dev20-final-fixed-redux.pak'
    entries,header,before=read_pack(oldpak,ids);entries2,header2,after=read_pack(newpak,ids);_,baseheader,baseline=read_pack(basepak,ids)
    changes=[];cumulative=[]
    for id,(symbol,key)in enumerate(entries):
        if before[key]!=after[key]:changes.append(dict(id=id,symbol=symbol,asset=key,oldBytes=len(before[key]),newBytes=len(after[key]),oldSha256=hashlib.sha256(before[key]).hexdigest(),newSha256=hashlib.sha256(after[key]).hexdigest()))
        if baseline[key]!=after[key]:cumulative.append(dict(id=id,symbol=symbol,asset=key))
    if entries!=entries2 or header!=header2 or header!=baseheader or len(entries)!=1174:raise ValueError('Namespace/header changed')
    if len(changes)!=1 or changes[0]['asset']!='graphics/animations/starman_jr_teleport.anim.lzhal' or len(cumulative)!=10:raise ValueError('Unexpected asset differences')
    build_report=read(new/'map-gas-teleport-candidate.report.json')if(new/'map-gas-teleport-candidate.report.json').exists()else json.loads((new/'pack-build.log').read_text(encoding='utf-8-sig'))
    source_review=build_report['sequenceAnimations']
    if source_review['zeroPaddingBytes']!=48 or not source_review['paddingUnreferenced']or len(source_review['reviewedSourceRecords'])!=6:raise ValueError('Source adaptation guard missing')
    archive=ROOT/'research/evidence-tools';module=archive/'maternalbound_sequence_animations-dev18-private.py';patch=archive/'sequence-animation-dev18-private-builder.patch'
    if module.exists()or patch.exists():raise ValueError('Proposal already frozen')
    shutil.copy2(new/'tools/maternalbound_sequence_animations.py',module)
    left=old/'tools/build_maternalbound_pack.py';right=new/'tools/build_maternalbound_pack.py'
    diff=''.join(difflib.unified_diff(left.read_text(encoding='utf-8').splitlines(True),right.read_text(encoding='utf-8').splitlines(True),fromfile='a/tools/build_maternalbound_pack.py',tofile='b/tools/build_maternalbound_pack.py'))
    patch.write_text(diff,encoding='utf-8')
    record=dict(checkpoint='dev.17-v4 evidence / private dev.18 proposal',toolSha256=sha(__file__),
        evidenceReports={key:identity(path)for key,path in paths.items()},
        evidenceTools=[identity(source_tool),identity(ROOT/'tools/prepare_private_sequence_animation_dev18.py'),identity(ROOT/'tools/starman_appearance_parent_qa_dev23.py'),identity(Path(__file__))],
        pinnedReduxCommit=red['pinnedReduxCommit'],compiledRomSha256=red['romSha256'],nativePresentationMismatchProven=True,nativeCodeChangeRequired=False,
        confirmedOmission='Starman Jr. retained animation ID3 frames4-7 differ from the compiled Redux source artwork.',
        sourceArtRed=failed,sourceTablePointer=red['sourceTablePointer'],sourceTableSha256=red['sourceTableSha256'],sixSequenceSourceReview=red['sourceRecords'],
        retainedEquivalentControls='All24 frames of the other five sequences render the compiled source image despite differing raw tile packing; their metadata, delays and arrangement bounds agree.',
        privateProposal=dict(privateOnly=True,releaseCandidate=False,baselineTownMapGasPackSha256=sha(oldpak),proposedPackSha256=sha(newpak),baselineDev17PackSha256=sha(basepak),
            registrySha256=sha(ids),namespaceAndHeaderUnchanged=True,incrementalChangedAssetCount=1,incrementalChangedAssets=changes,
            cumulativeChangedAssetCount=10,cumulativeChangedAssets=cumulative,unchangedComparedWithDev17=1164,
            sourceRecipe=source_review,importer=identity(module),builderPatch=identity(patch),
            baselineBuilderSha256=sha(left),candidateBuilderSha256=sha(right),unchangedNativePrivateRuntime=read(ROOT/'_BuildScratch/presentation-import-dev18-candidate3/runtime-provenance.json')),
        executedAssertionsPositive=sum(reports[key]['executedAssertions']for key in reports if key!='reduxRed'),executedAssertionsRed=red['executedAssertions'],
        actualParentProcesses=6,actualColdProcesses=2,skippedCases=0,allPrivateControlsPassed=True,
        actualAppearanceScope='Packed C67501 creates source sprite303 Original /481 Redux and runs complete EVENT622 appearance until its first movement wait naturally returns.127Redux/113Original frames; mid-frame2 cold replays finish40frames without completion injection.',
        sourceContract='Compiled teleport912bytes/57tiles versus native960bytes/60tiles; insert48zero bytes before source8-byte palette and eight1792-byte arrangements. All source frame tile references are below57; inserted tiles are never referenced.',
        limits=['Source/actual centered BG3 frames and exact delays are proved; composite natural overworld visual/audio parity is not claimed.',
                'The appearance parent proof stops at its first completed WAIT_FOR_ACTIONSCRIPT. Surrounding party is prepared Ness-only at source hotspot43; later smoke, dialogue and boss battle are not run.',
                'Public evidence contains hashes, source recipes, code patches and numeric results, no game asset bytes, ROMs, saves or PCM.',
                'Root must integrate the narrow importer, regenerate a coherent final pack and separately verify content/save migration; private native observer alias is not tested.'],
        ownerWrites=False,redistributableGameAssetsIncluded=False,sharedSourcesModifiedByThisTask=False)
    output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(manifest=identity(output),proposedPackSha256=sha(newpak),incrementalChangedAssets=changes,cumulativeChangedAssets=cumulative,executedAssertionsPositive=record['executedAssertionsPositive'])))

if __name__=='__main__':main()
