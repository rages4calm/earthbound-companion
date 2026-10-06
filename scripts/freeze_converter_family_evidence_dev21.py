# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze dev.17 converter findings and an isolated dev.18 Town Map proposal.

Public output contains source patches and identities, never ROM/assets/screens.
The candidate remains private and requires setup/content-migration integration.
"""
import argparse
import difflib
import hashlib
import json
import shutil
from pathlib import Path

from build_maternalbound_pack import read_pack

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identity(path):
    path = Path(path)
    return dict(path=str(path.relative_to(ROOT)).replace('\\', '/'), sha256=sha(path))


def json_read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def put_json(path, data):
    path = ROOT / path
    if path.exists():
        raise ValueError('Refusing to overwrite frozen evidence: ' + str(path))
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate', type=Path, required=True)
    a = p.parse_args()
    candidate = a.candidate.resolve()
    if not candidate.is_relative_to(ROOT / '_BuildScratch'):
        raise ValueError('Private candidate must remain within workspace scratch')
    baseline = ROOT / '_BuildScratch/audit-dev17-v4-complete-source'
    ids = baseline / 'src/data/runtime_generated/asset_ids.h'
    old_pack = ROOT / '_BuildScratch/art-decode-dev20-final-fixed-redux.pak'
    new_pack = candidate / 'town-map-candidate.pak'
    entries, old_header, old = read_pack(old_pack, ids)
    new_entries, new_header, new = read_pack(new_pack, ids)
    allowed = {71, *range(1168, 1174)}
    changed = []
    for i, (symbol, name) in enumerate(entries):
        if old[name] != new[name]:
            changed.append(dict(id=i, symbol=symbol, asset=name,
                                oldBytes=len(old[name]), newBytes=len(new[name]),
                                oldSha256=hashlib.sha256(old[name]).hexdigest(),
                                newSha256=hashlib.sha256(new[name]).hexdigest()))
    if {x['id'] for x in changed} != allowed or old_header != new_header or entries != new_entries:
        raise ValueError('Town Map proposal changed unapproved assets or namespace')
    report_names = {
        'family': 'research/redux-converter-family-dev21-v4-review.json',
        'reduxRed': 'research/redux-retained-presentation-dev21-v4-red-review.json',
        'originalControl': 'research/original-retained-presentation-dev21-v4-control-review.json',
        'reduxPrivateGreen': 'research/redux-retained-presentation-dev21-private-dev18-review.json',
        'originalPrivateControl': 'research/original-retained-presentation-dev21-private-dev18-control-review.json',
    }
    reports = {key: json_read(ROOT / path) for key, path in report_names.items()}
    if not reports['family']['auditPassed'] or reports['reduxRed']['allPassed']:
        raise ValueError('Expected source inventory pass and frozen Redux red evidence')
    for key in ('originalControl', 'reduxPrivateGreen', 'originalPrivateControl'):
        if not reports[key]['allPassed'] or reports[key]['executedAssertions'] != 56:
            raise ValueError('Required production controls missing: ' + key)
    if reports['reduxRed']['executedAssertions'] != 56:
        raise ValueError('Frozen red fixture coverage changed')
    tools = ['tools/audit_converter_family_coverage_dev21.py',
             'tools/retained_presentation_qa_dev21.py',
             'tools/prepare_private_town_map_dev18.py',
             'tools/freeze_converter_family_evidence_dev21.py']
    for key, tool in (('family', tools[0]), ('reduxRed', tools[1]),
                      ('originalControl', tools[1]), ('reduxPrivateGreen', tools[1]),
                      ('originalPrivateControl', tools[1])):
        if reports[key]['toolSha256'] != sha(ROOT / tool):
            raise ValueError('Executed tool identity changed: ' + key)
    evidence = ROOT / 'research/evidence-tools'
    evidence.mkdir(exist_ok=True, parents=True)
    patches = []
    for left, right, name, old_label, new_label in (
        (baseline / 'src/game/town_map.c', candidate / 'native-source/src/game/town_map.c',
         'town-map-dev18-private-native.patch', 'a/src/game/town_map.c', 'b/src/game/town_map.c'),
        (evidence / 'build_maternalbound_pack-dev17-v4.py', candidate / 'tools/build_maternalbound_pack.py',
         'town-map-dev18-private-builder.patch', 'a/tools/build_maternalbound_pack.py', 'b/tools/build_maternalbound_pack.py'),
    ):
        target = evidence / name
        if target.exists():
            raise ValueError('Patch already frozen')
        diff = ''.join(difflib.unified_diff(left.read_text(encoding='utf-8').splitlines(True), right.read_text(encoding='utf-8').splitlines(True), fromfile=old_label, tofile=new_label))
        target.write_text(diff, encoding='utf-8')
        patches.append(dict(**identity(target), baselineSha256=sha(left), candidateSha256=sha(right)))
    importer = evidence / 'maternalbound_town_maps-dev18-private.py'
    if importer.exists():
        raise ValueError('Importer already frozen')
    shutil.copy2(candidate / 'tools/maternalbound_town_maps.py', importer)
    runtime = json_read(candidate / 'runtime-provenance.json')
    proposal = dict(
        toolSha256=sha(__file__), profile='Redux', privateOnly=True,
        integratedIntoSharedSources=False, releaseCandidate=False, ownerWrites=False,
        pinnedReduxCommit=reports['family']['pinnedReduxCommit'],
        compiledRomSha256=reports['family']['compiledRomSha256'],
        baselinePackSha256=sha(old_pack), proposedPackSha256=sha(new_pack),
        assetRegistrySha256=sha(ids), registryAssets=len(entries),
        namespaceAndHeaderUnchanged=old_header == new_header and entries == new_entries,
        changedAssetCount=len(changed), unchangedAssetCount=len(entries)-len(changed),
        allowedChangedAssetIds=sorted(allowed), changedAssets=changed,
        sourcePatches=patches, newImporter=identity(importer),
        privateRuntime=runtime,
        productionReports={key: identity(ROOT / report_names[key]) for key in ('reduxPrivateGreen', 'originalPrivateControl')},
        preparedCases=sum(reports[key]['preparedCases'] for key in ('reduxPrivateGreen', 'originalPrivateControl')),
        executedAssertions=sum(reports[key]['executedAssertions'] for key in ('reduxPrivateGreen', 'originalPrivateControl')),
        skippedCases=0, allPassed=True,
        changes=[
            'Import each of six Town Map streams from actual compiled E02190 pointer table, and the source label stream from C4D62F.',
            'Prove all source map upper 256 tiles are zero and unreferenced, then normalize map decompression to 18496 bytes for the native 20KB buffer.',
            'Keep native bounded 16384-byte tile copy and clear the additional 8192 VRAM bytes only in Redux, matching source C4D625 upload.',
            'Preserve all six shared icon/placement/mapping/palette tables and both game-over art families unchanged.',
        ],
        independentControls=['Original private consumer passes 56 assertions.',
            'Real Redux six-map render/upload/reload exits and source labels pass 56 assertions.',
            'Source game-over packing differences produced identical actual BG1 images for Ness and Jeff; no importer change justified.'],
        remainingIntegration=['Root must lease/adopt source and importer changes separately.',
            'Real setup regeneration and content-identity/phone/F6 migration are not established by this private candidate.',
            'The private observer is only a player alias and was not tested; shipping observer requires a real coherent build.',
            'Owning Goods/X-button callers, item acquisition, natural story progression, whole-screen visual parity and full game-over comeback dialogue are outside these prepared fixtures.'],
    )
    put_json('research/redux-town-map-dev18-private-candidate-review.json', proposal)
    family = reports['family']
    frozen = dict(
        toolSha256=sha(__file__), checkpoint='dev.17-v4',
        evidenceReports={key: identity(ROOT / path) for key, path in report_names.items()},
        evidenceTools=[identity(ROOT / path) for path in tools],
        previousConverters=[identity(evidence / 'maternalbound_graphics-dev17-v4.py'), identity(evidence / 'build_maternalbound_pack-dev17-v4.py')],
        privateProposal=identity(ROOT / 'research/redux-town-map-dev18-private-candidate-review.json'),
        registryAssets=family['registryAssets'], importerAssignedDistinctAssets=family['importerAssignedDistinctAssets'],
        assignedButByteIdenticalToDonor=family['assignedButByteIdenticalToDonor'], changedBytesAssets=family['changedBytesAssets'],
        unassignedDonorAssets=family['unassignedDonorAssets'], zeroMatchRegistrySelectors=len(family['silentlyZeroMatchSelectors']),
        familyInventoryPassed=True, conversionCompletionPercentage=None, fullConversionVerified=False,
        confirmedMissingSemantics=['Town Map base image pixels on maps 0/2/4 differ 43/48/115 from compiled Redux source.',
            'Labels differ under actual native PPU source-label-only controls on all six prepared maps.',
            'Source 0x6000-byte map tile upload/zero-tail was omitted from native 0x4000-byte donor upload.'],
        qualifiedFindings=['Six unassigned Town Map streams are a source omission; only three have visible base image differences in tested frames.',
            'Raw game-over gfx/arr differ from relocated compiled source, but actual Ness/Jeff BG1 renders match; this is tile packing, not a demonstrated visual defect.',
            'Nintendo/APE/HALKEN, Produced/Presented and gas-station raw differences remain consumer-layout triage; no missing runtime semantics claim.',
            '347 unassigned assets include intentionally shared or shadowed families; assignment counts are not a completion metric.'],
        ownerWrites=False, redistributableGameAssetsIncluded=False,
    )
    put_json('research/converter-family-dev21-dev17-v4-manifest.json', frozen)
    print(json.dumps(dict(changedAssets=changed, proposedPackSha256=sha(new_pack),
                          originalPrivatePassed=True, reduxPrivatePassed=True,
                          proposal=identity(ROOT / 'research/redux-town-map-dev18-private-candidate-review.json'),
                          manifest=identity(ROOT / 'research/converter-family-dev21-dev17-v4-manifest.json'))))


if __name__ == '__main__':
    main()
