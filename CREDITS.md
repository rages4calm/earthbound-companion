# Credits and provenance

EarthBound Companion exists because of years of documentation, disassembly, native-port, ROM-hacking and preservation work. Links below identify what was used directly and what informed compatibility research.

## Original game

- **EarthBound / Mother 2** — Nintendo, APE, HAL Laboratory, Shigesato Itoi, and the original development and localization teams.
- All original game code, characters, text, graphics, music and other assets remain the property of their respective owners. None are included in this repository.

## Native source lineage

- [Herringway/ebsrc](https://github.com/Herringway/ebsrc) — foundational EarthBound disassembly and source recreation.
- [BrianPugh/earthbound](https://github.com/BrianPugh/earthbound) — C game-code recreation, runtime asset tooling and native-platform work derived from ebsrc.
- [seanstaggsQU/earthboundRecompLinux2026](https://github.com/seanstaggsQU/earthboundRecompLinux2026) — selected extended native fork, pinned at commit `76eacab54b05766b82c98da9c55d94d1236ece03`.
- [seanstaggsQU/EarthboundNativePublic](https://github.com/seanstaggsQU/EarthboundNativePublic) — related packaged-release history consulted during source selection.

All contributors to those repositories retain credit for their work. Companion’s patch does not erase or replace upstream authorship.

## Music and ROM-hack research

- **Conn** — EarthBound MSU-1 implementation work.
- **ShadowOne333** — [EarthBound MSU-1 pack](https://archive.org/details/earthbound-msu-1-pack), track loop rules, and [MaternalBound Redux](https://github.com/ShadowOne333/MaternalBound-Redux).
- **MaternalBound Redux contributors** — the native command adaptation follows their documented CCScript semantics. The [safe money commands](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/bugfixes/try_give_money.ccs), [SupremeKirb's party-position command](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/essential/cc_char_in_party.ccs), and [the window-title extension](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/redux/window_titles.ccs) inform the initial native handlers. **jtolmar**, **cooprocks123e**, **Catador**, **SupremeKirb**, and the other authors credited in those source files retain credit for their extensions. These handlers do not establish support for the complete hack.
- [stochaztic/eb-randomizer](https://github.com/stochaztic/eb-randomizer) and [earthbound.app](https://earthbound.app/) — randomizer behavior and softlock-risk research. Companion’s Story Shuffle is an independent native implementation and does not reproduce their seed format.
- [Raid-rgb/Earthbound-Widescreen-patch-for-BSNES-HD](https://github.com/Raid-rgb/Earthbound-Widescreen-patch-for-BSNES-HD) — compared during widescreen research; not bundled or applied.
- [ShrineFox/EarthBound-Mod-Menu](https://github.com/ShrineFox/EarthBound-Mod-Menu) — ROM-side QoL reference; not bundled or applied.
- [TheRunaway5/Phase-Distorter](https://github.com/TheRunaway5/Phase-Distorter) and [nickclyde/EarthBoundRecomp](https://github.com/nickclyde/EarthBoundRecomp) — alternative native/recompilation architectures evaluated during source selection.

## Libraries and tools

- [SDL2](https://github.com/libsdl-org/SDL) — native window, rendering, audio and input layer. zlib license included.
- [.NET](https://github.com/dotnet/runtime) and Windows Forms — self-contained Companion desktop application. Notices included.
- [BrianPugh/tamp](https://github.com/BrianPugh/tamp) — save-state compression. Original license included.
- [Dave Gamble/cJSON](https://github.com/DaveGamble/cJSON) — JSON parsing used by the native layer. MIT license included.
- [LakeSnes](https://github.com/elzo-d/LakeSnes) contributors — software SNES graphics/audio implementation lineage. Notice included.
- Brad Conte’s [crypto-algorithms](https://github.com/B-Con/crypto-algorithms) — SHA-256 implementation lineage. Notice included.
- [PyInstaller](https://github.com/pyinstaller/pyinstaller) — standalone first-run ROM extraction helper.
- [pk-hack/CoilSnake](https://github.com/pk-hack/CoilSnake) — builds the upstream MaternalBound development source for the local native-conversion work.
- [charasyn/ccscript_legacy](https://github.com/charasyn/ccscript_legacy) — legacy CCScript compiler dependency, locally updated to build under C++17.

## Companion work

The Companion application, native PC option integration, packaging, Story Shuffle v2, recovery workflow, validation tooling and documentation were assembled for Carl Prewitt Jr.’s native PC edition with OpenAI Codex assistance. Generated work was reviewed, built and tested locally; upstream authorship remains as listed above.

If a material credit is missing or inaccurate, open an issue with the project/file and requested correction.
