# SPDX-License-Identifier: GPL-3.0-or-later
"""Complete prepared stat-down and Magnet Omega callbacks in immutable native code.

Source arithmetic is restricted to stated ordinary stat ranges. Optional actual
original/pinned machine reports corroborate stat helpers, not whole callbacks.
"""
import argparse,collections,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
import battle_action_catalog_qa_dev15 as previous
from build_maternalbound_pack import read_pack

FUNCTIONS=(0xC28EAE,0xC28F21,0xC29254,0xC29E86,0xC29FE1)


def driver_source(original):
    s=previous.driver_source()
    marker='static unsigned qa_function,qa_var_count,qa_var_rolls[32],qa_damage[16];'
    s=s.replace(marker,marker+r'''
static unsigned stat_text_count,stat_text_pc[8],stat_text_cnum[8];
static Battler stat_target_before,stat_attacker_before;
''')
    s=s.replace('unsigned v[48],n=0;','unsigned v[51],n=0;').replace('n<48','n<51').replace('if(n!=48)','if(n!=51)')
    s=s.replace('qa_var_count=0;', '''qa_var_count=0;
        t->base_offense=(uint8_t)v[48];t->base_guts=(uint8_t)v[49];
        a->pp=a->pp_target=(uint16_t)v[50];a->pp_max=300;
        if(a->ally_or_enemy==0) {
            party_characters[a->id-1].current_pp=party_characters[a->id-1].current_pp_target=a->pp_target;
            party_characters[a->id-1].max_pp=a->pp_max;
        }
        stat_target_before=*t;stat_attacker_before=*a;stat_text_count=0;
        ''')
    s=s.replace('if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);', '''
        if(r.kind==STEP_PUSH && r.push_mode==GAME_MODE_DISPLAY_TEXT && g_mode_stack.mode[top]==GAME_MODE_BATTLE_ACTION) {
            if(stat_text_count>=8)return 30000;
            stat_text_pc[stat_text_count]=pc;stat_text_cnum[stat_text_count++]=dt.cnum;
        }
        if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);''')
    s=s.replace('        fflush(stdout);',r'''
        printf("QA_STAT {\"id\":%u,\"attackerPP\":%u,\"textPcs\":[",v[0],a->pp_target);
        for(unsigned i=0;i<stat_text_count;i++)printf("%s%u",i?",":"",stat_text_pc[i]);
        printf("],\"textCnums\":[");for(unsigned i=0;i<stat_text_count;i++)printf("%s%u",i?",":"",stat_text_cnum[i]);
        printf("],\"unchangedFields\":%u}\n",
            t->hp_target==stat_target_before.hp_target && t->consciousness==stat_target_before.consciousness &&
            memcmp(t->afflictions,stat_target_before.afflictions,7)==0 && t->id==stat_target_before.id);
        fflush(stdout);''')
    if original:s=s.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"').replace(' || !maternalbound_enabled()',' || maternalbound_enabled()')
    return s


def decreased(value,base,defense,original):
    amount=max(value>>(4 if original else 3),1)
    floor=base*5//8 if defense and not original else base*3//4
    return max((value-amount)&65535,floor)


def profiles(f,original):
    if f==0xC29FE1:
        return [dict(name=f'pp-{pp}-max-{maximum}-caster-{ap}-target-{member}',pp=pp,maxpp=maximum,ap=ap,member=member,enemy=None)
                for pp,maximum in((0,300),(1,300),(2,300),(5,300),(100,300),(303,300))
                for ap in(100,299,300)for member in(1,3,4)] + [
                dict(name='enemy',enemy=7),dict(name='enemy-npc',enemy=7,npc=6),
                dict(name='inactive-enemy',enemy=7,conscious=0)]
    if f==0xC28EAE:
        # All ordinary byte guts, exact 16-bit source multiply has no overflow.
        return [dict(name=f'guts-{g}-base-{b}',guts=g,baseguts=b,enemy=7)for b in(0,80,255)for g in range(b//2,256)] + [
                dict(name='npc-refusal',enemy=7,npc=6,guts=255,baseguts=255),dict(name='player',enemy=None,guts=255,baseguts=255)]
    rows=[dict(name=f'stat-{v}-base0',offense=v,defense=v,baseoff=0,basedef=0,enemy=7)for v in range(1,512)]
    rows += [dict(name=f'stat-{v}-base-{b}-luck-{luck}',offense=v,defense=v,baseoff=b,basedef=b,luck=luck,enemy=7)
             for b in(1,80,255)for v in sorted(set((max(1,b*3//4),max(1,b),max(1,b*2),511)))for luck in(0,20,79,80)]
    rows += [dict(name='npc-refusal',enemy=7,npc=6),dict(name='player',enemy=None),dict(name='inactive',enemy=7,conscious=0)]
    return rows


def expected(t,a,original):
    f=t['function'];p=t['profile'];v=t['values'];roll=a['rolls8']
    off,defense,guts=v[24],v[25],v[27];pp=v[6];ap=v[50];text=[];nums=[]
    if f==0xC29FE1:
        if not (p.get('enemy')is None and p.get('member',1)==3):
            text=[0]
            if pp:
                drain=min(pp,roll[0]*4//256+roll[1]*4//256+2)
                pp=min(pp-drain,v[8]);ap=min(ap+drain,300);nums=[drain]
    elif p.get('npc'):
        text=[0]
    elif f==0xC28EAE:
        guts=max(guts*3//4,v[49]//2);text=[0];nums=[(v[27]-guts)&65535]
    elif f==0xC29E86 and roll[0]*80//256<v[22]:
        text=[0]
    else:
        text=[0]
        if f in(0xC28F21,0xC29254):
            off=decreased(off,v[48],False,original);nums.append((v[24]-off)&65535)
        if f in(0xC28F21,0xC29E86):
            defense=decreased(defense,v[46],True,original)
            diff=(v[25]-defense)&65535
            nums.append(0 if f==0xC29E86 and diff>=32768 else diff)
        if f==0xC28F21:text.append(1)
    return dict(offense=off,defense=defense,guts=guts,pp=pp,attackerPP=ap,textPcs=text,
                unchangedFields=1,attackerRestored=1,targetRestored=1),nums


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in('build','native-source','assets','runtime','scratch','output','project'):ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--machine-report',type=Path);ap.add_argument('--original',action='store_true');ap.add_argument('--pilot',action='store_true');ap.add_argument('--diagnostic',action='store_true');args=ap.parse_args()
    if args.scratch.exists():raise ValueError('Fresh private scratch required')
    pin=subprocess.check_output(['git','-C',str(args.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=helper.PIN:raise ValueError('Unreviewed pin')
    args.scratch.mkdir(parents=True);session=args.scratch/'session';session.mkdir();helper.DRIVER=driver_source(args.original);exe,build=helper.private_build(args)
    _,_,assets=read_pack(args.assets,args.native_source/'src/data/runtime_generated/asset_ids.h');table=assets['data/battle_action_table.bin'];selected={}
    for i in range(len(table)//12):
        f=int.from_bytes(table[i*12+8:i*12+12],'little');kind=table[i*12+2]
        if f in FUNCTIONS:selected.setdefault((f,kind),i)
    if{f for f,k in selected}!=set(FUNCTIONS):raise ValueError('Catalog differs')
    machine=json.loads(args.machine_report.read_text())if args.machine_report else None
    if machine and (machine['sourceMismatchCount'] or machine['reference']!=('clean-original-machine'if args.original else'pinned-redux-machine')):raise ValueError('Machine evidence differs')
    machine_rows={(r['kind'],r['base'],r['current']):r['machine']for r in machine['cases']}if machine else{}
    tests=[]
    for(f,kind),action in selected.items():
        for p in profiles(f,args.original):
            for seed in((1,)if args.pilot else range(1,65)if f==0xC29FE1 else range(1,9)):
                v=[len(tests),action,seed*0x9e3779b9&0xffffffff,0 if p.get('enemy')is None else p['enemy']+1,
                    0,5000,p.get('pp',100),5000,p.get('maxpp',300),0,0,0,0,0,0,0,255,255,255,255,255,255,p.get('luck',20),p.get('npc',0),
                    p.get('offense',80),p.get('defense',50),20,p.get('guts',80),0,0,0,0,0,p.get('conscious',1),0,0,0,0,0,p.get('member',1),20,20,0,0,0,0,
                    p.get('basedef',50),0,p.get('baseoff',80),p.get('baseguts',80),p.get('ap',100)]
                tests.append(dict(function=f,type=kind,action=action,profile=p,seed=seed,values=v))
    path=args.scratch/'cases.tsv';path.write_text('\n'.join(' '.join(map(str,t['values']))for t in tests)+'\n')
    run=subprocess.run([str(exe.resolve()),str(args.assets.resolve()),str(session.resolve()),str(path.resolve())],cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=300)
    log=args.scratch/'native.log';log.write_bytes(run.stdout+run.stderr);results={}
    for line in run.stdout.decode(errors='replace').splitlines():
        for prefix in('QA ','QA_DETAIL ','QA_STAT '):
            if line.startswith(prefix):r=json.loads(line[len(prefix):]);results.setdefault(r['id'],{}).update(r)
    rows=[];matched=0;counts=collections.Counter()
    for i,t in enumerate(tests):
        a=results.get(i,{});errors=[];nums=[]
        if 'textPcs'not in a:errors.append('Missing native result')
        else:
            wanted,nums=expected(t,a,args.original)
            for k,v in wanted.items():
                if a[k]!=v:errors.append(f'{k} got{a[k]} expected{v}')
            if nums and a['textCnums'][:len(nums)]!=nums:errors.append(f'Text stat/drain amount got{a["textCnums"]} expected{nums}')
            if a['depth']!=1 or a['steps']>=30000:errors.append('Native continuation incomplete')
            if not t['profile'].get('npc') and t['function']in(0xC28F21,0xC29254,0xC29E86):
                v=t['values']
                for field,base,current in(('offense',v[48],v[24]),('defense',v[46],v[25])):
                    applied=field=='offense'and t['function']in(0xC28F21,0xC29254)or field=='defense'and t['function']in(0xC28F21,0xC29E86)and a['rolls8'][0]*80//256>=v[22]
                    if t['function']==0xC28F21 and field=='defense':applied=True
                    m=machine_rows.get((field,base,current))if applied else None
                    if m is not None:
                        matched+=1
                        if a[field]!=m:errors.append(f'{field} machine got{m} native{a[field]}')
        counts[f'{t["function"]:06X}']+=1
        rows.append(dict(function=f'{t["function"]:06X}',actionId=t['action'],actionType=t['type'],profile=t['profile'],seed=t['seed'],passed=not errors,errors=errors,**({'actual':a}if errors else{})))
    refs=['src/game/battle_actions.c','src/game/battle_calc.c','asm/battle/actions/cut_guts.asm','asm/battle/actions/reduce_offense.asm','asm/battle/actions/reduce_offense_defense.asm','asm/battle/actions/defense_down_alpha.asm','asm/battle/actions/magnet_omega.asm','asm/battle/actions/magnet_alpha.asm','asm/battle/decrease_offense_16th.asm','asm/battle/decrease_defense_16th.asm']
    pinned=[]
    for p in('ccscript/main.ccs','ccscript/redux/offense_defense_psi_buff.ccs'):
        file=args.project/p;content=subprocess.check_output(['git','-C',str(args.project.parent),'show',f'{pin}:Project/{p}'])
        if file.read_bytes().replace(b'\r\n',b'\n')!=content.replace(b'\r\n',b'\n'):raise ValueError('Pin changed')
        pinned.append(dict(path=p,sha256=helper.digest(file),matchesPinnedSource=True))
    report=dict(schemaVersion=1,toolVersion='dev16-stat-drain',reduxRevision=pin,originalPack=args.original,runtimeSha256={n:helper.digest(args.runtime/n)for n in('player.exe','observer.exe')},assetsSha256=helper.digest(args.assets),privateBuild=build,nativeExitCode=run.returncode,nativeLogSha256=helper.digest(log),cases=rows,semanticCoverage=dict(completedCases=len(results),activeCallbacks=[f'{f:06X}'for f in FUNCTIONS],actionIds=list(selected.values()),callbackCaseCounts=dict(counts)),sourceReferences=[dict(path=p,sha256=helper.digest(args.native_source/p))for p in refs],pinnedReduxReferences=pinned,machineReportSha256=helper.digest(args.machine_report)if machine else None,machineComparedFields=matched,pilot=args.pilot,diagnostic=args.diagnostic,allPassed=run.returncode==0 and len(results)==len(tests)and all(r['passed']for r in rows),reproductionFlags={n:str(getattr(args,n.replace('-','_')))for n in('build','native-source','assets','runtime','scratch','output','project','machine-report')},limits=['Five prepared complete callbacks, real text children and displayed amounts. No outer command/target traversal, natural encounter, rendering/audio or complete story proof.','Ordinary stat corpus: current1..511 for offense/defense and base_guts/2..255 for guts; exact source floors and NPC guards. Zero/high-word offense/defense boundaries and synthetic guts below its own floor are excluded here. Separate private pilot exposed unsigned text-parameter extension only for those below-floor guts fixtures; natural reachability is unestablished.','Optional machine comparison corroborates unchanged/pinned stat-down helper results for matching inputs; full actions and CUTGUTS/Magnet are source-derived, not independently machine-tested.','Magnet tests Jeff-specific ally guard, NPC/nonconscious prepared contexts, zero/short/over-max PP and caster cap; no owner saves or serialized continuation proof.','Only player library executes; observer hash is provenance. Review source identities are separate from frozen executed library. No ROM/assets/dialogue/save payload included.'],fullConversionVerified=False,fullPlaythroughVerified=False)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(cases=len(rows),passed=sum(r['passed']for r in rows),allPassed=report['allPassed'],nativeExitCode=run.returncode,machineComparedFields=matched,firstFailures=[r for r in rows if not r['passed']][:3])))
    if not report['allPassed']and not args.diagnostic:raise SystemExit(1)


if __name__=='__main__':main()
