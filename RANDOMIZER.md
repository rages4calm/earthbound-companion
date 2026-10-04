# Native Story Shuffle v3

Open **EarthBound Companion → Solo Play → Randomized adventure**. The starter seed **Tonight in Onett** is ready in the library. Choose it and press **Play selected seed**, or enter a number/phrase and **Generate & play**. Generation is local and needs no additional downloads, browser, emulator or ROM setup.

## What changes

| Option | Native behavior |
|---|---|
| Gift contents | Replace eligible optional items within their original category. Keep every original source of protected quest/trade items, money gifts and special/zero-price items. |
| Shop stock | Randomize what shops sell by replacing optional items with another item of the same type (for example, food with food, or a weapon with a compatible weapon). Quest/trade items, each shop's first item, empty slots and other ineligible stock stay fixed. Item prices themselves do not change. |
| Enemy stats | Vary ordinary enemy HP, offense, defense and speed by a shared factor of up to ±15% in Balanced or ±30% in Surprise. Scripted-battle enemies, bosses and level-zero records remain fixed. Attack/defense and speed are bounded to the native 8-bit range; HP retains its 16-bit range. |
| Enemy drops | Randomize which items regular enemies drop by replacing optional loot with another item of the same type. The chance of getting a drop does not change. Quest/trade items, scripted-enemy/boss drops and special/zero-price drops stay fixed. Enemies that originally drop nothing still drop nothing. |

Eligible categories are priced weapons, armor, food, drinks, condiments, party food and healing items. Balanced replacements cost between half and one-and-a-half times the original price, with a small minimum range for cheap items. Surprise allows the entire eligible category, so strong equipment can appear early. Item prices and equipment stats themselves remain original. Some options have no alternative for an individual item; that entry stays unchanged.

The story, door routing, NPC dialogue/scripts, quest flags, enemy actions, encounter placement, boss records, experience and money rewards remain original. This preserves the original progression structure; it is not a new progression solver or a claim that a full randomized playthrough has been verified.

## Progression protection

Protection is mandatory in both styles and every option combination. It cannot be disabled. Story Shuffle v3 selects its policy by the exact active asset-pack hash. Each supported content profile has its own name, protected items, protected scripted enemies, seed identity and save directory. An unknown or unfinished profile is playable normally but cannot be randomized until its content-specific audit passes.

For original EarthBound (USA), `scripts/audit_progression.py` decodes all 61 original text/script blocks, preserves literal item dependencies outside debug/item-help menus, and adds Monkey Cave trades and item transformations. That policy protects **78 items** and **52 enemies used in scripted battles**. Quest categories and all boss/level-zero records receive further protections. Casey bat is excluded because of its unusual miss rate.

The pinned MaternalBound Redux profile has a separate policy derived from **64,360 decoded operations**, literal and dynamic item dependencies, native tables and **45 scripted encounter groups**. It protects **110 items** and **84 enemy records**. The generator understands the expanded 69-shop table and preserves Redux's 936-byte enemy-AI footer exactly. Both editions pass independent checks across 1,000 seeds and all 30 valid style/option combinations; a Redux randomized opening also runs natively. These results do not establish a complete randomized playthrough.

This includes ordinary-looking foods: **Hamburger, Pizza, Picnic Lunch, Skip Sandwich, Wet Towel**, plus the Ruler, King Banana and related trades. Their original shops, gift boxes and drops remain unchanged wherever they occur. The unchanged scripts still supply their scripted rewards. The original starting equipment, prices and money/experience rewards also remain fixed.

An independent validator compares the entire approximately 3 MB pack against the audited original. It permits only eligible optional reward/stat fields, enforces category/equip-mask/price/stat bounds, and rejects any other changed byte. It runs during generation and again immediately before launch. An unaudited replacement original pack is refused. **Check seed safety** runs the same checks; **Open safety report** describes what the generator preserved.

These checks prevent this generator from removing the protected original progression sources. They do not certify every scene in the community C engine, every player action or a completed playthrough.

### Older seeds

Version 3 adds the content-profile identity to every seed and recipe. Version 1 and 2 folders and saves remain on disk. They appear as legacy entries and must pass the current protection checks before play; the original v1 **Tonight in Onett** fails those checks and is blocked. **Create v3 for selected version** generates a new adventure from an older seed's text/options and the currently selected audited content profile, without overwriting its saves. It does not migrate an old playthrough or reproduce older output. New recipe imports require version 3.

## Seeds, saves and sharing

The same generator version, seed, options and exact content profile produce the same native data. Seeds accept 1–80 characters and are case-sensitive. Option or content-profile changes produce separate adventures. Generation starts from the active native asset pack selected in Companion. Only asset hashes with an embedded, content-specific progression policy are accepted. Normal visual/audio/gameplay settings still apply.

Each adventure lives at `UserData/Seeds/<identity>/`:

- `seed.json`: version, content profile, options, original/generated checksums and change counts.
- `safety.json`: protection counts, fixed item/enemy IDs, validation scope and the full-playthrough limit.
- `assets.pak`: generated native game data, approximately 3 MB; the soundtrack is shared.
- `recipe.ebseed.json`: portable seed/options recipe without game assets or saves.
- `spoiler.json`: actual changed gifts, shops, enemy stats and drops, identified by native table IDs.
- `Game/saves/`: this seed's phone saves and five quick-save banks.
- `Game/screenshots/` and `Game/game.log`: this seed's captures and diagnostics.

**Generate only** saves an adventure without launching. **Play selected seed** opens its normal title/file-selection flow; select its phone save to continue. **Resume quick save** loads the selected quick-save bank. Generating an existing seed reuses it and preserves its saves. The launcher checks the generated pack's checksum before play. Quick saves remain specific to the engine build.

Use **Export seed recipe** to share settings. The recipient needs the same content profile, exact native asset pack and generator version. **Import seed recipe** loads its profile, seed and options; generate it to recreate the adventure. Changing the loaded seed/options discards the imported pack constraint. Recipes do not include copyrighted game assets, soundtrack or your saves.

Backups use `UserData/Backups`. Close the game, select the adventure, and use **Back up seed saves** or **Restore seed backup**. New backups include `save-manifest.json` with the adventure ID, asset/engine hashes and save checksums. Guided restore refuses another adventure, mismatched assets, damaged files, duplicate/traversing ZIP paths or oversized archives. It backs up the current saves before applying the restored files and rolls back applied writes if an I/O error interrupts restoration.

**Phone saves only** is the default: it restores `earthbound.srm` and keeps quick-save banks/settings unchanged. Restoring quick saves additionally requires the same native executable hash and checks the native header, format version, length and payload CRC. The CRC polynomial is derived from this engine's actual source to retain its existing file compatibility. A restored checkpoint must still pass the native engine's own load validation. Existing backups without the new manifest remain available for manual recovery; guided restore does not guess their adventure. Original-story recovery is under **Mods & saves → Restore save backup**.

## Compatibility

This is **EarthBound Companion Story Shuffle**, an independent native generator. It does not reproduce [earthbound.app](https://earthbound.app/) seeds and does not implement Ancient Cave, Open mode, Keysanity, shuffled routes or arbitrary randomized ROM imports. The website's generator applies SNES code patches and relocates/expands data; those modes require additional native gameplay/script adaptations. A numeric seed copied from the website will create a different Companion adventure.

Research references: [stochaztic/eb-randomizer](https://github.com/stochaztic/eb-randomizer), [generator patches](https://github.com/stochaztic/eb-randomizer/blob/master/src/Randomizer/index.js), [Ancient Cave routing](https://github.com/stochaztic/eb-randomizer/blob/master/src/Randomizer/AncientCave.js). This edition retains the community C engine's existing compatibility limits and has not been played through to the ending.

The upstream randomizer's [README](https://github.com/stochaztic/eb-randomizer/blob/master/README.md) itself marks dangerous options and states that Keysanity is disabled in its UI due to softlock issues. Native Ancient Cave/Open mode need their actual routing, script relocation, game-code patches and progression logic ported together. They remain unavailable here; copying randomized tables alone would not establish that compatibility.

## Developer verification

`Verify.ps1` includes **1,000 seeds**, all **30 valid option/style combinations**, deterministic output, option isolation, exact protected-byte checks, native stat bounds, content identity and recipe roundtrip, save preservation/isolation, backup/restore checks, content-pack mismatch and tamper rejection. Negative cases deliberately remove trade foods, alter scripted battles, change other assets, submit an unaudited content pack, rewrite an unsafe legacy manifest with a matching checksum, damage a backup and inject ZIP traversal; all are refused. `tools/validate_randomizer.py` exercises the native gift lookup and actual battle-stat initialization, fresh opening, seed quick-save/resume, 1080p output, real shared MSU tracks and invalid-session refusal. These use isolated validation folders.

Native `--session-dir DIRECTORY` is resolved before any save migration/read/write and refuses an invalid directory. The launcher writes absolute soundtrack paths into each session. The generator version must change when algorithms or seed identity semantics change.

Advanced local generation: `"EarthBound Companion.exe" --generate-seed "my seed"` (optional `--surprise`), or `--recipe "recipe.ebseed.json"`. These commands generate data without launching gameplay.

Advanced validation: `"EarthBound Companion.exe" --check-seed "full seed folder path"` returns zero only if the manifest, original pack, generated pack and protection checks pass. It does not launch the game or modify saves.

For reproducible native recovery verification, run the randomizer test fixture, `tools/validate_randomizer.py`, then `"EarthBound Companion.exe" --native-recovery-test "full validation/randomizer path"`. The last step damages an isolated native checkpoint, restores it using the shipped recovery code, and verifies that the native engine loads it and resumes Ness at level 1 / 30 HP. Actual story saves are hash-checked and remain unchanged.
