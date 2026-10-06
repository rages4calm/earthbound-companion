# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded complete Giygas prayer callbacks with production scene initialization.

Uses an unchanged frozen native library in a private driver. Inputs prepare
the battle entry context, then run every callback stage and real text/map/entity
children. No event completion signals or program counters are forced mid-scene.
"""
import argparse,json,os,re,struct,subprocess
from pathlib import Path
import battle_action_catalog_qa as frozen
import battle_action_catalog_qa_dev15 as prior
from build_maternalbound_pack import read_pack

def combine_reports(inputs,output):
    """Join separately executed profile evidence without rerunning native code."""
    parts=[json.loads(path.read_text()) for path in inputs]
    positive=[r for r in parts if not r.get('diagnosticMode')]
    negative=[r for r in parts if r.get('diagnosticMode')]
    identities={json.dumps(r['runtimeSha256'],sort_keys=True) for r in parts}
    if len(identities)!=1 or {r['profile'] for r in positive}!={'Original','Redux'}:
        raise ValueError('Both complete profiles must share one frozen runtime identity.')
    negative_checks=[{'profile':r['profile'],'overworldInitialization':r['overworldInitialization'],
        'titleScriptInitialization':r['titleScriptInitialization'],'entryStoryFlags':r['entryStoryFlags'],
        'expectedFailureObserved':not r['allPassed'],'nativeExit':r['nativeExit'],
        'errors':[c['errors'] for c in r['cases']],'nativeWarnings':r['nativeWarnings'],
        'evidenceSha256':frozen.digest(path)} for path,r in zip(inputs,parts) if r.get('diagnosticMode')]
    passed=all(r['allPassed'] for r in positive) and all(r['expectedFailureObserved'] for r in negative_checks)
    report={'format':'redux-complete-prayer-cinematics-review-v1','status':'Passed' if passed else 'Failed',
        'allPassed':passed,'sourceRevision':parts[0]['sourceRevision'],'runtimeSha256':parts[0]['runtimeSha256'],
        'toolSha256':frozen.digest(Path(__file__)),
        'executedCases':sum(r['executedCases'] for r in positive),
        'executedAssertions':sum(r['executedAssertions'] for r in positive),
        'skippedCases':sum(r['skippedCases'] for r in positive),
        'negativeControlCases':sum(r['executedCases'] for r in negative),
        'negativeControls':negative_checks,'profiles':positive,
        'coverage':'Each prayer1–7 starts at its real callback pc0; real map/text/entity/animation children execute through every observed callback pc and all source wait_movement boundaries.',
        'fixturePrerequisites':[
            {'prerequisite':'initialize_overworld_state','source':'asm/overworld/initialize_overworld_state.asm',
             'effect':'Normal slot23 overworld controller, NPC spawns, IRQ tasks, entity allocation/fade state and party/map initialization.'},
            {'prerequisite':'load_title_screen_script_data','source':'src/intro/init_intro.c init_intro',
             'effect':'Ordinary startup loads C42172–C42972 before gameplay. Original EVENT859 is C4279F in this range; abbreviated --inspect-shuffle boot omits it.'},
            {'prerequisite':'FLG_STEP_PAST372 and FLG_DKFD_DOOR_DISAPPEAR651','source':'pinned Project/ccscript/data/data_58.ccs phase-distorter/endgame scripts; data_09.ccs debug progress counters62/65',
             'effect':'Actual source visibility prerequisites for prayer actors including NPC729/735, brothers, Dalaam and Frank; not scene-completion flags.'},
            {'prerequisite':'audio_init','source':'game/audio.h production APU initialization',
             'effect':'Headless driver enables real music/SFX consumers; sound audibility is not asserted.'}],
        'limits':[
            'Prepared endgame callback entries; preceding full story, natural Pray command choice and a continuous final battle remain untested here.',
            'Production native library/player platform objects executed. Observer executable hash identifies the matching frozen pair; no separate observer run claim.',
            'Exact wait counts, scene coordinates/NPCs, naturally generated flags/signals and callback progress are asserted. Pixel-perfect visuals, audible mixes and original timing are not independently proved.',
            'Negative controls demonstrate fixture omissions. Neither omitted prerequisites nor earlier stalls are confirmed native defects.',
            'This expands branches of existing seven callback IDs; it does not add seven new callbacks to the callback inventory.']}
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('allPassed','executedCases','executedAssertions','skippedCases','negativeControlCases')},indent=2))
    if not passed:raise SystemExit(1)

def driver_source(initialize_world,story_prerequisites,title_scripts):
    src=prior.driver_source()
    src=src.replace('#include "game/battle.h"', '#include "game/battle.h"\n#include "game/audio.h"\n#include "data/event_script_data.h"')
    src=src.replace('if(argc!=4) return 2;', 'if(argc!=5) return 2;')
    src=src.replace('char *boot[]={', 'bool original=atoi(argv[4])!=0;\n    char *boot[]={')
    src=src.replace('"--redux-battle-fixture","0"', 'original?"--inspect-shuffle":"--redux-battle-fixture","0"')
    src=src.replace('if(eb_platform_main((int)(sizeof(boot)/sizeof(boot[0])),boot)!=0 || !maternalbound_enabled()) return 3;',
        'int bootargc=(int)(sizeof(boot)/sizeof(boot[0]))-(original?1:0);\n    if(eb_platform_main(bootargc,boot)!=0 || maternalbound_enabled()==original) return 3;')
    src=src.replace('game_set_fast_forward(true);', 'game_set_fast_forward(true);audio_init();')
    if title_scripts:
        # Normal init_intro loads this C4 region before the first game scene.
        # The abbreviated headless bootstrap omits it; Original EVENT859
        # ($C4279F, entity wipe) requires that range during Saturn's prayer.
        src=src.replace('audio_init();','audio_init();load_title_screen_script_data();')
    if story_prerequisites:
        # Pinned data_58 phase-distorter entry sets FLG_STEP_PAST372.
        # NPC729 requires FLG_DKFD_DOOR_DISAPPEAR651, set before the endgame
        # in data_58 and the source debug progress counter62/65 in data_09.
        src=src.replace('dt.instant_printing=0;',
            'dt.instant_printing=0;event_flag_set(372);event_flag_set(651);')
    if initialize_world:
        src=src.replace('ow.battle_mode=0xffff;bt.battle_mode_flag=1;',
            'initialize_overworld_state();\n        ow.battle_mode=0xffff;bt.battle_mode_flag=1;')
    src=src.replace('static unsigned qa_function,qa_var_count,qa_var_rolls[32],qa_damage[16];',
        'static unsigned qa_function,qa_var_count,qa_var_rolls[32],qa_damage[16],qa_signals,qa_wait_entries,qa_seen757,qa_seen729,qa_seen735,qa_case_id,qa_pcs;\nstatic unsigned char qa_seen_scripts[4096],qa_seen_npcs[2048];')
    src=src.replace('unsigned top=g_mode_stack.depth-1;', '''unsigned top=g_mode_stack.depth-1;
        unsigned signal_before=ert.actionscript_state;
        if(top==1 && g_mode_stack.mode[top]==GAME_MODE_BATTLE_ACTION)qa_pcs|=1u<<g_mode_stack.state[top].battle_action.pc;
        if(g_mode_stack.mode[top]==GAME_MODE_ACTIONSCRIPT_WAIT && g_mode_stack.state[top].actionscript_wait.phase==0){
            qa_wait_entries++;
            printf("QA_WAIT {\\"id\\":%u,\\"ordinal\\":%u,\\"step\\":%u,\\"frame\\":%u,\\"leader\\":[%u,%u],\\"animPort522\\":%u,\\"monsterOff\\":%u,\\"battleModeFlag\\":%u}\\n",qa_case_id,qa_wait_entries,steps,core.frame_counter,game_state.leader_x_coord,game_state.leader_y_coord,event_flag_get(522),event_flag_get(11),bt.battle_mode_flag);
        }
        for(unsigned ei=0;ei<MAX_ENTITIES;ei++)if(entities.script_table[ei]>=0){
            if(entities.script_table[ei]<4096)qa_seen_scripts[entities.script_table[ei]]=1;
            if(entities.npc_ids[ei]<2048)qa_seen_npcs[entities.npc_ids[ei]]=1;
            if(entities.script_table[ei]==757)qa_seen757=1;
            if(entities.npc_ids[ei]==729)qa_seen729=1;
            if(entities.npc_ids[ei]==735)qa_seen735=1;
        }
        if(steps%1000==0)fprintf(stderr,"PRAYER_WAIT steps=%u frame=%u top=%u signal=%u port522=%u npcs=%u enabled=%u init23=%d\\n",steps,core.frame_counter,g_mode_stack.mode[top],ert.actionscript_state,event_flag_get(522),ow.overworld_enemy_count,ow.npc_spawns_enabled,entities.script_table[23]);''')
    src=src.replace('if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);',
        'if(!signal_before && ert.actionscript_state)qa_signals++;\n        if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);')
    src=src.replace('qa_var_count=0;', 'qa_var_count=qa_signals=qa_wait_entries=qa_seen757=qa_seen729=qa_seen735=qa_pcs=0;qa_case_id=v[0];memset(qa_seen_scripts,0,sizeof(qa_seen_scripts));memset(qa_seen_npcs,0,sizeof(qa_seen_npcs));')
    src=src.replace('        fflush(stdout);', '''printf("QA_CINEMA {\\"id\\":%u,\\"naturalSignals\\":%u,\\"waitEntries\\":%u,\\"seen757\\":%u,\\"seen729\\":%u,\\"seen735\\":%u,\\"animPort522\\":%u,\\"monsterOff\\":%u,\\"init23Script\\":%d,\\"npcSpawnsEnabled\\":%u,\\"frame\\":%u}\\n",v[0],qa_signals,qa_wait_entries,qa_seen757,qa_seen729,qa_seen735,event_flag_get(522),event_flag_get(11),entities.script_table[23],ow.npc_spawns_enabled,core.frame_counter);
        { int sb=-1;uint16_t so=0;bool bound859=resolve_script_id(859,&sb,&so);
        printf("QA_ACTORS {\\"id\\":%u,\\"event859Bound\\":%u,\\"callbackPcMask\\":%u,\\"observedScripts\\":[",v[0],bound859,qa_pcs);unsigned emitted=0;
        for(unsigned si=0;si<4096;si++)if(qa_seen_scripts[si])printf("%s%u",emitted++?",":"",si);
        printf("],\\"observedNpcs\\":[");emitted=0;
        for(unsigned ni=0;ni<2048;ni++)if(qa_seen_npcs[ni])printf("%s%u",emitted++?",":"",ni);
        printf("]}\\n"); }
        fflush(stdout);''')
    src=src.replace('fclose(input);return 0;', 'fclose(input);audio_shutdown();return 0;')
    return src

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','native-source','runtime','assets','scratch','project'):
        p.add_argument('--'+name,type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--combine-existing',type=Path,nargs='+')
    p.add_argument('--original-profile',action='store_true')
    p.add_argument('--omit-overworld-initialization',action='store_true')
    p.add_argument('--omit-story-prerequisites',action='store_true')
    p.add_argument('--omit-title-script-initialization',action='store_true')
    p.add_argument('--only-prayer',type=int,choices=range(1,8))
    p.add_argument('--diagnostic',action='store_true')
    a=p.parse_args()
    if a.combine_existing:
        combine_reports(a.combine_existing,a.output);return
    if any(getattr(a,name.replace('-','_')) is None for name in ('build','native-source','runtime','assets','scratch','project')):
        p.error('Native execution requires --build, --native-source, --runtime, --assets, --scratch and --project.')
    if a.scratch.exists():raise ValueError('Fresh isolated scratch required.')
    pin=subprocess.check_output(['git','-C',str(a.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=frozen.PIN:raise ValueError('Unreviewed source pin')
    a.scratch.mkdir(parents=True);session=a.scratch/'session';session.mkdir()
    frozen.DRIVER=driver_source(not a.omit_overworld_initialization,not a.omit_story_prerequisites,not a.omit_title_script_initialization)
    exe,evidence=frozen.private_build(a)
    tests=[]
    pack=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h')[2]
    teleport_data=pack['data/teleport_destination_table.bin']
    for prayer,callback in enumerate((0xC2C572,0xC2C5D1,0xC2C5FA,0xC2C623,0xC2C64C,0xC2C675,0xC2C69E),1):
        if a.only_prayer and prayer!=a.only_prayer:continue
        v=[len(tests),callback,0x9e3779b9,222 if prayer==1 else 230,0,60000,200,60000,300,
            0,0,0,0,0,0,0,255,255,255,255,255,255,20,0,80,50,20,0,0,0,0,0,
            0,1,0,0,prayer+3,0,0,0,20,20,0,0,0,0,50,0]
        waits=(4,2,4,5,4,2,5)[prayer-1]
        warp=(229,222,223,224,226,227,221)[prayer-1]
        # TELEPORT_TO stores destinations as 8px tiles; source shifts each
        # component three times before LOAD_MAP_AT_POSITION (door.c TT_AFTER_OUT).
        xy=[coordinate*8 for coordinate in struct.unpack_from('<HH',teleport_data,warp*8)]
        npcs={1:[729,735],2:[1072,1073,1074,1075],3:[],4:[600,601,602,603],5:[1110,1111],6:[38],7:[]}[prayer]
        tests.append({'prayer':prayer,'callback':f'{callback:06X}','values':v,'requiredSceneNpcs':npcs,'sourceWarp':warp,'expectedSceneCoordinates':xy,
            'expected':{'depth':1,'giygasPhase':prayer+4,'battleGroup':480 if prayer==7 else 479,
                'naturalSignals':waits,'waitEntries':waits,'animPort522':1,'monsterOff':0,
                'seen757':1,'init23Script':1,'npcSpawnsEnabled':255,'event859Bound':1,
                'callbackPcMask':(1<<(10 if prayer in (1,7) else 9))-1}})
    inputs=a.scratch/'cases.tsv';inputs.write_text('\n'.join(' '.join(map(str,t['values'])) for t in tests)+'\n')
    result=subprocess.run([str(exe),str(a.assets.resolve()),str(session.resolve()),str(inputs.resolve()),str(int(a.original_profile))],
        cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=180)
    (a.scratch/'native.log').write_bytes(result.stdout+result.stderr)
    (a.scratch/'native.stdout.log').write_bytes(result.stdout)
    (a.scratch/'native.stderr.log').write_bytes(result.stderr)
    warnings=[line for line in result.stderr.decode(errors='replace').splitlines() if re.search(r'\b(?:WARN|ERROR|FATAL|STALL|HANG)\b',line)]
    rows={};waits={}
    for line in result.stdout.decode(errors='replace').splitlines():
        if line.startswith('QA_WAIT '):
            row=json.loads(line[len('QA_WAIT '):]);waits.setdefault(row['id'],[]).append(row)
        for prefix in ('QA ','QA_DETAIL ','QA_CINEMA ','QA_ACTORS '):
            if line.startswith(prefix):
                row=json.loads(line[len(prefix):]);rows.setdefault(row['id'],{}).update(row)
    cases=[]
    for t in tests:
        actual=rows.get(t['values'][0],{});errors=[]
        for key,value in t['expected'].items():
            if actual.get(key)!=value:errors.append({'field':key,'actual':actual.get(key),'expected':value})
        for npc in t['requiredSceneNpcs']:
            if npc not in actual.get('observedNpcs',[]):errors.append({'field':'requiredSceneNpc','actual':npc,'expected':'observed'})
        trace=waits.get(t['values'][0],[])
        for wait in trace:
            for key,value in {'leader':t['expectedSceneCoordinates'],'monsterOff':1,'battleModeFlag':0,
                'animPort522':int(wait['ordinal']==t['expected']['waitEntries'])}.items():
                if wait.get(key)!=value:errors.append({'field':'wait.'+key,'ordinal':wait['ordinal'],'actual':wait.get(key),'expected':value})
        if len(trace)!=t['expected']['waitEntries']:errors.append({'field':'waitTraceCount','actual':len(trace),'expected':t['expected']['waitEntries']})
        cases.append({**{k:v for k,v in t.items() if k!='values'},'actual':actual,'waitTimeline':trace,'passed':not errors,'errors':errors})
    refs=['src/game/battle_actions.c','src/game/display_text_cc.c','src/game/overworld.c','src/game/map_loader.c','src/entity/script.c','src/entity/callroutine.c',
        'asm/battle/display_battle_cutscene_text.asm','asm/text/wait_for_actionscript.asm','asm/overworld/initialize_overworld_state.asm',
        'asm/data/events/scripts/757.asm','asm/data/events/scripts/747.asm','asm/data/events/scripts/859.asm',
        'src/intro/init_intro.c','src/data/event_script_data.c','src/entity/callbacks.c','src/game_main.c','src/game/door.c']
    source_refs=['ccscript/data/data_34.ccs','ccscript/data/data_58.ccs','ccscript/data/data_09.ccs','ccscript/data/data_59.ccs']
    report={'format':'redux-prayer-cinematic-qa-v2','profile':'Original' if a.original_profile else 'Redux',
        'sourceRevision':pin,'runtimeSha256':{n:frozen.digest(a.runtime/n) for n in ('player.exe','observer.exe')},
        'packSha256':frozen.digest(a.assets),'privateBuild':evidence,'overworldInitialization':not a.omit_overworld_initialization,
        'titleScriptInitialization':not a.omit_title_script_initialization,
        'entryStoryFlags':[] if a.omit_story_prerequisites else [372,651],
        'entryStoryFlagSources':{'372':'Project/ccscript/data/data_58.ccs l_0xc9c19b: phase-distorter entry sets FLG_STEP_PAST',
            '651':'Project/ccscript/data/data_58.ccs before FLG_DKFD_GUMI_BOSS; data_09.ccs progress counter62 also sets FLG_DKFD_DOOR_DISAPPEAR'},
        'nativeExit':result.returncode,'allPassed':result.returncode==0 and bool(cases) and not warnings and all(x['passed'] for x in cases),
        'executedCases':sum(bool(x['actual']) for x in cases),'requestedCases':len(cases),'cases':cases,
        'executedAssertions':sum(len(x['expected'])+len(x['requiredSceneNpcs'])+1+len(x['waitTimeline'])*4 for x in cases if x['actual']),
        'skippedCases':sum(not bool(x['actual']) for x in cases),'nativeWarnings':warnings,
        'sourceFiles':{r:frozen.digest(a.native_source/r) for r in refs},
        'pinnedSourceFiles':{r:frozen.digest(a.project/r) for r in source_refs},
        'diagnosticMode':a.diagnostic,
        'limits':['Prepared battle callback entry; no preceding full story or natural Pray command selection claim.',
            'Natural text/map/entity scene children are driven without injected completion flags or skipped callback PCs.',
            'Actor observations show real assigned scripts/NPCs; no pixel-perfect appearance, sound audibility or original timing oracle claim.',
            'A failed bounded diagnostic is not a native defect until missing fixture prerequisites have been excluded.']}
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('allPassed','nativeExit','executedCases','requestedCases')},indent=2))
    if not report['allPassed'] and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
