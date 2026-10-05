<img src="Companion/Assets/earthbound-companion.png" width="88" height="88" alt="EarthBound Companion red-cap planet icon">

# EarthBound Companion

**EarthBound for Windows, with a native MaternalBound Redux adaptation, widescreen and ultrawide scenery, 1080p–4K output, MSU music, PC controls, save recovery and Story Shuffle v3.**

> [!WARNING]
> **Current release: `v0.5.0-redux-dev.9`, an experimental conversion. Full MaternalBound Redux compatibility is not finished.** The older v0.4.0 preview contains original EarthBound. The Redux development edition compiles the pinned upstream source from your clean ROM, converts it into a native pack, and implements explicit native gameplay adaptations. Opening gameplay, shops, equipment, all 11 Tools, title/narration and ending fixtures pass. A complete story or randomized playthrough, all combat combinations and every story/music transition remain unverified. See [MATERNALBOUND-NATIVE.md](MATERNALBOUND-NATIVE.md).

The target is one polished PC edition: MaternalBound Redux's restored writing, art, fixes, and presentation running through the native engine alongside Companion's display, audio, input, save, QoL, mod, and randomizer features. Story Shuffle v3 binds every seed to the exact selected game version, asset hash, progression policy, and save namespace. Both the original and the pinned Redux packs have content-specific protection policies; unknown packs cannot be randomized.

> [!IMPORTANT]
> This project does **not** contain an EarthBound ROM, extracted Nintendo assets, soundtrack audio or saves. The documentation includes clearly labeled development screenshots. You must provide your own legally obtained clean **EarthBound (USA)** ROM. Companion verifies it and builds the required native data locally. We do not condone piracy.

[Latest tester release](https://github.com/rages4calm/earthbound-companion/releases/tag/v0.5.0-redux-dev.9) · [MaternalBound native port status](MATERNALBOUND-NATIVE.md) · [Randomizer rules](RANDOMIZER.md) · [Research and compatibility](RESEARCH.md) · [Credits](CREDITS.md) · [Source lineage](UPSTREAM.md)

The ninth Redux development build fixes a shared encounter race after instant victories, bicycle music fading away after combat, and unread sound effects being overwritten between audio callbacks. The contact checks cover all 230 non-placeholder enemy records in both editions; audio checks cover original/SPC and MSU playback. These are targeted regressions, not a completed playthrough. [Fixes and test boundaries](docs/RELIABILITY-dev9.md).

The launcher retains the red-cap planet application icon, Play and Game Mode tab names, and clear descriptions for all eight tabs. The corrected content pack, quick-save format 16 and story/seed identities are unchanged. [Icon source and generation prompt](Companion/Assets/README.md).

The seventh Redux development build checks all **177 placed containers in each edition** against their source loot, opened flags, text mappings and placements. All 698 prepared native reward/full-inventory cases pass, including repeat-opening protection and collecting rejected gifts after freeing space. It preserves the two source-defined empty containers and Redux's documented Broken iron → Broken gadget replacement. These are exhaustive catalog/reward fixtures, not a walk through every room. [Coverage and method](docs/PRESENT-AUDIT.md).

Four additional scripted reward containers—Fly Honey and the three ending letters—also pass their actual reward, repeat and full-inventory paths in both editions. That adds 16 cases, for 714 reward cases total. Eight scripted-battle entries and eight no-dialogue scenery interactions pass as well; battle victories and story appearance conditions remain outside this fixture coverage. Representative player/observer replays match at all 153 serialized checkpoints.

The launcher now explains all eight left-hand tabs with visible descriptions and fuller hover/accessibility help. Story play, seed play, edition switching and save recovery are easier to find. The dev.7 launcher update retained the dev.6 engine. Dev.9 now includes the shared encounter and audio fixes above while preserving content and save identities.

The sixth Redux development build connects the three rest-script stamina hooks: hotel recovery, full recovery and hot springs now refill running stamina. Twelve prepared four-member cases preserve each rest type’s health/status rules; the previous engine reproduced the missing reset. Twenty-four exact player/observer checkpoints and six real VM jump/continuation checks pass. The corrected pack, state format 16 and seed identities remain unchanged. These fixtures do not establish every rest location or a completed playthrough.

A follow-up [source/data review](research/redux-control-and-battle-hooks-review.json) checks 29 active literal writes across controls, terrain speed, expanded Spy, PSI stat buffs and colored cast text. On the same dev.6 engine, a prepared Spy battle displays the target’s Offense 5, Defense 3 and Speed 77, awards one Cookie to Jeff and returns to the battle menu. All 21 cold-restored input checkpoints match between player and observer builds. These checks do not establish every enemy, map or story branch.

The fifth Redux development build fixes present rewards being lost by the deferred Talk/Check window. Two unopened Giant Step presents reproduce the failure in dev.4 and now deliver the exact items from the pinned source; repeat checks cannot duplicate the rewards. A prepared cash-gift case also passes. No player saves are modified by these tests. The pack and quick-save format remain unchanged. Already opened presents are not retroactively granted items.

The fourth Redux development build corrects the native `CC 1D 15` argument width: the upstream fix stores a 16-bit value before multiplying, while the former C handler retained high bits. Twenty-five actual dispatcher cases pass after reproducing eight failures in the previous handler. The [36 active bugfix reviews](research/redux-active-bugfix-review.json) distinguish native adaptations, platform differences and remaining gameplay tests. This build also retains the dev.3 fixes for stranded empty Talk/Check windows, cutscene masks covering the Starman Junior battle UI, cold quick-save restores during stat-growth messages, and Redux story launch/save-backup handling. It also reads the relocated PSI-name table correctly and rebuilds the PSI menu in front of the pause menu when loading an older checkpoint. Actual Lifeup input heals Ness and consumes 5 PP. Copied player saves passed the Starman fight, victory and following Buzz Buzz dialogue, plus empty Talk/Check → natural Onett combat → victory and roaming, with ordinary inputs. [Jev-assisted development testing](JEV-QA.md) also completes normal City Hall navigation, the guard conversation and Mayor Pirkle’s Shack Key award from a copied post-Frank save. Testing is bounded and isolated from player saves; it has not completed the whole game.

Invited testers need repository access or a ZIP supplied by the project owner. The repository and combined binary releases currently remain private while native-engine redistribution terms are clarified. Private visibility is a precaution, not a redistribution license.

## Companion at a glance

These are real captures from the ROM-free dev.8 development launcher before game-data setup. They contain no extracted game artwork or gameplay screenshots.

<table>
  <tr>
    <td width="50%"><img src="docs/images/redux-port.png" alt="MaternalBound Redux native port status"></td>
    <td width="50%"><img src="docs/images/story-shuffle-v3.png" alt="Story Shuffle v3 randomizer options"></td>
  </tr>
  <tr>
    <td align="center"><strong>MaternalBound Redux native-port status</strong></td>
    <td align="center"><strong>Story Shuffle v3 content-safe randomizer</strong></td>
  </tr>
  <tr>
    <td width="50%"><img src="docs/images/display-settings.png" alt="Resolution, widescreen and rendering settings"></td>
    <td width="50%"><img src="docs/images/msu-audio.png" alt="Native MSU soundtrack controls"></td>
  </tr>
  <tr>
    <td align="center"><strong>HD, widescreen and rendering controls</strong></td>
    <td align="center"><strong>Native MSU audio setup</strong></td>
  </tr>
  <tr>
    <td width="50%"><img src="docs/images/solo-play.png" alt="Play and first-run ROM setup"></td>
    <td width="50%"><img src="docs/images/mods-saves.png" alt="Native mod profiles, asset packs, saves and recovery"></td>
  </tr>
  <tr>
    <td align="center"><strong>Guided ROM setup and Play</strong></td>
    <td align="center"><strong>Native profiles, asset packs and save recovery</strong></td>
  </tr>
</table>

The [Redux port page](MATERNALBOUND-NATIVE.md#development-captures) also shows actual native gameplay, Tools, equipment and cast renders. The latest packaged engine passes normal-button walking through the house, doors and stairs, Mom's dialogue, the clothes-change event and initial outdoor movement, with fresh-process restores between checkpoints. This passes for both Redux story and a generated seed.

![Native Redux opening dialogue at 1920×1080](docs/images/native-redux-mom-1080p.png)

![Ordinary Mayor Pirkle quest award in the native dev.4 engine](docs/images/native-redux-mayor-key-dev4.png)

This capture replays the mayor’s actual Shack Key award using the production engine and ordinary recorded inputs. It is a story checkpoint, not a completed playthrough.

This 1080p capture uses locally supplied game data. It documents the development build; it is not proof of complete story compatibility.

![Native dev.5 present reward replay at 1920×1080](docs/images/native-redux-present-dev5.png)

This production-engine capture shows the real present reward after the dev.5 fix. Testing also checks inventory, the opened flag and repeat protection.

![Native dev.6 expanded Spy cold render at 1920×1080](docs/images/native-redux-spy-dev6.png)

This unedited production-engine capture restores the added Speed message from the prepared four-member battle fixture. The debug character names and stats are fixture inputs; this is not ordinary story progress.

## What this is

EarthBound Companion packages a native x64 C/SDL2 game build with a self-contained Windows settings application. Gameplay executes as compiled native code; the optional SNES main-CPU verification emulator is disabled. Software implementations of the original graphics and SPC/DSP audio subsystems remain for rendering and sound.

The player-facing setup separates code/tools from player-supplied game data. Setup reads the owner's ROM locally and never modifies or uploads it. Conversion creates local working data and generated ROMs, removed after successful setup. Failed builds can retain private diagnostics and working files; those folders must not be uploaded.

**We still use the upstream native engine. This is an adaptation of that foundation, not a ground-up replacement.** The source lineage is [Herringway/ebsrc](https://github.com/Herringway/ebsrc) → [BrianPugh/earthbound](https://github.com/BrianPugh/earthbound) → [seanstaggsQU/earthboundRecompLinux2026](https://github.com/seanstaggsQU/earthboundRecompLinux2026) → Companion's pinned patch. Our launcher, Redux converters/adapters, PC integration, fixes, randomizer and recovery build on that work. Adding these features does not erase upstream authorship or licensing obligations. [Verified provenance](UPSTREAM.md) · [Full credits](CREDITS.md).

## Quick start

1. Download the Redux development package from [Releases](https://github.com/rages4calm/earthbound-companion/releases) for experimental MaternalBound testing, or v0.4.0 for the older original-story preview.
2. Extract the complete ZIP to a normal folder.
3. Run **EarthBound Companion.exe**.
4. Select your clean EarthBound (USA) `.sfc` or `.smc` ROM.
5. Leave **Install the complete MSU soundtrack** checked for enhanced music, or clear it to use SPC music. Internet access is needed for the pinned source and soundtrack downloads; testers need no Python, Git, .NET installation or compiler.
6. When setup finishes, choose **Play EarthBound**. The Redux package identifies itself as a development profile. **Game Mode → Use original EarthBound** returns to the original story without changing either edition's saves.

The application accepts the clean 3 MiB USA ROM, with or without a 512-byte copier header. A different revision or modified ROM is rejected before extraction.

For dev.3 through dev.8 → dev.9, close the game and launcher, back up the existing installation, then extract the new package over it. Keep `Profiles`, `UserData` and `msu`. The pack hash and quick-save format 16 are unchanged, so existing corrected-pack story and seed saves keep their identities.

For dev.2 → dev.9, extract to a fresh folder and build Redux from your ROM. Then choose **Game Mode → Import dev.2 story saves** and select the previous installation folder. This checked, names-only update copies phone and format-16 quick saves into empty destination saves; it preserves the previous installation and refuses other content pairs. Randomizer seeds keep their original content and save folders.

Switching editions selects a separate adventure; it does not convert an existing playthrough. Normal phone saves are the migration path between engine builds. Development quick saves require a compatible engine and state format.

## Where to go in the launcher

| Tab | Use it for |
|---|---|
| Play | Start or resume the normal story in the selected edition; choose a presentation/convenience preset. |
| Randomizer | Choose shuffle options, generate and replay seeds, open spoiler logs and manage each seed's separate saves. |
| Game Mode | Build/select the MaternalBound development edition, review coverage or switch back to original EarthBound. |
| Display | Resolution, fullscreen, widescreen framing, pixel filtering and visual effects. |
| Audio | MSU soundtrack selection/installation, music and game volume, and soundtrack credits. |
| Gameplay | Sprint, quick dialogue, homesickness/call settings, battle rewards and quick-save bank. |
| Controls | Keyboard/controller bindings, stick deadzone and face-button labels. |
| Mods & saves | Settings profiles, compatible native asset packs, and story-save backup/restore. |

Click **Apply settings** to save option changes. Game Mode selects the story edition played from Play. Randomizer's seed library manages randomized adventures and their saves.

## PC features

| Area | Included |
|---|---|
| Display | 720p, 1080p, 1440p, 4K, 3440×1440; borderless fullscreen; 4:3, 16:9 and 21:9 |
| Rendering | Crisp pixels, Scale2x and bilinear output; integer scaling; optional color grade, scanlines and miniature depth effect |
| World view | Expanded native scenery and adjustable field of view; fixed artwork keeps its designed framing |
| Input | Keyboard and controller rebinding, analog movement, hotplug, deadzone control and Nintendo/Xbox face-label layouts |
| Quality of life | Sprint, quick dialogue, optional homesickness and Dad-reminder suppression, reward multipliers, fast-forward and shared key-item storage |
| Redux gameplay | Adapted controls/stamina, six-letter names, ten-letter favorite food, Keys/Jeff's Tools menus, inventory-free battle Tools, expanded equipment/resistance previews and native combat/item fixes |
| Doors | Faster entrance/exit transitions in the Redux profile, added by Companion from an optional upstream hook; original-profile timing stays unchanged |
| Saves | Normal phone saves, five crash-safe quick-save banks, per-session backups and guided recovery |
| Tools | F1 settings, F6/F7 quick save/load, F9 pause, F11 fullscreen, F12 screenshots and FPS display |

**HD means high-resolution output and enhanced presentation.** Converted pixel artwork is used; a replacement hand-drawn HD art pack is not included. Widescreen expands the native world view within the renderer's limits, rather than merely stretching the original picture. Physical controller play and every display/DPI combination have not been fully verified. Mod profiles tune supported native options; arbitrary ROM patches require explicit native adaptations.

## Native MSU soundtrack

First-run setup can download all 164 PCM tracks from [ShadowOne333’s EarthBound MSU-1 pack](https://archive.org/details/earthbound-msu-1-pack). Each file is checked against the embedded size and checksum manifest before it is installed. Interrupted setup keeps completed tracks; **Audio → Install / repair soundtrack** resumes and verifies the collection. Missing or invalid files fall back to the selected edition's SPC soundtrack. Native checks cover all 164 PCM loop/end boundaries, the eight Sound Stone transitions and retained SPC sound effects; complete listening and story-transition coverage remain unverified.

The PCM files are not stored in this repository or the release ZIP. See [CREDITS.md](CREDITS.md) for provenance.

## Story Shuffle v3

Companion includes its own native randomizer for replayable adventures:

- **Gift contents:** eligible optional gifts change within their item category; protected quest/trade sources stay fixed.
- **Shop stock:** eligible optional stock changes within its type; protected items, each shop's first slot and empty/ineligible slots stay fixed. Item prices are unchanged.
- **Enemy stats:** ordinary-enemy HP, offense, defense and speed vary within bounded ranges; bosses and scripted enemies stay fixed.
- **Enemy drops:** eligible ordinary-enemy loot changes within its type. Drop chances, empty drops and protected/boss/scripted drops stay fixed.
- Balanced and Surprise modes;
- deterministic seed recipes;
- isolated saves, screenshots and recovery backups for every seed.

The generator keeps 78 identified quest/trade items and their original sources fixed, preserves 52 scripted-battle records, and leaves maps, doors, routes, scripts, bosses, prices and starting items unchanged. Independent guards run at generation and before launch. Version 3 also isolates game editions: content ID, exact asset hash, safety policy, seed identity, and save folder must agree. This protects the audited original-story dependencies; it is not proof of every possible full playthrough.

The pinned Redux profile separately protects 110 items and 84 enemy records. Its audit covers 64,360 decoded operations, scripted encounter groups and the expanded 69-shop table. Independent generation checks pass across 1,000 seeds and all 30 option combinations for each edition. The Redux enemy-AI footer, routes, scripts and protected sources remain intact. This is conservative story preservation, not a randomized-world logic solver or proof of every playthrough.

This generator is inspired by the EarthBound randomizer community but does not claim seed parity with [earthbound.app](https://earthbound.app/) or [stochaztic/eb-randomizer](https://github.com/stochaztic/eb-randomizer). Ancient Cave, Open mode and Keysanity are not implemented. See [RANDOMIZER.md](RANDOMIZER.md).

## Current boundaries

- A complete start-to-ending playthrough of this specific build has not yet been verified.
- [MaternalBound Redux](https://github.com/ShadowOne333/MaternalBound-Redux) is being adapted from a pinned active-source snapshot, rather than the official v1.1 BPS release. The checkpoint converts 7,397 dialogue spans, implements 17 routine adapters, passes 81 VM command checks and 48,640 AI-selector turns, and resolves all 898 movement-script roots. Title scenes, 191 SPC tracks, 68 PSI effects, native shops/equipment, all 11 battle Tools and all 32 photo-credit branches have bounded checks. Full story playthroughs, later interactions, all combat-effect combinations and complete music-transition coverage remain unverified. See the [detailed coverage](MATERNALBOUND-NATIVE.md).
- Arbitrary IPS, BPS and EBP patches cannot be loaded as native mods; their game-code changes require explicit ports.
- The release is a Windows x64 private test build. Bug reports should include the active edition or seed session's `game.log` and a normal phone save when possible.

## Source layout

| Path | Purpose |
|---|---|
| `Companion/` | .NET 8 Windows Forms launcher, settings, setup, backups and Story Shuffle source |
| `patches/native-companion.patch` | Exact native-engine changes against the pinned upstream commit |
| `scripts/Bootstrap-Native.ps1` | Fetches the upstream source and applies that patch |
| `scripts/` | Asset registry, progression audit, MSU verification and package-audit tools |
| `Mods/` | ROM-free example `.ebmod.json` profiles |
| `Licenses/` | Notices shipped with used dependencies |
| `validation/` | Bounded build, package and gameplay evidence |

## Building from source

The repository records the native foundation as a pin and patch rather than vendoring its entire tree. Bootstrap fetches the exact revision used by the release:

```powershell
git clone https://github.com/rages4calm/earthbound-companion.git
cd earthbound-companion
powershell -ExecutionPolicy Bypass -File .\scripts\Bootstrap-Native.ps1
```

Developers need a Windows x64 C toolchain, CMake/Ninja, SDL2 development files, Python and the .NET 8 SDK. Runtime builds use `EB_RUNTIME_ASSETS=ON`, `EB_ENABLE_VERIFY=OFF` and `EB_ENABLE_AUDIO=ON`. Redux setup-helper builds additionally require the pinned CoilSnake/CCScript toolchain and PyInstaller; see [the conversion instructions](MATERNALBOUND-NATIVE.md#reproducing-development-conversion).

The checked-in rebuild/package scripts record the current workspace's tool paths; they are not a one-command provisioner for a fresh machine. Some historical commands refer to local `tools/` files, while published scripts live in `scripts/`. Put your own ROM at `ROM\EarthBound (USA).sfc`; `ROM/` is ignored by Git. Generated game data, build outputs, soundtracks, saves and runtime screenshots remain untracked; the labeled documentation screenshots are checked in.

## Legal and project status

EarthBound and Mother 2 are trademarks and copyrighted works of their respective owners. This is an unofficial fan project, not affiliated with or endorsed by Nintendo, Shigesato Itoi, APE, HAL Laboratory, or any rights holder. No ownership of the original game is claimed.

The October 4 review found no repository-wide redistribution grant in the reviewed native-foundation README/license files; GitHub also detects no top-level license. Third-party library licenses cover those libraries, not the whole engine. Public visibility and credits do not supply missing permission. [Review record](validation/upstream-license-provenance.json) · [GitHub's licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).

MaternalBound Redux and its adaptations have separate GPLv3 terms. Those terms do not license the native foundation. The combined engine's distribution and GPL compatibility need clarification before a public combined release; private visibility does not settle either issue. Original Companion files have their own [limited-scope license](LICENSE.md). A patch or compiled executable can still contain upstream material even when the full source tree is not vendored. See [LEGAL.md](LEGAL.md) and [CREDITS.md](CREDITS.md). No disclaimer claims to grant game rights or guarantee legal protection.

## Verification

The v0.4.0 package passed clean-ZIP first-run extraction, exact asset-pack comparison, Companion self-tests, seed safety validation, and all 164 installed MSU checks. The archive was scanned and contained zero ROM, `.pak`, PCM, save, state or screenshot files. The Redux development ZIP also passed clean setup from a headered USA ROM with no Python on PATH, a real corrupt-track download/repair and verification of all 164 MSU files, exact original/Redux pack reproduction, native story and randomized openings, and profile save-isolation checks. Story Shuffle v3 passes 1,000 seeds and all 30 option combinations for each edition. Exact hashes and coverage limits are in [validation/](validation/).

Issues and contributions should never attach ROMs, extracted asset packs, saves containing embedded game data, or soundtrack files. Documentation captures are labeled with their tested development scope.
