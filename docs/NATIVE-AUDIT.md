# Native conversion audit — dev.14 checkpoint

For the following checkpoint, see [dev.15 audit](NATIVE-AUDIT-dev15.md).

The audit covers the pinned MaternalBound Redux source `897d00833f4a08a0a92f106abf631629a6a6a041` and the shared native engine. It combines source/data reviews, ordinary-input replay, cold saves, prepared subsystem scenarios and independent execution of selected original SNES routines. **Complete Redux compatibility and a complete story or randomized playthrough remain unverified.** A green fixture is evidence for its stated behavior, not for the whole game.

## Corrections in this checkpoint

- **Hotel wake-up movement:** the Companion swept collision guard introduced in dev.11 rejected every direction when the original scripted arrival placed a footprint sample inside a bed tile. The guard now allows that existing overlap to leave its original cell while rejecting entry into new solid cells. The reported Threek save walks out with normal Down input, without relocation or save repair. Progress, party, inventory and phone save are preserved; player/observer serialized states match after normalizing only process-specific PSI pointers. The old cliff escape remains blocked.
- **Collision coordinates:** the original `CHECK_COLLISION_TILE_PATTERN` wraps its coordinate addition to 16 bits, then uses logical `LSR`. The native helper used signed shifts, preserving the low-six-bit tile lookup but recording incorrect ladder coordinates at wrap boundaries. It now matches the original operation.
- **Redux naming:** the exact active six-row keyboard includes accented letters and added symbols. A separate rendering check caught transient font tiles reaching the text tilemap's VRAM address. The Redux glyph grid now uses a dedicated range, separate from names, cursors and labels. Original's retail keyboard is retained.
- **Redux battle UI:** HP/PP boxes and rolling digits stay on their normal row, damage does not undraw the boxes, and AUTO renders/clears at the upstream Redux position. Portrait state resets at actual shared battle entry, including deliberately prepared stale checkpoints. Original's raised selection, damage blink and AUTO position remain intact.
- **Large damage/healing variance:** both native variance helpers narrowed the original 16-bit scaled product to eight bits. The correction retains the full result for both game editions. Original machine-code execution confirms the wider result; this is a native conversion defect, not an upstream Redux change.
- **Item quantity command:** `CC 1A 10` now counts empty slots when item zero is requested, takes a zero operand's argument from its low 16 bits and respects the original four-position party boundary. Native shared key-item storage remains an explicit adaptation. No active pinned story call uses this command.
- **Gauss Labs End:** the pinned Redux sequence locks input immediately before its final text prompt, making its following reset unreachable. A narrowly identified native adaptation retains the prompt/fade/pause/reset sequence without that self-blocking lock. Other input-lock commands and the Continue paths remain intact. This is a correction to the pinned source behavior, not a claim that the source already did this.

No asset pack, content hash, seed identity or format-16 save layout changes are required.

## Evidence and its bounds

| Area | Evidence | Boundaries |
|---|---|---|
| Native subsystems | [60 required cases](../validation/native-subsystems-dev14.json), both editions/builds, zero silent skips | Prepared subsystem checks; player and observer share game code |
| Rest destinations | [12 destinations, 48 actual warp arrivals and 384 cold movement replays](../validation/hotel-arrivals-dev14.json) | One healthy Ness; NPC/enemy spawning disabled; purchases and story branches excluded |
| Reported hotel save | [Copied-save movement and preservation](../validation/hotel-owner-dev14.json) | The actual reported party; private save files are excluded |
| Stairs and cliffs | [Stair catalogs](../validation/stairs-audit-dev14.json), [captured cliff regression](../validation/cliff-dev14.json) | Catalogs and captured positions, not every story condition or physical controller |
| Winters | [Bubble Gum, rope, climbing, departure and migration exclusions](../validation/winters-dev14.json) | Prepared progression scenarios, not the whole Winters chapter |
| Independent collision reference | [11,088 cases](../validation/snes-collision-oracle-dev14.json); pre-fix probe disagrees in 1,731 | Original 65816 helpers versus isolated actual native helper bodies; no whole-game frame comparison |
| Battle/items | [Six active-module review](../research/redux-battle-item-feature-review.json), [handler/continuation and original-CPU variance checks](../research/redux-battle-action-coverage.json) | Dispatch metadata is not exhaustive action semantics; isolated handlers are not complete battle turns |
| Presentation/audio | [Six active-module review](../research/redux-presentation-feature-review.json), [final-build battle UI replays](../validation/party-ui-dev14.json) and soundtrack checks | Special encounter branches, exact visual parity and complete listening remain open |
| Remaining active hooks | [16-module review](../research/redux-remaining-feature-review.json), [naming input/render/save evidence](../research/redux-naming-runtime-review.json) | Unused destructor opcode and disabled boot debugger are distinguished from active story behavior |
| Record/End flows | [Full Dad/Gauss entry, Continue/End and cold title checks](../research/redux-reset-runtime-review.json) | Prepared caller prerequisites; not a whole chapter or physical-controller test |

Every report retains the actual runtime/source hashes. Some catalog or visual checks use earlier immutable binaries from this checkpoint; those hashes are retained rather than relabeled as the release binary. The final release binary repeats the subsystem suite, reported-save movement, battle UI and Dad/Gauss reset checks. The independent combat comparisons test the same unchanged variance source through the earlier frozen player library. Earlier title/narration smoke evidence retains its own hash.

The earlier [36 active bugfix reviews](../research/redux-active-bugfix-review.json), [control/battle hook review](../research/redux-control-and-battle-hooks-review.json), [general hooks](../research/redux-general-hooks-review.json), [rest hooks](../research/redux-recovery-hooks-review.json) and [excluded-assembly ledger](../validation/native-redux-assembly-ledger.json) remain part of the audit. These scopes overlap; their counts must not be added into a feature-completion percentage. Symbol presence and source classification alone do not prove behavior.

## Reproducing and extending the tests

Developer runners live in `scripts/`: `native_conversion_audit.py`, `hotel_arrival_qa.py`, `stairs_qa.py`, `sprint_collision_qa.py`, `winters_monkey_qa.py`, `redux_naming_qa.py`, `redux_party_ui_qa.py` and the three `audit_redux_*_features.py` reviews. Each takes explicit local inputs and uses fresh `_BuildScratch` sessions. The native `--world-fixture` and `--teleport-fixture` options prepare controlled scenes; story prerequisites must be taken from the pinned scripts rather than guessed. These options are developer tools, not automatic proof of every location.

`snes_collision_oracle.py` additionally requires the owner's clean USA ROM, a local compiler, generated native headers and [mesen-agent](https://github.com/atonamy/mesen-agent). It injects only a test caller into temporary emulator memory, leaving the original tested routine bytes and the disk ROM unchanged. Stack/direct-page canaries, completion/sample counts and Lua error checks are required. The reference emulator is a **development tool**; it is absent from the native player release.

The independent-reference work follows the [Retro Porting Toolkit co-simulation guidance](https://retroportingtoolkit.com/docs/concepts/co-simulation): shared native code agreement cannot serve as an independent oracle. This checkpoint implements selected function comparisons; it does not claim the toolkit's full aligned-frame co-simulation workflow.

## Work still required

The continuing audit must close reachable gameplay branches with source-backed scenarios, extend independent reference comparisons, exercise special encounters and rewards, and run complete story/seed playthroughs. A fixture warp cannot prove the preceding quest, and a compiled patch cannot prove its behavior. Physical controller and display combinations, complete audio listening and full story/music transition coverage also remain incomplete.

The active pinned release has `DEBUG_BUILD = 0`. The unadapted `m_ondestroy` destructor API has zero reachable calls/opcodes in the audited pinned movement graph. These are recorded gaps, not hidden claims that the normal game has been verified completely.

## Continue the installed playtest

Use the existing desktop **EarthBound Companion** shortcut, then **Play → Resume quick save**. With dev.14 installed, Down exits the saved Threek bed position. Existing phone/F6 saves, settings, soundtrack and Redux profile are copied forward without editing the owner's saves. The prior installation remains available as a rollback.

Credits and terms remain separate: [CREDITS.md](../CREDITS.md), [UPSTREAM.md](../UPSTREAM.md), [LEGAL.md](../LEGAL.md).
