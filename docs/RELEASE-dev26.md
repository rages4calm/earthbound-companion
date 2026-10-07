# Redux dev.26 — four playtest fixes

- Lost Underworld geysers stay hidden and walkable while idle, animate during earthquakes, and return to their idle state. Frame-selection helpers now preserve the script's persistent animation state. Older checkpoints with an idle fountain stuck on frame zero also render correctly.
- Equipment comparisons retain every digit. Values and a compact arrow share one variable-width text run; changed resistances use one trailing percent sign, such as `100 → 90%`, leaving room before the adjacent window and the next row.
- Lumine Hall wall writing advances in the original phase order. The previous packed implementation interleaved the current and next column too early, making alternate steps jump backward. Lower phases now use the previous/current pair and are reconstructed on playback so older mid-animation saves continue correctly.
- Black staging screens used during transfers stay black across the expanded PC view. The wider camera no longer exposes neighbouring cave terrain during the fall to the Lost Underworld. The renderer detects a blank canvas from the actual map tiles and palette; objects and text remain visible.

Verification includes a copied geyser checkpoint walked onto its centre, observed eruption frames and return to idle; 206 usable-item previews across four characters with 1,865,536 rendered pixel comparisons and strongest usable gear; complete Original/Redux Lumine canvas checks and cold continuation of an older mid-animation checkpoint; and the actual hole-to-Underworld route with matching before/after frames and no cave fragment in the staging screen. The latest playthrough checkpoint was tested separately and kept unchanged.

Save format 16, gameplay asset packs, seed identities, music and player settings are retained. The Original title option from dev.25 remains available. This is an experimental native adaptation; full campaign, randomized playthrough, physical controller and listening coverage remain unverified.

[Rendered equipment and staging fixtures](../validation/presentation-qa-dev26.json) · [Original scroll](../validation/lumine-original-dev26.json) · [Redux scroll](../validation/lumine-redux-dev26.json) · [Copied replay coverage](../validation/playtest-fixes-dev26.json)
