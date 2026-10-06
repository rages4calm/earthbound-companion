# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze actual intro consumer red/control and isolated gas importer proposal."""
import argparse
import difflib
import hashlib
import json
import shutil
from pathlib import Path

from build_maternalbound_pack import read_pack

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identity(path):
    path=Path(path)
    return dict(path=str(path.relative_to(ROOT)).replace('\\','/'),sha256=sha(path))


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--map-candidate',type=Path,required=True)
    p.add_argument('--gas-candidate',type=Path,required=True)
    a=p.parse_args();maps=a.map_candidate.resolve();gas=a.gas_candidate.resolve()
    for folder in (maps,gas):
        if not folder.is_relative_to(ROOT/'_BuildScratch'):
            raise ValueError('Private candidate must remain in workspace scratch')
    output=ROOT/'research/intro-family-dev22-dev17-v4-manifest.json'
    if output.exists():
        raise ValueError('Refusing to overwrite immutable manifest')
    reports={key:ROOT/path for key,path in {
        'reduxRed':'research/redux-intro-retained-dev22-v4-red-review.json',
        'originalControl':'research/original-intro-retained-dev22-v4-control-review.json',
        'reduxPrivateGreen':'research/redux-intro-retained-dev22-private-dev18-review.json',
        'mapPrivateGreen':'research/redux-retained-presentation-dev21-gas-private-dev18-review.json',
    }.items()}
    data={key:read(path)for key,path in reports.items()}
    tool=ROOT/'tools/intro_retained_presentation_qa_dev22.py'
    for key in ('reduxRed','originalControl','reduxPrivateGreen'):
        if data[key]['toolSha256']!=sha(tool)or data[key]['executedAssertions']!=19:
            raise ValueError('Executed intro tool differs from current frozen source')
    if data['reduxRed']['allPassed']or not data['reduxRed']['nativeExecutionPassed']:
        raise ValueError('Expected one source omission with successful native execution')
    failures=[x for x in data['reduxRed']['sourceParityChecks']if not x['passed']]
    if len(failures)!=1 or failures[0]['check']!='gas-source-base-art' or failures[0]['differingPixels']!=5794:
        raise ValueError('Unexpected source red evidence')
    if not all(data[key]['allPassed']for key in ('originalControl','reduxPrivateGreen','mapPrivateGreen')):
        raise ValueError('Private controls must pass before proposing integration')
    ids=maps/'native-source/src/data/runtime_generated/asset_ids.h'
    old_pack=maps/'town-map-candidate.pak';new_pack=gas/'town-map-gas-candidate.pak'
    entries,old_header,old=read_pack(old_pack,ids);new_entries,new_header,new=read_pack(new_pack,ids)
    changed=[]
    for i,(symbol,name)in enumerate(entries):
        if old[name]!=new[name]:
            changed.append(dict(id=i,symbol=symbol,asset=name,oldBytes=len(old[name]),newBytes=len(new[name]),
                                oldSha256=hashlib.sha256(old[name]).hexdigest(),newSha256=hashlib.sha256(new[name]).hexdigest()))
    wanted={'US/intro/gas_station.gfx.lzhal','US/intro/gas_station.arr.lzhal'}
    if {x['asset']for x in changed}!=wanted or old_header!=new_header or entries!=new_entries:
        raise ValueError('Unapproved gas-station asset/namespace change')
    baseline_pack=ROOT/'_BuildScratch/art-decode-dev20-final-fixed-redux.pak'
    _,baseline_header,baseline=read_pack(baseline_pack,ids)
    cumulative=[dict(id=i,symbol=symbol,asset=name)for i,(symbol,name)in enumerate(entries)if baseline[name]!=new[name]]
    if len(cumulative)!=9 or baseline_header!=new_header:
        raise ValueError('Expected seven Town Map changes plus two gas-station changes')
    archive=ROOT/'research/evidence-tools';archive.mkdir(exist_ok=True)
    module=archive/'maternalbound_gas_station-dev18-private.py'
    patch=archive/'gas-station-dev18-private-builder.patch'
    if module.exists()or patch.exists():
        raise ValueError('Private importer/patch already frozen')
    shutil.copy2(gas/'tools/maternalbound_gas_station.py',module)
    left=maps/'tools/build_maternalbound_pack.py';right=gas/'tools/build_maternalbound_pack.py'
    diff=''.join(difflib.unified_diff(left.read_text(encoding='utf-8').splitlines(True),right.read_text(encoding='utf-8').splitlines(True),
                                    fromfile='a/tools/build_maternalbound_pack.py',tofile='b/tools/build_maternalbound_pack.py'))
    patch.write_text(diff,encoding='utf-8')
    record=dict(
        toolSha256=sha(__file__),checkpoint='dev.17-v4 evidence / private dev.18 proposal',
        evidenceReports={key:identity(path)for key,path in reports.items()},
        evidenceTools=[identity(tool),identity(ROOT/'tools/prepare_private_gas_station_dev18.py'),identity(Path(__file__))],
        pinnedReduxCommit=data['reduxRed']['pinnedReduxCommit'],compiledRomSha256=data['reduxRed']['romSha256'],
        nativeDefectProven=True,nativeCodeChangeRequired=False,
        confirmedSourceOmission='Gas-station BG1 still shows EARTH BOUND / THE WAR AGAINST GIYGAS! instead of compiled Redux MOTHER 2 / GIYGAS STRIKES BACK!',
        differingSourcePixels=5794,
        resolvedSharedControls=['All three company logos render exactly the compiled source image through the real timed logo parent/fades.',
            'Produced by Itoi and Nintendo Presentation render exactly the compiled source through real CALLROUTINE dispatch, with prepared BG3 layout.',
            'Both gas-station palettes decode identically to source and remain unchanged.',
            'Raw repacking differences for those controls are not missing semantic conversion.'],
        sourceConsumers=data['reduxPrivateGreen']['compiledConsumers'],
        privateProposal=dict(privateOnly=True,releaseCandidate=False,ownerWrites=False,
            baselineTownMapPackSha256=sha(old_pack),proposedPackSha256=sha(new_pack),
            baselineDev17PackSha256=sha(baseline_pack),registrySha256=sha(ids),namespaceAndHeaderUnchanged=True,
            incrementalChangedAssetCount=2,incrementalChangedAssets=changed,
            cumulativeChangedAssetCount=9,cumulativeChangedAssets=cumulative,
            unchangedComparedWithDev17=len(entries)-9,
            importer=identity(module),builderPatch=identity(patch),
            baselineBuilderSha256=sha(left),candidateBuilderSha256=sha(right),
            unchangedNativePrivateRuntime=read(maps/'runtime-provenance.json'),
            preparedCases=data['reduxPrivateGreen']['preparedCases']+data['mapPrivateGreen']['preparedCases'],
            executedAssertions=data['reduxPrivateGreen']['executedAssertions']+data['mapPrivateGreen']['executedAssertions'],
            skippedCases=0,allPassed=True),
        limits=['Source256x224 centered BG1 comparison covers the normal gas image at GS_PH3, not every dynamic color-math frame or modern shader.',
            'Native gas child completes real EVENT860 flash and fade sequence in1678 frames with normal cleanup; full intro boot/title/file-selection parent is not run.',
            'Produced/Presented caller art registers are prepared source prerequisites; complete natural attract scenes are not run.',
            'Private pack regeneration and consumers are proved. Root must separately adopt importer, regenerate final coherent pack and verify phone/F6/content migration.',
            'Observer private alias was not tested; shipping observer needs a coherent actual build.'],
        ownerWrites=False,redistributableGameAssetsIncluded=False,sharedSourcesModifiedByThisTask=False,
    )
    output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(manifest=identity(output),proposedPackSha256=sha(new_pack),changedAssets=changed,cumulativeChangedAssets=cumulative)))


if __name__=='__main__':
    main()
