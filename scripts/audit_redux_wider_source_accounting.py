# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only crosswalk of existing pinned Redux inventories and evidence.

Reuses the published 191-file/5661-syntax/105-exclusion ledger. Does not walk
imports, parse a second write inventory, execute the game, or certify parity.
Local inputs are explicit; only a fresh metadata report is written. No ROM,
asset-pack, graphics, soundtrack, compiled source bytes, or saves are emitted.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

PIN = '897d00833f4a08a0a92f106abf631629a6a6a041'
V8 = {
    'player.exe': 'cd0c6f9ef6d01d7b29ebb6180eedb29f11b95adeb3a35dfb6687bcb6cf6cdf67',
    'observer.exe': '9c21413218297b43c46db8f784cb6cd228417f7f13ca672ef562baf7ebfd93d4',
}
LIB = 'e7cacb1ef302d0b7bec395958af0dbb17fa01a67d777267677f20034964fb7b8'

REVIEWS = (
    'redux-active-bugfix-review-dev16.json',
    'redux-control-and-battle-hooks-review.json',
    'redux-general-hooks-review.json',
    'redux-remaining-feature-review.json',
    'redux-battle-item-feature-review.json',
    'redux-presentation-feature-review.json',
    'redux-recovery-hooks-review.json',
    'redux-hook-semantic-gaps-dev16-v8.json',
    'redux-reset-runtime-review.json',
    'redux-naming-runtime-review.json',
    'redux-complete-prayer-cinematics-review.json',
    'redux-complete-ending-transaction-review.json',
    'battle-semantic-coverage-dev16-final.json',
)

# Explicitly reviewed additional write-bearing sources. A reference records
# the adapter/decision and evidence boundary, never a whole-module pass.
EXTRA = {
    'ccscript/data_mem_overwrite.ccs': (
        'converted-dialogue-entry-pointers',
        'Retained compiled dialogue, relocated pointers and source-address aliases replace the many original ROM text jumps. This file is mostly pointer/data installation, not 5295 independent native algorithms.',
        [('tools/maternalbound_dialogue.py', 'redirectedOriginalEntries'),
         ('tools/build_maternalbound_pack.py', 'Unmapped native game entries')],
        ['research/maternalbound-dialogue-report.json'],
        'No complete natural traversal of every converted story entry or every emitted pointer target.'),
    'ccscript/data/data_19.ccs': (
        'native-delivery-timed-adapter',
        'Escargo_Letterbox is adapted at the actual delivery action-script sequence point; a saved child performs fourteen letterbox frames before deferred music/dismount.',
        [('native-source/src/entity/script.c', 'AS_CHILD_DELIVERY_LETTERBOX'),
         ('native-source/src/entity/callroutine.c', 'actionscript_request_delivery_letterbox();')],
        ['research/redux-presentation-feature-review.json'],
        'The recorded fourteen-frame prepared delivery fixture is not every natural delivery request, location, bike/party or interrupted save context.'),
    'ccscript/essential/cc_load_two_str.ccs': (
        'native-menu-string-adapter',
        'Installed19/02 dispatcher and vertical-print hooks become typed left/right menu labels, optional hover callback and native right-edge rendering. Native four-variant fixtures test dispatch labels/callback/operand consumption.',
        [('native-source/src/game/display_text_cc.c', 'if (terminator == 3 || terminator == 4)'),
         ('native-source/src/game/window.c', 'if (item->right_label[0])'),
         ('native-source/src/game/display_text.c', 'const struct {uint8_t term; const char *right; uint32_t callback;} menus[]')],
        [],
        'A full original-machine/right-edge hover-render oracle and source-encoded boundary-length strings are not established by four synthetic dispatcher cases. Source command macros have no invocation in the existing191-file source set; installed hooks still require the adapter.'),
    'ccscript/essential/cc_effects.ccs': (
        'native-effects-and-unused-definition',
        'Active fade/letterbox calls use typed adapters and saved per-frame state. The sole inventoried ROM write is inside register_startup_pointer, whose macro has no invocation in the pinned191-file source set; ellipse door patches are commented upstream.',
        [('native-source/src/game/display_text_cc.c', 'maternalbound_letterbox_start((uint8_t)routine);'),
         ('native-source/src/game/maternalbound.c', 'void maternalbound_letterbox_start(uint8_t routine)')],
        ['research/redux-presentation-feature-review.json', 'research/redux-reset-runtime-review.json'],
        'Source frame progression/selected scenes are bounded. No every-cutscene fade, mask, audio or exact NMI envelope equivalence claim.'),
    'ccscript/essential/commands.ccs': (
        'native-interpreter-and-empty-extension',
        'CheckTalkHijack installs an optional checkable_people expansion, empty in the pinned source. Native ordinary interaction/interpreter paths already represent the retail person/check behavior. Other command definitions expand to converted control codes.',
        [('native-source/src/game/overworld_interaction.c', 'int16_t find_nearby_checkable_tpt_entry(void)'),
         ('native-source/src/game/display_text_cc.c', 'void cc_19_dispatch(ScriptReader *r)')],
        ['research/redux-control-and-battle-hooks-review.json'],
        'No populated optional checkable_person entries are present. set_pixel_mode/set_tile_mode are unused command definitions. Complete ordinary dialogue command combinations are not certified.'),
    'ccscript/redux/cutscenes.ccs': (
        'retained-movement-interpreter-data',
        'Ghost-reception movement speed/pause, three Sky Walker timings/offsets and custom monkey-camera/controller scripts are retained in relocated movement regions. Typed instant-letterbox calls replace original assembly helper calls.',
        [('tools/maternalbound_events.py', 'customScriptIds'),
         ('native-source/src/entity/opcodes.c', 'OP_SET_VAR'),
         ('native-source/src/entity/script.c', 'mode_step_actionscript')],
        ['research/redux-presentation-feature-review.json', 'research/redux-remaining-feature-review.json'],
        'Pointer/data and selected interpreter fixtures do not establish complete natural ghost-chase, Bubble Monkey rope-camera or Sky Walker entrance/exit scenes, including all party status variants.'),
    'ccscript/redux/enemy_ai.ccs': (
        'native-enemy-ai-script-adapter',
        'Enemy selector/threshold/status commands and packed configuration/action rows are retained and interpreted by typed native battle adapters.',
        [('native-source/src/game/battle.c', 'redux_enemy_ai_active'),
         ('native-source/src/game/display_text_cc.c', 'redux_enemy_ai_active')],
        ['research/redux-battle-item-feature-review.json', 'research/battle-semantic-coverage-dev16-final.json'],
        'Every catalog callback has selected evidence; evolving multi-turn AI choices and all real party/target/status combinations are not thereby complete.'),
    'ccscript/redux/refill_stamina_on_heal.ccs': (
        'native-recovery-entry-adapter',
        'Three compiled heal-entry trampolines map to once-per-entry native stamina reset, preserving resumable heal-loop guards.',
        [('native-source/src/game/display_text.c', 'maternalbound_rest_entry(DIALOGUE_BLOB_BASE+r->ptr_off)'),
         ('native-source/src/game/maternalbound.c', 'void maternalbound_rest_entry(')],
        ['research/redux-recovery-hooks-review.json'],
        'Selected entry/loop proofs do not cover every natural healing dialogue or concurrent stamina/special movement state.'),
}

LEDGER_EVIDENCE = {
    'ShopSys': ['research/redux-remaining-feature-review.json'],
    'goods_menu_equip': ['research/redux-inventory-transform-pool-dev17-v8.json', 'research/redux-presentation-feature-review.json'],
    'data_19': ['research/redux-presentation-feature-review.json'],
    'data_24': ['research/redux-presentation-feature-review.json'],
    'item_determiners': ['research/redux-remaining-feature-review.json'],
    'keyitems': ['research/redux-inventory-transform-pool-dev17-v8.json'],
    'tools': ['research/redux-control-and-battle-hooks-review.json'],
    'new_stats_equipment': ['research/redux-presentation-feature-review.json'],
    'window_titles': ['research/redux-control-and-battle-hooks-review.json'],
    'psi_battle_anims': ['research/redux-battle-item-feature-review.json', 'research/battle-semantic-coverage-dev16-final.json'],
    'coffee_tea_sequences': ['research/redux-presentation-feature-review.json'],
    'flyover_texts': ['research/redux-presentation-feature-review.json'],
    'staff_text': ['research/redux-complete-ending-transaction-review.json'],
    'debug_menu_enabler': ['research/redux-remaining-feature-review.json'],
    'diamond': ['research/redux-remaining-feature-review.json'],
    'psi_anims': ['research/redux-battle-item-feature-review.json'],
}

GAPS = [
    {
        'priority': 1, 'scope': 'Lost Underworld and other special terrain/style transitions',
        'sources': ['ccscript/redux/fast_terrain.ccs', 'ccscript/redux/four_frames_run.ccs', 'ccscript/redux/run_patch.ccs', 'ccscript/redux/run_stamina_mechanic.ccs'],
        'existing': 'Original machine arithmetic and ordinary Redux walk/run/sprite/stamina fixtures are available.',
        'nextRequirement': 'Replay actual source-defined entrances/water/ladder/rope/stair transitions, including exhausted/recovered stamina and tiny/robot/ghost/follower sprite selection; verify cold continuation and collision-safe exit.',
        'implementationRequiredNow': 'No additional C implementation is proved missing. Change only after an exact source/production mismatch is reproduced.',
    },
    {
        'priority': 1, 'scope': 'Retained special cutscene movement and delivery context',
        'sources': ['ccscript/redux/cutscenes.ccs', 'ccscript/data/data_19.ccs'],
        'existing': 'Relocated movement regions/pointers, custom IDs895..898, immediate letterbox adapter and selected fourteen-frame delivery child proof are available.',
        'nextRequirement': 'Run complete ghost-reception chase, Bubble Monkey rope-camera/return/unlock and Sky Walker lab/Fourside/desert transitions through their real script parents. Run delivery spawn/contact/dialogue on and off bike with cold restore at waits.',
        'implementationRequiredNow': 'The retained scripts and adapters are present; natural integration/scene timing is unverified rather than known missing.',
    },
    {
        'priority': 2, 'scope': 'Custom shops and repeated menu/equipment transactions',
        'sources': ['ccscript/shops/ShopMain.ccs', 'ccscript/shops/ShopSys.ccs', 'ccscript/expansion/expand_shops.ccs', 'ccscript/redux/goods_menu_equip.ccs', 'ccscript/redux/new_stats_equipment.ccs'],
        'existing': 'All69 shop rows, register comparison, early buy/equip/sell/cancel replay, source equipment/menu adapters and selected item/pool transactions have evidence.',
        'nextRequirement': 'Exercise shops66..68 and Moonside bulk-buy loops through actual dialogue with insufficient cash/full bags, pooled key refusal, Poo equipment restrictions, preview/cancel/unequip/re-equip and source-window cleanup.',
        'implementationRequiredNow': 'Do not infer missing bulk-buy behavior from table/classification counts; an actual transaction mismatch is needed.',
    },
    {
        'priority': 2, 'scope': 'Two-string/hover and window-title rendering',
        'sources': ['ccscript/essential/cc_load_two_str.ccs', 'ccscript/redux/window_titles.ccs', 'ccscript/redux/optimize_text_rendering.ccs'],
        'existing': 'Native dispatcher consumes all four menu terminators, title commands/affixes are present, five source fonts are byte-matched and native text blits are implemented.',
        'nextRequirement': 'Obtain exact active compiled call sites before claiming live story relevance. Independently compare actual callback selection/right-edge pixels/font widths for applicable source strings and all legal title prefixes/suffixes; include cold open-menu continuation.',
        'implementationRequiredNow': 'No missing adapter is proved. Unused macro/API boundary differences should not become gameplay defects without a reachable source caller.',
    },
    {
        'priority': 2, 'scope': 'Battle target layouts, evolving AI and portrait/audio composition',
        'sources': ['ccscript/redux/enemy_ai.ccs', 'ccscript/expansion/Extended_PSI_Animations.ccs', 'ccscript/redux/m3sprites.ccs', 'ccscript/redux/Bowspr.ccs', 'ccscript/redux/msu1.ccs'],
        'existing': 'All active callback catalog entries have selected semantic evidence; prepared final-v8 full battles/prayers/endings and source/render/adapters have separate exact reports.',
        'nextRequirement': 'Expand actual multi-turn AI/status/reflection/layout combinations and naturally reached party-change/death/reward paths; compare composed portrait/PSI/background frames and requested/mixed music/effects. Listen to soundtrack transitions where automated sample checks cannot establish perceived parity.',
        'implementationRequiredNow': 'Bowspr SNES DMA/VRAM allocator and MSU-register cycle emulation are platform-specific; current direct composition/PCM ramps are documented adaptations, not proof of a missing gameplay consumer.',
    },
    {
        'priority': 3, 'scope': 'Whole converted story/randomizer and save migration combinations',
        'sources': ['ccscript/data_mem_overwrite.ccs', 'ccscript/essential/commands.ccs'],
        'existing': '7397 label spans/12859 relocated pointer fields have structural gates with zero reported unresolved fields, failed spans or ambiguous original aliases.',
        'nextRequirement': 'Replay source-defined stateful story entry sequences and checkpoint migrations, including different party orders/flags and supported randomizer data. Preserve owner playthrough independently.',
        'implementationRequiredNow': 'Structural conversion counts do not establish story completion, progression safety or every gameplay dependency.',
    },
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'project', 'native-source', 'source-snapshot', 'runtime', 'build', 'assembly-ledger', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    for name in ('root', 'project', 'native_source', 'source_snapshot', 'runtime', 'build', 'assembly_ledger', 'output'):
        setattr(args, name, getattr(args, name).resolve())
    if args.output.exists():
        raise ValueError('Fresh output required; historical evidence must not be overwritten')
    inputs = {}

    def read(path):
        path = Path(path).resolve()
        inputs[str(path)] = sha(path)
        return json.loads(path.read_text(encoding='utf-8-sig'))

    ledger = read(args.assembly_ledger)
    bridge = read(args.root / 'research/maternalbound-native-bridge.json')
    dialogue = read(args.root / 'research/maternalbound-dialogue-report.json')
    reviews = {name: read(args.root / 'research' / name) for name in REVIEWS}
    if len(ledger['sourceInventory']) != 191 or len(ledger['syntacticRomWriteSites']) != 5661 or len(ledger['excludedSpanLedger']) != 105 or ledger['unclassifiedExcludedSpans']:
        raise ValueError('Pinned reused inventory changed')
    if bridge['sourceGraph']['unresolvedImports'] or bridge['sourceGraph']['duplicateModuleNames'] or len(bridge['sourceGraph']['files']) != 191:
        raise ValueError('Pinned existing import accounting changed')
    if reviews['redux-active-bugfix-review-dev16.json']['upstreamCommit'] != PIN:
        raise ValueError('Pinned source revision changed')
    span_keys = lambda rows: Counter((r['module'], r.get('address'), r.get('kind'), tuple(r.get('labels', []))) for r in rows)
    if span_keys(ledger['excludedSpanLedger']) != span_keys(dialogue['excluded']):
        raise ValueError('105-span ledger no longer matches original converter exclusions')
    source_texts = {}
    for row in ledger['sourceInventory']:
        path = args.project / row['path']
        raw = path.read_bytes()
        normal = raw.replace(b'\r\n', b'\n')
        forms = (raw, normal, normal.replace(b'\n', b'\r\n'))
        if row['sha256'].lower() not in {hashlib.sha256(value).hexdigest() for value in forms}:
            raise ValueError('Pinned source identity changed: ' + row['path'])
        source_texts[row['path']] = raw.decode('utf-8-sig')
    site_counts = Counter(row['source'] for row in ledger['syntacticRomWriteSites'])
    if any(site_counts[row['path']] != row['syntacticRomWriteSites'] for row in ledger['sourceInventory']):
        raise ValueError('Existing syntactic source totals disagree')
    if sum(row['syntacticRomWriteSites'] for row in ledger['sourceInventory']) != 5661:
        raise ValueError('Existing syntactic totals disagree')
    actual_runtime = {name: sha(args.runtime / name) for name in V8}
    if actual_runtime != V8 or sha(args.build / 'game_lib/libearthbound_game.a') != LIB:
        raise ValueError('Exact final-v8 runtime/library identity changed')
    evidence = {}

    def ev(relative):
        if relative not in evidence:
            data = read(args.root / relative)
            evidence[relative] = {'path': relative, 'sha256': inputs[str((args.root / relative).resolve())],
                                  'recordedRuntimeIdentityRetained': True,
                                  'limits': data.get('limits', data.get('scopeLimits', data.get('Limits', [])))}
        return evidence[relative]

    def refs(bindings):
        result = []
        for name, anchor in bindings:
            if name.startswith('native-source/'):
                relative = name[len('native-source/'):]
                path = args.source_snapshot / relative
                origin = 'exact-v8-source-snapshot'
                if not path.is_file():
                    path = args.native_source / relative
                    origin = 'unchanged-base-source-not-an-execution-claim'
            else:
                path = args.root / name
                origin = 'current-tool-source-reference'
            value = path.read_text(encoding='utf-8-sig')
            at = value.find(anchor)
            if at < 0:
                raise ValueError('Reviewed native/converter anchor changed: ' + name + ': ' + anchor)
            inputs[str(path.resolve())] = sha(path)
            result.append({'path': name, 'line': value[:at].count('\n') + 1, 'anchor': anchor,
                           'sha256': sha(path), 'referenceOrigin': origin})
        return result

    by_source = defaultdict(set)
    for name, report in reviews.items():
        rows = report.get('modules', report.get('reviews', []))
        for row in rows:
            if isinstance(row, dict) and row.get('source'):
                by_source[row['source']].add('research/' + name)
            if isinstance(row, dict) and row.get('name') and name == 'redux-presentation-feature-review.json':
                by_source['ccscript/redux/' + row['name'] + '.ccs'].add('research/' + name)
    by_source['ccscript/redux/redux_changes.ccs'].add('research/redux-general-hooks-review.json')
    by_source['ccscript/redux/enemy_ai_actions.ccs'].update({
        'research/redux-battle-item-feature-review.json',
        'research/battle-semantic-coverage-dev16-final.json',
    })
    prior = {r['source'] for r in reviews['redux-active-bugfix-review-dev16.json']['reviews']}
    prior |= {r['source'] for r in reviews['redux-control-and-battle-hooks-review.json']['modules']}
    prior.add('ccscript/redux/redux_changes.ccs')
    if len(prior) != 42:
        raise ValueError('Prior36+1+5 source scope changed')
    excluded_by_module = defaultdict(list)
    for index, row in enumerate(ledger['excludedSpanLedger']):
        excluded_by_module[row['module']].append(index)
        if row['module'] not in LEDGER_EVIDENCE:
            raise ValueError('New excluded module requires manual source review: ' + row['module'])
    if 'define DEBUG_BUILD = 0' not in source_texts['ccscript/debug/debug_menu_enabler.ccs']:
        raise ValueError('Pinned debug activation changed')
    rows = []
    for source in ledger['sourceInventory']:
        name = source['path']
        module = Path(name).stem
        links = set(by_source[name])
        indices = excluded_by_module.get(module, [])
        if indices:
            links.update(LEDGER_EVIDENCE[module])
        native_refs = []
        boundary = 'Linked report decisions and structural conversion are not full semantic parity.'
        if name in EXTRA:
            classification, decision, bindings, extra_links, boundary = EXTRA[name]
            links.update(extra_links)
            native_refs = refs(bindings)
        elif name in prior:
            classification = 'prior-named-hook-review'
            decision = 'Already individually source-reviewed in the prior36 bugfix /15 redux_changes /29 five-module scope; current supplemental runtime evidence retains its own exact identities.'
        elif links:
            classification = 'existing-native-feature-or-excluded-span-review'
            decision = 'Explicit module or assembly-family native/data/adaptation decision already exists in linked reviews. Review/classification alone is not a behavior pass.'
        elif name.startswith('ccscript/debug/'):
            classification = 'developer-conditional-source'
            decision = 'Pinned boot DEBUG_BUILD is0. Converted debugger dialogue and installed debug-only hooks do not prove wholesale Kirby/developer-menu parity or a missing normal-story feature.'
            links.add('research/redux-remaining-feature-review.json')
        elif name.startswith(('ccscript/data/', 'ccscript/dialogue/', 'ccscript/shops/')):
            classification = 'converted-script-or-special-format-data'
            decision = 'Covered by existing converted script/pointer accounting or dedicated presentation converter. Shop/dialogue story reachability and every branch remain separate behavioral requirements.'
            links.add('research/maternalbound-dialogue-report.json')
        elif name.startswith(('ccscript/definitions/', 'ccscript/essential/')) or name in ('ccscript/main.ccs', 'ccscript/redux/menu_macros.ccs'):
            classification = 'definition-or-command-library'
            decision = 'Import/definition/DSL support in the existing source graph. A library definition or syntactic write does not demonstrate an instantiated live caller.'
            links.add('research/maternalbound-dialogue-report.json')
        else:
            raise ValueError('Source lacks explicit existing/manual accounting: ' + name)
        rows.append({'source': name, 'pinnedInventorySha256': source['sha256'],
                     'syntacticWriteSites': source['syntacticRomWriteSites'],
                     'outsidePriorNamedHookSources': name not in prior,
                     'classification': classification, 'sourceBackedDecision': decision,
                     'existing105SpanIndices': indices, 'nativeReferences': native_refs,
                     'evidence': [ev(path) for path in sorted(links)], 'behaviorBoundary': boundary,
                     'newMissingNativeAdapterProved': False, 'fullModuleBehaviorVerifiedByThisRunner': False})
    # Additional v8 inventory evidence supersedes only the explicitly limited
    # older game-over exclusion. Do not rewrite or relabel the frozen gap report.
    newer = []
    for mode in ('original', 'redux'):
        for kind in ('inventory-gameover', 'inventory-transform-pool'):
            relative = f'research/{mode}-{kind}-dev17-v8.json'
            data = read(args.root / relative)
            if not data['allPassed'] or data['runtimeSha256'] != V8 or data['privateBuild']['productionLibrarySha256'] != LIB:
                raise ValueError('New inventory report does not prove exact frozen-v8 production execution: ' + relative)
            newer.append({'mode': mode, 'scope': kind, 'caseCount': len(data['cases']), 'evidence': ev(relative),
                          'actualV8ProductionLibraryExecuted': True, 'sourceOverrideUsed': False,
                          'pairedObserverHashIsNotSeparateObserverExecution': True})
    unused = []
    # This is a narrow lexical call-site audit on already inventoried files,
    # not a new import/write/opcode traversal. Ignore comments/declarations.
    from maternalbound_dialogue import without_comments
    for command in ('register_startup_pointer', 'checkable_person', 'set_pixel_mode', 'set_tile_mode', 'load_two_str', 'load_two_str_callonhover'):
        found = []
        for name, text in source_texts.items():
            clean = without_comments(text)
            for line, value in enumerate(clean.splitlines(), 1):
                if re.match(r'\s*(?:command|define)\b', value):
                    continue
                if re.search(r'\b' + re.escape(command) + r'\b', value):
                    found.append({'source': name, 'commentStrippedLine': line})
        unused.append({'command': command, 'nonDeclarationSourceOccurrences': found,
                       'foundCount': len(found), 'proofBoundary': 'Lexical source-use check, not bytecode reachability or a behavior pass.'})
    broader = [row for row in rows if row['outsidePriorNamedHookSources']]
    report = {
        'format': 'redux-wider-source-accounting-dev16-v8-v1',
        'status': 'complete-existing-inventory-crosswalk-not-full-gameplay-parity',
        'upstreamCommit': PIN, 'structuralAccountingVerified': True,
        'reusedInventory': {'ledgerPath': str(args.assembly_ledger), 'sourceFiles': 191,
                           'syntacticRomWriteSites': 5661, 'excludedAssemblyOrSpecialFormatSpans': 105,
                           'unclassifiedExcludedSpans': 0, 'newImportWriteOrOpcodeInventoryParsed': False,
                           'graphCategoryCounts': bridge['sourceGraph']['categoryCounts']},
        'priorNamedScope': {'sources': 42, 'activeBugfixImports': 36, 'reduxChangesLiteralWrites': 15,
                           'fiveControlBattleModulesLiteralWrites': 29,
                           'scopeCountsAreNotAddedToOtherOverlappingReviews': True},
        'widerScope': {'sourceFilesOutsidePriorNamedSources': len(broader),
                      'writeBearingSourcesOutsidePriorNamedSources': sum(bool(row['syntacticWriteSites']) for row in broader),
                      'syntacticWriteSitesOutsidePriorNamedSources': sum(row['syntacticWriteSites'] for row in broader),
                      'classificationCounts': dict(Counter(row['classification'] for row in broader))},
        'sourceCrosswalk': rows,
        'excludedSpanEvidenceCrosswalk': [
            {'existingLedgerIndex': index, 'module': row['module'], 'kind': row['kind'],
             'existingClassification': row['nativeClassification'], 'existingDecision': row['reviewDecision'],
             'evidence': [ev(path) for path in LEDGER_EVIDENCE[row['module']]],
             'classificationIsNotFullBehaviorPass': True}
            for index, row in enumerate(ledger['excludedSpanLedger'])],
        'newerExactV8InventoryEvidence': newer,
        'supersededOlderGap': {
            'preservedOldReport': ev('research/redux-hook-semantic-gaps-dev16-v8.json'),
            'correction': 'The game-over/reset timed-item context listed open by that limited refresh is now covered by16 actual native entry/text/menu/reset outcomes per profile plus later lifecycle callbacks, recorded separately on finalv8. Original retains its source-expected dormant Egg after same-process game-over; Redux timers continue.',
            'remaining': 'Complete intro/reboot parent, natural acquisition/roaming and every story/save dependency remain excluded. This does not change the older report or turn its exclusions into prior defects.'},
        'narrowUnusedDefinitionChecks': unused,
        'practicalRemainingIntegrationRequirements': GAPS,
        'newConfirmedNativeImplementationRequirements': [],
        'emptyConfirmedListMeansNoNewDefectProvedNotNoWorkRemaining': True,
        'newMissingNativeAdapterProved': False, 'newNativeDefectProved': False,
        'fullReduxSemanticParityVerified': False, 'fullStoryVerified': False,
        'exactV8ProvenanceOnly': {'runtimeSha256': actual_runtime, 'librarySha256': LIB,
                                'thisRunnerExecutesNeitherPlayerNorObserver': True},
        'mutations': {'nativeC': False, 'sharedBuild': False, 'ownerSaves': False, 'ROM': False,
                      'packs': False, 'historicalReports': False, 'onlyFreshMetadataOutput': True},
        'inputs': inputs, 'runner': {'path': str(Path(__file__).resolve()), 'sha256': sha(Path(__file__))},
        'limits': [
            'Complete accounting refers to all rows of existing pinned inventories, not all instantiated patches, execution branches or full gameplay.',
            'Syntactic ROM write inventory includes macro definitions and is not an emitted patch count. No completion percentage is computed.',
            'Referenced historical reports retain actual runtimes and limits. A symbol, converted byte match, classification or selected fixture is never promoted to whole-module parity.',
            'No new original-machine run, native gameplay run, pixel/audio comparison or scene traversal is performed by this accounting runner.',
            'Prepared production-library drivers execute common code with player platform objects; matching observer hash is paired provenance unless the cited report explicitly says both executables were run.',
            'Unused APIs and disabled developer startup are explicitly distinguished from active reachable normal-story requirements.',
            'All commercial game payloads and private saves remain local; this output contains metadata/references only.',
        ],
    }
    if any(sha(Path(path)) != value for path, value in inputs.items()):
        raise ValueError('Read-only audit input changed during accounting')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(args.output), 'structuralAccountingVerified': True,
                      'widerScope': report['widerScope'], 'newConfirmedNativeImplementationRequirements': 0,
                      'fullStoryVerified': False}))


if __name__ == '__main__':
    main()
