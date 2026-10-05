# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify the installed MSU pack and native Redux audio transitions in isolation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("native-exe", "assets", "msu-dir", "msu-manifest", "scratch"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    exe, pak, directory, manifest, scratch = (
        p.resolve() for p in (args.native_exe, args.assets, args.msu_dir, args.msu_manifest, args.scratch)
    )
    if scratch.exists():
        raise ValueError("Use a fresh isolated diagnostic directory.")
    scratch.mkdir(parents=True)
    tracks = json.loads(manifest.read_text(encoding="utf-8-sig"))
    for track in tracks:
        path = directory / track["name"]
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "md5").hexdigest()
        if path.stat().st_size != int(track["size"]) or digest.lower() != track["md5"].lower():
            raise ValueError("Soundtrack checksum mismatch: " + track["name"])
    if len(tracks) != 164 or (directory / "eb_msu1-11.pcm").exists():
        raise ValueError("This diagnostic requires the pinned 164-track soundtrack.")
    result = subprocess.run(
        [str(exe), "--assets", str(pak), "--session-dir", str(scratch), "--save", str(scratch / "fixture.srm"),
         "--selftest-redux-audio", "--msu-dir", str(directory), "--msu-name", "eb_msu1"],
        env=dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy"),
        capture_output=True, timeout=60,
    )
    log = result.stdout + result.stderr
    (scratch / "audio.log").write_bytes(log)
    output = log.decode(errors="replace")
    recordings = re.findall(
        r"Redux Sound Stone SPC-to-MSU (\d+): acknowledged stop, echo peak=(\d+), (\d+) PCM frames, PASS", output
    )
    pack = re.search(
        r"MSU installed pack: (\d+) tracks, (\d+) loop boundaries, (\d+) one-shot ends, (\d+) missing fallbacks, PASS", output
    )
    effect = re.search(r"Redux MSU retains SPC effects: peak=(\d+), PASS", output)
    if (result.returncode or "FAIL" in output or not pack or not effect
        or {int(row[0]) for row in recordings} != set(range(160, 168))
        or "Redux MSU transitions: 8 Sound Stone recordings, SPC fallback, PASS" not in output):
        raise RuntimeError("Native MSU diagnostic failed: " + output[-2200:])
    covered, loops, one_shots, missing = map(int, pack.groups())
    if covered != len(tracks) or loops + one_shots != covered or covered + missing != 191:
        raise RuntimeError("Native MSU coverage counts disagree with the verified manifest.")
    record = {
        "status": "development-only", "passed": True,
        "nativeExeSha256": hashlib.sha256(exe.read_bytes()).hexdigest().upper(),
        "packSha256": hashlib.sha256(pak.read_bytes()).hexdigest().upper(),
        "msuManifestSha256": hashlib.sha256(manifest.read_bytes()).hexdigest().upper(),
        "soundtrackChecksumsVerified": len(tracks),
        "soundStoneTransitions": [
            {"track": int(track), "residualEchoPeak": int(peak), "pcmFrames": int(frames)}
            for track, peak, frames in recordings
        ],
        "spcEffectPeak": int(effect.group(1)), "spcFallbackTrack": 11,
        "msuTracks": covered, "loopBoundaryChecks": loops, "oneShotEndChecks": one_shots,
        "missingTracks": missing,
        "limits": [
            "File checks and native loop/end checks do not replace soundtrack listening.",
            "Eight Sound Stone transitions, one SPC effect and one missing-track fallback are covered; every story audio transition remains unverified.",
        ],
    }
    (scratch / "results.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
