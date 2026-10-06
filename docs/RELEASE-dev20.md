# Release checkpoint — dev.20

This update fixes two reported native conversion defects. All dev.19 fixes remain included. Game data, save format 16 and seed identity are unchanged.

## Shop-only Suporma and ordinary items

Suporma is Orange Kid's Super Orange Machine. The pinned Redux source gives it through an ordinary inventory script; it is absent from the source's fixed Keys menu. The native adapter incorrectly pooled all non-transforming key-category records, leaving some items absent from Goods/Tools/Keys but visible in every character's shop preview. The earlier assumption that Suporma should appear in Keys was incorrect.

Pooling now follows the exact source Keys membership, intersected with packed key categories. Fifteen non-transforming category records return to regular bags, including Suporma, Exit mouse, Brain stone, letters, King banana and Contact lens. Transforming Chick/Chicken and the temporary bulk-shop reservation retain their existing exclusions. Original mode retains its generic native Keys policy.

Older phone saves recover on load; F6 saves recover at the idle overworld root. Recovery uses the first free active PC bag because the old shared pool stored no owner. Full bags retain items until a slot opens, with source find/take/select access meanwhile. Recovery neither overwrites slots nor changes equipment. This cannot reconstruct duplicates that an earlier build already deduplicated.

## AUTO label after combat

Redux relocates AUTO from the original header position to byte offset `0x2B4`. Battle cleanup resets the battle flag before clearing the header; the old clear routine then chose the original address. The corrected clear uses the selected game edition throughout cleanup. Exact stale AUTO tile patterns in older idle roaming states are removed from the shadow and displayed tilemaps independently. Other window content and live battles are guarded.

## Executed checks

- [49 inventory fixtures in the player](../research/redux-inventory-membership-dev20-final-player-redux.json) and [49 in the observer](../research/redux-inventory-membership-dev20-final-observer-redux.json): all 256 classification calls, fifteen ordinary item duplicate/give/take/preview checks, phone/F6 recovery with one/three active PCs and zero/one free slot, transient menu/battle guards, and a copy of the reported save. Owner raw inventory/position observations are omitted from the public reports.
- [Original classifier control](../research/redux-inventory-membership-dev20-final-player-original.json) retains the existing policy.
- [Three real Auto Fight encounters in the player](../research/battle-auto-header-dev20-player-redux.json), [three in the observer](../research/battle-auto-header-dev20-observer-redux.json), and [three Original controls](../research/battle-auto-header-dev20-player-original.json), followed by prepared stale-header recovery, unrelated-window and active-battle controls. Actual menu button replays select Auto Fight; full production turns/endings execute. The [previous build leaks the label in all three Redux encounters](../research/battle-auto-header-dev20-baseline.json).
- [Six source-entry shop transactions](../research/shop-inventory-regression-dev20.json): buying with Suporma carried, selling Suporma, ordinary purchase/sale, equipped upgrade/trade and full-party bulk-buy rejection. Fixtures assert source wallet/item/equipment/SFX-request outcomes; this is not every shop branch or delivered-audio proof.
- [Shipping source/runtime provenance](../research/native-runtime-dev20-provenance.json): six reviewed source files change semantically from dev.19; complete 4,312-input comparison normalizes line endings only. Both binaries compile from a fresh pinned source archive, pinned Tamp submodule and the cumulative public patch. No replacement native handler objects are used.

The dev.19 clean setup/MSU evidence remains historical: setup helpers, data packs and soundtrack setup are unchanged. Dev.20 verification focuses on these reported defects, archive identities and basic packaged runtime controls. This does not certify every battle ending, cold battle state, every item event, full story/randomized progression, controller hardware or full pixels/audio.

## Continue playing

Keep your current saves. If loading a saved open menu, close it once and return to roaming so F6 recovery can run safely. With completely full bags, free a slot before expecting an affected item to appear in Goods. The game automatically retries; you do not need to edit your save. No ongoing goal, agents or automated playthrough are scheduled.
