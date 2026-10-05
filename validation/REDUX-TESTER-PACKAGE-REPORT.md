# Redux development tester package verification

This is a private experimental conversion checkpoint, not a completed compatibility release.

## Dev.9 encounter and audio release

- Archive: `EarthBound-Companion-Redux-Tester-v0.5.0-redux-dev.9.zip`
- Bytes: 124,569,020
- SHA-256: `C52D445B1E604FC3F3878419EED59FB04D41DC3583971B136988EFC38E1F6BE9`
- Native engine: `1EB1D64956370AEE674B603F0E6717A02D35E5C6E9CC22E3DBD2CE60A962CEAF`
- Frozen Redux setup: `2931EB12806513F836A70D7451F3AF9CCB27E603248DDA2AED372B36DCDBE8AA`
- Corrected Redux pack remains `ED299183D4B1AFF4B38C56EF16DA28A256C3A65D33BA1D9327C9B19DF0272EF3`.

The exact archive passed fresh extracted setup using a headered owner ROM with no Python/Git on PATH, native story/randomized openings and ordinary house/Mom/outdoor input replays, profile/save isolation, all 164 music checks, one corrupt-track repair through the real download path, and generated-ROM cleanup. [Clean package evidence](redux-clean-package-dev9.json).

The newly rebuilt player/observer engines pass the shared encounter and audio regressions, including 230 enemy records per edition, retained bicycle music after both victory paths, acknowledged cash/equipment/menu/bell effects, and real shop sound dispatch in both audio modes. The native patch reconstructs all 71 modified/new source files on the pinned upstream checkout. [Reliability methods and limits](../docs/RELIABILITY-dev9.md).

The ZIP contains no ROM, game asset pack, PCM soundtrack, saves or states. Full Redux compatibility and completed story/randomized playthroughs remain unverified.

## Historical dev.2 documentation refresh

- Distributed archive: `EarthBound-Companion-Redux-Tester-v0.5.0-redux-dev.2-20261004-200535-docs-9a5f7c3a.zip`
- Bytes: 124047305
- SHA-256: `68AF7A45742D7599EB9CC6351411B359BD14A65C109F0661F94DE16770F191B0`

Only documentation and the package manifest changed. All 17 other files—including the launcher, native executable, both setup helpers, SDL2, profiles and dependency notices—are byte-identical to the fully tested parent archive below. This refresh passed ZIP CRC/path/payload checks, exact manifest verification and 27 package-local link checks. Source-only report/screenshot links now point to the repository; access to that private repository is required. Full setup/audio/gameplay suites were not repeated for unchanged binaries. See [native-redux-documentation-package.json](native-redux-documentation-package.json).

## Runtime-validation parent archive

- Archive: `EarthBound-Companion-Redux-Tester-v0.5.0-redux-dev.2-20261004-194236-6df619b3.zip`
- Bytes: 124036401
- SHA-256: `7204B6126D84C9FCE16C8CF88AB50749D861717D4453EA0331A59E6C28015F65`
- Native engine: `20C8FBCB910447E2817F5D22F6D57F8D22C5AE2C8EABF832B18EEA2CF19E0474`
- Frozen Redux setup: `889C677DF234D04AF4C71DA94BB9680589515BBCB5999042B422668E4CE62E9E`
- Generated Redux pack: `62BA3D70B37C95812BC742B40F1F599B142263FFB39F3DD949DDC66AA7E246C2`

The exact final ZIP passed a fresh extracted-directory test with a 512-byte-header USA ROM and only Windows system directories on PATH. It verified every manifest file, generated exact original and Redux packs, selected a separate development profile, removed generated ROMs, ran native story and randomized openings with mixed-case naming and cold restores, and passed profile/save isolation checks. The owner input ROM hash remained unchanged.

Soundtrack testing deliberately corrupted one track and left a stale partial. Production setup downloaded and repaired that track, removed the partial and independently checked all 164 files. The other 163 already-verified tracks were hard-linked from the local cache; a full 1.25 GB download was not repeated.

The packaged native engine additionally passes all eight Sound Stone SPC-to-MSU transitions without overlapping the old music, retained SPC effects, missing-PCM fallback, 125 real PCM loop boundaries and 39 one-shot ends. The final ZIP also passes normal-button replays from naming through house door/stair crossings, Mom's dialogue, the clothes-change warp and initial outdoor movement, on both story and generated-seed packs, with cold restores between checkpoints and actual 1080p renders. See [native-redux-audio.json](native-redux-audio.json) and [native-redux-story-walk.json](native-redux-story-walk.json).

The packaged launcher separately passed 1,000 seeds and all 30 option combinations for each content edition. Current native tests cover font-width highlighting, the fourteen-frame delivery letterbox/music sequence and 21 faster door-timer cases. Faster doors are an additional Companion QoL change from an optional hook disabled in upstream's pinned import list. Original-profile input, saves, key items and join-level regression checks pass.

Full start-to-ending story and randomized playthroughs, every combat effect/resistance combination, complete soundtrack listening/transitions, live photo collection and complete developer/debug parity remain unverified. Metadata reports record their actual engine/content hashes; earlier focused reports are retained with their original hashes.

No ROM, asset pack, PCM, save or state files are included in the ZIP or repository. Existing installed files were backed up before the local update; original story saves were preserved.
