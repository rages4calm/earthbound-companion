#!/usr/bin/env python3
"""Check that each preview APK contains one complete ABI and no private game data."""
import argparse
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("apk")
parser.add_argument("abi", choices=("arm64-v8a", "x86_64"))
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
print(f"APK package check passed: {args.abi}; native engine, SDL and managed UI present; no private game data.")
