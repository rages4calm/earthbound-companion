# Redux development tester package verification

This is a private experimental conversion checkpoint, not a completed compatibility release.

- Archive: `EarthBound-Companion-Redux-Tester-v0.5.0-redux-dev.1-20261004-184816-be818100.zip`
- Bytes: 124029264
- SHA-256: `04B7ED5BCB014F047F6B70C6184A3198969F14CC6DA32F10D384A2D34153CDE7`
- Native engine: `86021608639A0DCD0D73B23C4BAF026D019E0935ED45E9BA00B745877985F4A8`
- Frozen Redux setup: `1CFAC8EDC5188F66F3024DDDAA949E8791AEAAF688B0E9AE2523E9CBB441E4D9`
- Generated Redux pack: `62BA3D70B37C95812BC742B40F1F599B142263FFB39F3DD949DDC66AA7E246C2`

The exact final ZIP passed a fresh extracted-directory test with a 512-byte-header USA ROM and only Windows system directories on PATH. It verified every manifest file, generated exact original and Redux packs, selected a separate development profile, removed generated ROMs, ran native story and randomized openings with mixed-case naming and cold restores, and passed profile/save isolation checks. The owner input ROM hash remained unchanged.

Soundtrack testing deliberately corrupted one track and left a stale partial. Production setup downloaded and repaired that track, removed the partial and independently checked all 164 files. The other 163 already-verified tracks were hard-linked from the local cache; a full 1.25 GB download was not repeated.

The packaged launcher separately passed 1,000 seeds and all 30 option combinations for each content edition. Current native tests cover the newly ported font-width highlighting and fourteen-frame delivery letterbox/music sequence. Original-profile input, saves, key items and join-level regression checks pass.

Full start-to-ending story and randomized playthroughs, every combat effect/resistance combination, complete soundtrack listening/transitions, live photo collection and complete developer/debug parity remain unverified. Metadata reports record their actual engine/content hashes; earlier focused reports are retained with their original hashes.

No ROM, asset pack, PCM, save or state files are included in the ZIP or repository. Existing installed files were backed up before the local update; original story saves were preserved.
