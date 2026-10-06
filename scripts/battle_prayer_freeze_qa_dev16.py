# SPDX-License-Identifier: GPL-3.0-or-later
"""Full prayer-command/time-freeze dispatch with source routing/effect checks."""
import argparse,collections,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
import battle_action_catalog_qa_dev15 as previous
from battle_stat_drain_qa_dev16 import decreased
from build_maternalbound_pack import read_pack

CHILDREN=(0xC2859F,0xC2AC2A,0xC2AC3E,0xC2AC68,0xC2AC51,0xC2955F,0xC29987,0xC2AC7B,0xC2AC99,0xC2ACDA,0xC29E86)
PRAYERS=(0,0,0,0,0,1,1,2,3,4,5,5,6,7,8,9)
PRAYER_FUNCTIONS=CHILDREN[1:]
FUNCTIONS=(0xC288EB,0xC2AD1B)

def driver_source(original):
    s=previous.driver_source();marker='static unsigned qa_function,qa_var_count,qa_var_rolls[32],qa_damage[16];'
    s=s.replace(marker,marker+r'''
static const unsigned flow_callbacks[]={0xC2859F,0xC2AC2A,0xC2AC3E,0xC2AC68,0xC2AC51,0xC2955F,0xC29987,0xC2AC7B,0xC2AC99,0xC2ACDA,0xC29E86};
static unsigned flow_indices[11],flow_main,flow_count,flow_active_depth,flow_rolls[8],flow_apply_count,flow_apply_mask,flow_prayer_type;
static Battler flow_before[BATTLER_COUNT];
typedef struct {unsigned callback,target,flags,disabled,rolls[8];Battler before,after;} FlowChild;
static FlowChild flow_children[24];
static void flow_hex(const void *data,unsigned size){const unsigned char*b=data;putchar('"');for(unsigned i=0;i<size;i++)printf("%02x",b[i]);putchar('"');}
''')
    s=s.replace('FILE *input=fopen(argv[3],"r");', '''for(unsigned i=0;i<11;i++){ModeState probe={0};if(!battle_action_dispatch(flow_callbacks[i],&probe))return 41;flow_indices[i]=probe.battle_action.table_index;}
    FILE *input=fopen(argv[3],"r");''')
    s=s.replace('unsigned v[48],n=0;','unsigned v[49],n=0;').replace('n<48','n<49').replace('if(n!=48)','if(n!=49)')
    s=s.replace('qa_var_count=0;', '''qa_var_count=0;flow_count=flow_active_depth=flow_apply_count=flow_apply_mask=flow_prayer_type=0;
        battle_init_enemy_stats(&bt.battlers_table[9],7);battle_init_enemy_stats(&bt.battlers_table[6],7);
        bt.battlers_table[6].npc_id=6;bt.battlers_table[6].ally_or_enemy=0;
        for(unsigned i=0;i<BATTLER_COUNT;i++)if(bt.battlers_table[i].consciousness){
            Battler *b=&bt.battlers_table[i];b->hp=b->hp_target=5000;b->hp_max=6000;b->pp=b->pp_target=100;b->pp_max=300;
            b->base_offense=b->offense=80;b->base_defense=b->defense=50;b->speed=20;b->guts=0;b->luck=20;b->exp=b->money=0;
            memset(b->afflictions,0,7);b->fire_resist=b->freeze_resist=b->flash_resist=b->paralysis_resist=b->brainshock_resist=b->hypnosis_resist=255;
            if(b->ally_or_enemy==0 && !b->npc_id){CharStruct *ch=&party_characters[b->id-1];ch->current_hp=ch->current_hp_target=5000;ch->max_hp=6000;ch->current_pp=ch->current_pp_target=100;ch->max_pp=300;memset(ch->afflictions,0,7);}
        }
        if(v[1]==65535)return 42;
        if(battle_action_table[v[1]].battle_function_pointer==0xC2AD1B){
            if(v[48]==1){bt.battlers_table[0].afflictions[0]=1;bt.battlers_table[0].hp=bt.battlers_table[0].hp_target=0;party_characters[0].afflictions[0]=1;party_characters[0].current_hp=party_characters[0].current_hp_target=0;
                bt.battlers_table[9].afflictions[0]=1;bt.battlers_table[9].hp=bt.battlers_table[9].hp_target=0;bt.battlers_table[2].afflictions[0]=2;party_characters[2].afflictions[0]=2;}
            if(v[48]==2){bt.battlers_table[9].consciousness=bt.battlers_table[3].consciousness=0;}
            if(v[48]==3)bt.battlers_table[9].npc_id=5;
        }else{
            if(v[48]==3 || v[48]==4){bt.battlers_table[8].afflictions[0]=1;bt.battlers_table[8].hp=bt.battlers_table[8].hp_target=0;}
            if(v[48]==4){bt.battlers_table[9].afflictions[0]=1;bt.battlers_table[9].hp=bt.battlers_table[9].hp_target=0;}
        }
        memcpy(flow_before,bt.battlers_table,sizeof(flow_before));
        ''')
    s=s.replace('action.battle_action.pc=(uint8_t)(v[32]<128?v[32]:0);','action.battle_action.pc=(uint8_t)(v[32]<128?v[32]:0);flow_main=action.battle_action.table_index;')
    s=s.replace('StepResult r=mode_dispatch_step', '''
        if(g_mode_stack.mode[top]==GAME_MODE_BATTLE_ACTION && g_mode_stack.state[top].battle_action.table_index==flow_main && (pc==1 || qa_function==0xC288EB && pc==0)){
            RNGState saved=rng_state;if(pc==0)(void)rng_next_byte();for(unsigned i=0;i<8;i++)flow_rolls[i]=rng_next_byte();rng_state=saved;
        }
        StepResult r=mode_dispatch_step''')
    s=s.replace('if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);', '''
        if(r.kind==STEP_PUSH && r.push_mode==GAME_MODE_BATTLE_APPLY){flow_apply_count++;flow_apply_mask=bt.battler_target_flags;flow_prayer_type=g_mode_stack.state[top].battle_action.scratch16[0];}
        if(r.kind==STEP_PUSH && r.push_mode==GAME_MODE_BATTLE_ACTION &&
            (g_mode_stack.mode[top]==GAME_MODE_BATTLE_APPLY ||
             g_mode_stack.mode[top]==GAME_MODE_BATTLE_ACTION && g_mode_stack.state[top].battle_action.table_index==flow_main)){
            if(flow_count>=24)return 30000;
            FlowChild *c=&flow_children[flow_count++];memset(c,0,sizeof(*c));
            for(unsigned i=0;i<11;i++)if(r.push_init->battle_action.table_index==flow_indices[i])c->callback=flow_callbacks[i];
            c->target=bt.current_target/sizeof(Battler);c->flags=bt.battler_target_flags;c->disabled=bt.disable_hppp_rolling;
            c->before=bt.battlers_table[c->target];
            RNGState saved=rng_state;for(unsigned i=0;i<8;i++)c->rolls[i]=rng_next_byte();rng_state=saved;
            if(qa_function==0xC288EB)memcpy(c->rolls,flow_rolls,sizeof(flow_rolls));
            flow_active_depth=g_mode_stack.depth;
        }
        if(r.kind==STEP_POP && flow_active_depth && top==flow_active_depth){flow_children[flow_count-1].after=bt.battlers_table[flow_children[flow_count-1].target];flow_active_depth=0;}
        if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);''')
    s=s.replace('        fflush(stdout);',r'''
        printf("QA_FLOW {\"id\":%u,\"applyCount\":%u,\"applyMask\":%u,\"prayerType\":%u,\"routingRoll\":%u,\"flagsAfter\":%u,\"disabledAfter\":%u,\"halfAfter\":%u,\"before\":[",v[0],flow_apply_count,flow_apply_mask,flow_prayer_type,flow_rolls[0],(unsigned)bt.battler_target_flags,bt.disable_hppp_rolling,bt.half_hppp_meter_speed);
        for(unsigned i=0;i<BATTLER_COUNT;i++){if(i)putchar(',');flow_hex(&flow_before[i],78);}printf("],\"events\":[");
        for(unsigned i=0;i<flow_count;i++){FlowChild*c=&flow_children[i];printf("%s{\"callback\":%u,\"target\":%u,\"flags\":%u,\"disabled\":%u,\"rolls\":[",i?",":"",c->callback,c->target,c->flags,c->disabled);for(unsigned j=0;j<8;j++)printf("%s%u",j?",":"",c->rolls[j]);printf("],\"before\":");flow_hex(&c->before,78);printf(",\"after\":");flow_hex(&c->after,78);printf("}");}
        printf("]}\n");fflush(stdout);''')
    if original:s=s.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"').replace(' || !maternalbound_enabled()',' || maternalbound_enabled()')
    return s

def word(b,o):return int.from_bytes(b[o:o+2],'little')
def choose(mask,roll):
    if not mask:return 0
    count=(roll&31)+1;p=0
    while count:
        p=(p+1)%20
        if mask&(1<<p):count-=1
    return 1<<p

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in('build','native-source','assets','runtime','scratch','output','project'):ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--original',action='store_true');ap.add_argument('--pilot',action='store_true');ap.add_argument('--diagnostic',action='store_true');a=ap.parse_args()
    if a.scratch.exists():raise ValueError('Fresh scratch required')
    pin=subprocess.check_output(['git','-C',str(a.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=helper.PIN:raise ValueError('Unreviewed pin')
    a.scratch.mkdir(parents=True);session=a.scratch/'session';session.mkdir();helper.DRIVER=driver_source(a.original);exe,build=helper.private_build(a)
    _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h');table=assets['data/battle_action_table.bin'];actions={int.from_bytes(table[i+8:i+12],'little'):i//12 for i in reversed(range(0,len(table),12))};tests=[]
    for f in FUNCTIONS:
        for scenario in range(4 if f==0xC2AD1B else 5):
            mask=(1<<8)if scenario==0 else(1<<8)|(1<<9)if scenario!=2 else 0
            for seed in((1,7)if a.pilot else range(1,257)):
                v=[len(tests),actions[f],seed*0x9e3779b9&0xffffffff,8,0,5000,100,6000,300,0,0,0,0,0,0,0,255,255,255,255,255,255,20,0,80,50,20,0,0,0,0,0,0,1,0,0,0,0,0,1,20,20,0,1,0,mask,50,0,scenario]
                tests.append(dict(function=f,scenario=scenario,seed=seed,values=v))
    path=a.scratch/'cases.tsv';path.write_text('\n'.join(' '.join(map(str,t['values']))for t in tests)+'\n')
    run=subprocess.run([str(exe.resolve()),str(a.assets.resolve()),str(session.resolve()),str(path.resolve())],cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=300)
    log=a.scratch/'native.log';log.write_bytes(run.stdout+run.stderr);results={}
    for line in run.stdout.decode(errors='replace').splitlines():
        for prefix in('QA ','QA_DETAIL ','QA_FLOW '):
            if line.startswith(prefix):r=json.loads(line[len(prefix):]);results.setdefault(r['id'],{}).update(r)
    rows=[];types=collections.Counter();hits=collections.Counter();effect_checks=0
    for i,t in enumerate(tests):
        r=results.get(i,{});errors=[];effect_scope=[]
        if 'events'not in r:errors.append('Missing native result')
        else:
            b=[bytes.fromhex(x)for x in r['before']];events=r['events']
            if t['function']==0xC2AD1B:
                typ=PRAYERS[r['rolls8'][0]*16//256];types[typ]+=1;mask=0
                for j,state in enumerate(b):
                    if not state[12]:continue
                    eligible=state[14]==0 or state[15]!=0 if typ<=3 else state[14]==1 if typ==4 else True
                    if typ<=4 and state[15]:eligible=False
                    if typ!=6 and state[29]==1:eligible=False
                    if eligible:mask|=1<<j
                # Golden/Rockin targeting RNG runs after its introductory text.
                if typ in(3,4):
                    mask=choose(mask,r['routingRoll'])
                if r['applyCount']!=1 or r['prayerType']!=typ or r['applyMask']!=mask:errors.append('Prayer weight/target mask differs')
                expected_order=[j for j in range(8,20)if mask&(1<<j)]+[j for j in range(8)if mask&(1<<j)]
                if[e['target']for e in events]!=expected_order or any(e['callback']!=PRAYER_FUNCTIONS[typ]for e in events):errors.append('Actual prayer child callback/order differs')
                for e in events:
                    before=bytes.fromhex(e['before']);after=bytes.fromhex(e['after']);target=before[15]==0;hp=word(before,19);pp=word(before,25);aff=list(before[29:36]);checks={}
                    if typ in(0,1,3):checks[19]=min(hp+(word(before,21)>>(4 if typ==0 else 3))if typ!=3 else hp+word(before,21)-5000,word(before,21))
                    elif typ==2:checks[25]=min(pp+max(helper.variance_reference(5,e['rolls'][:2],0),1),word(before,27))
                    elif typ==6:
                        if aff[0]==1:checks[19]=word(before,21);aff=[0]*7
                    elif typ==7:
                        if target and(aff[2]==0 or aff[2]>1):aff[2]=1
                    elif typ==8:
                        if target and(aff[3]==0 or aff[3]>1):aff[3]=1
                    elif typ==9:
                        if target and e['rolls'][0]*80//256>=word(before,46):checks[40]=decreased(word(before,40),before[51],True,a.original)
                    else:continue
                    for offset,value in checks.items():
                        if word(after,offset)!=value:errors.append(f'Prayer{typ} target{e["target"]} field{offset} got{word(after,offset)} expected{value}')
                    if list(after[29:36])!=aff:errors.append(f'Prayer{typ} status result differs')
                    effect_checks+=1
                effect_scope=['Complete child mutations checked for0,1,2,3,6,7,8,9; Rockin/Flash4,5 routing/completion only.']
            else:
                saved=t['values'][45];working=saved;wanted=r['rolls8'][0]*4//256+1;count=0
                for e in events:
                    filtered=working
                    for j,state in enumerate(b):
                        if not state[12]or state[29]in(1,2):filtered&=~(1<<j)
                    if not filtered:errors.append('Freeze child ran after source empty filtered mask');break
                    single=choose(saved,e['rolls'][0]);slot=single.bit_length()-1
                    if e['target']!=slot or e['flags']!=single or e['callback']!=0xC2859F or count==0 and e['disabled']!=1:errors.append('Freeze actual target/child/entry rolling state differs')
                    b[slot]=bytes.fromhex(e['after']);working=single;count+=1
                remaining=working
                for j,state in enumerate(b):
                    if not state[12]or state[29]in(1,2):remaining&=~(1<<j)
                if count>wanted or count<wanted and remaining:errors.append('Freeze source hit bound/termination differs')
                if r['disabledAfter']or r['halfAfter']:errors.append('Freeze rolling state not resumed')
                hits[count]+=1;effect_scope=['Complete real Bash children; source-selected targets,1..4hit bound, unfiltered saved mask and dead-stop, rolling resume. Individual Bash damage/critical mutations outside this runner.']
            if r['flagsAfter']or r['depth']!=1 or r['steps']>=30000:errors.append('Native continuation did not cleanly finish')
        rows.append(dict(function=f'{t["function"]:06X}',scenario=t['scenario'],seed=t['seed'],prayerType=r.get('prayerType')if t['function']==0xC2AD1B else None,childCount=len(r.get('events',[])),passed=not errors,errors=errors))
    refs=['src/game/battle_actions.c','src/game/battle_targeting.c','src/game/battle.c','asm/battle/actions/pray.asm','asm/data/battle/prayer_list.asm','asm/battle/actions/freeze_time.asm','asm/battle/random_targetting.asm','asm/battle/remove_status_untargettable_targets.asm','asm/battle/apply_action_to_targets.asm']
    coverage_complete=a.pilot or set(types)==set(range(10))and set(hits)==set(range(5))
    report=dict(schemaVersion=1,toolVersion='dev16-prayer-freeze',reduxRevision=pin,originalPack=a.original,runtimeSha256={n:helper.digest(a.runtime/n)for n in('player.exe','observer.exe')},assetsSha256=helper.digest(a.assets),privateBuild=build,nativeExitCode=run.returncode,nativeLogSha256=helper.digest(log),sourceReferences=[dict(path=p,sha256=helper.digest(a.native_source/p))for p in refs],cases=rows,semanticCoverage=dict(completedCases=len(results),activeCallbacks=[f'{f:06X}'for f in FUNCTIONS],prayerTypes=dict(types),freezeHits=dict(hits),prayerChildEffectChecks=effect_checks,requiredOutcomeCoverageComplete=coverage_complete),allPassed=run.returncode==0 and len(results)==len(tests)and all(r['passed']for r in rows)and coverage_complete,pilot=a.pilot,diagnostic=a.diagnostic,reproductionFlags={n:str(getattr(a,n.replace('-','_')))for n in('build','native-source','assets','runtime','scratch','output','project')},limits=['Complete prepared actual prayer/time-freeze callbacks and all real children. Exact weighted prayer selection, source masks/cyclic random selection, callback/order/termination and selected mutations; full outer battle/AI/story unevaluated.','Child effects checked for prayer0,1,2,3,6,7,8,9; Rockin/Flash4,5 mutation branches not evaluated by this runner. Real complete Rockin/Flash children do execute.','Freeze uses1..4hit count from actual source, exact original saved-mask cyclic selection including wasted dead-target hits and dead-stop. Initial rolling disable and final resume checked; rolling state during later children and individual Bash damage/critical outcomes not validated here.','Source-derived expectations, no independent complete original-machine command proof. Only player library executes; observer identity is provenance. No owner payload/save/ROM bytes included.'],fullConversionVerified=False,fullPlaythroughVerified=False)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(cases=len(rows),passed=sum(r['passed']for r in rows),allPassed=report['allPassed'],nativeExitCode=run.returncode,prayerTypes=dict(types),freezeHits=dict(hits),firstFailures=[r for r in rows if not r['passed']][:3])))
    if not report['allPassed']and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
