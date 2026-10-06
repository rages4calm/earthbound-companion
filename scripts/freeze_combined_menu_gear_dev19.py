# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze a four-file private candidate and exact combined paired QA evidence."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
from prepare_combined_menu_gear_dev19 import sha, tree, load, NAMES, INVENTORY, OLD_COMMENT, NEW_COMMENT

ROOT = Path(__file__).resolve().parents[1]

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for n in ('baseline-source', 'candidate-source', 'baseline-runtime', 'candidate-runtime', 'builds',
              'source-review', 'build-review', 'execution-review', 'original-assets', 'redux-assets', 'patch', 'manifest'):
        ap.add_argument('--' + n, type=Path, required=True)
    a = ap.parse_args()
    for n, v in vars(a).items():
        setattr(a, n, v.resolve())
    if a.patch.exists() or a.manifest.exists():
        raise ValueError('Fresh final outputs are required')
    baseline, candidate = tree(a.baseline_source), tree(a.candidate_source)
    changes = sorted(p for p in baseline.keys() | candidate.keys() if baseline.get(p) != candidate.get(p))
    if changes != sorted((*NAMES, INVENTORY)):
        raise ValueError('Four-file source lease exceeded')
    source, builds, execution = load(a.source_review), load(a.build_review), load(a.execution_review)
    if source['files'] != [dict(path=p, baselineSha256=baseline[p], candidateSha256=candidate[p]) for p in changes]:
        raise ValueError('Candidate source changed after preparation')
    counts = dict(partyParentSequences=128, partyColdContinuations=64, boundedNativeObservations=360,
                  gearParentSequences=732, gearColdContinuations=116, gearWarmColdComparisons=116)
    if execution['counts'] != counts or not execution['allPassed'] or len(execution['checks']) != 7:
        raise ValueError('Combined paired execution is incomplete or not green')
    for row in builds['results']:
        mode = row['mode']
        if row['executableSha256'] != sha(a.candidate_runtime / (mode + '.exe')) or \
           row['archiveSha256'] != sha(a.builds / mode / 'game_lib/libearthbound_game.a'):
            raise ValueError('Complete paired build identity changed')
    if len(builds['results']) != 2 or sha(a.candidate_runtime / 'player.exe') == sha(a.candidate_runtime / 'observer.exe'):
        raise ValueError('Distinct paired complete executables are required')
    checks = []
    prior = load(ROOT / 'research/party-name-controls-dev19-v2-red-r2-review.json')
    controls_job = next(r for r in execution['checks'] if r['id'] == 'party-controls')
    current = load(ROOT / controls_job['output'])
    for old, new in zip(prior['results'], current['results']):
        if (old['build'], old['profile'], old['names']) != (new['build'], new['profile'], new['names']):
            raise ValueError('Bounded controls do not pair')
        generic = all(x == y for x, y in zip(old['observations'], new['observations']) if x['test'].startswith('generic'))
        ascii_rows = old['profile'] != 'original' and old['names'] != 'ascii' or old['observations'] == new['observations']
        title = old['titleControl'] == new['titleControl']
        hppp = old['hpppControl'] == new['hpppControl']
        structs = old['structures'] == new['structures']
        if not all((generic, ascii_rows, title, hppp, structs)):
            raise ValueError('Generic/title/HPPP/structure/ASCII control changed')
        checks.append(dict(build=new['build'], profile=new['profile'], names=new['names'],
            genericAsciiRendererUnchanged=generic, originalAndAsciiNameRowsUnchanged=ascii_rows,
            tinyTitleActualVramUnchanged=title, hpppNameGlyphPlanesUnchanged=hppp,
            serializedStructureSizesUnchanged=structs))
    if len(checks) != 8:
        raise ValueError('Missing bounded paired controls')
    # Bind reported driver links to both actual full archives, not replacement objects.
    link_count = 0
    for row in execution['checks']:
        report_path = ROOT / row['output']
        if sha(report_path) != row['sha256']:
            raise ValueError('Executed suite metadata changed')
        report = load(report_path)
        for observation in report.get('results', []):
            mode = observation['build']
            link = observation['link']
            if link['productionExecutableSha256'] != sha(a.candidate_runtime / (mode + '.exe')) or \
               link['productionLibrarySha256'] != sha(a.builds / mode / 'game_lib/libearthbound_game.a'):
                raise ValueError('Party driver link does not match complete build')
            link_count += 1
        if row['id'].startswith('gear-'):
            q = report['combinedCandidateQualification']
            if q['optionalPrivateInventoryReplacementUsed'] or not q['inventoryCorrectionCompiledInCompleteArchive']:
                raise ValueError('Gear proof used a private replacement object')
            if len(report['cases']) != 183 or len(report['warmColdGearComparisons']) != 29:
                raise ValueError('Gear corpus incomplete')
            link_count += 1
    patch = ''.join(''.join(difflib.unified_diff(
        (a.baseline_source / p).read_text(encoding='utf-8').splitlines(True),
        (a.candidate_source / p).read_text(encoding='utf-8').splitlines(True),
        fromfile='a/' + p, tofile='b/' + p)) for p in changes)
    a.patch.write_text(patch, encoding='utf-8', newline='')
    frozen_manifests = ['research/party-name-label-dev19-private-final-manifest.json',
                        'research/equipped-give-qol-dev26-private-manifest.json']
    paths = set(frozen_manifests)
    for path in frozen_manifests:
        frozen = load(ROOT / path)
        for row in frozen['files']:
            p = row['path'].replace('\\', '/')
            if sha(ROOT / p) != row['sha256']:
                raise ValueError('Frozen independent evidence changed: ' + p)
            paths.add(p)
    paths.update(row['output'].replace('\\', '/') for row in execution['checks'])
    paths.update(str(p.relative_to(ROOT)).replace('\\', '/') for p in
        (a.source_review, a.build_review, a.execution_review, a.patch))
    paths.update(('tools/prepare_combined_menu_gear_dev19.py', 'tools/combined_menu_gear_qa_dev19.py',
                  'tools/freeze_combined_menu_gear_dev19.py', 'tools/build_title_private_dev18.py'))
    files = [dict(path=p, sha256=sha(ROOT / p), bytes=(ROOT / p).stat().st_size) for p in sorted(paths)]
    manifest = dict(schemaVersion=1, proof='private-combined-menu-gear-dev19-v1-final', privateOnly=True,
        baseCheckpoint='dev18-v2', upstreamRevision='897d00833f4a08a0a92f106abf631629a6a6a041',
        changedFiles=source['files'], baselineSourceFileCount=len(baseline),
        onlyFourAuthorizedSourceFilesChanged=True, otherSourceFilesByteIdentical=True,
        commentOnlyDifferenceFromFrozenPartyProposal=source['commentOnlyDifferenceFromPartyProposal'],
        equipmentChangeIntentionalOriginalSourceQoL=True, schemasAndSaveFormat16Unchanged=True,
        completeDistinctPairedBuilds=True, nativeReplacementObjectsUsed=False,
        builds=builds['results'], runtimes={name: {n: sha(p / n) for n in ('player.exe', 'observer.exe', 'SDL2.dll')}
            for name, p in (('baselineDev18V2', a.baseline_runtime), ('privateCombinedDev19', a.candidate_runtime))},
        packs={name: sha(p) for name, p in (('original', a.original_assets), ('redux', a.redux_assets))},
        counts=dict(**counts, gearDistinctFrozenFixtures=366, gearExecutionsPerBinary=366),
        allSelectedCombinedTestsPassed=True, controls=checks,
        sourceArchiveLinkIdentityChecks=link_count, files=files,
        independentRedBaselinesPreserved=True, rootOrOwnerInputsModified=False,
        fullConversionVerified=False, fullPlaythroughVerified=False,
        reproduction=execution['checks'],
        limits=['128 selected real Goods/Give/PSI/doctor/nurse/healer name parents include64 fresh-process save16 continuations. 360 bounded producer/render/highlight observations are unit/integration controls, not extra naturally reached story parents.',
            'The366 frozen dev26 fixtures execute once per complete player/observer library:732 parent executions and116 cold continuations/explicit warm-cold gear comparisons. Distinct fixture count is366. No replacement native objects are used.',
            'Give mode2 remains its separate raw-name/HPPP renderer. Generic ASCII menus, existing tiny titles and serialized structures remain unchanged in explicit controls.',
            'The equipment changes intentionally correct Original-source self-Give/full-bag equipment location and post-compaction stat recalculation; they are not presented as missing Redux parity.',
            'Prepared legal party/name/inventory/status prerequisites precede actual input/menu/text/effect execution. Full natural story/map/controller reachability, every item/stat/save boundary, delivered audio, an original CPU fullUI execution and a full playthrough remain unproved.',
            'Existing pre-fix saved ordinary labels already containing question marks require reopening their parent menu; there is no migration or new save field.'])
    a.manifest.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(manifest=str(a.manifest), manifestSha256=sha(a.manifest), patch=str(a.patch),
        patchSha256=sha(a.patch), changedFiles=source['files'], counts=manifest['counts'], allPassed=True)), flush=True)

if __name__ == '__main__':
    main()
