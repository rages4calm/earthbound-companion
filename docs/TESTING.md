# Testing the native conversion

The audit uses isolated sessions, explicit input identities and repeatable native execution. Tests do not edit the owner's playthrough. A prepared scene verifies that scene and its asserted branches; it does not verify the quest that normally reaches it. The autonomous audit is stopped; development now follows playtesting reports. See [dev.19 release evidence](RELEASE-dev19.md). Earlier reports retain their tested release identities.

## Three different kinds of evidence

1. **Native scenarios** drive actual menus, dialogue transactions, entity scripts and battle continuations in copied or prepared states. They assert concrete outputs and bounded completion.
2. **Player/observer comparisons** detect diagnostic-build differences using normalized host-pointer fields. Both share game code, so agreement is not an independent reference.
3. **Original-machine comparisons** execute byte-checked Original or pinned Redux SNES routines in a separate development reference. They record CPU/RAM, call ordering and operand ranges. Some narrow helper tests explicitly stub their children; full consumer tests are identified separately.

Reports retain executed library/executable hashes and source identities. Historical evidence is not relabeled as execution on a later build. Known red builds and deliberate corruption controls check that tools can detect the failures they claim to test. Missing inputs, incomplete output and timeouts are failures, rather than successful skips.

## Run the subsystem audit

After preparing the pinned native source and building player and observer executables, use a new private scratch folder:

```powershell
python scripts/native_conversion_audit.py `
  --player "build/companion/earthbound.exe" `
  --observer "build/jev-qa/earthbound.exe" `
  --original-assets "path/to/original/assets.pak" `
  --redux-assets "path/to/redux/assets.pak" `
  --msu-dir "path/to/msu" `
  --scratch "private-qa/subsystems-new"
```

This executes 60 requested cases across both profiles/builds, including cold saves, key items, encounters/instant wins, SFX and bicycle audio, sprint/cliff collision, stairs, fades, VM/AI, names, movement, PSI, combat, battle sprites/art and SPC/MSU transitions. The report distinguishes these subsystem checks from independent reference or full-story coverage.

## Scenario and oracle tools

Tools under `scripts/` provide `--help` and require explicit local inputs. Battle tools execute the real production dispatcher and selected child continuations from a frozen library. Prayer, ending and final-letter tools execute full transactions from their documented entry prerequisites. Movement tools compare ordinary copied-save traces or prepared coordinate/terrain cases; their reports identify which.

- `shop_transaction_qa_dev18.py`, `shop_transaction_cases_dev18.py`, `shop_inventory_outcome_audit_dev18.py`: actual packed buy/equip/sell/refund/cancel transactions, source-selected prerequisites, cold menu continuations and complete bag preservation. [Frozen instructions and limits](../research/shop-audit-dev18-final-evidence.md).
- `runtime_constants_headers_qa.py`, `runtime_constants_clean_build_qa.py`: numeric assembly constants, malformed-input controls, fresh code-only compilation and the explicit synthetic loader fixture.
- `redux_special_movement_integration_qa.py`, `audit_redux_wider_source_accounting.py`: prepared map/timer continuations and the existing wider source-ledger crosswalk; structural accounting is separate from behavior.
- `redux_story_cutscene_parent_qa.py`: complete prepared rope, flight, ghost and hotel-capture parents with immediate post-bootstrap cold loads. [Frozen v8 scope](../research/story-cutscene-parent-dev16-v8-evidence-manifest-final.json).
- `shop_special_entry_qa_dev19.py`, `shop_special_entry_cases_dev19.py`: Tools ownership and selected OneItem-vendor transactions, including cold continuations. [Frozen source contracts](../research/shop-special-dev19-evidence.md).
- `timed_item_lifecycle_qa.py`, `timed_item_cold_continue_qa.py`: real private phone saves, Continue finalization, 6,000 party-leader ticks and cold item transitions.
- `inventory_transform_pool_qa_dev18.py`, `inventory_gameover_lifecycle_qa_dev17.py`: actual phone/F6 loads, full/free bag recovery and real game-over branches.
- `battle_full_encounter_qa_dev18.py`: complete prepared encounters through platform-input menus, turns, rewards, special escapes and cleanup.
- `snes_direction_approach_oracle.py`, `redux_encounter_initiative_machine_qa.py`: actual source-machine fine direction and contact-to-encounter initiative.
- `snes_sprite_render_abi_oracle.py`, `snes_sprite_entry3_abi_oracle.py`, `native_sprite_render_abi_qa.py`, `native_sprite_entry3_abi_qa.py`, `event_wram_consumer_qa.py`: complete original/pinned render bodies, their real native dispatch entries, WRAM-consuming events and private cold continuations.
- `rng_consumers_qa_dev16.py`, `overworld_rng_qa_dev16.py`: source-specific random consumers and cold restoration.
- `snes_rand_mod_oracle.py`, `snes_spawn_probability_oracle.py`: complete original arithmetic/probability routines with protected CPU/RAM and exact call counts.
- `redux_party_screen_oracle.py`, `redux_party_follow_reachability_qa.py`: mode-specific follower rules and ordinary Redux walking/running.
- `battle_*_qa_dev16.py`: callback effects, real child modes, targets, text amounts, statuses, gear, guards and source boundary controls. The battle ledger lists the exact callbacks and untested branches.
- `redux_prayer_cinematic_qa.py`, `redux_ending_transaction_qa.py`, `redux_ending_letter_qa.py`: full source-prerequisite cinematic/ending transactions.
- `event_interpreter_gap_qa.py`, `original_movement_pack_qa.py`: script binding, old Original ghost states and donor extraction. Structural root scans remain separate from runtime proof.
- `audit_progression.py`, `original_progression_upgrade_qa.py`: source-derived Original story protections and exact-pack upgrade checks.

Reference-machine binaries, ROMs, generated callers, extracted bytecode and runtime game data stay in private scratch directories. The reference is a development dependency, not part of gameplay or the player ZIP. The [Retro Porting Toolkit co-simulation guide](https://retroportingtoolkit.com/docs/guides/set-up-co-simulation) explains the general comparison discipline; these tools implement EarthBound-specific contracts.

## Check a real native backup

The launcher includes a developer CLI that copies a real format-16 checkpoint into a new directory, damages/restores only that copy, refuses an obsolete format-12 copy, then loads the restored checkpoint in the native engine:

```powershell
& "EarthBound Companion.exe" --checkpoint-recovery-test `
  "path/to/matching/assets.pak" `
  "path/to/quicksave_1.bin.0" `
  "private-qa/checkpoint-new"
```

Run this from a complete installation containing `Game/earthbound.exe` and SDL2. Supply the exact matching pack. The result records checkpoint, pack and executable hashes. Owner inputs remain unchanged; private outputs contain game data and must not be uploaded.

## Release checks

`verify_redux_package.py` extracts a fresh ZIP, checks its file manifest and absence of ROM/game/save payloads, performs actual setup from a headered owner ROM without Python on PATH, repairs a corrupt MSU track, checks all 164 tracks, runs story/seed openings and validates save-profile isolation. Its optional `--legacy-original-pack` checks the real Original data-upgrade path.

Each accepted content pack also runs 1,000 deterministic seeds and all 30 option/preset combinations, with independent rejected mutations of protected story assets, stock and scripted enemies. These preservation checks do not establish a full randomized playthrough.

Further testing still includes untested turn/encounter branches and groups, untested shop/service/barter transactions, natural NPC callers, full progression, photo acquisition, all map/event/audio transitions, displays/controllers and start-to-ending story/seed playthroughs. Reports should identify the first changed field or missing continuation, rather than infer a cause from the final screenshot.

## Dev.17 reproducible additions

Use the explicit input paths in each tool's `--help`. `redux_pack_upgrade_qa_dev17.py` exercises the real ROM-driven graphics update on isolated copies. `runtime_asset_alignment_qa_dev17.py` varies private pack alignment and tests cleanup/failure controls. `native_sanitizer_qa_dev17.py` builds a separate instrumented runtime; `native_sanitizer_scenarios_dev17.py` links its untouched archive into whitelisted source-prerequisite scenarios. Menu, transition, item-selector and battle-art tools are bound by the manifests linked from the current audit. Historical manifest paths beginning `tools/` refer to the same byte-identical public file under `scripts/`; the manifests retain their original paths and hashes. Reports from dev.16 v9 or dev.17 v3 retain those executed identities.

## Dev.18 additions

The current ledger and [dev.18 audit](NATIVE-AUDIT-dev18.md) bind the final player/observer and exact native/data inputs. Presentation drivers compare the owner's compiled Original/Redux routines with the actual native map, intro, sequence and swirl consumers. Title/save drivers run real parents and fresh-process cold restores. Sprite upload checks cover every nonempty packed frame; equipment checks cover all 85 equipment IDs and four PC flags. These are bounded subsystem/parent checks, not full quests or story completion.

Use `verify_redux_package_dev18.py` for the actual clean ZIP, self-contained owner-ROM setup, soundtrack repair, native story/seed opening and actual checkpoint recovery. `redux_pack_upgrade_qa_dev18.py` runs the real ROM-driven historical pack update. Runtime and sanitizer reports retain the exact binaries that executed them. Historical builder hashes describe historical input construction; the current builder creates dev.18 packs.

## Dev.19 release integration

The completed private party-name/Give suites are now integrated and published; their exact tested player is the shipping binary. See [release evidence](RELEASE-dev19.md) and [shipping provenance](../research/native-runtime-dev19-provenance.json). The reused dev.18 clean-package verifier also checks dev.19 because its pack/content contract is unchanged. No ongoing automated playthrough or autonomous audit is scheduled.
