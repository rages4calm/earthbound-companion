# SPDX-License-Identifier: GPL-3.0-or-later
"""Drive a real loaded-map photographer through ordinary movement and dialogue."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import battle_action_catalog_qa as frozen
import redux_ending_transaction_qa as ending

DRIVER = ending.DRIVER.split('int main(int argc,char **argv){')[0] + r'''
#include "data/text_refs.h"
#include "include/constants.h"
#include "game/battle.h"
static void require(int ok,const char*message){if(!ok){fprintf(stderr,"PHOTO_FAIL %s\n",message);exit(7);}}
int main(int argc,char**argv){
 if(argc!=8)return 2;int original=atoi(argv[3]);unsigned photo=atoi(argv[4]);int wrapper=atoi(argv[5]);const char*stage=argv[6];int statuses=atoi(argv[7]);
 char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 char*boot[]={"photo-acquisition","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot)||maternalbound_enabled()==original)return 3;
 char input[4096];snprintf(input,sizeof(input),"%s/input.replay",argv[2]);pc_input_script_path=input;
 platform_max_frames=0;platform_input_shutdown();require(platform_input_init(),"input init");
 game_set_fast_forward(true);audio_init();load_title_screen_script_data();
 game_state.party_count=game_state.player_controlled_party_count=1;
 game_state.party_npc_1=game_state.party_npc_2=0;
 memset(game_state.party_members,0,sizeof(game_state.party_members));game_state.party_members[0]=1;
 for(unsigned i=0;i<4;i++){memset(&party_characters[i],0,sizeof(party_characters[i]));party_characters[i].level=10;party_characters[i].max_hp=party_characters[i].current_hp=party_characters[i].current_hp_target=100;}
 const uint8_t name[]={0x7e,0x95,0xa3,0xa3,0};maternalbound_set_character_name(0,name,4);
 if(statuses){
  require(wrapper,"status boundary case uses prepared wrapper entry");
  game_state.party_count=game_state.player_controlled_party_count=4;
  game_state.party_members[0]=4;game_state.party_members[1]=1;game_state.party_members[2]=3;game_state.party_members[3]=2;
  party_characters[1].afflictions[1]=STATUS_1_MUSHROOMIZED;
  party_characters[2].afflictions[0]=STATUS_0_UNCONSCIOUS;
  party_characters[3].afflictions[0]=STATUS_0_DIAMONDIZED;
 }
 for(unsigned i=0;i<NUM_PHOTOS;i++){event_flag_clear(698+i);memset(&game_state.saved_photo_states[i],0xa5,sizeof(PhotoState));}
 event_flag_set(73);event_flag_set(11);for(unsigned i=479;i<=510;i++)event_flag_clear(i);event_flag_set(478+photo);
 game_state.leader_x_coord=2640;game_state.leader_y_coord=414;
 window_system_init();init_used_bg2_tile_map();text_setup_bg3();text_upload_font_tiles();text_load_window_gfx();text_load_flavour_palette(0);
 initialize_overworld_state();update_party();core.play_timer=3600*(statuses?70000:123);
 uint8_t expected_party[6]={0};
 for(unsigned y=0;y<6;y++){
  unsigned id=game_state.party_order[y];expected_party[y]=id;
  if(id==2)expected_party[y]|=128;else if(id==3)expected_party[y]|=32;else if(id==4)expected_party[y]|=64;
 }
 memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_OVERWORLD;g_mode_stack.state[0].overworld.phase=OWP_RENDER;
 if(wrapper&&(!strcmp(stage,"warm") || !strcmp(stage,"capture"))){
  static const uint32_t entries[]={MSG_GLOBAL_PHOTO_1,MSG_GLOBAL_PHOTO_2,MSG_GLOBAL_PHOTO_3,MSG_GLOBAL_PHOTO_4,MSG_GLOBAL_PHOTO_5,MSG_GLOBAL_PHOTO_6,MSG_GLOBAL_PHOTO_7,MSG_GLOBAL_PHOTO_8,MSG_GLOBAL_PHOTO_9,MSG_GLOBAL_PHOTO_10,MSG_GLOBAL_PHOTO_11,MSG_GLOBAL_PHOTO_12,MSG_GLOBAL_PHOTO_13,MSG_GLOBAL_PHOTO_14,MSG_GLOBAL_PHOTO_15,MSG_GLOBAL_PHOTO_16,MSG_GLOBAL_PHOTO_17,MSG_GLOBAL_PHOTO_18,MSG_GLOBAL_PHOTO_19,MSG_GLOBAL_PHOTO_20,MSG_GLOBAL_PHOTO_21,MSG_GLOBAL_PHOTO_22,MSG_GLOBAL_PHOTO_23,MSG_GLOBAL_PHOTO_24,MSG_GLOBAL_PHOTO_25,MSG_GLOBAL_PHOTO_26,MSG_GLOBAL_PHOTO_27,MSG_GLOBAL_PHOTO_28,MSG_GLOBAL_PHOTO_29,MSG_GLOBAL_PHOTO_30,MSG_GLOBAL_PHOTO_31,MSG_GLOBAL_PHOTO_32};
  ModeState child={0};require(dt_make_child_init(&child,entries[photo-1]),"source photo wrapper resolves");mode_push(GAME_MODE_DISPLAY_TEXT,&child);
 }
 dt.instant_printing=0;ow.battle_mode=0;
 if(!strcmp(stage,"resume")||!strcmp(stage,"verify")){
  host_request_load();host_root_boundary();require(host_capture_status()==HOST_CAPTURE_COMMITTED,"actual fresh-process load");
 }
 unsigned npc183=0,photo_resume=0,child_seen=0,steps=0;uint32_t expected_time=0;
 while(++steps<12000){
  unsigned top=g_mode_stack.depth-1;GameMode mode=(GameMode)g_mode_stack.mode[top];
  core.pad1_pressed=platform_input_get_pad_new();core.pad1_held=platform_input_get_pad();core.pad1_autorepeat=core.pad1_pressed;
  for(unsigned i=0;i<MAX_ENTITIES;i++)if(entities.script_table[i]>=0&&entities.npc_ids[i]==183)npc183=1;
  if(mode==GAME_MODE_DISPLAY_TEXT){child_seen=1;if(g_mode_stack.state[top].display_text.resume==DT_RESUME_CC1F_PHOTO){
   if(!strcmp(stage,"capture")){host_request_capture();host_root_boundary();require(host_capture_status()==HOST_CAPTURE_COMMITTED,"before-save root capture");require(!event_flag_get(697+photo),"capture before photo flag commit");printf("PHOTO_CAPTURE %u\n",photo);audio_shutdown();return 0;}
   photo_resume++;expected_time=core.play_timer/3600;if(expected_time>=60000)expected_time=59999;
  }}
  if(!strcmp(stage,"verify")){require(event_flag_get(697+photo)&&g_mode_stack.depth==1,"after-save cold boundary");expected_time=core.play_timer/3600;if(expected_time>=60000)expected_time=59999;break;}
  StepResult r=mode_dispatch_step(mode,&g_mode_stack.state[top]);
  if(r.kind==STEP_PUSH)mode_push(r.push_mode,r.push_init);else if(r.kind==STEP_POP)mode_pop(r.pop_result);else host_process_frame();
  if(event_flag_get(697+photo)&&g_mode_stack.depth==1)break;
  if(steps%1000==0)fprintf(stderr,"PHOTO_PROGRESS %u mode %u depth %u pos %u,%u npc %u photo %u aux %u\n",steps,mode,g_mode_stack.depth,game_state.leader_x_coord,game_state.leader_y_coord,npc183,event_flag_get(698),ow.spawning_travelling_photographer_id);
 }
 require(steps<12000,"bounded completion");if(!wrapper&&strcmp(stage,"verify"))require(npc183,"real map controller183 loaded");if(strcmp(stage,"verify"))require(child_seen&&photo_resume==1,"actual camera child and save continuation");
 require(event_flag_get(697+photo)&&event_flag_get(478+photo)==(photo==8||photo==13),"source acquisition/availability flags");
 require(game_state.saved_photo_states[photo-1].unknown==expected_time,"timer snapshot after camera");
 require(!memcmp(game_state.saved_photo_states[photo-1].party,expected_party,6),"party order, affliction bits and empty slots");
 for(unsigned i=0;i<NUM_PHOTOS;i++){if(i==photo-1)continue;const uint8_t*p=(const uint8_t*)&game_state.saved_photo_states[i];for(unsigned j=0;j<sizeof(PhotoState);j++)require(p[j]==0xa5,"other photo sentinel");require(!event_flag_get(698+i),"other acquisition flag");}
 if(!strcmp(stage,"resume")){host_request_capture();host_root_boundary();require(host_capture_status()==HOST_CAPTURE_COMMITTED,"after-save root capture");}
 printf("PHOTO_ACQUISITION {\"passed\":true,\"photo\":%u,\"ordinaryMovementEntry\":%s,\"stage\":\"%s\",\"steps\":%u,\"cameraSaveResumes\":%u,\"timestamp\":%u,\"otherPhotosPreserved\":31}\n",photo,wrapper?"false":"true",stage,steps,photo_resume,expected_time);
 audio_shutdown();return 0;
}
'''

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('native-source','build','runtime','assets','scratch','output'):
        parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--original-profile',action='store_true')
    parser.add_argument('--all-wrappers',action='store_true',help='Prepared entry into each source photo wrapper; only the default photo1 case proves ordinary movement entry.')
    parser.add_argument('--cold',action='store_true',help='Capture at the actual camera return, resume in a fresh process, then cold-load the committed photo.')
    parser.add_argument('--status-fixture',action='store_true',help='With all-wrappers, use reordered four-character party, three afflictions and a capped play timer.')
    args = parser.parse_args()
    args.scratch=args.scratch.resolve();args.scratch.mkdir(parents=True,exist_ok=False)
    frozen.DRIVER=DRIVER;exe,proof=frozen.private_build(args)
    rows=[]
    for photo in (range(1,33) if args.all_wrappers else [1]):
        session=args.scratch/f'photo-{photo}';session.mkdir()
        (session/'input.replay').write_text(''.join(f'{i} {"800" if not args.all_wrappers and i<60 else "80" if i>180 and i%2==0 else "0"}\n' for i in range(50000)))
        for stage in (['capture','resume','verify'] if args.cold else ['warm']):
            with (session/(stage+'.log')).open('wb') as output:
                result=subprocess.run([str(exe),str(args.assets.resolve()),str(session),str(int(args.original_profile)),str(photo),str(int(args.all_wrappers)),stage,str(int(args.status_fixture))],cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),stdout=output,stderr=subprocess.STDOUT,timeout=120)
            log=(session/(stage+'.log')).read_bytes();case=[json.loads(line.split(' ',1)[1]) for line in log.decode(errors='replace').splitlines() if line.startswith('PHOTO_ACQUISITION ')]
            if result.returncode or (stage!='capture' and len(case)!=1) or (stage=='capture' and b'PHOTO_CAPTURE ' not in log):raise RuntimeError(log.decode(errors='replace')[-2200:])
            rows.extend(case)
    report={'passed':len(rows)==(32 if args.all_wrappers else 1)*(2 if args.cold else 1),'privateBuild':proof,'packSha256':frozen.digest(args.assets),'actual':rows,'limits':['Source-defined availability, map and party prerequisites are prepared. Default photo1 executes ordinary movement, actual placed controller and queue. All-wrappers enters each actual source wrapper directly and executes camera/save/flags; it does not prove map reachability or preceding story for those 32 locations. Saturn/Gumi source flag branches run for photo32/photo31. Cold runs use actual format-16 capture/load in separate processes before and after the photo commit. No owner saves modified.']}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'cases':len(rows),'packSha256':report['packSha256']}))
if __name__=='__main__':main()
