# EarthBound Companion v0.4.0 tester-package verification

Final archive: `release/EarthBound-Companion-Tester-v0.4.0.zip`

- Size: 94,423,057 bytes
- SHA-256: `9BDB1B4E620C48EE83E3DD38E59DD683607BDE4542110CC14A864915CF93EB58`
- Packaged files: 21 files plus empty first-run directories
- Forbidden-content scan: 0 ROM, asset-pack, PCM, save-state, screenshot or save files
- Standalone setup helper SHA-256: `F94202B789F620C7394C89299870209D99871C6FDA9D3BECB56E9FD5E99B00B9`

## End-to-end extracted-ZIP test

1. Extracted the final ZIP to a new directory.
2. Ran its bundled Companion and standalone helper against the clean EarthBound (USA) donor ROM.
3. Setup completed with exit code 0 and did not copy the ROM into the app.
4. Generated `Game/assets.pak` SHA-256: `4E01C943711D32C41E85CB858D9058169E7C8B1739FC7DC0A211E441F9631B9B`, matching the audited native asset pack.
5. The generated **Tonight in Onett** v2 seed passed `--check-seed` with exit code 0.
6. The packaged Companion passed `--selftest` with exit code 0.
7. The integrated MSU installer verified all 164 locally installed tracks, totaling 1,335,449,356 bytes, with exit code 0.

The setup user interface compiled and ships in the same single-file executable exercised above. The full 1.25 GB remote download was not repeated because all 164 source files had already been downloaded and checksum-verified locally; the integrated code rechecked those files against the embedded manifest. A complete randomized or original-story playthrough remains outside this bounded package test.

Temporary extracted copies and packaging directories were moved into `_BuildScratch/tester-package-artifacts-20261004-095459` after testing. The final archive is the only file left in `release`.
