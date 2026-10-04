"""Run Redux's production title and narration modes with isolated saves."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("native-exe", "assets", "scratch"):
        parser.add_argument("--"+name, required=True, type=Path)
    args = parser.parse_args()
    exe, pak, scratch = (x.resolve() for x in (args.native_exe,args.assets,args.scratch))
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    tests=[]
    cases = [(f"title-{i}", "--redux-title-fixture",i,500,3000) for i in range(2)]
    cases += [(f"narration-{i}","--redux-narration-fixture",i,100 if i<8 else 600,16000) for i in range(10)]
    for name,option,value,frame,budget in cases:
        folder=scratch/name; folder.mkdir(parents=True,exist_ok=True)
        config=folder/"fixture.ini"
        config.write_text("companion=1\nfullscreen=0\nwidth=1920\nheight=1080\n",encoding="utf-8")
        command=[str(exe),"--assets",str(pak),"--session-dir",str(folder),"--save",str(folder/"fixture.srm"),
                 "--config",str(config),"--allow-redux-development",option,str(value),"--windowed",
                 "--frames",str(budget),"--dump-frame",str(frame)]
        process=subprocess.run(command,env=env,capture_output=True,timeout=55)
        log=(process.stdout+process.stderr).decode(errors="replace")
        (folder/"render.log").write_text(log,encoding="utf-8")
        if process.returncode or re.search(r"FATAL|unimplemented|unknown opcode|unknown bank|ERROR",log,re.I):
            raise RuntimeError(f"{name} render failed: {log[-1200:]}")
        with Image.open(folder/"screenshot.bmp") as source:
            image=source.convert("RGB"); colours=len(image.getcolors(image.width*image.height))
            if image.size!=(1920,1080) or colours<(3 if option=="--redux-title-fixture" else 2):
                raise RuntimeError(f"{name} missing presentation: {image.size}, {colours} colours")
            image.save(folder/"presentation.png")
        record={"test":name,"renderResolution":[1920,1080],"colours":colours,"passed":True}
        command=command[:command.index("--windowed")]+["--headless","--frames",str(budget)]
        process=subprocess.run(command,env=env,capture_output=True,timeout=55)
        log=(process.stdout+process.stderr).decode(errors="replace")
        (folder/"completion.log").write_text(log,encoding="utf-8")
        label="title" if option=="--redux-title-fixture" else "narration"
        match=re.search(rf"Redux {label} fixture {value} completed in (\d+) frames, PASS",log)
        if process.returncode or not match:
            raise RuntimeError(f"{name} did not complete: {log[-1200:]}")
        record["completedFrames"]=int(match[1])
        tests.append(record); print(json.dumps(record),flush=True)
    report={"status":"development-only", "nativeExeSha256":hashlib.sha256(exe.read_bytes()).hexdigest().upper(),
            "packSha256":hashlib.sha256(pak.read_bytes()).hexdigest().upper(),"tests":tests,
            "limits":["Production-mode fixtures; full story playthrough is still required."]}
    (scratch/"results.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__": main()
