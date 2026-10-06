# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise pinned hotel/rest arrivals and cold-resumed ordinary movement.

Uses the actual native warp transition and the unmodified owner asset packs.
One healthy Ness, NPC/enemy spawning disabled: this is an arrival/movement
fixture, not proof of every hotel purchase or story branch.
"""
import argparse, hashlib, json, os, re, shutil, struct, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from check_jev_observer_parity import latest, local_scratch, sections
from build_maternalbound_pack import read_pack

ROOT=Path(__file__).resolve().parents[1]
PADS=(0x800,0x900,0x100,0x500,0x400,0x600,0x200,0xa00)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('player','observer','original-assets','redux-assets','project','scratch'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--previous',type=Path)
    a=p.parse_args();out=local_scratch(a.scratch)
    if out.exists():raise ValueError('Choose fresh scratch output.')
    out.mkdir(parents=True)
    identities={key:hashlib.sha256(path.read_bytes()).hexdigest() for key,path in
                [('player',a.player),('observer',a.observer)]}
    sys.path.insert(0,str(ROOT/'native-source/src/vendor/tamp'));import tamp
    source=a.project/'ccscript/data/data_48.ccs';text=source.read_text(encoding='utf-8-sig')
    ids=sorted(set(map(int,re.findall(r'^\s*warp\((\d+)\)',text,re.M))))
    if ids!=[2,11,13,14,17,19,39,43,49,50,54,162]:raise ValueError('Re-review the changed rest source.')
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    rows=[]
    def execute(exe,pak,d,warp=None,start=None,pad=0):
        d.mkdir()
        if start:shutil.copytree(start/'saves',d/'saves')
        (d/'settings.dat').write_bytes(b'EBST'+bytes([5,1,0,0,0,0,0,0,0,0,1,0]))
        (d/'fixture.ini').write_text('companion=1\nwidth=640\nheight=480\nvolume=0\nno_dad_calls=1\nno_homesickness=1\nfast_forward_multiplier=16\n')
        # Only move far enough to leave the bed. Holding a direction for
        # hundreds of frames can enter/exit nearby doors and tests a different
        # scenario; leave those routes to the door/progression harness.
        (d/'input.replay').write_text(f'0 0\n10 {pad:04x}\n30 0\n')
        cmd=[str(exe.resolve()),'--assets',str(pak.resolve()),'--session-dir',str(d),
             '--save',str(d/'fixture.srm'),'--config',str(d/'fixture.ini'),
             '--allow-redux-development','--fast-forward','--input-script',str(d/'input.replay'),
             '--frames','580','--capture-state','400']
        cmd+=['--load-state'] if start else ['--teleport-fixture',str(warp)]
        proc=subprocess.run(cmd,cwd=d,env=env,capture_output=True,timeout=45)
        log=proc.stdout+proc.stderr;(d/'native.log').write_bytes(log)
        if proc.returncode or b'PC replay checkpoint:' not in log:
            raise RuntimeError((d.name,proc.returncode,log[-1200:]))
        if warp is not None and f'Teleport fixture {warp} completed'.encode() not in log:
            raise RuntimeError('Native warp failed to return: '+d.name)
        s=sections(latest(d),tamp)
        return [struct.unpack_from('<H',s[2],o)[0] for o in (130,134)],struct.unpack_from('<H',s[2],142)[0]

    def batch(edition,engine,exe,pak):
        _,_,assets=read_pack(pak,ROOT/'native-source/src/data/runtime_generated/asset_ids.h')
        table=assets['data/teleport_destination_table.bin'];results=[]
        for dest in ids:
            d=out/f'{edition}-{engine}-{dest}'
            xy,style=execute(exe,pak,d,warp=dest)
            expected=[v*8 for v in struct.unpack_from('<HH',table,dest*8)]
            # overWorld surface selection: normal=0, Redux slower=6,
            # original slowest=10. Destination 54 starts on that terrain.
            if xy!=expected or style not in (0,6,10):
                raise RuntimeError(('Arrival mismatch',dest,xy,expected,style))
            paths=[]
            for direction,pad in enumerate(PADS):
                end,endstyle=execute(exe,pak,out/(d.name+f'-dir{direction}'),start=d,pad=pad)
                moved=max(abs(end[i]-xy[i]) for i in (0,1))
                paths.append({'direction':direction,'position':end,'distance':moved,'style':endstyle})
            escaped=any(row['distance']>=8 and row['style'] in (0,6,10) for row in paths)
            row={'edition':edition,'engine':engine,'destination':dest,'arrival':xy,
                 'arrivalStyle':style,'transitionReturned':True,'coldResumeEscaped':escaped,'paths':paths,'passed':escaped}
            if a.previous and edition=='redux' and engine=='player':
                oldpaths=[]
                for direction,pad in enumerate(PADS):
                    end,oldstyle=execute(a.previous,pak,out/(d.name+f'-previous{direction}'),start=d,pad=pad)
                    oldpaths.append({'direction':direction,'position':end,'style':oldstyle})
                row['previousPaths']=oldpaths
                row['previousTrapped']=all(v['position']==xy for v in oldpaths)
            results.append(row);print(d.name+': '+('PASS' if escaped else 'FAIL'),flush=True)
        return results
    tasks=[(ed,engine,exe,pak) for ed,pak in [('original',a.original_assets),('redux',a.redux_assets)]
           for engine,exe in [('player',a.player),('observer',a.observer)]]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(lambda task:batch(*task),tasks):rows.extend(result)
    if identities!={key:hashlib.sha256(path.read_bytes()).hexdigest() for key,path in
                     [('player',a.player),('observer',a.observer)]}:
        raise RuntimeError('Runtime changed during the catalog audit; rerun against immutable binaries.')
    report={'Passed':all(row['passed'] for row in rows),'RestDestinations':len(ids),'ArrivalCases':len(rows),
            'ColdMovementReplays':len(rows)*8,'Cases':rows,
            'EngineSha256':identities,
            'SourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'FullPlaythroughVerified':False,
            'Limitations':['Prepared arrivals do not exercise purchases, hotel telepathy or zombie story branches.',
                           'Single-party fixtures exclude NPC/enemy collisions; the separate copied owner save covers the reported actual party.']}
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if not report['Passed']:raise SystemExit(1)

if __name__=='__main__':main()
