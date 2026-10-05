# SPDX-License-Identifier: GPL-3.0-or-later
"""Check quest/ending containers outside the generic item-box table path."""
import argparse,json,re,shutil,sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import yaml
from audit_all_presents import prepare,execute,layout,verify_final_rewards,placement_catalog
from build_maternalbound_pack import read_pack
from check_jev_observer_parity import local_scratch,latest,sections
from jev_gameplay_runner import sha,mode_names

ROOT=Path(__file__).resolve().parents[1]
REWARDS=((582,'FLY_HONEY','FLG_ITEM_HAEMITU'),(744,'LETTER_FROM_MOM','FLG_ITEM_LETTER_1'),(745,'LETTER_FROM_TONY','FLG_ITEM_LETTER_2'),(746,'LETTER_FROM_KIDS','FLG_ITEM_LETTER_3'))

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('original','redux','project','checkpoint','engine','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();output=local_scratch(a.output)
 if output.exists():raise ValueError('Use fresh scratch output')
 output.mkdir(parents=True);offsets=layout(output)
 sys.path.insert(0,str(ROOT/'native-source/src/vendor/tamp'));import tamp
 save=latest(local_scratch(a.checkpoint));base=(save,sections(save,tamp))
 flags=(a.project/'ccscript/definitions/flags.ccs').read_text();items=(a.project/'ccscript/definitions/items.ccs').read_text()
 records=yaml.safe_load((a.project/'npc_config_table.yml').read_text().replace('\t',' '))
 source=(a.project/'ccscript/data/data_36.ccs').read_text()
 case_rows=[]
 for npc,item_name,flag_name in REWARDS:
  item=int(re.search(r'^define '+item_name+r'\s*=\s*(\d+)',items,re.M)[1])
  flag=int(re.search(r'^define '+flag_name+r'\s*=\s*flag\s+(\d+)',flags,re.M)[1])
  label=records[npc]['Text Pointer 1'].split('.')[-1]
  body=source.split('\n'+label+':',1)[1].split('\nl_0x',1)[0]
  if f'counter({item_name})' not in body or f'set({flag_name})' not in body or 'get_item_receiver(-1)' not in body:
   raise ValueError('Review scripted reward source before testing')
  case_rows.append({'npcId':npc,'itemId':item,'cash':None,'lootValue':item,'openedFlag':flag,'sourceItemSymbol':item_name,'sourceFlagSymbol':flag_name})
 ids=ROOT/'native-source/src/data/runtime_generated/asset_ids.h'
 packs={'original':a.original,'redux':a.redux};jobs=[];runtimes=[]
 for profile,pack in packs.items():
  assets=read_pack(pack,ids)[2];placed=placement_catalog(assets);runtime=output/(profile+'-runtime');runtime.mkdir()
  for f in (a.engine,a.engine.with_name('SDL2.dll')):shutil.copy2(f,runtime/f.name)
  frozen=runtime/'assets.pak';shutil.copy2(pack,frozen)
  run={'schema':1,'nativeExe':str(runtime/a.engine.name),'assets':str(frozen),'nativeExeSha256':sha(a.engine),'assetsSha256':sha(pack),'modeNames':mode_names(),'ordinaryInputsOnly':True,'seededFixture':True}
  for row in case_rows:
   if row['npcId'] not in placed or not int.from_bytes(assets['data/npc_config_table.bin'][row['npcId']*17+9:row['npcId']*17+13],'little'):
    raise ValueError('Missing scripted reward placement or dialogue')
   for full in (False,True):jobs.append((profile,run,row,full))
 def run_case(job):
  profile,run,row,full=job;folder=output/f'{profile}-{row["npcId"]}{"-full" if full else ""}'
  prepare(folder,base,row,offsets,tamp,full);(folder/'run.json').write_text(json.dumps(run,indent=2)+'\n')
  result=execute(folder,run,row,tamp,full);result['profile']=profile
  print(json.dumps({'profile':profile,'npc':row['npcId'],'full':full,'passed':True}),flush=True)
  return result
 with ThreadPoolExecutor(max_workers=4) as executor:results=list(executor.map(run_case,jobs))
 verify_final_rewards(output,results,tamp)
 # These share art IDs with item boxes, but their source defines encounters
 # or inert scenery instead of fixed loot. Record the boundary explicitly.
 classifications={'scriptedRewardContainers':[r['npcId'] for r in case_rows],
  'scriptedBattleObjects':{'680':446,'681':446,'1039':442,'1040':442},
  'noDialogueScenery':[987,1041,1042,1043]}
 battle=(a.project/'ccscript/data/data_65.ccs').read_text()
 for npc,formation in classifications['scriptedBattleObjects'].items():
  label=records[int(npc)]['Text Pointer 1'].split('.')[-1]
  body=battle.split('\n'+label+':',1)[1].split('\nl_0x',1)[0]
  if f'start_battle({formation})' not in body:raise ValueError('Battle object classification changed')
 for npc in classifications['noDialogueScenery']:
  if records[npc]['Text Pointer 1']!='$0' or records[npc]['Text Pointer 2']!='$0':raise ValueError('Scenery gained a scripted interaction')
 report={'Passed':True,'format':'scripted-container-rewards-v1','Cases':results,'ExpectedRewards':case_rows,
  'AdditionalContainerClassifications':classifications,'NativeExeSha256':sha(a.engine),'PlayerEngineSha256':sha(ROOT/'build/companion/earthbound.exe'),
  'OriginalPackSha256':sha(a.original),'ReduxPackSha256':sha(a.redux),'TypeSafeRequests':0,'OwnerSavesWritten':False,'FullPlaythroughVerified':False,
  'Boundary':'Prepared NPC identity/inventory/award flags bypass physical travel and appearance conditions. Unmodified native packs and ordinary confirm inputs execute all four real reward scripts in both editions, with full inventory and repeat checks. Four battle objects and four no-dialogue scenery objects are source-classified, not fought or traversed.'}
 (output/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'Passed':True,'scriptedRewardContainers':4,'cases':len(results)}))

if __name__=='__main__':main()
