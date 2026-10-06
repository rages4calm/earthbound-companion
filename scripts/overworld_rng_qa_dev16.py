# SPDX-License-Identifier: GPL-3.0-or-later
"""Check frozen overworld random consumers with source-defined prepared gates.

Production functions and assets are used. The isolated spawn position cases
wrap terrain/path helpers to return declared blocked/open results. They do not
certify real map collision. No source or owner save is modified.
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
#include "core/mode_stack.h"
#include "core/state_dump.h"
#include "game/game_state.h"
#include "game/overworld.h"
#include "game/maternalbound.h"
#include "entity/entity.h"
#include "entity/sprite.h"
#include "data/assets.h"
#include "platform/pc_options.h"
extern int eb_platform_main(int,char**);
static unsigned surface,probes;
uint16_t __wrap_lookup_surface_flags(int16_t x,int16_t y,uint16_t size){(void)x;(void)y;(void)size;probes++;return surface;}
int main(int argc,char**argv){
 if(argc!=6)return 2;unsigned redux=atoi(argv[5]);char save[4096];snprintf(save,sizeof(save),"%s/private.srm",argv[2]);
 char*boot[]={"overworld-rng-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1",redux?"--redux-battle-fixture":"--inspect-shuffle","0"};
 unsigned n=sizeof(boot)/sizeof(boot[0]);if(!redux)n--;
 if(eb_platform_main(n,boot)||maternalbound_enabled()!=(redux!=0))return 3;
 load_sprite_data();load_enemy_spawn_data();if(!get_delivery_table())return 4;
 FILE*f=fopen(argv[3],"r");if(!f)return 5;
 unsigned i,kind,arg,x,y,enc,combo,seed,terrain,width,height;
 while(fscanf(f,"%u %u %u %u %u %u %u %u %u %u %u",&i,&kind,&arg,&x,&y,&enc,&combo,&seed,&terrain,&width,&height)==11){
  surface=terrain;probes=0;
  if(!strcmp(argv[4],"cold")){if(!state_dump_load_slots())return 6;}
  else {
   memset(&ow,0,sizeof(ow));memset(party_characters,0,sizeof(party_characters));memset(event_flags,0,sizeof(event_flags));
   entity_system_init();memset(entities.sprite_ids,0xff,sizeof(entities.sprite_ids));memset(sprite_vram_table,0,sizeof(sprite_vram_table));clear_overworld_spritemaps();
   game_state.party_count=game_state.player_controlled_party_count=1;game_state.party_members[0]=1;game_state.party_order[0]=1;
   game_state.leader_x_coord=1234;game_state.leader_y_coord=5678;
   party_characters[0].level=arg;party_characters[0].current_hp=100;party_characters[0].current_hp_target=100;party_characters[0].max_hp=100;
   pc_options.no_homesickness=kind==1&&x==2;party_characters[0].afflictions[0]=kind==1&&x==1;
   ow.loaded_map_tile_combo=combo;ow.enemy_spawn_range_width=width;ow.enemy_spawn_range_height=height;
   ow.enemy_spawn_counter=kind==4?15:0;ow.overworld_enemy_maximum=(kind==5||kind==7)?16:0;ow.spawning_enemy_group=0xffff;
   if(kind==2){const DeliveryEntry*t=get_delivery_table();event_flag_set(t[arg].event_flag);}
   if(kind>=3&&enc){const uint8_t*p=ASSET_DATA(ASSET_DATA_ENEMY_PLACEMENT_GROUPS_PTR_TABLE_BIN);const uint8_t*d=ASSET_DATA(ASSET_DATA_ENEMY_PLACEMENT_GROUPS_BIN);unsigned off=(p[enc*4]|p[enc*4+1]<<8|p[enc*4+2]<<16)-0xd0bbac;unsigned flag=d[off]|d[off+1]<<8;if(arg&&flag)event_flag_set(flag);}
   rng_state.a=seed&65535;rng_state.b=seed>>16;
   if(!strcmp(argv[4],"prepare")){if(!state_dump_save_slots())return 7;printf("OW_SAVED %u\n",i);continue;}
  }
  RNGState before=rng_state,states[128];unsigned rolls[128];for(unsigned j=0;j<128;j++){rolls[j]=rng_next_byte();states[j]=rng_state;}rng_state=before;
  unsigned value=0;
  if(kind==0)get_delivery_sprite_and_placeholder(arg+1);
  else if(kind==1)value=attempt_homesickness();
  else if(kind==2)spawn_delivery_entities();
  else if(kind==6){ow.psi_teleport_style=arg;ModeState st={0};st.teleport.phase=TP_SETUP;mode_step_teleport(&st);value=ow.psi_teleport_beta_angle;}
  else if(kind>=3)attempt_enemy_spawn(x,y,enc);
  else return 8;
  printf("OW_RNG {\"index\":%u,\"value\":%u,\"status\":%u,\"group\":%u,\"count\":%u,\"probes\":%u,\"counter\":%u,\"before\":[%u,%u],\"after\":[%u,%u],\"rolls\":[",i,value,party_characters[0].afflictions[6],ow.spawning_enemy_group,ow.overworld_enemy_count,probes,ow.enemy_spawn_counter,before.a,before.b,rng_state.a,rng_state.b);
  for(unsigned j=0;j<128;j++)printf("%s%u",j?",":"",rolls[j]);printf("],\"states\":[");for(unsigned j=0;j<128;j++)printf("%s[%u,%u]",j?",":"",states[j].a,states[j].b);printf("],\"entities\":[");unsigned found=0;for(unsigned j=0;j<MAX_ENTITIES;j++)if(entities.script_table[j]!=-1){printf("%s[%u,%d,%d,%d,%d,%d]",found++?",":"",j,entities.sprite_ids[j],entities.npc_ids[j],entities.abs_x[j],entities.abs_y[j],entities.weak_enemy_value[j]);}puts("]}");
 }
 return 0;
}
'''

def private_build(a):
 build=a.build.resolve();out=a.scratch/'production-driver';out.mkdir()
 entry=next(x for x in json.loads((build/'compile_commands.json').read_text(encoding='utf-8')) if x['file'].endswith('/port/unix/main.c'))
 if '"' in entry['command'] or "'" in entry['command']:raise ValueError('Review compiler quoting')
 flags=entry['command'].split();compiler=Path(flags[0]);toolchain=compiler.parent
 def run(cmd,name):
  r=subprocess.run(list(map(str,cmd)),cwd=build,capture_output=True,timeout=60);(out/name).write_bytes(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(name+': '+r.stderr.decode(errors='replace'))
 library=build/'game_lib/libearthbound_game.a';original=sha(library)
 source=out/'driver.c';source.write_text(DRIVER,encoding='utf-8');obj=out/'driver.c.obj'
 flags[flags.index('-o')+1]=str(obj);flags[flags.index('-c')+1]=str(source);run(flags,'compile.log')
 ninja=(build/'build.ninja').read_text(encoding='utf-8');m=re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_Release (.*?)\n(.*?)(?=\n\n)',ninja,re.M|re.S)
 objects=m[1].split(' | ',1)[0].split();libraries=re.search(r'^  LINK_LIBRARIES = (.*)$',m[2],re.M)[1].split()
 main=next(x for x in objects if x.replace('\\','/').endswith('/main.c.obj'));copied=out/'platform-main.c.obj';shutil.copy2(build/main,copied)
 run([toolchain/'objcopy.exe','--redefine-sym','main=eb_platform_main',copied],'main.log');objects=[str(copied) if x==main else str(build/x) for x in objects]
 exe=out/'driver.exe';run([compiler,'-O3','-DNDEBUG',obj,*objects,'-o',exe,'-Wl,--wrap=lookup_surface_flags',*libraries],'link.log');shutil.copy2(a.runtime/'SDL2.dll',out/'SDL2.dll')
 if sha(library)!=original:raise RuntimeError('Shared library changed')
 return exe,{'ProductionPlayerSha256':sha(build/'earthbound.exe'),'ProductionLibrarySha256':original,'DriverSha256':sha(exe),'DriverSourceSha256':sha(source),'ProductionLibraryUnedited':True,'PrivateTerrainWrapper':'Declared flags replace only lookup_surface_flags in isolated position cases.'}

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('build','runtime','native-source','original-assets','redux-assets','rng-review','scratch','output'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--diagnostic',action='store_true');p.add_argument('--legacy-nonzero-ranges',action='store_true',help='Exclude zero-range controls when recording the uncorrected build.');a=p.parse_args();a.scratch=local_scratch(a.scratch)
 if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch/output required')
 review=json.loads(a.rng_review.read_text(encoding='utf-8'))
 if not review['Passed'] or review['Pilot'] or review['Mismatches']:raise ValueError('Complete independent generator review required')
 files=[Path(__file__),a.original_assets,a.redux_assets,a.rng_review,a.runtime/'provenance.json']+[a.native_source/'src/game'/n for n in ('overworld.c','overworld_spawn.c','overworld_teleport.c')]+[a.native_source/'asm/overworld'/n for n in ('attempt_homesickness.asm','spawn_delivery_entities.asm','get_delivery_sprite_and_placeholder.asm','attempt_enemy_spawn.asm','teleport/init_psi_teleport_beta.asm')]
 identities={str(x):sha(x) for x in files};a.scratch.mkdir(parents=True);exe,build=private_build(a);reports=[]
 env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
 for mode,pack in (('original',a.original_assets),('redux',a.redux_assets)):
  out=a.scratch/mode;out.mkdir();assets=read_pack(pack,a.native_source/'src/data/runtime_generated/asset_ids.h')[2]
  delivery=assets['data/timed_delivery_table.bin'];signs=assets['data/for_sale_sign_sprite_table.bin'];sector=assets['data/per_sector_attributes.bin'];tsp=assets['data/global_map_tilesetpalette_data.bin'];ptr=assets['data/enemy_placement_groups_ptr_table.bin'];groups=assets['data/enemy_placement_groups.bin']
  rows=[];seeds=[(0x56781234+i*0x01010301)&0xffffffff for i in range(1,65)]
  def add(kind,arg=0,x=0,y=0,enc=0,combo=0,seed=1,terrain=0xd0,width=8,height=8,label=''):
   rows.append({'input':(len(rows)+1,kind,arg,x,y,enc,combo,seed,terrain,width,height),'label':label})
  for kind in (0,2):
   for idx in range(10):
    for seed in seeds[:16]:add(kind,idx,seed=seed,label='delivery placeholder' if kind==0 else 'pending delivery reload')
  for level in (1,15,16,30,31,45,46,60,61,75,76,90,91,99):
   for gate in range(3):
    for seed in seeds:add(1,level,x=gate,seed=seed,label='homesickness level/gate')
  categories={}
  for y in range(160):
   for x in range(128):
    off=(y//2)*64+(x//4)*2;cat=sector[off]&7
    if cat not in categories:categories[cat]=(x,y)
  if any(c>5 for c in categories):raise ValueError('Source unspecified butterfly rate categories require separate audit')
  for cat,(x,y) in categories.items():
   for seed in seeds:add(4,x=x,y=y,seed=seed,label='butterfly source rate '+str(cat))
  # Use real placement records, with zero enemy capacity isolating the two
  # selection calls. Position probes use the same real group records.
  selected=[]
  for enc in range(1,len(ptr)//4):
   off=int.from_bytes(ptr[enc*4:enc*4+3],'little')-0xd0bbac
   if not 0<=off<len(groups)-4:raise ValueError('Invalid actual placement pointer')
   if groups[off+2] or groups[off+3]:selected.append(enc)
   if len(selected)==12:break
  for enc in selected:
   for alt in (0,1):
    for seed in seeds:add(3,alt,enc=enc,combo=tsp[0]>>3,seed=seed,label='normal source chance/group')
  for seed in seeds[:16]:add(3,enc=0,seed=seed,label='empty encounter consumes no RNG')
  for style in (2,4):
   for seed in seeds:add(6,style,seed=seed,label='teleport beta initial angle')
  for enc in selected[:3]:
   for seed in seeds[:16]:add(5,enc=enc,combo=tsp[0]>>3,seed=seed,label='blocked spawn attempts')
   for width in ((8,) if a.legacy_nonzero_ranges else (0,8)):
    for seed in seeds[:16]:add(7,enc=enc,combo=tsp[0]>>3,seed=seed,terrain=0,width=width,height=width,label='prepared open spawn/weak value')
  def execute(action,session,tests):
   session.mkdir(exist_ok=True);file=session/(action+'.tsv');file.write_text(''.join(' '.join(map(str,r['input']))+'\n' for r in tests),encoding='utf-8')
   q=subprocess.run([str(exe),str(pack.resolve()),str(session),str(file),action,str(int(mode=='redux'))],cwd=session,env=env,capture_output=True,timeout=120);(session/(action+'.log')).write_bytes(q.stdout+q.stderr)
   if q.returncode:raise RuntimeError(mode+' '+action+' return '+str(q.returncode)+q.stderr.decode(errors='replace')[-1800:])
   got=[json.loads(s[7:]) for s in q.stdout.decode(errors='replace').splitlines() if s.startswith('OW_RNG ')]
   if action=='prepare':
    if 'OW_SAVED '+str(tests[0]['input'][0]) not in q.stdout.decode():raise ValueError('Missing save marker')
   elif [g['index'] for g in got]!=[r['input'][0] for r in tests]:raise ValueError('Incomplete ordered corpus')
   return got
  def check(row,got):
   i,kind,arg,x,y,enc,combo,seed,terrain,width,height=row['input'];rolls=got['rolls'];calls=0;expected={}
   if kind in (0,2):
    sprite=int.from_bytes(delivery[arg*20:arg*20+2],'little');calls=int(sprite==0)
    if not sprite:sprite=int.from_bytes(signs[(rolls[0]&3)*2:(rolls[0]&3)*2+2],'little')
    expected['entities']=[[0,sprite,65535,0,0,0]]
   elif kind==1:
    bracket=(arg-1)//15;prob=[0,100,150,200,250,0][bracket] if bracket<6 else 0
    calls=int(x==0 and prob!=0);expected['status']=int(calls and rolls[0]%(prob+1)==0)
   elif kind==4:
    rate=[2,0,1,0,5,1][sector[(y//2)*64+(x//4)*2]&7];calls=1;expected['group']=481 if rolls[0]%100<rate else 65535;expected['count']=0;expected['probes']=0;expected['counter']=16
   elif kind==6:
    calls=1;expected['value']=rolls[0]<<8
   elif kind in (3,5,7):
    expected={'count':0,'probes':0,'counter':1,'group':65535}
    if enc:
     off=int.from_bytes(ptr[enc*4:enc*4+3],'little')-0xd0bbac;flag=int.from_bytes(groups[off:off+2],'little');alt=bool(arg and flag);chance=groups[off+3 if alt else off+2];calls=1
     if (rolls[0]*100)>>8<chance:
      calls=2;target=(8 if alt and groups[off+2] else 0)+(rolls[1]&7);acc=0;offset=off+4
      while True:
       acc+=groups[offset]
       if target<acc:break
       offset+=3
       if offset+3>len(groups):raise ValueError('Source group range invalid')
      expected['group']=int.from_bytes(groups[offset+1:offset+3],'little')
      if kind in (5,7):
       bptr=assets['data/btl_entry_ptr_table.bin'];bgroup=assets['data/enemy_battle_groups_table.bin'];conf=assets['data/enemy_configuration_table.bin'];gid=expected['group'];boff=int.from_bytes(bptr[gid*8:gid*8+3],'little')-0xd0d52d;enemies=[]
       while bgroup[boff]!=255:enemies.extend([int.from_bytes(bgroup[boff+1:boff+3],'little')]*bgroup[boff]);boff+=3
       if len(enemies)>3:raise ValueError('Position corpus needs more precomputed random states')
       placed=[];probes=0
       for enemy in enemies:
        if kind==7 and conf[enemy*94+32]&4:
         xo=rolls[calls]%width if width else rolls[calls];yo=rolls[calls+1]%height if height else rolls[calls+1];weak=rolls[calls+2];calls+=3;probes+=1
         sprite=int.from_bytes(conf[enemy*94+30:enemy*94+32],'little');placed.append([len(placed),sprite,gid+32768,(x*8+xo)*8,(y*8+yo)*8,weak])
        else:calls+=40;probes+=20
       expected['probes']=probes;expected['count']=len(placed);expected['entities']=placed
   expected['after']=got['states'][calls-1] if calls else got['before']
   errors={k:{'expected':v,'actual':got[k]} for k,v in expected.items() if got[k]!=v}
   # Keep reports compact; sampled rolls/next states remain in the private log.
   actual={k:v for k,v in got.items() if k not in ('rolls','states')}
   return {'input':row['input'],'label':row['label'],'expectedCalls':calls,'expected':expected,'actual':actual,'passed':not errors,'errors':errors}
  warm=[check(r,g) for r,g in zip(rows,execute('warm',out/'warm',rows))];cold=[]
  selectedcold=[next(r for r in rows if r['input'][1]==k) for k in (0,1,2,3,4,5,6,7)]
  selectedcold[1]=next(r for r in rows if r['input'][1]==1 and r['input'][2]==16 and r['input'][3]==0)
  for k in (5,7):selectedcold[k]=rows[next(r['input'][0]-1 for r in warm if r['input'][1]==k and r['expectedCalls']>2)]
  for j,r in enumerate(selectedcold):
   session=out/f'cold-{j}';execute('prepare',session,[r]);cold.append(check(r,execute('cold',session,[r])[0]))
  reports.append({'mode':mode,'warmCases':len(warm),'coldCases':len(cold),'warmFailures':sum(not r['passed'] for r in warm),'coldFailures':sum(not r['passed'] for r in cold),'warm':warm,'cold':cold,'SectorCategories':sorted(categories)})
 if any(sha(Path(p))!=v for p,v in identities.items()):raise RuntimeError('Immutable input changed')
 passed=all(not r['warmFailures'] and not r['coldFailures'] for r in reports)
 result={'format':'overworld-rng-consumer-dev16-v1','Passed':passed,'LegacyNonzeroRangesOnly':a.legacy_nonzero_ranges,'PrivateBuild':build,'InputIdentities':identities,'Modes':reports,'OwnerSavesTouched':False,'FullPlaythroughVerified':False,'Limits':['Actual production consumers with prepared event/level/capacity gates. Preceding quests, visible sprites and sounds are excluded.','Normal spawn chance uses the source MULT168 then XBA formula, butterfly uses byte modulo100. Whole original spawn routine is not executed by this runner.','Capacity-zero selection and private blocked/open-terrain probes check production allocations, position rolls and weak values but exclude real map collision and full spawn timeline.','Teleport controls execute actual TP_SETUP and its first no-entity animation step; destinations, full flight and collisions are excluded.','F6 cases verify serialized restoration; phone-save RNG timeline and full story are excluded.']}
 result['FrozenBuildProvenance']=json.loads((a.runtime/'provenance.json').read_text(encoding='utf-8'))
 result['AuditSourceInputsAreNotBuildAttestation']=True
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'Passed':passed,'Summary':[{k:r[k] for k in ('mode','warmCases','coldCases','warmFailures','coldFailures')} for r in reports]}),flush=True)
 if not passed and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
