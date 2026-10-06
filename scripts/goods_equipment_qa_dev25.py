# SPDX-License-Identifier: GPL-3.0-or-later
"""Selected full Give/Drop/Equip parents with real menus and cold continuations."""
import json
import sys
from pathlib import Path
import overworld_use_qa_dev24 as use

base=use.base
old_source=use.driver_source
replace_once=use.replace_once

C_GEAR=r'''
static int pause_phase(void){
 for(int i=(int)g_mode_stack.depth-2;i>=1;i--)if(g_mode_stack.mode[i]==GAME_MODE_PAUSE_MENU)return g_mode_stack.state[i].pause_menu.phase;
 return -1;
}
static void gear_fixture(const char*session){
 char path[4096];snprintf(path,sizeof(path),"%s/gear-input.txt",session);FILE*f=fopen(path,"r");if(!f)exit(50);
 unsigned slot;
 for(unsigned c=0;c<4;c++){
  CharStruct*p=&party_characters[c];p->base_offense=80;p->base_defense=50;p->base_speed=20;p->base_guts=10;p->base_luck=20;
  p->boosted_guts=2;p->boosted_speed=3;p->boosted_luck=4;
  for(unsigned i=0;i<4;i++){if(fscanf(f,"%u",&slot)!=1)exit(51);if(slot)equip_item(c+1,slot);}
  recalc_character_postmath_offense(c+1);recalc_character_postmath_defense(c+1);recalc_character_postmath_speed(c+1);
  recalc_character_postmath_guts(c+1);recalc_character_postmath_luck(c+1);calc_resistances(c+1);
 }fclose(f);
}
static void gear_snap(const char*stage){
 printf("QA_GEAR {\"stage\":\"%s\",\"party\":[",stage);
 for(unsigned c=0;c<4;c++){
  CharStruct*p=&party_characters[c];printf("%s{\"equipment\":[%u,%u,%u,%u],\"stats\":[%u,%u,%u,%u,%u],\"missRate\":%u,\"resistances\":[%u,%u,%u,%u,%u]}",c?",":"",p->equipment[0],p->equipment[1],p->equipment[2],p->equipment[3],p->offense,p->defense,p->speed,p->guts,p->luck,p->miss_rate,p->fire_resist,p->freeze_resist,p->flash_resist,p->paralysis_resist,p->hypnosis_brainshock_resist);
 }printf("]}\n");fflush(stdout);
}
'''


def driver_source(original):
    s=old_source(original)
    s=replace_once(s,'static void snap(const char*stage){',C_GEAR+'\nstatic void snap(const char*stage){\n gear_snap(stage);')
    s=replace_once(s,'effect_fixture(argv[2]);replay(0,0,0);','effect_fixture(argv[2]);gear_fixture(argv[2]);replay(0,0,0);')
    s=replace_once(s,'if(capture_kind && ((capture_kind==7',
                   'if(capture_kind && ((capture_kind==12&&mode==GAME_MODE_SELECTION_MENU&&st->selection_menu.phase==SM_SETUP&&win.current_focus_window==WINDOW_EQUIP_MENU_ITEMLIST)||(capture_kind==13&&mode==GAME_MODE_CHAR_SELECT&&st->char_select.phase==CSP_INIT&&pause_phase()==PM_GIVE_CHAR_RESULT)||(capture_kind==14&&mode==GAME_MODE_DISPLAY_TEXT&&pause_phase()==PM_DROP_RESUME)||(capture_kind==15&&mode==GAME_MODE_DISPLAY_TEXT&&pause_phase()==PM_GIVE_MSG_RESUME)||(capture_kind==16&&mode==GAME_MODE_DISPLAY_TEXT&&pause_phase()==PM_USE_RESUME)||(capture_kind==7')
    return s


def main():
    output=Path(sys.argv[sys.argv.index('--output')+1]);cases=json.loads(Path(sys.argv[sys.argv.index('--cases')+1]).read_text());by_id={c['id']:c for c in cases}
    real_run=base.subprocess.run
    def run(command,*args,**kwargs):
        if isinstance(command,list)and len(command)==5 and command[-1]in('warm','capture','resume'):
            session=Path(command[2]);case=by_id[session.name];eq=case.get('initialEquipment',[[0]*4 for _ in range(4)])
            (session/'gear-input.txt').write_text(' '.join(str(x)for pc in eq for x in pc),encoding='utf-8')
        return real_run(command,*args,**kwargs)
    base.subprocess.run=run;use.driver_source=driver_source;failure=0
    try:use.main()
    except SystemExit as e:
        if e.code not in(0,1):raise
        failure=e.code
    r=json.loads(output.read_text())
    for row in r['cases']:
        states={e['actual']['stage']:e['actual']for e in row['events']if e['type']=='QA_GEAR'}
        for stage,key in [('before-entry','expectedInitialGear'),('captured','expectedCapturedGear'),('after-entry','expectedGear')]:
            want=row['fixture'].get(key)
            if want is None:continue
            for pc,expected in enumerate(want):
                got=states.get(stage,{}).get('party',[{}]*4)[pc]
                for field,v in expected.items():
                    if got.get(field)!=v:row['errors'].append(f'Source {stage} PC{pc+1} {field}: {got.get(field)} expected {v}')
        row['passed']=not row['errors']
    by_case={row['fixture']['id']:row for row in r['cases']}
    parity=[]
    for row in r['cases']:
        peer_id=row['fixture'].get('warmPeer')
        if not peer_id:continue
        def final_gear(x):return [e['actual']['party']for e in x['events']if e['type']=='QA_GEAR'and e['actual']['stage']=='after-entry'][-1]
        ok=final_gear(row)==final_gear(by_case[peer_id]);parity.append(dict(cold=row['fixture']['id'],warm=peer_id,passed=ok))
        if not ok:row['errors'].append('Warm/cold equipment/stats/resistance continuation differs');row['passed']=False
    source=Path(sys.argv[sys.argv.index('--executed-source')+1])
    refs=('src/game/text.c','src/game/inventory.c','src/game/display_text.c','src/game/display_text_cc.c','src/core/mode_stack.h',
          'asm/overworld/open_menu.asm','asm/battle/swap_item_into_equipment.asm','asm/battle/find_empty_inventory_slot.asm',
          'asm/misc/equip_item.asm','asm/inventory/equipment/equipment_change_menu.asm',
          'asm/misc/change_equipped_weapon.asm','asm/misc/recalc_character_postmath_offense.asm','asm/misc/recalc_character_postmath_defense.asm',
          'asm/misc/recalc_character_postmath_speed.asm','asm/misc/recalc_character_postmath_guts.asm','asm/misc/recalc_character_postmath_luck.asm')
    r.update(toolVersion='dev25-complete-selected-goods-equipment-parents',executedSourceReferences=[dict(path=p,sha256=base.helper.digest(source/p))for p in refs if(source/p).is_file()],
             limits=['Prepared complete pause-menu Goods Give/Drop/Equip parents and production children/menus/platform input. Initial gear is set through actual equip_item before entry; no handler/result/post-entry state injection. No natural map/controller/story reachability claim.',
                     'Selected source inventory/equipment/stat/HP/PP outcomes and specified guards/cold children only. Source oddities are reported distinctly; not every equipment, give/drop state, title/pixel/audio delivery or full playthrough proof.'])
    r['warmColdGearComparisons']=parity
    r['allPassed']=not failure and all(row['passed']for row in r['cases']);output.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(cases=len(r['cases']),passed=sum(row['passed']for row in r['cases']),failures=[dict(id=row['fixture']['id'],errors=row['errors'])for row in r['cases']if not row['passed']][:20])))
    if not r['allPassed']and '--diagnostic'not in sys.argv:raise SystemExit(1)


if __name__=='__main__':main()
