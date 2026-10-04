"""Run real native cast/credits and cold save restores in isolated sessions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from PIL import Image


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("native-exe","assets","scratch"):
        parser.add_argument("--"+name,required=True,type=Path)
    args=parser.parse_args()
    exe=args.native_exe.resolve(); assets=args.assets.resolve(); scratch=args.scratch.resolve()
    env=dict(os.environ,SDL_VIDEODRIVER="dummy",SDL_AUDIODRIVER="dummy")
    tests=[]
    for part,name in enumerate(("cast","credits","credits-all-photos")):
        directory=scratch/name;directory.mkdir(parents=True,exist_ok=True)
        config=directory/"fixture.ini"
        config.write_text("companion=1\nfullscreen=0\nwidth=1920\nheight=1080\n",encoding="utf-8")
        base=[str(exe),"--assets",str(assets),"--session-dir",str(directory),"--save",str(directory/"fixture.srm"),
              "--config",str(config),"--allow-redux-development"]
        def run(label,options):
            process=subprocess.run(base+options,env=env,capture_output=True,timeout=45)
            log=(process.stdout+process.stderr).decode(errors="replace")
            (directory/(label+".log")).write_text(log,encoding="utf-8")
            if process.returncode: raise RuntimeError(f"{name}/{label} failed: {log[-1200:]}")
            return log
        for label,options in (
            ("complete",["--capture-state","2000"]),
            ("cold-restore-complete",["--load-state"]),
        ):
            log=run(label,["--redux-ending-fixture",str(part),"--headless","--frames","60000"]+options)
            match=re.search(rf"Redux ending fixture {part} completed in (\d+) frames, PASS",log)
            if not match: raise RuntimeError(f"{name}/{label} did not complete within the frame bound")
            if label.startswith("cold") and "Failed" in log: raise RuntimeError("Cold restore was rejected")
            tests.append({"test":name+"-"+label,"frames":int(match[1]),"passed":True})
            if part==2 and label=="complete":
                photos=set(map(int,re.findall(r"Redux credits photograph (\d+) rendered",log)))
                if photos!=set(range(32)): raise RuntimeError(f"Missing photograph branches: {set(range(32))-photos}")
                tests[-1]["photosRendered"]=len(photos)
        run("cold-restore-render",["--load-state","--skip-intro","--windowed","--frames","45","--dump-frame","20"])
        with Image.open(directory/"screenshot.bmp") as image:
            colors=image.convert("RGB").getcolors(image.width*image.height)
            # Credits deliberately use a four-color font/palette. Require
            # substantial visible content rather than an arbitrary color count.
            visible=sum(count for count,color in colors or [] if color!=(0,0,0))
            if image.size!=(1920,1080) or not colors or len(colors)<2 or visible<2000:
                raise RuntimeError(f"{name} cold restore did not render the ending")
            image.save(directory/"ending.png")
            image.resize((960,540)).save(directory/"review.png")
        tests.append({"test":name+"-cold-render","passed":True,"resolution":[1920,1080]})
    record={"status":"development-only","nativeExeSha256":hashlib.sha256(exe.read_bytes()).hexdigest().upper(),
            "assetPackSha256":hashlib.sha256(assets.read_bytes()).hexdigest().upper(),"tests":tests,
            "limitations":["Photograph flags set by an isolated fixture; acquisition through gameplay unverified","No full game playthrough"]}
    (scratch/"results.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(record,indent=2))


if __name__=="__main__":main()
