# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared complete Mirror/neutralization/Spy/Clumsy Robot dispatch semantics.

Immutable production library, real text and application children. Private
snapshots are compared field-by-field to source expectations; owner files are
never written. This does not certify whole turns, progression or a playthrough.
"""
import argparse,collections,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
import battle_action_catalog_qa_dev15 as previous
from build_maternalbound_pack import read_pack

FUNCTIONS=(0xC28770,0xC290C6,0xC29298,0xC2B0A1)


def driver_source(original):
    s=previous.driver_source()
    marker='static unsigned qa_function,qa_var_count,qa_var_rolls[32],qa_damage[16];'
    s=s.replace(marker,marker+r'''
static Battler party_before[BATTLER_COUNT],party_backup_before;static unsigned party_mirror_before,
    party_timer_before,party_main_index,party_text_count,party_text_pc[64],party_cnums[64];
static unsigned char party_inventory_before[4][14];
static void party_hex(const void *data,unsigned size) {
    const unsigned char *b=data;putchar('"');for(unsigned i=0;i<size;i++)printf("%02x",b[i]);putchar('"');
}
''')
    s=s.replace('unsigned v[48],n=0;', 'unsigned v[54],n=0;').replace('n<48','n<54').replace('if(n!=48)','if(n!=54)')
    s=s.replace('v[31] && v[4]!=2?FIRST_ENEMY_INDEX+1:1','v[31] && v[4]!=2?FIRST_ENEMY_INDEX+1:v[49]')
    s=s.replace('qa_var_count=0;', '''qa_var_count=0;
        bt.item_dropped=(uint16_t)v[50];
        for(unsigned p=0;p<4;p++)memset(party_characters[p].items,0,14);
        if(v[51])for(unsigned p=0;p<4;p++)for(unsigned i=0;i<14;i++)party_characters[p].items[i]=88;
        if(v[51]==2)party_characters[2].items[13]=0;
        if(v[51]==3)party_characters[0].items[13]=0;
        const uint8_t *tele=ASSET_DATA(ASSET_DATA_PSI_TELEPORT_DEST_TABLE_BIN);
        unsigned sourceFlag=read_u16_le(tele+(maternalbound_enabled()?15:13)*31+25);
        unsigned otherFlag=read_u16_le(tele+(maternalbound_enabled()?13:15)*31+25);
        event_flag_clear(sourceFlag);event_flag_clear(otherFlag);
        if(v[52])event_flag_set(sourceFlag);
        if(v[53])event_flag_set(otherFlag);
        if(v[48]) {
            battle_init_enemy_stats(&bt.battlers_table[9],7);
            battle_init_enemy_stats(&bt.battlers_table[6],7);
            bt.battlers_table[6].ally_or_enemy=0;bt.battlers_table[6].npc_id=6;
            for(unsigned i=0;i<BATTLER_COUNT;i++)if(bt.battlers_table[i].consciousness) {
                Battler *b=&bt.battlers_table[i];
                b->base_offense=11+i;b->base_defense=21+i;b->base_speed=31+i;b->base_guts=41+i;b->base_luck=51+i;
                b->offense=111+i;b->defense=121+i;b->speed=131+i;b->guts=141+i;b->luck=151+i;
                b->afflictions[6]=4;b->shield_hp=3;
            }
            bt.battlers_table[1].afflictions[0]=1;
            bt.battlers_table[2].afflictions[0]=2;
            bt.battlers_table[9].consciousness=0;
            if(v[48]>=2) {
                /* Real preceding Mirror, using an actual nonzero-rate enemy selected
                 * by the Python table review. No handler/result replacement. */
                qa_function=0xC2B0A1;
                for(unsigned attempt=1;attempt<=64 && !bt.mirror_enemy;attempt++) {
                    rng_seed(attempt);ModeState preparatory={0};
                    if(!battle_action_dispatch(qa_function,&preparatory))return 41;
                    mode_push(GAME_MODE_BATTLE_ACTION,&preparatory);
                    if(pump()>=30000)return 42;
                }
                if(!bt.mirror_enemy)return 43;
                if(v[48]==3)bt.battlers_table[3].consciousness=0;
                if(v[48]==4)bt.battlers_table[3].id=1;
                if(v[48]==5)bt.battlers_table[3].afflictions[0]=1;
            }
        }
        memcpy(party_before,bt.battlers_table,sizeof(party_before));party_backup_before=bt.mirror_battler_backup;
        party_mirror_before=bt.mirror_enemy;party_timer_before=bt.mirror_turn_timer;
        for(unsigned p=0;p<4;p++)memcpy(party_inventory_before[p],party_characters[p].items,14);
        party_text_count=0;
        ''')
    s=s.replace('action.battle_action.pc=(uint8_t)(v[32]<128?v[32]:0);','action.battle_action.pc=(uint8_t)(v[32]<128?v[32]:0);party_main_index=action.battle_action.table_index;')
    s=s.replace('if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);', '''
        if(r.kind==STEP_PUSH && r.push_mode==GAME_MODE_DISPLAY_TEXT &&
            g_mode_stack.mode[top]==GAME_MODE_BATTLE_ACTION &&
            g_mode_stack.state[top].battle_action.table_index==party_main_index) {
            if(party_text_count>=64)return 30000;
            unsigned effective_pc=pc;
            if(qa_function==0xC28770 && pc>=2 && pc!=10)
                effective_pc=g_mode_stack.state[top].battle_action.pc-1;
            party_text_pc[party_text_count]=effective_pc;party_cnums[party_text_count++]=dt.cnum;
        }
        if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);''')
    s=s.replace('        fflush(stdout);',r'''
        printf("QA_PARTY {\"id\":%u,\"mirrorBefore\":%u,\"mirrorAfter\":%u,\"timerBefore\":%u,\"timerAfter\":%u,\"dropAfter\":%u,\"targetOffsetAfter\":%u,\"flagsAfter\":%u,\"before\":[",
            v[0],party_mirror_before,bt.mirror_enemy,party_timer_before,bt.mirror_turn_timer,bt.item_dropped,bt.current_target,(unsigned)bt.battler_target_flags);
        for(unsigned i=0;i<BATTLER_COUNT;i++){if(i)putchar(',');party_hex(&party_before[i],sizeof(Battler));}
        printf("],\"after\":[");for(unsigned i=0;i<BATTLER_COUNT;i++){if(i)putchar(',');party_hex(&bt.battlers_table[i],sizeof(Battler));}
        printf("],\"backupBefore\":");party_hex(&party_backup_before,sizeof(Battler));
        printf(",\"backupAfter\":");party_hex(&bt.mirror_battler_backup,sizeof(Battler));
        printf(",\"inventoryBefore\":[");for(unsigned p=0;p<4;p++){if(p)putchar(',');party_hex(party_inventory_before[p],14);}
        printf("],\"inventoryAfter\":[");for(unsigned p=0;p<4;p++){if(p)putchar(',');party_hex(party_characters[p].items,14);}
        printf("],\"textPcs\":[");for(unsigned i=0;i<party_text_count;i++)printf("%s%u",i?",":"",party_text_pc[i]);
        printf("],\"textCnums\":[");for(unsigned i=0;i<party_text_count;i++)printf("%s%u",i?",":"",party_cnums[i]);printf("]}\n");
        fflush(stdout);''')
    if original:s=s.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"').replace(' || !maternalbound_enabled()', ' || maternalbound_enabled()')
    return s


def u16(b,o):return int.from_bytes(b[o:o+2],'little')
def put16(b,o,v):b[o:o+2]=(v&65535).to_bytes(2,'little')


def copy_mirror(dest,source):
    result=bytearray(source)
    for o,n in ((0,2),(13,1),(14,1),(16,1),(17,2),(19,2),(21,2),(23,2),(25,2),(27,2)):
        result[o:o+n]=dest[o:o+n]
    return result


def expected(test,a,enemies,original):
    f=test['function'];v=test['values'];before=[bytearray.fromhex(b)for b in a['before']];after=[bytearray(b)for b in before]
    backup=bytearray.fromhex(a['backupBefore']);mirror=a['mirrorBefore'];timer=a['timerBefore'];inv=[bytearray.fromhex(b)for b in a['inventoryBefore']]
    ai=v[49];ti=8 if v[3]else v[39]-1;target=before[ti];text=[];cnums=None;drop=v[50];flags=v[45];dest=None;special=0
    if f==0xC2B0A1:
        rate=enemies[u16(target,0)*94+93];success=target[14]!=0 and target[15]==0 and a['rolls8'][0]*100//256<rate
        if success:
            mirror=u16(target,0);timer=16;backup=before[ai];after[ai]=copy_mirror(before[ai],target)
        text=[0]
    elif f==0xC290C6:
        if mirror:
            for i,b in enumerate(after):
                if b[12] and b[14]==0 and u16(b,0)==4:
                    mirror=0;after[i]=copy_mirror(b,backup);put16(after[i],4,0);text=[0];break
        for b in after:
            if b[12] and b[29]!=1:
                for current,base in ((38,50),(40,51),(42,52),(44,53),(46,54)):put16(b,current,b[base])
                b[37]=b[35]=0
        flags=0
    elif f==0xC28770:
        text=[0,1]+([]if original else[10])+[pc for pc,o in ((2,58),(3,56),(4,57),(5,55),(6,60),(7,59))if target[o]==255]
        cnums=[u16(target,38),u16(target,40)]+([]if original else[u16(target,42)])
        # FIND_INVENTORY_SPACE2(3) checks Jeff only, not another party member.
        if target[14]==1 and drop and 0 in inv[2]:
            inv[2][inv[2].index(0)]=drop;drop=0;text.append(8)
    else:
        source_active=bool(v[52] or v[53] and test['profile'].get('sameFlag'))
        text=[0];dest=15 if source_active else 13 if original else 8;special=int(not source_active)
    wanted={'mirrorAfter':mirror,'timerAfter':timer,'dropAfter':drop,'flagsAfter':flags,'attackerRestored':1}
    if f==0xC290C6:wanted['targetOffsetAfter']=8*78
    else:wanted['targetRestored']=1
    if f==0xC29298:wanted.update(teleportStyle=3,teleportDestination=dest,specialDefeat=special)
    return wanted,after,backup,inv,text,cnums


def profiles(f,enemies):
    if f==0xC2B0A1:
        rows=[dict(name=f'actual-species-{e}',enemy=e)for e in range(1,len(enemies)//94)if int.from_bytes(enemies[e*94+33:e*94+35],'little')>0]
        rows.extend((dict(name='ally-refusal',enemy=None),dict(name='npc-refusal',enemy=7,npc=6)))
        return rows
    if f==0xC290C6:
        eligible=max(range(1,len(enemies)//94),key=lambda e:enemies[e*94+93])
        return[dict(name=name,enemy=eligible,scenario=scene)for scene,name in ((1,'unmirrored'),(2,'real-mirror'),(3,'inactive-Poo'),(4,'missing-Poo'),(5,'unconscious-Poo'))]
    if f==0xC28770:
        return[dict(name=f'res-mask-{mask}-inv-{inv}-drop-{drop}-side-{side}',enemy=7 if side else None,resmask=mask,inventory=inv,drop=drop)
            for mask in range(64)for inv in range(4)for drop in (0,88)for side in (0,1)]
    return[dict(name=f'source-flag-{s}-other-flag-{o}',enemy=146,sourceflag=s,otherflag=o)for s in(0,1)for o in(0,1)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for n in('build','native-source','assets','runtime','scratch','output','project'):parser.add_argument('--'+n,type=Path,required=True)
    parser.add_argument('--original',action='store_true');parser.add_argument('--pilot',action='store_true');parser.add_argument('--diagnostic',action='store_true');args=parser.parse_args()
    if args.scratch.exists():raise ValueError('Fresh scratch required')
    pin=subprocess.check_output(['git','-C',str(args.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=helper.PIN:raise ValueError('Unreviewed pin')
    args.scratch.mkdir(parents=True);session=args.scratch/'session';session.mkdir();helper.DRIVER=driver_source(args.original);exe,build=helper.private_build(args)
    _,_,assets=read_pack(args.assets,args.native_source/'src/data/runtime_generated/asset_ids.h');enemies=assets['data/enemy_configuration_table.bin'];table=assets['data/battle_action_table.bin']
    selected={}
    for i in range(len(table)//12):
        f=int.from_bytes(table[i*12+8:i*12+12],'little');kind=table[i*12+2]
        if f in FUNCTIONS:selected.setdefault((f,kind),i)
    if{f for f,k in selected}!=set(FUNCTIONS):raise ValueError('Catalog differs')
    tests=[]
    for(f,kind),action in selected.items():
        for p in profiles(f,enemies):
            if f==0xC29298:
                tele=assets['data/psi_teleport_dest_table.bin']
                sourceflag=u16(tele,(13 if args.original else 15)*31+25)
                otherflag=u16(tele,(15 if args.original else 13)*31+25)
                p.update(sourceFlagId=sourceflag,otherFlagId=otherflag,sameFlag=sourceflag==otherflag)
            for seed in((1,)if args.pilot else range(1,9)if f in(0xC28770,0xC2B0A1)else range(1,65)):
                mask=p.get('resmask',63);res=[255 if mask&(1<<j) else 64 for j in range(6)]
                v=[len(tests),action,seed*0x9e3779b9&0xffffffff,0 if p['enemy']is None else p['enemy']+1,
                    0,5000,100,5000,300,0,0,0,0,0,0,0,*res,20,p.get('npc',0),80,50,20,0,0,0,0,0,
                    0,1,0,0,0,0,0,1,20,20,0,0,0,0,50,0,p.get('scenario',0),3 if f in(0xC290C6,0xC2B0A1) else 2,
                    p.get('drop',0),p.get('inventory',0),p.get('sourceflag',0),p.get('otherflag',0)]
                tests.append(dict(function=f,type=kind,action=action,profile=p,seed=seed,values=v))
    path=args.scratch/'cases.tsv';path.write_text('\n'.join(' '.join(map(str,t['values']))for t in tests)+'\n')
    run=subprocess.run([str(exe.resolve()),str(args.assets.resolve()),str(session.resolve()),str(path.resolve())],cwd=session,
        env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=300)
    log=args.scratch/'native.log';log.write_bytes(run.stdout+run.stderr);results={}
    for line in run.stdout.decode(errors='replace').splitlines():
        for prefix in('QA ','QA_DETAIL ','QA_PARTY '):
            if line.startswith(prefix):r=json.loads(line[len(prefix):]);results.setdefault(r['id'],{}).update(r)
    rows=[];outcomes=collections.Counter()
    for i,t in enumerate(tests):
        a=results.get(i,{});errors=[]
        if 'before'not in a:errors.append('Missing native result')
        else:
            wanted,after,backup,inv,text,cnums=expected(t,a,enemies,args.original)
            for k,value in wanted.items():
                if a[k]!=value:errors.append(f'{k} got{a[k]} expected{value}')
            for j,b in enumerate(after):
                got=bytes.fromhex(a['after'][j])
                dif=[o for o in range(78)if got[o]!=b[o]]
                if dif:errors.append(f'battler{j} offsets{dif}')
            if bytes.fromhex(a['backupAfter'])!=backup:errors.append('Mirror backup differs')
            if[bytes.fromhex(b)for b in a['inventoryAfter']]!=inv:errors.append('Inventory differs')
            if a['textPcs']!=text:errors.append(f'Text stage order got{a["textPcs"]} expected{text}')
            if cnums is not None and a['textCnums'][:len(cnums)]!=cnums:errors.append('Spy displayed stat parameters differ')
            if a['depth']!=1 or a['steps']>=30000:errors.append('Native continuation did not finish')
            outcomes['mirror-success'if t['function']==0xC2B0A1 and a['mirrorAfter']else'dispatch-complete']+=1
        row={'function':f'{t["function"]:06X}','actionId':t['action'],'actionType':t['type'],'profile':t['profile'],'seed':t['seed'],'passed':not errors,'errors':errors}
        if errors:row['actual']=a
        rows.append(row)
    refs=['src/game/battle_actions.c','src/game/battle.c','src/game/battle_targeting.c','src/game/battle.h',
        'asm/battle/actions/spy.asm','asm/battle/actions/mirror.asm','asm/battle/copy_mirror_data.asm',
        'asm/battle/apply_neutralize_to_all.asm','asm/battle/actions/neutralize.asm','asm/battle/actions/clumsy_robot_death.asm']
    pinned=[]
    for p in('ccscript/main.ccs','ccscript/expansion/Extended_Battle_Action_Table.ccs','ccscript/expansion/expanded_spy_action.ccs','ccscript/redux/redux_changes.ccs'):
        file=args.project/p;content=subprocess.check_output(['git','-C',str(args.project.parent),'show',f'{pin}:Project/{p}'])
        if file.read_bytes().replace(b'\r\n',b'\n')!=content.replace(b'\r\n',b'\n'):raise ValueError('Pin changed')
        pinned.append(dict(path=p,sha256=helper.digest(file),matchesPinnedSource=True))
    report=dict(schemaVersion=1,toolVersion='dev16-party-effects',reduxRevision=pin,originalPack=args.original,
        runtimeSha256={n:helper.digest(args.runtime/n)for n in('player.exe','observer.exe')},assetsSha256=helper.digest(args.assets),privateBuild=build,
        nativeExitCode=run.returncode,nativeLogSha256=helper.digest(log),cases=rows,sourceReferences=[dict(path=p,sha256=helper.digest(args.native_source/p))for p in refs],
        pinnedReduxReferences=pinned,sourceReferenceRole='Separate exact source review identities from immutable executed library.',
        semanticCoverage=dict(completedCases=len(results),activeCallbacks=[f'{f:06X}'for f in FUNCTIONS],actionIds=list(selected.values()),outcomes=dict(outcomes)),
        pilot=args.pilot,diagnostic=args.diagnostic,allPassed=run.returncode==0 and len(results)==len(tests)and all(r['passed']for r in rows),
        reproductionFlags={n:str(getattr(args,n.replace('-','_')))for n in('build','native-source','assets','runtime','scratch','output','project')},
        limits=['Prepared complete callbacks, real text children and neutralization target iteration; no outer turn/AI/story or natural command-selection proof.',
            'All nonzero-HP packed enemy IDs exercise Mirror selection with normalized HP/stats. Source clone/preservation and backup are checked bytewise; full art/input/audio/timer expiration remain unevaluated.',
            'Neutralization includes a real preceding successful Mirror and distinct inactive/missing/unconscious Poo controls; these are constructed callback prerequisites, not owner saves or natural encounter proof.',
            'Spy checks all64 elemental resistance masks, Jeff inventory/full/lastslot/other-space controls, zero/nonzero drops and ordered Original/Redux stat text parameters; no arbitrary item drop catalog or rendered wording proof.',
            'Clumsy Robot checks exact packed source event flag versus the other profile entry flag; teleport request state is asserted, not complete post-battle map transition.',
            'Source-derived expectations, not independent complete machine actions. Only player production library executes; observer hash is provenance.',
            'Successful detailed state snapshots remain in hashed private logs. No owner ROM, assets, dialogue or save payload published. Full progression/randomizer remains untested.'],
        fullConversionVerified=False,fullPlaythroughVerified=False)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(cases=len(rows),completed=len(results),passed=sum(r['passed']for r in rows),nativeExitCode=run.returncode,allPassed=report['allPassed'],outcomes=dict(outcomes),firstFailures=[r for r in rows if not r['passed']][:2])))
    if not report['allPassed']and not args.diagnostic:raise SystemExit(1)


if __name__=='__main__':main()
