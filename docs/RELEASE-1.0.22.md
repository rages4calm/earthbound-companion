# EarthBound Companion 1.0.22 / platform preview.32

Fixes issue #15: crashing when the pizza courier gives Ness the Zombie Paper.

The two item-award commands read the wrong temporary script registers when an operand is zero: the recipient must come from argument memory and the item from working memory. A flag check in the Redux delivery branch can leave working memory zero, which was then incorrectly used as the character ID. Imported saves can expose this branch; starting a new run or editing the save is unnecessary.

The fix follows the original ROM handlers, covers both award commands and preserves existing item receipt handling. Existing saves and asset packs remain compatible; no ROM setup is needed again.

Focused checks pass in Original and Redux: 48 literal/indirect register combinations per edition, pooled and unpooled key items, all 14 receipt slots and full-inventory refusal. The actual pinned Redux Zombie Paper award script was also executed with the imported-style branch settings. The pre-fix handler reproduces the reported fatal error. The reporter's own save and the full courier arrival/departure scene were not replayed.

Previous fixes and Windows Steam launch options are retained: add `EarthBound Companion.exe` to Steam twice with `--play-original` and `--play-redux` after the usual one-time setup.
