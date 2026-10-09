# Companion platform preview

This work lives on `ports/multiplatform-preview`. The stable Windows experience remains the dev.33 release; this preview is not installed over it or marked Latest.

## Current scope

Linux x64, Apple Silicon macOS and Intel macOS build the existing C/SDL2 game core and a separate Avalonia launcher. The launcher compiles the same settings, Story Shuffle v4, progression checks, content profile and save recovery sources as Windows. Its private data root is `EarthBoundCompanionPreview` beneath the operating system's local application data directory. Windows stays with its current Windows Forms launcher and paths.

Android uses the same game core with SDL's official Android activity, native touch inputs, app-private data, and file-picker imports. An Android background event requests a quick save on the game thread and pauses game logic. A quick save cannot be guaranteed after sudden process termination. Normal phone saves are the recommended cross-platform transfer format; raw quick saves retain the exact-engine restriction.

## Testing and missing parity

Compilation and automated checks are distinct from community gameplay testing. No full campaign on a new platform is claimed. Android device behavior, Bluetooth controllers, suspend/resume, display effects and long sessions need volunteer checks. macOS packages are currently unsigned and not notarized.

The first preview supports importing privately generated Original and Redux packs. Desktop Original ROM setup is packaged. Redux ROM conversion packaging is still pending on Linux/macOS. Android does not yet generate game packs or Story Shuffle seeds on the device. External Slang presets require new graphics integrations on these platforms and are currently disabled; native display effects remain available. Android MSU importing and controller remapping UI are pending. These limitations must remain visible in download descriptions.

## Running a desktop preview

Extract the archive, then launch `EarthBoundCompanion.Portable` from that directory. On Linux install the normal desktop libraries for X11, OpenGL, fontconfig and audio if your distribution does not already provide them. Select your clean USA ROM for Original setup, or import `Game/assets.pak` from your own Windows Companion installation. For Redux also import the privately generated `Profiles/maternalbound-redux-897d0083/assets.pak`, then select Redux. Never post those packs publicly.

## Android preview

Install the preview APK. Choose **Import game data** and select your privately generated Original or supported Redux `assets.pak`. Select the edition and press Play. Save and Load buttons operate the selected quick-save slot; Y is sprint, and holding Fast advances the game faster. You can export/import the 8192-byte normal phone save through the system file picker. Save imports first keep a copy of the previous phone save.

The APK has its own application ID, `org.earthbound.companion.preview`; it does not modify any Windows installation. Removing the Android app removes its private saves, so export before uninstalling.

## Builds

`scripts/prepare_port_sources.py` prepares a new pinned native checkout and a SHA-256-checked SDL 2.32.10 archive. It refuses to reset existing source. The portable native patch is applied *after* the dev.33 patch. `.github/workflows/platform-preview.yml` builds each platform, compiles the existing Windows launcher as a guard, and publishes workflow artifacts without ROMs, music or personal saves. Standard public-repository runners are used.

The source is GPL-3.0-or-later with the existing upstream notices. SDL is zlib; Avalonia is MIT; the audio implementation retains its LakeSnes notice. Preview packaging must retain these notices.
