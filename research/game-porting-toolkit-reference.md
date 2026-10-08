# Game-porting toolkit reference

Reviewed October 8, 2026 for EarthBound Companion and future ports. The owner welcomes our own tools as well as useful open-source components. These are integration candidates and engineering references; the review did not replace the game engine, launcher, or save system.

## Where each project fits

| Resource | Useful contribution | EarthBound decision | Future-port decision |
|---|---|---|---|
| [1379.tech](https://1379.tech/) | Architecture and debugging methods | Apply relevant methods through our existing tools | Consult alongside the source and runtime tests |
| [snesrecomp](https://github.com/RetroPortingToolKit/snesrecomp) | 65816 translation and SNES runtime | Keep the working C foundation; Redux mapper compatibility requires investigation | Evaluate when there is no suitable high-level native base |
| [recomp-ui](https://github.com/RetroPortingToolKit/recomp-ui) | Shared launcher and in-game settings interfaces | Useful model and overlay candidate; the existing .NET launcher needs a deliberate adapter or refactor | Strong candidate for a common native launcher/settings layer |
| [recomp-net](https://github.com/RetroPortingToolKit/recomp-net) | Input synchronization, transports and rollback coordination | No automatic multiplayer benefit for this single-player game | Evaluate for games with a defined multiplayer input model |
| [rbengine](https://github.com/RetroPortingToolKit/rbengine) | Offline tick-keyed snapshot storage | Candidate for a copied-save replay/debugger experiment | Useful small component for rewind or run-ahead experiments |

The project-specific decisions in this table are our assessment, not upstream compatibility guarantees. The [earlier review](retroporting-toolkit-review-20261008.md) covers rendering, widescreen and co-simulation methods in more detail. [RESEARCH.md](../RESEARCH.md) retains the original native-foundation comparison.

## recomp-ui

The [architecture](https://github.com/RetroPortingToolKit/recomp-ui/blob/7e884a227accea91ddb378671bd49aaeeea13371/docs/ARCHITECTURE.md) composes capability panels and specializes shared behavior through console/game descriptors. That is a useful design for our own tools: one settings implementation, with per-game capabilities and labels instead of copied launchers.

The [launcher API](https://github.com/RetroPortingToolKit/recomp-ui/blob/7e884a227accea91ddb378671bd49aaeeea13371/src/recomp_launcher.h) exposes a C boundary. Its settings and mod controls require host callbacks; displaying a mod in this UI does not implement its patch format or translate ROM instructions into native behavior. A host must still apply settings, validate compatibility and own persistence.

The [runtime UI guide](https://github.com/RetroPortingToolKit/recomp-ui/blob/7e884a227accea91ddb378671bd49aaeeea13371/docs/RUNTIME_UI.md) separates navigation/presentation from simulation, renderer, audio and input routing. It offers ImGui presentation, an SDL2 renderer integration and a compact CPU-framebuffer fallback. An SDL host must restore its logical size/viewport after drawing the overlay and consume menu input before gameplay receives it. Backend switches need a safe host restart path. These responsibilities matter for Companion's display settings and transition regressions.

Our current Windows launcher is .NET/WinForms, while gameplay uses native C/SDL2. Reusing this library would require an adapter and lifecycle work; no replacement was made. For a new native port, evaluate the shared interface before writing another full launcher.

## recomp-net

The [README](https://github.com/RetroPortingToolKit/recomp-net/blob/618640272fd715bf8317fa17bf1f739e79738040/README.md) describes C11 delay synchronization: every peer waits for the required input before advancing simulation. UDP LAN and optional libjuice/ICE transports are available. Signaling and online deployment have additional responsibilities; the linked lobby server is a separate project. Inspect the chosen topology rather than assuming every internet connection works through a simple port-forward.

Important documentation mismatch: that README still describes rollback as branch-only/planned. The pinned [rollback guide](https://github.com/RetroPortingToolKit/recomp-net/blob/618640272fd715bf8317fa17bf1f739e79738040/docs/rollback.md), [driver API](https://github.com/RetroPortingToolKit/recomp-net/blob/618640272fd715bf8317fa17bf1f739e79738040/include/recomp_net/rb_driver.h) and source tree put the shared rollback stack on main. The passive episode object is not a complete runner; the episode driver coordinates correction and replay. The host supplies snapshots, simulation ticks, state digests, input decoding and replay presentation/audio suppression. This review establishes source presence, not verified end-to-end game netplay.

The [host integration contract](https://github.com/RetroPortingToolKit/recomp-net/blob/618640272fd715bf8317fa17bf1f739e79738040/docs/host_integration.md) requires deterministic RNG/timing, published inputs as the simulation's controller source, synchronized loads, and thread ownership or external locking. A stalled simulation still needs a responsive host window and a disconnect path.

Future adoption must begin with a deterministic two-instance offline comparison, then local network tests, then impaired-network and reconnect tests. For EarthBound, party control/co-op rules would be a separate game feature. The library does not design those rules.

## rbengine

The current [README](https://github.com/RetroPortingToolKit/rbengine/blob/2a03e73693acee0fb78076ea058642c931bef12e/README.md) describes a dependency-free offline core: opaque snapshot storage and a monotonic clock. Peer-related scheduling, input history and hash confirmation moved to recomp-net. The current repository is smaller than the broad phrase “rollback engine” might suggest.

The [snapshot API](https://github.com/RetroPortingToolKit/rbengine/blob/2a03e73693acee0fb78076ea058642c931bef12e/include/retcomm_rbengine/snap_ring.h) accepts host-serialized blobs, supports tick lookup and discarding future snapshots, and transfers ownership of stored data. Its default depth is 40 **slots**, not a fixed duration; history length depends on snapshot frequency. The [implementation](https://github.com/RetroPortingToolKit/rbengine/blob/2a03e73693acee0fb78076ea058642c931bef12e/src/snap/rbe_snap_ring.c) caps requested depth at 512 slots. Budget memory from measured state size and cadence.

A game's full deterministic state still needs serialization. A phone save or an opaque desktop quick-save is not automatically sufficient for replay: test RNG, queued events, rendering/audio state and external effects explicitly. Replaying a tick must not duplicate disk writes or already-heard sound.

Locally compiled the unmodified pinned snapshot source and upstream `snap_ring_test.c` with GCC/C11 and warnings enabled. All 18 reported checks passed, including eviction, lookup, serializer callbacks, future deletion and clearing. This is an upstream unit test with small synthetic blobs; it does not prove EarthBound rewind, the monotonic-clock implementation or either networking/UI integration.

## Our own tools: practical next candidates

These are proposed utilities, not newly shipped features. Keep the reusable runner separate from each game's state/input adapter.

| Tool | First useful result | Acceptance check |
|---|---|---|
| Bug replay runner | Copy a checkpoint, record input, identify build/assets/settings and capture a bounded replay | Two identical runs agree; a deliberately changed input produces a reported difference |
| Viewport inspector | Capture authored area, expanded margins, camera/scroll and effect bounds through transitions | Compare first visible frames and both edges at supported aspects; flag repeated target effects outside their arena |
| Asset/progression inspector | Display typed records, quest dependencies and randomizer changes | Known invalid pointers/trade stock are rejected; valid fixture changes reach the native consumer |

EarthBound already has bounded input fixtures, asset invariants and save/package receipts. Build on those pieces. A useful first generalization is a single replay report containing screenshots, state differences and an exact reproduction command. That can reduce repeated manual playtesting without claiming full campaign coverage.

Import small mature components when they save effort; write our own adapters, inspection interfaces and game-specific logic where that gives better control. Pin dependencies and preserve their license notices. Original code can coexist with upstream components.

## Related references retained

- [Authentic and custom rendering](https://1379.tech/faithful-first-then-let-go-experimenting-with-custom-renderers/) — compare enhancements against a faithful path.
- [Decomp-annotated recompilation](https://1379.tech/recomp-vs-decomp-wrong-question/) — use game-specific knowledge with reusable runtime machinery.
- [Widescreen patterns](https://github.com/RetroPortingToolKit/snesrecomp/blob/main/docs/WIDESCREEN_PATTERNS.md) and [SNES co-simulation](https://github.com/RetroPortingToolKit/snesrecomp/blob/main/SNES_COSIM.md) — detailed sources assessed in the earlier review; re-pin before implementation.
- [earthbound.app](https://earthbound.app/) and [eb-randomizer](https://github.com/stochaztic/eb-randomizer) — behavior references. Companion's [Story Shuffle](../RANDOMIZER.md) remains an independent native implementation; website seeds and Open/Ancient Cave modes are not claimed compatible.
- [Native-source comparisons and Redux](../RESEARCH.md) — retain the selected C foundation and patch-translation boundaries.

## Version, license and coverage record

| Repository | Reviewed commit | Root license |
|---|---|---|
| recomp-ui | `7e884a227accea91ddb378671bd49aaeeea13371` | MIT, Matthew Stanley |
| recomp-net | `618640272fd715bf8317fa17bf1f739e79738040` | MIT, recomp-net contributors |
| rbengine | `2a03e73693acee0fb78076ea058642c931bef12e` | MIT, retcomm-rbengine contributors |

Root licenses were read. Bundled and optional dependency licenses still require an integration-specific review. Selected documentation, API headers, source and tests were inspected, not every file in these repositories. The snapshot test is the only compiled/executed upstream component in this pass. No game migration, multiplayer implementation, Discord access or owner-save modification occurred. [Review receipt](../validation/toolkit-review-20261008.json) records the selected source hashes and test scope. Refresh these commits and contracts before adopting a component in another project.
