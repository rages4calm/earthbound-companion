# EarthBound Companion 1.0.21 / platform preview.31

Combined maintenance update for issues #12, #13 and #14:

- PSI ability labels redraw on their own row after canceling a healing target, rather than using the targeting window's cursor row.
- Tony's pinned Redux running group repeats one straight-left frame. The runtime uses the two mirrored right-facing frames for that broken pair; other directions and corrected/custom descriptors remain unchanged.
- In-game player-name keyboards no longer advance the last loaded battle/title background. Both keyboard layouts use a separate glyph tile pool, keeping long player names from pushing glyphs into the text tilemap.

Existing asset packs and saves remain compatible; no ROM conversion is needed again. Windows direct launch is retained: add `EarthBound Companion.exe` to Steam twice, using `--play-original` and `--play-redux` as Launch Options. Complete each edition's usual setup once first.

Focused checks pass with private Original and Redux packs: all 10 overworld PSI ability rows, unchanged sprite pointers outside the Tony correction, and both in-game name targets over 90 frames each with a previously loaded animated background. Pre-fix controls reproduce the respective failures. These are isolated native fixtures, not full playthroughs or a recreation of the reporter's exact Summers save. Platform build/startup checks are recorded separately in the release receipt.
