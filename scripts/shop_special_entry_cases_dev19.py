# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate selected source Tools-purchase/OneItem fixtures from private packs."""
import argparse,json,re
from pathlib import Path
from build_maternalbound_pack import read_pack

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for name in('assets','native-source','output'):ap.add_argument('--'+name,type=Path,required=True)
 ap.add_argument('--original',action='store_true');ap.add_argument('--relocations',type=Path);a=ap.parse_args()
 _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h');items=assets['data/item_configuration_table.bin'];shops=assets['data/store_table.bin'];cases=[]
 defs={n:int(v,16)for n,v in re.findall(r'#define\s+(MSG_\w+)\s+0x([0-9a-fA-F]+)',(a.native_source/'src/data/text_refs.h').read_text())};reloc=json.loads(a.relocations.read_text())['originalAddresses']if a.relocations else{}
 def stock(sid):return[x for x in shops[sid*7:sid*7+7]if x]
 def price(item):return int.from_bytes(items[item*39+26:item*39+28],'little')
 def entry(addr,name):
  if a.original:return defs[name]
  if not reloc:raise ValueError('Exact pinned dialogue relocation map required')
  return reloc[addr]
 bazooka=133;assert stock(51)[3]==bazooka
 b=dict(sourceEntry='C5D539',entry=entry('C5D539','MSG_SHOP1_SCARABA_OASIS_SHOP'),money=80000,shop=51,stock=stock(51),sound=120)
 if a.original:
  for name,cash,free,count in [('single',80000,14,1),('insufficient',price(bazooka)-1,14,0),('all-bags-full',80000,0,0)]:
   cases.append(dict(b,id='Original-Bazooka-'+name,money=cash,freeSlots=free,plan=[0,3,1],expectedItem=bazooka,expectedCount=count,expectedDelta=-price(bazooka)*count,soundCount=count,expectedToolFlags=dict(bazookaOwned=0,brokenIronPurchased=0)))
 else:
  for name,flag,cash,free,plan,count,delta,ping,owned in [('Tools-first-Bazooka',782,80000,14,[0,3,1],0,-price(bazooka),1,1),('Tools-Bazooka-insufficient',782,price(bazooka)-1,14,[0,3,1],0,0,0,0),('Tools-Bazooka-all-bags-full',782,80000,0,[0,3,1],0,0,0,0),('Tools-off-single-Bazooka',0x10000|782,80000,14,[0,3,0,1],1,-price(bazooka),1,0),('Tools-off-multiple-Bazooka',0x10000|782,80000,14,[0,3,1,1],3,-price(bazooka)*3,3,0)]:
   cases.append(dict(b,id=name,flag=flag,money=cash,freeSlots=free,plan=plan,expectedItem=bazooka,expectedCount=count,expectedDelta=delta,soundCount=ping,expectedToolsEnabled=0 if flag&0x10000 else 1,expectedToolFlags=dict(bazookaOwned=owned,brokenIronPurchased=0)))
  food=stock(66)[3]
  cases.append(dict(b,id='Tools-Bazooka-repeat-stock-transition',flag=782,plan=[0,3,0,0,3,0,1],expectedItem=food,expectedCount=1,expectedDelta=-price(bazooka)-price(food),soundCount=2,expectedToolsEnabled=1,expectedToolFlags=dict(bazookaOwned=1,brokenIronPurchased=0),expectedStockSequence=[stock(51),stock(66)]))
 # ShopMain flag238 selects table15, not table13. OneItem is a wrapper with
 # source purchase/repeat behavior; its name does not prohibit bulk quantities.
 b=dict(sourceEntry='C5D2ED',entry=entry('C5D2ED','MSG_SHOP1_TWOSON_FRUIT_STAND'),money=80000,shop=15,stock=stock(15),sound=120);item=stock(15)[0];cost=price(item)
 specs=[('single',1,80000,14,[0,*([]if a.original else[0]),1],True),('insufficient',1,cost-1,14,[0],False),('all-bags-full',1,80000,0,[0],False),('cancel',1,80000,14,[999],False)]
 if not a.original:specs.extend([('bulk3',3,80000,14,[0,1,1],True),('bulk14',14,80000,14,[0,1,1],True),('bulk-capacity2',3,80000,2,[0,1],False),('bulk0',0,80000,14,[0,1],True)])
 for label,q,cash,free,plan,success in specs:cases.append(dict(b,id='OneItem-Banana-'+label,quantity=q,money=cash,freeSlots=free,plan=plan,expectedItem=item,expectedCount=q if success else 0,expectedDelta=-cost*q if success else 0,soundCount=q if success else 0))
 if not a.original:
  # Source only conditions stock on flag985 here; the selected ordinary
  # purchase paths contain no flag985 setter. No later repair-path claim.
  for name,addr,sid,pos,plan in [('Twoson', 'C5D2B7',11,5,[0,5,1,1]),('Fourside','C5D44F',35,1,[1,1,1])]:
   assert stock(sid)[pos]==9
   cases.append(dict(id=name+'-BrokenIron-bulk3',sourceEntry=addr,entry=reloc[addr],money=80000,shop=sid,stock=stock(sid),sound=120,soundCount=3,flag=782,quantity=3,plan=plan,expectedItem=9,expectedCount=3,expectedDelta=-price(9)*3,expectedToolFlags=dict(brokenIronPurchased=0,bazookaOwned=0)))
 cold=['Original-Bazooka-single','OneItem-Banana-single']if a.original else['Tools-first-Bazooka','Tools-off-single-Bazooka','Tools-off-multiple-Bazooka','OneItem-Banana-bulk3','OneItem-Banana-bulk-capacity2']
 for name in cold:
  case=next(c for c in cases if c['id']==name);numeric=name in('Tools-off-multiple-Bazooka','OneItem-Banana-bulk3','OneItem-Banana-bulk-capacity2');cases.append(dict(case,id=name+'-cold',checkpoint=1 if numeric else 2))
 a.output.write_text(json.dumps(cases,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(cases=len(cases),profile='Original'if a.original else'Redux')))
if __name__=='__main__':main()
