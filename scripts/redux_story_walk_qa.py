# SPDX-License-Identifier: GPL-3.0-or-later
"""Replay the Redux opening, house doors, Mom dialogue and outdoor movement.

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
import shutil

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("native-exe", "assets", "scratch"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--opening-session", type=Path, help="Copy an already verified opening; its source saves stay untouched.")
    args = parser.parse_args()
    exe, pak, scratch = (p.resolve() for p in (args.native_exe, args.assets, args.scratch))
    if scratch.exists():
        raise ValueError("Use a fresh isolated verification directory.")
    scratch.mkdir(parents=True)
    session = scratch / "session"
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    if args.opening_session:
        source = args.opening_session.resolve()
        opening = json.loads((source / "results.json").read_text(encoding="utf-8-sig"))
        if (opening["nativeExeSha256"] != hashlib.sha256(exe.read_bytes()).hexdigest().upper()
                or opening["assetPackSha256"] != hashlib.sha256(pak.read_bytes()).hexdigest().upper()
                or not opening["selectTogglesNamingAlphabet"]):
            raise ValueError("Opening source does not match this exact executable/content and naming test")
        session.mkdir()
        shutil.copytree(source / "saves", session / "saves")
        shutil.copy2(source / "fixture.srm", session / "fixture.srm")
    else:
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
        # --frames includes synchronous map-setup frames as well as main-loop
        # replay frames. Leave room for the checkpoint to run after door loads.
        run = subprocess.run(base + ["--headless", "--input-script", str(replay), "--frames", str(frame + 300),
                                    "--capture-state", str(frame)], env=env, capture_output=True, timeout=60)
        output = run.stdout + run.stderr
        (scratch / (name + ".log")).write_bytes(output)
        text = output.decode(errors="replace")
        match = re.search(r"party=1 position=(-?\d+),(-?\d+) level=1 HP=30", text)
        stack = re.search(r"PC replay modes: ([0-9 ]+)", text)
        if run.returncode or not match or not stack or "PC replay name 1: IIIiiI" not in text:
            raise RuntimeError(f"{name} failed (exit {run.returncode}): " + text[-1500:])
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
    # Release before the arrival animation completes, so this test walks
    # deliberately through one door instead of holding through return doors.
    step("stairs-down", [(20, 0x0200), (180, 0)], 700, (7472, 336), [61], "offset=0x04CF")
    position, modes, text = step("living-room-walk", [(20, 0x0400), (32, 0), (60, 0x0100), (136, 0)],
                                 300, (7577, 352), [61])
    # Mom is NPC 15 in the pinned upstream npc_config_table.yml and wanders.
    # Observe her real position and approach with normal inputs; faster door
    # timing must not be mistaken for an NPC/dialogue failure in a fixed replay.
    for approach in range(1, 31):
        mom = re.search(r"PC replay NPC: id=15 position=(-?\d+),(-?\d+)", text)
        if not mom:
            raise RuntimeError("Mom's real NPC was not present in the loaded room")
        mx, my = map(int, mom.groups())
        dx, dy = mx - 18 - position[0], my - position[1]
        if abs(dx) > 3:
            pad = 0x0100 if dx > 0 else 0x0200
            length = min(12, max(1, round(abs(dx) / 1.4375)))
            rows = [(20, pad), (20 + length, 0)]
        elif abs(dy) > 3:
            pad = 0x0400 if dy > 0 else 0x0800
            length = min(12, max(1, round(abs(dy) / 1.4375)))
            rows = [(20, pad), (20 + length, 0)]
        else:
            rows = [(20, 0x0100), (22, 0), (35, 0x0020), (36, 0)]
        position, modes, text = step(f"mom-approach-{approach}", rows, 120)
        if "title=Mom" in text:
            step("mom-talk", [], 400, modes=[61, 33, 28, 6])
            break
        if modes != [61]:
            raise RuntimeError("Approach interacted with another NPC; inspect the replay log")
    else:
        raise RuntimeError("Normal-input approach did not reach Mom")
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
    step("bedroom-return", [(20, 0x0200), (130, 0)], 300, (7656, 1000), [61], "offset=0x0615")
    step("stairs-return", [(20, 0x0200), (180, 0)], 400, (7472, 336), [61], "offset=0x04CF")
    position, _, _ = step("front-door-approach", [(20, 0x0400), (80, 0), (100, 0x0100), (450, 0)], 700, modes=[61])
    for hallway_try in range(1, 13):
        if position[0] >= 7795:
            break
        position, _, _ = step(f"front-door-clear-path-{hallway_try}", [(20, 0x0100), (140, 0)], 220, modes=[61])
    else:
        raise RuntimeError("Could not walk past the moving NPCs toward the front door")
    for align_try in range(1, 8):
        difference = 7800 - position[0]
        if abs(difference) <= 2:
            break
        length = max(1, min(8, round(abs(difference) / 1.4375)))
        pad = 0x0100 if difference > 0 else 0x0200
        position, _, _ = step(f"front-door-align-{align_try}", [(20, pad), (20 + length, 0)], 100, modes=[61])
    for door_try in range(1, 33):
        position, modes, text = step(f"front-door-{door_try}", [(20, 0x0800), (23, 0)], 150, modes=[61])
        if position[0] < 4000:
            if "flag_id=467 flag_value=0 expected=0 -- OK" not in text:
                raise RuntimeError("Front-door story flag was not checked by the real transition")
            break
    else:
        raise RuntimeError("Deliberate front-door input did not reach the outdoors")
    render("outside-house")
    # Move away from the arrival door after releasing the transition input.
    step("outside-walk", [(20, 0x0400), (32, 0)], 200, modes=[61])
    record = {
        "format": "maternalbound-native-story-walk-v1", "Passed": True,
        "NativeExeSha256": hashlib.sha256(exe.read_bytes()).hexdigest().upper(),
        "AssetPackSha256": hashlib.sha256(pak.read_bytes()).hexdigest().upper(),
        "OrdinaryButtonInputOnly": True, "FreshProcessRestoreBetweenCheckpoints": True,
        "RenderResolution": [1920, 1080], "MomDialogueAdvances": attempt,
        "Checkpoints": checkpoints, "FullPlaythroughVerified": False,
        "Limits": ["Naming, house interactions and initial outdoor movement only; no combat or later story progression.",
                   "A passing protected seed or opening is not proof of a complete randomized playthrough."],
    }
    (scratch / "results.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
