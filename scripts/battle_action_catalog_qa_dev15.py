# SPDX-License-Identifier: GPL-3.0-or-later
"""Additional isolated battle progression/item semantics, separate from dev14.

Uses the release-frozen private builder but adds fixture context and observables.
Owner saves and production sources/builds are never written. Source-derived
expectations are not described as independent original-machine validation.
"""
import argparse
import collections
import json
import os
from pathlib import Path
import re
import struct
import subprocess

import battle_action_catalog_qa as frozen
from build_maternalbound_pack import read_pack


def driver_source():
    src=frozen.DRIVER
    src=src.replace('extern int eb_platform_main(int argc, char **argv);',
        'extern int eb_platform_main(int argc, char **argv);\nextern const uint8_t *btl_entry_ptr_table,*btl_entry_bg_table;\nstatic unsigned qa_function,qa_var_count,qa_var_rolls[32],qa_damage[16];')
    # Preserve control-code changes to instant printing during cinematics. Forcing
    # it back on each step can skip required script/render synchronization beats.
    src=src.replace('dt.instant_printing=1;', '')
    src=src.replace('else { core.frame_counter++; core.nmi_count++; }',
        'else { host_process_frame(); }')
    src=src.replace('StepResult r=mode_dispatch_step', '''
        unsigned pc=g_mode_stack.state[top].battle_action.pc;
        bool capture=(g_mode_stack.mode[top]==GAME_MODE_BATTLE_ACTION) &&
            ((qa_function==0xC292EE && pc==2) ||
             (qa_function>=0xC2C5D1 && qa_function<=0xC2C69E && pc==6) ||
             (qa_function==0xC2C6F0 && pc==9));
        unsigned vr[2]={0};
        if(capture) { RNGState saved=rng_state;vr[0]=rng_next_byte();vr[1]=rng_next_byte();rng_state=saved; }
        StepResult r=mode_dispatch_step''')
    src=src.replace('if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);', '''if(capture && r.kind==STEP_PUSH && r.push_mode==GAME_MODE_BATTLE_CALC && qa_var_count<30) {
            const BattleCalcState *calc=&r.push_init->battle_calc;
            qa_damage[qa_var_count/2]=(calc->kind==BC_CALC_DAMAGE)?calc->arg1:calc->arg0;
            qa_var_rolls[qa_var_count++]=vr[0];qa_var_rolls[qa_var_count++]=vr[1];
        }
        if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);''')
    src=src.replace('unsigned v[40],n=0;', 'unsigned v[48],n=0;').replace('n<40','n<48')
    src=src.replace('if(n!=32) return 5;', 'if(n!=48) return 5;')
    src=src.replace('FILE *input=fopen(argv[3],"r");', '''
    __typeof__(game_state) baseline_game_state=game_state;
    __typeof__(ow) baseline_ow=ow;
    __typeof__(dt) baseline_dt=dt;
    FILE *input=fopen(argv[3],"r");''')
    src=src.replace('memset(&bt,0,sizeof(bt));',
        'game_state=baseline_game_state;ow=baseline_ow;dt=baseline_dt;\n        entity_system_init();\n        dt.instant_printing=0;\n        memset(&bt,0,sizeof(bt));')
    src=src.replace('unsigned ti=v[3]?FIRST_ENEMY_INDEX:0;',
        'unsigned ti=v[3]?FIRST_ENEMY_INDEX:(v[39]?v[39]-1:0);')
    src=src.replace('CharStruct *c=&party_characters[0];', 'CharStruct *c=&party_characters[ti];')
    src=src.replace('npc_ai_table=ASSET_DATA(ASSET_DATA_NPC_AI_TABLE_BIN);', '''npc_ai_table=ASSET_DATA(ASSET_DATA_NPC_AI_TABLE_BIN);
    btl_entry_ptr_table=ASSET_DATA(ASSET_DATA_BTL_ENTRY_PTR_TABLE_BIN);
    btl_entry_bg_table=ASSET_DATA(ASSET_DATA_BTL_ENTRY_BG_TABLE_BIN);''')
    src=src.replace('unsigned rolls[8];rng_seed(v[2]);', '''
        t->consciousness=(uint8_t)v[33];
        t->iq=(uint8_t)v[40];t->vitality=(uint8_t)v[41];
        t->base_defense=(uint8_t)v[46];
        if(v[42]) { battle_init_enemy_stats(&bt.battlers_table[6],v[42]-1);bt.battlers_table[6].npc_id=v[42]-1; }
        if(v[47] && !v[3])party_characters[ti].items[1]=(uint8_t)v[47];
        bt.half_hppp_meter_speed=(uint16_t)v[43];bt.disable_hppp_rolling=(uint16_t)v[44];
        bt.battler_target_flags=v[45];
        game_state.leader_x_coord=(uint16_t)v[34];game_state.leader_y_coord=(uint16_t)v[35];
        game_state.unknownC3=7;
        ow.psi_teleport_style=ow.psi_teleport_destination=0;
        ow.battle_mode=v[38]?0:0xffff;
        bt.giygas_phase=(uint16_t)v[36];
        bt.current_battle_group=479;
        t->sprite_x=55;t->sprite_y=66;
        if(v[37]) {
            battle_init_enemy_stats(&bt.battlers_table[9],(uint16_t)v[37]-1);
            bt.battlers_table[9].hp=bt.battlers_table[9].hp_target=2000;
            bt.battlers_table[9].hp_max=2000;
        }
        if(v[32]==128) {
            /* Master Barf's real story precondition: Poo is temporarily away. */
            game_state.party_count=game_state.player_controlled_party_count=3;
            game_state.current_party_members=7;
            game_state.party_members[3]=game_state.party_order[3]=0;
            memset(&bt.battlers_table[3],0,sizeof(Battler));
        }
        unsigned original_attacker=bt.current_attacker,original_target=bt.current_target;
        qa_var_count=0;
        unsigned rolls[8];rng_seed(v[2]);''')
    src=src.replace('if(battle_action_dispatch(callback,&action)) {',
        'qa_function=callback;\n            if(battle_action_dispatch(callback,&action)) {\n                action.battle_action.pc=(uint8_t)(v[32]<128?v[32]:0);')
    src=src.replace('if(steps>=30000 || g_mode_stack.depth!=1) return 6;', '''if(steps>=30000 || g_mode_stack.depth!=1) {
            for(unsigned si=1;si<g_mode_stack.depth;si++) fprintf(stderr,"STALL slot=%u mode=%u rawphase=%u actionpc=%u\\n",si,g_mode_stack.mode[si],g_mode_stack.state[si].display_text.phase,g_mode_stack.state[si].battle_action.pc);
            fprintf(stderr,"ENTITY disabled=%u state=%u slot=%d\\n",ert.disable_actionscript,ert.actionscript_state,ert.current_entity_offset);
            for(unsigned ei=0;ei<MAX_ENTITIES;ei++) if(entities.script_table[ei]>=0) {
                unsigned ss=entities.script_index[ei];
                fprintf(stderr,"ENTITY e=%u index=%u script=%d x=%d y=%d pc=%u bank=%u sleep=%d vars=%d,%d,%d,%d\\n",ei,ss,entities.script_table[ei],entities.abs_x[ei],entities.abs_y[ei],scripts.pc[ss],scripts.pc_bank[ss],scripts.sleep_frames[ss],entities.var[0][ei],entities.var[1][ei],entities.var[2][ei],entities.var[3][ei]);
            }
            return 6;
        }''')
    marker='        fflush(stdout);'
    extra=r'''        printf("QA_DETAIL {\"id\":%u,\"targetId\":%u,\"targetTurn\":%u,\"targetSprite\":[%u,%u],\"giygasPhase\":%u,\"battleGroup\":%u,\"specialDefeat\":%u,\"skipDeath\":%u,\"teleportStyle\":%u,\"teleportDestination\":%u,\"attackerRestored\":%u,\"targetRestored\":%u,\"secondId\":%u,\"secondHp\":%u,\"secondConscious\":%u,\"pooId\":%u,\"pooConscious\":%u,\"targetIq\":%u,\"targetVitality\":%u,\"attackerItem\":%u,\"rolls8\":[",
            v[0],t->id,t->has_taken_turn,t->sprite_x,t->sprite_y,bt.giygas_phase,bt.current_battle_group,
            bt.special_defeat,bt.skip_death_text_and_cleanup,ow.psi_teleport_style,ow.psi_teleport_destination,
            bt.current_attacker==original_attacker,bt.current_target==original_target,
            bt.battlers_table[9].id,bt.battlers_table[9].hp_target,bt.battlers_table[9].consciousness,
            bt.battlers_table[3].id,bt.battlers_table[3].consciousness,t->iq,t->vitality,
            a->ally_or_enemy==0?party_characters[a->id-1].items[0]:0);
        for(unsigned ri=0;ri<8;ri++) printf("%s%u",ri?",":"",rolls[ri]);
        printf("],\"varianceRolls\":[");
        for(unsigned ri=0;ri<qa_var_count;ri++) printf("%s%u",ri?",":"",qa_var_rolls[ri]);
        printf("],\"damageInputs\":[");
        for(unsigned ri=0;ri<qa_var_count/2;ri++) printf("%s%u",ri?",":"",qa_damage[ri]);
        printf("]}\n");
        printf("QA_STATUS {\"id\":%u,\"ghostId\":%u,\"ghostNpc\":%u,\"ghostConscious\":%u,\"ghostTurn\":%u,\"rollingHalf\":%u,\"rollingDisabled\":%u,\"targetFlags\":%u}\n",
            v[0],bt.battlers_table[6].id,bt.battlers_table[6].npc_id,bt.battlers_table[6].consciousness,
            bt.battlers_table[6].has_taken_turn,bt.half_hppp_meter_speed,bt.disable_hppp_rolling,(unsigned)bt.battler_target_flags);
'''
    src=src.replace(marker,extra+marker)
    return src


def expectations(test,result):
    oracle=test['oracle'];kind=oracle.get('kind');v=test['values'];rolls=result['rolls8']
    if not kind:return oracle
    if kind=='barf':
        vr=result['varianceRolls']
        return {'hp':2000-frozen.variance_reference(360,vr[:2],1),
            'secondHp':2000-frozen.variance_reference(360,vr[2:4],1),
            'party':[1,2,3,4,0,0],'partyCount':4,'pooId':4,'pooConscious':1,
            'attackerRestored':1,'targetRestored':1}
    if kind=='prayer-damage':
        # Original CALC_DAMAGE deliberately skips Giygas6 HP reduction. Prayer
        # progress is phase-driven; the displayed damage input still varies.
        return {'hp':v[5],'damageInputs':[frozen.variance_reference(oracle['damage'],result['varianceRolls'][:2],1)],
            'giygasPhase':oracle['phase'],'battleGroup':oracle['group']}
    if kind=='escape':
        strength=oracle['strength'];threshold=((strength-128)&65535)^0xff80
        success=not oracle['sectorBlocked'] and (v[38] or rolls[0]*100//256<threshold and not oracle['boss'])
        return {'specialDefeat':int(success),'teleportStyle':3 if success else 0,
            'teleportDestination':7 if success else 0,'attackerItem':0 if success else v[30]}
    if kind=='recovery':
        power=oracle['power']
        if power==10000:amount=10000 if v[39]==4 else rolls[0]*4//256+1
        else:amount=(rolls[0]*4//256)+1 if power==-1 else frozen.variance_reference(power,rolls[:2],1)
        field='hp' if oracle['resource']=='hp' else 'pp';start=v[5] if field=='hp' else v[6];maximum=v[7] if field=='hp' else v[8]
        return {field:start if v[9]==1 else min(start+amount,maximum)}
    if kind=='stat':
        field=oracle['field'];amount=rolls[0]*4//256+1
        return {field:(oracle['before']+amount)&(255 if field in ('targetIq','targetVitality') else 65535)}
    if kind=='random-stat':
        fields=('defense','offense','speed','guts','targetVitality','targetIq','luck')
        before={'defense':50,'offense':80,'speed':20,'guts':0,'targetVitality':20,'targetIq':20,'luck':20}
        field=fields[rolls[0]*7//256];before[field]=(before[field]+rolls[1]*4//256+1)&(255 if field in ('targetIq','targetVitality') else 65535)
        return before
    if kind=='infliction':
        group=oracle['group'];value=oracle['value'];aff=v[9:16].copy();roll_index=0
        success=v[23]==0 and not (oracle.get('onlyPlayer') and v[3])
        if oracle.get('luckLimit'):
            success=success and rolls[roll_index]*oracle['luckLimit']//256>=v[22];roll_index+=1
        if oracle.get('resistIndex') is not None:
            success=success and rolls[roll_index]<v[oracle['resistIndex']]
        if oracle.get('concentration'):
            success=success and aff[group]==0 and not (oracle.get('brainStone') and v[47]==201 and not v[3])
        else:success=success and (aff[group]==0 or aff[group]>value)
        if success:aff[group]=value
        result={'aff':aff,'hp':v[5]}
        if oracle.get('diamond'):
            if success:result['aff']=[2,0,0,0,0,0,0]
            result.update(battleExp=oracle['exp'] if success else 0,battleMoney=oracle['money'] if success else 0)
        if oracle.get('onlyPlayer'):
            spawned=success and not v[42]
            ghost=213 if spawned else v[42]-1 if v[42] else 0
            result.update(ghostId=ghost,ghostNpc=ghost,ghostConscious=int(spawned or bool(v[42])),ghostTurn=int(spawned))
        return result
    if kind=='heal-poison':
        aff=v[9:16].copy()
        if aff[0]==5:aff[0]=0
        return {'aff':aff,'hp':v[5]}
    if kind=='shield-killer':
        aff=v[9:16].copy()
        if rolls[0]*80//256>=v[22] and aff[6]:aff[6]=0
        return {'aff':aff,'shieldhp':v[28],'hp':v[5]}
    if kind=='reduce-pp':
        # The action returns before REDUCE_PP for zero PP or max PP < 16.
        # Otherwise original SET_PP also clamps its subtraction to max PP,
        # including deliberately prepared over-max boundary states.
        if v[6]==0 or v[8]<16:pp=v[6]
        else:
            amount=frozen.variance_reference(v[8]//16,rolls[:2],0)
            pp=min(max(0,v[6]-amount),v[8])
        return {'pp':pp,'attackerPp':200}
    if kind=='guts-pill':
        return {'guts':v[27] if v[23] else min((v[27]*2)&65535,255)}
    if kind=='defense-spray':
        value=v[25]
        # Pinned enabled Redux replaces the fourth LSR with NOP and the
        # cap multiplier with seven. Preserve original uint16 addition.
        if not v[23]:value=min((value+max(1,value//8))&65535,v[46]*7//4)
        return {'defense':value}
    raise ValueError('Unknown source-derived assertion: '+str(kind))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('build','native-source','assets','runtime','scratch','output','project'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--baseline',type=Path,default=Path('research/redux-battle-action-coverage.json'))
    parser.add_argument('--only-category')
    parser.add_argument('--full-cutscene-prerequisites',action='store_true',
        help='Diagnostic full first-prayer cinematic entry; otherwise stage at reviewed post-cinematic continuation.')
    args=parser.parse_args()
    if args.scratch.exists():raise ValueError('Fresh isolated scratch required.')
    pin=subprocess.check_output(['git','-C',str(args.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=frozen.PIN:raise ValueError('Review new Redux revision before running.')
    args.scratch.mkdir(parents=True);session=args.scratch/'session';session.mkdir()
    frozen.DRIVER=driver_source();exe,build_evidence=frozen.private_build(args)
    _,_,assets=read_pack(args.assets,args.native_source/'src/data/runtime_generated/asset_ids.h')
    data=assets['data/battle_action_table.bin'];records=[struct.unpack('<BBBBII',data[p:p+12]) for p in range(0,len(data),12)]
    by_function={r[5]:i for i,r in reversed(list(enumerate(records)))}
    tests=[]
    def add(name,function,oracle,category,**overrides):
        values=[len(tests),by_function.get(function,function),0x9e3779b9,8,0,2000,200,2000,300,
            0,0,0,0,0,0,0,255,255,255,255,255,255,20,0,80,50,20,0,0,0,0,0,
            0,1,0,0,0,0,0,0,20,20,0,0,0,0,50,0]
        for index,value in overrides.items():values[int(index)]=value
        tests.append({'name':name,'function':function,'values':values,'oracle':oracle,'category':category})

    # Exact Fly Honey loop mutates only the first conscious enemy Belch ID.
    for enemy in (7,93,169,192):
        for conscious in (0,1):
            wanted=169 if conscious and enemy in (93,192) else enemy
            add(f'Fly Honey enemy {enemy} conscious {conscious}',0xC2C1BD,
                {'targetId':wanted,'hp':2000},'fly-honey',**{'3':enemy+1,'33':conscious})
    for enemy in (93,192):
        add(f'Fly Honey transforms first of two Belches {enemy}',0xC2C1BD,
            {'targetId':169,'secondId':192,'hp':2000,'secondHp':2000},'fly-honey',**{'3':enemy+1,'37':193})
    for seed in range(1,17):
        add(f'Poo returns to three-character party and hits two enemies seed {seed}',0xC292EE,
            {'kind':'barf'},'poo-return',**{'32':128,'37':8,'2':(seed*0x9e3779b9)&0xffffffff})

    # Prepared valid final-boss contexts; full text/fade/load/swirl children run.
    add('Pokey first speech replaces boss and hides mech',0xC2C4C0,
        {'targetId':220,'targetTurn':1,'targetSprite':[55,66],'giygasPhase':3,'battleGroup':477,'skipDeath':1,'secondConscious':0},
        'giygas-progression',**{'3':219,'37':222,'36':1})
    add('Pokey second speech begins praying and replaces boss',0xC2C516,
        {'targetId':221,'targetTurn':1,'targetSprite':[55,66],'giygasPhase':4,'battleGroup':478,'skipDeath':1,'secondConscious':0},
        'giygas-progression',**{'3':221,'37':222,'36':3})
    add('Prayer one installs vulnerable boss phase',0xC2C572,
        {'targetId':229,'targetTurn':1,'targetSprite':[55,66],'giygasPhase':5,'battleGroup':479},
        'giygas-progression',**{'3':222,'37':222,'36':4,'32':0 if args.full_cutscene_prerequisites else 5})
    for prayer,function,damage in ((2,0xC2C5D1,50),(3,0xC2C5FA,100),(4,0xC2C623,200),
                                  (5,0xC2C64C,400),(6,0xC2C675,800),(7,0xC2C69E,1600)):
        for seed in range(1,9):
            add(f'Prayer {prayer} source damage and next phase seed {seed}',function,
                {'kind':'prayer-damage','damage':damage,'phase':prayer+4,'group':480 if prayer==7 else 479},
                'giygas-prayer-damage',**{'3':230,'5':60000,'7':60000,'36':prayer+3,'32':0 if args.full_cutscene_prerequisites else 5,'2':(seed*0x9e3779b9)&0xffffffff})
    add('Prayer eight advances to final prayer',0xC2C6D0,{'giygasPhase':12,'hp':2000},
        'giygas-progression',**{'3':230,'36':11})
    add('Final prayer runs death tail and requests special defeat',0xC2C6F0,
        {'specialDefeat':3,'giygasPhase':0,'battleGroup':483,'secondConscious':0},
        'giygas-progression',**{'3':230,'5':60000,'7':60000,'36':12,'37':222})

    # Select real packed sector attribute coordinates: no fabricated map flags.
    sector=assets['data/per_sector_attributes.bin']
    coords={blocked:next((i%32*256,i//32*128) for i in range(len(sector)//2)
                        if bool(struct.unpack_from('<H',sector,i*2)[0]&128)==blocked) for blocked in (False,True)}
    items=assets['data/item_configuration_table.bin']
    escape_items=[i for i in range(len(items)//39) if struct.unpack_from('<H',items,i*39+29)[0]==185]
    # The packed callback is active, but this revision assigns it to no item.
    # Test the unused API with real existing item-configuration operands only.
    teleport_has_story_item=bool(escape_items)
    if not escape_items:escape_items=[1,55,24,27,63,73]
    for item in escape_items:
        strength=items[item*39+31]
        for blocked in (False,True):
            for enemy in (7,93):
                for outside in (0,1):
                    for seed in range(1,33):
                        x,y=coords[blocked]
                        add(f'Teleport item {item} enemy {enemy} blocked {blocked} outside {outside} seed {seed}',0xC2AB71,
                            {'kind':'escape','strength':strength,'sectorBlocked':blocked,'boss':enemy==93},
                            'teleport-box',**{'30':item,'3':enemy+1,'34':x,'35':y,'38':outside,'2':(seed*0x9e3779b9)&0xffffffff})

    recovery=((0xC2A0AE,-1,'hp'),(0xC2A0BF,50,'hp'),(0xC2A0CF,200,'hp'),
              (0xC2A0DF,20,'pp'),(0xC2A0EF,80,'pp'),(0xC2A26F,300,'hp'),
              (0xC2A360,10,'hp'),(0xC2A370,100,'hp'),(0xC2A380,10000,'hp'))
    for function,power,resource in recovery:
        for character in ((1,4) if power==10000 else (1,)):
            for unconscious in (0,1):
                for seed in range(1,17):
                    add(f'Recovery {function:06X} {resource} character {character} unconscious {unconscious} seed {seed}',function,
                        {'kind':'recovery','power':power,'resource':resource},'recovery-items',
                        **{'3':0,'39':character,'5':0 if unconscious else 950,'6':290,'7':999,'8':300,'9':unconscious,'2':(seed*0x9e3779b9)&0xffffffff})
    for function,field,before in ((0xC2A0FF,'targetIq',20),(0xC2A14B,'guts',0),(0xC2A193,'speed',20),
                                 (0xC2A1DB,'targetVitality',20),(0xC2A227,'luck',20)):
        for seed in range(1,33):
            add(f'Stat food {function:06X} seed {seed}',function,{'kind':'stat','field':field,'before':before},
                'stat-items',**{'2':(seed*0x9e3779b9)&0xffffffff})
    for seed in range(1,65):
        add(f'Random stat food chooses source branch seed {seed}',0xC2A27F,{'kind':'random-stat'},'stat-items',
            **{'2':(seed*0x9e3779b9)&0xffffffff})
    for function,field,index,before in ((0xC2A0FF,'targetIq',40,254),(0xC2A14B,'guts',27,65534),
                                      (0xC2A193,'speed',26,65534),(0xC2A1DB,'targetVitality',41,254),(0xC2A227,'luck',22,65534)):
        for seed in range(1,17):
            add(f'Stat food {function:06X} original width boundary seed {seed}',function,
                {'kind':'stat','field':field,'before':before},'stat-width-boundaries',
                **{str(index):before,'2':seed*0x9e3779b9&0xffffffff})

    # Exact original status grouping/priority and chance sequencing. Values
    # remain in each real status domain; these are prepared battle boundaries.
    status_functions=((0xC28AEB,0,4,None,None),(0xC28B2C,0,5,None,None),
        (0xC28B6D,0,7,17,None),(0xC28BBE,1,1,None,None),
        (0xC28BFD,1,2,None,None),(0xC28C69,2,2,18,None),
        (0xC28CB8,2,3,None,None),(0xC28CF1,2,4,None,80),
        (0xC28D5A,4,4,19,40),(0xC28DBB,3,1,None,None),
        (0xC28DFC,2,2,None,None),(0xC28A92,0,3,19,80),
        (0xC289CE,0,2,19,None),(0xC2A3D1,4,4,None,40))
    enemy7=assets['data/enemy_configuration_table.bin'][7*94:8*94]
    for function,group,value,resist,luck_limit in status_functions:
        for npc_id in (0,9):
            for before in sorted({0,1,value,7 if group==0 else 4 if group in (2,4) else 2}):
                for resistance in ((0,26,128,255) if resist is not None else (255,)):
                    for seed in range(1,17):
                        oracle={'kind':'infliction','group':group,'value':value,'resistIndex':resist,'luckLimit':luck_limit,
                            'onlyPlayer':function==0xC28BFD,'concentration':group==4,'brainStone':function==0xC28D5A,
                            'diamond':function==0xC289CE,'exp':int.from_bytes(enemy7[37:41],'little'),'money':int.from_bytes(enemy7[41:43],'little')}
                        values={'23':npc_id,str(9+group):before,'2':seed*0x9e3779b9&0xffffffff,'22':20 if luck_limit else 0}
                        if resist is not None:values[str(resist)]=resistance
                        if function==0xC28BFD:values['3']=0
                        if function==0xC289CE:values.update({'10':2,'11':3,'12':1,'13':4,'14':1,'15':2})
                        add(f'Status {function:06X} NPC {npc_id} prior {before} resistance {resistance} seed {seed}',function,
                            oracle,'enemy-item-statuses',**values)
    for seed in range(1,17):
        for item in (0,201):
            add(f'Brain Stone prevents distraction item {item} seed {seed}',0xC28D5A,
                {'kind':'infliction','group':4,'value':4,'resistIndex':19,'luckLimit':40,'concentration':True,'brainStone':True},
                'brain-stone-concentration',**{'3':0,'47':item,'22':0,'2':seed*0x9e3779b9&0xffffffff})
        add(f'Possession rejects enemy target seed {seed}',0xC28BFD,
            {'kind':'infliction','group':1,'value':2,'onlyPlayer':True},'possession-ghost',**{'2':seed*0x9e3779b9&0xffffffff})
        add(f'Possession retains existing ghost seed {seed}',0xC28BFD,
            {'kind':'infliction','group':1,'value':2,'onlyPlayer':True},'possession-ghost',**{'3':0,'42':214,'2':seed*0x9e3779b9&0xffffffff})
    for easyheal in range(8):
        add(f'Serum only cures poison status {easyheal}',0xC2A39D,{'kind':'heal-poison'},'status-removal',**{'9':easyheal})
    for shield in range(5):
        for luck in (0,20,80):
            for seed in range(1,17):
                add(f'Shield Killer type {shield} luck {luck} seed {seed}',0xC2A422,
                    {'kind':'shield-killer'},'status-removal',**{'15':shield,'28':3,'22':luck,'2':seed*0x9e3779b9&0xffffffff})
    for pp in (0,1,200):
        for maximum in (15,16,320,2000):
            for seed in range(1,17):
                add(f'Reduce PP current {pp} max {maximum} seed {seed}',0xC28E42,
                    {'kind':'reduce-pp'},'pp-reduction',**{'6':pp,'8':maximum,'2':seed*0x9e3779b9&0xffffffff})
    for npc_id in (0,9):
        for guts in (0,1,127,128,255,32768,65535):
            add(f'Guts Pill NPC {npc_id} guts {guts}',0xC2AA7F,{'kind':'guts-pill'},'combat-stat-items',**{'23':npc_id,'27':guts})
        for function in (0xC2AAC6,0xC2AB0D):
            for defense in (0,1,16,50,62,63,100,65535):
                add(f'Defense spray {function:06X} NPC {npc_id} defense {defense}',function,
                    {'kind':'defense-spray'},'combat-stat-items',**{'23':npc_id,'25':defense})
    if args.only_category:tests=[t for t in tests if t['category']==args.only_category]
    for i,test in enumerate(tests):test['values'][0]=i
    input_file=args.scratch/'cases.tsv';input_file.write_text('\n'.join(' '.join(map(str,t['values'])) for t in tests)+'\n')
    p=subprocess.run([str(exe.resolve()),str(args.assets.resolve()),str(session.resolve()),str(input_file.resolve())],
        cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=240)
    (args.scratch/'native.log').write_bytes(p.stdout+p.stderr)
    lines=p.stdout.decode(errors='replace').splitlines()
    results={r['id']:r for r in (json.loads(line[3:]) for line in lines if line.startswith('QA '))}
    details={r['id']:r for r in (json.loads(line[10:]) for line in lines if line.startswith('QA_DETAIL '))}
    status_details={r['id']:r for r in (json.loads(line[10:]) for line in lines if line.startswith('QA_STATUS '))}
    rows=[]
    for i,test in enumerate(tests):
        actual={**results.get(i,{}),**details.get(i,{}),**status_details.get(i,{})};errors=[]
        if not actual:errors.append('No native result')
        else:
            for key,wanted in expectations(test,actual).items():
                if actual[key]!=wanted:errors.append(f'{key}: got {actual[key]} expected {wanted}')
            if actual['depth']!=1 or actual['steps']>=30000:errors.append('Native continuation did not complete')
        rows.append({'name':test['name'],'function':f'{test["function"]:06X}','actionId':test['values'][1],
            'entryPc':test['values'][32] if test['category'].startswith('giygas') else 0,
            'category':test['category'],'passed':not errors,'errors':errors})
    active={r[5] for r in records};tested={t['function'] for t in tests}
    baseline=json.loads(args.baseline.read_text());prior={int(r['function'],16) for r in baseline['cases'] if r['function']}
    union=active&(prior|tested)
    sources=['include/constants/battle.asm','asm/battle/actions/fly_honey.asm','asm/battle/actions/master_barf_death.asm',
        'asm/battle/actions/teleport_box.asm','asm/battle/boss_battle_check.asm',
        'asm/battle/replace_boss_battler.asm','asm/battle/giygas_hurt_prayer.asm',
        'asm/battle/display_battle_cutscene_text.asm','asm/battle/play_giygas_weakened_sequence.asm',
        'asm/battle/actions/pokey_speech_1.asm','asm/battle/actions/pokey_speech_2.asm',
        'asm/battle/actions/hp_recovery_1d4.asm','asm/battle/actions/iq_up_1d4.asm',
        'asm/battle/actions/random_stat_up_1d4.asm','src/game/battle_actions.c','src/game/battle.c','src/game/battle_ui.c',
        'asm/battle/inflict_status.asm','asm/battle/success_255.asm','asm/battle/success_luck40.asm','asm/battle/success_luck80.asm',
        'asm/battle/recover_hp.asm','asm/battle/recover_pp.asm','asm/battle/increase_defense_16th.asm',
        'asm/battle/reduce_pp.asm','asm/battle/set_pp.asm','src/game/battle_calc.c']
    sources+=['asm/battle/actions/giygas_prayer_'+str(i)+'.asm' for i in range(1,10)]
    sources+=['asm/battle/actions/'+name+'.asm' for name in (
        'hp_recovery_50','hp_recovery_200','pp_recovery_20','pp_recovery_80','hp_recovery_300','hp_recovery_10',
        'hp_recovery_100','hp_recovery_10000','guts_up_1d4','speed_up_1d4','vitality_up_1d4','luck_up_1d4',
        'nauseate','poison','cold','mushroomize','possess','crying','immobilize','solidify','distract','feel_strange',
        'crying2','paralyze','diamondize','counter_psi','heal_poison','shield_killer','reduce_pp','sudden_guts_pill',
        'defense_spray','defense_shower')]
    pinned=[]
    for path in ('ccscript/main.ccs','ccscript/expansion/Extended_Battle_Action_Table.ccs',
                 'ccscript/redux/m3sprites.ccs','ccscript/bugfixes/brainstone_fix.ccs','ccscript/bugfixes/heal_poison_fix.ccs',
                 'ccscript/redux/offense_defense_psi_buff.ccs'):
        source=args.project/path
        original=subprocess.check_output(['git','-C',str(args.project.parent),'show',f'{pin}:Project/{path}'])
        if source.read_bytes().replace(b'\r\n',b'\n')!=original.replace(b'\r\n',b'\n'):
            raise ValueError('Reviewed Redux source differs from pin: '+path)
        pinned.append({'path':path,'sha256':frozen.digest(source),'matchesPinnedSource':True})
    report={'schemaVersion':1,'toolVersion':'dev15-additional-semantics','reduxRevision':pin,
        'runtimeSha256':{name:frozen.digest(args.runtime/name) for name in ('player.exe','observer.exe')},
        'assetsSha256':frozen.digest(args.assets),'privateBuild':build_evidence,'nativeExitCode':p.returncode,
        'cases':rows,'sourceReferences':[{'path':path,'sha256':frozen.digest(args.native_source/path)} for path in sources],
        'pinnedReduxReferences':pinned,
        'reproductionFlags':{name:str(getattr(args,name.replace('-','_'))) for name in ('build','native-source','assets','runtime','scratch','output','project','baseline')},
        'sourceReferenceRole':'Reviewed sources at audit execution; tested library/executable identities are separately hashed. Older immutable library tests do not claim these current C files were their compiled source.',
        'baseline':{'reportSha256':frozen.digest(args.baseline),'runtimeSha256':baseline['runtimeSha256'],
            'passed':baseline['allPassed'],'coverageNotRelabeledToCurrentRuntime':True},
        'semanticCoverage':{'executedCases':len(tests),'completedNativeCases':len(results),
            'categories':dict(collections.Counter(t['category'] for t in tests)),
            'uniqueActiveCallbacksInNewCases':len(active&tested),'uniqueActiveCallbacksInPriorAndNewCases':len(union),
            'remainingActiveCallbacks':len(active-union),'unevaluatedActiveCallbacks':[f'{f:06X}' for f in sorted(active-union)]},
        'teleportBoxScope':{'sourceItemPresent':teleport_has_story_item,
            'claim':'Unused packed callback API tested with real item parameters; no ordinary story escape item is assigned this action in the pinned pack.'},
        'pendingCinematicEntry':{'firstPrayerAndPrayersTwoThroughSeven':
            'Post-cinematic continuations staged at pc5; full relocated Mr Saturn cinematic entry currently awaits a script signal in the prepared fixture. Prerequisites and production behavior remain under investigation. This is not yet a confirmed game defect.',
            'diagnosticEvidence':'_BuildScratch/battle-item-audit-dev15-pilot16-giygas/native.log'},
        'allPassed':p.returncode==0 and len(results)==len(tests) and all(r['passed'] for r in rows),
        'limits':['Source-derived assertions with actual native dispatch/continuations; no new independent original-machine oracle in this tool.',
            'Prepared handler entry contexts bypass full-turn selection, targeting, cost, AI and story-trigger ordering.',
            'Pokey and prayers eight/nine exercise full native entry; prayers one through seven enter post-cinematic pc5. Real remaining text/fade/load/swirl children execute, but staged cases do not certify skipped cinematics or complete ending.',
            'Only the player native library is executed; observer runtime hash is provenance, not separate semantic execution.',
            'Prior frozen v5 coverage retains its own runtime/library hashes and is not relabeled as testing the current runtime.',
            'Status, item and stat-width cases prepare exact callback boundaries; broader inventory, input, cost, rolling meter timing and whole-turn behavior remain outside these assertions.',
            'No owner save, game assets or ROM bytes are published in this report.'],
        'fullConversionVerified':False,'fullPlaythroughVerified':False}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cases':len(rows),'completed':len(results),'passed':sum(r['passed'] for r in rows),
        'nativeExitCode':p.returncode,'allPassed':report['allPassed'],'firstFailures':[r for r in rows if not r['passed']][:8]}))
    if not report['allPassed']:raise SystemExit(1)


if __name__=='__main__':main()
