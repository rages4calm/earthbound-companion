#!/usr/bin/env python3
"""Check that each preview APK contains one complete ABI and no private game data."""
import argparse
import zipfile
import re
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("apk")
parser.add_argument("abi", choices=("arm64-v8a", "x86_64"))
parser.add_argument("--aapt2", help="Inspect the packaged launcher activity configuration")
args = parser.parse_args()
with zipfile.ZipFile(args.apk) as package:
    names = set(package.namelist())
    abis = {name.split("/")[1] for name in names if name.startswith("lib/")}
    if abis != {args.abi}:
        raise SystemExit(f"Unexpected APK architectures: {sorted(abis)}")
    for library in ("libearthbound.so", "libSDL2.so", "libmonodroid.so", "libSkiaSharp.so"):
        if f"lib/{args.abi}/{library}" not in names:
            raise SystemExit(f"Missing Android library: {library}")
    private_data = [name for name in names if name.lower().endswith((".pak", ".sfc", ".smc", ".srm"))]
    if private_data:
        raise SystemExit(f"Private game data in APK: {private_data}")
if args.aapt2:
    manifest = subprocess.check_output([args.aapt2, "dump", "xmltree", args.apk, "--file", "AndroidManifest.xml"], text=True)
    launcher = next(block for block in manifest.split("E: activity") if '"org.earthbound.companion.ManagedLauncher"' in block)
    flags = re.search(r"configChanges\([^)]*\)=(0x[0-9a-fA-F]+)", launcher)
    if flags is None or int(flags[1], 16) & 0x680 != 0x680:
        raise SystemExit("Packaged launcher does not preserve orientation/screen/UI-mode changes")
    if "exported(0x01010010)=true" not in launcher or "theme(0x01010000)=@" not in launcher:
        raise SystemExit("Packaged launcher is missing its exported entry point or AppCompat theme")
print(f"APK package check passed: {args.abi}; native engine, SDL and managed UI present; no private game data.")
