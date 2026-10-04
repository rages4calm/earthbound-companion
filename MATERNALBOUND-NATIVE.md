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

### Dialogue conversion and native handlers

The October 4 development checkpoint goes beyond that inventory. [`scripts/maternalbound_dialogue.py`](scripts/maternalbound_dialogue.py) reads the locally compiled Redux ROM, checks its exact checksum and all 191 source-file checksums against the bridge, parses the script instructions, expands compressed text, and rewrites script pointers for the native text VM.

- 7,133 accepted label spans produced 545,615 bytes of converted dialogue.
- 10,054 pointer fields were relocated, with zero unresolved targets within those accepted spans.
- Seven spans were rejected because their jump-table operands are truncated. They are recorded as errors rather than repaired silently.
- Forty original-address aliases remain ambiguous. The converter does not choose between duplicate definitions; those must be resolved before replacing the native engine's original entry points.
- Sixteen distinct SNES routine/return-type combinations are still unported, with 352 call sites in the accepted scripts.
- Six custom native handlers now exist: safe money gifts, wallet-capacity checks, bank-capacity checks, current party position, full-width register equality, and string-based window titles.

The native build passed 19 command checks through its real script reader and dispatchers. Four title strings from the actual converted Redux blob passed through native CC180C and the existing font-rendering path. Eleven synthetic converter tests cover compressed-text boundaries, pointer widths, malformed tables, dual-column menu callbacks, unknown commands, and source classification. The original build's input/MSU, save-state, key-items and join-level checks also passed after these changes.

These are bounded development tests. They do **not** establish playable Redux gameplay, six-letter-name compatibility, complete native routine coverage, converted graphics/tables, or safe Redux randomizer progression. The converted blob is private local game content and is deliberately excluded from this repository and releases. The metadata-only [conversion report](research/maternalbound-dialogue-report.json) and [native test record](validation/native-redux-results.json) identify the precise checkpoint.

To reproduce the compiler stage after building the pinned Redux source locally:

```powershell
python scripts/maternalbound_dialogue.py `
  --bridge research/maternalbound-native-bridge.json `
  --project "PATH\TO\MaternalBound-Redux\Project" `
  --compiled-rom "PATH\TO\MaternalBound-Redux\Mother 2.sfc" `
  --native-source native-source `
  --output-dir "LOCAL\redux-dialogue"
python scripts/test_maternalbound_dialogue.py
```

Use the native source's Python environment so `ebtools` dependencies are available. [`scripts/Verify-MaternalBound-Dev.ps1`](scripts/Verify-MaternalBound-Dev.ps1) runs the native command and converted-title checks using explicit executable, base-asset, converted-directory, bridge and scratch-directory paths. It records `development-only-not-playable` even when all of those tests pass. This compiler checkpoint targets the pinned current upstream source; official v1.1 remains a separate compatibility target.

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
