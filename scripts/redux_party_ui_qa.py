# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise native Redux party UI through isolated production battle modes.

This prepares scratch-only state-format-16 checkpoints. The second scripted
battle is inserted into a completed battle's ordinary overworld mode stack;
the production scripted-entry, combat and cleanup handlers remain unchanged.
No owner saves, ROM, asset pack or audio data are modified.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

from check_jev_observer_parity import latest, local_scratch, sections
from redux_recovery_qa import write_state


def layout(native, compiler, generated, directory):
    source = directory/'party-ui-layout.c'
    source.write_text(r'''#include <stdio.h>
#include <stddef.h>
#include "game/window.h"
#include "game/battle.h"
#include "game/game_state.h"
#include "game/overworld.h"
#include "core/mode_stack.h"
#define F(T,N) printf("\"" #T "." #N "\":%zu,",offsetof(T,N))
int main(void) {
 printf("{");
 F(WindowSystemState,bg2_buffer); F(WindowSystemState,battle_menu_current_character_id);
 F(WindowSystemState,hppp_window_buffer);
 F(BattleState,battle_mode_flag); F(BattleState,hp_pp_box_blink_duration);
 F(BattleState,hp_pp_box_blink_target);
 F(OverworldState,redraw_all_windows);
 F(GameState,auto_fight_enable);
 F(ModeStack,depth); F(ModeStack,mode); F(ModeStack,state);
 F(BattleScriptedState,battle_group); F(CharStruct,current_hp_fraction);
 F(CharStruct,current_hp); F(CharStruct,current_hp_target);
 F(CharStruct,current_pp_fraction); F(CharStruct,current_pp); F(CharStruct,current_pp_target);
 printf("\"modeStateSize\":%zu,\"scriptedMode\":%u,\"overworldMode\":%u,\"hpppCenter\":%u,\"charSize\":%zu}",
 sizeof(ModeState),GAME_MODE_BATTLE_SCRIPTED,GAME_MODE_OVERWORLD,HPPP_CENTER_TILE,sizeof(CharStruct));
 return 0;
}
''', encoding='utf-8')
    executable=directory/'party-ui-layout.exe'
    result=subprocess.run([str(compiler),'-std=c2x','-DEB_VIEWPORT_WIDTH=512','-DEB_VIEWPORT_HEIGHT=256',
                           '-I',str(native/'src'),'-I',str(generated),str(source),'-o',str(executable)],
                          capture_output=True,timeout=45)
    if result.returncode: raise RuntimeError(result.stderr.decode(errors='replace'))
    return json.loads(subprocess.check_output([str(executable)],timeout=10))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native-exe','assets','native-source','compiler','scratch'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--expect-fixed',action='store_true')
    p.add_argument('--original-assets',type=Path)
    p.add_argument('--generated-dir',type=Path,default=Path(__file__).resolve().parents[1]/'build/companion/game_lib/generated')
    a=p.parse_args()
    exe,pak,native,compiler=[x.resolve() for x in (a.native_exe,a.assets,a.native_source,a.compiler)]
    sys.path.insert(0,str(native/'src/vendor/tamp'))
    import tamp
    scratch=local_scratch(a.scratch)
    if scratch.exists(): raise ValueError('Use a fresh isolated diagnostic directory.')
    scratch.mkdir(parents=True)
    offsets=layout(native,compiler,a.generated_dir.resolve(),scratch)
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    records=[]

    def run(name,frame=140,actions=(),source=None,mutate=None,fixture=False,asset=None,held=()):
        directory=scratch/name;directory.mkdir()
        if source:
            shutil.copytree(source/'saves',directory/'saves')
            if mutate:
                state=latest(directory);blobs=sections(state,tamp);mutate(blobs)
                write_state(state,blobs,tamp)
        config=directory/'fixture.ini'
        config.write_text('companion=1\nfullscreen=0\nwidth=1280\nheight=720\nvolume=0\nfast_forward_multiplier=16\n',encoding='utf-8')
        replay=directory/'input.replay'
        inputs={f:mask for t,mask in actions for f,mask in ((t,mask),(t+2,0))}
        for start,end,mask in held: inputs[start]=mask;inputs[end]=0
        replay.write_text('\n'.join(f'{f} {mask:04X}' for f,mask in sorted(inputs.items())),encoding='utf-8')
        command=[str(exe),'--assets',str(asset or pak),'--session-dir',str(directory),'--save',str(directory/'fixture.srm'),
                 '--config',str(config),'--allow-redux-development','--skip-intro','--windowed','--fast-forward',
                 '--input-script',str(replay),'--frames',str(frame+180),'--capture-state',str(frame),'--dump-frame',str(frame+5)]
        command+=['--redux-battle-fixture','1'] if fixture else ['--load-state']
        result=subprocess.run(command,env=env,capture_output=True,timeout=55)
        log=(result.stdout+result.stderr).decode(errors='replace')
        (directory/'replay.log').write_text(log,encoding='utf-8')
        if result.returncode or 'savestate: wrote slot' not in log or re.search(r'FATAL|unimplemented|unknown opcode|unknown bank|ERROR',log,re.I):
            raise RuntimeError(name+': '+log[-2000:])
        return directory,sections(latest(directory),tamp),log

    def details(blobs):
        ui=blobs[8];sp=blobs[47];mode=blobs[21];bt=blobs[6]
        header=offsets['WindowSystemState.bg2_buffer'];count=4
        x=offsets['hpppCenter']-(count*7)//2
        selected=struct.unpack_from('<h',ui,offsets['WindowSystemState.battle_menu_current_character_id'])[0]
        rows=[]
        for char in range(count):
            # Each window's top-left border tile is 0x2004, including status palette bits.
            rows.append([r for r in range(17,21) if struct.unpack_from('<H',ui,header+r*64+(x+char*7)*2)[0]&0x3ff==4])
        depth=mode[offsets['ModeStack.depth']]
        return {'selected':selected,'headerRows':rows,'spriteActive':sp[10],'spriteVictory':sp[11],
                'spriteTargets':sp[8],'spriteVisible':sp[9],
                'damageBlinkDuration':struct.unpack_from('<H',bt,offsets['BattleState.hp_pp_box_blink_duration'])[0],
                'autoFight':blobs[2][offsets['GameState.auto_fight_enable']],
                'battleActive':struct.unpack_from('<H',bt,offsets['BattleState.battle_mode_flag'])[0],
                'modes':list(mode[offsets['ModeStack.mode']:offsets['ModeStack.mode']+depth])}

    intro,b,_=run('first-intro',frame=500,fixture=True)
    ness,b,_=run('ness-selected',actions=((10,0x20),),source=intro)
    before=details(b);records.append({'case':'ness-selection','actual':before})
    expected=[[19]]*4
    if a.expect_fixed and (before['selected']!=0 or before['headerRows']!=expected):
        raise AssertionError('Redux boxes still move with selection: '+str(before))
    paula,b,_=run('paula-selected',actions=((10,0x100),(30,0x400),(70,0x20)),source=ness)
    after=details(b);records.append({'case':'paula-selection','actual':after})
    if a.expect_fixed and (after['selected']!=1 or after['headerRows']!=expected):
        raise AssertionError('Second selected box/previous box disagrees: '+str(after))

    def roller(blobs):
        for char in range(4):
            base=char*offsets['charSize']
            for name,val in (('current_hp_fraction',1),('current_hp',500),('current_hp_target',400),
                             ('current_pp_fraction',1),('current_pp',150),('current_pp_target',100)):
                struct.pack_into('<H',blobs[3],base+offsets['CharStruct.'+name],val)
    rolled,b,_=run('rolling-digits',frame=25,source=paula,mutate=roller)
    ui=b[8];x=offsets['hpppCenter']-14
    meter_rows=[]
    for char in range(4):
        hp=ui[offsets['WindowSystemState.hppp_window_buffer']+char*24:offsets['WindowSystemState.hppp_window_buffer']+char*24+6]
        matches=[r for r in (21,22) if ui[offsets['WindowSystemState.bg2_buffer']+r*64+(x+char*7+3)*2:
                                            offsets['WindowSystemState.bg2_buffer']+r*64+(x+char*7+3)*2+6]==hp]
        meter_rows.append(matches)
    records.append({'case':'rolling-digit-row','hpDigitRows':meter_rows,'actual':details(b)})
    if a.expect_fixed and meter_rows!=[[22]]*4: raise AssertionError('Rolling HP digits use raised rows: '+str(meter_rows))

    def blink(blobs):
        struct.pack_into('<H',blobs[6],offsets['BattleState.hp_pp_box_blink_duration'],21)
        struct.pack_into('<H',blobs[6],offsets['BattleState.hp_pp_box_blink_target'],0)
    _,b,_=run('damage-blink',frame=4,source=ness,mutate=blink)
    blinked=details(b);records.append({'case':'damage-blink-off-phase','actual':blinked})
    if not (blinked['damageBlinkDuration']//3)&1: raise AssertionError('Blink sample must be in the actual off phase.')
    if a.expect_fixed and blinked['headerRows'][0]!=[19]: raise AssertionError('Redux damage still undraws the box.')

    auto,b,_=run('auto-indicator',frame=70,source=ness,actions=((10,0x100),(30,0x100),(50,0x80)))
    pattern=struct.pack('<4H',0x3A69,0x3A6A,0x3A6B,0x3A6C)
    def auto_positions(blobs):
        tiles=blobs[8][offsets['WindowSystemState.bg2_buffer']:offsets['WindowSystemState.bg2_buffer']+0x800]
        return [[i//64,(i%64)//2] for i in range(0,len(tiles)-7,2) if tiles[i:i+8]==pattern]
    positions=auto_positions(b);records.append({'case':'auto-indicator-render','positions':positions})
    if a.expect_fixed and positions!=[[10,26]]: raise AssertionError('AUTO marker was not relocated: '+str(positions))
    # The current battle line must reach its prompt before a fresh confirm
    # edge can advance it. Keep B held across that edge so the *next* real
    # battle_push_text_ex call executes the source's auto-fight cancellation.
    _,b,_=run('auto-cancel',frame=450,source=auto,
              held=((210,230,0x8000),(230,232,0x8080),(232,451,0x8000)))
    positions=auto_positions(b);actual=details(b)
    records.append({'case':'auto-indicator-clear','positions':positions,'actual':actual})
    if positions or actual['autoFight']: raise AssertionError('Cancelled AUTO marker remains: '+str(positions))

    # Use the real menu to set Auto Fight, then ordinary confirm presses through victory.
    actions=[(10,0x100),(30,0x100)]+[(t,0x80) for t in range(50,2200,30)]
    completed,b,log=run('first-completed',frame=2250,actions=actions,source=ness)
    done=details(b);records.append({'case':'first-battle-completed','actual':done})
    if done['battleActive'] or done['modes']!=[offsets['overworldMode']]:
        raise AssertionError('First ordinary combat did not return to roaming: '+str(done))

    def second(blobs):
        mode=blobs[21]
        if mode[offsets['ModeStack.depth']]!=1: raise AssertionError('Completed first battle not at ordinary root.')
        mode[offsets['ModeStack.depth']]=2
        mode[offsets['ModeStack.mode']+1]=offsets['scriptedMode']
        start=offsets['ModeStack.state']+offsets['modeStateSize']
        mode[start:start+offsets['modeStateSize']]=bytes(offsets['modeStateSize'])
        struct.pack_into('<H',mode,start+offsets['BattleScriptedState.battle_group'],1)
    entry,b,_=run('second-intro',frame=500,source=completed,mutate=second)
    _,b,_=run('second-ness-selected',actions=((10,0x20),),source=entry)
    repeated=details(b);records.append({'case':'second-production-battle-entry','actual':repeated})
    if repeated['spriteVictory'] or repeated['spriteTargets']!=1:
        raise AssertionError('Victory state leaked into the next production battle: '+str(repeated))

    # Explicitly seed the preceding victory's state at the same valid root to
    # test initialization without depending on which overworld fade ran last.
    def stale_second(blobs):
        second(blobs)
        blobs[47][:]=struct.pack('<4h4B',152,152,152,152,15,15,1,1)
    entry,b,_=run('stale-victory-second-intro',frame=500,source=completed,mutate=stale_second)
    _,b,_=run('stale-victory-second-selected',actions=((10,0x20),),source=entry)
    stale=details(b);records.append({'case':'prepared-stale-victory-entry','actual':stale,'preparedState':True})
    if a.expect_fixed and (stale['spriteVictory'] or stale['spriteTargets']!=1):
        raise AssertionError('Explicit lifecycle reset not effective through entry: '+str(stale))

    if a.original_assets:
        original=a.original_assets.resolve()
        # Re-enter from the completed root so scene initialization allocates
        # and draws Original windows; a loaded Redux menu's existing tilemap
        # alone cannot prove an Original draw path.
        def original_second(blobs):
            second(blobs)
            # Profiles normally have independent saves. This cross-pack QA
            # prepares an empty BG2 buffer so old Redux AUTO tiles retained
            # in the completed root cannot count as new Original rendering.
            start=offsets['WindowSystemState.bg2_buffer']
            blobs[8][start:start+0x800]=bytes(0x800)
        original_intro,b,_=run('original-intro',frame=500,source=completed,mutate=original_second,asset=original)
        original_ness,b,_=run('original-ness-selection',source=original_intro,asset=original,actions=((10,0x20),))
        item=details(b);records.append({'case':'original-ness-selection','actual':item})
        if item['headerRows']!=[[18],[19],[19],[19]]: raise AssertionError('Original raised selection changed.')
        _,b,_=run('original-damage-blink',frame=4,source=original_ness,mutate=blink,asset=original)
        item=details(b);records.append({'case':'original-damage-blink-off-phase','actual':item})
        if not (item['damageBlinkDuration']//3)&1 or item['headerRows'][0]:
            raise AssertionError('Original off-phase no longer undraws the damaged box: '+str(item))
        _,b,_=run('original-auto-indicator',frame=70,source=original_ness,asset=original,
                   actions=((10,0x100),(30,0x100),(50,0x80)))
        positions=auto_positions(b);records.append({'case':'original-auto-indicator','positions':positions})
        if positions!=[[17,26]]: raise AssertionError('Original AUTO location changed: '+str(positions))

    record={'format':'redux-native-party-ui-qa-v1','nativeExeSha256':hashlib.sha256(exe.read_bytes()).hexdigest(),
            'packSha256':hashlib.sha256(pak.read_bytes()).hexdigest(),'fixedExpectationsEnforced':a.expect_fixed,
            'rows':records,'limits':['Prepared four-member combat, real production entry/menu/cleanup modes; not an entire story playthrough.',
              'Stale victory is deliberately prepared to test hardening; it is not evidence of a naturally reproduced user bug.']}
    if a.original_assets:
        record['originalPackSha256']=hashlib.sha256(a.original_assets.read_bytes()).hexdigest()
        record['limits'].append('Original UI regressions prepare new production battle entry from a scratch completed Redux root with BG2 cleared before entry; independent Original story progress is not claimed.')
    (scratch/'results.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record,indent=2))


if __name__=='__main__': main()
