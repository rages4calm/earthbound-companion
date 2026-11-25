# 1.0.27 maintenance release

- Shows the carried-money window directly below the command menu. It kept its original position, which the taller menu (Keys, Save, Set Up, Quit) covered. Shops and the cancel-button HP/PP display keep the original position.
- Shows HP/PP and money as soon as the command menu opens, instead of only after choosing Goods, PSI, Equip or Status.
- Adds **Press to finish dialogue** (off by default). With Quick dialogue off, pressing confirm or cancel while a page is typing shows the rest of that page; the next press advances as usual. Scripted pauses are kept.
- Adds **Pause in the background** (off by default). The game and its audio pause while another window has focus and resume when you return. Not shown on Android, which already pauses in the background.
- Adds **Hide launcher while playing** (off by default, Windows launcher). The launcher window closes when the game starts; F1 in the game still opens settings, and the launcher exits with the game.

The same 25-patch native source is used for Windows and platform preview.37 (Linux x64, macOS ARM64/x64, Android ARM64/x64). Saves, settings, seeds and achievements are unchanged. Android retains its app identity and signing key.

Checked on Windows in Original with scripted input in an isolated session: menu, Equip, the cancel-button display and menu close, compared against 1.0.26; press-to-finish with the option off and on, including that the following prompt still waits for its own press. Frame timing over 900 frames matches 1.0.26. Redux uses the same placement code and was not run separately. This is bounded regression evidence, not a campaign replay.

[Windows downloads](https://github.com/rages4calm/earthbound-companion/releases/tag/v1.0.27) · [Linux/macOS/Android downloads](https://github.com/rages4calm/earthbound-companion/releases/tag/v0.5.0-ports-preview.37)
