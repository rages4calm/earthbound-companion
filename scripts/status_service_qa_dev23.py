# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual packed ATM/hospital text and button transactions on a frozen library.

Prerequisite party, money and status fixtures are set before the source entry.
Five-digit input and retry plans use actual platform D-pad/A/B pulses. Production
handlers, menu results and post-entry state are never replaced or injected.
"""
import json
import sys
from pathlib import Path

import barter_delivery_qa_dev20 as barter

base = barter.base
old_source = barter.driver_source


def replace_once(s, old, new):
    if s.count(old) != 1:
        raise ValueError('Frozen driver boundary changed: ' + old[:90])
    return s.replace(old, new, 1)


C_SERVICE = r'''
static unsigned number_plan[20],number_count,number_pos,capture_number_index;
static void service_fixture(const char*session){
 char path[4096];snprintf(path,sizeof(path),"%s/service-input.txt",session);
 FILE*f=fopen(path,"r");if(!f)exit(40);unsigned bank,hp,pp,status;
 if(fscanf(f,"%u %u %u",&bank,&number_count,&capture_number_index)!=3||number_count>20)exit(41);
 game_state.bank_balance=bank;
 for(unsigned i=0;i<number_count;i++)if(fscanf(f,"%u",&number_plan[i])!=1)exit(42);
 for(unsigned c=0;c<4;c++){
  if(fscanf(f,"%u %u",&hp,&pp)!=2)exit(43);
  party_characters[c].current_hp=party_characters[c].current_hp_target=hp;
  party_characters[c].current_pp=party_characters[c].current_pp_target=pp;
  for(unsigned i=0;i<7;i++){if(fscanf(f,"%u",&status)!=1)exit(44);party_characters[c].afflictions[i]=status;}
 }fclose(f);
}
static void service_snap(const char*stage){
 const ItemConfig*card=get_item_entry(177);
 printf("QA_ATM_PREREQ {\"stage\":\"%s\",\"cardType\":%u,\"cardFlags\":%u,\"cardKeyCategory\":%u,\"poolLookup\":%u,\"anyPartyLookup\":%u}\n",stage,card?card->type:255,card?card->flags:255,is_key_item_type(177),key_items_find(177),find_item_in_inventory2(255,177));
 printf("QA_SERVICE {\"stage\":\"%s\",\"wallet\":%u,\"bank\":%u,\"numberPlanUsed\":%u,\"party\":[",stage,game_state.money_carried,game_state.bank_balance,number_pos);
 for(unsigned c=0;c<4;c++){
  printf("%s{\"hp\":%u,\"hpTarget\":%u,\"pp\":%u,\"ppTarget\":%u,\"status\":[",c?",":"",party_characters[c].current_hp,party_characters[c].current_hp_target,party_characters[c].current_pp,party_characters[c].current_pp_target);
  for(unsigned i=0;i<7;i++)printf("%s%u",i?",":"",party_characters[c].afflictions[i]);printf("]}");
 }
 printf("],\"serviceFlags\":[%u,%u,%u",event_flag_get(176),event_flag_get(177),event_flag_get(178));
 for(unsigned f=226;f<=233;f++)printf(",%u",event_flag_get(f));
 printf("],\"keyItemFlags\":[%u,%u],\"moonsideFlag\":%u}\n",event_flag_get(781),event_flag_get(784),event_flag_get(659));fflush(stdout);
}
'''

C_NUMBER = r'''
static void replay_number(unsigned value){
 FILE*f=fopen(replay_path,"w");if(!f)exit(10);
 unsigned keys[80],count=0;
 if(value!=99999999u){
  for(unsigned digit=0;digit<5;digit++){
   unsigned n=(value/(digit==0?1:digit==1?10:digit==2?100:digit==3?1000:10000))%10;
   for(unsigned j=0;j<n;j++)keys[count++]=PAD_UP;
   if(digit<4)keys[count++]=PAD_LEFT;
  }
 }
 unsigned last=10+count*8;
 for(unsigned i=0;i<100000;i++){
  unsigned key=0;
  if(i>=5&&i<5+count*8&&(i-5)%8==0)key=keys[(i-5)/8];
  else if(i>=last&&(i-last)%8==0)key=value==99999999u?PAD_B:PAD_A;
  fprintf(f,"%u %04x\n",i,key);
 }
 fclose(f);pc_input_script_path=replay_path;platform_input_shutdown();if(!platform_input_init())exit(11);
 core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=0;
}
'''


def driver_source(original):
    s = old_source(original)
    begin = s.index('static void replay_number(unsigned value){')
    end = s.index('static unsigned sequence[8]', begin)
    s = s[:begin] + C_NUMBER + s[end:]
    s = replace_once(s, 'static void snap(const char*stage){',
                     C_SERVICE + '\nstatic void snap(const char*stage){\n service_snap(stage);')
    s = replace_once(s, 'transaction_fixture(argv[2]);replay(0,0,0);snap("before-entry");',
                     'transaction_fixture(argv[2]);service_fixture(argv[2]);replay(0,0,0);snap("before-entry");')
    s = replace_once(s, 'fprintf(f,"%u",plan_pos);',
                     'fprintf(f,"%u %u",plan_pos,number_pos);')
    s = replace_once(s, 'fscanf(f,"%u",&plan_pos)!=1',
                     'fscanf(f,"%u %u",&plan_pos,&number_pos)!=2')
    needle = 'if(capture_kind && ((capture_kind==1&&mode==GAME_MODE_NUMBER_SELECT)'
    s = replace_once(s, needle,
                     'if(capture_kind && ((capture_kind==5&&mode==GAME_MODE_SELECTION_MENU&&st->selection_menu.phase==SM_SETUP&&(win.current_focus_window==WINDOW_SINGLE_CHARACTER_SELECT||(win.current_focus_window>=WINDOW_TARGETING_PROMPT&&win.current_focus_window<=WINDOW_TARGETING_PROMPT+3)))||(capture_kind==6&&mode==GAME_MODE_SELECTION_MENU&&st->selection_menu.phase==SM_SETUP&&win.current_focus_window==1)||(capture_kind==1&&!number_depth&&number_pos==capture_number_index&&mode==GAME_MODE_NUMBER_SELECT)')
    s = replace_once(s, 'number_depth=g_mode_stack.depth;numbers++;printf("QA_NUMBER',
                     'number_depth=g_mode_stack.depth;quantity=number_pos<number_count?number_plan[number_pos++]:99999999u;numbers++;printf("QA_NUMBER')
    return s


def main():
    output = Path(sys.argv[sys.argv.index('--output') + 1])
    cases = json.loads(Path(sys.argv[sys.argv.index('--cases') + 1]).read_text())
    by_id = {c['id']: c for c in cases}
    real_run = base.subprocess.run

    def run(command, *args, **kwargs):
        if isinstance(command, list) and len(command) == 5 and command[-1] in ('warm', 'capture', 'resume'):
            session = Path(command[2])
            case = by_id[session.name]
            numbers = case.get('numbers', [])
            values = [case.get('bank', 0), len(numbers), case.get('captureNumberIndex', 0), *numbers]
            for pc in case.get('initialParty', [{'hp': 100, 'pp': 50, 'status': [0] * 7} for _ in range(4)]):
                values.extend([pc['hp'], pc['pp'], *pc['status']])
            (session / 'service-input.txt').write_text(' '.join(map(str, values)), encoding='utf-8')
        return real_run(command, *args, **kwargs)

    base.subprocess.run = run
    barter.driver_source = driver_source
    failure = 0
    try:
        barter.main()
    except SystemExit as e:
        if e.code not in (0, 1):
            raise
        failure = e.code
    r = json.loads(output.read_text())
    for row in r['cases']:
        states = {e['actual']['stage']: e['actual'] for e in row['events'] if e['type'] == 'QA_SERVICE'}
        for stage, key in [('before-entry', 'expectedInitialService'), ('captured', 'expectedCapturedService'), ('after-entry', 'expectedService')]:
            actual = states.get(stage, {})
            for field, want in row['fixture'].get(key, {}).items():
                if field == 'party':
                    for pc, expected in enumerate(want):
                        got = actual.get('party', [{}] * 4)[pc]
                        for k, v in expected.items():
                            if got.get(k) != v:
                                row['errors'].append(f'Source {stage} party[{pc}].{k} mismatch: {got.get(k)} expected {v}')
                    continue
                if actual.get(field) != want:
                    row['errors'].append(f'Source {stage} {field} mismatch: {actual.get(field)} expected {want}')
        # Mode ID is resolved and recorded by fixtures, rather than assumed here.
        pops = [e['actual']['result'] for e in row['events'] if e['type'] == 'QA_POP' and e['actual']['mode'] == row['fixture'].get('numberSelectMode', -1)]
        if 'expectedNumberResults' in row['fixture'] and pops != row['fixture']['expectedNumberResults']:
            row['errors'].append(f'Actual numeric button results differ: {pops}')
        ends = [e['actual'] for e in row['events'] if e['type'] == 'QA_END']
        if not ends or ends[-1].get('planUsed') != row['fixture']['expectedPlanUsed']:
            row['errors'].append('Actual source menu choice count differs')
        for pc in row['fixture'].get('expectedAwakePCs', []):
            got = states.get('after-entry', {}).get('party', [{}] * 4)[pc]
            if not 0 < got.get('hp', 0) <= got.get('hpTarget', 0):
                row['errors'].append(f'Source revival did not wake party member {pc + 1}')
        row['passed'] = not row['errors']
    source = Path(sys.argv[sys.argv.index('--executed-source') + 1])
    project = Path(sys.argv[sys.argv.index('--project') + 1])
    refs = ('src/game/display_text_cc.c', 'src/game/display_text_menus.c', 'src/game/inventory.c',
            'src/game/game_state.c', 'src/game/window.c', 'src/game/maternalbound.c', 'src/core/mode_stack.h')
    pinned = ('ccscript/data/data_18.ccs', 'ccscript/data/data_22.ccs', 'ccscript/data/data_36.ccs',
              'ccscript/data/data_47.ccs', 'ccscript/data/data_48.ccs', 'ccscript/data/data_49.ccs',
              'ccscript/bugfixes/try_give_money.ccs', 'ccscript/bugfixes/try_deposit_money.ccs',
              'ccscript/definitions/flags.ccs')
    r.update(toolVersion='dev23-source-parent-atm-hospital-services',
             executedSourceReferences=[dict(path=p, sha256=base.helper.digest(source / p)) for p in refs],
             pinnedSource=[dict(path=p, sha256=base.helper.digest(project / p)) for p in pinned],
             limits=['Selected packed source-entry parents with source prerequisites prepared before entry; production text, children, menu and numeric button dispatch. No handler, menu result, post-entry state or completion-signal injection. No full natural NPC/story reachability claim.',
                     'Selected numeric bank/wallet and status/HP/PP outcomes only. Original controls use Original packed entries; Redux expectations use active pinned scripts. Refusal and deliberate partial treatment are distinguished from bugs.',
                     'Cold captures use production serialization at specified actual child states and restore in a fresh process. Actual sound requests are traced; sound delivery, pixels, every status combination and complete playthrough remain unproved.'])
    r['allPassed'] = not failure and all(row['passed'] for row in r['cases'])
    output.write_text(json.dumps(r, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(cases=len(r['cases']), passed=sum(row['passed'] for row in r['cases']),
                         failures=[dict(id=row['fixture']['id'], errors=row['errors']) for row in r['cases'] if not row['passed']][:10])))
    if not r['allPassed'] and '--diagnostic' not in sys.argv:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
