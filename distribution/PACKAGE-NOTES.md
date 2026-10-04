# EarthBound Companion private tester package

This archive contains a native Windows x64 build, the Companion settings and mod launcher, a standalone ROM-to-assets helper, SDL2, documentation, sample native profiles, and dependency notices.

It deliberately contains no ROM, extracted `assets.pak`, saves, screenshots, or PCM soundtrack files. First-run setup asks for the tester's own clean EarthBound (USA) ROM and builds `Game/assets.pak` on that computer. If selected, it downloads the 164-file EarthBound MSU-1 fan soundtrack from its credited source and verifies every file against the bundled manifest before installation.

The MSU source page does not declare a redistribution license for the audio payloads. Automatic installation keeps the shared archive small and avoids repackaging those files while still giving the tester a one-step full setup.

Use is limited to private testing because the selected native C fork currently has no top-level distribution license. This note does not grant rights to EarthBound or any third-party material.
