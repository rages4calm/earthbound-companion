# SPDX-License-Identifier: GPL-3.0-or-later
"""Complete prepared scripted encounters through real menus, turns, KO and exit."""
import argparse,collections,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
from battle_food_summon_qa_dev15 import groups_from_pack
from build_maternalbound_pack import read_pack

def driver_source(original):
 s=helper.DRIVER[:helper.DRIVER.index('static unsigned pump(void)')]
 s=s.replace('#include "game/battle.h"','#include "game/battle.h"\n#include "game/audio.h"\n#include "platform/pc_options.h"\n#include "data/event_script_data.h"')
 s+=r''' 
static unsigned steps,turns,menu_choices,action_count,ko_count,case_id;
static unsigned phase_seen[64],action_seen[320],mode_seen[128];
static struct {unsigned before,after,target,aff,hp,skip,final;unsigned exp,money;} kos[128];
static unsigned pump(void){
 steps=turns=menu_choices=action_count=ko_count=0;memset(phase_seen,0,sizeof(phase_seen));memset(action_seen,0,sizeof(action_seen));memset(mode_seen,0,sizeof(mode_seen));
 unsigned ko_depth=0,ko_index=0;
 while(g_mode_stack.depth>1 && ++steps<30000){
  core.pad1_pressed=platform_input_get_pad_new();core.pad1_held=platform_input_get_pad();core.pad1_autorepeat=core.pad1_pressed;
  unsigned top=g_mode_stack.depth-1,mode=g_mode_stack.mode[top];ModeState *state=&g_mode_stack.state[top];
  if(mode<128)mode_seen[mode]++;
  if(mode==GAME_MODE_BATTLE){unsigned phase=state->battle.phase;if(phase<64)phase_seen[phase]++;if(state->battle.turn_counter>turns)turns=state->battle.turn_counter;}
  if(mode==GAME_MODE_BATTLE_ACTION && state->battle_action.pc==0){unsigned i=state->battle_action.table_index;if(i<320)action_seen[i]++;action_count++;}
  StepResult r=mode_dispatch_step((GameMode)mode,state);
  if(mode==GAME_MODE_BATTLE_MENU && r.kind==STEP_POP && r.pop_result)menu_choices++;
  if(r.kind==STEP_PUSH && r.push_mode==GAME_MODE_BATTLE_KO){
   if(ko_count>=128)return steps;ko_depth=g_mode_stack.depth;ko_index=ko_count++;
   unsigned ti=r.push_init->battle_ko.target/sizeof(Battler);kos[ko_index].target=ti;kos[ko_index].before=bt.battlers_table[ti].id;kos[ko_index].final=enemy_config_table[kos[ko_index].before].final_action;
  }
  if(r.kind==STEP_POP && mode==GAME_MODE_BATTLE_KO && top==ko_depth){
   unsigned ti=kos[ko_index].target;Battler*b=&bt.battlers_table[ti];kos[ko_index].after=b->id;kos[ko_index].hp=b->hp_target;kos[ko_index].aff=b->afflictions[0];kos[ko_index].skip=bt.skip_death_text_and_cleanup;kos[ko_index].exp=bt.battle_exp_scratch;kos[ko_index].money=bt.battle_money_scratch;ko_depth=0;
  }
  if(r.kind==STEP_PUSH)mode_push(r.push_mode,r.push_init);
  else if(r.kind==STEP_POP)mode_pop(r.pop_result);
  else host_process_frame();
 }
 return steps;
}
int main(int argc,char**argv){
 if(argc!=4)return 2;char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 char*boot[]={"battle-full-encounter-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--redux-battle-fixture","0"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot)!=0 || !maternalbound_enabled())return 3;
 platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 4;
 game_set_fast_forward(true);audio_init();load_title_screen_script_data();
 pc_options.money_multiplier=pc_options.exp_multiplier=1;
 __typeof__(game_state)base_game=game_state;__typeof__(ow)base_ow=ow;__typeof__(dt)base_dt=dt;
 CharStruct baseline_characters[6];memcpy(baseline_characters,party_characters,sizeof(baseline_characters));
 FILE*input=fopen(argv[3],"r");if(!input)return 5;char line[256];
 while(fgets(line,sizeof(line),input)){
  unsigned v[9],n=0;for(char*p=strtok(line," \t\r\n");p&&n<9;p=strtok(NULL," \t\r\n"))v[n++]=strtoul(p,NULL,10);if(n!=9)return 6;
  char replay_path[4096];snprintf(replay_path,sizeof(replay_path),"%s/input.replay",argv[2]);pc_input_script_path=replay_path;platform_input_shutdown();if(!platform_input_init())return 9;
  game_state=base_game;ow=base_ow;dt=base_dt;memset(&bt,0,sizeof(bt));memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_NONE;
  entity_system_init();memcpy(party_characters,baseline_characters,sizeof(baseline_characters));
  memset(game_state.party_order,0,6);memset(game_state.party_members,0,6);game_state.party_npc_1=game_state.party_npc_2=0;game_state.party_npc_1_hp=game_state.party_npc_2_hp=0;
  game_state.party_count=game_state.player_controlled_party_count=v[3];game_state.current_party_members=(1u<<v[3])-1;game_state.auto_fight_enable=0;game_state.bank_balance=1000;memset(game_state.unknownC4,0,4);
  for(unsigned i=0;i<4;i++){
   CharStruct*c=&party_characters[i];game_state.party_order[i]=game_state.party_members[i]=i<v[3]?i+1:0;
   c->level=99;c->exp=0;c->max_hp=c->current_hp=c->current_hp_target=v[4];c->max_pp=c->current_pp=c->current_pp_target=300;c->current_hp_fraction=c->current_pp_fraction=0;
   memset(c->items,0,14);memset(c->equipment,0,4);memset(c->afflictions,0,7);
   c->base_offense=c->offense=v[5];c->base_defense=c->defense=255;c->base_speed=c->speed=v[6];c->base_guts=c->guts=255;c->base_luck=c->luck=255;c->base_vitality=c->vitality=c->base_iq=c->iq=255;c->miss_rate=0;
  }
  event_flag_clear(EVENT_FLAG_BUNBUN);
  if(v[1]==462){const unsigned char*tp=ASSET_DATA(ASSET_DATA_PSI_TELEPORT_DEST_TABLE_BIN);unsigned ix=maternalbound_enabled()?15:13;unsigned flag=tp[ix*31+25]+256u*tp[ix*31+26];if(v[8])event_flag_set(flag);else event_flag_clear(flag);}
  initialize_overworld_state();
  window_system_init();init_used_bg2_tile_map();text_setup_bg3();text_upload_font_tiles();text_load_window_gfx();text_load_flavour_palette(0);
  ow.debug_flag=0;ow.psi_teleport_style=ow.psi_teleport_destination=0;ow.overworld_status_suppression=v[7];ow.player_intangibility_frames=0;
  dt.instant_printing=0;case_id=v[0];rng_seed(v[2]);ModeState encounter={0};encounter.battle_scripted.phase=BS_ENTER;encounter.battle_scripted.battle_group=v[1];
  mode_push(GAME_MODE_BATTLE_SCRIPTED,&encounter);pump();
  printf("QA_ENCOUNTER {\"id\":%u,\"group\":%u,\"steps\":%u,\"depth\":%u,\"result\":%d,\"turns\":%u,\"menuChoices\":%u,\"actionCount\":%u,\"postBattleFlag\":%u,\"overworldBattleMode\":%u,\"statusSuppression\":%u,\"intangibility\":%u,\"autoFight\":%u,\"rollingDisabled\":%u,\"rollingHalf\":%u,\"metersStable\":%u,\"bank\":%u,\"depositBookkeeping\":%u,\"battleMoney\":%u,\"battleExpPerSurvivor\":%u,\"itemDrop\":%u,\"partyExp\":[",v[0],v[1],steps,g_mode_stack.depth,mode_child_result(),turns,menu_choices,action_count,bt.battle_mode_flag,ow.battle_mode,ow.overworld_status_suppression,ow.player_intangibility_frames,game_state.auto_fight_enable,bt.disable_hppp_rolling,bt.half_hppp_meter_speed,check_all_hppp_meters_stable(),(unsigned)game_state.bank_balance,(unsigned)(game_state.unknownC4[0]+256u*game_state.unknownC4[1]+65536u*game_state.unknownC4[2]+16777216u*game_state.unknownC4[3]),bt.battle_money_scratch,(unsigned)bt.battle_exp_scratch,bt.item_dropped);
  for(unsigned i=0;i<4;i++)printf("%s%u",i?",":"",(unsigned)party_characters[i].exp);printf("],\"partyStatus\":[");
  for(unsigned i=0;i<4;i++)printf("%s%u",i?",":"",party_characters[i].afflictions[0]);printf("],\"enemyStates\":[");
  for(unsigned i=8;i<BATTLER_COUNT;i++)printf("%s[%u,%u,%u,%u]",i==8?"":",",bt.battlers_table[i].id,bt.battlers_table[i].consciousness,bt.battlers_table[i].afflictions[0],bt.battlers_table[i].hp_target);printf("],\"kos\":[");
  for(unsigned i=0;i<ko_count;i++)printf("%s{\"before\":%u,\"after\":%u,\"slot\":%u,\"hp\":%u,\"aff\":%u,\"skip\":%u,\"finalAction\":%u,\"exp\":%u,\"money\":%u}",i?",":"",kos[i].before,kos[i].after,kos[i].target,kos[i].hp,kos[i].aff,kos[i].skip,kos[i].final,kos[i].exp,kos[i].money);printf("],\"actionRows\":[");unsigned count=0;
  for(unsigned i=0;i<320;i++)if(action_seen[i])printf("%s[%u,%u]",count++?",":"",i,action_seen[i]);printf("],\"battlePhases\":[");count=0;for(unsigned i=0;i<64;i++)if(phase_seen[i])printf("%s%u",count++?",":"",i);printf("]}\n");fflush(stdout);
  if(g_mode_stack.depth!=1 || steps>=30000){fprintf(stderr,"STALL group=%u top=%u phase=%u\n",v[1],g_mode_stack.mode[g_mode_stack.depth-1],g_mode_stack.state[g_mode_stack.depth-1].battle.phase);return 7;}
 }
 fclose(input);audio_shutdown();return 0;
}
'''
 # Raw C string literals above need actual C escape sequences (JSON quotes only).
 if original:s=s.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"').replace(' || !maternalbound_enabled()',' || maternalbound_enabled()')
 return s

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in('build','native-source','assets','runtime','scratch','output','project'):ap.add_argument('--'+n,type=Path,required=True)
 ap.add_argument('--executed-source',type=Path,required=True);ap.add_argument('--original',action='store_true');ap.add_argument('--groups',default='1,48,448,471');ap.add_argument('--seeds',type=int,default=1);ap.add_argument('--suppression-controls',action='store_true');ap.add_argument('--diagnostic',action='store_true');a=ap.parse_args()
 if a.scratch.exists():raise ValueError('Fresh private scratch required')
 pin=subprocess.check_output(['git','-C',str(a.project.parent),'rev-parse','HEAD'],text=True).strip()
 if pin!=helper.PIN:raise ValueError('Unreviewed pin')
 a.scratch.mkdir(parents=True);session=a.scratch/'session';session.mkdir();helper.DRIVER=driver_source(a.original);exe,build=helper.private_build(a)
 _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h');groups=groups_from_pack(assets);enemies=assets['data/enemy_configuration_table.bin'];tests=[]
 for group in map(int,a.groups.split(',')):
  if not any(n for n,e in groups[group]):raise ValueError('Empty group has no battle entry')
  for seed in range(1,a.seeds+1):tests.append(dict(group=group,seed=seed,values=[len(tests),group,seed*0x9e3779b9&0xffffffff,4,9999,255,255,0,1]))
 if a.suppression_controls:
  for seed in range(1,a.seeds+1):tests.append(dict(group=448,seed=seed,values=[len(tests),448,seed*0x9e3779b9&0xffffffff,4,9999,255,255,1,1]))
 if a.suppression_controls:
  for seed in range(1,a.seeds+1):tests.append(dict(group=462,seed=seed,values=[len(tests),462,seed*0x9e3779b9&0xffffffff,4,9999,255,255,0,0]))
 (session/'input.replay').write_text('\n'.join(str(frame)+' '+('0080' if frame%4==1 else '0000') for frame in range(120000))+'\n')
 path=a.scratch/'cases.tsv';path.write_text('\n'.join(' '.join(map(str,t['values']))for t in tests)+'\n')
 run=subprocess.run([str(exe.resolve()),str(a.assets.resolve()),str(session.resolve()),str(path.resolve())],cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=300)
 log=a.scratch/'native.log';log.write_bytes(run.stdout+run.stderr);results={}
 for line in run.stdout.decode(errors='replace').splitlines():
  if line.startswith('QA_ENCOUNTER '):r=json.loads(line[13:]);results[r['id']]=r
 rows=[]
 for i,t in enumerate(tests):
  r=results.get(i,{});errors=[]
  if not r:errors.append('Missing complete native encounter')
  else:
   expected_exp=expected_money=0
   for ko in r['kos']:
    if ko['slot']<8:continue
    data=enemies[ko['before']*94:(ko['before']+1)*94];expected_exp+=int.from_bytes(data[37:41],'little');expected_money+=int.from_bytes(data[41:43],'little')
   alive=sum(status not in(1,2)for status in r['partyStatus']);special=t['group']==462 and not t['values'][8];victory=alive>0 and not special;per=(expected_exp+alive-1)//alive if victory else expected_exp
   deposit=expected_money if victory else 0;result=0 if victory else 1
   for k,v in dict(depth=1,result=result,postBattleFlag=0,overworldBattleMode=0,statusSuppression=t['values'][7],autoFight=0,rollingDisabled=0,rollingHalf=0,metersStable=1,bank=1000+deposit,depositBookkeeping=deposit,battleMoney=expected_money,battleExpPerSurvivor=per).items():
    if r[k]!=v:errors.append(f'{k}: got{r[k]} expected{v}')
   if r['partyExp']!=[per if victory and state not in(1,2)else 0 for state in r['partyStatus']]:errors.append('EXP writeback differs from source surviving/non-diamondized split or defeat/special exclusion')
   if not r['turns']or not r['menuChoices']or not r['actionCount']:errors.append('Missing real turn/menu/action evidence')
   if t['group']==471:
    transitions=[(k['before'],k['after'],k['aff'],k['hp'])for k in r['kos']]
    if not any(x[0]in(27,174) and x[1]==83 and x[2]==0 and x[3]>0 for x in transitions):errors.append('Carbon-to-Diamond KO must preserve living new form')
    final_ids={83};todo=[83]
    while todo:
     eid=todo.pop();data=enemies[eid*94:(eid+1)*94]
     for j in range(4):
      if int.from_bytes(data[70+2*j:72+2*j],'little')==245 and data[80+j] not in final_ids:final_ids.add(data[80+j]);todo.append(data[80+j])
    if victory and not any(x[0]in final_ids and x[2]==1 for x in transitions):errors.append('Source Diamond/ENEMY_EXTENDER final form never fought/KOd')
   if victory and t['group']<448 and r['intangibility']!=120:errors.append('Ordinary scripted exit intangibility differs')
  rows.append(dict(group=t['group'],seed=t['seed'],incomingSuppression=t['values'][7],clumsyRescuePrerequisite=bool(t['values'][8])if t['group']==462 else None,observedOutcome=('victory'if r.get('result')==0 else'special-teleport'if t['group']==462 else'party-defeat'),passed=not errors,errors=errors,actual=r))
 refs=['src/game/battle.c','src/game/battle_actions.c','src/game/inventory.c','src/game/window.c','port/unix/platform/sdl2_input.c','asm/battle/ko_target.asm','asm/battle/init_scripted.asm','asm/battle/main_battle_routine.asm','asm/battle/init_common.asm','asm/battle/actions/rainbow_of_colours.asm']
 report=dict(schemaVersion=1,reviewedSourceReferences=[dict(path=p,sha256=helper.digest(a.native_source/p))for p in refs],reproductionFlags={n:str(getattr(a,n.replace('-','_')))for n in('build','native-source','assets','runtime','scratch','output','project','groups','seeds')},toolVersion='dev18-full-encounter-v9-regression',reduxRevision=pin,originalPack=a.original,runtimeSha256={n:helper.digest(a.runtime/n)for n in('player.exe','observer.exe')},assetsSha256=helper.digest(a.assets),privateBuild=build,nativeExitCode=run.returncode,nativeLogSha256=helper.digest(log),cases=rows,allPassed=run.returncode==0 and len(results)==len(tests)and all(r['passed']for r in rows),diagnostic=a.diagnostic,limits=['Prepared four-player level99/HP9999/stats255, real scripted BS_ENTER, swirl, battle constructors/AI/menus/attacks/KO/rewards/map reload/cleanup. Actual platform input replay of pulsed A feeds real dispatcher; no physical-controller/pixels/audio/story reachability certification.','Source-derived money/EXP expectations use actual KO victim IDs. Complete lifecycle mutation assertions; no independent whole original-machine encounter execution.','Actual packed Clumsy rescue flag is set for rescue cases; explicit missing-flag controls execute its failure teleport/no-reward branch. Incoming suppression1 controls must remain1 as original scripted wrapper preserves it. A-only Diamond fights can legitimately lose to reflected shield damage; defeat checks exclude rewards.', 'Observer hash provenance only. Prepared group membership/source data unchanged. Owner saves/assets/ROMs untouched.'],fullConversionVerified=False,fullPlaythroughVerified=False)
 report['executedSourceSnapshot']=str(a.executed_source);report['executedSourceReferences']=[dict(path=p,sha256=helper.digest(a.executed_source/p))for p in refs if(a.executed_source/p).is_file()]
 a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(cases=len(rows),passed=sum(r['passed']for r in rows),exit=run.returncode,firstFailures=[r for r in rows if not r['passed']][:1])))
 if not report['allPassed']and not a.diagnostic:raise SystemExit(1)
if __name__=='__main__':main()
