# SPDX-License-Identifier: GPL-3.0-or-later
"""Check source-empty callbacks through native dispatch and exact ROM bodies.

The action description, inventory consumption and outer turn are intentionally
outside this test. Empty callback semantics never imply an empty whole action.
"""
import argparse,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
import battle_action_catalog_qa_dev15 as previous
from build_maternalbound_pack import read_pack

FUNCTIONS={0xC2889B:'null01',0xC29033:'null02',0xC29039:'null04',0xC2903C:'null05',
    0xC2903F:'null06',0xC29042:'null07',0xC29045:'null08',0xC29048:'null09',
    0xC2904B:'null10',0xC2904E:'null11',0xC292EB:'enemy_extend',0xC2C513:'null12'}


def driver_source(original):
    s=previous.driver_source()
    s=s.replace('static unsigned qa_function,','static unsigned pure_result;static unsigned qa_function,')
    s=s.replace('ModeState action={0};', '''ModeState action={0};
            before_bt=bt;before_core=core;before_game=game_state;before_dt=dt;before_ow=ow;
            before_modes=g_mode_stack;before_rng=rng_state;memcpy(before_party,party_characters,sizeof(before_party));''')
    s=s.replace('if(battle_action_dispatch(callback,&action)) {', 'pure_result=battle_action_dispatch(callback,&action);\n            if(pure_result) {')
    s=s.replace('        printf("QA {',r'''
            after_bt=bt;after_bt.temp_function_pointer=before_bt.temp_function_pointer;
            printf("QA_EMPTY {\"id\":%u,\"pureResult\":%u,\"metadataPointer\":%u,\"battleUnchanged\":%u,\"coreUnchanged\":%u,\"gameUnchanged\":%u,\"textUnchanged\":%u,\"overworldUnchanged\":%u,\"modesUnchanged\":%u,\"rngUnchanged\":%u,\"inventoryUnchanged\":%u}\n",
                v[0],pure_result,bt.temp_function_pointer,!memcmp(&before_bt,&after_bt,sizeof(bt)),!memcmp(&before_core,&core,sizeof(core)),
                !memcmp(&before_game,&game_state,sizeof(game_state)),!memcmp(&before_dt,&dt,sizeof(dt)),!memcmp(&before_ow,&ow,sizeof(ow)),
                !memcmp(&before_modes,&g_mode_stack,sizeof(g_mode_stack)),!memcmp(&before_rng,&rng_state,sizeof(rng_state)),!memcmp(before_party,party_characters,sizeof(before_party)));
        printf("QA {''')
    # Copies remain in case scope after the callback branch closes.
    declaration='''static __typeof__(bt) before_bt,after_bt;static __typeof__(core) before_core;
        static __typeof__(game_state) before_game;static __typeof__(dt) before_dt;static __typeof__(ow) before_ow;
        static __typeof__(g_mode_stack) before_modes;static __typeof__(rng_state) before_rng;
        static CharStruct before_party[TOTAL_PARTY_COUNT];'''
    s=s.replace('        unsigned steps=0;', '        '+declaration+'\n        unsigned steps=0;')
    if original:s=s.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"').replace(' || !maternalbound_enabled()',' || maternalbound_enabled()')
    return s


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ('build','native-source','assets','runtime','scratch','output','project','rom','redux-rom'):parser.add_argument('--'+n,type=Path,required=True)
    parser.add_argument('--original',action='store_true');args=parser.parse_args()
    if args.scratch.exists():raise ValueError('Fresh scratch required')
    pin=subprocess.check_output(['git','-C',str(args.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=helper.PIN:raise ValueError('Unreviewed pin')
    rom_hashes={name:helper.digest(path)for name,path in (('Original',args.rom),('Redux',args.redux_rom))}
    roms={name:path.read_bytes()for name,path in (('Original',args.rom),('Redux',args.redux_rom))};bodies=[]
    for callback,name in FUNCTIONS.items():
        source=args.native_source/f'asm/battle/actions/{name}.asm'
        lines=[line.split(';')[0].strip()for line in source.read_text().splitlines()]
        body=[line for line in lines if line and not line.endswith(':')]
        if body!=['BEGIN_C_FUNCTION_FAR','END_STACK_VARS','END_C_FUNCTION']:raise ValueError('Not an empty source function '+name)
        position=callback-0xC00000
        matches={profile:rom[position:position+3]==bytes((0xC2,0x31,0x6B))for profile,rom in roms.items()}
        if not all(matches.values()):raise ValueError('Routine body changed in owner ROM '+name)
        bodies.append({'function':f'{callback:06X}','asmSource':str(source.relative_to(args.native_source)),
            'asmSourceSha256':helper.digest(source),'verifiedBothRomBodies':matches,'decodedBody':['REP #$31','RTL']})
    args.scratch.mkdir();session=args.scratch/'session';session.mkdir();helper.DRIVER=driver_source(args.original);exe,build=helper.private_build(args)
    _,_,assets=read_pack(args.assets,args.native_source/'src/data/runtime_generated/asset_ids.h');data=assets['data/battle_action_table.bin']
    actions=[(i//12,int.from_bytes(data[i+8:i+12],'little'),data[i+2])for i in range(0,len(data),12)if int.from_bytes(data[i+8:i+12],'little')in FUNCTIONS]
    if {f for _,f,_ in actions}!=set(FUNCTIONS):raise ValueError('Catalog missing callback')
    profiles=[('enemy',8,0,[0]*7),('player',0,0,[0]*7),('NPC',8,5,[0]*7),('unconscious',8,0,[1,0,0,0,0,0,0]),
        ('diamondized',8,0,[2,0,0,0,0,0,0]),('mixed-status-shield',8,0,[4,1,1,1,1,1,2])]
    tests=[]
    for action,callback,action_type in actions:
        for name,enemy,npc,aff in profiles:
            for seed in (1,7,64):
                v=[len(tests),action,seed*0x9e3779b9&0xffffffff,enemy,0,5000,100,5000,300,
                    *aff,64,128,192,255,255,255,20,npc,80,50,20,0,3,0,88,0,
                    0,1,0,0,0,0,0,1,20,20,0,0,0,0,50,0]
                tests.append({'function':f'{callback:06X}','actionId':action,'actionType':action_type,'profile':{'name':name},'seed':seed,'values':v})
    cases=args.scratch/'cases.tsv';cases.write_text('\n'.join(' '.join(map(str,t['values']))for t in tests)+'\n')
    run=subprocess.run([str(exe.resolve()),str(args.assets.resolve()),str(session.resolve()),str(cases.resolve())],cwd=session,
        env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=120)
    log=args.scratch/'native.log';log.write_bytes(run.stdout+run.stderr);results={}
    for line in run.stdout.decode(errors='replace').splitlines():
        for prefix in ('QA ','QA_EMPTY '):
            if line.startswith(prefix):r=json.loads(line[len(prefix):]);results.setdefault(r['id'],{}).update(r)
    rows=[]
    for i,t in enumerate(tests):
        a=results.get(i,{});wanted=dict(pureResult=0,metadataPointer=int(t['function'],16),steps=0,depth=1,
            **{name:1 for name in ('battleUnchanged','coreUnchanged','gameUnchanged','textUnchanged','overworldUnchanged','modesUnchanged','rngUnchanged','inventoryUnchanged')})
        errors=[f'{k}: got {a.get(k)} expected {v}'for k,v in wanted.items()if a.get(k)!=v]
        rows.append({k:v for k,v in dict(t,passed=not errors,errors=errors).items()if k!='values'})
    preserved={name:helper.digest(path)==rom_hashes[name]for name,path in (('Original',args.rom),('Redux',args.redux_rom))}
    report={'schemaVersion':1,'toolVersion':'dev16-empty-callbacks','reduxRevision':pin,'originalPack':args.original,
        'runtimeSha256':{n:helper.digest(args.runtime/n)for n in ('player.exe','observer.exe')},'assetsSha256':helper.digest(args.assets),
        'privateBuild':build,'nativeExitCode':run.returncode,'nativeLogSha256':helper.digest(log),'cases':rows,
        'romBodyReview':bodies,'ownerRomSha256':rom_hashes,'ownerRomsUnchanged':preserved,
        'nativeReviewSha256':helper.digest(args.native_source/'src/game/battle_actions.c'),
        'semanticCoverage':{'completedCases':len(results),'activeCallbacks':[f'{f:06X}'for f in FUNCTIONS],'actualActionRows':len(actions),'profiles':len(profiles)},
        'allPassed':run.returncode==0 and len(results)==len(tests)and all(r['passed']for r in rows)and all(preserved.values()),
        'reproductionFlags':{k:str(getattr(args,k.replace('-','_')))for k in ('build','native-source','assets','runtime','scratch','output','project','rom','redux-rom')},
        'limits':['Exact Original/pinned Redux machine bodies were decoded at original function addresses; this is body inspection, not executed SNES machine proof.',
            'Actual native production dispatcher executes each pure callback for every actual matching action row with seeded battle, status, inventory and RNG state. Full struct state is unchanged except expected dispatcher temp_function_pointer metadata.',
            'No claim that action descriptions, outer turn, PP payment, inventory consumption or other caller behavior is empty.',
            'Core/game/overworld/text/mode/RNG/battle/party state invariants are tested; unlisted globals, pixels/audio and full story/randomizer remain unevaluated.',
            'No owner ROM, extracted asset or save payload is included in the report. Only player library executed; observer hash records provenance.'],
        'fullConversionVerified':False,'fullPlaythroughVerified':False}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cases':len(rows),'completed':len(results),'passed':sum(r['passed']for r in rows),'allPassed':report['allPassed'],'firstFailures':[r for r in rows if not r['passed']][:2]}))
    return 0 if report['allPassed']else 1


if __name__=='__main__':raise SystemExit(main())
