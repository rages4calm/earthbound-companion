# SPDX-License-Identifier: GPL-3.0-or-later
"""Run the real ending-trigger text through cast, credits and post-credits setup.

Private driver links an unchanged frozen native library/platform. Prepared
home/party/story prerequisites are explicit. No cinematic completion signals,
mode PCs or ending results are injected after the trigger starts.
"""
import argparse,json,os,re,struct,subprocess,sys
from pathlib import Path
import battle_action_catalog_qa as frozen
from build_maternalbound_pack import read_pack

DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "core/mode_stack.h"
#include "core/memory.h"
#include "game/ending.h"
#include "game/game_state.h"
#include "game/display_text.h"
#include "game/window.h"
#include "game/text.h"
#include "game/overworld.h"
#include "game/maternalbound.h"
#include "game/audio.h"
#include "game/map_loader.h"
#include "game/position_buffer.h"
#include "entity/entity.h"
#include "platform/platform.h"
#include "platform/pc_options.h"
#include "data/assets.h"
#include "data/event_script_data.h"
#include "snes/ppu.h"
#include "include/pad.h"
#include "include/binary.h"
extern int eb_platform_main(int argc,char **argv);

int main(int argc,char **argv){
    if(argc!=6)return 2;
    bool original=atoi(argv[3])!=0;unsigned photo_mode=atoi(argv[4]);
    uint32_t entry=(uint32_t)strtoul(argv[5],NULL,16);
    char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
    char *boot[]={"ending-transaction-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,
        "--allow-redux-development","--headless","--frames","1",original?"--inspect-shuffle":"--redux-battle-fixture","0"};
    if(eb_platform_main(sizeof(boot)/sizeof(boot[0])-(original?1:0),boot)!=0 || maternalbound_enabled()==original)return 3;
    char input_path[4096];snprintf(input_path,sizeof(input_path),"%s/input.replay",argv[2]);
    pc_input_script_path=input_path;
    platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 4;
    game_set_fast_forward(true);audio_init();load_title_screen_script_data();
    game_state.party_count=game_state.player_controlled_party_count=2;
    game_state.current_party_members=3;game_state.party_npc_1=game_state.party_npc_2=0;
    for(unsigned i=0;i<6;i++)game_state.party_members[i]=game_state.party_order[i]=i<2?i+1:0;
    for(unsigned i=0;i<4;i++){
        CharStruct *c=&party_characters[i];memset(c,0,sizeof(*c));
        c->level=50;c->max_hp=c->current_hp=c->current_hp_target=999;
        c->max_pp=c->current_pp=c->current_pp_target=300;
        const uint8_t name[]={'N'+0x30,'a'+0x30,'t'+0x30,'i'+0x30,'v'+0x30,'e'+0x30};
        maternalbound_set_character_name(i,name,6);
    }
    const unsigned prerequisite_flags[]={73,304,469,643};
    for(unsigned i=0;i<4;i++)event_flag_set(prerequisite_flags[i]);
    const uint8_t *photos=ASSET_DATA(ASSET_ENDING_PHOTOGRAPHER_CFG_BIN);
    for(unsigned i=0;i<NUM_PHOTOS;i++){
        unsigned flag=read_u16_le(photos+i*PHOTOGRAPHER_CFG_ENTRY_SIZE);
        if(photo_mode)event_flag_set(flag);else event_flag_clear(flag);
    }
    /* Pinned map_sprites.yml row1/column29: Mom14 at7584,344 and King18
     * at7540,368. This is the real home interior used by the ending. */
    game_state.leader_x_coord=7568;game_state.leader_y_coord=360;
    initialize_overworld_state();
    memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_NONE;
    window_system_init();init_used_bg2_tile_map();text_setup_bg3();text_upload_font_tiles();text_load_window_gfx();text_load_flavour_palette(0);
    create_window(WINDOW_TEXT_STANDARD);set_window_focus(WINDOW_TEXT_STANDARD);
    dt.instant_printing=0;ow.battle_mode=0;
    unsigned home_npc14=0,home_npc18=0;
    for(unsigned i=0;i<MAX_ENTITIES;i++)if(entities.script_table[i]>=0){
        if(entities.npc_ids[i]==14)home_npc14=1;
        if(entities.npc_ids[i]==18)home_npc18=1;
    }
    ModeState text={0};if(!dt_make_child_init(&text,entry))return 5;
    mode_push(GAME_MODE_DISPLAY_TEXT,&text);
    unsigned steps=0,cast_seen=0,credits_seen=0,waits=0,signals=0,cast_palette_seen=0,choice_seen=0,choice_result=~0u;
    uint32_t photo_mask=0;uint16_t cast_palette[20]={0};
    while(g_mode_stack.depth>1 && ++steps<120000){
        unsigned top=g_mode_stack.depth-1;GameMode mode=(GameMode)g_mode_stack.mode[top];
        core.pad1_pressed=platform_input_get_pad_new();
        core.pad1_held=platform_input_get_pad();
        core.pad1_autorepeat=core.pad1_pressed;
        if(mode==GAME_MODE_SELECTION_MENU)choice_seen=1;
        if(mode==GAME_MODE_ACTIONSCRIPT_WAIT && g_mode_stack.state[top].actionscript_wait.phase==0)waits++;
        if(mode==GAME_MODE_ENDING){
            unsigned ep=g_mode_stack.state[top].ending.phase;
            if(ep==EN_CAST_LOOP){cast_seen=1;if(!cast_palette_seen){memcpy(cast_palette,ert.palettes,sizeof(cast_palette));cast_palette_seen=1;}}
            if(ep>=EN_CR_SETUP){credits_seen=1;if(ep==EN_CR_FADEIN)photo_mask|=1u<<g_mode_stack.state[top].ending.photo_idx;}
        }
        unsigned signal_before=ert.actionscript_state;
        StepResult r=mode_dispatch_step(mode,&g_mode_stack.state[top]);
        if(!signal_before && ert.actionscript_state)signals++;
        if(r.kind==STEP_PUSH)mode_push(r.push_mode,r.push_init);
        else if(r.kind==STEP_POP){if(mode==GAME_MODE_SELECTION_MENU)choice_result=(unsigned)r.pop_result;mode_pop(r.pop_result);}
        else host_process_frame();
        if(steps%10000==0)fprintf(stderr,"ENDING_PROGRESS steps=%u depth=%u top=%u flag=%u position=%u,%u\n",steps,g_mode_stack.depth,g_mode_stack.mode[g_mode_stack.depth-1],ert.actionscript_state,game_state.leader_x_coord,game_state.leader_y_coord);
    }
    printf("QA_ENDING {\"steps\":%u,\"depth\":%u,\"castSeen\":%u,\"creditsSeen\":%u,\"choiceSeen\":%u,\"photoMask\":%u,\"waits\":%u,\"naturalSignals\":%u,\"homeNpc14\":%u,\"homeNpc18\":%u,\"partyCount\":%u,\"partyMember\":%u,\"leader\":[%u,%u],\"transitionsDisabled\":%u,\"mainScreenMask\":%u,\"flags\":[",steps,g_mode_stack.depth,cast_seen,credits_seen,choice_seen,photo_mask,waits,signals,home_npc14,home_npc18,game_state.party_count,game_state.party_members[0],game_state.leader_x_coord,game_state.leader_y_coord,ow.disabled_transitions,ppu.tm);
    unsigned printed=0;for(unsigned i=0;i<EVENT_FLAG_COUNT;i++)if(event_flag_get(i))printf("%s%u",printed++?",":"",i);
    printf("],\"choiceResult\":%u,\"castPalette\":[",choice_result);for(unsigned i=0;i<20;i++)printf("%s%u",i?",":"",cast_palette[i]);printf("]}\n");
    audio_shutdown();return g_mode_stack.depth==1?0:6;
}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','native-source','runtime','assets','scratch','output','project'):
        p.add_argument('--'+name,type=Path)
    p.add_argument('--combine-existing',type=Path,nargs='+')
    p.add_argument('--original-profile',action='store_true')
    p.add_argument('--all-photos',action='store_true')
    p.add_argument('--entry',default='C755C4')
    p.add_argument('--diagnostic',action='store_true')
    a=p.parse_args()
    if a.combine_existing:
        reports=[json.loads(f.read_text(encoding='utf-8')) for f in a.combine_existing]
        if not a.output:raise ValueError('Combined output required.')
        if len(reports)!=4 or {(r['profile'],r['allPhotoFlagsPrepared']) for r in reports}!={(s,p) for s in ('Original','Redux') for p in (False,True)}:
            raise ValueError('Exactly both profiles and both photo controls required.')
        if len({json.dumps(r['runtimeSha256'],sort_keys=True) for r in reports})!=1 or any(r['sourceEntry'].upper()!='C755C4' for r in reports):
            raise ValueError('Complete Mom choice cases must use one frozen runtime pair.')
        passed=all(r['allPassed'] and r['skippedCases']==0 for r in reports)
        report={'format':'redux-ending-transaction-review-v1','Passed':passed,'allPassed':passed,
            'executedCases':sum(r['executedCases'] for r in reports),'executedAssertions':sum(r['executedAssertions'] for r in reports),
            'skippedCases':sum(r['skippedCases'] for r in reports),'runtimeSha256':reports[0]['runtimeSha256'],
            'sourceRevision':reports[0]['sourceRevision'],'toolSha256':frozen.digest(Path(__file__)),
            'nativeDefectFound':False,'cases':reports,
            'sourceReferences':[
                'Project/ccscript/data/data_31.ccs:56 Mom ending question, two_choice_menu Yes -> C7562F; actual menu result is asserted.',
                'Project/ccscript/data/data_31.ccs:65 Yes branch with Paula; native full child is run from the question, not a later PC.',
                'Project/ccscript/data/data_31.ccs:80 C75695 cast EVENT11, three interlude scripts/waits, credits EVENT12 and C9C7FA.',
                'Project/ccscript/data/data_58.ccs:511 C9C7FA clears flags, removes Paula, sets postcredits flags, executes warp81/196.',
                'Project/ccscript/redux/cast_coloured_text.ccs PhoenixBound colored cast palette hooks at C4E48D and C4E4C0.',
                'Native platform/SDL replay supplies normal press/release edges; selection_menu reads platform_input_get_pad_new.'
            ],
            'fixtureResolution':'Initial core-only button assignments could advance text but could not choose a selection menu. Source-backed frozen SDL replay input corrected the fixture; no native code was changed.',
            'limits':['Prepared home/party/story prerequisites; preceding full playthrough and interaction dispatch to Mom are not tested.',
                'Actual Mom question, Yes choice, full text/cast/photo credits/interludes and postcredits callback execute with natural completion signals.',
                'All32 photo acquisition flags are prepared; collecting the photos during a full playthrough is unverified.',
                'Final Porky letter and intentional THE END loop are outside this transaction report.',
                'No audible soundtrack, full visual or frame-timing parity claim. Only stated state, palette, signal and continuation assertions are proved.',
                'Player production platform/library objects execute; paired observer hash is provenance, not a second execution.']}
        a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:report[k] for k in ('allPassed','executedCases','executedAssertions','skippedCases')},indent=2))
        if not passed:raise SystemExit(1)
        return
    if any(getattr(a,s.replace('-','_')) is None for s in ('build','native-source','runtime','assets','scratch','output','project')):
        raise ValueError('Build, native-source, runtime, assets, scratch, output and project required for execution.')
    if a.scratch.exists():raise ValueError('Fresh isolated scratch required.')
    pin=subprocess.check_output(['git','-C',str(a.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=frozen.PIN:raise ValueError('Unreviewed pinned source')
    a.scratch.mkdir(parents=True);session=a.scratch/'session';session.mkdir()
    # Deliver ordinary press/release edges through the frozen SDL platform's
    # replay consumer. Selection menus intentionally read platform input rather
    # than core.pad1_pressed, so assigning the latter alone is not valid input.
    (session/'input.replay').write_text(''.join(f'{i} {"80" if i%2==0 else "0"}\n' for i in range(120000)),encoding='ascii')
    frozen.DRIVER=DRIVER;exe,evidence=frozen.private_build(a)
    effective_entry=int(a.entry,16);entry_symbol=None
    if a.original_profile and effective_entry>=0xc00000:
        # Original's compiled text VM uses text_refs IDs rather than raw SNES
        # addresses. Resolve the exact known label from source, not a byte scan.
        sys.path.insert(0,str(a.native_source.resolve()))
        from ebtools.config import load_dump_doc
        doc=load_dump_doc(a.native_source/'earthbound.yml')
        symbols={doc.renameLabels.get(e.name,{}).get(effective_entry-0xc00000-e.offset)
            for e in doc.dumpEntries}
        symbols.discard(None)
        if len(symbols)!=1:raise ValueError('Original ending entry is not one unambiguous known text label.')
        entry_symbol=symbols.pop()
        match=re.search(r'#define\s+'+re.escape(entry_symbol)+r'\s+0x([0-9a-fA-F]+)',(a.native_source/'src/data/text_refs.h').read_text())
        if not match:raise ValueError('Original ending label has no native text reference.')
        effective_entry=int(match[1],16)
    result=subprocess.run([str(exe),str(a.assets.resolve()),str(session.resolve()),str(int(a.original_profile)),str(int(a.all_photos)),f'{effective_entry:X}'],
        cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=180)
    (a.scratch/'native.stdout.log').write_bytes(result.stdout);(a.scratch/'native.stderr.log').write_bytes(result.stderr)
    rows=[json.loads(s[len('QA_ENDING '):]) for s in result.stdout.decode(errors='replace').splitlines() if s.startswith('QA_ENDING ')]
    actual=rows[0] if rows else {};errors=[]
    pack=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h')[2]
    palette_key=next(k for k in pack if k.endswith('ending/cast_bg_palette.pal'))
    palette=list(struct.unpack('<16H',pack[palette_key]))
    expected={'depth':1,'castSeen':1,'creditsSeen':1,'photoMask':0xffffffff if a.all_photos else 0,
        'homeNpc14':1,'homeNpc18':1,'partyCount':1,'partyMember':1,'leader':[8120,1104],
        'transitionsDisabled':0,'mainScreenMask':23,'waits':5,'naturalSignals':6,
        'flags':[11,295,468,469,472,473,476,513,530,749,750,763,775]+([805] if a.original_profile else [781,805])}
    if a.entry.upper()=='C755C4':expected.update(choiceSeen=1,choiceResult=1)
    for k,v in expected.items():
        if actual.get(k)!=v:errors.append({'field':k,'actual':actual.get(k),'expected':v})
    cast_palette=actual.get('castPalette',[])
    palette_assertions=1
    if a.original_profile:
        if cast_palette[:16]!=palette:errors.append({'field':'castPalette[0:16]','actual':cast_palette[:16],'expected':palette})
    else:
        palette_assertions=3
        for k,v in [(0,0),(3,0)]:
            if len(cast_palette)<=k or cast_palette[k]!=v:errors.append({'field':f'castPalette[{k}]','actual':cast_palette,'expected':v})
        if cast_palette[4:20]!=palette:errors.append({'field':'castPalette[4:20]','actual':cast_palette[4:20],'expected':palette})
    warnings=[s for s in result.stderr.decode(errors='replace').splitlines() if re.search(r'\b(?:WARN|ERROR|FATAL|STALL|HANG)\b',s)]
    passed=result.returncode==0 and not errors and not warnings
    report={'format':'redux-ending-transaction-qa-v1','sourceRevision':pin,'profile':'Original' if a.original_profile else 'Redux',
        'allPassed':passed,'nativeExit':result.returncode,'runtimeSha256':{n:frozen.digest(a.runtime/n) for n in ('player.exe','observer.exe')},
        'packSha256':frozen.digest(a.assets),'privateBuild':evidence,'sourceEntry':a.entry,'nativeEntry':f'{effective_entry:X}',
        'nativeEntrySymbol':entry_symbol,'allPhotoFlagsPrepared':a.all_photos,
        'entryPrerequisites':{'flags':[73,304,469,643],'position':[7568,360],'party':[1,2],
            'initialization':['load_title_screen_script_data','audio_init','initialize_overworld_state']},
        'expected':expected,'actual':actual,'errors':errors,'nativeWarnings':warnings,
        'executedCases':int(bool(actual)),'executedAssertions':len(expected)+palette_assertions if actual else 0,'skippedCases':int(not bool(actual)),
        'pinnedSourceFiles':{s:frozen.digest(a.project/s) for s in ('ccscript/data/data_31.ccs','ccscript/data/data_58.ccs','ccscript/redux/cast_coloured_text.ccs')},
        'nativeReferenceFiles':{s:frozen.digest(a.native_source/s) for s in ('src/game/ending.c','src/game/display_text_menus.c','src/game/display_text_cc.c','src/intro/init_intro.c')},
        'runtimeSourceQualification':'Runtime uses unchanged frozen library/platform objects. Native reference files are current reviewed source; display_text_cc.c includes a later dev16 CC1D21 RNG correction not present in executed v6. Production library hash is authoritative.',
        'diagnosticMode':a.diagnostic,
        'limits':['Prepared home/party/story context; preceding full story and interaction dispatch to Mom not covered.',
            'Actual text/cast/credits/interlude/post-credits children execute without injected completion flags or mid-scene PCs.',
            'Photo acquisition is fixture-prepared; complete audiovisual and original timing parity unverified.',
            'Missing prerequisites are investigated before attributing a failure to production native conversion.',
            'Observer hash identifies matching frozen binary pair; this private driver executes player platform objects only.']}
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('allPassed','nativeExit','executedCases')},indent=2))
    if not passed and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
