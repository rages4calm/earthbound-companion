# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded pinned-source Monkey Cave and Escargo transaction prerequisites."""
import argparse,json,re
from pathlib import Path

MONKEYS=[('A',0xC61616,224,451),('B',0xC61715,93,452),('C',0xC61817,127,453),('D',0xC61966,95,454),('E',0xC61A88,108,455),('F',0xC61B85,95,456),('G',0xC61CAC,90,457),('H',0xC61DDB,90,458),('I',0xC61F07,166,459),('J',0xC62026,90,460),('K',0xC620F7,92,461),('L',0xC62257,140,462)]
SPECIAL={0xC623BF:'MSG_DSRT_MONKEY_CAVE_M',0xC62578:'MSG_DSRT_MONKEY_CAVE_N',0xC636E5:'MSG_SHOP3_PHONE_ESCARGO_EXPRESS',0xC642A3:'MSG_SHOP3_ESCARGO_DELIVERY_VISIT',0xC63EB0:'MSG_SHOP3_ESCARGO_PICKUP_VISIT'}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--native-source',type=Path,required=True);ap.add_argument('--relocations',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--original',action='store_true');ap.add_argument('--pilot',action='store_true');a=ap.parse_args()
 defs={n:int(v,16)for n,v in re.findall(r'#define\s+(\w+)\s+0x([0-9a-fA-F]+)',(a.native_source/'src/data/text_refs.h').read_text())};reloc=json.loads(a.relocations.read_text())['originalAddresses'];names={addr:'MSG_DSRT_MONKEY_CAVE_'+letter for letter,addr,_,_ in MONKEYS}|SPECIAL
 def entry(addr):return defs[names[addr]]if a.original else reloc[f'{addr:06X}']
 def inv(items,who=0):bags=[[0]*14 for _ in range(4)];bags[who][:len(items)]=items;return bags
 cases=[]
 for letter,addr,item,flag in MONKEYS:
  variants=[('correct',[item], [0,0],1,0),('incorrect',[87],[0,0],0,0),('decline',[item],[1],0,0),('inventory-cancel',[item],[0,999],0,0),('cold-correct',[item],[0,0],1,3),('duplicate-correct',[item,item],[0,1],1,0)]
  if a.pilot:variants=[variants[0]]if letter in('A','I','L')else[]
  for label,bag,plan,success,cold in variants:
   expected=bag.copy()
   if success:expected.pop(plan[-1])
   c=dict(id=f'monkey-{letter}-{label}',sourceEntry=f'{addr:06X}',entry=entry(addr),initialInventory=inv(bag),plan=plan,checkpoint=cold,expectedDelta=0,sound=118,soundCount=success,expectedTransfer={'flags':{str(flag-451):success},'queuedItems':[0,0,0],'storage':[0]*36},sourceContract=dict(acceptedItem=item,flag=flag,success=bool(success)))
   if item!=166:c['expectedInventory']=inv(expected)
   else:c['expectedTransfer']['keyPool']=([166]+[0]*63)if not success else[0]*64
   cases.append(c)
 chain=dict(id='monkey-N-gift-then-I-trade',sourceEntry='C62578',entry=entry(0xC62578),entrySequence=[entry(0xC61F07)],initialInventory=inv([]),plan=[0,0],expectedInventory=inv([]),expectedDelta=0,sound=118,soundCount=1,expectedTransfer={'flags':{'8':1,'13':1},'keyPool':[0]*64,'queuedItems':[0,0,0],'storage':[0]*36},sourceContract=dict(giftItem=166,giftFlag=464,tradeFlag=459,success=True))
 cases.append(chain)
 if not a.pilot:
  for letter,addr,item,flag in MONKEYS:
   cases.append(dict(id=f'monkey-{letter}-already-completed',sourceEntry=f'{addr:06X}',entry=entry(addr),initialInventory=inv([item]),initialFlags={str(flag):1},plan=[],expectedDelta=0,sound=118,soundCount=0,expectedTransfer={'flags':{str(flag-451):1}},sourceContract=dict(acceptedItem=item,flag=flag,success=False)))
  for name,addr,flag,item in [('gift-Egg',0xC623BF,463,92),('gift-KingBanana',0xC62578,464,166)]:
   for free in (0,1,14):
    bag=[87]*(14-free);expected=bag+[item] if free and item!=166 else bag
    cases.append(dict(id=f'monkey-{name}-free{free}',sourceEntry=f'{addr:06X}',entry=entry(addr),initialInventory=inv(bag),plan=[],expectedInventory=inv(expected),expectedDelta=0,expectedTransfer={'flags':{str(flag-451):int(bool(free))},'keyPool':([166]+[0]*63)if free and item==166 else[0]*64},sourceContract=dict(giftItem=item,giftFlag=flag,freeSlots=free)))
  # Delivery visits expect the source phone request's pending queue, not stored
  # items selected at the visit. Queue setup uses the actual source API.
  for queue in ([87],[87,90],[87,90,93]):
   for free in (0,1,2,14):
    delivered=min(len(queue),free);bag=[224]*(14-free)
    for cold in (0,3):
     if cold:continue # Visit Yes/No is window1; added as a separately reviewed boundary later.
     cases.append(dict(id=f'escargo-deliver-{len(queue)}-free{free}',sourceEntry='C642A3',entry=entry(0xC642A3),initialInventory=inv(bag),initialQueue=[[255,x]for x in queue],initialFlags={'181':1},plan=[0],checkpoint=cold,expectedDelta=-18 if delivered else 0,expectedInventory=inv(bag+queue[:delivered]),expectedTransfer={'storage':queue[delivered:]+[0]*(36-len(queue[delivered:])),'queuedItems':[0]*3,'queuedSources':[0]*3},sourceContract=dict(charge=18,deliver=delivered,returnToStorage=queue[delivered:])))
  for label,cash,plan in [('insufficient',17,[0]),('decline',80000,[1,0])]:
   cases.append(dict(id='escargo-deliver-'+label,sourceEntry='C642A3',entry=entry(0xC642A3),money=cash,initialInventory=inv([]),initialQueue=[[255,87],[255,90],[255,93]],initialFlags={'181':1},plan=plan,expectedDelta=0,expectedInventory=inv([]),expectedTransfer={'storage':[87,90,93]+[0]*33,'queuedItems':[0]*3,'queuedSources':[0]*3},sourceContract=dict(charge=0,returnToStorage=[87,90,93])))
  for label,plan,expected in [('one',[0,0,1,0],1),('three',[0,0,0,0,0,0,0],3),('cancel',[1],0),('selection-cancel',[0,999],0)]:
   items=[87,90,93];cases.append(dict(id='escargo-pickup-'+label,sourceEntry='C63EB0',entry=entry(0xC63EB0),initialInventory=inv(items),initialFlags={'645':1},plan=plan,expectedDelta=-18 if expected else 0,expectedInventory=inv(items[expected:]),expectedTransfer={'storage':items[:expected]+[0]*(36-expected),'queuedItems':[0]*3,'queuedSources':[0]*3},sourceContract=dict(store=items[:expected],charge=18 if expected else 0)))
  for label,initial,plan,storage,queue in [('one',[87,90,93],[1,0,1,0],[90,93],[87]),('three',[87,90,93],[1,0,0,0,0,0,0],[ ],[87,90,93]),('cancel',[87],[999],[87],[]),('empty',[],[1],[],[])]:
   for cold in (0,4) if queue else(0,):
    cases.append(dict(id=f'escargo-phone-{label}'+('-cold'if cold else''),sourceEntry='C636E5',entry=entry(0xC636E5),initialInventory=inv([]),initialStorage=initial,plan=plan,checkpoint=cold,expectedInventory=inv([]),expectedDelta=0,expectedTransfer={'storage':storage+[0]*(36-len(storage)),'queuedItems':queue+[0]*(3-len(queue))},sourceContract=dict(requestedItems=queue,charge=0)))
 a.output.write_text(json.dumps(cases,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(cases=len(cases),original=a.original)))
if __name__=='__main__':main()
