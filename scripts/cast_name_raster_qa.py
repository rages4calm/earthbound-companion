# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare actual cast-name tiles with an independent packed-font compositor."""
import argparse,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as frozen
import redux_ending_transaction_qa as ending

DRIVER=ending.DRIVER.split('int main(int argc,char **argv){')[0]+r'''
#include "include/constants.h"
#include "game/battle.h"
static unsigned pixels,blocks;
static void require(int ok,const char*why){if(!ok){fprintf(stderr,"CAST_FAIL %s blocks%u pixels%u\n",why,blocks,pixels);exit(7);}}
static void compare(const uint8_t*text,unsigned tile,unsigned count){
 uint8_t expected[16][208]={{0}};unsigned length=0;
 for(const uint8_t*p=text;*p;p++)length+=font_get_width(FONT_ID_NORMAL,*p-0x50)+character_padding;
 unsigned x=count*8>length?(count*8-length)/2:0;
 for(const uint8_t*p=text;*p;p++){
  const uint8_t*g=font_get_glyph(FONT_ID_NORMAL,*p-0x50);require(g!=NULL,"legal loaded glyph");
  for(unsigned y=0;y<font_get_height(FONT_ID_NORMAL);y++)for(unsigned dx=0;dx<8;dx++)if(x+dx<count*8&&!(g[y]&(128>>dx)))expected[y][x+dx]=1;
  x+=font_get_width(FONT_ID_NORMAL,*p-0x50)+character_padding;
 }
 for(unsigned y=0;y<16;y++)for(unsigned x=0;x<count*8;x++){
  unsigned id=(tile+x/8)&1023,offset=((id/16)*32+id%16)*16+(y/8)*256+(y%8)*2;
  unsigned actual=((ppu.vram[offset]>>(7-x%8))&1)|(((ppu.vram[offset+1]>>(7-x%8))&1)<<1);pixels++;
  if(actual!=expected[y][x]){fprintf(stderr,"CAST_PIXEL tile%u count%u x%u y%u actual%u expected%u\n",tile,count,x,y,actual,expected[y][x]);require(0,"independent centered glyph raster");}
 }blocks++;
}
int main(int argc,char**argv){
 if(argc!=6)return 2;unsigned original=atoi(argv[3]),kind=atoi(argv[4]);const char*stage=argv[5];
 char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 char*boot[]={"cast-raster","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot)||maternalbound_enabled()==original)return 3;
 platform_max_frames=0;platform_input_shutdown();require(platform_input_init(),"input init");game_set_fast_forward(true);audio_init();load_title_screen_script_data();
 static const uint8_t accents[4][6]={{0xb0,0xb1,0xb2,0xb3,0xb4,0xb5},{0xc0,0xc1,0xc2,0xc3,0xc4,0xc5},{0xb7,0xc7,0xb0,0xc0,0xb5,0xc5},{0x87,0x87,0x71,0x78,0x78,0x95}};
 static const char*names[]={"WMWMWM","iiiiii","Native","Mimimi","N"};unsigned cap=maternalbound_name_capacity();uint8_t prepared[4][7]={{0}};
 for(unsigned c=0;c<4;c++){
  if(kind==5)memcpy(prepared[c],accents[c],cap);else{const char*s=names[kind];for(unsigned j=0;j<cap&&s[j];j++)prepared[c][j]=(uint8_t)s[j]+0x30;}
  maternalbound_set_character_name(c,prepared[c],cap);
 }
 memset(game_state.pet_name,0,sizeof(game_state.pet_name));for(unsigned j=0;j<cap;j++)game_state.pet_name[j]=(j%2?'i':'W')+0x30;
 window_system_init();init_used_bg2_tile_map();text_setup_bg3();text_upload_font_tiles();entity_system_init();
 memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_NONE;
 if(!strcmp(stage,"resume")){
  host_request_load();host_root_boundary();require(host_capture_status()==HOST_CAPTURE_COMMITTED,"cold cast checkpoint load");
  unsigned top=g_mode_stack.depth-1;StepResult r=mode_dispatch_step((GameMode)g_mode_stack.mode[top],&g_mode_stack.state[top]);
  if(r.kind==STEP_PUSH)mode_push(r.push_mode,r.push_init);else if(r.kind==STEP_POP)mode_pop(r.pop_result);
 }else{ModeState child={0};child.ending.phase=EN_CAST_SETUP;mode_push(GAME_MODE_ENDING,&child);}
 unsigned steps=0;while(++steps<5000){unsigned top=g_mode_stack.depth-1;
  if(g_mode_stack.mode[top]==GAME_MODE_ENDING&&g_mode_stack.state[top].ending.phase==EN_CAST_LOOP)break;
  StepResult r=mode_dispatch_step((GameMode)g_mode_stack.mode[top],&g_mode_stack.state[top]);if(r.kind==STEP_PUSH)mode_push(r.push_mode,r.push_init);else if(r.kind==STEP_POP)mode_pop(r.pop_result);else host_process_frame();
 }require(steps<5000,"cast setup completes naturally");
 if(!strcmp(stage,"capture")){host_request_capture();host_root_boundary();require(host_capture_status()==HOST_CAPTURE_COMMITTED,"cast root capture");}
 const uint8_t*fmt=ASSET_DATA(ASSET_ENDING_CAST_SEQUENCE_FORMATTING_BIN);const uint8_t*guard=ASSET_DATA(ASSET_ENDING_GUARDIAN_TEXT_BIN);
 require(ASSET_SIZE(ASSET_ENDING_PARTY_CAST_TILE_IDS_BIN)==8,"source-defined party tile table size");
 /* Source coordinates are independent of the converted table. Legacy packs
  * contain the known bad table, and production must recover their layout. */
 for(unsigned c=0;c<4;c++)compare(prepared[c],384+c*16,6);
 for(unsigned c=0;c<5;c++){
  print_cast_name_party(c==4?PARTY_MEMBER_KING:c+1,16,30);
  unsigned row=((ppu.bg_vofs[2]>>3)+30)&31,start=(row*32+16+VRAM_CAST_TILEMAP-3)*2;
  unsigned tile=c==4?448:384+c*16;
  for(unsigned x=0;x<6;x++){
   unsigned expected=((tile+x)&0x3f0)*2+((tile+x)&15)+cast_tile_offset;
   require(read_u16_le(ppu.vram+start+x*2)==expected,"actual top-row cast name placement");
   unsigned bottom=(row==31?start-0x7c0:start+64);
   require(read_u16_le(ppu.vram+bottom+x*2)==expected+16,"actual bottom-row cast name placement");
  }
 }
 compare(game_state.pet_name,448,6);
 static const unsigned entry[]={39,36,108};
 for(unsigned c=0;c<3;c++){
  uint8_t composed[32]={0};unsigned at=0;
  if(original){unsigned who=c==2?3:1;for(unsigned j=0;prepared[who][j];j++)composed[at++]=prepared[who][j];for(unsigned j=0;guard[c*7+j];j++)composed[at++]=guard[c*7+j];}
  else {const uint8_t*row=guard+8+c*16;require(row[0]==0,"pinned Redux guardian choice is none");memcpy(composed,row+4,row[2]);}
  compare(composed,read_u16_le(fmt+entry[c]),fmt[entry[c]+2]);
 }
 printf("CAST_RASTER {\"passed\":true,\"kind\":%u,\"stage\":\"%s\",\"blocks\":%u,\"pixelsCompared\":%u,\"castSetupSteps\":%u}\n",kind,stage,blocks,pixels,steps);audio_shutdown();return 0;
}
'''

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('native-source','build','runtime','assets','scratch','output'):
        parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--original-profile',action='store_true')
    parser.add_argument('--cold',action='store_true',help='Capture actual cast setup and validate its fresh-process continuation.')
    args=parser.parse_args();args.scratch=args.scratch.resolve();args.scratch.mkdir(parents=True,exist_ok=False)
    frozen.DRIVER=DRIVER;exe,proof=frozen.private_build(args);rows=[]
    for kind in ([0,1,2,3,4] if args.original_profile else [0,1,2,3,4,5]):
        session=args.scratch/f'case-{kind}';session.mkdir()
        for stage in (['capture','resume'] if args.cold else ['warm']):
            with (session/(stage+'.log')).open('wb') as log:
                r=subprocess.run([str(exe),str(args.assets.resolve()),str(session),str(int(args.original_profile)),str(kind),stage],cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),stdout=log,stderr=subprocess.STDOUT,timeout=90)
            text=(session/(stage+'.log')).read_text(errors='replace')
            if r.returncode:raise RuntimeError(text[-1300:])
            case=[json.loads(line.split(' ',1)[1]) for line in text.splitlines() if line.startswith('CAST_RASTER ')]
            if len(case)!=1:raise RuntimeError('Missing cast result')
            rows.extend(case)
    report={'passed':len(rows)==(5 if args.original_profile else 6)*(2 if args.cold else 1),'cases':rows,'privateBuild':proof,'packSha256':frozen.digest(args.assets),'limits':['Prepared legal five-letter Original/six-letter Redux names and pet names; actual cast load, five printed name tilemaps and all eight dynamic name blocks checked against source coordinates and independently centered glyph pixels. Cold mode uses actual root capture and a fresh-process load and ending dispatcher. Pinned Redux chooses three fixed guardian labels; inactive custom prefix/suffix configurations are not natural gameplay choices. No preceding full campaign, physical display or independent SNES CPU raster claim.']}
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':report['passed'],'cases':len(rows),'blocks':sum(r['blocks'] for r in rows),'pixelsCompared':sum(r['pixelsCompared'] for r in rows)}))
if __name__=='__main__':main()
