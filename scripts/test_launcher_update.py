# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise a built desktop package's real update/download/helper/restart path.

Uses a loopback synthetic release and a fresh isolated folder. No ROM or player
installation is read. macOS also verifies the installed app's code signature.
"""
import argparse, hashlib, json, os, shutil, subprocess, tarfile, threading, time, zipfile
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package',required=True,type=Path)
    parser.add_argument('--platform',required=True,choices=['win-x64','linux-x64','osx-arm64','osx-x64'])
    parser.add_argument('--output',required=True,type=Path)
    a=parser.parse_args();a.package=a.package.resolve();a.output=a.output.resolve();a.output.mkdir(exist_ok=False,parents=True)
    windows=a.platform=='win-x64';mac=a.platform.startswith('osx-')
    if windows:
        with zipfile.ZipFile(a.package) as z:z.extractall(a.output)
        install=a.output/'EarthBound Companion';launcher=install/'EarthBound Companion.exe';doc=install/'START HERE.txt'
    else:
        unpack=a.output/'unpack';unpack.mkdir()
        with tarfile.open(a.package) as t:t.extractall(unpack,filter='data')
        if mac:
            install=unpack/'EarthBound Companion Preview.app';launcher=install/'Contents/MacOS/EarthBoundCompanion.Portable';doc=install/'Contents/Resources/README-PORTABILITY.md'
            if not doc.exists():doc=install/'Contents/MacOS/README-PORTABILITY.md'
        else:
            install=unpack;launcher=install/'EarthBoundCompanion.Portable';doc=install/'README-PORTABILITY.md'
    assert launcher.is_file() and doc.is_file()
    expected_doc=hashlib.sha256(doc.read_bytes()).hexdigest();doc.write_text('OLD DOCUMENT FIXTURE',encoding='utf-8')
    # Portable data is stored outside the program; Windows stores it in-place.
    data=install if windows else a.output/'private-data';data.mkdir(exist_ok=True)
    private=['Game/assets.pak','Game/saves/earthbound.srm','Profiles/Redux/assets.pak','UserData/settings.json','UserData/Seeds/test/seed.json','msu/music.pcm']
    for rel in private:
        p=data/rel;p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(('PRIVATE FIXTURE '+rel).encode())
    before={rel:hashlib.sha256((data/rel).read_bytes()).hexdigest() for rel in private}
    tag='v1.0.29' if windows else 'v0.5.0-ports-preview.39'
    name='EarthBound-Companion-Windows-v1.0.29.zip' if windows else f'EarthBound-Companion-{a.platform}-preview.tar.gz'
    digest=hashlib.sha256(a.package.read_bytes()).hexdigest();requests=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            requests.append(self.path)
            if self.path=='/releases':
                body=json.dumps([dict(tag_name=tag,name='synthetic fixture',draft=False,prerelease=not windows,body='Fixture only',assets=[dict(name=name,size=a.package.stat().st_size,digest='sha256:'+digest,browser_download_url=f'http://127.0.0.1:{self.server.server_port}/package')])]).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            elif self.path=='/package':
                self.send_response(200);self.send_header('Content-Length',str(a.package.stat().st_size));self.end_headers()
                with a.package.open('rb') as source:
                    while block:=source.read(1024*1024):self.wfile.write(block)
            else:self.send_error(404)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
    env=dict(os.environ,EB_UPDATE_FEED=f'http://127.0.0.1:{server.server_port}/releases',EB_UPDATE_FIXTURE='1')
    proof=install.parent/'.updater-fixture-result.json'
    try:
        start=subprocess.run([str(launcher),'--update-fixture-install'],env=env,capture_output=True,timeout=180)
        (a.output/'initial.log').write_bytes(start.stdout+start.stderr)
        deadline=time.monotonic()+90
        while not proof.exists() and time.monotonic()<deadline:time.sleep(.2)
        if not proof.exists():
            errors=[p.read_text(errors='replace') for p in a.output.rglob('update-error.txt')]
            raise RuntimeError('No restarted launcher receipt: '+str(errors)+' '+start.stderr.decode(errors='replace'))
        result=json.loads(proof.read_text());assert start.returncode==0 and result['Restarted'] and 'installed' in result['Message'].lower(),result
        assert hashlib.sha256(doc.read_bytes()).hexdigest()==expected_doc
        assert all(hashlib.sha256((data/rel).read_bytes()).hexdigest()==h for rel,h in before.items())
        assert '/releases' in requests and '/package' in requests
        if mac:subprocess.run(['codesign','--verify','--deep','--strict',str(install)],check=True)
        receipt=dict(passed=True,platform=a.platform,actualPackagedLauncher=True,downloadDigest=digest,httpRequests=requests,helperRestart=result,protectedFixtureFiles=len(before),macSignatureVerified=mac,ownerDataWritten=False)
        (a.output/'result.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt))
    finally:server.shutdown()

if __name__=='__main__':main()
