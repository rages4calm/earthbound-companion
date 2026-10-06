# SPDX-License-Identifier: GPL-3.0-or-later
"""Replay every type-4 stair endpoint in an owner-supplied native asset pack.

Prepares locations with one healthy party member and NPC/enemy spawning off.
Uses ordinary held directional inputs and cold saves through native callbacks.
This catalog coverage is not a story playthrough or a controller hardware test.
"""
import argparse, hashlib, json, os, re, struct, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from check_jev_observer_parity import latest, local_scratch, sections

ROOT=Path(__file__).resolve().parents[1]

def stair_catalog(pak, ids):
    names=re.findall(r'^\s+ASSET_\w+, /\* (.*?) \*/',ids.read_text(encoding='utf-8'),re.M)
    raw=pak.read_bytes(); magic,version,count=struct.unpack_from('<4sII',raw)
    if magic!=b'EBPK' or version!=1 or count!=len(names): raise ValueError('Asset registry mismatch.')
    data={}
    for name in ('maps/door_pointer_table.bin','maps/door_config_table.bin'):
        i=names.index(name);offset,length=struct.unpack_from('<II',raw,44+i*8)
        start=44+count*8+offset
        data[name]=raw[start:start+length]
        if len(data[name])!=length:raise ValueError('Truncated asset pack.')
    ptrs=data['maps/door_pointer_table.bin']; cfg=data['maps/door_config_table.bin'];out=[]
    for sector in range(len(ptrs)//4):
        offset=struct.unpack_from('<I',ptrs,sector*4)[0]-0xCF264F
        if offset<0 or offset+2>len(cfg):continue
        count=struct.unpack_from('<H',cfg,offset)[0]
        if offset+2+count*5>len(cfg):raise ValueError('Truncated door table.')
        for k in range(count):
            y,x,kind,value=struct.unpack_from('<BBBH',cfg,offset+2+k*5)
            if kind==4:
                if value&255 or value>>8>=4:raise ValueError('Unknown stair variant.')
                out.append({'tile':[sector%32*32+x,sector//32*32+y],'variant':value>>8})
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('engine','assets','scratch'):p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--redux',action='store_true')
    p.add_argument('--workers',type=int,default=4)
    a=p.parse_args(); output=local_scratch(a.scratch)
    if output.exists():raise ValueError('Choose a fresh scratch directory.')
    output.mkdir(parents=True)
    sys.path.insert(0,str(ROOT/'native-source/src/vendor/tamp'))
    import tamp
    exe=a.engine.resolve();pak=a.assets.resolve()
    rows=stair_catalog(pak,ROOT/'native-source/src/data/runtime_generated/asset_ids.h')
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')

    def execute(folder, actions, frames, start=None):
        if start:
            folder.mkdir()
        elif not (folder/'saves').is_dir():
            raise ValueError('A cold replay needs its own saved checkpoint.')
        (folder/'fixture.ini').write_text('companion=1\nwidth=640\nheight=480\nvolume=0\nfast_forward_multiplier=16\n',encoding='utf-8')
        # Valid engine preference blob: default speed, no costly visual effects.
        (folder/'settings.dat').write_bytes(b'EBST'+bytes([5,1,0,0,0,0,0,0,0,0,1,0]))
        (folder/'input.replay').write_text('0 0\n'+''.join(f'{f} {mask:04x}\n' for f,mask in actions),encoding='utf-8')
        cmd=[str(exe),'--assets',str(pak),'--session-dir',str(folder),'--save',str(folder/'fixture.srm'),
             '--config',str(folder/'fixture.ini'),'--allow-redux-development','--fast-forward',
             '--input-script',str(folder/'input.replay'),'--frames',str(frames+160)]
        if start:
            cmd+=['--stairs-fixture',str(start[0]),str(start[1]),'--capture-state',str(frames)]
        else:cmd+=['--load-state','--stairs-stop-at-landing']
        proc=subprocess.run(cmd,cwd=folder,env=env,capture_output=True,timeout=40)
        (folder/'native.log').write_bytes(proc.stdout+proc.stderr)
        if proc.returncode:raise RuntimeError((folder.name,proc.returncode,proc.stderr[-1200:]))
        marker=b'PC replay checkpoint:' if start else b'Stair landing completed at '
        if marker not in proc.stderr or b'savestate: wrote slot' not in proc.stderr:
            raise RuntimeError('Requested checkpoint was not captured: '+folder.name)
        s=sections(latest(folder),tamp)
        return s

    def case(index,row):
        v=row['variant']; tx,ty=row['tile'];x,y=tx*8,ty*8
        start=(x+16 if v%2==0 else x-8,y+8 if v<2 else y)
        # Horizontal cardinal input heads toward the stair from its landing.
        mask=0x200 if v%2==0 else 0x100
        root=output/f'endpoint-{index:03d}'
        mid=execute(root,[(10,mask)],24,start)
        import shutil
        endroot=output/f'endpoint-{index:03d}-cold'
        endroot.mkdir();shutil.copytree(root/'saves',endroot/'saves')
        end=execute(endroot,[(10,mask)],900)
        visited=[struct.unpack_from('<hhBBBB',s[11],i*8) for s in (mid,end) for i in range(256)]
        position=[struct.unpack_from('<H',end[2],off)[0] for off in (130,134)]
        style=struct.unpack_from('<H',end[2],142)[0]
        entered=any(entry[3]==13 for entry in visited) or struct.unpack_from('<H',mid[2],142)[0]==13
        resumed_from=[struct.unpack_from('<H',mid[2],off)[0] for off in (130,134)]
        resumed_motion=max(abs(position[i]-resumed_from[i]) for i in range(2))
        mid_style=struct.unpack_from('<H',mid[2],142)[0]
        result={'endpoint':index,'variant':v,'tile':[tx,ty],'position':position,
                'enteredStairs':entered,'coldCheckpointStyle':mid_style,
                'coldResumeCompleted':style==0 and resumed_motion>8,
                'passed':entered and style==0 and resumed_motion>8}
        if not result['passed']:print(json.dumps(result),flush=True)
        return result

    results=[]
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for result in pool.map(lambda pair:case(*pair),enumerate(rows)):
            results.append(result)
            if len(results)%12==0:print(f'{len(results)}/{len(rows)} endpoints checked',flush=True)
    report={'Passed':all(r['passed'] for r in results),'Edition':'redux' if a.redux else 'original',
            'EndpointCount':len(rows),'VariantCounts':{str(v):sum(r['variant']==v for r in rows) for v in range(4)},
            'Cases':results,'EngineSha256':hashlib.sha256(exe.read_bytes()).hexdigest(),
            'ColdStairCheckpoints':sum(r['coldCheckpointStyle']==13 for r in results),
            'AssetSha256':hashlib.sha256(pak.read_bytes()).hexdigest(),'FullPlaythroughVerified':False,
            'Limits':['Prepared maps with NPC/enemy spawning disabled; one party member.',
                      'One horizontal cardinal approach per endpoint; no-input pause and cold resume.',
                      'Stops at the first actual stair exit; verifies the native leave callback returned free walking.',
                      'Story appearance conditions and physical controller hardware are not covered.']}
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if not report['Passed']:sys.exit(1)

if __name__=='__main__':main()
