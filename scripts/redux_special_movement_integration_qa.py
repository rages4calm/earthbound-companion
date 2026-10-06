# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded actual-pack small-party loads and live special-movement consumers.

Only a fresh private caller is compiled; production objects remain unchanged.
Stamina samples are checked by executing the two complete byte-equal pinned
Redux timer routines in private reference-runner memory. ROM/pixels/saves stay
local. This does not claim a natural Lost Underworld entrance or a playthrough.
"""
import argparse, hashlib, json, os, re, subprocess
from pathlib import Path
import battle_action_catalog_qa as frozen
from build_maternalbound_pack import read_pack
from check_jev_observer_parity import local_scratch
from maternalbound_graphics import slice_rom


DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "game/game_state.h"
#include "game/overworld.h"
#include "game/position_buffer.h"
#include "game/maternalbound.h"
#include "game/map_loader.h"
#include "game/battle.h"
#include "entity/entity.h"
#include "entity/sprite.h"
#include "core/memory.h"
#include "core/mode_stack.h"
#include "core/state_dump.h"
#include "data/assets.h"
#include "platform/platform.h"
#include "platform/pc_options.h"
#include "include/pad.h"
extern int eb_platform_main(int,char**);
static unsigned party_slot(unsigned i){return game_state.party_entity_slots[i*2]|game_state.party_entity_slots[i*2+1]<<8;}
static void world(void){
 game_state.party_count=game_state.player_controlled_party_count=4;game_state.current_party_members=15;
 for(unsigned i=0;i<6;i++){game_state.party_members[i]=game_state.party_order[i]=i<4?i+1:0;memset(&party_characters[i],0,sizeof(party_characters[i]));party_characters[i].level=30;party_characters[i].max_hp=party_characters[i].current_hp=party_characters[i].current_hp_target=300;}
 memset(event_flags,0,sizeof(event_flags));event_flag_set(11);
 game_state.leader_x_coord=7496;game_state.leader_y_coord=9458;initialize_overworld_state();
 pc_options.no_dad_calls=pc_options.no_homesickness=true;
 memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_NONE;
}
static void map_row(unsigned id,unsigned phase,unsigned x,unsigned y){
 ow.current_teleport_destination_x=ow.current_teleport_destination_y=0;game_state.leader_x_coord=x;game_state.leader_y_coord=y;core.pad1_held=0;maternalbound_stamina_reset();
 load_map_at_position(x,y);load_party_at_map_position(4);
 printf("MAP_NATIVE [%u,%u,%u,%u,%u",id,phase,game_state.character_mode,game_state.walking_style,ow.footstep_sound_id);
 for(unsigned i=0;i<4;i++){unsigned e=party_slot(i);printf(",%d",entities.sprite_ids[e]);}puts("]");
}
static void timers(unsigned i){printf("TIMER_NATIVE [%u,%u,%u,%u,%u]\n",i,ow.redux_primary_timer,ow.redux_secondary_timer,maternalbound_running(),event_flag_get(65));}
int main(int argc,char **argv){
 if(argc!=7)return 2;char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);unsigned original=atoi(argv[3]),mode=atoi(argv[5]),surface=atoi(argv[6]);
 char *boot[]={"special-movement-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1",original?"--inspect-shuffle":"--redux-battle-fixture","0"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0])-(original?1:0),boot)!=0 || maternalbound_enabled()==original)return 3;
 platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 4;world();
 FILE *in=fopen(argv[4],"rb");if(!in)return 5;unsigned id,x,y,kind,character,style,small,sf,alt,secondary,status,frame,moving,held;
 if(mode==0){
  while(fscanf(in,"%u %u %u",&id,&x,&y)==3){map_row(id,0,x,y);map_row(id,1,7496,9458);}
 }else if(mode==1){
  unsigned e=party_slot(0);ow.pajama_flag=0;ow.disabled_transitions=0;game_state.party_status=0;game_state.leader_moved=1;
  while(fscanf(in,"%u %u %u %u %u %u %u %u %u",&id,&character,&style,&small,&sf,&alt,&secondary,&status,&held)==9){
   game_state.character_mode=small;game_state.walking_style=style;core.pad1_held=held;
   ow.redux_secondary_timer=secondary;entities.surface_flags[e]=sf;entities.var[4][e]=alt;
   memset(party_characters[character].afflictions,0,sizeof(party_characters[character].afflictions));party_characters[character].afflictions[0]=status;
   unsigned before_style=entities.walking_styles[e],before_hi=entities.graphics_ptr_hi[e],before_lo=entities.graphics_ptr_lo[e],before_bank=entities.graphics_sprite_bank[e];entities.animation_frame[e]=0;
   int sprite=get_party_member_sprite_id(character,style,e,character);unsigned anim=entities.var[3][e],overlay=entities.overlay_flags[e];
   update_party_entity_graphics(character,style,e,character);
   printf("SELECT_NATIVE [%u,%d,%u,%u,%u,%u,%u,%u,%u,%d,%u,%u,%u,%u]\n",id,sprite,anim,overlay,entities.walking_styles[e],entities.graphics_ptr_hi[e],entities.graphics_ptr_lo[e],entities.graphics_sprite_bank[e],entities.var[7][e],entities.animation_frame[e],before_style,before_hi,before_lo,before_bank);
  }
 }else if(mode==2){
  unsigned e=party_slot(0);ow.moving_party_member_entity_id=e;game_state.walking_style=surface;
  while(fscanf(in,"%u %u %u %u %u %u",&id,&secondary,&x,&frame,&moving,&held)==6){
   ow.redux_primary_timer=x;ow.redux_secondary_timer=secondary;entities.var[7][e]=moving;core.frame_counter=frame;core.pad1_held=held;
   maternalbound_stamina_tick();timers(id);
  }
 }else if(mode==3 || mode==4){
  unsigned e=party_slot(0);ow.moving_party_member_entity_id=e;game_state.character_mode=3;game_state.walking_style=surface;
  if(mode==4){if(!state_dump_load_slots())return 6;e=ow.moving_party_member_entity_id;timers(1200);}
  else{maternalbound_stamina_reset();}
  unsigned first=mode==4?1200:0;
  while(fscanf(in,"%u %u %u %u",&id,&frame,&moving,&held)==4){
   if(id<=first)continue;entities.var[7][e]=moving;core.frame_counter=frame;core.pad1_held=held;
   printf("TIMER_INPUT [%u,%u,%u,%u,%u,%u]\n",id,ow.redux_secondary_timer,ow.redux_primary_timer,frame,moving,held);
   maternalbound_stamina_tick();timers(id);
   if(mode==3 && id==1200 && !state_dump_save_slots())return 7;
  }
 }else return 8;
 fclose(in);return 0;
}
'''

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def parse_extra_tables(path):
    text=path.read_text();names=('extra_animation_sprite_table','extra_animation_sprite_table_running1','extra_animation_sprite_table_running2');tables=[]
    for name in names:
        match=re.search(r'^'+name+r':\s*\{(.*?)^\}',text,re.M|re.S)
        if not match:raise ValueError('Pinned source table missing '+name)
        rows=[]
        for row in re.findall(r'ExtraSprites\(([^)]+)\)',match[1]):
            entry,dead,normal,ladder,robot,rope,tinyghost,tiny=map(int,row.split(','))
            if entry!=len(rows):raise ValueError('Unexpected source row order')
            rows.append([normal,dead,ladder,rope,tiny,tinyghost,robot,65535])
        if len(rows)!=17:raise ValueError('Unexpected source table length')
        tables.append(rows)
    return tables


def timer_sources(a,out,rom):
    """Mechanically translate the two active CCS bodies; demand full equality."""
    source=a.project/'ccscript/redux/run_stamina_mechanic.ccs';text=source.read_text()
    hook=slice_rom(rom,0xc0b824,4)
    if hook[0]!=0x22:raise ValueError('Active wait-frame stamina hook is not JSL')
    entry=int.from_bytes(hook[1:],'little');stub=slice_rom(rom,entry,13)
    if stub[::4][:3]!=bytes((0x22,0x22,0x22)) or int.from_bytes(stub[1:4],'little')!=0xc08756 or stub[12]!=0x6b:
        raise ValueError('Active stamina update is not the source three calls and RTL')
    values={'RAM_primary_timer':0x3250,'RAM_secondary_timer':0x3251,'stamina_max':15,'stamina_cooldown':8}
    opcodes={'SEP':(0xe2,1),'REP':(0xc2,1),'LDA_a':(0xad,2),'LDA_x':(0xbd,2),'AND_8':(0x29,1),'CMP_8':(0xc9,1),'ORA_8':(0x09,1),'STA_a':(0x8d,2),'INC_a':(0xee,2),'DEC_a':(0xce,2),'ADC_8':(0x69,1),'SBC_8':(0xe9,1),'BNE':(0xd0,1),'BEQ':(0xf0,1),'BRA':(0x80,1)}
    singles={'ASL':0x0a,'TAX':0xaa,'RTL':0x6b,'CLC':0x18,'SEC':0x38}
    proof=[];addresses=[]
    for i,name in enumerate(('primary_timer_update','secondary_timer_update')):
        entry=int.from_bytes(stub[5+i*4:8+i*4],'little');addresses.append(entry)
        match=re.search(r'^'+name+r':\s*\{(.*?)^\}',text,re.M|re.S)
        if not match:raise ValueError('Active source timer body missing')
        code=['.segment "CODE"']
        for line in match[1].splitlines():
            line=line.split('//',1)[0].strip()
            if not line:continue
            if re.fullmatch(r'\w+:',line):code.append(line);continue
            if line in singles:code.append(f'.byte ${singles[line]:02x}');continue
            m=re.fullmatch(r'(\w+)\(([^)]+)\)',line)
            if not m:raise ValueError('Review new timer source instruction: '+line)
            op,arg=m.groups()
            if op in ('BEQ_a','BNE_a','BRA_a'):
                if op!='BRA_a':code.append('.byte $'+('d0' if op=='BEQ_a' else 'f0')+',$03')
                code.extend(('.byte $4c','.word '+arg));continue
            if op not in opcodes:raise ValueError('Review new timer macro '+op)
            opcode,n=opcodes[op];value=values[arg] if arg in values else int(arg,0)
            code.append('.byte '+','.join(f'${v:02x}' for v in bytes((opcode,))+value.to_bytes(n,'little')))
        folder=out/name;folder.mkdir();asm=folder/'source.asm';obj=folder/'source.o';blob=folder/'source.bin';cfg=folder/'source.cfg'
        asm.write_text('\n'.join(code)+'\n');cfg.write_text(f'MEMORY {{ ROM:start=${entry&65535:04X},size=$10000,type=ro,file=%O; }} SEGMENTS {{ CODE:load=ROM,type=ro; }}\n')
        for cmd,log in (([a.ca65,'--cpu','65816',asm,'-o',obj],folder/'compile.log'),([a.ld65,'-C',cfg,'-o',blob,obj],folder/'link.log')):
            q=subprocess.run(list(map(str,cmd)),capture_output=True,timeout=30);log.write_bytes(q.stdout+q.stderr)
            if q.returncode:raise RuntimeError(log.name+' failed')
        body=blob.read_bytes()
        if slice_rom(rom,entry,len(body))!=body:raise ValueError('Complete pinned timer body not byte-equal: '+name)
        proof.append({'sourceFunction':name,'compiledAddress':f'{entry:06X}','byteEqualLength':len(body),'byteEqualSha256':sha(blob)})
    return addresses,proof


def timer_machine(a,out,addresses,rows):
    out.mkdir();samples=out/'samples.jsonl'
    code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230');begin=0xc0ff00+len(code)
    # The source helpers use A8/TAX with X16, so the incoming B byte must be
    # explicit. Supply A16=0; do not accidentally leak the setup DP/SP into B.
    code+=bytes.fromhex('a90000')
    for address in addresses:code+=bytes((0x22,))+address.to_bytes(3,'little')
    code+=bytes.fromhex('7b8f08707e3b8f0a707e');end=0xc0ff00+len(code);code+=bytes((0x4c,begin&255,begin>>8&255))
    lua=['local out=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))',
         'local rows='+json.dumps(rows,separators=(',',':')).replace('[','{').replace(']','}'),
         'local m=emu.memType.snesWorkRam','local function w16(a,v) emu.write(a,v%256,m);emu.write(a+1,math.floor(v/256)%256,m) end',
         'local function r16(a) return emu.read(a,m)+256*emu.read(a+1,m) end','local i=0;local primary=0;local secondary=0;w16(0x7200,0x55aa)',
         'emu.addMemoryCallback(function() i=i+1;local r=assert(rows[i],"past corpus");emu.write(0x3251,r[2],m);emu.write(0x3250,r[3],m);emu.write(2,r[4]%256,m);w16(0x9889,23);w16(0x1002+46,r[5]);w16(0x65,r[6]);end,emu.callbackType.exec,'+str(begin)+')',
         'emu.addMemoryCallback(function() primary=primary+1 end,emu.callbackType.exec,'+str(addresses[0])+')',
         'emu.addMemoryCallback(function() secondary=secondary+1 end,emu.callbackType.exec,'+str(addresses[1])+')',
         'emu.addMemoryCallback(function() assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"CPU frame corrupted");assert(r16(0x7200)==0x55aa,"protected RAM corrupted");out:write(string.format("[%d,%d,%d]\\n",i,emu.read(0x3250,m),emu.read(0x3251,m)));if i==#rows then assert(primary==#rows and secondary==#rows,"call count differs");out:flush();out:close();emu.log("STAMINA_COMPLETE "..i);emu.breakExecution() end end,emu.callbackType.exec,'+str(end)+')']
    script=out/'timer.lua';script.write_text('\n'.join(lua)+'\n')
    q=subprocess.run([str(a.oracle.resolve()),str(a.redux_rom.resolve()),'--home',str(out/'oracle-home'),'--frames','10000','--timeout','90','--lua-timeout','30','--lua-allow-io','--lua',str(script),'--write-memory','SnesPrgRom:0xff00:'+code.hex(),'--set-pc','0xc0ff00','--cpu','Snes'],capture_output=True,timeout=100)
    (out/'oracle.stdout.jsonl').write_bytes(q.stdout);(out/'oracle.stderr.log').write_bytes(q.stderr)
    events=[json.loads(s) for s in q.stdout.decode().splitlines()];logs=[r for r in events if r['event']=='lua_log'];markers=[r['text'] for r in logs if 'STAMINA_COMPLETE ' in r['text']]
    if q.returncode or not events[-1].get('ok') or events[-1].get('reason')!='debugger_break' or any(r['error_count'] for r in logs) or len(markers)!=1:
        raise RuntimeError('Actual pinned timer execution incomplete: '+q.stderr.decode(errors='replace'))
    got=[json.loads(s) for s in samples.read_text().splitlines()]
    if [r[0] for r in got]!=list(range(1,len(rows)+1)):raise ValueError('Actual source timer corpus incomplete')
    return got,{'executedCalls':len(got),'completeCallMarker':markers[0],'samplesSha256':sha(samples),'callerSha256':hashlib.sha256(code).hexdigest().upper(),'luaSha256':sha(script),'protectedRamStackAndDirectPagePassed':True}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('build','native-source','runtime','assets','original-assets','scratch','project','frozen-source','redux-rom','oracle','ca65','ld65','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--diagnostic',action='store_true');a=p.parse_args();a.scratch=local_scratch(a.scratch)
    if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch and report required')
    pin=subprocess.check_output(['git','-C',str(a.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=frozen.PIN:raise ValueError('Unexpected Redux source pin')
    a.scratch.mkdir(parents=True);frozen.DRIVER=DRIVER;exe,build=frozen.private_build(a)
    identity_paths=(a.assets,a.original_assets,a.redux_rom,a.oracle,a.ca65,a.ld65,a.runtime/'player.exe',a.runtime/'observer.exe',a.build/'game_lib/libearthbound_game.a',a.frozen_source/'native-companion.patch')
    identities={str(n.resolve()):sha(n) for n in identity_paths}
    tables=parse_extra_tables(a.project/'ccscript/redux/four_frames_run.ccs');cases=[];failures=[];assertions=0;source_inputs=[];native_timer_outputs=[]
    def check(name,ok,detail):
        nonlocal assertions
        assertions+=1
        if not ok:failures.append({'check':name,'detail':detail})
    def run(profile,pak,folder,mode,inputs,style=0):
        folder.mkdir(exist_ok=True);source=folder/'cases.tsv';source.write_text(''.join(' '.join(map(str,r))+'\n' for r in inputs))
        q=subprocess.run([str(exe.resolve()),str(pak.resolve()),str(folder.resolve()),str(int(profile=='Original')),str(source.resolve()),str(mode),str(style)],cwd=folder,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=180)
        log=q.stdout.decode(errors='replace')+'\n'+q.stderr.decode(errors='replace');(folder/f'native-{mode}.log').write_text(log)
        check(folder.name+' process',q.returncode==0,{'returnCode':q.returncode,'tail':log[-1800:] if q.returncode else None})
        warnings=[s for s in log.splitlines() if re.search(r'unhandled|unknown|unimplemented|FATAL',s,re.I)]
        check(folder.name+' no fallback',not warnings,warnings)
        return [(line.split(' ',1)[0],json.loads(line.split(' ',1)[1])) for line in log.splitlines() if line.startswith(('MAP_NATIVE ','SELECT_NATIVE ','TIMER_NATIVE ','TIMER_INPUT '))]
    styles=(0,6,7,8,10,13);surfaces=(0,8,12);states=(143,128,120);statuses=(0,1,3)
    for profile,pak in (('Original',a.original_assets),('Redux',a.assets)):
        assets=read_pack(pak,a.native_source/'src/data/runtime_generated/asset_ids.h')[2];attrs=assets['data/per_sector_attributes.bin'];smallsectors=[i for i in range(len(attrs)//2) if int.from_bytes(attrs[i*2:i*2+2],'little')&7==3]
        inputs=[[i,i%32*256+128,i//32*128+64] for i in smallsectors];rows=[r for tag,r in run(profile,pak,a.scratch/(profile.lower()+'-maps'),0,inputs) if tag=='MAP_NATIVE']
        check(profile+' complete small-sector/return corpus',len(rows)==len(inputs)*2,{'expected':len(inputs)*2,'actual':len(rows)})
        normal_mode=int.from_bytes(attrs[((9458//128)*32+7496//256)*2:((9458//128)*32+7496//256+1)*2],'little')&7
        for row in rows:
            expected=[row[0],row[1],3,10 if profile=='Original' else 6,6,27,28,29,30] if not row[1] else [row[0],1,normal_mode,0,normal_mode*2,1,2,3,4]
            check(profile+' small/return '+str(row[:2]),row==expected,{'expected':expected,'actual':row})
            cases.append({'profile':profile,'kind':'actual-packed-small-sector-party-load' if not row[1] else 'production-return-to-normal-map','sector':row[0],'phase':row[1],'native':row})
        gfx=assets['data/playable_character_graphics_table.bin'];base=[[int.from_bytes(gfx[(i*8+j)*2:(i*8+j+1)*2],'little') for j in range(8)] for i in range(17)]
        if profile=='Redux':
            check('Redux four-frame container signature',gfx[272:280]==b'MRWALK01',None)
            for variant,table in enumerate(tables):
                expected=b''.join(v.to_bytes(2,'little') for row in table for v in row);actual=gfx[280+variant*272:280+(variant+1)*272]
                check('Redux source graphics variant'+str(variant),actual==expected,{'sourceTable':variant})
        inputs=[];expected=[]
        for char in range(4):
            for small in (0,3):
                for style in styles:
                    for sf in surfaces:
                        for alt in (0,1):
                            for secondary in states:
                                for status in statuses:
                                    for held in (0,16384):
                                        i=len(inputs);inputs.append([i,char,style,small,sf,alt,secondary,status,held]);running=profile=='Redux' and secondary&128 and held
                                        column=1 if status==1 else (2 if style==7 else 3 if style==8 else 0)
                                        if small==3:column+=4
                                        table=tables[2 if alt else 1] if running else tables[0] if alt and profile=='Redux' else base
                                        animation=56 if status==3 else 5 if running else 16 if status==1 else {0:8,8:16,12:24}[sf]
                                        overlay=0 if small else 2 if profile=='Redux' and not secondary&128 else 0
                                        sprite=table[char][column]
                                        expected.append([i,-1 if sprite==65535 else sprite,animation,overlay,style])
        rows=[r for tag,r in run(profile,pak,a.scratch/(profile.lower()+'-selector'),1,inputs) if tag=='SELECT_NATIVE']
        check(profile+' complete selector corpus',len(rows)==len(inputs),{'expected':len(inputs),'actual':len(rows)})
        ptrs=assets['overworld_sprites/sprite_grouping_ptr_table.bin'];groups=assets['overworld_sprites/sprite_grouping_data.bin']
        for row,wanted,context in zip(rows,expected,inputs):
            check(profile+' source selector '+str(row[0]),row[:4]==wanted[:4] and (row[1]<0 or row[4]==wanted[4]),{'context':context,'expected':wanted,'native':row})
            if row[1]<0:
                check(profile+' source intentional hidden tiny-rope '+str(row[0]),row[9]==-1 and row[4:8]==row[10:14],{'native':row})
            else:
                offset=int.from_bytes(ptrs[row[1]*4:row[1]*4+4],'little')-0xef1a7f
                check(profile+' actual graphics group acquired '+str(row[0]),0<=offset<len(groups)-9 and row[5:8]==[0,(offset+9)&65535,groups[offset+8]] and not row[8]&0xe000,{'native':row,'normalizedGroupOffset':offset})
        cases.append({'profile':profile,'kind':'production-special-style-sprite-and-graphics-consumers','executedCases':len(rows),'styles':list(styles),'surfaceFlags':list(surfaces),'characters':[0,1,2,3],'modes':[0,3],'statusCodes':list(statuses),'graphicsPointerAcquisitionExecuted':True})
        # Boundary corpus comes from source timer byte domains, not a copied
        # native formula. Original's no-op is a separately asserted control.
        inputs=[]
        for secondary in (143,142,129,128,127,121,120,15,14,1,0):
            for primary in (191,190,128,127,64,63,62,2,1,0,255):
                for frame in (0,1,127,128,255):
                    for moving in (0,1,256,8192,32768):
                        for held in (0,16384):inputs.append([len(inputs),secondary,primary,frame,moving,held])
        rows=[r for tag,r in run(profile,pak,a.scratch/(profile.lower()+'-timer-boundaries'),2,inputs) if tag=='TIMER_NATIVE']
        check(profile+' complete timer boundary corpus',len(rows)==len(inputs),{'expected':len(inputs),'actual':len(rows)})
        if profile=='Original':
            for actual,given in zip(rows,inputs):check('Original stamina handler inert'+str(actual[0]),actual[1:3]==[given[2],given[1]] and actual[4]==0,{'input':given,'native':actual})
        else:source_inputs.extend(inputs);native_timer_outputs.extend(r[1:3] for r in rows)
        cases.append({'profile':profile,'kind':'production-stamina-boundary-callback','executedCases':len(rows)})
        if profile=='Redux':
            timeline=[[i,i%256,0 if i<=1200 or i>2350 else 8192,16384 if i<=1200 or i>2350 else 0] for i in range(1,2471)]
            for style in (0,6,7,8,13):
                folder=a.scratch/f'redux-timeline-style{style}';result=run(profile,pak,folder,3,timeline,style)
                ins=[r for t,r in result if t=='TIMER_INPUT'];outs=[r for t,r in result if t=='TIMER_NATIVE']
                check('style'+str(style)+' full trace',len(ins)==len(outs)==len(timeline),{'inputs':len(ins),'outputs':len(outs)})
                source_inputs.extend(ins);native_timer_outputs.extend(r[1:3] for r in outs)
                check('style'+str(style)+' exhaustion/recovery reachable',any(r[2]==120 for r in outs[:1200]) and any(r[2]==143 for r in outs[1200:2350]),None)
                cold=run(profile,pak,folder,4,timeline,style);coldouts=[r for t,r in cold if t=='TIMER_NATIVE']
                warm=[r for r in outs if r[0]>=1200]
                check('style'+str(style)+' separate-process stamina checkpoint identical',coldouts==warm,{'warmCount':len(warm),'coldCount':len(coldouts),'firstCold':coldouts[:2],'firstWarm':warm[:2]})
                for r,inputrow in zip(outs,timeline):check('style'+str(style)+' run flag'+str(r[0]),r[3]==r[4]==int(bool(r[2]&128 and inputrow[3]&16384)),{'row':r,'input':inputrow})
                cases.append({'profile':profile,'kind':'source-stamina-special-style-timeline','walkingStyle':style,'executedTicks':len(outs),'coldContinuationTicks':max(0,len(coldouts)-1),'surroundingWalkingExecuted':False})
    rom=a.redux_rom.read_bytes()
    terrain_hooks={0xc03ae3:bytes((6,)),0xc02f45:bytes((0xea,))*3,0xc031cd:bytes((0xea,))*3}
    for address,wanted in terrain_hooks.items():check('active fast-terrain patch '+f'{address:06X}',slice_rom(rom,address,len(wanted))==wanted,{'sourceAddress':f'{address:06X}'})
    addresses,proof=timer_sources(a,a.scratch,rom);machine,metadata=timer_machine(a,a.scratch/'actual-stamina-machine',addresses,source_inputs)
    metadata.update({'incomingA16':0,'incomingDirectPage':4096,'incomingStack':8191,'incomingDataBank':126,'controllerWordRamAddress':'0065','sourceReadsControllerHighByteAt':'0066','movingEntityId':23})
    check('full actual source machine/native paired corpus',len(machine)==len(native_timer_outputs),{'machine':len(machine),'native':len(native_timer_outputs)})
    for i,(reference,actual) in enumerate(zip(machine,native_timer_outputs)):check('actual pinned timer pair'+str(i),reference[1:3]==actual,{'source':reference[1:3],'native':actual,'context':source_inputs[i]})
    paths=('src/game/overworld.c','src/game/position_buffer.c','src/game/maternalbound.c','src/game_main.c','src/core/state_dump.c')
    source={n:sha(a.native_source/n) for n in paths};snapshots={n:sha(a.frozen_source/n) for n in paths if (a.frozen_source/n).is_file()}
    for n,value in snapshots.items():check('frozen source '+n,value==source[n],{'current':source[n],'frozen':value})
    original_root=a.native_source.parent/'_BuildScratch/upstream'
    original_references=('asm/overworld/party/get_party_member_sprite_id.asm','asm/overworld/party/update_party_entity_graphics.asm','asm/overworld/party/load_party_at_map_position.asm','asm/overworld/update_joypad_state.asm','asm/system/wait_until_next_frame.asm')
    for path,value in identities.items():check('read-only input '+Path(path).name,sha(Path(path))==value,None)
    maploads=sum(c['kind'] in ('actual-packed-small-sector-party-load','production-return-to-normal-map') for c in cases)
    selectorcases=sum(c.get('executedCases',0) for c in cases if c['kind']=='production-special-style-sprite-and-graphics-consumers')
    boundaries=sum(c.get('executedCases',0) for c in cases if c['kind']=='production-stamina-boundary-callback')
    timelines=sum(c.get('executedTicks',0) for c in cases);coldticks=sum(c.get('coldContinuationTicks',0) for c in cases)
    report={'format':'redux-special-movement-integration-qa-v1','Passed':not failures,'allPassed':not failures,'executedNativeCases':maploads+selectorcases+boundaries+timelines+coldticks,'executedAssertions':assertions,'executedMapLoads':maploads,'executedSelectorCases':selectorcases,'executedTimerBoundaryCases':boundaries,'executedTimelineTicks':timelines,'executedColdContinuationTicks':coldticks,'separateProcessColdContinuations':5,'executedMachineTimerPairs':len(machine),'skippedCases':0,'failures':failures,'cases':cases,'privateBuild':build,'runtimeSha256':{n:sha(a.runtime/n) for n in ('player.exe','observer.exe')},'packSha256':{'Original':sha(a.original_assets),'Redux':sha(a.assets)},'sourceSha256':source,'frozenSourceMatchedFiles':list(snapshots),'frozenFullPatchSha256':sha(a.frozen_source/'native-companion.patch'),'originalReferenceSha256':{n:sha(original_root/n) for n in original_references},'pinnedReduxRevision':pin,'pinnedSourceSha256':{n:sha(a.project/n) for n in ('ccscript/redux/fast_terrain.ccs','ccscript/redux/four_frames_run.ccs','ccscript/redux/run_patch.ccs','ccscript/redux/run_stamina_mechanic.ccs','ccscript/essential/asm65816.ccs')},'actualTimerMachine':metadata,'compiledTimerSourceProof':proof,'compiledReduxRomSha256':sha(a.redux_rom),'readOnlyInputHashesChecked':True,'toolSha256':sha(Path(__file__)),'ownerSavesTouched':False,'sharedBuildModified':False,'fullConversionVerified':False,'fullPlaythroughVerified':False,'limits':['All actual small-party sector centers are prepared through production LOAD_MAP_AT_POSITION/LOAD_PARTY_AT_MAP_POSITION; each is followed by an actual normal-map reload. Natural entrance door/dialogue and traversability of every sector center are not tested.','Special-style graphics selectors execute actual get/update consumers. Sprite IDs and animation speeds are source/table contracts; this does not prove full audiovisual geometry, collision or rendered pixel parity for tiny/rope/stair art.','The source complete primary/secondary timer bodies are mechanically translated from pinned CCS and verified byte-equal against active hook targets. The actual compiled pinned routines execute with prepared RAM; the source WaitFrame and surrounding full SNES world are not executed.','The source SEP A8/TAX X16 helpers retain the incoming accumulator B byte. This corpus explicitly supplies A16=0, a source steady-input WaitFrame return context (PAD_PRESS=0). It does not establish every nonzero incoming B-byte/controller edge context.','Stamina timelines invoke the unchanged native production per-frame consumer with explicitly supplied source moving/static var7 and controller signals. They do not pretend an actual natural rope/stair transaction was walked end to end.','Cold tests use only own private timer checkpoints; they establish serialized timer/run-flag continuation, not generic compatibility for already-wrong historical event PCs.','Run-button inversion and original Skip Sandwich versus Redux run semantics remain native adaptations outside this flag56-clear bounded corpus.','Observer identity is paired provenance; caller links player production objects. ROM/pack/sprite/save/reference-runner artifacts remain private inputs.']}
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ('Passed','executedAssertions','executedMapLoads','executedMachineTimerPairs','skippedCases')}));print(json.dumps(failures[:12]))
    if failures and not a.diagnostic:raise SystemExit(1)


if __name__=='__main__':main()
