# Linux, macOS and Android previews

These builds live on `ports/multiplatform-preview`. Windows dev.33 remains the stable release and keeps its Windows Forms launcher, renderer and installation paths. Preview builds use their own data and never replace a Windows installation.

## What is included

Linux x64, Apple Silicon macOS and Intel macOS use the existing C/SDL2 game core with a portable Avalonia launcher. Android ARM64 phones and x64 emulators use that same game core with SDL's Android activity and touch controls. The portable launchers share the existing settings, Story Shuffle v4, progression checks, content profiles and save recovery code with Windows.

The launchers include Original/Redux selection, display presets, widescreen, built-in display effects, HQ/MSU music settings, gameplay options, controller/keyboard mapping, seed generation and recipe import, verified backup recovery, phone-save transfer and settings export. Desktop packages include Original and Redux ROM conversion helpers. Android imports privately generated asset packs; converting a ROM on the phone is not available yet.

External Slang shader presets are currently Windows-only. Built-in scanlines, color grading, filtering and depth effects are available in these previews. macOS packages have an ad-hoc signature, but no Apple Developer ID signing or notarization. iOS is outside this preview.

## Desktop setup

1. Extract the archive. On Linux launch `EarthBoundCompanion.Portable` from its folder and keep `Game` beside it. On macOS 12+ open **EarthBound Companion Preview.app** from Finder.
2. Select **Game & setup**, then **Set up Original from ROM** and choose your clean USA EarthBound ROM. To use Redux, build Original first, then **Build Redux from ROM**. Alternatively import packs prepared by your own existing Companion installation.
3. Select Original or Redux and press **Play**. Story Shuffle seeds are generated under **Story Shuffle** and keep their own saves.

Linux needs a desktop session and normal X11/OpenGL/fontconfig/audio libraries. On macOS use Finder's explicit Open command if Gatekeeper blocks the unnotarized preview. A trusted local build is also supported; do not disable system security globally.

Privately prepared packs come from `Game/assets.pak` for Original and `Profiles/maternalbound-redux-897d0083/assets.pak` for Redux. Import both if you want Redux's optional Original title presentation. Do not post ROMs or generated packs publicly.

Desktop preview data is stored in `EarthBoundCompanionPreview` beneath the operating system's local application data directory. The launcher displays its exact path. Executables stay in the extracted package while saves, settings and content profiles stay in the private data folder. The Settings shortcut pauses the game and activates the launcher; **Save settings / return to game** applies changes and resumes.

## Android setup

Install the ARM64 APK on a compatible Android 8.0+ device. The x64 APK is supplied for emulator testing. The preview application ID is `org.earthbound.companion.preview`. APK updates use a persistent project signing key.

1. Transfer your privately prepared Original or supported Redux pack to your device.
2. In **Game & setup**, import the matching `assets.pak`, select the edition and press **Play**.
3. Touch controls include diagonals, sprint (Y), A/B/X, L/R, Start/Select, quick Save/Load, Fast and Settings. A Bluetooth or USB controller can also be used. Save/Load uses the selected quick-save slot.
4. The touch Settings button opens the launcher. **Save settings / return to game** resumes the existing game.

A background event requests a quick save on the game thread and pauses game logic. Back requests a checkpoint and clean game exit. If SDL reports a lost render device, the game requests a checkpoint and returns to the launcher rather than continuing with invalid textures. Sudden termination cannot guarantee a new quick save. Phone lifecycle, touch layout, controllers and actual gameplay still require device testing.

Android data stays in app-private storage. **Saves & mods** exports/imports through the system file picker. Export saves before uninstalling; removing the app removes its private data.

## Save transfer

Choose the matching edition and seed before transferring an 8192-byte `earthbound.srm` phone save. Raw saves do not identify their story or seed, so the user must choose correctly. Imports back up previous data first. Press **Play** and load the normal in-game save after importing; an older quick save is a separate snapshot.

Verified Companion backup ZIPs check the adventure and asset identity before restoring the phone save. Quick saves are restricted to their exact engine build and are not the cross-platform transfer format. Never overwrite an owner's newest save for a test.

## What has and has not been tested

Builds, ROM-free input/MSU checks, settings ABI/round trips, path isolation, synthetic phone-save backup/recovery and launcher startup are covered by automation. Android emulator checks launch the managed UI and SDL native ROM-free selftest. Those checks do not verify the game campaign, audio playback quality, real controllers, physical phones or long sessions. Community reports remain necessary; see [PLATFORM-TESTING.md](PLATFORM-TESTING.md) for short focused tests.

The Windows launcher is compiled as a guard. Local tests additionally use copies and temporary sessions to check Original/Redux native launches and deterministic seed recipes. No new-platform full playthrough is claimed. Published build results identify the checks that actually passed.

## Reproducing builds

`scripts/prepare_port_sources.py` prepares a fresh pinned native checkout and a SHA-256-checked SDL 2.32.10 archive. It refuses to reset an existing source folder. Apply `patches/native-portable.patch` after the dev.33 `native-companion.patch`. For the Android launcher, copy the verified SDL archive's `android-project/app/src/main/java/org/libsdl/app/*.java` into `Ports/AndroidManaged/Java` before publishing; those generated bridge files are intentionally ignored by Git. `.github/workflows/platform-preview.yml` builds previews without ROMs, generated packs, music or personal saves, using standard public-repository runners.

Portable code retains its SPDX notices; the repository's license scopes and existing upstream notices still apply. SDL is zlib, Avalonia is MIT, Inter is OFL, and LakeSnes/SkiaSharp/HarfBuzz notices accompany packages. Pinned legacy CCScript does not supply a standalone compiler license declaration; the helper includes its source provenance and bundled filesystem notice rather than inventing a license.
