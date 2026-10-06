# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded actual Redux Offense Up dispatch with pinned-instruction assertions."""
import argparse,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
import battle_action_catalog_qa_dev15 as previous
from build_maternalbound_pack import read_pack


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('build','native-source','assets','runtime','scratch','output','project'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--diagnostic',action='store_true')
    parser.add_argument('--original',action='store_true')
    parser.add_argument('--machine-report',type=Path)
    args=parser.parse_args()
    if args.scratch.exists():raise ValueError('Fresh private scratch required')
    pin=subprocess.check_output(['git','-C',str(args.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=helper.PIN:raise ValueError('Unreviewed Redux revision')
    args.scratch.mkdir(parents=True);session=args.scratch/'session';session.mkdir()
    driver=previous.driver_source().replace('unsigned original_attacker=bt.current_attacker,original_target=bt.current_target;',
        't->base_offense=(uint8_t)v[34];\n        unsigned original_attacker=bt.current_attacker,original_target=bt.current_target;')
    if args.original:
        driver=driver.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"')
        driver=driver.replace(' || !maternalbound_enabled()', ' || maternalbound_enabled()')
    helper.DRIVER=driver;exe,build=helper.private_build(args)
    _,_,assets=read_pack(args.assets,args.native_source/'src/data/runtime_generated/asset_ids.h')
    actions=assets['data/battle_action_table.bin']
    action=next(i//12 for i in range(0,len(actions),12) if int.from_bytes(actions[i+8:i+12],'little')==0xC29E38)
    tests=[]
    # Includes natural repeated-buff states from base80 as well as explicit
    # low/high boundary fixtures. All arithmetic below follows pinned opcodes,
    # including uint16 doubling, add wrapping, and the 17/8 base cap.
    for base in (1,80,200,255):
        for npc in (0,9):
            for offense in (0,1,7,8,16,50,60,80,90,101,113,127,142,159,170,255,32768,65535):
                v=[len(tests),action,0x9e3779b9,0,0,500,100,999,300,
                    0,0,0,0,0,0,0,255,255,255,255,255,255,20,npc,offense,50,20,0,0,0,0,0,
                    0,1,base,0,0,0,0,1,20,20,0,0,0,0,50,0]
                increment=max(offense>>4,1) if args.original else ((offense*2)&65535)>>4
                expected=offense if npc else min((offense+increment)&65535,base*(5 if args.original else 17)//(4 if args.original else 8))
                tests.append({'values':v,'offense':offense,'base':base,'npc':npc,'expectedOffense':expected})
    inputs=args.scratch/'cases.tsv';inputs.write_text('\n'.join(' '.join(map(str,t['values'])) for t in tests)+'\n')
    run=subprocess.run([str(exe.resolve()),str(args.assets.resolve()),str(session.resolve()),str(inputs.resolve())],
        cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=60)
    (args.scratch/'native.log').write_bytes(run.stdout+run.stderr)
    actual={r['id']:r for r in (json.loads(x[3:]) for x in run.stdout.decode(errors='replace').splitlines() if x.startswith('QA '))}
    machine=json.loads(args.machine_report.read_text()) if args.machine_report else None
    if machine and (machine['sourceMismatchCount'] or machine['reference']!=('clean-original-machine' if args.original else 'pinned-redux-machine')):
        raise ValueError('Machine report does not match reviewed pack semantics')
    machine_by_input={(r['baseOffense'],r['initialOffense']):r['machineOffense'] for r in machine['cases']} if machine else {}
    rows=[]
    for i,t in enumerate(tests):
        a=actual.get(i,{});passed=bool(a) and a['offense']==t['expectedOffense'] and a['depth']==1 and a['steps']<30000
        m=machine_by_input.get((t['base'],t['offense'])) if not t['npc'] else None
        if machine and not t['npc'] and (m is None or a.get('offense')!=m):passed=False
        rows.append({'initialOffense':t['offense'],'baseOffense':t['base'],'npc':t['npc'],
            'expectedOffense':t['expectedOffense'],'actualOffense':a.get('offense'),'machineOffense':m,'passed':passed})
    refs=['asm/battle/increase_offense_16th.asm','asm/battle/actions/offense_up_alpha.asm',
        'src/game/battle_calc.c','src/game/battle_actions.c']
    pinned=[]
    for path in ('ccscript/main.ccs','ccscript/redux/offense_defense_psi_buff.ccs'):
        f=args.project/path;b=subprocess.check_output(['git','-C',str(args.project.parent),'show',f'{pin}:Project/{path}'])
        if f.read_bytes().replace(b'\r\n',b'\n')!=b.replace(b'\r\n',b'\n'):raise ValueError('Pinned source differs')
        pinned.append({'path':path,'sha256':helper.digest(f),'matchesPinnedSource':True})
    report={'schemaVersion':1,'toolVersion':'dev15-offense-up','reduxRevision':pin,
        'originalPack':args.original,
        'runtimeSha256':{n:helper.digest(args.runtime/n) for n in ('player.exe','observer.exe')},
        'assetsSha256':helper.digest(args.assets),'privateBuild':build,'nativeExitCode':run.returncode,
        'function':'C29E38','actionId':action,'cases':rows,'pinnedReduxReferences':pinned,
        'sourceReferences':[{'path':p,'sha256':helper.digest(args.native_source/p)} for p in refs],
        'sourceReferenceRole':'Current review files separately identified from immutable tested library.',
        'machineReportSha256':helper.digest(args.machine_report) if args.machine_report else None,
        'machineComparedCases':sum(r['machineOffense'] is not None for r in rows),
        'reproductionFlags':{name:str(getattr(args,name.replace('-','_'))) for name in ('build','native-source','assets','runtime','scratch','output','project','machine-report')},
        'allPassed':run.returncode==0 and len(actual)==len(tests) and all(r['passed'] for r in rows),
        'diagnosticMode':args.diagnostic,
        'limits':['Actual callback and resumable text execute in prepared player/NPC boundaries; full turn and input/render are outside scope.',
            'Expected arithmetic is derived from exact enabled pinned opcodes; independent patched-machine results are recorded separately.',
            'Only player library executed; observer hash is provenance. No save, ROM or extracted payload bytes included.']}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cases':len(rows),'passed':sum(r['passed'] for r in rows),'nativeExitCode':run.returncode,
        'allPassed':report['allPassed'],'firstFailures':[r for r in rows if not r['passed']][:5]}))
    if not report['allPassed'] and not args.diagnostic:raise SystemExit(1)


if __name__=='__main__':main()
