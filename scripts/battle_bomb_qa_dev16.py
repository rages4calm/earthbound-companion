# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual complete Bomb callbacks in prepared compact party configurations."""
import argparse,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
import battle_action_catalog_qa_dev15 as previous
from build_maternalbound_pack import read_pack

FUNCTIONS={0xC2A818:90,0xC2A821:270}

def driver_source(original):
    s=previous.driver_source();marker='static unsigned qa_function,qa_var_count,qa_var_rolls[32],qa_damage[16];'
    s=s.replace(marker,marker+r'''
static unsigned bomb_count,bomb_targets[4],bomb_damage[4],bomb_rolls[4][2],bomb_hp_before[BATTLER_COUNT],bomb_stage_rolls[2];
''')
    s=s.replace('unsigned v[48],n=0;','unsigned v[50],n=0;').replace('n<48','n<50').replace('if(n!=48)','if(n!=50)')
    s=s.replace('qa_var_count=0;', '''qa_var_count=0;bomb_count=0;
        memset(bt.battlers_table,0,sizeof(bt.battlers_table));
        memset(game_state.party_members,0,6);memset(game_state.party_order,0,6);
        game_state.party_count=game_state.player_controlled_party_count=v[48];game_state.current_party_members=(1u<<v[48])-1;
        for(unsigned i=0;i<v[48];i++) {
            game_state.party_members[i]=game_state.party_order[i]=i+1;
            party_characters[i].max_hp=party_characters[i].current_hp=party_characters[i].current_hp_target=5000;
            battle_init_player_stats(i+1,&bt.battlers_table[i]);
        }
        battle_init_enemy_stats(&bt.battlers_table[8],7);a=&bt.battlers_table[8];
        bt.current_attacker=8*sizeof(Battler);bt.current_target=v[49]*sizeof(Battler);t=battler_from_offset(bt.current_target);
        a->current_action=v[1];a->current_action_argument=0;
        original_attacker=bt.current_attacker;original_target=bt.current_target;
        for(unsigned i=0;i<BATTLER_COUNT;i++)bomb_hp_before[i]=bt.battlers_table[i].hp_target;
        ''')
    s=s.replace('StepResult r=mode_dispatch_step', '''
        if(g_mode_stack.mode[top]==GAME_MODE_BATTLE_ACTION && pc<=2) {
            RNGState saved=rng_state;bomb_stage_rolls[0]=rng_next_byte();bomb_stage_rolls[1]=rng_next_byte();rng_state=saved;
        }
        StepResult r=mode_dispatch_step''')
    s=s.replace('if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);', '''
        if(r.kind==STEP_PUSH && r.push_mode==GAME_MODE_BATTLE_CALC && r.push_init->battle_calc.kind==BC_RESIST_DAMAGE) {
            if(bomb_count>=4)return 30000;
            bomb_targets[bomb_count]=bt.current_target/sizeof(Battler);bomb_damage[bomb_count]=r.push_init->battle_calc.arg0;
            memcpy(bomb_rolls[bomb_count],bomb_stage_rolls,sizeof(bomb_stage_rolls));bomb_count++;
        }
        if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);''')
    s=s.replace('        fflush(stdout);',r'''
        printf("QA_BOMB {\"id\":%u,\"targets\":[",v[0]);for(unsigned i=0;i<bomb_count;i++)printf("%s%u",i?",":"",bomb_targets[i]);
        printf("],\"damage\":[");for(unsigned i=0;i<bomb_count;i++)printf("%s%u",i?",":"",bomb_damage[i]);
        printf("],\"rolls\":[");for(unsigned i=0;i<bomb_count;i++)printf("%s[%u,%u]",i?",":"",bomb_rolls[i][0],bomb_rolls[i][1]);
        printf("],\"hpBefore\":[");for(unsigned i=0;i<BATTLER_COUNT;i++)printf("%s%u",i?",":"",bomb_hp_before[i]);
        printf("],\"hpAfter\":[");for(unsigned i=0;i<BATTLER_COUNT;i++)printf("%s%u",i?",":"",bt.battlers_table[i].hp_target);
        printf("]}\n");fflush(stdout);''')
    if original:s=s.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"').replace(' || !maternalbound_enabled()',' || maternalbound_enabled()')
    return s

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in('build','native-source','assets','runtime','scratch','output','project','machine-report'):ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--original',action='store_true');ap.add_argument('--diagnostic',action='store_true');a=ap.parse_args()
    if a.scratch.exists():raise ValueError('Fresh scratch required')
    pin=subprocess.check_output(['git','-C',str(a.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=helper.PIN:raise ValueError('Unreviewed pin')
    m=json.loads(a.machine_report.read_text())
    if m['sourceMismatchCount']or m['reference']!=('clean-original-machine'if a.original else'pinned-redux-machine'):raise ValueError('Wrong machine proof')
    a.scratch.mkdir(parents=True);session=a.scratch/'session';session.mkdir();helper.DRIVER=driver_source(a.original);exe,build=helper.private_build(a)
    _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h');table=assets['data/battle_action_table.bin'];selected={}
    for i in range(len(table)//12):
        f=int.from_bytes(table[i*12+8:i*12+12],'little');kind=table[i*12+2]
        if f in FUNCTIONS:selected.setdefault((f,kind),i)
    tests=[]
    for(f,kind),action in selected.items():
        for count in range(1,5):
            for slot in range(count):
                for seed in range(1,65):
                    v=[len(tests),action,seed*0x9e3779b9&0xffffffff,0,0,5000,100,5000,300,0,0,0,0,0,0,0,255,255,255,255,255,255,20,0,80,50,20,0,0,0,0,0,0,1,0,0,0,0,0,1,20,20,0,0,0,0,50,0,count,slot]
                    tests.append(dict(function=f,type=kind,action=action,count=count,slot=slot,seed=seed,values=v))
    path=a.scratch/'cases.tsv';path.write_text('\n'.join(' '.join(map(str,t['values']))for t in tests)+'\n')
    run=subprocess.run([str(exe.resolve()),str(a.assets.resolve()),str(session.resolve()),str(path.resolve())],cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=120)
    log=a.scratch/'native.log';log.write_bytes(run.stdout+run.stderr);results={}
    for line in run.stdout.decode(errors='replace').splitlines():
        for prefix in('QA ','QA_DETAIL ','QA_BOMB '):
            if line.startswith(prefix):r=json.loads(line[len(prefix):]);results.setdefault(r['id'],{}).update(r)
    rows=[]
    for i,t in enumerate(tests):
        r=results.get(i,{});errors=[];slot=t['slot'];wanted=[slot]+([slot-1]if slot else[])+([slot+1]if slot+1<t['count']else[])
        if 'targets'not in r:errors.append('Missing native trace')
        else:
            if r['targets']!=wanted:errors.append(f'Adjacency target sequence got{r["targets"]} expected{wanted}')
            hp=r['hpBefore'].copy()
            for j,(target,damage,rolls)in enumerate(zip(r['targets'],r['damage'],r['rolls'])):
                value=helper.variance_reference(FUNCTIONS[t['function']]>>(int(j>0)),rolls,0)
                if damage!=value:errors.append(f'Variance input{j} got{damage} expected{value}')
                if target<t['count']:hp[target]-=max(damage,1)
            if r['hpAfter']!=hp:errors.append('HP outcomes differ from actual validated damage children')
            if not r['targetRestored']or not r['attackerRestored']or r['depth']!=1:errors.append('Native continuation context differs')
        rows.append(dict(function=f'{t["function"]:06X}',actionId=t['action'],actionType=t['type'],partyCount=t['count'],primarySlot=slot,seed=t['seed'],expectedSourceTargets=wanted,actualTargets=r.get('targets'),passed=not errors,errors=errors))
    refs=['src/game/battle_actions.c','src/game/battle_calc.c','asm/battle/actions/bomb_common.asm','asm/battle/actions/bomb.asm','asm/battle/actions/super_bomb.asm','include/macros.asm']
    report=dict(schemaVersion=1,toolVersion='dev16-bomb',reduxRevision=pin,originalPack=a.original,runtimeSha256={n:helper.digest(a.runtime/n)for n in('player.exe','observer.exe')},assetsSha256=helper.digest(a.assets),privateBuild=build,nativeExitCode=run.returncode,nativeLogSha256=helper.digest(log),machineReportSha256=helper.digest(a.machine_report),sourceReferences=[dict(path=p,sha256=helper.digest(a.native_source/p))for p in refs],cases=rows,semanticCoverage=dict(completedCases=len(results),activeCallbacks=[f'{f:06X}'for f in FUNCTIONS]),allPassed=run.returncode==0 and len(results)==len(tests)and all(r['passed']for r in rows),diagnostic=a.diagnostic,reproductionFlags={n:str(getattr(a,n.replace('-','_')))for n in('build','native-source','assets','runtime','scratch','output','project','machine-report')},limits=['Prepared compact1..4-player party fixtures, every primary party slot, real complete Bomb/Super Bomb damage/text/calculation children. Source neighbor ordering independently machine-checked with stubbed machine damage children.','Only player library executes; observer identity is provenance. Enemy splash layout, shields, lethal outcomes, actual AI selection, full battle and natural story progression unevaluated.','No owner payload/save/ROM bytes included; all transient fixtures remain private. Source/runtime identities explicitly separate.'],fullConversionVerified=False,fullPlaythroughVerified=False)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(cases=len(rows),passed=sum(r['passed']for r in rows),allPassed=report['allPassed'],nativeExitCode=run.returncode,firstFailures=[r for r in rows if not r['passed']][:2])))
    if not report['allPassed']and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
