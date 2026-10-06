# SPDX-License-Identifier: GPL-3.0-or-later
"""Real physical callbacks and nested calculations with exact source assertions.

Prepared nonlethal contexts. Production code is linked unchanged from an
immutable library; stage RNG observation does not consume or replace it.
"""
import argparse
import collections
import json
import os
from pathlib import Path
import subprocess

import battle_action_catalog_qa as helper
import battle_action_catalog_qa_dev15 as previous
from build_maternalbound_pack import read_pack


FUNCTIONS={0xC2859F:('Bash',2,True),0xC285DA:('Level4',4,True),
    0xC28651:('Level3',3,True),0xC286CB:('Level1',1,True),
    0xC28740:('Shoot',2,False),0xC28FF9:('DoubleBash',2,True)}
IMMUNE=(93,192,219,221,229)


def driver_source(original):
    source=previous.driver_source()
    source=source.replace('static unsigned qa_function,',r'''
typedef struct {
    unsigned missRoll,missResult,smashCalled,smashRoll,smashResult,postCaptured,postRolls[8];
    unsigned rawSeen,rawDamage,resist,hpBefore,hpAfter,attackerBefore,attackerAfter,shieldBefore,shieldAfter;
    unsigned affBefore[7],affAfter[7];
} PhysicalHit;
static PhysicalHit physical_hits[8];static unsigned physical_count,physical_indices[5];
static Battler *physical_target,*physical_attacker;
static const unsigned physical_functions[5]={0xC2859F,0xC285DA,0xC28651,0xC286CB,0xC28740};
static unsigned physical_function(unsigned index) {
    for(unsigned i=0;i<5;i++)if(index==physical_indices[i])return physical_functions[i];return 0;
}
static void physical_end(void) {
    if(!physical_count)return;PhysicalHit *h=&physical_hits[physical_count-1];
    h->hpAfter=physical_target->hp_target;h->attackerAfter=physical_attacker->hp_target;
    h->shieldAfter=physical_target->shield_hp;
    for(unsigned i=0;i<7;i++)h->affAfter[i]=physical_target->afflictions[i];
}
static unsigned qa_function,''')
    source=source.replace('FILE *input=fopen(argv[3],"r");', '''
    for(unsigned i=0;i<5;i++) {
        ModeState temporary={0};
        if(!battle_action_dispatch(physical_functions[i],&temporary))return 21;
        physical_indices[i]=temporary.battle_action.table_index;
    }
    FILE *input=fopen(argv[3],"r");''')
    source=source.replace('unsigned v[48],n=0;', 'unsigned v[56],n=0;').replace('n<48','n<56').replace('if(n!=48)', 'if(n!=56)')
    source=source.replace('qa_var_count=0;', '''qa_var_count=0;physical_count=0;memset(physical_hits,0,sizeof(physical_hits));
        physical_target=t;physical_attacker=a;
        a->hp=a->hp_target=a->hp_max=5000;a->guts=(uint16_t)v[51];
        a->offense=(uint16_t)v[52];a->speed=(uint16_t)v[53];
        a->afflictions[STATUS_GROUP_TEMPORARY]=(uint8_t)v[49];
        a->afflictions[STATUS_GROUP_PERSISTENT_EASYHEAL]=(uint8_t)v[50];
        if(a->ally_or_enemy==0) {
            CharStruct *ca=&party_characters[a->id-1];ca->max_hp=ca->current_hp=ca->current_hp_target=5000;
            ca->items[0]=(uint8_t)v[48];ca->equipment[EQUIP_WEAPON]=v[48]?1:0;
        }''')
    source=source.replace('StepResult r=mode_dispatch_step', '''
        if(g_mode_stack.mode[top]==GAME_MODE_BATTLE_CALC &&
            g_mode_stack.state[top].battle_calc.pc==0 &&
            g_mode_stack.state[top].battle_calc.kind==BC_MISS_CALC) {
            physical_end();if(physical_count>=8)return 30000;
            PhysicalHit *h=&physical_hits[physical_count++];
            h->hpBefore=physical_target->hp_target;h->attackerBefore=physical_attacker->hp_target;
            h->shieldBefore=physical_target->shield_hp;
            for(unsigned i=0;i<7;i++)h->affBefore[i]=physical_target->afflictions[i];
            RNGState saved=rng_state;h->missRoll=rng_next_byte();rng_state=saved;
        }
        if(physical_count && g_mode_stack.mode[top]==GAME_MODE_BATTLE_CALC &&
            g_mode_stack.state[top].battle_calc.pc==0 &&
            g_mode_stack.state[top].battle_calc.kind==BC_SMAAAASH) {
            PhysicalHit *h=&physical_hits[physical_count-1];h->smashCalled++;
            RNGState saved=rng_state;h->smashRoll=rng_next_byte();rng_state=saved;
        }
        if(physical_count && g_mode_stack.mode[top]==GAME_MODE_BATTLE_ACTION) {
            unsigned f=physical_function(g_mode_stack.state[top].battle_action.table_index);
            if(f && pc==1)physical_hits[physical_count-1].missResult=(unsigned)mode_child_result();
            if(f && pc==2 && f!=0xC28740)physical_hits[physical_count-1].smashResult=(unsigned)mode_child_result();
            if(f && mode_child_result()==0 && (pc==(f==0xC28740?1:2))) {
                PhysicalHit *h=&physical_hits[physical_count-1];h->postCaptured++;
                RNGState saved=rng_state;for(unsigned i=0;i<8;i++)h->postRolls[i]=rng_next_byte();rng_state=saved;
            }
        }
        StepResult r=mode_dispatch_step''')
    source=source.replace('if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);', '''
        if(physical_count && r.kind==STEP_PUSH && r.push_mode==GAME_MODE_BATTLE_CALC &&
            r.push_init->battle_calc.kind==BC_RESIST_DAMAGE) {
            PhysicalHit *h=&physical_hits[physical_count-1];h->rawSeen++;
            h->rawDamage=r.push_init->battle_calc.arg0;h->resist=r.push_init->battle_calc.arg1;
        }
        if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);''')
    source=source.replace('        fflush(stdout);',r'''
        physical_end();printf("QA_PHYSICAL {\"id\":%u,\"hits\":[",v[0]);
        for(unsigned i=0;i<physical_count;i++) {
            PhysicalHit *h=&physical_hits[i];
            printf("%s{\"missRoll\":%u,\"missResult\":%u,\"smashCalled\":%u,\"smashRoll\":%u,\"smashResult\":%u,\"postCaptured\":%u,\"postRolls\":[",i?",":"",
                h->missRoll,h->missResult,h->smashCalled,h->smashRoll,h->smashResult,h->postCaptured);
            for(unsigned j=0;j<8;j++)printf("%s%u",j?",":"",h->postRolls[j]);
            printf("],\"rawSeen\":%u,\"rawDamage\":%u,\"resist\":%u,\"hpBefore\":%u,\"hpAfter\":%u,\"attackerBefore\":%u,\"attackerAfter\":%u,\"shieldBefore\":%u,\"shieldAfter\":%u,\"affBefore\":[",
                h->rawSeen,h->rawDamage,h->resist,h->hpBefore,h->hpAfter,h->attackerBefore,h->attackerAfter,h->shieldBefore,h->shieldAfter);
            for(unsigned j=0;j<7;j++)printf("%s%u",j?",":"",h->affBefore[j]);
            printf("],\"affAfter\":[");for(unsigned j=0;j<7;j++)printf("%s%u",j?",":"",h->affAfter[j]);printf("]}");
        }
        printf("],\"smaaaashFlag\":%u}\n",bt.is_smaaaash_attack);fflush(stdout);''')
    if original:
        source=source.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"').replace(' || !maternalbound_enabled()', ' || maternalbound_enabled()')
    return source


def profiles(items):
    p=[dict(name='normal',enemy=7),dict(name='floor',enemy=7,defense=400),
       dict(name='raw-one',enemy=7,raw_one=True),dict(name='fast',enemy=64,speed=200),
       dict(name='paralyzed',enemy=7,easy=3,speed=200),dict(name='solidified',enemy=7,temp=4,speed=200),
       dict(name='strange',enemy=7,strange=1),dict(name='guarding',enemy=7,guarding=1),
       dict(name='guard-and-shield',enemy=7,guarding=1,shield=4,shield_hp=3),
       dict(name='power-shield',enemy=7,shield=3,shield_hp=3),
       dict(name='shield-break',enemy=7,shield=4,shield_hp=1),
       dict(name='psi-shield',enemy=7,shield=1,shield_hp=3),
       dict(name='forced-smash',enemy=7,guts=500,strange=1),
       dict(name='forced-smash-zero',enemy=7,guts=500,defense=320),
       dict(name='forced-smash-power-shield',enemy=7,guts=500,shield=3,shield_hp=3),
       dict(name='pc-crying',enemy=7,crying=2),dict(name='pc-nausea',enemy=7,nausea=4),
       dict(name='enemy-attacker',enemy=None,attacker_enemy=64),
       dict(name='enemy-attacker-crying',enemy=None,attacker_enemy=64,crying=2),
       dict(name='enemy-attacker-nausea',enemy=None,attacker_enemy=64,nausea=4)]
    p.extend(dict(name=f'immune-boss-{e}',enemy=e) for e in IMMUNE)
    p.append(dict(name='giygas4-damageable',enemy=220))
    # Select actual weapons for every distinct packed miss parameter.
    weapons={}
    for i in range(1,len(items)//39):
        row=items[i*39:(i+1)*39]
        if row[25] in (16,17):weapons.setdefault(row[34],i)
    p.extend(dict(name=f'weapon-{item}-special-{special}',enemy=7,weapon=item)
        for special,item in sorted(weapons.items()))
    return p


def expected_hits(test,actual,items,enemies,original):
    p=test['profile'];v=test['values'];_,mult,smash=FUNCTIONS[test['function']]
    before={'hp':5000,'attackerHp':5000,'shield':v[28],'aff':v[9:16].copy()};errors=[];outcomes=[]
    wanted_count=2 if test['function']==0xC28FF9 else 1
    if len(actual)!=wanted_count:errors.append(f'Attack count got{len(actual)} expected{wanted_count}')
    for hit in actual:
        for key,value in [('hpBefore',before['hp']),('attackerBefore',before['attackerHp']),
                          ('shieldBefore',before['shield']),('affBefore',before['aff'])]:
            if hit[key]!=value:errors.append(f'{key}: got {hit[key]} expected {value}')
        if p.get('attacker_enemy') is not None:
            miss=enemies[p['attacker_enemy']*94+68]
            if not original and p.get('crying')==2:miss+=8
        else:
            weapon=p.get('weapon',0)
            miss=((((items[weapon*39+34]-128)&65535)^0xff80) if weapon else 1)
            if p.get('crying')==2 or p.get('nausea')==4:miss=(miss+8)&65535
        missed=bool(miss and (miss-1)>=hit['missRoll']*16//256)
        critical=not missed and smash and hit['smashRoll']*500//256<max(p.get('guts',0),0 if p.get('attacker_enemy') is not None else 25)
        called=not missed and smash
        expect={'missResult':int(missed),'smashCalled':int(called),'smashResult':int(critical),
                'postCaptured':int(not missed and not critical)}
        rolls=hit['postRolls'];easy=before['aff'][0];temp=before['aff'][2]
        chance=p.get('speed',20)*2-20
        dodge_allowed=not (easy==3 or temp in (1,3,4)) and chance>=0
        dodged=not missed and not critical and dodge_allowed and rolls[0]*500//256<chance
        got_damage=not missed and not dodged
        expect['rawSeen']=int(got_damage)
        if got_damage:
            if critical:
                raw=(80*4-v[25])&65535
                if before['aff'][6] in (3,4):before['shield']=1
            else:
                raw=(80*mult-v[25])&65535
                signed=raw if raw<32768 else raw-65536
                if signed>1:raw=helper.variance_reference(raw,rolls[int(dodge_allowed):int(dodge_allowed)+2],1)
                if raw>=32768 or raw==0:raw=1
            expect.update(rawDamage=raw,resist=255)
            damage=0 if raw>=32768 else raw
            if test['type']==1 and p.get('guarding'):damage//=2
            if test['type']==1 and before['aff'][6] in (3,4):damage//=2
            damage=max(damage,1)
            if p['enemy'] not in IMMUNE:before['hp']=max(0,before['hp']-damage)
            if before['aff'][6]==3:before['attackerHp']=max(0,before['attackerHp']-max(1,damage//2))
            if before['aff'][6] in (3,4):
                before['shield']=(before['shield']-1)&255
                if not before['shield']:before['aff'][6]=0
            if not critical and test['function']!=0xC28740:before['aff'][3]=0
        expect.update(hpAfter=before['hp'],attackerAfter=before['attackerHp'],shieldAfter=before['shield'],affAfter=before['aff'].copy())
        for key,value in expect.items():
            if hit[key]!=value:errors.append(f'{key}: got {hit[key]} expected {value}')
        outcomes.append('miss' if missed else 'smash' if critical else 'dodge' if dodged else 'hit')
    return errors,before,outcomes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ('build','native-source','assets','runtime','scratch','output','project'):parser.add_argument('--'+n,type=Path,required=True)
    parser.add_argument('--original',action='store_true');parser.add_argument('--pilot',action='store_true');parser.add_argument('--diagnostic',action='store_true')
    args=parser.parse_args()
    if args.scratch.exists():raise ValueError('Fresh private scratch required')
    pin=subprocess.check_output(['git','-C',str(args.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=helper.PIN:raise ValueError('Unreviewed Redux revision')
    args.scratch.mkdir(parents=True);session=args.scratch/'session';session.mkdir()
    helper.DRIVER=driver_source(args.original);exe,build=helper.private_build(args)
    _,_,assets=read_pack(args.assets,args.native_source/'src/data/runtime_generated/asset_ids.h')
    actions=assets['data/battle_action_table.bin'];items=assets['data/item_configuration_table.bin'];enemies=assets['data/enemy_configuration_table.bin']
    selected={}
    for i in range(0,len(actions),12):
        f=int.from_bytes(actions[i+8:i+12],'little');kind=actions[i+2]
        if f in FUNCTIONS:selected.setdefault((f,kind),i//12)
    tests=[]
    for (f,kind),action in selected.items():
        for p in profiles(items):
            defense=80*FUNCTIONS[f][1]-1 if p.get('raw_one') else p.get('defense',50)
            for seed in ((1,7) if args.pilot else range(1,65)):
                aff=[p.get('easy',0),0,p.get('temp',0),p.get('strange',0),0,0,p.get('shield',0)]
                v=[len(tests),action,seed*0x9e3779b9&0xffffffff,0 if p['enemy'] is None else p['enemy']+1,
                    0,5000,100,5000,300,*aff,255,255,255,255,255,255,20,0,80,defense,p.get('speed',20),0,p.get('shield_hp',0),p.get('guarding',0),0,
                    p['attacker_enemy']+1 if 'attacker_enemy' in p else 0,0,1,0,0,0,0,0,1,20,20,0,0,0,0,50,0,
                    p.get('weapon',0),p.get('crying',0),p.get('nausea',0),p.get('guts',0),80,20,0,0]
                tests.append({'function':f,'type':kind,'actionId':action,'profile':p,'seed':seed,'values':v})
    path=args.scratch/'cases.tsv';path.write_text('\n'.join(' '.join(map(str,t['values'])) for t in tests)+'\n')
    run=subprocess.run([str(exe.resolve()),str(args.assets.resolve()),str(session.resolve()),str(path.resolve())],cwd=session,
        env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=240)
    logfile=args.scratch/'native.log';logfile.write_bytes(run.stdout+run.stderr);results={}
    for line in run.stdout.decode(errors='replace').splitlines():
        for prefix in ('QA ','QA_DETAIL ','QA_PHYSICAL '):
            if line.startswith(prefix):r=json.loads(line[len(prefix):]);results.setdefault(r['id'],{}).update(r)
    rows=[];outcomes=collections.Counter()
    for i,t in enumerate(tests):
        a=results.get(i,{});errors=[];before={};case_outcomes=[]
        if 'hits' not in a:errors.append('Missing native result')
        else:
            errors,before,case_outcomes=expected_hits(t,a['hits'],items,enemies,args.original)
            for key,value in [('hp',before['hp']),('attackerHp',before['attackerHp']),('shieldhp',before['shield']),('aff',before['aff']),('attackerRestored',1),('targetRestored',1)]:
                if a[key]!=value:errors.append(f'{key}: got{a[key]} expected{value}')
            if a['depth']!=1 or a['steps']>=30000:errors.append('Native continuation did not finish')
        outcomes.update(case_outcomes)
        row={'function':f'{t["function"]:06X}','actionId':t['actionId'],'actionType':t['type'],'profile':t['profile'],
            'seed':t['seed'],'attackOutcomes':case_outcomes,'passed':not errors,'errors':errors}
        if errors:row.update(actual=a,expectedFinal=before)
        rows.append(row)
    pinned=[]
    for p in ('ccscript/main.ccs','ccscript/bugfixes/crying_fix.ccs','ccscript/expansion/Extended_Battle_Action_Table.ccs'):
        file=args.project/p;content=subprocess.check_output(['git','-C',str(args.project.parent),'show',f'{pin}:Project/{p}'])
        if file.read_bytes().replace(b'\r\n',b'\n')!=content.replace(b'\r\n',b'\n'):raise ValueError('Pinned source differs')
        pinned.append({'path':p,'sha256':helper.digest(file),'matchesPinnedSource':True})
    refs=['src/game/battle_actions.c','src/game/battle_calc.c','src/game/battle.h','src/game/inventory.h',
        'asm/battle/actions/bash.asm','asm/battle/actions/shoot.asm','asm/battle/actions/level_1_attack.asm',
        'asm/battle/actions/level_2_attack.asm','asm/battle/actions/level_3_attack.asm','asm/battle/actions/level_4_attack.asm',
        'asm/battle/actions/bash_twice.asm','asm/battle/miss_calc.asm','asm/battle/smaaaash.asm','asm/battle/determine_dodge.asm',
        'asm/battle/calc_damage_reduction.asm','asm/battle/calc_damage.asm','asm/battle/heal_strangeness.asm']
    report={'schemaVersion':1,'toolVersion':'dev16-physical-actions','reduxRevision':pin,'originalPack':args.original,
        'runtimeSha256':{n:helper.digest(args.runtime/n) for n in ('player.exe','observer.exe')},'assetsSha256':helper.digest(args.assets),
        'privateBuild':build,'nativeExitCode':run.returncode,'nativeLogSha256':helper.digest(logfile),
        'cases':rows,'sourceReferences':[{'path':p,'sha256':helper.digest(args.native_source/p)}for p in refs],'pinnedReduxReferences':pinned,
        'sourceReferenceRole':'Review files separately identified from immutable executed library.',
        'semanticCoverage':{'completedCases':len(results),'activeCallbacks':[f'{f:06X}'for f in FUNCTIONS],
            'actionIds':[i for i in selected.values()],'profiles':len(profiles(items)),'attackOutcomes':dict(outcomes)},
        'pilot':args.pilot,'diagnostic':args.diagnostic,
        'allPassed':run.returncode==0 and len(results)==len(tests) and all(r['passed']for r in rows),
        'reproductionFlags':{n:str(getattr(args,n.replace('-','_')))for n in ('build','native-source','assets','runtime','scratch','output','project')},
        'limits':['Source-backed prepared physical callbacks, real miss/smash/dodge/variance/damage/text and double-Bash child sequencing; outer turn/AI selection is not executed.',
            'First packed row of each distinct active physical action type per callback is selected; every description/targeting row variant remains unevaluated.',
            'Actual weapon miss parameters cover every distinct packed weapon-special value, with normalized offense and HP. This does not certify equipment recalculation.',
            'Stage RNG is observed without consumption; complete encounter RNG timing and independent original-machine full-action equivalence remain unevaluated.',
            'Nonlethal target/attacker contexts intentionally exclude KO, Guts saves and final attacks; sleep wake and Giygas2 redirects are covered only in separate PSI report.',
            'Pixels, audio, physical input, full story and randomizer progression remain unevaluated. Only player library executed; observer identity is provenance.',
            'Public cases omit successful full trace arrays; immutable private native log is hashed and repeatable by the included runner. No owner save, ROM or asset payload included.'],
        'fullConversionVerified':False,'fullPlaythroughVerified':False}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cases':len(rows),'completed':len(results),'passed':sum(r['passed']for r in rows),
        'nativeExitCode':run.returncode,'allPassed':report['allPassed'],'attackOutcomes':dict(outcomes),
        'firstFailures':[r for r in rows if not r['passed']][:2]}))
    if not report['allPassed']and not args.diagnostic:raise SystemExit(1)


if __name__=='__main__':main()
