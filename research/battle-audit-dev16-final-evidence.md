# Battle callback checkpoint: dev.16

The pinned active action table contains 320 records and 144 distinct callback
addresses. `battle-semantic-coverage-dev16-final.json` maps all 144 addresses to
selected source-backed semantic evidence. This is an address coverage ledger,
not a conversion percentage, full branch coverage, complete battle lifecycle
test, or completed playthrough. Earlier reports retain their actual executed
runtime hashes; they have not been relabeled as the newest game build.

`battle-audit-dev16-final-manifest.json` freezes the new runners and reports by
SHA-256. The final new eight-callback tests execute the immutable dev16 v5 player
library and identify the observer only as provenance. No owner saves, extracted
game payloads or ROMs are published by these reports.

| New scope | Redux cases | Original cases | Executed build |
| --- | ---: | ---: | --- |
| Spy, Mirror, Neutralize All, Clumsy Robot escape | 10,688 | 10,624 | dev16 v1 |
| Stat down, CUTGUTS, Magnet Omega | 21,864 | 21,864 | dev16 v4 |
| Physical attack plus poison or diamondization | 7,936 | 7,936 | dev16 v4 |
| Bomb and Super Bomb after the guard correction | 1,920 | 1,920 | dev16 v5 |
| Equipment swaps, all packed equipment IDs and four characters | 10,880 | 10,880 | dev16 v5 |
| HP-sucker alias and Rainbow transformation | 6,656 | 6,656 | dev16 v5 |
| Prayer command and time-freeze attack | 2,304 | 2,304 | dev16 v5 |

Each green row consists of prepared complete callbacks with real native
calculation/text/application children. Assertions are narrower than the game's
overall behavior. Full report limits are authoritative. For example, prayer
tests check all ten weighted selections, actual child order and selected effects;
Rockin/Flash child mutations are outside that runner. Time-freeze tests check
source masks, cyclic random selection, zero-to-four executed hits, wasted dead
targets and entry/exit rolling state; damage and intermediate rolling are not
certified there. Rainbow checks the real group471 constructor and full art setup,
then Pink Cloud27 transforming to83 against all78 source battler bytes. Species174
has no initial count-positive group caller and remains outside that fixture.

The confirmed production correction changes Bomb's right-neighbor test from
`next_member <= 5` to `next_member >= 1 && next_member <= 4`. The old game performed
an extra damage-child push and variance roll against a trailing empty party
slot. The immutable v4 corpus preserves 768 failing cases per mode out of1,920;
the corresponding v5 corpus passes all1,920 per mode. This is a shared consumer
fix across Original and Redux. No HP failure or crash was reproduced by this
particular corpus.

Independent machine proof is specifically bounded. The untouched clean and
pinned `BOMB_COMMON` machine body passes72 party-adjacency cases each while its
variance, damage and target-name children are deliberately stubbed in temporary
emulator memory. That proves neighbor control flow, not original-machine damage
or full battle behavior. Separate actual stat-down helpers execute4,136 inputs
per mode with stack/direct-page canaries. Ordinary current1..511 inputs match
the reviewed native arithmetic. Synthetic zero/high-word differences remain
identified separately and are not claimed as reachable story failures. A
private CUTGUTS pilot also found a text-number extension difference only for
prepared guts below its own base floor; natural reachability is unestablished.

For reproducibility, each runner accepts `--build`, `--native-source`, `--assets`,
`--runtime`, `--scratch`, `--output`, and `--project`; choose a new private scratch
directory on every run. Add `--original` for the Original pack. Stat/drain can
accept `--machine-report`; Bomb requires it. The frozen machine runners require
the exact owner-provided clean or pinned ROM and a separate dev-only oracle.
Use `--diagnostic` only to preserve known baseline red results; default runners
fail on semantic mismatches. Do not build the immutable CMake snapshots: their
caches still point at the original build directory.

The next material gap is complete battle turns and KO/final-action lifecycle,
including scripted bosses, HP rollers, victory/rewards and overworld cleanup.
Callback entry fixtures do not establish that whole lifecycle or full progression.
