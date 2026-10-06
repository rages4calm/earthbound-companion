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
from redux_audio_qa import main as audio_checks
from redux_story_walk_qa import main as story_walk


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("zip","rom","scratch","msu-cache","msu-manifest"):
        parser.add_argument("--"+name,required=True,type=Path)
    parser.add_argument('--legacy-original-pack',type=Path,help='Exercise upgrading an existing Original pack during real setup.')
    parser.add_argument('--checkpoint',type=Path,help='Read-only matching Redux format-16 checkpoint for actual packaged backup/restore/native-load verification.')
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
    legacy_hash=None
    if args.legacy_original_pack:
        legacy_hash=sha(args.legacy_original_pack)
        (app/'Game/assets.pak').write_bytes(args.legacy_original_pack.read_bytes())
        tests.append('Prepared legacy Original pack for the actual setup upgrade path')
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
        if sha(pack)!='D9A772D10AFF68BDF93C077CDA640D42B835884D6834BB18BF0D43C3800F57BB':raise ValueError('Unexpected Redux pack.')
        if sha(app/'Game/assets.pak')!='01AF4F4B590D9E83937B772399EE60A9181E2384E13C1567C94DFC92101B5549':raise ValueError('Unexpected original pack.')
        if args.legacy_original_pack:
            if sha(args.legacy_original_pack)!=legacy_hash:raise ValueError('Legacy input pack changed.')
            tests.append('Legacy Original movement data upgraded; input pack unchanged')
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
        sys.argv=['audio-checks','--native-exe',str(app/'Game/earthbound.exe'),'--assets',str(pack),
                  '--msu-dir',str(folder),'--msu-manifest',str(args.msu_manifest),'--scratch',str(scratch/'audio-checks')]
        try:audio_checks()
        finally:sys.argv=argv
        tests.append('Packaged native MSU: eight Sound Stone transitions, SPC effects/fallback and all 164 loop/end checks')
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
        for label, content in (('story', pack), ('seed', seed/'assets.pak')):
            sys.argv=['story-walk','--native-exe',str(app/'Game/earthbound.exe'),'--assets',str(content),
                      '--scratch',str(scratch/(label+'-walk')),'--opening-session',str(scratch/(label+'-opening'))]
            try:story_walk()
            finally:sys.argv=argv
        tests.append('Normal-button story and seed gameplay through house doors/stairs, Mom, clothes change and outdoor movement')
        run('profile-isolation',['--profile-test',str(pack),str(scratch/'profile-isolation')])
        tests.append('Original/Redux/seed save namespaces and profile switching')
        checkpoint_hash=None
        if args.checkpoint:
            checkpoint_hash=sha(args.checkpoint)
            run('checkpoint-recovery',['--checkpoint-recovery-test',str(pack),str(args.checkpoint.resolve()),str(scratch/'checkpoint-recovery')])
            checkpoint_result=json.loads((scratch/'checkpoint-recovery/results.json').read_text())
            if not checkpoint_result['Passed'] or sha(args.checkpoint)!=checkpoint_hash:raise ValueError('Actual checkpoint recovery failed or input changed.')
            tests.append('Packaged launcher restores actual format-16 checkpoint and native engine loads it; obsolete version rejected and input unchanged')
        if sha(args.rom)!=source_hash:raise ValueError('Owner input ROM changed.')
        record={'Passed':True,'PackageSha256':sha(args.zip),'NativeExeSha256':sha(app/'Game/earthbound.exe'),
                'ReduxSetupSha256':sha(app/'Game/redux-setup.exe'),'ReduxPackSha256':sha(pack),
                'ActualCheckpointSha256':checkpoint_hash,
                'Tests':tests,'DownloadedTrack':download['name'],'MsuTracksVerified':len(tracks),
                'ExistingTracksReusedViaHardlinks':len(tracks)-1,'FullPlaythroughVerified':False,
                'Limits':['Isolated setup/opening tests; no complete story or randomized playthrough.','One soundtrack track downloaded; remaining tracks reused and independently checked.']}
        (scratch/'results.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(record,indent=2))
    finally:
        # Only the private headered test copy created above is removed.
        if headered.parent==scratch and headered.exists():headered.unlink()


if __name__=='__main__':main()
