# Native battle and item audit, dev15

The cold table regressions below are confirmed native conversion defects. They
are separate from ordinary ROM-hack behavior and from the remaining untested
story and cinematic paths. No ROM, extracted asset bytes, dialogue or player
saves are included in these reports.

## Cold native table dependencies

`tools/cold_battle_dependency_qa.py` links the unchanged production game library
and copied platform objects into a private driver. It runs real startup and
observes that `enemy_config_table` is already available while `npc_ai_table` and
`consolation_item_table` are still null. Each test prepares a bounded native
state with those transient pointers either null, matching that fresh process,
or bound to the actual asset tables as a normal `BTL_BEGIN` would do.

| Native consumer | Exact checked behavior | Pre-fix cold result |
| --- | --- | --- |
| `add_char_to_party` → `update_npc_party_lineup` → `get_npc_max_hp` | Actual NPC addition obtains max HP from its configured enemy record | Five NPCs receive HP 0 instead of the packed HP |
| `mode_step_battle_ko`, pc 11 | Prepared dying Teddy continuation replaces its NPC ID, enemy configuration ID, HP and consciousness | Replacement keeps the dying bear's enemy ID when the NPC table is absent |
| `mode_step_battle`, `BTL_PREP` | Real item-drop and consolation selection for both source table entries over 32 seeds | Consolation loot is skipped when the table is absent |
| `choose_target` → `find_targettable_npc` | Real enemy Bash chooses the configured NPC interception before its ordinary player targeting loop | Eligible NPC interception is skipped; attack instead targets a player |

Original assembly reads these ROM tables directly at the decision points. The
native correction lazily obtains the same immutable table at each consumer.
It changes no asset-pack identity, save layout or gameplay formula.

The 340-case corpus contains 170 cold and 170 normally bound control cases per
pack. For both original EarthBound and the pinned Redux pack:

- Frozen dev14 v6: all 170 bound controls pass; 136 of 170 cold cases mismatch.
- Frozen dev15 v3: all 340 cases pass. Both packs together pass 680 cases.

The original and Redux reports retain their separate pack hashes and immutable
runtime/library hashes. The v6 evidence is retained as diagnostic red evidence,
not relabeled as testing a corrected build. The default tool fails on any cold
or bound mismatch. `--diagnostic` permits expected cold baseline failures while
still requiring every bound control to pass.

The KO case enters the actual pc 11 continuation with the post-text replacement
state. It does not test preceding inventory destruction or text. PREP cases
stop at the next native child/phase; they do not prove a whole encounter or
reward flow. A cold checkpoint already past PREP does not rerun that battle's
drop selection. These fixtures prepare states in a private process; they do not
load or rewrite an owner's serialized save. Root-level saved-game restore
coverage is a separate audit.

## Additional action semantics

`tools/battle_action_catalog_qa_dev15.py` extends the release-frozen native action
driver with real host-frame processing, source-derived assertions and explicit
entry-stage reporting. It binds the normal battle-entry tables as a deliberate
fixture prerequisite; it therefore does not test the cold dependency defects
above.

## Summon-only enemies and their battle art

Two additional native defects are confirmed by original assembly and real
native group construction, sprite allocation/layout and callback execution.
The full enemy-group record contains entries with an initial count of zero.
Those species are eligible to be summoned later and need their battle art
preloaded even though no initial battler is instantiated for them.

The pre-fix native summon handler searched only the initial battler IDs. It
therefore rejected eligible zero-count species. The native sprite loader also
explicitly skipped zero-count records, leaving the summoned species' art
unavailable. Original `CALL_FOR_HELP_COMMON` scans the full group and original
`SETUP_BATTLE_ENEMY_SPRITES` loads every entry until the `FF` terminator.

The fixes restore those source decisions: the actual summon consumer reads the
full immutable group with bounded asset access; the sprite loader retains
zero-count records. Initial battler counts remain determined by the record's
count. Both pack catalogs fit the existing four-art-slot allocation: the
original pack has at most four entries per group and Redux at most three.

The frozen v3 red corpus executes 896 cases per pack. It preserves successful
initial-species controls but denies 540 source-expected zero-count spawns. All
896 cases also omit required full-group art. The frozen v4 green corpus adds
cases with transient battle-entry pointers null and passes all 1,792 cases per
pack, 3,584 total. Reports retain exact original/Redux pack and runtime/library
hashes. The earlier red run is reproduced with `--entry-bindings bound` and
`--diagnostic`; corrected runs are strict by default.

The driver uses actual `BS_ENTER`, ordinary native art setup/layout and both
summon callbacks with actual packed group/parameter records. Redux enemy 64's
real AI includes call-for-help action 62 with parameters 129 and 134, so the
checked zero-count behavior has ordinary gameplay callers. Both callbacks are
also exercised directly in prepared contexts where every AI does not assign
both callbacks. The assertions certify one summon in comfortably fitting
selected groups, not dead-slot replacement, every packed row arrangement,
all AI turns or rendered pixel appearance.

These two callbacks bring the union with the separately identified earlier
semantic reports to 76 of 144 active callbacks; 68 remain unevaluated by those
drivers. The v3 action corpus is not relabeled as having executed on v4. The
680 cold NPC/KO/consolation/targeting cases also pass on frozen v4, with their
own reports separate from the retained v3 results.

Coverage includes Belch's Fly Honey transformation, Poo's return and Starstorm,
Pokey transitions, prayer continuations, item healing and stat changes, enemy
status actions, Diamondize reward clearing, possession ghost handling, Brain
Stone concentration protection, poison cure, Shield Killer, PP reduction and
combat stat items. The exact executed counts and remaining active callbacks
are recorded in `redux-battle-action-coverage-dev15.json`.

The frozen dev15 v3 player library passes all 6,085 additional semantic cases.
These exercise 49 active callbacks, bringing the union with the separately
identified frozen dev14 cases to 74 of 144 active callbacks. Seventy remain
unevaluated by these two semantic drivers. Dispatch metadata alone is excluded
from those semantic counts.

The unused packed Teleport Box callback is assigned to no ordinary item in the
pinned pack. Its API is exercised with real item parameter records across
strength, boss and sector restrictions. This is API parity coverage, not proof
that an ordinary story item uses that callback.

Prayers one through seven enter the reviewed post-cinematic pc 5 continuation.
The full first-prayer/Mr Saturn cinematic entry currently waits for a script
signal in a prepared fixture. That behavior needs caller/actor prerequisites
and production-path investigation; it is not yet a confirmed game defect.
Pokey transitions and prayers eight/nine start at native action entry and run
their remaining text/fade/load/swirl children. State assertions alone do not
certify rendered images, music, every cutscene or a complete ending.

An early prayer oracle incorrectly expected Giygas's HP to decrease. Exact
`CALC_DAMAGE` source excludes the phase-six Giygas ID from ordinary HP loss.
The corrected assertion checks the actual varied damage input and phase/group
transition while HP stays unchanged. An early status oracle likewise used an
incorrect numeric nausea constant; `include/constants/battle.asm` establishes
the correct value. Both were fixture/oracle corrections, not native fixes.
The final assertions also preserve original `SET_PP` maximum clamping for
deliberate over-max PP boundary fixtures and the enabled Redux Defense Spray
instructions: a 1/8 increment with a 175% base-defense cap. Those corrections
likewise changed the expected results, not production code.

The earlier frozen dev14 semantic and original-machine variance reports keep
their own build identities. Their case counts are not asserted to have run on
dev15. Full-turn selection, cost, AI and story trigger ordering, physical input,
render/audio correctness, and a full playthrough remain distinct proof
obligations.

## Reproduction

Use a compiled player build, its exact matching `player.exe`/`observer.exe` and
`SDL2.dll` snapshot, an owner-local asset pack, and a fresh scratch directory.
The tool checks the production executable hash against the runtime snapshot
before privately linking; it never rebuilds the shared library or modifies
production source. Reproduction flags are embedded in each JSON report.

For the cold tool, use `--original` with an original pack; omit it for Redux.
Use `--diagnostic` only when intentionally reproducing a pre-fix build. Source
file hashes describe the review inputs at execution; the immutable library and
executable hashes identify the actual tested code, particularly when reviewing
an older library after source corrections have been applied.
