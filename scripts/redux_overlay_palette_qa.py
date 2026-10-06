# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared real overlay rendering, map tint consumers and elevator EVENT583.

Links an unchanged frozen production library to a private caller. Owner saves,
packs and shared sources/builds are never changed. Expected palette arithmetic
is independently transcribed from the original assembly and pinned Redux hooks;
it is not a full audiovisual or story equivalence assertion.
"""
import argparse, array, hashlib, json, os, re, struct, subprocess
from pathlib import Path
import battle_action_catalog_qa as frozen
from build_maternalbound_pack import read_pack
from check_jev_observer_parity import local_scratch

DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "game/game_state.h"
#include "game/overworld.h"
#include "game/battle.h"
#include "game/audio.h"
#include "game/map_loader.h"
#include "game/maternalbound.h"
#include "game/window.h"
#include "game/display_text.h"
#include "game/display_text_internal.h"
#include "entity/entity.h"
#include "entity/sprite.h"
#include "core/state_dump.h"
#include "core/mode_stack.h"
#include "core/memory.h"
#include "data/assets.h"
#include "data/event_script_data.h"
#include "platform/platform.h"
#include "snes/ppu.h"
extern int eb_platform_main(int argc,char **argv);
extern void build_entity_draw_list(void);
static FILE *pixels;
static void line(int y,const pixel_t *p){if(pixels)fwrite(p,sizeof(pixel_t),EB_VIEWPORT_WIDTH,pixels);}
static void raw_frame(const char *name){pixels=fopen(name,"wb");ppu_render_frame(line);fclose(pixels);pixels=NULL;}
static void world(void){
    game_state.party_count=game_state.player_controlled_party_count=1;
    game_state.current_party_members=1;game_state.party_npc_1=game_state.party_npc_2=0;
    for(unsigned i=0;i<6;i++)game_state.party_members[i]=game_state.party_order[i]=i==0?1:0;
    memset(&party_characters[0],0,sizeof(party_characters[0]));
    party_characters[0].level=30;party_characters[0].max_hp=party_characters[0].current_hp=party_characters[0].current_hp_target=300;
    party_characters[0].max_pp=party_characters[0].current_pp=party_characters[0].current_pp_target=100;
    memset(event_flags,0,sizeof(event_flags));event_flag_set(11);
    game_state.leader_x_coord=7568;game_state.leader_y_coord=360;
    initialize_overworld_state();load_title_screen_script_data();
    bt.battle_mode_flag=ow.battle_mode=0;ppu.inidisp=15;
}
static void overlay_prepare(unsigned *v){
    entity_system_init();load_overlay_sprites();clear_overworld_spritemaps();
    memset(overworld_spritemaps,0,5);overworld_spritemaps[4]=0x80;
    unsigned e=v[1];entities.first_entity=e;entities.next_entity[e]=-1;
    entities.screen_x[e]=256;entities.screen_y[e]=130;
    entities.abs_x[e]=256;entities.abs_y[e]=130;
    entities.spritemap_ptr_lo[e]=0;entities.spritemap_ptr_hi[e]=v[7]?0x8000:0;
    entities.spritemap_sizes[e]=5;entities.animation_frame[e]=0;
    entities.draw_callback[e]=CB_DRAW_ENTITY_SPRITE;entities.draw_priority[e]=2;
    entities.surface_flags[e]=v[3];entities.byte_widths[e]=0x40;
    entities.overlay_flags[e]=v[5];entities.mushroomized_next_update[e]=v[4];
    const uint8_t *data=ASSET_DATA(ASSET_OVERWORLD_SPRITES_ENTITY_OVERLAY_DATA_BIN);
    entities.mushroomized_spritemaps[e]=(uint16_t)(data[181]|data[182]<<8)-0x0e31;
    entities.ripple_next_update[e]=255;entities.ripple_spritemaps[e]=(uint16_t)(data[193]|data[194]<<8)-0x0e31;
    game_state.trodden_tile_type=v[2];ppu.tm=0x10;ppu.ts=0;ppu.inidisp=15;ppu.obsel=0x62;
    ppu.cgadsub=0;ppu.cgwsel=0;ppu.window_hdma_active=ppu.window2_hdma_active=ppu.tm_hdma_active=false;
    ert.palette_upload_mode=PALETTE_UPLOAD_FULL;sync_palettes_to_cgram();
    memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_NONE;
}
static void overlay_draw(unsigned *v,const char *label){
    for(unsigned p=0;p<4;p++)sprite_priority[p].offset=0;
    ert.oam_write_index=0;build_entity_draw_list();
    printf("QA_OVERLAY {\"id\":%u,\"label\":\"%s\",\"delay\":%u,\"script\":%u,\"map\":%u,\"queue\":[",v[0],label,
        entities.mushroomized_next_update[v[1]],entities.mushroomized_overlay_ptrs[v[1]],entities.mushroomized_spritemaps[v[1]]);
    unsigned n=0;
    for(unsigned p=0;p<4;p++)for(unsigned i=0;i<sprite_priority[p].offset;i++){
        SpritePriorityQueue *q=&sprite_priority[p];printf("%s[%u,%u,%d,%d,%u]",n++?",":"",p,q->spritemaps[i],q->sprite_x[i],q->sprite_y[i],q->spritemap_banks[i]);}
    render_all_priority_sprites();printf("],\"oam\":[");
    for(unsigned i=0;i<ert.oam_write_index;i++)printf("%s[%d,%d,%u,%u]",i?",":"",ppu.oam_full_x[i],ppu.oam_full_y[i],ppu.oam[i].tile,ppu.oam[i].attr);
    printf("]}\n");char name[128];snprintf(name,sizeof(name),"overlay-%u-%s.bin",v[0],label);raw_frame(name);
}
int main(int argc,char **argv){
    if(argc!=6)return 2;
    unsigned original=atoi(argv[3]),kind=atoi(argv[4]);
    char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
    char *boot[]={"overlay-palette-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,
        "--allow-redux-development","--headless","--frames","1",original?"--inspect-shuffle":"--redux-battle-fixture","0"};
    if(eb_platform_main(sizeof(boot)/sizeof(boot[0])-(original?1:0),boot)!=0 || maternalbound_enabled()==original)return 3;
    platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 4;
    game_set_fast_forward(true);audio_init();world();
    if(kind==0 || kind==3 || kind==4){
        FILE *input=fopen(argv[5],"r");if(!input)return 5;unsigned v[8];
        while(fscanf(input,"%u %u %u %u %u %u %u %u",v,v+1,v+2,v+3,v+4,v+5,v+6,v+7)==8){
            if(kind==4){if(!state_dump_load_slots())return 9;}
            else overlay_prepare(v);
            if(kind==3 && !state_dump_save_slots())return 8;
            overlay_draw(v,"actual");
            if(kind==0){unsigned delay=entities.mushroomized_next_update[v[1]],ptr=entities.mushroomized_overlay_ptrs[v[1]],map=entities.mushroomized_spritemaps[v[1]];
                overlay_prepare(v);entities.overlay_flags[v[1]]=0;overlay_draw(v,"control");
                (void)delay;(void)ptr;(void)map;}
        }fclose(input);
    }else if(kind==1){
        FILE *input=fopen(argv[5],"r");if(!input)return 5;unsigned id,x,y;
        while(fscanf(input,"%u %u %u",&id,&x,&y)==3){
            game_state.current_party_members=1;memset(event_flags,0,sizeof(event_flags));event_flag_set(11);
            ow.current_teleport_destination_x=ow.current_teleport_destination_y=0;
            load_map_at_sector((uint16_t)x,(uint16_t)y);
            char name[128];snprintf(name,sizeof(name),"palette-%u.bin",id);FILE *out=fopen(name,"wb");fwrite(ert.palettes,2,256,out);fclose(out);
            printf("QA_PALETTE {\"id\":%u,\"reference\":[%u,%u,%u],\"loadedPalette\":%u,\"loadedCombo\":%u,\"upload\":%u}\n",id,
                ml.saved_colour_average_red,ml.saved_colour_average_green,ml.saved_colour_average_blue,ml.loaded_palette_index,ml.loaded_tileset_combo,ert.palette_upload_mode);
        }fclose(input);
    }else if(kind==2){
        memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_NONE;
        FILE *input=fopen(argv[5],"r");unsigned offset=0;
        if(!input || fscanf(input,"%u",&offset)!=1)return 10;
        fclose(input);
        ScriptReader reader={TEXT_SRC_DIALOGUE,offset,offset+6,-1};
        ModeState child={0};GameMode mode=GAME_MODE_NONE;uint8_t resume=0;uint16_t aux=0;
        if(cc_1f_dispatch(&reader,&child,&mode,&resume,&aux))return 11;
        int actor=find_entity_by_sprite_id(106);
        if(actor<0 || entities.script_table[actor]!=583 || reader.ptr_off-offset!=6)return 12;
        int leader=ow.current_leading_party_member_entity;int startx=entities.abs_x[leader],starty=entities.abs_y[leader];
        ert.actionscript_state=0;ModeState wait={0};mode_push(GAME_MODE_ACTIONSCRIPT_WAIT,&wait);
        unsigned steps=0,host=0,oldmode=255,oldr=255,oldg=255,oldb=255,maxspeed=0;
        int miny=32767,maxy=-32768;
        while(g_mode_stack.depth>1 && ++steps<2000){
            unsigned top=g_mode_stack.depth-1;StepResult r=mode_dispatch_step((GameMode)g_mode_stack.mode[top],&g_mode_stack.state[top]);
            if(r.kind==STEP_PUSH)mode_push(r.push_mode,r.push_init);
            else if(r.kind==STEP_POP)mode_pop(r.pop_result);
            else{host_process_frame();host++;}
            if(entities.script_table[actor]>=0){
                if(entities.abs_y[actor]<miny)miny=entities.abs_y[actor];
                if(entities.abs_y[actor]>maxy)maxy=entities.abs_y[actor];
                if(entities.movement_speeds[actor]>maxspeed)maxspeed=entities.movement_speeds[actor];
            }
            if(ppu.cgadsub!=oldmode || ppu.coldata_r!=oldr || ppu.coldata_g!=oldg || ppu.coldata_b!=oldb){
                printf("QA_ELEVATOR_STAGE {\"step\":%u,\"host\":%u,\"mode\":%u,\"color\":[%u,%u,%u],\"position\":[%d,%d],\"script\":%d,\"speed\":%d}\n",steps,host,
                    ppu.cgadsub,ppu.coldata_r,ppu.coldata_g,ppu.coldata_b,entities.abs_x[actor],entities.abs_y[actor],entities.script_table[actor],entities.movement_speeds[actor]);
                oldmode=ppu.cgadsub;oldr=ppu.coldata_r;oldg=ppu.coldata_g;oldb=ppu.coldata_b;
            }
        }
        printf("QA_ELEVATOR {\"depth\":%u,\"steps\":%u,\"host\":%u,\"mode\":%u,\"color\":[%u,%u,%u],\"windowHdma\":%u,\"script\":%d,\"speed\":%d,\"maximumSpeed\":%u,\"actorYRange\":[%d,%d],\"leaderPreserved\":%u,\"ccConsumed\":%u}\n",
            g_mode_stack.depth,steps,host,ppu.cgadsub,ppu.coldata_r,ppu.coldata_g,ppu.coldata_b,ppu.window_hdma_active,entities.script_table[actor],entities.movement_speeds[actor],maxspeed,miny,maxy,
            entities.abs_x[leader]==startx && entities.abs_y[leader]==starty,reader.ptr_off-offset);
    }else return 6;
    audio_shutdown();return 0;
}
'''

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def average(colors):
    active=[c for c in colors if c&0x7fff]
    return [sum((c>>shift)&31 for c in active)*8//len(active) if active else 0 for shift in (0,5,10)]
def tint(colors,bg,reference,threshold):
    avg=average(bg)
    if not all(reference):return colors[:],avg,None
    ratios=[a*256//r for a,r in zip(avg,reference)]
    if any(r>256 for r in ratios):return colors[:],avg,ratios
    combined=sum(ratios)//3;out=[]
    for c in colors:
        channels=[c&31,(c>>5)&31,(c>>10)&31]
        weights=[combined]*3 if channels[0]==channels[1]==channels[2] else ratios
        transformed=[]
        for old,weight in zip(channels,weights):
            target=((old*weight)>>8)&31
            transformed.append(min(old+threshold,max(old-threshold,target)))
        out.append(sum(c<<s for c,s in zip(transformed,(0,5,10))))
    return out,avg,ratios
def box_difference(actual,control):
    diffs=[i for i,(a,b) in enumerate(zip(actual,control)) if a!=b]
    return [min(i%512 for i in diffs),min(i//512 for i in diffs),max(i%512 for i in diffs),max(i//512 for i in diffs)] if diffs else None,len(diffs)
def pixels(path):
    data=array.array('H');data.frombytes(path.read_bytes());return data

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('build','native-source','runtime','assets','original-assets','scratch','project','frozen-source','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--supplement-source',type=Path)
    p.add_argument('--diagnostic',action='store_true')
    a=p.parse_args();a.scratch=local_scratch(a.scratch)
    if a.scratch.exists():raise ValueError('Fresh private scratch required.')
    a.scratch.mkdir(parents=True)
    pin=subprocess.check_output(['git','-C',str(a.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=frozen.PIN:raise ValueError('Unexpected Redux pin')
    frozen.DRIVER=DRIVER;exe,build=frozen.private_build(a)
    cases=[];checks=[];failures=[];private_rows=[];assertions=0
    def check(name,condition,detail):
        nonlocal assertions
        assertions+=1
        if not condition:failures.append({'check':name,'detail':detail})
        return bool(condition)
    def run(profile,pak,kind,folder,fixture):
        folder.mkdir();inputs=folder/'cases.tsv';inputs.write_text(fixture,encoding='utf-8')
        r=subprocess.run([str(exe),str(pak.resolve()),str(folder.resolve()),str(int(profile=='Original')),str(kind),str(inputs.resolve())],cwd=folder,
            env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=180)
        (folder/'native.stdout.log').write_bytes(r.stdout);(folder/'native.stderr.log').write_bytes(r.stderr)
        warnings=[s for s in r.stderr.decode(errors='replace').splitlines() if re.search(r'\b(?:WARN|ERROR|FATAL|STALL|HANG)\b',s)]
        check(profile+' process '+folder.name,r.returncode==0 and not warnings,{'exit':r.returncode,'warnings':warnings})
        def rows(prefix):return [json.loads(s[len(prefix):]) for s in r.stdout.decode(errors='replace').splitlines() if s.startswith(prefix)]
        return rows
    for profile,pak in (('Original',a.original_assets),('Redux',a.assets)):
        assets=read_pack(pak,a.native_source/'src/data/runtime_generated/asset_ids.h')[2]
        overlay=assets['overworld_sprites/entity_overlay_data.bin']
        mushroom_frame=int.from_bytes(overlay[181:183],'little')-0x0e31
        tests=[]
        for slot in (23,24,25,26):
            for tile in (0,4,8,12):
                for surface in (0,1,8,9,12,13):
                    for delay in (0,1,255):tests.append([len(tests),slot,tile,surface,delay,1,0,0])
        for slot,flag,hidden in ((22,1,0),(0,1,0),(23,0,0),(23,1,1)):
            tests.append([len(tests),slot,8,0,0,flag,0,hidden])
        folder=a.scratch/(profile.lower()+'-overlay')
        rows=run(profile,pak,0,folder,'\n'.join(' '.join(map(str,t)) for t in tests)+'\n')('QA_OVERLAY ')
        lookup={(r['id'],r['label']):r for r in rows}
        dry_ids={(slot,surface,delay):id for id,slot,tile,surface,delay,flag,unused,hidden in tests if tile==0 and flag==1 and not hidden}
        for values in tests:
            id,slot,tile,surface,delay,flag,unused,hidden=values
            actual=lookup.get((id,'actual'),{});control=lookup.get((id,'control'),{})
            active=bool(slot>=23 and flag&1 and not hidden)
            expected_y=130+(8 if tile&12==8 else 16 if tile&12==12 else 0) if profile=='Redux' else 130
            expected_smap=mushroom_frame+(5 if surface&1 else 0)
            mushroom=[q for q in actual.get('queue',[]) if q[4]==2 and q[1]==expected_smap]
            errors=[]
            def ck(name,cond,detail):
                if not check(f'{profile} overlay{id} '+name,cond,detail):errors.append(name)
            ck('queue count',len(mushroom)==int(active),{'actual':mushroom,'expectedActive':active})
            if active:
                ck('source global-water offset',mushroom==[[2,expected_smap,256,expected_y,2]],mushroom)
                ck('animation countdown',actual.get('delay')==(254 if delay==0 else delay-1),actual)
                ck('script pointer',actual.get('script')==(187 if delay==0 else 179),actual)
                expected_oam=[248,expected_y-25,overlay[expected_smap+1],overlay[expected_smap+2]]
                ck('actual OAM entry',expected_oam in actual.get('oam',[]),{'expected':expected_oam,'oam':actual.get('oam')})
            pa=pixels(folder/f'overlay-{id}-actual.bin');pc=pixels(folder/f'overlay-{id}-control.bin')
            box,count=box_difference(pa,pc)
            ck('visible mushroom pixels',bool(count)==active,{'bbox':box,'changedPixels':count})
            if active:
                dry_id=dry_ids[slot,surface,delay]
                dry_actual=pixels(folder/f'overlay-{dry_id}-actual.bin');dry_control=pixels(folder/f'overlay-{dry_id}-control.bin')
                dry_delta={(i//512+(expected_y-130),i%512):a for i,(a,b) in enumerate(zip(dry_actual,dry_control)) if a!=b}
                current_delta={(i//512,i%512):a for i,(a,b) in enumerate(zip(pa,pc)) if a!=b}
                ck('source-expected raster translation',current_delta==dry_delta,{'translationY':expected_y-130,'referenceCase':dry_id,'actualChangedPixels':len(current_delta),'expectedChangedPixels':len(dry_delta)})
            cases.append({'profile':profile,'kind':'overlay-draw','slot':slot,'globalTerrain':tile,'entitySurface':surface,'initialDelay':delay,'active':active,'expectedY':expected_y if active else None,'bbox':box,'changedPixels':count,'passed':not errors,'errors':errors})
        # Same captured entity/overlay state is drawn after an actual cold process restore.
        for tile in (0,8,12):
            capture=a.scratch/(profile.lower()+f'-cold-{tile}-capture')
            fixture=f'0 23 {tile} 1 0 1 0 0\n'
            warm=run(profile,pak,3,capture,fixture)('QA_OVERLAY ')[0]
            import shutil
            cold=a.scratch/(profile.lower()+f'-cold-{tile}-resume');cold.mkdir()
            shutil.copytree(capture/'saves',cold/'saves')
            # run() normally creates the new directory; use a separate runner with copied save slots.
            inputs=cold/'cases.tsv';inputs.write_text(fixture)
            r=subprocess.run([str(exe),str(pak.resolve()),str(cold.resolve()),str(int(profile=='Original')),'4',str(inputs.resolve())],cwd=cold,
                env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=180)
            (cold/'native.log').write_bytes(r.stdout+r.stderr)
            restored=[json.loads(s[len('QA_OVERLAY '):]) for s in r.stdout.decode(errors='replace').splitlines() if s.startswith('QA_OVERLAY ')]
            passed=check(profile+f' overlay cold{tile}',r.returncode==0 and restored==[warm] and (capture/'overlay-0-actual.bin').read_bytes()==(cold/'overlay-0-actual.bin').read_bytes(),{'exit':r.returncode,'rowsEqual':restored==[warm]})
            cases.append({'profile':profile,'kind':'cold-overlay-restore','globalTerrain':tile,'passed':passed,'frameSha256':sha(cold/'overlay-0-actual.bin')})
        # Inventory all actual map sector configurations; run one representative per combo/index.
        sector_data=assets['data/global_map_tilesetpalette_data.bin'];configurations={}
        for index,value in enumerate(sector_data):configurations.setdefault((value>>3,value&7),index)
        palette_tests=[(i,index%32,index//32,combo,palette) for i,((combo,palette),index) in enumerate(sorted(configurations.items()))]
        folder=a.scratch/(profile.lower()+'-palette')
        records=run(profile,pak,1,folder,'\n'.join(f'{i} {x} {y}' for i,x,y,c,p in palette_tests)+'\n')('QA_PALETTE ')
        lookup={r['id']:r for r in records}
        raw_sprite=list(struct.unpack('<128H',b''.join(assets[f'overworld_sprites/palettes/{i}.pal'] for i in range(8))))
        reference=[0x8a,0x96,0x74] if profile=='Redux' else average(struct.unpack('<96H',assets['US/maps/palettes/1.pal'][:192]))
        for id,x,y,combo,palette in palette_tests:
            row=lookup.get(id,{});colors=list(struct.unpack('<256H',(folder/f'palette-{id}.bin').read_bytes()))
            adjusted,avg,ratios=tint(raw_sprite,colors[32:128],reference,4 if profile=='Redux' else 6)
            special=colors[64]
            if special:
                check(f'{profile} palette{id} special index',special<16,{'index':special})
                # LOAD_SPECIAL_SPRITE_PALETTE reads the already-adjusted palette image.
                full=colors[:128]+adjusted
                adjusted[64:80]=full[special*16:special*16+16]
            errors=[i for i,(a,b) in enumerate(zip(colors[128:256],adjusted)) if a!=b]
            passed=check(f'{profile} palette{id} production tint',not errors and row.get('reference')==reference and row.get('loadedPalette')==palette and row.get('loadedCombo')==combo,{'mismatchingIndices':errors,'row':row,'reference':reference})
            cases.append({'profile':profile,'kind':'map-tint-consumer','sector':[x,y],'combo':combo,'palette':palette,'reference':reference,'actualAverage':avg,'ratios':ratios,'grayscaleInputColors':sum((c&31)==((c>>5)&31)==((c>>10)&31) for c in raw_sprite),'specialPaletteIndex':special,'sourceExpectedColorComparisons':128,'passed':passed,'mismatchingColorIndices':errors})
            private_rows.append({'profile':profile,'id':id,'reference':reference,'bg':colors[32:128],'initial':raw_sprite,'native':colors[128:256],'specialIndex':special})
        folder=a.scratch/(profile.lower()+'-elevator')
        dialogue=assets['dialogue/dialogue.bin']
        spawn=dialogue.find(bytes((31,21,106,0,71,2,1)))
        if spawn<0:raise ValueError('Existing source-backed elevator spawn command missing')
        parse=run(profile,pak,2,folder,str(spawn+1)+'\n')
        stages=parse('QA_ELEVATOR_STAGE ');final=parse('QA_ELEVATOR ')
        expected_color=[31]*3 if profile=='Redux' else [24]*3
        subtraction=next((s for s in stages if s['mode']==0xb3),{})
        tail=final[0] if final else {}
        passed=check(profile+' full EVENT583',subtraction.get('color')==expected_color and tail.get('depth')==1 and tail.get('mode')==0x33 and tail.get('color')==[0,0,0] and tail.get('windowHdma')==0 and tail.get('speed')==0 and tail.get('script')==-1 and tail.get('maximumSpeed')==384 and tail.get('leaderPreserved')==1 and tail.get('ccConsumed')==6 and tail.get('actorYRange',[0,0])[0]<tail.get('actorYRange',[0,0])[1],{'stages':stages,'final':tail})
        cases.append({'profile':profile,'kind':'elevator-script583','passed':passed,'stages':stages,'final':tail,'scope':'Actual script begins at root; source-yield ends ACTIONSCRIPT_WAIT. Not the surrounding hotel/elevator dialogue transaction.'})
    (a.scratch/'palette-machine-cases.json').write_text(json.dumps(private_rows)+'\n')
    source_names=('src/entity/callbacks.c','src/entity/callroutine_movement.c','src/entity/script.c','src/game/map_loader.c','src/game/overworld_palette.c','src/snes/ppu_render.c')
    source_inputs={name:(a.frozen_source/name if (a.frozen_source/name).exists() else a.supplement_source/name) for name in source_names}
    identities={name:sha(path) for name,path in source_inputs.items()}
    for name,h in identities.items():check('frozen source '+name,sha(a.native_source/name)==h,{'frozenSha256':h})
    report={'format':'redux-overlay-palette-behavior-qa-v1','Passed':not failures,'allPassed':not failures,'executedCases':len(cases),'executedAssertions':assertions,'skippedCases':0,'failures':failures,'cases':cases,'privateBuild':build,'runtimeSha256':{n:sha(a.runtime/n) for n in ('player.exe','observer.exe')},'packSha256':{'Original':sha(a.original_assets),'Redux':sha(a.assets)},'sourceSha256':identities,'supplementSourceEvidenceSha256':sha(a.supplement_source/'source-identities.json') if a.supplement_source else None,'pinnedReduxRevision':pin,'toolSha256':sha(Path(__file__)),'ownerSavesTouched':False,'sharedBuildModified':False,'sourceReferences':['asm/overworld/entity/draw_entity_overlays.asm','asm/overworld/execute_overlay_animation_script.asm','ccscript/bugfixes/mushroom_pos_fix.ccs C0AD3F','asm/system/get_colour_average.asm','asm/overworld/adjust_sprite_palettes_by_average.asm','asm/overworld/adjust_single_colour.asm','ccscript/bugfixes/palette_tint_fix.ccs C005E7/C00453/C0045D/C0046D/C00477/C34E0C','asm/data/events/scripts/583.asm'], 'limits':['Prepared overlay actors exercise actual draw callback, queues, OAM and rasterization with source-backed graphics. Main sprite uses an inert prepared entry to isolate overlay pixels; no walking/combat status timeline claimed.','Cold overlay checkpoints are private prepared fixtures captured/restored by actual save-slots APIs in different processes.','One map sector per unique combo/palette is executed with source flag11 set and all other event flags clear; alternative map-palette event overrides and every sector are not claimed.','Tint expected values derive independently from original assembly, not an executed SNES machine oracle in this report. Private captured palette cases permit a separate machine comparison.','Full EVENT583 color-math/motion script executes to its text yield; surrounding elevator dialogue/progression and pixel-equivalent full cinematic remain outside scope.','No ROM, asset, bytecode, PCM, save or raw palette content is distributed in the report. Observer hash is paired provenance; private driver executes player objects.']}
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('Passed','executedCases','executedAssertions','skippedCases')}));print(json.dumps(failures[:12]))
    if failures and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
