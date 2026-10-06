# SPDX-License-Identifier: GPL-3.0-or-later
"""Review remaining active Redux behavior evidence without reparsing inventory.

Consumes the existing 36-hook review and 105-span assembly ledger. Findings are
manual source-backed gaps, not newly proved defects or a compatibility score.
Only a fresh metadata report is written; no game/ROM/pack/save data is emitted.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from snes_movement_helpers_oracle import sha

PIN='897d00833f4a08a0a92f106abf631629a6a6a041'
PACK_SHA='ed299183d4b1aff4b38c56ef16da28a256c3a65d33ba1d9327c9b19df0272ef3'

# This is a targeted evidence crosswalk, not a second parsed import/opcode map.
SOURCE_ONLY = [
    {'module':'swirls_without_ness_fix','priority':1,
     'source':'ccscript/bugfixes/swirls_without_ness_fix.ccs',
     'sourceAnchor':'ROM[0xC0D668] = LDA_a (0x9889)',
     'sourceMeaning':'The player-initiated enemy-contact special case uses the actual party leader instead of hardcoded Ness entity24.',
     'nativeReferences':[('src/entity/callroutine.c','ert.enemy_pathfinding_target_entity = maternalbound_enabled() ? game_state.current_party_members : 24;')],
     'gap':'The older review records source/movement review. No dedicated Jeff/Poo contact-advantage trace is present in the reviewed evidence set. Shared encounter-race checks do not establish this leader-selection branch.',
     'nextProof':'Use actual source-defined player-initiated and enemy-initiated contact paths with solo Jeff/Poo, Ness position deliberately distinct, and source-defined facing/coordinates. Compare target selection and resulting advantage against pinned CPU code, including a cold native continuation.'},
    {'module':'dad_bike_phone_fix','priority':1,
     'source':'ccscript/bugfixes/dad_bike_phone_fix.ccs',
     'sourceAnchor':'CMP_i (3)',
     'sourceMeaning':'While walking_style is bicycle3, skip the Dad interruption to preserve bicycle bell behavior.',
     'nativeReferences':[('src/game/overworld.c','if(pc_options.no_dad_calls || (maternalbound_enabled() && game_state.walking_style == WALKING_STYLE_BICYCLE))return;'),
                         ('src/game/overworld.c','if (!ow.dad_phone_timer && game_state.camera_mode != 2)')],
     'gap':'The bicycle selftest rotates leaders/statuses but never invokes load_dad_phone. The old review explicitly leaves a live timed phone event unverified. The no_dad_calls host option can also mask the branch in ordinary QA.',
     'nextProof':'Keep the host no_dad_calls option disabled; obtain event/timer prerequisites from source. Exercise actual overworld timer expiration on bike, dismount, open-window/battle guards and Original control. Measure queued interaction/phone state and subsequent bell/audio requests.'},
    {'module':'mushroom_pos_fix','priority':2,
     'source':'ccscript/bugfixes/mushroom_pos_fix.ccs',
     'sourceAnchor':'define MUSHROOM_DEEP_WATER_Y_OFFSET\t= 16',
     'sourceMeaning':'Global trodden tile bits0C select mushroom draw Y offsets8 in shallow water and16 in deep water.',
     'nativeReferences':[('src/entity/callbacks.c','unsigned water=game_state.trodden_tile_type & 0x0C;'),
                         ('src/entity/callbacks.c','if (water==8) y+=8;')],
     'gap':'Source and callback constants are reviewed. Bicycle mushroom-refresh tests establish dismount/status, not the mushroom draw queue or shallow/deep-water overlay coordinates. No dedicated rendered multiparty water-overlay check is present in this evidence set.',
     'nextProof':'Capture actual draw-queue coordinates and rendered overlays for each player at dry/shallow/deep boundaries, zero/nonzero overlay countdown, and cold restore. Preserve the source global terrain input rather than inventing per-follower terrain semantics.'},
    {'module':'palette_tint_fix','priority':2,
     'source':'ccscript/bugfixes/palette_tint_fix.ccs',
     'sourceAnchor':'define how_much_tinting = 4',
     'sourceMeaning':'Reference channel averages are fixed at8A/96/74, channel approach uses threshold4, and the elevator movement bytes are1F1F1F.',
     'nativeReferences':[('src/game/map_loader.c','ml.saved_colour_average_red=0x8A;'),
                         ('src/game/map_loader.c','if (orig_r>new_r+4) new_r=orig_r-4;'),
                         ('src/game/overworld_palette.c','uint16_t adjust_single_colour')],
     'gap':'The old review proves source constants and retained elevator command bytes, not actual palette arithmetic or live elevator sequencing. Dissolve-slot RNG and battle palette tests cover separate paths. A source anchor is insufficient to establish tint parity.',
     'nextProof':'Identify actual source GET_COLOUR_AVERAGE/ADJUST_SINGLE_COLOUR and the pinned tint hook bodies, compare actual palette-channel results at threshold/greyscale/ratio boundaries, then replay a real elevator transition through its retained movement commands.'},
]

PARTIAL = [
    {'modules':['item_transformations_fix'],'priority':1,
     'sources':['ccscript/bugfixes/item_transformations_fix.ccs'],
     'nativeReferences':[('src/game/overworld.c','if (maternalbound_enabled() || item_transformations_loaded)'),
                         ('src/game/inventory.c','void reset_item_transformations(void)')],
     'existingEvidence':['research/rng-consumers-dev16-v3-green.json'],
     'proved':'Actual production timer initialization and SFX/reset-gate RNG consumers now have warm/cold evidence with serialized source RNG. The active per-frame condition is present.',
     'remainingGap':'No full Fresh Egg→Chick→Chicken lifecycle is established after phone-save load or game-over/reset, which is the upstream bug trigger. Direct timer consumer calls do not prove actual per-frame invocation/reinitialization through that lifecycle.'},
    {'modules':['fast_terrain','four_frames_run','run_patch','run_stamina_mechanic'],'priority':1,
     'sources':['ccscript/redux/fast_terrain.ccs','ccscript/redux/four_frames_run.ccs','ccscript/redux/run_patch.ccs','ccscript/redux/run_stamina_mechanic.ccs'],
     'nativeReferences':[('src/game/overworld.c','maternalbound_enabled() ? WALKING_STYLE_SLOWER : WALKING_STYLE_SLOWEST'),
                         ('src/game/position_buffer.c','bool maternalbound_motion_selftest(void)'),
                         ('src/game/maternalbound.c','maternalbound_stamina_update')],
     'existingEvidence':['research/redux-control-and-battle-hooks-review.json','research/redux-remaining-feature-review.json',
                         'research/native-position-arithmetic-runtime-review-dev15-v6-final-green.json',
                         'research/native-redux-party-run-dev16-v4-final-green.json'],
     'proved':'Converted sprite tables match pinned data; default/PJs/run/exhaustion and timer fixtures exist. Original arithmetic is independently machine-tested; current Redux ordinary walk/run callback parity passes.',
     'remainingGap':'These are not actual Lost Underworld entrance, water, ladder/rope and special-style stamina/sprite transition traces. The explicit native inversion/run-flag adaptation is documented, not literal source equality.'},
    {'modules':['expand_shops','ShopSys','ShopMain'],'priority':2,
     'sources':['ccscript/expansion/expand_shops.ccs','ccscript/shops/ShopSys.ccs','ccscript/shops/ShopMain.ccs'],
     'nativeReferences':[('src/game/maternalbound.c','maternalbound_registers_equal'),
                         ('src/game/display_text_menus.c','st->shop_id * STORE_ITEMS_PER_SHOP')],
     'existingEvidence':['research/redux-remaining-feature-review.json'],
     'existingRunner':'tools/redux_dialogue_qa.py',
     'proved':'All69 shop rows are retained, typed register comparison exists, and actual early-store buy/equip/sell/cancel replays exist. This is not classification-only at module level.',
     'remainingGap':'The existing dialogue replay uses one early shop entry; no complete bulk-buy/insufficient-cash/full-inventory transactions across custom shops66..68, Moonside logic and later shop categories are established by that runner.'},
    {'modules':['Extended_Battle_Action_Table','enemy_ai','m3_defend_roller','Extended_PSI_Animations'],'priority':2,
     'sources':['ccscript/expansion/Extended_Battle_Action_Table.ccs','ccscript/redux/enemy_ai.ccs','ccscript/redux/m3_defend_roller.ccs','ccscript/expansion/Extended_PSI_Animations.ccs'],
     'nativeReferences':[('src/game/battle.c','redux_enemy_ai_active'),
                         ('src/game/display_text_cc.c','case 0x1B:')],
     'existingEvidence':['research/redux-battle-item-feature-review.json','research/battle-semantic-coverage-dev16.json'],
     'proved':'Packed action rows, selector/VM turns, actual handler branches and playback fixtures provide substantial bounded behavior evidence. Dispatch existence alone is explicitly not treated as completion.',
     'remainingGap':'Cross-turn combinations, all real target layouts/status interactions, each enemy AI condition sequence under evolving combat and pixel-level PSI comparisons still depend on the separate battle audit. These are not new missing-adapter findings.'},
]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('project','native-source','root','assembly-ledger','before-pack','after-pack','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();root=a.root.resolve();a.project=a.project.resolve();a.native_source=a.native_source.resolve()
    if a.output.exists():raise ValueError('Fresh report filename required')
    inputs={}
    def read(path):
        path=path.resolve();inputs[path.as_posix()]=sha(path)
        return json.loads(path.read_text(encoding='utf-8-sig'))
    old=read(root/'research/redux-active-bugfix-review.json')
    current=read(root/'research/redux-active-bugfix-review-dev16.json')
    ledger=read(a.assembly_ledger)
    dialogue=read(root/'research/maternalbound-dialogue-report.json')
    if old['upstreamCommit']!=PIN or current['upstreamCommit']!=PIN or len(old['reviews'])!=36:
        raise ValueError('Existing hook review/pin changed')
    if len(ledger['excludedSpanLedger'])!=105 or ledger['unclassifiedExcludedSpans']:
        raise ValueError('Existing excluded-span ledger changed')
    inventory=lambda rows:Counter((r['module'],r.get('kind'),tuple(r.get('labels',[])),r.get('address')) for r in rows)
    if inventory(ledger['excludedSpanLedger'])!=inventory(dialogue['excluded']):
        raise ValueError('Existing105-span ledger and dialogue exclusion map differ')
    # Reuse checksum inventory rather than reparse imports/writes/bytecode.
    for row in ledger['sourceInventory']:
        path=a.project/row['path'];raw=path.read_bytes();expected=row['sha256'].lower()
        forms=(raw,raw.replace(b'\r\n',b'\n'),raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
        if not any(hashlib.sha256(data).hexdigest()==expected for data in forms):
            raise ValueError('Pinned source identity changed: '+row['path'])
    before=sha(a.before_pack);after=sha(a.after_pack)
    if before!=PACK_SHA or after!=PACK_SHA or a.before_pack.read_bytes()!=a.after_pack.read_bytes():
        raise ValueError('Note-only generator change affected expected Redux pack')
    def refs(bindings):
        result=[]
        for relative,anchor in bindings:
            path=a.native_source/relative;text=path.read_text(encoding='utf-8');at=text.find(anchor)
            if at<0:raise ValueError('Native binding changed: '+relative+': '+anchor)
            result.append({'path':relative,'line':text[:at].count('\n')+1,'anchor':anchor,'sha256':sha(path)})
        return result
    reviews={r['module']:r for r in current['reviews']};main=(a.project/'ccscript/main.ccs').read_text(encoding='utf-8-sig')
    gaps=[]
    for row in SOURCE_ONLY:
        source=a.project/row['source'];text=source.read_text(encoding='utf-8-sig');at=text.find(row['sourceAnchor'])
        if at<0 or sha(source)!=reviews[row['module']]['sourceSha256']:
            raise ValueError('Reviewed pinned hook/anchor differs: '+row['module'])
        activation='import "bugfixes/'+row['module']+'.ccs"'
        if activation not in main:raise ValueError('Reviewed hook is no longer directly active')
        gaps.append({**row,'sourceSha256':sha(source),'sourceLine':text[:at].count('\n')+1,
                     'activationLine':main[:main.index(activation)].count('\n')+1,
                     'nativeReferences':refs(row['nativeReferences']),
                     'nativeAdapterPresent':True,'confirmedNativeDefect':False,
                     'evidenceLevel':'source-review-only-for-the-exact-named-branch',
                     'legacyReviewCoverage':reviews[row['module']]['targetedCoverageAndLimits']})
    partial=[]
    for row in PARTIAL:
        evidence=[{'path':name,'sha256':sha(root/name)} for name in row['existingEvidence']]
        for name in row['existingEvidence']:read(root/name)
        partial.append({**row,'nativeReferences':refs(row['nativeReferences']),
                        'sourceIdentities':{name:sha(a.project/name) for name in row['sources']},
                        'existingEvidence':evidence,'confirmedNativeDefect':False})
    closed=[]
    for name in ('native-party-screen-dual-dev16-v4-final-green.json','native-redux-party-run-dev16-v4-final-green.json','native-tile-merge-dev16-v4-final-green.json'):
        path=root/'research'/name;data=read(path)
        if not data['Passed']:raise ValueError('Required final current evidence failed: '+name)
        closed.append({'path':'research/'+name,'sha256':sha(path),'Passed':True})
    supplemental=('redux-naming-runtime-review.json','redux-reset-runtime-review.json','redux-special-presentation-v6-review.json',
                  'redux-prayer-complete-dev16-v3.json','redux-letter-complete-dev16-v3.json')
    for name in supplemental:read(root/'research'/name)
    boot=(a.project/'ccscript/debug/debug_menu_enabler.ccs').read_text(encoding='utf-8-sig')
    if 'define DEBUG_BUILD = 0' not in boot:raise ValueError('Debug boot hook activation changed')
    remaining=read(root/'research/redux-remaining-feature-review.json')
    library=remaining['movementLibrary']
    if library['reachableDestructorOpcodes'] or library['activeSourceDestructorCalls']:
        raise ValueError('Previously unused destructor has active use')
    bugtool=root/'tools/audit_redux_bugfixes.py';builder=root/'tools/build_maternalbound_pack.py'
    inputs[bugtool.as_posix()]=sha(bugtool);inputs[builder.as_posix()]=sha(builder);inputs[Path(__file__).resolve().as_posix()]=sha(Path(__file__))
    report={'format':'redux-active-hook-evidence-completeness-dev16-v1',
            'status':'manual-source-backed-gap-review-not-a-gameplay-pass','upstreamCommit':PIN,
            'structuralAccountingVerified':True,'reusedInventories':{'activeBugfixHooks':36,'excludedSpans':105,
              'excludedGroups':dict(Counter(r['module'] for r in ledger['excludedSpanLedger'])),
              'publicLedgerPath':a.assembly_ledger.as_posix(),'publicLedgerExists':True,
              'newImportOrOpcodeInventoryParsed':False},
            'prioritizedExactBranchEvidenceGaps':gaps,'partiallyCoveredActiveGameplayScopes':partial,
            'newMissingNativeAdapterProved':False,'newNativeDefectProved':False,
            'supersededLegacyClassifications':[{'module':'party_member_diagonal_fix','oldReport':'research/redux-active-bugfix-review.json',
              'currentReview':'research/redux-active-bugfix-review-dev16.json',
              'correction':'Original source guards retained; actual pinned Redux two-pixel predicted-coordinate threshold now implemented and independently tested. Earlier rendering-bypass row is historical.',
              'currentEvidence':closed},
              {'module':'item_transformations_fix','correction':'Dev16 timer/RNG helper evidence supersedes source-only helper wording; complete reset/game-over Egg timeline remains open.'}],
            'explicitlyUnusedOrPlatformOnly':[{'scope':'movscr_codes destructor API','activeReachableOpcodes':0,'activeSourceCalls':0,
               'qualification':'Unused-library gap in audited pinned graph, not an active normal-story conversion requirement.'},
              {'scope':'debug_fixes/debug_menu_enabler/diamond/psi_anims debugger support','DEBUG_BUILD':0,
               'qualification':'Pinned boot debugger disabled; wholesale developer-menu parity remains separate from normal gameplay.'},
              {'scope':'chunked DMA race and region/protection boot patches',
               'qualification':'Native immediate DMA/PC startup have different execution; no SNES hardware emulation claim.'}],
            'builderIdentityRegression':{'beforeNoteChangePackSha256':before,'afterNoteChangePackSha256':after,
              'bothPacksByteIdentical':True,'matchesInstalledPinnedPack':True,
              'reviewGeneratorSha256BeforeNotes':'7dc2742c6d4014a6435022bb73feda90f1557215dbb2ee4cff703fc20154e85f',
              'reviewGeneratorSha256AfterNotes':sha(bugtool),'builderSha256':sha(builder),
              'builderBehaviorEdited':False,'onlyTwoReviewNotesEdited':True},
            'inputIdentities':inputs,'nativeCEdited':False,'sharedBuildEdited':False,'ownerSavesTouched':False,
            'fullReduxSemanticParityVerified':False,'fullStoryVerified':False,
            'limits':['This reuses existing accounting, current source anchors and stated runtime evidence; source binding is never automatically a behavior pass.',
              'Absence of dedicated evidence means not found in this reviewed set, not a proof that no test exists anywhere or that the feature is broken.',
              'The105 spans and36 hooks overlap other module reviews. Their counts are not added into a completion percentage.',
              'Existing historical runtime reports retain their actual hashes; only the explicitly named final-v4 refreshes claim that exact current production library.',
              'No new machine execution, scene traversal, audio listening or screenshot comparison is performed by this completeness runner.',
              'Prepared unit/branch coverage does not prove every reachable story, randomizer, controller/display or save migration combination.']}
    if any(sha(Path(path))!=value for path,value in inputs.items()):raise ValueError('Audit input changed')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'structuralAccountingVerified':True,'exactBranchEvidenceGaps':[r['module'] for r in gaps],
                      'newNativeDefectProved':False,'fullStoryVerified':False,'builderPacksByteIdentical':True}),flush=True)


if __name__=='__main__':main()
