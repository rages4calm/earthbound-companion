# Feature freeze and maintenance

Effective October 8, 2026, active feature development is wrapped at **v0.5.0-redux-dev.32**. The project is in community testing and focused bug-fix maintenance. The existing experimental designation remains; closeout does not certify complete compatibility.

[Frozen release](https://github.com/rages4calm/earthbound-companion/releases/tag/v0.5.0-redux-dev.32) · [Community testing](docs/COMMUNITY-TESTING.md) · [Developer tools](docs/TESTING.md)

October 9 maintenance update: **dev.33** implements the owner-requested scrolling, widescreen encounter and shader preset work. The original freeze and campaign limits remain; [dev.33 evidence](docs/RELEASE-dev33.md) records the new bounded tests.

## Frozen scope

The scope includes Original EarthBound and the pinned native MaternalBound Redux adaptation, Windows launcher/setup, display and input settings, MSU music, save recovery, native mod profiles and Story Shuffle v4. The [README](README.md#game-features) lists the included features; [randomizer rules](RANDOMIZER.md) distinguish v4 from preserved legacy recipes.

Dev.32 keeps the dev.31 native player and setup helpers. This documentation closeout does not rebuild or replace the game, launcher, packs, release ZIP or installed saves. Baseline ZIP: `EarthBound-Companion-Redux-Tester-v0.5.0-redux-dev.32.zip`; SHA256: `c78d87e7d2c52afa26e1766668bcb6886978825937289c2d0745d69e053d8264`.

Reproducible defects in this scope can receive fixes. New gameplay modes, engine migration, netplay, HD replacement artwork and new general-purpose utilities require an explicitly reopened feature scope. [Toolkit research](research/game-porting-toolkit-reference.md) is a future reference, not a remaining-work commitment.

## What the evidence supports

| Area | Evidence and limit |
|---|---|
| Redux campaign | The owner completed the story through Giygas and credits, reporting defects subsequently addressed. Final testing used equipment/stat boosts. This is real playthrough evidence, not an unboosted or independently automated full-campaign certification. |
| Redux features | No whole normal-play feature is currently confirmed absent in the status records. Exact equivalence of every upstream patch and complete developer/debug-menu parity remain unverified. The target is pinned active source, not the official v1.1 BPS release. |
| Focused regressions | Native menus, equipment, Tools, PSI, story/presentation scenarios, credits/photos and recovery have bounded checks. Reports retain their tested binary/pack identities. Prepared scenes do not establish every natural quest route. |
| Story Shuffle v4 | Four reviewed Original/Redux pack identities each pass 1,000 seeds, 62 combinations and corruption controls. Native consumers, opening/cold restores and selected prepared encounters are covered. A full randomized campaign and every new lineup terrain/render combination remain unverified. |
| Display, input and audio | Automated presentation and soundtrack boundary checks exist. Broader physical hardware/controller behavior, complete listening and every story/music transition remain unverified. |
| Unavailable features | Native Open mode, Ancient Cave, Keysanity and earthbound.app seed compatibility are not included. Arbitrary IPS/BPS game-code patches need their own native adaptations. |
| Distribution terms | Recorded native-foundation licensing and combined GPL distribution questions remain unresolved. Feature freeze does not change that status; see [LEGAL.md](LEGAL.md). |

Details: [Redux status](MATERNALBOUND-NATIVE.md), [dev.31](docs/RELEASE-dev31.md), [dev.32](docs/RELEASE-dev32.md), and [validation records](validation/). Exhaustive coverage is documented uncertainty, not a mandatory queue keeping active development open.

## How maintenance works

1. Collect a report with release, edition/seed, location, smallest reproduction steps and expected/actual behavior. Use the [bug form](https://github.com/rages4calm/earthbound-companion/issues/new?template=bug-report.yml).
2. Reproduce in an isolated session or copied checkpoint. Preserve owner progress and record the exact build, pack, seed and settings.
3. Investigate the reported subsystem. Use an existing focused fixture or add a small regression that detects the actual defect. Do not automatically start a whole-project source audit, agent review or full campaign.
4. Fix the cause and run the affected checks. Broaden only if evidence shows a shared risk. Preserve legacy seed semantics and save compatibility, or document an explicit migration requirement.
5. Publish the fix with exact coverage and uncertainty. New binaries still need appropriate package/setup/recovery checks; this documentation-only closeout does not replace them.

The owner and volunteers do not need another full playthrough. Short reports during ordinary play are useful. Reports are handled when brought to the project; no automatic issue monitor or scheduled audit has been enabled.

## Historical audits

Earlier scripts, source comparisons, release notes and failed diagnostic evidence remain available for specific reproductions. They are historical tools and records, not instructions to rerun all suites or finish every theoretical comparison. A broad audit requires an explicit new request with a bounded scope.
