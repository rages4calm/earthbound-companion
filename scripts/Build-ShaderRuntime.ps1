# SPDX-License-Identifier: GPL-3.0-or-later
<#
.SYNOPSIS
Build the pinned, optional Windows x64 D3D11 Slang runtime into a fresh directory.
.DESCRIPTION
Requires an existing Rust 1.91.1 MSVC toolchain and Visual C++/Windows SDK build
tools. This script installs no tools, changes no global settings, and deletes
nothing. Run from a developer shell if the C++ toolchain is not discoverable.
The Cargo lockfile pins dependencies. Source bytes and build inputs are checked;
a rebuilt DLL is not promised to be byte-identical across C++ toolchain versions.
.EXAMPLE
./scripts/Build-ShaderRuntime.ps1 -Destination C:/Builds/eb-shader-runtime
.EXAMPLE
./scripts/Build-ShaderRuntime.ps1 -Destination C:/Builds/eb-shader-runtime -RustToolchain stable
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Destination,
    [string]$RustToolchain = '1.91.1'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
function Get-DllImports([string]$Path) {
    $bytes = [IO.File]::ReadAllBytes($Path)
    $pe = [BitConverter]::ToInt32($bytes, 0x3c)
    if ([BitConverter]::ToUInt32($bytes, $pe) -ne 0x4550 -or
        [BitConverter]::ToUInt16($bytes, $pe + 4) -ne 0x8664) {
        throw 'Expected an x64 PE DLL.'
    }
    $count = [BitConverter]::ToUInt16($bytes, $pe + 6)
    $optionalSize = [BitConverter]::ToUInt16($bytes, $pe + 20)
    $optional = $pe + 24
    if ([BitConverter]::ToUInt16($bytes, $optional) -ne 0x20b) { throw 'Expected PE32+.' }
    $sections = $optional + $optionalSize
    $rvaOffset = {
        param([uint32]$Rva)
        for ($i = 0; $i -lt $count; $i++) {
            $section = $sections + $i * 40
            $start = [BitConverter]::ToUInt32($bytes, $section + 12)
            $size = [Math]::Max([BitConverter]::ToUInt32($bytes, $section + 8),
                [BitConverter]::ToUInt32($bytes, $section + 16))
            if ($Rva -ge $start -and $Rva -lt ($start + $size)) {
                return [int]([BitConverter]::ToUInt32($bytes, $section + 20) + $Rva - $start)
            }
        }
        throw 'PE import RVA is outside its sections.'
    }
    $imports = [BitConverter]::ToUInt32($bytes, $optional + 120)
    if ($imports -eq 0) { return @() }
    $offset = & $rvaOffset $imports
    $names = @()
    for (;;) {
        $nameRva = [BitConverter]::ToUInt32($bytes, $offset + 12)
        if ($nameRva -eq 0) { break }
        $nameOffset = & $rvaOffset $nameRva
        $end = $nameOffset
        while ($bytes[$end] -ne 0) { $end++ }
        $names += [Text.Encoding]::ASCII.GetString($bytes, $nameOffset, $end - $nameOffset).ToLowerInvariant()
        $offset += 20
    }
    return @($names | Sort-Object -Unique)
}
$sourceUrl = 'https://codeload.github.com/SnowflakePowered/librashader/zip/refs/tags/librashader-v0.12.0'
$sourceSha256 = 'e5404dc94b3993c76f6248f061f2c83c6f178be595c0de76530abb777b2898df'
$destinationPath = [IO.Path]::GetFullPath($Destination)
if (Test-Path -LiteralPath $destinationPath) {
    if (-not (Test-Path -LiteralPath $destinationPath -PathType Container) -or
        @(Get-ChildItem -LiteralPath $destinationPath -Force).Count -ne 0) {
        throw 'Destination must be a new or empty directory; existing files will not be overwritten.'
    }
}
$cargo = (Get-Command cargo.exe -ErrorAction Stop).Source
$rustc = (Get-Command rustc.exe -ErrorAction Stop).Source
$savedAutoInstall = [Environment]::GetEnvironmentVariable('RUSTUP_AUTO_INSTALL', 'Process')
$savedRustFlags = [Environment]::GetEnvironmentVariable('RUSTFLAGS', 'Process')
$savedTargetDir = [Environment]::GetEnvironmentVariable('CARGO_TARGET_DIR', 'Process')
$savedCargoFlags = [Environment]::GetEnvironmentVariable('CARGO_ENCODED_RUSTFLAGS', 'Process')
$locationPushed = $false
try {
    $env:RUSTUP_AUTO_INSTALL = '0'
    $compiler = (& $rustc "+$RustToolchain" -vV 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Requested Rust toolchain is not installed. No automatic installation was attempted.' }
    if ($compiler -notmatch '(?m)^release: 1\.91\.1\r?$' -or
        $compiler -notmatch '(?m)^host: x86_64-pc-windows-msvc\r?$') {
        throw 'This build recipe requires Rust 1.91.1 with host x86_64-pc-windows-msvc.'
    }
    New-Item -ItemType Directory -Path $destinationPath -Force | Out-Null
    $archive = Join-Path $destinationPath 'librashader-v0.12.0-source.zip'
    Invoke-WebRequest -Uri $sourceUrl -OutFile $archive -UseBasicParsing
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sourceSha256) {
        throw 'Pinned source ZIP SHA256 mismatch. Download retained for inspection; build stopped.'
    }
    Expand-Archive -LiteralPath $archive -DestinationPath $destinationPath
    $source = Join-Path $destinationPath 'librashader-librashader-v0.12.0'
    $env:RUSTFLAGS = '-C target-feature=+crt-static'
    [Environment]::SetEnvironmentVariable('CARGO_ENCODED_RUSTFLAGS', $null, 'Process')
    $env:CARGO_TARGET_DIR = Join-Path $source 'target'
    Push-Location -LiteralPath $source
    $locationPushed = $true
    & $cargo "+$RustToolchain" build --release --locked -p librashader-capi --no-default-features --features runtime-d3d11
    if ($LASTEXITCODE -ne 0) { throw 'Shader runtime compilation failed; source/build outputs retained.' }
    $built = Join-Path $env:CARGO_TARGET_DIR 'release/librashader_capi.dll'
    $output = Join-Path $destinationPath 'librashader.dll'
    Copy-Item -LiteralPath $built -Destination $output
    $imports = @(Get-DllImports $output)
    $unexpected = @($imports | Where-Object {
        $_ -notmatch '^(?:api-ms-win-core-[a-z0-9-]+|bcryptprimitives|kernel32|d3dcompiler_47|combase|oleaut32|shell32|ntdll)\.dll$'
    })
    if ($unexpected.Count -ne 0) {
        throw "Unexpected DLL dependencies: $($unexpected -join ', '). Output retained for inspection."
    }
    $receipt = [ordered]@{
        sourceUrl = $sourceUrl
        sourceSha256 = $sourceSha256
        compiler = $compiler
        rustflags = $env:RUSTFLAGS
        command = 'cargo build --release --locked -p librashader-capi --no-default-features --features runtime-d3d11'
        dllSha256 = (Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash.ToLowerInvariant()
        runtime = 'Windows x64 D3D11 only; static CRT'
        importedSystemDlls = $imports
        output = $output
    }
    $receipt | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $destinationPath 'build-receipt.json') -Encoding UTF8
    Write-Output "Built $output"
    Write-Output "SHA256 $($receipt.dllSha256)"
} finally {
    if ($locationPushed) { Pop-Location }
    [Environment]::SetEnvironmentVariable('RUSTUP_AUTO_INSTALL', $savedAutoInstall, 'Process')
    [Environment]::SetEnvironmentVariable('RUSTFLAGS', $savedRustFlags, 'Process')
    [Environment]::SetEnvironmentVariable('CARGO_TARGET_DIR', $savedTargetDir, 'Process')
    [Environment]::SetEnvironmentVariable('CARGO_ENCODED_RUSTFLAGS', $savedCargoFlags, 'Process')
}
