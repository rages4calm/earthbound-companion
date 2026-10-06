# Complete selected Give, Drop, and equipment parents

Both profiles pass 71 complete pause-menu parents on the immutable dev17-v4 player library: 142 executions, including 30 fresh-process continuations and 30 explicit warm/cold comparisons. A separate source review passes 77 checks. The continuation and source-check counts overlap the execution corpus; they are not additional game features or a conversion percentage.

The fixtures enter the actual pause menu and use production character selectors, item menus, packed text, inventory routines, and platform D-pad/A/B input. They prepare party, inventory, afflictions, and initial gear before entry. They never replace a production handler, selected result, transaction effect, or completion signal. Checks cover complete bags, equipment locations, five effective stats, weapon miss rate, five stored resistance fields, target HP/PP, seven affliction groups, wallet, key pool, storage, delivery queue, and closure of the full window list. Cold snapshots are taken before real transaction/menu children and restored in a fresh process.

Selected cases cover all ten source Give message branches, equipped-item transfers and bag compaction, self rearrangement, full recipient refusal, recipient cancellation, the last slot of a full bag, Drop before or on equipment, a zero-price Poo weapon refusal, all four equipment categories for all four PCs, None, incompatible menu-item exclusion, item cancellation, Poo's alternate modifiers, and Goods → Use equipment behavior. Original Goods → Use supplies an informational message. Active Redux redirects it to equip or unequip, including its wrong-carrier refusal. The latter is verified through the actual packed helper rather than a direct equip call.

Two Original-source oddities are explicitly preserved in this parity proof. They remain candidates for a separate intentional QoL correction:

- Self-Give with a full fourteen-item bag appends the equipped item at position 14 but assigns equipment position 13. The original `FIND_EMPTY_INVENTORY_SLOT` bound stops at index 13, and `SWAP_ITEM_INTO_EQUIPMENT` stores that result. The previously stored weapon stats remain unchanged. Both profiles reproduce this exact source order.
- Giving equipped Body or Arms gear to another PC compacts the bag before recalculation but adjusts later equipment positions afterward. With the selected four-piece loadout, stored defense becomes 55 instead of a fresh recalculation's 60 after giving Body; giving Arms produces 65 instead of 70. Both profiles reproduce the source's intermediate-position reads. The report records both the source-faithful stored fields and the independently calculated final-gear fields.

These cases pass the original contract and do not establish that the odd behaviors are desirable. Eight executions, including their cold counterparts across both profiles, carry an explicit `sourceOddity` field. No production change is included in this checkpoint.

Redux's expanded equipment hook also closes the gameplay menu, while its reopen call is commented in the pinned source. Its complete parent therefore exits one B press earlier than Original. This difference is represented in the actual input plans; it is not hidden as a missing choice or reported as a conversion defect.

Pilot qualifications: initial Give fixtures mistakenly supplied menu userdata to the character selector, which takes a raw right-move count; the final plans use the correct actual controls. Initial equipment plans included an extra final B for Redux. Initial Original Goods → Use expectations incorrectly assumed Redux's equipment shortcut existed in Original; bounded original bytecode confirms it does not. An expanded pilot assumed final derived stats after Give, then source review established the intermediate-position oddity above. These pilot assumptions are not native failures. Final strict reports enforce exact consumed input plans, captured gear, complete return, and warm/cold outcomes.

The source review compares selected Original ROM numerical item rows and parsed control opcodes with the packed data, and checks pinned Redux rows, active imports, and ordered assembly/control-flow tokens. It does not execute an original SNES CPU or prove every branch. No ROM, dialogue, or graphics payload is published. Observer identity is recorded, but observer is not independently executed. This corpus does not prove natural NPC/controller/story reachability, every equipment ID or stat boundary, visible glyph/pixel correctness, delivered audio, or a complete playthrough.

## Immutable identities

- Player: `970db06806793b2cbbad643c0a460b8f84bb6fa980ba49b6d09d1ca3ea88644d`
- Observer: `54553cfca96f6eab08842bb88decc37d59ab8cb4ede0bdf876dac19de9bd2f4a`
- Production library: `b0cae8b3cce2c5a480b47cff9e7d6d96685ca123bb94031c23a035889ec0e3c0`
- Original pack: `01af4f4b590d9e83937b772399ee60a9181e2384e13c1567c94dfc92101b5549`
- Redux pack: `3ed273eaedad5131a13dc07b6916377130857929854886b139b30a723482f8b9`
- Pinned Redux source: `897d00833f4a08a0a92f106abf631629a6a6a041`

## Reproduction

The published scripts use the `scripts/` directory; local proof metadata retains the original `tools/` paths. Use the matching checkpoint's native build/source/runtime, your locally extracted assets, and a new scratch directory. The runner links a private driver against the unchanged production library and fails on any native exit, transaction/state mismatch, missing input, or cold difference. `--diagnostic` is only for investigating failures.

```powershell
python scripts/goods_equipment_cases_dev25.py --assets MyReduxGame/assets.pak --output redux-fixtures.json
python scripts/goods_equipment_qa_dev25.py --build build/companion --native-source native-source --executed-source native-source --assets MyReduxGame/assets.pak --runtime MyReduxGame --project LocalPinnedRedux/Project --cases redux-fixtures.json --scratch Scratch/goods-equipment-redux --output redux-report.json --jobs 3
```

For Original, pass its extracted pack and add `--original` to both commands. Source review additionally requires your own clean USA ROM and the pinned source checkout. It publishes hashes, numerical metadata, and bounded review outcomes only. A different runtime or pack is a new result and must retain its actual identity.
