# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared production Town Map/game-over upload and base-render audit.

Private raw frames/VRAM and ROM bytes stay outside public reports. Source parity
is separate from successful native execution and donor upload controls.
"""
import argparse, hashlib, json, os, struct, subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
import battle_art_decode_qa_dev20 as art
from build_maternalbound_pack import read_pack
from maternalbound_graphics import asm_pointer, snes_offset
from audit_converter_family_coverage_dev21 import town_pixels

ROOT=Path(__file__).resolve().parents[1]
DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "core/mode_stack.h"
#include "core/memory.h"
#include "game/battle.h"
#include "game/game_state.h"
#include "game/overworld.h"
#include "game/map_loader.h"
#include "game/town_map.h"
#include "game/fade.h"
#include "game/window.h"
#include "game/maternalbound.h"
#include "entity/entity.h"
#include "entity/sprite.h"
#include "snes/ppu.h"
#include "platform/platform.h"
#include "data/assets.h"
#include "include/pad.h"
extern int eb_platform_main(int,char**);
static pixel_t frame[EB_VIEWPORT_HEIGHT][EB_VIEWPORT_WIDTH];
static void scanline(int y,const pixel_t*row){if(y>=0&&y<EB_VIEWPORT_HEIGHT)memcpy(frame[y],row,sizeof(frame[y]));}
static void save(const char*folder,const char*kind,unsigned id,const void*p,size_t n){char path[4096];snprintf(path,sizeof(path),"%s/%s-%u.raw",folder,kind,id);FILE*f=fopen(path,"wb");if(!f)exit(12);fwrite(p,1,n,f);fclose(f);}
static void snapshot(const char*folder,const char*kind,unsigned id){
 char name[64];snprintf(name,sizeof(name),"%s-vram",kind);save(folder,name,id,ppu.vram,sizeof(ppu.vram));
 snprintf(name,sizeof(name),"%s-palette",kind);save(folder,name,id,ert.palettes,sizeof(ert.palettes));
 snprintf(name,sizeof(name),"%s-oam",kind);save(folder,name,id,ppu.oam,sizeof(ppu.oam));
 ppu_render_frame(scanline);snprintf(name,sizeof(name),"%s-frame",kind);save(folder,name,id,frame,sizeof(frame));
 unsigned old=ppu.tm;ppu.tm=1;ppu_render_frame(scanline);snprintf(name,sizeof(name),"%s-bgframe",kind);save(folder,name,id,frame,sizeof(frame));ppu.tm=old;
 printf("QA_CAPTURE {\"kind\":\"%s\",\"id\":%u,\"width\":%u,\"height\":%u,\"bgYOffset\":%d,\"brightness\":%u,\"mode\":%u,\"tm\":%u,\"ts\":%u,\"bgSc\":%u,\"bgNba\":%u,\"objConfig\":%u,\"oamCount\":%u,\"xy\":[%u,%u]}\n",kind,id,EB_VIEWPORT_WIDTH,EB_VIEWPORT_HEIGHT,ppu.bg_win_y_offset,ppu.inidisp,ppu.bgmode,ppu.tm,ppu.ts,ppu.bg_sc[0],ppu.bg_nba[0],ppu.obsel,ert.oam_write_index,game_state.leader_x_coord,game_state.leader_y_coord);
}
static void source_label_control(const char*folder,unsigned id){
 char path[4096];snprintf(path,sizeof(path),"%s/source-label.raw",folder);FILE*f=fopen(path,"rb");if(!f)exit(13);
 unsigned char old[0x2400],source[0x2400];memcpy(old,ppu.vram+0xc000,sizeof(old));memcpy(source,old,sizeof(old));size_t n=fread(source,1,sizeof(source),f);fclose(f);if(n!=8832&&n!=9216)exit(14);
 memcpy(ppu.vram+0xc000,source,sizeof(source));ppu_render_frame(scanline);save(folder,"town-source-label-frame",id,frame,sizeof(frame));memcpy(ppu.vram+0xc000,old,sizeof(old));
}
static void party(unsigned leader){
 memset(event_flags,0,sizeof(event_flags));event_flag_set(11);
 game_state.party_count=game_state.player_controlled_party_count=1;game_state.party_npc_1=game_state.party_npc_2=0;
 game_state.party_npc_1_id_copy=game_state.party_npc_2_id_copy=0;
 memset(game_state.party_members,0,sizeof(game_state.party_members));memset(game_state.party_order,0,sizeof(game_state.party_order));
 game_state.party_members[0]=game_state.party_order[0]=leader;
 for(unsigned i=0;i<4;i++){CharStruct*c=&party_characters[i];memset(c,0,sizeof(*c));c->level=10;c->max_hp=c->current_hp=c->current_hp_target=100;c->max_pp=c->current_pp=c->current_pp_target=30;}
}
int main(int argc,char**argv){
 if(argc!=4)return 2;char session[4096];snprintf(session,sizeof(session),"%s/fixture.srm",argv[2]);
 char*boot[]={"retained-art-qa","--assets",argv[1],"--session-dir",argv[2],"--save",session,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot))return 3;
 platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 4;game_set_fast_forward(true);
 load_sprite_data();window_system_init();bt.battle_mode_flag=0;
 if(!strcmp(argv[3],"town")){
  const unsigned char*sectors=ASSET_DATA(ASSET_DATA_PER_SECTOR_TOWN_MAP_BIN);size_t sectorbytes=ASSET_SIZE(ASSET_DATA_PER_SECTOR_TOWN_MAP_BIN);
  for(unsigned id=0;id<6;id++){
   party(1);for(unsigned f=681;f<=686;f++)event_flag_set(f);unsigned sector=0;for(;sector+2<sectorbytes;sector+=3)if((sectors[sector]&15)==id+1)break;if(sector+2>=sectorbytes)return 20;
   game_state.leader_x_coord=(sector/3%32)*256+128;game_state.leader_y_coord=(sector/96)*128+64;initialize_overworld_state();
   memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_TOWN_MAP;
   save(argv[2],"town-pre-vram",id,ppu.vram,sizeof(ppu.vram));ModeState*s=&g_mode_stack.state[0];run_town_map_menu_prepare(s);s->town_map.map_id=id;core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=0;
   unsigned steps=0;while((s->town_map.phase!=TM_MAIN||fade_active())&&++steps<100){StepResult r=mode_step_town_map(s);if(r.kind!=STEP_CONTINUE)return 21;host_process_frame();core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=0;}
   if(steps>=100)return 22;
   StepResult r=mode_step_town_map(s);if(r.kind!=STEP_CONTINUE)return 23;host_process_frame();snapshot(argv[2],"town",id);source_label_control(argv[2],id);
   core.pad1_pressed=PAD_A;r=mode_step_town_map(s);core.pad1_pressed=0;
   printf("QA_EXIT {\"kind\":\"town\",\"id\":%u,\"steps\":%u,\"stepKind\":%u,\"tm\":%u,\"bgMode\":%u,\"phase\":%u}\n",id,steps,r.kind,ppu.tm,ppu.bgmode,s->town_map.phase);
   if(r.kind!=STEP_POP)return 24;
  }
 }else if(!strcmp(argv[3],"gameover")){
  for(unsigned variant=0;variant<2;variant++){
   party(variant?3:1);game_state.leader_x_coord=1952;game_state.leader_y_coord=1584;initialize_overworld_state();
   memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_GAME_OVER;
   ModeState*s=&g_mode_stack.state[0];s->game_over.phase=GO_ENTER;bt.party_members_alive_overworld=0;
   unsigned steps=0;while(s->game_over.phase!=GO_CB_PAUSE&&++steps<100){
    StepResult r=mode_step_game_over(s);if(r.kind!=STEP_PUSH||r.push_mode!=GAME_MODE_FADE_WAIT)return 30;
    ModeState child=*r.push_init;unsigned childsteps=0;while(++childsteps<100){StepResult c=mode_dispatch_step(GAME_MODE_FADE_WAIT,&child);if(c.kind==STEP_POP)break;if(c.kind!=STEP_CONTINUE)return 31;host_process_frame();}if(childsteps>=100)return 32;
   }
   if(steps>=100)return 33;snapshot(argv[2],"gameover",variant);
   // Staged post-dialogue Continue cleanup; the comeback text is outside this art fixture.
   s->game_over.phase=GO_CONT_FADE;StepResult r=mode_step_game_over(s);if(r.kind!=STEP_PUSH||r.push_mode!=GAME_MODE_FADE_WAIT)return 34;
   ModeState child=*r.push_init;unsigned childsteps=0;while(++childsteps<100){StepResult c=mode_dispatch_step(GAME_MODE_FADE_WAIT,&child);if(c.kind==STEP_POP)break;if(c.kind!=STEP_CONTINUE)return 35;host_process_frame();}if(childsteps>=100)return 36;
   r=mode_step_game_over(s);printf("QA_EXIT {\"kind\":\"gameover\",\"id\":%u,\"steps\":%u,\"stepKind\":%u,\"result\":%d,\"phase\":%u}\n",variant,steps,r.kind,r.pop_result,s->game_over.phase);
   if(r.kind!=STEP_POP||r.pop_result!=-1)return 37;
  }
 }else return 5;return 0;
}
'''

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def decode(data):return art.strict_decode(data,True)[0]
def source_stream(rom,loadsite):return art.strict_decode(rom[snes_offset(asm_pointer(rom,loadsite),len(rom)):])[0]
def bgr565(data):
    return b''.join((((w&0x7fe0)<<1)|(w&31)).to_bytes(2,'little')for(w,)in struct.iter_unpack('<H',data))
def base_pixels(gfx,arr,pal):
    out=bytearray()
    for y in range(224):
        for x in range(256):
            word=struct.unpack_from('<H',arr,((y//8)*32+x//8)*2)[0];tile=word&1023
            xx=7-x%8 if word&0x4000 else x%8;yy=7-y%8 if word&0x8000 else y%8;at=tile*32
            if at+32>len(gfx):raise ValueError('Arrangement exceeds selected graphics')
            color=sum(((gfx[at+yy*2+(p%2)+(p//2)*16]>>(7-xx))&1)<<p for p in range(4))
            index=((word>>10)&7)*16+color if color else 0
            if index*2+2>len(pal):raise ValueError('Palette reference exceeds selected palette')
            out.extend(pal[index*2:index*2+2])
    return bytes(out)
def crop_frame(raw,row):
    width=row['width'];x=(width-256)//2;y=row['bgYOffset']
    if y<0 or y+224>row['height']:raise ValueError('Native crop outside frame')
    return b''.join(raw[((yy*width+x)*2):((yy*width+x+256)*2)]for yy in range(y,y+224))
def gameover_pal(raw):
    out=bytearray(raw.ljust(512,b'\0'));out[224:256]=out[:32];out[32:224]=b'\0'*192;out[64:96]=out[:32]
    return bytes(out)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native-source','build','runtime','assets','rom','scratch','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--redux',action='store_true');p.add_argument('--diagnostic',action='store_true')
    a=p.parse_args();a.scratch=a.scratch.resolve()
    if a.scratch.exists():raise ValueError('Fresh scratch required')
    a.scratch.mkdir(parents=True);helper.DRIVER=DRIVER;exe,provenance=helper.private_build(a)
    _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h');rom=a.rom.read_bytes()
    result=dict(toolSha256=digest(__file__),production=provenance,packSha256=digest(a.assets),romSha256=digest(a.rom),
                pinnedReduxCommit=art.PIN if a.redux else None,profile='Redux'if a.redux else'Original',runtimeExecuted=True,
                preparedCases=8,skippedCases=0,ownerWrites=False,fullVisualParityVerified=False,nativeRuns=[],checks=[],sourceParityChecks=[])
    def check(name,passed,**detail):result['checks'].append(dict(check=name,passed=bool(passed),**detail))
    def sourcecheck(name,left,right,metric='differingPixels',**detail):result['sourceParityChecks'].append(dict(check=name,passed=left==right,sourceSha256=art.h(left),nativeSha256=art.h(right),**{metric:sum(left[i:i+2]!=right[i:i+2]for i in range(0,min(len(left),len(right)),2))},**detail))
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    for kind in ('town','gameover'):
        folder=a.scratch/kind;folder.mkdir()
        if kind=='town':(folder/'source-label.raw').write_bytes(source_stream(rom,0x4d62f))
        cp=subprocess.run([str(exe),str(a.assets.resolve()),str(folder),kind],env=env,capture_output=True,timeout=150)
        (folder/'stdout.log').write_bytes(cp.stdout);(folder/'stderr.log').write_bytes(cp.stderr)
        rows=[dict(event=line.split(' ',1)[0],**json.loads(line.split(' ',1)[1]))for line in cp.stdout.decode(errors='replace').splitlines()if line.startswith(('QA_CAPTURE ','QA_EXIT '))]
        result['nativeRuns'].append(dict(kind=kind,exitCode=cp.returncode,rows=rows,stdoutSha256=digest(folder/'stdout.log'),stderrSha256=digest(folder/'stderr.log')))
        if cp.returncode or len(rows)!=(12 if kind=='town' else 4):raise RuntimeError('Incomplete production '+kind+': '+str(cp.returncode)+' '+cp.stderr.decode(errors='replace'))
        for row in rows:
            i=row['id']
            if row['event']=='QA_EXIT':
                check(kind+f'-{i}-exit',row['stepKind']==2 and (row['tm']==23 if kind=='town'else row['result']==-1),native=row);continue
            vram=(folder/f'{kind}-vram-{i}.raw').read_bytes();palette=(folder/f'{kind}-palette-{i}.raw').read_bytes();frame=crop_frame((folder/f'{kind}-bgframe-{i}.raw').read_bytes(),row)
            if kind=='town':
                key=('US/'if i in(2,4)else'')+f'town_maps/{i}.bin.lzhal';raw=decode(assets[key]);label=decode(assets['US/town_maps/label.gfx.lzhal'])
                ptr=int.from_bytes(rom[0x202190+i*4:0x202194+i*4],'little')
                source=art.strict_decode(rom[snes_offset(ptr,len(rom)):])[0]
                check(f'town-{i}-real-uploads',vram[:0x4000]==raw[0x840:0x4840]and vram[0x6000:0x6800]==raw[0x40:0x840]and palette[:64]==raw[:64]and vram[0xc000:0xc000+len(label)]==label,native=row)
                check(f'town-{i}-real-base-render',frame==bgr565(town_pixels(raw)),expectedSha256=art.h(bgr565(town_pixels(raw))),nativeSha256=art.h(frame),native=row)
                before=(folder/f'town-pre-vram-{i}.raw').read_bytes()
                check(f'town-{i}-bounded-uploads',all(vram[j]==before[j]for j in range(65536)if not(j<0x6000 or 0x6000<=j<0x6800 or 0xc000<=j<0xe400)))
                sourcecheck(f'town-{i}-compiled-base-art',bgr565(town_pixels(source)),frame,scope='BG1 only render diagnostic: dynamic OBJ icons excluded; original palette/VRAM state retained.')
                tile_bytes=int.from_bytes(rom[0x4d626:0x4d628],'little')
                sourcecheck(f'town-{i}-compiled-tile-upload',source[0x840:0x840+tile_bytes],vram[:tile_bytes],metric='differingVramWords',sourceUploadBytes=tile_bytes,scope='Exact source tile layout and zero tail through real native VRAM. Repacked tile numbering may differ without a visible image difference.')
                slabel=source_stream(rom,0x4d62f)
                sourcecheck(f'town-{i}-compiled-label-upload',slabel,vram[0xc000:0xc000+len(slabel)],metric='differingVramWords',sourceDecodedBytes=len(slabel),sourceUploadBytes=0x2400,scope='Decoded source label prefix through actual upload; Original undecoded tail is deliberately not treated as source bytes.')
                sourcecheck(f'town-{i}-compiled-label-render-control',(folder/f'town-source-label-frame-{i}.raw').read_bytes(),(folder/f'town-frame-{i}.raw').read_bytes(),scope='Same native OAM/palette/PPU capture, with only label VRAM privately replaced by actual source bytes, then restored. Prepared flags show ordinary labels plus hints. This diagnostic isolates label art contribution; not a converted runtime.')
            else:
                raw=decode(assets['E1CFAF.gfx.lzhal']);arr=decode(assets['E1D5E8.arr.lzhal']);pal=gameover_pal(decode(assets['E1D4F4.pal.lzhal']));gfx=raw[i*0x8000:(i+1)*0x8000]
                source=source_stream(rom,0x4c32f);sarr=source_stream(rom,0x4c388);spal=gameover_pal(source_stream(rom,0x4c3c3));sgfx=source[i*0x8000:(i+1)*0x8000]
                check(f'gameover-{i}-real-uploads',vram[:0x8000]==gfx and vram[0xb000:0xb800]==arr,native=row)
                expected=bgr565(base_pixels(gfx,arr,pal));actual=frame
                check(f'gameover-{i}-real-base-render',expected==actual,expectedSha256=art.h(expected),nativeSha256=art.h(actual),native=row)
                sourcecheck(f'gameover-{i}-compiled-base-art',bgr565(base_pixels(sgfx,sarr,spal)),actual,scope='BG1 art render, Ness and Jeff source-selected variants; comeback dialogue and modern postprocessing excluded.')
    files=['src/game/town_map.c','src/game/overworld_palette.c','src/snes/ppu_render.c','src/entity/callbacks.c','asm/overworld/load_town_map_data.asm','asm/misc/initialize_game_over_screen.asm']
    result['sourceIdentities']={x:digest(a.native_source/x)for x in files};result['executedAssertions']=len(result['checks'])+len(result['sourceParityChecks'])
    result['nativeExecutionPassed']=all(x['passed']for x in result['checks']);result['sourceParityPassed']=all(x['passed']for x in result['sourceParityChecks']);result['allPassed']=result['nativeExecutionPassed']and result['sourceParityPassed']
    result['limits']=['Prepared real Town Map menu load/render/reload exits for each map; the owning Goods/X-button caller and natural item acquisition are not tested here.',
        'Prepared GO_ENTER includes real music request/fade children/setup/fade-in for both source leader variants; staged post-dialogue Continue tail proves fade and pop only, not the comeback text or No-Continue progression.',
        'BG1 render diagnostic temporarily disables OBJ/text layer for the captured comparison, then restores native TM; all upload/setup operations are unchanged production consumers.',
        'Independent source decoding/base colors validate retained source art differences; this is not whole-screen visual parity or a complete playthrough.']
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({x:result[x]for x in ('nativeExecutionPassed','sourceParityPassed','allPassed','executedAssertions','preparedCases','skippedCases')}))
    raise SystemExit(0 if result['allPassed']or(a.diagnostic and result['nativeExecutionPassed']) else 1)
if __name__=='__main__':main()
