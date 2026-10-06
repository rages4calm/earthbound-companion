# SPDX-License-Identifier: GPL-3.0-or-later
"""Combine exact frozen Original movement/restore checks into a public report."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reports', nargs='+', type=Path, required=True)
    for name in ('pack-review', 'baseline-red', 'checkpoint-red', 'frozen-source', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    records = [json.loads(path.read_text()) for path in a.reports]
    pack = json.loads(a.pack_review.read_text())
    runtime_ids = {json.dumps(r['runtimeSha256'],sort_keys=True) for r in records}
    libraries = {r['privateBuild']['productionLibrarySha256'] for r in records}
    if len(runtime_ids) != 1 or len(libraries) != 1:
        raise ValueError('Final records must execute exactly one immutable runtime/library pair.')
    for record in records:
        for name, expected in record['sourceFiles'].items():
            source = a.frozen_source/name
            if source.exists() and digest(source).lower() != expected.lower():
                raise ValueError('Final test source differs from frozen snapshot: '+name)
    passed = pack['allPassed'] and all(r['allPassed'] for r in records)
    baseline = json.loads(a.baseline_red.read_text())
    stale = json.loads(a.checkpoint_red.read_text())
    output = {'format':'event-interpreter-original-ghost-review-v1', 'Passed':passed, 'allPassed':passed,
              'executedCases':sum(r['executedCases'] for r in records)+pack['executedCases'],
              'executedAssertions':sum(r['executedAssertions'] for r in records)+pack['executedAssertions'],
              'skippedCases':sum(r['skippedCases'] for r in records)+pack['skippedCases'],
              'scope':'Original EVENT786 extraction/normal possession, stable script-bank indices, narrowly guarded old checkpoint repair; Redux unchanged-content controls.',
              'runtimeSha256':records[0]['runtimeSha256'], 'productionLibrarySha256':next(iter(libraries)),
              'pinnedReduxRevision':records[0]['sourceRevision'],
              'toolSha256':{'event_interpreter_gap_qa.py':digest(Path(__file__).with_name('event_interpreter_gap_qa.py')),
                            'original_movement_pack_qa.py':digest(Path(__file__).with_name('original_movement_pack_qa.py')),
                            'summarize_event_interpreter_gap_qa.py':digest(Path(__file__))},
              'sourceFiles':records[0]['sourceFiles'],
              'packReview':pack,
              'baseline':{'originalMissingRegion':{'privateReportSha256':digest(a.baseline_red),
                  'runtimeSha256':baseline['runtimeSha256'], 'packSha256':baseline['packSha256'],
                  'allPassed':baseline['allPassed'], 'structuralErrors':baseline['static']['Errors'],
                  'cases':[{k:c[k] for k in ('possessed','actual','errors','warnings')} for c in baseline['cases']]},
                  'oldCheckpointBeforeRepair':{'privateReportSha256':digest(a.checkpoint_red),
                  'runtimeSha256':stale['runtimeSha256'], 'allPassed':stale['allPassed'],
                  'cases':[{k:c[k] for k in ('possessed','actual','errors','warnings','checkpoint')} for c in stale['cases']]}},
              'finalChecks':[{'label':path.stem.split('-proof-')[-1], 'reportSha256':digest(path), 'report':record}
                             for path,record in zip(a.reports,records)],
              'limits':['Movement pointer-root coverage is structural bytecode reachability and recognized operands/targets, not complete story-semantic or audiovisual parity.',
                        'Normal and cold restored possession executes actual prepared home overworld roots for96 host frames; this is not a full playthrough.',
                        'Actual private old v6 checkpoints use normal save/load-slots production APIs. All party/story/inventory/GameState and event-flag bytes are compared immediately after restore.',
                        'Standalone EVENT859 checkpoint proves old title bank2/PC1581 binding and bounded execution; it has no normal V4 fade prerequisites, so ghost motion is intentionally excluded there and tested in the normal checkpoint separately.',
                        'Wrong-event, wrong-sprite and Redux invalid-marker checks are deliberately prepared negative fixtures. They prove restore leaves excluded markers unchanged, not that those artificial states should play normally.',
                        'Legacy naked Original C3 packs remain accepted with their known missing ghost. Local owner-ROM regeneration supplies that bytecode; it is never embedded in release executables.',
                        'No ROM/pak/bytecode/PCM/save content is included in this report. Observer hash is provenance; private drivers execute the player platform/library.']}
    a.output.write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:output[k] for k in ('allPassed','executedCases','executedAssertions','skippedCases')}))
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
