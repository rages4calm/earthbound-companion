"""Verify v4 packs through the unchanged native wild chooser and loot/stat consumers.

This prepares placement/event states; it does not claim natural story reachability
or render/collision coverage. All output and save access is in private sessions.
"""
import argparse,json,os,struct,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
from build_maternalbound_pack import read_pack

DRIVER=helper.DRIVER[:helper.DRIVER.index('static unsigned pump(void)')]+r'''
int main(int argc,char**argv){
 if(argc!=3)return 2;
 char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 char*boot[]={"wild-choice-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--inspect-shuffle"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot)!=0)return 3;
 const unsigned char*ptr=ASSET_DATA(ASSET_DATA_ENEMY_PLACEMENT_GROUPS_PTR_TABLE_BIN);
 const unsigned char*data=ASSET_DATA(ASSET_DATA_ENEMY_PLACEMENT_GROUPS_BIN);
 const unsigned char*tsp=ASSET_DATA(ASSET_DATA_GLOBAL_MAP_TILESETPALETTE_DATA_BIN);
 entity_system_init();
 for(unsigned i=1;i<203;i++){
  unsigned at=(ptr[i*4]+256u*ptr[i*4+1]+65536u*ptr[i*4+2])-0xD0BBACu;
  unsigned flag=data[at]+256u*data[at+1];
  for(unsigned state=0;state<(flag?2:1);state++){
   if(flag){if(state)event_flag_set(flag);else event_flag_clear(flag);}
   unsigned seen[484]={0},misses=0;
   for(unsigned seed=1;seed<=4096;seed++){
    // Saturated entity budget isolates the actual placement chooser from
    // unrelated terrain/graphics, while still reading the selected lineup.
    ow.loaded_map_tile_combo=tsp[0]>>3;ow.overworld_enemy_maximum=0;
    ow.enemy_spawn_counter=0;ow.spawning_enemy_group=65535;
    rng_seed(seed*0x9e3779b9u);attempt_enemy_spawn(0,0,i);
    unsigned group=ow.spawning_enemy_group;
    if(group==65535)misses++;
    else if(group<484)seen[group]++;
    else return 4;
   }
   printf("QA_WILD {\"placement\":%u,\"state\":%u,\"misses\":%u,\"groups\":[",i,state,misses);
   unsigned n=0;for(unsigned group=0;group<484;group++)if(seen[group])printf("%s[%u,%u]",n++?",":"",group,seen[group]);printf("]}\n");
  }
 }
 return 0;
}
'''

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('build','runtime','native-source','assets','scratch','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();a.scratch=a.scratch.resolve()
 if a.scratch.exists():raise ValueError('Use a fresh private scratch folder')
 a.scratch.mkdir(parents=True);session=a.scratch/'session';session.mkdir()
 helper.DRIVER=DRIVER;exe,build=helper.private_build(a)
 _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h')
 run=subprocess.run([str(exe),str(a.assets.resolve()),str(session)],cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=120)
 log=a.scratch/'native.log';log.write_bytes(run.stdout+run.stderr)
 if run.returncode:raise RuntimeError('Native chooser failed: '+run.stderr.decode(errors='replace')[-1500:])
 rows=[json.loads(line[8:])for line in run.stdout.decode().splitlines()if line.startswith('QA_WILD ')]
 data=assets['data/enemy_placement_groups.bin'];ptr=assets['data/enemy_placement_groups_ptr_table.bin'];expected={}
 for i in range(1,203):
  at=(struct.unpack_from('<I',ptr,i*4)[0]&0xffffff)-0xd0bbac;flag=struct.unpack_from('<H',data,at)[0];rates=data[at+2:at+4];at+=4
  for state,rate in enumerate(rates):
   groups=set();weight=0
   while rate and weight<8:
    if data[at]:groups.add(struct.unpack_from('<H',data,at+1)[0])
    weight+=data[at];at+=3
   if state==0 or flag:expected[i,state]=(groups,rate)
 for row in rows:
  groups,rate=expected[row['placement'],row['state']];observed={x[0] for x in row['groups']}
  assert observed<=groups,(row,groups)
  assert row['misses']+sum(x[1]for x in row['groups'])==4096
  assert bool(observed)==bool(rate),(row,rate)
 assert len(rows)==len(expected) and {(r['placement'],r['state'])for r in rows}==set(expected)
 # Same getters and battler construction as normal gameplay, in the driver boot.
 import re
 gifts=re.findall(rb'SHUFFLE_GIFT (\d+) (\d+)',run.stderr);enemies=re.findall(rb'SHUFFLE_ENEMY (\d+) (\d+) (\d+) (\d+) (\d+)',run.stderr)
 npcs=assets['data/npc_config_table.bin'];enemy=assets['data/enemy_configuration_table.bin']
 assert len(gifts)==sum(npcs[i]==2 for i in range(0,len(npcs),17))
 for i,item in gifts:assert int(item)==struct.unpack_from('<I',npcs,int(i)*17+13)[0]
 assert len(enemies)==230
 for i,hp,offense,defense,speed in enemies:
  at=int(i)*94;assert (int(hp),int(offense),int(defense),int(speed))==(struct.unpack_from('<H',enemy,at+33)[0],enemy[at+56],enemy[at+58],enemy[at+60])
 coverage=sum({x[0]for x in r['groups']}==expected[r['placement'],r['state']][0] for r in rows)
 report=dict(Passed=True,AssetHash=helper.digest(a.assets),PrivateBuild=build,PlacementStates=len(rows),SamplesPerState=4096,StatesWithAllGroupsObserved=coverage,NativeGiftRecords=len(gifts),NativeEnemyRecords=len(enemies),NativeLogHash=helper.digest(log),FullPlaythroughVerified=False,Limits=['Prepared wild chooser/event states with saturated entity budget; no terrain, spawn entity, rendering or natural reachability certification.','Native consumer records, not unique reachable gift boxes or ordinary gameplay battles.'])
 a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
