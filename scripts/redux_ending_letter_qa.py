# SPDX-License-Identifier: GPL-3.0-or-later
"""Run the Mom ending, then the real final letter into its terminal THE END wait.

Only the player's downstairs arrival is prepared between transactions. All
letter text, animation waits, closing animation and terminal wait are native.
Unchanged frozen production platform/library objects execute privately.
"""
import argparse,json,os,re,subprocess,sys
from pathlib import Path
import battle_action_catalog_qa as frozen
import redux_ending_transaction_qa as ending
from build_maternalbound_pack import read_pack


def driver():
    # Reuse the already-reviewed complete ending bootstrap and pump; keep its
    # hash as a dependency. These narrowly delimited replacements add the
    # second production transaction and a bounded observation of its loop.
    source=ending.DRIVER
    replacements=[
        ('if(argc!=6)return 2;', 'if(argc!=8)return 2;'),
        ('uint32_t entry=(uint32_t)strtoul(argv[5],NULL,16);',
         'uint32_t entry=(uint32_t)strtoul(argv[5],NULL,16);\n'
         '    uint32_t letter_entry=(uint32_t)strtoul(argv[6],NULL,16),loop_entry=(uint32_t)strtoul(argv[7],NULL,16);'),
        ('while(g_mode_stack.depth>1 && ++steps<120000){', r'''
    unsigned letter_started=0,ending_completed=0,knock_npc22=0,terminal_delays=0;
    unsigned actor776_seen=0,actor776_count=0,animation_frame_mask=0;
    char oracle_path[4096];snprintf(oracle_path,sizeof(oracle_path),"%s/theend.bin",argv[2]);
    unsigned char expected_art[8192];FILE *oracle=fopen(oracle_path,"rb");
    size_t art_size=oracle?fread(expected_art,1,sizeof(expected_art),oracle):0;if(oracle)fclose(oracle);
    uint32_t loop_offset=~0u;
    while(++steps<120000){
        if(g_mode_stack.depth==1 && !letter_started){
            ending_completed=cast_seen && credits_seen && choice_result==1;
            /* Source map_sprites.yml row1/col30 places knockNPC22 at7792,344.
             * Prepare only the player's normal downstairs arrival. Do not
             * inject any new event flags or actor completion signals. */
            game_state.leader_x_coord=7776;game_state.leader_y_coord=344;
            initialize_overworld_state();
            for(unsigned i=0;i<MAX_ENTITIES;i++)if(entities.script_table[i]>=0 && entities.npc_ids[i]==22)knock_npc22=1;
            ModeState terminal={0},letter={0};
            if(!dt_make_child_init(&terminal,loop_entry) || !dt_make_child_init(&letter,letter_entry))return 7;
            loop_offset=terminal.display_text.reader.ptr_off;
            waits=signals=0;letter_started=1;
            mode_push(GAME_MODE_DISPLAY_TEXT,&letter);
        }
        if(g_mode_stack.depth<=1)break;
        actor776_count=0;
        for(unsigned i=0;i<MAX_ENTITIES;i++)if(entities.script_table[i]==776){
            actor776_seen=1;actor776_count++;
        }
        /* The final frame and entity END run in the same script tick, so
         * inspect actual native VRAM rather than a transient var1 value. */
        if(actor776_seen && art_size>=288+8+2*1792)
            for(unsigned frame=0;frame<2;frame++)
                if(!memcmp(&ppu.vram[0xf800],expected_art+288+8+frame*1792,1792))animation_frame_mask|=1u<<frame;
        unsigned parent=1,top_for_loop=g_mode_stack.depth-1;
        /* EVENT776 ends after playing the image without YIELD_TO_TEXT. Source
         * WAIT_FOR_ACTIONSCRIPT therefore intentionally remains pending. Its
         * following pause/goto loop is a fallback after debugger skip only. */
        if(letter_started && actor776_seen && !actor776_count && waits==3 &&
            g_mode_stack.mode[parent]==GAME_MODE_DISPLAY_TEXT &&
            g_mode_stack.state[parent].display_text.reader.ptr_off==loop_offset &&
            g_mode_stack.mode[top_for_loop]==GAME_MODE_ACTIONSCRIPT_WAIT &&
            g_mode_stack.state[top_for_loop].actionscript_wait.phase==1 && !ert.actionscript_state){
            terminal_delays++;
            if(terminal_delays>=120)break;
        }
'''),
        ('audio_shutdown();return g_mode_stack.depth==1?0:6;', r'''
    unsigned tiles_match=art_size>=288 && !memcmp(&ppu.vram[0xc000],expected_art,288);
    unsigned frame_match=art_size>=288+8+2*1792 && !memcmp(&ppu.vram[0xf800],expected_art+288+8+1792,1792);
    unsigned palette_match=art_size>=296 && ert.palettes[0]==0 && !memcmp(&ert.palettes[1],expected_art+290,6);
    printf("QA_LETTER {\"endingCompleted\":%u,\"letterStarted\":%u,\"knockNpc22\":%u,\"stableTerminalFrames\":%u,\"terminalReader\":%u,\"expectedReader\":%u,\"letterWaits\":%u,\"letterNaturalSignals\":%u,\"actor776Seen\":%u,\"actor776Count\":%u,\"animationFrameMask\":%u,\"tilesMatch\":%u,\"finalFrameMatch\":%u,\"paletteMatch\":%u,\"bg3Y\":%u}\n",ending_completed,letter_started,knock_npc22,terminal_delays,g_mode_stack.state[1].display_text.reader.ptr_off,loop_offset,waits,signals,actor776_seen,actor776_count,animation_frame_mask,tiles_match,frame_match,palette_match,ppu.bg_vofs[2]);
    audio_shutdown();return terminal_delays>=120?0:6;
'''),
    ]
    for old,new in replacements:
        if source.count(old)!=1:raise ValueError('Ending driver dependency changed; review required: '+old[:70])
        source=source.replace(old,new)
    return source


def resolve_original(address,source):
    sys.path.insert(0,str(source.resolve()))
    from ebtools.config import load_dump_doc
    doc=load_dump_doc(source/'earthbound.yml')
    symbols={doc.renameLabels.get(e.name,{}).get(address-0xc00000-e.offset) for e in doc.dumpEntries}
    symbols.discard(None)
    if len(symbols)!=1:raise ValueError('No single known Original text label.')
    symbol=symbols.pop()
    match=re.search(r'#define\s+'+re.escape(symbol)+r'\s+0x([0-9a-fA-F]+)',(source/'src/data/text_refs.h').read_text())
    if not match:raise ValueError('Missing native text label.')
    return int(match[1],16),symbol


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('build','native-source','runtime','assets','scratch','output','project'):p.add_argument('--'+n,type=Path)
    p.add_argument('--original-profile',action='store_true');p.add_argument('--diagnostic',action='store_true')
    p.add_argument('--combine-existing',type=Path,nargs='+')
    a=p.parse_args()
    if a.combine_existing:
        cases=[json.loads(f.read_text()) for f in a.combine_existing]
        if len(cases)!=2 or {r['profile'] for r in cases}!={'Original','Redux'}:raise ValueError('Both profiles required.')
        if len({json.dumps(r['runtimeSha256'],sort_keys=True) for r in cases})!=1:raise ValueError('Different frozen runtimes.')
        passed=all(r['allPassed'] for r in cases)
        report={'format':'redux-complete-final-letter-review-v1','Passed':passed,'allPassed':passed,
            'sourceRevision':frozen.PIN,'executedCases':sum(r['executedCases'] for r in cases),
            'executedAssertions':sum(r['executedAssertions'] for r in cases),'skippedCases':sum(r['skippedCases'] for r in cases),
            'runtimeSha256':cases[0]['runtimeSha256'],'toolSha256':frozen.digest(Path(__file__)),
            'bootstrapDependencySha256':frozen.digest(Path(ending.__file__)),'cases':cases,
            'nativeDefectFound':False,'limits':cases[0]['limits']}
        a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:report[k] for k in ('allPassed','executedCases','executedAssertions','skippedCases')},indent=2))
        if not passed:raise SystemExit(1)
        return
    if any(getattr(a,n.replace('-','_')) is None for n in ('build','native-source','runtime','assets','scratch','output','project')):
        raise ValueError('All execution paths required.')
    pin=subprocess.check_output(['git','-C',str(a.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=frozen.PIN:raise ValueError('Unreviewed source revision.')
    if a.scratch.exists():raise ValueError('Fresh scratch required.')
    a.scratch.mkdir(parents=True);session=a.scratch/'session';session.mkdir()
    (session/'input.replay').write_text(''.join(f'{i} {"80" if i%2==0 else "0"}\n' for i in range(120000)),encoding='ascii')
    pack=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h')[2]
    sys.path.insert(0,str(a.native_source.resolve()))
    from ebtools.hallz import decompress
    animation_key=next(k for k in pack if k.endswith('graphics/animations/the_end.anim.lzhal'))
    art=decompress(pack[animation_key]);(session/'theend.bin').write_bytes(art)
    frozen.DRIVER=driver();exe,evidence=frozen.private_build(a)
    raw=(0xc755c4,0xc9c85d,0xc9c98a)
    entries=[resolve_original(n,a.native_source) if a.original_profile else (n,None) for n in raw]
    run=subprocess.run([str(exe),str(a.assets.resolve()),str(session.resolve()),str(int(a.original_profile)),'0',*[f'{n:X}' for n,_ in entries]],
        cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=180)
    (a.scratch/'native.stdout.log').write_bytes(run.stdout);(a.scratch/'native.stderr.log').write_bytes(run.stderr)
    rows={}
    for line in run.stdout.decode(errors='replace').splitlines():
        for name in ('ENDING','LETTER'):
            if line.startswith('QA_'+name+' '):rows[name]=json.loads(line[len(name)+4:])
    e=rows.get('ENDING',{});l=rows.get('LETTER',{});errors=[]
    destinations=pack['data/teleport_destination_table.bin']
    import struct
    x,y,*_=struct.unpack_from('<HHBBH',destinations,81*8)
    flags=[11,97,209,467,468,469,472,473,476,513,530,749,750,763,775]+([805] if a.original_profile else [781,805])
    expectations={'ENDING':{'castSeen':1,'creditsSeen':1,'choiceSeen':1,'choiceResult':1,'photoMask':0,
        'partyCount':1,'partyMember':1,'leader':[x*8,y*8],'flags':flags},
        'LETTER':{'endingCompleted':1,'letterStarted':1,'knockNpc22':1,'stableTerminalFrames':120,
            'letterWaits':3,'letterNaturalSignals':2,'actor776Seen':1,'actor776Count':0,'animationFrameMask':3,
            'tilesMatch':1,'finalFrameMatch':1,'paletteMatch':1,'bg3Y':65535}}
    for name,expect in expectations.items():
        for field,v in expect.items():
            if rows.get(name,{}).get(field)!=v:errors.append({'scope':name,'field':field,'actual':rows.get(name,{}).get(field),'expected':v})
    if l.get('terminalReader')!=l.get('expectedReader') or not l:errors.append({'field':'terminalReader','actual':l})
    warnings=[s for s in run.stderr.decode(errors='replace').splitlines() if re.search(r'\b(?:WARN|ERROR|FATAL|STALL|HANG)\b',s)]
    passed=run.returncode==0 and not errors and not warnings
    report={'format':'redux-ending-letter-qa-v1','allPassed':passed,'sourceRevision':pin,
        'profile':'Original' if a.original_profile else 'Redux','nativeExit':run.returncode,
        'runtimeSha256':{n:frozen.digest(a.runtime/n) for n in ('player.exe','observer.exe')},
        'packSha256':frozen.digest(a.assets),'privateBuild':evidence,'sourceEntries':[f'{n:X}' for n in raw],
        'nativeEntries':[{'entry':f'{n:X}','symbol':s} for n,s in entries],
        'expected':expectations,'actual':rows,'errors':errors,'nativeWarnings':warnings,
        'executedCases':int(bool(l)),'executedAssertions':sum(map(len,expectations.values()))+1 if l else 0,'skippedCases':int(not bool(l)),
        'animationOracle':{'assetSha256':__import__('hashlib').sha256(pack[animation_key]).hexdigest(),
            'decompressedSha256':__import__('hashlib').sha256(art).hexdigest(),'tileBytes':288,'frameBytes':1792,'frameIndex':1,
            'method':'Independently decompressed the actual profile pack; final native VRAM tiles/frame and palette compare without publishing asset bytes.'},
        'sourceReferences':[
            'Project/ccscript/data/data_58.ccs:545 C9C85D entire final letter, real movement wait, final flags, animation775 and776 waits.',
            'Project/ccscript/data/data_58.ccs:589 C9C98A fallback pause1/goto loop follows the terminal wait; its entry address bounds the preceding reader.',
            'Project/ccscript/data/data_57.ccs:576 C9B4B8 camera/freeze/wait helper completes naturally.',
            'native-source/asm/data/events/scripts/039.asm knock entity yields;775 oval sequence yields;776 THE END sequence6 then despawns without YIELD_TO_TEXT.',
            'native-source/asm/text/wait_for_actionscript.asm clears signal and waits for YIELD; opcode00/deallocate does not produce a signal. Ordinary THE END remains intentionally parked.',
            'native-source/asm/data/animation_sequence_pointers.asm USA THE END metadata288 tilebytes,2frames,8delay.',
            'native-source/asm/misc/load_animation_sequence_frame.asm and display_animation_sequence_frame.asm prescribe VRAM tiles/palette/frame layout.'
        ],
        'pinnedSourceFiles':{s:frozen.digest(a.project/s) for s in ('ccscript/data/data_31.ccs','ccscript/data/data_57.ccs','ccscript/data/data_58.ccs','map_sprites.yml')},
        'nativeReferenceFiles':{s:frozen.digest(a.native_source/s) for s in ('src/entity/callroutine.c','src/game/display_text.c','src/game/display_text_cc.c','asm/data/events/scripts/039.asm','asm/data/events/scripts/775.asm','asm/data/events/scripts/776.asm','asm/data/events/C33C1D.asm','asm/text/wait_for_actionscript.asm','asm/overworld/actionscript/script/00.asm','asm/overworld/entity/deallocate_entity_sprite.asm','asm/data/animation_sequence_pointers.asm','asm/misc/load_animation_sequence_frame.asm','asm/misc/display_animation_sequence_frame.asm')},
        'runtimeSourceQualification':'Frozen v6 library/platform execute unchanged. Current reviewed display_text_cc.c includes later dev16 CC1D21 serialized RNG change not executed here; privateBuild hashes are authoritative.',
        'limits':['Home story/party context is prepared and actual Mom question/Yes ending runs first; preceding full playthrough is not covered.',
            'Only downstairs arrival7776,344 is prepared between transactions; walking downstairs/knock interaction dispatch is not covered.',
            'Final letter starts at its first source command and uses real camera, freeze, text, movement/animation waits and terminal wait.',
            'Intentional source terminal wait is observed for120 native frames after animation776 despawns; no forced pop/completion or debugger skip.',
            'VRAM/palette state comparison covers final THE END image; audible audio and every transition-frame visual/timing parity remain unverified.',
            'Player platform/library executes; observer paired hash is provenance only.']}
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('allPassed','nativeExit','executedCases','errors')},indent=2))
    if not passed and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
