# Inventory and encounter lifecycle audit: dev17 evidence

Execution uses unchanged immutable production libraries and private drivers with
copied platform objects. Owner ROMs, packs, phone saves and F6 saves are untouched.
This supplements the frozen 144-address callback ledger and KO lifecycle bundle;
it does not establish complete conversion or a complete playthrough.

## Confirmed inventory defect and correction

Fresh Egg92 is an ordinary edible item. Chick168 and Chicken169 use the source
key-item category but also have the TRANSFORM flag. Both supplied item tables
have exactly those two transforming key-category records. Original assembly's
give-item consumer stores them in character inventory and starts their timers.
The native Key Items feature previously diverted them to unique pool storage,
collapsing duplicates and bypassing the timer consumer. This is a native feature
interaction, not an upstream Redux change.

The correction excludes transforming records from quest-item classification.
Legacy phone and F6 recovery moves only these records into free slots in active
player inventories. Full bags retain the existing pool items for later recovery;
no regular item is overwritten. Recovery waits during menus and battles. Phone
file-selection finalization starts regular timers; idle-root recovery starts
timers after F6 restoration or after inventory space becomes available.

The v6 diagnostic corpus fails all177 selected inventory cases per pack. The v7
and final v8 corpora each pass177/177 per pack: all256 byte-ID classifications
(254 packed records and two invalid IDs), duplicate give/take/find/count behavior,
real phone/F6 restoration, one/four active players,0/1/2/14 free slots per bag,
full-bag retry and6000 neutral leader callbacks. Quantity uses the actual CC1A10
dispatcher with packed operands; it is an API check with no claimed story call
site. Shop mapping covers all69 Redux and66 Original packed records; it does not
certify shop menus, purchases, sales or every associated script.

A solo bag with one free slot holds one recovered Chicken and preserves the
second Chicken in the pool when still full. The test expects this bounded safe
overflow behavior rather than forcing both items into the full bag.

## Actual game-over choices and timer controls

The prepared one-player fixture uses normal party migration/update constructors,
actual give Egg and a private phone save, then deliberate unconscious/zero-HP
state before GAME_OVER GO_ENTER. Text Yes resumes at respawn with the source's
NoContinue flag and result0. Text No plus its confirmation returns-1 to reboot;
the fixture follows that result with real file-menu setup/selection/Continue.
The complete intro/reboot parent is not executed in this fixture.

The Original counter clears while its timer slots remain valid. Its original
leader guard therefore retains the Egg on these same-process paths, matching
the known source bug. Redux deliberately removes that guard. Joined-party v6
Redux fails16/16 cases because the resulting Chick is pooled; v7 and v8 pass16/16.
Original source controls pass16/16 at each recorded version. No timer slots,
counter or countdowns are set to produce the oracle.

## Final complete encounter regression

The frozen full-encounter driver passes72/72 per pack on v7 and final v8. Prepared
four-player level99/HP9999/stats255 fixtures enter real scripted battles in groups
1,48,448,450,453,462,471, with eight seeds, incoming suppression controls and missing
Clumsy rescue-flag controls. Actual platform A replay advances real swirl,
constructors, AI, menus, attacks, KO/final actions, rewards and map return.

The final144 encounters contain125 victories,16 source special teleports and
three legitimate party defeats. They execute282 turns,893 menu choices,597 action
callback entries and177 KO continuations. Carbon Dog's transformation preserves
Diamond Dog's new form before the second form is actually fought. Reward checks
use actual packed KO victim money/EXP, survivor eligibility and source failure
branches; exit checks cover meters, flags, suppression, map restoration and
ordinary battle invulnerability. Logs contain no warning/fatal/error/stall
diagnostics in this final corpus.

These prepared encounters do not certify natural story reachability, every
battle branch, physical controller input, pixel/audio presentation or an entire
playthrough. The seven selected groups are not an all484-group semantic proof.

## Provenance

Reports retain their executed v6/v7/v8 player, observer, library and private
driver hashes. Observer hashes are provenance only: the private semantic driver
links the matching player library. Whole-file current review hashes are labelled
as review references; they are not asserted to match an older executed library.
The separate execution-provenance document records available frozen source
identities, including v6 inventory7d6126 and the corresponding final v8 files.
No prior frozen report or callback ledger was overwritten.

The complete filename/hash inventory is in
`inventory-lifecycle-dev17-final-manifest.json`.
