# SPDX-License-Identifier: GPL-3.0-or-later
"""Inventory-selector caller inventory from the exact pinned CCScript source.

This is a structural list, not execution or branch coverage. Runtime reports
remain separate so an observed selector call cannot become semantic proof.
"""
import argparse, hashlib, json, re
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    rows, refs = [], []
    patterns = {
        'party-has-items-preflight': r'call\((?:data_15\.)?(?:l_0xc5e431|0xc5e431)\)',
        'generic-inventory-selector': r'call\((?:data_15\.)?(?:l_0xc5e456|0xc5e456)\)',
        'battle-discard-inventory-selector': r'call\((?:data_15\.)?l_0xc5e4c3\)',
        'recipient-selector': r'call\((?:data_15\.)?l_0xc5e54a\)',
        'build-inventory-menu': r'\bshow_inventory\(',
    }
    for f in sorted((a.project / 'ccscript').rglob('*.ccs')):
        relative = f.relative_to(a.project).as_posix()
        if '/essential/' in relative or '/definitions/' in relative:
            continue
        # Keep newlines while removing comments so original line references
        # remain stable. Quoted dialogue is not copied into this inventory.
        text = re.sub(r'/\*.*?\*/', lambda m: '\n' * m[0].count('\n'),
                      f.read_bytes().decode('latin-1'), flags=re.S)
        label, found = None, []
        for line_number, line in enumerate(text.splitlines(), 1):
            line = line.split('//', 1)[0]
            name = re.match(r'^\s*([\w.]+):', line)
            if name:
                label = name[1]
            for kind, pattern in patterns.items():
                if re.search(pattern, line, re.I):
                    debug = '/debug/' in relative or relative.endswith('/data_07.ccs')
                    found.append(dict(path=relative, line=line_number, callerLabel=label, kind=kind,
                                      scope='debug-source' if debug else 'production-source-candidate',
                                      executedByThisTool=False))
        if found:
            rows.extend(found)
            refs.append(dict(path=relative, sha256=sha(f)))
    report = dict(schemaVersion=1, toolVersion='dev21-inventory-selector-source-catalog',
                  pinnedRevision='897d00833f4a08a0a92f106abf631629a6a6a041',
                  sourceReferences=refs, staticCallSites=rows,
                  scanEncoding='Lossless byte-to-codepoint mapping; only ASCII labels/calls are matched.',
                  callSiteCount=len(rows), executedCases=0,
                  limits=['Static syntax inventory only; source import reachability and runtime branches are not established by this scan.',
                          'Multiple labels in one parent transaction and multiple calls to the same helper are separate call sites, not separate game features.',
                          'Debug candidates are recorded separately and excluded from gameplay verification claims.',
                          'Monkey, Tracy and retail selected runtime proofs remain in separate immutable reports; other transactions need independent prerequisites and outcomes.'])
    a.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(callSites=len(rows), preflightSites=sum(r['kind']=='party-has-items-preflight' for r in rows))))


if __name__ == '__main__':
    main()
