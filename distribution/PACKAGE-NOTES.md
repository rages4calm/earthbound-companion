# EarthBound Companion private tester package

The current Redux development archive contains a native Windows x64 build, the Companion settings/mod launcher, original and Redux ROM-to-native-data helpers, SDL2, documentation, sample native profiles and dependency notices. The older v0.4 archive contains only the original-story setup.

It contains no ROM, extracted `assets.pak`, saves, screenshots or PCM soundtrack files. First-run setup asks for the tester's own clean EarthBound (USA) ROM and builds original data plus a separate pinned Redux development profile on that computer. If selected, it downloads the 164-file EarthBound MSU-1 fan soundtrack from its credited source and verifies every file against the bundled manifest before installation. Successful Redux builds remove generated ROM working files; failed builds can retain private diagnostics. Game/source/soundtrack downloads require Internet access; no Python or Git installation is needed by the tester.

The MSU source page does not declare a redistribution license for the audio payloads. Automatic installation keeps the shared archive small and avoids repackaging those files while still giving the tester a one-step full setup.

The combined archive currently remains private as a precaution because native-engine redistribution and combined GPL terms are unresolved. Private testing is not itself a permission grant. See LEGAL.md and UPSTREAM.md; this note does not grant rights to EarthBound or any third-party material. Full story/randomized playthroughs remain unverified.
