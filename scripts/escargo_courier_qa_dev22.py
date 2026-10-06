# SPDX-License-Identifier: GPL-3.0-or-later
"""Qualify real phone lookup, courier pathfinding, transaction and departure.

Uses a fresh source-derived world fixture and an unchanged production library.
No courier is manually created, teleported, advanced to an exit label, or given
an artificial completion signal. Pilot reports retain unsuccessful prerequisites.
"""
import json
import sys
from pathlib import Path

import barter_delivery_qa_dev20 as barter

base = barter.base
old_source = barter.driver_source

C_WORLD = r'''
static unsigned phone_npc,phone_done,visit_seen,courier_done,world_x,world_y,world_direction,walk_stage,exit_x,exit_y,destination_x,destination_y,last_walk_key,door_seen,interaction_type;
static void replay_idle(void){
 FILE*f=fopen(replay_path,"w");if(!f)exit(30);
 for(unsigned i=0;i<100000;i++)fprintf(f,"%u 0000\n",i);fclose(f);
 pc_input_script_path=replay_path;platform_input_shutdown();if(!platform_input_init())exit(31);
 core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=0;
}
static void replay_hold(unsigned key){
 FILE*f=fopen(replay_path,"w");if(!f)exit(30);
 for(unsigned i=0;i<100000;i++)fprintf(f,"%u %04x\n",i,key);fclose(f);
 pc_input_script_path=replay_path;platform_input_shutdown();if(!platform_input_init())exit(31);
 core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=0;last_walk_key=key;
}
static void courier_fixture(const char*session){
 char path[4096];snprintf(path,sizeof(path),"%s/courier-input.txt",session);
 FILE*f=fopen(path,"r");if(!f||fscanf(f,"%u %u %u %u %u %u %u %u %u",&phone_npc,&world_x,&world_y,&world_direction,&exit_x,&exit_y,&destination_x,&destination_y,&interaction_type)!=9)exit(32);fclose(f);
 game_state.leader_x_coord=(uint16_t)world_x;game_state.leader_y_coord=(uint16_t)world_y;
 game_state.leader_direction=(uint8_t)world_direction;game_state.walking_style=0;
}
static void courier_snap(const char*stage){
 int16_t slot=find_entity_by_npc_id(1311);int16_t scr=slot>=0?entities.script_index[slot]:-1;
 printf("QA_COURIER {\"stage\":\"%s\",\"phoneDone\":%u,\"visitSeen\":%u,\"courierDone\":%u,\"leader\":[%u,%u,%u],\"phoneNpc\":%u,\"phoneEntity\":%d,\"courierEntity\":%d,\"courierScript\":%d,\"courierPosition\":[%d,%d],\"scriptPc\":%u,\"scriptBank\":%u,\"pathCount\":%d,\"deliveryTimer\":%d,\"deliveryAttempts\":%d,\"actionscriptState\":%u,\"pending\":%u,\"suppression\":%u,\"windowOpen\":%u,\"brightness\":%u,\"fadeActive\":%u,\"mode\":%u,\"depth\":%u}\n",
 stage,phone_done,visit_seen,courier_done,game_state.leader_x_coord,game_state.leader_y_coord,game_state.current_party_members,
 phone_npc,find_entity_by_npc_id(phone_npc),slot,scr,slot>=0?entities.abs_x[slot]:0,slot>=0?entities.abs_y[slot]:0,
 scr>=0?scripts.pc[scr]:0,scr>=0?scripts.pc_bank[scr]:0,slot>=0?ert.entity_path_point_counts[slot]:0,
 ow.delivery_timers[1],ow.delivery_attempts[1],ert.actionscript_state,ow.pending_interactions,ow.overworld_status_suppression,
 any_window_open(),ppu.inidisp,fade_active(),g_mode_stack.mode[g_mode_stack.depth-1],g_mode_stack.depth);fflush(stdout);
}
static void courier_capture(void){
 host_request_capture();host_root_boundary();if(host_capture_status()!=HOST_CAPTURE_COMMITTED)exit(12);
 FILE*f=fopen(continuation_path,"w");if(!f)exit(13);
 fprintf(f,"%u %u %u %u %u %u %u",plan_pos,phone_done,visit_seen,courier_done,walk_stage,last_walk_key,door_seen);fclose(f);
 captured=1;snap("captured");courier_snap("captured");
}
'''


def replace_once(s, old, new):
    if s.count(old) != 1:
        raise ValueError('Frozen driver boundary changed: ' + old[:100])
    return s.replace(old, new, 1)


def driver_source(original):
    s = old_source(original)
    s = replace_once(s, '#include "game/audio.h"',
                     '#include "game/audio.h"\n#include "game/map_loader.h"\n#include "game/fade.h"\n#include "snes/ppu.h"')
    s = replace_once(s, 'static void snap(const char*stage){',
                     'static void snap(const char*stage);\n' + C_WORLD + '\nstatic void snap(const char*stage){')
    s = replace_once(s, 'update_party();initialize_overworld_state();',
                     'transaction_fixture(argv[2]);courier_fixture(argv[2]);update_party();initialize_overworld_state();')
    s = replace_once(s, 'text_load_flavour_palette(0);create_window(WINDOW_TEXT_STANDARD);',
                     'text_load_flavour_palette(0);fade_in(1,1);')
    s = replace_once(s, 'g_mode_stack.mode[0]=GAME_MODE_NONE;transaction_fixture(argv[2]);replay(0,0,0);snap("before-entry");',
                     'g_mode_stack.mode[0]=GAME_MODE_OVERWORLD;g_mode_stack.state[0].overworld.phase=OWP_RENDER;replay(0,0,0);snap("before-entry");courier_snap("before-phone");')
    s = replace_once(s, 'ModeState text={0};if(!dt_make_child_init(&text,entry))return 8;mode_push(GAME_MODE_DISPLAY_TEXT,&text);',
                     'ModeState caller={0};caller.quick_checktalk.phase=QCT_TEXT;mode_push(GAME_MODE_QUICK_CHECKTALK,&caller);')
    s = replace_once(s, 'while(g_mode_stack.depth>1 && ++steps<50000){',
                     'while(!courier_done && ++steps<50000){')
    s = replace_once(s, 'if(capture_kind && ((', 'if(capture_kind &&capture_kind<=4&& ((')
    s = replace_once(s, 'if(!f||fscanf(f,"%u",&plan_pos)!=1)return 15;',
                     'if(!f||fscanf(f,"%u %u %u %u %u %u %u",&plan_pos,&phone_done,&visit_seen,&courier_done,&walk_stage,&last_walk_key,&door_seen)!=7)return 15;')
    s = replace_once(s, 'unsigned top=g_mode_stack.depth-1,mode=g_mode_stack.mode[top];ModeState*st=&g_mode_stack.state[top];', r'''
  unsigned top=g_mode_stack.depth-1,mode=g_mode_stack.mode[top];ModeState*st=&g_mode_stack.state[top];
  if(g_mode_stack.depth==1&&!phone_done){phone_done=1;replay_idle();snap("after-phone");courier_snap("after-phone");walk_stage=exit_x?1:0;}
  if(capture_kind==9&&phone_done&&g_mode_stack.depth==1){courier_capture();break;}
  if(phone_done&&walk_stage&&g_mode_stack.depth==1){
   if(game_state.leader_x_coord==destination_x&&game_state.leader_y_coord==destination_y){walk_stage=0;replay_idle();courier_snap("after-source-door");}
   else{
    unsigned key;
    if(walk_stage==1&&game_state.leader_x_coord+2<exit_x)key=PAD_RIGHT;
    else {walk_stage=2;key=game_state.leader_y_coord>exit_y?PAD_UP:PAD_DOWN;}
    if(key!=last_walk_key)replay_hold(key);
   }
  }
  for(unsigned scan=1;scan<g_mode_stack.depth;scan++){
   if(g_mode_stack.mode[scan]==GAME_MODE_DOOR_TRANSITION&&!door_seen){door_seen=1;walk_stage=0;replay_idle();courier_snap("source-door-entered");}
   if(g_mode_stack.mode[scan]==GAME_MODE_PROCESS_INTERACTION&&g_mode_stack.state[scan].process_interaction.phase==PI_RESUME&&g_mode_stack.state[scan].process_interaction.type==interaction_type&&!visit_seen){
    visit_seen=1;walk_stage=0;replay(0,0,0);snap("before-visit");courier_snap("before-visit");
   }
  }
  if(visit_seen&&((capture_kind==6&&mode==GAME_MODE_SELECTION_MENU&&st->selection_menu.phase==SM_SETUP&&win.current_focus_window==1)||
     (capture_kind==7&&mode==GAME_MODE_SELECTION_MENU&&st->selection_menu.phase==SM_SETUP&&win.current_focus_window==2)||
     (capture_kind==8&&mode==GAME_MODE_ACTIONSCRIPT_WAIT))){courier_capture();break;}
  if(visit_seen&&g_mode_stack.depth==1&&!ow.pending_interactions&&!event_flag_get(181)&&!event_flag_get(645)){
   courier_done=1;replay_idle();courier_snap("completed");break;
  }
  if(steps%1000==0)courier_snap("progress");
''')
    s = replace_once(s, 'return captured||g_mode_stack.depth==1?0:9;',
                     'courier_snap("final");return captured||courier_done?0:9;')
    return s


def main():
    output = Path(sys.argv[sys.argv.index('--output') + 1])
    cases_path = Path(sys.argv[sys.argv.index('--cases') + 1])
    cases = json.loads(cases_path.read_text())
    by_id = {c['id']: c for c in cases}
    real_run = base.subprocess.run

    def run(command, *args, **kwargs):
        if isinstance(command, list) and len(command) == 5 and command[-1] in ('warm', 'capture', 'resume'):
            session = Path(command[2])
            world = by_id[session.name]['worldFixture']
            (session / 'courier-input.txt').write_text(' '.join(map(str, (
                world['phoneNpc'], world['leaderX'], world['leaderY'], world['direction'],
                world.get('exitX', 0), world.get('exitY', 0), world.get('destinationX', 0),
                world.get('destinationY', 0),world.get('expectedInteractionType',8)))), encoding='utf-8')
        return real_run(command, *args, **kwargs)

    base.subprocess.run = run
    barter.driver_source = driver_source
    failed = False
    try:
        barter.main()
    except SystemExit as e:
        if e.code not in (0, 1):
            raise
        failed = bool(e.code)
    r = json.loads(output.read_text())
    for row in r['cases']:
        before = next((e['actual'] for e in row['events'] if e['type']=='QA_SNAP' and e['actual']['stage']=='before-entry'), {})
        initial = next((e['actual'] for e in row['events'] if e['type']=='QA_TRANSFER' and e['actual']['stage']=='before-entry'), {})
        for field, want in row['fixture'].get('expectedInitialSnapshot',{}).items():
            if before.get(field)!=want:
                row['errors'].append(f'Pre-entry source snapshot {field} differs')
        for field, want in row['fixture'].get('expectedInitialTransfer',{}).items():
            if initial.get(field)!=want:
                row['errors'].append(f'Pre-entry source transfer {field} differs')
        evidence = [e['actual'] for e in row['events'] if e['type'] == 'QA_COURIER']
        completed = next((e for e in reversed(evidence) if e['stage'] == 'completed'), None)
        if completed is None:
            row['errors'].append('Actual courier parent did not complete; fixture remains unqualified')
        else:
            expected = dict(phoneDone=1, visitSeen=1, courierDone=1, courierEntity=-1,
                            actionscriptState=0, pending=0, suppression=0, windowOpen=0,
                            brightness=15, fadeActive=0, depth=1, mode=61)
            for field, want in expected.items():
                if completed.get(field) != want:
                    row['errors'].append(f'Courier completion {field}: {completed.get(field)} != {want}')
        final = next((e['actual'] for e in reversed(row['events']) if e['type']=='QA_END'), {})
        if final.get('planUsed') != len(row['fixture']['plan']):
            row['errors'].append('Source-selected plan was not fully consumed by actual menus')
        row['passed'] = not row['errors']
    source = Path(sys.argv[sys.argv.index('--executed-source') + 1])
    for p in ('src/game/overworld_interaction.c', 'src/game/overworld_spawn.c', 'src/game/overworld.c',
              'src/entity/callroutine.c', 'src/entity/script.c', 'src/entity/pathfinding.c', 'src/game/map_loader.c'):
        if (source / p).exists():
            r['executedSourceReferences'].append(dict(path=p, sha256=base.helper.digest(source / p)))
    r['toolVersion'] = 'dev22-real-phone-courier-parent'
    r['allPassed'] = not failed and all(row['passed'] for row in r['cases'])
    r['limits'] = [
        'Starts the real QuickCheckTalk caller at QCT_TEXT, resolving an actually loaded packed phone NPC. Source-derived leader position is prepared before production world initialization; natural story reachability and approach from another map are not asserted.',
        'The phone menu, request, actual platform movement through the packed exit door, normal pending-delivery rearm, courier timer/route, interaction queue, visit and exit run as production dispatcher children with actual platform buttons. No courier handler, position, completion signal, post-entry flags or inventory mutation is injected.',
        'Selected cold boundaries are actual post-phone root, visit bill/inventory menu setup and source movement wait. Driver input-plan progress is retained separately; native state comes only from production capture and fresh-process restore.',
        'A failed prerequisite or bounded stall is retained as an unqualified fixture rather than a game defect. No complete delivery claim unless the completed event and strict postconditions pass.',
        'No audible sound, graphics, all services, all routes or full playthrough proof.']
    output.write_text(json.dumps(r, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(cases=len(r['cases']), passed=sum(row['passed'] for row in r['cases']), qualified=r['allPassed'])))
    if not r['allPassed'] and '--diagnostic' not in sys.argv:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
