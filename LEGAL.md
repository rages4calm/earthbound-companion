# Legal and distribution notes

This document records practical project boundaries. It is not legal advice and does not replace permission from a rights holder.

## No game distribution

This repository and its release packaging must not contain:

- EarthBound or Mother 2 ROM images, in whole or in part;
- `assets.pak` or other data extracted from a ROM;
- original game screenshots, sprites, maps, dialogue dumps or audio;
- MSU PCM payloads;
- user save files or save states.

The release tool verifies a player-supplied clean EarthBound (USA) ROM and generates the native asset pack on that player’s computer. The ROM is not modified, retained by Companion, or uploaded.

## Upstream source status

As checked on October 4, 2026, GitHub reports no detected top-level license for [Herringway/ebsrc](https://github.com/Herringway/ebsrc), [BrianPugh/earthbound](https://github.com/BrianPugh/earthbound), or [seanstaggsQU/earthboundRecompLinux2026](https://github.com/seanstaggsQU/earthboundRecompLinux2026). Their public availability does not place the work in the public domain.

This repository therefore stores:

1. the exact upstream URL and commit used;
2. a patch containing the changes needed by Companion;
3. independently authored launcher, tooling and documentation.

It does not vendor or relicense the complete upstream tree. The initial compiled release is restricted to private invited testing while redistribution permission is unresolved. Do not make the repository or binary release public solely on the strength of a disclaimer.

## Trademarks and affiliation

EarthBound and Mother 2 are trademarks and copyrighted works of their respective owners. This is an unofficial, noncommercial fan project. It is not affiliated with, sponsored by, approved by, or endorsed by Nintendo, APE, HAL Laboratory, Shigesato Itoi, or any other rights holder.

## Original Companion code

Files authored specifically for Companion may be used under [LICENSE.md](LICENSE.md). That license applies only where this repository’s contributors have the right to grant it. It does not cover the upstream patch, Nintendo material, third-party code, trademarks, or separately licensed dependencies.

## Contributions and reports

Do not attach ROMs, extracted data, copyrighted media, MSU tracks, or saves containing embedded game data to issues or pull requests. Describe defects using logs, steps, hashes and source-level references.
