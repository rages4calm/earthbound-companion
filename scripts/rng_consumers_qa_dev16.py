# SPDX-License-Identifier: GPL-3.0-or-later
"""Check actual frozen text, item-timer and level-growth RNG consumers.

The real production code is privately linked. Only static symbol visibility
changes in a copied inventory object; its text sections must stay byte-equal.
Expected rolls use the serialized generator already compared with original
machine execution. This is a consumer/call-count check, not full RNG timelines.
"""
import argparse, json, os, re, shutil, subprocess
from pathlib import Path
from build_maternalbound_pack import read_pack
from check_jev_observer_parity import local_scratch
from snes_movement_helpers_oracle import sha

DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "core/math.h"
#include "core/state_dump.h"
#include "game/game_state.h"
#include "game/inventory.h"
#include "game/overworld.h"
#include "game/display_text.h"
#include "game/display_text_internal.h"
#include "game/maternalbound.h"
#include "data/assets.h"
extern int eb_platform_main(int,char**);
extern bool ensure_stats_growth(void);
extern int16_t level_up_apply_stage(uint16_t,uint16_t,uint8_t);
extern void qa_initialize_item_transformation(uint16_t);
extern const uint8_t *dialogue_blob;
extern size_t dialogue_blob_size;
int main(int argc,char**argv){
 if(argc!=6)return 2;unsigned redux=atoi(argv[5]);char save[4096];snprintf(save,sizeof(save),"%s/private.srm",argv[2]);
 char*boot[]={"rng-consumer-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1",redux?"--redux-battle-fixture":"--inspect-shuffle","0"};
 unsigned n=sizeof(boot)/sizeof(boot[0]);if(!redux)n--;
 if(eb_platform_main(n,boot)||maternalbound_enabled()!=(redux!=0))return 3;
 if(!ensure_stats_growth())return 4;
 memset(&ow,0,sizeof(ow));game_state.camera_mode=0;process_item_transformations();
 FILE*f=fopen(argv[3],"r");if(!f)return 5;
 unsigned index,kind,arg,bound,seed,who,stage,oldlevel,base;
 while(fscanf(f,"%u %u %u %u %u %u %u %u %u",&index,&kind,&arg,&bound,&seed,&who,&stage,&oldlevel,&base)==9){
  if(!strcmp(argv[4],"cold")){if(!state_dump_load_slots())return 6;}
  else {
   memset(party_characters,0,sizeof(party_characters));memset(&ow,0,sizeof(ow));
   game_state.camera_mode=0;game_state.party_count=game_state.player_controlled_party_count=1;game_state.party_members[0]=who;
   rng_state.a=seed&65535;rng_state.b=seed>>16;
   set_argument_memory(bound);set_working_memory(0x87654321);
   CharStruct*c=&party_characters[who-1];
   c->base_offense=c->base_defense=c->base_speed=c->base_guts=c->base_vitality=c->base_iq=c->base_luck=base;
   c->vitality=c->iq=base;c->max_hp=c->max_pp=900;c->current_hp_target=c->current_pp_target=800;
   ItemTransformSaveState timer={0};
   if(kind==2){timer.time_until_next_item_transformation_check=1;timer.item_transformations_loaded=2;timer.loaded_transformations[0]=101;timer.loaded_transformations[1]=2;timer.loaded_transformations[2]=1;timer.loaded_transformations[3]=2;
    timer.loaded_transformations[4]=104;timer.loaded_transformations[5]=15;timer.loaded_transformations[6]=1;timer.loaded_transformations[7]=2;
    if(arg==1)ow.enemy_has_been_touched=1;else if(arg==2)ow.battle_swirl_countdown=1;else if(arg==3)ow.disabled_transitions=1;else if(arg==4)game_state.camera_mode=2;else if(arg==5)timer.time_until_next_item_transformation_check=2;
   }
   item_transform_savestate_unpack(&timer);
   if(!strcmp(argv[4],"prepare")){if(!state_dump_save_slots())return 7;printf("RNG_SAVED %u\n",index);continue;}
  }
  RNGState before=rng_state;unsigned roll=rng_next_byte();RNGState once=rng_state;rng_state=before;
  unsigned value=0,consumed=0;ItemTransformSaveState timer={0};
  if(kind==0){const uint8_t*saved=dialogue_blob;size_t savedsize=dialogue_blob_size;uint8_t command[]={0x21,(uint8_t)arg};dialogue_blob=command;dialogue_blob_size=2;ScriptReader reader={TEXT_SRC_DIALOGUE,0,2,-1};cc_1d_dispatch(&reader);value=get_working_memory();consumed=reader.ptr_off;dialogue_blob=saved;dialogue_blob_size=savedsize;}
  else if(kind==1){qa_initialize_item_transformation(arg);item_transform_savestate_pack(&timer);value=timer.loaded_transformations[arg*4+2];}
  else if(kind==2){process_item_transformations();item_transform_savestate_pack(&timer);value=timer.loaded_transformations[2];}
  else if(kind==3){value=(uint16_t)level_up_apply_stage(who,oldlevel,stage);}
  else return 8;
  printf("RNG_CONSUMER {\"index\":%u,\"value\":%u,\"roll\":%u,\"before\":[%u,%u],\"once\":[%u,%u],\"after\":[%u,%u],\"consumed\":%u,\"timer\":%u,\"active\":%u,\"slots\":[",
   index,value,roll,before.a,before.b,once.a,once.b,rng_state.a,rng_state.b,consumed,timer.time_until_next_item_transformation_check,timer.item_transformations_loaded);
  for(unsigned i=0;i<16;i++)printf("%s%u",i?",":"",timer.loaded_transformations[i]);puts("]}");
 }
 fclose(f);return 0;
}
'''

def private_build(a):
 build=a.build.resolve();out=a.scratch
 if sha(build/'earthbound.exe')!=sha(a.runtime/'player.exe'):raise ValueError('Runtime/build mismatch')
 entries=json.loads((build/'compile_commands.json').read_text(encoding='utf-8'))
 entry=next(x for x in entries if x['file'].endswith('/port/unix/main.c'))
 if '"' in entry['command'] or "'" in entry['command']:raise ValueError('Review compiler quoting')
 flags=entry['command'].split();compiler=Path(flags[0]);toolchain=compiler.parent
 def run(cmd,name,cwd=build):
  r=subprocess.run(list(map(str,cmd)),cwd=cwd,capture_output=True,timeout=60);(out/name).write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(name+': '+r.stderr.decode(errors='replace'))
 library=build/'game_lib/libearthbound_game.a';copied=out/library.name;original=sha(library);shutil.copy2(library,copied)
 member=out/'inventory.c.obj';run([toolchain/'ar.exe','x',library,member.name],'extract.log',out)
 symbols=('ensure_stats_growth','level_up_apply_stage','initialize_item_transformation.part.0')
 texts={}
 for i,symbol in enumerate(symbols):
  before=out/f'text-{i}-before.bin';after=out/f'text-{i}-after.bin'
  run([toolchain/'objcopy.exe','--dump-section','.text$'+symbol+'='+str(before),member],f'text-{i}-before.log')
  if not before.exists() or not before.stat().st_size:raise ValueError('Missing original compiled section '+symbol)
  run([toolchain/'objcopy.exe','--globalize-symbol',symbol,member],f'globalize-{i}.log')
  run([toolchain/'objcopy.exe','--dump-section','.text$'+symbol+'='+str(after),member],f'text-{i}-after.log')
  if before.read_bytes()!=after.read_bytes():raise ValueError('Changed production instructions')
  texts[symbol]=sha(before)
 run([toolchain/'objcopy.exe','--redefine-sym','initialize_item_transformation.part.0=qa_initialize_item_transformation',member],'rename-init.log')
 run([toolchain/'ar.exe','r',copied,member],'replace-private.log')
 textmember=out/'display_text.c.obj';run([toolchain/'ar.exe','x',library,textmember.name],'extract-text.log',out)
 textbefore=out/'reader-before.bin';textafter=out/'reader-after.bin'
 run([toolchain/'objcopy.exe','--dump-section','.text$script_read_byte='+str(textbefore),textmember],'reader-before.log')
 run([toolchain/'objcopy.exe','--globalize-symbol','dialogue_blob','--globalize-symbol','dialogue_blob_size',textmember],'globalize-text-data.log')
 run([toolchain/'objcopy.exe','--dump-section','.text$script_read_byte='+str(textafter),textmember],'reader-after.log')
 if not textbefore.exists() or textbefore.read_bytes()!=textafter.read_bytes():raise ValueError('Changed production ScriptReader instructions')
 texts['script_read_byte']=sha(textbefore)
 run([toolchain/'ar.exe','r',copied,textmember],'replace-private-text.log')
 source=out/'rng-consumer-driver.c';source.write_text(DRIVER,encoding='utf-8');obj=out/'rng-consumer-driver.c.obj'
 flags[flags.index('-o')+1]=str(obj);flags[flags.index('-c')+1]=str(source);run(flags,'compile.log')
 ninja=(build/'build.ninja').read_text(encoding='utf-8');m=re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_Release (.*?)\n(.*?)(?=\n\n)',ninja,re.M|re.S)
 objects=m[1].split(' | ',1)[0].split();libraries=re.search(r'^  LINK_LIBRARIES = (.*)$',m[2],re.M)[1].split()
 main=next(x for x in objects if x.replace('\\','/').endswith('/main.c.obj'));maincopy=out/'platform-main.c.obj';shutil.copy2(build/main,maincopy)
 run([toolchain/'objcopy.exe','--redefine-sym','main=eb_platform_main',maincopy],'main.log');objects=[str(maincopy) if x==main else str(build/x) for x in objects]
 indices=[i for i,x in enumerate(libraries) if x.replace('\\','/').endswith('game_lib/libearthbound_game.a')]
 if len(indices)!=1:raise ValueError('Changed link layout')
 libraries[indices[0]]=str(copied);exe=out/'rng-consumer-driver.exe'
 run([compiler,'-O3','-DNDEBUG',obj,*objects,'-o',exe,'-Wl,--major-image-version,0,--minor-image-version,0',*libraries],'link.log');shutil.copy2(a.runtime/'SDL2.dll',out/'SDL2.dll')
 if sha(library)!=original:raise RuntimeError('Shared library changed')
 return exe,{'ProductionPlayerSha256':sha(build/'earthbound.exe'),'ProductionLibrarySha256':original,'StaticTextByteIdentical':True,'StaticTextSha256':texts,'DriverSha256':sha(exe),'DriverSourceSha256':sha(source),'SharedBuildEdited':False}

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('build','runtime','native-source','original-assets','redux-assets','rng-review','scratch','output'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--diagnostic',action='store_true');a=p.parse_args();a.scratch=local_scratch(a.scratch)
 if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch and output required')
 review=json.loads(a.rng_review.read_text(encoding='utf-8'))
 if not review['Passed'] or review['Pilot'] or review['Mismatches']:raise ValueError('Passing complete generator comparison required')
 files=[a.original_assets,a.redux_assets,a.rng_review,Path(__file__),a.native_source/'src/game/inventory.c',a.native_source/'src/game/display_text_cc.c']
 files += [a.native_source/'asm'/x for x in ('text/ccs/get_random_number.asm','system/math/rand_mod.asm','overworld/initialize_item_transformation.asm','overworld/process_item_transformations.asm','text/calculate_stat_gain.asm','misc/level_up_char.asm')]
 identities={str(x):sha(x) for x in files};a.scratch.mkdir(parents=True);exe,build=private_build(a);reports=[]
 env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
 for mode,pack in (('original',a.original_assets),('redux',a.redux_assets)):
  out=a.scratch/mode;out.mkdir();assets=read_pack(pack,a.native_source/'src/data/runtime_generated/asset_ids.h')[2]
  dialogue=assets['dialogue/dialogue.bin'];growth=list(assets['data/stats_growth_vars.bin']);mod=list(assets['data/stat_gain_modifier_table.bin']);trans=list(assets['data/timed_item_transformation_table.bin'])
  rows=[]
  def add(kind,arg,bound,seed,who=1,stage=0,old=10,base=2,label=''):
   rows.append({'input':(len(rows)+1,kind,arg,bound,seed,who,stage,old,base),'label':label})
  seeds=[(0x56781234+i*0x01010301)&0xffffffff for i in range(1,17)]
  for literal in (0,1,2,3,7,15,99,255):
   for bound in ((0,1,2,99,255,256,32767,65535) if not literal else (0,65535)):
    for seed in seeds:add(0,literal,bound,seed,label='CC1D21 literal' if literal else 'CC1D21 argument')
  for slot in range(3):
   for seed in seeds:add(1,slot,0,seed,label='timer initialization')
  for gate in range(6):
   for seed in seeds:add(2,gate,0,seed,label='timer SFX reset / gate')
  for who in range(1,5):
   for stage in range(9):
    for old in (1,9,10,30,98):
     for base in (2,255):
      for seed in seeds[:4]:add(3,0,0,seed,who,stage,old,base,'level growth RNG')
  def execute(action,session,tests):
   session.mkdir(exist_ok=True);file=session/(action+'.tsv');file.write_text(''.join(' '.join(map(str,r['input']))+'\n' for r in tests),encoding='utf-8')
   q=subprocess.run([str(exe),str(pack.resolve()),str(session),str(file),action,str(int(mode=='redux'))],cwd=session,env=env,capture_output=True,timeout=60);(session/(action+'.log')).write_bytes(q.stdout+q.stderr)
   if q.returncode:raise RuntimeError(mode+' '+action+' failed '+str(q.returncode)+q.stderr.decode(errors='replace')[-1500:])
   got=[json.loads(line[len('RNG_CONSUMER '):]) for line in q.stdout.decode(errors='replace').splitlines() if line.startswith('RNG_CONSUMER ')]
   if action=='prepare':
    if 'RNG_SAVED '+str(tests[0]['input'][0]) not in q.stdout.decode():raise ValueError('Save marker missing')
   elif [x['index'] for x in got]!=[x['input'][0] for x in tests]:raise ValueError('Ordered native corpus incomplete')
   return got
  def check(test,actual):
   index,kind,arg,bound,seed,who,stage,old,base=test['input'];roll=actual['roll'];calls=1;expected={}
   if kind==0:
    limit=arg or bound;expected={'value':roll%(limit+1),'consumed':2}
   elif kind==1:expected={'value':(trans[arg*5+2]+roll%3-1)&255,'timer':60,'active':1}
   elif kind==2:
    calls=int(arg==0);expected={'value':(2+roll%3-1)&255 if arg==0 else 1,'timer':60 if arg==0 else 1,'active':2}
    expected['slots']=[101,2,expected['value'],1 if arg==0 else 2,104,15,1,1 if arg==0 else 2]+[0]*8
   else:
    if stage<7:
     diff=growth[(who-1)*7+stage]*old-(base-2)*10
     simple=stage in (4,5) and old<10
     calls=int(not simple and diff>0)
     gain=int(diff/10) if simple else int(diff*(mod[(old+1)%4]+roll%4-1)/50) if diff>0 else 0
     expected={'value':max(gain,0)}
    elif stage==7:
     potential=base*15-900;calls=int(potential<=1);expected={'value':potential if potential>1 else roll%3+1}
    else:
     potential=base*5-900;calls=int(who!=3 and potential<=1);expected={'value':0 if who==3 else potential if potential>1 else roll%3}
   expected['after']=actual['once'] if calls else actual['before']
   errors={k:{'expected':v,'actual':actual[k]} for k,v in expected.items() if actual[k]!=v}
   return {'input':test['input'],'label':test['label'],'expectedCalls':calls,'expected':expected,'actual':actual,'passed':not errors,'errors':errors}
  warm=[check(t,g) for t,g in zip(rows,execute('warm',out/'warm',rows))];cold=[]
  selected=[rows[0],rows[129],next(r for r in rows if r['input'][1]==1),next(r for r in rows if r['input'][1]==2 and r['input'][2]==0),next(r for r in rows if r['input'][1]==2 and r['input'][2]==1),next(r for r in rows if r['input'][1]==3 and r['input'][6]==7),next(r for r in rows if r['input'][1]==3 and r['input'][5]==3 and r['input'][6]==8)]
  for i,test in enumerate(selected):
   session=out/f'cold-{i}';execute('prepare',session,[test]);cold.append(check(test,execute('cold',session,[test])[0]))
  reports.append({'mode':mode,'warmCases':len(warm),'coldCases':len(cold),'warmFailures':sum(not x['passed'] for x in warm),'coldFailures':sum(not x['passed'] for x in cold),'warm':warm,'cold':cold})
 if any(sha(Path(path))!=value for path,value in identities.items()):raise RuntimeError('Immutable input changed')
 passed=all(not r['warmFailures'] and not r['coldFailures'] for r in reports)
 result={'format':'rng-consumer-qa-dev16-v1','Passed':passed,'PrivateBuild':build,'InputIdentities':identities,'Modes':reports,'IndependentGeneratorReviewSha256':sha(a.rng_review),'OwnerSavesTouched':False,'FullPlaythroughVerified':False,'Limits':['Prepared real consumer calls and fresh-process restores; not full preceding item/dialogue/level events.','Level formula controls mirror reviewed native arithmetic while verifying source-required RAND call sites. Complete original stat formula arithmetic and the diff=1 branch remain separate audit work.','Timer tests isolate initial/reset RNG and transition guards; item expiry and audible SFX are not covered here.','CC fixtures bind source-derived two-byte operands into a private copied data symbol. Original asset bytes and dispatcher/reader instructions are unchanged; story reachability is not claimed.','Single call/next state expectations rely on the separately independently compared native generator.']}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'Passed':passed,'Summary':[{k:x[k] for k in ('mode','warmCases','coldCases','warmFailures','coldFailures')} for x in reports]}),flush=True)
 if not passed and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
