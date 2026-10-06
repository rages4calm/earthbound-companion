# Escargo complete request and courier audit

The final strict corpus passes 72 selected source-parent sequences on the
immutable dev17-v4 runtime: 36 with Original packed data and 36 with the final
Redux pack. Eighteen fresh-process continuations are included in those 72
sequences. Sixty-eight sequences run natural courier arrival, transaction and
departure; four run the source's natural route-exhaustion failure and refund.
These are selected semantic tests, not a complete playthrough or a claim that
every delivery route works. No production change was required by this corpus.

The matching native library is
`b0cae8b3cce2c5a480b47cff9e7d6d96685ca123bb94031c23a035889ec0e3c0`.
The player is
`970db06806793b2cbbad643c0a460b8f84bb6fa980ba49b6d09d1ca3ea88644d`;
the observer is
`54553cfca96f6eab08842bb88decc37d59ab8cb4ede0bdf876dac19de9bd2f4a`.
The manifest carries the verified executable identities; numeric tests link
the unchanged production library and copied platform objects, with only a
private entry-point driver added. The observer executable is identified but
is not separately executed by this corpus.

The Redux pack is
`3ed273eaedad5131a13dc07b6916377130857929854886b139b30a723482f8b9`.
The Original pack is
`01af4f4b590d9e83937b772399ee60a9181e2384e13c1567c94dfc92101b5549`.
Original controls execute Original packed scripts while retaining the native
project's intentional shared key-pool QoL. They are not an untouched SNES
playthrough. Both ordinary slots and the shared pool are asserted before entry.

## What the fixtures actually run

The pinned Redux source is commit
`897d00833f4a08a0a92f106abf631629a6a6a041`. Source NPC 13 is an always-visible
payphone object, with movement 8 and text entry C6803D. Its real packed placement
is (7800,1520). A source-adjacent leader position (7800,1528) and contact flag 201
are prepared before production world initialization. The actual QuickCheckTalk
caller starts at QCT_TEXT and resolves the loaded phone normally. Initial bags,
pool, storage, party and cash are prepared through native APIs before entry.

The phone's actual menus request delivery or pickup. Successful-route fixtures
use platform RIGHT/UP input through the real packed door at (7920,1512), type 2,
destination-data offset 1856. The source door destination is (1600,1136); normal
door finalization places the leader at (1608,1136). The runner stops input when
the actual door child appears. It does not teleport the player, create the
courier, select a courier event handler, force pathfinding, advance its script,
write menu state, or set a completion signal.

Production pending-delivery rearming, timer, event 499, pathfinding, interaction
queue, visit script, native child menus, movement wait and courier departure
then run through the actual dispatcher. Source event 499 assigns NPC 1311 and
ultimately signals C46E46 after the departure sequence. The runner advances
text using platform button pulses and reads the native state. Normal success
must finish with no courier entity, no pending interaction or suppression,
closed windows, brightness 15, no active fade, actionscript_state 0 and the
overworld root. Complete bags, pool, storage, queues, source flags and wallet
changes are checked separately.

Failure controls stay in the room after the same real phone request. Natural
route attempts exhaust, and source PROCESS_INTERACTION type 10 executes
C64515/C6451A. Queued delivery items return to storage, pickup bags remain
unchanged, and only the $1 phone charge remains. This is an intended source
failure path, not a discovered native defect.

## Selected branches and cold boundaries

| Scope | Checked behavior |
| --- | --- |
| Delivery capacity | Requests 1, 2, 3 with 0, 1, 2, 14 free ordinary slots; partial delivery returns undelivered items and charges $18 once if at least one is delivered. |
| Payment and refusal | Insufficient cash after the $1 phone charge; declined delivery bill with item-return confirmation; declined pickup bill. |
| Pickup | One or three items; inventory cancellation; final-confirmation rejection restores the queued item before retry/cancellation; 35 stored items fills the last storage slot. |
| Party selection | Delivery skips the full first PC and gives to the second; pickup uses the real character selector to choose the second PC. |
| Key pool | Full-bag Redux Banana selection and storage; Original packed-script pooled Banana control; Sound Stone storage rejection preserves its pooled ownership. |
| Natural failure | Delivery and pickup route exhaustion, source failure interaction and cleanup, without courier or completion injection. |
| Cold continuation | Post-phone overworld root, visit bill menu setup, inventory menu setup, and source movement-wait/departure boundary; production capture and fresh-process restore. |

Cold runs keep only the driver's input-plan progress and observation stage in
a separate private file. Native state is restored only by the production
capture/load API. Sound118 request counts are checked for successful
transactions and absent for refusal/failure. They prove requests, not audible
queue delivery.

The source refund loop calls GIVE_AND_RETURN_LOCATION, which inserts an item
into the first free ordinary slot. Returning the first item from [87,90,93]
therefore produces [90,93,87], with no item loss. An earlier diagnostic fixture
expected the original order and failed. The corrected final expectation is
backed by C64155 and the original GIVE_ITEM_TO_SPECIFIC_CHARACTER assembly,
which scans from slot0 for an empty byte. Other earlier fixture diagnostics
incorrectly expected native Original Banana/Sound Stone to remain in ordinary
slots. Final controls explicitly preserve the project's intended key-pool
classification. Those diagnostics are retained, not called native bugs.

## Reproduction and limits

The public scripts are `scripts/escargo_courier_cases_dev22.py` and
`scripts/escargo_courier_qa_dev22.py`; frozen metadata records their workspace
`tools/` identities. The cases generator takes `--native-source`,
`--relocations`, `--output`, and optional `--original`. The runner takes
`--build`, `--native-source`, `--executed-source`, `--runtime`, `--assets`,
`--project`, `--cases`, `--scratch`, `--output`, and optional `--original`.
Use a fresh private scratch directory. The default runner fails on any
postcondition or native exit failure; `--diagnostic` retains an unsuccessful
fixture report without a success exit requirement.

Final reports are `original-escargo-courier-dev22-v4-final-r2.json` and
`redux-escargo-courier-dev22-v4-final-r2.json`. Their manifest records every
tool/fixture/report dependency, executed source identities and exact selected
counts. No ROM, pack contents, dialogue dump or owner save is included.

Untested here: every world region and path, delayed arrival while another
story/battle event is busy, endgame/free-service branches, all initial contact
and phone refusal guards, every storage-capacity or equipped/transforming-item
combination, screenshots, audible sound, physical-controller latency and
natural story reachability from a new game. The fixed delivery-index1 timer
fields in the read-only courier snapshots are not asserted as pickup-index2
timer evidence. This proof supplements the earlier Monkey/service/selector
manifests; it does not rewrite their historical coverage limits.
