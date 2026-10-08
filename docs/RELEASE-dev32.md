# Redux dev.32 - Broader Story Shuffle v4

The previous Surprise mode kept ordinary loot in the same category and globally protected many items merely referenced by scripts. V4 mixes ordinary loot across categories, includes rare/priceless equipment, changes Cookie drops and shop baselines, and adds wild encounter lineup randomization. Keys, quest helpers, required trade supplies and scripted boss lineups remain intact. [Exact rules](../RANDOMIZER.md).

For seed 595173162 on the owner's reviewed Redux base, v3 changed 59 gift records, 134 shop slots, 142 stat records and 39 drop records. V4 changes 172 gift records, 286 shop slots, 142 stat records, 129 drop records and 426 weighted wild encounter slots. These are data records, not unique reachable chests or natural gameplay battles.

V3 recipes reproduce their old pack and identity exactly. V4 uses a separate identity/save folder. The production native player, base packs, normal-story saves and format16 are unchanged.

Both editions pass 1,000 v4 seeds, 62 option/style combinations and 12 corruption controls. Frozen v3 tests pass 1,000 seeds and 30 combinations per edition. Native fixtures verify 177 gift records, 230 enemy records and all expected lineups across 278 prepared placement/event states per edition, with 4,096 RNG samples per state. Entity creation is suppressed in the chooser fixture; this is selection coverage, not rendered spawning or story certification.

The two corrected fresh-setup packs also pass 1,000 v4 seeds each and all 62 combinations. Both editions complete an automated opening and cold quick-save restore; 12 selected Redux lineups complete prepared battles through real menus, actions, rewards and cleanup. The launcher recovery suite and compact UI review pass. Four reviewed base-pack identities are covered; a full randomized campaign is not.

This update records a [RetroPortingToolKit engineering review](../research/retroporting-toolkit-review-20261008.md), with rendering and comparison methods for future work. No snesrecomp engine replacement is claimed.

Full randomized campaigns, website seed compatibility and native Open/Ancient Cave/Keysanity remain unverified or unavailable. [Machine-readable v4 evidence](../validation/story-shuffle-v4-dev32.json).
