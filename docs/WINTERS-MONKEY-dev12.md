# Winters Bubble Monkey fix — dev.12

## Cause

The female monkey uses movement event 284. It waits for Jeff to **leave** a small rectangle centered at (432, 4264), then queues the departure dialogue. That assumes the entity first loads as Jeff exits the cave inside that rectangle. The native 512 × 256 view can load her at (432, 4304) while Jeff is still approaching Brick Road from outside the rectangle. Departure can therefore run before the rope puzzle.

An isolated comparison executable, built from the same source with only the departure guard and legacy repair disabled, reproduces this at (200, 4264) in both Original EarthBound and Redux: Monkey leaves while rope flag 311 remains off. This comparison includes a prepared position/story state; it does not reproduce the owner's whole travel route.

The shared spawn path now matches the female monkey's event/appearance-flag pair and keeps that event dormant until rope flag 311 is set. No game data is replaced. The converted Redux script still performs the actual Bubble Gum animation, lowers the rope, and removes Monkey during his normal later departure.

A second issue prevented the gum action after a cold F6 load: the battle-action table was bound lazily through enemy spawn data. Item targeting could return before executing anything. The native boot path now binds those asset pointers before any saved menu or overworld action resumes. This also covers overworld PSI reading the same table.

## Existing saves

The repair runs at an ordinary overworld render boundary. It requires Jeff as the sole party member, Bubble Gum acquisition, the original monkey-join and Tessie-crossing flags, an unfinished rope puzzle, an unset Jeff-joins flag, and Monkey's presence flag 22 off. It sets Monkey's presence flag, creates his real native party entity and enables his follower movement. It leaves the puzzle unfinished and does not alter player inventory, levels, money, location or unrelated story flags.

Saves after the rope/departure milestone do not restore Monkey. New games and cases missing acquisition/crossing or using another party are excluded. Phone saves and format-16 quick saves keep their existing content identity. Back up saves before changing builds.

## Verification

[Prepared native progression checks](../validation/winters-monkey-dev12.json) cover 12 cases per edition/build: before-cave gating, rope proximity, ordinary menu/gum use, rope lowering, climbing, exit waiting, intended departure, departure reload, legacy recovery, and four excluded recovery states. The excluded fixtures test the repair predicate; they are not playable story checkpoints.

An independent copy of the reported cave save also completes the real Redux Keys → Pak of bubble gum → Use sequence and climbs the lowered rope. The owner's install is recovered before the puzzle, leaving it for the player to finish. Captured player files remain private.

[Encounter/audio regressions](../validation/native-reliability-dev12.json) also pass. Collision checks retain the dev.11 guard and scripted/ladder handling. These are bounded fixtures and copied-save replays, not a full story or randomized playthrough.

## Sources

- [MaternalBound Redux's pinned cave and departure scripts](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/data/data_43.ccs)
- [Herringway's original movement event 284](https://github.com/Herringway/ebsrc/blob/main/asm/data/events/scripts/284.asm)
- Native adaptations in `patches/native-companion.patch`: `map_loader.c`, `overworld.c`, `game_main.c`; prepared fixture entry in `port/unix/main.c`.
- Reproducible checker: `scripts/winters_monkey_qa.py`. Credits and foundation details: [CREDITS.md](../CREDITS.md), [UPSTREAM.md](../UPSTREAM.md).
