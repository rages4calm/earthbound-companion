# Legal and distribution notes

This document records practical project boundaries. It is not legal advice and does not replace permission from a rights holder.

## No game distribution

This repository and its release packaging must not contain:

- EarthBound or Mother 2 ROM images, in whole or in part;
- `assets.pak` or other data extracted from a ROM;
- extracted sprites, maps, dialogue dumps or audio;
- MSU PCM payloads;
- user save files or save states.

Documentation may include clearly labeled screenshots captured from isolated native development tests using locally supplied game data. Screenshots are not asset packs or permission to redistribute the game.

The release tool verifies a player-supplied clean EarthBound (USA) ROM and generates native data on that player's computer. The input ROM is never modified or uploaded. Conversion creates working files and generated ROMs locally; successful builds remove them, while failed builds can retain a private diagnostic staging folder. Do not upload that folder.

## Upstream source status

As checked on October 4, 2026, GitHub reports no detected top-level license for [Herringway/ebsrc](https://github.com/Herringway/ebsrc), [BrianPugh/earthbound](https://github.com/BrianPugh/earthbound), or [seanstaggsQU/earthboundRecompLinux2026](https://github.com/seanstaggsQU/earthboundRecompLinux2026). A complete-tree path review and inspection of their root README/license files did not locate a repository-wide redistribution grant. Their READMEs describe the C port as open source, but do not state a license's permissions or conditions. Separately licensed vendor files do not license the whole engine. The checked commits, paths and document hashes are recorded in [the provenance audit](validation/upstream-license-provenance.json).

This review cannot rule out permission granted elsewhere. It records the evidence available in the reviewed sources, rather than a legal determination. [GitHub's guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) distinguishes public viewing/forking from permission to reproduce, distribute or create derivative works without a license.

This repository therefore stores:

1. the exact upstream URL and commit used;
2. a patch containing the changes needed by Companion;
3. independently authored launcher, tooling and documentation.

It does not vendor or relicense the complete upstream tree. **The native engine still derives from that tree.** The patch includes upstream context, the compiled executable contains upstream implementations, and the frozen Redux helper bundles some native source files for conversion. Storing a patch instead of a full checkout does not by itself settle distribution rights.

The repository and experimental combined releases are public as of October 6, 2026. Public visibility does not resolve native-foundation distribution terms or prove compliance with the separately licensed GPL components. Neither attribution nor an unofficial-project disclaimer supplies missing rights. The project does not claim legal clearance for the combined release.

## MaternalBound and GPL components

[MaternalBound Redux](https://github.com/ShadowOne333/MaternalBound-Redux/blob/897d00833f4a08a0a92f106abf631629a6a6a041/LICENSE) supplies GPLv3 terms. Its [README](https://github.com/ShadowOne333/MaternalBound-Redux/tree/897d00833f4a08a0a92f106abf631629a6a6a041#license) also requests public source for modified versions and distinct naming. Companion uses a distinct name and retains source attribution and per-file GPL notices for the adaptation work. CoilSnake and related tools have separate notices as well.

Those terms do not grant rights to the native foundation or Nintendo's original game assets. The native engine links GPL adaptation modules into the same executable; its combined distribution and license compatibility need clarification. Published converters, patches and pinned bootstrap inputs are development source records, not a certification that every corresponding-source/distribution obligation has been satisfied. Recipients must receive the source access and rights required by the applicable licenses; a private GitHub link inaccessible to a recipient is not sufficient.

A public release of the combined project needs documented applicable native-engine terms, resolution of the combined-work license obligations, and a matching source/distribution review. Independently authored launcher/tool components can be assessed separately; rewriting a converter or adding features does not remove retained upstream code from the engine.

## Trademarks and affiliation

EarthBound and Mother 2 are trademarks and copyrighted works of their respective owners. This is an unofficial, noncommercial fan project. It is not affiliated with, sponsored by, approved by, or endorsed by Nintendo, APE, HAL Laboratory, Shigesato Itoi, or any other rights holder.

## Original Companion code

Files authored specifically for Companion may be used under [LICENSE.md](LICENSE.md), subject to its scope and any more specific per-file license. It does not override GPL adaptation notices or cover the upstream patch, Nintendo material, third-party code, trademarks, or separately licensed dependencies.

## Contributions and reports

Do not attach ROMs, extracted data, copyrighted media, MSU tracks, or saves containing embedded game data to issues or pull requests. Describe defects using logs, steps, hashes and source-level references.
