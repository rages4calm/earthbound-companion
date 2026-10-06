# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared complete story parents and fresh-process mid-scene continuation.

Links unchanged frozen production objects. No scene-completion signal, actor PC
or branch result is injected after entry. The surrounding quest is prepared;
this does not replay the entire game or validate every audiovisual frame.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path
import battle_action_catalog_qa as frozen
from check_jev_observer_parity import local_scratch

DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "core/mode_stack.h"
#include "core/memory.h"
#include "core/state_dump.h"
#include "game/game_state.h"
#include "game/display_text.h"
#include "game/window.h"
#include "game/text.h"
#include "game/overworld.h"
#include "game/maternalbound.h"
#include "game/audio.h"
#include "game/map_loader.h"
#include "game/battle.h"
#include "entity/entity.h"
#include "platform/platform.h"
#include "platform/pc_options.h"
#include "data/assets.h"
#include "data/event_script_data.h"
#include "snes/ppu.h"
extern int eb_platform_main(int,char**);
static unsigned seen[1024],npcs[1600],scripts_init[1024],npcs_init[1600];
static unsigned steps,frames,waits,signals,camera2,letterbox,camera_min_y=65535,camera_max_y;
static unsigned first153z=65535,first157z=65535,warps[256];
static unsigned actual137pc,settle_frames;
static unsigned warp_order[32],warp_count;
static void observe(void){
 if(game_state.camera_mode==2)camera2=1;
 if(ow.redux_letterbox_active)letterbox=1;
 for(unsigned i=0;i<MAX_ENTITIES;i++)if(entities.script_table[i]>=0){
  int event=entities.script_table[i];if(event<1024)seen[event]=1;
  if(entities.npc_ids[i]<1600)npcs[entities.npc_ids[i]]=1;
  if(entities.npc_ids[i]==623){int bank=-1,endbank=-1;uint16_t begin=0,end=0;int s=entities.script_index[i];if(s>=0&&resolve_script_id(137,&bank,&begin)&&resolve_script_id(138,&endbank,&end)&&bank==endbank&&scripts.pc_bank[s]==bank&&scripts.pc[s]>=begin&&scripts.pc[s]<end)actual137pc=1;}
  if(event==153&&first153z==65535&&entities.abs_z[i]>0)first153z=entities.abs_z[i];
  if(event==157&&first157z==65535&&entities.abs_z[i]>0)first157z=entities.abs_z[i];
  if(event==898){unsigned y=(uint16_t)entities.abs_y[i];if(y<camera_min_y)camera_min_y=y;if(y>camera_max_y)camera_max_y=y;}
 }
}
static void array(const unsigned*a,unsigned n){unsigned comma=0;printf("[");for(unsigned i=0;i<n;i++)if(a[i])printf("%s%u",comma++?",":"",i);printf("]");}
static void snapshot(const char*tag,unsigned scene,unsigned kind){
 printf("QA_SCENE {\"tag\":\"%s\",\"scene\":%u,\"kind\":%u,\"steps\":%u,\"frames\":%u,\"depth\":%u,\"top\":%u,\"waits\":%u,\"signals\":%u,\"xy\":[%u,%u],\"camera\":%u,\"cameraFocus\":%d,\"cameraMode2Seen\":%u,\"letterboxSeen\":%u,\"letterboxFinal\":%u,\"cameraPanY\":[%u,%u],\"first153Z\":%u,\"first157Z\":%u,\"pending\":%u,\"money\":%u,\"walletBackup\":%u,\"partyCount\":%u,\"playerCount\":%u,\"party\":[",
 tag,scene,kind,steps,frames,g_mode_stack.depth,g_mode_stack.mode[g_mode_stack.depth-1],waits,signals,game_state.leader_x_coord,game_state.leader_y_coord,game_state.camera_mode,ow.camera_focus_entity,camera2,letterbox,ow.redux_letterbox_active,camera_min_y,camera_max_y,first153z,first157z,ow.pending_interactions,game_state.money_carried,game_state.wallet_backup,game_state.party_count,game_state.player_controlled_party_count);
 for(unsigned i=0;i<6;i++)printf("%s%u",i?",":"",game_state.party_members[i]);
 printf("],\"hp\":[");for(unsigned i=0;i<4;i++)printf("%s%u",i?",":"",party_characters[i].current_hp);
 printf("],\"flags\":[");unsigned comma=0;for(unsigned i=1;i<EVENT_FLAG_COUNT;i++)if(event_flag_get(i))printf("%s%u",comma++?",":"",i);
 printf("],\"scripts\":");array(seen,1024);printf(",\"npcs\":");array(npcs,1600);printf(",\"initialScripts\":");array(scripts_init,1024);printf(",\"initialNpcs\":");array(npcs_init,1600);printf(",\"warps\":");array(warps,256);printf(",\"remainingActors\":[");
 comma=0;for(unsigned i=0;i<MAX_ENTITIES;i++)if(entities.script_table[i]>=0&&((scene==1&&((entities.script_table[i]>=253&&entities.script_table[i]<=265&&entities.script_table[i]!=260)||entities.script_table[i]==897||entities.script_table[i]==898))||(scene==4&&entities.npc_ids[i]==484)||(scene==5&&entities.npc_ids[i]==538)||(scene==6&&entities.npc_ids[i]==489)))printf("%s%u",comma++?",":"",i);
 printf("],\"actual137PcObserved\":%u,\"npc677Bound\":%u,\"settleFrames\":%u,\"warpOrder\":[",actual137pc,find_entity_by_npc_id(677)>=0,settle_frames);for(unsigned i=0;i<warp_count;i++)printf("%s%u",i?",":"",warp_order[i]);puts("]}");
}
int main(int argc,char**argv){
 if(argc!=7)return 2;
 bool original=atoi(argv[3])!=0;unsigned scene=atoi(argv[4]),kind=atoi(argv[5]);uint32_t entry=strtoul(argv[6],NULL,16);char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 char*boot[]={"cutscene-parent-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1",original?"--inspect-shuffle":"--redux-battle-fixture","0"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0])-(original?1:0),boot)!=0||maternalbound_enabled()==original)return 3;
 char replay[4096];snprintf(replay,sizeof(replay),"%s/input.replay",argv[2]);pc_input_script_path=replay;platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 4;
 game_set_fast_forward(true);audio_init();load_title_screen_script_data();pc_options.no_dad_calls=pc_options.no_homesickness=true;
 if(kind!=2){
 memset(event_flags,0,sizeof(event_flags));event_flag_set(11);
 game_state.party_count=scene==1||scene>=4?2:1;game_state.player_controlled_party_count=scene>=4?2:1;game_state.current_party_members=scene>=4?3:scene==1?260:4;game_state.party_npc_1=game_state.party_npc_2=0;
 game_state.party_npc_1_id_copy=game_state.party_npc_2_id_copy=0;game_state.wallet_backup=1234;game_state.money_carried=scene==3?2:77;
 for(unsigned i=0;i<6;i++)game_state.party_members[i]=game_state.party_order[i]=i==0?(scene>=4?1:3):i==1?(scene>=4?2:scene==1?9:0):0;
 for(unsigned i=0;i<4;i++){CharStruct*c=&party_characters[i];memset(c,0,sizeof(*c));c->level=30;c->max_hp=c->current_hp=c->current_hp_target=300;c->max_pp=c->current_pp=c->current_pp_target=100;const uint8_t name[]={0x7e,0x91,0xa4,0x99,0xa6,0x95};maternalbound_set_character_name(i,name,6);}
 if(scene==1){unsigned flags[]={129,323,334,22,338};for(unsigned i=0;i<5;i++)event_flag_set(flags[i]);game_state.leader_x_coord=5029;game_state.leader_y_coord=406;party_characters[2].items[0]=104;}
 else if(scene>=4){event_flag_set(scene==4?296:scene==5?46:scene==6?297:298);game_state.leader_x_coord=scene==4?6728:scene==5?5536:scene==7?7640:7808;game_state.leader_y_coord=scene==4?9336:scene==5?8976:scene==6?9320:9456;}
 else{game_state.leader_x_coord=7824;game_state.leader_y_coord=2872;if(!original)event_flag_set(798);}
 initialize_overworld_state();ppu.inidisp=15;ow.battle_mode=bt.battle_mode_flag=0;
 window_system_init();init_used_bg2_tile_map();text_setup_bg3();text_upload_font_tiles();text_load_window_gfx();text_load_flavour_palette(0);create_window(WINDOW_TEXT_STANDARD);set_window_focus(WINDOW_TEXT_STANDARD);dt.instant_printing=0;
 observe();memcpy(scripts_init,seen,sizeof(seen));memcpy(npcs_init,npcs,sizeof(npcs));
 memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=scene>=3?GAME_MODE_OVERWORLD:GAME_MODE_NONE;g_mode_stack.state[0].overworld.phase=OWP_RENDER;
 if(scene==1||scene==3||scene==7){ModeState text={0};if(!dt_make_child_init(&text,entry))return 6;mode_push(GAME_MODE_DISPLAY_TEXT,&text);}
 }else{if(!state_dump_load_slots())return 5;snapshot("cold-restored",scene,kind);}
 unsigned saved=0;
 while((scene==4||scene==6?frames<240:scene==5?(!event_flag_get(296)||g_mode_stack.depth>1):scene==3?(!event_flag_get(14)||g_mode_stack.depth>1):g_mode_stack.depth>1)&&++steps<90000){
  unsigned top=g_mode_stack.depth-1;GameMode mode=g_mode_stack.mode[top];
  core.pad1_pressed=platform_input_get_pad_new();core.pad1_held=platform_input_get_pad();core.pad1_autorepeat=core.pad1_pressed;observe();
  if(mode==GAME_MODE_ACTIONSCRIPT_WAIT&&g_mode_stack.state[top].actionscript_wait.phase==0){waits++;snapshot("wait-entry",scene,kind);}
  if(mode==GAME_MODE_TELEPORT_TO){unsigned dest=g_mode_stack.state[top].teleport_to.dest_id;if(dest<256)warps[dest]=1;if(g_mode_stack.state[top].teleport_to.phase==TT_BEGIN&&warp_count<32)warp_order[warp_count++]=dest;}
  unsigned before=ert.actionscript_state;StepResult r=mode_dispatch_step(mode,&g_mode_stack.state[top]);if(!before&&ert.actionscript_state)signals++;
  if(r.kind==STEP_PUSH)mode_push(r.push_mode,r.push_init);else if(r.kind==STEP_POP)mode_pop(r.pop_result);else{host_process_frame();frames++;}
  observe();
  unsigned t=g_mode_stack.depth-1,wait=g_mode_stack.mode[t]==GAME_MODE_ACTIONSCRIPT_WAIT&&g_mode_stack.state[t].actionscript_wait.phase==1;
  unsigned eligible=scene==1?wait&&seen[253]&&frames>=10:scene==3?wait&&seen[153]:scene==7?wait&&frames>=100:frames==8;
  if(kind==1&&!saved&&eligible){if(!state_dump_save_slots())return 7;saved=1;snapshot("saved",scene,kind);}
 }
 snapshot("parent-ended",scene,kind);
 if(g_mode_stack.depth==1){ModeState idle={0};idle.wait_frames.phase=WF_FRAME;idle.wait_frames.remaining=64;mode_push(GAME_MODE_WAIT_FRAMES,&idle);while(g_mode_stack.depth>1&&++steps<90100){unsigned t=g_mode_stack.depth-1;StepResult r=mode_dispatch_step(g_mode_stack.mode[t],&g_mode_stack.state[t]);if(r.kind==STEP_PUSH)mode_push(r.push_mode,r.push_init);else if(r.kind==STEP_POP)mode_pop(r.pop_result);else{host_process_frame();settle_frames++;}observe();}}
 snapshot("final",scene,kind);audio_shutdown();return steps>=90000?8:kind==1&&!saved?9:0;
}
'''

SCENES={
 1:{'name':'full Bubble Gum rope scene','root':0xC88000,'xy':[5029,406], 'party':[3,9,0,0,0,0], 'flags':[11,22,129,323,334,338], 'requiredNpcs':[677], 'children':[253,255,261,263,264,265], 'waits':7},
 3:{'name':'Dr. Andonuts introduction to complete first Sky Walker flight and Jeff joining','root':0xC6B18D,'xy':[7824,2872], 'party':[3,0,0,0,0,0], 'flags':[11], 'requiredNpcs':[615,621,623], 'children':[145,146,147,148,149,153,155,157,159,161,164,175,176,177,777,778], 'waits':17},
 4:{'name':'hotel reception ghost EVENT78 complete natural approach and removal','root':None,'xy':[6728,9336], 'party':[1,2,0,0,0,0], 'flags':[11,296], 'requiredNpcs':[484], 'children':[78], 'waits':0},
 5:{'name':'outside ghost EVENT77 naturally queues complete C79D66 parent','root':None,'xy':[5536,8976], 'party':[1,2,0,0,0,0], 'flags':[11,46], 'requiredNpcs':[538], 'children':[77], 'waits':1},
 6:{'name':'rear hotel ghost EVENT79 complete natural approach and removal','root':None,'xy':[7808,9320], 'party':[1,2,0,0,0,0], 'flags':[11,297], 'requiredNpcs':[489], 'children':[79], 'waits':0},
 7:{'name':'complete hotel capture C79D81 camera, collapse and basement parent','root':0xC79D81,'xy':[7640,9456], 'party':[1,2,0,0,0,0], 'flags':[11,298], 'requiredNpcs':[493,494,495,496], 'children':[80,651,662,663], 'waits':2},
}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()

def original_ref(native,address):
 sys.path.insert(0,str(native.resolve()))
 from ebtools.config import load_dump_doc
 doc=load_dump_doc(native/'earthbound.yml')
 labels={doc.renameLabels.get(e.name,{}).get(address-0xC00000-e.offset)for e in doc.dumpEntries};labels.discard(None)
 if len(labels)!=1:raise ValueError(('Original source reference',hex(address),labels))
 m=re.search(r'#define\s+'+re.escape(labels.pop())+r'\s+0x([0-9a-fA-F]+)',(native/'src/data/text_refs.h').read_text())
 if not m:raise ValueError('Missing original source reference')
 return int(m[1],16)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('build','runtime','native-source','frozen-source','project','original-assets','redux-assets','scratch','output'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--diagnostic',action='store_true');a=p.parse_args();a.scratch=local_scratch(a.scratch)
 if a.scratch.exists() or a.output.exists():raise ValueError('Fresh tool scratch and output required; preserve all earlier evidence.')
 pin=subprocess.check_output(['git','-C',str(a.project.parent),'rev-parse','HEAD'],text=True).strip()
 if pin!=frozen.PIN:raise ValueError('Unreviewed Redux pin')
 a.scratch.mkdir(parents=True);frozen.DRIVER=DRIVER;exe,evidence=frozen.private_build(a)
 identities={str(path):sha(path)for path in (a.runtime/'player.exe',a.runtime/'observer.exe',a.build/'game_lib/libearthbound_game.a',a.original_assets,a.redux_assets)}
 rows=[];assertions=0
 env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
 for profile,pak in (('Original',a.original_assets),('Redux',a.redux_assets)):
  for scene,contract in SCENES.items():
   previous={}
   for kind,label in ((0,'warm'),(1,'checkpoint-and-finish'),(2,'fresh-process-restore-and-finish')):
    folder=a.scratch/(profile.lower()+'-'+str(scene)+'-'+label);folder.mkdir()
    if kind==2:shutil.copytree(previous[1]/'saves',folder/'saves')
    (folder/'input.replay').write_text(''.join(f'{i} {"80" if i%2==0 and scene in (1,3,7) else "0"}\n' for i in range(100000)))
    address=contract['root'];entry=original_ref(a.native_source,address)if profile=='Original' and address else address or 0
    run=subprocess.run([str(exe.resolve()),str(pak.resolve()),str(folder.resolve()),str(int(profile=='Original')),str(scene),str(kind),f'{entry:X}'],cwd=folder,env=env,capture_output=True,timeout=180)
    log=run.stdout+run.stderr;(folder/'native.log').write_bytes(log)
    stages=[json.loads(line[len('QA_SCENE '):])for line in run.stdout.decode(errors='replace').splitlines()if line.startswith('QA_SCENE ')]
    final=next((x for x in stages if x['tag']=='final'),{})
    checks={'nativeExitZero':run.returncode==0,'finalDepthOne':final.get('depth')==1,'restoredCamera':final.get('camera')==0,'boundedCompletion':0<final.get('steps',0)<90000,'normal64FrameClosingTail':final.get('settleFrames')==64,'letterboxClosed':final.get('letterboxFinal')==0,'noPendingInteraction':final.get('pending')==0}
    flags=set(final.get('flags',[]))
    if kind!=2:
     checks['sourceEntryNpcsPresent']=set(contract['requiredNpcs']).issubset(final.get('initialNpcs',[]))
     checks['allRetainedChildrenObserved']=set(contract['children']).issubset(final.get('scripts',[]))
     checks['sourceWaitCount']=final.get('waits')==contract['waits']
    if scene==1:
     checks.update(partyRetained=final.get('party')==[3,9,0,0,0,0],ropeFlagSet=311 in flags,ropePendingFlagCleared=338 not in flags,animationActorsRemoved=final.get('remainingActors')==[],sourceRopeBlocker677Removed=final.get('npc677Bound')==0)
     if profile=='Redux' and kind!=2:checks.update(newCameraAndJeffActorsObserved={897,898}.issubset(final.get('scripts',[])),cameraMode2Observed=final.get('cameraMode2Seen')==1,cameraPanReachedUpperLedge=final.get('cameraPanY',[65535,0])[0]<=322)
    elif scene==3:
     checks.update(jeffJoined=final.get('party')==[1,2,3,0,0,0],finalBasementPosition=final.get('xy')==[6752,10064],sourceFinalFlagsSet={14,47,49,127,589,622,626,748}.issubset(flags),sceneLocksCleared=not{11,655,798}&flags,walletRestored=final.get('money')==1234)
     if kind!=2:checks.update(fullDestinationInventory=set(final.get('warps',[]))=={77,186,188,189,191,193},exactSourceEightWarpOrder=final.get('warpOrder')==[186,188,189,188,191,188,193,77],actual137AssignedPcObserved=final.get('actual137PcObserved')==1,sourceFoursideFirstPostTickHeight=final.get('first153Z')==(191 if profile=='Original' else 167),sourceDesertFirstPostTickHeight=final.get('first157Z')==(191 if profile=='Original' else 167))
    elif scene==4:checks.update(stage296Cleared=296 not in flags,stage297Set=297 in flags,ghostRemoved=final.get('remainingActors')==[])
    elif scene==5:checks.update(stage46Cleared=46 not in flags,stage296Set=296 in flags,parentWaitNaturallyYielded=final.get('signals')>=1,ghostRemoved=final.get('remainingActors')==[])
    elif scene==6:checks.update(stage298Set=298 in flags,ghostRemoved=final.get('remainingActors')==[])
    elif scene==7:checks.update(finalBasementPosition=final.get('xy')==[6768,10064],partyRetained=final.get('party')==[1,2,0,0,0,0],allCharactersHealed=final.get('hp')==[300]*4)
    if kind==1:checks['actualMidSceneSaveWritten']=any(x['tag']=='saved' and(x['depth']>1 or x['frames']==8)for x in stages)
    if kind==2:
     checks['actualColdCheckpointRestored']=any(x['tag']=='cold-restored'for x in stages)
     baseline=previous['baseline']
     for field in ('depth','xy','camera','party','flags','money','walletBackup','hp','partyCount','playerCount','remainingActors'):checks['coldSameFinal.'+field]=final.get(field)==baseline.get(field)
    assertions+=len(checks)
    rows.append({'profile':profile,'scene':scene,'name':contract['name'],'continuation':label,'entryContract':{**contract,'root':f'{address:06X}'if address else'ordinary OVERWORLD with real source actor'},'nativeExit':run.returncode,'checks':checks,'passed':all(checks.values()),'final':final,'midSceneCheckpoints':[x for x in stages if x['tag']in('saved','cold-restored')],'waitTimeline':[x for x in stages if x['tag']=='wait-entry']})
    if kind==0:previous['baseline']=final
    previous[kind]=folder
    print(f'{profile} {scene} {label}: '+('PASS'if rows[-1]['passed']else'FAIL'),flush=True)
 sources=['src/game/display_text_cc.c','src/game/overworld.c','src/game/door.c','src/game/map_loader.c','src/entity/entity.c','src/entity/callroutine.c','src/entity/callroutine_movement.c','src/entity/script.c','src/entity/sprite.c','src/core/state_dump.c','src/data/event_script_data.c','src/game_main.c']
 source_ids={r:sha(a.frozen_source/r)if(a.frozen_source/r).exists()else sha(a.native_source/r)for r in sources}
 redux_sources=['ccscript/data/data_25.ccs','ccscript/data/data_34.ccs','ccscript/data/data_43.ccs','ccscript/data/data_44.ccs','ccscript/redux/cutscenes.ccs','ccscript/redux/movement_reloc.ccs','npc_config_table.yml','map_sprites.yml']
 redux_ids={}
 for r in redux_sources:
  current=a.project/r;reference=subprocess.check_output(['git','-C',str(a.project.parent),'show','HEAD:Project/'+r])
  if current.read_bytes().replace(b'\r\n',b'\n')!=reference.replace(b'\r\n',b'\n'):raise ValueError('Pinned source changed: '+r)
  redux_ids[r]=sha(current)
 originals=['asm/data/events/scripts/'+f'{n:03d}.asm'for n in (77,78,79,80,137,145,146,153,157,161,164,175,176,177,253,255,261,263,264,265,651,662,663,777,778)]
 original_ids={r:sha(a.native_source/r)for r in originals}
 if any(sha(Path(path))!=digest for path,digest in identities.items()):raise ValueError('Read-only frozen input changed')
 report={'schemaVersion':1,'status':'Passed'if rows and all(r['passed']for r in rows)else'Failed','allPassed':bool(rows)and all(r['passed']for r in rows),'sourceRevision':pin,'runtimeIdentities':identities,'privateBuild':evidence,'frozenSourcePatchSha256':sha(a.frozen_source/'native-companion.patch'),'nativeSourceFiles':source_ids,'pinnedReduxSourceFiles':redux_ids,'originalSourceFiles':original_ids,'executedCases':len(rows),'skippedCases':0,'executedAssertions':assertions,'coldProcessCases':sum(r['continuation']=='fresh-process-restore-and-finish'for r in rows),'cases':rows,'scopeNotes':['Six prepared complete scene branches in both profiles, with unchanged production text/entity/map/mode consumers and real SDL input replay.','Sky Walker begins at the full Dr. Andonuts dialogue C6B18D, whose real CC assigns EVENT137; this actor naturally queues boarding C88332 and launch C88387.','Six unique destination IDs cover eight ordered map transitions: seven flight segments plus the basement arrival; clouds188 repeats three times.','NPC/wallet backups are prepared to the source pre-Jeff-solo contract: NPC companions absent, prior Ness wallet1234, Jeff wallet2. Surrounding Threek telepathy/dorm quest entry is not replayed here.','Ghost stages77,78,79 and hotel-capture text each use their own source map/story contexts; walking all connecting doors between these contexts is not asserted.','Original EVENT79 does not prime zero before its first flag command; this report asserts flag298 and actor removal, without asserting that flag297 clears.','Reassigned NPC623 retains its allocation metadata script_table8; the actual resolved EVENT137 bank/PC range is observed independently. The source comment IDs for Redux camera/Jeff duplicate are stale: actual builder assigns897 Jeff_Dup and898 Rope_Camera_Pan; actual generated pack actors are tested.','Each cold case restores immediately after normal bootstrap and title-bank binding, without prepared-world/map initialization in the new process, from an actual mid-scene checkpoint; finish-state comparison checks party, flags, HP, wallet, position, camera, remaining actors and counts. Native WAIT_FRAMES renders64 ordinary closing-tail frames after each parent finishes; no completion flags are supplied.','EVENT153/157 first observable post-physics Z is191 Original/167 Redux: source initializes192/168 then applies the first minus-one tick. Actor PCs and original/source contracts are checked; no independent SNES full-scene timing or rendering oracle is claimed. Pixel-perfect frames, all audio and complete game progression remain unverified.','No owner save, ROM, extracted dialogue/assets or soundtrack bytes are included in this report.'],'fixtureDiagnostics':['Initial standalone C88387 pilot stalled because NPC623 still had default EVENT8; preceding C6B18D/EVENT137 supplies its actual production prerequisite. No native correction was made.','An early hotel-capture pilot used the wrong room coordinate and lacked actors493–496; final fixtures use7640,9456 and assert all four source actors.'],'fullConversionVerified':False,'fullPlaythroughVerified':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:report[k]for k in('status','allPassed','executedCases','skippedCases','executedAssertions','coldProcessCases')}))
 if not report['allPassed']and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
