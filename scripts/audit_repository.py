"""Fail when ROMs, extracted game data, release binaries, or secrets enter Git."""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_SUFFIXES = {
    ".sfc", ".smc", ".fig", ".swc", ".rom", ".pak", ".pcm", ".srm",
    ".sav", ".state", ".bmp", ".exe", ".dll", ".pdb", ".zip", ".7z", ".rar",
}
FORBIDDEN_PARTS = {"rom", "userdata", "msu", "saves", "screenshots", "native-source", "build", "bin", "obj"}
KNOWN_ROM_SHA256 = "a8fe2226728002786d68c27ddddf0b90a894db52e4dfe268fdf72a68cae5f02e"
SECRET_PATTERNS = [
    re.compile(rb"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(rb"gh[opurs]_[A-Za-z0-9]{30,}"),
    re.compile(rb"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
]


def tracked_files() -> list[Path]:
    output = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-z"])
    return [ROOT / item.decode("utf-8") for item in output.split(b"\0") if item]


def main() -> int:
    failures: list[str] = []
    for path in tracked_files():
        relative = path.relative_to(ROOT)
        lowered = {part.lower() for part in relative.parts[:-1]}
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            failures.append(f"forbidden extension: {relative}")
            continue
        if lowered & FORBIDDEN_PARTS:
            failures.append(f"forbidden generated directory: {relative}")
            continue
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() == KNOWN_ROM_SHA256:
            failures.append(f"known EarthBound ROM hash: {relative}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(data):
                failures.append(f"possible credential: {relative}")
                break
    if failures:
        print("Repository audit failed:")
        print("\n".join(f"- {failure}" for failure in failures))
        return 1
    print(f"Repository audit passed: {len(tracked_files())} tracked files, no forbidden payloads found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
