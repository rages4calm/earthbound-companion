# Companion app icon

The red-cap planet and sparkle are original artwork created for EarthBound Companion with the built-in OpenAI image-generation tool on October 5, 2026. They express the fan launcher's identity. The artwork is not extracted from a ROM or copied from an official game logo.

- `earthbound-companion.png`: original transparent artwork.
- `earthbound-companion.ico`: 16, 20, 24, 32, 40, 48, 64, 128 and 256 pixel Windows entries.

The ICO is compiled into the launcher executable and included as a managed resource for its windows/dialogs. Portable packages also include `EarthBound Companion.ico` for shortcut use. Rebuild the ICO with Pillow and `python scripts/build_app_icon.py` from the repository root.

Generation prompt:

> Use case: logo-brand. Asset type: finished Windows desktop application icon for EarthBound Companion, a fan-made native PC game launcher. Generate ONE centered original emblem on a fully transparent canvas. A rich sapphire-blue planet with very simple mint-teal continent shapes wears a bright red baseball cap with a short cream-yellow brim, a subtle nod to EarthBound's Ness. One small warm yellow four-point sparkle sits beside the lower-right of the planet. Polished flat illustrated game-app icon, strong silhouette, clean thick navy outlines, limited cel-shaded highlights, crisp smooth contours, no tiny texture. The cap and planet form one cohesive compact icon, not a separate scene. Nearly circular overall silhouette, fills 85 percent of the square canvas with breathing room. Front/three-quarter view, cap brim angled slightly toward the viewer's right. Keep it readable at 32 pixels. Transparent outside the emblem, no square tile, no background, no text, no letters, no wordmark, no watermark, no screenshots, no existing official logo, no actual human character. Friendly premium desktop-game icon, bold red/blue/teal/yellow palette. Draw the final icon itself, not a mockup or sheet.
