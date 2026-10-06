# ATM, hospital and status-service audit

The final strict corpus passes 268 selected packed source-parent transactions
on the unchanged dev17-v4 native library: 135 Redux cases and 133 Original
controls. Fifty-five fresh-process continuations are included in those counts
(28 Redux, 27 Original). No production correction was required by this corpus.
The separate source review passes 144 checks on original local bytecode and
active pinned Redux scripts. Source-review checks and transaction cases are
different kinds of evidence and must not be added as a feature count.

The pinned Redux revision is
`897d00833f4a08a0a92f106abf631629a6a6a041`. The exact executed native library is
`b0cae8b3cce2c5a480b47cff9e7d6d96685ca123bb94031c23a035889ec0e3c0`;
the player is
`970db06806793b2cbbad643c0a460b8f84bb6fa980ba49b6d09d1ca3ea88644d`,
and the observer is
`54553cfca96f6eab08842bb88decc37d59ab8cb4ede0bdf876dac19de9bd2f4a`.
The private driver links the unchanged library and copied platform objects.
It adds fixture/input/observation code, replaces no production handler, and
does not edit shared builds. Observer identity is recorded; these transactions
are not separately executed through the observer executable.

The final Redux pack is
`3ed273eaedad5131a13dc07b6916377130857929854886b139b30a723482f8b9`.
The Original pack is
`01af4f4b590d9e83937b772399ee60a9181e2384e13c1567c94dfc92101b5549`.
Original controls execute Original packed scripts with the native project's
intentional shared key-pool QoL retained. They are not untouched SNES gameplay.

## Source contracts and checked behavior

| Service | Selected actual transactions |
| --- | --- |
| ATM | ATM-card guard, withdrawal/deposit, actual five-digit values 12,345 and 23,456, zero/cancel, empty bank/full wallet/full bank, insufficient funds followed by retry, exact wallet/account limits. |
| Redux ATM caps | A withdrawal exceeding wallet capacity is rejected, refunded in full, then retried. A cold capture occurs after rollback and before the second number prompt. A deposit exceeding account capacity changes neither balance. |
| Doctor | All nine source town wrappers/prices and all four curable primary illnesses: nausea, poison, sunstroke, cold. Each PC is selected through actual menus. HP/PP targets and other affliction slots remain unchanged. |
| Doctor refusal | Healthy, unconscious, diamond, numb, mushroom and possessed conditions; insufficient/exact cash, declined/canceled bill, canceled character selection. Homesickness is preserved. |
| Nurse | All nine town wrappers/prices, chosen unconscious member, restored HP/PP targets, nonzero awakened HP. Only primary, secondary and homesickness status slots are cleared. Other status groups and other PCs remain unchanged. |
| Nurse refusal | Healthy selected character, canceled selection/bill, declined bill, insufficient/exact cash, no active patient, unconscious benched character excluded by the source active-party scan. |
| Healer | All eight town wrappers and each source price for diamond, numb and possession treatment. Matching status only is cleared; source treatment/town flags are cleared afterward. |
| Healer refusal/retry | Declined service/bill, canceled treatment/character, insufficient/exact cash, wrong selected member followed by real menu retry, wrong condition in a single-member prepared party. |
| Mushroom sale | Two active mushrooms sold for $50 each, and declined-sale controls, in Onett and Moonside. |
| Moonside | Actual inverted Yes/No choices for doctor, nurse and healer billing; flag 659 cleanup. Mushroom-sale choices use their own source branches. |

Fixtures prepare party membership, cash, bank balance, item prerequisites and
affliction/HP/PP state before the packed entry. The entry runs the normal text
dispatcher and real child menus. Selection plans are translated into actual
platform D-pad/A/B pulses. Numeric plans also use actual button pulses at all
five digit positions; they never write numeric values, cursor state, menu
results, text registers or post-entry gameplay state. All regular inventory
slots, key pool, storage and delivery queues are asserted unchanged.

The ATM card-check caller is original C680A6 / MSG_GLOBAL_CASHDISPENSER.
C680C2 / MSG_GLOBAL_ATM_RECEIVE_ITEM is a different item-use caller. The first
Original pilot used the latter alias without its item-use register prerequisite;
it correctly returned without opening the ATM. That was a fixture error, not
a native ATM defect. Final controls verify the proper source alias from the
original label registry and run the matching caller in both profiles.

Doctor C90FEC treats only the source's illness branches. Nurse C9128D applies
the exact script encodings (character 0, groups 1/2/6, value 1) and calls the
100% HP/PP recovery commands. Script groups are 1-based; recorded native
affliction arrays are 0-based. The source review parses those original commands
locally and verifies every selected wrapper's original identity, cost and
callee. It also checks the active imports of the two Redux money-cap helpers.
This is source evidence, not original SNES CPU execution.

## Cold boundaries and fixture corrections

Production capture/load runs at real five-digit number input, bill-menu setup
and overworld character-selection menu setup. Native state is restored in a
fresh process; only the private input-plan indexes survive in a separate file.
The corrected character-menu condition follows the production party selector:
single-character window 51, or targeting prompt 40 plus party count minus one.
The first cold pilot only watched the two-person window 41 and missed actual
four-person window 43. Those incomplete captures remain private diagnostics.

The Redux refund retry capture also requires a newly entered number child,
not simply an incremented private input-plan index. The final case confirms
the first actual numeric POP is 2,000, reads refunded balances of wallet 99,000
and bank 3,000 at capture, restores them unchanged, enters 999 with buttons,
and finishes with wallet 99,999 and bank 2,001. It issues one successful
withdrawal sound request. An earlier capture fired before the first entry
completed; its omitted numeric POP was a harness error, not broken rollback.

Hospital HP/PP assertions cover target recovery and awakened nonzero HP at
the prepared text-parent boundary. Current rolling values are recorded, but
their final visual settling and the outer NPC caller's hide/cleanup stage are
not claimed here. The isolated fixture clears battle state, including normal
HP roller speed; its current HP can remain at the source wake value 1 until
outer cleanup. This does not establish an ordinary-game HP roller defect.
Sound 37, 116 and 118 request counts are checked where specified; request
traces do not prove audible delivery.

## Reproduction and remaining limits

Public scripts are `scripts/status_service_cases_dev23.py`,
`scripts/status_service_qa_dev23.py` and
`scripts/status_service_source_review_dev23.py`. The manifest records their
frozen workspace `tools/` paths. Use the included exact fixture JSONs, or run
the cases generator with `--native-source`, `--relocations`, `--output` and
optional `--original`. The native runner takes `--build`, `--native-source`,
`--executed-source`, `--runtime`, `--assets`, `--project`, `--cases`, `--scratch`,
`--output` and optional `--original`. Use a fresh private scratch directory.
Any native exit or asserted mismatch fails by default; `--diagnostic` preserves
an unsuccessful investigation without treating it as proof. The source review
also requires the owner's `--rom`; no ROM bytes or dialogue payload are public.

Untested: natural approach/contact/departure for every service NPC, every
combination of status/party/order, Saturn/Tenda/hotel/dungeon healing, every
item-use ATM caller, Original ATM overflow behavior, arbitrary numeric cursor
editing, physical controllers, pixels, final rolling-meter settling, audible
sound, and full story progression. Synthetic pre-entry status combinations
are not a reachability claim. This corpus supplements the earlier transaction
audits and does not establish complete conversion or full-game correctness.
