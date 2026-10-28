# 1.0.13: Windows launcher scaling

Fixes [issue #8](https://github.com/rages4calm/earthbound-companion/issues/8).
The Windows launcher now declares a DPI scaling baseline. Settings and achievement
rows grow to fit their text, dropdown item heights follow the font, action rows
wrap, and input-binding grid rows size to their contents. Page text wraps to the
available width instead of forcing a minimum width wider than the window.

Original and Redux setup dialogs are resizable and scrollable. Build and Cancel
stay in a separate bottom action area, and longer button captions get enough
space. Windows are constrained to the monitor work area when opened.

All nine launcher pages and both setup dialogs passed isolated layout stress
checks with geometry and text enlarged to 100%, 125%, 150% and 200%; representative
screenshots were visually reviewed. These are simulated scaling checks on a
96-DPI desktop, not a physical multi-monitor DPI transition test. No game runtime,
ROM conversion, asset packs, settings format or saves changed. The native game
binary remains byte-identical to 1.0.12. Linux/macOS/Android remain preview.24;
this fix applies to the separate Windows Forms launcher only.
