# RetroPortingToolKit review - October 8, 2026

The owner requested study of Matthew Stanley's work for EarthBound Companion and future native ports. This records methods and application boundaries. No framework migration or third-party code integration occurred in this pass.

Follow-up: [game-porting toolkit reference](game-porting-toolkit-reference.md) covers the subsequently supplied recomp-ui, recomp-net and rbengine repositories, their pinned APIs/licenses, a snapshot unit test and opportunities for our own tools.

## Architecture

Stanley's [renderer article](https://1379.tech/faithful-first-then-let-go-experimenting-with-custom-renderers/) separates authentic rendering from enhanced rendering of the same state. For Companion, retain a reference presentation when validating widescreen; treat scenery extension, HUD placement and battle effects as distinct consumers. This is a recommendation, not evidence that our C renderer already has an independent reference renderer.

His [decomp-annotated recomp article](https://1379.tech/recomp-vs-decomp-wrong-question/) describes combining a reusable runtime with game-specific names and semantic knowledge. For future ports, use disassemblies/symbol maps to identify state and functions before adding high-level features. Companion already benefits from EarthBound assembly references; the principle fits our narrow C adaptations.

## Widescreen checks

The [widescreen guide](https://github.com/RetroPortingToolKit/snesrecomp/blob/main/docs/WIDESCREEN_PATTERNS.md) is relevant to reported cave-fragment transitions, repeated PSI at Giygas and credits corruption. Transferable checks include prepopulating visible margins, using actual rendered scroll phase, respecting authored arena edges, distinguishing periodic layers from world history, and preserving rigid HUD glyph groups. It also warns that widening enemy spawning can activate progression triggers early. Future Companion regressions should test both edges, first visible frames, raster changes and cold restores. Similarities do not establish identical root causes across engines.

## Comparison testing

[SNES_COSIM.md](https://github.com/RetroPortingToolKit/snesrecomp/blob/main/SNES_COSIM.md) proposes finding the earliest divergent state through subsystem hashes rather than a guessed culprit. Repeated self-comparisons and injected faults prove the comparison detects errors. For Companion, use deterministic input, canonical game snapshots and separate graphics/audio state when diagnosing a reference mismatch. Hardware-specific SNES clock/device structures are not directly applicable to this high-level C engine.

One method is used concretely now: v4 validation deliberately changes trade stock, battle/placement pointers, spawn weights, enemy AI, drop odds and unrelated bytes to prove rejection. Native chooser fixtures compare production selection against independently parsed asset data. This is invariant testing, not full machine co-simulation.

## Framework fit

The [repository](https://github.com/RetroPortingToolKit/snesrecomp) translates 65816 code to C, supplying modeled SNES devices and an interpreter fallback. It requires per-game analysis and validation; documented cartridge support excludes ExHiROM at this review. Our private compiled Redux image is 6 MiB with mapping byte 0x25 in its expanded header, a concrete compatibility question before any experiment. No EarthBound/Redux execution was demonstrated here.

Keep the playable C port. For a future port without such a base, evaluate snesrecomp with a clean image, pinned framework, explicit mapper support, reference comparisons and separate enhancement gates. Review the source license before importing code. No Discord messages or private server content were accessed.
