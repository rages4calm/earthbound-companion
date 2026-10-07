# EarthBound Companion development tester package

Dev.26 fixes idle geysers, equipment comparison clipping, Lumine Hall scrolling and exposed cave terrain on black transfer screens. [Verification](../docs/RELEASE-dev26.md).

The current Redux development archive contains a native Windows x64 build, the Companion settings/mod launcher, original and Redux ROM-to-native-data helpers, SDL2, documentation, sample native profiles and dependency notices. The older v0.4 archive contains only the original-story setup.

It contains no ROM, extracted `assets.pak`, saves, screenshots or PCM soundtrack files. First-run setup asks for the tester's own clean EarthBound (USA) ROM and builds original data plus a separate pinned Redux development profile on that computer. If selected, it downloads the 164-file EarthBound MSU-1 fan soundtrack from its credited source and verifies every file against the bundled manifest before installation. Successful Redux builds remove generated ROM working files; failed builds can retain private diagnostics. Game/source/soundtrack downloads require Internet access; no Python or Git installation is needed by the tester.

The MSU source page does not declare a redistribution license for the audio payloads. Automatic installation keeps the shared archive small and avoids repackaging those files while still giving the tester a one-step full setup.

The repository and development releases are public. Native-engine redistribution and combined GPL terms remain unresolved in the recorded review; public availability is not a permission grant. See LEGAL.md and UPSTREAM.md; this note does not grant rights to EarthBound or any third-party material. Full story/randomized playthroughs remain unverified.

Dev.16 updates Original mode extraction for the missing possession script. Setup can rebuild older Original data from the tester's clean ROM. Redux data and seed identities are unchanged; previously generated Original seeds keep their own packs and should be regenerated to receive the data fix.

Dev.17 corrects Redux battle-background graphics and four palettes. Updating an audited older Redux profile retains its data in a backup and copies compatible story saves into the corrected pack namespace. Previous seeds retain their original packs/recipes/saves and need the matching retained base selected. Original-mode rebuilding can add the documented starter seed without replacing existing runs. Mid-battle quick saves retain cached artwork until the next battle. See [the current audit](../docs/NATIVE-AUDIT-dev17.md) for remaining conversion gaps and exact verification.

Dev.18 imports exactly 41 additional Redux presentation assets (Town Maps/label, intro, teleport and swirl data), fixes extended title/file-slot glyphs and cold Continue slot detection, and recognizes current Original setup data. Compatible story phone/F6 saves migrate only for reviewed pack pairs; existing seeds retain their exact base. Those separately confirmed party-target and equipped-Give follow-ups are integrated in dev.19. [Current audit](../docs/NATIVE-AUDIT-dev18.md).

Dev.19 ships the previously verified accented party-name and equipped-Give fixes. It preserves dev.18 pack/seed identities and save format 16, so current dev.18 saves need no namespace migration. The open-ended audit is stopped; further changes follow playtesting reports. [Release evidence](../docs/RELEASE-dev19.md).
