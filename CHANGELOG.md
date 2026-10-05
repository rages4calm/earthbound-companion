# Changelog

## 0.5.0-redux-dev.6 - rest stamina hooks

- Connect hotel, full-recovery and hot-spring script entries to native stamina reset. Preserve their existing healing bodies, converted pack, quick-save format 16 and seed identities. Rest loop continuations do not reset stamina repeatedly.
- Reproduce the missing reset in dev.5. Twelve prepared four-member cases pass in dev.6; 24 player/observer checkpoints match and the production VM now passes 112 checks, including six rest-entry/continuation cases. Original-profile regressions pass.
- Record the exact three active recovery writes and their native adaptation. Ordinary testing of every resting location, the remaining all-module audit and complete story/randomized playthroughs remain unfinished. Jev exploration stays stopped.

## 0.5.0-redux-dev.5 - present reward fix

- Create the deferred Redux gift window before writing item/cash registers, preserving silent empty Talk/Check behavior. Reproduce two lost present rewards on dev.4, then verify source-defined rewards, opened flags, window cleanup and no duplicate gifts on dev.5. A prepared $123 cash gift also passes.
- Rebuild player/observer engines and the setup helper together; keep the corrected pack, state format 16 and seed identities unchanged. Previously opened presents are not automatically compensated.
- Record 15 additional literal-hook reviews, exact retained movement commands, shack/cave exploration and process-pointer-aware observer comparisons. Complete story, randomized story and all-module conversion parity remain unfinished.
- Stop Jev exploration at the owner’s request; subsequent gift regressions use deterministic ordinary inputs with no TypeSafe requests.

## 0.5.0-redux-dev.4 - script width fix and active bugfix review

- Correct Redux `CC 1D 15` variable-argument handling to use the low word stored by the upstream assembly fix. The real dispatcher reproduces eight failures before the correction; all 25 operand/party-position cases now pass, raising the VM suite to 106 checks.
- Record all 36 active bugfix imports against the exact source pin, with native bindings, execution differences, targeted coverage and remaining branch tests. This is source review, not full compatibility certification.
- Rebuild the player engine, QA engine and frozen setup helper together. Fresh movement/combat/original-profile checks, a clean upstream patch check, and 20 natural-combat observer parity checkpoints pass.
- Extend bounded Jev navigation through shop menus, City Hall, the guard and the mayor’s ordinary Shack Key award. Add expected door-destination checks and alternative NPC approaches. Full story and randomized playthroughs remain unverified.
- Keep dev.3’s corrected pack and quick-save format 16, preserving content and seed identities. Existing dev.2 story imports remain restricted to the exact checked names-only pack change.

## 0.5.0-redux-dev.3 - PSI names, combat UI and save-restore fixes

- Read the PSI-name table from CoilSnake's patched assembly pointer. The former fixed address held unrelated script bytes, producing names such as `103`. Validate the pointer and names during conversion.
- Recreate the PSI list in front of the pause menu and repaint older format-16 PSI-menu checkpoints after loading. Lifeup heals Ness and spends 5 PP through ordinary inputs.
- Add a checked dev.2 → dev.3 story-save importer for the exact names-only content change. Require empty destination saves, preserve the previous installation and reject other content pairs; randomizer seeds remain on their original content.
- Apply Redux's delayed Talk/Check window creation: empty space no longer leaves an invisible window behind later battle text, and the removed quick-check sound stays removed.
- Suspend cutscene letterbox updates during battles. Repair the distinctive bad masks in older Redux quick saves without restarting the fight or changing progression.
- Reload the stat-growth asset cache when resuming between level-up messages; fix an attacker-name stack-buffer overread with six-character Redux names.
- Fix managed Redux story backup identity and use one production launch path for story and seed sessions, covered by launcher regression checks.
- Add optional structured QA observations and a bounded Jev runner. Actual copied Starman combat, level-ups and post-fight dialogue return to roaming; normal NPC conversation and empty Talk/Check → natural Onett combat/victory also pass. Player and observer state match at 66 combined checkpoints. Full story and randomized playthroughs remain unverified.

## 0.5.0-redux-dev.2 - audio, door timing and gameplay checks

- Reviewed README, credits, setup, HD/widescreen, randomizer descriptions and source/license status against the current build. Recorded the retained native foundation and upstream license review; private visibility is explicitly a precaution, not permission to distribute.
- Refreshed player documentation in the tester ZIP and added the source/license notes. Package documentation links now point to shipped documents or the repository, so source-only reports and screenshots do not become broken local paths.
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
