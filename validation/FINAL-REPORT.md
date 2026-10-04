# EarthBound Companion local verification

Completed October 4, 2026. This report records bounded checks of the local private build, not a complete playthrough or every device combination.

## Installed entry points

- `C:\Users\crono\Desktop\Projects\eb\EarthBound Companion\EarthBound Companion.exe`
- `C:\Users\crono\Desktop\EarthBound Companion.lnk`
- Native game: `EarthBound Companion/Game/earthbound.exe`; assets already extracted from the user's USA ROM.

## Passed

- Native x64 C/SDL build with `EB_ENABLE_VERIFY=OFF`, `EB_ENABLE_AUDIO=ON`, runtime asset packs enabled. Self-contained Windows Forms UI published locally.
- Normal companion opening through title, file selection, naming and prologue. Fresh isolated replay reaches Ness at level 1, 30 HP, bedroom position 8120,1106. See `final-gameplay/opening/run.log` and `tools/final_gameplay_qa.py`.
- Earlier interactive-input replays crossed bedroom/upstairs/living-room doors to the exterior at 2656,344. The exploration saves and replay logs remain under `gameplay`, separate from the user's empty initial save folder.
- Restored exterior rendered at 1920×1080, 2560×1440, 3840×2160 and 3440×1440 with SDL's software renderer in isolated dummy-driver tests. PNGs and exact sizes recorded under `final-gameplay`. Earlier normal-window game captures exercise accelerated presentation. The isolated exploration checkpoint was captured without live audio, so these resolution runs do not certify restored soundtrack playback.
- Separate normal startup with the installed pack logs native PCM tracks 121 and 7. See `msu-playback/run.log`. Synthetic audio tests cover one-shot/loop points/resampling/fades/malformed/missing files. `msu-audit.json` records all 164 source MD5, header, length and loop checks.
- Four savestate integrity checks, key-item pool, party join-level scaling, runtime asset error handling, remapping/source overlap/deadzone/hotkey/focus checks: logs and exit results in `tests`.
- Companion bounds/presets including Classic/Custom identification, keyboard mapping, binding serialization, native settings persistence, profile import/rejection and ZIP save backups. Tests use a separate temporary root and do not alter user saves.
- Six launcher pages at 1120×800 and 990×760. Fresh Impeccable reviewer found preset labeling and compact clipping issues; one fix batch and follow-up state captures resolved all three findings. `finish-review.md` and `finish-verdict.md` record scope and ship verdict. Actual raster provenance scan passes.

## Native randomizer update — October 4, 2026

- Shipped independent Companion Story Shuffle v2 with Balanced/Surprise styles, four selectable gift/shop/enemy-stat/drop options, Generate & Play, saved-seed replay/resume, safety/spoiler logs and recipe import/export. Updated starter **Tonight in Onett · v2** is prepared in the actual app library. ALttP was not modified.
- Decoded 61 original script blocks / 61,972 entries with zero unknown opcodes. The derived policy and explicit dynamic Monkey Cave request list protect 78 items, their original sources, and 52 literal scripted-battle enemy records. Whole-pack checks run during generation and immediately before launch. No routing or script mutation is permitted. Audit: `randomizer/progression-audit.json`.
- 1,000 seeds and all 30 valid option/style combinations: deterministic output, exact byte whitelist, protected quest/trade sources, native stat bounds, disabled-option isolation, recipes, original-pack mismatch/tamper refusal, separate save namespaces and preserved saves. Deliberately broken trade foods, scripted battles, other assets and an unsafe legacy pack with a rewritten matching manifest are refused. See `randomizer/tests.txt`.
- The original version 1 starter fails the new progression validator and is blocked. Its files and saves remain intact. `randomizer/legacy-starter.log` records refusal. New version 2 identities prevent overwriting or silently reusing older saves; the UI can regenerate from an older seed's text/options into a new adventure.
- Actual C gift lookup reads all 177 gift records in a generated pack; actual C battle initialization reads all 230 nonzero enemy records. Fresh randomized opening reaches Ness at level 1 / 30 HP and writes a quick save in its seed's folder. Resume produces nonblack 1920×1080 output. Audio-enabled startup logs native PCM tracks 121 and 7 from the shared installed MSU pack. See `randomizer/native-tests.txt`, `native-consumers.log`, `opening.log`, `resume-1080p.log`, `msu-start.log` and `native-1080p.png`.
- `--session-dir` is entered before any save access and rejects a missing directory. Native tests prove normal-story assets/settings/saves/screenshots did not change. F1 settings markers, seed quick saves, SRAM, screenshots and logs use this session directory; the launcher writes an absolute shared soundtrack path.
- Guided save recovery verifies adventure identity, assets, engine version, save checksums and native quick-save header/version/length/CRC, with a current-save backup before restoration and rollback on I/O failure. Tests cover phone-only/full restoration, cross-seed refusal, engine mismatch, damaged ZIP contents and path traversal. A real native-generated checkpoint was deliberately damaged in an isolated fixture, restored byte-for-byte through the same recovery code, then loaded by the native engine: Ness resumes at level 1 / 30 HP. Settings and installed story saves stay unchanged. See `randomizer/native-recovery-tests.txt` and `native-recovery.log`.
- Seven-page launcher extension manually checked through its own HWND. The v2 compact 990×760 captures in `ui-randomizer-v2` show all four options and Generate controls in the first viewport; safety/recovery actions and the complete compatibility note remain reachable below. The old six-page finish review remains historical baseline evidence.
- The v2 ready seed changes 58 gift contents, 90 shop slots, 141 ordinary enemy stat records and 39 enemy drops. Its original story, routes, trade sources and scripted battles remain fixed. Pack SHA256: `72cabd77a165b1f3a1f736e247a11eab3836aa328b74352d3470e9f7f2df5c70`.
- Full earthbound.app seed parity, Ancient Cave, Open mode and Keysanity are **not implemented**. This update does not certify a complete randomized playthrough or ending.

## Material limits

No complete game playthrough, battle/ending regression suite, physical controller hardware session or every display/DPI arrangement is certified. The game remains a community C reimplementation. Original graphics and audio use software PPU/SPC/DSP; SNES main CPU verification/emulation is disabled. HD output scales enhanced original art; no replacement HD texture set is claimed. Full MaternalBound Redux support requires additional native game/data ports and is not bundled as complete.

User's library ROM/archive was not modified. The private native asset pack, donor ROM and soundtrack must remain outside any future public source upload. Source and attribution are retained; the native custom changes are also saved as `research/native-companion.patch`.

## Cleanup

Unused clones, archive downloads, one-time helper scripts and old screenshots are collected in project `_BuildScratch`. Automatic approval review rejected deletion with `blocked by policy`; reversible moves within this project were allowed. No deletion is claimed. Build tools needed by Rebuild.ps1, selected source, validation evidence and final app remain in their working locations.
