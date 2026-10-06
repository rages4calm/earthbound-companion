# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared real KO/final-action continuation; separate from frozen callback proofs."""
import argparse,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
import battle_food_summon_qa_dev15 as prior
from build_maternalbound_pack import read_pack

def driver_source(original):
    s=prior.driver_source(original)
    old="""if(battle_action_dispatch(callback,&action)) {
                action.battle_action.pc=(uint8_t)(v[32]<128?v[32]:0);
                mode_push(GAME_MODE_BATTLE_ACTION,&action);steps=pump();
            }"""
    new="""battle_ko_make_init(&action,8*sizeof(Battler));
            t->hp=t->hp_target=0;
            mode_push(GAME_MODE_BATTLE_KO,&action);steps=pump();"""
    if old not in s:raise ValueError('Reviewed native-driver insertion changed')
    s=s.replace(old,new)
    s=s.replace('qa_var_count=0;','qa_var_count=0;a->sprite_x=(uint8_t)v[36];a->sprite_y=(uint8_t)v[37];')
    return s

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in('build','native-source','assets','runtime','scratch','output','project'):ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--original',action='store_true');ap.add_argument('--diagnostic',action='store_true');a=ap.parse_args()
    if a.scratch.exists():raise ValueError('Fresh scratch required')
    pin=subprocess.check_output(['git','-C',str(a.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=helper.PIN:raise ValueError('Unreviewed pin')
    a.scratch.mkdir(parents=True);session=a.scratch/'session';session.mkdir();helper.DRIVER=driver_source(a.original);exe,build=helper.private_build(a)
    _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h');enemies=assets['data/enemy_configuration_table.bin'];groups=prior.groups_from_pack(assets);tests=[]
    for group in(448,471):
      enemy=next(e for n,e in groups[group]if n);edata=enemies[enemy*94:(enemy+1)*94];action=int.from_bytes(edata[78:80],'little');new=edata[84]if action else enemy
      for x,y in((1,1),(55,66)):
       for cold in(0,1):
        for seed in range(1,9):
          v=[len(tests),action,seed*0x9e3779b9&0xffffffff,enemy+1,3,2000,200,2000,300,0,0,0,0,0,0,0,255,255,255,255,255,255,20,0,80,50,20,0,0,0,edata[84],0,0,1,group,cold,x,y,0,0,20,20,0,0,0,0,50,0]
          tests.append(dict(group=group,enemy=enemy,new=new,action=action,cold=bool(cold),seed=seed,values=v))
    path=a.scratch/'cases.tsv';path.write_text('\n'.join(' '.join(map(str,t['values']))for t in tests)+'\n')
    run=subprocess.run([str(exe.resolve()),str(a.assets.resolve()),str(session.resolve()),str(path.resolve())],cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=180)
    log=a.scratch/'native.log';log.write_bytes(run.stdout+run.stderr);results={}
    for line in run.stdout.decode(errors='replace').splitlines():
      for prefix in('QA ','QA_DETAIL ','QA_SUMMON '):
       if line.startswith(prefix):r=json.loads(line[len(prefix):]);results.setdefault(r['id'],{}).update(r)
    rows=[]
    for i,t in enumerate(tests):
      r=results.get(i,{});errors=[];edata=enemies[t['enemy']*94:(t['enemy']+1)*94]
      aff=[0]*7;initial=enemies[t['new']*94+89]
      if t['action']and 1<=initial<=4:aff[6]=(2,1,4,3)[initial-1]
      elif t['action']and initial in(5,6,7):aff[{5:2,6:4,7:3}[initial]]=1
      expected=dict(targetId=t['new'],hp=int.from_bytes(enemies[t['new']*94+33:t['new']*94+35],'little')if t['action']else 0,aff=aff if t['action']else[1,0,0,0,0,0,0],battleExp=int.from_bytes(edata[37:41],'little'),battleMoney=int.from_bytes(edata[41:43],'little'),depth=1)
      if not r:errors.append('Missing actual native KO result')
      else:
       for k,v in expected.items():
        if r[k]!=v:errors.append(f'{k}: got{r[k]} expected{v}')
       if t['action']and not r['skipDeath']:errors.append('Source final-action cleanup skip was lost')
      rows.append(dict(**{k:v for k,v in t.items()if k!='values'},expected=expected,actual={k:r.get(k)for k in expected},passed=not errors,errors=errors))
    refs=['src/game/battle.c','src/game/battle_actions.c','src/game/battle_ui.c','asm/battle/ko_target.asm','asm/battle/actions/rainbow_of_colours.asm','asm/battle/init_scripted.asm']
    report=dict(schemaVersion=1,toolVersion='dev17-ko-lifecycle',reduxRevision=pin,originalPack=a.original,runtimeSha256={n:helper.digest(a.runtime/n)for n in('player.exe','observer.exe')},assetsSha256=helper.digest(a.assets),privateBuild=build,nativeExitCode=run.returncode,nativeLogSha256=helper.digest(log),sourceReferences=[dict(path=p,sha256=helper.digest(a.native_source/p))for p in refs],cases=rows,allPassed=run.returncode==0 and len(results)==len(tests)and all(r['passed']for r in rows),diagnostic=a.diagnostic,reproductionFlags={n:str(getattr(a,n.replace('-','_')))for n in('build','native-source','assets','runtime','scratch','output','project')},limits=['Real KO frompc0 including packed final action, text/apply/calc children and source group constructor/art/layout. Prepared dying HP0; not a full menu/turn encounter or natural story reachability proof.','Frank group448 no-final negative control; Carbon Dog group471 final action290arg83. Cold only transient entry pointers cleared after constructor, not fresh restore.','Source SKIP_DEATH_TEXT_AND_CLEANUP branches to whole KO return before death text/animation/status. Current native ordinary KO control and transformed boss expected separately.','Only player library executes; observer hash provenance. No owner payload published.'],fullConversionVerified=False,fullPlaythroughVerified=False)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(cases=len(rows),passed=sum(r['passed']for r in rows),nativeExitCode=run.returncode,firstFailures=[r for r in rows if not r['passed']][:2])))
    if not report['allPassed']and not a.diagnostic:raise SystemExit(1)
if __name__=='__main__':main()
