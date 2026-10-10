# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep pinned Redux CCScript roots independent of filesystem enumeration."""
from pathlib import Path
import sys


def stable_ccscript_arguments(arguments):
    result = list(arguments)
    positions = [i for i, value in enumerate(result) if value.lower().endswith('.ccs')]
    scripts = sorted((result[i] for i in positions),
        key=lambda value: (Path(value).name.casefold(), Path(value).name))
    for i, value in zip(positions, scripts):
        result[i] = value
    return result


def compile_cli():
    from coilsnake.ui import common
    from coilsnake.ui.cli import main
    compiler = common.ccc
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
    layout = root / 'research/redux-module-order.txt'
    common.ccc = lambda arguments: compiler([
        '--module-order', str(layout), *stable_ccscript_arguments(arguments)])
    try:
        main()
    finally:
        common.ccc = compiler


def compiler_order_selftest():
    """Exercise the packaged native compiler using only invented ROM bytes."""
    import hashlib
    import tempfile
    from ccscript import ccc
    from coilsnake.util.common.assets import ccscript_library_path
    expected = hashlib.sha256(b'\x02' + bytes(0x600000 - 1)).hexdigest()
    hashes = []
    with tempfile.TemporaryDirectory(prefix='redux-compiler-selftest-') as temporary:
        root = Path(temporary)
        first = root / 'data_mem_overwrite.ccs'
        second = root / 'main.ccs'
        # Deliberate overlapping writes make input ordering observable.
        first.write_text('ROM[0xC00000] = { 0x01 }', encoding='utf-8')
        second.write_text('ROM[0xC00000] = { 0x02 }', encoding='utf-8')
        output = root / 'synthetic.sfc'
        for inputs in ((first, second), (second, first)):
            output.write_bytes(bytes(0x600000))
            args = ['-n', '--libs', ccscript_library_path(), '-s', 'F31000', '-o', str(output),
                *map(str, inputs)]
            status, log = ccc(stable_ccscript_arguments(args))
            if status:
                raise RuntimeError('Synthetic compiler selftest failed: ' + log)
            digest = hashlib.sha256(output.read_bytes()).hexdigest()
            if digest != expected:
                raise RuntimeError('Synthetic compiler ordering differs from the expected result.')
            hashes.append(digest)
        # Enough equal-size modules to exercise the legacy unstable sort.
        parts = [root / f'part_{i:02d}.ccs' for i in range(24)]
        for i, part in enumerate(parts):
            part.write_text(f'"[{i+1:02x}]"', encoding='utf-8')
        layout = root / 'module-order.txt'
        layout.write_text(''.join(f'{p.stem} 1\n' for p in reversed(parts)), encoding='utf-8')
        expected_bytes = bytearray(0x600000)
        expected_bytes[0x331000:0x331018] = bytes(range(24, 0, -1))
        allocation_hash = hashlib.sha256(expected_bytes).hexdigest()
        for inputs in (parts, list(reversed(parts))):
            output.write_bytes(bytes(0x600000))
            args = ['-n', '--libs', ccscript_library_path(), '-s', 'F31000',
                '-o', str(output), '--module-order', str(layout), *map(str, inputs)]
            status, log = ccc(args)
            if status or hashlib.sha256(output.read_bytes()).hexdigest() != allocation_hash:
                raise RuntimeError('Synthetic equal-size module ordering failed: ' + log)
        # Reject an incompatible layout rather than silently compiling it.
        layout.write_text(layout.read_text().replace('part_23 1', 'part_23 2'), encoding='utf-8')
        status, _ = ccc(args)
        if not status:
            raise RuntimeError('Compiler accepted an incompatible module order.')
    return {'stage': 'compiler-order', 'status': 'passed', 'synthetic': True,
        'rootPermutations': len(hashes), 'rootSha256': expected,
        'equalSizeModules': len(parts), 'allocationPermutations': 2,
        'allocationSha256': allocation_hash, 'invalidLayoutRejected': True}


if __name__ == '__main__':
    compile_cli()
