# SPDX-License-Identifier: GPL-3.0-or-later
"""Refresh bounded hook evidence using existing inventories and exact reports.

Does not traverse imports, reclassify assembly, execute game code, or certify a
full conversion. Older evidence retains its exact measured runtime identity.
Only the explicit fresh output file is written.
"""
import argparse
import hashlib
import json
from pathlib import Path

from snes_movement_helpers_oracle import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('root','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.root=a.root.resolve()
    if a.output.exists():raise ValueError('Fresh output required')
    inputs={}
    def read(relative):
        path=a.root/relative;inputs[relative]=sha(path)
        return json.loads(path.read_text(encoding='utf-8-sig'))
    old=read('research/redux-active-hook-evidence-completeness-dev16.json')
    if old['upstreamCommit']!='897d00833f4a08a0a92f106abf631629a6a6a041' or not old['structuralAccountingVerified']:
        raise ValueError('Reviewed source inventory identity changed')
    evidence={}
    paths={
      'contact-phone':'research/redux-contact-phone-hook-dev16-v5-final.json',
      'direction':'research/native-direction-approach-dev16-v8-final.json',
      'encounter':'research/native-encounter-initiative-dev16-v8-final.json',
      'overlay':'research/redux-overlay-palette-behavior-dev16-v5-review.json',
      'palette-machine':'research/redux-palette-tint-machine-dev16-v5-review.json',
      'timed-items':'research/timed-item-dev16-v8-green.json',
      'timed-items-cold':'research/timed-item-cold-dev16-v8.json',
      'battle-ledger':'research/battle-semantic-coverage-dev16-final.json'}
    for key,path in paths.items():
        value=read(path)
        if key=='direction':
            if not value['EvidenceComplete'] or not value['NativeEquivalent']:raise ValueError('Final actual direction evidence incomplete')
        elif key=='battle-ledger':
            if value['remaining']:raise ValueError('Battle selected-evidence status changed')
        elif not value.get('Passed'):raise ValueError('Required bounded behavior report failed: '+key)
        evidence[key]=dict(Path=path,Sha256=inputs[path],ExactRecordedRuntimeIdentityRetained=True,
                          Limits=value.get('Limits',value.get('limits',value.get('Limitations',[]))))
    closed=[
      dict(Module='swirls_without_ness_fix',PriorGap='No exact Jeff/Poo leader-selection/advantage branch evidence.',
           Evidence=[evidence[k] for k in ('contact-phone','direction','encounter')],
           CurrentBoundedProof='Actual Original/pinned first-contact target and guards; actual final-v8 full contact/init encounter prefixes through swirl entry for Ness/Paula/Jeff/Poo and both contact routes; actual source lookup/division/facing/initiative, countdown120 and group1.',
           StillExcluded='Collision geometry producing the prepared contact result, later swirl/pathfinding/combat and natural Jeff/Poo story routes.'),
      dict(Module='dad_bike_phone_fix',PriorGap='No actual expired bicycle Dad-call queue/dismount/dialogue proof.',
           Evidence=[evidence['contact-phone']],
           CurrentBoundedProof='Exact v5 evidence: actual source/production timer and guard/FIFO branches with no_dad_calls disabled, real bicycle expiry/dismount queue behavior, both exact player/observer Yes/No dialogue flows and second cold restore.',
           StillExcluded='Real-time two-hour waiting, every late speaker/context and bell/audio listening. This v5 full phone-flow report is not relabeled as a v8 rerun.'),
      dict(Module='mushroom_pos_fix',PriorGap='No actual dry/shallow/deep overlay draw/OAM/pixels proof.',
           Evidence=[evidence['overlay']],
           CurrentBoundedProof='Exact v5 prepared overlay actors exercise draw callbacks, draw queues, OAM/rasterization and private cold checkpoints with source global terrain offsets.',
           StillExcluded='Walking/status application and removal through natural multiparty water transitions. v8 sprite-render ABI fixes have separate evidence; the whole overlay fixture is not relabeled as reexecuted v8.'),
      dict(Module='palette_tint_fix',PriorGap='Constants reviewed without executed source tint or elevator command sequencing.',
           Evidence=[evidence[k] for k in ('overlay','palette-machine')],
           CurrentBoundedProof='Exact v5 native representative sectors for149 packed combo/palette configurations per profile, paired actual complete source tint/average/channel/multiply/division code,38144 aggregate color comparisons; complete EVENT583 color-math/motion body reaches its text yield.',
           StillExcluded='Alternative map event-palette flag branches, every sector and full elevator entrance/dialogue/exit/pixel-equivalent cinematic. Source-only words in earlier report remain historical.'),
      dict(Module='item_transformations_fix',PriorGap='Only isolated timer helper evidence; load/finalization omitted source initialization.',
           Evidence=[evidence[k] for k in ('timed-items','timed-items-cold')],
           CurrentBoundedProof='Final v8 actual native save/load, file-select finalization, overworld initialization and6000 production party-leader callbacks complete Fresh Egg/Chick/Chicken transitions.32 cold cases use two fresh processes with transition pause120 and all four playable solo inventory owners.',
           StillExcluded='Successful Continue outcome is prepared. Actual title/menu selection, phone conversation, game-over reset, natural acquisition and exact audio/timing parity remain outside these reports.')]
    remaining=[]
    for row in old['partiallyCoveredActiveGameplayScopes']:
        if row['modules']==['item_transformations_fix']:continue
        remaining.append(dict(Modules=row['modules'],Sources=row['sources'],PriorNativeReferences=row['nativeReferences'],
                              ConfirmedMissingAdapter=False,ConfirmedNativeDefect=False,RemainingIntegrationRequirement=row['remainingGap'],
                              ExistingAdaptersAndEvidence=row['proved'],EvidenceType='Prior source-backed adapter review plus selected runtime proof; remaining context is not proof of missing functionality.'))
    remaining.append(dict(Modules=['item_transformations_fix'],ConfirmedMissingAdapter=False,ConfirmedNativeDefect=False,
                          RemainingIntegrationRequirement='Exercise the upstream game-over/reset branch while carrying timed items using actual source-defined flow; cold Continue and6000 callback lifecycle are already covered.',
                          EvidenceType='Explicit current report exclusion, not a new implementation defect.'))
    remaining.append(dict(Modules=['enemy_ai','Extended_Battle_Action_Table','Extended_PSI_Animations'],
                          ConfirmedMissingAdapter=False,ConfirmedNativeDefect=False,Evidence=[evidence['battle-ledger']],
                          RemainingIntegrationRequirement='Selected callback evidence now exists for all active catalog callbacks. Cross-turn evolving AI/status/target layouts, complete encounters and frame/pixel/audio parity are not certified by the callback ledger.',
                          EvidenceType='Coverage qualification; empty remaining catalog list is not all-branches or whole-story parity.'))
    output=dict(Schema='redux-hook-semantic-gap-refresh-dev16-v8-v1',SourcePin=old['upstreamCommit'],
                ReusedAccounting=old['reusedInventories'],ReparsedImportOrOpcodeInventory=False,
                StructuralClassificationIsNeverBehaviorCompletion=True,SupersededSourceOnlyGaps=closed,
                RemainingMaterialIntegrationRequirements=remaining,ExplicitPlatformOrUnusedQualifications=old['explicitlyUnusedOrPlatformOnly'],
                NewMissingAdapterProved=False,NewNativeDefectProved=False,FullReduxSemanticParityVerified=False,FullStoryVerified=False,
                Inputs=inputs,Runner=dict(Path=str(Path(__file__)),Sha256=sha(Path(__file__))),
                Limits=['Reuses existing source inventory and exact executable reports; no new game execution is performed by this refresh.',
                        'Branch/helper/selected callback evidence is never promoted to whole module, story or randomizer certification.',
                        'Reports from v5/v4 and earlier retain their actual identities. Only explicitly named final-v8 reports claim that current frozen library.',
                        'Remaining integration requirements are testing gaps, not missing implementation claims. New native corrections require source-backed runtime mismatch evidence.'])
    if any(sha(a.root/path)!=value for path,value in inputs.items()):raise ValueError('Evidence changed while refreshing')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(Output=str(a.output),PriorSourceOnlyBranchesWithNewBoundedEvidence=len(closed),NewMissingAdapterProved=False,FullStoryVerified=False)))


if __name__=='__main__':main()
