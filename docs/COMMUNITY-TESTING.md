# Community testing

Features are frozen at **v0.5.0-redux-dev.32**. Help is welcome with bugs encountered during ordinary play. Testing one short section is useful; another complete campaign is not required.

[Download](https://github.com/rages4calm/earthbound-companion/releases/tag/v0.5.0-redux-dev.32) · [Report a bug](https://github.com/rages4calm/earthbound-companion/issues/new?template=bug-report.yml) · [Coverage limits](../MAINTENANCE.md#what-the-evidence-supports)

You can contact the project owner on Discord as **`chrono.trigger`**. Use GitHub Issues for bug reports that need tracking.

## Useful short checks

Pick something you already want to play:

- **Story:** blocked quests, missing NPCs, wrong rewards or unexpected character/stat behavior.
- **Menus/equipment:** selected item, character and any clipped/overlapping text or incorrect preview.
- **Graphics/transitions:** location, door/teleport/battle/effect and whether corruption clears by itself or remains after moving/loading.
- **Audio:** location/event, whether MSU is enabled and any missing, overlapping or incorrect music.
- **Controller/display:** controller model, resolution/aspect/filter and exact input or display problem.
- **Story Shuffle:** seed, recipe version, edition and enabled options. Describe unreachable required supplies, unexpectedly unchanged enabled options or problematic new encounters.

Keep playing your own session. Use Companion's backup tools before experimenting with restore/settings, and keep phone saves as well as quick saves. Do not delete progress, rebuild packs or edit saves to make a report.

## What to include

1. Launcher release and Original/Redux/story/randomizer mode.
2. Exact location/menu and what you did immediately before the problem.
3. Expected behavior and what actually happened.
4. Whether it happens every time, sometimes or only once; note a fresh start, phone save or quick-save load.
5. Relevant display/audio/controller settings; seed and recipe version for randomized sessions.

Intermittent issues are worth reporting even without an on-demand reproduction. Follow the issue form's attachment rules: do not upload ROMs, generated packs, soundtrack tracks, saves/states, gameplay screenshots or credentials. A written description and relevant redacted log lines are sufficient. Keep useful checkpoints locally so reproduction can be discussed without putting game data in a public issue.

The active story/seed session's `game.log` can help. Paste only relevant lines, remove personal paths/private information, and check the text before posting. Reports do not need full asset dumps or system logs.

## Scope and limits

Open-world randomization, Ancient Cave, Keysanity and earthbound.app recipe compatibility are unsupported. New features and engine changes are deferred; supported story/settings/setup/save/randomizer defects remain eligible for focused fixes.

The owner finished one Redux campaign through credits, with boosts for final testing. Full randomized progression, every optional branch/effect combination, broad physical hardware and complete listening remain unverified. [Maintenance status](../MAINTENANCE.md) distinguishes completed testing from remaining coverage.
