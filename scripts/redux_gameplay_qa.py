"""Isolated native Redux opening fixture; never reads or writes player saves."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
from PIL import Image

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("native-exe","assets","scratch"):
        parser.add_argument("--"+option,required=True,type=Path)
    parser.add_argument("--six-letter-fixture",action="store_true")
    parser.add_argument("--mixed-case-fixture",action="store_true")
    args = parser.parse_args()
    if args.mixed_case_fixture:
        args.six_letter_fixture = True
    exe = args.native_exe.resolve(); pak = args.assets.resolve(); scratch = args.scratch.resolve()
    scratch.mkdir(parents=True,exist_ok=True)
    env = dict(os.environ,SDL_VIDEODRIVER="dummy",SDL_AUDIODRIVER="dummy")
    config = scratch/"fixture.ini"
    config.write_text("companion=1\nfullscreen=0\nwidth=1280\nheight=720\n",encoding="utf-8")
    base = [str(exe),"--assets",str(pak),"--session-dir",str(scratch),"--save",str(scratch/"fixture.srm"),"--config",str(config)]
    def run(name,flags):
        result = subprocess.run(base+flags,env=env,capture_output=True,timeout=55)
        (scratch/(name+".log")).write_bytes(result.stdout+result.stderr)
        if result.returncode:
            raise RuntimeError(f"{name} failed ({result.returncode}): "+result.stderr.decode(errors="replace")[-500:])
        return result.stderr.decode(errors="replace")
    refused = subprocess.run(base+["--headless","--frames","2"],env=env,capture_output=True,timeout=10)
    if refused.returncode != 1 or b"development integration fixture" not in refused.stderr:
        raise RuntimeError("Incomplete Redux pack was not blocked from a normal launch")
    rows=[]
    for frame in range(300,5000,80):
        rows.extend(((frame,"0020"),(frame+2,"0000"),(frame+35,"1000"),(frame+37,"0000")))
    if args.six_letter_fixture:
        rows=[]
        # The first keyboard follows the longer title/file-select transition.
        for frame in (300,460,500,650,670,690,710,730): rows.extend(((frame,"0020"),(frame+2,"0000")))
        for frame in range(780,844,8): rows.extend(((frame,"0100"),(frame+2,"0000")))
        for frame in range(900,1020,20): rows.extend(((frame,"0020"),(frame+2,"0000")))
        if args.mixed_case_fixture:
            for frame in (950,990): rows.extend(((frame,"2000"),(frame+2,"0000")))
        rows.extend(((1100,"1000"),(1102,"0000")))
        for frame in range(1200,10000,650):
            # Naming's introductory prompt accepts a button, before directions
            # can move the keyboard cursor. Advance it before choosing I.
            for offset in (0,160,200): rows.extend(((frame+offset,"0020"),(frame+offset+2,"0000")))
            for offset in range(250,314,8): rows.extend(((frame+offset,"0100"),(frame+offset+2,"0000")))
            for offset in range(350,470,20): rows.extend(((frame+offset,"0020"),(frame+offset+2,"0000")))
            rows.extend(((frame+550,"1000"),(frame+552,"0000")))
    replay = scratch/"opening.replay"
    replay.write_text("\n".join(f"{frame} {pad}" for frame,pad in sorted(rows)),encoding="utf-8")
    log = run("opening",["--allow-redux-development","--headless","--input-script",str(replay),"--frames","12020","--capture-state","12000"])
    if "party=1" not in log or "level=1 HP=30" not in log:
        raise RuntimeError("Redux opening did not reach Ness with the expected starting party/HP: "+log[-500:])
    names=re.findall(r"PC replay name \d: ([^\r\n]*)",log)
    if args.six_letter_fixture and (not names or len(names[0])!=6):
        raise RuntimeError("Keyboard replay did not preserve six letters: "+str(names))
    if args.mixed_case_fixture and names[0] != "IIIiiI":
        raise RuntimeError("Select did not toggle the naming alphabet without erasing letters: "+str(names))
    visual = run("opening-render",["--allow-redux-development","--windowed","--skip-intro","--load-state","--frames","60","--dump-frame","20"])
    if args.six_letter_fixture:
        restored=run("name-restore",["--allow-redux-development","--headless","--skip-intro","--load-state","--frames","35","--capture-state","30"])
        if f"PC replay name 1: {names[0]}" not in restored:
            raise RuntimeError("Six-letter name did not survive a fresh-process quick-save load")
    screenshot = scratch/"screenshot.bmp"
    with Image.open(screenshot) as image:
        if image.convert("RGB").getbbox() is None: raise RuntimeError("Opening rendered a black frame")
        image.save(scratch/"opening.png")
        resolution=image.size
    record={"format":"maternalbound-native-gameplay-fixture-v1","status":"development-only",
        "nativeExeSha256":hashlib.sha256(exe.read_bytes()).hexdigest().upper(),
        "assetPackSha256":hashlib.sha256(pak.read_bytes()).hexdigest().upper(),
        "openingReached":True,"startingParty":1,"startingLevel":1,"startingHp":30,
        "normalLaunchBlocked":True,"renderResolution":resolution,
        "sixLetterKeyboardAndQuicksave":bool(args.six_letter_fixture),
        "selectTogglesNamingAlphabet":bool(args.mixed_case_fixture),
        "limitations":["Opening-only automation", "No full Redux playthrough", "Content-specific randomizer checks run separately"]}
    (scratch/"results.json").write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps(record,indent=2))

if __name__ == "__main__": main()
