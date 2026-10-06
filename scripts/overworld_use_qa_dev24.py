# SPDX-License-Identifier: GPL-3.0-or-later
"""Selected complete pause-menu Goods/PSI parents and real cold children.

Fixture statuses, levels and inventory are established before PM_ENTER. All
choices use actual production menus and platform D-pad/A/B input. No production
handler, selected result, post-entry effect or completion signal is replaced.
"""
import json
import copy
import sys
from pathlib import Path

import barter_delivery_qa_dev20 as barter

base = barter.base
old_source = barter.driver_source


def replace_once(s, old, new):
    if s.count(old) != 1:
        raise ValueError('Frozen driver boundary changed: ' + old[:90])
    return s.replace(old, new, 1)


C_EFFECT = r'''
static int psi_loop_member(void){
 for(int i=(int)g_mode_stack.depth-2;i>=1;i--)
  if(g_mode_stack.mode[i]==GAME_MODE_PSI_MENU)return g_mode_stack.state[i].psi_menu.exec_i;
 return -1;
}
static void effect_fixture(const char*session){
 char path[4096];snprintf(path,sizeof(path),"%s/effect-input.txt",session);
 FILE*f=fopen(path,"r");if(!f)exit(40);unsigned level,hp,pp,maxhp,maxpp,status;
 for(unsigned c=0;c<4;c++){
  if(fscanf(f,"%u %u %u %u %u",&level,&hp,&pp,&maxhp,&maxpp)!=5)exit(41);
  party_characters[c].level=level;party_characters[c].max_hp=maxhp;party_characters[c].max_pp=maxpp;
  party_characters[c].current_hp=party_characters[c].current_hp_target=hp;
  party_characters[c].current_pp=party_characters[c].current_pp_target=pp;
  for(unsigned i=0;i<7;i++){if(fscanf(f,"%u",&status)!=1)exit(42);party_characters[c].afflictions[i]=status;}
 }fclose(f);
}
static void effect_snap(const char*stage){
 printf("QA_EFFECT {\"stage\":\"%s\",\"party\":[",stage);
 for(unsigned c=0;c<4;c++){
  printf("%s{\"hp\":%u,\"hpTarget\":%u,\"pp\":%u,\"ppTarget\":%u,\"status\":[",c?",":"",party_characters[c].current_hp,party_characters[c].current_hp_target,party_characters[c].current_pp,party_characters[c].current_pp_target);
  for(unsigned i=0;i<7;i++)printf("%s%u",i?",":"",party_characters[c].afflictions[i]);printf("]}");
 }printf("],\"windowHead\":%d,\"windowTail\":%d}\n",win.window_head,win.window_tail);fflush(stdout);
}
'''


def driver_source(original):
    s = old_source(original)
    s = replace_once(s, 'static void snap(const char*stage){',
                     C_EFFECT + '\nstatic void snap(const char*stage){\n effect_snap(stage);')
    s = replace_once(s, 'transaction_fixture(argv[2]);replay(0,0,0);snap("before-entry");',
                     'transaction_fixture(argv[2]);effect_fixture(argv[2]);replay(0,0,0);snap("before-entry");')
    s = replace_once(s, 'else {ModeState text={0};if(!dt_make_child_init(&text,entry))return 8;mode_push(GAME_MODE_DISPLAY_TEXT,&text);',
                     'else {ModeState initial={0};initial.pause_menu.phase=PM_ENTER;mode_push(GAME_MODE_PAUSE_MENU,&initial);')
    s = replace_once(s, 'if(capture_kind && ((capture_kind==1&&mode==GAME_MODE_NUMBER_SELECT)',
                     'if(capture_kind && ((capture_kind==7&&mode==GAME_MODE_DETERMINE_TARGETING&&st->targeting.phase==TGT_ENTER)||(capture_kind==8&&mode==GAME_MODE_BATTLE_ACTION&&st->battle_action.pc==0)||(capture_kind==9&&mode==GAME_MODE_BATTLE_REVIVE)||(capture_kind==10&&mode==GAME_MODE_BATTLE_ACTION&&st->battle_action.pc==0&&psi_loop_member()==2)||(capture_kind==11&&mode==GAME_MODE_PSI_MENU&&st->psi_menu.phase==PS_FAIL_RESUME)||(capture_kind==1&&mode==GAME_MODE_NUMBER_SELECT)')
    s = replace_once(s, 'unsigned pick=choose();WindowInfo*w=get_window(win.current_focus_window);',
                     'unsigned pick=choose();WindowInfo*w=get_window(win.current_focus_window);if(pick>=1000&&pick!=999){unsigned wanted=pick-1000;pick=998;if(w)for(unsigned i=0;i<w->menu_count;i++)if(w->menu_items[i].userdata==wanted){pick=i;break;}if(pick==998)exit(43);}')
    s = replace_once(s, 'core.pad1_pressed=platform_input_get_pad_new();', r'''
  if(mode==GAME_MODE_BATTLE_ACTION&&st->battle_action.pc==0){
   RNGState saved=rng_state;unsigned next=rng_next_byte();rng_state=saved;
   printf("QA_ACTION {\"tableIndex\":%u,\"attacker\":%u,\"target\":%u,\"nextRandomByte\":%u}\n",st->battle_action.table_index,bt.current_attacker,bt.current_target,next);
  }
  core.pad1_pressed=platform_input_get_pad_new();''')
    return s


def main():
    output = Path(sys.argv[sys.argv.index('--output') + 1])
    cases = json.loads(Path(sys.argv[sys.argv.index('--cases') + 1]).read_text())
    by_id = {c['id']: c for c in cases}
    real_run = base.subprocess.run

    def run(command, *args, **kwargs):
        if isinstance(command, list) and len(command) == 5 and command[-1] in ('warm', 'capture', 'resume'):
            session = Path(command[2]); case = by_id[session.name]
            values = []
            for pc in case['initialParty']:
                values.extend([pc.get('level', 1), pc['hp'], pc['pp'], pc.get('maxHP', 100), pc.get('maxPP', 50), *pc['status']])
            (session / 'effect-input.txt').write_text(' '.join(map(str, values)), encoding='utf-8')
        return real_run(command, *args, **kwargs)

    base.subprocess.run = run
    barter.driver_source = driver_source
    failure = 0
    try:
        barter.main()
    except SystemExit as e:
        if e.code not in (0, 1): raise
        failure = e.code
    r = json.loads(output.read_text())
    for row in r['cases']:
        states = {e['actual']['stage']: e['actual'] for e in row['events'] if e['type'] == 'QA_EFFECT'}
        actions = [e['actual'] for e in row['events'] if e['type'] == 'QA_ACTION']
        expected_effect=copy.deepcopy(row['fixture']['expectedEffect'])
        if 'sourceGammaRevival' in row['fixture'] and actions:
            # Original SUCCESS_255 compares actual RAND byte strictly <192.
            # Peek restores the RNG state and does not consume the game draw.
            target = row['fixture']['sourceGammaRevival']
            if actions[0]['nextRandomByte'] < 192:
                expected_effect[target]['status'] = [0]*7
                expected_effect[target]['hpTarget'] = row['fixture']['initialParty'][target].get('maxHP',100)//4
            row['sourceGammaExpectation']=dict(targetIndex=target, randomByte=actions[0]['nextRandomByte'],
                                              strictSuccessThreshold=192, expectedParty=expected_effect)
        for stage, key in [('before-entry', 'expectedInitialEffect'), ('captured', 'expectedCapturedEffect'), ('after-entry', 'expectedEffect')]:
            actual = states.get(stage, {})
            for pc, expected in enumerate(expected_effect if key=='expectedEffect' else row['fixture'].get(key, [])):
                got = actual.get('party', [{}] * 4)[pc]
                for field, want in expected.items():
                    if got.get(field) != want:
                        row['errors'].append(f'Source {stage} party[{pc}].{field}: {got.get(field)} expected {want}')
        ends = [e['actual'] for e in row['events'] if e['type'] == 'QA_END']
        if not ends or ends[-1].get('planUsed') != len(row['fixture']['plan']):
            row['errors'].append('Actual source menu choice count differs')
        if 'expectedActions' in row['fixture']:
            actual = [e['actual']['tableIndex'] for e in row['events'] if e['type'] == 'QA_ACTION']
            if actual != row['fixture']['expectedActions']: row['errors'].append(f'Actual action dispatch differs: {actual}')
        if 'expectedActionCount' in row['fixture'] and len(actions) != row['fixture']['expectedActionCount']:
            row['errors'].append(f'Actual effect entry count differs: {len(actions)}')
        for wanted in row['fixture'].get('expectedMenus', []):
            menus = [e['actual'] for e in row['events'] if e['type']=='QA_MENU' and e['actual']['window']==wanted['window']]
            if not menus or [i['id'] for i in menus[0]['options']] != wanted['ids']:
                row['errors'].append('Source menu guard differs: '+str(wanted))
        for wanted in row['fixture'].get('expectedAbsentMenuIDs', []):
            menus=[e['actual'] for e in row['events'] if e['type']=='QA_MENU' and e['actual']['window']==wanted['window']]
            if not menus or wanted['id'] in [i['id'] for i in menus[0]['options']]:row['errors'].append('Source unavailable menu entry was offered: '+str(wanted))
        if states.get('after-entry',{}).get('windowHead')!=-1 or states.get('after-entry',{}).get('windowTail')!=-1:
            row['errors'].append('Full pause parent did not close the window list')
        row['passed'] = not row['errors']
    source = Path(sys.argv[sys.argv.index('--executed-source') + 1]); project = Path(sys.argv[sys.argv.index('--project') + 1])
    refs = ('src/game/text.c', 'src/game/battle_targeting.c', 'src/game/battle_psi.c', 'src/game/battle_actions.c',
            'src/game/battle_effects.c', 'src/game/overworld_spawn.c', 'src/game/inventory.c', 'src/core/mode_stack.h',
            'asm/overworld/use_item.asm', 'asm/overworld/open_menu.asm', 'asm/text/menu/overworld_psi_menu.asm',
            'asm/battle/actions/healing_alpha.asm', 'asm/battle/actions/healing_beta.asm',
            'asm/battle/actions/healing_gamma.asm', 'asm/battle/actions/healing_omega.asm', 'asm/battle/revive_target.asm',
            'asm/battle/actions/lifeup_common.asm','asm/battle/recover_hp.asm','asm/battle/set_hp.asm','asm/battle/success_255.asm')
    r.update(toolVersion='dev24-source-parent-overworld-goods-psi-effects',
             executedSourceReferences=[dict(path=p, sha256=base.helper.digest(source / p)) for p in refs if (source / p).is_file()],
             pinnedSource=[dict(path=p, sha256=base.helper.digest(project / p)) for p in ('item_configuration_table.yml', 'psi_ability_table.yml', 'ccscript/main.ccs')],
             limits=['Selected full pause-menu Goods/PSI parents with source prerequisites prepared before PM_ENTER. Actual production children, target menus and platform D-pad/A/B dispatch, without handler/result/post-entry state injection. No natural map/story/controller reachability claim.',
                     'Specified item consumption, PP targets, HP targets, status writeback and parent return only. Source refusal and no-effect consumption are distinguished from bugs. No full family, all status combinations, pixels or eventual rolling-meter settling claim.',
                     'Cold captures use production serialization at actual targeting/action/revival child states and restore in a fresh process. Observer identity recorded, but observer not separately executed. Sound requests only; audio delivery and full playthrough remain unproved.'])
    r['allPassed'] = not failure and all(row['passed'] for row in r['cases'])
    by_case = {row['fixture']['id']: row for row in r['cases']}
    parity=[]
    for row in r['cases']:
        peer_id=row['fixture'].get('warmPeer')
        if not peer_id:continue
        peer=by_case[peer_id]
        def final(row, kind):return [e['actual'] for e in row['events'] if e['type']==kind and e['actual']['stage']=='after-entry'][-1]
        a,b=final(row,'QA_EFFECT'),final(peer,'QA_EFFECT')
        ok=all(a['party'][i][k]==b['party'][i][k] for i in range(4) for k in ('hpTarget','ppTarget','status'))
        ok=ok and final(row,'QA_SNAP')['inventory']==final(peer,'QA_SNAP')['inventory'] and final(row,'QA_TRANSFER')==final(peer,'QA_TRANSFER')
        parity.append(dict(cold=row['fixture']['id'],warm=peer_id,passed=ok,scope='Exact target HP/PP, all status groups, complete inventory/pool/storage/queue after complete parent; current roller/frame counters excluded.'))
        if not ok:row['errors'].append('Warm/cold semantic continuation differs');row['passed']=False
    r['warmColdComparisons']=parity
    r['allPassed']=r['allPassed'] and all(p['passed'] for p in parity)
    output.write_text(json.dumps(r, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(cases=len(r['cases']), passed=sum(row['passed'] for row in r['cases']),
                         failures=[dict(id=row['fixture']['id'], errors=row['errors']) for row in r['cases'] if not row['passed']][:10])))
    if not r['allPassed'] and '--diagnostic' not in sys.argv: raise SystemExit(1)


if __name__ == '__main__': main()
