# SPDX-License-Identifier: GPL-3.0-or-later
"""Extend frozen shop QA with source Tools ownership and stock transitions.

The imported dev18 runner is unchanged. Only this new private driver adds
pre-entry source flag controls and read-only Tools flag snapshots. All actual
transactions/children/input use the production dispatcher and immutable library.
"""
import json,sys
from pathlib import Path
import shop_transaction_qa_dev18 as base

original_driver_source=base.driver_source
def driver_source(original):
 s=original_driver_source(original)
 s=s.replace('if(flag)event_flag_set(flag);rng_seed(seed);','if(flag & 0x10000u)event_flag_clear(flag & 0xffffu);else if(flag)event_flag_set(flag);rng_seed(seed);')
 marker='static void snap(const char*stage){\n'
 extra=r''' printf("QA_TOOLS {\"stage\":\"%s\",\"toolsEnabled\":%u,\"bazookaOwned\":%u,\"brokenIronPurchased\":%u}\n",stage,event_flag_get(782),event_flag_get(982),event_flag_get(985));
'''
 if s.count(marker)!=1:raise ValueError('Reviewed private snapshot insertion changed')
 return s.replace(marker,marker+extra)

def main():
 base.driver_source=driver_source
 failure=0
 try:base.main()
 except SystemExit as e:
  if e.code not in(0,1):raise
  failure=e.code
 output=Path(sys.argv[sys.argv.index('--output')+1]);report=json.loads(output.read_text())
 for row in report['cases']:
  case=row['fixture'];states={e['actual']['stage']:e['actual']for e in row['events']if e['type']=='QA_TOOLS'};after=states.get('after-entry',{});before=states.get('before-entry',{})
  for key,want in case.get('expectedToolFlags',{}).items():
   if after.get(key)!=want:row['errors'].append(f'Source Tools mutation differs:{key} actual{after.get(key)} expected{want}')
  if 'expectedToolsEnabled'in case and before.get('toolsEnabled')!=case['expectedToolsEnabled']:row['errors'].append('Prepared source Tools flag differs')
  if 'expectedStockSequence'in case:
   actual=[[x['id']for x in e['actual']['options']]for e in row['events']if e['type']=='QA_MENU'and e['actual']['window']==12]
   if actual!=case['expectedStockSequence']:row['errors'].append('Actual stock sequence did not follow source ownership mutation')
  row['passed']=not row['errors']
 report['toolVersion']='dev19-selected-special-shop-entries';report['allPassed']=not failure and all(r['passed']for r in report['cases'])
 report['limits'].append('New private driver optionally clears a source flag before entry when fixture flag bit16 is set; no post-entry flag/result mutation. Tools ownership fields are read-only actual source event flags782/982/985. These selected source entries do not prove the subsequent battle Tools menu or natural story reachability.')
 project=Path(sys.argv[sys.argv.index('--project')+1])
 report['pinnedSource'].extend(dict(path=p,sha256=base.helper.digest(project/p))for p in('ccscript/shops/shops_scarabia.ccs','ccscript/shops/shops_twoson.ccs','ccscript/redux/tools.ccs'))
 output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(cases=len(report['cases']),passed=sum(r['passed']for r in report['cases']),failures=[dict(id=r['fixture']['id'],errors=r['errors'])for r in report['cases']if not r['passed']][:3])))
 if not report['allPassed']and '--diagnostic'not in sys.argv:raise SystemExit(1)
if __name__=='__main__':main()
