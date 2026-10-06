# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze exact current and historical direction/encounter evidence identities.

No game execution, source edits or shared builds. Existing reports preserve
their measured versions; only the explicit fresh manifest is written.
"""
import argparse
import json
from pathlib import Path
from snes_movement_helpers_oracle import sha
from snes_position_arithmetic_oracle import native_body
import hashlib


FILES=(
 ('tools/snes_direction_approach_oracle.py','current-repeatable-original-cpu-and-production-library-direction-runner'),
 ('tools/redux_encounter_initiative_machine_qa.py','current-repeatable-full-contact-and-init-prefix-cpu-and-production-runner'),
 ('tools/review_direction_approach_consumers.py','source-consumer-review-with-explicitly-derived-initiative-examples'),
 ('tools/refresh_redux_hook_semantic_gaps.py','current-bounded-hook-evidence-refresh-no-game-execution'),
 ('tools/direction_encounter_evidence_manifest.py','exact-identity-manifest-generator'),
 ('research/native-direction-approach-dev17-red.json','historical-v6-actual-library-direction-red'),
 ('research/native-direction-approach-dev17-private-green.json','historical-v6-private-corrected-entity-object-direction-proof-not-production'),
 ('research/native-direction-approach-consumer-review.json','historical-red-consumer-reachability-and-derived-predicate-qualification'),
 ('research/native-direction-approach-dev16-v7-final.json','historical-v7-actual-untouched-library-direction-green'),
 ('research/native-direction-approach-dev16-v8-final.json','final-v8-actual-untouched-library-direction-green'),
 ('research/native-encounter-initiative-dev16-v6-red.json','historical-v6-actual-untouched-library-measured-initiative-red'),
 ('research/native-encounter-initiative-dev16-v7-final.json','historical-v7-actual-untouched-library-measured-initiative-green'),
 ('research/native-encounter-initiative-dev16-v8-final.json','final-v8-actual-untouched-library-measured-initiative-green'),
 ('research/redux-hook-semantic-gaps-dev16-v8.json','final-selected-hook-evidence-and-remaining-integration-qualifications'),
 ('research/redux-contact-phone-hook-dev16-v5-final.json','historical-v5-exact-first-contact-and-full-phone-dialogue-cold-proof'),
 ('tools/redux_contact_phone_hook_qa.py','unchanged-source-identification-and-first-contact-dependency'),
 ('tools/party_follow_private_build.py','unchanged-private-real-object-linker-dependency'),
 ('tools/snes_position_arithmetic_oracle.py','unchanged-original-source-identity-and-native-body-reader-dependency'),
 ('tools/snes_movement_helpers_oracle.py','unchanged-file-hash-and-clean-USA-ROM-gate-dependency'),
 ('tools/check_jev_observer_parity.py','unchanged-fresh-safe-local-scratch-validator-dependency'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('root','runtime','build','source-snapshot','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.root=a.root.resolve()
    if a.output.exists():raise ValueError('Fresh manifest required')
    files=[dict(Path=relative,Sha256=sha(a.root/relative),Role=role) for relative,role in FILES]
    read=lambda name:json.loads((a.root/'research'/name).read_text(encoding='utf-8'))
    current_direction=read('native-direction-approach-dev16-v8-final.json');current_encounter=read('native-encounter-initiative-dev16-v8-final.json')
    runtime={name:sha(a.runtime/name) for name in ('player.exe','observer.exe')};library=sha(a.build/'game_lib/libearthbound_game.a')
    if runtime!={'player.exe':'cd0c6f9ef6d01d7b29ebb6180eedb29f11b95adeb3a35dfb6687bcb6cf6cdf67',
                 'observer.exe':'9c21413218297b43c46db8f784cb6cd228417f7f13ca672ef562baf7ebfd93d4'} or library!='e7cacb1ef302d0b7bec395958af0dbb17fa01a67d777267677f20034964fb7b8':
        raise ValueError('Expected exact frozen final-v8 identities differ')
    for report in (current_direction,current_encounter):
        if not report['EvidenceComplete']:raise ValueError('Current evidence incomplete')
        for name,expected in runtime.items():
            if report['Inputs'][str((a.runtime/name).resolve())]!=expected:raise ValueError('Report runtime differs')
        if report['Inputs'][str((a.build/'game_lib/libearthbound_game.a').resolve())]!=library:raise ValueError('Report library differs')
    if not current_direction['NativeEquivalent'] or current_direction['Cases']!=115200 or not current_direction['ProductionEvidence']['UntouchedProductionLibraryLinked']:
        raise ValueError('Actual current direction green missing')
    if not current_encounter['Passed'] or current_encounter['PilotOnly'] or current_encounter['Cases']!=100:
        raise ValueError('Actual current full encounter-prefix green missing')
    if any(not mode['NativeEvidence']['UntouchedProductionLibraryLinked'] or not mode['NativeEvidence']['ReadOnlySwirlEntryObserver'] for mode in current_encounter['Modes']):
        raise ValueError('Current integration uses an unreviewed private replacement')
    source=a.root/'native-source/src/entity/entity.c';snapshot=a.source_snapshot/'src/entity/entity.c'
    if sha(source)!=sha(snapshot):raise ValueError('Reviewed actual source differs from final frozen snapshot')
    body=native_body(source.read_text(encoding='utf-8'),'calculate_direction_fine')
    baseline=read('native-direction-approach-dev17-red.json');encounter_red=read('native-encounter-initiative-dev16-v6-red.json')
    report=dict(Schema='direction-encounter-final-evidence-dev16-v8-v1',Frozen=True,
                SourcePin='897d00833f4a08a0a92f106abf631629a6a6a041',Files=files,RuntimeV8=runtime,ProductionLibraryV8=library,
                SourceChange=dict(Path='native-source/src/entity/entity.c',FileSha256=sha(source),FrozenSnapshotSha256=sha(snapshot),
                    ExactFunction='calculate_direction_fine',FunctionBodySha256=hashlib.sha256(body.encode()).hexdigest(),
                    PublicInterfaceUnchanged=True,Scope='Exact original wrapped16-bit subtraction/absolute/normalization, source lookup thresholds/quadrants and hardware-division saturation; source/pinned bodies identical. No unrelated entity behavior changes.',
                    DoesNotClaimOwnerMovementBlockerCause=True),
                BaselineDirectionV6={mode['Mode']:dict(FineDifferences=mode['FineMismatchCount'],EightWayDifferences=mode['EightWayMismatchCount']) for mode in baseline['Modes']},
                BaselineMeasuredInitiativeV6={mode['Mode']:mode['MismatchCount'] for mode in encounter_red['Modes']},
                FinalV8=dict(DirectionCasesPerMode=115200,FineDifferencesPerMode=0,EightWayDifferencesPerMode=0,
                    ActualContactAndInitPrefixesPerMode=100,MeasuredPrefixDifferencesPerMode=0,
                    OriginalAndPinnedMachineBodiesExecuted=True,PrivateCorrectedObjectsUsed=False,
                    ObserverIdentityPaired=True,PrivateDriversLinkPlayerPlatformObjectsAndSharedProductionLibrary=True,
                    SeparateObserverPlatformExecutionClaimed=False),
                ConsumerDistinctions=['Direction corpus executes actual common production-library pure functions and original/pinned CPU routines; it does not drive the desktop input loop.',
                    'Encounter corpus bootstraps actual local packs, invokes actual contact callback and init function, and observes real globals at swirl entry; prepared collision result precedes the source prefix.',
                    'Actual source and native facing/initiative branches are executed by the encounter corpus. The separate earlier consumer review labels its algebraic implications as derived, not executed.',
                    'Native swirl-entry wrapper is an observation checkpoint. Later swirl rendering, pathfinding/marking and battle completion are excluded.',
                    'Historical v5 full phone-dialogue tests separately executed both player/observer and cold restore; they are never relabeled as v8.'],
                Reproduction='Use each report ReproductionFlags with explicit local ROMs, original source, packs and exact frozen build/runtime. Current tool supports baseline reproduction against immutable v6 without corrected-entity-source, and private correction proof only with explicit override.',
                RunnerSourceEdited=False,SharedBuildEdited=False,OwnerSavesTouched=False,
                FullConversionVerified=False,FullPlaythroughVerified=False,
                Limits=['Counts from overlapping reports or profiles are not added into a conversion percentage.',
                        'Original/pinned machine gate and prepared function/prefix evidence do not certify every natural encounter, story or randomizer.',
                        'Only final-v8 reports in this manifest claim the current frozen library. Previous reports and tool identities remain historical.',
                        'No ROM, extracted game table, palette, save or PCM data is bundled by this manifest.'])
    if any(sha(a.root/row['Path'])!=row['Sha256'] for row in files):raise ValueError('Evidence/tool changed while freezing')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(Output=str(a.output),Frozen=True,Files=len(files),DirectionAndEncounterActualV8Passed=True)))


if __name__=='__main__':main()
