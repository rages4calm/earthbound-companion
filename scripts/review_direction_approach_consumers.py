# SPDX-License-Identifier: GPL-3.0-or-later
"""Qualify direction oracle differences by ordinary inputs and actual consumers.

Reads a complete prior machine report and its private own sample logs, never a
ROM. Consumer/initiative implications are labeled source-backed inferences, not
executed story encounters. Only the explicit fresh output report is written.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from snes_position_arithmetic_oracle import native_body
from snes_movement_helpers_oracle import sha


CONSUMERS = (
    ('src/game/overworld_spawn.c','initiate_enemy_encounter','overworld/initiate_enemy_encounter.asm','Encounter initiative: compares enemy moving direction and leader facing with approach direction.'),
    ('src/game/overworld.c','calculate_movement_path_steps','misc/calculate_movement_path_steps.asm','Automatic movement: selects the next eight-way movement step toward a destination.'),
    ('src/entity/entity.c','get_direction_between_entities','misc/get_direction_between_entities.asm','Scripted entity direction between two resolved character/NPC/sprite positions.'),
    ('src/entity/callroutine_screen.c','cr_make_party_look_at_entity','overworld/actionscript/make_party_look_at_active_entity.asm','Party look-at callback: changes sprite facing on even frames.'),
    ('src/entity/callroutine_movement.c','cr_movement_cmd_face_toward_npc','overworld/entity/face_entity_toward_npc.asm','Movement-script NPC facing toward an active entity.'),
    ('src/entity/callroutine_movement.c','cr_movement_cmd_face_toward_sprite','overworld/entity/face_entity_toward_sprite.asm','Movement-script sprite facing toward an active entity.'),
    ('src/game/overworld_teleport.c','get_direction_from_player_to_entity','overworld/get_direction_from_player_to_entity.asm','Entity-to-leader direction used by active callback paths.'),
)


def initiative(direction,enemy,leader):
    # Exact facing predicates in source INITIATE_ENEMY_ENCOUNTER lines55-99.
    # This applies source text to machine-observed directions; it is not an
    # assertion that a complete production encounter was executed here.
    approaching=((enemy-direction)&7) in (0,1,7)
    away=((leader-direction)&7) in (0,1,7)
    return 'enemies-first' if approaching and away else 'party-first' if not approaching and not away else 'normal'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('machine-report','native-source','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh report path required')
    report=json.loads(a.machine_report.read_text(encoding='utf-8'))
    if not report['EvidenceComplete'] or not report['BothModesActualMachineResultsIdentical']:raise ValueError('Completed dual CPU report required')
    folder=Path(report['ReproductionFlags']['scratch'])
    samples=folder/'machine-original/samples.jsonl'
    if sha(samples)!=report['Modes'][0]['MachineEvidence']['SamplesSha256']:raise ValueError('Private source samples changed')
    source=[json.loads(line) for line in samples.read_text(encoding='utf-8').splitlines()]
    native=[json.loads(line[10:]) for line in (folder/'production/native.log').read_text(encoding='utf-8').splitlines() if line.startswith('DIRECTION ')]
    rows=[list(map(int,line.split())) for line in (folder/'production/cases.tsv').read_text(encoding='utf-8').splitlines()]
    n=report['Cases']
    if [row[0] for row in source]!=list(range(1,n+1)) or [row[0] for row in native]!=list(range(1,n+1)) or len(rows)!=n:raise ValueError('Samples incomplete')
    ordinary=[];near=[];derived_count=0;examples=[]
    for row,cpu,production in zip(rows,source,native):
        index,x,y,tx,ty=row
        if x!=1024 or y!=1024:continue
        if max(abs(tx-x),abs(ty-y))>64:continue
        changed=cpu[2]!=production[2]
        ordinary.append(changed)
        if 0<abs(tx-x)+abs(ty-y)<16:near.append(changed)
        if not changed:continue
        outcomes=[(enemy,leader,initiative(cpu[2],enemy,leader),initiative(production[2],enemy,leader))
                  for enemy in range(8) for leader in range(8)
                  if initiative(cpu[2],enemy,leader)!=initiative(production[2],enemy,leader)]
        derived_count+=len(outcomes)
        if max(abs(tx-x),abs(ty-y))<=7 and len(examples)<12:
            enemy,leader,before,after=outcomes[0]
            examples.append(dict(Positions=row[1:],RelativeVector=[tx-x,ty-y],ActualCpuDirection=cpu[2],FrozenProductionDirection=production[2],
                                 EnemyMovementDirection=enemy,LeaderFacing=leader,SourcePredicateInitiative=before,FrozenNativePredicateInitiative=after,
                                 EvidenceType='Derived from complete CPU outputs and source/native identical facing predicates; full encounter not executed.'))
    consumers=[]
    for relative,function,original,meaning in CONSUMERS:
        path=a.native_source/relative;text=path.read_text(encoding='utf-8');body=native_body(text,function)
        if 'calculate_direction_8(' not in body:raise ValueError('Reviewed native consumer changed: '+function)
        asm=a.native_source/'asm'/original;original_text=asm.read_text(encoding='utf-8')
        if not any(name in original_text for name in ('CALCULATE_DIRECTION_FROM_POSITIONS','GET_DIRECTION_TO','GET_DIRECTION_BETWEEN_ENTITIES')):
            raise ValueError('Original consumer chain needs changed review: '+original)
        consumers.append(dict(NativePath=str(path),Function=function,DefinitionLine=text[:text.index(body.rstrip('\n'))].count('\n')+1,
                              NativeFunctionBodySha256=hashlib.sha256(body.encode()).hexdigest(),SourcePath=str(asm),SourceSha256=sha(asm),Behavior=meaning,
                              Evidence='Current native/source callsite inspection; full consumer execution excluded.'))
    output=dict(Schema='native-direction-consumer-qualification-v1',MachineReport=dict(Path=str(a.machine_report),Sha256=sha(a.machine_report)),
                OrdinaryCoordinateSquareCases=len(ordinary),OrdinaryEightWayDifferences=sum(ordinary),
                NonCoincidentManhattanUnder16Cases=len(near),NonCoincidentManhattanUnder16Differences=sum(near),
                SourcePredicateDerivedInitiativeDifferencesAcross64FacingPairs=derived_count,DerivedExamples=examples,Consumers=consumers,
                Reachability='Inputs are ordinary positive pixel coordinates, with differences within five pixels. These distances fit ordinary proximity/facing domains and do not require overflow, sprint or out-of-bounds state. Map-specific contact route and collision footprints were not executed here.',
                Exclusions=['No actual full encounter or natural contact route is claimed by the derived initiative examples.',
                            'No claim that this helper mismatch caused hotel, cliff or stair blockers.',
                            'No full AI, automatic-path completion or story coverage claim.'],
                FullPlaythroughVerified=False,FullConversionVerified=False,NativeSourceEdited=False,SharedBuildEdited=False,
                Tool=dict(Path=str(Path(__file__)),Sha256=sha(Path(__file__))))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:output[k] for k in ('OrdinaryCoordinateSquareCases','OrdinaryEightWayDifferences','NonCoincidentManhattanUnder16Differences')}))


if __name__=='__main__':main()
