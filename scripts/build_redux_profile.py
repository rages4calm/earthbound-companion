# SPDX-License-Identifier: GPL-3.0-or-later
"""Rebuild an isolated native Redux development profile from the owner's ROM.

The pinned upstream project and repaired CoilSnake/CCScript toolchain must
already be available locally. No ROM, pack, music or player save is downloaded.
Every generated file stays in a new staging directory until checks pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

from apply_rom_patch import apply

USA_SHA256 = "A8FE2226728002786D68C27DDDDF0B90A894DB52E4DFE268FDF72A68CAE5F02E"
REDUX_REVISION = "897d00833f4a08a0a92f106abf631629a6a6a041"
REDUX_ARCHIVE_SHA256 = "DB4E9FB842741FBB2671CD4AF119237442F5AE943ABF765F5D4C79852C856796"
ORIGINAL_PACK_SHA256 = "4E01C943711D32C41E85CB858D9058169E7C8B1739FC7DC0A211E441F9631B9B"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("rom", "redux-source", "coilsnake-python", "native-python",
                   "native-source", "base-assets", "bridge", "output-directory"):
        parser.add_argument("--" + option, required=True, type=Path)
    parser.add_argument("--bundled-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    paths = {key: value.resolve() for key, value in vars(args).items() if isinstance(value, Path)}
    target = paths["output_directory"]
    if target.exists():
        raise RuntimeError("Choose a new output directory; existing profiles and saves are never overwritten.")
    raw = paths["rom"].read_bytes()
    if len(raw) == 3146240:
        raw = raw[512:]
    if len(raw) != 3145728 or hashlib.sha256(raw).hexdigest().upper() != USA_SHA256:
        raise RuntimeError("Use the supported clean EarthBound (USA) ROM. No files were changed.")
    if args.bundled_worker:
        origin = json.loads((paths["redux_source"] / ".redux-source.json").read_text(encoding="utf-8"))
        if origin["archiveSha256"] != REDUX_ARCHIVE_SHA256:
            raise RuntimeError("Redux source archive differs from the pinned build input.")
        revision = origin["revision"]
    else:
        revision = subprocess.run(["git", "-C", str(paths["redux_source"]), "rev-parse", "HEAD"],
                                  capture_output=True, check=True, text=True).stdout.strip()
    if revision != REDUX_REVISION:
        raise RuntimeError("Redux checkout does not match the pinned development profile.")
    bridge = json.loads(paths["bridge"].read_text(encoding="utf-8-sig"))
    if bridge["source"]["revision"] != REDUX_REVISION:
        raise RuntimeError("Bridge does not match the pinned Redux source.")
    project = paths["redux_source"] / "Project"
    for entry in bridge["sourceGraph"]["files"]:
        if sha(project / entry["path"]) != entry["sha256"].upper():
            raise RuntimeError("Redux source differs from the audited compiler input: " + entry["path"])
    if sha(paths["base_assets"]) != ORIGINAL_PACK_SHA256:
        raise RuntimeError("Original asset pack does not match the audited native base.")
    for key in ("coilsnake_python", "native_python"):
        if not paths[key].is_file():
            raise RuntimeError("Python environment is missing: " + str(paths[key]))

    target.parent.mkdir(parents=True, exist_ok=True)
    stage = target.parent / ("." + target.name + "." + uuid.uuid4().hex + ".partial")
    stage.mkdir()
    work = stage / "work"
    work.mkdir()
    started = time.monotonic()
    env = dict(os.environ, PYTHONUTF8="1", PYTHONHASHSEED="0")
    scripts = Path(__file__).resolve().parent

    def run(name: str, command: list[str]) -> None:
        print(json.dumps({"stage": name, "status": "running"}), flush=True)
        with (stage / (name + ".log")).open("wb") as log:
            result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(f"{name} failed. Inspect {stage / (name + '.log')}. No profile was installed.")
        print(json.dumps({"stage": name, "status": "passed"}), flush=True)

    def worker(name: str, arguments: list[str], source_command: list[str]) -> list[str]:
        if args.bundled_worker:
            entry = [] if getattr(sys, 'frozen', False) else [str(scripts / "redux_setup_entry.py")]
            return [str(paths["coilsnake_python"]), *entry, "--worker", name, *arguments]
        return source_command

    try:
        shutil.copytree(project, work / "Project")
        base = work / "expanded-base.sfc"
        patch = paths["redux_source"] / "Patches" / "FixedPSIAnims.bps"
        # The pinned project's FixedPSIAnims.bps actually carries an IPS
        # header. Detect bytes, then verify the expanded result against the
        # audited base hash; the filename does not establish the format.
        patched, patch_format = apply(raw, patch.read_bytes())
        base.write_bytes(patched)
        run("expand-base", worker("expand", [str(base)], [str(paths["coilsnake_python"]), "-X", "utf8", "-c",
            "import sys;from coilsnake.model.common.blocks import Rom;"
            "r=Rom();r.from_file(sys.argv[1]);r.expand(0x600000);r.to_file(sys.argv[1])", str(base)]))
        if sha(base) != bridge["roms"]["base"]["sha256"].upper():
            raise RuntimeError("Expanded PSI base differs from the audited input.")
        compiled = work / "compiled-redux.sfc"
        compile_args=["compile", str(work / "Project"), str(base), str(compiled), "--ccscript-offset", "F31000"]
        run("compile-redux", worker("compile", compile_args, [str(paths["coilsnake_python"]), "-X", "utf8", "-c",
            "from coilsnake.ui.cli import main;main()", "compile", str(work / "Project"),
            str(base), str(compiled), "--ccscript-offset", "F31000"]))
        if sha(compiled) != bridge["roms"]["compiled"]["sha256"].upper():
            raise RuntimeError("Compiler output differs from the audited Redux ROM. Conversion was stopped.")
        dialogue = work / "dialogue"
        common = ["--bridge", str(paths["bridge"]), "--project", str(work / "Project"),
                  "--compiled-rom", str(compiled), "--native-source", str(paths["native_source"])]
        run("convert-dialogue", worker("dialogue", [*common, "--output-dir", str(dialogue)], [str(paths["native_python"]), "-X", "utf8",
            str(scripts / "maternalbound_dialogue.py"), *common, "--output-dir", str(dialogue)]))
        pack_args=[*common, "--base-assets", str(paths["base_assets"]), "--converted-directory", str(dialogue), "--output", str(stage / "assets.pak")]
        run("convert-pack", worker("pack", pack_args, [str(paths["native_python"]), "-X", "utf8",
            str(scripts / "build_maternalbound_pack.py"), *common, "--base-assets", str(paths["base_assets"]),
            "--converted-directory", str(dialogue), "--output", str(stage / "assets.pak")]))
        audit_args=["--assets", str(stage / "assets.pak"), "--native-source", str(paths["native_source"]), "--output", str(stage / "movement-audit.json")]
        run("audit-movement", worker("movement", audit_args, [str(paths["native_python"]), "-X", "utf8",
            str(scripts / "audit_redux_movement.py"), "--assets", str(stage / "assets.pak"),
            "--native-source", str(paths["native_source"]), "--output", str(stage / "movement-audit.json")]))
        shutil.copy2(dialogue / "dialogue-report.json", stage / "dialogue-report.json")
        record = {"format": "native-redux-local-profile-v1", "status": "development-only",
                  "contentId": "maternalbound-redux-897d0083", "sourceRevision": revision,
                  "ownerRomSha256": USA_SHA256, "baseRomSha256": sha(base),
                  "basePatchFormat": patch_format,
                  "compiledRomSha256": sha(compiled), "assetPackSha256": sha(stage / "assets.pak"),
                  "fullPlaythroughVerified": False, "elapsedSeconds": round(time.monotonic() - started, 2),
                  "limits": ["Requires a development executable and explicit --allow-redux-development.",
                             "Structural conversion does not establish full MaternalBound parity.",
                             "No player game files or saves were replaced."]}
        (stage / "profile.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        # This exact private staging subtree was created above. Generated ROMs
        # and duplicate source copies are unnecessary once the pack is checked.
        if work.parent != stage or stage.parent != target.parent:
            raise RuntimeError("Unexpected cleanup path.")
        shutil.rmtree(work)
        stage.rename(target)
        print(json.dumps({"status": "built-development-profile", "directory": str(target),
                          "assetPackSha256": record["assetPackSha256"]}), flush=True)
    except Exception:
        print(json.dumps({"status": "failed", "diagnostics": str(stage), "installed": False}), flush=True)
        raise


if __name__ == "__main__":
    main()
