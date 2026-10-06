# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepare bounded source-selected shop transaction fixtures from packed tables.

Entry scripts correspond to exact Original SNES labels and native text aliases.
Prices and stock IDs are always decoded from the supplied profile's pack. These
fixtures are source-entry tests, not claims of natural NPC/story reachability.
"""
import argparse,json,re,sys
from pathlib import Path
from build_maternalbound_pack import read_pack

ENTRY_NAMES={0xC5D24B:'MSG_SHOP1_ONETT_DRUGSTORE_A',0xC5D2B7:'MSG_SHOP1_TWOSON_JUNK_SHOP',0xC5D44F:'MSG_SHOP1_FOURSIDE_JUNK_SHOP',0xC5D539:'MSG_SHOP1_SCARABA_OASIS_SHOP',0xC5D593:'MSG_SHOP1_MOON_HOTEL_SHOP'}

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in('assets','native-source','output'):ap.add_argument('--'+n,type=Path,required=True)
 ap.add_argument('--original',action='store_true');ap.add_argument('--relocations',type=Path);ap.add_argument('--set',choices=['bulk','retail','all'],default='all');a=ap.parse_args()
 _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h');items=assets['data/item_configuration_table.bin'];shops=assets['data/store_table.bin']
 defs={n:int(v,16)for n,v in re.findall(r'#define\s+(MSG_\w+)\s+0x([0-9a-fA-F]+)',(a.native_source/'src/data/text_refs.h').read_text())}
 reloc=json.loads(a.relocations.read_text())['originalAddresses']if not a.original and a.relocations else{}
 if not a.original and not reloc:raise ValueError('Exact dialogue relocation map required for Redux entry addresses')
 def entry(addr):return defs[ENTRY_NAMES[addr]]if a.original else reloc[f'{addr:06X}']
 def stock(shop):return[x for x in shops[shop*7:shop*7+7]if x]
 def price(item):return int.from_bytes(items[item*39+26:item*39+28],'little')
 def base(name,addr,shop,index,flag=0,sound=120):
  st=stock(shop);item=st[index];return dict(id=name,sourceEntry=f'{addr:06X}',entry=entry(addr),shop=shop,stock=st,flag=flag,money=80000,expectedItem=item,expectedCount=1,expectedDelta=-price(item),sound=sound,soundCount=1)
 cases=[]
 if a.set in('bulk','all')and not a.original:
  for name,addr,shop,pos,flag,buy in [('custom66',0xC5D539,66,3,982,True),('custom67',0xC5D2B7,67,0,985,True),('custom68',0xC5D44F,68,1,985,False),('moonside',0xC5D593,60,0,0,False),('ordinary-Onett',0xC5D24B,1,0,0,True)]:
   b=base(name,addr,shop,pos,flag,12 if name=='ordinary-Onett'else 120);plan=([0]if buy else[])+[pos,1,0 if name=='moonside'else 1];p=price(b['expectedItem'])
   for label,q,party,free,cash,cold in [('good',3,1,14,80000,0),('capacity2',3,1,2,80000,0),('cold-capacity2',3,1,2,80000,1),('cash2',3,1,14,p*2,0),('cold-cash2',3,1,14,p*2,1),('party2-capacity2',3,2,1,80000,0),('party2-capacity4',3,2,2,80000,0),('cold-good',3,1,14,80000,1),('party4-full56',56,4,14,80000,0),('party4-overflow99',99,4,14,80000,0)]:
    success=q<=party*free and cash>=p*q;cases.append(dict(b,id=name+'-'+label,quantity=q,party=party,freeSlots=free,money=cash,checkpoint=cold,plan=plan,expectedCount=q if success else 0,expectedDelta=-p*q if success else 0,soundCount=q if success else 0))
   fullplan=([0]if buy else[])+[pos]+([1]if buy else[])
   cases.append(dict(b,id=name+'-all-bags-full',freeSlots=0,party=4,plan=fullplan,expectedCount=0,expectedDelta=0,soundCount=0))
  b=base('moonside',0xC5D593,60,0)
  for q in(0,1,6,14):cases.append(dict(b,id='moonside-quantity'+str(q),quantity=q,plan=[0,1,0],expectedCount=q,expectedDelta=-price(b['expectedItem'])*q,soundCount=q))
  for name,addr,shop,pos in [('custom66-before-Bazooka',0xC5D539,51,4),('custom67-before-BrokenIron',0xC5D2B7,11,0),('custom68-before-BrokenIron',0xC5D44F,35,2)]:
   b=base(name,addr,shop,pos);buy=shop!=35;cases.append(dict(b,quantity=3,plan=([0]if buy else[])+[pos,1,1],expectedCount=3,expectedDelta=-price(b['expectedItem'])*3,soundCount=3))
 if a.set in('retail','all'):
  extra=[]if a.original else[0]
  b=base('Onett',0xC5D24B,1,0,sound=12);blank=[[0]*4 for _ in range(4)]
  for yes,label in[(0,'equip'),(1,'keep-unequipped')]:
   equip=[[1,0,0,0],*blank[1:]]if yes==0 else blank
   cases.append(dict(b,id='Onett-bat-'+label,plan=[0,0,*extra,yes,1],expectedEquipment=equip))
  # Actual packed flags for Fry pan32 are0x02: Paula eligible, Ness ineligible.
  # Shooter49 is flags0x0F and all four can equip it, despite its item type.
  shot=base('Scaraba-frypan',0xC5D539,51,0)
  for buy,label in[(0,'buy-without-equipping'),(1,'decline-cannot-equip')]:
   cases.append(dict(shot,id='Scaraba-frypan-'+label,plan=[0,0,*extra,buy,1],expectedCount=1 if buy==0 else 0,expectedDelta=-price(shot['expectedItem'])if buy==0 else 0,soundCount=1 if buy==0 else 0,expectedEquipment=blank))
  cases.append(dict(b,id='Onett-insufficient-single',money=17,plan=[0,0,1],expectedCount=0,expectedDelta=0,soundCount=0))
  for yes,label in[(0,'confirm'),(1,'cancel')]:
   sale=dict(b,id='Onett-sell-cookie-'+label,freeSlots=13,plan=[1,0,yes,1],expectedItem=90,expectedCount=-1 if yes==0 else 0,expectedDelta=price(90)//2 if yes==0 else 0,soundCount=1 if yes==0 else 0);sale.pop('stock');cases.append(sale)
  if not a.original:
   sale=dict(b,id='Onett-sell-unsellable',item=9,plan=[1,0,1],expectedItem=9,expectedCount=0,expectedDelta=0,soundCount=0);sale.pop('stock');cases.append(sale)
  cases.append(dict(b,id='Onett-equip-upgrade-sell-old',oldItem=17,plan=[0,1,*extra,0,0,1],expectedItem=18,expectedCount=1,expectedDelta=-price(18)+price(17)//2,soundCount=2,expectedEquipment=[[1,0,0,0],*blank[1:]]))
  moon=base('moonside',0xC5D593,60,0)
  cases.append(dict(moon,id='moonside-single',plan=[0,*extra,0],checkpoint=2))
  if not a.original:
   retry=base('custom66',0xC5D539,66,3,982)
   cases.append(dict(retry,id='custom66-selected-full-retry-Paula',party=2,freeSlots=0,freeSlotsSecond=14,plan=[0,3,0,0,0,1,1]))
   cases.append(dict(retry,id='custom66-selected-full-cancel',party=2,freeSlots=0,freeSlotsSecond=14,plan=[0,3,0,0,1,1],expectedCount=0,expectedDelta=0,soundCount=0))
 a.output.write_text(json.dumps(cases,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(cases=len(cases),profile='Original'if a.original else'Redux',set=a.set)))
if __name__=='__main__':main()
