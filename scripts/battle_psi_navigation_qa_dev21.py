# SPDX-License-Identifier: GPL-3.0-or-later
"""Replay actual native inputs from copied battle-menu F6 data, in scratch only."""
import argparse,json,os,re,shutil,struct,subprocess,sys
from pathlib import Path
from check_jev_observer_parity import latest,local_scratch,sections
from build_maternalbound_pack import read_pack
from battle_action_catalog_qa import digest

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('native-exe','native-source','assets','scratch','owner','layout-log','output'):ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--baseline',action='store_true');ap.add_argument('--only-repaint',action='store_true');a=ap.parse_args()
    scratch=local_scratch(a.scratch);scratch.mkdir(parents=True,exist_ok=False)
    offsets=json.loads(next(s[10:] for s in a.layout_log.read_text(encoding='utf-8').splitlines() if s.startswith('QA_LAYOUT ')))
    sys.path.insert(0,str(a.native_source.resolve()/'src/vendor/tamp'));import tamp
    _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h');psi=assets['data/psi_ability_table.bin']
    rows=[]
    for cat,actions in ((0,()),(1,((50,0x80),)),(2,((10,0x400),(50,0x80))),(3,((10,0x400),(30,0x400),(50,0x80)))):
        if a.only_repaint and cat:continue
        dest=scratch/str(cat);dest.mkdir();shutil.copytree(a.owner/'saves',dest/'saves')
        replay=dest/'input.replay';replay.write_text('\n'.join(f'{f} {mask:04x}' for t,key in actions for f,mask in ((t,key),(t+2,0)))+'\n',encoding='utf-8')
        cfg=dest/'fixture.ini';cfg.write_text('companion=1\nfullscreen=0\nwidth=1920\nheight=1080\nvolume=0\nfast_forward_multiplier=16\n',encoding='utf-8')
        cmd=[str(a.native_exe.resolve()),'--assets',str(a.assets.resolve()),'--session-dir',str(dest.resolve()),'--save',str((dest/'fixture.srm').resolve()),'--config',str(cfg.resolve()),'--allow-redux-development','--skip-intro','--windowed','--fast-forward','--input-script',str(replay.resolve()),'--load-state','--frames','125','--capture-state','100','--dump-frame','105']
        result=subprocess.run(cmd,cwd=dest,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=50)
        log=dest/'native.log';log.write_bytes(result.stdout+result.stderr)
        blobs=sections(latest(dest),tamp);ui=blobs[8];windows={}
        for i in range(8):
            start=offsets['windows']+i*offsets['windowSize'];w=ui[start:start+offsets['windowSize']]
            if not w[offsets['active']]:continue
            items=[]
            for j in range(w[offsets['count']]):
                m=offsets['menu']+j*offsets['menuSize']
                items.append(dict(label=bytes(w[m:m+26]).split(b'\0')[0].decode('ascii',errors='replace'),id=struct.unpack_from('<H',w,m+offsets['userdata'])[0],page=w[m+offsets['itemPage']]))
            windows[w[offsets['id']]]=items
        expected=[i for i in range(1,len(psi)//15) if psi[i*15] and psi[i*15+7] and psi[i*15+7]<=51 and psi[i*15+3]&2 and psi[i*15+2]&(1<<(cat-1))] if cat else [1,2,3]
        actual=[m['id'] for m in windows.get(1 if cat else 16,[]) if m['id']]
        ok=result.returncode==0 and actual==expected and not re.search('FATAL|unimplemented|unknown opcode|ERROR',log.read_text(encoding='utf-8'),re.I)
        rows.append(dict(category=cat,expected=expected,actual=actual,categories=windows.get(16),passed=bool(ok),executableSha256=digest(a.native_exe),screenshotSha256=digest(dest/'screenshot.bmp')))
    report=dict(nativeInputReplay=True,copiedOwnerInput=True,allPassed=all(r['passed'] for r in rows),cases=rows,
        limits=['Actual saved Paula menu with level51; real category navigation, ability IDs and 1080p renderer. Does not cover all ability targeting/action outcomes.'],fullPlaythroughVerified=False)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
    if not a.baseline and not report['allPassed']:raise SystemExit(1)
if __name__=='__main__':main()
