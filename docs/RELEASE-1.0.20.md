# EarthBound Companion 1.0.20 (Windows)

Launch either regular story directly without opening the launcher window:

- Double-click `Play Original.cmd` or `Play Redux.cmd` in the extracted package.
- For Steam Big Picture, add `EarthBound Companion.exe` as a non-Steam game. Set Launch Options to `--play-original` or `--play-redux`. Add it twice and rename the entries to keep both editions one click away. Keep Start In set to the folder containing Companion.

Complete the usual ROM setup once first. Redux also needs to be built once under Game Mode. Each entry uses its existing saves, settings and achievements. The background Companion process stays alive for Steam tracking and opens settings when requested with F1. Closing the settings window resumes/hides it; the process exits when the game closes. Missing game data produces an explanatory error instead of silently choosing Original.

Windows integration checks passed for both editions: invisible startup, separate content sessions, actual native child launch, settings request, closing settings without ending the game, and exit lifecycle. Native game bytes are unchanged from 1.0.19. Linux/macOS/Android remain on preview.30; this change only adds the Windows entry points.
