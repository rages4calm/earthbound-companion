# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared real offensive-item callbacks with original-source state assertions.

Links an immutable production library. No production source, owner save or asset
pack writes. Observed effect-stage RNG is restored without consuming a byte.
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

FUNCTIONS = {
    0xC2900B: ('fire350', 'fire', 350),
    0xC2A50E: ('mummy', 'strap', 400),
    0xC2A5D1: ('rocket', 'rocket', 1),
    0xC2A5DA: ('bigRocket', 'rocket', 5),
    0xC2A5E3: ('multiRocket', 'rocket', 20),
    0xC2A5EC: ('handbag', 'strap', 100),
    0xC2A86B: ('yogurt', 'small', 250),
    0xC2A89D: ('snake', 'snake', 250),
    0xC2A99C: ('dragonite', 'fire', 800),
    0xC2AA0C: ('insect', 'spray', 100),
    0xC2AA15: ('xterminator', 'spray', 200),
    0xC2AA6D: ('rust', 'spray', 200),
    0xC2AA76: ('rustDX', 'spray', 400),
}
IMMUNE = (93, 192, 219, 221, 229)


def driver_source(original):
    source = previous.driver_source()
    marker='static unsigned qa_function,qa_var_count,qa_var_rolls[32],qa_damage[16];'
    source = source.replace(marker, marker+r'''
static unsigned item_entry_count,item_entry_rolls[32],item_raw_count,item_raw[8],item_resist[8],
    item_target[8],item_poison_count,item_poison_roll;
static const unsigned item_entry1_functions[]={0xC2A50E,0xC2A5EC,0xC2A89D};
static unsigned item_entry_pc(void) {
    for(unsigned i=0;i<3;i++)if(qa_function==item_entry1_functions[i])return 1;
    return 0;
}
''')
    source=source.replace('unsigned v[48],n=0;', 'unsigned v[49],n=0;').replace('n<48','n<49').replace('if(n!=48)','if(n!=49)')
    source=source.replace('qa_var_count=0;', '''qa_var_count=0;
        item_entry_count=item_raw_count=item_poison_count=item_poison_roll=0;
        memset(item_entry_rolls,0,sizeof(item_entry_rolls));
        a->hp=a->hp_target=a->hp_max=5000;a->speed=(uint16_t)v[48];
        if(a->ally_or_enemy==0) {
            CharStruct *ca=&party_characters[a->id-1];
            ca->max_hp=ca->current_hp=ca->current_hp_target=5000;
        }
        ''')
    source=source.replace('StepResult r=mode_dispatch_step', '''
        if(g_mode_stack.mode[top]==GAME_MODE_BATTLE_ACTION && pc==item_entry_pc()) {
            item_entry_count++;
            RNGState before=rng_state;
            for(unsigned i=0;i<32;i++)item_entry_rolls[i]=rng_next_byte();
            rng_state=before;
        }
        if(g_mode_stack.mode[top]==GAME_MODE_BATTLE_ACTION && qa_function==0xC2A89D && pc==2) {
            RNGState before=rng_state;item_poison_roll=rng_next_byte();rng_state=before;item_poison_count++;
        }
        StepResult r=mode_dispatch_step''')
    source=source.replace('if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);', '''
        if(r.kind==STEP_PUSH && r.push_mode==GAME_MODE_BATTLE_CALC &&
            r.push_init->battle_calc.kind==BC_RESIST_DAMAGE) {
            if(item_raw_count>=8)return 28;
            item_raw[item_raw_count]=r.push_init->battle_calc.arg0;
            item_resist[item_raw_count]=r.push_init->battle_calc.arg1;
            item_target[item_raw_count++]=bt.current_target/sizeof(Battler);
        }
        if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);''')
    source=source.replace('        fflush(stdout);',r'''
        printf("QA_ITEMS {\"id\":%u,\"entryCount\":%u,\"entryRolls\":[",v[0],item_entry_count);
        for(unsigned i=0;i<32;i++)printf("%s%u",i?",":"",item_entry_rolls[i]);
        printf("],\"rawDamage\":[");for(unsigned i=0;i<item_raw_count;i++)printf("%s%u",i?",":"",item_raw[i]);
        printf("],\"resist\":[");for(unsigned i=0;i<item_raw_count;i++)printf("%s%u",i?",":"",item_resist[i]);
        printf("],\"resistTarget\":[");for(unsigned i=0;i<item_raw_count;i++)printf("%s%u",i?",":"",item_target[i]);
        printf("],\"poisonCount\":%u,\"poisonRoll\":%u}\n",item_poison_count,item_poison_roll);
        fflush(stdout);''')
    if original:
        source=source.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"').replace(' || !maternalbound_enabled()', ' || maternalbound_enabled()')
    return source


def profiles(function,enemies):
    name,kind,power=FUNCTIONS[function]
    base=[dict(name='normal-enemy',enemy=7),dict(name='normal-player',enemy=None),
        dict(name='fast-player',enemy=None,speed=150),dict(name='npc-target',enemy=7,npc=6),
        dict(name='speed0',enemy=7,speed=0),dict(name='speed50',enemy=7,speed=50),
        dict(name='speed200',enemy=7,speed=200),dict(name='speed32768-wrap',enemy=7,speed=32768),
        dict(name='speed65535',enemy=7,speed=65535),dict(name='attacker-speed300',enemy=7,attack_speed=300),
        dict(name='luck0',enemy=7,luck=0),dict(name='luck79',enemy=7,luck=79),
        dict(name='luck80',enemy=7,luck=80),dict(name='unconscious-enemy',enemy=7,easy=1),
        dict(name='inactive-enemy',enemy=7,conscious=0),dict(name='solidified-enemy',enemy=7,temp=4),
        dict(name='immobilized-enemy',enemy=7,temp=3),dict(name='poisoned-enemy',enemy=7,easy=5),
        dict(name='nausea-enemy',enemy=7,easy=4),dict(name='cold-enemy',enemy=7,easy=7),dict(name='guarding',enemy=7,guarding=1)]
    for shield,hp in ((1,3),(2,3),(3,1),(3,3),(4,1),(4,3)):
        base.append(dict(name=f'shield-{shield}-hp-{hp}',enemy=7,shield=shield,shield_hp=hp))
    base.extend(dict(name=f'immune-boss-{e}',enemy=e) for e in IMMUNE)
    base.append(dict(name='giygas4-damageable',enemy=220))
    if kind=='fire':
        base.extend(dict(name=f'fire-resistance-{r}',enemy=7,resist=r) for r in (0,64,128,192))
    elif kind=='strap':
        base.extend(dict(name=f'defense-{d}',enemy=7,defense=d) for d in (0,power-1,power,power+1,65535))
    elif kind=='spray':
        desired=1 if function in (0xC2AA0C,0xC2AA15) else 2
        # All actual eligible species, normalized HP/luck/speed; ID/type stays
        # untouched. This is not a whole encounter or AI audit.
        base.extend(dict(name=f'actual-species-{e}-type-{desired}',enemy=e,luck=0)
            for e in range(len(enemies)//94) if enemies[e*94+27]==desired and e!=218)
    return base


def expected(test,actual):
    f=test['function'];_,kind,power=FUNCTIONS[f];p=test['profile'];v=test['values'];rolls=actual['entryRolls']
    aff=v[9:16].copy();hp=v[5];attacker=5000;shield_hp=v[28]
    wanted={'entryCount':1,'rawDamage':[],'resist':[],'resistTarget':[],
        'hp':hp,'attackerHp':attacker,'aff':aff,'shieldhp':shield_hp,
        'attackerRestored':1,'targetRestored':1,'poisonCount':0}
    doubled=(p.get('speed',20)*2)&65535;speed=p.get('attack_speed',20)
    threshold=0 if doubled<speed else doubled-speed
    raw=None;resist=255;hits=None;outcome='no-effect'
    if kind=='fire':raw=helper.variance_reference(power,rolls[:2],1);resist=p.get('resist',255)
    elif kind=='rocket':
        hits=sum(r*100//256>=threshold for r in rolls[:power])
        if hits:raw=helper.variance_reference(hits*120,rolls[power:power+2],1)
    elif kind=='spray':
        desired=1 if f in (0xC2AA0C,0xC2AA15) else 2
        if rolls[0]*80//256>=p.get('luck',20) and p['enemy'] is not None and test['enemyType']==desired:
            raw=helper.variance_reference(power,rolls[1:3],0)
    elif not p.get('npc') and rolls[0]*250//256>=threshold:
        if kind=='strap':
            value=(power-p.get('defense',50))&65535
            if 0<value<32768:raw=value
        else:raw=rolls[1]*4//256+1
    # Yogurt has no FAIL_ON_NPCS, unlike snake and strap.
    if kind=='small' and p.get('npc') and rolls[0]*250//256>=threshold:
        raw=rolls[1]*4//256+1
    if raw is not None:
        wanted.update(rawDamage=[raw],resist=[resist],resistTarget=[8 if p['enemy'] is not None else 0])
        outcome='damage'
        if p.get('conscious',1)==1 and aff[0]!=1:
            damage=raw if raw<32768 else 0
            if resist<255:damage=damage*resist//256
            if test['type']==1 and p.get('guarding'):damage//=2
            if test['type']==1 and aff[6] in (3,4):damage//=2
            damage=max(damage,1)
            if p['enemy'] not in IMMUNE:wanted['hp']=hp-damage
            if aff[6]==3:wanted['attackerHp']=attacker-max(1,damage//2)
            if aff[6] in (3,4):
                wanted['shieldhp']=(shield_hp-1)&255
                if not wanted['shieldhp']:aff[6]=0
        if kind=='strap' and not p.get('npc') and (not aff[2] or aff[2]>4):aff[2]=4
        if kind=='snake':
            wanted['poisonCount']=1
            if actual['poisonRoll']<128 and not p.get('npc') and (not aff[0] or aff[0]>5):aff[0]=5
    return wanted,outcome,hits


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ('build','native-source','assets','runtime','scratch','output','project'):parser.add_argument('--'+n,type=Path,required=True)
    parser.add_argument('--original',action='store_true');parser.add_argument('--pilot',action='store_true')
    parser.add_argument('--diagnostic',action='store_true');args=parser.parse_args()
    if args.scratch.exists():raise ValueError('Fresh private scratch required')
    pin=subprocess.check_output(['git','-C',str(args.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=helper.PIN:raise ValueError('Unreviewed Redux revision')
    args.scratch.mkdir(parents=True);session=args.scratch/'session';session.mkdir()
    helper.DRIVER=driver_source(args.original);exe,build=helper.private_build(args)
    _,_,assets=read_pack(args.assets,args.native_source/'src/data/runtime_generated/asset_ids.h')
    table=assets['data/battle_action_table.bin'];enemies=assets['data/enemy_configuration_table.bin'];selected={}
    for i in range(len(table)//12):
        f=int.from_bytes(table[i*12+8:i*12+12],'little');kind=table[i*12+2]
        if f in FUNCTIONS:selected.setdefault((f,kind),i)
    if {f for f,k in selected}!=set(FUNCTIONS):raise ValueError('Catalog differs')
    tests=[]
    for (f,kind),action in selected.items():
        for p in profiles(f,enemies):
            for seed in ((1,7) if args.pilot else range(1,65)):
                aff=[p.get('easy',0),0,p.get('temp',0),0,0,0,p.get('shield',0)]
                v=[len(tests),action,seed*0x9e3779b9&0xffffffff,0 if p['enemy'] is None else p['enemy']+1,
                    0,5000,100,5000,300,*aff,p.get('resist',255),255,255,255,255,255,p.get('luck',20),p.get('npc',0),
                    80,p.get('defense',50),p.get('speed',20),0,p.get('shield_hp',0),p.get('guarding',0),0,0,
                    0,p.get('conscious',1),0,0,0,0,0,1,20,20,0,0,0,0,50,0,p.get('attack_speed',20)]
                tests.append(dict(function=f,type=kind,action=action,profile=p,seed=seed,values=v,
                    enemyType=enemies[p['enemy']*94+27] if p['enemy'] is not None else None))
    path=args.scratch/'cases.tsv';path.write_text('\n'.join(' '.join(map(str,t['values']))for t in tests)+'\n')
    run=subprocess.run([str(exe.resolve()),str(args.assets.resolve()),str(session.resolve()),str(path.resolve())],cwd=session,
        env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=300)
    logfile=args.scratch/'native.log';logfile.write_bytes(run.stdout+run.stderr);results={}
    for line in run.stdout.decode(errors='replace').splitlines():
        for prefix in ('QA ','QA_DETAIL ','QA_ITEMS '):
            if line.startswith(prefix):r=json.loads(line[len(prefix):]);results.setdefault(r['id'],{}).update(r)
    rows=[];outcomes=collections.Counter();rocket_hits=collections.Counter()
    for i,t in enumerate(tests):
        a=results.get(i,{});errors=[];wanted={};outcome='missing';hits=None
        if 'entryRolls' not in a:errors.append('Missing native result')
        else:
            wanted,outcome,hits=expected(t,a)
            for k,value in wanted.items():
                if a[k]!=value:errors.append(f'{k}: got{a[k]} expected{value}')
            if a['depth']!=1 or a['steps']>=30000:errors.append('Native continuation did not finish')
        outcomes[outcome]+=1
        if hits is not None:rocket_hits[hits]+=1
        row={'function':f'{t["function"]:06X}','actionId':t['action'],'actionType':t['type'],
            'profile':t['profile'],'enemyType':t['enemyType'],'seed':t['seed'],'outcome':outcome,
            'rocketHits':hits,'passed':not errors,'errors':errors}
        if errors:row.update(actual=a,expected=wanted)
        rows.append(row)
    pinned=[]
    for p in ('ccscript/main.ccs','ccscript/expansion/Extended_Battle_Action_Table.ccs'):
        file=args.project/p;content=subprocess.check_output(['git','-C',str(args.project.parent),'show',f'{pin}:Project/{p}'])
        if file.read_bytes().replace(b'\r\n',b'\n')!=content.replace(b'\r\n',b'\n'):raise ValueError('Pinned source differs')
        pinned.append({'path':p,'sha256':helper.digest(file),'matchesPinnedSource':True})
    refs=['src/game/battle_actions.c','src/game/battle_calc.c','src/game/battle.c','src/game/battle.h',
        'asm/battle/actions/350_fire_damage.asm','asm/battle/actions/bottle_rocket_common.asm',
        'asm/battle/actions/insect_spray_common.asm','asm/battle/actions/rust_promoter_common.asm',
        'asm/battle/actions/handbag_strap.asm','asm/battle/actions/mummy_wrap.asm','asm/battle/actions/snake.asm',
        'asm/battle/actions/yogurt_dispenser.asm','asm/battle/actions/bag_of_dragonite.asm',
        'asm/battle/success_speed.asm','asm/battle/success_luck80.asm','asm/battle/calc_damage_reduction.asm',
        'asm/battle/calc_damage.asm','asm/battle/inflict_status.asm']
    report={'schemaVersion':1,'toolVersion':'dev16-offensive-items','reduxRevision':pin,'originalPack':args.original,
        'runtimeSha256':{n:helper.digest(args.runtime/n)for n in ('player.exe','observer.exe')},'assetsSha256':helper.digest(args.assets),
        'privateBuild':build,'nativeExitCode':run.returncode,'nativeLogSha256':helper.digest(logfile),
        'cases':rows,'sourceReferences':[{'path':p,'sha256':helper.digest(args.native_source/p)}for p in refs],'pinnedReduxReferences':pinned,
        'sourceReferenceRole':'Source review identities are separate from immutable executed library; no production code changed by this runner.',
        'semanticCoverage':{'completedCases':len(results),'activeCallbacks':[f'{f:06X}'for f in FUNCTIONS],
            'actionIds':list(selected.values()),'outcomes':dict(outcomes),'rocketHits':dict(rocket_hits)},
        'pilot':args.pilot,'diagnostic':args.diagnostic,
        'allPassed':run.returncode==0 and len(results)==len(tests) and all(r['passed']for r in rows),
        'reproductionFlags':{n:str(getattr(args,n.replace('-','_')))for n in ('build','native-source','assets','runtime','scratch','output','project')},
        'limits':['Thirteen prepared complete offensive callbacks with actual calculation/text children, exact source hit/damage/resistance/status/guard/shield and selected immunity branches; outer descriptions, item consumption, targeting traversal and whole turns unevaluated.',
            'One actual action row per distinct callback/type is selected; other row descriptions and targeting variants are not certified.',
            'All packed insect/metal species are tested with normalized high HP and luck0. Natural species stats and whole encounters remain unevaluated.',
            'Nonlethal HP5000 isolates damage and status. KO, Guts saves, final attacks, asleep wake and Giygas2 redirects remain outside this runner.',
            'Observed effect-stage RNG is read/restored without consumption; source formulas provide expectations, not independent complete original-machine execution or a full encounter RNG timeline.',
            'Prepared NPC targets isolate refusal/type branches and do not construct every temporary party role.',
            'Only player production library executes; observer hash is provenance. No pixel/audio/input/full story/randomizer or full-conversion claim.',
            'No owner save, ROM or extracted payload is published; successful native traces stay in a hashed private log.'],
        'fullConversionVerified':False,'fullPlaythroughVerified':False}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cases':len(rows),'completed':len(results),'passed':sum(r['passed']for r in rows),
        'nativeExitCode':run.returncode,'allPassed':report['allPassed'],'outcomes':dict(outcomes),
        'rocketHits':dict(rocket_hits),'firstFailures':[r for r in rows if not r['passed']][:2]}))
    if not report['allPassed']and not args.diagnostic:raise SystemExit(1)


if __name__=='__main__':main()
