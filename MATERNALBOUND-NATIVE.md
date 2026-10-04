# MaternalBound Redux native port

![EarthBound Companion's MaternalBound Redux native-port status screen](docs/images/redux-port.png)

The project direction is now explicit: combine MaternalBound Redux's restored writing, art, fixes, and presentation with Companion's native x64 engine, HD and ultrawide display, MSU music, PC settings, QoL profiles, save recovery, and content-safe randomizer. It is a direct native adaptation effort, not a plan to run the patched ROM through an embedded emulator.

## Current player-facing status

EarthBound Companion v0.4.0 does **not** contain MaternalBound Redux. It launches the original EarthBound (USA) story data with Companion's native display, input, MSU, quality-of-life, save, and Story Shuffle features. The main v0.5 development source adds the conversion bridge, visible port-status page, and content-aware randomizer foundation; it still does not claim playable Redux content.

The current MSU player includes Redux-compatible track loop behavior. That compatibility does not import Redux's rewritten script, uncensored graphics, enemy and character art, tables, controls, bug fixes, or 65816 routines.

## Why the ROM patch cannot be loaded directly

Companion executes the game as compiled native C. MaternalBound Redux patches SNES 65816 machine code, relocates CCScript text, and replaces a large amount of game data. A BPS patch can produce the intended SNES ROM, but those patched machine-code routines cannot execute inside the native C game.

The first direct extraction test used the verified official v1.1 BPS patch. Extraction reached the modified `E01ONET0` script and stopped when a Redux pointer targeted relocated script data outside the original ROM's fixed text map. Silently accepting that pointer would create a pack that could crash or run the wrong event later in a playthrough.

## Native conversion work completed

- The official v1.1 BPS patch was applied with source, target, and patch checksum verification.
- The current MaternalBound Redux source at commit `897d00833f4a08a0a92f106abf631629a6a6a041` was compiled locally with CoilSnake.
- CoilSnake's legacy CCScript dependency was updated locally for C++17 so it builds with current Visual Studio.
- The current source produced a verified 6 MiB development ROM and a deterministic CCScript summary.
- `tools/maternalbound_bridge.py` converts that summary into a machine-readable native-port manifest.
- The bridge now follows the complete recursive CCScript import graph: 191 reachable source files and 1,018 import edges with zero unresolved imports. It maps 188 of 190 compiled modules directly to source; the remaining two are compiler-provided standard modules. The compiled inventory contains 166 nonempty modules and 7,840 labels.
- Byte comparison found 3,001,565 changed bytes across 94,305 contiguous regions versus the 6 MiB compile base.

The generated manifest is evidence and a porting map. Its status is deliberately `inventory-only-native-port-incomplete`; generating it does not make the native game Redux-compatible.

## Port order

1. Generate versioned Redux label and relocation maps during local setup.
2. Convert Redux's CoilSnake data, tables, graphics, sprites, and rewritten text into a separate native asset pack.
3. Replace every Redux 65816 routine used by that data with an audited native C implementation or an existing equivalent Companion feature.
4. Give Redux its own asset identity and save namespace so original-story and randomized saves cannot cross-load.
5. Generate Redux's separate Story Shuffle v3 policy from its rewritten scripts and converted tables. The launcher matches the exact asset hash before allowing seed generation; an unknown profile remains locked.
6. Validate setup, boot, event scripts, battles, shops, randomizer guards, controls, saves, MSU transitions, and a full playthrough before calling the mode supported.

Stable v1.1 is the first compatibility target. The active upstream source is tracked separately so a later release can be added as another versioned target without changing existing saves.

## Upstream project and credit

MaternalBound Redux is created by [ShadowOne333 and its contributors](https://github.com/ShadowOne333/MaternalBound-Redux) and is licensed under GPLv3. Companion's eventual native adaptation will use a distinct name, preserve upstream credit, publish the corresponding adaptation source, and continue requiring the player to supply their own clean EarthBound ROM.
