# SPDX-License-Identifier: GPL-3.0-or-later
"""Combine frozen private name-label and Give fixes in a fresh private source tree."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
from check_jev_observer_parity import local_scratch

ROOT = Path(__file__).resolve().parents[1]
NAME_MANIFEST = '6a78010ad85fc17c2769ca6870454a2eca8e52256db252c72db876a9e71aa0f2'
GEAR_MANIFEST = '2388d8696ae6766db50e5df905bca51ca22679477d5a0ea3cf11365fcf64234a'
NAMES = ('src/game/battle.c', 'src/game/display_text.c', 'src/game/window.c')
INVENTORY = 'src/game/inventory.c'
OLD_COMMENT = (' * Other menus, dialogue, right labels and the HPPP Give picker stay ASCII. */')
NEW_COMMENT = (' * Other menus, dialogue and right labels keep their existing ASCII decoding;\n'
               ' * the HPPP Give picker uses its separate raw-name renderer. */')

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def tree(path):
    return {p.relative_to(path).as_posix(): sha(p) for p in path.rglob('*') if p.is_file()}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline-source', 'party-source', 'gear-source', 'candidate-source', 'output'):
        ap.add_argument('--' + name, type=Path, required=True)
    a = ap.parse_args()
    for name, value in vars(a).items():
        setattr(a, name, value.resolve())
    a.candidate_source = local_scratch(a.candidate_source)
    if a.candidate_source.exists() or a.output.exists():
        raise ValueError('Fresh private source/report paths are required')
    nm = ROOT / 'research/party-name-label-dev19-private-final-manifest.json'
    gm = ROOT / 'research/equipped-give-qol-dev26-private-manifest.json'
    if sha(nm) != NAME_MANIFEST or sha(gm) != GEAR_MANIFEST:
        raise ValueError('Frozen proposal identity changed')
    names, gear = load(nm), load(gm)
    before = tree(a.baseline_source)
    for row in names['changedFiles']:
        if before[row['path']] != row['baselineSha256'] or sha(a.party_source / row['path']) != row['candidateSha256']:
            raise ValueError('Name source/baseline identity mismatch')
    provenance = gear['candidateProvenance']
    if before[INVENTORY] != provenance['baselineSourceSha256'] or sha(a.gear_source) != provenance['candidateSourceSha256']:
        raise ValueError('Gear source/baseline identity mismatch')
    shutil.copytree(a.baseline_source, a.candidate_source)
    for name in NAMES:
        shutil.copy2(a.party_source / name, a.candidate_source / name)
    shutil.copy2(a.gear_source, a.candidate_source / INVENTORY)
    win = a.candidate_source / NAMES[2]
    text = win.read_text(encoding='utf-8')
    if text.count(OLD_COMMENT) != 1:
        raise ValueError('Reviewed HPPP comment boundary changed')
    win.write_bytes(text.replace(OLD_COMMENT, NEW_COMMENT, 1).encode('utf-8'))
    comment_diff = ''.join(difflib.unified_diff(
        (a.party_source / NAMES[2]).read_text(encoding='utf-8').splitlines(True),
        win.read_text(encoding='utf-8').splitlines(True),
        fromfile='frozen-party-proposal/' + NAMES[2], tofile='combined-candidate/' + NAMES[2]))
    if win.read_text(encoding='utf-8').replace(NEW_COMMENT, OLD_COMMENT, 1) != (a.party_source / NAMES[2]).read_text(encoding='utf-8'):
        raise ValueError('Combined party-name changes extend beyond the comment')
    after = tree(a.candidate_source)
    changes = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    if changes != sorted((*NAMES, INVENTORY)) or tree(a.baseline_source) != before:
        raise ValueError('Combined source exceeded four-file lease or changed the frozen base')
    report = dict(schemaVersion=1, proof='private-combined-menu-gear-dev19-source-preparation',
                  privateOnly=True, baseCheckpoint='dev18-v2',
                  baselineSource=str(a.baseline_source), candidateSource=str(a.candidate_source),
                  sourceFileCount=len(before), onlyFourAuthorizedSourceFilesChanged=True,
                  files=[dict(path=p, baselineSha256=before[p], candidateSha256=after[p]) for p in changes],
                  frozenInputs=[dict(path=str(p.relative_to(ROOT)), sha256=sha(p)) for p in (nm, gm)],
                  commentOnlyDifferenceFromPartyProposal=dict(file=NAMES[2], diff=comment_diff,
                    frozenSourceSha256=sha(a.party_source / NAMES[2]), candidateSourceSha256=sha(win),
                    checkedReverseReplacementEqualsFrozenProposal=True),
                  gearFix=dict(symbol='swap_item_into_equipment', exactFrozenInventoryCandidate=True,
                    intentionalOriginalSourceBugCorrection=True, lineEndingNormalizationFromFrozenCandidate=True),
                  rootOrOwnerInputsModified=False, toolSha256=sha(Path(__file__)))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(report=str(a.output), reportSha256=sha(a.output), files=report['files'])), flush=True)

if __name__ == '__main__':
    main()
