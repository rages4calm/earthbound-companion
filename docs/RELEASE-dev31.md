# Redux dev.31 - Cast-name repair and continued source audit

Party names in the ending cast could use the wrong graphics tiles. Original extraction read eight bytes before the real table; Redux extraction used a different, incorrect ROM offset. Both now read ROM offset 0x3FDB5, confirmed by the assembly table and the actual consumer instruction.

The native runtime recognizes the two exact legacy tables and restores their source-defined tile positions for both name rendering and placement. Existing Original/Redux packs keep their identity, save namespace and format-16 checkpoints. Fresh setup produces corrected packs; the launcher accepts both reviewed versions and does not require an automatic rebuild of current dev.30 profiles. Optional story-save import accepts only the exact reviewed presentation change and preserves source saves and seeds.

The explicitly resumed audit now includes:

- All 32 actual photo-script parents in both editions, including Saturn/Tenda branches, acquired/availability flags, preservation of the other 31 slots, reordered afflictions and capped play time. Actual camera-return and committed-photo checkpoints continue in fresh processes. The ordinary Onett walking trigger is also verified in both editions.
- Eleven legal name vectors across Original/Redux, including wide/narrow/short and six-letter accented names, with independent glyph pixels, source tile positions, five printed name maps and cold continuation. Corrected fresh packs pass too; dev.30 fails the source-coordinate regression.
- 68 qualified evolving encounter cases, including 17 strict warm/cold endpoint pairs. These execute real menus, AI, actions, KO, rewards and cleanup. Original has no active equivalent of Redux group473, so those four cases are explicitly excluded there.
- 44 legacy-pack release regressions and 76 corrected-pack checks across the shipping and freshly compiled public-source player. Both corrected packs pass 1,000 deterministic seeds and all 30 option combinations. Complete prepared ending transactions pass in both editions.

Earlier diagnostic failures are retained privately. The battle fixtures were corrected to observe AI at its actual entry boundary, account for translated text addresses, give the late-game fixture adequate offense and retain enough recorded button presses for post-battle level-up prompts. No battle production fix was needed for those fixture failures.

[Fresh packaged setup and recovery](../validation/package-dev31.json) · [Identity-bound audit receipt](../validation/continued-audit-dev31.json) · [Testing tools and reproduction](TESTING.md)

The installed player matches the final package manifest. A copy of the owner's latest credits checkpoint loads in that player, and protected saves, packs, settings and music remain unchanged apart from three installation-path remaps. Nine discarded build directories were moved to a dated private archive after bulk deletion was blocked by policy. [Installation and cleanup receipt](../validation/installation-and-cleanup-dev31.json).

This is bounded conversion evidence. Most photo tests enter a prepared script rather than establishing natural map/story reachability. Selected battle semantics are not all possible combat combinations or a full Original CPU reference. A fresh full randomized campaign, physical controller/display expansion and audible music review remain unverified. The owner's completed credits save is preserved. No ROM, extracted pack, soundtrack or personal save is distributed.
