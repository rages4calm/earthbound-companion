# EarthBound Companion 1.0.16 / platform preview.27

Fixes Redux cinematic bars remaining after a For Sale Sign buyer leaves, which could also clip the town map and other screens. The shared delivery exit now clears a held cinematic mask when returning control. Original mode, unrelated masks and in-progress opening/closing effects retain their behavior.

The old exit reproduced the stuck mask in a focused native fixture. The fix passes 12 Redux and 12 Original cases covering cinematic bars on/off, delivery ownership and opening/held/closing state. The final source also applies through all 15 patches to the pinned foundation. A full natural sale/cancel playthrough was not repeated.

Existing saves and asset packs remain compatible. If an existing quick save already contains the stuck bars, enter and leave a building once to clear them. This release rebuilds all platform downloads with the fix; earlier movement, setup logging and touch-control fixes remain included.
