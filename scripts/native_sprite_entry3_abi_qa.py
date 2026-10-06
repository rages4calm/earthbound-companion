# SPDX-License-Identifier: GPL-3.0-or-later
"""Real C0A4A8 dispatcher return and transient frame-zero source checks.

Links an unchanged frozen native library. The frame-zero upload reference uses
the actual ME2 production render path, whose complete source machine body is
independently byte-equal and executed in the paired machine proof.
"""
import argparse, hashlib, json, os, subprocess
from pathlib import Path
import battle_action_catalog_qa as frozen
import native_sprite_render_abi_qa as native
from snes_sprite_render_abi_oracle import corpus
from check_jev_observer_parity import local_scratch

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('build','runtime','native-source','original-assets','assets','machine-review','machine-scratch','scratch','frozen-source','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--diagnostic',action='store_true');a=p.parse_args();a.scratch=local_scratch(a.scratch)
    if a.scratch.exists():raise ValueError('Fresh scratch required')
    machine=json.loads(a.machine_review.read_text())
    if not machine['Passed'] or machine['format']!='snes-sprite-entry3-live-abi-oracle-v1':raise ValueError('Passed actual ENTRY3 machine proof required')
    for path in (Path('tools/snes_sprite_render_abi_oracle.py'),Path('tools/snes_sprite_entry3_abi_oracle.py')):
        if machine['InputIdentities'].get(str(path.resolve()))!=sha(path):raise ValueError('Actual machine corpus identity changed')
    selector='''  if(v[1]==1)got=cr_render_entity_sprite_me1(e,0,0x1234,&pc);
  else if(v[1]==2)got=cr_render_entity_sprite_me2(e,0,0x1234,&pc);
  else got=cr_render_entity_sprite_me3(e,0,0x1234,&pc);'''
    replacement='''  int16_t saved=entities.animation_frame[e];uint16_t refpc;
  cr_render_entity_sprite_me2(e,0,0x1234,&refpc);uint64_t reference=hash_vram();entities.animation_frame[e]=saved;
  entities.current_displayed_sprites[e]=0xa55a;memset(ppu.vram,0xa5,sizeof(ppu.vram));
  got=callroutine_dispatch(0xc0a4a8,e,0,0x1234,&pc);
  printf("QA_REFERENCE {\\"id\\":%u,\\"vramHash\\":\\"%016llX\\"}\\n",v[0],(unsigned long long)reference);'''
    if native.DRIVER.count(selector)!=1:raise ValueError('Frozen base private driver selector changed')
    frozen.DRIVER=native.DRIVER.replace(selector,replacement).replace('extern int eb_platform_main(int argc,char **argv);','extern int eb_platform_main(int argc,char **argv);\nextern int16_t callroutine_dispatch(uint32_t,int16_t,int16_t,uint16_t,uint16_t*);');a.scratch.mkdir(parents=True);exe,build=frozen.private_build(a)
    failures=[];cases=[];assertions=0
    def check(name,ok,detail):
        nonlocal assertions
        assertions+=1
        if not ok:failures.append({'check':name,'detail':detail})
    for mode in machine['modes']:
        profile=mode['profile'];folder=a.scratch/profile.lower();folder.mkdir();rows=[r for r in corpus(mode['spriteIdentity']) if r['method']==3]
        source=a.machine_scratch/profile.lower()/'samples.jsonl'
        if sha(source)!=mode['samplesSha256']:raise ValueError('Actual machine samples changed')
        samples=[json.loads(s) for s in source.read_text().splitlines()]
        rows.extend(dict(rows[0],guard=i) for i in range(1,8))
        data=folder/'cases.tsv';data.write_text(''.join(' '.join(str(v) for v in (i,r['method'],r['direction'],r['frame'],r['surface'],r['vram'],r['width'],r['height'],int(r['onScreen']),r.get('guard',0)))+'\n' for i,r in enumerate(rows)))
        run=subprocess.run([str(exe.resolve()),str((a.original_assets if profile=='Original' else a.assets).resolve()),str(folder.resolve()),str(int(profile=='Original')),str(data.resolve())],cwd=folder,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=120)
        log=run.stdout.decode(errors='replace')+'\n'+run.stderr.decode(errors='replace');(folder/'native.log').write_text(log)
        actual=[json.loads(s.split(' ',1)[1]) for s in log.splitlines() if s.startswith('QA_RENDER ')];refs=[json.loads(s.split(' ',1)[1]) for s in log.splitlines() if s.startswith('QA_REFERENCE ')]
        check(profile+' process',run.returncode==0,run.returncode);check(profile+' corpus',len(actual)==len(rows)==len(refs) and [r['id'] for r in actual]==list(range(len(rows))),len(actual))
        for i,(row,r,ref) in enumerate(zip(rows,actual,refs)):
            expected=samples[i][1] if i<len(samples) else 0
            check(profile+f' case{i} actual source return',r['value']==expected,{'got':r['value'],'expected':expected})
            check(profile+f' case{i} transient frame0 upload',r['vramHash']==ref['vramHash'],{'inputFrame':row['frame'],'method':4,'guard':row.get('guard',0)})
            check(profile+f' case{i} persistent frame/PC preserved',r['frame']==row['frame'] and r['pc']==0x1234,r)
            if i<len(samples):check(profile+f' case{i} source displayed flags',r['displayedFlags']==samples[i][3]&3,{'got':r['displayedFlags'],'expected':samples[i][3]&3})
            cases.append({'profile':profile,'id':i,'guard':row.get('guard',0),'inputFrame':row['frame'],'value':r['value'],'vramHash':r['vramHash'],'sourceFrame0UploadHash':ref['vramHash']})
    report={'format':'native-sprite-entry3-live-abi-qa-v1','Passed':not failures,'allPassed':not failures,'executedCases':len(cases),'executedAssertions':assertions,'skippedCases':0,'failures':failures,'cases':cases,'actualDispatcherAddress':'C0A4A8','privateBuild':build,'runtimeSha256':{n:sha(a.runtime/n) for n in ('player.exe','observer.exe')},'packSha256':{'Original':sha(a.original_assets),'Redux':sha(a.assets)},'machineReportSha256':sha(a.machine_review),'frozenFullPatchSha256':sha(a.frozen_source/'native-companion.patch'),'toolSha256':sha(Path(__file__)),'baseDriverToolSha256':sha(Path(native.__file__)),'ownerSavesTouched':False,'sharedBuildModified':False,'limits':['The actual callroutine dispatcher C0A4A8 executes in prepared normally allocated NPC773 sprite contexts, including frame1 persistence while the source renders transient frame0.','The independent actual machine samples verify the live A return and source selected-frame flags. Native full VRAM upload hashes compare against the actual source-equivalent ME2 frame0 production path.','Seven invalid-data guards per profile prove safe-zero behavior only, not legitimacy of malformed sprites in the original game.','This addendum tests the source event macro ENTRY3 callback separately from the differently named movement-entry3 C0A480 callback.','Owner saves and frozen builds/paks remain unchanged; public output contains no original pixels or bytecode.']}
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ('Passed','executedCases','executedAssertions','skippedCases')}));print(json.dumps(failures[:8]))
    if failures and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
