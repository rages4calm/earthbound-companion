# SPDX-License-Identifier: GPL-3.0-or-later
"""Run frozen party-name and equipped-Give suites on complete private paired builds.

No native replacement objects are used. Explicit local packs remain read only;
every output and capture requires a fresh private destination.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from check_jev_observer_parity import local_scratch

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for n in ('source', 'builds', 'runtime', 'original-assets', 'redux-assets', 'project', 'scratch', 'output'):
        ap.add_argument('--' + n, type=Path, required=True)
    ap.add_argument('--label', default='combined-menu-gear-dev19-v1')
    ap.add_argument('--parallel', type=int, default=3)
    a = ap.parse_args()
    for n, v in vars(a).items():
        if isinstance(v, Path):
            setattr(a, n, v.resolve())
    a.scratch = local_scratch(a.scratch)
    if a.scratch.exists() or a.output.exists():
        raise ValueError('Fresh private scratch and report are required')
    if not a.label.replace('-', '').isalnum() or a.parallel not in range(1, 5):
        raise ValueError('Review label or parallelism')
    a.scratch.mkdir(parents=True)
    original_hashes = {str(p): sha(p) for p in (a.original_assets, a.redux_assets,
        a.source / 'src/game/inventory.c', a.runtime / 'player.exe', a.runtime / 'observer.exe',
        a.builds / 'player/game_lib/libearthbound_game.a', a.builds / 'observer/game_lib/libearthbound_game.a')}
    jobs = []
    for suite, tool, extra in (('party-parents', 'party_name_parents_qa_dev19.py', []),
        ('party-services', 'party_name_parents_qa_dev19.py', ['--services']),
        ('party-controls', 'party_name_label_controls_dev19.py', [])):
        output = ROOT / 'research' / (a.label + '-' + suite + '-review.json')
        cmd = [sys.executable, str(ROOT / 'tools' / tool), '--source', str(a.source),
            '--builds', str(a.builds), '--runtime', str(a.runtime),
            '--original-assets', str(a.original_assets), '--redux-assets', str(a.redux_assets),
            '--scratch', str(a.scratch / suite), '--output', str(output), *extra]
        jobs.append(dict(id=suite, kind='party', command=cmd, output=output))
    for mode in ('player', 'observer'):
        if sha(a.builds / mode / 'earthbound.exe') != sha(a.runtime / (mode + '.exe')):
            raise ValueError('Paired build/runtime identity mismatch: ' + mode)
        for profile, pack in (('original', a.original_assets), ('redux', a.redux_assets)):
            suite = 'gear-' + mode + '-' + profile
            output = ROOT / 'research' / (a.label + '-' + suite + '-review.json')
            fixtures = ROOT / 'research' / (profile + '-equipped-give-fixtures-dev26-private-final.json')
            cmd = [sys.executable, str(ROOT / 'tools/equipped_give_qa_dev26.py'),
                '--build', str(a.builds / mode), '--native-source', str(a.source),
                '--executed-source', str(a.source), '--assets', str(pack), '--runtime', str(a.runtime),
                '--project', str(a.project), '--cases', str(fixtures), '--scratch', str(a.scratch / suite),
                '--output', str(output), '--jobs', '3', *(['--original'] if profile == 'original' else [])]
            jobs.append(dict(id=suite, kind='gear', command=cmd, output=output, mode=mode,
                profile=profile, fixtures=fixtures, fixtureSha256=sha(fixtures)))
    if any(j['output'].exists() for j in jobs):
        raise ValueError('Fresh suite output paths are required')
    def run(job):
        log = a.scratch / (job['id'] + '.log')
        with log.open('wb') as stream:
            p = subprocess.run(job['command'], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=1800)
        if p.returncode or not job['output'].is_file():
            raise RuntimeError(job['id'] + ' failed; private log: ' + str(log))
        report = load(job['output'])
        if job['kind'] == 'party':
            passed = report.get('nativeControlsPassed', True) and report.get('sourceExpectedPassed', report.get('allPassed', False))
            rows = report['results']
            cases = len(rows)
            cold = sum(bool(x.get('cold')) for x in rows)
            controls = sum(len(x.get('observations', [])) for x in rows) if job['id'] == 'party-controls' else 0
            result = dict(id=job['id'], cases=cases, cold=cold, boundedObservations=controls,
                output=str(job['output'].relative_to(ROOT)), sha256=sha(job['output']), passed=passed,
                command=job['command'], logSha256=sha(log))
        else:
            expected = load(job['fixtures'])
            if [r['fixture'] for r in report['cases']] != expected:
                raise ValueError('Frozen dev26 fixture order/content changed')
            link = report['privateBuild']
            if link['productionExecutableSha256'] != sha(a.runtime / (job['mode'] + '.exe')) or \
               link['productionLibrarySha256'] != sha(a.builds / job['mode'] / 'game_lib/libearthbound_game.a'):
                raise ValueError('Gear driver did not link the requested complete paired build')
            if report['privateCorrectedInventory'] or 'correctedInventory' in link:
                raise ValueError('Unexpected native replacement object')
            upstream_limits = report['limits']
            report.update(combinedCandidateQualification=dict(executedBuildMode=job['mode'],
                fullIntegratedNativeCandidate=True, inventoryCorrectionCompiledInCompleteArchive=True,
                optionalPrivateInventoryReplacementUsed=False, actualObserverArchiveExecuted=job['mode'] == 'observer',
                wrapperToolSha256=sha(Path(__file__)), frozenFixturePath=str(job['fixtures'].relative_to(ROOT)),
                frozenFixtureSha256=job['fixtureSha256']), upstreamFrozenRunnerLimits=upstream_limits,
                limits=['Complete private paired candidate: this report executes the explicitly named player/observer archive plus its matching platform objects, without replacing native handlers. The frozen optional-replacement flag remains false because the reviewed inventory correction is compiled into the complete archive.',
                    'Selected actual Goods/Give/Drop/Equip/Use parents prepare party and contiguous bag/gear prerequisites before OPEN_MENU; production menus, platform input, text children, effects and fresh-process save16 continuations run afterward.',
                    'Desired equipment identity, stats, miss/resistance fields and complete inventory/pool/storage/delivery/wallet outcomes remain intentional QoL postconditions, distinct from Original-source parity. Full story/natural map/controller reachability, every item/stat/save boundary and delivered pixels/audio are unproved.'])
            job['output'].write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
            result = dict(id=job['id'], mode=job['mode'], profile=job['profile'], cases=len(report['cases']),
                cold=sum(bool(r['fixture'].get('checkpoint')) for r in report['cases']),
                warmColdComparisons=len(report['warmColdGearComparisons']),
                output=str(job['output'].relative_to(ROOT)), sha256=sha(job['output']),
                passed=report['allPassed'] and all(r['passed'] for r in report['warmColdGearComparisons']),
                command=job['command'], fixtureSha256=job['fixtureSha256'], logSha256=sha(log))
        if not result['passed']:
            raise ValueError('Combined suite is not green: ' + job['id'])
        print(json.dumps(result), flush=True)
        return result
    with ThreadPoolExecutor(max_workers=a.parallel) as pool:
        results = list(pool.map(run, jobs))
    if any(sha(Path(p)) != value for p, value in original_hashes.items()):
        raise ValueError('Immutable candidate input changed during QA')
    report = dict(schemaVersion=1, proof='private-combined-menu-gear-dev19-v1-execution', privateOnly=True,
        source=str(a.source), builds=str(a.builds), runtime=str(a.runtime), checks=results,
        allPassed=all(r['passed'] for r in results), toolSha256=sha(Path(__file__)),
        candidateInputsUnchanged=True, rootOrOwnerInputsModified=False,
        counts=dict(partyParentSequences=sum(r['cases'] for r in results if r['id'] in ('party-parents', 'party-services')),
            partyColdContinuations=sum(r['cold'] for r in results if r['id'] in ('party-parents', 'party-services')),
            boundedNativeObservations=sum(r.get('boundedObservations', 0) for r in results),
            gearParentSequences=sum(r['cases'] for r in results if r['id'].startswith('gear-')),
            gearColdContinuations=sum(r['cold'] for r in results if r['id'].startswith('gear-')),
            gearWarmColdComparisons=sum(r.get('warmColdComparisons', 0) for r in results)),
        fullConversionVerified=False, fullPlaythroughVerified=False)
    a.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(report=str(a.output), sha256=sha(a.output), counts=report['counts'], allPassed=report['allPassed'])), flush=True)

if __name__ == '__main__':
    main()
