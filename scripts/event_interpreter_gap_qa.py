# SPDX-License-Identifier: GPL-3.0-or-later
"""Expand the movement structural audit to Original and prove mini-ghost behavior.

Static pointer-root reachability is a candidate inventory, not proof of full
story coverage. Private runtime uses the unchanged frozen production library.
"""
import argparse,collections,hashlib,inspect,json,os,re,struct,subprocess,sys
from pathlib import Path
import audit_redux_movement as movement
import battle_action_catalog_qa as frozen
from build_maternalbound_pack import read_pack

DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "game/game_state.h"
#include "game/overworld.h"
#include "game/battle.h"
#include "game/maternalbound.h"
#include "game/audio.h"
#include "game/position_buffer.h"
#include "entity/entity.h"
#include "core/mode_stack.h"
#include "core/state_dump.h"
#include "data/event_script_data.h"
#include "platform/platform.h"
#include "platform/pc_options.h"
#include "include/constants.h"
#include "snes/ppu.h"
extern int eb_platform_main(int argc,char **argv);

static void progress_snapshot(const char *name){
    FILE *f=fopen(name,"wb");if(!f)return;
    fwrite(&game_state,sizeof(game_state),1,f);
    fwrite(party_characters,sizeof(party_characters),1,f);
    fwrite(event_flags,sizeof(event_flags),1,f);fclose(f);
}
static void ghost_marker(const char *label){
    int ghost=ow.mini_ghost_entity_id,script=-1;
    if(ghost>=0 && ghost<MAX_ENTITIES)script=entities.script_index[ghost];
    printf("%s {\"entity\":%d,\"sprite\":%d,\"event\":%d,\"script\":%d,\"bank\":%d,\"pc\":%d,\"sleep\":%d,\"stack\":%d}\n",label,ghost,
        ghost>=0?entities.sprite_ids[ghost]:-1,ghost>=0?entities.script_table[ghost]:-1,script,
        script>=0?scripts.pc_bank[script]:-1,script>=0?scripts.pc[script]:-1,
        script>=0?scripts.sleep_frames[script]:-1,script>=0?scripts.stack_offset[script]:-1);
}

int main(int argc,char **argv){
    if(argc!=8)return 2;
    bool original=atoi(argv[3])!=0;unsigned possession=atoi(argv[4]);
    unsigned title_first=atoi(argv[5]),checkpoint=atoi(argv[6]);
    unsigned marker=atoi(argv[7]);
    char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
    char *boot[]={"ghost-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,
        "--allow-redux-development","--headless","--frames","1",original?"--inspect-shuffle":"--redux-battle-fixture","0"};
    if(eb_platform_main(sizeof(boot)/sizeof(boot[0])-(original?1:0),boot)!=0 || maternalbound_enabled()==original)return 3;
    platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 4;
    if(title_first){
        free_event_script_data();free_title_screen_script_data();
        load_title_screen_script_data();load_event_script_data();
    }
    game_set_fast_forward(true);audio_init();load_title_screen_script_data();
    pc_options.no_dad_calls=pc_options.no_homesickness=true;
    game_state.party_count=game_state.player_controlled_party_count=1;
    game_state.current_party_members=1;game_state.party_npc_1=game_state.party_npc_2=0;
    for(unsigned i=0;i<6;i++)game_state.party_members[i]=game_state.party_order[i]=i==0?1:0;
    memset(&party_characters[0],0,sizeof(party_characters[0]));
    party_characters[0].level=30;party_characters[0].max_hp=party_characters[0].current_hp=party_characters[0].current_hp_target=300;
    party_characters[0].max_pp=party_characters[0].current_pp=party_characters[0].current_pp_target=100;
    event_flag_set(11);game_state.leader_x_coord=7568;game_state.leader_y_coord=360;
    initialize_overworld_state();
    /* Normal overworld_boot_flush unblanks after intro/fade setup. The
     * abbreviated headless bootstrap stops before that production tail. */
    ppu.inidisp=0x0f;
    party_characters[0].afflictions[STATUS_GROUP_PERSISTENT_HARDHEAL]=possession?STATUS_1_POSSESSED:0;
    memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_OVERWORLD;
    g_mode_stack.state[0].overworld.phase=OWP_RENDER;
    unsigned loaded=0;
    if(checkpoint==2){loaded=state_dump_load_slots();if(!loaded)return 8;progress_snapshot("restored-progress.bin");}
    ghost_marker("QA_GHOST_ENTRY");
    int fade_bank=-1;uint16_t fade_pc=0;unsigned fade_roots=0,fade_byte=255;
    if(resolve_script_id(859,&fade_bank,&fade_pc)){
        fade_byte=script_bank_read_byte(fade_bank,fade_pc);
        for(unsigned i=0;i<MAX_ENTITIES;i++)if(entities.script_index[i]>=0){
            int slot=entities.script_index[i];
            if(scripts.pc_bank[slot]==fade_bank && scripts.pc[slot]==fade_pc)fade_roots++;
        }
    }
    printf("QA_LEGACY_TITLE {\"bank\":%d,\"pc\":%u,\"byte\":%u,\"savedActorsAtEntry\":%u}\n",fade_bank,fade_pc,fade_byte,fade_roots);
    int resume_ghost=ow.mini_ghost_entity_id,resume_script_bank=-1;
    if(resume_ghost>=0 && resume_ghost<MAX_ENTITIES && entities.script_index[resume_ghost]>=0)
        resume_script_bank=scripts.pc_bank[entities.script_index[resume_ghost]];
    int resolved_bank=-1;uint16_t resolved_offset=0;
    unsigned resolves786=resolve_script_id(786,&resolved_bank,&resolved_offset);
    unsigned roots=0,resolved_roots=0;
    for(unsigned id=1;id<event_script_pointer_count;id++){
        int bank;uint16_t offset;roots++;
        if(resolve_script_id((uint16_t)id,&bank,&offset))resolved_roots++;
    }
    printf("QA_BANKS {\"roots\":%u,\"resolvedRoots\":%u,\"regions\":[",roots,resolved_roots);
    for(int i=0;i<script_bank_count;i++)printf("%s{\"index\":%d,\"bank\":%u,\"base\":%u,\"size\":%u}",i?",":"",i,script_banks[i].rom_bank,script_banks[i].rom_base_addr,script_banks[i].size);
    printf("]}\n");
    unsigned ghost_seen=0,ghost_visible=0,ghost_moved=0;int first_x=-256,first_y=-256,last_x=-256,last_y=-256;
    unsigned frames=0,steps=0;
    while(frames<96 && ++steps<3000){
        unsigned top=g_mode_stack.depth-1;GameMode m=(GameMode)g_mode_stack.mode[top];
        StepResult r=mode_dispatch_step(m,&g_mode_stack.state[top]);
        if(r.kind==STEP_PUSH)mode_push(r.push_mode,r.push_init);
        else if(r.kind==STEP_POP)mode_pop(r.pop_result);
        else {host_process_frame();frames++;}
        int ghost=ow.mini_ghost_entity_id;
        if(ghost>=0 && ghost<MAX_ENTITIES){
            if(!ghost_seen){first_x=entities.abs_x[ghost];first_y=entities.abs_y[ghost];}
            ghost_seen=1;last_x=entities.abs_x[ghost];last_y=entities.abs_y[ghost];
            if(last_x!=first_x || last_y!=first_y)ghost_moved=1;
            if(last_x!=-256 && last_y!=-256 && entities.animation_frame[ghost]>=0)ghost_visible=1;
        }
    }
    int ghost=ow.mini_ghost_entity_id,sleep=-999,script_bank=-1;
    if(ghost>=0 && ghost<MAX_ENTITIES && entities.script_index[ghost]>=0){
        int script=entities.script_index[ghost];sleep=scripts.sleep_frames[script];script_bank=scripts.pc_bank[script];
    }
    printf("QA_GHOST {\"resolves786\":%u,\"frames\":%u,\"depth\":%u,\"ghostSeen\":%u,\"ghostVisible\":%u,\"ghostMoved\":%u,\"ghostId\":%d,\"first\":[%d,%d],\"last\":[%d,%d],\"sleep\":%d,\"scriptBank\":%d,\"affliction\":%u}\n",resolves786,frames,g_mode_stack.depth,ghost_seen,ghost_visible,ghost_moved,ghost,first_x,first_y,last_x,last_y,sleep,script_bank,party_characters[0].afflictions[1]);
    int title_entity=-1,title_bank=-1;uint16_t title_pc=0;
    if(checkpoint==3){
        title_entity=create_entity(0,859,-1,0,0);
        if(title_entity>=0 && entities.script_index[title_entity]>=0){
            int script=entities.script_index[title_entity];title_bank=scripts.pc_bank[script];title_pc=scripts.pc[script];
        }
    }
    if(marker && ghost>=0 && ghost<MAX_ENTITIES && entities.script_index[ghost]>=0){
        int slot=entities.script_index[ghost];scripts.pc_bank[slot]=0xff;scripts.pc[slot]=0;
        scripts.sleep_frames[slot]=-1;scripts.stack_offset[slot]=0;
        if(marker==2)entities.script_table[ghost]=785;
        if(marker==3)entities.sprite_ids[ghost]=263;
    }
    ghost_marker("QA_GHOST_CAPTURE");
    unsigned saved=(checkpoint==1 || checkpoint==3)?state_dump_save_slots():0;
    printf("QA_CHECKPOINT {\"saved\":%u,\"loaded\":%u,\"initialGhost\":%d,\"initialGhostBank\":%d,\"titleEntity\":%d,\"titleBank\":%d,\"titlePc\":%u}\n",saved,loaded,resume_ghost,resume_script_bank,title_entity,title_bank,title_pc);
    if(saved)progress_snapshot("checkpoint-progress.bin");
    audio_shutdown();return frames==96?0:6;
}
'''


def profile_audit(pack,source,original):
    function=inspect.getsource(movement.audit)
    function=function.replace('def audit(assets, native_source):','def audit(assets, native_source, redux):',1)
    function=function.replace('sizes.update({0x32:0,0x33:0})','\n    if redux: sizes.update({0x32:0,0x33:0})',1)
    function=function.replace('if opcode in (0x03,0x04,0x31):','if opcode in ((0x03,0x04,0x31) if redux else (0x03,0x04)):',1)
    scope=dict(vars(movement));exec(function,scope)
    assets=dict(pack)
    if original:
        from ebtools.parsers.original_movement_banks import decode_original_movement_banks
        raw=pack['US/events/bank_c3_scripts_combined.bin']
        decoded=decode_original_movement_banks(raw)
        # Exactly the donor asset's Original production regions; legacy naked
        # C3 has no C0 region. Title is supplied by normal startup initialization.
        regions=[(0xc3,0,decoded[0] if decoded else raw),
            (0xc4,0x0e24,pack['US/events/bank_c4_scripts.bin']),
            (0xc4,0x2172,pack['US/intro/title_screen_scripts.bin'])]
        if decoded:regions.append((0xc0,0xad8a,decoded[1]))
        container=bytearray(struct.pack('<8sI',b'MRMVBN01',len(regions)))
        for bank,base,data in regions:container.extend(struct.pack('<BBHI',bank,0,base,len(data)));container.extend(data)
        assets['US/events/bank_c3_scripts_combined.bin']=bytes(container)
    result=scope['audit'](assets,source,not original)
    result['AnalyzerDependencySha256']=frozen.digest(Path(movement.__file__))
    result['ProfileAdaptation']='Original opcode31 is BGscroll,32/33 consume3bytes; regions reflect naked C3 or EBMVBN01 donor container plus normal C4/title init.' if original else 'Unchanged existing Redux structural traversal.'
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('build','native-source','runtime','assets','scratch','output','project'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--original-profile',action='store_true');p.add_argument('--diagnostic',action='store_true')
    p.add_argument('--expect-legacy-missing-ghost',action='store_true',help='Assert readable legacy naked-C3 behavior and document its expected missing ghost.')
    p.add_argument('--title-first',action='store_true',help='Exercise the alternative actual public loader initialization order.')
    p.add_argument('--capture-checkpoint',choices=('normal','title'),help='Capture private fixtures through actual save-slots production API after the root-loop test.')
    p.add_argument('--resume-from',type=Path,help='Copy private fixture saves and cold-load with actual save-slots production API.')
    p.add_argument('--expect-saved-title',action='store_true',help='Assert actual old bank2 EVENT859 checkpoint entry remains mapped to the same donor title bytecode.')
    p.add_argument('--resume-visible-ghost',action='store_true',help='Cold checkpoint already has a visible ghost; do not require new offscreen-to-visible motion.')
    p.add_argument('--capture-ghost-marker',choices=('unresolved','wrong-event','wrong-sprite'),help='Prepare a private invalid-marker negative-control checkpoint after the completed overworld test.')
    p.add_argument('--expect-unrepaired-marker',action='store_true',help='Assert a deliberately unrecognized/profile-excluded invalid ghost is not repaired.')
    a=p.parse_args()
    if a.scratch.exists():raise ValueError('Fresh private scratch required.')
    pin=subprocess.check_output(['git','-C',str(a.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=frozen.PIN:raise ValueError('Unexpected pin.')
    a.scratch.mkdir(parents=True)
    sys.path.insert(0,str(a.native_source.resolve()))
    pack=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h')[2]
    legacy=a.expect_legacy_missing_ghost
    if legacy and (not a.original_profile or pack['US/events/bank_c3_scripts_combined.bin'].startswith(b'EBMVBN01')):
        raise ValueError('Legacy expectation requires Original naked C3 pack.')
    static=profile_audit(pack,a.native_source,a.original_profile)
    frozen.DRIVER=DRIVER;exe,evidence=frozen.private_build(a)
    cases=[]
    for possessed in (False,True):
        session=a.scratch/('possessed' if possessed else 'healthy');session.mkdir()
        if a.resume_from:
            import shutil
            shutil.copytree(a.resume_from/session.name/'saves',session/'saves')
        checkpoint=2 if a.resume_from else (3 if a.capture_checkpoint=='title' else (1 if a.capture_checkpoint else 0))
        marker={'unresolved':1,'wrong-event':2,'wrong-sprite':3}.get(a.capture_ghost_marker,0)
        r=subprocess.run([str(exe),str(a.assets.resolve()),str(session.resolve()),str(int(a.original_profile)),str(int(possessed)),str(int(a.title_first)),str(checkpoint),str(marker)],
            cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=90)
        (session/'native.stdout.log').write_bytes(r.stdout);(session/'native.stderr.log').write_bytes(r.stderr)
        rows=[json.loads(s[len('QA_GHOST '):]) for s in r.stdout.decode(errors='replace').splitlines() if s.startswith('QA_GHOST ')]
        actual=rows[0] if rows else {}
        expected={'resolves786':0 if legacy else 1,'frames':96,'depth':1,'ghostSeen':int(possessed),'ghostVisible':int(possessed and not legacy),'ghostMoved':int(possessed and not legacy),'affliction':2 if possessed else 0}
        if a.resume_visible_ghost and possessed:expected.pop('ghostMoved')
        if a.expect_unrepaired_marker and possessed:expected.pop('ghostVisible');expected.pop('ghostMoved')
        if a.expect_saved_title and possessed:
            # EVENT859 here is an explicitly isolated bank-mapping actor,
            # not a complete fade scene. With V4=0 its real source disables
            # other callbacks then ends; ghost motion is proved separately.
            expected.pop('ghostVisible');expected.pop('ghostMoved')
        errors=[{'field':k,'expected':v,'actual':actual.get(k)} for k,v in expected.items() if actual.get(k)!=v]
        warnings=[s for s in r.stderr.decode(errors='replace').splitlines() if re.search(r'\b(?:WARN|ERROR|FATAL)\b|unknown script|unhandled',s)]
        allowed_warnings=legacy and possessed and len(warnings)==1 and 'unknown script ID 786' in warnings[0]
        banks=[json.loads(s[len('QA_BANKS '):]) for s in r.stdout.decode(errors='replace').splitlines() if s.startswith('QA_BANKS ')]
        bank_actual=banks[0] if banks else {}
        if bank_actual.get('roots')!=static['Roots'] or bank_actual.get('resolvedRoots')!=static['Roots']-int(legacy):
            errors.append({'field':'productionRootResolution','expected':static['Roots']-int(legacy),'actual':bank_actual})
        checkpoint_rows=[json.loads(s[len('QA_CHECKPOINT '):]) for s in r.stdout.decode(errors='replace').splitlines() if s.startswith('QA_CHECKPOINT ')]
        checkpoint_actual=checkpoint_rows[0] if checkpoint_rows else {}
        if checkpoint and checkpoint_actual.get('loaded' if checkpoint==2 else 'saved')!=1:
            errors.append({'field':'checkpointStorage','expected':1,'actual':checkpoint_actual})
        progress_equal=None
        if a.resume_from and (a.resume_from/session.name/'checkpoint-progress.bin').exists():
            progress_equal=(a.resume_from/session.name/'checkpoint-progress.bin').read_bytes()==(session/'restored-progress.bin').read_bytes()
            if not progress_equal:errors.append({'field':'partyStoryInventoryProgress','expected':'byte-identical immediately after restore','actual':'different'})
        title_rows=[json.loads(s[len('QA_LEGACY_TITLE '):]) for s in r.stdout.decode(errors='replace').splitlines() if s.startswith('QA_LEGACY_TITLE ')]
        title_actual=title_rows[0] if title_rows else {}
        if a.expect_saved_title:
            address=int.from_bytes(pack['US/events/event_script_pointers.bin'][859*3:859*3+3],'little')
            pc=address-0xc42172
            title_expected={'bank':2,'pc':pc,'byte':pack['US/intro/title_screen_scripts.bin'][pc],'savedActorsAtEntry':1}
            errors.extend({'field':'legacyTitle.'+k,'expected':v,'actual':title_actual.get(k)} for k,v in title_expected.items() if title_actual.get(k)!=v)
        markers={}
        for key in ('ENTRY','CAPTURE'):
            prefix='QA_GHOST_'+key+' '
            parsed=[json.loads(s[len(prefix):]) for s in r.stdout.decode(errors='replace').splitlines() if s.startswith(prefix)]
            markers[key]=parsed[0] if parsed else {}
        marker_equal=None
        if a.resume_from and (a.resume_visible_ghost or a.expect_unrepaired_marker):
            old_report=json.loads(a.resume_from.with_suffix('.json').read_text())
            old_case=next(c for c in old_report['cases'] if c['possessed']==possessed)
            marker_equal=markers['ENTRY']==old_case['ghostMarkers']['CAPTURE']
            if not marker_equal:errors.append({'field':'unchangedGhostMarker','expected':old_case['ghostMarkers']['CAPTURE'],'actual':markers['ENTRY']})
        assertion_count=len(expected)+1+int(bool(checkpoint))+4*int(a.expect_saved_title)+int(progress_equal is not None)+int(marker_equal is not None)
        cases.append({'possessed':possessed,'passed':r.returncode==0 and not errors and (not warnings or allowed_warnings),'nativeExit':r.returncode,'expected':expected,'actual':actual,'errors':errors,'warnings':warnings,'expectedLegacyWarning':bool(allowed_warnings),'productionBanks':bank_actual,'checkpoint':checkpoint_actual,'legacyTitle':title_actual,'partyStoryInventoryProgressUnchanged':progress_equal,'ghostMarkers':markers,'ghostMarkerUnchangedAfterRestore':marker_equal,'executedAssertions':assertion_count})
    static_passed=static['Passed'] or (legacy and static['Errors']==['Unavailable bytes at C0AD8A (1); reached from script 786'])
    passed=static_passed and all(c['passed'] for c in cases)
    report={'format':'event-interpreter-gap-qa-v1','profile':'Original' if a.original_profile else 'Redux',
        'allPassed':passed,'Passed':passed,'sourceRevision':pin,'static':static,'cases':cases,'privateBuild':evidence,
        'runtimeSha256':{n:frozen.digest(a.runtime/n) for n in ('player.exe','observer.exe')},'packSha256':frozen.digest(a.assets),
        'sourceFiles':{s:frozen.digest(a.native_source/s) for s in ('src/data/event_script_data.c','src/core/state_dump.c','ebtools/cli/extract.py','ebtools/cli/pack_all.py','ebtools/parsers/original_movement_banks.py','src/entity/entity.c','src/entity/script.c','src/entity/opcodes.c','src/entity/callroutine.c','src/game/position_buffer.c','src/game/overworld.c','asm/data/events/scripts/786.asm','asm/overworld/update_overworld_frame.asm','asm/overworld/entity/create_mini_ghost_entity.asm')},
        'executedCases':len(cases),'executedAssertions':sum(c['executedAssertions'] for c in cases),'skippedCases':0,'legacyMissingGhostExpected':legacy,'titleFirst':a.title_first,'savedTitleMappingScope':a.expect_saved_title,
        'sourceReferences':['Original EVENT786 at C0AD8A in donor pointer table; new EBMVBN01 retains donor bytecode in existing asset, legacy naked C3 omits C0.',
            'GET_PARTY_MEMBER_SPRITE_ID possessed affliction increments count; normal overworld root then creates mini-ghost via CREATE_ENTITY script786.',
            'Source EVENT786 sets position/physics, pauses8frames, renders sprite, loops UPDATE_MINI_GHOST_POSITION.',
            'Restore repairs only Original tracked sprite264/event786 with unresolved saved bank0xFF and now-resolvable donor script, using normal reassign_entity_script.',
            'Original loader eagerly registers normal title C4 before appended C0, retaining legacy bank indices; later title initialization deduplicates the identical region.'],
        'limits':['All movement pointer roots are a conservative structural inventory, not a full story reachability proof.',
            'Runtime root starts after normal prepared home/party initialization and executes96 actual overworld/host frames with no input.',
            'No owner save edits or completion flags. Normal possession uses the real ghost-creation consumer; optional private checkpoint controls explicitly modify markers or create an EVENT859 actor.',
            'Isolated EVENT859 checkpoint tests prove legacy bank2 bytecode binding and bounded execution, not a full fade timeline. That actor lacks normal V4 fade prerequisites and source-disables other callbacks, so its ghost motion is excluded.',
            'Runtime uses the supplied immutable library/platform; exact privateBuild and runtime hashes identify executed code.',
            'Observer hash is paired provenance; driver executes player platform objects only.']}
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'allPassed':passed,'structuralErrors':static['Errors'],'cases':cases},indent=2))
    if not passed and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
