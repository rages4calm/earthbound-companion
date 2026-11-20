# 1.0.26 maintenance release

- Restores the maintained Windows runtime: 1.0.25 accidentally shipped an older source build that rejected the launcher's achievement arguments, preventing Play and Resume from reaching save loading. No save conversion is needed.
- Fixes enemy-count underflow when leaving a room containing enemies. The wrapped count could suppress all encounters in the next room, including Fire Spring. Removal cannot decrement zero; old quick saves with an impossible count recover from their active entities.
- Keeps the Starman Super sprite binding fix and the owner-approved Sword of Kings drop increase in both normal and instant-win battles.
- Windows packaging and Linux/macOS CI now check the native executable against Companion's actual launch arguments before release.

The same 24-patch native source is used for Windows and platform preview.36 (Linux x64, macOS ARM64/x64, Android ARM64/x64). Android retains its app identity and signing key.

Focused private-asset checks reproduce the room-transition and sprite failures on pre-fix code and pass in both Original and Redux after correction. They cover 320 Fire Spring entry scans per edition, old quick-state counter recovery, rendered sprite bindings, and 4,096 actual normal/instant drop rolls per edition. This is bounded regression evidence, not another full campaign or a run of the reporter's private save.

[Windows downloads](https://github.com/rages4calm/earthbound-companion/releases/tag/v1.0.26) · [Linux/macOS/Android downloads](https://github.com/rages4calm/earthbound-companion/releases/tag/v0.5.0-ports-preview.36)
