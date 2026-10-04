# MaternalBound Redux native port

Companion is adapting MaternalBound Redux into its native x64 C/SDL engine, alongside HD and ultrawide output, MSU music, PC controls, save recovery and Story Shuffle. Gameplay runs as compiled C; patched SNES CPU code is explicitly translated into native behavior.

**Full Redux support is incomplete. The downloadable v0.4 preview and installed original-profile game do not contain Redux. The development pack is isolated, requires explicit test flags and is excluded from this repository and releases.**

## Exact upstream target

This checkpoint targets the active upstream source at `897d00833f4a08a0a92f106abf631629a6a6a041`, compiled locally with CoilSnake into a verified 6 MiB ROM. It is not the official v1.1 release. The v1.1 BPS was separately checksum-verified and tested during initial extraction research; supporting that release requires a separate conversion map and validation record.

The bridge records 191 reachable CCS files, 1,018 import edges, 190 compiler modules, 7,840 labels and source checksums. An exact ROM/source mismatch stops conversion. This is a deterministic porting input, not a claim that every upstream assembly feature has been implemented.

## Implemented development coverage

| Area | Current native work and evidence |
|---|---|
| Dialogue | 7,367 converted spans, 568,504 bytes and 12,835 relocated fields; zero failed spans, unresolved targets or ambiguous original aliases. Seven pinned malformed source jump tables are repaired explicitly and reported. |
| Script extensions | Typed menu, title, fade, money, party, item, timeout and enemy-AI commands. Sixteen stable native adapters replace the routine calls encountered in converted dialogue. 62 native VM checks and four actual converted titles pass. |
| World | Converted maps, palettes, collision, NPC placements, doors, events, movement data, shops, items, PSI configuration, encounter groups and music-zone selection data. Original native entry points map to rewritten scripts. |
| Graphics | 483 sprite groups / 4,432 frames, all five fonts, map artwork and battle backgrounds/enemy art. Redux walking/run tables and run sprites are bound to the native animation callbacks. Upstream alternate walking tables share some graphics; cycling the tables does not create missing art. |
| Controls | Redux pause layout, quick check, HP/PP toggle, town map, Keys/Jeff's Tools menus, stamina and exhaustion. Production animation/stamina checks pass. |
| Enemy AI | Converted scripts for 190 enemies; the production selector and VM pass 48,640 turns across four HP/PP/status conditions. Action bounds, persistent cursors and retained money rewards are checked. These are selector checks, not full battle playthroughs. |
| Names and saves | Six-letter party names, ten-letter favorite food and 49 expanded default names. Original character/save sizes stay fixed; tagged spare save bytes hold the extra letters. Extended names survive phone saves, old untagged save migration and quick-save reloads. |
| Runtime replays | Six-letter keyboard entry and opening rendering pass. Six menu cases pass at 1920×1080, including Keys, Help and the Use prompt. These checks do not prove every item's use action or later progression. |
| Original profile | Native input/MSU, save-state roundtrip/perturbation/recovery, key-items and join-level regression checks pass with the updated engine. |

Metadata evidence: [dialogue conversion](research/maternalbound-dialogue-report.json), [pack conversion](research/maternalbound-native-pack-report.json), [native checks](validation/native-redux-results.json), [opening](validation/native-redux-opening.json), [menus](validation/native-redux-menus.json), [original regression](validation/native-original-regression.json).

## Remaining before support is enabled

- Convert and implement the Mother 2 title presentation and custom title movements.
- Import expanded PSI effects and party battle sprites, and validate actual battles.
- Adapt specialized flyover, coffee/tea, ending and staff text formats.
- Import custom SPC music/sample banks and verify SPC/MSU transitions.
- Audit remaining assembly-only QoL changes and bug fixes against native functions.
- Validate free movement, doors, NPCs, item use, shops and cutscenes through real gameplay, including a start-to-ending playthrough.
- Finish reproducible player-ROM setup, content identity and isolated saves for this exact profile.
- Audit rewritten scripts/items for progression, generate the Redux Story Shuffle policy and test randomized progression before unlocking seed generation.

Existing original-story randomizer checks do not establish safety for the rewritten Redux story. Unknown and unaudited content stays locked. Arbitrary BPS/IPS patches cannot execute automatically in the native engine.

## Reproducing development conversion

Build the pinned Redux source locally using the player-provided ROM and CoilSnake first. Then use the native source Python environment with `ebtools`, PyYAML and Pillow:

```powershell
python scripts/maternalbound_dialogue.py --bridge research/maternalbound-native-bridge.json --project "PATH\TO\Project" --compiled-rom "PATH\TO\Mother 2.sfc" --native-source native-source --output-dir "LOCAL\redux-dialogue"
python scripts/test_maternalbound_dialogue.py
python scripts/build_maternalbound_pack.py --base-assets "LOCAL\original-assets.pak" --native-source native-source --bridge research/maternalbound-native-bridge.json --converted-directory "LOCAL\redux-dialogue" --compiled-rom "PATH\TO\Mother 2.sfc" --project "PATH\TO\Project" --output "LOCAL\redux-assets.pak"
```

The pack builder reads compiled local data, validates structure/pointers and writes a separate development pack. Reports list explicit repairs and deferred work. `Verify-MaternalBound-Dev.ps1`, `redux_gameplay_qa.py` and `redux_menu_qa.py` run isolated native checks; passing them does not authorize replacing a player's game or saves. No ROM, extracted asset pack, soundtrack or save is published.

## Credit

[ShadowOne333 and the MaternalBound Redux contributors](https://github.com/ShadowOne333/MaternalBound-Redux) created the hack. Its adaptation follows GPLv3 with upstream credit and published corresponding source. The native engine builds on Herringway, BrianPugh and seanstaggsQU. See [CREDITS.md](CREDITS.md) for sources, individual extensions, libraries and tools.
