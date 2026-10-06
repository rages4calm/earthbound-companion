# Native inventory selector and barter checkpoint

The native script inventory menu now offers valid owned Key Pool items alongside
ordinary bag items. A stable virtual location (`0x100 + item ID`) supports the
source's repeated read, register save/restore and eventual item consumption.
The location survives pool compaction and existing phone/F6 saves without a new
serialized field. Ordinary bag slots and the older one-shot Use sentinel retain
their previous meanings.

This closes three confirmed failures in selected native transactions:

- Monkey N's real King banana gift entered the pool, but Monkey I's source
  inventory selector could not offer it, blocking flag 459.
- Fourteen ordinary bag items plus a pooled item exposed a source interior-row
  mismatch. Actual D-pad pulses selected an ordinary slot instead of the hidden
  pooled choice. The shared menu layout now uses the source's interior height.
- The source party-has-items helper (`C5E431`) inspected only ordinary slot 1.
  Tracy storage and retail selling therefore rejected pool-only inventories.
  Only that helper's literal `(0,1)` read now sees an eligible pooled fallback;
  unrelated slot 1 reads remain ordinary bag reads.

The exact Original helper aliases and Redux relocation bounds identify that
preflight. Its three static source callers test truthiness. The original
`GET_CHARACTER_ITEM` and multiply helper executed from the unchanged owner ROM
in 420 prepared CPU cases, with complete byte-equal source identification and
stack/direct-page canaries. This machine proof covers the item reader; it does
not execute the entire original text interpreter. Pool-aware fallback is an
explicit native PC QoL adaptation.

On frozen native **dev17-v3**, final verification records:

| Evidence | Original | Redux |
|---|---:|---:|
| Selected complete Monkey parent sequences | 101 passed | 101 passed |
| Fresh-process Monkey menu continuations | 16, included above | 16, included above |
| Selected helper, Tracy and retail sequences | 28 passed | 28 passed |
| Fresh-process helper/service continuations | 12, included above | 12, included above |
| Bounded production API / CC / save observations | 16,479 passed | 16,475 passed |

These are 258 selected source-entry sequences, including 56 cold continuations.
The 32,954 API observations are a separate, overlapping corpus; they are not
additional complete transactions or a completion percentage. Selected checks
include correct/wrong items, decline/cancel, ordinary duplicates, unique pooled
ownership, already-completed monkeys, full bags, two active PCs, actual gift then
trade, pool-only sale/storage, storage-full retention and the source's Sound
Stone storage rejection. Money, all bag slots, pool/storage/queue state, flags,
actual menu choices and sound requests are checked where specified by each
fixture. Sound requests do not establish audible delivery.

Redux repeats used the final pack with SHA-256
`3ed273eaedad5131a13dc07b6916377130857929854886b139b30a723482f8b9`.
The prior Redux pack proof remains separate. A complete asset comparison found
107 changed assets; the dialogue, item, store and timed-delivery transaction
inputs remain byte-identical. Original pack proof remains on
`4e01c943711d32c41e85cb858d9058169e7c8b1739fc7dc0a211e441f9631b9b`.
Every runtime report retains actual player/observer/library/source identities.

The red evidence is preserved. The old full-bag Monkey corpus's planner refused
an unreachable option; the separate four-case actual-button red corpus entered
the real menu and exited normally with the wrong item retained/flag unchanged.
The old pool-only retail pilot's input plan encountered a different menu after
the failed preflight; its extra confirmations do not prove an automatic purchase
bug. The independently confirmed defect is the source guard rejecting selectable
pooled ownership. The corrected source helper and complete real transactions
pass both profiles.

Reproduction uses an explicit matching runtime/build/source snapshot, local
owner-created assets, fresh scratch folders and the exported runners:

```powershell
python scripts/barter_delivery_qa_dev20.py --help
python scripts/service_transaction_qa_dev21.py --help
python scripts/key_pool_selection_qa_dev21.py --help
python scripts/snes_inventory_slot_oracle_dev20.py --help
```

Use the saved `*-fixtures-*.json` for each profile; pass `--original` only for the
Original pack. Runners are strict by default. `--diagnostic` is for explicitly
preserved baseline failures. `barter-selector-dev20-v1-red-manifest.json` fixes
the original full-bag red runner dependencies. The final manifest binds tools,
fixtures, reports and evidence to their exact file hashes.

Coverage remains bounded. `inventory-selector-source-catalog-dev21.json` is a
static inventory of 55 source call sites, including debug candidates; it is not
execution proof. Escargo phone queue selection has earlier selected evidence,
but the complete courier arrival, exit, refund and full-bag delivery parent has
not been qualified here. A prepared visit without the real courier stalls at
the source's movement wait; that is a fixture prerequisite gap, not a confirmed
game defect. Remaining selected inventory consumers include other barter/gift
parents, delivery services and battle item-discard flows. These tests establish
neither natural map/NPC reachability nor every branch, pixels, controller
hardware, a full playthrough or 100% conversion.
