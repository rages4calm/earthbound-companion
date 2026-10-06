# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared real Rockin/Starstorm callbacks with source-backed damage checks.

Separate from the release-frozen dev15 tools. Uses the immutable private
production library; no owner checkpoint, ROM, source or shared build writes.
"""
import argparse
import collections
import json
import os
from pathlib import Path
import subprocess

import battle_action_catalog_qa as helper
import battle_action_catalog_qa_dev15 as prior
from build_maternalbound_pack import read_pack


FUNCTIONS = {
    0xC29556: ('Rockin alpha', 80, 0),
    0xC2955F: ('Rockin beta', 180, 0),
    0xC29568: ('Rockin gamma', 320, 0),
    0xC29571: ('Rockin omega', 640, 0),
    0xC29AA6: ('Starstorm alpha', 360, 1),
    0xC29AAF: ('Starstorm omega', 720, 1),
}
IMMUNE = (93, 192, 219, 221, 229)


def driver_source(original=False):
    source = prior.driver_source()
    source = source.replace('static unsigned qa_function,',
        'static unsigned damage_entry_rolls[8],damage_entry_count,damage_count,damage_raw[8],damage_resist[8],damage_target[8],sleep_captured,sleep_roll;\nstatic unsigned qa_function,')
    source = source.replace('StepResult r=mode_dispatch_step', '''
        if(g_mode_stack.mode[top]==GAME_MODE_BATTLE_ACTION && pc==1 && mode_child_result()==0 &&
            ((qa_function>=0xC29556 && qa_function<=0xC29571) || qa_function==0xC29AA6 || qa_function==0xC29AAF)) {
            RNGState before=rng_state;
            for(unsigned ri=0;ri<8;ri++)damage_entry_rolls[ri]=rng_next_byte();
            rng_state=before;damage_entry_count++;
        }
        if(g_mode_stack.mode[top]==GAME_MODE_BATTLE_CALC &&
            g_mode_stack.state[top].battle_calc.kind==BC_RESIST_DAMAGE &&
            g_mode_stack.state[top].battle_calc.pc==1 &&
            battler_from_offset(bt.current_target)->afflictions[STATUS_GROUP_TEMPORARY]==STATUS_2_ASLEEP) {
            RNGState before=rng_state;sleep_roll=rng_next_byte();rng_state=before;sleep_captured++;
        }
        StepResult r=mode_dispatch_step''')
    source = source.replace('if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);', '''
        if(r.kind==STEP_PUSH && r.push_mode==GAME_MODE_BATTLE_CALC &&
            r.push_init->battle_calc.kind==BC_RESIST_DAMAGE && damage_count<8) {
            damage_raw[damage_count]=r.push_init->battle_calc.arg0;
            damage_resist[damage_count]=r.push_init->battle_calc.arg1;
            damage_target[damage_count]=bt.current_target/sizeof(Battler);
            damage_count++;
        }
        if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);''')
    source = source.replace('qa_var_count=0;', '''qa_var_count=0;damage_count=damage_entry_count=sleep_captured=sleep_roll=0;
        memset(damage_entry_rolls,0,sizeof(damage_entry_rolls));
        a->hp=a->hp_target=a->hp_max=5000;
        if(a->ally_or_enemy==0) {
            CharStruct *ca=&party_characters[a->id-1];
            ca->max_hp=ca->current_hp=ca->current_hp_target=5000;
        }''')
    source = source.replace('        fflush(stdout);', r'''
        printf("QA_DAMAGE {\"id\":%u,\"entryCount\":%u,\"entryRolls\":[",v[0],damage_entry_count);
        for(unsigned ri=0;ri<8;ri++)printf("%s%u",ri?",":"",damage_entry_rolls[ri]);
        printf("],\"rawDamage\":[");
        for(unsigned ri=0;ri<damage_count;ri++)printf("%s%u",ri?",":"",damage_raw[ri]);
        printf("],\"resist\":[");
        for(unsigned ri=0;ri<damage_count;ri++)printf("%s%u",ri?",":"",damage_resist[ri]);
        printf("],\"resistTarget\":[");
        for(unsigned ri=0;ri<damage_count;ri++)printf("%s%u",ri?",":"",damage_target[ri]);
        printf("],\"partyHp\":[%u,%u,%u,%u],\"reflected\":%u,\"shieldNullified\":%u,\"sleepCaptured\":%u,\"sleepRoll\":%u}\n",
            bt.battlers_table[0].hp_target,bt.battlers_table[1].hp_target,
            bt.battlers_table[2].hp_target,bt.battlers_table[3].hp_target,
            bt.damage_is_reflected,bt.shield_has_nullified_damage,sleep_captured,sleep_roll);
        fflush(stdout);''')
    if original:
        source=source.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"')
        source=source.replace(' || !maternalbound_enabled()', ' || maternalbound_enabled()')
    return source


def profiles():
    rows=[]
    for enemy,speed in ((7,20),(64,200),(169,0),(220,20)):
        rows.append(dict(name=f'enemy-{enemy}-speed-{speed}',enemy=enemy,speed=speed))
    rows.extend(dict(name=f'immune-boss-{enemy}',enemy=enemy,speed=20) for enemy in IMMUNE)
    rows.append(dict(name='giygas2-redirect',enemy=218,speed=20))
    for enemy in (7,None):
        prefix='enemy' if enemy is not None else 'player'
        for shield,shield_hp in ((1,1),(1,3),(2,1),(2,3),(3,3),(4,3)):
            rows.append(dict(name=f'{prefix}-shield-{shield}-hp-{shield_hp}',enemy=enemy,
                speed=20,shield=shield,shield_hp=shield_hp))
    rows.extend(dict(name=f'player-disabled-{name}',enemy=None,speed=200,
        easy=easy,temp=temp) for name,easy,temp in (
            ('paralyzed',3,0),('immobilized',0,3),('solidified',0,4),('asleep',0,1)))
    rows.append(dict(name='player-guarding-fast',enemy=None,speed=200,guarding=1))
    rows.append(dict(name='player-negative-dodge-speed',enemy=None,speed=0))
    return rows


def wanted(test,actual):
    p=test['profile'];v=test['values'];_,power,shift=FUNCTIONS[test['function']]
    shield=p.get('shield',0);aff=v[9:16].copy();hp=v[5];attacker_hp=5000
    party_hp=[5000,5000,999,999] if p['enemy'] is None else [999,5000,999,999]
    # Prepared PC target starts at5000; fixture PC attacker at5000.
    if p['enemy'] is None:party_hp[0]=hp
    expected={'hp':hp,'attackerHp':attacker_hp,'aff':aff,'shieldhp':v[28],
        'rawDamage':[],'resist':[],'resistTarget':[],'partyHp':party_hp,
        'attackerRestored':1,'targetRestored':1,'reflected':0,'sleepCaptured':0}
    if shield==2:
        expected['shieldhp']=(v[28]-1)&255
        if not expected['shieldhp']:expected['aff'][6]=0
        # Absorb exits before the shared WEAKEN_SHIELD epilogue.
        expected['entryCount']=0;expected['shieldNullified']=1
        return expected
    expected['entryCount']=1;expected['shieldNullified']=0
    rolls=actual['entryRolls'];damage=helper.variance_reference(power,rolls[:2],shift)
    reflected=shield==1
    effective_speed=20 if reflected else p['speed']
    attack_speed=p['speed'] if reflected else 20
    easy=0 if reflected else p.get('easy',0)
    temp=0 if reflected else p.get('temp',0)
    chance=effective_speed*2-attack_speed
    can_dodge=not (easy==3 or temp in (1,3,4)) and chance>=0
    dodged=not shift and can_dodge and rolls[2]*500//256<chance
    if reflected:
        expected['shieldhp']=(v[28]-1)&255
        if not expected['shieldhp']:expected['aff'][6]=0
    if dodged:return expected
    expected.update(rawDamage=[damage],resist=[255],resistTarget=[1 if reflected else 8 if p['enemy'] is not None else 0])
    if reflected:
        expected['attackerHp']=max(0,5000-damage)
        expected['partyHp'][1]=expected['attackerHp']
    elif p['enemy']==218:
        index=2+int(not shift and can_dodge)
        target=rolls[index]&3
        expected['partyHp'][target]=max(0,expected['partyHp'][target]-damage)
        if target==1:expected['attackerHp']=expected['partyHp'][1]
    elif p['enemy'] not in IMMUNE:
        expected['hp']=max(0,hp-damage)
        if p['enemy'] is None:expected['partyHp'][0]=expected['hp']
    if temp==1:
        # DISPLAY_IN_BATTLE_TEXT advances RAND before the later wake check.
        # In these nonlethal PSI cases pc1 falls through pc8 to pc6 without
        # another child or RNG call. Read at that actual calc continuation,
        # rather than assume
        # damage-entry RNG indices still apply after native text children.
        expected['sleepCaptured']=1
        if actual['sleepRoll']<128:expected['aff'][2]=0
    return expected


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('build','native-source','assets','runtime','scratch','output','project'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--original',action='store_true')
    parser.add_argument('--pilot',action='store_true')
    parser.add_argument('--diagnostic',action='store_true')
    args=parser.parse_args()
    if args.scratch.exists():raise ValueError('Fresh private scratch required')
    pin=subprocess.check_output(['git','-C',str(args.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=helper.PIN:raise ValueError('Unreviewed Redux revision')
    args.scratch.mkdir(parents=True);session=args.scratch/'session';session.mkdir()
    helper.DRIVER=driver_source(args.original);exe,build=helper.private_build(args)
    _,_,assets=read_pack(args.assets,args.native_source/'src/data/runtime_generated/asset_ids.h')
    action_data=assets['data/battle_action_table.bin']
    by_function={int.from_bytes(action_data[i+8:i+12],'little'):i//12 for i in range(0,len(action_data),12)}
    tests=[]
    for function in FUNCTIONS:
        for profile in profiles():
            for seed in (range(1,65) if not args.pilot else (1,7)):
                enemy=profile['enemy'];aff=[profile.get('easy',0),0,profile.get('temp',0),0,0,0,profile.get('shield',0)]
                v=[len(tests),by_function[function],seed*0x9e3779b9&0xffffffff,
                    0 if enemy is None else enemy+1,0,5000,100,5000,300,
                    *aff,255,255,255,255,255,255,20,0,80,50,
                    profile['speed'],0,profile.get('shield_hp',0),profile.get('guarding',0),0,0,
                    0,1,0,0,0,0,0,1,20,20,0,0,0,0,50,0]
                tests.append({'function':function,'profile':profile,'seed':seed,'values':v})
    path=args.scratch/'cases.tsv';path.write_text('\n'.join(' '.join(map(str,t['values'])) for t in tests)+'\n')
    run=subprocess.run([str(exe.resolve()),str(args.assets.resolve()),str(session.resolve()),str(path.resolve())],
        cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=240)
    (args.scratch/'native.log').write_bytes(run.stdout+run.stderr)
    results={}
    for line in run.stdout.decode(errors='replace').splitlines():
        for prefix in ('QA ','QA_DETAIL ','QA_DAMAGE '):
            if line.startswith(prefix):
                row=json.loads(line[len(prefix):]);results.setdefault(row['id'],{}).update(row)
    rows=[]
    for i,test in enumerate(tests):
        a=results.get(i,{});errors=[];expected={}
        if 'entryRolls' not in a:errors.append('Missing native result')
        else:
            expected=wanted(test,a)
            for key,value in expected.items():
                if a[key]!=value:errors.append(f'{key}: got {a[key]} expected {value}')
            if a['depth']!=1 or a['steps']>=30000:errors.append('Native continuation did not finish')
        rows.append({'function':f'{test["function"]:06X}','profile':test['profile'],
            'seed':test['seed'],'expected':expected,'actual':{k:a.get(k) for k in expected},
            'entryRolls':a.get('entryRolls'),'sleepRoll':a.get('sleepRoll'),'passed':not errors,'errors':errors})
    refs=['src/game/battle_actions.c','src/game/battle_calc.c','src/game/battle_internal.h',
        'asm/battle/actions/psi_rockin_common.asm','asm/battle/actions/psi_starstorm_common.asm',
        'asm/battle/determine_dodge.asm','asm/battle/success_500.asm',
        'asm/battle/psi_shield_nullify.asm','asm/battle/weaken_shield.asm',
        'asm/battle/calc_damage_reduction.asm','asm/battle/calc_damage.asm',
        'asm/battle/reduce_hp.asm','asm/system/math/rand_limit.asm','asm/text/display_in_battle_text.asm','src/game/display_text.c','include/config.asm',
        'include/constants/battle.asm','include/constants/enemies.asm']
    report={'schemaVersion':1,'toolVersion':'dev16-rockin-starstorm','reduxRevision':pin,
        'originalPack':args.original,'runtimeSha256':{n:helper.digest(args.runtime/n) for n in ('player.exe','observer.exe')},
        'assetsSha256':helper.digest(args.assets),'privateBuild':build,'nativeExitCode':run.returncode,
        'cases':rows,'sourceReferences':[{'path':p,'sha256':helper.digest(args.native_source/p)} for p in refs],
        'sourceReferenceRole':'Current source review files; separately hashed immutable library identifies executed code.',
        'reproductionFlags':{name:str(getattr(args,name.replace('-','_'))) for name in ('build','native-source','assets','runtime','scratch','output','project')},
        'semanticCoverage':{'completedCases':len(results),'activeCallbacks':[f'{f:06X}' for f in FUNCTIONS],
            'passedCases':sum(r['passed'] for r in rows),'profiles':len(profiles())},
        'pilot':args.pilot,'diagnostic':args.diagnostic,
        'allPassed':run.returncode==0 and len(results)==len(tests) and all(r['passed'] for r in rows),
        'limits':['Prepared single-target real callbacks and resumable calculation/text children; no outer action target traversal, whole turn or enemy AI selection.',
            'Expected state follows reviewed original assembly and exact packed action types; no independent full original-machine oracle in this tool.',
            'RNG values are observed without consumption at actual effect entry. Complete encounter RNG timing and serialization are outside scope.',
            'High target/attacker HP isolates non-lethal damage, dodge and shield/boss branches; KO and guts-save are intentionally unevaluated.',
            'Physical input, rendered pixels, audio, PSI animation timing and the full story remain unevaluated.',
            'Only player library executed. Observer hash records provenance. No owner save, ROM or asset payload included.'],
        'fullConversionVerified':False,'fullPlaythroughVerified':False}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cases':len(rows),'completed':len(results),'passed':sum(r['passed'] for r in rows),
        'nativeExitCode':run.returncode,'allPassed':report['allPassed'],'firstFailures':[r for r in rows if not r['passed']][:3]}))
    if not report['allPassed'] and not args.diagnostic:raise SystemExit(1)


if __name__=='__main__':main()
