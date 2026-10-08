# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared evolving scripted battles, real menus, source AI and damage children."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import battle_full_encounter_qa_dev18 as old
import battle_action_catalog_qa as helper
import equipment_private_build_dev27 as builder
from battle_evolving_contracts_dev31 import ai_checks,source_review
from transaction_menu_replay_dev20 import C_SOURCE as MENU_REPLAY
from battle_food_summon_qa_dev15 import groups_from_pack
from build_maternalbound_pack import read_pack


C_EXTRA=r'''
static char replay_path[4096];
static unsigned defend_rounds,capture_round,captured,menu_depth;
static unsigned turn_now(void){
 for(int i=(int)g_mode_stack.depth-1;i>=0;i--)if(g_mode_stack.mode[i]==GAME_MODE_BATTLE)return g_mode_stack.state[i].battle.turn_counter;
 return 0;
}
static void replay(unsigned direction,unsigned moves,unsigned cancel){
 FILE*f=fopen(replay_path,"w");if(!f)exit(80);
 for(unsigned frame=0;frame<100000;frame++){unsigned key=0;
  if(frame>=5&&frame<5+moves*16&&(frame-5)%16==0)key=direction;
  else if(frame>=5+moves*16&&(frame-5-moves*16)%16==0)key=cancel?PAD_B:PAD_A;
  fprintf(f,"%u %04x\n",frame,key);
 }fclose(f);pc_input_script_path=replay_path;platform_input_shutdown();if(!platform_input_init())exit(81);
 core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=0;
}
static void stage_snapshot(const char*stage){
 printf("QA_STAGE {\"stage\":\"%s\",\"turn\":%u,\"depth\":%u,\"rng\":[%u,%u],\"party\":[",stage,turn_now(),g_mode_stack.depth,rng_state.a,rng_state.b);
 for(unsigned i=0;i<4;i++){CharStruct*c=&party_characters[i];printf("%s[%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u]",i?",":"",c->current_hp_target,c->current_pp_target,c->afflictions[0],c->afflictions[1],c->afflictions[2],c->afflictions[3],c->afflictions[4],c->afflictions[5],c->afflictions[6],c->guts,c->offense,c->defense);}
 printf("],\"aiCursors\":[");for(unsigned i=8;i<BATTLER_COUNT;i++)printf("%s%u",i==8?"":",",(unsigned)bt.redux_enemy_ai_cursor[i]);printf("]}\n");fflush(stdout);
}
'''


def driver_source(original):
    s=old.driver_source(original).replace('30000','200000')
    s=s.replace('#include "game/battle.h"', '#include "game/battle.h"\n#include "core/log.h"')
    marker='static unsigned steps,turns,menu_choices,action_count,ko_count,case_id;'
    s=s.replace(marker,C_EXTRA+MENU_REPLAY+'\n'+marker)
    s=s.replace('unsigned ko_depth=0,ko_index=0;','unsigned ko_depth=0,ko_index=0,ai_turn=0,ai_input_turn=0,resist_depth=0;unsigned resistance_expected=0;menu_depth=0;')
    needle='StepResult r=mode_dispatch_step((GameMode)mode,state);'
    insertion=r'''
  if(capture_round && mode==GAME_MODE_BATTLE_MENU && state->battle_menu.phase==BM_ENTER && turn_now()>=capture_round){
   host_request_capture();host_root_boundary();if(host_capture_status()!=HOST_CAPTURE_COMMITTED)exit(82);
   captured=1;stage_snapshot("captured");return steps;
  }
  if(mode==GAME_MODE_SELECTION_MENU && !menu_depth){
   WindowInfo*w=get_window(win.current_focus_window);if(!w||!w->menu_count)exit(83);
   unsigned wanted=1;unsigned parent=top?g_mode_stack.mode[top-1]:0;
   if(parent==GAME_MODE_BATTLE_MENU && g_mode_stack.state[top-1].battle_menu.phase==BM_MAIN_RESULT)
    wanted=turn_now()<=defend_rounds?5:1;
   unsigned pick=UINT16_MAX;for(unsigned i=0;i<w->menu_count;i++)if(w->menu_items[i].userdata==wanted){pick=i;break;}
   if(pick==UINT16_MAX)exit(84);unsigned initial=win.restore_menu_backup?win.menu_backup_selected_option:w->selected_option;if(initial>=w->menu_count)initial=0;
   printf("QA_CHOICE {\"turn\":%u,\"window\":%u,\"userdata\":%u}\n",turn_now(),win.current_focus_window,wanted);fflush(stdout);
   replay_menu(w,pick,initial);menu_depth=g_mode_stack.depth;
  }
  if(mode==GAME_MODE_BATTLE_CALC && state->battle_calc.pc==0 && state->battle_calc.kind==BC_RESIST_DAMAGE && !resist_depth){
   Battler*t=battler_from_offset(bt.current_target),*a=battler_from_offset(bt.current_attacker);unsigned amount=state->battle_calc.arg0,modifier=state->battle_calc.arg1;
   unsigned damage=(int16_t)amount<0?0:amount;if(modifier<255)damage=damage*modifier/256;
   unsigned type=battle_get_action_type(a->current_action);
   if(t->consciousness==1 && t->afflictions[0]!=STATUS_0_UNCONSCIOUS){
    if(type==ACTION_TYPE_PHYSICAL && t->guarding)damage/=2;
    if(type==ACTION_TYPE_PHYSICAL && (t->afflictions[6]==STATUS_6_SHIELD||t->afflictions[6]==STATUS_6_SHIELD_POWER))damage/=2;
    if(!damage)damage=1;
   }
   resistance_expected=damage;resist_depth=g_mode_stack.depth;
   printf("QA_RESIST_INPUT {\"turn\":%u,\"attacker\":%u,\"target\":%u,\"action\":%u,\"raw\":%u,\"modifier\":%u,\"guarding\":%u,\"shield\":%u,\"targetHP\":%u,\"expectedReturn\":%u}\n",turn_now(),bt.current_attacker/sizeof(Battler),bt.current_target/sizeof(Battler),a->current_action,amount,modifier,t->guarding,t->afflictions[6],t->hp_target,damage);fflush(stdout);
  }
  if(mode==GAME_MODE_BATTLE_ACTION && state->battle_action.pc==0){
   printf("QA_ACTOR {\"turn\":%u,\"actor\":%u,\"id\":%u,\"action\":%u,\"target\":%u,\"targetFlags\":%u,\"reflected\":%u}\n",turn_now(),bt.current_attacker/sizeof(Battler),battler_from_offset(bt.current_attacker)->id,battler_from_offset(bt.current_attacker)->current_action,bt.current_target/sizeof(Battler),(unsigned)bt.battler_target_flags,bt.damage_is_reflected);fflush(stdout);
  }
  if(mode==GAME_MODE_BATTLE && state->battle.phase==BTL_ENEMY_AI && state->battle.turn_counter>ai_input_turn){
   ai_input_turn=state->battle.turn_counter;
   printf("QA_AI_INPUT {\"turn\":%u,\"rng\":[%u,%u],\"enemies\":[",turn_now(),rng_state.a,rng_state.b);
   for(unsigned i=8;i<BATTLER_COUNT;i++){Battler*b=&bt.battlers_table[i];printf("%s[%u,%u,%u,%u,%u,%u]",i==8?"":",",b->id,b->consciousness,b->hp_target,b->pp_target,b->action_order_var,(unsigned)bt.redux_enemy_ai_cursor[i]);}
   printf("]}\n");fflush(stdout);
  }
  StepResult r=mode_dispatch_step((GameMode)mode,state);
  if(mode==GAME_MODE_BATTLE && state->battle.turn_counter>ai_turn && state->battle.phase>=BTL_EXEC_SETUP && state->battle.phase<=BTL_TARGET_POST){
   ai_turn=state->battle.turn_counter;printf("QA_AI {\"turn\":%u,\"enemies\":[",ai_turn);
   for(unsigned i=8;i<BATTLER_COUNT;i++){Battler*b=&bt.battlers_table[i];printf("%s[%u,%u,%u,%u,%u,%u,%u]",i==8?"":",",b->id,b->consciousness,b->hp_target,b->pp_target,b->current_action,b->current_action_argument,b->current_target);}
   printf("]}\n");fflush(stdout);
  }
  if(mode==GAME_MODE_SELECTION_MENU && r.kind==STEP_POP)menu_depth=0;
  if(mode==GAME_MODE_BATTLE_CALC && r.kind==STEP_POP && g_mode_stack.depth==resist_depth){
   printf("QA_RESIST_RETURN {\"turn\":%u,\"actual\":%d,\"expected\":%u}\n",turn_now(),r.pop_result,resistance_expected);fflush(stdout);resist_depth=0;
  }
'''
    if s.count(needle)!=1:raise ValueError('Frozen step boundary changed')
    s=s.replace(needle,insertion)
    s=s.replace('if(argc!=4)return 2;','if(argc!=5)return 2;').replace('unsigned v[9],n=0;','unsigned v[17],n=0;').replace('n<9','n<17').replace('if(n!=9)','if(n!=17)')
    s=s.replace('char replay_path[4096];snprintf(replay_path','snprintf(replay_path')
    s=s.replace('c->level=99;c->exp=0;','c->level=v[9];c->exp=0;').replace('current_pp_target=300','current_pp_target=50')
    s=s.replace('c->base_defense=c->defense=255','c->base_defense=c->defense=v[10]').replace('c->base_guts=c->guts=255','c->base_guts=c->guts=v[11]').replace('c->base_luck=c->luck=255','c->base_luck=c->luck=v[12]')
    s=s.replace('c->base_vitality=c->vitality=c->base_iq=c->iq=255','c->base_vitality=c->vitality=c->base_iq=c->iq=20')
    s=s.replace('event_flag_clear(EVENT_FLAG_BUNBUN);','event_flag_clear(EVENT_FLAG_BUNBUN);if(v[14])give_item_to_character(1,1);if(v[15])party_characters[0].afflictions[0]=v[15];')
    s=s.replace('platform_max_frames=0;', 'verbose_level=0;platform_max_frames=0;')
    s=s.replace('mode_push(GAME_MODE_BATTLE_SCRIPTED,&encounter);pump();',r'''
  defend_rounds=v[13];capture_round=strcmp(argv[4],"capture")==0?v[16]:0;captured=0;
  if(strcmp(argv[4],"resume")==0){host_request_load();host_root_boundary();if(host_capture_status()!=HOST_CAPTURE_COMMITTED)return 85;stage_snapshot("cold-loaded");}
  else {mode_push(GAME_MODE_BATTLE_SCRIPTED,&encounter);replay(0,0,0);}
  pump();if(captured){audio_shutdown();fclose(input);return 0;}
''')
    s=s.replace('  if(g_mode_stack.depth!=1 || steps>=200000)', '  stage_snapshot("after-encounter");\n  if(g_mode_stack.depth!=1 || steps>=200000)')
    return s


def fixtures(pilot=False):
    rows=[]
    definitions=[('robot-cycle',449,1,300,20,15,22,4,0),('frank-guts',448,1,250,15,12,25,3,0),
                 ('carpainter-badge',454,1,400,35,25,70,4,1),('carpainter-no-badge',454,1,400,35,25,70,4,0),
                 ('digger-shield',459,4,500,70,30,90,3,0),('shroom-status',465,4,600,160,30,100,4,0),
                 ('kraken-active-ai',467,4,1000,100,70,130,4,0),('magikraken-active-ai',473,4,1000,180,70,130,4,0),
                 ('carbon-diamond',471,4,1800,180,70,160,3,0)]
    for name,group,party,hp,off,speed,defense,defend,badge in(definitions[:1]if pilot else definitions):
        for seed in((1,)if pilot else(1,2,3)):
            row=dict(id=name+'-seed'+str(seed),group=group,seed=seed,values=[len(rows),group,seed*0x9e3779b9&0xffffffff,party,hp,off,speed,0,1,20,defense,8,15,defend,badge,0,0],
                     sourceContract=name,cold=False)
            rows.append(row)
        cold=copy.deepcopy(rows[-1]);cold['id']+='-cold';cold['warmPeer']=rows[-1]['id'];cold['cold']=True;cold['values'][0]=len(rows);cold['values'][16]=2;rows.append(cold)
    return rows


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in('build','native-source','executed-source','assets','runtime','project','scratch','output','rom'):ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--original',action='store_true');ap.add_argument('--pilot',action='store_true');ap.add_argument('--diagnostic',action='store_true');a=ap.parse_args()
    if a.scratch.exists():raise ValueError('Fresh private scratch required')
    a.scratch.mkdir(parents=True);helper.DRIVER=driver_source(a.original);exe,build=builder.private_build(a)
    _,_,pack=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h');groups=groups_from_pack(pack);enemies=pack['data/enemy_configuration_table.bin']
    contracts=source_review(a.executed_source,a.project,pack,a.rom,a.original)
    tests=fixtures(a.pilot);rows=[];unsupported=[]
    if a.original:
        unsupported=[r['id'] for r in tests if r['sourceContract']=='magikraken-active-ai']
        tests=[r for r in tests if r['id'] not in unsupported]
        # Original group473 has zero-count entries, while Redux has one
        # enemy182. An empty Original group is not an equivalent encounter.
        if unsupported and groups[473]!=[(0,214),(0,34)]:raise ValueError('Original unused group473 contract changed')
    for fixture in tests:
        session=a.scratch/fixture['id'];session.mkdir();cfg=session/'case.tsv';cfg.write_text(' '.join(map(str,fixture['values']))+'\n');events=[];runs=[]
        for stage in(['capture','resume']if fixture['cold']else['warm']):
            r=subprocess.run([str(exe.resolve()),str(a.assets.resolve()),str(session.resolve()),str(cfg.resolve()),stage],cwd=session,
                             env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=180)
            log=session/(stage+'.log');log.write_bytes(r.stdout+r.stderr);runs.append(dict(stage=stage,exit=r.returncode,logSha256=helper.digest(log)))
            for line in r.stdout.decode(errors='replace').splitlines():
                if line.startswith('QA_')and' {'in line:
                    kind,value=line.split(' ',1);events.append(dict(type=kind,actual=json.loads(value)))
        final=[e['actual']for e in events if e['type']=='QA_ENCOUNTER'];errors=[]
        if any(r['exit']for r in runs)or len(final)!=1:errors.append('Native full encounter/capture/resume did not complete')
        if final:
            actual=final[-1];xp=money=0
            for ko in actual['kos']:
                if ko['slot']<8:continue
                data=enemies[ko['before']*94:(ko['before']+1)*94];xp+=int.from_bytes(data[37:41],'little');money+=int.from_bytes(data[41:43],'little')
            alive=sum(s not in(1,2)for s in actual['partyStatus'][:fixture['values'][3]]);won=alive>0;per=(xp+alive-1)//alive if won else xp;deposit=money if won else 0
            for k,v in dict(depth=1,result=0 if won else 1,postBattleFlag=0,overworldBattleMode=0,statusSuppression=0,autoFight=0,rollingDisabled=0,rollingHalf=0,metersStable=1,bank=1000+deposit,
                            depositBookkeeping=deposit,battleMoney=money,battleExpPerSurvivor=per).items():
                if actual[k]!=v:errors.append(f'{k}: got {actual[k]}, expected {v}')
            if actual['turns']<=fixture['values'][13]:errors.append('Enemy did not survive all planned defended turns')
            for event in events:
                if event['type']=='QA_RESIST_RETURN'and event['actual']['actual']!=event['actual']['expected']:errors.append('Actual resist/guard/shield child differs from source contract')
            ai=[e['actual']for e in events if e['type']=='QA_AI']
            if fixture['sourceContract']=='robot-cycle':
                sequence=[x['enemies'][0][4]for x in ai[:3]]
                if sequence!=[127,220,127]:errors.append('Source first three robot AI actions differ: '+str(sequence))
            if fixture['cold']:
                states={e['actual']['stage']:e['actual']for e in events if e['type']=='QA_STAGE'}
                left=states.get('captured',{}).copy();right=states.get('cold-loaded',{}).copy();left.pop('stage',None);right.pop('stage',None)
                if not left or left!=right:errors.append('Actual serialized turn/RNG/party/AI cursor differs after cold load')
        ai_proof=ai_checks(events,enemies,pack['data/battle_action_table.bin'])
        if any(x.get('passed')is False for x in ai_proof):errors.append('Independent selected AI/RNG/source contract mismatch')
        if fixture['cold']:
            peer=next((r for r in rows if r['fixture']['id']==fixture['warmPeer']),None)
            def endpoint(ev):
                return next((e['actual'] for e in ev if e['type']=='QA_STAGE' and e['actual']['stage']=='after-encounter'),None)
            if peer is None or endpoint(peer['events']) is None or endpoint(peer['events'])!=endpoint(events):
                errors.append('Complete warm/cold party, RNG, AI cursor and root endpoint differs')
        rows.append(dict(fixture=fixture,stages=runs,events=events,aiSourceChecks=ai_proof,passed=not errors,errors=errors))
        print(json.dumps(dict(id=fixture['id'],stages=runs,passed=not errors,errors=errors)),flush=True)
    report=dict(schemaVersion=1,toolVersion='dev31-evolving-battle-source-boundary',runtimeSha256={n:helper.digest(a.runtime/n)for n in('player.exe','observer.exe')},assetsSha256=helper.digest(a.assets),privateBuild=build,sourceContracts=contracts,
                cases=rows,allPassed=contracts['allPassed']and all(r['passed']for r in rows),pilot=a.pilot,diagnostic=a.diagnostic,unsupportedProfileCases=unsupported,
                limits=['Prepared level20 party and real BS_ENTER/turn menus/defend/AI/actions/KO/rewards/cleanup, selected source AI/damage contracts and strict warm/cold root endpoint equality. Magicant Kraken uses offense180 to avoid minimum-damage thousands-of-turn fixtures. Broader combat combinations remain unverified.',
                        'Read-only actual input/damage-child observations; no production substitution. No physical-controller/pixel/audio/natural-story/full Original machine/full playthrough proof.'])
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    if not report['allPassed']and not a.diagnostic:raise SystemExit(1)


if __name__=='__main__':main()
