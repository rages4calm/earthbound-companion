# Sprint, corner and cliff collision

Dev.11 adds a pure swept collision check to the shared free-walking path. The old routine checked a requested endpoint, selected a different direction when nudging around a corner, and masked out the original blocking flags. It then committed that redirected endpoint without checking the actual segment. Higher movement speeds could amplify the resulting corner escapes; the prepared regression also reproduces an escape with sprint disabled.

The new check samples the accepted segment at intervals of at most one pixel, using the existing directional leading-edge geometry and checking the feet cell. It does not change collision-query globals, corner memory, surface effects or detected doors. It runs after the original directional/NPC checks and before an ordinary position commit. Scripted movement retains its intended collision bypass, and the existing door/ladder handlers retain their intentional transition override. The existing 1.5x/2x sprint and Skip Sandwich speed values are unchanged.

Both original EarthBound and Redux, including their native Story Shuffle packs, use this shared movement routine. Game packs, state format 16 and seed/save identities are unchanged. Existing stranded positions are not automatically relocated.

## Verification

- A prepared cliff/corner regression fails in the old movement implementation, including with sprint disabled. The new player and observer pass 12,288 prepared paths per edition/build: eight directions, all three sprint settings, with/without Skip Sandwich and varied corner patterns/start fractions. These are synthetic collision grids, not visits to every game map.
- 144 prepared unobstructed speed/surface cases per edition/build retain normal, sprint, Skip Sandwich, shallow-water and deep-water displacement. A scripted movement case retains its intentional collision bypass.
- An isolated replay made from a tester's captured pre-crossing position enters a blocked feet tile in the archived dev.10 player. Both corrected builds stop on the accessible approach without blocked entries in the movement history.
- A separate recovery fixture uses a clear position recorded in that party's own movement history. Cold-restored player/observer builds agree on the position, and ordinary southward sprint inputs leave the area. Experience, HP/PP, money, inventory, story flags and the phone save are preserved. The fixture changes positioning/history data and advances ordinary frames; it is specific to this reviewed capture.
- Existing encounter, bicycle-music and SFX regressions pass in both editions/builds. Full playthroughs, every doorway/ladder and every map remain unverified. The shared guard is not a claim that all original collision exploits have been catalogued.

[Collision and recovery evidence](../validation/sprint-collision-dev11.json) · [Shared reliability checks](../validation/native-reliability-dev11.json)
