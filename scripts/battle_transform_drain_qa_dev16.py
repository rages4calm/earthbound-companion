# SPDX-License-Identifier: GPL-3.0-or-later
"""Complete real Rainbow transformation and HP-sucker alias callbacks."""
import argparse,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
import battle_food_summon_qa_dev15 as summon
from build_maternalbound_pack import read_pack

FUNCTIONS=(0xC2A507,0xC2C14E)

def driver_source(original):
    s=summon.driver_source(original);marker='static unsigned qa_function,qa_var_count,qa_var_rolls[32],qa_damage[16];'
    s=s.replace(marker,marker+r'''
static unsigned transform_self;static unsigned char transform_before[78];
''')
    s=s.replace('unsigned v[48],n=0;','unsigned v[51],n=0;').replace('n<48','n<51').replace('if(n!=48)','if(n!=51)')
    s=s.replace('qa_var_count=0;', '''qa_var_count=0;transform_self=v[48];
        if(v[4]==3){a->sprite_x=v[49];a->sprite_y=v[50];memset(a->afflictions,7,7);bt.redux_enemy_ai_cursor[8]=123;}
        else {
            a->hp=a->hp_target=v[49];a->hp_max=999;
            if(a->ally_or_enemy==0){party_characters[a->id-1].current_hp=party_characters[a->id-1].current_hp_target=v[49];party_characters[a->id-1].max_hp=999;}
            if(transform_self){bt.current_attacker=bt.current_target;a=t;}
        }
        original_attacker=bt.current_attacker;memcpy(transform_before,a,78);
        ''')
    s=s.replace('        fflush(stdout);',r'''
        printf("QA_TRANSFORM {\"id\":%u,\"attackerBytes\":\"",v[0]);for(unsigned i=0;i<78;i++)printf("%02x",((unsigned char*)a)[i]);
        printf("\",\"attackerBefore\":\"");for(unsigned i=0;i<78;i++)printf("%02x",transform_before[i]);
        printf("\",\"aiCursor\":%u}\n",bt.redux_enemy_ai_cursor[8]);fflush(stdout);''')
    return s

def enemy_bytes(edata,enemy,x,y,index):
    b=bytearray(78)
    def put(o,n,v):b[o:o+n]=int(v).to_bytes(n,'little')
    def word(o):return int.from_bytes(edata[o:o+2],'little')
    put(0,2,enemy);b[2]=word(28)&255;b[11]=b[12]=b[13]=b[14]=1;b[16]=edata[91]
    for o in(17,19,21):put(o,2,word(33))
    for o in(23,25,27):put(o,2,word(35))
    for current,base,value in((38,50,edata[56]),(40,51,edata[58]),(42,52,edata[60]),(44,53,edata[61]),(46,54,edata[62])):put(current,2,value);b[base]=value
    b[49]=edata[85];dmg=(255,179,102,13);res=(255,128,26,0)
    mod=lambda table,v:table[v]if 0<=v<4 else 255
    b[58]=mod(dmg,edata[63]);b[56]=mod(dmg,edata[64]);b[57]=mod(res,edata[65]);b[55]=mod(res,edata[66]);b[60]=mod(res,edata[67]);b[59]=mod(res,3-edata[67]);b[61:67]=edata[41:43]+edata[37:41]
    status=edata[89]
    if 1<=status<=4:b[35]=(2,1,4,3)[status-1];b[37]=3
    elif status==5:b[31]=1
    elif status==6:b[33]=1
    elif status==7:b[32]=1
    b[67]=index;b[68]=x;b[69]=y;b[76]=enemy
    return b

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in('build','native-source','assets','runtime','scratch','output','project'):ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--original',action='store_true');ap.add_argument('--pilot',action='store_true');ap.add_argument('--diagnostic',action='store_true');a=ap.parse_args()
    if a.scratch.exists():raise ValueError('Fresh scratch required')
    pin=subprocess.check_output(['git','-C',str(a.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=helper.PIN:raise ValueError('Unreviewed pin')
    a.scratch.mkdir(parents=True);session=a.scratch/'session';session.mkdir();helper.DRIVER=driver_source(a.original);exe,build=helper.private_build(a)
    _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h');table=assets['data/battle_action_table.bin'];enemies=assets['data/enemy_configuration_table.bin'];groups=summon.groups_from_pack(assets);actions={int.from_bytes(table[i+8:i+12],'little'):i//12 for i in reversed(range(0,len(table),12))};tests=[]
    for maximum in(8,999,2000,10000):
        for luck in(0,20,79,80):
            for side in(0,1):
                for self_target,attacker_hp in((0,500),(0,0),(1,500)):
                    for seed in((1,)if a.pilot else range(1,65)):
                        f=0xC2A507;v=[len(tests),actions[f],seed*0x9e3779b9&0xffffffff,8 if side else 0,0,min(maximum,5000),100,maximum,300,0,0,0,0,0,0,0,255,255,255,255,255,255,luck,0,80,50,20,0,0,0,0,0,0,1,0,0,0,0,0,1,20,20,0,0,0,0,50,0,self_target,attacker_hp,0]
                        tests.append(dict(function=f,maximum=maximum,luck=luck,side=side,self_target=self_target,attacker_hp=attacker_hp,seed=seed,values=v))
    # All actual initial group callers with Rainbow as final action and their
    # unchanged packed final argument. Initial species174 has no count>0 group.
    for group,records in groups.items():
        for count,enemy in records:
            action=int.from_bytes(enemies[enemy*94+78:enemy*94+80],'little')
            if not count or int.from_bytes(table[action*12+8:action*12+12],'little')!=0xC2C14E:continue
            new=enemies[enemy*94+84]
            if new not in[e for n,e in records]:raise ValueError('Transform art absent from source group')
            for x,y in((1,1),(55,66),(128,128),(255,255)):
                for cold in(0,1):
                    for seed in((1,)if a.pilot else range(1,65)):
                        f=0xC2C14E;v=[len(tests),action,seed*0x9e3779b9&0xffffffff,enemy+1,3,2000,200,2000,300,0,0,0,0,0,0,0,255,255,255,255,255,255,20,0,80,50,20,0,0,0,new,0,0,1,group,cold,0,0,0,0,20,20,0,0,0,0,50,0,0,x,y]
                        tests.append(dict(function=f,group=group,enemy=enemy,new=new,records=records,x=x,y=y,cold=bool(cold),seed=seed,values=v))
    path=a.scratch/'cases.tsv';path.write_text('\n'.join(' '.join(map(str,t['values']))for t in tests)+'\n')
    run=subprocess.run([str(exe.resolve()),str(a.assets.resolve()),str(session.resolve()),str(path.resolve())],cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=300)
    log=a.scratch/'native.log';log.write_bytes(run.stdout+run.stderr);results={}
    for line in run.stdout.decode(errors='replace').splitlines():
        for prefix in('QA ','QA_DETAIL ','QA_TRANSFORM ','QA_SUMMON '):
            if line.startswith(prefix):r=json.loads(line[len(prefix):]);results.setdefault(r['id'],{}).update(r)
    rows=[]
    for i,t in enumerate(tests):
        r=results.get(i,{});errors=[]
        if 'attackerBytes'not in r:errors.append('Missing native result')
        elif t['function']==0xC2C14E:
            ids=[e for n,e in t['records']];wanted=enemy_bytes(enemies[t['new']*94:(t['new']+1)*94],t['new'],t['x'],t['y'],ids.index(t['new']));actual=bytes.fromhex(r['attackerBytes'])
            differences=[i for i in range(78)if wanted[i]!=actual[i]]
            if differences:errors.append(f'Transformed battler byte offsets differ{differences}')
            if not r['skipDeath']or r['aiCursor']or r['artIds'][:len(ids)]!=ids:errors.append('Transform cleanup/art/source AI cursor state differs')
        else:
            success=r['rolls8'][0]*80//256>=t['luck'] and t['attacker_hp']!=0 and not t['self_target']
            drain=helper.variance_reference(t['maximum'],r['rolls8'][1:3],0)>>3 if success else 0
            hp=min(t['maximum'],5000)-drain;ahp=min(t['attacker_hp']+drain,999)if success else t['attacker_hp']
            if t['self_target']:ahp=min(t['maximum'],5000)
            for key,value in(('hp',hp),('attackerHp',ahp),('aff',[0]*7),('attackerRestored',1),('targetRestored',1)):
                if r[key]!=value:errors.append(f'{key} got{r[key]} expected{value}')
        if r and(r['depth']!=1 or r['steps']>=30000):errors.append('Native continuation incomplete')
        public={k:v for k,v in t.items()if k not in('values','records')};public['function']=f'{t["function"]:06X}';rows.append(dict(**public,passed=not errors,errors=errors))
    refs=['src/game/battle_actions.c','src/game/battle.c','src/game/battle_ui.c','src/game/battle_calc.c','asm/battle/actions/hp_sucker.asm','asm/battle/actions/rainbow_of_colours.asm','asm/battle/init_enemy_stats.asm','asm/battle/enemy/setup_battle_enemy_sprites.asm','asm/battle/enemy/find_battle_sprite_for_enemy.asm']
    report=dict(schemaVersion=1,toolVersion='dev16-transform-drain',reduxRevision=pin,originalPack=a.original,runtimeSha256={n:helper.digest(a.runtime/n)for n in('player.exe','observer.exe')},assetsSha256=helper.digest(a.assets),privateBuild=build,nativeExitCode=run.returncode,nativeLogSha256=helper.digest(log),sourceReferences=[dict(path=p,sha256=helper.digest(a.native_source/p))for p in refs],cases=rows,semanticCoverage=dict(completedCases=len(results),activeCallbacks=[f'{f:06X}'for f in FUNCTIONS]),allPassed=run.returncode==0 and len(results)==len(tests)and all(r['passed']for r in rows),pilot=a.pilot,diagnostic=a.diagnostic,reproductionFlags={n:str(getattr(a,n.replace('-','_')))for n in('build','native-source','assets','runtime','scratch','output','project')},limits=['Complete prepared HP-sucker C2A507 alias callback with actual text/drain/heal; luck, dead attacker, self-target, sides and high max HP. Nonlethal fixtures exclude KO/outer item consumption/target traversal.','Actual BS_ENTER full group constructor and native art/layout precede Rainbow final-action callback; all actual count>0 group callers are selected. Species174 no initial group caller is explicitly unevaluated.','Transformation compares all78 source battler bytes including position, fresh stats/status, full-group art index and cleanup/cursor flags; metadata match alone is not asserted as gameplay proof. Cold here only clears transient entry pointer globals after actual group construction, not fresh serialized restoration.','Source-derived expectations, no full original-machine action proof; art allocation does not certify pixels/audio. Only player library executed; observer hash provenance. No owner payload/ROM/save bytes included.'],fullConversionVerified=False,fullPlaythroughVerified=False)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(cases=len(rows),passed=sum(r['passed']for r in rows),allPassed=report['allPassed'],nativeExitCode=run.returncode,firstFailures=[r for r in rows if not r['passed']][:3])))
    if not report['allPassed']and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
