# Dev.9 encounter and audio fixes

This checkpoint fixes three reported problems in the shared native runtime. The corrected original/Redux content packs, quick-save format 16 and randomizer seed identities are unchanged.

## Repeated instant victories

The crash dump faults in enemy battle-position layout after an invalid enemy ID (`65535`) was read through a cleared contact slot (`-1`). An overlapping enemy could start another camera shake during instant-win victory text: that path never sets the ordinary battle-scene flag, and the first encounter's cleanup clears the contact slot before the queued second encounter uses it. A prepared replay reproduces that nested contact in the previous code.

The shared contact handler now rejects contact while an encounter is active, including instant-win victory processing. It still permits enemies to join an existing encounter swirl and permits a new encounter when post-battle invulnerability expires. Encounter initiation validates live slots, enemy IDs and group indices before indexing entity data; stale contacts cancel safely. Enemy-list appends respect capacity. Camera restoration repairs an impossible nested-shake backup from older checkpoints.

Each edition/build passes 1,178 prepared checks, including all 230 non-placeholder enemy records. These call the actual contact, battle-entry, protection and enemy-layout functions. Six repeated instant-win setups also cover every value of the 120-frame protection timer. The count is grouped assertions, not 1,178 ordinary gameplay battles. These guards apply to original EarthBound, Redux and native Story Shuffle packs through their common encounter path; they are not specific to Twoson or mushrooms.

## Bicycle music after combat

Battle map reload invalidates the sector-song cache. While riding, the game correctly restores song 82, but subsequent sector lookups repeatedly issued a fade because the cached map song remained invalid. Both SPC and MSU playback became silent in the before-fix diagnostic.

Sector music lookups now leave the bicycle's independent song alone while riding. They still resolve the map's next song, and dismounting explicitly restores map music. Prepared ordinary- and instant-victory return sequences retain audible samples for three seconds in both audio modes and both editions.

## Intermittent sound effects

The game thread writes one effect per host frame. SDL's 1,024-sample callback advances the SPC engine in roughly two-frame bursts. Two host writes could therefore occur before the SPC engine read either command: a text or cursor effect overwrote the unread transaction/equipment effect. The original `READ_PORT` routine echoes consumed commands on output port 3.

Dispatch now waits for that acknowledgment before replacing input port 3. It drains at emulated audio-frame cadence as well as host cadence, with the queue protected by the shared audio mutex. A bounded 64-slot queue absorbs callback bursts; after prolonged suspended playback it retains recent effects instead of allowing a full ring to appear empty. Toggles are assigned when dispatching. Fast-forward still intentionally mutes audio.

Each edition/build passes 40 isolated effect cases: cash register 12, equipment 115, alternate shop sound 120, bicycle bell 23 and menu 27, with four music-bank selections and both original/SPC and MSU modes. The following text effect cannot overwrite the first; the SPC acknowledges it and produces nonzero effect samples. A further 256-request callback-cadence replay preserves order, and a suspended-callback overflow case drains correctly: 42 cases per edition/build.

Eleven production Redux shop/Goods/equipment/Status input replays pass with the real SDL dummy audio device in each audio mode. Buy, equip and sell checkpoints retain their expected money, inventory and gear changes, dispatch the script's expected sounds, and do not overflow the queue. Upstream `ShopSys.ccs` deliberately selects a different sound for some vendors; the conversion preserves that choice. No cash-register sound was added to actions where the source does not request one.

## Evidence and limits

- [Shared encounter/audio diagnostics](../validation/native-reliability-dev9.json)
- [SPC shop/menu replays](../validation/native-shop-spc-dev9.json) and [MSU replays](../validation/native-shop-msu-dev9.json)
- [Native runtime regression checks](../validation/native-runtime-regressions-dev9.json)
- [Three copied-owner quick-save resume checkpoints](../validation/native-owner-resume-parity-dev9.json)
- [Rebuilt executables, setup helper and clean upstream patch check](../validation/native-redux-dev9-build.json)

All tests write isolated copies. The key-item migration diagnostic remains an original-edition test: its legacy Tiny Ruby fixture assumes the original starting inventory, whereas pinned Redux deliberately removes that starting item for its Keys system. The ordinary original-edition key-item test passes; the Redux script and movement/combat checks pass separately.

The prepared audio tests measure command delivery and sample energy, and the production shop tests verify script dispatch. They do not establish every effect's perceptual balance against every soundtrack. Full story/randomized playthroughs and all story audio transitions remain unverified. These fixes do not certify complete MaternalBound compatibility.
