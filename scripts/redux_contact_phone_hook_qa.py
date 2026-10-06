# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual Original/Redux contact-target and Dad bicycle-call branch checks.

Explicit local inputs are required. Original source is assembled solely to gate
complete original/pinned machine bodies before running those unchanged bodies.
An own caller and prepared RAM are injected into isolated emulator memory; no
ROM, pack, owner save, shared source or production build is edited. Generated
original code/data remain in fresh private scratch, never in this public tool.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess

from build_maternalbound_pack import read_pack
from check_jev_observer_parity import local_scratch
from party_follow_private_build import private_build
from snes_movement_helpers_oracle import sha, US_SHA1
import snes_position_arithmetic_oracle as mapping

CONTACT_DRIVER = r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game/overworld.h"
#include "game/game_state.h"
#include "game/battle.h"
#include "game/door.h"
#include "game/position_buffer.h"
#include "game/maternalbound.h"
#include "entity/entity.h"
#include "data/assets.h"
#include "data/event_script_data.h"
extern int eb_platform_main(int,char**);
extern int16_t callroutine_dispatch(uint32_t,int16_t,int16_t,uint16_t,uint16_t*);
int main(int argc,char**argv){
 if(argc!=5)return 2;unsigned redux=atoi(argv[4]);char save[4096];snprintf(save,sizeof(save),"%s/private.srm",argv[2]);
 char*boot[]={"contact-hook-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1",redux?"--redux-battle-fixture":"--inspect-shuffle","0"};
 if(eb_platform_main(redux?13:12,boot)||maternalbound_enabled()!=(redux!=0))return 3;
 const EnemyData*enemies=(const EnemyData*)ASSET_DATA(ASSET_DATA_ENEMY_CONFIGURATION_TABLE_BIN);
 if(!enemies||enemies[1].event_script==0||enemies[ENEMY_MAGIC_BUTTERFLY].event_script==0)return 4;
 FILE*f=fopen(argv[3],"r");if(!f)return 5;unsigned index,leader,player,guard,slot,camera;
 while(fscanf(f,"%u %u %u %u %u %u",&index,&leader,&player,&guard,&slot,&camera)==6){
  memset(&ow,0,sizeof(ow));memset(&bt,0,sizeof(bt));memset(&dr,0,sizeof(dr));
  game_state.camera_mode=camera;game_state.walking_style=0;game_state.current_party_members=leader;
  unsigned enemy=guard==8?ENEMY_MAGIC_BUTTERFLY:1;
  for(unsigned i=0;i<30;i++){entities.collided_objects[i]=-1;entities.tick_callback_hi[i]=0x1200+i;}
  entities.enemy_ids[slot]=enemy;entities.script_table[slot]=enemies[enemy].event_script;
  ert.current_entity_slot=slot;ert.enemy_pathfinding_target_entity=7;bt.touched_enemy=-1;
  pb.camera_mode_3_frames_left=0;pb.camera_mode_backup=9;
  if(player)entities.collided_objects[23]=slot;else entities.collided_objects[slot]=leader;
  if(guard==1)ow.battle_mode=1;else if(guard==2)dr.using_door=1;else if(guard==3)game_state.camera_mode=2;
  else if(guard==4)ow.player_movement_flags=2;else if(guard==5)game_state.walking_style=WALKING_STYLE_ESCALATOR;
  else if(guard==6)ow.player_intangibility_frames=1;else if(guard==7){entities.collided_objects[23]=-1;entities.collided_objects[slot]=-1;}
  uint16_t pc=65535;int value=callroutine_dispatch(ROM_ADDR_HANDLE_ENEMY_CONTACT,slot,slot,0,&pc);
  if(pc!=0)return 6;
  printf("CONTACT [%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,[",index,(uint16_t)value,(uint16_t)ert.enemy_pathfinding_target_entity,
   (uint16_t)bt.touched_enemy,ow.enemy_has_been_touched,game_state.camera_mode,pb.camera_mode_3_frames_left,
   pb.camera_mode_backup,ow.overworld_status_suppression,ow.battle_swirl_countdown);
  for(unsigned i=0;i<30;i++)printf("%s%u",i?",":"",entities.tick_callback_hi[i]);puts("]]");
 }fclose(f);return 0;
}
'''

PHONE_DRIVER = r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game/overworld.h"
#include "game/game_state.h"
#include "game/battle.h"
#include "game/position_buffer.h"
#include "game/window.h"
#include "game/text.h"
#include "game/map_loader.h"
#include "game/maternalbound.h"
#include "entity/entity.h"
#include "entity/sprite.h"
#include "core/memory.h"
#include "core/state_dump.h"
#include "core/mode_stack.h"
#include "platform/pc_options.h"
#include "platform/platform.h"
#include "data/text_refs.h"
#include "include/constants.h"
#include "snes/ppu.h"
_Static_assert(EVENT_FLAG_DIS_2H_PAPA==775,"Review source Dad-disable flag ABI");
extern int eb_platform_main(int,char**);
extern void load_dad_phone(void);
static void show(unsigned index){
 printf("PHONE [%u,%u,%u,%u,%u,%u,%u,%u,[",index,ow.dad_phone_queued,ow.next_queued_interaction,
  ow.current_queued_interaction,ow.pending_interactions,ow.current_queued_interaction_type,
  ow.dad_phone_timer,game_state.walking_style);
 for(unsigned i=0;i<4;i++)printf("%s[%u,%u]",i?",":"",ow.queued_interactions[i].type,ow.queued_interactions[i].data_ptr==MSG_SYS_PHONE_DAD);
 puts("]]");
}
static void base(unsigned style,unsigned guard,unsigned next,unsigned current){
 memset(&ow,0,sizeof(ow));bt.battle_mode_flag=0;ow.mini_ghost_entity_id=-1;
 game_state.camera_mode=0;game_state.walking_style=style;
 game_state.party_count=game_state.player_controlled_party_count=1;game_state.party_members[0]=game_state.party_order[0]=1;
 game_state.player_controlled_party_members[0]=1;game_state.current_party_members=24;game_state.leader_direction=0;
 for(unsigned i=0;i<30;i++)entities.script_table[i]=-1;
 ow.next_queued_interaction=next;ow.current_queued_interaction=next;ow.current_queued_interaction_type=current;
 for(unsigned i=0;i<4;i++){ow.queued_interactions[i].type=65535;ow.queued_interactions[i].data_ptr=0;}
 pc_options.no_dad_calls=0;close_all_windows();event_flag_clear(EVENT_FLAG_DIS_2H_PAPA);
 if(guard==1){if(!create_window(0)||!any_window_open())exit(14);}else if(guard==2){bt.battle_mode_flag=1;ow.battle_mode=1;}
 else if(guard==3)ow.battle_swirl_countdown=1;else if(guard==4)ow.enemy_has_been_touched=1;
 else if(guard==5)ow.dad_phone_queued=1;else if(guard==6)event_flag_set(EVENT_FLAG_DIS_2H_PAPA);
}
int main(int argc,char**argv){
 if(argc!=6)return 2;unsigned redux=atoi(argv[4]);char save[4096];snprintf(save,sizeof(save),"%s/private.srm",argv[2]);
 char*boot[]={"phone-hook-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
 if(eb_platform_main(12,boot)||maternalbound_enabled()!=(redux!=0))return 3;
 platform_max_frames=0;platform_input_init();
 if(!strcmp(argv[5],"inspect")){if(!state_dump_load_slots())return 4;show(1);printf("PHONE_MODES [");for(unsigned i=0;i<g_mode_stack.depth;i++)printf("%s%u",i?",":"",g_mode_stack.mode[i]);puts("]");for(unsigned i=0;i<g_mode_stack.depth;i++)if(g_mode_stack.mode[i]==GAME_MODE_DISPLAY_TEXT){DisplayTextModeState*s=&g_mode_stack.state[i].display_text;printf("PHONE_READER [%u,%u,%u,%u,%u,%u]\n",s->phase,s->reader.source,s->reader.ptr_off,s->reader.end_off,s->delay_remaining,game_state.text_speed);}return 0;}
 FILE*f=fopen(argv[3],"r");if(!f)return 5;unsigned index,style,guard,next,current;
 while(fscanf(f,"%u %u %u %u %u",&index,&style,&guard,&next,&current)==5){
  if(!strcmp(argv[5],"timing")){base(0,guard,0,65535);ow.dad_phone_timer=style;core.frame_counter=next;process_overworld_tasks();printf("PHONE_TIMER [%u,%u]\n",index,ow.dad_phone_timer);continue;}
  if(!strcmp(argv[5],"cold")){if(!state_dump_load_slots())return 6;pc_options.no_dad_calls=0;}
  else base(style,guard,next,current);
  if(!strcmp(argv[5],"prepare")){if(!state_dump_save_slots())return 7;puts("PHONE_PREPARED");continue;}
  if(!strcmp(argv[5],"lifecycle")){
   // The mount's source-defined single-party prerequisite is prepared. This
   // is a private diagnostic scene, not a claim that this story route is played.
   platform_max_frames=0;platform_input_init();load_sprite_data();entity_system_init();ow.disable_music_changes=1;
   memset(game_state.party_members,0,sizeof(game_state.party_members));memset(game_state.player_controlled_party_members,0,sizeof(game_state.player_controlled_party_members));
   game_state.party_members[0]=game_state.player_controlled_party_members[0]=1;
   window_system_init();init_used_bg2_tile_map();text_setup_bg3();text_upload_font_tiles();text_load_window_gfx();
   game_state.text_flavour=1;game_state.text_speed=0;text_load_flavour_palette(0);ppu.inidisp=15;
   unsigned char name[]={0x84,0x95,0xa3,0xa4,0};memcpy(party_characters[0].name,name,sizeof(name));
   party_characters[0].max_hp=party_characters[0].current_hp=party_characters[0].current_hp_target=100;
   memset(party_characters[0].afflictions,0,sizeof(party_characters[0].afflictions));initialize_party();init_party_position_buffer();
   load_map_at_position(7696,2280);
   game_state.walking_style=0;game_state.leader_x_coord=entities.abs_x[24]=7696;game_state.leader_y_coord=entities.abs_y[24]=2280;
   fprintf(stderr,"PHONE_PHASE mount\n");
   entities.script_table[24]=EVENT_SCRIPT_002;get_on_bicycle();if(game_state.walking_style!=WALKING_STYLE_BICYCLE)return 8;
   fprintf(stderr,"PHONE_PHASE timer\n");
   ow.dad_phone_timer=1;core.frame_counter=255;process_overworld_tasks();if(ow.dad_phone_timer!=1)return 9;
   core.frame_counter=256;process_overworld_tasks();if(ow.dad_phone_timer!=0)return 10;
   fprintf(stderr,"PHONE_PHASE overworld\n");update_overworld_frame(23);show(1);
   fprintf(stderr,"PHONE_PHASE dismount\n");
   if(redux){if(ow.dad_phone_queued||ow.pending_interactions)return 11;dismount_bicycle();update_overworld_frame(23);show(2);}
   if(!ow.dad_phone_queued||!ow.pending_interactions)return 12;
   // Save before real queued-interaction dispatch, then cold replay drives the
   // full real text/fade chain; no hand-advanced PI_RESUME is used.
   ow.entity_fade_entity=-1;ow.battle_mode=0;bt.battle_mode_flag=0;
   memset(&g_mode_stack,0,sizeof(g_mode_stack));ModeState root={0};root.overworld.phase=OWP_RESUME_INTERACTION;
   mode_push(GAME_MODE_OVERWORLD,&root);mode_push(GAME_MODE_PROCESS_INTERACTION,NULL);
   if(!state_dump_save_slots())return 13;puts("PHONE_LIFECYCLE_SAVED");continue;
  }
  load_dad_phone();show(index);
 }fclose(f);return 0;
}
'''


def identify(a,out,original,redux):
    old=mapping.ROUTINES
    try:
        mapping.ROUTINES=()
        globals_,addresses,proof=mapping.identify(a,out,original)
    finally:mapping.ROUTINES=old
    folder=out/'source-mapping'
    base=(folder/'movement_speeds.asm').read_text(encoding='utf-8').split('.SEGMENT "CODE"',1)[0]
    base=base.replace('.IMPORT BUFFER: absolute\n','')+f'BUFFER := ${globals_["BUFFER"]:06X}\n'
    include=['--cpu','65816','-D','USA','-I',folder/'include-overlay','-I',a.native_source/'include','-I',a.native_source/'asm']
    result={}
    catalog=(
      ('CHECK_ENTITY_ENEMY_COLLISION','overworld/collision/check_entity_enemy_collision.asm',()),
      ('WRITE_APU_PORT1','overworld/write_apu_port1.asm',()),
      ('START_CAMERA_SHAKE','overworld/camera/start_camera_shake.asm',('WRITE_APU_PORT1',)),
      ('HANDLE_ENEMY_CONTACT','overworld/handle_enemy_contact.asm',('CHECK_ENTITY_ENEMY_COLLISION','DESATURATE_PALETTES','START_CAMERA_SHAKE','IS_BATTLE_SWIRL_ACTIVE')),
      ('QUEUE_INTERACTION','overworld/queue_interaction.asm',()),
      ('GET_EVENT_FLAG','text/get_event_flag.asm',('MODULUS16','POWERS_OF_TWO_8BIT')),
      ('LOAD_DAD_PHONE','overworld/load_dad_phone.asm',('GET_EVENT_FLAG','QUEUE_INTERACTION','MSG_SYS_PAPA_2H')),
      ('PROCESS_OVERWORLD_TASKS','overworld/process_overworld_tasks.asm',('JUMP_TEMP_FUNCTION_POINTER',)),
    )
    for symbol,relative,externals in catalog:
        def assemble(values,start,suffix,source_override=None):
            src=folder/(symbol.lower()+suffix+'.asm');obj=src.with_suffix('.o');blob=src.with_suffix('.bin')
            src.write_text(base+''.join(f'{k} := ${v:06X}\n' for k,v in values.items())+'.SEGMENT "CODE"\n.A16\n.I16\n'+
                ('.INCLUDE "'+relative+'"\n' if source_override is None else source_override),encoding='utf-8')
            cfg=src.with_suffix('.cfg');cfg.write_text((folder/'code.cfg').read_text(encoding='utf-8').replace('start=$C00000',f'start=${start:06X}'),encoding='utf-8')
            mapping.run([a.ca65,*include,src,'-o',obj],src.with_suffix('.compile.log'))
            mapping.run([a.ld65,'-C',cfg,'-o',blob,obj],src.with_suffix('.link.log'));return blob
        placeholder={k:0xC00000 for k in externals};first=assemble(placeholder,0xC00000,'-placeholder');data=first.read_bytes()
        relocs={};mask=set()
        for name in externals:
            positions=[]
            for byte in range(3):
                altered=assemble(dict(placeholder,**{name:0xC00000^(1<<(8*byte))}),0xC00000,f'-reloc-{name}-{byte}').read_bytes()
                offsets=[i for i,(x,y) in enumerate(zip(data,altered)) if x!=y]
                if not offsets:raise ValueError('Missing external relocation '+name)
                positions.append(offsets);mask.update(offsets)
            relocs[name]=positions
        for delta in (1,256):
            altered=assemble(placeholder,0xC00000+delta,'-base'+str(delta)).read_bytes()
            if len(altered)!=len(data):raise ValueError('Function length changed while locating')
            mask.update(i for i,(x,y) in enumerate(zip(data,altered)) if x!=y)
        pattern=b''.join(b'.' if i in mask else re.escape(bytes((v,))) for i,v in enumerate(data))
        found=list(re.finditer(pattern,original,re.S))
        if len(found)!=1:raise ValueError('Full source candidate not unique: '+symbol+' '+str(len(found)))
        at=found[0].start();address=0xC00000+at;actual=original[at:at+len(data)];resolved={}
        for name,positions in relocs.items():
            bytes_=[]
            for offsets in positions:
                values={actual[i] for i in offsets}
                if len(values)!=1:raise ValueError('Repeated relocation inconsistent: '+name)
                bytes_.append(values.pop())
            resolved[name]=int.from_bytes(bytes(bytes_),'little')
        full=assemble(resolved,address,'-verified')
        if mapping.find_unique(original,full.read_bytes(),symbol)!=address:raise ValueError('Unmasked body mismatch')
        redux_actual=redux[at:at+len(actual)]
        row={'symbol':symbol,'address':f'{address:06X}','source':relative,'OriginalByteEqualLength':len(actual),
             'OriginalByteEqualSha256':sha(full),'ResolvedDependencies':{k:f'{v:06X}' for k,v in resolved.items()}}
        if symbol=='WRITE_APU_PORT1':
            if redux_actual[0]!=0x22 or redux_actual[4]!=0xEA:raise ValueError('Pinned MSU fade-hook caller missing')
            hook=int.from_bytes(redux_actual[1:4],'little');expected=bytearray(actual)
            expected[:5]=redux_actual[:5]
            if bytes(expected)!=redux_actual:raise ValueError('APU body changes outside active MSU hook')
            src=folder/'msu-fade-hook.asm';obj=src.with_suffix('.o');blob=src.with_suffix('.bin');cfg=src.with_suffix('.cfg')
            src.write_text('.SEGMENT "CODE"\n.A16\n.I16\nSEP #$20\n.A8\nPHA\nLDA f:$002002\nCMP #$53\nBEQ msu\nend:\nPLA\nORA $1ACB\nRTL\nmsu:\nPLA\nPHA\nSTA f:$7E0103\nBRA end\n',encoding='utf-8')
            cfg.write_text('MEMORY {ROM:start=$'+f'{hook:06X}'+',size=$10000,type=ro,file=%O;} SEGMENTS {CODE:load=ROM,type=ro;}',encoding='utf-8')
            mapping.run([a.ca65,*include,src,'-o',obj],src.with_suffix('.compile.log'));mapping.run([a.ld65,'-C',cfg,'-o',blob,obj],src.with_suffix('.link.log'))
            if redux[hook-0xC00000:hook-0xC00000+blob.stat().st_size]!=blob.read_bytes():raise ValueError('Pinned MSU full fade hook differs from source')
            row.update(ReduxMsuHookAddress=f'{hook:06X}',ReduxMsuHookLength=blob.stat().st_size,ReduxMsuHookSha256=sha(blob))
        elif symbol=='HANDLE_ENEMY_CONTACT':
            source=(a.native_source/'asm'/relative).read_text(encoding='utf-8')
            old='LDA #24\n\tSTA ENEMY_PATHFINDING_TARGET_ENTITY'
            if source.count(old)!=1:raise ValueError('Review current contact patch site')
            patched=assemble(resolved,address,'-redux-verified',source.replace(old,'LDA GAME_STATE+game_state::current_party_members\n\tSTA ENEMY_PATHFINDING_TARGET_ENTITY'))
            if patched.read_bytes()!=redux_actual:raise ValueError('Pinned Redux contact complete byte gate failed')
            row['ReduxByteEqualSha256']=sha(patched);row['ReduxPatchAddress']='C0D668'
        elif symbol=='LOAD_DAD_PHONE':
            source=(a.native_source/'asm'/relative).read_text(encoding='utf-8')
            hook_at=0xC0DCF1;offset=hook_at-address
            if not 0<=offset<len(actual)-4 or redux_actual[offset]!=0x5C:raise ValueError('Pinned Dad JML patch missing')
            hook=int.from_bytes(redux_actual[offset+1:offset+4],'little')
            expected=bytearray(actual);expected[offset:offset+5]=bytes((0x5C,))+hook.to_bytes(3,'little')+bytes((0xEA,))
            if bytes(expected)!=redux_actual:raise ValueError('Dad body has changes outside exact source hook')
            # Verify complete compiled hook against the pinned source semantics.
            hook_source='.SEGMENT "CODE"\n.A16\n.I16\nCMP #0\nBEQ pass\nJMP skip\npass:\nLDA $9883\nCMP #3\nBNE phone\nJMP skip\nphone:\nJML $C0DCF6\nskip:\nJML $C0DD0D\n'
            src=folder/'dad-hook.asm';obj=src.with_suffix('.o');blob=src.with_suffix('.bin');cfg=src.with_suffix('.cfg')
            src.write_text(hook_source,encoding='utf-8');cfg.write_text('MEMORY {ROM:start=$'+f'{hook:06X}'+',size=$10000,type=ro,file=%O;} SEGMENTS {CODE:load=ROM,type=ro;}',encoding='utf-8')
            mapping.run([a.ca65,*include,src,'-o',obj],src.with_suffix('.compile.log'));mapping.run([a.ld65,'-C',cfg,'-o',blob,obj],src.with_suffix('.link.log'))
            if redux[hook-0xC00000:hook-0xC00000+blob.stat().st_size]!=blob.read_bytes():raise ValueError('Pinned Dad full hook bytes differ')
            row.update(ReduxPatchAddress='C0DCF1',ReduxHookAddress=f'{hook:06X}',ReduxHookByteEqualLength=blob.stat().st_size,ReduxHookSha256=sha(blob))
        else:
            if actual!=redux_actual:raise ValueError('Pinned Redux changes dependency '+symbol)
            row['ReduxBodyByteIdentical']=True
        result[symbol]={'address':address,'dependencies':resolved,'abi':'near' if symbol=='PROCESS_OVERWORLD_TASKS' else 'far'};proof.append(row)
    # Cross-check independently assembled dependency bodies against each caller.
    for symbol,row in result.items():
        for name,addr in row['dependencies'].items():
            if name in result and result[name]['address']!=addr:raise ValueError('Caller dependency identity mismatch')
    return globals_,result,proof


def contact_cases():
    labels=('normal-contact','battle-blocked','door-blocked','camera2-blocked','movement-bit-blocked',
            'escalator-blocked','intangible-blocked','no-collision','magic-butterfly')
    return [(leader,player,guard,slot,camera,labels[guard]) for leader in range(24,28)
            for player in (0,1) for guard in range(9) for slot in (0,7) for camera in (0,1)]


def contact_machine(a,out,mode,g,func,rows):
    out.mkdir();samples=out/'samples.jsonl'
    code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230');entry=0xC0FF00+len(code)
    code+=bytes((0x22,))+func['HANDLE_ENEMY_CONTACT']['address'].to_bytes(3,'little')
    code+=bytes.fromhex('8f00707e7b8f08707e3b8f0a707e');finish=0xC0FF00+len(code);code+=bytes((0x4C,entry&255,entry>>8&255))
    def at(n):return g[n]&65535
    gs=at('GAME_STATE');scalar=('ENEMY_PATHFINDING_TARGET_ENTITY','TOUCHED_ENEMY','ENEMY_HAS_BEEN_TOUCHED')
    captures=[at(n) for n in scalar]+[gs+176,at('CAMERA_MODE_3_FRAMES_LEFT'),at('CAMERA_MODE_BACKUP'),at('OVERWORLD_STATUS_SUPPRESSION'),at('BATTLE_SWIRL_COUNTDOWN')]
    init={'BATTLE_MODE':0,'BATTLE_MODE_FLAG':0,'USING_DOOR':0,'BATTLE_SWIRL_COUNTDOWN':0,'ENEMY_HAS_BEEN_TOUCHED':0,
          'PLAYER_MOVEMENT_FLAGS':0,'PLAYER_INTANGIBILITY_FRAMES':0,'ENEMY_PATHFINDING_TARGET_ENTITY':7,'TOUCHED_ENEMY':65535,
          'CAMERA_MODE_3_FRAMES_LEFT':0,'CAMERA_MODE_BACKUP':9,'OVERWORLD_STATUS_SUPPRESSION':0}
    guards={1:at('BATTLE_MODE'),2:at('USING_DOOR'),3:gs+176,4:at('PLAYER_MOVEMENT_FLAGS'),5:gs+142,6:at('PLAYER_INTANGIBILITY_FRAMES')}
    lua=['local output=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))','local rows={'+','.join('{'+','.join(map(str,r[:5]))+'}' for r in rows)+'}',
         'local mem=emu.memType.snesWorkRam','local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256)%256,mem) end',
         'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end','local index=0;local calls=0;local collision=0;local palette=0;local shake=0',
         'local cap={'+','.join(map(str,captures))+'}',
         'emu.addMemoryCallback(function() index=index+1;local r=assert(rows[index],"past corpus");local leader,player,guard,slot,camera=table.unpack(r);'+
         ''.join(f'w16({at(k)},{v});' for k,v in init.items())+f'w16({gs+148},leader);w16({gs+142},0);w16({gs+176},camera);w16({at("CURRENT_ENTITY_SLOT")},slot);'+
         f'for i=0,29 do w16({at("ENTITY_COLLIDED_OBJECTS")}+2*i,65535);w16({at("ENTITY_TICK_CALLBACK_HIGH")}+2*i,0x1200+i) end;'+
         f'w16({at("ENTITY_ENEMY_IDS")}+2*slot,guard==8 and 225 or 1);'+
         f'if player==1 then w16({at("ENTITY_COLLIDED_OBJECTS")}+46,slot) else w16({at("ENTITY_COLLIDED_OBJECTS")}+2*slot,leader) end;'+
         ''.join(f'if guard=={k} then w16({v},{2 if k in (3,4) else 12 if k==5 else 1}) end;' for k,v in guards.items())+
         f'if guard==7 then w16({at("ENTITY_COLLIDED_OBJECTS")}+46,65535);w16({at("ENTITY_COLLIDED_OBJECTS")}+2*slot,65535) end;w16(0x7200,0x55aa) end,emu.callbackType.exec,{entry})',
         f'emu.addMemoryCallback(function() calls=calls+1 end,emu.callbackType.exec,{func["HANDLE_ENEMY_CONTACT"]["address"]})',
         f'emu.addMemoryCallback(function() collision=collision+1 end,emu.callbackType.exec,{func["CHECK_ENTITY_ENEMY_COLLISION"]["address"]})',
         f'emu.addMemoryCallback(function() palette=palette+1 end,emu.callbackType.exec,{func["HANDLE_ENEMY_CONTACT"]["dependencies"]["DESATURATE_PALETTES"]})',
         f'emu.addMemoryCallback(function() shake=shake+1 end,emu.callbackType.exec,{func["START_CAMERA_SHAKE"]["address"]})',
         'emu.addMemoryCallback(function() assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"CPU frame corrupt");assert(r16(0x7200)==0x55aa,"protected RAM corrupt");'+
         'local result={index,r16(0x7000)};for _,addr in ipairs(cap) do result[#result+1]=r16(addr) end;local text="["..table.concat(result,",")..",[";local flags={};'+
         f'for i=0,29 do flags[#flags+1]=r16({at("ENTITY_TICK_CALLBACK_HIGH")}+2*i) end;output:write(text..table.concat(flags,",").."]]\\n");'+
         f'if index==#rows then assert(calls==#rows and collision==96 and palette==32 and shake==32,"actual source dependency count differs");output:flush();output:close();emu.log("CONTACT_COMPLETE "..index.." "..collision.." "..palette.." "..shake);emu.breakExecution() end end,emu.callbackType.exec,{finish})']
    return run_machine(a,out,mode,lua,code,rows,samples,'CONTACT_COMPLETE '+str(len(rows))+' 96 32 32')


def run_machine(a,out,mode,lua,code,rows,samples,marker):
    script=out/'caller.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
    rom=a.rom if mode=='original' else a.redux_rom
    proc=subprocess.run([str(a.oracle.resolve()),str(rom.resolve()),'--home',str(out/'oracle-home'),'--frames','5000','--timeout','60','--lua-timeout','10','--lua-allow-io','--lua',str(script),'--write-memory','SnesPrgRom:0xff00:'+code.hex(),'--set-pc','0xc0ff00','--cpu','Snes'],capture_output=True,timeout=70)
    (out/'oracle.jsonl').write_bytes(proc.stdout);(out/'oracle.stderr').write_bytes(proc.stderr)
    events=[json.loads(x) for x in proc.stdout.decode().splitlines()];logs=[r for r in events if r['event']=='lua_log']
    if proc.returncode or not events[-1].get('ok') or events[-1].get('reason')!='debugger_break' or any(r['error_count'] for r in logs):raise ValueError('Actual machine run incomplete: '+str(events[-2:]))
    if sum(marker in r['text'] for r in logs)!=1:raise ValueError('Exact completion marker absent')
    got=[json.loads(x) for x in samples.read_text(encoding='utf-8').splitlines()]
    if [r[0] for r in got]!=list(range(1,len(rows)+1)):raise ValueError('Machine corpus incomplete/unordered')
    return got,dict(Calls=len(got),ActualOriginalOrPinnedMachineExecuted=True,CompleteOrderedCorpus=True,FrameAndProtectedRamGuards=True,
        CallerSha256=hashlib.sha256(code).hexdigest(),LuaSha256=sha(script),SamplesSha256=sha(samples),CompletionMarker=marker)


def native_contact(a,out,mode,rows,expected):
    out.mkdir();exe,built=private_build(a,out,CONTACT_DRIVER);session=out/'session';session.mkdir();cases=out/'cases.tsv'
    cases.write_text(''.join(f'{i+1} '+ ' '.join(map(str,r[:5]))+'\n' for i,r in enumerate(rows)),encoding='utf-8')
    pack=a.original_assets if mode=='original' else a.redux_assets
    proc=subprocess.run([str(exe),str(pack.resolve()),str(session),str(cases),str(int(mode=='redux'))],capture_output=True,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),timeout=30)
    (out/'native.log').write_bytes(proc.stdout+proc.stderr)
    if proc.returncode:raise ValueError('Native contact runner failed: '+str(proc.returncode)+' '+proc.stderr.decode(errors='replace')[-2000:])
    got=[json.loads(x[len('CONTACT '):]) for x in proc.stdout.decode(errors='replace').splitlines() if x.startswith('CONTACT ')]
    if [r[0] for r in got]!=list(range(1,len(rows)+1)):raise ValueError('Native contact corpus incomplete')
    diff=[dict(Index=i+1,Input=rows[i],ActualMachine=e,ActualNative=g) for i,(e,g) in enumerate(zip(expected,got)) if e!=g]
    return dict(Cases=len(got),MismatchCount=len(diff),FirstMismatches=diff[:16],Build=built)


def phone_cases():
    return [(style,guard,next,current) for style in (0,3) for guard in range(7) for next in range(4) for current in (65535,10)]


def timing_machine(a,out,mode,g,func):
    out.mkdir();rows=[(timer,frame,guard) for timer in (0,1,2,2531,65535) for frame in (0,1,255,256,257,65535) for guard in (0,1)];samples=out/'samples.jsonl'
    address=func['PROCESS_OVERWORLD_TASKS']['address']
    if address>>16!=0xC0:raise ValueError('Near task caller must share source bank')
    code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230');entry=0xC0FF00+len(code)
    code+=bytes((0x20,address&255,address>>8&255))+bytes.fromhex('7b8f08707e3b8f0a707e');finish=0xC0FF00+len(code);code+=bytes((0x4C,entry&255,entry>>8&255))
    def at(n):return g[n]&65535
    lua=['local output=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))','local rows={'+','.join('{'+','.join(map(str,r))+'}' for r in rows)+'}',
      'local mem=emu.memType.snesWorkRam','local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256)%256,mem) end',
      'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end','local index=0;local calls=0;',
      f'emu.addMemoryCallback(function() index=index+1;local r=assert(rows[index],"past corpus");w16({at("DAD_PHONE_TIMER")},r[1]);w16({at("FRAME_COUNTER")},r[2]);w16({at("WINDOW_HEAD")},r[3]==1 and 0 or 65535);'+
      ''.join(f'w16({at(k)},0);' for k in ('BATTLE_MODE_FLAG','BATTLE_SWIRL_COUNTDOWN','ENEMY_HAS_BEEN_TOUCHED'))+
      f'for i=0,3 do w16({at("OVERWORLD_TASKS")}+6*i,0) end;w16(0x7200,0x55aa) end,emu.callbackType.exec,{entry})',
      f'emu.addMemoryCallback(function() calls=calls+1 end,emu.callbackType.exec,{address})',
      f'emu.addMemoryCallback(function() assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"CPU frame corrupt");assert(r16(0x7200)==0x55aa,"protected RAM corrupt");output:write(string.format("[%d,%d]\\n",index,r16({at("DAD_PHONE_TIMER")})));'+
      f'if index==#rows then assert(calls==#rows,"task call count differs");output:flush();output:close();emu.log("PHONE_TIMER_COMPLETE "..index);emu.breakExecution() end end,emu.callbackType.exec,{finish})']
    expected,meta=run_machine(a,out,mode,lua,code,rows,samples,'PHONE_TIMER_COMPLETE '+str(len(rows)))
    return rows,expected,meta


def phone_machine(a,out,mode,g,func,rows):
    out.mkdir();samples=out/'samples.jsonl';code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230');entry=0xC0FF00+len(code)
    code+=bytes((0x22,))+func['LOAD_DAD_PHONE']['address'].to_bytes(3,'little')+bytes.fromhex('7b8f08707e3b8f0a707e');finish=0xC0FF00+len(code);code+=bytes((0x4C,entry&255,entry>>8&255))
    def at(n):return g[n]&65535
    ptr=func['LOAD_DAD_PHONE']['dependencies']['MSG_SYS_PAPA_2H'];queue=at('QUEUED_INTERACTIONS');gs=at('GAME_STATE')
    cap=[at(n) for n in ('DAD_PHONE_QUEUED','NEXT_QUEUED_INTERACTION','CURRENT_QUEUED_INTERACTION','PENDING_INTERACTIONS','CURRENT_QUEUED_INTERACTION_TYPE','DAD_PHONE_TIMER')]+[gs+142]
    guards={1:at('WINDOW_HEAD'),2:at('BATTLE_MODE_FLAG'),3:at('BATTLE_SWIRL_COUNTDOWN'),4:at('ENEMY_HAS_BEEN_TOUCHED'),5:at('DAD_PHONE_QUEUED')}
    init={'WINDOW_HEAD':65535,'BATTLE_MODE_FLAG':0,'BATTLE_SWIRL_COUNTDOWN':0,'ENEMY_HAS_BEEN_TOUCHED':0,'DAD_PHONE_QUEUED':0,'PENDING_INTERACTIONS':0,'DAD_PHONE_TIMER':0}
    lua=['local output=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))','local rows={'+','.join('{'+','.join(map(str,r))+'}' for r in rows)+'}',
      'local mem=emu.memType.snesWorkRam','local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256)%256,mem) end',
      'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end','local index=0;local calls=0;local queuecalls=0;local getflags=0;local cap={'+','.join(map(str,cap))+'}',
      'emu.addMemoryCallback(function() index=index+1;local r=assert(rows[index],"past corpus");local style,guard,next,current=table.unpack(r);'+
      ''.join(f'w16({at(k)},{v});' for k,v in init.items())+f'w16({gs+142},style);w16({at("NEXT_QUEUED_INTERACTION")},next);w16({at("CURRENT_QUEUED_INTERACTION")},next);w16({at("CURRENT_QUEUED_INTERACTION_TYPE")},current);'+
      f'for i=0,3 do w16({queue}+6*i,65535);w16({queue}+6*i+2,0);w16({queue}+6*i+4,0) end;emu.write({at("EVENT_FLAGS")+96},guard==6 and 64 or 0,mem);'+
      ''.join(f'if guard=={k} then w16({v},{0 if k==1 else 1}) end;' for k,v in guards.items())+
      f'w16(0x7200,0x55aa) end,emu.callbackType.exec,{entry})',
      f'emu.addMemoryCallback(function() calls=calls+1 end,emu.callbackType.exec,{func["LOAD_DAD_PHONE"]["address"]})',
      f'emu.addMemoryCallback(function() queuecalls=queuecalls+1 end,emu.callbackType.exec,{func["QUEUE_INTERACTION"]["address"]})',
      f'emu.addMemoryCallback(function() getflags=getflags+1 end,emu.callbackType.exec,{func["GET_EVENT_FLAG"]["address"]})',
      'emu.addMemoryCallback(function() assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"CPU frame corrupt");assert(r16(0x7200)==0x55aa,"protected RAM corrupt");local fields={index};for _,addr in ipairs(cap) do fields[#fields+1]=r16(addr) end;local cells={};'+
      f'for i=0,3 do local at={queue}+6*i;cells[#cells+1]="["..r16(at)..","..((r16(at+2)+65536*r16(at+4))=={ptr} and 1 or 0).."]" end;output:write("["..table.concat(fields,",")..",["..table.concat(cells,",").."]]\\n");'+
      f'if index==#rows then assert(calls==#rows and queuecalls=={16 if mode=="original" else 8} and getflags==32,"source phone dependency count differs");output:flush();output:close();emu.log("PHONE_COMPLETE "..index.." "..queuecalls.." "..getflags);emu.breakExecution() end end,emu.callbackType.exec,{finish})']
    return run_machine(a,out,mode,lua,code,rows,samples,f'PHONE_COMPLETE {len(rows)} {16 if mode=="original" else 8} 32')


def native_phone(a,out,mode,rows,expected):
    out.mkdir();exe,built=private_build(a,out,PHONE_DRIVER);session=out/'session';session.mkdir();cases=out/'cases.tsv'
    cases.write_text(''.join(f'{i+1} '+' '.join(map(str,r))+'\n' for i,r in enumerate(rows)),encoding='utf-8');pack=a.original_assets if mode=='original' else a.redux_assets
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    def execute(action,tsv=cases,private=session):
        try:proc=subprocess.run([str(exe),str(pack.resolve()),str(private),str(tsv),str(int(mode=='redux')),action],capture_output=True,env=env,timeout=30)
        except subprocess.TimeoutExpired as e:
            (private/(action+'-timeout.log')).write_bytes((e.stdout or b'')+(e.stderr or b''));raise
        (private/(action+'.log')).write_bytes(proc.stdout+proc.stderr)
        if proc.returncode:raise ValueError('Native phone '+action+' failed '+str(proc.returncode)+' '+proc.stderr.decode(errors='replace')[-2000:])
        return [json.loads(x[6:]) for x in proc.stdout.decode(errors='replace').splitlines() if x.startswith('PHONE ')]
    got=execute('warm')
    if [r[0] for r in got]!=list(range(1,len(rows)+1)):raise ValueError('Incomplete native phone corpus')
    diff=[dict(Index=i+1,Input=rows[i],ActualMachine=e,ActualNative=g) for i,(e,g) in enumerate(zip(expected,got)) if e!=g]
    cold=[]
    for i in (0,7,8,48,56,63,104):
        private=out/f'cold-{i}';private.mkdir();tsv=private/'case.tsv';tsv.write_text(f'{i+1} '+' '.join(map(str,rows[i]))+'\n',encoding='utf-8')
        execute('prepare',tsv,private);restored=execute('cold',tsv,private)
        if len(restored)!=1:raise ValueError('Cold phone result missing')
        cold.append(dict(Index=i+1,MatchesMachine=restored[0]==expected[i],MatchesWarm=restored[0]==got[i]))
    private=out/'expiry-dismount-lifecycle';private.mkdir();tsv=private/'case.tsv';tsv.write_text('1 0 0 0 65535\n',encoding='utf-8')
    lifecycle=execute('lifecycle',tsv,private)
    if mode=='redux':
        if len(lifecycle)!=2 or lifecycle[0][1]!=0 or lifecycle[0][4]!=0 or lifecycle[0][7]!=3 or lifecycle[1][1]!=1 or lifecycle[1][4]!=1 or lifecycle[1][7]!=0:raise ValueError('Redux expiry/dismount sequence incomplete')
    elif len(lifecycle)!=1 or lifecycle[0][1]!=1 or lifecycle[0][4]!=1 or lifecycle[0][7]!=3:raise ValueError('Original bike call must retain source behavior')
    full=phone_runtime_flow(a,out,mode,exe,private,pack,env)
    return dict(Cases=len(got),MismatchCount=len(diff),FirstMismatches=diff[:16],ColdRestore=cold,ExpiryDismountQueue=lifecycle,FullColdPhoneFlow=full,Build=built)


def phone_runtime_flow(a,out,mode,inspector,queued,pack,env):
    """Drive the actual executable from queued call through native Yes/No UI.

    Every interaction is real text/menu input. No script jump, manual PI_RESUME
    or direct timer reset is injected. The two frozen executables share the same
    prepared private mode-stack state and their final cold states are inspected
    using the untouched production library.
    """
    def inspect(d,label):
        proc=subprocess.run([str(inspector),str(pack.resolve()),str(d),str(d/'inputs.replay'),str(int(mode=='redux')),'inspect'],capture_output=True,env=env,timeout=30)
        (d/(label+'-inspect.log')).write_bytes(proc.stdout+proc.stderr)
        if proc.returncode:raise ValueError('Cold flow inspection failed')
        lines=proc.stdout.decode(errors='replace').splitlines();phones=[json.loads(s[6:]) for s in lines if s.startswith('PHONE ')];modes=[json.loads(s[12:]) for s in lines if s.startswith('PHONE_MODES ')]
        if len(phones)!=1 or len(modes)!=1:raise ValueError('Cold inspector did not complete')
        return dict(Phone=phones[0],Modes=modes[0])
    def run(exe,d,label,press=None,frames=60):
        replay=d/'inputs.replay';replay.write_text(''.join(f'{i} {(press or {}).get(i,0):04X}\n' for i in range(frames+5)),encoding='utf-8')
        config=d/'fixture.ini';config.write_text('companion=1\nfullscreen=0\nmasterVolume=0\nno_dad_calls=0\n',encoding='utf-8')
        proc=subprocess.run([str(exe),'--assets',str(pack.resolve()),'--session-dir',str(d),'--save',str(d/'private.srm'),'--config',str(config),'--allow-redux-development','--headless','--load-state','--fast-forward','--input-script',str(replay),'--frames',str(frames+5),'--capture-state',str(frames-1)],capture_output=True,env=env,timeout=45)
        log=(proc.stdout+proc.stderr).decode(errors='replace');(d/(label+'.log')).write_text(log,encoding='utf-8')
        if proc.returncode or 'savestate: loaded slot' not in log or 'savestate: wrote slot' not in log or re.search(r'\b(FATAL|ERROR|unimplemented|unknown opcode|unknown bank)\b',log,re.I):raise ValueError('Actual phone flow failed: '+log[-1000:])
        return inspect(d,label),log
    menu=out/'actual-phone-menu';menu.mkdir();shutil.copytree(queued/'saves',menu/'saves')
    reached=None
    for index in range(40):
        state,log=run(a.runtime/'player.exe',menu,f'menu-{index}',{5:0x20})
        if ' [1:Yes] [2:No]' in log:
            reached=dict(Chunks=index+1,State=state,MenuSourceConfirmed=True,LogSha256=sha(menu/f'menu-{index}.log'));break
        if state['Phone'][1]==0:raise ValueError('Phone answer was advanced before observed menu')
    if reached is None:raise ValueError('Real automatic Dad call did not reach its source Yes/No menu')
    results=[]
    for buildname in ('player','observer'):
        for answer in ('yes','no'):
            d=out/f'actual-phone-{buildname}-{answer}';d.mkdir();shutil.copytree(menu/'saves',d/'saves');exe=a.runtime/(buildname+'.exe')
            state,log=run(exe,d,'selected-answer',{5:0x100} if answer=='no' else {},frames=10)
            choice=1 if answer=='no' else 0
            if not re.search(r'PC replay window 1 option='+str(choice)+r'.* \[1:Yes\] \[2:No\]',log):raise ValueError('Actual source choice row not selected: '+answer)
            state,log=run(exe,d,'confirm-answer',{5:0x20},frames=60)
            count=0
            while state['Phone'][1]!=0 and count<40:
                state,log=run(exe,d,f'finish-{count}',{5:0x20},frames=60);count+=1
            phone=state['Phone'];reloadtimer=2531 if mode=='redux' else 1687
            if phone[1]!=0 or phone[2]!=phone[3] or phone[4]!=0 or phone[5]!=65535 or not reloadtimer-10<=phone[6]<=reloadtimer or state['Modes']!=[61]:raise ValueError('Full Dad phone did not drain queue/rearm timer at root: '+str(state))
            again=inspect(d,'second-cold-restore')
            if again!=state:raise ValueError('Final cold restored state changed')
            results.append(dict(Build=buildname,ExecutableSha256=sha(exe),Answer=answer,ActualSelectionOption=choice,
                                FinishChunks=count,State=state,SecondColdRestoreEqual=True,ActualDialogueMenuFadeAndQueueFinishExecuted=True))
    return dict(SourceMenuReached=reached,Results=results,NoManualInterpreterJumpOrQueueFinish=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','redux-rom','oracle','ca65','ld65','native-source','project','build','runtime','original-assets','redux-assets','scratch','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--diagnostic',action='store_true');a=p.parse_args();a.scratch=local_scratch(a.scratch);a.native_source=a.native_source.resolve();a.build=a.build.resolve();a.runtime=a.runtime.resolve()
    if a.scratch.exists() or a.output.exists():raise ValueError('Fresh private scratch/output required')
    original=a.rom.read_bytes();redux=a.redux_rom.read_bytes()
    if len(original)!=0x300000 or hashlib.sha1(original).hexdigest()!=US_SHA1:raise ValueError('Exact clean USA ROM required')
    if hashlib.sha256(redux).hexdigest()!='c2a2fc98c7e6518b797959ffadf24ca4db8b4d7745ed3a9eb92eee106db1d0ab':raise ValueError('Exact pinned compiled Redux ROM required')
    files=(a.rom,a.redux_rom,a.original_assets,a.redux_assets,a.runtime/'player.exe',a.runtime/'observer.exe',a.build/'game_lib/libearthbound_game.a',Path(__file__),a.project/'ccscript/bugfixes/swirls_without_ness_fix.ccs',a.project/'ccscript/bugfixes/dad_bike_phone_fix.ccs',a.project/'ccscript/redux/msu1.ccs')
    sourcefiles=[a.native_source/'asm'/p for p in ('overworld/handle_enemy_contact.asm','overworld/load_dad_phone.asm','overworld/queue_interaction.asm','overworld/process_overworld_tasks.asm','overworld/collision/check_entity_enemy_collision.asm','overworld/camera/start_camera_shake.asm','overworld/write_apu_port1.asm','text/get_event_flag.asm')]
    sourcefiles += [a.native_source/'include/structs.asm',a.native_source/'include/macros.asm',a.project/'ccscript/essential/asm65816.ccs',a.project/'ccscript/data/data_35.ccs',a.native_source/'src/entity/callroutine.c',a.native_source/'src/game/overworld.c',a.native_source/'src/game/overworld_interaction.c',a.native_source/'src/include/constants.h']
    identities={str(f):sha(f) for f in (*files,*sourcefiles)};a.scratch.mkdir(parents=True)
    globals_,functions,proof=identify(a,a.scratch,original,redux);rows=contact_cases();modes=[]
    for mode in ('original','redux'):
        expected,machine=contact_machine(a,a.scratch/(mode+'-machine'),mode,globals_,functions,rows)
        native=native_contact(a,a.scratch/(mode+'-native'),mode,rows,expected)
        prows=phone_cases();pexpected,pmachine=phone_machine(a,a.scratch/(mode+'-phone-machine'),mode,globals_,functions,prows)
        pnative=native_phone(a,a.scratch/(mode+'-phone-native'),mode,prows,pexpected)
        trows,texpected,tmeta=timing_machine(a,a.scratch/(mode+'-timing-machine'),mode,globals_,functions)
        folder=a.scratch/(mode+'-phone-native');tsv=folder/'timing.tsv';tsv.write_text(''.join(f'{i+1} {timer} {guard} {frame} 65535\n' for i,(timer,frame,guard) in enumerate(trows)),encoding='utf-8')
        session=folder/'timing';session.mkdir();pack=a.original_assets if mode=='original' else a.redux_assets
        proc=subprocess.run([str(folder/'party-driver.exe'),str(pack.resolve()),str(session),str(tsv),str(int(mode=='redux')),'timing'],capture_output=True,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),timeout=30);(session/'timing.log').write_bytes(proc.stdout+proc.stderr)
        got=[json.loads(s[12:]) for s in proc.stdout.decode(errors='replace').splitlines() if s.startswith('PHONE_TIMER ')]
        if proc.returncode or [r[0] for r in got]!=list(range(1,len(trows)+1)):raise ValueError('Native timing corpus incomplete')
        tdiff=[dict(Index=i+1,Input=trows[i],ActualMachine=e,ActualNative=g) for i,(e,g) in enumerate(zip(texpected,got)) if e!=g]
        modes.append(dict(Mode=mode,ContactMachine=machine,ContactNative=native,PhoneMachine=pmachine,PhoneNative=pnative,TimerMachine=tmeta,TimerNative=dict(Cases=len(got),MismatchCount=len(tdiff),FirstMismatches=tdiff[:10])))
    if any(sha(Path(f))!=h for f,h in identities.items()):raise ValueError('Immutable input changed')
    report=dict(format='redux-contact-phone-hook-qa-v1',ReduxRevision='897d00833f4a08a0a92f106abf631629a6a6a041',Passed=not any(r['ContactNative']['MismatchCount'] or r['PhoneNative']['MismatchCount'] or r['TimerNative']['MismatchCount'] or any(not c['MatchesMachine'] or not c['MatchesWarm'] for c in r['PhoneNative']['ColdRestore']) for r in modes),
        InputIdentities=identities,SourceProof=proof,Modes=modes,CaseGroups=dict(Counter(r[-1] for r in rows)),OwnerSavesTouched=False,
        SharedSourceEdited=False,SharedBuildEdited=False,FullConversionVerified=False,FullPlaythroughVerified=False,
        ReproductionFlags={name:str(getattr(a,name.replace('-','_')).resolve()) for name in ('rom','redux-rom','oracle','ca65','ld65','native-source','project','build','runtime','original-assets','redux-assets','scratch','output')},
        Limits=['Contact first-touch target, return, camera shake/suppression and tick flags are compared through actual callback dispatcher and original/pinned CPU. Prepared collision results are source-defined entry prerequisites; movement geometry creating contact is not tested here.',
                'Palette routine executes on the reference CPU but palette RGB/VRAM and later swirl/battle completion are not compared in this first-touch scope.',
                'Dad call guards, FIFO queue/deduplication, timer clock boundaries and seven cold entries are compared to actual original/pinned CPU. Native full automatic phone Yes/No dialogue, fade, queue finish, rearm and second cold restore run on both exact player/observer binaries.',
                'Phone fixtures use the source-defined single-party and dialogue prerequisites at a private loaded map. Actual two-hour real-time waiting, every late-story speaker branch and bicycle bell/music audibility are not covered here.'])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'Passed':report['Passed'],'Modes':[{'Mode':r['Mode'],'Cases':r['ContactNative']['Cases'],'MismatchCount':r['ContactNative']['MismatchCount']} for r in modes]}),flush=True)
    if not report['Passed'] and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
