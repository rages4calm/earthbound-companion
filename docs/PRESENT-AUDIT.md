# Present and container checks

The dev.7 audit covers **177 placed item containers in each edition**: 172 item rewards, three positive cash rewards and two source-defined empty containers. Each container has its own opened flag. The native packs retain all 177 placements, coordinates, flags and reward entries from their respective source data.

Redux's table is checked against the relocated table in the locally compiled, checksum-pinned ROM and the upstream project YAML. Original EarthBound's table is checked against the owner's clean USA ROM. The native placement lists are decoded and compared with the upstream map-sprite lists. Every reward resolves to an existing item definition or the source's cash value; every text pointer resolves through the conversion map.

Redux intentionally changes NPC 1523 from **Broken iron (item 9)** to **Broken gadget (item 5)**. The upstream YAML explicitly records that change. Original EarthBound retains the Broken iron. NPCs 1410 and 1432 contain the source value `256`, which encodes `$0` and follows the empty-container dialogue path. They are not missing item definitions, and Companion does not invent rewards for them.

With Redux's Key items mode enabled, the **HP-sucker, Neutralizer and Carrot Key** containers grant their permanent menu entries through source-defined flags 855, 870 and 904. Those flags intentionally also identify the opened containers. The audit checks that each flag changes from unset to set while inventory/cash stay unchanged. Original EarthBound receives the corresponding physical items. Flag-backed menu rewards remain collectable with a full ordinary inventory.

The executable checks use independent scratch saves. One reachable container's saved NPC identity is replaced with each real container ID; its own opened flag is cleared and its inventory/cash conditions are prepared. The asset packs remain unmodified. Normal confirm inputs then execute that ID's actual native lookup and converted reward dialogue.

For both editions, the checks cover:

- Opening all 177 containers, receiving the expected item, permanent menu unlock, cash or empty result, setting the correct opened flag, and returning to roaming.
- Checking every container again without receiving a duplicate reward.
- Opening all 172 item containers with a full ordinary inventory. An ordinary item must remain available after rejection and be collectable after freeing a slot. The three permanent Redux menu rewards must unlock while the ordinary inventory is full. The two editions pass 341 rejection/retry cases and three permanent-menu cases.

That is **698 prepared executable cases**, plus repeat checks within each case. These are exhaustive catalog/reward tests, not a claim that a tester walked every room, satisfied every story condition or completed the game. Story Shuffle intentionally replaces eligible optional loot; its generation and progression checks are separate from this base-edition loot audit.

The sprite review also identifies **four scripted reward containers** outside the generic item-box path: Fly Honey and letters from Mom, Tony and the kids. Their source-defined items and award flags pass opening, repeat and full-inventory/retry fixtures in both editions: **16 additional reward cases**, for **714 reward cases total** covering 181 reward-container identities per edition. The fixtures bypass physical travel and story appearance conditions; those conditions are not established by a direct reward-script test. [Scripted-container evidence](../validation/native-scripted-containers-dev7.json).

Four other objects using the same sprite IDs start scripted battles instead of granting fixed loot. All eight edition/object pairs enter the exact source-defined battle groups (442 or 446). Four zero-dialogue scenery objects also pass all eight edition/object pairs without granting loot or leaving a stale window. Battle victory and drop probabilities are not tested by these entry checks. [Additional interaction evidence](../validation/native-container-candidate-entries-dev7.json).

Representative ordinary-container replays match the production player and observer builds at **153 complete serialized checkpoints**, including all four container dialogue variants, cash, empty checks and Redux's permanent rewards. [Original parity](../validation/native-present-original-parity-dev7.json) · [Redux parity](../validation/native-present-redux-parity-dev7.json).

The report records binary/pack hashes and per-container outcomes, without bundling game assets or saves. The source fixture tool requires local owner-provided game data: [audit_all_presents.py](../scripts/audit_all_presents.py). Evidence: [native-present-audit-dev7.json](../validation/native-present-audit-dev7.json).

Source references: [pinned Redux container table](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/npc_config_table.yml), [map placements](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/map_sprites.yml), [container scripts](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/Project/ccscript/data/data_35.ccs). See [CREDITS.md](../CREDITS.md) and [UPSTREAM.md](../UPSTREAM.md) for the native engine, disassembly, converters and authorship.
