# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual multi-hit Thunder continuations in bounded nonlethal source fixtures."""
import argparse,collections,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
import battle_action_catalog_qa_dev15 as previous
from build_maternalbound_pack import read_pack

FUNCTIONS={0xC29871:(120,1),0xC2987D:(120,2),0xC29889:(200,3),0xC29895:(200,4)}
INDICES=(0,1,2,3,8,9,10,11,12)

def driver_source(original):
    source=previous.driver_source().replace('unsigned v[48],n=0;','unsigned v[64],n=0;').replace('n<48','n<64').replace('if(n!=48)','if(n!=64)')
    source=source.replace('static unsigned qa_function,',r'''
typedef struct {unsigned choiceRoll,hitRoll,target,threshold,success,variance[2],damageSeen,damage,damageTarget;} ThunderHit;
static ThunderHit thunder_hits[4];static unsigned thunder_count,pending_rolls[2];
static const unsigned thunder_indices[9]={0,1,2,3,8,9,10,11,12};
static unsigned qa_function,''')
    source=source.replace('qa_var_count=0;', '''qa_var_count=0;thunder_count=0;memset(thunder_hits,0,sizeof(thunder_hits));
        for(unsigned i=0;i<4;i++) {
            Battler *p=&bt.battlers_table[i];p->hp=p->hp_target=p->hp_max=5000;
            party_characters[i].max_hp=party_characters[i].current_hp=party_characters[i].current_hp_target=5000;
            memset(p->afflictions,0,7);p->shield_hp=0;
            party_characters[i].items[0]=(v[53]&(1u<<i))?1:0;
            if(v[53]&(1u<<i))p->current_action=(uint16_t)v[58];
        }
        for(unsigned i=8;i<=12;i++) {
            battle_init_enemy_stats(&bt.battlers_table[i],7);
            Battler *p=&bt.battlers_table[i];p->hp=p->hp_target=p->hp_max=5000;
            memset(p->afflictions,0,7);p->shield_hp=0;
        }
        bt.enemies_in_battle=4;
        bt.current_attacker=(v[48]?12:1)*sizeof(Battler);a=battler_from_offset(bt.current_attacker);
        a->current_action=(uint16_t)v[1];a->current_action_argument=0;
        a->afflictions[STATUS_GROUP_SHIELD]=(uint8_t)v[56];a->shield_hp=(uint8_t)v[57];
        bt.battler_target_flags=0;
        for(unsigned i=0;i<v[49];i++) {
            unsigned index=(v[48]?0:8)+i;Battler *p=&bt.battlers_table[index];
            bt.battler_target_flags|=1u<<index;
            if(v[50]&(1u<<i))p->afflictions[0]=1;
            if(v[51]&(1u<<i))p->afflictions[0]=2;
            if(v[52]&(1u<<i))p->consciousness=0;
            p->afflictions[6]=(uint8_t)v[54];p->shield_hp=(uint8_t)v[55];
        }
        bt.current_target=(v[48]?0:8)*sizeof(Battler);t=battler_from_offset(bt.current_target);
        original_attacker=bt.current_attacker;original_target=bt.current_target;
        bt.damage_is_reflected=bt.shield_has_nullified_damage=0;''')
    source=source.replace('StepResult r=mode_dispatch_step', '''
        if(g_mode_stack.mode[top]==GAME_MODE_BATTLE_ACTION) {
            RNGState saved=rng_state;pending_rolls[0]=rng_next_byte();pending_rolls[1]=rng_next_byte();rng_state=saved;
            if(thunder_count && ((pc==5 && mode_child_result()==0) ||
                (pc==4 && g_mode_stack.state[top].battle_action.scratch16[1] && maternalbound_enabled()))) {
                thunder_hits[thunder_count-1].variance[0]=pending_rolls[0];
                thunder_hits[thunder_count-1].variance[1]=pending_rolls[1];
            }
        }
        StepResult r=mode_dispatch_step''')
    source=source.replace('if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);', '''
        if(g_mode_stack.mode[top]==GAME_MODE_BATTLE_ACTION) {
            BattleActionState *action=&g_mode_stack.state[top].battle_action;
            if(r.kind==STEP_PUSH && r.push_mode==GAME_MODE_DISPLAY_TEXT && (action->pc==2 || action->pc==7)) {
                if(thunder_count>=4)return 30000;ThunderHit *h=&thunder_hits[thunder_count++];
                h->choiceRoll=pending_rolls[0];h->hitRoll=pending_rolls[1];
                h->target=bt.current_target/sizeof(Battler);h->threshold=action->scratch16[0];h->success=action->pc==2;
            }
            if(thunder_count && r.kind==STEP_PUSH && r.push_mode==GAME_MODE_BATTLE_CALC &&
                r.push_init->battle_calc.kind==BC_RESIST_DAMAGE) {
                ThunderHit *h=&thunder_hits[thunder_count-1];h->damageSeen++;
                h->damage=r.push_init->battle_calc.arg0;h->damageTarget=bt.current_target/sizeof(Battler);
            }
        }
        if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);''')
    source=source.replace('        fflush(stdout);',r'''
        printf("QA_THUNDER {\"id\":%u,\"hits\":[",v[0]);
        for(unsigned i=0;i<thunder_count;i++) {
            ThunderHit *h=&thunder_hits[i];
            printf("%s{\"choiceRoll\":%u,\"hitRoll\":%u,\"target\":%u,\"threshold\":%u,\"success\":%u,\"variance\":[%u,%u],\"damageSeen\":%u,\"damage\":%u,\"damageTarget\":%u}",
                i?",":"",h->choiceRoll,h->hitRoll,h->target,h->threshold,h->success,h->variance[0],h->variance[1],h->damageSeen,h->damage,h->damageTarget);
        }
        printf("],\"hpAll\":[");for(unsigned i=0;i<9;i++)printf("%s%u",i?",":"",bt.battlers_table[thunder_indices[i]].hp_target);
        printf("],\"shieldAll\":[");for(unsigned i=0;i<9;i++)printf("%s%u",i?",":"",bt.battlers_table[thunder_indices[i]].shield_hp);
        printf("],\"shieldTypes\":[");for(unsigned i=0;i<9;i++)printf("%s%u",i?",":"",bt.battlers_table[thunder_indices[i]].afflictions[6]);
        printf("],\"targetFlags\":%u,\"reflected\":%u}\n",(unsigned)bt.battler_target_flags,bt.damage_is_reflected);fflush(stdout);''')
    if original:source=source.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"').replace(' || !maternalbound_enabled()',' || maternalbound_enabled()')
    return source

def profiles():
    p=[dict(name=f'enemies-{n}',players=0,count=n)for n in (0,1,2,4)]
    p.extend(dict(name=f'players-{n}',players=1,count=n)for n in (1,2,4))
    p.extend([dict(name='one-unconscious',players=0,count=4,unconscious=1),
        dict(name='one-diamondized',players=0,count=4,diamond=1),
        dict(name='all-untargettable',players=0,count=4,unconscious=3,diamond=4,inactive=8)])
    for shield in (1,2,3,4):p.append(dict(name=f'enemy-shield-{shield}',players=0,count=1,shield=shield,shield_hp=3))
    for shield,caster_shield in ((0,0),(2,0),(4,0),(2,2),(4,4)):
        p.append(dict(name=f'badge-ownshield-{shield}-castershield-{caster_shield}',players=1,count=1,
            badge=1,shield=shield,shield_hp=3 if shield else 0,caster_shield=caster_shield,caster_hp=3 if caster_shield else 0))
    p.append(dict(name='mixed-badge-targets',players=1,count=4,badge=5,shield=2,shield_hp=3))
    for caster_shield in (0,2):
        p.append(dict(name=f'badge-PSI-action-castershield-{caster_shield}',players=1,count=1,badge=1,
            shield=2,shield_hp=3,caster_shield=caster_shield,caster_hp=3 if caster_shield else 0,badge_action=22,badge_action_type=3))
    return p

def expected(test,actual,original):
    p=test['profile'];power,count=FUNCTIONS[test['function']];start=0 if p['players'] else 8;caster=12 if p['players'] else 1
    hp={i:5000 for i in INDICES};shield={i:0 for i in INDICES};kind={i:0 for i in INDICES}
    shield[caster]=p.get('caster_hp',0);kind[caster]=p.get('caster_shield',0)
    for i in range(p['count']):kind[start+i]=p.get('shield',0);shield[start+i]=p.get('shield_hp',0)
    valid=[start+i for i in range(p['count']) if not ((p.get('unconscious',0)|p.get('diamond',0)|p.get('inactive',0))&(1<<i))]
    # Original cyclic scan advances from bit0 before checking the first bit.
    order=sorted(valid,key=lambda i:(i==0,i));wanted_count=count if valid else 0;errors=[];outcomes=[]
    if len(actual['hits'])!=wanted_count:errors.append(f'Hit attempts got {len(actual["hits"])} expected {wanted_count}')
    for hit in actual['hits']:
        if not order:errors.append('Unexpected hit with no valid targets');continue
        target=order[(hit['choiceRoll']&31)%len(order)];threshold=min(p['count']*64,255);success=hit['hitRoll']<threshold
        wanted={'target':target,'threshold':threshold,'success':int(success),'damageSeen':0}
        if success:
            badge=target<4 and p.get('badge',0)&(1<<target)
            destination=target;absorbed=False
            if badge:
                destination=caster
                if not original:
                    # Enabled Thunder_Reflection_Fix bypasses PSI shield tests
                    # and the badge-holder's WEAKEN_SHIELD tail.
                    damage=helper.variance_reference(power,hit['variance'],0)
                    hp[caster]-=damage
                    if kind[caster]==4:
                        shield[caster]=(shield[caster]-1)&255
                        if not shield[caster]:kind[caster]=0
                else:
                    # The source swaps CURRENT_ATTACKER to the badge holder.
                    # Idle holder action0/type0 bypasses the caster's shield;
                    # the real PSI-action holder control permits absorption.
                    if kind[caster] in (1,2):shield[caster]=1
                    if kind[caster]==2 and p.get('badge_action_type',0)==3:
                        shield[caster]=0;kind[caster]=0;absorbed=True
                    else:hp[caster]-=helper.variance_reference(power,hit['variance'],0)
                    shield[target]=(shield[target]-1)&255
                    if not shield[target]:kind[target]=0
            elif kind[target]==2 and test['actionType']==3:
                shield[target]=0;kind[target]=0;absorbed=True
            elif kind[target]==1 and test['actionType']==3:
                destination=caster;hp[caster]-=helper.variance_reference(power,hit['variance'],0)
                shield[target]=0;kind[target]=0
            else:
                if kind[target] in (1,2):shield[target]=1
                hp[target]-=helper.variance_reference(power,hit['variance'],0)
            if not absorbed:wanted.update(damageSeen=1,damage=helper.variance_reference(power,hit['variance'],0),damageTarget=destination)
            outcomes.append('absorb'if absorbed else 'badge'if badge else 'reflect'if destination!=target else'hit')
        else:outcomes.append('miss')
        for key,value in wanted.items():
            if hit[key]!=value:errors.append(f'{key}: got {hit[key]} expected {value}')
    wanted={'hpAll':[hp[i]for i in INDICES],'shieldAll':[shield[i]for i in INDICES],
        'shieldTypes':[kind[i]for i in INDICES],'targetFlags':0,'reflected':0,'attackerRestored':1}
    for key,value in wanted.items():
        if actual[key]!=value:errors.append(f'{key}: got {actual[key]} expected {value}')
    return errors,outcomes

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
    _,_,assets=read_pack(args.assets,args.native_source/'src/data/runtime_generated/asset_ids.h');data=assets['data/battle_action_table.bin']
    actions={}
    for i in range(0,len(data),12):
        f=int.from_bytes(data[i+8:i+12],'little')
        if f in FUNCTIONS:actions.setdefault((f,data[i+2]),i//12)
    tests=[]
    for (f,action_type),action in actions.items():
        for p in profiles():
            for seed in ((1,7)if args.pilot else range(1,65)):
                v=[len(tests),action,seed*0x9e3779b9&0xffffffff,8,0,5000,100,5000,300,
                    0,0,0,0,0,0,0,255,255,255,255,255,255,20,0,80,50,20,0,0,0,0,0,
                    0,1,0,0,0,0,0,1,20,20,0,0,0,0,50,0,
                    p['players'],p['count'],p.get('unconscious',0),p.get('diamond',0),p.get('inactive',0),p.get('badge',0),
                    p.get('shield',0),p.get('shield_hp',0),p.get('caster_shield',0),p.get('caster_hp',0),p.get('badge_action',0),0,0,0,0,0]
                tests.append({'function':f,'actionId':action,'actionType':action_type,'profile':p,'seed':seed,'values':v})
    path=args.scratch/'cases.tsv';path.write_text('\n'.join(' '.join(map(str,t['values']))for t in tests)+'\n')
    run=subprocess.run([str(exe.resolve()),str(args.assets.resolve()),str(session.resolve()),str(path.resolve())],cwd=session,
        env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=180)
    logfile=args.scratch/'native.log';logfile.write_bytes(run.stdout+run.stderr);results={}
    for line in run.stdout.decode(errors='replace').splitlines():
        for prefix in ('QA ','QA_DETAIL ','QA_THUNDER '):
            if line.startswith(prefix):r=json.loads(line[len(prefix):]);results.setdefault(r['id'],{}).update(r)
    rows=[];outcomes=collections.Counter()
    for i,t in enumerate(tests):
        a=results.get(i,{});errors=[];case_outcomes=[]
        if 'hits'not in a:errors.append('Missing native trace')
        else:
            errors,case_outcomes=expected(t,a,args.original)
            if a['depth']!=1 or a['steps']>=30000:errors.append('Native continuation did not finish')
        outcomes.update(case_outcomes);row={'function':f'{t["function"]:06X}','actionId':t['actionId'],'actionType':t['actionType'],'profile':t['profile'],'seed':t['seed'],
            'hitOutcomes':case_outcomes,'passed':not errors,'errors':errors}
        if errors:row['actual']=a
        rows.append(row)
    refs=['src/game/battle_actions.c','src/game/battle_calc.c','src/game/battle_targeting.c','asm/battle/actions/psi_thunder_common.asm',
        'asm/battle/random_targetting.asm','asm/battle/psi_shield_nullify.asm','asm/battle/weaken_shield.asm','asm/battle/calc_damage_reduction.asm']
    pinned=[]
    for p in ('ccscript/main.ccs','ccscript/bugfixes/thunder_reflect_fix.ccs'):
        f=args.project/p;b=subprocess.check_output(['git','-C',str(args.project.parent),'show',f'{pin}:Project/{p}'])
        if f.read_bytes().replace(b'\r\n',b'\n')!=b.replace(b'\r\n',b'\n'):raise ValueError('Pinned source differs')
        pinned.append({'path':p,'sha256':helper.digest(f),'matchesPinnedSource':True})
    report={'schemaVersion':1,'toolVersion':'dev16-thunder','reduxRevision':pin,'originalPack':args.original,
        'runtimeSha256':{n:helper.digest(args.runtime/n)for n in ('player.exe','observer.exe')},'assetsSha256':helper.digest(args.assets),
        'privateBuild':build,'nativeExitCode':run.returncode,'nativeLogSha256':helper.digest(logfile),'cases':rows,
        'sourceReferences':[{'path':p,'sha256':helper.digest(args.native_source/p)}for p in refs],'pinnedReduxReferences':pinned,
        'sourceReferenceRole':'Current review files separately identified from immutable tested library.',
        'semanticCoverage':{'completedCases':len(results),'activeCallbacks':[f'{f:06X}'for f in FUNCTIONS],'actionTypeRepresentatives':[{'function':f'{f:06X}','actionType':t,'actionId':i}for(f,t),i in actions.items()],'profiles':len(profiles()),'hitOutcomes':dict(outcomes)},
        'pilot':args.pilot,'diagnostic':args.diagnostic,'allPassed':run.returncode==0 and len(results)==len(tests) and all(r['passed']for r in rows),
        'reproductionFlags':{n:str(getattr(args,n.replace('-','_')))for n in ('build','native-source','assets','runtime','scratch','output','project')},
        'limits':['Actual complete Thunder callback hit loops, native random targeting/filtering, text/waits/calculations and selected badge/shield interactions; no outer turn/AI/PP payment.',
            'Source-derived state/roll expectations; no independent full original-machine Thunder oracle.',
            'Target/attacker HP is normalized to prevent KO. Lethal/side-wipe/final-attack branches and reflective shields on the badge-reflected caster remain unevaluated.',
            'RNG observations occur at actual effect stages without consumption; complete encounter RNG timing is not certified.',
            'Initial targeted count controls hit chance even when statuses filter some targets, matching original source.',
            'Pixel/audio/animation timing/physical input/story/randomizer progression remain unevaluated. Only player library executed; observer hash is provenance.',
            'Successful raw traces remain in hashed private log; no owner ROM/save/asset payload in the public report.'],
        'fullConversionVerified':False,'fullPlaythroughVerified':False}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cases':len(rows),'completed':len(results),'passed':sum(r['passed']for r in rows),'nativeExitCode':run.returncode,
        'allPassed':report['allPassed'],'hitOutcomes':dict(outcomes),'firstFailures':[r for r in rows if not r['passed']][:2]}))
    if not report['allPassed']and not args.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
