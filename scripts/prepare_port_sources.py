# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepare an isolated, pinned native port and SDL source; no ROM required."""
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import subprocess
import urllib.request
import zipfile

NATIVE_REVISION = '76eacab54b05766b82c98da9c55d94d1236ece03'
SDL_REVISION = '5d249570393f7a37e037abf22cd6012a4cc56a71'
SDL_SHA256 = '8f71d910b4fd8eb9b40e2f33752cf17d50070e87d2985c54c6cd3e1da4b35f32'

def run(*args):
    subprocess.run(args, check=True)

def prepare(repo, destination):
    if destination.exists():
        raise ValueError('Choose a new native-source directory. Existing checkouts are never reset.')
    run('git', 'clone', '--no-checkout', 'https://github.com/seanstaggsQU/earthboundRecompLinux2026.git', str(destination))
    run('git', '-C', str(destination), 'checkout', '--detach', NATIVE_REVISION)
    run('git', '-C', str(destination), 'submodule', 'update', '--init', 'src/vendor/tamp')
    for name in ('native-companion.patch', 'native-portable.patch'):
        patch = str(repo / 'patches' / name)
        run('git', '-C', str(destination), 'apply', '--check', patch)
        run('git', '-C', str(destination), 'apply', patch)

def sdl(destination):
    folder = destination / ('SDL-' + SDL_REVISION)
    if folder.exists():
        raise ValueError('Use an empty SDL destination; source integrity must not be inferred from an existing directory.')
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / 'SDL-source.zip'
    urllib.request.urlretrieve('https://codeload.github.com/libsdl-org/SDL/zip/' + SDL_REVISION, archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SDL_SHA256:
        raise ValueError('SDL archive checksum mismatch')
    with zipfile.ZipFile(archive) as zipped:
        for entry in zipped.infolist():
            p = PurePosixPath(entry.filename)
            if p.is_absolute() or '..' in p.parts or any(':' in v or '\\' in v for v in p.parts) or p.parts[0] != folder.name:
                raise ValueError('Unsafe SDL archive path')
        zipped.extractall(destination)
    return folder

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', type=Path)
    parser.add_argument('--sdl', type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    if args.native: prepare(repo, args.native.resolve())
    if args.sdl: print(sdl(args.sdl.resolve()))
