# SPDX-License-Identifier: GPL-3.0-or-later
"""Source-backed repair RNG consumer checks against an immutable native library.

Real inventory helper and serialized native RNG run after normal pack bootstrap.
Cold cases save in one private process and load in another. No owner data edits.
"""
import argparse, json, os, subprocess
from pathlib import Path
import battle_action_catalog_qa as linker
from build_maternalbound_pack import read_pack
from check_jev_observer_parity import local_scratch
from snes_movement_helpers_oracle import sha

DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>
#include "game_main.h"
#include "core/math.h"
#include "core/mode_stack.h"
#include "core/state_dump.h"
#include "game/game_state.h"
#include "game/inventory.h"
#include "game/maternalbound.h"
extern int eb_platform_main(int argc,char**argv);
int main(int argc,char**argv){
 if(argc==2&&strcmp(argv[1],"--layout")==0){printf("{\"recordBytes\":%zu,\"type\":%zu,\"params\":%zu,\"epi\":%u,\"brokenType\":%u}\n",sizeof(ItemConfig),offsetof(ItemConfig,type),offsetof(ItemConfig,params),ITEM_PARAM_EPI,ITEM_TYPE_BROKEN);return 0;}
 if(argc!=6)return 2;unsigned redux=atoi(argv[5]);char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 char*boot[]={"repair-rng-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1",redux?"--redux-battle-fixture":"--inspect-shuffle","0"};
 int count=sizeof(boot)/sizeof(boot[0]);if(!redux)count--;
 if(eb_platform_main(count,boot)||maternalbound_enabled()!=(redux!=0))return 3;
 FILE*f=fopen(argv[3],"r");if(!f)return 4;
 unsigned index,a,b,prob,item,iq,present;
 while(fscanf(f,"%u %u %u %u %u %u %u",&index,&a,&b,&prob,&item,&iq,&present)==7){
  if(strcmp(argv[4],"cold")==0){if(!state_dump_load_slots())return 5;}
  else {
   memset(party_characters,0,sizeof(party_characters));memset(game_state.party_members,0,sizeof(game_state.party_members));
   game_state.party_count=present?1:0;game_state.party_members[0]=present?3:0;
   party_characters[2].iq=(uint8_t)iq;party_characters[2].items[0]=(uint8_t)item;
   rng_state.a=(uint16_t)a;rng_state.b=(uint16_t)b;
   g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_NONE;memset(&g_mode_stack.state[0],0,sizeof(g_mode_stack.state[0]));
   if(strcmp(argv[4],"prepare")==0){if(!state_dump_save_slots())return 6;printf("REPAIR_SAVED %u\n",index);continue;}
  }
  RNGState saved=rng_state;unsigned roll=rng_next_byte();RNGState expected=rng_state;rng_state=saved;
  const ItemConfig*entry=get_item_entry((uint16_t)item);
  unsigned eligible=present&&entry&&entry->type==ITEM_TYPE_BROKEN&&entry->params[ITEM_PARAM_EPI]<=party_characters[2].iq;
  unsigned success=eligible&&(roll%100)<prob;
  unsigned expected_item=success?entry->params[ITEM_PARAM_EP]:item;
  if(!eligible)expected=saved;
  unsigned result=try_fix_broken_item((uint16_t)prob);
  unsigned passed=result==(success?item:0)&&party_characters[2].items[0]==expected_item&&rng_state.a==expected.a&&rng_state.b==expected.b;
  printf("REPAIR_RNG {\"index\":%u,\"passed\":%s,\"roll\":%u,\"result\":%u,\"expectedResult\":%u,\"item\":%u,\"expectedItem\":%u,\"rng\":[%u,%u],\"expectedRng\":[%u,%u],\"eligible\":%s}\n",index,passed?"true":"false",roll,result,success?item:0,party_characters[2].items[0],expected_item,rng_state.a,rng_state.b,expected.a,expected.b,eligible?"true":"false");
 }
 fclose(f);return 0;
}
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('build','runtime','native-source','original-assets','redux-assets','rng-review','scratch','output'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--diagnostic',action='store_true');a=p.parse_args();a.scratch=local_scratch(a.scratch)
 if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch/report required')
 review=json.loads(a.rng_review.read_text());assert review['Passed'] and not review['Pilot'] and review['Mismatches']==0
 source=a.native_source/'asm/inventory/try_fix_broken_item.asm';asm=source.read_text()
 assert 'LDA #99\n\tJSL RAND_MOD' in asm and 'BCS @NEXT_ITEM' in asm
 identities={str(path):sha(path) for path in (a.original_assets,a.redux_assets,a.rng_review,source,a.native_source/'src/game/inventory.c',Path(__file__))}
 a.scratch.mkdir(parents=True);linker.DRIVER=DRIVER;exe,build=linker.private_build(a)
 env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy');reports=[]
 for edition,pak in (('original',a.original_assets),('redux',a.redux_assets)):
  out=a.scratch/edition;out.mkdir()
  _,_,assets=read_pack(pak,a.native_source/'src/data/runtime_generated/asset_ids.h')
  table=assets['data/item_configuration_table.bin']
  layout=json.loads(subprocess.check_output([str(exe),'--layout'],timeout=10))
  size=layout['recordBytes']
  if len(table)!=254*size:raise ValueError('Re-review changed item layout')
  broken=[(n,table[n*size+layout['params']+layout['epi']]) for n in range(254) if table[n*size+layout['type']]==layout['brokenType']]
  if len(broken)!=13:raise ValueError('Re-review broken-item corpus')
  cases=[]
  def add(item,iq,prob,seed,present=1,kind='eligible'):cases.append((len(cases)+1,seed&65535,seed>>16,prob,item,iq,present,kind))
  for item,iq in broken:
   for prob in (0,25,100,101):
    for seed in range(1,17):add(item,iq,prob,0x56781234+seed*0x01010301)
  for item,iq in broken:
   add(item,iq,100,0x12345678,0,'Jeff-absent')
   if iq:add(item,iq-1,100,0x12345678,1,'low-IQ')
  add(0,255,100,0x12345678,1,'empty-slot');add(88,255,100,0x12345678,1,'non-broken')
  inputfile=out/'all.txt';inputfile.write_text('\n'.join(' '.join(map(str,r[:7])) for r in cases)+'\n')
  def execute(mode,session,file):
   session.mkdir(exist_ok=True)
   proc=subprocess.run([str(exe),str(pak.resolve()),str(session),str(file),mode,'1' if edition=='redux' else '0'],capture_output=True,env=env,timeout=35)
   (session/(mode+'.log')).write_bytes(proc.stdout+proc.stderr)
   if proc.returncode:raise RuntimeError('Native '+edition+' '+mode+' incomplete:'+str(proc.returncode))
   return proc.stdout.decode(errors='replace')
  output=execute('warm',out/'warm',inputfile)
  rows=[json.loads(line.split('REPAIR_RNG ',1)[1]) for line in output.splitlines() if line.startswith('REPAIR_RNG ')]
  if [r['index'] for r in rows]!=list(range(1,len(cases)+1)):raise RuntimeError('Native sample count/order differs')
  cold=[]
  # Fresh process replay for both chance results and no-roll exclusions.
  selected=[r for r in cases if r[3] in (25,100) and r[0]%16==1][:12]+cases[-4:]
  for c in selected:
   s=out/f'cold-{c[0]}';one=out/f'case-{c[0]}.txt';one.write_text(' '.join(map(str,c[:7]))+'\n')
   saved=execute('prepare',s,one)
   if 'REPAIR_SAVED '+str(c[0]) not in saved:raise RuntimeError('Private saved marker missing')
   result=execute('cold',s,one)
   got=[json.loads(line.split('REPAIR_RNG ',1)[1]) for line in result.splitlines() if line.startswith('REPAIR_RNG ')]
   if len(got)!=1 or got[0]['index']!=c[0]:raise RuntimeError('Cold sample incomplete')
   cold.extend(got)
  reports.append({'edition':edition,'brokenRecords':len(broken),'warmCases':len(rows),'coldCases':len(cold),'warmFailures':sum(not r['passed'] for r in rows),'coldFailures':sum(not r['passed'] for r in cold),'rows':rows,'cold':cold})
 if any(sha(Path(path))!=value for path,value in identities.items()):raise RuntimeError('Immutable input changed')
 passed=all(not r['warmFailures'] and not r['coldFailures'] for r in reports)
 report={'Passed':passed,'Cases':reports,'NativeLayout':layout,'PrivateBuild':build,'Identities':identities,'IndependentGeneratorReviewSha256':sha(a.rng_review),'OwnerSavesTouched':False,'Limits':['Real helper with prepared single-item inventories; full repair dialogue and inventory scan combinations remain separate.','Expected roll and next-state come from actual native serialized generator independently compared to original machine.','Does not independently execute the whole original repair routine or full RNG call timeline.','Cold cases load in a fresh process; v4 libc random is deliberately not forced or mocked.']}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'Passed':passed,'Summary':[{k:r[k] for k in ('edition','warmCases','coldCases','warmFailures','coldFailures')} for r in reports]}),flush=True)
 if not passed and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
