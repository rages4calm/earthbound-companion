# SPDX-License-Identifier: GPL-3.0-or-later
"""Standalone owner-ROM setup for the isolated native Redux development profile."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import ssl
import sys
import tempfile
import urllib.request
import zipfile

from build_redux_profile import main as build_profile, REDUX_REVISION, REDUX_ARCHIVE_SHA256, USA_SHA256


def source_download_context():
    # A frozen Python can retain its build machine's OpenSSL CA paths, which
    # need not exist on the player's Linux/macOS system. Keep system trust
    # (including locally installed roots), and add the packaged public roots.
    import certifi
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    return context


def download_source(archive):
    print(json.dumps({"stage":"download-source","status":"running"}),flush=True)
    request=urllib.request.Request(
        f"https://codeload.github.com/ShadowOne333/MaternalBound-Redux/zip/{REDUX_REVISION}",
        headers={"User-Agent":"EarthBound-Companion-Redux-Setup"})
    with urllib.request.urlopen(request,timeout=60,context=source_download_context()) as response, archive.open("wb") as output:
        total=0
        while chunk:=response.read(262144):
            total+=len(chunk)
            if total>30_000_000:raise ValueError("Redux source archive exceeds its expected size.")
            output.write(chunk)
    if hashlib.sha256(archive.read_bytes()).hexdigest().upper()!=REDUX_ARCHIVE_SHA256:
        raise ValueError("Redux source download failed its checksum. No profile was installed.")


def run_worker(name, arguments):
    sys.argv=[name,*arguments]
    if name == "expand":
        from coilsnake.model.common.blocks import Rom
        rom=Rom();rom.from_file(arguments[0]);rom.expand(0x600000);rom.to_file(arguments[0])
    elif name == "compile":
        from redux_compile_order import compile_cli
        compile_cli()
    elif name == "dialogue":
        from maternalbound_dialogue import main
        main()
    elif name == "pack":
        from build_maternalbound_pack import main
        main()
    elif name == "movement":
        from audit_redux_movement import main
        main()
    else:
        raise ValueError("Unknown setup worker")


def main():
    if sys.argv[1:]==["--selftest-compiler-order"]:
        from redux_compile_order import compiler_order_selftest
        print(json.dumps(compiler_order_selftest()),flush=True)
        return
    if sys.argv[1:]==["--selftest-source-download"]:
        # ROM-free check of the actual packaged HTTPS path and pinned archive.
        with tempfile.TemporaryDirectory(prefix="redux-download-selftest-") as temporary:
            download_source(Path(temporary)/"source.zip")
        print(json.dumps({"stage":"download-source","status":"passed"}),flush=True)
        return
    if len(sys.argv)>2 and sys.argv[1]=="--worker":
        run_worker(sys.argv[2],sys.argv[3:]);return
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("rom","base-assets","output-directory"):
        parser.add_argument("--"+name,required=True,type=Path)
    parser.add_argument("--source-archive",type=Path,help="Optional checksum-matched pinned archive for offline setup.")
    parser.add_argument("--native-source",type=Path,help=argparse.SUPPRESS)
    parser.add_argument("--bridge",type=Path,help=argparse.SUPPRESS)
    args=parser.parse_args()
    rom=args.rom.resolve();target=args.output_directory.resolve()
    raw=rom.read_bytes()
    if len(raw)==3146240:raw=raw[512:]
    if len(raw)!=3145728 or hashlib.sha256(raw).hexdigest().upper()!=USA_SHA256:
        raise ValueError("Use the supported clean EarthBound (USA) ROM. No profile was changed.")
    if target.exists():
        raise ValueError("That profile already exists. Choose a new output directory; saves are never overwritten.")
    root=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parents[1]))
    native=(args.native_source or root/"native-source").resolve()
    bridge=(args.bridge or root/"research/maternalbound-native-bridge.json").resolve()
    target.parent.mkdir(parents=True,exist_ok=True)
    # The source download is private temporary build input and is removed
    # on exit. Build diagnostics remain in the separate .partial profile.
    with tempfile.TemporaryDirectory(prefix=".redux-source-",dir=target.parent) as temporary:
        work=Path(temporary);archive=args.source_archive
        if archive is None:
            archive=work/"source.zip"
            download_source(archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest().upper()!=REDUX_ARCHIVE_SHA256:
            raise ValueError("Redux source download failed its checksum. No profile was installed.")
        source=work/"source";source.mkdir()
        prefix=f"MaternalBound-Redux-{REDUX_REVISION}"
        with zipfile.ZipFile(archive) as zipped:
            total=0
            for entry in zipped.infolist():
                path=PurePosixPath(entry.filename)
                if path.is_absolute() or ".." in path.parts or any(":" in part or "\\" in part for part in path.parts):
                    raise ValueError("Unsafe source archive path.")
                if len(path.parts)<2 or path.parts[0]!=prefix or path.parts[1] not in ("Project","Patches"):
                    continue
                total+=entry.file_size
                if total>250_000_000:raise ValueError("Expanded source archive exceeds its expected size.")
                destination=source.joinpath(*path.parts[1:])
                if entry.is_dir():destination.mkdir(parents=True,exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    destination.write_bytes(zipped.read(entry))
        # Git's Windows checkout uses CRLF for some CCS files; the pinned
        # archive carries LF. Restore only the exact checksum-matched form
        # in this temporary copy. No source token or player file is changed.
        inventory=json.loads(bridge.read_text(encoding="utf-8-sig"))
        normalized=0
        for entry in inventory["sourceGraph"]["files"]:
            path=source/"Project"/entry["path"];content=path.read_bytes()
            if hashlib.sha256(content).hexdigest().upper()==entry["sha256"].upper():continue
            lf=content.replace(b"\r\n",b"\n")
            variants=(lf,lf.replace(b"\n",b"\r\n"))
            match=next((data for data in variants if hashlib.sha256(data).hexdigest().upper()==entry["sha256"].upper()),None)
            if match is None:raise ValueError("Pinned source differs beyond line endings: "+entry["path"])
            path.write_bytes(match);normalized+=1
        (source/".redux-source.json").write_text(json.dumps({"revision":REDUX_REVISION,"archiveSha256":REDUX_ARCHIVE_SHA256,"lineEndingNormalizations":normalized}),encoding="utf-8")
        print(json.dumps({"stage":"download-source","status":"passed"}),flush=True)
        os.environ["PYTHONUTF8"]="1"
        build_profile(["--rom",str(rom),"--base-assets",str(args.base_assets.resolve()),
            "--redux-source",str(source),"--coilsnake-python",sys.executable,"--native-python",sys.executable,
            "--native-source",str(native),"--bridge",str(bridge),"--output-directory",str(target),"--bundled-worker"])


if __name__=="__main__":
    try:main()
    except Exception as error:
        print(str(error),file=sys.stderr);raise SystemExit(1)
