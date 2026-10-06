# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared source doorway with ordinary SDL movement and cold continuation.

Links unchanged frozen production objects. The external controller journal is
separate from F6. No coordinates, script PCs, terrain, party or event flags are
modified after the initial source-context preparation.
"""
import argparse, hashlib, json, os, re, shutil, subprocess
from pathlib import Path
import yaml
import battle_action_catalog_qa as frozen
from check_jev_observer_parity import local_scratch
from build_maternalbound_pack import read_pack
from redux_special_movement_integration_qa import parse_extra_tables

DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "core/memory.h"
#include "core/mode_stack.h"
#include "core/state_dump.h"
#include "game/game_state.h"
#include "game/overworld.h"
#include "game/position_buffer.h"
#include "game/map_loader.h"
#include "game/maternalbound.h"
#include "game/audio.h"
#include "entity/entity.h"
#include "platform/platform.h"
#include "platform/pc_options.h"
#include "data/event_script_data.h"
#include "snes/ppu.h"
#include "include/pad.h"
extern int eb_platform_main(int,char**);
static unsigned frames,stage,ticks,changed,doors,saved,exhausted,recovered;
static unsigned follow_calls,follow_checks,follow_failures;
extern void __real_update_follower_state(int16_t);
void __wrap_update_follower_state(int16_t e){
 int p=entities.var[1][e];unsigned live=game_state.camera_mode!=3&&!ow.battle_swirl_countdown&&!ow.enemy_has_been_touched&&!ow.battle_mode&&p>=0&&p<6;
 PositionBufferEntry entry={0};if(live)entry=pb.player_position_buffer[party_characters[p].position_index&255];
 unsigned moves=live&&(game_state.leader_moved||entry.walking_style==12);
 __real_update_follower_state(e);follow_calls++;
 if(live){follow_checks+=2;follow_failures+=entities.directions[e]!=entry.direction;follow_failures+=entities.surface_flags[e]!=entry.tile_flags;}
 if(moves){follow_checks+=2;follow_failures+=entities.abs_x[e]!=entry.x_coord;follow_failures+=entities.abs_y[e]!=entry.y_coord;}
}
static unsigned slot(unsigned i){return game_state.party_entity_slots[i*2]|game_state.party_entity_slots[i*2+1]<<8;}
static const char*folder;
static unsigned held;
static void input(unsigned pad){
 char path[4096];snprintf(path,sizeof(path),"%s/input.replay",folder);
 FILE*f=fopen(path,"wb");if(!f)exit(20);fprintf(f,"0 %x\n",pad);fclose(f);
 platform_input_shutdown();pc_input_script_path=path;
 /* The platform copies the file contents at init; path lives until that call. */
 if(!platform_input_init())exit(21);platform_input_poll();platform_input_poll();held=pad;
}
static void snap(const char*tag){
 printf("QA_TERRAIN {\"tag\":\"%s\",\"frames\":%u,\"stage\":%u,\"ticks\":%u,\"depth\":%u,\"top\":%u,\"mode\":%u,\"style\":%u,\"xy\":[%u,%u],\"frac\":[%u,%u],\"surface\":%u,\"index\":%u,\"timers\":[%u,%u],\"running\":%u,\"runFlag\":%u,\"moving\":%u,\"doors\":%u,\"held\":%u,\"exhausted\":%u,\"recovered\":%u,\"entities\":[",
 tag,frames,stage,ticks,g_mode_stack.depth,g_mode_stack.mode[g_mode_stack.depth-1],game_state.character_mode,game_state.walking_style,game_state.leader_x_coord,game_state.leader_y_coord,game_state.leader_x_frac,game_state.leader_y_frac,game_state.trodden_tile_type,game_state.position_buffer_index,ow.redux_primary_timer,ow.redux_secondary_timer,maternalbound_running(),event_flag_get(65),changed,doors,held,exhausted,recovered);
 for(unsigned i=0;i<4;i++){unsigned e=slot(i),p=(unsigned)entities.var[1][e];printf("%s[%u,%d,%d,%d,%u,%d,%d,%u,%u,%u,%d,%d,%u,%u,%u,%d,%u]",i?",":"",e,entities.sprite_ids[e],entities.abs_x[e],entities.abs_y[e],entities.walking_styles[e],entities.var[7][e],entities.move_callback[e],p<4?party_characters[p].position_index:65535,entities.surface_flags[e],entities.directions[e],entities.var[0][e],entities.var[1][e],entities.graphics_ptr_hi[e],entities.graphics_ptr_lo[e],entities.graphics_sprite_bank[e],entities.var[3][e],entities.overlay_flags[e]);}
 unsigned history=2166136261u;const unsigned char*b=(const unsigned char*)pb.player_position_buffer;for(unsigned i=0;i<sizeof(pb.player_position_buffer);i++)history=(history^b[i])*16777619u;
 printf("],\"hp\":[%u,%u,%u,%u],\"party\":[%u,%u,%u,%u],\"pending\":%u,\"battle\":%u,\"historyHash\":%u,\"followerCalls\":%u,\"followerAssertions\":%u,\"followerFailures\":%u}\n",party_characters[0].current_hp,party_characters[1].current_hp,party_characters[2].current_hp,party_characters[3].current_hp,game_state.party_members[0],game_state.party_members[1],game_state.party_members[2],game_state.party_members[3],ow.pending_interactions,ow.battle_mode,history,follow_calls,follow_checks,follow_failures);fflush(stdout);
}
int main(int argc,char**argv){
 if(argc!=8)return 2;unsigned original=atoi(argv[3]),ghost=atoi(argv[4]),kind=atoi(argv[5]),sprint=atoi(argv[6]),scene=atoi(argv[7]);folder=argv[2];
 unsigned smallx=scene?1872:1976,smally=scene?3096:2632;
 char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",folder);
 char*boot[]={"terrain-parent-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1",original?"--inspect-shuffle":"--redux-battle-fixture","0"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0])-(original?1:0),boot)!=0||maternalbound_enabled()==original)return 3;
 platform_max_frames=0;game_set_fast_forward(true);audio_init();pc_options.no_dad_calls=pc_options.no_homesickness=true;
 if(kind==2){
  if(!state_dump_load_slots())return 4;
  char path[4096];snprintf(path,sizeof(path),"%s/controller.tsv",folder);FILE*f=fopen(path,"rb");if(!f||fscanf(f,"%u %u %u %u %u %u %u %u",&frames,&stage,&ticks,&changed,&doors,&held,&exhausted,&recovered)!=8)return 5;fclose(f);input(held);snap("restored");
 }else{
  load_title_screen_script_data();memset(event_flags,0,sizeof(event_flags));event_flag_set(11);
  game_state.party_count=game_state.player_controlled_party_count=4;game_state.current_party_members=15;game_state.party_npc_1=game_state.party_npc_2=0;
  for(unsigned i=0;i<6;i++)game_state.party_members[i]=game_state.party_order[i]=i<4?i+1:0;
  for(unsigned i=0;i<4;i++){CharStruct*c=&party_characters[i];memset(c,0,sizeof(*c));c->level=30;c->max_hp=c->current_hp=c->current_hp_target=300;c->max_pp=c->current_pp=c->current_pp_target=100;}
  if(ghost){party_characters[1].afflictions[0]=1;party_characters[1].current_hp=party_characters[1].current_hp_target=0;}
  game_state.leader_x_coord=scene?2864:6064;game_state.leader_y_coord=scene?6808:152;initialize_overworld_state();ppu.inidisp=15;
  /* Isolate terrain/following from random enemy encounters, not map/NPC collision. */
  ow.enemy_spawns_enabled=0;if(!original)maternalbound_stamina_reset();
  memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_OVERWORLD;g_mode_stack.state[0].overworld.phase=OWP_RENDER;
  input(PAD_UP|(sprint?PAD_Y:0));snap("initial");
 }
 unsigned steps=0,lastmode=game_state.character_mode;
 while(frames<4000&&stage!=6&&++steps<50000){
  unsigned top=g_mode_stack.depth-1;GameMode mode=g_mode_stack.mode[top];
  core.pad1_pressed=platform_input_get_pad_new();core.pad1_held=platform_input_get_pad();core.pad1_autorepeat=core.pad1_pressed;
  if(mode==GAME_MODE_DOOR_TRANSITION&&g_mode_stack.state[top].door_transition.phase==DTR_BEGIN){doors++;snap("door-begin");}
  unsigned x=game_state.leader_x_coord,y=game_state.leader_y_coord;
  StepResult r=mode_dispatch_step(mode,&g_mode_stack.state[top]);
  if(r.kind==STEP_PUSH)mode_push(r.push_mode,r.push_init);else if(r.kind==STEP_POP)mode_pop(r.pop_result);else{host_process_frame();frames++;ticks++;}
  if(x!=game_state.leader_x_coord||y!=game_state.leader_y_coord)changed++;
  if(lastmode!=game_state.character_mode){lastmode=game_state.character_mode;snap("mode-change");}
  if(g_mode_stack.depth==1){
   unsigned next=stage;
   if(stage==0&&game_state.character_mode==3)next=1;
   else if(stage==1&&game_state.leader_y_coord>=smally+22)next=2;
   else if(stage==2&&game_state.leader_x_coord>=smallx+32)next=3;
   else if(stage==3&&game_state.leader_x_coord<=smallx+8){
    if(!original&&sprint){if(ow.redux_secondary_timer&128)next=2;else{next=7;exhausted=frames;}}
    else next=4;
   }
   else if(stage==7&&ticks>=700&&ow.redux_secondary_timer==143){next=4;recovered=frames;}
   else if(stage==4&&game_state.character_mode!=3)next=5;
   else if(stage==5&&ticks>=48)next=6;
   if(next!=stage){stage=next;ticks=0;unsigned pads[]={PAD_UP,PAD_DOWN,PAD_RIGHT,PAD_LEFT,PAD_UP,PAD_DOWN,0,0};input(pads[stage]|(sprint&&(stage<3||(!original&&stage==3))?PAD_Y:0));snap("stage-change");}
  }
  if(kind==1&&!saved&&stage==2&&ticks>=8&&g_mode_stack.depth==1){
   if(!state_dump_save_slots())return 6;char path[4096];snprintf(path,sizeof(path),"%s/controller.tsv",folder);FILE*f=fopen(path,"wb");fprintf(f,"%u %u %u %u %u %u %u %u\n",frames,stage,ticks,changed,doors,held,exhausted,recovered);fclose(f);saved=1;snap("saved");
  }
  if(frames%40==0&&r.kind==STEP_CONTINUE)snap("tick");
 }
 snap("final");audio_shutdown();return stage==6?(kind==1&&!saved?8:0):7;
}
'''

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def source_review(a):
 pin=subprocess.check_output(['git','-C',str(a.project.parent),'rev-parse','HEAD'],text=True).strip()
 if pin!=frozen.PIN:raise ValueError('Unreviewed Redux source revision')
 roms={'Original':a.original_rom.read_bytes(),'Redux':a.redux_rom.read_bytes()}
 packs={profile:read_pack(pak,a.native_source/'src/data/runtime_generated/asset_ids.h')[2]for profile,pak in (('Original',a.original_assets),('Redux',a.redux_assets))}
 for profile,assets in packs.items():
  attrs=assets['data/per_sector_attributes.bin']
  if len(attrs)!=5120 or attrs!=roms[profile][0x17b200:0x17b200+5120]:raise ValueError(profile+' sector attributes do not equal actual compiled table')
 attrs=packs['Redux']['data/per_sector_attributes.bin']
 def mode(x,y):
  i=((y//128)*32+x//256)*2;return int.from_bytes(attrs[i:i+2],'little')&7
 doors=yaml.safe_load((a.project/'map_doors.yml').read_text());cross=[]
 for by,row in doors.items():
  for bx,entries in row.items():
   for d in entries or []:
    if d['Type']!='door':continue
    x,y=bx*256+d['X']*8,by*256+d['Y']*8;dx,dy=d['Destination X']*8,d['Destination Y']*8;m,n=mode(x,y),mode(dx,dy)
    if m!=n and(m in(3,4,5)or n in(3,4,5)):cross.append(dict(xy=[x,y],destination=[dx,dy],modes=[m,n],eventFlag=d['Event Flag'],style=d['Style'],text=d['Text Pointer']))
 if len(cross)!=4 or {tuple(x['xy'])for x in cross}!={(6064,136),(1976,2624),(2856,6792),(1872,3088)}:raise ValueError('Special-mode doorway inventory changed')
 variants=parse_extra_tables(a.project/'ccscript/redux/four_frames_run.ccs');gfx=packs['Redux']['data/playable_character_graphics_table.bin']
 if gfx[272:280]!=b'MRWALK01':raise ValueError('Missing typed four-frame variants')
 for i,rows in enumerate(variants):
  if gfx[280+i*272:280+(i+1)*272]!=b''.join(v.to_bytes(2,'little')for row in rows for v in row):raise ValueError('Packed source graphics variants differ')
 if roms['Redux'][0x3ae3]!=6 or roms['Redux'][0x2f45:0x2f48]!=bytes([234])*3 or roms['Redux'][0x31cd:0x31d0]!=bytes([234])*3:raise ValueError('Active fast-terrain patch differs')
 names=('src/game/position_buffer.c','src/game/position_buffer.h','src/game/overworld.c','src/game/map_loader.c','src/game/door.c','src/game/maternalbound.c','src/game_main.c','src/entity/callroutine_screen.c','src/core/mode_stack.h','src/core/state_dump.c','port/unix/platform/sdl2_input.c')
 files={n:sha(a.complete_source/n)for n in names}
 for n,h in files.items():
  if sha(a.native_source/n)!=h:raise ValueError('Header/source context drift from exact frozen build: '+n)
 asm=('asm/overworld/party/load_party_at_map_position.asm','asm/overworld/party/get_party_member_sprite_id.asm','asm/overworld/update_follower_state.asm','asm/overworld/party/update_party_entity_graphics.asm','asm/overworld/load_sector_attributes.asm')
 return packs,dict(pinnedRevision=pin,doors=cross,crossModeDoorEntriesInventoried=len(cross),compiledSectorTablesByteEqual=True,activeTinyStyle=6,activeNonstandardRunNops=True,sourceFiles=files,originalAssembly={n:sha(a.complete_source/n)for n in asm},pinnedFiles={n:sha(a.project/n)for n in ('map_doors.yml','map_sectors.yml','ccscript/redux/fast_terrain.ccs','ccscript/redux/four_frames_run.ccs','ccscript/redux/run_stamina_mechanic.ccs')},romIdentities={profile:sha(path)for profile,path in (('Original',a.original_rom),('Redux',a.redux_rom))})

def graphics_checks(assets,state,ghost,profile):
 checks={}
 table=assets['data/playable_character_graphics_table.bin'];ptrs=assets['overworld_sprites/sprite_grouping_ptr_table.bin'];groups=assets['overworld_sprites/sprite_grouping_data.bin']
 for e in state.get('entities',[]):
  slot,_,x,y,style,var7,callback,index,surface,direction,char,party,*tail=e
  if callback!=2 or not 0<=char<4:continue
  dead=ghost and party==1;column=(5 if dead else 4)if state['mode']==3 else(1 if dead else 0)
  sprite=int.from_bytes(table[(char*8+column)*2:(char*8+column+1)*2],'little')
  offset=int.from_bytes(ptrs[sprite*4:sprite*4+4],'little')-0xef1a7f
  checks[f'liveGraphics.slot{slot}']=tail[:3]==[0,(offset+9)&65535,groups[offset+8]]
  if state['mode']==3:checks[f'tinyOverlayClear.slot{slot}']=tail[4]==0
 return checks
def build_probe(a):
 build=a.build.resolve();scratch=a.scratch.resolve()
 if sha(build/'earthbound.exe')!=sha(a.runtime/'player.exe'):raise ValueError('Frozen player build differs')
 library=build/'game_lib/libearthbound_game.a';library_hash=sha(library)
 commands=json.loads((build/'compile_commands.json').read_text());row=next(r for r in commands if r['file'].endswith('/port/unix/main.c'))
 if '\"'in row['command']or "'"in row['command']:raise ValueError('Review quoted compiler flags')
 flags=row['command'].split();compiler=flags[0];source=scratch/'battle_action_driver.c';source.write_text(DRIVER,encoding='utf-8');obj=scratch/'battle_action_driver.c.obj';flags[flags.index('-o')+1]=str(obj);flags[flags.index('-c')+1]=str(source)
 q=subprocess.run(flags,cwd=build,capture_output=True,timeout=60);(scratch/'compile.log').write_bytes(q.stdout+q.stderr)
 if q.returncode:raise RuntimeError(q.stderr.decode(errors='replace'))
 match=re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_Release (.*?)\n(.*?)(?=\n\n)',(build/'build.ninja').read_text(),re.M|re.S)
 objects=match[1].split(' | ',1)[0].split();libraries=re.search(r'^  LINK_LIBRARIES = (.*)$',match[2],re.M)[1].split()
 main=next(s for s in objects if s.replace('\\','/').endswith('/main.c.obj'));copied=scratch/'platform_main.c.obj';shutil.copy2(build/main,copied)
 q=subprocess.run([str(Path(compiler).parent/'objcopy.exe'),'--redefine-sym','main=eb_platform_main',str(copied)],cwd=build,capture_output=True,timeout=30);(scratch/'rename.log').write_bytes(q.stdout+q.stderr)
 if q.returncode:raise RuntimeError(q.stderr.decode(errors='replace'))
 objects=[str(copied)if s==main else str(build/s)for s in objects];exe=scratch/'terrain-parent-probe.exe'
 q=subprocess.run([compiler,'-O3','-DNDEBUG',str(scratch/'battle_action_driver.c.obj'),*objects,'-Wl,--wrap=update_follower_state','-o',str(exe),'-Wl,--major-image-version,0,--minor-image-version,0',*libraries],cwd=build,capture_output=True,timeout=60);(scratch/'link-observer.log').write_bytes(q.stdout+q.stderr)
 if q.returncode:raise RuntimeError(q.stderr.decode(errors='replace'))
 shutil.copy2(a.runtime/'SDL2.dll',scratch/'SDL2.dll')
 if sha(library)!=library_hash:raise ValueError('Frozen library changed')
 evidence=dict(executableSha256=sha(exe),driverSourceSha256=sha(source),productionExecutableSha256=sha(build/'earthbound.exe'),productionLibrarySha256=library_hash,platformMainObjectSha256=sha(build/main),sharedBuildModified=False,sharedSourceModified=False,readOnlyWrapper='update_follower_state: pre-call source buffer entry and post-call direction/surface/position assertions only')
 return exe,evidence
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('build','runtime','native-source','frozen-source','complete-source','project','original-assets','redux-assets','original-rom','redux-rom','scratch','output'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--diagnostic',action='store_true');p.add_argument('--pilot',action='store_true');p.add_argument('--pilot-scene',type=int,default=0);a=p.parse_args();a.scratch=local_scratch(a.scratch)
 if a.scratch.exists()or a.output.exists():raise ValueError('Fresh evidence names required')
 packs,source=source_review(a);identities={str(p):sha(p)for p in (a.runtime/'player.exe',a.runtime/'observer.exe',a.original_assets,a.redux_assets)};a.scratch.mkdir(parents=True);exe,build=build_probe(a);rows=[];skipped=0
 env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
 for scene in ((a.pilot_scene,)if a.pilot else(0,1)):
  for profile,pak in (('Original',a.original_assets),('Redux',a.redux_assets)):
   for ghost in (0,1):
    for sprint in (0,1):
     prev={}
     for kind,label in ((0,'warm'),(1,'checkpoint'),(2,'cold')):
      folder=a.scratch/f'{scene}-{profile}-{ghost}-{sprint}-{label}';folder.mkdir()
      if kind==2:
       if not (prev[1]/'controller.tsv').exists():skipped+=1;continue
       shutil.copytree(prev[1]/'saves',folder/'saves');shutil.copy2(prev[1]/'controller.tsv',folder/'controller.tsv')
      q=subprocess.run([str(exe.resolve()),str(pak.resolve()),str(folder.resolve()),str(int(profile=='Original')),str(ghost),str(kind),str(sprint),str(scene)],cwd=folder,env=env,capture_output=True,timeout=60);(folder/'native.log').write_bytes(q.stdout+q.stderr)
      stages=[json.loads(s.split(' ',1)[1])for s in q.stdout.decode(errors='replace').splitlines()if s.startswith('QA_TERRAIN ')];final=next((s for s in stages if s['tag']=='final'),{})
      checks={'nativeExitZero':q.returncode==0,'completeExit':final.get('stage')==6,'twoDoors':final.get('doors')==2,'ordinaryMovement':final.get('moving',0)>50,'finalSourceMode':final.get('mode')==(2 if scene else 0),'finalDepthOne':final.get('depth')==1,'realFollowerCallbacks':final.get('followerCalls',0)>100,'sourceFollowerWrites':final.get('followerFailures')==0}
      checks.update({'partyPreserved':final.get('party')==[1,2,3,4],'healthPreserved':final.get('hp')==[300,0 if ghost else 300,300,300],'pendingInteractionCleared':final.get('pending')==0,'noBattle':final.get('battle')==0,'normalStyleRestored':final.get('style')==0,'runFlagCleared':final.get('runFlag')==0})
      checks.update(graphics_checks(packs[profile],final,ghost,profile))
      tiny=next((s for s in stages if s['stage']==2 and s['tag']=='stage-change'),None)
      if kind!=2:
       checks['sourceTinyModeEntered']=tiny is not None and tiny['mode']==3 and tiny['style']==(10 if profile=='Original'else 6)
       if tiny:checks.update({'tiny.'+k:v for k,v in graphics_checks(packs[profile],tiny,ghost,profile).items()})
      if profile=='Redux'and sprint:
       checks['ordinaryInputExhaustedStamina']=0<final.get('exhausted',0)<1400
       checks['naturalCooldownRecovered']=0<final.get('recovered',0)-final.get('exhausted',0)<=900 and final.get('timers',[0,0])[1]==143
      if kind==1:checks['checkpointSaved']=any(s['tag']=='saved'for s in stages)
      if kind==2:
       for k in ('depth','top','mode','style','xy','frac','surface','index','timers','runFlag','moving','doors','entities','hp','party','pending','battle','historyHash','exhausted','recovered','frames'):checks['sameFinal.'+k]=final.get(k)==prev['final'].get(k)
       saved=next((s for s in prev['stages']if s['tag']=='saved'),{});restored=next((s for s in stages if s['tag']=='restored'),{})
       for k in ('depth','top','mode','style','xy','frac','surface','index','timers','runFlag','entities','hp','party','pending','battle','historyHash','frames'):checks['sameCheckpoint.'+k]=saved.get(k)==restored.get(k)
      row=dict(scene=scene,profile=profile,ghostFollower=bool(ghost),sprint=bool(sprint),continuation=label,nativeExit=q.returncode,checks=checks,passed=all(checks.values()),stages=stages);rows.append(row);prev[kind]=folder
      if kind==0:prev['final']=final
      if kind==1:prev['stages']=stages
      print(json.dumps({'scene':scene,'profile':profile,'ghost':ghost,'sprint':sprint,'kind':kind,'exit':q.returncode,'xy':final.get('xy'),'frames':final.get('frames'),'failed':[k for k,v in checks.items()if not v]}),flush=True)
      if a.pilot:break
     if a.pilot:break
    if a.pilot:break
   if a.pilot:break
  if a.pilot:break
 if any(sha(path)!=h for path,h in identities.items()):raise ValueError('Read-only input changed during tests')
 passed=bool(rows)and not skipped and all(r['passed']for r in rows)
 result=dict(schemaVersion=1,status='Passed'if passed else'Failed',allPassed=passed,sourceReview=source,rows=rows,toolSha256=sha(__file__),privateBuild=build,frozenPatchSha256=sha(a.frozen_source/'native-companion.patch'),runtimeIdentities=identities,readOnlyInputHashesChecked=True,executedAssertions=sum(len(r['checks'])for r in rows),executedFollowerAssertions=sum(r['stages'][-1].get('followerAssertions',0)for r in rows),executedProcesses=len(rows),coldCases=sum(r['continuation']=='cold'for r in rows),skippedCases=skipped,ownerSavesTouched=False,sharedBuildModified=False,fullConversionVerified=False,fullPlaythroughVerified=False,scope=['Prepared source entrance approaches; production root OVERWORLD ordinary SDL held inputs then actual entrance and return doors. Full corpus covers all four normal↔tiny door records; --pilot intentionally runs one branch only. All connecting Lost Underworld tiles or surrounding quest are not walked.','Only initial world, party, healthy/rested stamina and enemy-spawn isolation are prepared. External controller journal travels alongside actual F6; its input poll counter is not claimed serialized. Polling is primed outside the game loop to supply a stable held controller rather than a fabricated new-button edge on restore.','Actual Redux Y shuttles exhaust stamina through ordinary movement, then normal idle frames recover it; no entity moving bits or timer results supplied after entry. Source atomic timing proof remains in the earlier v8 report; no full source WaitFrame CPU oracle here.','Read-only forwarding wrapper verifies actual follower direction/surface/position writes against the source history entry from the production callback. Spacing index selection and render pixels are not independently machine-compared in this fixture.','Graphics pointers are checked against packed source table groups. entities.sprite_ids is an allocation diagnostic and remains stale when animation graphics change; it is not used as rendered sprite proof.','Tiny exit approach is aligned by ordinary directional input at destinationX+8. Earlier fixed-coordinate pilots that held Up from a misaligned fractional position stalled; those controller failures are not called native collision defects.','Player production library only; observer identity is provenance. Robot/Magicant parents, wet terrain, all stairs/ropes and campaign/audio parity remain separate gaps.'])
 a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');raise SystemExit(0 if result['allPassed']or a.diagnostic else 1)
if __name__=='__main__':main()
