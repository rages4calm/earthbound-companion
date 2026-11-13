# EarthBound Companion 1.0.23 / platform preview.33

Fixes issue #15: crashing when the pizza courier gives Ness the Zombie Paper.

Two item-award commands used the wrong temporary script registers for zero operands. The pinned Redux courier's legacy-inventory branch also loses its selected recipient while checking the Keys-menu option. The runtime now resolves that exact mapped award back to the first party member with inventory space. Other scripts retain normal VM semantics and invalid-character checks.

This can be exposed by imported emulator saves; Ness is still character1. Existing saves and asset packs work without editing or repeating ROM setup. The incomplete1.0.22 candidate was withdrawn after a test starting earlier in the delivery script caught the second problem.

Focused tests pass in both editions: 48 literal/indirect register combinations per edition, pooled/unpooled key items, all14 receipt slots and full-inventory refusal. The real pinned Redux script passes from recipient search through award for Ness, Paula and Jeff, with argument memory initially zero; the exact mapped award also handles a full party safely. The pre-fix handler reproduces the reported fatal error. The reporter's save and full arrival/departure scene were not replayed.

Previous fixes and Windows Steam direct-launch options are retained.
