# Stair entrances and landings — dev.13

The reported blue stairway could stop the party at its lower or upper landing. A copy of the owner's F6 save reproduces the lower-entry block in dev.12. Dev.13 climbs from the same position and descends onto the lower landing with steady input, without repositioning the save.

## Shared correction

The original assembly returns zero when stair entry is allowed. The native ascending variants had the condition reversed, accepting Down while rejecting the expected Up, horizontal and diagonal approaches. Dev.13 explicitly accepts the two cardinal components and the diagonal toward each flight. The descending variants also use these directional masks, so moving away does not start an entry. This is a documented PC control adaptation; it is not a claim of exact assembly behavior for every direction.

A landing's trigger can also be just behind the newly requested leading edge. The shared movement path now checks the current six-point collision footprint for a collision-marked, real type-4 stair record. It only starts the normal stair alignment/callback sequence when moving toward that flight. Failed searches restore the door lookup state and do not modify collision-detection globals. Ordinary walls, ladders, ropes and scripted movement do not use this fallback.

The dev.11 swept collision guard remains enabled for free walking, including sprint and Skip Sandwich. Stair speeds, alignment targets and deferred enter/leave callbacks are retained. There is no teleport, wall-walk, story skip or asset-pack change.

## Verification

- [Catalog replay evidence](../validation/stairs-dev13.json): all 72 type-4 endpoints in each edition, 18 per variant. Player and observer replay them independently: 288 endpoint checks. Ordinary horizontal inputs enter the stairs, a copied checkpoint resumes on a cold process, and the real stair exit returns the party to free walking. Each replay stops at its first actual exit rather than continuing into a nearby door or second flight. The evidence records how many cold checkpoints were already in stair walking style.
- The reported three-member Redux save climbs and descends in both builds; their full serialized checkpoints match after the existing two restored PSI pointers are normalized for process addresses. Player data, story flags, party stats/items and the phone save are preserved. The source capture is unchanged and remains private.
- [Direction/collision/save regressions](../validation/stairs-regressions-dev13.json): 32 direction combinations, three invalid inputs and three excluded transition states per edition/build; 12,288 prepared corner/cliff paths, 144 free-speed/surface cases and scripted bypass; save round-trip, cold-load perturbation, crash safety and asset-pointer binding.
- [Encounter/audio regressions](../validation/native-reliability-dev13.json) pass in both editions/builds. [Winters progression regression](../validation/winters-regression-dev13.json) passes in the Redux player, including Bubble Gum, rope climbing, departure and repair exclusions.

Catalog fixtures use one healthy party member with NPC/enemy spawning disabled. They do not cover every story appearance condition, physical controller hardware, escalators or a complete story/randomized playthrough. The copied owner save covers the reported actual party. The runtime fix is shared by Original, Redux and supported Story Shuffle packs; the map catalog replay here uses the unshuffled Original/Redux packs.

## Install and saves

State format 16, content hashes and save namespaces are unchanged. Existing phone/F6 saves and settings can be copied forward. For the installed playtest, use the existing desktop EarthBound Companion shortcut and Resume quick save; the reported stair checkpoint is retained.

## Source references

- [Herringway: stair direction test](https://github.com/Herringway/ebsrc/blob/main/asm/overworld/door/get_stairs_movement_direction.asm)
- [Herringway: stair alignment and movement](https://github.com/Herringway/ebsrc/blob/main/asm/overworld/door/handle_stairs_movement.asm)
- [Herringway: stair enter callback](https://github.com/Herringway/ebsrc/blob/main/asm/overworld/door/handle_stairs_enter.asm) and [leave callback](https://github.com/Herringway/ebsrc/blob/main/asm/overworld/door/handle_stairs_leave.asm)
- Native patch: `src/game/door.c`, `door.h`, `position_buffer.c`; explicit fixture/checkpoint options in `port/unix/main.c`. Reproducible runner: `scripts/stairs_qa.py`. [Credits](../CREDITS.md) and [source lineage](../UPSTREAM.md).
