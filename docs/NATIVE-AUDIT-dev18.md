# Native conversion audit — dev.18

This checkpoint converts confirmed missing presentation data and fixes native title/save-menu behavior. **Full MaternalBound Redux compatibility and complete story or randomized playthroughs remain unfinished.** Counts describe executed assertions and prepared scenarios, not a percentage of the game converted.

## Changes

- Import the six Redux Town Maps and Map label with bounded graphics transfers. The two tested game-over scenes already match the compiled source and need no replacement.
- Import Redux gas-station intro graphics and Starman teleport frames. The other tested sequence frames already match their compiled input.
- Import the 31 swirl payloads whose decoded rows differ, and implement the source's second battle-transition window. Rebuild its derived cache after F6 without advancing the serialized transition timer or cursor.
- Preserve legal extended glyphs in native window titles and file-select slot labels, including highlighting. This is a bounded title/slot representation; generic dialogue is unchanged. An old cached question mark is repaired when the menu is reopened.
- Determine occupied phone-save slots from a pure local save peek after a fresh-process F6 restore. Continue no longer depends on an uninitialized file-select cache, and the peek does not load or mutate live game state.
- Recognize an already-current Original pack during setup. It is no longer incorrectly rebuilt or given another starter seed.
- Update exactly **41 presentation assets** relative to dev.17. Story scripts, items, enemies, world maps and audio remain byte-identical. The guarded upgrade accepts only reviewed historical pack pairs and copies compatible phone/F6 story saves. Save format remains 16. Existing seeds retain their original exact base; new seeds use the corrected pack.

## Executed evidence

| Area | Evidence | Practical limits |
|---|---|---|
| Maps, intro, sequences and swirls | [Final player proof](../research/presentation-release-dev18-v2-final-manifest.json): 6,794 assertions, eight prepared complete encounters, real cold continuations and all 126 compiled swirl row comparisons. | Staged actors and selected cold scenes; Starman appearance stops at the first ordinary movement wait. Mask checks do not establish all final audiovisual composition. |
| Titles, slots and Continue | [Paired final builds](../research/title-save-menu-dev18-v2-final-manifest.json): 1,324 direct producer cases plus actual Goods/Equipment/Status/naming parents, occupied-save cold cases and slot-font comparisons. | These title and file-slot fixes do not fix the separately confirmed party-target glyph bug. Prepared source names are distinct from naturally reached name-entry quests. |
| Every packed sprite frame | [Upload proof](../research/sprite-frame-upload-dev25-dev18-v2-manifest.json): 41,430 assertions and 10,351 real native uploads across 464 Original and 483 Redux groups. | Pixel/flag/geometry and VRAM transfer comparisons; group 0 is the explicit empty placeholder. Natural OAM composition, live palette use and every story animation are separate. |
| Normal/tiny terrain entry and exit | [Compiled-source doorway parents](../research/special-terrain-dev27-dev18-v2-manifest.json): 48 processes including 16 cold continuations, ordinary Y exhaustion/recovery, four followers/ghost follower and real history writes. | Selected source doorway pairs and source-sized tiny sprites; full quests, all tiles and robot/water integration remain separate. |
| Every active packed equipment ID | [Equipment proof](../research/all-equipment-dev27-final-manifest.json): 85 IDs, 744 complete Equip parents, 32 included cold continuations/comparisons, 2,720 compact consumers and 279 source checks. | Source prerequisites and one RNG seed per compact combination. Full combat turns, audible effects and natural equipment acquisition are not claimed. |
| Runtime regression | [15 jobs](../research/native-regressions-dev18-v2.json), including player/observer subsystem requests, RNG/cold state, hotels, Jeff repairs, prayer, final letters and all 32 prepared photo-credit branches. | Prepared photo playback does not verify natural photo collection. |
| Instrumentation | [30 subsystem cases](../research/native-sanitizer-dev18-v2-green.json) and [16 scenario jobs](../research/sanitized-scenarios-dev18-v2-summary.json), with explicit trap controls and actual instrumented provenance. | Additional undefined-behavior checks, not a proof of memory safety or all gameplay parity. |
| Actual setup and save upgrade | [13 owner-ROM-driven checks](../research/redux-real-upgrade-dev18-v2.json): exact corrected pack, unchanged source ROM, compatible phone/F6 copies, existing seeds unchanged, no extra Original starter, actual cold checkpoint load and idempotent repeat setup. | Isolated copies; no complete playthrough or old mid-transition migration claim. |
| Randomizer and Original setup | [1,000 seeds and 30 option combinations](../research/redux-randomizer-dev18-v3.json); [seven registry/setup cases](../research/original-setup-registry-dev18-v3-green.json). | Source-preservation guards, not proof of every seed progression. |
| Clean source | [Fresh code-only build](../validation/public-clean-source-dev18.json): pinned clean native source plus Tamp and the complete public patch; eight runtime checks. | Builds without a ROM; running real gameplay still requires owner-provided assets. |

Earlier service/item/Give transaction proofs retain their executed dev.17 identities: [268 service parents](../research/status-service-dev23-final-manifest.json), [310 overworld-use parents](../research/overworld-use-dev24-final-manifest.json), and [142 equipment/Goods parents](../research/goods-equipment-dev25-final-manifest.json). Earlier shopping/bicycle PCM evidence retains its dev.16 v9 identity. None is relabeled as a dev.18 execution.

## Reproducible identities

| Input | SHA-256 or revision |
|---|---|
| Native foundation | `76eacab54b05766b82c98da9c55d94d1236ece03` |
| Tamp | `32034abf367d6bf2ee7a25cce8f64482cb955a65` |
| Pinned Redux | `897d00833f4a08a0a92f106abf631629a6a6a041` |
| Complete native patch | `955557298e7b3f92d1b9e3ab8f952ffccea2707b6ebd16c9f2bbd442d665ae12` |
| Player | `3b467f471acd6bb5aa0cb29b96d89790be3097d8d0c5dd114ce2f128895d6292` |
| Observer | `033ed02642e0fc2cb61e2244de40c1b918f6b8e17635fb0c86eb7c11f92aeb92` |
| Player library | `6a2ea279a762df4c3a887eda7580e09c8034da55f08fb7f9059eb404c949d411` |
| Corrected Redux pack | `d9a772d10aff68bdf93c077cda640d42b835884d6834bb18bf0d43c3800f57bb` |
| Current Original pack | `01af4f4b590d9e83937b772399ee60a9181e2384e13c1567c94dfc92101b5549` |

Packs, ROMs, soundtrack payloads and saves remain local. The public source and release ZIP contain none of them. Historical manifest paths beginning `tools/` map to byte-identical public files under `scripts/`; manifests preserve their executed paths and hashes.

## Known follow-up work

The current [conversion ledger](../research/native-conversion-ledger-dev18.json) records a separate reproduced accented-name loss in party-target rows (Goods/PSI and selected services). A narrow private correction is in progress; dev.18's title fix does not claim to cover those rows. Two equipped-Give quirks reproduce the original source: a full bag's self-Give can leave an equipment index stale, and cross-character armor transfers can recalculate stats before other gear indices compact. An intentional QoL correction has passed private tests but is not integrated here.

Remaining coverage includes full story and seed playthroughs, untested combat combinations and multi-turn interactions, natural photo acquisition, all terrain/special party forms, progression events and soundtrack transitions, plus physical controller/display and listening checks. Independent playtesting remains necessary alongside automated source comparisons.
