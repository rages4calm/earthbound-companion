# SPDX-License-Identifier: GPL-3.0-or-later
"""Isolated actual native food, condiment and Lucky Sandwich execution.

Direct callback cases and bounded production description/target/consumption
continuations are distinguished explicitly. Only private files are written.
"""
import argparse
import collections
import json
import os
from pathlib import Path
import struct
import subprocess

import battle_action_catalog_qa as helper
import battle_action_catalog_qa_dev15 as previous
from build_maternalbound_pack import read_pack


def driver_source():
    src=previous.driver_source()
    src=src.replace('static unsigned qa_function,qa_var_count,qa_var_rolls[32],qa_damage[16];',
        'static unsigned qa_function,qa_var_count,qa_var_rolls[32],qa_damage[16];\nstatic unsigned qa_food_index,qa_food_initial[8],qa_food_effect[8],qa_food_second[8],qa_food_route;')
    src=src.replace('unsigned pc=g_mode_stack.state[top].battle_action.pc;',r'''
        if(qa_food_route && g_mode_stack.depth==2 && g_mode_stack.mode[top]==GAME_MODE_BATTLE &&
           g_mode_stack.state[top].battle.phase==BTL_AFTER_STATUS_BODY) {
            /* Actual description, targeting loop, callback, item consumption
             * and post-action dead-player check have completed. Stop before
             * unrelated later actor/status/turn processing. */
            mode_pop(0);return steps;
        }
        unsigned pc=g_mode_stack.state[top].battle_action.pc;
        if(g_mode_stack.mode[top]==GAME_MODE_BATTLE_ACTION &&
           g_mode_stack.state[top].battle_action.table_index==qa_food_index) {
            unsigned *dest=pc==0?qa_food_initial:pc==1?qa_food_effect:pc==2?qa_food_second:NULL;
            if(dest) {
                RNGState saved=rng_state;for(unsigned i=0;i<8;i++)dest[i]=rng_next_byte();rng_state=saved;
                if(pc==0)memcpy(qa_food_effect,qa_food_initial,sizeof(qa_food_effect));
            }
        }''')
    src=src.replace('unsigned original_attacker=bt.current_attacker,original_target=bt.current_target;',r'''
        memset(party_characters[a->id-1].items,0,14);
        party_characters[a->id-1].items[0]=(uint8_t)v[30];
        party_characters[a->id-1].items[1]=(uint8_t)v[34];
        party_characters[a->id-1].items[2]=(uint8_t)v[35];
        party_characters[a->id-1].items[13]=(uint8_t)v[37];
        CharStruct *food_char=&party_characters[t->id-1];
        food_char->boosted_iq=food_char->boosted_guts=food_char->boosted_speed=
            food_char->boosted_vitality=food_char->boosted_luck=(uint8_t)v[45];
        game_state.party_status=0;
        OverworldDeferredSaveState clear_tasks={0};clear_tasks.demo_read_index=0xffff;
        overworld_deferred_savestate_unpack(&clear_tasks);
        ow.redux_primary_timer=71;ow.redux_secondary_timer=99;
        unsigned original_attacker=bt.current_attacker,original_target=bt.current_target;''')
    src=src.replace('qa_function=callback;\n            if(battle_action_dispatch(callback,&action)) {',r'''
            qa_function=callback;qa_food_route=v[36];
            if(battle_action_dispatch(callback,&action)) {
                qa_food_index=action.battle_action.table_index;
                memcpy(qa_food_initial,rolls,sizeof(rolls));memcpy(qa_food_effect,rolls,sizeof(rolls));
                memset(qa_food_second,0,sizeof(qa_food_second));
                if(qa_food_route) {
                    fix_attacker_name(0);set_current_item_far(a->current_action_argument);fix_target_name();
                    bt.battler_target_flags=1u<<ti;
                    ModeState battle={0};battle.battle.phase=BTL_EXEC_DESC;
                    battle.battle.attacker=(uint16_t)(bt.current_attacker/sizeof(Battler));
                    mode_push(GAME_MODE_BATTLE,&battle);steps=pump();
                } else {''')
    src=src.replace('mode_push(GAME_MODE_BATTLE_ACTION,&action);steps=pump();',
        'mode_push(GAME_MODE_BATTLE_ACTION,&action);steps=pump();\n                }')
    src=src.replace('        fflush(stdout);',r'''
        OverworldDeferredSaveState tasks={0};overworld_deferred_savestate_pack(&tasks);
        unsigned task_frames=0,task_id=0;
        for(unsigned i=0;i<MAX_OVERWORLD_TASKS;i++)if(tasks.task_frames_left[i]) {
            task_frames=tasks.task_frames_left[i];task_id=tasks.task_callback_id[i];break;
        }
        printf("QA_FOOD {\"id\":%u,\"items\":[",v[0]);
        for(unsigned i=0;i<14;i++)printf("%s%u",i?",":"",party_characters[a->id-1].items[i]);
        printf("],\"boosted\":[%u,%u,%u,%u,%u],\"partyStatus\":%u,\"animationVar\":%u,\"taskFrames\":%u,\"taskId\":%u,\"stamina\":[%u,%u],\"initialRolls\":[",
            food_char->boosted_iq,food_char->boosted_guts,food_char->boosted_speed,food_char->boosted_vitality,food_char->boosted_luck,
            game_state.party_status,entities.var[3][ENT(24)],task_frames,task_id,
            ow.redux_primary_timer,ow.redux_secondary_timer);
        for(unsigned i=0;i<8;i++)printf("%s%u",i?",":"",qa_food_initial[i]);
        printf("],\"effectRolls\":[");for(unsigned i=0;i<8;i++)printf("%s%u",i?",":"",qa_food_effect[i]);
        printf("],\"secondRolls\":[");for(unsigned i=0;i<8;i++)printf("%s%u",i?",":"",qa_food_second[i]);
        printf("]}\n");
        fflush(stdout);''')
    return src


def expected(test,actual,items,condiments):
    v=test['values'];food=v[30];r=items[food*39:(food+1)*39];params=list(r[31:35]);inventory=[food,v[34],v[35]]+[0]*10+[v[37]]
    wanted={'hp':v[5],'pp':v[6],'aff':v[9:16],'items':inventory,'boosted':[v[45]]*5,
        'targetIq':v[40],'targetVitality':v[41],'guts':v[27],'speed':v[26],'luck':v[22]}
    blocked=v[9]==1
    outcome=None
    if test['function']==0xC2FFF0:
        rolls=actual['initialRolls'];idx=0
        for limit,cutoff,compare in ((16,7,'lt'),(9,4,'lt'),(5,3,'lt'),(2,0,'eq'),(3,1,'ge')):
            draw=rolls[idx]*limit//256;idx+=1
            matches=draw<cutoff if compare=='lt' else draw==cutoff if compare=='eq' else draw>=cutoff
            if matches:break
        else:idx=6
        outcome=idx-1
        if not blocked:
            if outcome in (0,1):wanted['hp']=min(v[5]+helper.variance_reference((60,240)[outcome],rolls[idx:idx+2],1),v[7])
            elif outcome in (2,5):wanted['hp']=min(v[5]+9999,v[7])
            elif outcome in (3,4):wanted['pp']=min(v[6]+helper.variance_reference(5 if outcome==3 else 20,rolls[idx:idx+2],1),v[8])
            if outcome==5:wanted['pp']=min(v[6]+v[8],v[8])
    elif not blocked:
        if r[25]&60==32:
            row=next((x for x in condiments if x[0]==food),None);good=set(row[1:3]) if row else set()
            selected=next((x for x in inventory if x and x in good),0)
            if not selected:selected=126 if 126 in inventory else next((x for x in inventory if x and items[x*39+25]&60==40),0)
            if selected:
                inventory.pop(inventory.index(selected));inventory.append(0)
                if row and (selected in good or selected==126):params=list(row[3:7])
        effect,amount=params[0],params[2] if v[39]==4 else params[1];rolls=actual['effectRolls']
        if effect in (0,2):wanted['hp']=min(v[5]+(30000 if not amount else helper.variance_reference(amount*6,rolls[:2],1)),v[7])
        if effect in (1,2):
            pp_rolls=actual['secondRolls'] if effect==2 else rolls
            wanted['pp']=min(v[6]+(30000 if not amount else helper.variance_reference(amount,pp_rolls[:2],1)),v[8])
        if 3<=effect<=8:
            which=rolls[0]*5//256 if effect==3 else effect-4
            fields=('targetIq','guts','speed','targetVitality','luck');field=fields[which]
            wanted[field]=min(wanted[field]+amount,255) if which in (0,3) else (wanted[field]+amount)&65535
            wanted['boosted'][which]=min(v[45]+amount,255)
        if effect==9:
            if wanted['aff'][0] in (6,7):wanted['aff'][0]=0
            elif wanted['aff'][2]==1:wanted['aff'][2]=0
        elif effect==10 and wanted['aff'][0]==5:wanted['aff'][0]=0
        if params[3]:wanted.update(partyStatus=3,animationVar=5,taskFrames=params[3]*6,taskId=5)
    if v[36] and r[28]&128 and r[28]&2:
        # Actual post-action item consumption follows its packed consumed flag.
        if inventory and inventory[0]==food:inventory.pop(0);inventory.append(0)
    if v[36] and food in (224,225):wanted['stamina']=[191,143]
    return wanted,outcome


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('build','native-source','assets','runtime','scratch','output','project'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--pilot',action='store_true')
    args=parser.parse_args()
    if args.scratch.exists():raise ValueError('Fresh scratch directory required')
    pin=subprocess.check_output(['git','-C',str(args.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=helper.PIN:raise ValueError('Unreviewed Redux revision')
    args.scratch.mkdir(parents=True);session=args.scratch/'session';session.mkdir()
    helper.DRIVER=driver_source();exe,build=helper.private_build(args)
    _,_,assets=read_pack(args.assets,args.native_source/'src/data/runtime_generated/asset_ids.h')
    items=assets['data/item_configuration_table.bin'];actions=assets['data/battle_action_table.bin'];raw=assets['data/condiment_table.bin']
    condiments=[list(raw[i:i+7]) for i in range(0,len(raw)-6,7) if raw[i]]
    foods=[]
    for item in range(1,len(items)//39):
        action=int.from_bytes(items[item*39+29:item*39+31],'little')
        function=int.from_bytes(actions[action*12+8:action*12+12],'little')
        if function==0xC2B27D:foods.append(item)
    tests=[]
    def add(item,character,unconscious,seed,category,profile=(0,0,0),route=0,boosted=0,status=None):
        action=int.from_bytes(items[item*39+29:item*39+31],'little')
        function=int.from_bytes(actions[action*12+8:action*12+12],'little')
        v=[len(tests),action,seed*0x9e3779b9&0xffffffff,0,0,500,100,999,300,
            unconscious,0,0,0,0,0,0,255,255,255,255,255,255,20,0,80,50,20,0,0,0,item,0,
            0,1,profile[0],profile[1],route,profile[2],0,character,20,20,0,0,0,boosted,50,0]
        if status is not None:v[9],v[11]=status
        tests.append({'name':f'{category} item{item} PC{character} unconscious{unconscious} seed{seed} route{route} profile{profile} boosted{boosted}',
            'values':v,'item':item,'function':function,'category':category,'route':route})
    for item in foods:
        for character in (1,4):
            for unconscious in (0,1):
                for seed in range(1,9):add(item,character,unconscious,seed,'all-packed-foods')
    condiment_ids=[i for i in range(1,len(items)//39) if items[i*39+25]&60==40]
    for row in condiments:
        food=row[0]
        if food not in foods:continue
        good=next((x for x in row[1:3] if x and x!=126),126)
        wrong=next(x for x in condiment_ids if x not in row[1:3] and x!=126)
        for profile in ((wrong,0,0),(wrong,126,0),(wrong,126,good)):
            for character in (1,4):
                for seed in range(1,9):add(food,character,0,seed,'condiment-priority-consumption',profile)
    for item in foods:
        if 4<=items[item*39+31]<=8:
            for character in (1,4):
                for seed in range(1,9):add(item,character,0,seed,'boosted-byte-saturation',boosted=254)
    for unconscious in (0,1):
        for character in (1,4):
            for seed in range(1,257):add(226,character,unconscious,seed,'lucky-sandwich-sequential-outcomes')
    for item,status in ((111,(0,1)),(111,(6,1)),(111,(7,1)),(111,(5,1)),(112,(5,2)),(112,(7,2))):
        for character in (1,4):add(item,character,0,1,'status-food-ordering',status=status)
    # Actual description -> target -> callback -> consumption, bounded before
    # further post-action status/turn processing. Includes Skip stamina CC.
    for item in (88,98,100,101,111,112,113,224,225,226):
        for character in (1,4):
            for seed in range(1,17):add(item,character,0,seed,'description-to-consumption',route=1)
    if args.pilot:
        full=tests
        tests=[next(t for t in full if t['category']==cat) for cat in sorted({t['category'] for t in full})]
        tests += [next(t for t in full if t['category']=='description-to-consumption' and t['item']==item)
                  for item in (98,100,101,111,112,113,224,225,226)]
        tests += [next(t for t in full if t['category']=='condiment-priority-consumption' and t['values'][37])]
    for i,t in enumerate(tests):t['values'][0]=i
    path=args.scratch/'cases.tsv';path.write_text('\n'.join(' '.join(map(str,t['values'])) for t in tests)+'\n')
    run=subprocess.run([str(exe.resolve()),str(args.assets.resolve()),str(session.resolve()),str(path.resolve())],
        cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=240)
    (args.scratch/'native.log').write_bytes(run.stdout+run.stderr)
    lines=run.stdout.decode(errors='replace').splitlines();parsed={}
    for prefix in ('QA ','QA_DETAIL ','QA_FOOD '):
        for line in lines:
            if line.startswith(prefix):
                r=json.loads(line[len(prefix):]);parsed.setdefault(r['id'],{}).update(r)
    rows=[];outcomes=collections.Counter()
    for i,t in enumerate(tests):
        a=parsed.get(i,{});errors=[]
        if not a or 'items' not in a:errors.append('Missing native food result')
        else:
            wanted,outcome=expected(t,a,items,condiments)
            if outcome is not None:outcomes[outcome]+=1
            for key,value in wanted.items():
                if a[key]!=value:errors.append(f'{key}: got {a[key]} expected {value}')
            if a['depth']!=1 or a['steps']>=30000:errors.append('Bounded native continuation did not finish')
        rows.append({'name':t['name'],'function':f'{t["function"]:06X}','item':t['item'],'actionId':t['values'][1],
            'category':t['category'],'route':'production-description-to-consumption' if t['route'] else 'direct-handler',
            'passed':not errors,'errors':errors})
    refs=['src/game/battle_actions.c','src/game/battle.c','src/game/inventory.c','src/game/maternalbound.c',
        'asm/battle/eat_food.asm','asm/battle/apply_condiment.asm','asm/misc/find_condiment.asm',
        'asm/battle/recover_hp.asm','asm/battle/recover_pp.asm','asm/battle/actions/healing_alpha.asm',
        'asm/battle/actions/heal_poison.asm','asm/overworld/party/schedule_party_animation_reset.asm']
    pinned=[]
    for p in ('ccscript/main.ccs','ccscript/redux/lucky_sandwich_revamp.ccs','ccscript/redux/better_condiment_search.ccs',
              'ccscript/bugfixes/stats_limit_fix.ccs','ccscript/bugfixes/rock_candy_fix.ccs','ccscript/dialogue/battle_text.ccs'):
        f=args.project/p;b=subprocess.check_output(['git','-C',str(args.project.parent),'show',f'{pin}:Project/{p}'])
        if f.read_bytes().replace(b'\r\n',b'\n')!=b.replace(b'\r\n',b'\n'):raise ValueError('Pinned source differs')
        pinned.append({'path':p,'sha256':helper.digest(f),'matchesPinnedSource':True})
    report={'schemaVersion':1,'toolVersion':'dev15-food-semantics','reduxRevision':pin,
        'runtimeSha256':{name:helper.digest(args.runtime/name) for name in ('player.exe','observer.exe')},
        'assetsSha256':helper.digest(args.assets),'privateBuild':build,'nativeExitCode':run.returncode,
        'cases':rows,'sourceReferences':[{'path':p,'sha256':helper.digest(args.native_source/p)} for p in refs],
        'pinnedReduxReferences':pinned,'sourceReferenceRole':'Review inputs separately identified from the immutable executed library.',
        'reproductionFlags':{name:str(getattr(args,name.replace('-','_'))) for name in ('build','native-source','assets','runtime','scratch','output','project')},
        'pilot':args.pilot,'semanticCoverage':{'executedCases':len(tests),'completedNativeCases':len(parsed),
            'categories':dict(collections.Counter(t['category'] for t in tests)),'luckySandwichOutcomes':dict(outcomes),
            'activeCallbacks':[f'{f:06X}' for f in sorted({t['function'] for t in tests})]},
        'allPassed':run.returncode==0 and len(parsed)==len(tests) and all(r['passed'] for r in rows),
        'limits':['Exact packed parameters and pinned/original source-derived state assertions; no independent original-machine food oracle.',
            'Direct callback fixtures verify condiment consumption but bypass the outer food consumption/description caller. Description-to-consumption cases execute actual BTL_EXEC_DESC through post-action dead-player check and stop before later status/turn processing.',
            'RNG is observed and restored at actual native effect entry points; this does not independently prove the complete RNG timeline.',
            'Deferred animation task ID/delay is checked at scheduling, not its complete future execution.',
            'No full enemy AI, whole encounter, physical input, rendered pixel/audio or full-story claims.',
            'Only player library executed; observer hash is provenance. No owner save or asset bytes redistributed.'],
        'fullConversionVerified':False,'fullPlaythroughVerified':False}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cases':len(rows),'completed':len(parsed),'passed':sum(r['passed'] for r in rows),
        'nativeExitCode':run.returncode,'allPassed':report['allPassed'],'firstFailures':[r for r in rows if not r['passed']][:5]}))
    if not report['allPassed']:raise SystemExit(1)


if __name__=='__main__':main()
