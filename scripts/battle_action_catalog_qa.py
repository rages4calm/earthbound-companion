# SPDX-License-Identifier: GPL-3.0-or-later
"""Execute isolated native battle handlers with assembly-backed semantic checks.

The private driver links the existing production library and copied platform
objects. It renames only a copied main entry point, then uses normal startup.
It runs the real dispatcher, resumable action/calculation/text children and
native RNG. It does not replace production handlers, fake their results, or
write player saves. Catalog membership is reported separately from semantics.
"""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess

from build_maternalbound_pack import read_pack

PIN = '897d00833f4a08a0a92f106abf631629a6a6a041'

DRIVER = r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "core/mode_stack.h"
#include "core/memory.h"
#include "core/math.h"
#include "game/battle.h"
#include "game/battle_internal.h"
#include "game/game_state.h"
#include "game/display_text.h"
#include "game/window.h"
#include "game/text.h"
#include "game/overworld.h"
#include "game/maternalbound.h"
#include "game/inventory.h"
#include "entity/entity.h"
#include "platform/platform.h"
#include "data/assets.h"
#include "include/pad.h"

extern int eb_platform_main(int argc, char **argv);

static unsigned pump(void) {
    unsigned steps=0;
    while (g_mode_stack.depth>1 && ++steps<30000) {
        /* Advance real prompts without SDL polling: this is a handler fixture,
         * not a physical controller/render/audio/full-turn test. */
        core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=PAD_A;
        dt.instant_printing=1;
        unsigned top=g_mode_stack.depth-1;
        StepResult r=mode_dispatch_step((GameMode)g_mode_stack.mode[top],&g_mode_stack.state[top]);
        if(r.kind==STEP_PUSH) mode_push(r.push_mode,r.push_init);
        else if(r.kind==STEP_POP) mode_pop(r.pop_result);
        else { core.frame_counter++; core.nmi_count++; }
    }
    return steps;
}

int main(int argc,char **argv) {
    if(argc!=4) return 2;
    char save[4096]; snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
    char *boot[]={"battle-action-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,
        "--allow-redux-development","--headless","--frames","1","--redux-battle-fixture","0"};
    if(eb_platform_main((int)(sizeof(boot)/sizeof(boot[0])),boot)!=0 || !maternalbound_enabled()) return 3;
    /* The one-frame startup intentionally requested quit. Clear that through
     * the platform's real input lifecycle before any exit-tail host yield. */
    platform_max_frames=0;platform_input_shutdown();
    if(!platform_input_init()) return 7;
    game_set_fast_forward(true);
    /* BTL_BEGIN normally binds this ROM table after the battle-entry fade;
     * the bounded one-frame bootstrap has not reached that phase yet. */
    npc_ai_table=ASSET_DATA(ASSET_DATA_NPC_AI_TABLE_BIN);
    const unsigned variance_values[]={80,180,320,512,540,720,999,2000,10000};
    for(unsigned vi=0;vi<sizeof(variance_values)/sizeof(variance_values[0]);vi++)
    for(unsigned seed=1;seed<=64;seed++) {
        uint32_t s=seed*0x9e3779b9u;unsigned rolls[2];rng_seed(s);
        rolls[0]=rng_next_byte();rolls[1]=rng_next_byte();
        rng_seed(s);unsigned a25=battle_25pct_variance((uint16_t)variance_values[vi]);
        rng_seed(s);unsigned a50=battle_50pct_variance((uint16_t)variance_values[vi]);
        printf("QA_VARIANCE {\"value\":%u,\"seed\":%u,\"rolls\":[%u,%u],\"pct25\":%u,\"pct50\":%u}\n",
            variance_values[vi],seed,rolls[0],rolls[1],a25,a50);
    }
    FILE *input=fopen(argv[3],"r"); if(!input) return 4;
    char line[4096];
    while(fgets(line,sizeof(line),input)) {
        unsigned v[40],n=0;
        for(char *part=strtok(line," \t\r\n");part && n<40;part=strtok(NULL," \t\r\n")) v[n++]=(unsigned)strtoul(part,NULL,10);
        if(n!=32) return 5;
        /* id, action, seed, target-enemy (+1, zero=player), raw-init,
         * hp, pp, maxhp, maxpp, aff[7], res[6], luck, npc, offense, defense,
         * speed, guts, shieldhp, guarding, item, attacker-enemy (+1). */
        memset(&bt,0,sizeof(bt)); memset(&g_mode_stack,0,sizeof(g_mode_stack));
        g_mode_stack.depth=1; g_mode_stack.mode[0]=GAME_MODE_NONE;
        memset(party_characters,0,sizeof(CharStruct)*TOTAL_PARTY_COUNT);
        for(unsigned p=0;p<4;p++) {
            game_state.party_order[p]=(uint8_t)p+1;game_state.party_members[p]=(uint8_t)p+1;
            CharStruct *c=&party_characters[p];
            c->level=30;c->max_hp=c->current_hp=c->current_hp_target=999;
            c->max_pp=c->current_pp=c->current_pp_target=300;
            c->base_offense=c->offense=80;c->base_defense=c->defense=50;
            c->base_speed=c->speed=20;c->base_guts=c->guts=0;c->base_luck=c->luck=20;
            c->base_vitality=c->vitality=20;c->base_iq=c->iq=20;
            battle_init_player_stats((uint16_t)p+1,&bt.battlers_table[p]);
        }
        game_state.party_order[4]=game_state.party_order[5]=0;
        game_state.party_members[4]=game_state.party_members[5]=0;
        game_state.party_npc_1=game_state.party_npc_2=0;
        game_state.party_npc_1_hp=game_state.party_npc_2_hp=0;
        game_state.party_count=game_state.player_controlled_party_count=4;
        game_state.current_party_members=15;
        bt.enemies_in_battle=1;bt.enemies_in_battle_ids[0]=(uint16_t)(v[3]?v[3]-1:7);
        battle_init_enemy_stats(&bt.battlers_table[FIRST_ENEMY_INDEX],bt.enemies_in_battle_ids[0]);
        unsigned ti=v[3]?FIRST_ENEMY_INDEX:0;
        bt.current_target=(uint16_t)(ti*sizeof(Battler));
        bt.current_attacker=(uint16_t)((v[31] && v[4]!=2?FIRST_ENEMY_INDEX+1:1)*sizeof(Battler));
        if(v[31] && v[4]!=2) battle_init_enemy_stats(&bt.battlers_table[FIRST_ENEMY_INDEX+1],(uint16_t)v[31]-1);
        Battler *t=&bt.battlers_table[ti],*a=battler_from_offset(bt.current_attacker);
        if(!v[4]) {
            t->hp=t->hp_target=(uint16_t)v[5];t->pp=t->pp_target=(uint16_t)v[6];
            t->hp_max=(uint16_t)v[7];t->pp_max=(uint16_t)v[8];
            for(unsigned i=0;i<7;i++) t->afflictions[i]=(uint8_t)v[9+i];
            t->fire_resist=(uint8_t)v[16];t->freeze_resist=(uint8_t)v[17];
            t->flash_resist=(uint8_t)v[18];t->paralysis_resist=(uint8_t)v[19];
            t->hypnosis_resist=(uint8_t)v[20];t->brainshock_resist=(uint8_t)v[21];
            t->luck=(uint16_t)v[22];t->npc_id=(uint8_t)v[23];
            t->offense=(uint16_t)v[24];t->defense=(uint16_t)v[25];
            t->speed=(uint16_t)v[26];t->guts=(uint16_t)v[27];
            t->shield_hp=(uint8_t)v[28];t->guarding=(uint8_t)v[29];
            t->base_offense=80;t->base_defense=50;t->base_speed=20;t->base_guts=0;t->base_luck=20;
        }
        if(!v[3] && !v[4]) {
            CharStruct *c=&party_characters[0];
            c->max_hp=t->hp_max;c->current_hp=c->current_hp_target=t->hp_target;
            c->max_pp=t->pp_max;c->current_pp=c->current_pp_target=t->pp_target;
            memcpy(c->afflictions,t->afflictions,7);
        }
        a->current_action=(uint16_t)v[1];a->current_action_argument=(uint8_t)v[30];
        a->action_item_slot=1;
        if(a->ally_or_enemy==0) {
            if(v[4]!=2) party_characters[a->id-1].items[0]=(uint8_t)v[30];
            a->hp=a->hp_target=500;a->pp=a->pp_target=200;
            CharStruct *c=&party_characters[a->id-1];
            c->current_hp=c->current_hp_target=500;c->current_pp=c->current_pp_target=200;
        }
        ow.battle_mode=0xffff;bt.battle_mode_flag=1;
        window_system_init();init_used_bg2_tile_map();text_setup_bg3();
        text_upload_font_tiles();text_load_window_gfx();text_load_flavour_palette(0);
        create_window(WINDOW_TEXT_BATTLE);set_window_focus(WINDOW_TEXT_BATTLE);
        unsigned rolls[8];rng_seed(v[2]);for(unsigned i=0;i<8;i++) rolls[i]=rng_next_byte();rng_seed(v[2]);
        unsigned steps=0;
        if(v[4]==2) {
            entity_system_init();
            /* This enters the real dropped-present text/CC give-item path,
             * EXP tail and battle exit, not an isolated inventory helper. */
            if(v[22]) (void)give_item_to_character(1,(uint16_t)v[22]);
            if(v[31]) add_char_to_party((uint16_t)v[31]);
            if(v[23]) for(unsigned p=0;p<(v[23]==2?3:4);p++)
                for(unsigned i=0;i<14;i++) if(!party_characters[p].items[i]) party_characters[p].items[i]=88;
            for(unsigned p=4;p<6;p++) if(game_state.party_members[p]) {
                unsigned member=game_state.party_members[p];
                battle_init_enemy_stats(&bt.battlers_table[p],npc_ai_table[member*2+1]);
                bt.battlers_table[p].npc_id=(uint8_t)member;bt.battlers_table[p].ally_or_enemy=0;
            }
            bt.item_dropped=(uint16_t)v[30];bt.battle_exp_scratch=0;
            ModeState battle={0};battle.battle.phase=BTL_VICTORY_DROP;
            mode_push(GAME_MODE_BATTLE,&battle);steps=pump();
        } else if(v[1]!=65535) {
            ModeState action={0};
            uint32_t callback=v[1]>65535?v[1]:battle_action_table[v[1]].battle_function_pointer;
            if(battle_action_dispatch(callback,&action)) {
                mode_push(GAME_MODE_BATTLE_ACTION,&action);steps=pump();
            }
        }
        printf("QA {\"id\":%u,\"steps\":%u,\"depth\":%u,\"firstRoll\":%u,\"hp\":%u,\"pp\":%u,\"maxhp\":%u,\"maxpp\":%u,\"offense\":%u,\"defense\":%u,\"speed\":%u,\"guts\":%u,\"luck\":%u,\"shieldhp\":%u,\"npc\":%u,\"consciousness\":%u,\"aff\":[",
            v[0],steps,g_mode_stack.depth,rolls[0],t->hp_target,t->pp_target,t->hp_max,t->pp_max,
            t->offense,t->defense,t->speed,t->guts,t->luck,t->shield_hp,t->npc_id,t->consciousness);
        for(unsigned i=0;i<7;i++) printf("%s%u",i?",":"",t->afflictions[i]);
        unsigned loot=0;for(unsigned p=0;p<4;p++) for(unsigned i=0;i<14;i++) if(v[30] && party_characters[p].items[i]==v[30]) loot++;
        printf("],\"res\":[%u,%u,%u,%u,%u,%u],\"attackerHp\":%u,\"attackerPp\":%u,\"rolls\":[%u,%u,%u,%u],\"battleExp\":%u,\"battleMoney\":%u,\"lootQuantity\":%u,\"postBattleFlag\":%u,\"partyCount\":%u,\"npc1\":%u,\"npc2\":%u,\"party\":[%u,%u,%u,%u,%u,%u]}\n",
            t->fire_resist,t->freeze_resist,t->flash_resist,t->paralysis_resist,t->hypnosis_resist,t->brainshock_resist,
            a->hp_target,a->pp_target,rolls[0],rolls[1],rolls[2],rolls[3],(unsigned)bt.battle_exp_scratch,bt.battle_money_scratch,
            loot,bt.battle_mode_flag,game_state.party_count,game_state.party_npc_1,game_state.party_npc_2,
            game_state.party_members[0],game_state.party_members[1],game_state.party_members[2],game_state.party_members[3],game_state.party_members[4],game_state.party_members[5]);
        fflush(stdout);
        if(steps>=30000 || g_mode_stack.depth!=1) return 6;
    }
    fclose(input);return 0;
}
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def variance_reference(value,rolls,shift):
    """65816 caller retains the 16-bit TRUNCATE_16_TO_8 return value."""
    delta=min((rolls[0]-128,rolls[1]-128),key=abs)
    adjustment=(value*abs(delta)//256)>>shift
    return value+(-adjustment if delta<0 else adjustment)


def variance_review(rows):
    expected={(value,seed) for value in (80,180,320,512,540,720,999,2000,10000) for seed in range(1,65)}
    if len(rows)!=len(expected) or {(r['value'],r['seed']) for r in rows}!=expected:
        raise ValueError('Missing/duplicate/truncated native variance corpus.')
    failures=[]
    for row in rows:
        for name,shift in (('pct25',1),('pct50',0)):
            expected=variance_reference(row['value'],row['rolls'],shift)
            if row[name]!=expected:
                failures.append({'value':row['value'],'seed':row['seed'],'variant':name,
                    'native':row[name],'reference':expected,'rolls':row['rolls']})
    return {'executedNativeCases':len(rows)*2,'mismatchCount':len(failures),'firstMismatches':failures[:8],
        'passed':not failures,'reference':'Reviewed original 16-bit multiply/shift ABI; separate original-machine oracle recorded below.'}


def semantic_expectations(test,result):
    oracle=test['oracle'];values=test['values'];kind=oracle.get('kind')
    if not kind:return oracle
    rolls=result['rolls']
    if kind=='status':
        aff=oracle['before'].copy();group=oracle['group'];status=oracle['status']
        if rolls[0]<oracle['probability'] and (not aff[group] or aff[group]>status):aff[group]=status
        return {'aff':aff}
    if kind=='elemental':
        damage=variance_reference(oracle['power'],rolls[:2],1)
        if oracle['resist']<255:damage=damage*oracle['resist']//256
        damage=max(damage,1)
        return {'hp':values[5] if oracle['immuneBoss'] else max(values[5]-damage,0)}
    if kind=='revive':
        success=oracle['tier']==3 or rolls[0]<192
        return {'hp':values[7]//4 if success and oracle['tier']==2 else values[7] if success else 0,
            'aff':[0 if success else 1,0,0,0,0,0,0]}
    if kind=='lifeup':return {'hp':min(values[5]+variance_reference(oracle['power'],rolls[:2],1),values[7])}
    if kind=='magnet':
        drain=min(values[6],(rolls[0]*4//256)+(rolls[1]*4//256)+2)
        return {'pp':values[6]-drain,'attackerPp':200+drain}
    if kind=='hp-sucker':
        drain=variance_reference(values[7],rolls[1:3],0)//8
        return {'hp':values[5]-drain,'attackerHp':min(500+drain,999)}
    raise ValueError('Unevaluated semantic oracle: '+str(kind))


def run_variance_oracle(args,rows):
    if not args.rom and not args.oracle:return {'executed':False,'reason':'No owner ROM/reference runner supplied.'}
    if not args.rom or not args.oracle:raise ValueError('--rom and --oracle must be supplied together.')
    rom=args.rom.read_bytes()
    if len(rom)!=0x300000 or hashlib.sha1(rom).hexdigest()!='d67a8ef36ef616bc39306aa1b486e1bd3047815a':
        raise ValueError('Oracle requires exact clean unheadered EarthBound USA ROM.')
    # Address proof: untouched original Lifeup Alpha calls common C29AB8,
    # which calls variance C26AFD; HP-sucker C2A46B calls C26A44.
    if rom[0x29ab8:0x29abe]!=bytes.fromhex('c231aa20fd6a') or bytes.fromhex('20446a') not in rom[0x2a46b:0x2a4f7]:
        raise ValueError('Original routine-address fingerprint changed.')
    samples=args.scratch/'variance-oracle-samples.tsv'
    # Native CPU mode,16-bit A/X/Y,D1000,S1FFF,DBR7E. Only ephemeral
    # unused caller memory is replaced; original variance/RNG/multiply intact.
    stub=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
    entry=0xc2ff00+len(stub)
    stub+=bytes.fromhex('af02717ef009af00717e20446a8007af00717e20fd6a8f00707e7b8f08707e3b8f0a707e')
    finish=0xc2ff00+len(stub);stub+=bytes([0x4c,entry&255,(entry>>8)&255])
    cases=[(row['value'],row['seed'],variant,row['pct25' if variant==0 else 'pct50']) for row in rows for variant in (0,1)]
    lua=['local output=assert(io.open('+json.dumps(samples.resolve().as_posix())+',"wb"))','local cases={']
    lua+=['{'+','.join(map(str,row[:3]))+'},' for row in cases]
    lua+=['}','local mem=emu.memType.snesWorkRam',
        'local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256),mem) end',
        'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end','local index=0',
        'emu.addMemoryCallback(function()',
        ' index=index+1;local c=assert(cases[index],"ran beyond corpus")',
        ' local seed=(c[2]*2654435769)%4294967296',
        ' w16(0x24,seed%65536);w16(0x26,math.floor(seed/65536))',
        ' w16(0x7100,c[1]);w16(0x7102,c[3])',
        f'end,emu.callbackType.exec,{entry})','emu.addMemoryCallback(function()',
        ' assert(r16(0x7008)==0x1000,"direct page corrupted");assert(r16(0x700a)==0x1fff,"stack corrupted")',
        ' output:write(string.format("%d,%d\\n",index,r16(0x7000)))',
        ' if index==#cases then output:flush();output:close();emu.log("VARIANCE_CORPUS_COMPLETE");emu.breakExecution() end',
        f'end,emu.callbackType.exec,{finish})']
    script=args.scratch/'variance.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
    cmd=[str(args.oracle.resolve()),str(args.rom.resolve()),'--home',str((args.scratch/'oracle-home').resolve()),
        '--frames','1000','--timeout','60','--lua-timeout','10','--lua-allow-io','--lua',str(script.resolve()),
        '--write-memory','SnesPrgRom:0x2ff00:'+stub.hex(),'--set-pc','0xc2ff00','--cpu','Snes']
    run=subprocess.run(cmd,capture_output=True,timeout=70)
    (args.scratch/'oracle.jsonl').write_bytes(run.stdout);(args.scratch/'oracle.stderr').write_bytes(run.stderr)
    logs=[json.loads(line) for line in run.stdout.decode().splitlines()]
    end=logs[-1] if logs else {}
    if run.returncode or end.get('event')!='summary' or not end.get('ok') or end.get('reason')!='debugger_break':
        raise RuntimeError('Original-machine oracle did not complete; inspect isolated logs.')
    events=[r for r in logs if r.get('event')=='lua_log']
    if any(r['error_count'] for r in events) or not any('VARIANCE_CORPUS_COMPLETE' in r['text'] for r in events):
        raise RuntimeError('Original-machine oracle had Lua errors/incomplete corpus.')
    pairs=[tuple(map(int,line.split(','))) for line in samples.read_text().splitlines()]
    if [i for i,_ in pairs]!=list(range(1,len(cases)+1)):raise RuntimeError('Oracle samples incomplete.')
    diffs=[{'case':i,'value':cases[i-1][0],'seed':cases[i-1][1],
        'variant':'pct25' if cases[i-1][2]==0 else 'pct50','native':cases[i-1][3],'originalMachine':value}
        for i,value in pairs if cases[i-1][3]!=value]
    formula_diffs=[]
    for i,value in pairs:
        row=rows[(i-1)//2];expected=variance_reference(row['value'],row['rolls'],1 if (i-1)%2==0 else 0)
        if value!=expected:formula_diffs.append(i)
    if args.rom.read_bytes()!=rom:raise RuntimeError('Owner ROM changed during read-only oracle run.')
    return {'executed':True,'executedCases':len(cases),'originalMachineCodeExecuted':True,
        'originalCalls':['C26AFD','C26A44'],'originalRngAndMultiplyExecuted':True,
        'ownerRomUnchanged':True,'stackAndDirectPageCanariesPassed':True,
        'romSha256':digest(args.rom),'referenceRunnerSha256':digest(args.oracle),
        'nativeMismatchCount':len(diffs),'firstMismatches':diffs[:8],
        'assemblyFormulaMismatchCount':len(formula_diffs),'passed':not diffs and not formula_diffs,
        'limits':['Original two helpers execute in prepared CPU context; this is not full-game emulation equivalence.',
            'Reference runner and owner ROM are local development inputs; neither is a player dependency or release payload.']}


def private_build(args):
    build=args.build.resolve();scratch=args.scratch.resolve();native=args.native_source.resolve()
    runtime_hashes={digest(args.runtime/name) for name in ('player.exe','observer.exe')}
    if digest(build/'earthbound.exe') not in runtime_hashes:
        raise ValueError('Shared production build differs from the frozen runtime; use the corresponding build.')
    source=scratch/'battle_action_driver.c';source.write_text(DRIVER,encoding='utf-8')
    commands=json.loads((build/'compile_commands.json').read_text())
    entry=next(row for row in commands if row['file'].endswith('/port/unix/main.c'))
    if '"' in entry['command'] or "'" in entry['command']:
        raise ValueError('Review quoted compiler flags before using this private builder.')
    flags=entry['command'].split();obj=scratch/'battle_action_driver.c.obj'
    flags[flags.index('-o')+1]=str(obj);flags[flags.index('-c')+1]=str(source)
    def run(command,name):
        p=subprocess.run(command,cwd=build,capture_output=True,timeout=120)
        (scratch/name).write_bytes(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError(name+': '+p.stderr.decode(errors='replace'))
    run(flags,'compile.log')
    ninja=(build/'build.ninja').read_text()
    match=re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_Release (.*?)\n(.*?)(?=\n\n)',ninja,re.M|re.S)
    objects=match[1].split(' | ',1)[0].split()
    libraries=re.search(r'^  LINK_LIBRARIES = (.*)$',match[2],re.M)[1].split()
    main_object=next(token for token in objects if token.replace('\\','/').endswith('/main.c.obj'))
    copied=scratch/'platform_main.c.obj';shutil.copy2(build/main_object,copied)
    objcopy=Path(flags[0]).parent/'objcopy.exe'
    run([str(objcopy),'--redefine-sym','main=eb_platform_main',str(copied)],'rename.log')
    objects=[str(copied) if token==main_object else str(build/token) for token in objects]
    exe=scratch/'battle-action-driver.exe'
    run([flags[0],'-O3','-DNDEBUG',str(obj),*objects,'-o',str(exe),
         '-Wl,--major-image-version,0,--minor-image-version,0',*libraries],'link.log')
    shutil.copy2(args.runtime/'SDL2.dll',scratch/'SDL2.dll')
    return exe,{'driverSourceSha256':digest(source),'executableSha256':digest(exe),
        'productionExecutableSha256':digest(build/'earthbound.exe'),
        'productionLibrarySha256':digest(build/'game_lib/libearthbound_game.a'),
        'platformMainObjectSha256':digest(build/main_object),
        'sharedBuildModified':False,'sharedSourceModified':False,
        'method':'Copied platform main renamed with objcopy; private driver linked to unchanged production native library.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('build','native-source','assets','runtime','scratch','output','project'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--rom',type=Path)
    parser.add_argument('--oracle',type=Path)
    parser.add_argument('--previous-driver-log',type=Path)
    args=parser.parse_args()
    if args.scratch.exists():raise ValueError('Use a fresh isolated scratch directory.')
    pin=subprocess.check_output(['git','-C',str(args.project.parent),'rev-parse','HEAD'],text=True).strip()
    if pin!=PIN:raise ValueError('Repeat source review against the new Redux revision.')
    args.scratch.mkdir(parents=True);session=args.scratch/'session';session.mkdir()
    exe,build_evidence=private_build(args)
    _,_,assets=read_pack(args.assets,args.native_source/'src/data/runtime_generated/asset_ids.h')
    action_data=assets['data/battle_action_table.bin']
    records=[struct.unpack('<BBBBII',action_data[p:p+12]) for p in range(0,len(action_data),12)]
    action_by_function={row[5]:i for i,row in reversed(list(enumerate(records)))}
    tests=[]
    dispatch_source=(args.native_source/'src/game/battle_actions.c').read_text()
    callback_names={int(addr,16):step if step!='NULL' else pure
        for addr,pure,step in re.findall(r'\{ 0x([0-9A-F]+), (\w+), (\w+) \}',dispatch_source)}
    def add(name,function,oracle,category='misc',**overrides):
        values=[len(tests),action_by_function.get(function,function) if function else 65535,0x9e3779b9,8,0,
            2000,200,2000,300,0,0,0,0,0,0,0,255,255,255,255,255,255,20,0,80,50,20,0,0,0,0,0]
        for index,value in overrides.items():values[int(index)]=value
        tests.append({'name':name,'function':function,'values':values,'oracle':oracle,'category':category})
    add('neutralize resets modified combat stats and shield',0xC29051,
        {'offense':80,'defense':50,'speed':20,'guts':0,'luck':20,'shieldhp':0,'aff':[0]*7},
        category='stat-neutralization',
        **{'24':180,'25':150,'26':70,'27':30,'22':60,'15':4,'28':3})

    enemy_data=assets['data/enemy_configuration_table.bin']
    footer=enemy_data.find(b'MRDXAI01')
    if footer<0 or footer%94:raise ValueError('Reviewed enemy-table trailer changed.')
    enemy_count=footer//94
    damage_modifiers=(255,179,102,13);status_modifiers=(255,128,26,0)
    for enemy in range(enemy_count):
        data=enemy_data[enemy*94:(enemy+1)*94]
        if any(level>3 for level in data[63:68]):raise ValueError('Review unsupported resistance level.')
        aff=[0]*7;shieldhp=0
        initial=data[89]
        if initial in (1,2,3,4):aff[6]={1:2,2:1,3:4,4:3}[initial];shieldhp=3
        elif initial==5:aff[2]=1
        elif initial==6:aff[4]=4
        elif initial==7:aff[3]=1
        elif initial!=0:raise ValueError('Review unsupported initial status.')
        res=[damage_modifiers[data[63]],damage_modifiers[data[64]],status_modifiers[data[65]],
            status_modifiers[data[66]],status_modifiers[data[67]],status_modifiers[3-data[67]]]
        expected={'hp':struct.unpack_from('<H',data,33)[0],'pp':struct.unpack_from('<H',data,35)[0],
            'offense':struct.unpack_from('<H',data,56)[0]&255,'defense':struct.unpack_from('<H',data,58)[0]&255,
            'speed':data[60],'guts':data[61],'luck':data[62],'aff':aff,'shieldhp':shieldhp,'res':res,'npc':0,'consciousness':1}
        add(f'enemy {enemy} native stats/resistance/initial-status initialization',0,expected,
            category='enemy-initialization',**{'3':enemy+1,'4':1})
        for function,res_index,group,status in ((0xC29FFE,3,0,3),(0xC29F06,4,2,1),(0xC2A056,5,3,1)):
            add(f'enemy {enemy} status callback {function:06X} uses actual configured vulnerability',function,
                {'kind':'status','group':group,'status':status,'probability':res[res_index],'before':aff},
                category='enemy-configured-status',**{'3':enemy+1,'4':1})
        # Giygas phase2 redirects damage to a random player; target HP alone is
        # not a sufficient oracle for that branch, so it is explicitly excluded.
        if enemy!=218:
            for function,power,res_index in ((0xC295AB,80,0),(0xC29647,180,1)):
                add(f'enemy {enemy} elemental callback {function:06X} resistance/boss immunity',function,
                    {'kind':'elemental','power':power,'resist':res[res_index],
                     'immuneBoss':enemy in (93,192,219,221,229)},category='enemy-configured-elemental',
                    **{'3':enemy+1,'16':res[0],'17':res[1]})

    for function,index,group,status in ((0xC29FFE,19,0,3),(0xC29F06,20,2,1),(0xC2A056,21,3,1)):
        for probability in (0,26,128,255):
            for seed in range(1,33):
                add(f'status {function:06X} probability {probability} seed {seed}',function,
                    {'kind':'status','group':group,'status':status,'probability':probability,'before':[0]*7},
                    category='status-chance',**{str(index):probability,'2':(seed*0x9e3779b9)&0xffffffff})
        for npc in (1,9,16):
            add(f'status {function:06X} NPC {npc} rejected',function,{'aff':[0]*7},
                category='status-npc',**{'23':npc})
        for existing in range(1,8 if group==0 else 5 if group==2 else 2):
            aff=[0]*7;aff[group]=existing
            add(f'status {function:06X} priority preserves/replaces {existing}',function,
                {'kind':'status','group':group,'status':status,'probability':255,'before':aff},
                category='status-priority',**{str(9+group):existing})

    for family,functions,powers,res_index in (
        ('fire',(0xC295AB,0xC295B4,0xC295BD,0xC295C6),(80,160,240,320),16),
        ('freeze',(0xC29647,0xC29650,0xC29659,0xC29662),(180,360,540,720),17)):
        for function,power in zip(functions,powers):
            for resist in damage_modifiers:
                for guard in (0,1):
                    for seed in range(1,9):
                        add(f'{family} power {power} resist {resist} guard {guard} seed {seed}',function,
                            {'kind':'elemental','power':power,'resist':resist,'immuneBoss':False},
                            category='elemental-tiers',**{str(res_index):resist,'29':guard,'2':(seed*0x9e3779b9)&0xffffffff})
            add(f'{family} power {power} PSI shield nullifies',function,{'hp':2000,'shieldhp':2,'aff':[0,0,0,0,0,0,2]},
                category='psi-shield-nullification',**{'15':2,'28':3})
        if family=='freeze':
            add('Freeze NPC check prevents damage',functions[0],{'hp':2000,'aff':[0]*7},
                category='elemental-npc',**{'23':9})

    # Higher Healing levels fall back through lower-tier cures; a single cast
    # cures its first applicable status, rather than clearing unrelated slots.
    status_inputs=[(0,0),(0,2),(0,3),(0,4),(0,5),(0,6),(0,7),(1,1),(1,2),(2,1),(2,2),(2,3),(3,1)]
    for tier,function in enumerate((0xC29AEA,0xC29B7A,0xC29C2C,0xC29CB8)):
        for group,status in status_inputs:
            aff=[0]*7;aff[group]=status;expected=aff.copy()
            if (group==0 and (status in (6,7) or tier>=1 and status in (4,5) or tier>=2 and status in (2,3))) or (group==2 and (status==1 or tier>=1 and status==2)) or (group==3 and tier>=1 and status==1):expected[group]=0
            add(f'Healing tier {tier} status {group}/{status}',function,{'aff':expected,'hp':2000},
                category='healing-cascade',**{str(9+group):status})
        if tier>=2:
            for seed in range(1,33):
                add(f'Healing tier {tier} revive seed {seed}',function,
                    {'kind':'revive','tier':tier},category='healing-revive',
                    **{'3':0,'5':0,'7':800,'9':1,'2':(seed*0x9e3779b9)&0xffffffff})

    for function,power in ((0xC29AC6,100),(0xC29ACF,300),(0xC29AD8,10000),(0xC29AE1,400)):
        for seed in range(1,9):
            add(f'Lifeup power {power} seed {seed}',function,{'kind':'lifeup','power':power},
                category='lifeup',**{'3':0,'5':100,'7':999,'2':(seed*0x9e3779b9)&0xffffffff})
        add(f'Lifeup power {power} unconscious cannot recover',function,{'hp':0,'aff':[1,0,0,0,0,0,0]},
            category='lifeup-blocked',**{'3':0,'5':0,'7':999,'9':1})

    for function,shield in ((0xC29D44,4),(0xC29D81,3),(0xC29DBE,2),(0xC29DFB,1)):
        for previous in (0,1,2,3,4):
            for hp in (0,1,3,6,7,8):
                aff=[0]*7;aff[6]=shield
                add(f'shield {shield} replaces/refreshes {previous} strength {hp}',function,
                    {'aff':aff,'shieldhp':min(hp+3,8) if previous==shield else 3},category='shield-application',
                    **{'15':previous,'28':hp})

    for pp in (0,1,5,200):
        for seed in range(1,17):
            add(f'Magnet drains/clamps PP {pp} seed {seed}',0xC29F5E,{'kind':'magnet'},
                category='pp-drain',**{'6':pp,'2':(seed*0x9e3779b9)&0xffffffff})
    for maxhp in (320,720,999,2000):
        for seed in range(1,17):
            add(f'HP-sucker maxHP {maxhp} seed {seed}',0xC2A46B,{'kind':'hp-sucker'},
                category='hp-drain',**{'7':maxhp,'5':maxhp,'22':0,'2':(seed*0x9e3779b9)&0xffffffff})

    items=assets['data/item_configuration_table.bin']
    teddy_items=[i for i in range(len(items)//39) if items[i*39+25]==4]
    if len(teddy_items)!=2:raise ValueError('Review changed Teddy Bear item catalog.')
    for item in teddy_items:
        for prior in (0,*teddy_items):
            for npc in (0,9,10,11):
                for full in (0,2):
                    accepted=full!=1
                    candidates=([prior] if prior else [])+([item] if accepted else [])
                    best=max(candidates,key=lambda i:items[i*39+33]) if candidates else 0
                    party=[1,2,3,4]+([npc] if npc else [])+([items[best*39+31]] if best else [])
                    party=sorted(party);party+=[0]*(6-len(party))
                    npcs=[x for x in party if x>4]+[0,0]
                    add(f'Teddy {item} reward/exit prior {prior} NPC {npc} inventory {full}',0,
                        {'lootQuantity':int(accepted)+int(prior==item),'postBattleFlag':0,
                         'party':party,'partyCount':len([x for x in party if x]),'npc1':npcs[0],'npc2':npcs[1]},
                        category='teddy-reward-exit',**{'4':2,'22':prior,'23':full,'30':item,'31':npc})

    input_file=args.scratch/'cases.tsv'
    input_file.write_text('\n'.join(' '.join(map(str,t['values'])) for t in tests)+'\n')
    p=subprocess.run([str(exe.resolve()),str(args.assets.resolve()),str(session.resolve()),str(input_file.resolve())],
        cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=180)
    (args.scratch/'native.log').write_bytes(p.stdout+p.stderr)
    lines=p.stdout.decode(errors='replace').splitlines()
    results={r['id']:r for r in (json.loads(line[3:]) for line in lines if line.startswith('QA '))}
    variance_rows=[json.loads(line[12:]) for line in lines if line.startswith('QA_VARIANCE ')]
    variance=variance_review(variance_rows)
    machine=run_variance_oracle(args,variance_rows)
    previous=None
    if args.previous_driver_log:
        old=[json.loads(line[12:]) for line in args.previous_driver_log.read_text().splitlines() if line.startswith('QA_VARIANCE ')]
        previous=variance_review(old)
        previous['logSha256']=digest(args.previous_driver_log)
        if previous['mismatchCount']==0:raise RuntimeError('Prior adapter mismatch was not retained.')
    rows=[]
    for index,test in enumerate(tests):
        actual=results.get(index);errors=[]
        if not actual:errors.append('No native result')
        else:
            for key,wanted in semantic_expectations(test,actual).items():
                if actual[key]!=wanted:errors.append(f'{key}: got {actual[key]} expected {wanted}')
            if actual['depth']!=1 or actual['steps']>=30000:errors.append('Native continuation did not complete')
        rows.append({'name':test['name'],'category':test['category'],
            'actionId':test['values'][1] if test['values'][1]<65535 else None,
            'function':f"{test['function']:06X}" if test['function'] else None,
            'invocation':'real reward text/CC give-item and battle exit' if test['values'][4]==2 else 'packed-action callback' if test['values'][1]<65535 else 'nested native callback' if test['function'] else 'native enemy initializer',
            'passed':not errors,'errors':errors})
    source_references=[]
    for path in ('include/macros.asm','include/config.asm','asm/system/math/truncate_16_to_8.asm',
        'asm/battle/25_percent_variance.asm','asm/battle/50_percent_variance.asm',
        'asm/battle/init_enemy_stats.asm','asm/battle/calc_psi_damage_modifiers.asm','asm/battle/calc_psi_resistance_modifiers.asm',
        'asm/battle/inflict_status.asm','asm/battle/success_255.asm','asm/battle/actions/paralysis_alpha.asm',
        'asm/battle/actions/hypnosis_alpha.asm','asm/battle/actions/brainshock_alpha.asm',
        'asm/battle/actions/psi_fire_common.asm','asm/battle/actions/psi_freeze_common.asm',
        'asm/battle/calc_damage_reduction.asm','asm/battle/calc_damage.asm','asm/battle/recover_hp.asm',
        'asm/battle/actions/healing_alpha.asm','asm/battle/actions/healing_beta.asm',
        'asm/battle/actions/healing_gamma.asm','asm/battle/actions/healing_omega.asm',
        'asm/battle/actions/lifeup_common.asm','asm/battle/actions/shield_common.asm',
        'asm/battle/actions/magnet_alpha.asm','asm/battle/actions/hp_sucker.asm','asm/battle/actions/neutralize.asm',
        'asm/battle/update_teddy_bear_party.asm','src/game/battle.c','src/game/battle_calc.c',
        'src/game/battle_actions.c','src/game/inventory.c','src/game/display_text_cc.c'):
        source=args.native_source/path
        source_references.append({'path':path,'fileSha256':digest(source)})
    redux_references=[]
    for path in ('ccscript/main.ccs','ccscript/redux/m3sprites.ccs','ccscript/redux/lucky_sandwich_revamp.ccs'):
        source=args.project/path
        original=subprocess.check_output(['git','-C',str(args.project.parent),'show','HEAD:Project/'+path])
        if source.read_bytes().replace(b'\r\n',b'\n')!=original.replace(b'\r\n',b'\n'):raise ValueError('Reviewed Redux source differs from pin: '+path)
        redux_references.append({'path':path,'fileSha256':digest(source)})
    tested_functions={t['function'] for t in tests if t['function']}
    active_functions={r[5] for r in records}
    unevaluated=[{'function':f'{callback:06X}','nativeHandler':callback_names.get(callback,'pure/native callback'),
        'actionIds':[i for i,r in enumerate(records) if r[5]==callback]}
        for callback in sorted(active_functions-tested_functions)]
    counts=collections.Counter(t['category'] for t in tests)
    report={'schemaVersion':1,'reduxRevision':pin,'assetsSha256':digest(args.assets),
        'runtimeSha256':{name:digest(args.runtime/name) for name in ('player.exe','observer.exe')},
        'privateBuild':build_evidence,'nativeExitCode':p.returncode,'cases':rows,
        'sourceReferences':source_references,'pinnedReduxReferences':redux_references,
        'semanticCoverage':{'executedCases':len(tests),'categories':dict(counts),
            'enemyRecordsInitializedAndResistanceMapped':enemy_count,
            'packedActionRecords':len(records),'uniqueActiveCallbacks':len(active_functions),
            'uniqueActiveCallbacksWithTargetedSemanticCases':len(active_functions&tested_functions),
            'nestedCallbacksWithTargetedSemanticCases':len(tested_functions-active_functions),
            'unevaluatedActiveCallbacksInThisTool':unevaluated},
        'variance':variance,'originalMachineVariance':machine,'previousVarianceRegression':previous,
        'allPassed':p.returncode==0 and variance['passed'] and (not machine['executed'] or machine['passed']) and len(results)==len(tests) and all(row['passed'] for row in rows),
        'teddyRewardAdaptation':{'source':'Pinned m3sprites C18B80 defers UPDATE_TEDDY_BEAR_PARTY during reward text; native inventory updates immediately.',
            'verified':'Real dropped-present text invokes the native CC give-item dispatcher; battle EXP/exit continuations complete. Both bear items, existing stronger/weaker bear, Bubble Monkey/Dungeon Man/Flying Man NPC, and allocation to fourth character when first three inventories are full have checked final loot/party/NPC state.',
            'limits':'No claim of identical ROM assembly timing, ordinary visual transitions, post-exit overworld walking or all-six-slot NPC permutations. Entirely full inventory opens an interactive disposal flow needing a different input fixture; that UI branch remains unevaluated here.'},
        'limits':['Prepared production callbacks and real mode/text/calculation continuations, not all ordinary battles or a full playthrough.',
            'The private driver links the player build matching the frozen player executable. Observer behavior is checked in the separate six-module audit, not independently for every semantic matrix row.',
            'Most handler fixtures bypass action selection, PP payment, whole-turn targeting/initiative, item consumption and enemy AI; separate menu/reward QA is required.',
            'Some functions share multiple table rows: one callback test does not validate every packed targeting/type/description variant.',
            'Callback membership and missing-handler inventory are metadata, not semantic validation.',
            'Original machine-code oracle covers exactly two variance helpers; other assertions derive from reviewed source/data and execute native handlers.',
            'Elemental cases check HP targets/boss immunities; Freeze solidify distribution, reflected PSI, Giygas phase2 redirection, KO/final attacks, player Guts and shield break ordering remain separate.',
            'No asserted audio/image correctness, all transitions, cold save phases, full randomizer seed progression or every source module.',
            'No owner ROM, game data, dialogue bytes, screenshots or player save appears in this public report.'],
        'fullConversionVerified':False,'fullPlaythroughVerified':False}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cases':len(rows),'passed':sum(row['passed'] for row in rows),'nativeExitCode':p.returncode,'allPassed':report['allPassed']}))
    if not report['allPassed']:raise SystemExit(1)


if __name__=='__main__':main()
