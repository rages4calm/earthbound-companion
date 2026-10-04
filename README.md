# EarthBound Companion

**A ROM-free native Windows PC edition of EarthBound with a guided launcher, modern display options, quality-of-life controls, native MSU music, and a progression-conscious randomizer.**

> [!IMPORTANT]
> This project does **not** contain an EarthBound ROM, extracted Nintendo assets, soundtrack audio, saves, or screenshots from the game. You must provide your own legally obtained clean **EarthBound (USA)** ROM. Companion verifies it and builds the required native data locally. We do not condone piracy.

[Download the latest private test build](https://github.com/rages4calm/earthbound-companion/releases/latest) · [Read the randomizer rules](RANDOMIZER.md) · [See research and compatibility](RESEARCH.md) · [Credits](CREDITS.md)

## What this is

EarthBound Companion packages a native x64 C/SDL2 game build with a self-contained Windows settings application. Gameplay executes as compiled native code. The project still uses software implementations of the original graphics and audio subsystems where required for accuracy; “native” does not mean the original game has been replaced with a new engine or remade art.

The player-facing setup follows the same asset separation used by established decompilation ports: the downloadable package supplies code and tools, while the player supplies the game. The ROM is read locally, never modified, retained, or uploaded.

## Quick start

1. Download `EarthBound-Companion-Tester-v0.4.0.zip` from [Releases](https://github.com/rages4calm/earthbound-companion/releases).
2. Extract the complete ZIP to a normal folder.
3. Run **EarthBound Companion.exe**.
4. Select your clean EarthBound (USA) `.sfc` or `.smc` ROM.
5. Leave **Install the complete MSU soundtrack** checked for the full audio setup.
6. When setup finishes, choose **Play EarthBound**.

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

## Story Shuffle v2

Companion includes its own native randomizer for replayable original-story runs:

- eligible optional NPC gifts;
- shop inventory;
- ordinary enemy stats and drops;
- Balanced and Surprise modes;
- deterministic seed recipes;
- isolated saves, screenshots and recovery backups for every seed.

The generator keeps 78 identified quest/trade items and their original sources fixed, preserves 52 scripted-battle records, and leaves maps, doors, routes, scripts, bosses, prices and starting items unchanged. Independent guards run at generation and before launch. This protects the audited original-story dependencies; it is not proof of every possible full playthrough.

This generator is inspired by the EarthBound randomizer community but does not claim seed parity with [earthbound.app](https://earthbound.app/) or [stochaztic/eb-randomizer](https://github.com/stochaztic/eb-randomizer). Ancient Cave, Open mode and Keysanity are not implemented. See [RANDOMIZER.md](RANDOMIZER.md).

## Current boundaries

- A complete start-to-ending playthrough of this specific build has not yet been verified.
- [MaternalBound Redux](https://github.com/ShadowOne333/MaternalBound-Redux) is researched and credited, but its ROM-side assembly and script changes have not been ported into the native C game.
- [RetroAchievements](https://github.com/RetroAchievements) integration is not currently implemented.
- Arbitrary IPS, BPS and EBP patches cannot be loaded as native mods; their game-code changes require explicit ports.
- The release is a Windows x64 private test build. Bug reports should include `UserData/game.log` and a normal phone save when possible.

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

The v0.4.0 package passed clean-ZIP first-run extraction, exact asset-pack comparison, Companion self-tests, seed safety validation, and all 164 installed MSU checks. The archive was scanned and contained zero ROM, `.pak`, PCM, save, state or screenshot files. Exact hashes and coverage limits are in [validation/TESTER-PACKAGE-REPORT.md](validation/TESTER-PACKAGE-REPORT.md).

Issues and contributions should never attach ROMs, extracted assets, copyrighted screenshots, saves containing embedded game data, or soundtrack files.
