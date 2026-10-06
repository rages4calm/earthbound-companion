# Credits and provenance

Development route research: [Rick N. Bruns / SNESMaps — Giant Step map](https://www.snesmaps.com/maps/EarthBound/EarthboundMapGiantStep.html). The third-party map is referenced, not redistributed.

EarthBound Companion exists because of years of documentation, disassembly, native-port, ROM-hacking and preservation work. Links below identify what was used directly and what informed compatibility research.

## Original game

- **EarthBound / Mother 2** — Nintendo, APE, HAL Laboratory, Shigesato Itoi, and the original development and localization teams.
- Original characters, text, graphics, music and game material remain the property of their respective rights holders. ROM images and extracted asset/audio packs are excluded; labeled development screenshots are included as documentation. The native source patch contains recreation/adaptation code and must not be represented as unrelated to the original game or upstream work.

## Native source lineage

- [Herringway/ebsrc](https://github.com/Herringway/ebsrc) — foundational EarthBound disassembly and source recreation.
- [BrianPugh/earthbound](https://github.com/BrianPugh/earthbound) — C game-code recreation, runtime asset tooling and native-platform work derived from ebsrc.
- [seanstaggsQU/earthboundRecompLinux2026](https://github.com/seanstaggsQU/earthboundRecompLinux2026) — selected extended native fork, pinned at commit `76eacab54b05766b82c98da9c55d94d1236ece03`.
- [seanstaggsQU/EarthboundNativePublic](https://github.com/seanstaggsQU/EarthboundNativePublic) — related packaged-release history consulted during source selection.

All contributors to those repositories retain credit for their work. Companion’s patch does not erase or replace upstream authorship.

**These are current dependencies, not just research references.** The compiled engine still uses Brian's C recreation through Sean's pinned fork, with Herringway in its ancestry. The [provenance review](UPSTREAM.md) records the actual build origin, fork chain and retained source. Companion's additional conversion work does not make the engine an independent rewrite.

## Music and ROM-hack work

- **Conn** — EarthBound MSU-1 implementation work.
- **ShadowOne333** — [EarthBound MSU-1 pack](https://archive.org/details/earthbound-msu-1-pack), track loop rules, and [MaternalBound Redux](https://github.com/ShadowOne333/MaternalBound-Redux).
- **TragicManner, H.S., the hack's script/art contributors and all upstream credit-listed authors** — the writing references, assembly help, restored art and additional work identified in MaternalBound's [complete credits](https://github.com/ShadowOne333/MaternalBound-Redux/tree/897d00833f4a08a0a92f106abf631629a6a6a041#credits) and [sprite credits](https://github.com/ShadowOne333/MaternalBound-Redux/tree/897d00833f4a08a0a92f106abf631629a6a6a041#sprite-credits). Those full lists remain the authority for individual upstream assets and changes.
- **MaternalBound Redux contributors** — the native command adaptation follows their documented CCScript semantics. The [safe money commands](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/bugfixes/try_give_money.ccs), [SupremeKirb's party-position command](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/essential/cc_char_in_party.ccs), and [the window-title extension](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/redux/window_titles.ccs) inform the initial native handlers. **jtolmar**, **cooprocks123e**, **Catador**, **SupremeKirb**, and the other authors credited in those source files retain credit for their extensions. These handlers do not establish support for the complete hack.
- **JTolmar, The_Kirby and Coop** — Redux's [scripted enemy-AI framework](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/redux/enemy_ai.ccs) and [action commands](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/redux/enemy_ai_actions.ccs), explicitly adapted to the native scheduler.
- **Vittorio, Chaz and D-Man** — [six-letter names](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/redux/six_letters.ccs). **D-Man and contributors** — expanded animation/run tables. Redux's favorite-food expansion, controls, stamina, item menus and related extensions also inform their native adaptations; authorship remains with the credited upstream source contributors.
- **CoilSnake contributors** — the binary formats and relocation code for sprites, maps, events, encounters and fonts inform the native pack converters. Corresponding converter/adaptation source is published with GPLv3 notices.
- [stochaztic/eb-randomizer](https://github.com/stochaztic/eb-randomizer) and [earthbound.app](https://earthbound.app/) — randomizer behavior and softlock-risk research. Companion’s Story Shuffle is an independent native implementation and does not reproduce their seed format.
- [Raid-rgb/Earthbound-Widescreen-patch-for-BSNES-HD](https://github.com/Raid-rgb/Earthbound-Widescreen-patch-for-BSNES-HD) — compared during widescreen research; not bundled or applied.
- [ShrineFox/EarthBound-Mod-Menu](https://github.com/ShrineFox/EarthBound-Mod-Menu) — ROM-side QoL reference; not bundled or applied.
- [TheRunaway5/Phase-Distorter](https://github.com/TheRunaway5/Phase-Distorter) and [nickclyde/EarthBoundRecomp](https://github.com/nickclyde/EarthBoundRecomp) — alternative native/recompilation architectures evaluated during source selection.

- **cooprocks123e and the Redux contributors** — [battle overworld sprites](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/redux/Bowspr.ccs), [Mother 3 style battle sprites](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/redux/m3sprites.ccs), and [expanded equipment stats](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/redux/new_stats_equipment.ccs). The native implementations follow the pinned source behavior and retain upstream credit.
- **CoilSnake CastModule and FontModule contributors** — [cast formats](https://github.com/pk-hack/CoilSnake/blob/master/coilsnake/modules/eb/CastModule.py) and [credits font relocation](https://github.com/pk-hack/CoilSnake/blob/master/coilsnake/modules/eb/FontModule.py) guide the ending converter. Refer to the pinned local build record for the complete source revision.

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

The reproducible Redux helper pins [CoilSnake `346cfc7`](https://github.com/pk-hack/CoilSnake/tree/346cfc753644bc3703b6fc4eaa0a5d6bdcb9bb4a) and [CCScript 1.500 `cecd6a4`](https://github.com/charasyn/ccscript_legacy/tree/cecd6a44baf88f3e6de86938b4052502b4c53366). The C++17 and Windows `std::filesystem` repair is published in [patches/ccscript-cxx17.patch](patches/ccscript-cxx17.patch). The standalone setup entry point, converters and packaging specification are corresponding source; upstream compiler authors retain their credit.

- **ShadowOne333 and Redux contributors** — [Jeff's Tools](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/redux/tools.ccs), restored shops, rewritten story and [expanded shop definitions](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/expansion/expand_shops.ccs).
- **Redux movement and title contributors** — [movement helpers](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/redux/movscr_codes.ccs) and [Mother 2 title movements](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/redux/m2_title_screen_movements.ccs), adapted to native resumable scenes.
- **PhoenixBound, Catador, JTolmar, cooprocks123e, SupremeKirb, Vittorio, D-Man, Chaz and all authors credited upstream** — the bug fixes, controls, animation, compiler formats and scene behavior on which these adaptations depend. The pinned source files retain the specific authorship of each change.
- **JTolmar, PhoenixBound and Catador** — the optional [fast-door timer hook](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/redux/fast_doors.ccs), adapted as an extra Companion QoL feature. It is commented out in upstream's pinned `main.ccs`; its inclusion here is a Companion choice.

- **CoilSnake ExpandedTablesModule and pointer utility contributors** — [relocated PSI table references](https://github.com/pk-hack/CoilSnake/blob/346cfc753644bc3703b6fc4eaa0a5d6bdcb9bb4a/coilsnake/modules/eb/ExpandedTablesModule.py) guide the corrected PSI-name conversion.
- [TypeSafe Jev](https://docs.typesafe.ai/primitives/choice) — optional developer gameplay decisions through the TypeSafe API. The QA runner supplies bounded ordinary inputs and native observations; TypeSafe is not needed to play the game.

## Companion app icon

The original red-cap planet emblem was created for Companion with the built-in OpenAI image-generation tool and exported to Windows ICO using [Pillow](https://github.com/python-pillow/Pillow). It is custom launcher artwork. Source artwork, the full prompt and conversion instructions are in [Companion/Assets](Companion/Assets/README.md). It uses no extracted ROM art or official game logo.

## Development reference testing

- [Retro Porting Toolkit](https://retroportingtoolkit.com/docs) — source-backed audit and independent co-simulation guidance. This project does not claim full toolkit frame alignment from its selected function comparisons.
- [atonamy/mesen-agent](https://github.com/atonamy/mesen-agent) and [SourMesen/Mesen2](https://github.com/SourMesen/Mesen2) — development-only original SNES machine-code reference execution. The GPL tool and its license remain local; the player ZIP does not include an emulator. [Pinned tool provenance](research/mesen-agent-provenance.json).
- Herringway's original collision, arithmetic and text assembly and the pinned MaternalBound contributors' keyboard, battle UI and reset scripts — the sources against which these native corrections are reviewed. Their existing project/file credits remain applicable.

## Companion work

The Companion application, native PC option integration, packaging, Story Shuffle v3, recovery workflow, validation tooling and documentation were assembled for Carl Prewitt Jr.’s native PC edition with OpenAI Codex assistance. Generated work was reviewed, built and tested locally; upstream authorship remains as listed above.

Credits identify provenance; they do not grant redistribution permission. Original Companion, GPL adaptation, native-foundation and dependency licensing are separate. The combined release's unresolved terms are recorded in [LEGAL.md](LEGAL.md).

If a material credit is missing or inaccurate, open an issue with the project/file and requested correction.
