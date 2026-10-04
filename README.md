# EarthBound Companion

**A native Windows adaptation of EarthBound that is now evolving into a MaternalBound Redux PC edition with HD and ultrawide output, native MSU music, PC settings, quality-of-life options, mod profiles, and a progression-conscious randomizer.**

> [!WARNING]
> **Full MaternalBound compatibility is still under development.** The older v0.4.0 preview contains original EarthBound. The Redux development edition compiles the pinned upstream source from your clean ROM, converts it into a native pack, and uses separate story and randomizer saves. Opening, shops, equipment, all 11 Tools, title/narration and ending fixtures pass. A complete story or randomized playthrough remains unverified. See [MATERNALBOUND-NATIVE.md](MATERNALBOUND-NATIVE.md).

The target is one polished PC edition: MaternalBound Redux's restored writing, art, fixes, and presentation running through the native engine alongside Companion's display, audio, input, save, QoL, mod, and randomizer features. Story Shuffle v3 binds every seed to the exact selected game version, asset hash, progression policy, and save namespace. Both the original and the pinned Redux packs have content-specific protection policies; unknown packs cannot be randomized.

> [!IMPORTANT]
> This project does **not** contain an EarthBound ROM, extracted Nintendo assets, soundtrack audio or saves. The documentation includes clearly labeled development screenshots. You must provide your own legally obtained clean **EarthBound (USA)** ROM. Companion verifies it and builds the required native data locally. We do not condone piracy.

[Download private test builds](https://github.com/rages4calm/earthbound-companion/releases) · [MaternalBound native port status](MATERNALBOUND-NATIVE.md) · [Read the randomizer rules](RANDOMIZER.md) · [See research and compatibility](RESEARCH.md) · [Credits](CREDITS.md)

## Companion at a glance

These are real captures from the ROM-free v0.5 development launcher before game-data setup. They contain no extracted game artwork or gameplay screenshots.

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
    <td width="50%"><img src="docs/images/solo-play.png" alt="Solo Play and first-run ROM setup"></td>
    <td width="50%"><img src="docs/images/mods-saves.png" alt="Native mod profiles, asset packs, saves and recovery"></td>
  </tr>
  <tr>
    <td align="center"><strong>Guided ROM setup and Solo Play</strong></td>
    <td align="center"><strong>Native profiles, asset packs and save recovery</strong></td>
  </tr>
</table>

The [Redux port page](MATERNALBOUND-NATIVE.md#development-captures) also shows actual native Tools, equipment and cast renders.

## What this is

EarthBound Companion packages a native x64 C/SDL2 game build with a self-contained Windows settings application. Gameplay executes as compiled native code. The project still uses software implementations of the original graphics and audio subsystems where required for accuracy; “native” does not mean the original game has been replaced with a new engine or remade art.

The player-facing setup follows the same asset separation used by established decompilation ports: the downloadable package supplies code and tools, while the player supplies the game. The ROM is read locally, never modified, retained, or uploaded.

## Quick start

1. Download the Redux development package from [Releases](https://github.com/rages4calm/earthbound-companion/releases) for experimental MaternalBound testing, or v0.4.0 for the older original-story preview.
2. Extract the complete ZIP to a normal folder.
3. Run **EarthBound Companion.exe**.
4. Select your clean EarthBound (USA) `.sfc` or `.smc` ROM.
5. Leave **Install the complete MSU soundtrack** checked for the full audio setup.
6. When setup finishes, choose **Play EarthBound**. The Redux package identifies itself as a development profile. **Redux Port → Use original EarthBound** returns to the original story without changing either edition's saves.

The application accepts the clean 3 MiB USA ROM, with or without a 512-byte copier header. A different revision or modified ROM is rejected before extraction.

## PC features

| Area | Included |
|---|---|
| Display | 720p, 1080p, 1440p, 4K, 3440×1440; borderless fullscreen; 4:3, 16:9 and 21:9 |
| Rendering | Crisp pixels, Scale2x and bilinear output; integer scaling; optional color grade, scanlines and miniature depth effect |
| World view | Expanded native scenery and adjustable field of view; fixed artwork keeps its designed framing |
| Input | Keyboard and controller rebinding, analog movement, hotplug, deadzone control and Nintendo/Xbox face-label layouts |
| Quality of life | Sprint, quick dialogue, optional homesickness and Dad-call suppression, reward multipliers and fast-forward |
| Saves | Normal phone saves, five crash-safe quick-save banks, per-session backups and guided recovery |
| Tools | F1 settings, F6/F7 quick save/load, F9 pause, F11 fullscreen, F12 screenshots and FPS display |

## Native MSU soundtrack

First-run setup can download all 164 PCM tracks from [ShadowOne333’s EarthBound MSU-1 pack](https://archive.org/details/earthbound-msu-1-pack). Each file is checked against the embedded size and checksum manifest before it is installed. Interrupted setup keeps completed tracks; **Audio → Install / repair soundtrack** resumes and verifies the collection. Missing or invalid files fall back to the original SPC soundtrack.

The PCM files are not stored in this repository or the release ZIP. See [CREDITS.md](CREDITS.md) for provenance.

## Story Shuffle v3

Companion includes its own native randomizer for replayable adventures:

- eligible optional NPC gifts;
- shop inventory;
- ordinary enemy stats and drops;
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

The repository source tree intentionally does not vendor the unlicensed upstream EarthBound source. Bootstrap pins the exact revision used by the release:

```powershell
git clone https://github.com/rages4calm/earthbound-companion.git
cd earthbound-companion
powershell -ExecutionPolicy Bypass -File .\scripts\Bootstrap-Native.ps1
```

You will need a Windows x64 C toolchain, CMake, Ninja, SDL2 development files, Python 3, PyInstaller, and the .NET 8 SDK. Put your own ROM at `ROM\EarthBound (USA).sfc`; `ROM/` is permanently ignored by Git. The checked-in scripts document the release build flow. Generated ROM data, build outputs, soundtracks, saves and screenshots remain untracked.

## Legal and project status

EarthBound and Mother 2 are trademarks and copyrighted works of their respective owners. This is an unofficial fan project, not affiliated with or endorsed by Nintendo, Shigesato Itoi, APE, HAL Laboratory, or any rights holder. No ownership of the original game is claimed.

The upstream EarthBound repositories used for the native foundation are public but currently publish no top-level license. Public visibility is not a redistribution license. For that reason this repository records the upstream revision and our patch instead of relicensing or vendoring their full tree. The initial binary release is kept private for invited testing while permission is clarified. See [LEGAL.md](LEGAL.md) and [CREDITS.md](CREDITS.md).

## Verification

The v0.4.0 package passed clean-ZIP first-run extraction, exact asset-pack comparison, Companion self-tests, seed safety validation, and all 164 installed MSU checks. The archive was scanned and contained zero ROM, `.pak`, PCM, save, state or screenshot files. The Redux development ZIP also passed clean setup from a headered USA ROM with no Python on PATH, a real corrupt-track download/repair and verification of all 164 MSU files, exact original/Redux pack reproduction, native story and randomized openings, and profile save-isolation checks. Story Shuffle v3 passes 1,000 seeds and all 30 option combinations for each edition. Exact hashes and coverage limits are in [validation/](validation/).

Issues and contributions should never attach ROMs, extracted asset packs, saves containing embedded game data, or soundtrack files. Documentation captures are labeled with their tested development scope.
