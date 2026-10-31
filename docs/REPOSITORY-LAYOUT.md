# Working with the source

The repository contains the Companion launcher, achievement system, Android integration, native-engine patches, ROM conversion tools, build workflows, current checks and project documentation. Downloads belong under GitHub Releases, not in the source tree.

## Native game source

The C game engine is fetched from the exact upstream revision in `scripts/prepare_port_sources.py`. Companion's ordered patches are then applied. This keeps the foundation's identity explicit and avoids maintaining a second vendored copy.

On Windows, run `scripts/Bootstrap-Native.ps1` with a fresh destination. It refuses to reset an existing checkout. On other build hosts, `scripts/prepare_port_sources.py --native <fresh-directory>` prepares the same source and patch sequence. See [source provenance](../UPSTREAM.md) and the [platform build workflow](../.github/workflows/platform-preview.yml) for toolchains and full packaging steps.

`Companion/` holds the Windows launcher. `Ports/` holds the shared launcher and platform integration. `Achievements/` holds the achievement catalog and reusable core. `patches/` contains the native changes. `scripts/` contains build, conversion, packaging and retained checking utilities.

## Why GitHub shows Python

GitHub counts files committed in this repository. It does not count the C engine fetched during a build, and native changes stored as `.patch` files do not count as C source. Python is used for ROM conversion, packaging and development checks; the game does not execute its gameplay in Python. The launcher uses C#, and Android also includes Java integration.

## Historical development material

Obsolete experiment scripts and bulk research reports were removed from the current tree during the maintenance cleanup. Historical documentation links to those files use the [last commit before cleanup](https://github.com/rages4calm/earthbound-companion/tree/76b243ff26392efbffea41b9c2617a83ced6092e), where the files remain available in Git history. Historical evidence applies to the build named in that evidence, not automatically to today's release.

Required data such as `research/msu-manifest.json`, source licenses, current release receipts, conversion tools and their retained dependencies remain. No history was rewritten and no release downloads were deleted.

## Local generated files

`.NET bin/obj`, fetched build dependencies, compiler output, generated reports and release staging are local build products. They are excluded from Git and can be regenerated. Keep ROMs, generated asset packs, soundtrack files and personal saves private. Never commit those files as part of a source change.
