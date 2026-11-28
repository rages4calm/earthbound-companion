# 1.0.28 / platform preview.38 — Threed NPCs and updates

Original now restores two Threed residents whose retail appearance flags hid
their existing dialogue. NPC 526 remains visible after Belch; NPC 563 appears
after Belch rather than waiting for an unused flag. The latter timing is inferred
and matches the pinned Redux data. Redux already has both corrected records.
Only the known original gates are normalized; custom records are preserved.
Thanks to TheRunaway5/Phase-Distorter for identifying these records.

## Updating from now on

Download this release once to get the updater. In Windows, choose **Updates**
near the top of the launcher sidebar, then **Check again → Install update**.
Linux/macOS use the **Updates** section in the page selector. Close the game
first. Checks at startup can be disabled; installation always requires a click.

Desktop updates download the matching GitHub release, verify its SHA-256,
stage it beside the installation, close the launcher, replace package files and
restart the launcher. A replacement failure rolls back the previous files.
Installation paths stay the same for Steam and desktop shortcuts. Original,
Redux, randomizer saves, achievements, settings, private game data and MSU files
are not replaced. A read-only installation must be moved to a writable folder.
The updater downloads the full package; this is not a binary-delta service.

Android offers **Download Android update** for the correct APK architecture.
Open the downloaded APK and approve Android's update prompt. Do not uninstall
the old app; installing over it preserves its data. Android's package manager
checks the persistent signing identity. This is not a silent APK installer.

## Verification limits

Focused native checks exercise every loaded NPC record with private Original
and Redux packs, both Belch flag states and unchanged custom records. Updater
tests cover release selection, ZIP/tar layouts, unsafe paths, SHA-256 mismatch,
player-data preservation, replacement rollback and staging cleanup. A synthetic
release exercises the packaged Windows launcher download/helper/restart path.
Launcher geometry and text are checked at 100–200% scaling.

This is bounded verification, not a new full campaign or proof on every device.
Linux/macOS/Android remain community previews. See the accompanying validation
receipts for platform build/test results.
