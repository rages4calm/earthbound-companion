# SPDX-License-Identifier: GPL-3.0-or-later
"""Execute the actual clean/pinned Redux 65816 Offense Up helper locally.

Only an ephemeral emulator-memory caller is injected. The owner ROM, original
helper, pinned patch and relocated callee remain untouched. No ROM is copied
into the public evidence report.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path

CLEAN='a8fe2226728002786d68c27ddddf0b90a894db52e4dfe268fdf72a68cae5f02e'
REDUX='c2a2fc98c7e6518b797959ffadf24ca4db8b4d7745ed3a9eb92eee106db1d0ab'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','oracle','scratch','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--native-report',type=Path)
    args=parser.parse_args();identity=sha(args.rom)
    if identity not in (CLEAN,REDUX):raise ValueError('Exact clean US or pinned compiled Redux ROM required')
    redux=identity==REDUX
    if args.scratch.exists():raise ValueError('Fresh private scratch directory required')
    args.scratch.mkdir(parents=True);scratch=args.scratch.resolve()
    offenses=(0,1,7,8,16,50,60,80,90,101,113,127,142,159,170,255,32768,65535)
    cases=[(base,offense) for base in (1,80,200,255) for offense in offenses]
    stub=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
    entry=0xc2ff00+len(stub)
    # A is a real near battler pointer. JSR executes unmodified C27D28,
    # including its original stack/direct-page prologue and Redux long calls.
    stub+=bytes.fromhex('a9005020287daf26507e8f00707e7b8f08707e3b8f0a707e')
    finish=0xc2ff00+len(stub);stub+=bytes((0x4c,entry&255,(entry>>8)&255))
    samples=scratch/'samples.tsv'
    lua=['local output=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))',
        'local cases={'+','.join('{'+str(base)+','+str(offense)+'}' for base,offense in cases)+'}',
        'local mem=emu.memType.snesWorkRam',
        'local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256),mem) end',
        'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end',
        'local index=0',
        'emu.addMemoryCallback(function() index=index+1;local c=cases[index];assert(c,"extra case");w16(0x5026,c[2]);w16(0x5032,c[1])',
        f'end,emu.callbackType.exec,{entry})',
        'emu.addMemoryCallback(function() assert(r16(0x7008)==0x1000,"D canary");assert(r16(0x700a)==0x1fff,"stack canary");',
        'output:write(string.format("%d,%d\\n",index,r16(0x7000)));if index==#cases then output:flush();output:close();emu.log("CORPUS_COMPLETE");emu.breakExecution() end',
        f'end,emu.callbackType.exec,{finish})']
    script=scratch/'oracle.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
    command=[str(args.oracle.resolve()),str(args.rom.resolve()),'--home',str(scratch/'oracle-home'),
        '--frames','1000','--timeout','60','--lua-timeout','10','--lua-allow-io','--lua',str(script),
        '--write-memory','SnesPrgRom:0x2ff00:'+stub.hex(),'--set-pc','0xc2ff00','--cpu','Snes']
    run=subprocess.run(command,capture_output=True,timeout=70)
    (scratch/'oracle.jsonl').write_bytes(run.stdout);(scratch/'oracle.stderr').write_bytes(run.stderr)
    logs=[json.loads(line) for line in run.stdout.decode().splitlines()]
    events=[r for r in logs if r.get('event')=='lua_log'];summary=logs[-1] if logs else {}
    if run.returncode or not summary.get('ok') or summary.get('reason')!='debugger_break' or any(r['error_count'] for r in events):
        raise RuntimeError('Machine execution did not complete cleanly')
    lines=samples.read_text().splitlines()
    if len(lines)!=len(cases) or not any('CORPUS_COMPLETE' in r['text'] for r in events):raise RuntimeError('Incomplete corpus')
    native=json.loads(args.native_report.read_text()) if args.native_report else None
    native_by_input={(r['baseOffense'],r['initialOffense']):r['actualOffense'] for r in native['cases'] if not r['npc']} if native else {}
    rows=[]
    for index,(base,offense) in enumerate(cases,1):
        match=re.fullmatch(r'(\d+),(\d+)',lines[index-1])
        if not match or int(match[1])!=index:raise RuntimeError('Missing/duplicate/order mismatch')
        actual=int(match[2])
        delta=((offense*2)&65535)>>4 if redux else max(offense>>4,1)
        expected=min((offense+delta)&65535,base*(17 if redux else 5)//(8 if redux else 4))
        n=native_by_input.get((base,offense))
        rows.append({'baseOffense':base,'initialOffense':offense,'machineOffense':actual,'sourceExpectedOffense':expected,
            'sourceMatchedMachine':actual==expected,'nativeOffense':n,'nativeMatchedMachine':None if n is None else n==actual})
    if sha(args.rom)!=identity:raise RuntimeError('Owner ROM changed')
    report={'schemaVersion':1,'reference':'pinned-redux-machine' if redux else 'clean-original-machine',
        'romSha256':identity,'oracleSha256':sha(args.oracle),'oracleCoreSha256':sha(args.oracle.parent/'MesenCore.dll'),
        'routineAddress':'C27D28','cases':rows,'executedMachineCases':len(rows),
        'sourceMismatchCount':sum(not r['sourceMatchedMachine'] for r in rows),
        'nativeComparedCases':sum(r['nativeOffense'] is not None for r in rows),
        'nativeMismatchCount':sum(r['nativeMatchedMachine'] is False for r in rows),
        'nativeReportSha256':sha(args.native_report) if args.native_report else None,
        'stackAndDirectPageCanariesPassed':True,'ownerRomUnchanged':True,
        'limits':['Actual unmodified helper and pinned relocated callees execute with prepared battler fields; this is not whole-game equivalence.',
            'Native comparison refers to the separately identified immutable real-dispatch report.',
            'Emulator is a development reference only and not part of native player releases. No ROM or payload bytes included.']}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('reference','executedMachineCases','sourceMismatchCount','nativeComparedCases','nativeMismatchCount')}))
    if report['sourceMismatchCount']:raise SystemExit(1)


if __name__=='__main__':main()
