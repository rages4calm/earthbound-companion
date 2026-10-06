# Native conversion audit — dev.17

This development checkpoint fixes confirmed native defects and expands repeatable, source-backed testing. **Full MaternalBound Redux conversion and a complete story or randomized playthrough remain unfinished.** Test counts below describe executed assertions or prepared scenarios, not a percentage of the game converted.

## Changes in this checkpoint

- Pooled Keys can be selected by the real inventory menus. The Monkey Cave's King banana exchange, Tracy storage and eligible shop sales now use the selected pooled item's identity. Ordinary bag slots retain their source behavior. The narrow source inventory helper recognizes a pool-only bag without interpreting unrelated empty slots as keys.
- Shared menu pagination reserves its overflow row correctly. Full-bag barter choices remain reachable with normal buttons. Two-string menus render their right column at the source pixel position; standard Yes/No choices regain their source default page/type/confirmation sound request.
- Transition scrolling uses the source integer trigonometry table and wrapped arithmetic. The old table differed at 60 entries. Instrumented builds reproduced signed-shift failures in the prior transition code; the selected fixed prayer and ending scenarios pass.
- The pack loader aligns mapped assets before typed native access and releases all alignment copies on unload or partial-load failure. This fixes a reproduced instrumented alignment trap; it is not evidence that alignment caused a reported Windows gameplay crash.
- Redux setup now imports all 103 compiled battle-background graphics entries and corrects four palette lengths at their actual 2/4-bit consumers. Exactly 107 assets change relative to dev.16; dialogue, progression tables, world maps and audio remain byte-identical.
- A guarded graphics update retains the previous profile and copies compatible story phone/F6 saves into the corrected pack's separate namespace. Existing seed files retain their exact base identity and saves. Old seeds require their retained base pack; newly generated seeds use the corrected pack. A cold mid-battle save retains its cached old artwork until the next genuine battle loads.

## Evidence and limits

| Area | Executed evidence | Limits |
|---|---|---|
| Pooled-item transactions | [Final production refresh](../research/inventory-selector-dev22-v4-refresh-manifest.json): 258 actual prepared parent sequences across Original and Redux, including 56 fresh-process continuations. [Detailed method](../research/inventory-selector-dev21-evidence.md). | Selected barter/storage/retail branches, not every service or natural quest. Earlier API evidence retains its v3 identity. |
| Menu and transition comparisons | [Frozen evidence](../research/remaining-hook-menu-transition-final-manifest-dev17-v4.json) and [final pack supplement](../research/remaining-hook-menu-transition-finalpacks-supplement-dev17-v4.json). Each mode passes 546 pagination layouts, source font/highlight comparisons, 4,616 transition initializer comparisons and 340 real native transition preparations. | Some independent machine tests bound or exclude child streaming updates. The supported pooled selector maximum is 78 actual items; 80-item overflow behavior is not claimed. |
| Backgrounds and PSI | [Final production evidence](../research/battle-art-dev20-dev17-v4-final-manifest.json): 1,270 prepared native cases, 5,294 played PSI frames, three actual cold processes and 4,123 assertions; zero skips. Original and compiled Redux inputs remain separate. | Actual decoding/upload/animation consumers and a prepared old-to-new cold battle, not every naturally reached ability or complete battle. |
| General regression | [Final runtime jobs](../research/native-regressions-dev17-v4.json), including 60 requested player/observer subsystem checks, RNG warm/cold checks, hotel transactions, Jeff repairs, the copied Threek save, prayer, final letters and ending branches. | Prepared/source-prerequisite scenes do not verify the quests that reach them. |
| Instrumentation | [30 subsystem cases](../research/native-sanitizer-dev17-v4-green.json) and [16 further scenario jobs](../research/sanitized-scenarios-dev17-v4-summary.json), with explicit trap controls and source/runtime provenance. | GCC undefined-behavior instrumentation is an additional check; it does not prove memory safety or complete gameplay parity. Failed earlier runners remain recorded as failures. |
| Shopping/bicycle audio | [Expanded audio evidence](../research/audio-delivery-dev19-v9-final-manifest.json): 186 prepared fixtures and 946 process executions compare actual SPC acknowledgement, DSP activity and final SDL PCM against target-suppressed controls, including three callback buffer layouts and normal/instant-win bicycle restoration. | **Executed on immutable dev.16 v9**, not relabeled dev.17. Physical-device listening and every audio transition remain unverified. |

The reference tools execute byte-checked routines from the owner's Original ROM or the pinned compiled Redux input. Some compare narrow helpers with explicitly bounded children; others run actual native parent transactions. The JSON records distinguish these methods. Development reference tools are not shipped inside the player.

The [actual ROM-driven graphics upgrade](../research/redux-real-upgrade-dev17-v4-r2.json) passes 13 checks, including every pre-existing seed file unchanged, exact story-save copies, previous-profile backup, old/new seed verification, actual checkpoint recovery and repeated setup. Original-data rebuilding may add its documented starter seed; the first test incorrectly treated that addition as a mutation and was corrected. [Fresh public-source compilation](../validation/public-clean-source-dev17.json) applies the complete patch to pinned clean source, compiles without a ROM and passes eight runtime checks. [The corrected Redux randomizer policy](../validation/native-redux-randomizer-dev17.json) passes 1,000 seeds and all 30 option combinations; this is source-preservation evidence, not full seed progression.

## Reproducible identities

| Input | SHA-256 or revision |
|---|---|
| Native foundation | `76eacab54b05766b82c98da9c55d94d1236ece03` |
| Tamp dependency | `32034abf367d6bf2ee7a25cce8f64482cb955a65` |
| MaternalBound Redux source | `897d00833f4a08a0a92f106abf631629a6a6a041` |
| Complete published native patch | `6830770da2de72ef0e4df81a7bf731e6e3274045f6dde880879938d2eda9a4e2` |
| Frozen player | `970db06806793b2cbbad643c0a460b8f84bb6fa980ba49b6d09d1ca3ea88644d` |
| Frozen observer | `54553cfca96f6eab08842bb88decc37d59ab8cb4ede0bdf876dac19de9bd2f4a` |
| Production library | `b0cae8b3cce2c5a480b47cff9e7d6d96685ca123bb94031c23a035889ec0e3c0` |
| Updated Original pack | `01af4f4b590d9e83937b772399ee60a9181e2384e13c1567c94dfc92101b5549` |
| Previous Redux pack | `ed299183d4b1aff4b38c56ef16da28a256c3a65d33ba1d9327c9b19df0272ef3` |
| Corrected Redux pack | `3ed273eaedad5131a13dc07b6916377130857929854886b139b30a723482f8b9` |

Packs, ROMs, soundtrack payloads and saves remain local. The release and source repository contain none of those files. See [Testing](TESTING.md) for the isolated tools and [Source lineage](../UPSTREAM.md) for upstream dependencies and licensing limits.

## Remaining conversion and verification

The systematic importer/consumer review has confirmed remaining Redux Town Map/label omissions; both tested game-over scenes render identically to the compiled source despite different repacking. An actual title observation also confirms that some legal accented naming glyphs become question marks in character window titles. These are active follow-up conversion work; dev.17 does not claim to fix them.

Escargo's real phone/request/door/courier chain now passes 72 prepared sequences across both editions, including 18 fresh-process continuations: delivery/pickup, full bags/storage, cancellation, cash/refunds, pooled items and natural route-failure controls. These are selected parent transactions, not every naturally reached location. Further work includes remaining upstream assembly consumers, untested menu/service and combat branches, full story progression, natural photo acquisition, all map/event/audio transitions, controller/display/device testing, and start-to-ending Original, Redux and seed playthroughs. A complete audit requires both automated evidence and independent playtesting.

The playable checkpoint is useful for further testing while this work continues. Please report the edition, release, settings, location/action, and a copied phone/F6 save where possible. Never replace your only good save to reproduce a bug.
