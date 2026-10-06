# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze final integrated release-candidate presentation execution identities."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def identity(path):
    path=Path(path).resolve()
    return dict(path=str(path.relative_to(ROOT)).replace('\\','/'),sha256=sha(path))
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def main():
    output=ROOT/'research/presentation-release-dev18-v2-final-manifest.json'
    if output.exists():raise ValueError('Refusing to overwrite final frozen evidence')
    paths={key:ROOT/('research/'+name)for key,name in {
        'originalMap':'original-map-dev18-v2-final-review.json','reduxMap':'redux-map-dev18-v2-final-review.json',
        'originalIntro':'original-intro-dev18-v2-final-review.json','reduxIntro':'redux-intro-dev18-v2-final-review.json',
        'originalSequences':'original-sequence-dev18-v2-final-review.json','reduxSequences':'redux-sequence-dev18-v2-final-review.json',
        'originalSwirls':'original-swirl-dev18-v2-final-review.json','reduxSwirls':'redux-swirl-dev18-v2-final-review.json',
        'starmanAppearanceCold':'starman-parent-dev18-v2-final-review.json','swirlFullParentCold':'swirl-cold-dev18-v2-final-review.json',
        'originalFullEncounters':'original-encounter-dev18-v2-final-review.json','reduxFullEncounters':'redux-encounter-dev18-v2-final-review.json',
    }.items()}
    reports={key:read(path)for key,path in paths.items()}
    runtime=ROOT/'_BuildScratch/audit-dev18-v2-runtime';build=ROOT/'_BuildScratch/audit-dev18-v2-build/companion'
    player=sha(runtime/'player.exe');observer=sha(runtime/'observer.exe');library=sha(build/'game_lib/libearthbound_game.a')
    if player!='3b467f471acd6bb5aa0cb29b96d89790be3097d8d0c5dd114ce2f128895d6292' or observer!='033ed02642e0fc2cb61e2244de40c1b918f6b8e17635fb0c86eb7c11f92aeb92' or library!='6a2ea279a762df4c3a887eda7580e09c8034da55f08fb7f9059eb404c949d411':
        raise ValueError('Unexpected final frozen runtime identity')
    if sha(build/'earthbound.exe')!=player:raise ValueError('Executed build differs from final player')
    for key,report in reports.items():
        if not report['allPassed']:raise ValueError('Failed final proof: '+key)
        production=report.get('production',report.get('privateBuild'))
        for executed in production if isinstance(production,list)else[production]:
            if executed['productionExecutableSha256']!=player or executed['productionLibrarySha256']!=library:
                raise ValueError('Wrong executed production identity: '+key)
        if report.get('skippedCases',0):raise ValueError('Skipped final proof: '+key)
    counts={key:report['executedAssertions']for key,report in reports.items()if'executedAssertions'in report}
    if sum(counts.values())!=6794:raise ValueError('Unexpected counted final assertions')
    fullcases=sum(len(reports[key]['cases'])for key in ('originalFullEncounters','reduxFullEncounters'))
    if fullcases!=8:raise ValueError('Incomplete real encounter corpus')
    tools=[ROOT/'tools'/name for name in (
        'retained_presentation_qa_dev21.py','intro_retained_presentation_qa_dev22.py',
        'sequence_animation_consumer_qa_dev23.py','starman_appearance_parent_qa_dev23.py',
        'swirl_source_consumer_qa_dev24.py','swirl_transition_cold_qa_dev24.py',
        'battle_full_encounter_qa_dev18.py','freeze_presentation_release_evidence_dev18.py')]
    pack=ROOT/'_BuildScratch/swirl-import-dev18-candidate3/map-gas-teleport-swirl-candidate.pak'
    if sha(pack)!='d9a772d10aff68bdf93c077cda640d42b835884d6834bb18bf0d43c3800f57bb':raise ValueError('Wrong coherent candidate pack')
    record=dict(format='presentation-release-dev18-v2-final-v1',allPassed=True,
        evidenceReports={key:identity(path)for key,path in paths.items()},evidenceTools=[identity(path)for path in tools],
        runtime=dict(playerSha256=player,observerSha256=observer,executedPlayerLibrarySha256=library,distinctObserver=True,
            observerExecutionScope='Paired final observer executable is identified here; these drivers execute the final player production library. Observer-specific execution/parity is outside this manifest.'),
        frozenRuntimeProvenance=identity(runtime/'provenance.json'),frozenFullNativePatch=identity(ROOT/'_BuildScratch/audit-dev18-v2-source/native-companion.patch'),
        packSha256=sha(pack),originalPackSha256=reports['originalMap']['packSha256'],
        pinnedReduxCommit=reports['reduxSwirls']['pinnedReduxCommit'],compiledRomSha256=reports['reduxSwirls']['romSha256'],
        executedAssertions=6794,assertionsByReport=counts,actualFullEncounters=8,starmanPreparedParents=2,starmanColdProcesses=2,
        swirlPreparedWarmColdParents=4,swirlColdProcesses=4,skippedCases=0,
        archivedPriorProofManifests=[identity(ROOT/'research'/name)for name in (
            'converter-family-dev21-dev17-v4-manifest.json','intro-family-dev22-dev17-v4-manifest.json',
            'sequence-animation-dev23-dev17-v4-manifest.json','swirl-consumer-dev24-dev17-v4-manifest.json')],
        coverage=['Both profiles: all six Town Maps plus two game-over leader variants through actual upload/render consumers.',
            'Both profiles: three company logo parents, Produced/Presented actual callroutine consumers, full gas-station child/fade cleanup with source images.',
            'Both profiles: six retained animation records/all28 actual native displayed frames, metadata, upload spans and source images.',
            'Both profiles: all six swirl sequence types/all126 frames under8 option variants, native timeline plus independent two-window mask compositions.',
            'Both profiles: packed Starman appearance parent until first naturally completed movement wait, mid-appearance strict bootstrap-only cold continuation.',
            'Both profiles: scripted regular/boss warm+cold parent continuation, immediate restored first/second HDMA masks and final gameplay state/cleanup.',
            'Both profiles: four complete prepared encounters run real modes/menu/turns/KO/reward/cleanup.'],
        limits=['Starman appearance proof stops before later dialogue/smoke/boss story stages; surrounding party/position prerequisites are prepared.',
            'Encounter parties are deliberately level99. Natural campaign progression and all battle-script branches are not claimed.',
            'Swirl composition uses uniform BG1 and independent Boolean windows; complete hardware audiovisual/color-math parity is not claimed.',
            'Cold scene checkpoints here use this candidate content; cross-version/cross-content migration and inactive held-mask caches are outside these reports.',
            'No serialized save size/version change in the swirl correction. Root-owned migration/setup proofs remain separate.',
            'This manifest identifies a tested integrated candidate, not a public release/publication confirmation.'],
        ownerWrites=False,sharedSourcesModifiedByThisTask=False,redistributableGameAssetsIncluded=False)
    output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(manifest=identity(output),allPassed=True,executedAssertions=6794,actualFullEncounters=fullcases)))

if __name__=='__main__':main()
