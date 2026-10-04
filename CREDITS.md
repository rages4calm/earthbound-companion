# Credits and provenance

EarthBound Companion exists because of years of documentation, disassembly, native-port, ROM-hacking and preservation work. Links below identify what was used directly and what informed compatibility research.

## Original game

- **EarthBound / Mother 2** â€” Nintendo, APE, HAL Laboratory, Shigesato Itoi, and the original development and localization teams.
- All original game code, characters, text, graphics, music and other assets remain the property of their respective owners. None are included in this repository.

## Native source lineage

- [Herringway/ebsrc](https://github.com/Herringway/ebsrc) â€” foundational EarthBound disassembly and source recreation.
- [BrianPugh/earthbound](https://github.com/BrianPugh/earthbound) â€” C game-code recreation, runtime asset tooling and native-platform work derived from ebsrc.
- [seanstaggsQU/earthboundRecompLinux2026](https://github.com/seanstaggsQU/earthboundRecompLinux2026) â€” selected extended native fork, pinned at commit `76eacab54b05766b82c98da9c55d94d1236ece03`.
- [seanstaggsQU/EarthboundNativePublic](https://github.com/seanstaggsQU/EarthboundNativePublic) â€” related packaged-release history consulted during source selection.

All contributors to those repositories retain credit for their work. Companionâ€™s patch does not erase or replace upstream authorship.

## Music and ROM-hack research

- **Conn** â€” EarthBound MSU-1 implementation work.
- **ShadowOne333** â€” [EarthBound MSU-1 pack](https://archive.org/details/earthbound-msu-1-pack), track loop rules, and [MaternalBound Redux](https://github.com/ShadowOne333/MaternalBound-Redux).
- **MaternalBound Redux contributors** â€” the native command adaptation follows their documented CCScript semantics. The [safe money commands](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/bugfixes/try_give_money.ccs), [SupremeKirb's party-position command](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/essential/cc_char_in_party.ccs), and [the window-title extension](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/redux/window_titles.ccs) inform the initial native handlers. **jtolmar**, **cooprocks123e**, **Catador**, **SupremeKirb**, and the other authors credited in those source files retain credit for their extensions. These handlers do not establish support for the complete hack.
- **JTolmar, The_Kirby and Coop** — Redux's [scripted enemy-AI framework](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/redux/enemy_ai.ccs) and [action commands](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/redux/enemy_ai_actions.ccs), explicitly adapted to the native scheduler.
- **Vittorio, Chaz and D-Man** — [six-letter names](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/redux/six_letters.ccs). **D-Man and contributors** — expanded animation/run tables. Redux's favorite-food expansion, controls, stamina, item menus and related extensions also inform their native adaptations; authorship remains with the credited upstream source contributors.
- **CoilSnake contributors** — the binary formats and relocation code for sprites, maps, events, encounters and fonts inform the native pack converters. Corresponding converter/adaptation source is published with GPLv3 notices.
- [stochaztic/eb-randomizer](https://github.com/stochaztic/eb-randomizer) and [earthbound.app](https://earthbound.app/) â€” randomizer behavior and softlock-risk research. Companionâ€™s Story Shuffle is an independent native implementation and does not reproduce their seed format.
- [Raid-rgb/Earthbound-Widescreen-patch-for-BSNES-HD](https://github.com/Raid-rgb/Earthbound-Widescreen-patch-for-BSNES-HD) â€” compared during widescreen research; not bundled or applied.
- [ShrineFox/EarthBound-Mod-Menu](https://github.com/ShrineFox/EarthBound-Mod-Menu) â€” ROM-side QoL reference; not bundled or applied.
- [TheRunaway5/Phase-Distorter](https://github.com/TheRunaway5/Phase-Distorter) and [nickclyde/EarthBoundRecomp](https://github.com/nickclyde/EarthBoundRecomp) â€” alternative native/recompilation architectures evaluated during source selection.

## Libraries and tools

- [SDL2](https://github.com/libsdl-org/SDL) â€” native window, rendering, audio and input layer. zlib license included.
- [.NET](https://github.com/dotnet/runtime) and Windows Forms â€” self-contained Companion desktop application. Notices included.
- [BrianPugh/tamp](https://github.com/BrianPugh/tamp) â€” save-state compression. Original license included.
- [Dave Gamble/cJSON](https://github.com/DaveGamble/cJSON) â€” JSON parsing used by the native layer. MIT license included.
- [LakeSnes](https://github.com/elzo-d/LakeSnes) contributors â€” software SNES graphics/audio implementation lineage. Notice included.
- Brad Conteâ€™s [crypto-algorithms](https://github.com/B-Con/crypto-algorithms) â€” SHA-256 implementation lineage. Notice included.
- [PyInstaller](https://github.com/pyinstaller/pyinstaller) â€” standalone first-run ROM extraction helper.
- [pk-hack/CoilSnake](https://github.com/pk-hack/CoilSnake) â€” builds the upstream MaternalBound development source for the local native-conversion work.
- [charasyn/ccscript_legacy](https://github.com/charasyn/ccscript_legacy) â€” legacy CCScript compiler dependency, locally updated to build under C++17.

## Companion work

The Companion application, native PC option integration, packaging, Story Shuffle v2, recovery workflow, validation tooling and documentation were assembled for Carl Prewitt Jr.â€™s native PC edition with OpenAI Codex assistance. Generated work was reviewed, built and tested locally; upstream authorship remains as listed above.

If a material credit is missing or inaccurate, open an issue with the project/file and requested correction.
