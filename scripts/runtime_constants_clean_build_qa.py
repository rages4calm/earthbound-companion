# SPDX-License-Identifier: GPL-3.0-or-later
"""Build a fresh code-only source tree with explicit local tools and inputs.

Only the supplied CMake/generator overlays are applied to a private copy.
The default build forbids ebtools; the optional, separate fixture step uses
the project's small test-data generator. No ROM or real assets.pak is read.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(root):
    return {p.relative_to(root).as_posix(): sha(p)
            for p in sorted(root.rglob('*')) if p.is_file() and '.git' not in p.parts}


def digest_manifest(entries):
    return hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def json_codegen_blocks(text):
    result = {}
    for kind in ('music', 'items'):
        matches = [block for block in re.findall(r'add_custom_command\((.*?)\n\s*\)', text, re.S)
                   if 'COMMAND ${EBTOOLS_EXE} generate ' + kind + '-header' in block]
        if len(matches) != 1:
            raise ValueError('Expected one original JSON ' + kind + ' command')
        result[kind] = '\n'.join(line.strip() for line in matches[0].strip().splitlines())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline-source', 'cmake-overlay', 'generator', 'cmake', 'gcc', 'ninja',
                 'sdl', 'python', 'ebtools', 'fixture-script', 'header-review',
                 'baseline-failure-log', 'scratch', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    for name, value in vars(args).items():
        setattr(args, name, value.resolve())
    if args.scratch.exists() or args.output.exists():
        raise ValueError('Fresh scratch and output are required')
    if args.scratch.is_relative_to(args.baseline_source) or args.baseline_source.is_relative_to(args.scratch):
        raise ValueError('Scratch and baseline must not contain one another')
    forbidden = ('src/assets/items/items.json', 'src/assets/music_tracks.json')
    if any((args.baseline_source / name).exists() for name in forbidden):
        raise ValueError('Baseline must not contain extracted item/music JSON')
    header_review = json.loads(args.header_review.read_text(encoding='utf-8'))
    if not header_review.get('Passed'):
        raise ValueError('Numeric/header consumer review must pass first')
    if header_review['inputs'].get(str(args.generator)) != sha(args.generator):
        raise ValueError('Numeric/header review generator identity does not match')
    previous = args.baseline_source / 'src/CMakeLists.txt'
    if json_codegen_blocks(previous.read_text(encoding='utf-8')) != json_codegen_blocks(args.cmake_overlay.read_text(encoding='utf-8')):
        raise ValueError('Original OFF JSON command bodies changed')

    args.scratch.mkdir(parents=True)
    source = args.scratch / 'native-source'
    build = args.scratch / 'build'
    before = manifest(args.baseline_source)
    shutil.copytree(args.baseline_source, source)
    shutil.copy2(args.cmake_overlay, source / 'src/CMakeLists.txt')
    shutil.copy2(args.generator, source / 'src/tools/generate_constants_headers.py')
    after = manifest(source)
    changed = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
    if changed != ['src/CMakeLists.txt', 'src/tools/generate_constants_headers.py']:
        raise ValueError('Unexpected clean-source overlay changes: ' + repr(changed))

    env = os.environ.copy()
    env['PATH'] = str(args.gcc.parent) + os.pathsep + env.get('PATH', '')
    steps = []

    def run(name, command):
        command = list(map(str, command))
        proc = subprocess.run(command, cwd=args.scratch, env=env, capture_output=True,
                              text=True, encoding='utf-8', errors='replace')
        log = args.scratch / (name + '.log')
        log.write_text(proc.stdout + proc.stderr, encoding='utf-8')
        step = {'name': name, 'command': command, 'exitCode': proc.returncode,
                'log': str(log), 'logSha256': sha(log)}
        steps.append(step)
        print(name + ': ' + str(proc.returncode), flush=True)
        if proc.returncode:
            raise ValueError(name + ' failed; see ' + str(log))

    configure = [args.cmake, '-S', source / 'port/unix', '-B', build, '-G', 'Ninja',
                 '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_C_COMPILER=' + str(args.gcc),
                 '-DCMAKE_MAKE_PROGRAM=' + str(args.ninja), '-DSDL2_DIR=' + str(args.sdl),
                 '-DPython3_EXECUTABLE=' + str(args.python), '-DEBTOOLS_EXE=EBTOOLS_EXE-NOTFOUND',
                 '-DEB_RUNTIME_ASSETS=ON', '-DEB_ENABLE_AUDIO=ON']
    run('configure-without-ebtools', configure)
    run('plain-default-build', [args.cmake, '--build', build, '--parallel', '8'])
    cache = args.scratch / 'default-no-ebtools-CMakeCache.txt'
    shutil.copy2(build / 'CMakeCache.txt', cache)
    if 'EBTOOLS_EXE:FILEPATH=EBTOOLS_EXE-NOTFOUND' not in cache.read_text(encoding='utf-8'):
        raise ValueError('Default build did not preserve explicit NOTFOUND ebtools')
    fixture_excluded = not (build / 'game_lib/test_runtime_assets.exe').exists()
    if not fixture_excluded:
        raise ValueError('Fixture unexpectedly built as part of plain default target')
    run('explicit-struct-targets', [args.cmake, '--build', build, '--target', 'gen_struct_info', 'struct_info', '--parallel', '8'])
    struct_info = json.loads((build / 'game_lib/struct_info.json').read_text(encoding='utf-8'))
    if not struct_info:
        raise ValueError('gen_struct_info did not produce non-empty JSON')
    default_outputs = {path.relative_to(build).as_posix(): sha(path) for path in (
        build / 'earthbound.exe', build / 'game_lib/libearthbound_game.a',
        build / 'game_lib/gen_struct_info.exe', build / 'game_lib/struct_info.json',
        build / 'game_lib/generated/items_generated.h', build / 'game_lib/generated/music_generated.h')}
    for filename, expected in header_review['generatedHeaderSha256'].items():
        if default_outputs['game_lib/generated/' + filename] != expected:
            raise ValueError('Compiled header differs from numeric consumer QA: ' + filename)
    if any((source / name).exists() for name in forbidden):
        raise ValueError('Default build fabricated extracted JSON')

    scripts = args.scratch / 'scripts'
    scripts.mkdir()
    shutil.copy2(args.fixture_script, scripts / 'create_fixture.py')
    run('create-public-test-fixture', [args.python, scripts / 'create_fixture.py'])
    run('configure-explicit-fixture-tools', [args.cmake, '-S', source / 'port/unix', '-B', build,
                                           '-DEBTOOLS_EXE=' + str(args.ebtools)])
    run('explicit-fixture-build', [args.cmake, '--build', build, '--target', 'test_runtime_assets', '--parallel', '8'])
    run('explicit-fixture-run', [build / 'game_lib/test_runtime_assets.exe',
                                 build / 'game_lib/runtime_assets_test/assets_test.pak',
                                 build / 'game_lib/runtime_assets_test/scratch'])
    if 'test_runtime_assets: all checks passed' not in (args.scratch / 'explicit-fixture-run.log').read_text(encoding='utf-8'):
        raise ValueError('Fixture success message missing')
    inputs = {str(path): sha(path) for path in (args.cmake_overlay, args.generator,
              args.cmake, args.gcc, args.ninja, args.python, args.ebtools, args.fixture_script,
              args.header_review, args.baseline_failure_log, previous)}
    report = {
        'format': 'runtime-source-constants-clean-build-qa-v1', 'Passed': True,
        'runnerSha256': sha(Path(__file__)), 'inputs': inputs,
        'baselineSource': str(args.baseline_source),
        'baselineSourceFileCount': len(before), 'baselineSourceManifestSha256': digest_manifest(before),
        'privateOverlaidSourceFileCount': len(after), 'privateOverlaidSourceManifestSha256': digest_manifest(after),
        'exactOverlayChanges': changed, 'plainDefaultBuildPassedWithoutEbtools': True,
        'fixtureExecutableExcludedFromDefaultBuild': fixture_excluded,
        'genStructInfoAndStructInfoTargetsPassed': True,
        'extractedItemsOrMusicJsonReadOrCreated': False,
        'OFFJsonCodegenCommandBodiesPreserved': True,
        'explicitPublicFixtureGenerationBuildAndExecutionPassed': True,
        'steps': steps, 'defaultBuildOutputSha256': default_outputs,
        'privateFixtureOutputSha256': {path.relative_to(build).as_posix(): sha(path) for path in (
            build / 'game_lib/test_runtime_assets.exe', build / 'game_lib/runtime_assets_test/assets_test.pak')},
        'noEbtoolsDefaultCacheSha256': sha(cache),
        'nativeGameplayRun': False, 'sharedBuildOrOwnerSaveOrRealPackModified': False,
        'limits': [
            'This builds a private fresh source copy; these executable hashes are not release runtime identities.',
            'The baseline is the recorded fresh Base archive plus public v8 patch and pinned tamp prepared by root; its missing-JSON failure log is hash-bound.',
            'Only CMakeLists.txt and the new constants generator differ before the explicit test-fixture step.',
            'Default runtime build, numeric/header consumer QA and gen_struct_info are executed; gameplay and full story are not run.',
            'EB_RUNTIME_ASSETS=OFF JSON commands are compared textually, not built without required extracted assets.',
            'The explicit fixture requires ebtools and the published synthetic fixture script; it creates only private loader test data, not game records.',
            'Runtime packs still provide actual item/music records; diagnostic arrays are source symbols and include the explicit source ID MUSIC_GIYGAS_WEAKENED191.'
        ]
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(str(args.output), flush=True)


if __name__ == '__main__':
    main()
