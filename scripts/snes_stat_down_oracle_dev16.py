# SPDX-License-Identifier: GPL-3.0-or-later
"""Execute untouched stat-down helpers from clean/pinned owner ROMs locally.

Private emulator-memory caller only; helpers/relocated callees and owner files
are unchanged. Machine boundary observations do not establish reachability.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from snes_offense_up_oracle import CLEAN,REDUX,sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('rom','oracle','scratch','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();identity=sha(a.rom)
    if identity not in (CLEAN,REDUX):raise ValueError('Exact clean/pinned ROM required')
    if a.scratch.exists():raise ValueError('Fresh private scratch required')
    a.scratch.mkdir(parents=True);s=a.scratch.resolve();redux=identity==REDUX
    # Current1..511 covers ordinary/high packed stat range. Zero and high words
    # are explicitly separate synthetic boundary observations.
    values=tuple(range(1,512))+(0,21845,32767,32768,50000,65535)
    cases=[(kind,base,current)for kind in (0,1)for base in (0,1,80,255)for current in values]
    stub=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
    entry=0xc2ff00+len(stub)
    # Owner helper near calls C27DDC(Offense), C27E33(Defense). Store result
    # plus original caller direct-page/stack canaries after the true returns.
    stub+=bytes.fromhex('af02717ef00ca9005020337eaf28507e800aa9005020dc7daf26507e8f00707e7b8f08707e3b8f0a707e')
    finish=0xc2ff00+len(stub);stub+=bytes((0x4c,entry&255,(entry>>8)&255))
    sample=s/'samples.tsv'
    lua=['local output=assert(io.open('+json.dumps(sample.as_posix())+',"wb"))',
        'local cases={'+','.join('{'+','.join(map(str,c))+'}'for c in cases)+'}',
        'local mem=emu.memType.snesWorkRam',
        'local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256),mem) end',
        'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end','local index=0',
        'emu.addMemoryCallback(function() index=index+1;local c=assert(cases[index],"extra case");w16(0x7102,c[1]);',
        'w16(0x5026+2*c[1],c[3]);emu.write(0x5032+c[1],c[2],mem)',
        f'end,emu.callbackType.exec,{entry})',
        'emu.addMemoryCallback(function() assert(r16(0x7008)==0x1000,"D canary");assert(r16(0x700a)==0x1fff,"stack canary");',
        'output:write(string.format("%d,%d\\n",index,r16(0x7000)));if index==#cases then output:flush();output:close();emu.log("CORPUS_COMPLETE");emu.breakExecution() end',
        f'end,emu.callbackType.exec,{finish})']
    script=s/'oracle.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
    command=[str(a.oracle.resolve()),str(a.rom.resolve()),'--home',str(s/'oracle-home'),'--frames','1000','--timeout','60',
        '--lua-timeout','10','--lua-allow-io','--lua',str(script),'--write-memory','SnesPrgRom:0x2ff00:'+stub.hex(),
        '--set-pc','0xc2ff00','--cpu','Snes']
    run=subprocess.run(command,capture_output=True,timeout=70)
    (s/'oracle.jsonl').write_bytes(run.stdout);(s/'oracle.stderr').write_bytes(run.stderr)
    logs=[json.loads(l)for l in run.stdout.decode().splitlines()];events=[r for r in logs if r.get('event')=='lua_log'];end=logs[-1]if logs else{}
    if run.returncode or not end.get('ok')or end.get('reason')!='debugger_break'or any(r['error_count']for r in events):raise RuntimeError('Machine failed')
    lines=sample.read_text().splitlines()
    if len(lines)!=len(cases)or not any('CORPUS_COMPLETE'in r['text']for r in events):raise RuntimeError('Incomplete corpus')
    rows=[]
    for i,(kind,base,current)in enumerate(cases,1):
        m=re.fullmatch(r'(\d+),(\d+)',lines[i-1])
        if not m or int(m[1])!=i:raise RuntimeError('Missing/duplicate/out-of-order')
        actual=int(m[2]);amount=max((((current*2)&65535)>>4 if redux and kind==0 else current>>(3 if redux else 4)),1)
        floor=base*5//8 if redux and kind==1 else base*3//4
        expected=max((current-amount)&65535,floor)
        native_formula=max(max(current-max(current>>(3 if redux else 4),1),0),floor)
        rows.append(dict(kind='defense'if kind else'offense',base=base,current=current,machine=actual,sourceExpected=expected,
            sourceMatched=actual==expected,nativeFormula=native_formula,nativeFormulaMatched=actual==native_formula,
            scope='ordinary-current'if 1<=current<=511 else'synthetic-boundary'))
    if sha(a.rom)!=identity:raise RuntimeError('Owner ROM changed')
    report=dict(schemaVersion=1,toolVersion='dev16-stat-down-machine',reference='pinned-redux-machine'if redux else'clean-original-machine',
        romSha256=identity,oracleSha256=sha(a.oracle),oracleCoreSha256=sha(a.oracle.parent/'MesenCore.dll'),
        routineAddresses=['C27DDC','C27E33'],executedMachineCases=len(rows),cases=rows,
        sourceMismatchCount=sum(not r['sourceMatched']for r in rows),
        ordinaryNativeFormulaMismatches=sum(not r['nativeFormulaMatched']for r in rows if r['scope']=='ordinary-current'),
        boundaryNativeFormulaMismatches=sum(not r['nativeFormulaMatched']for r in rows if r['scope']=='synthetic-boundary'),
        stackAndDirectPageCanariesPassed=True,ownerRomUnchanged=True,
        limits=['Actual untouched helper/relocated callee execution with prepared fields; nativeFormula is arithmetic review, not executed native dispatcher.',
            'Synthetic zero/high-word differences do not establish natural gameplay reachability or a reproduced story failure.',
            'Dev reference emulator is excluded from player release. No owner ROM, save or payload bytes included.'])
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k]for k in ('reference','executedMachineCases','sourceMismatchCount','ordinaryNativeFormulaMismatches','boundaryNativeFormulaMismatches')}))
    if report['sourceMismatchCount']:raise SystemExit(1)


if __name__=='__main__':main()
