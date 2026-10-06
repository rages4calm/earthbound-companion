# Selected shop transaction audit, frozen native dev16v9

The final selected corpus passes 83 transactions: 74 Redux and 9 Original controls.
These are actual packed shop text entries with production text/menu/number/
character-selector children and replayed platform button input, linked against
the unchanged frozen production native library. The fixture establishes party,
bags, source guard flags and cash before entry. It does not claim natural NPC
reachability, every shop branch, physical controller operation, audible output,
or full-game conversion. No owner saves, ROMs or asset packs were changed.

## Confirmed and fixed defect

Active pinned Redux `shops/ShopSys.ccs` BulkBuy reserves each ordinary inventory
slot with unused item 203 before removing the reservations and giving the real
items. The native Key Items adaptation instead classified 203 as a unique pooled
key. Reservations therefore did not fill ordinary bags. A quantity 3 request
with only 2 free slots could charge for 3 while delivering 2.

The valid immutable v8 red corpus contains 25 prepared transactions: 15 capacity
failures across custom 66/67/68, Moonside and ordinary Onett, plus 10 passing
insufficient-cash refund controls. All native exits were 0; 10 cases used real
fresh-process quantity-selector capture/restore. The red input fixtures are
identical to the corresponding final green fixtures. The report retains its
original pilot-labelled metadata rather than being rewritten retrospectively;
these 25 selected input/expected-result assertions are valid, while earlier
private pilot runs with other source assumptions are excluded from this claim.

The correction excludes 203 from the Key Items pool in Redux only. It does not change
the Original classifier or general key categories. The original compiled source
uses 14 ordinary slots per active player and first-empty-slot allocation. The
source `main.ccs` imports ShopSys; the separate `bulk_buy_vanilla.ccs` import is
commented out and is not an enabled feature being claimed.

## Final verification

- Custom 66/67/68, Moonside and ordinary Onett: quantity 3 successful, capacity 2
  abort/refund, insufficient cash abort/refund, two-player distributed capacity,
  four-player 56-slot fill, 99-item overflow abort/refund and all-bags-full guard.
- Actual fresh-process number-selector continuations for capacity/cash/success
  branches; real store-child continuation for Moonside in both profiles.
- Before-Bazooka/Broken-Iron source stock guards, Moonside quantities 0/1/6/14,
  source reversed Yes/No handling, single purchases, cannot-equip confirmation
  and cancellation, immediate equip/decline, half-price sale/cancellation,
  unsellable control, equip-upgrade/sell-old and full selected-bag retry to Paula.
- Actual source cash-register/ping request counts and equipment sound request
  traces with initialized audio. This proves requests, not delivery/audibility.
- A separate post-execution check compares all 56 recorded inventory slots and
  transaction/configuration flags for the same 83 cases. Its 83 assertions overlap
  the 83 executions; they are not additional native transactions.
- Immutable v9 regressions: 177 inventory/classifier/legacy-pool cases per profile,
  16 game-over Egg cases per profile and 72 complete prepared encounters per profile.
  Total 613 selected logical cases including 83 shops. The structural 69 Redux/
  66 Original stock rows and 256 classifier calls per profile are not transaction
  counts, and no coverage percentage is claimed.

The shop harness separates event and diagnostic streams, buffers diagnostic IO,
and suppresses trace verbosity only around its outer host-frame yields. Actual
shop dispatcher requests remain traced. It replaces no native handler and writes
no menu-result, transaction-result or post-entry inventory values. Cold state is
captured/restored through the actual production APIs at real child boundaries.

## Runtime identities

- Player: `56ab9f539d50383b236098c80f8feeaea606d23dd3f2ad26b0326bd138650d73`
- Observer: `290094e1eb7135218fbe5d8403436c058eef672215f34e578ea3f48e5b12bcd6`
- Library: `1d7054446d01284f1bb13025ef12371bf2c0c6cecd979685252795ecafc5c8f1`
- Source snapshot: `_BuildScratch/audit-dev16-v9-source`; root patch identity:
  `ec4c42e6cbe54bc7c8ff6e25bf53afaea97f09bb5536fc5db6f09ab80c84cd60`.
- Pinned Redux revision: `897d00833f4a08a0a92f106abf631629a6a6a041`.

The manifest freezes tools, fixtures, red/green reports and source references.
Use final `*-shop-transactions-dev18-v9-buffered.json` reports; earlier repeated
merged/separated/private pilot logs are not release evidence.

## Reproduction

The QA tools require a locally compiled matching native library/platform objects
and privately prepared matching asset pack. They do not download or distribute a
ROM. Substitute your own existing build/runtime/profile paths and fresh scratch
directories. The frozen fixtures target the exact matching pinned pack; their
numeric entries are not a general API for arbitrary patched-ROM packs.

```powershell
& native-source/.venv/Scripts/python.exe scripts/shop_transaction_qa_dev18.py `
  --build _BuildScratch/audit-dev16-v9-build/companion `
  --native-source native-source --runtime _BuildScratch/audit-dev16-v9-runtime `
  --executed-source _BuildScratch/audit-dev16-v9-source `
  --assets 'PATH_TO_YOUR_REDUX_ASSETS.PAK' `
  --project _BuildScratch/MaternalBound-Redux/Project `
  --cases research/redux-shop-transaction-fixtures-dev18.json `
  --scratch _BuildScratch/shop-reproduction-fresh `
  --output _BuildScratch/shop-reproduction.json --jobs 3
```

Use the Original fixture/pack and `--original` for the 9 control transactions.
Strict mode fails on any semantic/native failure. `--diagnostic` is only for
collecting deliberately failing historical red cases. Regenerate fixtures with
`scripts/shop_transaction_cases_dev18.py` from the matching private pack and exact
dialogue relocation map if repeating the source-selected generation step.

Remaining gaps include naturally reached NPC callers, more stock/recipient
combinations, every serialized shop phase, delivery/barter/service shops,
visual correctness and audible timing, and complete natural playthroughs.
