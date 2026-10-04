---
name: EarthBound Companion
description: Native Windows settings with night violet surfaces and warm yellow actions.
colors:
  canvas: "#1A182A"
  rail: "#12101F"
  surface: "#2A263E"
  ink: "#F7F3FF"
  muted: "#C2B6D8"
  line: "#504868"
  gold: "#FAD870"
  gold-hover: "#FFE696"
  surface-hover: "#3F3759"
  ready: "#9EDBB3"
  error: "#FFA6A2"
typography:
  headline:
    fontFamily: "Segoe UI"
    fontSize: "25pt"
    fontWeight: 700
  title:
    fontFamily: "Segoe UI"
    fontSize: "13pt"
    fontWeight: 700
  body:
    fontFamily: "Segoe UI"
    fontSize: "11pt"
    fontWeight: 400
  label:
    fontFamily: "Segoe UI"
    fontSize: "11pt"
    fontWeight: 700
  detail:
    fontFamily: "Segoe UI"
    fontSize: "10pt"
    fontWeight: 400
rounded:
  square: "0px"
spacing:
  label-after: "8px"
  action-gap: "12px"
  section-before: "16px"
  content-inset: "32px"
components:
  button-primary:
    backgroundColor: "{colors.gold}"
    textColor: "{colors.rail}"
    typography: "{typography.label}"
    rounded: "{rounded.square}"
    width: "190px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.gold-hover}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.square}"
    width: "190px"
    height: "44px"
  button-secondary-hover:
    backgroundColor: "{colors.surface-hover}"
  navigation-item:
    backgroundColor: "{colors.rail}"
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    width: "166px"
    height: "46px"
  navigation-item-selected:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.gold}"
  choice:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
  binding-grid:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.detail}"
---

# Design System: EarthBound Companion

## Overview

**Creative North Star: "Night violet companion"**

The system pairs a quiet violet work area with warm yellow actions and actual EarthBound pixels. It carries the familiar Companion navigation and settings structure authorized by the user, rather than a separately approved image comp. This document records the published Windows Forms artifact; the source remains authoritative for native rendering.

The interface favors readable task names, descriptions immediately below them, aligned controls and persistent status. Game imagery provides character without replacing Windows control affordances. The palette supports the original artwork; the artwork is not a source of additional UI colors.

**Key Characteristics:**

- Flat violet canvas, darker rail and footer, lighter interactive surfaces.
- Segoe UI hierarchy with bold task headings and regular help text.
- Rectangular actions, native input controls and visible keyboard focus.
- Flexible settings width with scrolling inside the content region.
- Authentic game imagery rendered with nearest-neighbor interpolation.

Evidence: `Companion/Program.cs` defines the visual system; `Companion/Settings.cs` defines loaded preset state. `validation/ui-final` and `validation/ui-compact` contain the six-page captures at default and compact sizes. `validation/finish-verdict.md` resolves the review's compact-fit, preset-state and authorization findings. The artifact is `EarthBound Companion/EarthBound Companion.exe`. There is no approved comp, seed or separate quality-bar card; `Companion.surface.md` records that boundary.

## Colors

Night violet layers carry the utility, with yellow for actions and selected content, and restrained semantic colors for readiness and errors. Frontmatter values are exact hexadecimal translations of the source's `Color.FromArgb` values, not a separate theme implementation.

### Primary

- **Warm yellow (`gold`):** primary action fill, selected navigation text, selected dropdown text, slider value and brand text. **Pale yellow (`gold-hover`)** is its explicit action hover state.

### Secondary

- **Ready green (`ready`):** the game-data-ready label.
- **Error rose (`error`):** missing game data and error notification text. Neither semantic color supplies action hierarchy.

### Neutral

- **Night violet (`canvas`):** content background and binding-grid cells.
- **Deep violet (`rail`):** navigation, footer, grid headers and dark primary-action text.
- **Raised violet (`surface`):** secondary buttons, dropdown contents and selected navigation/grid cells.
- **Hover violet (`surface-hover`):** explicit button hover fill.
- **Pale ink (`ink`):** titles, body copy and default field values.
- **Lavender detail (`muted`):** supporting text, unselected navigation, footer status and disabled action text.
- **Violet line (`line`):** secondary-action edges, selected navigation edges and grid separators.

### Named Rules

**The Action and State Rule.** Yellow identifies actionable or selected content; green and rose communicate readiness and failure through accompanying words.

## Typography

**Headline and body font:** Segoe UI, the explicitly selected native Windows family. There is no supplied webfont or custom fallback stack. Font sizes in the frontmatter are points, matching `System.Drawing.Font`; they are not CSS pixel measurements. Native font metrics determine line height and spacing between glyphs.

### Hierarchy

- **Headline:** bold page heading using the `headline` role.
- **Title:** bold section heading using the `title` role.
- **Body:** regular field titles, descriptions under page headings and dropdown values using the `body` role.
- **Label:** bold action and navigation text using the `label` role.
- **Detail:** regular row help, shortcut explanations, grid content and footer status using the `detail` role.

The scale is role-based, not a fixed mathematical ratio. Brand and occasional supporting labels have local sizes; these are not promoted into reusable type roles. Labels use natural sentence case; button mnemonics are disabled so literal ampersands remain literal.

### Named Rules

**The Native Type Rule.** Use Segoe UI in native point units; reserve bold for navigation, actions, section titles and page headings. Keep supporting explanations regular and muted.

## Layout

The shell is a two-column, two-row native `TableLayoutPanel`: a fixed left rail (210 logical coordinate units), flexible content column, and fixed bottom action region (76 units). The rail spans both rows. Default client size is 1120 by 800. Compact validation uses a 990 by 760 client area; `MinimumSize` is also set to 990 by 760, but that property constrains outer window dimensions, not the client area. These are native WinForms coordinates, subject to the application's DPI behavior, not web breakpoints.

The content uses a vertical nonwrapping `FlowLayoutPanel` with automatic scrolling and padding of 32 left, 26 top, 24 right and 12 bottom. The rail uses 24 left, 32 top, 18 right and 20 bottom. Its action entries have 6 units between them. The footer uses 32 left, 9 top, 24 right and 10 bottom; its final column reserves 190 units for Apply. Scroll the content without moving navigation or the footer.

Content blocks resize to `max(680, contentClientWidth - horizontalPadding - 22)`. Settings rows have 64% text and 36% input columns, a height of 78 and 8 units after each row. Field titles occupy the first 28-unit row. Help width recalculates to `max(200, floor(rowClientWidth * .64) - 12)` so compact text wraps in its column. Input margins are 12 left and 4 right. Labels normally allow a maximum width of 730; setting help uses the dynamic width above.

Sections have 16 units before and 12 after their title. Action strips are 58 units high, do not wrap, and carry 6 units before and 12 after. Standard actions have a right margin of 12. Text uses an 8-unit bottom margin by default. These explicit relationships, rather than a universal spacing multiplier, define the rhythm.

### Named Rules

**The Persistent Apply Rule.** Keep the status and Apply action outside the scrollable page; longer settings pages scroll while this action remains visible.

**The Help Column Rule.** Constrain explanatory text to its actual text column and allow it to wrap at compact width.

## Elevation & Depth

The application defines no shadows or animated elevation. Depth comes from violet tonal layers, thin control edges and selected fills. Native dropdown arrows, scrollbars, checkbox checks and trackbar thumbs retain operating-system rendering. The application changes states immediately; its 350ms process/status timer is operational polling, not a motion token.

### Named Rules

**The Flat Task Rule.** Separate actions and selection with fill, edge and text changes; retain native focus and control affordances.

## Shapes

Custom painted actions are square rectangles with a one-unit edge. Their focus rectangle is inset by 4 units. Navigation uses the same action component at its own dimensions. Grid divisions are straight lines; content groups use spacing rather than decorative cards. Native widget shapes remain platform-owned: this square custom-control vocabulary does not forbid rounded details supplied by Windows.

## Components

### Buttons

Direct rectangular task actions. Standard size is recorded in `button-primary` and `button-secondary`; footer docking can reduce the effective width to fit its reserved column.

- Primary uses warm yellow with deep violet text and edge; secondary uses raised violet, pale ink and a violet edge.
- Hover fills are explicitly recorded variants. The custom paint method derives hover from cursor containment and paints no separate pressed-fill variant.
- Text is centered vertically and horizontally with end ellipsis, bold label type and no mnemonic parsing.
- Enabled actions use a hand cursor. Disabled action text becomes muted. Focus is a native dotted inset rectangle.

### Inputs / Fields

Settings align a plain-language title and help with the corresponding control. Accessible names use the setting title.

- **Choices:** native, noneditable `DropDownList` combo boxes. Items are owner-drawn on raised violet with pale ink or selected yellow text, 24-unit item height and native focus drawing. The preset selector computes Enhanced, Classic, CRT, Easygoing or Custom from loaded options; returning to the page preserves truthful state.
- **Checkboxes:** native checks with an adjacent “Enabled” label, pale text and the setting title as their accessible name. Checked state carries the setting value; Windows supplies the check mark and focus rendering.
- **Sliders:** native tick-free trackbars, with small change 1 and large change 5; a yellow numeric label occupies the rightmost 45 units. Values update immediately in the pending settings object.
- Changes become persistent through Apply. Normal and error feedback appears in the footer rather than a transient toast.

### Navigation

Seven stacked, stable page destinations use bold label typography: Solo Play, Randomizer, Display, Audio, Gameplay, Controls and Mods & saves. Unselected entries blend with the rail and use muted text. Selected entries use a raised violet fill, yellow text and a violet edge. Selecting a destination reconstructs its controls from current settings and resets content scrolling to the top. Focus can remain on another navigation entry while the selected page differs; focus and selection are separate states.

The Randomizer page uses a two-column, two-row group of compact toggle cells on raised violet surfaces. Its seed-library dropdown uses the same owner-drawn dark dropdown treatment as other choices. Generate & Play fits in the first viewport at both standard and compact sizes. A final 32-unit spacer lets the scrolled page reveal its last compatibility note above the persistent footer. Current extension evidence is in `validation/ui-randomizer-ready`, `validation/ui-randomizer-compact` and the final corrected compact captures in `validation/ui-randomizer-final`.

Story Shuffle v2 retains that layout with an always-on protection notice and an explicit version in seed labels. Safety inspection, backup/restore and regeneration actions follow the selected-seed controls; none are hidden behind hover. All four options and generation actions remain visible at 990x760, and the final compatibility paragraph is completely reachable by scrolling. `validation/ui-randomizer-v2` records this manual review. The recovery dialog defaults to phone saves only and states that current saves are backed up before restoration; the button says Restore backup.

### Input bindings

A read-only `DataGridView` presents Action, Keyboard and Controller columns. Binding columns are native flat button cells; click or Enter opens binding capture. Cells use canvas/ink, with surface/yellow selection, violet grid lines and padding of 7 horizontal and 4 vertical units. Row height is 32, header height 36 and visible grid height 400. The table has its own scrolling inside the scrolling settings page.

The capture dialog is a centered fixed native dialog, with the same canvas, ink and Segoe UI. It captures a physical key or newly pressed controller input, provides Clear binding and Cancel actions, and cancels on Escape. File selection and save prompts use native Windows dialogs rather than invented custom modal styling.

### Game scene

The image control reads the packaged `Media/onett.png`. It uses nearest-neighbor interpolation and centered cover scaling, clipping excess imagery to its rectangular viewport without stretching aspect ratio. The shipped Play scene is 200 units high, with 8 units before and 24 after. If the image is unavailable, the control renders the deep violet background. Its pixels come from the user's privately extracted game assets; future imagery must retain provenance rather than imitate a game capture.

## Do's and Don'ts

### Do:

- **Do** preserve the recorded native point-based type hierarchy and violet/yellow action relationships.
- **Do** retain visible focus, keyboard access and the native checkbox, dropdown, slider and dialog behaviors.
- **Do** keep footer actions visible while long settings and binding lists scroll.
- **Do** represent current settings truthfully, including Custom preset state, and wrap help at the actual column width.
- **Do** retain pixel-preserving interpolation and provenance for game imagery.

### Don't:

- **Don't** replace platform focus and control states with decorative mock behavior.
- **Don't** stretch scene imagery to force an aspect ratio or present fabricated artwork as an actual game capture.
- **Don't** treat browser preview CSS, synthesized swatch ramps or operating-system widget colors as new native theme tokens.
- **Don't** infer a responsive mobile design, an approved image comp or a custom animation system from these native desktop captures.

Not canonized: local 15pt/18pt text sizes are one-off uses, and Windows blue checkbox/trackbar accents are platform rendering rather than palette primitives. Segoe UI headings are the confirmed native Operate choice, not a general prescription for web display type. The sidecar's HTML/CSS illustrates the controls for a browser panel; it is not a native implementation or a pixel-exact rendering contract. Its synthesized tonal ramps are display metadata only.
