# Packed equipment coverage on dev18-v2

Both packs contain 254 item records and 85 equipment IDs. Their exact types are 23 type 16 bash weapons, 19 type 17 shooting weapons, 11 type 20 body pieces, 12 type 24 arm pieces, and 20 type 28 accessories. Type17 belongs to the same masked equipment category as type 16 and is included. Across four PCs, the source usability flags allow 202 item/PC pairs and exclude 138. Packed membership does not establish where an item can be obtained in the story.

The independent source review passes 279 checks. Every equipment row's numerical fields are compared with the clean owner Original ROM and pinned Redux YAML. Selected Original/pinned flows corroborate menu category/usability filtering, None and equipment commits, signed modifiers, Poo's alternate strength parameter, miss rate, and resistance consumers. Original pagination explicitly appends the More entry with userdata 0. This is bounded source and bytecode review; the Original SNES CPU does not execute in this review.

Each profile passes 372 complete Equip parents: all 340 equipment/PC pairs, 16 full fourteen-slot duplicate-item parents, and 16 included fresh-process continuations of those full-bag parents. The actual pause menu, character/category/item selection, previews, equipment transaction, children, and closure execute on the production dispatcher with real platform replay buttons. Eligible pairs select the actual bag slot; excluded items must be absent from the offered choices, and actual B cancellation preserves equipment. The full-bag cases start with a duplicate equipped at slot 3, navigate source pages to slot 14, and verify the final item identity. Every cold case matches its warm peer. Across both profiles, that is 744 parent executions, 32 included cold continuations, and 32 warm/cold comparisons.

Final checks independently derive five normal-range stats, weapon miss rate, and five stored resistance fields from the corroborated packed parameters. They also check equipment locations and actual item identities, complete ordinary inventory arrays, wallet, HP/PP/status, pool/storage/delivery queue, and the closed window list. The initial fixtures are prepared before menu entry through real give/equip APIs. No production menu result, selected handler, post-entry inventory effect, or completion flag is substituted.

The separate compact corpus passes 1,360 real weapon/armor callback executions per profile, or 2,720 total. It covers all 85 IDs/four PCs, present/missing item controls, and retained battle stat bonus 0/17, using one serialized RNG seed per combination. The production callback and real weapon attack child complete. Source-derived expectations check party equipment/stat changes, battler bases and retained bonuses, resistance coefficients, unchanged inventory, and child function identity. These cases are separate from complete menu parents and do not prove complete battle turns.

No native defect was found in this bounded expansion. Early pilot failures were review-fixture mistakes: the expected paginated option list omitted the source More entry, and the wrapper expected one final snapshot although capture/resume records both capture-stage and resumed after-entry snapshots. Corrected fixtures retain the actual source overflow control and final resumed snapshot. The passing final runs use strict failure handling.

All execution uses the unchanged frozen dev18-v2 player library and platform objects. Only a private driver and copied main symbol are added for linkage, using the matching frozen include snapshots. Input files are bounded to 8192 replay frames per menu instead of generating 100000-frame files; exercised parents finish in the recorded bounded native steps. No per-frame dump is produced. Shared source/build, owner saves and packs remain unchanged. The private dev26 intentional equipped-Give QoL patch is separate and has not been integrated into this player.

The normal-range fixtures avoid Original's -1/256 carry-boundary oddities and the Redux upper-stat clamp changes. This evidence does not establish arbitrary malformed saves/bags, all stat boundaries, all inventory/permutation states, delivered labels/pixels/audio, a physical controller, observer execution, natural NPC/map/story reachability, a full playthrough, or complete conversion parity. Cold counts are included in parent totals; compact callback counts overlap earlier selected semantic coverage and are not a completion percentage.

## Identities

- Player: `3b467f471acd6bb5aa0cb29b96d89790be3097d8d0c5dd114ce2f128895d6292`
- Observer provenance: `033ed02642e0fc2cb61e2244de40c1b918f6b8e17635fb0c86eb7c11f92aeb92`
- Library: `6a2ea279a762df4c3a887eda7580e09c8034da55f08fb7f9059eb404c949d411`
- Original pack: `01af4f4b590d9e83937b772399ee60a9181e2384e13c1567c94dfc92101b5549`
- Redux pack: `d9a772d10aff68bdf93c077cda640d42b835884d6834bb18bf0d43c3800f57bb`
- Pinned Redux: `897d00833f4a08a0a92f106abf631629a6a6a041`

## Reproduction

Published tools live under `scripts/`; frozen metadata retains their local `tools/` paths. Use a matching developer source/build/runtime, your own extracted pack, the pinned source, and fresh scratch directories.

```powershell
python scripts/all_equipment_cases_dev27.py --assets MyReduxGame/assets.pak --output equipment-fixtures.json
python scripts/all_equipment_qa_dev27.py --build build/companion --native-source native-source --executed-source native-source --assets MyReduxGame/assets.pak --runtime MyReduxGame --project LocalPinnedRedux/Project --cases equipment-fixtures.json --scratch Scratch/equipment-parents --output equipment-parents.json --jobs 2
python scripts/all_equipment_qa_dev27.py --consumer --build build/companion --native-source native-source --executed-source native-source --assets MyReduxGame/assets.pak --runtime MyReduxGame --project LocalPinnedRedux/Project --scratch Scratch/equipment-consumers --output equipment-consumers.json
```

Add `--original` to the generator and runner for Original. Source review additionally takes your local clean ROM through `all_equipment_source_dev27.py`; neither ROM nor pack payload is included in the published evidence. A different source/build/pack is a new result with its own recorded identity.
