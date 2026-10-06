# SPDX-License-Identifier: GPL-3.0-or-later
"""Real native food/summon continuations with exact packed caller contexts.

The private driver links the immutable production library. It constructs each
summon group through the actual BS_ENTER constructor and normal native battle
sprite setup/layout, then dispatches the selected callback. It never changes
owner saves, asset bytes, production source or shared builds.
"""
import argparse
import collections
import json
import os
from pathlib import Path
import struct
import subprocess

import battle_action_catalog_qa as helper
import battle_action_catalog_qa_dev15 as additional
from build_maternalbound_pack import read_pack


def driver_source(original=False):
    src=additional.driver_source()
    if original:
        src=src.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"')
        src=src.replace(' || !maternalbound_enabled()', ' || maternalbound_enabled()')
    src=src.replace('static unsigned qa_function,qa_var_count,qa_var_rolls[32],qa_damage[16];',
        'static unsigned qa_function,qa_var_count,qa_var_rolls[32],qa_damage[16];\nstatic unsigned qa_group_count,qa_art_count,qa_art_ids[4],qa_before_count;')
    src=src.replace('unsigned original_attacker=bt.current_attacker,original_target=bt.current_target;',r'''
        qa_group_count=qa_art_count=qa_before_count=0;
        memset(qa_art_ids,0,sizeof(qa_art_ids));
        if(v[4]==3) {
            /* Use the actual constructor, then its ordinary native sprite
             * preparation and layout. Stop before a whole encounter/AI turn. */
            memset(&bt.battlers_table[8],0,sizeof(Battler)*(BATTLER_COUNT-8));
            ModeState group={0};group.battle_scripted.phase=BS_ENTER;
            group.battle_scripted.battle_group=(uint16_t)v[34];
            StepResult setup=mode_step_battle_scripted(&group);
            if(setup.kind!=STEP_PUSH || group.battle_scripted.phase!=BS_SWIRL_DONE)return 8;
            qa_group_count=bt.enemies_in_battle;
            setup_battle_enemy_sprites();
            qa_art_count=bt.current_battle_sprites_allocated;
            for(unsigned i=0;i<4;i++)qa_art_ids[i]=bt.current_battle_sprite_enemy_ids[i];
            for(unsigned i=0;i<bt.enemies_in_battle;i++)
                battle_init_enemy_stats(&bt.battlers_table[8+i],bt.enemies_in_battle_ids[i]);
            if(!layout_enemy_battle_positions())return 9;
            bt.current_attacker=bt.current_target=8*sizeof(Battler);
            a=t=&bt.battlers_table[8];
            a->current_action=(uint16_t)v[1];a->current_action_argument=(uint8_t)v[30];
            for(unsigned i=8;i<BATTLER_COUNT;i++)qa_before_count+=bt.battlers_table[i].consciousness==1;
            if(v[35]) {
                /* These globals are transient and absent after cold startup.
                 * Actual group constructors/art helpers above have separate
                 * immutable asset dependencies, matching production. */
                btl_entry_ptr_table=btl_entry_bg_table=NULL;
            }
        }
        unsigned original_attacker=bt.current_attacker,original_target=bt.current_target;''')
    src=src.replace('        fflush(stdout);',r'''
        if(v[4]==3) {
            unsigned after=0;for(unsigned i=8;i<BATTLER_COUNT;i++)after+=bt.battlers_table[i].consciousness==1;
            Battler *summoned=battler_from_offset(bt.current_target);
            printf("QA_SUMMON {\"id\":%u,\"initialGroupCount\":%u,\"artCount\":%u,\"artIds\":[%u,%u,%u,%u],\"beforeCount\":%u,\"afterCount\":%u,\"summonedId\":%u,\"summonedHp\":%u,\"summonedTurn\":%u,\"summonedVram\":%u,\"summonedSprite\":%u}\n",
                v[0],qa_group_count,qa_art_count,qa_art_ids[0],qa_art_ids[1],qa_art_ids[2],qa_art_ids[3],
                qa_before_count,after,summoned->id,summoned->hp_target,summoned->has_taken_turn,
                summoned->vram_sprite_index,summoned->sprite);
        }
        fflush(stdout);''')
    return src


def groups_from_pack(assets):
    pointers=assets['data/btl_entry_ptr_table.bin'];data=assets['data/enemy_battle_groups_table.bin'];groups={}
    for group in range(len(pointers)//8):
        offset=int.from_bytes(pointers[group*8:group*8+3],'little')-0xD0D52D
        if not 0<=offset<len(data):raise ValueError('Group pointer outside actual packed data')
        rows=[]
        while offset+2<len(data) and data[offset]!=255:
            rows.append(struct.unpack_from('<BH',data,offset));offset+=3
        groups[group]=rows
    return groups


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('build','native-source','assets','runtime','scratch','output','project'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--original',action='store_true')
    parser.add_argument('--entry-bindings',choices=('bound','cold','both'),default='both')
    parser.add_argument('--diagnostic',action='store_true',help='Preserve a known failing baseline without exiting nonzero.')
    args=parser.parse_args()
    if args.scratch.exists():raise ValueError('Fresh private scratch directory required')
    pin=subprocess.check_output(['git','-C',str(args.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=helper.PIN:raise ValueError('Unreviewed Redux revision')
    args.scratch.mkdir(parents=True);session=args.scratch/'session';session.mkdir()
    helper.DRIVER=driver_source(args.original)
    exe,build_evidence=helper.private_build(args)
    _,_,assets=read_pack(args.assets,args.native_source/'src/data/runtime_generated/asset_ids.h')
    groups=groups_from_pack(assets);enemy_data=assets['data/enemy_configuration_table.bin']
    actions=assets['data/battle_action_table.bin']
    by_function={int.from_bytes(actions[p+8:p+12],'little'):p//12 for p in reversed(range(0,len(actions),12))}
    tests=[]
    # Both natural initial-species controls and intentional zero-count summon
    # species from actual group records. All selected groups fit comfortably
    # before and after a single added small sprite; placement proof is bounded.
    for group,enemy in ((8,129),(8,134),(9,129),(9,134),(431,129),(431,134),(460,1)):
        records=groups[group]
        if enemy not in [e for n,e in records]:raise ValueError('Target absent from actual full group')
        maximum=enemy_data[enemy*94+92]
        existing=sum(n for n,e in records if e==enemy)
        threshold=int((maximum-existing)*205/maximum)&255 if maximum else 0
        for function in (0xC2C145,0xC2C13C):
            for binding in (('bound','cold') if args.entry_bindings=='both' else (args.entry_bindings,)):
                for seed in range(1,65):
                    v=[len(tests),by_function[function],seed*0x9e3779b9&0xffffffff,records[0][1]+1,3,
                        2000,200,2000,300,0,0,0,0,0,0,0,255,255,255,255,255,255,20,0,80,50,20,0,0,0,enemy,0,
                        0,1,group,int(binding=='cold'),0,0,0,0,20,20,0,0,0,0,50,0]
                    tests.append({'name':f'Summon group {group} enemy {enemy} callback {function:06X} {binding} seed {seed}',
                        'values':v,'group':group,'enemy':enemy,'function':function,'threshold':threshold,'binding':binding,
                        'initialCount':sum(n for n,e in records),'fullArtIds':[e for n,e in records],
                        'summonOnly':not existing})
    inputs=args.scratch/'cases.tsv';inputs.write_text('\n'.join(' '.join(map(str,t['values'])) for t in tests)+'\n')
    run=subprocess.run([str(exe.resolve()),str(args.assets.resolve()),str(session.resolve()),str(inputs.resolve())],
        cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=120)
    (args.scratch/'native.log').write_bytes(run.stdout+run.stderr)
    lines=run.stdout.decode(errors='replace').splitlines()
    basic={r['id']:r for r in (json.loads(x[3:]) for x in lines if x.startswith('QA '))}
    actual={r['id']:r for r in (json.loads(x[10:]) for x in lines if x.startswith('QA_SUMMON '))}
    rows=[]
    for i,t in enumerate(tests):
        b=basic.get(i,{});a=actual.get(i,{});errors=[]
        success=bool(b) and b['firstRoll']<t['threshold']
        expected={'initialGroupCount':t['initialCount'],'beforeCount':t['initialCount'],
            'afterCount':t['initialCount']+int(success),'artCount':len(t['fullArtIds'])}
        if success:
            expected.update(summonedId=t['enemy'],summonedHp=int.from_bytes(enemy_data[t['enemy']*94+33:t['enemy']*94+35],'little'),
                summonedTurn=1,summonedVram=t['fullArtIds'].index(t['enemy']),
                summonedSprite=int.from_bytes(enemy_data[t['enemy']*94+28:t['enemy']*94+30],'little'))
        if not a:errors.append('Missing native result')
        else:
            for key,value in expected.items():
                if a[key]!=value:errors.append(f'{key}: got {a[key]} expected {value}')
            if a['artIds'][:len(t['fullArtIds'])]!=t['fullArtIds']:errors.append('Loaded enemy art does not include exact full group order')
            if b['depth']!=1 or b['steps']>=30000:errors.append('Native child did not complete')
        rows.append({'name':t['name'],'function':f'{t["function"]:06X}','group':t['group'],'enemy':t['enemy'],
            'entryTableGlobals':t['binding'],'summonOnlySpecies':t['summonOnly'],'seed':t['values'][2],'roll':b.get('firstRoll'),
            'threshold':t['threshold'],'expectedSuccess':success,'expected':expected,'actual':a,'passed':not errors,'errors':errors})
    refs=['src/game/battle_actions.c','src/game/battle_ui.c','src/game/battle.c',
        'asm/battle/call_for_help_common.asm','asm/battle/actions/call_for_help.asm','asm/battle/actions/sow_seeds.asm',
        'asm/battle/enemy/setup_battle_enemy_sprites.asm','asm/battle/enemy/find_battle_sprite_for_enemy.asm',
        'asm/battle/get_battle_sprite_width.asm','asm/battle/success_255.asm']
    report={'schemaVersion':1,'toolVersion':'dev15-food-summon','reduxRevision':pin,'originalPack':args.original,
        'runtimeSha256':{name:helper.digest(args.runtime/name) for name in ('player.exe','observer.exe')},
        'assetsSha256':helper.digest(args.assets),'privateBuild':build_evidence,'nativeExitCode':run.returncode,
        'cases':rows,'sourceReferences':[{'path':p,'sha256':helper.digest(args.native_source/p)} for p in refs],
        'sourceReferenceRole':'Current source review inputs; separately hashed immutable native library identifies executed code.',
        'reproductionFlags':{name:str(getattr(args,name.replace('-','_'))) for name in ('build','native-source','assets','runtime','scratch','output','project','entry-bindings')},
        'diagnosticMode':args.diagnostic,'semanticCoverage':{'executedCases':len(tests),'completedNativeCases':len(actual),
            'passedCases':sum(r['passed'] for r in rows),'activeCallbacks':[f'{f:06X}' for f in sorted({t['function'] for t in tests})]},
        'allPassed':run.returncode==0 and len(actual)==len(tests) and all(r['passed'] for r in rows),
        'limits':['Source-derived expected behavior; no original-machine comparison in this tool.',
            'Actual BS_ENTER constructor and native sprite setup/layout precede real summon callbacks; full encounter turns and AI selection are not executed.',
            'Both callbacks intentionally tested with exact group parameters, but not every enemy AI assigns both callbacks in every group.',
            'Selected comfortably fitting groups test one added enemy and full-group art allocation; dead replacement, packed rows and every summon group remain unevaluated.',
            'Cold cases clear transient battle-entry pointer globals after actual group/sprite construction; they are consumer prerequisites, not serialized owner-save loading.',
            'State/art allocation assertions do not certify rendered pixel appearance or physical controller interaction.',
            'Only player library is executed. Observer hash is separate provenance.',
            'No owner save, ROM or extracted payload bytes included.'],
        'fullConversionVerified':False,'fullPlaythroughVerified':False}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cases':len(rows),'completed':len(actual),'passed':sum(r['passed'] for r in rows),
        'nativeExitCode':run.returncode,'allPassed':report['allPassed'],'firstFailures':[r for r in rows if not r['passed']][:3]}))
    if not report['allPassed'] and not args.diagnostic:raise SystemExit(1)


if __name__=='__main__':main()
