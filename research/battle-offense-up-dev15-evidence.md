# Redux Offense Up parity evidence

The native Redux adaptation used base offense for every Offense Up increment.
The pinned Redux instructions use current offense. For a character with base
offense 80, the first buff changes 80 to 90 in both versions. The next buff
changes 90 to 101 in the pinned game but previously changed it to 100 natively.
This is a native adaptation defect, not a defect established in Redux itself.

The enabled `redux/offense_defense_psi_buff.ccs` patch at `C27D34` loads current
offense into the accumulator before `_Find3Over8`. Its instructions double the
value in a 16-bit accumulator and shift four times. Despite the old 37.5%
comment, the actual increment is:

```text
increment = uint16(current_offense * 2) >> 4
next = min(uint16(current_offense + increment), base_offense * 17 >> 3)
```

The correction changes only that Redux increment expression. Original
EarthBound retains its current-offense 1/16 increment, minimum increment one,
and 125% base cap.

`tools/snes_offense_up_oracle.py` executes actual unmodified `C27D28` and its
pinned relocated callees using the development-only reference emulator. A
small temporary caller and prepared battler fields are placed in emulator
memory. The ROM file is unchanged. Both stack and direct-page canaries are
checked after every call.

Both machine corpora cover 72 cases: four base values and eighteen current
values, including ordinary repeated-buff states and explicit 16-bit
boundaries. Clean original and pinned compiled Redux each match their exact
source-derived formula in all 72 cases. The report identities distinguish the
clean ROM from the compiled pinned ROM; neither ROM is distributed.

The immutable v4 native dispatcher initially reproduces fourteen mismatches
among eighteen non-NPC cases at base 80. The expanded corpus reproduces 47
mismatches among 72 non-NPC cases over all four bases. All 72 NPC failure
controls pass. These red reports retain their original runtime/library hashes
and are not relabeled as corrected-build tests.

Machine helper parity and actual native callback parity are separate claims.
The native driver also executes resumable text children, but it prepares the
callback boundary and does not test an entire turn, physical input, pixels,
audio or every battle. This evidence does not certify a full conversion or a
full playthrough.

The corrected immutable dev.15 v5 native library passes all 144 prepared
dispatch cases per pack (288 total). Each pack's 72 non-NPC cases also agrees
with the corresponding independent machine corpus. Fresh machine reruns
execute 72 clean-original and 72 pinned-Redux calls (144 total), with zero
source or native mismatches. All stack/direct-page canaries pass, and both
owner-provided ROM files remain unchanged. The 72 NPC controls per native
pack retain the source failure behavior.

Final execution identities:

```text
player.exe  68935ae10a49086601e872e2b271d3cf6460010598b842c6683aa5779a1ad1ab
observer.exe 6bb03da1e7de099ba0a611e65e3a9ce4d703f281d680e00629260edd57ba1407
library     67df5cacc2bb2fecb3491fd9c003eea67a5f0458edc3188a2db36eb40df760b8
```

The player library is executed by the private native driver. The observer
hash records provenance; these cases do not execute its gameplay loop.
Reports are `research/redux-battle-offense-up-dev15-v5.json`,
`research/original-battle-offense-up-dev15-v5.json`,
`research/redux-battle-offense-up-machine-dev15-v5.json`, and
`research/original-battle-offense-up-machine-dev15-v5.json`. Their reproduction
flags, source identities, input case results and private-driver hashes are
retained separately from the pre-correction v4 reports.
