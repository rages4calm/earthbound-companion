# Changelog

## 0.5.0-redux-dev.2 - audio, door timing and gameplay checks

- Fixed a native MSU transition bug: a previous SPC Sound Stone recording could continue underneath its PCM replacement. The native music command now stops that sequence while retaining SPC effects.
- Added verified checks for all eight recordings, SPC effects under MSU, missing-track fallback, all 164 real PCM loop/end boundaries and fast, slow, quarter-volume and full-volume fades.
- Added doubled exit/entrance transition timers as Companion QoL, following upstream's optional `fast_doors.ccs` hook (disabled in the pinned upstream import list). Twenty-one native exit/palette/brightness cases pass for Redux and original EarthBound, with the original profile retaining its timing.
- Added normal-button gameplay from naming through house doors/stairs, Mom's dialogue, the clothes-change warp and outdoor movement, for both Redux story and a generated seed. Replays observe the wandering NPC and cold-restore between checkpoints. Added an actual 1080p capture.
- Native development checks and original-profile regressions pass with the updated engine. Full story/randomized playthroughs, soundtrack listening and every story audio transition remain unverified.

## 0.5.0-redux-dev.1 - private development tester

- Added guided owner-ROM setup for a separate MaternalBound Redux profile. A frozen helper downloads the pinned source, repairs compiler compatibility, compiles and converts locally; testers need neither Python nor Git.
- Converted the complete reachable dialogue graph, maps, shops, enemies, SPC tracks, expanded PSI, enemy and party artwork, names, cast, credits and photo data for the pinned active-source target.
- Added native typed commands and movement helpers, Redux controls/stamina, all eleven inventory-free Jeff Tools, expanded equipment/resistance previews and native combat/item/stat fixes.
- Fixed scene completion, invisible controllers, mosaic fade, object allocation, teleport cleanup, bicycle leader/revival behavior, door bounds, interrupted stairs and cast scrolling.
- Ported font-aware menu highlights and the delivery letterbox hook; delivery music starts after its fourteen-frame opening.
- Added quick-save format 16 with ending continuation and pointer reconstruction. Original, Redux and randomized adventures keep separate save namespaces.
- Added Story Shuffle v3 with separate original/Redux progression policies, exact content hashes and independent whole-pack checks. Each edition passes 1,000 seeds and all 30 option combinations; unknown packs remain locked.
- Fixed fresh MSU downloads so output handles close before checksum verification and installation. Setup can repair invalid or interrupted tracks without discarding verified files.
- Added actual launcher/gameplay captures, source/compiler patches, reproducible package tooling and metadata validation reports. The clean ZIP test uses a headered owner ROM, no Python on PATH, a real soundtrack repair, native story/randomized openings and save-isolation checks.
- Accounted for all 105 dialogue-excluded spans in a source-pinned ledger. Classification is not complete assembly equivalence or full gameplay verification.
- **Full MaternalBound compatibility remains incomplete.** Full story/randomized playthroughs, all combat combinations, listening/transition coverage, live photo collection and developer/debug parity remain unverified. The older v0.4 package remains the original-story preview.

## 0.4.0 — private preview

- Added a ROM-free first-run setup flow with clean-USA-ROM validation.
- Bundled a standalone extractor so testers do not need Python.
- Added optional installation and repair of the complete 164-track MSU pack with per-file integrity checks.
- Added the Story Shuffle v2 native randomizer, deterministic recipes, isolated saves, progression guards and recovery tools.
- Added 1080p through 4K and ultrawide presets, expanded field of view, Scale2x, color grading, depth effect and scanlines.
- Added controller remapping, hotplug, analog movement, sprint, quick dialogue and configurable gameplay conveniences.
- Added crash-safe quick-save banks, automatic session backups and guided save restoration.
- Added ROM-derived-content gates to release packaging and the checked-in repository audit.

See [validation/TESTER-PACKAGE-REPORT.md](validation/TESTER-PACKAGE-REPORT.md) for the exact archive hash and bounded validation results.
