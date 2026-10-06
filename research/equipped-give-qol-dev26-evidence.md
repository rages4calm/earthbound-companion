# Private equipped-Give QoL correction

This is an intentional correction of two Original-source behaviors, separate from Redux conversion parity. The unchanged dev25 proof preserves those behaviors with 142 complete parents and 77 independent source-review checks. It remains frozen.

The private candidate changes only `inventory.c::swap_item_into_equipment`. After self-Give, a bounded scan of the actual post-append ordinary bag determines the equipped item's one-based location, including position 14 in a full bag. After giving equipped gear to another PC, the matching category's existing `CHANGE_EQUIPPED_*` call runs after the remaining equipment locations compact. Its production recalculation therefore reads the correct final gear. The global Original `FIND_EMPTY_INVENTORY_SLOT` helper remains unchanged for its other callers.

On the unchanged player, a six-case corpus per profile has four expected failures against these desired postconditions and two passing controls. Every native stage completes with exit 0. The failures reproduce self-Give's position 13 instead of 14 and the stale Body/Arms defense values, including a cold Arms transaction. They are deliberate red checks of an intentional QoL change, not newly claimed Original/Redux parity defects.

The corrected private archive passes 183 complete pause-menu parents per profile: 366 total, including 58 fresh-process continuations and 58 explicit warm/cold comparisons. The expanded matrix uses all four PCs, Poo's alternate equipment modifiers, all four categories, giver bag sizes 4/7/14, self and other recipients, and independently calculated final equipment item identities, stats, miss rate, and stored resistance fields. The previous complete Give/Drop/Equip/Use cancellation, refusal, full recipient, and zero-price controls remain present. Additional warm/cold cases retain nonempty key-pool, storage, and delivery queue sentinels. Complete inventory arrays and wallet are checked, so ordinary duplicate items and quantities are preserved.

The inputs enter the actual pause menu, replay real platform buttons, and execute production packed text, selectors, children, transaction functions, capture, and fresh-process restore. Party/inventory/initial gear are prepared before entry; no production handler, selected result, post-entry effect, or completion signal is injected. Private compilation replaces one copied archive member, `inventory.c.obj`. The other 83 of 84 archive members are byte-identical to the held dev17-v4 library. Platform objects remain unchanged, and compilation uses the held source/build include snapshots.

The old source-faithful cases and desired final postconditions are kept distinct in fixture metadata. Passing this candidate does not establish every item ID, arbitrary malformed bag/save state, stat boundary, natural map/controller/story reachability, delivered pixels/audio, observer execution, or a full playthrough. Original-source control-flow corroboration is bounded source/bytecode review, not original SNES CPU execution.

No shared source, build, owner save, pack, or current release is modified. Parent integration and checks against the resulting complete frozen production build are still required before describing the fix as shipped.

## Identities

- Base player: `970db06806793b2cbbad643c0a460b8f84bb6fa980ba49b6d09d1ca3ea88644d`
- Base observer: `54553cfca96f6eab08842bb88decc37d59ab8cb4ede0bdf876dac19de9bd2f4a`
- Base library: `b0cae8b3cce2c5a480b47cff9e7d6d96685ca123bb94031c23a035889ec0e3c0`
- Original pack: `01af4f4b590d9e83937b772399ee60a9181e2384e13c1567c94dfc92101b5549`
- Redux pack: `3ed273eaedad5131a13dc07b6916377130857929854886b139b30a723482f8b9`
- Baseline inventory source: `54dc872979eb93e273bddf603cf7bfbd6530a6161cef48d9038d6bb08e5df93d`
- Corrected private inventory source: `0ce9700c84c3b14f2df4d3a67ba12fda550da26a8880ba04261e8aebb934856c`
- Corrected private archive: `a4e8a6f8b986bf70b42a334501890c9e4cc4e53df07d5e405826c0027065d92c`
- Pinned Redux: `897d00833f4a08a0a92f106abf631629a6a6a041`

## Reproduction

Published tools live under `scripts/`; recorded local identities retain `tools/`. Use the matching checkpoint's source/build/runtime, your extracted pack, and fresh scratch directories.

```powershell
python scripts/prepare_equipped_give_qol_dev26.py --source native-source/src/game/inventory.c --output-dir Scratch/gear-candidate
python scripts/equipped_give_cases_dev26.py --assets MyReduxGame/assets.pak --output redux-fixtures.json
python scripts/equipped_give_qa_dev26.py --private-inventory-source Scratch/gear-candidate/src/game/inventory.c --build build/companion --native-source native-source --executed-source native-source --assets MyReduxGame/assets.pak --runtime MyReduxGame --project LocalPinnedRedux/Project --cases redux-fixtures.json --scratch Scratch/gear-private-test --output redux-report.json --jobs 3
```

Add `--original` to the case generator and runner for Original. Omit `--private-inventory-source` to test the unchanged library against the desired corrected postconditions; those red checks require `--diagnostic` to preserve the expected failing report. Green runs are strict by default. A new runtime/pack/candidate is a new result and must keep its actual identity.
