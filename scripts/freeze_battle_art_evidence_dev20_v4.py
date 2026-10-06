# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze public hash-only provenance for the bounded dev20 battle-art audit."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, default=ROOT/'research/battle-art-dev20-dev17-v4-final-manifest.json')
    a = p.parse_args()
    reports = {
        'graphicsRed': 'research/redux-battle-art-dev20-v9-red-review.json',
        'paletteRed': 'research/redux-battle-art-dev20-v9-palette-red-review.json',
        'originalFinal': 'research/original-battle-art-dev20-dev17-v4-final-review.json',
        'reduxFinal': 'research/redux-battle-art-dev20-dev17-v4-final-review.json',
        'coldFinal': 'research/redux-battle-art-dev20-dev17-v4-cold-review.json',
        'finalPackDiff': 'research/redux-battle-art-dev20-final-pack-change-review.json',
    }
    loaded = {key: json.loads((ROOT/path).read_text()) for key, path in reports.items()}
    artifacts = list(reports.values()) + [
        'tools/battle_art_decode_qa_dev20.py',
        'tools/battle_art_cold_qa_dev20.py',
        'tools/freeze_battle_art_evidence_dev20_v4.py',
        'tools/battle_action_catalog_qa.py',
        'tools/build_maternalbound_pack.py',
        'tools/maternalbound_graphics.py',
        'research/evidence-tools/maternalbound_graphics-dev16-v9.py',
        'research/evidence-tools/maternalbound_graphics-dev20-graphics-only.py',
        'research/evidence-tools/battle_art_decode_qa_dev20-v9-red.py',
        'research/evidence-tools/battle_art_decode_qa_dev20-v9-palette-red.py',
    ]
    identities = {path: digest(ROOT/path) for path in artifacts}
    expected_tools = {
        'graphicsRed': 'research/evidence-tools/battle_art_decode_qa_dev20-v9-red.py',
        'paletteRed': 'research/evidence-tools/battle_art_decode_qa_dev20-v9-palette-red.py',
        'originalFinal': 'tools/battle_art_decode_qa_dev20.py',
        'reduxFinal': 'tools/battle_art_decode_qa_dev20.py',
        'coldFinal': 'tools/battle_art_cold_qa_dev20.py',
    }
    for key, tool in expected_tools.items():
        if loaded[key]['toolSha256'] != identities[tool]:
            raise ValueError('Evidence tool identity mismatch: '+key)
    if loaded['coldFinal']['artToolSha256'] != identities['tools/battle_art_decode_qa_dev20.py']:
        raise ValueError('Cold evidence dependency identity mismatch')
    final_keys = ('originalFinal', 'reduxFinal', 'coldFinal')
    if any(not loaded[key]['allPassed'] for key in final_keys):
        raise ValueError('Final assertions failed')
    diff = loaded['finalPackDiff']
    if diff['changedAssetCount'] != 107 or not diff['allChangesAllowed'] or not diff['namespaceAndIdsUnchanged']:
        raise ValueError('Unexpected pack change scope')
    if diff['newConverterSha256'] != identities['tools/maternalbound_graphics.py']:
        raise ValueError('Final converter changed since private pack build')
    native = [loaded[key].get('nativeProvenance', loaded[key].get('provenance')) for key in final_keys]
    if len({x['productionLibrarySha256'] for x in native}) != 1:
        raise ValueError('Final native libraries differ')
    result = {
        'audit': 'Packed battle backgrounds and PSI animation data/production consumers',
        'pinnedReduxCommit': '897d00833f4a08a0a92f106abf631629a6a6a041',
        'allPassed': True,
        'executedAssertions': sum(loaded[key]['executedAssertions'] for key in final_keys),
        'nativePreparedCases': sum(loaded[key]['nativeExecutedCases'] for key in ('originalFinal','reduxFinal')),
        'coldProcesses': loaded['coldFinal']['executedCases'],
        'playedPsiFrames': sum(loaded[key]['nativeRenderedPsiFrames'] for key in ('originalFinal','reduxFinal')),
        'skippedCases': sum(loaded[key]['skippedCases'] for key in final_keys),
        'reports': reports,
        'artifactSha256': identities,
        'runtimeIdentities': loaded['reduxFinal']['runtimeIdentities'],
        'productionLibrarySha256': native[0]['productionLibrarySha256'],
        'productionPlatformMainObjectSha256': native[0]['platformMainObjectSha256'],
        'completeNativePatchSha256': digest(ROOT/'_BuildScratch/audit-dev17-v4-source/native-companion.patch'),
        'nativeSourceIdentities': loaded['reduxFinal']['sourceIdentities'],
        'originalPackSha256': loaded['originalFinal']['packSha256'],
        'legacyReduxPackSha256': diff['oldPackSha256'],
        'correctedReduxPackSha256': diff['newPackSha256'],
        'compiledReduxRomSha256': loaded['reduxFinal']['romSha256'],
        'originalRomSha256': loaded['originalFinal']['romSha256'],
        'registrySha256': diff['registrySha256'],
        'changedAssetCount': 107,
        'changedGraphicsAssets': 103,
        'changedPaletteIds': [x['assetId'] for x in diff['changedAssets'] if '/palettes/' in x['asset']],
        'redEvidence': {
            'graphics': {
                'runtimeLibrarySha256': loaded['graphicsRed']['nativeProvenance']['productionLibrarySha256'],
                'failedNativeBackgroundGraphicsRecords': sum(not x['passed'] for x in loaded['graphicsRed']['checks'] if x['check'].startswith('native-background-source-graphics-')),
                'reason': 'Importer matched battle_bgs/gfx instead of the real battle_bgs/graphics registry family; Redux arrangements referenced retained Original tiles.',
            },
            'palette': {
                'runtimeLibrarySha256': loaded['paletteRed']['nativeProvenance']['productionLibrarySha256'],
                'failedNativeBackgroundPaletteRecords': sum(not x['passed'] for x in loaded['paletteRed']['checks'] if x['check'].startswith('native-background-source-palette-')),
                'reason': 'Palette source pointers were correct but donor lengths were reused after Redux reassigned palette IDs; active 4bpp records lost colors 4 through 13.',
            },
        },
        'correctionScope': 'Only tools/maternalbound_graphics.py graphics-family match, expected size branch and compiled-consumer palette width import. Exact 107-asset diff; native C, namespace and registry IDs unchanged by this correction.',
        'coldCheckpointLimit': 'Prepared real background 284 and native BW_FRAMES format16 save/load. Cached old art and exact continuation stay unchanged on cold restore under the corrected pack; next actual load_battle_bg refresh matches pinned source. No full natural battle continuation or owner-save coverage claimed.',
        'coverageLimits': loaded['reduxFinal']['coverageLimits'],
        'reproduction': [
            'Use battle_art_decode_qa_dev20.py with each owner-provided ROM/pack and matching immutable --build/--runtime. --redux selects pinned Redux tables. Each --scratch must be new.',
            'Use battle_art_cold_qa_dev20.py with --old-assets, --new-assets and --compiled-rom plus the same immutable native build/runtime. No owner saves are used.',
            'Archived red QA tools and old converter revisions retain their exact recorded SHA. Run archived tools with tools on PYTHONPATH and an explicit --native-source; their default ROOT is archive-relative.',
            'Final pack is built locally with build_maternalbound_pack.py from the source ROM, pinned compiled Redux ROM, bridge and converted dialogue inputs. No ROM, pack, decoded graphics, palette bytes or saves appear in these public reports.',
        ],
        'ownerWrites': False,
        'fullVisualParityVerified': False,
        'naturalFullPlaythroughVerified': False,
    }
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'allPassed':True, 'executedAssertions':result['executedAssertions'], 'nativePreparedCases':result['nativePreparedCases'], 'coldProcesses':result['coldProcesses'], 'playedPsiFrames':result['playedPsiFrames'], 'manifestSha256':digest(a.output)}))


if __name__ == '__main__':
    main()
