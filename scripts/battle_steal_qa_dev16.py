# SPDX-License-Identifier: GPL-3.0-or-later
"""Real STEAL callback, candidate selection, item compaction and cold saves."""
import argparse,collections,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
from build_maternalbound_pack import read_pack

FUNCTION=0xC2889E
DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "core/mode_stack.h"
#include "core/math.h"
#include "core/state_dump.h"
#include "game/battle.h"
#include "game/battle_internal.h"
#include "game/game_state.h"
#include "game/inventory.h"
#include "game/overworld.h"
#include "game/maternalbound.h"
extern int eb_platform_main(int,char**);
int main(int argc,char**argv){
 if(argc!=6)return 2;unsigned redux=atoi(argv[5]);char save[4096];snprintf(save,sizeof(save),"%s/private.srm",argv[2]);
 char*boot[]={"steal-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1",redux?"--redux-battle-fixture":"--inspect-shuffle","0"};
 int count=sizeof(boot)/sizeof(boot[0]);if(!redux)count--;
 if(eb_platform_main(count,boot)||maternalbound_enabled()!=(redux!=0))return 3;
 FILE*f=fopen(argv[3],"r");if(!f)return 4;char line[2048];
 while(fgets(line,sizeof(line),f)){
  unsigned v[16],n=0;for(char*p=strtok(line," \t\r\n");p&&n<16;p=strtok(NULL," \t\r\n"))v[n++]=strtoul(p,NULL,10);if(n!=16)return 5;
  /* id/action/seed/item/targetkind/mirror/attackerkind/order/fill/owner/slot/duplicates/activeTimer/reserved/actionSlot/selection */
  if(!strcmp(argv[4],"cold")){if(!state_dump_load_slots())return 6;}
  else {
   memset(&bt,0,sizeof(bt));memset(party_characters,0,sizeof(party_characters));memset(&game_state,0,sizeof(game_state));memset(&g_mode_stack,0,sizeof(g_mode_stack));
   g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_NONE;memset(&ow,0,sizeof(ow));
   const unsigned orders[4][4]={{1,2,3,4},{4,1,2,3},{3,0,0,0},{1,2,0,0}};
   for(unsigned i=0;i<4;i++){unsigned member=orders[v[7]][i];game_state.party_order[i]=game_state.party_members[i]=member;if(member){game_state.party_count++;game_state.player_controlled_party_count++;game_state.current_party_members|=1u<<(member-1);}}
   for(unsigned i=0;i<4;i++){
    CharStruct*c=&party_characters[i];c->max_hp=c->current_hp=c->current_hp_target=999;c->level=30;c->base_offense=c->offense=80;c->base_defense=c->defense=50;
    battle_init_player_stats(i+1,&bt.battlers_table[i]);bt.battlers_table[i].action_item_slot=(uint8_t)v[14];
    if(v[8])memset(c->items,v[3]==88?89:88,14);
   }
   if(v[3]&&v[9]){party_characters[v[9]-1].items[v[10]]=(uint8_t)v[3];if(v[11])party_characters[(v[9]%4)].items[0]=(uint8_t)v[3];}
   battle_init_enemy_stats(&bt.battlers_table[8],7);bt.enemies_in_battle=1;
   unsigned attacker=v[6]==0?8:v[6]==1?3:0;bt.current_attacker=attacker*sizeof(Battler);
   unsigned target=v[4]==1?8:0;bt.current_target=target*sizeof(Battler);if(v[4]==2)bt.battlers_table[0].npc_id=5;
   bt.battlers_table[attacker].current_action=v[1];bt.battlers_table[attacker].current_action_argument=v[3];bt.mirror_enemy=v[5];
   ItemTransformSaveState timer={0};if(v[12]){timer.loaded_transformations[2]=77;timer.loaded_transformations[3]=50;timer.item_transformations_loaded=1;timer.time_until_next_item_transformation_check=17;}
   item_transform_savestate_unpack(&timer);rng_seed(v[2]);
   if(!strcmp(argv[4],"prepare")){if(!state_dump_save_slots())return 7;printf("STEAL_SAVED %u\n",v[0]);continue;}
  }
  RNGState states[5];unsigned rolls[4];states[0]=rng_state;for(unsigned i=0;i<4;i++){rolls[i]=rng_next_byte();states[i+1]=rng_state;}rng_state=states[0];
  unsigned candidates=find_stealable_items(),argument=bt.battlers_table[bt.current_attacker/sizeof(Battler)].current_action_argument;
  if(v[15]){argument=select_stealable_item();bt.battlers_table[bt.current_attacker/sizeof(Battler)].current_action_argument=argument;}
  RNGState selection=rng_state;ModeState action={0};bool resumable=battle_action_dispatch(battle_action_table[v[1]].battle_function_pointer,&action);
  ItemTransformSaveState timer={0};item_transform_savestate_pack(&timer);
  printf("QA_STEAL {\"id\":%u,\"argument\":%u,\"candidates\":%u,\"resumable\":%u,\"depth\":%u,\"selectionRng\":[%u,%u],\"afterRng\":[%u,%u],\"rngStates\":[",v[0],argument,candidates,resumable,g_mode_stack.depth,selection.a,selection.b,rng_state.a,rng_state.b);
  for(unsigned i=0;i<5;i++)printf("%s[%u,%u]",i?",":"",states[i].a,states[i].b);
  printf("],\"rolls\":[%u,%u,%u,%u],\"inventory\":[",rolls[0],rolls[1],rolls[2],rolls[3]);
  for(unsigned p=0;p<4;p++){printf("%s[",p?",":"");for(unsigned i=0;i<14;i++)printf("%s%u",i?",":"",party_characters[p].items[i]);printf("]");}
  printf("],\"timerLoaded\":%u,\"timerCheck\":%u,\"timerSlots\":[",timer.item_transformations_loaded,timer.time_until_next_item_transformation_check);
  for(unsigned i=0;i<16;i++)printf("%s%u",i?",":"",timer.loaded_transformations[i]);printf("]}\n");
 }
 fclose(f);return 0;
}
'''


def profile_rows(eligible):
    profiles=[dict(name='partial-first',owner=1),dict(name='full-last-slot',owner=1,fill=1,slot=13),
        dict(name='full-reordered-party',owner=4,fill=1,order=1),dict(name='inactive-owner',owner=1,order=2),
        dict(name='active-Jeff-only',owner=3,order=2),dict(name='duplicate-party-owners',owner=1,duplicate=1),
        dict(name='enemy-target-refusal',owner=1,target=1),dict(name='NPC-target-refusal',owner=1,target=2),
        dict(name='mirrored-Poo-refusal',owner=1,mirror=1,attacker=1),dict(name='mirrored-Ness-control',owner=1,mirror=1,attacker=2),
        dict(name='mirrored-enemy-control',owner=1,mirror=1,attacker=0),dict(name='item-absent',owner=0)]
    for item in eligible:
        for p in profiles:
            for seed in (1,7,64):yield item,p,seed
    for p in profiles:
        yield 0,p,7
    for item in (88,92):
        for order in (0,1,2):
            for action_slot in (0,1,14):
                for seed in range(1,65):
                    yield item,dict(name='real-selection',owner=1,duplicate=1,fill=1,order=order,selection=1,action_slot=action_slot),seed
    for duplicate in (0,1):
        for active in (0,1):
            for seed in range(1,65):yield 92,dict(name='egg-timer-restart',owner=1,duplicate=duplicate,active_timer=active),seed


def values(index,action,item,p,seed):
    return[index,action,seed*0x9e3779b9&0xffffffff,item,p.get('target',0),p.get('mirror',0),p.get('attacker',0),p.get('order',0),
        p.get('fill',0),p['owner'],p.get('slot',0),p.get('duplicate',0),p.get('active_timer',0),0,p.get('action_slot',0),p.get('selection',0)]


def expected(t,a,table,transform):
    item=t['item'];p=t['profile'];v=t['values'];order=[[1,2,3,4],[4,1,2,3],[3],[1,2]][p.get('order',0)]
    inv=[[89 if item==88 else 88]*14 if p.get('fill')else[0]*14 for _ in range(4)]
    if item and p['owner']:
        inv[p['owner']-1][p.get('slot',0)]=item
        if p.get('duplicate'):inv[p['owner']%4][0]=item
    candidates=[]
    for member in order:
        for slot,candidate in enumerate(inv[member-1],1):
            if slot==p.get('action_slot',0)or not candidate:continue
            record=table[candidate*39:(candidate+1)*39];cost=int.from_bytes(record[26:28],'little')
            if 0<cost<290 and record[25]&0x30==0x20:candidates.append(candidate)
    consumed=0;argument=item
    if p.get('selection'):
        if not candidates:argument=0
        elif a['rolls'][0]&128:argument=0;consumed=1
        else:argument=candidates[a['rolls'][1]*len(candidates)//256];consumed=2
    selection_consumed=consumed;removed=False
    eligible=not p.get('target',0)and not(p.get('mirror')and p.get('attacker',0)==1)and argument
    if eligible:
        for member in order:
            if argument not in inv[member-1]:continue
            slots=inv[member-1];slot=slots.index(argument);pos=slot+1
            while pos<14:
                next_item=slots[pos];slots[pos-1]=next_item
                if not next_item:break
                pos+=1
            slots[pos-1]=0;removed=True;break
    timer=[0]*16;active=int(bool(p.get('active_timer')));check=17 if active else 0
    if active:timer[2:4]=[77,50]
    if removed and table[argument*39+28]&16:
        entry=next(i for i in range(4)if transform[i*5]==argument)
        if timer[entry*4+1]or timer[entry*4+3]:active-=1
        timer[entry*4+1]=timer[entry*4+3]=0
        remaining=False
        for member in order:
            for value in inv[member-1]:
                if not value:break
                if value==argument:remaining=True;break
            if remaining:break
        if remaining:
            entry_data=transform[entry*5:entry*5+5];timer[entry*4:entry*4+4]=[entry_data[1],entry_data[2],(entry_data[2]+a['rolls'][consumed]%3-1)&255,entry_data[4]]
            consumed+=1;active+=1;check=60
    wanted={'argument':argument,'candidates':len(candidates),'inventory':inv,'resumable':0,'depth':1,
        'selectionRng':a['rngStates'][selection_consumed],'afterRng':a['rngStates'][consumed],
        'timerLoaded':active,'timerCheck':check,'timerSlots':timer}
    return[f'{k}: got {a.get(k)} expected {value}'for k,value in wanted.items()if a.get(k)!=value],removed,consumed


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ('build','native-source','assets','runtime','scratch','output','project'):parser.add_argument('--'+n,type=Path,required=True)
    parser.add_argument('--original',action='store_true');parser.add_argument('--pilot',action='store_true');parser.add_argument('--diagnostic',action='store_true');args=parser.parse_args()
    if args.scratch.exists():raise ValueError('Fresh scratch required')
    pin=subprocess.check_output(['git','-C',str(args.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=helper.PIN:raise ValueError('Unreviewed Redux revision')
    args.scratch.mkdir();helper.DRIVER=DRIVER;exe,build=helper.private_build(args)
    _,_,assets=read_pack(args.assets,args.native_source/'src/data/runtime_generated/asset_ids.h');data=assets['data/battle_action_table.bin']
    actions=[i//12 for i in range(0,len(data),12)if int.from_bytes(data[i+8:i+12],'little')==FUNCTION]
    table=assets['data/item_configuration_table.bin'];transform=assets['data/timed_item_transformation_table.bin']
    eligible=[i for i in range(len(table)//39)if 0<int.from_bytes(table[i*39+26:i*39+28],'little')<290 and table[i*39+25]&0x30==0x20]
    if not eligible or 88 not in eligible or 92 not in eligible:raise ValueError('Review changed item fixture')
    tests=[]
    for action in actions:
        for item,p,seed in profile_rows((88,92)if args.pilot else eligible):
            if args.pilot and seed not in (1,7):continue
            t={'item':item,'profile':p,'seed':seed,'actionId':action,'function':f'{FUNCTION:06X}'}
            t['values']=values(len(tests),action,item,p,seed);tests.append(t)
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy');logs=[]
    def run(cases,session,mode):
        session.mkdir(exist_ok=True);casefile=session/(mode+'.tsv');casefile.write_text('\n'.join(' '.join(map(str,t['values']))for t in cases)+'\n')
        process=subprocess.run([str(exe.resolve()),str(args.assets.resolve()),str(session.resolve()),str(casefile.resolve()),mode,str(int(not args.original))],cwd=session,env=env,capture_output=True,timeout=180)
        log=session/(mode+'.log');log.write_bytes(process.stdout+process.stderr);logs.append({'path':str(log.relative_to(args.scratch)),'sha256':helper.digest(log),'exitCode':process.returncode})
        found={}
        for line in process.stdout.decode(errors='replace').splitlines():
            if line.startswith('QA_STEAL '):a=json.loads(line[9:]);found[a['id']]=a
        return found
    actual=run(tests,args.scratch/'batch','warm');rows=[];counts=collections.Counter()
    def record(t,a,cold=False):
        errors=['Missing native trace']if a is None else expected(t,a,table,transform)[0]
        if a is not None:
            _,removed,consumed=expected(t,a,table,transform);counts['removed'if removed else'preserved']+=1;counts[f'RNG-calls-{consumed}']+=1
        row={k:v for k,v in t.items()if k!='values'};row.update(coldRestore=cold,nativeResultPresent=a is not None,passed=not errors,errors=errors)
        if errors:row['actual']=a
        rows.append(row)
    for t in tests:record(t,actual.get(t['values'][0]))
    # Each cold test loads a real private checkpoint in a separate fresh process.
    cold_cases=[(88,dict(name='cold-full-last',owner=1,fill=1,slot=13)),(88,dict(name='cold-reordered',owner=4,fill=1,order=1)),
        (88,dict(name='cold-NPC-refusal',owner=1,target=2)),(88,dict(name='cold-mirrored-Poo',owner=1,mirror=1,attacker=1)),
        (88,dict(name='cold-selection',owner=1,fill=1,duplicate=1,selection=1)),
        (92,dict(name='cold-egg-last',owner=1,active_timer=1)),(92,dict(name='cold-egg-restart',owner=1,duplicate=1,active_timer=1))]
    for index,(item,p)in enumerate(cold_cases):
        t={'function':f'{FUNCTION:06X}','actionId':actions[0],'item':item,'profile':p,'seed':7};t['values']=values(100000+index,actions[0],item,p,7)
        session=args.scratch/f'cold-{index}';run([t],session,'prepare');got=run([t],session,'cold');record(t,got.get(t['values'][0]),True)
    refs=['src/game/battle_actions.c','src/game/inventory.c','asm/battle/actions/steal.asm','asm/battle/find_stealable_items.asm',
        'asm/battle/select_stealable_item.asm','asm/misc/take_item_from_character.asm','asm/misc/take_item_from_specific_character.asm',
        'asm/misc/remove_item_from_inventory.asm','asm/inventory/start_timed_item_transformation.asm','asm/overworld/initialize_item_transformation.asm']
    report={'schemaVersion':1,'toolVersion':'dev16-steal','reduxRevision':pin,'originalPack':args.original,'assetsSha256':helper.digest(args.assets),
        'runtimeSha256':{n:helper.digest(args.runtime/n)for n in ('player.exe','observer.exe')},'privateBuild':build,'cases':rows,'nativeRuns':logs,
        'sourceReferences':[{'path':p,'sha256':helper.digest(args.native_source/p)}for p in refs],
        'sourceReferenceRole':'Current review source separately identified from immutable tested library.',
        'semanticCoverage':{'completedCases':sum(r['nativeResultPresent']for r in rows),
            'activeCallbacks':[f'{FUNCTION:06X}'],'actualActionRows':actions,'eligiblePackedItems':eligible,'outcomes':dict(counts),
            'warmCases':len(tests),'freshProcessColdCases':len(cold_cases)},
        'allPassed':all(log['exitCode']==0 for log in logs)and len(actual)==len(tests)and all(r['passed']for r in rows),
        'pilot':args.pilot,'diagnostic':args.diagnostic,
        'reproductionFlags':{k:str(getattr(args,k.replace('-','_')))for k in ('build','native-source','assets','runtime','scratch','output','project')},
        'limits':['Actual STEAL callback and optional actual source candidate selection. Caller action-description text, AI/turn and outer progression remain unevaluated.',
            'All packed eligibility item IDs exercise prepared inventory/target/mirror cases; this does not prove an entire natural enemy STEAL turn.',
            'Fresh-process tests load actual serialized private root-boundary fixtures before real dispatcher. They do not load an owner playthrough save or model every serialized battle phase.',
            'Selected egg duplicates/removal exercise real timer cancellation/restart and exact serialized RNG call counts. No complete overworld timer or encounter RNG timeline is claimed.',
            'Source-derived semantic expectations; no independent SNES machine STEAL execution. Only player library executes, observer hash is provenance.',
            'Equipment, key item pool, Teddy Bear removal and empty-slot anomalies lie outside actual eligible food/drink/condiment scope; no claim for those unused STEAL arguments.',
            'No owner ROM, asset bytes or save payload is included in public report; generated checkpoints remain isolated in private scratch.'],
        'fullConversionVerified':False,'fullPlaythroughVerified':False}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cases':len(rows),'passed':sum(r['passed']for r in rows),'allPassed':report['allPassed'],'outcomes':dict(counts),'firstFailures':[r for r in rows if not r['passed']][:2]}))
    return 0 if report['allPassed']or args.diagnostic else 1


if __name__=='__main__':raise SystemExit(main())
