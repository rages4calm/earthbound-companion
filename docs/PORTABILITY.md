# Linux, macOS and Android previews

[Windows 1.0.15](https://github.com/rages4calm/earthbound-companion/releases/latest) is the official Windows release; preview.26 supplies the shared dialogue, battle-render and lifecycle fixes on Linux, macOS and Android. These are platform preview
builds with the shared native game core and 46-achievement catalog. Windows retains its Windows Forms
launcher, renderer and installation paths. Previews use separate platform data
and never replace a Windows installation. [Achievements](ACHIEVEMENTS.md).

## What is included

Linux x64, Apple Silicon macOS and Intel macOS use the existing C/SDL2 game core with a portable Avalonia launcher. Android ARM64 phones and x64 emulators use that same game core with SDL's Android activity and touch controls. The portable launchers share the existing settings, Story Shuffle v4, progression checks, content profiles and save recovery code with Windows.

The launchers include Original/Redux selection, display presets, widescreen, built-in display effects, HQ/MSU music settings, gameplay options, controller/keyboard mapping, seed generation and recipe import, verified backup recovery, phone-save transfer and settings export. Desktop and Android can set up both editions from a clean USA ROM. Importing privately generated asset packs remains supported.

External Slang shader presets are currently Windows-only. Built-in scanlines, color grading, filtering and depth effects are available in these previews. macOS packages have an ad-hoc signature, but no Apple Developer ID signing or notarization. iOS is outside this preview.

## Desktop setup

1. Extract the archive. On Linux launch `EarthBoundCompanion.Portable` from its folder and keep `Game` beside it. On macOS 12+ open **EarthBound Companion Preview.app** from Finder.
2. Select **Game & setup**, then **Set up Original from ROM** and choose your clean USA EarthBound ROM. To use Redux, build Original first, then **Build Redux from ROM**. Alternatively import packs prepared by your own existing Companion installation.

**The import buttons are for an already generated `assets.pak`, not a ROM.**
If you have a `.sfc` or `.smc` ROM, use the ROM setup buttons above. Do not patch
it with Redux first; Companion builds Redux from the same clean USA ROM. Wait
for setup to finish, choose **Select Original** or **Select Redux**, then press
**Play**. If setup fails, report the displayed error before trying Play.
3. Select Original or Redux and press **Play**. Story Shuffle seeds are generated under **Story Shuffle** and keep their own saves.

The Linux binary is built on Ubuntu 24.04 and requires glibc 2.38 or newer, a desktop session and normal X11/OpenGL/fontconfig/audio libraries. Older distributions need a local build. If macOS blocks the unnotarized preview, first try opening the app, then use **System Settings > Privacy & Security > Open Anyway** for this app, following [Apple's instructions](https://support.apple.com/en-us/102445). A trusted local build is also supported; do not disable system security globally.

Privately prepared packs come from `Game/assets.pak` for Original and `Profiles/maternalbound-redux-897d0083/assets.pak` for Redux. Import both if you want Redux's optional Original title presentation. Do not post ROMs or generated packs publicly.

The Redux helper includes public HTTPS trust roots and compiles CCScript inputs in a fixed order. Source, base ROM and compiled ROM checksums remain mandatory. If compilation finishes but fails the audited ROM check, the failed `.partial` profile now includes `compiler-identity.json` with expected and actual checksums. Share that text and `compile-redux.log` when reporting a setup failure; keep `work/compiled-redux.sfc` private. See [the compiler-order investigation](../research/redux-compiler-order-20261009.md) for the focused checks and remaining limits.

Desktop preview data is stored in `EarthBoundCompanionPreview` beneath the operating system's local application data directory. The launcher displays its exact path. Executables stay in the extracted package while saves, settings and content profiles stay in the private data folder. The Settings shortcut pauses the game and activates the launcher; **Save settings / return to game** applies changes and resumes.

## Android setup

Install the ARM64 APK on a compatible Android 8.0+ device. The x64 APK is supplied for emulator testing. The preview application ID is `org.earthbound.companion.preview`. APK updates use a persistent project signing key.

Use [Android preview.26](https://github.com/rages4calm/earthbound-companion/releases/tag/v0.5.0-ports-preview.26) for Android and [platform preview.26](https://github.com/rages4calm/earthbound-companion/releases/tag/v0.5.0-ports-preview.26) for Linux/macOS. Android retains the persistent application ID/signing key, so an APK update preserves existing app data.

1. Put your clean EarthBound (USA) `.sfc` or `.smc` ROM on the device. Headered clean dumps are supported. Extract a ZIP first; do not apply a hack patch to the ROM.
2. In **Game & setup**, choose **Set up Original from ROM** or **Set up Redux from ROM**, then select the ROM in Android's file picker. Original setup works offline. Redux downloads the pinned supported source files over verified HTTPS and builds them locally; it also prepares Original data if needed. Keep Companion open while setup runs. Once setup completes, the edition is selected automatically—press **Play**. A computer is not required. Existing packs can still be imported with the matching **Import … assets.pak** button.
3. Touch controls include diagonals, sprint (Y), A/B/X, L/R, Start/Select, quick Save/Load, Fast and Settings. A Bluetooth or USB controller can also be used. Save/Load uses the selected quick-save slot.
4. For a handheld or controller, open **Controls**, turn off **Show touch controls**, then choose **Save settings / return to game**. All touch buttons disappear. Android Back reveals them temporarily if you need Settings; the saved choice is reapplied when you return. With the buttons already visible, Back requests a checkpoint and exits as before.
5. The touch **Settings** button pauses the game and opens the launcher. **Save settings / return to game** resumes the existing game. Preview.13 corrects the old button sending the Zoom action instead, and resumes after Save/Return even when settings arrive before Android brings the game back to the foreground.
6. To keep the zoomed-out wide view during dialogue and Goods, set **Wide FOV On** in the game's own **Set Up** menu. If the old Settings button already selected close-up zoom, switch that option Off, then On once; this resets the saved camera to the wide view. The launcher's **Wide field of view** checkbox alone does not reset an already selected close-up zoom. The saved touch-overlay choice is independent of the camera.

A background event requests a quick save on the game thread and pauses game logic. Back requests a checkpoint and clean game exit. If SDL reports a lost render device, the game requests a checkpoint and returns to the launcher rather than continuing with invalid textures. Sudden termination cannot guarantee a new quick save. Phone lifecycle, touch layout, controllers and actual gameplay still require device testing.

Preview.19 uses a sliding thumbstick: drag continuously between all eight directions, move into the center to stop, or lift your thumb. Movement remains digital, matching the game. A second finger can hold **Y / Run**, **A** or another action. The compact phone layout keeps L/R beside the face buttons; tablets use a shoulder row. Interrupted touches, hiding the overlay and leaving the game release held touch inputs. The same **Show touch controls** preference remains available for handheld/controller play. [Touch update and checks](RELEASE-android-preview19.md).

Android data stays in app-private storage. **Saves & mods** exports/imports through the system file picker. Export saves before uninstalling; removing the app removes its private data.

Setup validates the ROM, pinned Redux source, compiled ROM and generated packs before installation. Existing profiles and saves are preserved. Generated ROMs and temporary source copies are removed when setup finishes. If setup fails, use **Export ROM setup log** in **Game & setup** to save the diagnostic text for a report; do not send your ROM or generated pack.

## Save transfer

Choose the matching edition and seed before transferring an 8192-byte `earthbound.srm` phone save. Raw saves do not identify their story or seed, so the user must choose correctly. Imports back up previous data first. Press **Play** and load the normal in-game save after importing; an older quick save is a separate snapshot.

Verified Companion backup ZIPs check the adventure and asset identity before restoring the phone save. Quick saves are restricted to their exact engine build and are not the cross-platform transfer format. Never overwrite an owner's newest save for a test.

## What has and has not been tested

Builds, ROM-free input/MSU checks, settings ABI/round trips, path isolation, synthetic phone-save backup/recovery and launcher startup are covered by automation. Android checks include embedded converter imports, synthetic native compiler ordering and invalid-ROM rejection. Private emulator tests additionally build Original and Redux from the owner's clean ROM and require their exact supported pack checksums; the ROM is never sent to public CI. These checks do not verify the game campaign, audio playback quality, physical controllers/handhelds or long sessions. Community reports remain necessary; see [PLATFORM-TESTING.md](PLATFORM-TESTING.md) for short focused tests.

The Windows launcher is compiled as a guard. Local tests additionally use copies and temporary sessions to check Original/Redux native launches and deterministic seed recipes. No new-platform full playthrough is claimed. Published build results identify the checks that actually passed.

## Reproducing builds

`scripts/prepare_port_sources.py` prepares a fresh pinned native checkout and a SHA-256-checked SDL 2.32.10 archive. It refuses to reset an existing source folder. Apply `patches/native-portable.patch` after the dev.33 `native-companion.patch`. For the Android launcher, copy the verified SDL archive's `android-project/app/src/main/java/org/libsdl/app/*.java` into `Ports/AndroidManaged/Java` before publishing; those generated bridge files are intentionally ignored by Git. `.github/workflows/platform-preview.yml` builds previews without ROMs, generated packs, music or personal saves, using standard public-repository runners.

Portable code retains its SPDX notices; the repository's license scopes and existing upstream notices still apply. SDL is zlib, Avalonia is MIT, Inter is OFL, and LakeSnes/SkiaSharp/HarfBuzz notices accompany packages. Pinned legacy CCScript and CCScriptWriter do not supply standalone license declarations; the helper retains their source provenance, package metadata and the bundled filesystem notice without inventing licenses.

The desktop Redux source-download helper includes Certifi's public CA bundle
and its MPL-2.0 notice, supplementing system trust while keeping TLS certificate
and hostname verification enabled. `redux-setup --selftest-source-download`
checks the HTTPS path and pinned source checksum without a ROM. This certificate
packaging repair is on the preview branch; existing preview.1 downloads do not
include it. See [the focused report](../research/redux-linux-download-tls-20261009.md).
