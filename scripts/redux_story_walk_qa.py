# SPDX-License-Identifier: GPL-3.0-or-later
"""Replay the Redux opening, house doors, Mom dialogue and clothes change.

Uses ordinary button input and fresh-process restores. No story flags, party
positions or ROM data are injected. All saves remain inside a new scratch dir.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("native-exe", "assets", "scratch"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    exe, pak, scratch = (p.resolve() for p in (args.native_exe, args.assets, args.scratch))
    if scratch.exists():
        raise ValueError("Use a fresh isolated verification directory.")
    scratch.mkdir(parents=True)
    session = scratch / "session"
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    opening = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("redux_gameplay_qa.py")),
         "--native-exe", str(exe), "--assets", str(pak), "--scratch", str(session), "--mixed-case-fixture"],
        env=env, capture_output=True, timeout=120,
    )
    (scratch / "opening.log").write_bytes(opening.stdout + opening.stderr)
    if opening.returncode:
        raise RuntimeError("Opening failed: " + opening.stderr.decode(errors="replace")[-1500:])
    config = session / "fixture.ini"
    config.write_text("companion=1\nfullscreen=0\nwidth=1920\nheight=1080\n", encoding="utf-8")
    base = [str(exe), "--assets", str(pak), "--session-dir", str(session),
            "--save", str(session / "fixture.srm"), "--config", str(config),
            "--allow-redux-development", "--skip-intro", "--load-state"]
    checkpoints = []

    def step(name, rows, frame, position=None, modes=None, door=None):
        replay = session / "walk.replay"
        replay.write_text("\n".join(f"{f} {pad:04X}" for f, pad in rows) + "\n", encoding="ascii")
        run = subprocess.run(base + ["--headless", "--input-script", str(replay), "--frames", str(frame + 2),
                                    "--capture-state", str(frame)], env=env, capture_output=True, timeout=60)
        output = run.stdout + run.stderr
        (scratch / (name + ".log")).write_bytes(output)
        text = output.decode(errors="replace")
        match = re.search(r"party=1 position=(-?\d+),(-?\d+) level=1 HP=30", text)
        stack = re.search(r"PC replay modes: ([0-9 ]+)", text)
        if run.returncode or not match or not stack or "PC replay name 1: IIIiiI" not in text:
            raise RuntimeError(name + " failed: " + text[-1500:])
        actual = tuple(map(int, match.groups()))
        actual_modes = list(map(int, stack.group(1).split()))
        if position and actual != position:
            raise RuntimeError(f"{name}: unexpected position {actual}, expected {position}")
        if modes and actual_modes != modes:
            raise RuntimeError(f"{name}: unexpected modes {actual_modes}, expected {modes}")
        if door and door not in text:
            raise RuntimeError(name + ": expected real door transition absent")
        checkpoints.append({"name": name, "position": actual, "modes": actual_modes})
        return actual, actual_modes, text

    def render(name):
        run = subprocess.run(base + ["--windowed", "--frames", "20", "--dump-frame", "10"],
                             env=env, capture_output=True, timeout=60)
        (scratch / (name + "-render.log")).write_bytes(run.stdout + run.stderr)
        if run.returncode:
            raise RuntimeError(name + " cold render failed")
        with Image.open(session / "screenshot.bmp") as frame:
            if frame.size != (1920, 1080) or not frame.convert("RGB").getbbox():
                raise RuntimeError(name + " invalid 1080p frame")
            frame.save(scratch / (name + ".png"))

    step("bedroom-walk", [(20, 0x8000), (21, 0), (90, 0x0200), (280, 0)], 300, (7949, 1143), [61])
    step("bedroom-door-approach", [(20, 0x0100), (43, 0), (70, 0x0800), (120, 0)], 240, (7992, 1097), [61])
    step("bedroom-door", [(20, 0x0400), (28, 0), (50, 0x0200), (74, 0)], 500, (7656, 1000), [61], "offset=0x0615")
    # Holding a direction across a transition really can cross the return door.
    # Check both doors before the single-press descent below.
    step("stairs-round-trip", [(20, 0x0200), (250, 0)], 700, (7448, 1000), [61], "offset=0x01F2")
    step("stairs-down", [(20, 0x0200), (32, 0)], 300, (7472, 336), [61], "offset=0x04CF")
    step("living-room-walk", [(20, 0x0400), (32, 0), (60, 0x0100), (136, 0), (170, 0x0020), (171, 0)], 300, (7577, 352), [61])
    step("mom-approach", [(20, 0x0100), (64, 0), (90, 0x0020), (91, 0)], 200, (7637, 352), [61])
    step("mom-moving-approach", [(20, 0x0100), (34, 0), (55, 0x0020), (56, 0)], 130,
         (7656, 352), [61])
    _, _, text = step("mom-talk", [(20, 0x0400), (32, 0), (60, 0x0100), (74, 0), (90, 0x0020), (91, 0)],
                      400, (7676, 369), [61, 33, 28, 6])
    if "title=Mom" not in text:
        raise RuntimeError("Quick Talk did not reach Mom's real dialogue")
    render("mom-dialogue")
    for attempt in range(1, 13):
        position, modes, _ = step(f"mom-advance-{attempt}", [(20, 0x0020), (21, 0)], 400)
        if modes == [61]:
            if position != (8120, 1104):
                raise RuntimeError("Mom's dialogue ended without the clothes-change warp")
            break
    else:
        raise RuntimeError("Mom's dialogue failed to return to gameplay")
    render("changed-clothes")
    step("clothes-cold-restore", [], 100, (8120, 1104), [61])
    record = {
        "format": "maternalbound-native-story-walk-v1", "Passed": True,
        "NativeExeSha256": hashlib.sha256(exe.read_bytes()).hexdigest().upper(),
        "AssetPackSha256": hashlib.sha256(pak.read_bytes()).hexdigest().upper(),
        "OrdinaryButtonInputOnly": True, "FreshProcessRestoreBetweenCheckpoints": True,
        "RenderResolution": [1920, 1080], "MomDialogueAdvances": attempt,
        "Checkpoints": checkpoints, "FullPlaythroughVerified": False,
        "Limits": ["Naming through Mom's clothes-change event only; no outdoor or combat progression.",
                   "A passing protected seed or opening is not proof of a complete randomized playthrough."],
    }
    (scratch / "results.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
