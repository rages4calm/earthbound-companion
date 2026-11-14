# EarthBound Companion 1.0.24 / platform preview.34

Fixes issue #16: crashing when opening Stonehenge chests containing Spicy jerky or a Guts capsule.

The previous item-register change was a regression: real chest scripts pass the recipient in working memory and the item in argument memory. Reversed handling could treat the item ID as a character ID. This update restores the established award convention in both item-award commands and keeps the narrowly scoped legacy Zombie Paper courier recovery.

Real chest-script fixtures pass for 169 ordinary item boxes in Redux and168 in Original, including both reported items. Prompt/delay children were auto-acknowledged in the isolated fixtures; this is not room-by-room traversal. The pre-fix runtime reproduces an invalid-character fatal error on a Guts capsule chest. The real courier receiver-to-award checks still pass for Ness, Paula and Jeff, alongside the corrected48 operand combinations and all14 receipt slots. Earlier synthetic operand tests had mirrored the mistaken register assumption; these are corrected and real chest coverage is retained.

Existing saves and assets remain compatible. No new game, save edit or repeated ROM conversion is needed. Portable packages are rebuilt from the same source; this release uses build-only CI following the focused private-pack runtime checks.
