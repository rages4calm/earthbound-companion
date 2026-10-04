# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify a clean Redux tester ZIP using isolated owner-ROM setup and gameplay."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

from redux_gameplay_qa import main as opening


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("zip","rom","scratch","msu-cache","msu-manifest"):
        parser.add_argument("--"+name,required=True,type=Path)
    args=parser.parse_args();scratch=args.scratch.resolve()
    if scratch.exists():raise ValueError("Use a fresh isolated verification directory.")
    scratch.mkdir(parents=True);tests=[];source_hash=sha(args.rom)
    with zipfile.ZipFile(args.zip) as archive:
        for entry in archive.infolist():
            path=PurePosixPath(entry.filename)
            if path.is_absolute() or '..' in path.parts or any(':' in x or '\\' in x for x in path.parts):raise ValueError("Unsafe ZIP path.")
            if path.suffix.lower() in ('.sfc','.smc','.rom','.pak','.pcm','.srm','.sav','.state','.bmp','.png','.replay') or path.name.startswith('quicksave_'):raise ValueError("Game data entered ZIP.")
        archive.extractall(scratch)
    app=scratch/'EarthBound Companion'
    manifest=json.loads((app/'PACKAGE-MANIFEST.json').read_text(encoding='utf-8-sig'))
    for record in manifest['Files']:
        file=app/record['Path']
        if file.stat().st_size!=record['Bytes'] or sha(file)!=record['SHA256']:raise ValueError("Package manifest mismatch.")
    tests.append('ROM-free archive and exact file manifest')
    tracks=json.loads(args.msu_manifest.read_text(encoding='utf-8-sig'))
    download=min((x for x in tracks if int(x['size'])>2000),key=lambda x:int(x['size']))
    folder=app/'msu';folder.mkdir(exist_ok=True)
    # Verified existing tracks are hard-linked solely to avoid a redundant
    # 1.25 GB test download. One corrupt track and a stale partial force the
    # real production streaming/verification/rename path to run.
    for record in tracks:
        if record['name']==download['name']:continue
        source=args.msu_cache/record['name']
        if source.stat().st_size!=int(record['size']):raise ValueError("Incomplete test soundtrack cache.")
        os.link(source,folder/record['name'])
    (folder/download['name']).write_bytes(b'corrupt-test-track')
    (folder/(download['name']+'.part')).write_bytes(b'stale-part')
    raw=args.rom.read_bytes()
    if len(raw)==3146240:raw=raw[512:]
    headered=scratch/'owner-headered-test.smc';headered.write_bytes(bytes(512)+raw)
    env=dict(os.environ,PATH=str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32'),SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    env.pop('PYTHONHOME',None);env.pop('PYTHONPATH',None)
    launcher=app/'EarthBound Companion.exe'
    def run(name,arguments,timeout=240):
        result=subprocess.run([str(launcher),'--data-root',str(app),*arguments],env=env,capture_output=True,timeout=timeout)
        (scratch/(name+'.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(name+' failed: '+(result.stdout+result.stderr).decode(errors='replace')[-2200:])
    try:
        run('setup',['--setup-redux',str(headered),'--with-msu'])
        tests.append('Self-contained first-run setup with headered owner ROM and online pinned Redux source')
        pack=app/'Profiles/maternalbound-redux-897d0083/assets.pak'
        if sha(pack)!='62BA3D70B37C95812BC742B40F1F599B142263FFB39F3DD949DDC66AA7E246C2':raise ValueError('Unexpected Redux pack.')
        if sha(app/'Game/assets.pak')!='4E01C943711D32C41E85CB858D9058169E7C8B1739FC7DC0A211E441F9631B9B':raise ValueError('Unexpected original pack.')
        settings=json.loads((app/'UserData/settings.json').read_text())
        if not settings['ReduxDevelopmentEnabled'] or Path(settings['AssetPack']).resolve()!=pack:raise ValueError('Redux was not selected after setup.')
        for record in tracks:
            data=(folder/record['name']).read_bytes()
            if len(data)!=int(record['size']) or hashlib.md5(data).hexdigest().lower()!=record['md5'].lower():raise ValueError('Soundtrack mismatch.')
        if list(folder.glob('*.part')):raise ValueError('Soundtrack partials were left behind.')
        tests.append('164 soundtrack checks; corrupt track and stale partial repaired by real download')
        for worker in (app/'Profiles').glob('.*.partial'):raise ValueError('Successful setup left a partial profile.')
        for file in (app/'Profiles').rglob('*'):
            if file.is_file() and file.suffix.lower() in ('.sfc','.smc'):raise ValueError('Setup retained a generated ROM.')
        tests.append('Verified profile installed atomically; generated ROMs cleaned')
        argv=sys.argv
        sys.argv=['opening','--native-exe',str(app/'Game/earthbound.exe'),'--assets',str(pack),'--scratch',str(scratch/'story-opening'),'--mixed-case-fixture']
        try:opening()
        finally:sys.argv=argv
        tests.append('Packaged native story opening, Select naming and cold restore')
        run('seed',['--generate-seed','Redux clean-package test'])
        records=list((app/'UserData/Seeds').glob('*/seed.json'))
        # The library location is defined by the shipped generator. Do not
        # assume the initial original-story starter seed is the Redux seed.
        records=list((app/'UserData').rglob('seed.json'))
        candidates=[p for p in records if json.loads(p.read_text())['ContentId']=='maternalbound-redux-897d0083']
        if len(candidates)!=1:raise ValueError('Expected one Redux seed.')
        seed=candidates[0].parent
        run('check-seed',['--check-seed',str(seed)])
        sys.argv=['opening','--native-exe',str(app/'Game/earthbound.exe'),'--assets',str(seed/'assets.pak'),'--scratch',str(scratch/'seed-opening'),'--mixed-case-fixture']
        try:opening()
        finally:sys.argv=argv
        tests.append('Packaged generator, independent seed guard and native randomized opening')
        run('profile-isolation',['--profile-test',str(pack),str(scratch/'profile-isolation')])
        tests.append('Original/Redux/seed save namespaces and profile switching')
        if sha(args.rom)!=source_hash:raise ValueError('Owner input ROM changed.')
        record={'Passed':True,'PackageSha256':sha(args.zip),'NativeExeSha256':sha(app/'Game/earthbound.exe'),
                'ReduxSetupSha256':sha(app/'Game/redux-setup.exe'),'ReduxPackSha256':sha(pack),
                'Tests':tests,'DownloadedTrack':download['name'],'MsuTracksVerified':len(tracks),
                'ExistingTracksReusedViaHardlinks':len(tracks)-1,'FullPlaythroughVerified':False,
                'Limits':['Isolated setup/opening tests; no complete story or randomized playthrough.','One soundtrack track downloaded; remaining tracks reused and independently checked.']}
        (scratch/'results.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(record,indent=2))
    finally:
        # Only the private headered test copy created above is removed.
        if headered.parent==scratch and headered.exists():headered.unlink()


if __name__=='__main__':main()
