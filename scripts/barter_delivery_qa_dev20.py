# SPDX-License-Identifier: GPL-3.0-or-later
"""Selected actual barter/delivery entries on an immutable native library.

Reuses the frozen input/dispatcher runner without editing it. New private-driver
code prepares source prerequisites before entry and records storage, queue and
key-pool state. It replaces no production handler or transaction result.
"""
import json, sys
from pathlib import Path
import shop_transaction_qa_dev18 as base
from transaction_menu_replay_dev20 import C_SOURCE as MENU_REPLAY

old_driver_source = base.driver_source

def driver_source(original):
    s = old_driver_source(original)
    s=s.replace('static void replay_number(unsigned value){',MENU_REPLAY+'\nstatic void replay_number(unsigned value){',1)
    needle='replay(direction,pick==999?0:moves,pick==999);'
    if s.count(needle)!=1:raise ValueError('Frozen selection replay boundary changed')
    s=s.replace(needle,'replay_menu(w,pick,initial);')
    setup = r'''
static unsigned sequence[8],sequence_count;
static void transaction_fixture(const char*session){
 char path[4096];snprintf(path,sizeof(path),"%s/transaction-input.txt",session);
 FILE*f=fopen(path,"r");if(!f)exit(20);unsigned n,item,flag,value;
 memset(key_items_pool,0,KEY_ITEMS_POOL_SIZE);memset(game_state.escargo_express_items,0,36);memset(game_state.unknownB6,0,3);memset(game_state.unknownB8,0,3);
 for(unsigned c=0;c<4;c++){memset(party_characters[c].items,0,14);memset(party_characters[c].equipment,0,4);for(unsigned j=0;j<14;j++){if(fscanf(f,"%u",&item)!=1)exit(21);if(item)give_item_to_character(c+1,item);}}
 for(unsigned j=0;j<36;j++){if(fscanf(f,"%u",&item)!=1)exit(22);if(item)escargo_express_store(item);}
 for(unsigned j=0;j<3;j++){if(fscanf(f,"%u %u",&value,&item)!=2)exit(23);if(item)queue_item_for_character(value,item);}
 if(fscanf(f,"%u",&n)!=1)exit(24);for(unsigned i=0;i<n;i++){if(fscanf(f,"%u %u",&flag,&value)!=2)exit(25);if(value)event_flag_set(flag);else event_flag_clear(flag);}
 if(fscanf(f,"%u",&n)!=1)exit(29);for(unsigned i=0;i<n;i++){if(fscanf(f,"%u",&item)!=1)exit(29);key_items_give(item);}
 if(fscanf(f,"%u",&sequence_count)!=1||sequence_count>8)exit(26);for(unsigned i=0;i<sequence_count;i++)if(fscanf(f,"%u",&sequence[i])!=1)exit(27);fclose(f);
}
'''
    s=s.replace('static void snap(const char*stage){',setup+'\nstatic void snap(const char*stage){',1)
    extra=r''' printf("QA_TRANSFER {\"stage\":\"%s\",\"flags\":[",stage);
 for(unsigned i=451;i<=464;i++)printf("%s%u",i==451?"":",",event_flag_get(i));
 printf("],\"deliveryFlags\":[%u,%u,%u,%u],\"storage\":[",event_flag_get(181),event_flag_get(645),event_flag_get(754),event_flag_get(779));
 for(unsigned i=0;i<36;i++)printf("%s%u",i?",":"",game_state.escargo_express_items[i]);printf("],\"queuedItems\":[%u,%u,%u],\"queuedSources\":[%u,%u,%u],\"keyPool\":[",game_state.unknownB6[0],game_state.unknownB6[1],game_state.unknownB6[2],game_state.unknownB8[0],game_state.unknownB8[1],game_state.unknownB8[2]);
 for(unsigned i=0;i<KEY_ITEMS_POOL_SIZE;i++)printf("%s%u",i?",":"",key_items_pool[i]);printf("]}\n");
'''
    s=s.replace('static void snap(const char*stage){\n','static void snap(const char*stage){\n'+extra,1)
    needle='g_mode_stack.mode[0]=GAME_MODE_NONE;replay(0,0,0);snap("before-entry");'
    if s.count(needle)!=1:raise ValueError('Frozen fixture boundary changed')
    s=s.replace(needle,'g_mode_stack.mode[0]=GAME_MODE_NONE;transaction_fixture(argv[2]);replay(0,0,0);snap("before-entry");')
    needle='st->selection_menu.phase==SM_SETUP&&win.current_focus_window==12)))'
    if s.count(needle)!=1:raise ValueError('Frozen capture boundary changed')
    s=s.replace(needle,'st->selection_menu.phase==SM_SETUP&&win.current_focus_window==12)||(capture_kind>=3&&mode==GAME_MODE_SELECTION_MENU&&st->selection_menu.phase==SM_SETUP&&win.current_focus_window==(capture_kind==3?2:13))))')
    needle='pump();snap("after-entry");audio_shutdown();'
    if s.count(needle)!=1:raise ValueError('Frozen completion boundary changed')
    s=s.replace(needle,'pump();for(unsigned i=0;i<sequence_count&&!captured&&g_mode_stack.depth==1;i++){snap("sequence-boundary");ModeState text={0};if(!dt_make_child_init(&text,sequence[i]))return 28;mode_push(GAME_MODE_DISPLAY_TEXT,&text);pump();}snap("after-entry");audio_shutdown();')
    return s

def main():
    output=Path(sys.argv[sys.argv.index('--output')+1])
    cases_path=Path(sys.argv[sys.argv.index('--cases')+1]);cases=json.loads(cases_path.read_text());by_id={c['id']:c for c in cases}
    real_run=base.subprocess.run
    def run(command,*args,**kwargs):
        # Only private native case launches have the session/cfg/stage layout.
        if isinstance(command,list) and len(command)==5 and command[-1] in ('warm','capture','resume'):
            session=Path(command[2]);case=by_id[session.name]
            inv=case.get('initialInventory',[[0]*14 for _ in range(4)])
            storage=case.get('initialStorage',[]);queue=case.get('initialQueue',[])
            flags={str(i):0 for i in range(451,465)};flags.update({'73':0,'770':0,'181':0,'645':0,'754':0,'779':0});flags.update(case.get('initialFlags',{}))
            values=[x for bag in inv for x in bag]+storage+[0]*(36-len(storage))
            values += [x for pair in queue for x in pair]+[0]*(6-2*len(queue))
            values += [len(flags)]+[int(x) for pair in flags.items() for x in pair]
            values += [len(case.get('initialPool',[]))]+case.get('initialPool',[])
            values += [len(case.get('entrySequence',[]))]+case.get('entrySequence',[])
            (session/'transaction-input.txt').write_text(' '.join(map(str,values)),encoding='utf-8')
        return real_run(command,*args,**kwargs)
    base.subprocess.run=run;base.driver_source=driver_source
    failure=0
    try:base.main()
    except SystemExit as e:
        if e.code not in (0,1):raise
        failure=e.code
    report=json.loads(output.read_text())
    for row in report['cases']:
        case=row['fixture'];states={e['actual']['stage']:e['actual']for e in row['events']if e['type']=='QA_TRANSFER'};after=states.get('after-entry',{})
        for field,want in case.get('expectedTransfer',{}).items():
            actual=after.get(field)
            if isinstance(want,dict):
                for index,value in want.items():
                    if actual is None or actual[int(index)]!=value:row['errors'].append(f'Source {field}[{index}] differs: {actual} expected {value}')
            elif actual!=want:row['errors'].append(f'Source {field} differs: {actual} expected {want}')
        row['passed']=not row['errors']
    report['toolVersion']='dev20-selected-barter-delivery-transactions';report['allPassed']=not failure and all(r['passed']for r in report['cases'])
    project=Path(sys.argv[sys.argv.index('--project')+1]);source=Path(sys.argv[sys.argv.index('--executed-source')+1])
    report['pinnedSource']=[dict(path=p,sha256=base.helper.digest(project/p))for p in ('ccscript/data/data_15.ccs','ccscript/data/data_17.ccs','ccscript/data/data_18.ccs','ccscript/data/data_19.ccs','ccscript/data/data_21.ccs','ccscript/data/data_36.ccs','ccscript/redux/keyitems.ccs','ccscript/definitions/items.ccs','ccscript/definitions/flags.ccs','timed_delivery_table.yml')]
    report['privateDriverSourceSha256']=base.helper.digest(Path(report['privateBuild']['driverSource'])) if 'driverSource' in report['privateBuild'] else None
    report['limits']=['Selected packed text entries and production child/menu/button/capture dispatch only. Source prerequisites prepared before entry; no post-entry inventory, register, flag or result injection. No natural NPC reachability, complete courier pathfinding, all callers, pixels or full-game proof.','Storage/queued items/key pool and all ordinary slots are actual read-only snapshots. Initial bag contents pass through production give-item classification; queue/storage fixture setup uses production APIs.','Cold captures are at actual inventory/storage menu setup, resumed through production restore in a fresh process. Sound trace proves requests only.']
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(cases=len(report['cases']),passed=sum(r['passed']for r in report['cases']),failures=[dict(id=r['fixture']['id'],errors=r['errors'])for r in report['cases']if not r['passed']][:5])))
    if not report['allPassed'] and '--diagnostic' not in sys.argv:raise SystemExit(1)

if __name__=='__main__':main()
