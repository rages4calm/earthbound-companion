# EarthBound Companion settings surface

Mode: Operate. Native Windows Forms. The user explicitly requested the breadth and ease of the existing Zelda Companion and delegated enhanced presentation and optional classic modes. This extends that familiar sidebar/settings structure. There is no separately approved EarthBound image comp. Typography and native controls follow Windows conventions.

User authority, quoted: "do the same thing for this project as we did for my Zelda project"; "you can do what you did with zelda and give options"; "whatever else you want to add". The inherited Companion structure was treated as pinned by those requests. No concept roll or seed was performed; there is no retrospective seed and no separate QUALITY BAR card. Native Operate conventions are the supplied quality reference.

## Direction contract

THESIS: Get Carl into EarthBound quickly, then make each enhancement easy to tune.

OWN-WORLD: Night violet surfaces, warm yellow actions, Segoe UI, flat rectangular controls, readable muted descriptions, actual Onett imagery.

STORY: Game ready; play first, tune display/music/gameplay, bind controls, recover saves and import supported profiles.

FIRST VIEWPORT: 210px left rail; actual wide Onett scene above Play/Resume; readiness and presets below; persistent Apply action at bottom right.

FORM: User-pinned Zelda Companion structure, native task controls; inherited form, no seed assignment.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Verification scope

Default 1120x800 and compact 990x760 client sizes, six pages each. Scrolling reveals longer pages. Screenshots are captured from the app's own HWND using Pillow ImageGrab; earlier DrawToBitmap/PrintWindow captures were rejected because native dropdown values were absent. Hero imagery comes from the user's extracted EarthBound USA game assets rendered by the native engine.

October 4 randomizer update: Play is now **Solo Play**, with a link into a seventh **Randomizer** page. That page retains the existing tokens and controls, adds four compact toggle cells and a seed-library dropdown, and puts Generate & Play in the first viewport at both supported window sizes. The saved-seed actions and compatibility note are available by scrolling. Direct HWND captures under `validation/ui-randomizer-*` record the manual review of this extension; the earlier six-page agent review remains the baseline review.

Story Shuffle v2 adds an always-on protection notice, visible seed versions/legacy status, safety reports/checks, regeneration without save replacement and guided seed backup/restore. Compact final captures are under `validation/ui-randomizer-v2`; the generation controls and all four options fit the first viewport, while every recovery action and the complete compatibility note is reachable below. These additions were manually inspected, not included in the earlier agent verdict.
