# Redux dev.27 — missing museum researcher

Mr. Spoon could fail to appear while walking across the Fourside museum, blocking the signed-banana quest and access to Magnet Hill. The wider viewport was added a second time to NPC streaming scan positions. Some NPC sectors were scanned while their occupants were beyond the loading margin, then skipped when they entered the visible area.

The native loader now uses the expanded viewport once, retaining the original small scan margins in all four scrolling directions. NPC placements, story flags, quest requirements and save format 16 remain unchanged. This also addresses the same loading error for other placed NPCs.

For an existing museum checkpoint: load with F7, leave the exhibition through the right-hand entrance, re-enter, and walk left to Mr. Spoon. Ask about the autograph, visit Venus at the Topolla Theater, and bring the signed banana back. Magnet Hill and its carrot reward lead to Pink Cloud in Dalaam; Redux calls the key "Rabbits' carrot" in Key Items.

Verified against an untouched copy of the reported museum save: dev.26 reproduces the missing NPC after real exit/re-entry; dev.27 loads NPC 908 while walking left and reaches his autograph dialogue. A private fixture with only the signed-banana acquisition flag supplied completes the normal handoff and opens the sewer route. The singer travel and a full campaign are not certified by that fixture. Original/Redux runtime regression results accompany the package validation.

The player's museum checkpoint is backed up, with no inventory or progress edits. Its six recorded melodies remain intact; Magnet Hill and Pink Cloud are unrecorded. Earlier dev.26 fixes and the Original-title option are retained. No ROM, game pack, soundtrack or save is distributed.
