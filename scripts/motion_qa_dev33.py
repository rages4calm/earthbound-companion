# SPDX-License-Identifier: GPL-3.0-or-later
"""Isolated real-game replay host; prepared RAM fixture after copied cold restore. Copies checkpoints; never writes owner installs."""
import argparse, csv, hashlib, json, os, re, shutil, statistics, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def build(a):
    work=a.out/'host';work.mkdir(parents=True)
    source='#include "game/position_buffer.h"\n#include "core/math.h"\n'+(a.source/'port/unix/main.c').read_text()
    hook='\n        if (frame_num == 0 && getenv("EB_SHOWCASE_X")) {\n            bool fresh_stage=getenv("EB_SHOWCASE_FRESH")!=NULL;\n            if (!fresh_stage && (!load_state_at_boot || host_capture_status() != HOST_CAPTURE_COMMITTED)) {\n                fprintf(stderr,"SHOWCASE refused: baseline did not load\\n"); return 2;\n            }\n            unsigned sx=(unsigned)strtoul(getenv("EB_SHOWCASE_X"),NULL,10);\n            const char *syenv=getenv("EB_SHOWCASE_Y");\n            unsigned sy=syenv?(unsigned)strtoul(syenv,NULL,10):0;\n            if(sx>=8192 || sy>=10240) return 2;\n            memset(&g_mode_stack,0,sizeof(g_mode_stack));\n            ModeState stage_root={.overworld={.phase=OWP_RENDER}};\n            mode_push(GAME_MODE_OVERWORLD,&stage_root);\n            memset(&bt,0,sizeof(bt));\n            window_system_init(); init_used_bg2_tile_map();\n            text_setup_bg3(); text_upload_font_tiles(); text_load_window_gfx();\n            if(fresh_stage) {\n                // A fresh early-game sandbox, not a transplanted end-game save.\n                game_state.party_count=game_state.player_controlled_party_count=1;\n                game_state.current_party_members=1;\n                memset(game_state.party_members,0,sizeof(game_state.party_members));\n                memset(game_state.party_order,0,sizeof(game_state.party_order));\n                game_state.party_members[0]=game_state.party_order[0]=1;\n                game_state.text_flavour=1;\n                text_load_flavour_palette(0);\n                CharStruct *ch=&party_characters[0];memset(ch,0,sizeof(*ch));\n                uint8_t name[]={\'N\'+0x30,\'e\'+0x30,\'s\'+0x30,\'s\'+0x30};\n                maternalbound_set_character_name(0,name,4);\n                ch->level=8;\n                ch->max_hp=ch->current_hp=ch->current_hp_target=110;\n                ch->max_pp=ch->current_pp=ch->current_pp_target=32;\n                ch->offense=ch->base_offense=24;ch->defense=ch->base_defense=10;\n                ch->speed=ch->base_speed=12;ch->vitality=ch->base_vitality=8;\n                ch->iq=ch->base_iq=8;ch->luck=ch->base_luck=8;\n                game_state.money_carried=200;\n            }\n            game_state.leader_x_coord=(uint16_t)sx;\n            game_state.leader_y_coord=(uint16_t)sy;\n            game_state.walking_style=WALKING_STYLE_NORMAL;\n            game_state.leader_direction=0;\n            // Private stage only: restore encounters even when a copied checkpoint\n            // carried the global monster suppression flag. No shipping/save edits.\n            initialize_overworld_state();\n            event_flag_clear(EVENT_FLAG_MONSTER_OFF);\n            event_flag_clear(EVENT_FLAG_WIN_GIEGU);\n            ow.enemy_spawns_enabled=1;\n            set_leader_position_and_load_party((uint16_t)sx,(uint16_t)sy,0);\n            enable_character_movement(0xFF);\n            ow.enemy_spawns_enabled=1;\n            ow.overworld_status_suppression=0;\n            ow.player_movement_flags=0; ow.demo_frames_left=0;\n            fade_state.fading=false; ppu.inidisp=15;\n            for(unsigned c=0;c<4;c++) {\n                party_characters[c].current_hp=party_characters[c].current_hp_target=party_characters[c].max_hp;\n                party_characters[c].current_pp=party_characters[c].current_pp_target=party_characters[c].max_pp;\n                memset(party_characters[c].afflictions,0,sizeof(party_characters[c].afflictions));\n            }\n            fprintf(stderr,"SHOWCASE ready at %u,%u; manual controls; enemy spawns enabled\\n",sx,sy);\n        }\n        if(getenv("EB_SHOWCASE_DIAGNOSTIC") && (frame_num==60 || frame_num==180))\n            fprintf(stderr,"SHOWCASE probe frame=%d position=%u,%u modes=%u elapsed_ms=%u\\n",frame_num,\n                game_state.leader_x_coord,game_state.leader_y_coord,g_mode_stack.depth,SDL_GetTicks());\n'
    hook=hook.replace('frame_num == 0 && getenv("EB_SHOWCASE_X")','!probe_staged && host_capture_status() == HOST_CAPTURE_COMMITTED && getenv("EB_SHOWCASE_X")')
    hook=hook.replace('bool fresh_stage=getenv', 'probe_staged=true;\n            bool fresh_stage=getenv')
    hook=hook.replace('initialize_overworld_state();','if(getenv("EB_PROBE_SEED"))rng_seed((uint32_t)strtoul(getenv("EB_PROBE_SEED"),NULL,10));\n            initialize_overworld_state();')
    hook=hook.replace('fade_state.fading=false; ppu.inidisp=15;', '''fade_state.fading=false; ppu.inidisp=15;
            if (getenv("EB_PROBE_SANDWICH")) {
                game_state.party_status=3;
                for (unsigned ent=24;ent<=28;ent++) entities.var[3][ent]=5;
                schedule_overworld_task(battle_actions_overworld_task_fn(OW_TASK_CB_INIT_PARTY_ANIMS),
                    (uint16_t)atoi(getenv("EB_PROBE_SANDWICH")));
            }
            ow.redux_secondary_timer=143;
            if (getenv("EB_PROBE_WIDE")) { engine_fx_wide_fov=1; ow.zoom_mode=EB_ZOOM_OUT; }
''')
    # Hook is a one-time private RAM stage, after the real cold restore completes.
    anchor='    for (int frame_num = 0; !platform_input_quit_requested(); frame_num++) {'
    assert source.count(anchor)==1
    trace=r'''
        if (frame_num == 0) {
            motion_log=fopen("motion.csv","wb");
            fprintf(motion_log,"frame,ticks,frequency,x,xf,y,yf,camera_x,camera_y,camera_mode,modes,animation,offset_x,offset_y,sandwich,stamina\n");
            entity_log=fopen("entities.csv","wb");
            fprintf(entity_log,"frame,entity,npc,enemy,x,y,oam\n");
        }
        float offset_x=0,offset_y=0;
        MOTION_OFFSETS
        unsigned leader=ow.current_leading_party_member_entity;
        fprintf(motion_log,"%d,%llu,%llu,%u,%u,%u,%u,%u,%u,%u,%u,%d,%.6f,%.6f,%u,%u\n",frame_num,
            (unsigned long long)SDL_GetPerformanceCounter(),(unsigned long long)SDL_GetPerformanceFrequency(),game_state.leader_x_coord,game_state.leader_x_frac,
            game_state.leader_y_coord,game_state.leader_y_frac,ppu.bg_hofs[0],ppu.bg_vofs[0],game_state.camera_mode,
            g_mode_stack.depth,leader<MAX_ENTITIES?entities.animation_frame[leader]:-1,offset_x,offset_y,
            game_state.party_status,ow.redux_secondary_timer);
        ENTITY_OBSERVATIONS_BEGIN
        for (unsigned ent=0;ent<MAX_ENTITIES;ent++) {
            unsigned sprites=0;
            for (unsigned at=0;at<128;at++) if (presentation_oam_entity[at]==(int)ent) sprites++;
            if (sprites || entities.enemy_ids[ent]>=0)
                fprintf(entity_log,"%d,%u,%u,%d,%d,%d,%u\n",frame_num,ent,entities.npc_ids[ent],
                    entities.enemy_ids[ent],entities.screen_x[ent],entities.screen_y[ent],sprites);
        }
        ENTITY_OBSERVATIONS_END
        if (getenv("EB_PROBE_CAPTURES") && frame_num>=70 && frame_num<150) {
            char filename[100];snprintf(filename,sizeof(filename),"frame-%03d.bmp",frame_num);
            platform_video_request_screenshot(filename);
        }
'''
    trace=trace.replace('MOTION_OFFSETS','offset_x=platform_video_motion_offset(0);offset_y=platform_video_motion_offset(1);' if a.enhanced else '')
    trace=re.sub(r'ENTITY_OBSERVATIONS_BEGIN(.*?)ENTITY_OBSERVATIONS_END',lambda m:m[1] if a.enhanced else '',trace,flags=re.S)
    source=source.replace(anchor,anchor+hook+trace)
    source=source.replace(anchor,'    FILE *motion_log=NULL,*entity_log=NULL; bool probe_staged=false;\n'+anchor)
    if a.enhanced: source='extern float platform_video_motion_offset(int axis);\n'+source
    dest=work/'main.c';dest.write_text(source)
    commands=json.loads((a.build/'compile_commands.json').read_text())
    entry=next(row for row in commands if row['file'].endswith('/port/unix/main.c'))
    flags=entry['command'].split();obj=work/'main.obj'
    flags[flags.index('-o')+1]=str(obj);flags[flags.index('-c')+1]=str(dest)
    def run(cmd,name):
        p=subprocess.run(cmd,cwd=a.build,capture_output=True,timeout=180)
        (work/(name+'.log')).write_bytes(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[-2500:])
    run(flags,'compile')
    ninja=(a.build/'build.ninja').read_text()
    match=re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_Release (.*?)\n(.*?)(?=\n\n)',ninja,re.M|re.S)
    objects=[str(obj) if x.replace('\\','/').endswith('/main.c.obj') else str(a.build/x) for x in match[1].split(' | ',1)[0].split()]
    libs=re.search(r'^  LINK_LIBRARIES = (.*)$',match[2],re.M)[1].split()
    exe=work/'motion-host.exe';run([flags[0],'-O3','-DNDEBUG',*objects,'-o',str(exe),*libs],'link')
    shutil.copy2(a.sdl_dll or a.build/'SDL2.dll',work/'SDL2.dll')
    if (a.build/'librashader.dll').exists():shutil.copy2(a.build/'librashader.dll',work/'librashader.dll')
    return exe
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,default=ROOT/'native-source');p.add_argument('--build',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--sdl-dll',type=Path,help='Matching SDL2 DLL; defaults to SDL2.dll in the build directory.')
    p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--assets',type=Path,required=True)
    p.add_argument('--x',type=int,default=2024);p.add_argument('--y',type=int,default=1488)
    p.add_argument('--frames',type=int,default=240);p.add_argument('--enhanced',action='store_true')
    p.add_argument('--captures',action='store_true');p.add_argument('--headless',action='store_true')
    p.add_argument('--sprint',type=int,default=0);p.add_argument('--sandwich',type=int,default=0)
    p.add_argument('--wide',action='store_true');p.add_argument('--direction',type=int,default=2)
    p.add_argument('--host',type=Path)
    p.add_argument('--shader',type=Path)
    p.add_argument('--fresh',action='store_true');p.add_argument('--route',type=Path)
    p.add_argument('--filter',type=int,default=0);p.add_argument('--aspect',type=int,default=0)
    p.add_argument('--seed',type=int);p.add_argument('--no-stage',action='store_true')
    a=p.parse_args();a.build=a.build.resolve();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    exe=a.host.resolve() if a.host else build(a);session=a.out/'session';(session/'saves').mkdir(parents=True)
    shutil.copy2(a.checkpoint,session/'saves/quicksave_1.bin.0')
    (session/'settings.dat').write_bytes(b'EBST'+bytes([5,a.sprint,0,0,0,0,1 if a.filter==1 else 0,0,0,0,a.aspect,0]))
    (session/'earthbound.ini').write_text(f'companion=1\nwidth=1280\nheight=720\nfullscreen=0\ninteger_scale=0\nfilter={a.filter}\nvolume=0\nno_homesickness=1\nno_dad_calls=1\n')
    if a.shader:
      with (session/'earthbound.ini').open('a') as ini:ini.write('shader_preset='+str(a.shader.resolve())+'\n')
    directions=[0x800,0x900,0x100,0x500,0x400,0x600,0x200,0xA00]
    pad=directions[a.direction]|(0x4000 if a.sprint else 0)
    (session/'movement.txt').write_text(f'0 0\n80 {pad:x}\n140 0\n150 {0x400|(0x4000 if a.sprint else 0):x}\n210 0\n')
    if a.route:shutil.copy2(a.route,session/'movement.txt')
    env=dict(os.environ,EB_SHOWCASE_X=str(a.x),EB_SHOWCASE_Y=str(a.y),EB_SHOWCASE_DIAGNOSTIC='1',SDL_AUDIODRIVER='dummy')
    if a.captures:env['EB_PROBE_CAPTURES']='1'
    if a.sandwich:env['EB_PROBE_SANDWICH']=str(a.sandwich)
    if a.wide:env['EB_PROBE_WIDE']='1'
    if a.fresh:env['EB_SHOWCASE_FRESH']='1'
    if a.seed is not None:env['EB_PROBE_SEED']=str(a.seed)
    if a.no_stage:env.pop('EB_SHOWCASE_X',None)
    cmd=[str(exe),'--session-dir',str(session),'--assets',str(a.assets.resolve()),'--allow-redux-development','--config',str(session/'earthbound.ini'),'--windowed','--skip-intro','--load-state','--frames',str(a.frames),'--input-script',str(session/'movement.txt')]
    if a.headless:cmd+=['--headless']
    r=subprocess.run(cmd,env=env,cwd=session,capture_output=True,timeout=45)
    (session/'run.log').write_bytes(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError((r.stdout+r.stderr).decode(errors='replace')[-2000:])
    rows=list(csv.DictReader((session/'motion.csv').open()));frequency=int(rows[0]['frequency']);intervals=[(int(b['ticks'])-int(c['ticks']))*1000/frequency for c,b in zip(rows,rows[1:])][10:]
    moving=[(c,b) for c,b in zip(rows,rows[1:]) if 0<float(b['x'])-float(c['x'])<12 and c['modes']==b['modes']=='1']
    raw=[float(b['camera_x'])-float(c['camera_x']) for c,b in moving]
    smooth=[dx+float(b['offset_x'])-float(c['offset_x']) for (c,b),dx in zip(moving,raw)]
    errors=[]
    for c,b in zip(rows[8:],rows[9:]):
      if c['modes']!=b['modes'] or c['modes']!='1':continue
      for axis,frac,cam,off in [('x','xf','camera_x','offset_x'),('y','yf','camera_y','offset_y')]:
        delta=int(b[axis])-int(c[axis]);logic_delta=delta+(int(b[frac])-int(c[frac]))/65536
        if not (-12<delta<12):continue
        presented_delta=int(b[cam])-int(c[cam])+float(b[off])-float(c[off])
        errors.append(abs(logic_delta-presented_delta))
    report={'executableSha256':sha(exe),'productionExecutableSha256':sha(a.build/'earthbound.exe'),'checkpointSha256':sha(a.checkpoint),'assetsSha256':sha(a.assets),'frames':len(rows),'movingFrames':len(moving),'cameraSteps':sorted(set(raw)),'cameraStepStdDev':statistics.pstdev(raw) if raw else None,'presentedStepStdDev':statistics.pstdev(smooth) if smooth else None,'timingMs':{'median':statistics.median(intervals),'min':min(intervals),'max':max(intervals),'p95':sorted(intervals)[int(len(intervals)*.95)]},'preparedStage':None if a.no_stage else {'x':a.x,'y':a.y},'limits':[('Actual copied checkpoint; no prepared warp.' if a.no_stage else 'One prepared warp after real copied-checkpoint restore; not a natural quest route.')+' Timings measure host ticks, not monitor scanout.']}
    report.update(sprint=a.sprint,sandwichFrames=a.sandwich,direction=a.direction,maxMotionError=max(errors),sandwichStatuses=sorted({int(r['sandwich']) for r in rows[8:]}))
    (a.out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
if __name__=='__main__':main()
