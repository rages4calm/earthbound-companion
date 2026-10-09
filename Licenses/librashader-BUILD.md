# Optional Slang runtime

The supplied Windows x64 DLL is librashader-capi 0.12.0 built from the unmodified
[librashader-v0.12.0 source](https://github.com/SnowflakePowered/librashader/tree/librashader-v0.12.0).
It enables only the D3D11 runtime and statically links the C runtime. The shipped
DLL SHA256 is `3b8f3a383b5405c5a79473c064b3f8900c7d7b1402e230602cc0fbd047fdac79`.
Its direct imports are Windows system DLLs, including `d3dcompiler_47.dll`; no
separate Visual C++ runtime DLL is imported.

The runtime is licensed under MPL-2.0 OR GPL-3.0-only. Both upstream license texts
are retained. The C header uses MIT, supplied separately. Compiled dependency
notices, exact package versions, recovered pinned upstream license links, and
Rust standard-library notices accompany these files. Shader preset licenses
remain separate from the runtime licenses.

Build from an existing Rust 1.91.1 x64 MSVC toolchain and Visual C++/Windows SDK
build tools with `scripts/Build-ShaderRuntime.ps1 -Destination C:/Builds/eb-shaders`.
If an existing `stable` alias is exactly Rust 1.91.1, pass `-RustToolchain stable`.
The helper checks the source ZIP SHA256 and Rust version, uses Cargo's lockfile,
requires a fresh/empty output directory, checks system-only DLL imports, and
writes a build receipt. It installs no tools, deletes no files, and restores its
process environment changes. Different C++ toolchains can change binary bytes;
this is a pinned build recipe rather than a bit-for-bit reproducibility claim.

See `librashader-BUILD-PROVENANCE.json` for the exact supplied build identity and
verification limits. The dependency inventory includes compilation tools and
procedural macros; it does not assert that every crate survives final linking.
Two pinned packages (`sptr` and `vec_extract_if_polyfill`) declare their licenses
but omit license files and copyright notices upstream. Their actual declarations
and standard license texts are marked explicitly; no copyright holder/year was
invented. Vendored glslang, SPIRV-Cross, and Mesa terms are included.
