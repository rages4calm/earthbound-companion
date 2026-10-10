# Redux compiler input ordering — October 9, 2026

A Linux tester passed the pinned source download, base expansion and compilation, but setup rejected the compiled ROM checksum. Original setup succeeded. The compiler log supplied by the tester contains no fatal compiler error. The warning about table relocation at `0x1327f` also occurs in the successful Windows control; it does not explain the checksum failure by itself.

## Reproduction

Pinned CoilSnake `346cfc753644bc3703b6fc4eaa0a5d6bdcb9bb4a` passes top-level `.ccs` files to CCScript using unsorted `os.listdir` results in [`compile_project`](https://github.com/pk-hack/CoilSnake/blob/346cfc753644bc3703b6fc4eaa0a5d6bdcb9bb4a/coilsnake/ui/common.py). Filesystem enumeration order is not a portable input contract.

The audited Redux source at `897d00833f4a08a0a92f106abf631629a6a6a041` has two top-level roots: `data_mem_overwrite.ccs` and `main.ccs`. Two isolated full compilations used the same verified source graph, PSI-expanded base and repaired pinned compiler, changing only their input order:

| Root order | Compiled ROM SHA-256 |
| --- | --- |
| `data_mem_overwrite.ccs`, `main.ccs` | `C2A2FC98C7E6518B797959FFADF24CA4DB8B4D7745ED3A9EB92EEE106DB1D0AB` — exact audited identity |
| `main.ccs`, `data_mem_overwrite.ccs` | `7D9BFFF7D6503050CA4DF836F90D756B73D30A6CD895AFFB2BA30D826DEBDC90` — rejected by the existing check |

The two outputs differ at 216 bytes, from file offset `0xDCF2` through `0x3C5B8D`. Generated ROMs and copied game data remain private.

The tester subsequently supplied a private compiled output with SHA-256 `F5407EE952C5DE6D05079096CA6829F11103C0D739C6B047E97996B7162CAD7C`. It differs from the audited ROM at only 186 bytes, concentrated in code-module allocation and references. A Windows-hosted GNU C++ control built from the same pinned CCScript source reproduces that exact identity with the audited root order. Its ASCII-path adaptation is confined to the private comparison tool; it is not part of the shipping patch.

The second defect is CCScript's size-only `std::sort` comparator in `AssignModuleAddresses`. Equal-sized modules have no defined tie order. Microsoft and GNU standard libraries produce different layouts. With both input ordering and explicit module ordering applied, GNU full compilations using both root permutations produce the original audited `C2A2FC...` identity.

## Change and checks

`redux_compile_order.py` sorts only the `.ccs` input arguments by basename, using case-insensitive ordering with a case-sensitive tie break. Compiler options retain their positions. Both the source-mode profile builder and frozen helper use this adapter.

`patches/ccscript-module-order.patch` adds an optional `--module-order` argument to the pinned compiler. The packaged helper supplies `research/redux-module-order.txt`, derived from the audited Windows compilation summary. Its 168 rows contain only module names and compiled sizes, ordered by audited allocation address; no code bytes are included. The compiler verifies every nonempty module's name and size, rejects missing/extra/duplicate entries, and uses the supplied order to break size ties. The largest-fitting-module allocation algorithm remains the same. Upstream game source, expected ROM identity and current native pack identity remain unchanged.

A complete Windows source-mode conversion passes expansion, compilation, dialogue conversion, native pack conversion and movement audit. It produces the exact audited ROM and current native Redux pack `4B5F1C5AC76E4BDCCE2DC66A2E8EF95B659E561D3CADEBEFA66EFB85C0BE5236`. The Original donor pack remains unchanged.

The rebuilt frozen Windows helper also passes the real pinned-source HTTPS download, all conversion stages and movement audit with that exact ROM and pack identity. It uses the patched compiler and bundled allocation metadata, without relying on the development compiler installation.

`redux-setup --selftest-compiler-order` invokes the real packaged native compiler with invented scripts and an all-zero synthetic 6 MiB ROM. Overlapping writes make the two root permutations observable. Both normalize to the expected output, SHA-256 `21fa4fa317fc722d4a0c138bf88c21e57115d5ef198294c09e756f802ad146c3`. A second fixture compiles 24 equal-sized modules in both input directions with an explicit reverse allocation order; both produce `1640f6fa0747706d579acf6815978e81d8b28d32db2f644c84c06aa225aa5f99`. A mismatched module size is rejected. These checks use no Nintendo content and run in desktop CI alongside the existing TLS checks and real pinned-source download.

On a compiled checksum mismatch, setup preserves a metadata-only `compiler-identity.json` in its failed profile. It never installs an unrecognized ROM or accepts a platform-specific alternate checksum.

## Limits

The exact reported compiler output is reproduced with GNU C++, and the corrected compiler reproduces the audited output. A GNU compiler hosted on Windows is not a complete Linux/macOS ROM conversion or gameplay test. Reporter retry remains necessary. Published release verification records must identify the packaged platform checks that actually ran.
