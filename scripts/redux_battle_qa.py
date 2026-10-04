"""Replay native battle Goods and Redux's flag-based Tools through real menus.

Every case uses its own session and cold save restore; player saves are unused.
"""
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
    for name in ("native-exe","assets","scratch"): parser.add_argument("--"+name,required=True,type=Path)
    args=parser.parse_args()
    exe,pak,scratch=(p.resolve() for p in (args.native_exe,args.assets,args.scratch))
    env=dict(os.environ,SDL_VIDEODRIVER="dummy",SDL_AUDIODRIVER="dummy")
    tests=[]
    def run(name,actions,frame,*,restore=None,profile=None,required=(),forbidden=(),render=False):
        folder=scratch/name;folder.mkdir(parents=True,exist_ok=True)
        if restore: shutil.copytree(restore/"saves",folder/"saves",dirs_exist_ok=True)
        config=folder/"fixture.ini";config.write_text("companion=1\nfullscreen=0\nwidth=1920\nheight=1080\n",encoding="utf-8")
        replay=folder/"input.replay"
        replay.write_text("\n".join(f"{f} {pad}" for t,button in actions for f,pad in ((t,button),(t+1,"0000"))),encoding="utf-8")
        base=[str(exe),"--assets",str(pak),"--session-dir",str(folder),"--save",str(folder/"fixture.srm"),
              "--config",str(config),"--allow-redux-development","--skip-intro"]
        fixture=["--load-state"] if restore else ["--redux-battle-fixture","1","--redux-battle-fixture-tools",str(profile)]
        result=subprocess.run(base+fixture+["--headless","--input-script",str(replay),"--frames","3500","--capture-state",str(frame)],
                              env=env,capture_output=True,timeout=35)
        log=(result.stdout+result.stderr).decode(errors="replace");(folder/"replay.log").write_text(log,encoding="utf-8")
        if result.returncode or re.search(r"FATAL|unimplemented|unknown opcode|unknown bank|ERROR",log,re.I):
            raise RuntimeError(f"{name}: {log[-2000:]}")
        for text in required:
            if text not in log: raise RuntimeError(f"{name} missing {text!r}: {log[-1800:]}")
        for text in forbidden:
            if text in log: raise RuntimeError(f"{name} retained {text!r}")
        if "savestate: wrote slot" not in log: raise RuntimeError(f"{name} did not reach its snapshot")
        if render:
            result=subprocess.run(base+["--load-state","--windowed","--frames","20","--dump-frame","10"],env=env,capture_output=True,timeout=20)
            (folder/"render.log").write_bytes(result.stdout+result.stderr)
            if result.returncode: raise RuntimeError(f"{name} cold render failed")
            with Image.open(folder/"screenshot.bmp") as source:
                if source.size!=(1920,1080) or len(source.convert("RGB").getcolors(source.width*source.height))<15:
                    raise RuntimeError(f"{name} blank or wrong-size image")
                source.save(folder/"gameplay.png")
        tests.append({"test":name,"passed":True,"checks":list(required),"coldRender1080p":render})
        print(json.dumps({"test":name,"passed":True}),flush=True)
        return folder

    jeff_inputs=[(10,"0100"),(30,"0400"),(70,"0020"),(100,"0100"),(130,"0400"),(170,"0020")]
    tools_open=[(10,"0400"),(40,"0020")]
    def execute_tool(name,committed,action):
        # Poo defends, then real button presses advance action/result text.
        # The production battle loop must enter AND return from Jeff's action.
        actions=[(10,"0100"),(30,"0400"),(70,"0020")]
        actions += [(tick,"0020") for tick in range(120,1900,20)]
        return run(name+"-execute",actions,2000,restore=committed,
                   required=(f"PC replay action start: actor=3 action={action} ",
                             f"PC replay action done: actor=3 action={action} "))
    bases={}
    for profile,name in enumerate(("no-devices","all-devices","paralyzed","immobilized","maid-handoff")):
        intro=run(name+"-intro",[],500,profile=profile,required=("PC replay battle: group=1 enemies=1",))
        ness=run(name+"-ness",[(10,"0020")],120,restore=intro,required=("selected=0", "[2:Goods]"))
        jeff=run(name+"-jeff",jeff_inputs,240,restore=ness,required=("selected=2", "[4:Tools]"))
        required=["title=Tools", "[1:Spy kit]"]
        forbidden=[]
        if profile in (0,2,3): forbidden=["Slime generator", "Heavy bazooka", "Tofu machine"]
        else:
            required.extend(("Slime generator", "Shield killer", "Counter PSI unit", "Neutralizer", "Defense shower", "HP-sucker", "Hungry HP-sucker", "Bazooka", "Heavy bazooka"))
            if profile==4: forbidden=["Tofu machine"]
            else: required.append("Tofu machine")
        tools=run(name+"-tools",tools_open,120,restore=jeff,required=required,forbidden=forbidden,render=True)
        bases[name]=(ness,jeff,tools)
    ness,jeff,tools=bases["all-devices"]
    run("tools-cancel",[(10,"8000")],100,restore=tools,required=("selected=2","[4:Tools]"),forbidden=("title=Tools",))
    spy=run("spy-target",[(10,"0020")],80,restore=tools,required=("PC replay window 38", "PC replay window 49"),render=True)
    run("spy-target-cancel",[(10,"8000")],120,restore=spy,required=("title=Tools","Slime generator"),forbidden=("PC replay window 38",))
    committed=run("spy-target-confirm",[(10,"0020")],150,restore=spy,required=("selected=3","[7:Transform]", "id=3 action=6 argument=231 slot=0 targetting=17"),forbidden=("PC replay window 38",),render=True)
    execute_tool("spy",committed,6)
    for name in ("paralyzed","immobilized"):
        restricted=bases[name][2]
        run(name+"-spy",[(10,"0020")],80,restore=restricted,required=("PC replay window 38","PC replay window 49"))
    # Neutralizer affects all enemies and Defense shower all party members.
    # The selection commits immediately, with no inventory slot consumed.
    for index,name,action,item,targetting in ((4,"neutralizer",247,195,18),(5,"defense-shower",184,157,4),(7,"hungry-sucker",176,136,18),(10,"tofu-machine",170,139,18)):
        actions=[];tick=10
        if index%2: actions.append((tick,"0100"));tick+=25
        for _ in range(index//2): actions.append((tick,"0400"));tick+=25
        actions.append((tick,"0020"))
        committed=run(name+"-commit",actions,tick+100,restore=tools,required=("selected=3","[7:Transform]",f"id=3 action={action} argument={item} slot=0 targetting={targetting}"),forbidden=("PC replay window 38","title=Tools"))
        execute_tool(name,committed,action)
    for index,name,action,item in ((1,"slime",169,138),(2,"shield-killer",160,132),(3,"counter-psi",159,131),(6,"hp-sucker",161,135),(8,"bazooka",310,133),(9,"heavy-bazooka",311,134)):
        actions=[];tick=10
        if index%2: actions.append((tick,"0100"));tick+=25
        for _ in range(index//2): actions.append((tick,"0400"));tick+=25
        actions.append((tick,"0020"))
        target=run(name+"-target",actions,tick+80,restore=tools,required=("PC replay window 38","PC replay window 49"),render=index==9)
        run(name+"-cancel",[(10,"8000")],120,restore=target,required=("title=Tools","Spy kit"),forbidden=("PC replay window 38",))
        committed=run(name+"-confirm",[(10,"0020")],150,restore=target,required=("selected=3",f"id=3 action={action} argument={item} slot=0 targetting=17"),forbidden=("PC replay window 38",))
        execute_tool(name,committed,action)
    goods=run("goods-list",[(10,"0100"),(40,"0020")],110,restore=ness,required=("[1:Cookie] [2:Teddy bear]",))
    cookie=run("goods-cookie-target",[(10,"0020")],100,restore=goods,required=("PC replay window 38","[1:Native] [2:Native] [3:Native] [4:Native]"),render=True)
    run("goods-cookie-cancel",[(10,"8000")],120,restore=cookie,required=("[1:Cookie] [2:Teddy bear]",),forbidden=("PC replay window 38",))
    run("goods-cookie-confirm",[(10,"0020")],150,restore=cookie,required=("selected=1","PC replay inventory: 88 2"),forbidden=("PC replay window 38",))
    report={"status":"development-only","nativeExeSha256":hashlib.sha256(exe.read_bytes()).hexdigest().upper(),
            "packSha256":hashlib.sha256(pak.read_bytes()).hexdigest().upper(),"tests":tests,
            "limits":["Isolated real battle-menu replays and cold restores; no full story playthrough.",
                      "All 11 devices execute and return through the production battle loop; all effect/resistance combinations remain untested."]}
    (scratch/"results.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__": main()
