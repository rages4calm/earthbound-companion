"""Replay Redux's real flag-based Key Items menu with isolated opening saves."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from PIL import Image

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("native-exe","assets","opening-fixture","scratch"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    exe=a.native_exe.resolve();pak=a.assets.resolve();opening=a.opening_fixture.resolve();scratch=a.scratch.resolve()
    env=dict(os.environ,SDL_VIDEODRIVER="dummy",SDL_AUDIODRIVER="dummy")
    cases={
        "down":([(10,"0040"),(12,"0000"),(30,"0400"),(31,"0000")],55,["[10:Keys]"]),
        "pause":([(10,"0040"),(12,"0000")],90,["[2:Goods]","[4:Equip]","[10:Keys]"]),
        "equipment":([(10,"0040"),(12,"0000"),(30,"0100"),(31,"0000"),(70,"0020"),(71,"0000")],180,["title=Status","title=Resistances"]),
        "key-items":([(10,"0040"),(11,"0000"),(30,"0400"),(31,"0000"),(70,"0020"),(71,"0000")],180,["title=Key items","ATM card"]),
    }
    keys=cases["key-items"][0]
    cases["use-help-submenu"]=(keys+[(220,"0020"),(221,"0000")],290,["[1:Use]","[2:Help!]"])
    cases["key-help"]=(keys+[(220,"0020"),(221,"0000"),(260,"0400"),(261,"0000"),(300,"0020"),(301,"0000")],400,["PC replay window 1"])
    cases["key-use"]=(keys+[(220,"0020"),(221,"0000"),(280,"0020"),(281,"0000")],450,["PC replay checkpoint: party=1"])
    results=[]
    for name,(rows,frames,wanted) in cases.items():
        directory=scratch/name;directory.mkdir(parents=True,exist_ok=True)
        # A prior replay writes the other journal slot with a higher sequence.
        # Restore a clean isolated journal, not only its older .0 file.
        if directory.resolve()==opening: raise RuntimeError("Fixture source and destination must differ")
        for old in (directory/"saves").glob("quicksave_*.bin.*"):
            if old.is_file(): old.unlink()
        shutil.copytree(opening/"saves",directory/"saves",dirs_exist_ok=True)
        shutil.copyfile(opening/"fixture.srm",directory/"fixture.srm")
        replay=directory/"input.replay";replay.write_text("\n".join(f"{f} {pad}" for f,pad in rows))
        config=directory/"fixture.ini";config.write_text("companion=1\nfullscreen=0\nwidth=1920\nheight=1080\n")
        base=[str(exe),"--assets",str(pak),"--save",str(directory/"fixture.srm"),"--session-dir",str(directory),"--config",str(config),"--allow-redux-development","--skip-intro","--load-state"]
        proc=subprocess.run(base+["--headless","--input-script",str(replay),"--frames",str(frames+2),"--capture-state",str(frames)],env=env,capture_output=True,timeout=30)
        log=(proc.stdout+proc.stderr).decode(errors="replace");(directory/"replay.log").write_text(log)
        if proc.returncode or any(value not in log for value in wanted):
            raise RuntimeError(f"{name} failed: {log[-2000:]}")
        proc=subprocess.run(base+["--windowed","--frames","30","--dump-frame","10"],env=env,capture_output=True,timeout=30)
        (directory/"render.log").write_bytes(proc.stdout+proc.stderr)
        if proc.returncode: raise RuntimeError(f"{name} render failed")
        with Image.open(directory/"screenshot.bmp") as im: im.save(directory/"menu.png")
        results.append({"test":name,"passed":True,"renderResolution":[1920,1080]})
    (scratch/"results.json").write_text(json.dumps({"status":"development-only",
        "nativeExeSha256":hashlib.sha256(exe.read_bytes()).hexdigest().upper(),
        "assetPackSha256":hashlib.sha256(pak.read_bytes()).hexdigest().upper(),"tests":results},indent=2)+"\n")
    print(json.dumps(results,indent=2))

if __name__=="__main__":main()
