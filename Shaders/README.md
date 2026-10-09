# Finishing shader presets

Choose **Display → Shader presets → Finishing shader** in the launcher. Off is the default. Warm, Monochrome and Soft CRT are supplied; changing a shader takes effect when you restart the game.

**Choose preset file…** accepts external `.slangp` presets. Keep the complete preset folder, linked `.slang` files and textures together. Preset parameters may be edited in the preset file. Legacy `.glsl` / `.glslp` shaders are not supported. A missing runtime, malformed preset or shader error retains ordinary rendering and records the reason in the game log.

These shaders run on the finished, scaled game image through Direct3D 11. They do not receive a native 224-line input image; CRT/upscaling presets designed around low-resolution input can look different. Black bars remain outside the effect. External presets may be demanding or require features not tested here. Compatibility with every RetroArch preset is not claimed.

The supplied effects are original Companion source, licensed under GPL-3.0-or-later. The optional runtime is [librashader v0.12.0](https://github.com/SnowflakePowered/librashader/releases/tag/librashader-v0.12.0), built with only its D3D11 backend and a static C runtime. See [build instructions](../scripts/Build-ShaderRuntime.ps1) and the included `Licenses/librashader*` notices. The upstream C interface header retains its MIT notice.
