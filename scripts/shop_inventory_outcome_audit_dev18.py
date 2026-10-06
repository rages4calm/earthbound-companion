# SPDX-License-Identifier: GPL-3.0-or-later
"""Check complete inventory vectors in recorded real shop transaction results.

This post-execution check adds source-derived inventory preservation assertions
to a matching transaction report. It does not execute additional native cases.
GIVE_ITEM_TO_CHARACTER traverses active party members in order; the specific
character helper fills the first free ordinary slot. Selected sale/upgrade
fixtures remove the identified old item, preserving other slots by compaction.
"""
import argparse,copy,hashlib,json
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(bags,item,party):
 for bag in bags[:party]:
  if 0 in bag:bag[bag.index(0)]=item;return
 raise ValueError('Successful fixture exceeds ordinary inventory capacity')
def remove(bags,item,party):
 for bag in bags[:party]:
  if item in bag:bag.pop(bag.index(item));bag.append(0);return
 raise ValueError('Selected sale fixture lacks source item')
def expected(case):
 party=case.get('party',1);before=[[0]*14 for _ in range(4)]
 for i in range(party):
  free=case.get('freeSlots',14)if i==0 else case.get('freeSlotsSecond',case.get('freeSlots',14))
  before[i]=[90]*(14-free)+[0]*free
  for item in(case.get('item',0),case.get('oldItem',0)):
   if item:
    if 0 not in before[i]:raise ValueError('Prepared source inventory has no free slot')
    before[i][before[i].index(0)]=item
 after=copy.deepcopy(before)
 if case.get('oldItem'):remove(after,case['oldItem'],party)
 count=case.get('expectedCount',0);item=case.get('expectedItem')
 for _ in range(abs(count)):
  if count>0:put(after,item,party)
  else:remove(after,item,party)
 return before,after

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--report',type=Path,action='append',required=True);ap.add_argument('--native-source',type=Path,required=True);ap.add_argument('--project',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();rows=[]
 for path in a.report:
  report=json.loads(path.read_text());profile='Original'if report['originalPack']else'Redux'
  for row in report['cases']:
   case=row['fixture'];stages={e['actual']['stage']:e['actual']for e in row['events']if e['type']=='QA_SNAP'};before,after=expected(case);errors=[]
   if not row['passed']:errors.append('Underlying real transaction checks failed')
   if stages.get('before-entry',{}).get('inventory')!=before:errors.append('Prepared inventory vector differs from recorded fixture inputs')
   if stages.get('after-entry',{}).get('inventory')!=after:errors.append('Complete source inventory vector differs; unrelated-item preservation/allocation failed')
   if stages.get('after-entry',{}).get('flags')!=[0]*6:errors.append('Selected entry did not finish with both transaction and configuration flags cleared')
   rows.append(dict(id=case['id'],profile=profile,cold=bool(case.get('checkpoint')),expectedBefore=before,expectedAfter=after,passed=not errors,errors=errors))
 refs=['asm/misc/give_item_to_character.asm','asm/misc/give_item_to_specific_character.asm','asm/misc/remove_item_from_inventory.asm']
 report=dict(schemaVersion=1,toolVersion='dev18-complete-shop-inventory-vectors',executionReports=[dict(path=str(p),sha256=sha(p),runtimeSha256=json.loads(p.read_text())['runtimeSha256'])for p in a.report],sourceReferences=[dict(path=p,sha256=sha(a.native_source/p))for p in refs if(a.native_source/p).is_file()],pinnedSourceReferences=[dict(path=p,sha256=sha(a.project/p))for p in('ccscript/shops/ShopSys.ccs','ccscript/shops/ShopMain.ccs')],cases=rows,allPassed=all(r['passed']for r in rows),limits=['Post-execution additional assertions on exactly the underlying real transaction records; no additional native executions or independent machine oracle.','Selected prepared active party1/2/4 inventory vectors only. Whole-vector assertions preserve all filler/unused/inactive slots for these fixtures, not every inventory layout, shop or story prerequisite.'],fullConversionVerified=False,fullPlaythroughVerified=False)
 a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(cases=len(rows),passed=sum(r['passed']for r in rows),failures=[r for r in rows if not r['passed']][:2])))
 if not report['allPassed']:raise SystemExit(1)
if __name__=='__main__':main()
