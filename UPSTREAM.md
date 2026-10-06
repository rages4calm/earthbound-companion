# Pinned upstream source

| Field | Value |
|---|---|
| Repository | <https://github.com/seanstaggsQU/earthboundRecompLinux2026> |
| Commit | `76eacab54b05766b82c98da9c55d94d1236ece03` |
| Patch | `patches/native-companion.patch` |
| Lineage | seanstaggsQU fork → BrianPugh/earthbound → Herringway/ebsrc |

Run `powershell -ExecutionPolicy Bypass -File .\scripts\Bootstrap-Native.ps1` to clone that exact revision, initialize its Tamp submodule, and apply the Companion patch.

## What is still used

The engine has not been replaced with an independent implementation. CMake links the pinned C gameplay library and its desktop platform layer; Companion's patch extends and fixes them. Battle, world, text, inventory, entity, graphics and audio implementations still retain upstream work. The frozen Redux setup helper also bundles selected native C/header/schema files to resolve conversion references.

The October 4 read-only review verifies the GitHub fork chain: Sean Staggs's repository is a fork of BrianPugh/earthbound, which is a fork of Herringway/ebsrc. The local build origin and HEAD match the pin above. Of 197 tracked C/H files under `src/` and `port/` at that pin, 136 are unchanged and 61 are modified by Companion. Modified files also retain upstream code. These counts exclude new Companion files, generated assets and vendor submodule contents; they are evidence of continued dependency, not an authorship percentage.

MaternalBound Redux is a separate input, pinned at [`897d00833f4a08a0a92f106abf631629a6a6a041`](https://github.com/ShadowOne333/MaternalBound-Redux/tree/897d00833f4a08a0a92f106abf631629a6a6a041). The local compiler/converters build its data and the native patch adapts its gameplay changes. New conversion tools do not supersede the C game engine.

## License review and visibility

The October 4 review found no root license file or repository-wide redistribution grant in the native-foundation root documents reviewed. GitHub's detected license is null for the three foundation repositories. Complete-tree scans found notices for individual vendor libraries in the C forks; those notices do not license the complete engine. MaternalBound's GPLv3 grant is separate.

The [machine-readable review](validation/upstream-license-provenance.json) records checked branch/pin commits, complete-tree coverage, notice paths, README/license hashes and relevant document lines. It cannot rule out permission granted outside those sources.

The repository and experimental releases are public as of October 6, 2026. Visibility does not resolve the recorded distribution terms. Public visibility alone does not grant a redistribution license, and credits/pin/patch packaging do not replace one. Combined native/GPL distribution terms remain unresolved. See [LEGAL.md](LEGAL.md) for the concrete boundaries and [CREDITS.md](CREDITS.md) for authorship.
