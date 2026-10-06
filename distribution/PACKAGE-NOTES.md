# EarthBound Companion development tester package

The current Redux development archive contains a native Windows x64 build, the Companion settings/mod launcher, original and Redux ROM-to-native-data helpers, SDL2, documentation, sample native profiles and dependency notices. The older v0.4 archive contains only the original-story setup.

It contains no ROM, extracted `assets.pak`, saves, screenshots or PCM soundtrack files. First-run setup asks for the tester's own clean EarthBound (USA) ROM and builds original data plus a separate pinned Redux development profile on that computer. If selected, it downloads the 164-file EarthBound MSU-1 fan soundtrack from its credited source and verifies every file against the bundled manifest before installation. Successful Redux builds remove generated ROM working files; failed builds can retain private diagnostics. Game/source/soundtrack downloads require Internet access; no Python or Git installation is needed by the tester.

The MSU source page does not declare a redistribution license for the audio payloads. Automatic installation keeps the shared archive small and avoids repackaging those files while still giving the tester a one-step full setup.

The repository and development releases are public. Native-engine redistribution and combined GPL terms remain unresolved in the recorded review; public availability is not a permission grant. See LEGAL.md and UPSTREAM.md; this note does not grant rights to EarthBound or any third-party material. Full story/randomized playthroughs remain unverified.

Dev.16 updates Original mode extraction for the missing possession script. Setup can rebuild older Original data from the tester's clean ROM. Redux data and seed identities are unchanged; previously generated Original seeds keep their own packs and should be regenerated to receive the data fix.
