# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual PSI Flash callbacks, status priority, shields and selected KO children."""
import argparse, collections, json, os, subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
import battle_action_catalog_qa_dev15 as previous
from build_maternalbound_pack import read_pack

FUNCTIONS={0xC29987:(-1,-1,0),0xC299AE:(0,1,2),0xC299EF:(1,2,3),0xC29A35:(2,3,4)}
KO_IMMUNE={218,219,221,229}


def driver_source(original):
    s=previous.driver_source().replace('unsigned v[48],n=0;','unsigned v[52],n=0;').replace('n<48','n<52').replace('if(n!=48)','if(n!=52)')
    s=s.replace('static unsigned qa_function,','static unsigned flash_seen,flash_rolls[2],flash_roll_target,flash_ko_seen,flash_ko_target;static unsigned qa_function,')
    s=s.replace('qa_var_count=0;', '''qa_var_count=0;flash_seen=flash_ko_seen=0;flash_roll_target=flash_ko_target=65535;
        memset(flash_rolls,0,sizeof(flash_rolls));
        a->hp=a->hp_target=a->hp_max=5000;memset(a->afflictions,0,7);
        a->flash_resist=(uint8_t)v[50];a->shield_hp=(uint8_t)v[49];a->afflictions[6]=(uint8_t)v[48];
        if(a->ally_or_enemy==0)party_characters[a->id-1].max_hp=party_characters[a->id-1].current_hp=party_characters[a->id-1].current_hp_target=5000;
        bt.damage_is_reflected=bt.shield_has_nullified_damage=0;''')
    s=s.replace('StepResult r=mode_dispatch_step', '''
        if(g_mode_stack.mode[top]==GAME_MODE_BATTLE_ACTION && pc==2 && mode_child_result()==0) {
            RNGState saved=rng_state;flash_rolls[0]=rng_next_byte();flash_rolls[1]=rng_next_byte();rng_state=saved;
            flash_seen++;flash_roll_target=bt.current_target/sizeof(Battler);
        }
        StepResult r=mode_dispatch_step''')
    s=s.replace('if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);', '''
        if(g_mode_stack.mode[top]==GAME_MODE_BATTLE_ACTION && r.kind==STEP_PUSH && r.push_mode==GAME_MODE_BATTLE_KO) {
            flash_ko_seen++;flash_ko_target=r.push_init->battle_ko.target/sizeof(Battler);
        }
        if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);''')
    s=s.replace('        fflush(stdout);',r'''
        printf("QA_FLASH {\"id\":%u,\"rollSeen\":%u,\"effectRolls\":[%u,%u],\"effectTarget\":%u,\"koSeen\":%u,\"koTarget\":%u,\"casterAff\":[",
            v[0],flash_seen,flash_rolls[0],flash_rolls[1],flash_roll_target,flash_ko_seen,flash_ko_target);
        for(unsigned i=0;i<7;i++)printf("%s%u",i?",":"",a->afflictions[i]);
        printf("],\"casterShieldHp\":%u,\"reflected\":%u,\"shieldNull\":%u,\"targetExpValue\":%u,\"targetMoneyValue\":%u}\n",a->shield_hp,bt.damage_is_reflected,bt.shield_has_nullified_damage,(unsigned)t->exp,t->money);fflush(stdout);''')
    if original:s=s.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"').replace(' || !maternalbound_enabled()',' || maternalbound_enabled()')
    return s


def profiles():
    p=[dict(name=f'enemy-resistance-{res}',enemy=7,resist=res)for res in (0,64,128,192,255)]
    p.extend(dict(name=f'player-resistance-{res}',enemy=None,resist=res)for res in (0,128,255))
    p.append(dict(name='NPC-failure',enemy=7,resist=255,npc=5))
    for kind,hp in ((1,1),(1,3),(2,1),(2,3),(3,3),(4,3)):
        p.append(dict(name=f'enemy-shield-{kind}-hp-{hp}',enemy=7,resist=255,shield=kind,shield_hp=hp))
    for group,status in ((0,3),(0,4),(0,7),(2,1),(2,2),(2,3),(2,4),(3,1)):
        aff=[0]*7;aff[group]=status;p.append(dict(name=f'status-priority-{group}-{status}',enemy=7,resist=255,aff=aff))
    for enemy in sorted(KO_IMMUNE):p.append(dict(name=f'Giygas-{enemy}-prepared-KO-control',enemy=enemy,resist=255))
    return p


def expected(test,actual):
    p=test['profile'];v=test['values'];aff=p.get('aff',[0]*7).copy();aff[6]=p.get('shield',0);caster_aff=[0]*7
    hp=5000;caster_hp=5000;shield=p.get('shield_hp',0);exp=money=0;outcome='NPC';errors=[]
    reflection=p.get('shield',0)==1 and test['actionType']==3 and not p.get('npc',0)
    absorbed=p.get('shield',0)==2 and test['actionType']==3 and not p.get('npc',0)
    effect_target=(1 if p['enemy']is not None else 9)if reflection else (8 if p['enemy']is not None else 0)
    ko=False;seen=0;ko_target=65535
    if not p.get('npc',0):
        if absorbed:
            outcome='absorb';shield=(shield-1)&255
            if not shield:aff[6]=0
        else:
            seen=1;res=255 if reflection else p['resist'];roll=actual['effectRolls'][1]&7
            outcome='resisted'
            if actual['effectRolls'][0]<res:
                ko_max,para,strange=FUNCTIONS[test['function']]
                dest=caster_aff if reflection else aff
                if roll<=ko_max:
                    outcome='KO';ko=True;ko_target=effect_target
                    immune=not reflection and p['enemy']in KO_IMMUNE
                    if not immune:
                        dest[:]=[1,0,0,0,0,0,0]
                        if reflection:caster_hp=0
                        else:
                            hp=0
                            if p['enemy']is not None:exp=actual['targetExpValue'];money=actual['targetMoneyValue']
                else:
                    group,status=(0,3)if roll==para else (3,1)if roll==strange else (2,2)
                    outcome={0:'paralysis',3:'strange',2:'crying'}[group]
                    if not dest[group] or dest[group]>status:dest[group]=status
        if reflection:
            shield=(shield-1)&255
            if not shield:aff[6]=0
    wanted={'rollSeen':seen,'koSeen':int(ko),'koTarget':ko_target,'hp':hp,'attackerHp':caster_hp,'aff':aff,
        'casterAff':caster_aff,'shieldhp':shield,'casterShieldHp':0,'battleExp':exp,'battleMoney':money,
        'reflected':0,'shieldNull':0,'attackerRestored':1,'targetRestored':1}
    if seen:wanted['effectTarget']=effect_target
    for key,value in wanted.items():
        if actual.get(key)!=value:errors.append(f'{key}: got {actual.get(key)} expected {value}')
    return errors,outcome


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ('build','native-source','assets','runtime','scratch','output','project'):parser.add_argument('--'+n,type=Path,required=True)
    for n in ('original','pilot','diagnostic'):parser.add_argument('--'+n,action='store_true')
    args=parser.parse_args()
    if args.scratch.exists():raise ValueError('Fresh private scratch required')
    pin=subprocess.check_output(['git','-C',str(args.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=helper.PIN:raise ValueError('Unreviewed Redux revision')
    args.scratch.mkdir(parents=True);session=args.scratch/'session';session.mkdir()
    helper.DRIVER=driver_source(args.original);exe,build=helper.private_build(args)
    _,_,assets=read_pack(args.assets,args.native_source/'src/data/runtime_generated/asset_ids.h');data=assets['data/battle_action_table.bin'];actions={}
    for i in range(0,len(data),12):
        f=int.from_bytes(data[i+8:i+12],'little')
        if f in FUNCTIONS:actions.setdefault((f,data[i+2]),i//12)
    tests=[]
    for(f,action_type),action in actions.items():
        for p in profiles():
            for seed in ((1,7)if args.pilot else range(1,65)):
                aff=p.get('aff',[0]*7).copy();aff[6]=p.get('shield',0)
                v=[len(tests),action,seed*0x9e3779b9&0xffffffff,0 if p['enemy']is None else p['enemy']+1,0,5000,100,5000,300,
                    *aff,255,255,p['resist'],255,255,255,20,p.get('npc',0),80,50,20,0,p.get('shield_hp',0),0,0,0 if p['enemy']is not None else 8,
                    0,1,0,0,0,0,0,1,20,20,0,0,0,0,50,0,0,0,255,0]
                tests.append({'function':f,'actionType':action_type,'actionId':action,'profile':p,'seed':seed,'values':v})
    cases=args.scratch/'cases.tsv';cases.write_text('\n'.join(' '.join(map(str,t['values']))for t in tests)+'\n')
    run=subprocess.run([str(exe.resolve()),str(args.assets.resolve()),str(session.resolve()),str(cases.resolve())],cwd=session,
        env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=180)
    logfile=args.scratch/'native.log';logfile.write_bytes(run.stdout+run.stderr);results={}
    for line in run.stdout.decode(errors='replace').splitlines():
        for prefix in ('QA ','QA_DETAIL ','QA_FLASH '):
            if line.startswith(prefix):r=json.loads(line[len(prefix):]);results.setdefault(r['id'],{}).update(r)
    rows=[];outcomes=collections.Counter()
    for i,t in enumerate(tests):
        a=results.get(i,{});errors=[];outcome='missing'
        if 'rollSeen'not in a:errors.append('Missing native trace')
        else:
            errors,outcome=expected(t,a)
            if a['depth']!=1 or a['steps']>=30000:errors.append('Native continuation did not finish')
        outcomes[outcome]+=1;row={'function':f'{t["function"]:06X}','actionId':t['actionId'],'actionType':t['actionType'],'profile':t['profile'],
            'seed':t['seed'],'outcome':outcome,'passed':not errors,'errors':errors}
        if errors:row['actual']=a
        rows.append(row)
    refs=['src/game/battle_actions.c','src/game/battle_calc.c','src/game/battle.c','asm/battle/ko_target.asm','asm/battle/inflict_status.asm',
        'asm/battle/psi_shield_nullify.asm','asm/battle/weaken_shield.asm','asm/battle/actions/psi_flash_immunity_test.asm',
        *[f'asm/battle/actions/psi_flash_{name}.asm'for name in ('alpha','beta','gamma','omega','crying','paralysis','feeling_strange')]]
    report={'schemaVersion':1,'toolVersion':'dev16-flash','reduxRevision':pin,'originalPack':args.original,
        'runtimeSha256':{n:helper.digest(args.runtime/n)for n in ('player.exe','observer.exe')},'assetsSha256':helper.digest(args.assets),
        'privateBuild':build,'nativeExitCode':run.returncode,'nativeLogSha256':helper.digest(logfile),'cases':rows,
        'sourceReferences':[{'path':p,'sha256':helper.digest(args.native_source/p)}for p in refs],
        'sourceReferenceRole':'Current review sources separately identified from immutable tested library.',
        'semanticCoverage':{'completedCases':len(results),'activeCallbacks':[f'{f:06X}'for f in FUNCTIONS],
            'actionTypeRepresentatives':[{'function':f'{f:06X}','actionType':t,'actionId':i}for(f,t),i in actions.items()],
            'profiles':len(profiles()),'outcomes':dict(outcomes)},'pilot':args.pilot,'diagnostic':args.diagnostic,
        'allPassed':run.returncode==0 and len(results)==len(tests) and all(r['passed']for r in rows),
        'reproductionFlags':{k:str(getattr(args,k.replace('-','_')))for k in ('build','native-source','assets','runtime','scratch','output','project')},
        'limits':['Prepared complete Flash callbacks, real calculation/text/KO children, selected shield and status priority rules; no outer turn/AI/PP payment.',
            'Source-derived expectations and observed real effect-stage RNG inputs; no independent original-machine Flash execution.',
            'KO cases use ordinary no-final-attack enemy7 and nonpossessed players. Four normalized Giygas targets force resistance255 to exercise original KO guards; this is not proof of natural boss encounter behavior.',
            'Final attacks, group death, possession and NPC replacement inside KO remain unevaluated by this tool.',
            'Complete story/randomizer, physical controller input, pixels/audio and full encounter RNG timing remain unevaluated. Only player library executes; observer hash records provenance.',
            'No owner ROM/save/asset payload is published; successful detailed traces stay in hashed private log.'],
        'fullConversionVerified':False,'fullPlaythroughVerified':False}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cases':len(rows),'completed':len(results),'passed':sum(r['passed']for r in rows),
        'nativeExitCode':run.returncode,'allPassed':report['allPassed'],'outcomes':dict(outcomes),'firstFailures':[r for r in rows if not r['passed']][:2]}))
    return 0 if report['allPassed'] or args.diagnostic else 1


if __name__=='__main__':raise SystemExit(main())
