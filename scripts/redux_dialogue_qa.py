"""Exercise production Redux shops, Goods, equipment and Status with isolated saves."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from PIL import Image


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("native-exe","assets","scratch"):
        parser.add_argument("--"+name,required=True,type=Path)
    args=parser.parse_args()
    exe,pak,scratch=(p.resolve() for p in (args.native_exe,args.assets,args.scratch))
    env=dict(os.environ,SDL_VIDEODRIVER="dummy",SDL_AUDIODRIVER="dummy")
    results=[]

    def run(name,actions,frames,*,dialogue=None,restore=None,expected=(),render=True):
        folder=scratch/name;folder.mkdir(parents=True,exist_ok=True)
        for old in (folder/"saves").glob("quicksave_*.bin.*"):
            if old.is_file(): old.unlink()
        if restore:
            shutil.copytree(restore/"saves",folder/"saves",dirs_exist_ok=True)
            if (restore/"fixture.srm").exists(): shutil.copyfile(restore/"fixture.srm",folder/"fixture.srm")
        config=folder/"fixture.ini"
        config.write_text("companion=1\nfullscreen=0\nwidth=1920\nheight=1080\n",encoding="utf-8")
        replay=folder/"input.replay"
        replay.write_text("\n".join(f"{f} {pad}" for t,button in actions if t<frames
                                    for f,pad in ((t,button),(t+1,"0000"))),encoding="utf-8")
        base=[str(exe),"--assets",str(pak),"--session-dir",str(folder),"--save",str(folder/"fixture.srm"),
              "--config",str(config),"--allow-redux-development","--skip-intro"]
        fixture=["--redux-dialogue-fixture",hex(dialogue)] if dialogue else ["--redux-world-fixture"]
        if restore: fixture=["--load-state"]
        command=base+fixture+["--headless","--input-script",str(replay),"--frames",str(frames+2),"--capture-state",str(frames)]
        proc=subprocess.run(command,env=env,capture_output=True,timeout=30)
        log=(proc.stdout+proc.stderr).decode(errors="replace");(folder/"replay.log").write_text(log,encoding="utf-8")
        if proc.returncode or re.search(r"FATAL|unimplemented|unknown opcode|unknown bank|ERROR",log,re.I):
            raise RuntimeError(f"{name} failed: {log[-2000:]}")
        for value in expected:
            if value not in log: raise RuntimeError(f"{name} missing {value!r}: {log[-2000:]}")
        if render:
            proc=subprocess.run(base+["--load-state","--windowed","--frames","20","--dump-frame","10"],
                                env=env,capture_output=True,timeout=30)
            (folder/"render.log").write_bytes(proc.stdout+proc.stderr)
            if proc.returncode: raise RuntimeError(f"{name} cold render failed")
            with Image.open(folder/"screenshot.bmp") as source:
                if source.size!=(1920,1080) or len(source.convert("RGB").getcolors(source.width*source.height))<10:
                    raise RuntimeError(f"{name} empty or wrong-size render")
                source.save(folder/"gameplay.png")
        results.append({"test":name,"passed":True,"checks":list(expected),"coldRender1080p":render})
        print(json.dumps({"test":name,"passed":True}),flush=True)
        return folder

    confirms=[(t,"0020") for t in range(30,1500,30)]
    run("shop-buy",confirms,600,dialogue=0xC5D24B,expected=(
        "PC replay inventory: 17 2 88 17 0", "cash=9982", "PC replay equipment: 1 0 0 0 stats=84/"))
    run("shop-equip-purchase",confirms,800,dialogue=0xC5D24B,expected=(
        "PC replay inventory: 17 2 88 17 0", "cash=9982", "PC replay equipment: 4 0 0 0 stats=84/"))
    run("shop-sell-old-weapon",confirms,1000,dialogue=0xC5D24B,expected=(
        "PC replay inventory: 2 88 17 0", "cash=9991", "PC replay equipment: 3 0 0 0 stats=84/"))
    run("shop-cancel",[(t,"8000") for t in range(30,1500,30)],1500,dialogue=0xC5D24B,render=False,
        expected=("Redux dialogue fixture C5D24B completed", "Redux dialogue result: cash=10000 weapon=1 inventory=17,2,88,0"))
    goods=[(10,"0040")]+[(t,"0020") for t in range(70,600,50)]
    run("goods-populated",goods,210,expected=("[1:Use] [2:Give] [3:Drop] [4:Help!]","Cracked bat","Teddy bear","Cookie"))
    run("goods-use-unequip",goods,260,expected=("PC replay equipment: 0 0 0 0 stats=80/",))
    unequipped=run("goods-use-finish",goods,600,expected=("PC replay equipment: 0 0 0 0 stats=80/","PC replay modes: 61"))
    run("goods-use-reequip",goods,600,restore=unequipped,expected=("PC replay equipment: 1 0 0 0 stats=84/",))
    equipment=[(10,"0040"),(30,"0100"),(70,"0020"),(120,"0020"),(170,"0020")]
    run("equipment-list",equipment,230,expected=("title=Weapons","[65535:None]","title=Status","title=Resistances"))
    run("equipment-none",equipment+[(220,"0400"),(270,"0020")],450,expected=("PC replay equipment: 0 0 0 0 stats=80/",))
    run("status-psi",[(10,"0040"),(30,"0400"),(50,"0100"),(90,"0020"),(140,"0020")],450,
        expected=("[1:Offense] [2:Recover] [3:Assist] [4:Other]",))
    report={"status":"development-only","nativeExeSha256":hashlib.sha256(exe.read_bytes()).hexdigest().upper(),
            "packSha256":hashlib.sha256(pak.read_bytes()).hexdigest().upper(),"tests":results,
            "limits":["Isolated production menu and dialogue replays, not a full story playthrough."]}
    (scratch/"results.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__": main()
