# MaternalBound native bridge verification

Date: 2026-10-04

## Toolchain

- MaternalBound Redux source revision: `897d00833f4a08a0a92f106abf631629a6a6a041`
- CoilSnake source revision: `346cfc753644bc3703b6fc4eaa0a5d6bdcb9bb4a`
- CoilSnake's legacy CCScript compiler was updated locally from `experimental/filesystem` to C++17 `filesystem` and built with current Visual Studio.
- Current upstream Redux source compiled successfully into a 6 MiB development ROM.

## Reproducible evidence

- Official v1.1 BPS SHA-256: `D3157892AFEAB6DD40F15FB73F8899A175247A71D93370D23E643A13E1371B56`
- Checksum-verified v1.1 patched ROM SHA-256: `B11307AEE0D772E35BBA12680DAC5CD7E57D6CAF87EE3582D759D319E13C3AD1`
- Current source compile SHA-256: `C2A2FC98C7E6518B797959FFADF24CA4DB8B4D7745ED3A9EB92EEE106DB1D0AB`
- Bridge manifest SHA-256: `081177D81CC462359906A855E22A4045C4C18A325F0296E071A753004E9E6179`
- Bridge inventory: 190 modules, 166 nonempty modules, 7,840 labels, and 188 modules mapped to CCS source files. The two unmapped entries are compiler-provided standard modules.
- Recursive source graph: 191 reachable CCS files, 1,018 resolved import edges, zero unresolved imports, zero duplicate module names, with a SHA-256 recorded for every source file.
- Compiled current source differs from its 6 MiB base in 3,001,565 bytes across 94,305 contiguous regions.

## Native boundary

The current native extractor recognizes the official v1.1 ROM but fails when modified `E01ONET0` data points to Redux's relocated script region. This is the first confirmed converter boundary. The manifest now resolves the entire reachable CCS source graph plus nearly every compiled module and label location, but it does not execute the project's SNES 65816 routines in the native engine.

The manifest carries `inventory-only-native-port-incomplete`. No Redux ROM, native asset pack, extracted Nintendo asset, save, screenshot, or PCM file is stored in this repository.

## Randomizer integration

Story Shuffle v3 now binds each seed to an explicit content ID, display name, exact base-pack hash, progression policy, and isolated save directory. The original EarthBound (USA) profile passed 1,000 deterministic seed runs and all 30 valid option/style combinations. An unknown or unaudited pack is rejected for seed generation. The Redux profile will remain locked until the converted native pack and its rewritten-script progression audit pass.
