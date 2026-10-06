# SPDX-License-Identifier: GPL-3.0-or-later
"""Isolated cold-versus-bound native battle table dependency reproducers.

Links the immutable player library without changing production source, ROMs,
assets or owner saves. Cold tests leave the lazy tables null as they are before
the first BTL_BEGIN; warm controls bind the exact packed asset table. Tests use
real NPC addition, KO continuation and BTL_PREP continuation.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

import battle_action_catalog_qa as helper
from build_maternalbound_pack import read_pack

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
extern int eb_platform_main(int argc,char **argv);
extern const uint8_t *consolation_item_table;

int main(int argc,char **argv) {
    if(argc!=4)return 2;
    char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
    char *boot[]={"cold-battle-dependency-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,
        "--allow-redux-development","--headless","--frames","1","--redux-battle-fixture","0"};
    if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot)!=0 || !maternalbound_enabled())return 3;
    platform_max_frames=0;platform_input_shutdown();
    if(!platform_input_init())return 7;
    printf("COLD_BOOT {\"npcTableBound\":%u,\"consolationTableBound\":%u,\"enemyConfigTableBound\":%u}\n",npc_ai_table!=NULL,consolation_item_table!=NULL,enemy_config_table!=NULL);
    FILE *input=fopen(argv[3],"r");if(!input)return 4;
    unsigned index,kind,warm,member,seed;
    while(fscanf(input,"%u %u %u %u %u",&index,&kind,&warm,&member,&seed)==5) {
        entity_system_init();
        memset(&bt,0,sizeof(bt));memset(&game_state,0,sizeof(game_state));
        memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;
        memset(party_characters,0,sizeof(CharStruct)*TOTAL_PARTY_COUNT);
        npc_ai_table=warm?ASSET_DATA(ASSET_DATA_NPC_AI_TABLE_BIN):NULL;
        consolation_item_table=warm?ASSET_DATA(ASSET_DATA_CONSOLATION_ITEM_TABLE_BIN):NULL;
        for(unsigned p=0;p<4;p++) {
            game_state.party_order[p]=game_state.party_members[p]=p+1;
            CharStruct *c=&party_characters[p];c->current_hp=c->current_hp_target=c->max_hp=999;
            c->base_offense=c->offense=80;c->base_defense=c->defense=50;
            battle_init_player_stats(p+1,&bt.battlers_table[p]);
        }
        game_state.party_count=game_state.player_controlled_party_count=4;
        game_state.current_party_members=15;
        window_system_init();init_used_bg2_tile_map();text_setup_bg3();
        text_upload_font_tiles();text_load_window_gfx();text_load_flavour_palette(0);
        create_window(WINDOW_TEXT_BATTLE);set_window_focus(WINDOW_TEXT_BATTLE);
        rng_seed(seed);unsigned rolls[32];for(unsigned r=0;r<32;r++)rolls[r]=rng_next_byte();rng_seed(seed);
        unsigned id=0,npc=0,hp=0,conscious=0,kindResult=0,phase=0;
        if(kind==0) {
            add_char_to_party(member);
            npc=game_state.party_npc_1;hp=game_state.party_npc_1_hp;
        } else if(kind==1) {
            /* Valid serialized KO continuation after the dying Teddy's text:
             * game_state now tracks the available replacement, battler still
             * carries the dying bear until the actual pc11 replacement stage.
             */
            Battler *b=&bt.battlers_table[4];
            const uint8_t *fixture_npc_data=ASSET_DATA(ASSET_DATA_NPC_AI_TABLE_BIN);
            b->id=fixture_npc_data[PARTY_MEMBER_TEDDY_BEAR*2+1];
            b->npc_id=PARTY_MEMBER_TEDDY_BEAR;b->row=0;b->ally_or_enemy=0;
            b->consciousness=1;b->afflictions[0]=STATUS_0_UNCONSCIOUS;
            game_state.party_npc_1=member;game_state.party_npc_1_hp=321;
            ModeState state={0};battle_ko_make_init(&state,4*sizeof(Battler));state.battle_ko.pc=11;
            StepResult result=mode_step_battle_ko(&state);
            id=b->id;npc=b->npc_id;hp=b->hp_target;conscious=b->consciousness;kindResult=result.kind;
        } else if(kind==2) {
            bt.enemies_in_battle=1;bt.enemies_in_battle_ids[0]=member;
            battle_init_enemy_stats(&bt.battlers_table[FIRST_ENEMY_INDEX],member);
            ow.battle_mode=0xffff;bt.battle_mode_flag=1;
            ModeState state={0};state.battle.phase=BTL_PREP;
            StepResult result=mode_step_battle(&state);
            id=bt.item_dropped;phase=state.battle.phase;kindResult=result.kind;
        } else {
            /* Normal single-target enemy Bash with a restored NPC party. */
            const uint8_t *fixture_npc_data=ASSET_DATA(ASSET_DATA_NPC_AI_TABLE_BIN);
            game_state.party_members[4]=game_state.party_order[4]=member;
            game_state.party_count=5;game_state.party_npc_1=member;
            battle_init_enemy_stats(&bt.battlers_table[4],fixture_npc_data[member*2+1]);
            bt.battlers_table[4].ally_or_enemy=0;bt.battlers_table[4].npc_id=member;
            battle_init_enemy_stats(&bt.battlers_table[8],7);
            bt.battlers_table[8].current_action=4;
            bt.current_attacker=8*sizeof(Battler);
            choose_target(bt.current_attacker);id=bt.battlers_table[8].current_target;
        }
        printf("COLD_CASE {\"index\":%u,\"kind\":%u,\"warm\":%u,\"member\":%u,\"seed\":%u,\"id\":%u,\"npc\":%u,\"hp\":%u,\"conscious\":%u,\"stepKind\":%u,\"phase\":%u,\"rolls\":[",
            index,kind,warm,member,seed,id,npc,hp,conscious,kindResult,phase);
        for(unsigned r=0;r<32;r++)printf("%s%u",r?",":"",rolls[r]);printf("]}\n");
        fflush(stdout);
    }
    fclose(input);return 0;
}
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('build','native-source','assets','runtime','scratch','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--original',action='store_true',help='Require an original EarthBound pack instead of Redux.')
    parser.add_argument('--diagnostic',action='store_true',help='Record known pre-fix cold failures without failing the process; bound controls must still pass.')
    args=parser.parse_args()
    if args.scratch.exists():raise ValueError('Fresh scratch required.')
    args.scratch.mkdir(parents=True);session=args.scratch/'session';session.mkdir()
    helper.DRIVER=(DRIVER.replace(' || !maternalbound_enabled()',' || maternalbound_enabled()')
        .replace(',"--redux-battle-fixture","0"',',"--inspect-shuffle"')) if args.original else DRIVER
    executable,build=helper.private_build(args)
    _,_,assets=read_pack(args.assets,args.native_source/'src/data/runtime_generated/asset_ids.h')
    npc=assets['data/npc_ai_table.bin'];enemy=assets['data/enemy_configuration_table.bin']
    consolation=assets['data/consolation_item_table.bin']
    action=assets['data/battle_action_table.bin'][4*12:5*12]
    if action[0]!=0 or action[1]!=1 or int.from_bytes(action[8:12],'little')!=0xC2859F:
        raise ValueError('Review changed ordinary Bash fixture action.')
    tests=[]
    for member in (9,10,11,16,17):
        for kind in (0,1):
            for warm in (0,1):
                tests.append({'kind':kind,'warm':warm,'member':member,'seed':0x9e3779b9})
    for member in (consolation[0],consolation[9]):
        for seed in range(1,33):
            for warm in (0,1):
                tests.append({'kind':2,'warm':warm,'member':member,'seed':seed*0x9e3779b9&0xffffffff})
    for member in (11,16,17):
        for seed in range(1,33):
            for warm in (0,1):
                tests.append({'kind':3,'warm':warm,'member':member,'seed':seed*0x9e3779b9&0xffffffff})
    (args.scratch/'cases.tsv').write_text('\n'.join(' '.join(map(str,(i,t['kind'],t['warm'],t['member'],t['seed']))) for i,t in enumerate(tests))+'\n')
    with (args.scratch/'native.log').open('wb') as log:
        process=subprocess.run([str(executable),str(args.assets.resolve()),str(session.resolve()),str((args.scratch/'cases.tsv').resolve())],
            cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),stdout=log,stderr=subprocess.STDOUT,timeout=60)
    lines=(args.scratch/'native.log').read_text(errors='replace').splitlines()
    boot=next((json.loads(line[10:]) for line in lines if line.startswith('COLD_BOOT ')),None)
    actual={r['index']:r for r in (json.loads(line[10:]) for line in lines if line.startswith('COLD_CASE '))}
    cases=[]
    for i,t in enumerate(tests):
        row=actual.get(i);expected={};errors=[]
        if t['kind']==0:
            cfg=npc[t['member']*2+1]
            expected={'npc':t['member'],'hp':int.from_bytes(enemy[cfg*94+33:cfg*94+35],'little')}
        elif t['kind']==1:
            expected={'id':npc[t['member']*2+1],'npc':t['member'],'hp':321,'conscious':1}
        elif t['kind']==2 and row:
            record=enemy[t['member']*94:(t['member']+1)*94]
            item=record[88];rarity=record[87]
            if rarity<=6 and row['rolls'][1]&((127,63,31,15,7,3,1)[rarity]):item=0
            if not item:
                entry=next(p for p in (0,9) if consolation[p]==t['member'])
                item=consolation[entry+1+row['rolls'][2]*7//256]
            expected={'id':item}
        elif row:
            # Source NPC shortcut precedes the normal valid-PC random loop.
            if row['rolls'][0]&3 and npc[t['member']*2]&2:target=5
            else:target=next((value&7)+1 for value in row['rolls'][1:] if (value&7)<4)
            expected={'id':target}
        if row is None:errors.append('No native result')
        else:
            for key,value in expected.items():
                if row[key]!=value:errors.append(f'{key}: got {row[key]} expected {value}')
        cases.append(dict(t,expected=expected,actual=row,passed=not errors,errors=errors))
    report={'schemaVersion':1,'tool':'cold-battle-dependency-qa','packMode':'original' if args.original else 'maternalbound-redux',
        'runtimeSha256':{n:helper.digest(args.runtime/n) for n in ('player.exe','observer.exe')},
        'assetsSha256':helper.digest(args.assets),'privateBuild':build,'nativeExitCode':process.returncode,'coldBootstrap':boot,
        'cases':cases,'summary':{label:{'cases':sum(t['warm']==value for t in cases),'passed':sum(t['warm']==value and t['passed'] for t in cases)} for label,value in (('cold',0),('boundControl',1))},
        'sourceReferences':[{'path':path,'sha256':helper.digest(args.native_source/path)} for path in (
            'asm/overworld/party/update_npc_party_lineup.asm','asm/battle/ko_target.asm','asm/battle/main_battle_routine.asm',
            'asm/battle/find_targettable_npc.asm','asm/battle/choose_target.asm',
            'src/game/battle.c','src/game/battle_targeting.c') if (args.native_source/path).exists()],
        'limits':['KO test starts at the actual serialized post-text pc11 continuation; it does not exercise preceding inventory destruction or text.',
            'PREP test executes the real drop/consolation selection and stops at its next native child/phase. It does not certify whole encounter entry or rewards.',
            'Cold quickloads past BTL_PREP do not rerun this drop selection; only an entry/PREP checkpoint can hit that missing table.',
            'NPC addition is an actual native helper call after prepared party initialization; owner saves are untouched.',
            'Expected values derive from exact original assembly and real packed tables; this is not independent full original-machine validation.']}
    report['allPassed']=process.returncode==0 and len(actual)==len(tests) and all(row['passed'] for row in cases)
    report['diagnosticMode']=args.diagnostic
    report['reproductionFlags']={name:str(getattr(args,name.replace('-','_'))) for name in ('build','native-source','assets','runtime','scratch','output')}
    report['reproductionFlags'].update(original=args.original,diagnostic=args.diagnostic)
    report['sourceReferenceRole']='Reviewed sources at audit execution; immutable linked library and executable hashes identify the tested build. Source hashes are not a compiled-source provenance claim for older baseline libraries.'
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'nativeExitCode':process.returncode,'coldBootstrap':boot,'summary':report['summary'],'firstFailures':[r for r in cases if not r['passed']][:5]}))
    if process.returncode or len(actual)!=len(tests) or any(not r['passed'] for r in cases if r['warm'] or not args.diagnostic):raise SystemExit(1)


if __name__=='__main__':main()
