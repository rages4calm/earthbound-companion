# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared full weapon/armor swap callbacks, exact packed equipment effects."""
import argparse,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
import battle_action_catalog_qa_dev15 as previous
from build_maternalbound_pack import read_pack

FUNCTIONS=(0xC1DE43,0xC1E00F)

def driver_source(original):
    s=previous.driver_source();marker='static unsigned qa_function,qa_var_count,qa_var_rolls[32],qa_damage[16];'
    s=s.replace(marker,marker+r'''
static unsigned gear_char,gear_child_count,gear_child_index,gear_bash_index,gear_shoot_index;static unsigned char gear_items_before[14];
''')
    s=s.replace('FILE *input=fopen(argv[3],"r");', '''ModeState gear_probe={0};
    if(!battle_action_dispatch(0xC2859F,&gear_probe))return 41;gear_bash_index=gear_probe.battle_action.table_index;
    if(!battle_action_dispatch(0xC28740,&gear_probe))return 42;gear_shoot_index=gear_probe.battle_action.table_index;
    FILE *input=fopen(argv[3],"r");''')
    s=s.replace('unsigned v[48],n=0;','unsigned v[55],n=0;').replace('n<48','n<55').replace('if(n!=48)','if(n!=55)')
    s=s.replace('qa_var_count=0;', '''qa_var_count=0;gear_child_count=gear_child_index=0;gear_char=v[54];
        bt.current_attacker=(gear_char-1)*sizeof(Battler);a=battler_from_offset(bt.current_attacker);
        CharStruct *gear=&party_characters[gear_char-1];memset(gear->items,0,14);memset(gear->equipment,0,4);
        gear->base_guts=gear->guts=50;gear->boosted_guts=gear->boosted_speed=gear->boosted_luck=0;
        for(unsigned i=0;i<4;i++)if(v[48+i]){gear->items[i]=v[48+i];equip_item(gear_char,i+1);}
        battle_init_player_stats(gear_char,a);a->row=gear_char-1;
        a->offense+=v[52];a->defense+=v[52];a->speed+=v[52];a->guts+=v[52];a->luck+=v[52];
        a->action_item_slot=5;a->current_action=v[1];a->current_action_argument=v[30];
        gear->items[4]=v[53]?0:v[30];memcpy(gear_items_before,gear->items,14);
        original_attacker=bt.current_attacker;
        ''')
    s=s.replace('if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);', '''
        if(r.kind==STEP_PUSH && r.push_mode==GAME_MODE_BATTLE_ACTION && g_mode_stack.mode[top]==GAME_MODE_BATTLE_ACTION) {
            gear_child_count++;gear_child_index=r.push_init->battle_action.table_index;
        }
        if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);''')
    s=s.replace('        fflush(stdout);',r'''
        printf("QA_GEAR {\"id\":%u,\"stats\":[%u,%u,%u,%u,%u],\"base\":[%u,%u,%u,%u,%u],\"res\":[%u,%u,%u,%u,%u,%u],\"characterStats\":[%u,%u,%u,%u,%u],\"equipment\":[%u,%u,%u,%u],\"childCount\":%u,\"childIndex\":%u,\"childFunction\":%u,\"inventoryUnchanged\":%u,\"triangle\":%u}\n",
            v[0],a->offense,a->defense,a->speed,a->guts,a->luck,a->base_offense,a->base_defense,a->base_speed,a->base_guts,a->base_luck,
            a->fire_resist,a->freeze_resist,a->flash_resist,a->paralysis_resist,a->hypnosis_resist,a->brainshock_resist,
            gear->offense,gear->defense,gear->speed,gear->guts,gear->luck,
            gear->equipment[0],gear->equipment[1],gear->equipment[2],gear->equipment[3],gear_child_count,gear_child_index,
            !gear_child_count?0:gear_child_index==gear_bash_index?0xC2859F:gear_child_index==gear_shoot_index?0xC28740:0xffff,
            memcmp(gear->items,gear_items_before,14)==0,dt.blinking_triangle_flag);fflush(stdout);''')
    if original:s=s.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"').replace(' || !maternalbound_enabled()',' || maternalbound_enabled()')
    return s

def signed(v):return v if v<128 else v-256
def calc_stats(items,equipment,character):
    def param(slot,index):return signed(items[equipment[slot]*39+31+index])if equipment[slot]else 0
    clamp=lambda v:max(0,min(v,255))
    return [clamp(80+param(0,int(character==4))),clamp(50+sum(param(i,int(character==4))for i in(1,2,3))),clamp(20+param(1,2)),clamp(50+param(0,2)),clamp(20+param(2,2)+param(3,2))]

def calc_res(items,equipment):
    vals=[items[e*39+34]if e else 0 for e in equipment];body,arms,other=vals[1:]
    levels=[min(((body>>shift)&3)+((other>>shift)&3),3)for shift in(0,2,4,6)]
    dmg=(255,179,102,13);res=(255,128,26,0)
    return [dmg[levels[0]],dmg[levels[1]],res[levels[2]],res[levels[3]],res[arms]if arms<4 else 255,res[3-arms]if 0<=3-arms<4 else 255]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in('build','native-source','assets','runtime','scratch','output','project'):ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--original',action='store_true');ap.add_argument('--pilot',action='store_true');ap.add_argument('--diagnostic',action='store_true');a=ap.parse_args()
    if a.scratch.exists():raise ValueError('Fresh scratch required')
    pin=subprocess.check_output(['git','-C',str(a.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=helper.PIN:raise ValueError('Unreviewed pin')
    a.scratch.mkdir(parents=True);session=a.scratch/'session';session.mkdir();helper.DRIVER=driver_source(a.original);exe,build=helper.private_build(a)
    _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h');table=assets['data/battle_action_table.bin'];items=assets['data/item_configuration_table.bin'];actions={int.from_bytes(table[i+8:i+12],'little'):i//12 for i in reversed(range(0,len(table),12))};tests=[]
    for item in range(1,len(items)//39):
        category=items[item*39+25]&0x3c
        if category not in(16,20,24,28):continue
        f=0xC1DE43 if category==16 else 0xC1E00F
        for char in range(1,5):
            old=[next((e for e in range(1,len(items)//39)if items[e*39+25]&0x3c==cat and items[e*39+28]&(1<<(char-1))),0)for cat in(16,20,24,28)]
            for missing in(0,1):
                for bonus in(0,17):
                    for seed in((1,)if a.pilot else range(1,9)):
                        v=[len(tests),actions[f],seed*0x9e3779b9&0xffffffff,8,0,5000,100,5000,300,0,0,0,0,0,0,0,255,255,255,255,255,255,20,0,80,50,20,0,0,0,item,0,0,1,0,0,0,0,0,1,20,20,0,0,0,0,50,0,*old,bonus,missing,char]
                        tests.append(dict(function=f,item=item,category=category,character=char,old=old,missing=missing,bonus=bonus,seed=seed,values=v))
    path=a.scratch/'cases.tsv';path.write_text('\n'.join(' '.join(map(str,t['values']))for t in tests)+'\n')
    run=subprocess.run([str(exe.resolve()),str(a.assets.resolve()),str(session.resolve()),str(path.resolve())],cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=300)
    log=a.scratch/'native.log';log.write_bytes(run.stdout+run.stderr);results={}
    for line in run.stdout.decode(errors='replace').splitlines():
        for prefix in('QA ','QA_DETAIL ','QA_GEAR '):
            if line.startswith(prefix):r=json.loads(line[len(prefix):]);results.setdefault(r['id'],{}).update(r)
    rows=[]
    for i,t in enumerate(tests):
        r=results.get(i,{});errors=[];eqitems=t['old'].copy();eqslots=[i+1 if e else 0 for i,e in enumerate(eqitems)];success=bool(items[t['item']*39+28]&(1<<(t['character']-1)))and not t['missing'];oldstats=calc_stats(items,eqitems,t['character'])
        if success:category=(t['category']-16)//4;eqitems[category]=t['item'];eqslots[category]=5
        stats=calc_stats(items,eqitems,t['character']);res=calc_res(items,eqitems);oldres=calc_res(items,t['old']);battler=oldstats.copy()
        if success:
            for o in((0,3)if t['function']==0xC1DE43 else(1,2,4)):battler[o]=stats[o]
        wanted=dict(stats=[s+t['bonus']for s in battler],base=battler,res=res if success and t['function']==0xC1E00F else oldres,characterStats=stats,equipment=eqslots,inventoryUnchanged=1,triangle=0,childCount=int(t['function']==0xC1DE43),attackerRestored=1,targetRestored=1)
        if 'equipment'not in r:errors.append('Missing native result')
        else:
            for k,v in wanted.items():
                if r[k]!=v:errors.append(f'{k} got{r[k]} expected{v}')
            if t['function']==0xC1DE43:
                child=5 if eqitems[0]and(items[eqitems[0]*39+25]&3)==1 else 4
                expected_child=0xC28740 if child==5 else 0xC2859F
                if r['childFunction']!=expected_child:errors.append(f'Actual attack child got{r["childFunction"]:06X} expected{expected_child:06X}')
            if r['depth']!=1 or r['steps']>=30000:errors.append('Native continuation did not finish')
        rows.append(dict(function=f'{t["function"]:06X}',item=t['item'],character=t['character'],missingItem=bool(t['missing']),bonus=t['bonus'],seed=t['seed'],usable=success,passed=not errors,errors=errors,**({'actual':r}if errors else{})))
    refs=['src/game/battle_actions.c','src/game/inventory.c','src/game/battle_calc.c','asm/battle/actions/switch_weapon.asm','asm/battle/actions/switch_armor.asm','asm/misc/recalc_character_postmath_offense.asm','asm/misc/recalc_character_postmath_guts.asm','asm/misc/recalc_character_postmath_defense.asm','asm/misc/recalc_character_postmath_speed.asm','asm/misc/recalc_character_postmath_luck.asm','asm/battle/calc_resistances.asm']
    report=dict(schemaVersion=1,toolVersion='dev16-equipment',reduxRevision=pin,originalPack=a.original,runtimeSha256={n:helper.digest(a.runtime/n)for n in('player.exe','observer.exe')},assetsSha256=helper.digest(a.assets),privateBuild=build,nativeExitCode=run.returncode,nativeLogSha256=helper.digest(log),sourceReferences=[dict(path=p,sha256=helper.digest(a.native_source/p))for p in refs],cases=rows,semanticCoverage=dict(completedCases=len(results),activeCallbacks=[f'{f:06X}'for f in FUNCTIONS]),allPassed=run.returncode==0 and len(results)==len(tests)and all(r['passed']for r in rows),pilot=a.pilot,diagnostic=a.diagnostic,reproductionFlags={n:str(getattr(a,n.replace('-','_')))for n in('build','native-source','assets','runtime','scratch','output','project')},limits=['Complete prepared weapon/armor swap callbacks with real equip/recalculation/text and weapon attack child; all actual packed equippable item IDs, four characters, usability/missing controls and retained stat bonuses.','Character stats, battler bases/bonuses, resistance coefficients, equipment slot identity and inventory are source-derived assertions. No independent full original-machine equipment comparison.','Weapon child presence completes real dispatch, but child function identity, UI selection, Teddy compaction, physical input, pixels/audio and whole encounter/progression remain unevaluated.','Only player production library executes; observer hash is provenance. No owner payload/ROM/save bytes included.'],fullConversionVerified=False,fullPlaythroughVerified=False)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(cases=len(rows),passed=sum(r['passed']for r in rows),allPassed=report['allPassed'],nativeExitCode=run.returncode,firstFailures=[r for r in rows if not r['passed']][:2])))
    if not report['allPassed']and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
