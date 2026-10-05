# EarthBound native PC research

Checked October 3–4, 2026. Findings distinguish native game code from a native executable running SNES instruction semantics. Local source inspection, build results and tests support the architecture conclusions below.

## Source choice

| Project | What it provides | Decision |
|---|---|---|
| [Herringway/ebsrc](https://github.com/Herringway/ebsrc) | EarthBound disassembly and a reconstructed SNES ROM. Valuable reference, without a desktop game engine. | Reference source. |
| [BrianPugh/earthbound](https://github.com/BrianPugh/earthbound) | Platform-independent C game code, asset tools and SDL2 desktop platform. | Correct foundational direction. |
| [seanstaggsQU/earthboundRecompLinux2026](https://github.com/seanstaggsQU/earthboundRecompLinux2026) | BrianPugh descendant with native widescreen, MSU mixing, runtime asset packs, sprint, key-item storage, save-anywhere and fixes. | Selected source, commit `76eacab54b05766b82c98da9c55d94d1236ece03`. |
| [EarthboundNativePublic](https://github.com/seanstaggsQU/EarthboundNativePublic) | Packaged releases of that project's native desktop game. | Useful release history; compiled our editable source locally. |
| [Phase Distorter](https://github.com/TheRunaway5/Phase-Distorter) | Extensive C++ static translation, desktop tooling, widescreen and a planned native-engine migration. Its current `cpp/docs/native-engine.md` explicitly documents remaining MainCpu65816/SnesBus/address-dispatch compatibility work. | Its current architecture does not meet the requested main-CPU-independent gameplay implementation. |
| [nickclyde/EarthBoundRecomp](https://github.com/nickclyde/EarthBoundRecomp) | An LLE-first runtime with optional recompilation work. | Not selected for the same architecture goal. |

The selected desktop build has `EB_ENABLE_VERIFY=OFF`. It links the C gameplay library and software PPU/SPC/DSP, rather than the optional full-system verification emulator. Widescreen uses extra world tile/entity rendering within the 512×256 maximum tilemap canvas. Its presentation layer crops for 16:9, 4:3 and 21:9, with fixed-art exceptions. Display resolution is independent of the original artwork resolution.

## MaternalBound Redux

[MaternalBound Redux](https://github.com/ShadowOne333/MaternalBound-Redux) is a substantial Mother 2 restoration/uncensoring and QoL project. The latest published release found on its [release page](https://github.com/ShadowOne333/MaternalBound-Redux/releases) was **v1.1**. The repository has ongoing work. A finished 2.0 release and a release date were not verified.

Its patch formats modify a SNES ROM, including executable instructions and relocated data. Loading a patched ROM's art into a C port does not reproduce those changes automatically. We have not labeled the entire hack compatible or stacked its patch over a native asset pack.

| Redux-related feature | This native edition |
|---|---|
| MSU music | Implemented and installed; playback flags checked against Redux's `msu1.ccs`. |
| Running and modern controls | Native sprint and full GUI remapping available. |
| Convenience / inventory improvements | Separate key-item pool inherited from the selected C fork; extra optional dialogue, homesickness, reminder-call and reward settings added. |
| Uncensored script, renamed enemies/items, restored graphics | Converted from the checksum-pinned active source. Native opening/dialogue, graphics and scene checks pass; full story parity remains unverified. |
| Redux-specific battle sprites, event patches, new shops and code fixes | Explicit native implementations cover Tools, equipment, movement helpers, combat fixes and converted shops. See the source-pinned coverage and assembly ledger in [MATERNALBOUND-NATIVE.md](MATERNALBOUND-NATIVE.md). Full compatibility is incomplete. |

The development edition pins active source `897d00833f4a08a0a92f106abf631629a6a6a041`, rather than labeling itself the official v1.1 release. Its standalone owner-ROM setup reproduces the checked native pack, with native implementations, data converters and development/debug exclusions recorded separately. Later gameplay and full story/randomized playthroughs remain to be verified. Keep Redux and original save sets separate if data or event semantics differ. Version 2.0 changes must be assessed after they are published.

## MSU sources and implementation

The [Zeldix EarthBound MSU thread](https://www.zeldix.net/t1931-earthbound) identifies Conn's MSU patch and ShadowOne333's loop table. The installed [EarthBound MSU-1 pack](https://archive.org/details/earthbound-msu-1-pack) is credited by its archive metadata to ShadowOne333, who describes it as prepared for MaternalBound Redux and usable with other MSU-compatible EarthBound builds.

Downloaded 164 individual PCM files, checked sizes and MD5 against the source metadata, and separately validated MSU1 magic, 44.1 kHz stereo frame lengths and loop-point bounds. The checksum registry is [research/msu-manifest.json](research/msu-manifest.json); current native loop/end, transition, effects and fallback evidence is [validation/native-redux-audio.json](validation/native-redux-audio.json). A local synthetic-audio test also covers one-shot ending, looping, resampling, fade-out and malformed input.

The selected source originally repeated every PCM track. This build uses game-specific repeat flags, so fanfares and jingles finish. It also follows music fade/half-volume/full-volume commands and exposes master/MSU volume controls. Gameplay does not need an MSU-patched ROM or emulated MSU hardware to play these files.

## Other hacks considered

[Raid-rgb's widescreen patch](https://github.com/Raid-rgb/Earthbound-Widescreen-patch-for-BSNES-HD) targets BSNES-HD and has separate ROM variants. It is not necessary for the native widescreen renderer and is not treated as a drop-in native mod.

[ShrineFox's EarthBound Mod Menu](https://github.com/ShrineFox/EarthBound-Mod-Menu) supplies useful ROM-side trainer/QoL ideas, but its assembly patch cannot be imported as compiled C behavior. This edition instead exposes the implemented native options through settings and safe profile files.

Other worthwhile future work includes an authored HD asset pack, richer shader choices, complete Redux compatibility, and a complete regression playthrough. These are future work, not shipped feature claims.

## Randomizer integration — October 4, 2026

The requested [earthbound.app](https://earthbound.app/) is backed by [stochaztic/eb-randomizer](https://github.com/stochaztic/eb-randomizer). Its generator expands ROM data, applies save/gameplay patches, and relocates scripts; Ancient Cave also regenerates routing. Our original-layout asset extractor cannot translate those changed SNES instructions into native C behavior. Website output is therefore not claimed compatible.

The older preview shipped independent **native Story Shuffle v2**: bounded optional gift/shop/drop/stat changes, mandatory progression preservation and isolated saves. The original ROM's 61 text/script blocks were decoded to derive item dependencies and literal scripted battles. A second explicit Monkey Cave request list protects dynamic trade handlers as well. The resulting policy preserves 78 items and 52 scripted-battle enemy records; a separate whole-pack invariant checker runs at generation and before launch. All 1,000 tested seeds and 30 option/style combinations pass. Guided save restoration verifies the selected adventure, assets, engine, file hashes and native quick-save header/CRC, with a backup before applying changes. These are bounded checks, not a completed playthrough.

The upstream [README](https://github.com/stochaztic/eb-randomizer/blob/master/README.md) explicitly marks dangerous options and disables Keysanity in its UI due to softlock issues. That mode should not be treated as a general safety guarantee. Full Ancient Cave/Open support requires the following together:

| Native port requirement | Why copying a randomized ROM's tables is insufficient |
|---|---|
| Door/cluster graph and sanctuary path generation | The new world needs its actual routing/connectivity rules and reachable exits. |
| Relocated/expanded dialogue script registry | The current extractor uses original script ranges and labels; new ROM expansion addresses are not represented. |
| Mandatory SNES patches translated into C | Expanded saves, introductory/story changes and native event handling must implement the same semantics. |
| Party, boss, key-item and progression state rules | Skipping original events changes assumptions in scripted movement, battles and character availability. |
| Seed solver and native regression fixtures | Successful website ROM generation alone does not prove that the native engine preserves its progression guarantees. |

These unported modes remain unavailable. Every supported Story Shuffle seed uses its own save/config/screenshot directory and shares the installed soundtrack. See [RANDOMIZER.md](RANDOMIZER.md) for exact rules, legacy recovery and verification scope.


## Redux development checkpoint

Story Shuffle v3 now has a separate policy for the exact Redux pack: 110 protected items and 84 enemy records, derived from 64,360 decoded operations and 45 scripted encounter groups. All 1,000 seeds and 30 option combinations pass independently for both original and Redux packs. A native randomized Redux opening passes; this is not full Ancient Cave/Open support or a complete randomized playthrough.

The frozen Redux setup helper and clean ZIP pass without installed Python/Git. MSU setup repaired one deliberately corrupt track through a real download and verified all 164 files; 163 already-verified cache files were reused for that bounded test. No ROM, game pack, PCM or save files are in the distributable ZIP. See [validation/native-redux-clean-package.json](validation/native-redux-clean-package.json) for exact hashes and coverage.
