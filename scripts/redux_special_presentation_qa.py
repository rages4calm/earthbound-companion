# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared production-mode render checks for special Redux battle scenes.

Only isolated copies under _BuildScratch are written. Mode-stack checkpoints
select actual resumable native action stages; no action result is replaced.
The distinction between staged action tests and complete encounters is kept
in the public report. No ROM, graphics, soundtrack or save data is published.
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

from PIL import Image
from build_maternalbound_pack import read_pack
from check_jev_observer_parity import latest, local_scratch, sections
from redux_recovery_qa import write_state

ROOT=Path(__file__).resolve().parents[1]
PIN='897d00833f4a08a0a92f106abf631629a6a6a041'


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def audit_preload_capacity(assets,profile):
    """Bound every full group, including intentional zero-count summon rows."""
    pointers=assets['data/btl_entry_ptr_table.bin']
    groups=assets['data/enemy_battle_groups_table.bin']
    enemies=assets['data/enemy_configuration_table.bin']
    art=assets['data/battle_sprites_pointers.bin']
    if art.startswith(b'MRBSX001'):
        count,palettes,directory=struct.unpack_from('<HHI',art,8)
        assert directory==16+count*5 and directory+(count+palettes)*8<=len(art)
        table=art[16:directory]
        for index in range(count+palettes):
            offset,size=struct.unpack_from('<II',art,directory+index*8)
            assert directory+(count+palettes)*8<=offset<=len(art) and 0<size<=len(art)-offset
            if index>=count:assert size==32
    else:
        assert len(art)%5==0
        count,palettes,table=len(art)//5,32,art
    rows=[]
    for group in range(len(pointers)//8):
        offset=int.from_bytes(pointers[group*8:group*8+3],'little')-0xD0D52D
        entries=[]
        while True:
            assert 0<=offset<len(groups),(profile,group,'group pointer/terminator')
            if groups[offset]==255:break
            assert offset+3<=len(groups)
            number,enemy=struct.unpack_from('<BH',groups,offset);offset+=3
            assert enemy*94+94<=len(enemies),(profile,group,'enemy record')
            sprite=struct.unpack_from('<H',enemies,enemy*94+28)[0]
            palette=enemies[enemy*94+53]
            assert 0<=sprite<=count and palette<palettes,(profile,group,'art index')
            if sprite:assert 1<=table[(sprite-1)*5+4]<=6,(profile,group,'sprite size')
            entries.append((number,enemy,sprite,palette))
        # This is stricter than distinct sprite count: native allocates per row.
        assert len(entries)<=4,(profile,group,'four-allocation capacity')
        rows.append({'group':group,'fullEntries':len(entries),
                     'nonzeroSpriteEntries':sum(bool(s) for n,e,s,p in entries),
                     'zeroCountEntries':sum(n==0 for n,e,s,p in entries),
                     'zeroSpriteEntries':sum(s==0 for n,e,s,p in entries),
                     'distinctNonzeroSprites':len({s for n,e,s,p in entries if s})})
    return {'profile':profile,'testedGroups':len(rows),'allPassed':True,
            'maximumFullEntries':max(x['fullEntries'] for x in rows),
            'maximumNonzeroSpriteEntries':max(x['nonzeroSpriteEntries'] for x in rows),
            'zeroCountGroups':[x['group'] for x in rows if x['zeroCountEntries']],
            'zeroSpriteGroups':[x['group'] for x in rows if x['zeroSpriteEntries']],
            'groups':rows,
            'sourceReferences':['asm/battle/enemy/setup_battle_enemy_sprites.asm',
                                'src/game/battle.h four-element allocation arrays'],
            'qualification':'Packed table bounds/capacity proof; sprite0 preserves the existing native no-art branch, not a new source-parity claim.'}


def get_layout(native,compiler,generated,output):
    source=output/'layout.c'
    source.write_text(r'''#include <stdio.h>
#include <stddef.h>
#include "core/mode_stack.h"
#include "game/battle.h"
#include "game/window.h"
#include "game/game_state.h"
#include "game/overworld.h"
#include "game/battle_bg.h"
#include "snes/ppu.h"
#define F(T,N) printf("\"" #T "." #N "\":%zu,",offsetof(T,N))
int main(void) {printf("{");
 F(ModeStack,depth);F(ModeStack,mode);F(ModeStack,state);
 F(BattleRoutineState,phase);F(BattleRoutineState,attacker);F(BattleRoutineState,target_i);
 F(BattleActionState,pc);F(BattleActionState,table_index);
 F(LoadBattleSceneState,phase);F(LoadBattleSceneState,group);F(LoadBattleSceneState,music);
 F(BattleState,current_battle_group);F(BattleState,current_attacker);F(BattleState,current_target);
 F(BattleState,giygas_phase);F(BattleState,battle_mode_flag);F(BattleState,battlers_table);
 F(BattleState,letterbox_top_end);F(BattleState,letterbox_bottom_start);F(BattleState,current_layer_config);
 F(WindowSystemState,battle_menu_current_character_id);F(WindowSystemState,bg2_buffer);
 F(OverworldState,render_hppp_windows);F(GameState,character_mode);F(GameState,party_members);
 F(OverworldState,battle_mode);
 F(GameState,party_order);F(GameState,player_controlled_party_members);F(GameState,party_count);
 F(GameState,player_controlled_party_count);F(GameState,current_party_members);
 F(LoadedBGData,target_layer);F(LoadedBGData,bitdepth);F(LoadedBGData,distortion_styles);
 F(LoadedBGData,scrolling_movements);F(LoadedBGData,palette_shifting_style);
 F(LoadedBGData,distortion_ripple_amplitude);F(LoadedBGData,distortion_speed);
 F(PPUState,bgmode);F(PPUState,tm);
 F(PPUState,inidisp);
 F(PPUState,bg_sc);F(PPUState,bg_nba);F(PPUState,bg_viewport_fill);
 F(LoadedBGData,freeze_palette_scrolling);F(LoadedBGData,distortion_type);
 F(LoadedBGData,horizontal_velocity);F(LoadedBGData,vertical_velocity);
 F(LoadedBGData,horizontal_acceleration);F(LoadedBGData,vertical_acceleration);
 printf("\"modeSize\":%zu,\"battlerSize\":%zu,\"actionMode\":%u,\"sceneMode\":%u,\"targetPost\":%u,\"battleMode\":%u,\"battleBegin\":%u,\"displayTextMode\":%u}",
 sizeof(ModeState),sizeof(Battler),GAME_MODE_BATTLE_ACTION,GAME_MODE_LOAD_BATTLE_SCENE,BTL_TARGET_POST,GAME_MODE_BATTLE,BTL_BEGIN,GAME_MODE_DISPLAY_TEXT);
 return 0;}
''',encoding='utf-8')
    exe=output/'layout.exe'
    p=subprocess.run([str(compiler),'-std=c2x','-DEB_VIEWPORT_WIDTH=512','-DEB_VIEWPORT_HEIGHT=256',
        '-I',str(native/'src'),'-I',str(generated),str(source),'-o',str(exe)],capture_output=True,timeout=40)
    if p.returncode: raise RuntimeError(p.stderr.decode(errors='replace'))
    return json.loads(subprocess.check_output([str(exe)],timeout=10))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native-exe','assets','scratch'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--native-source',type=Path,default=ROOT/'native-source')
    p.add_argument('--compiler',type=Path,default=ROOT/'tools/mingw64/bin/gcc.exe')
    p.add_argument('--generated',type=Path,default=ROOT/'build/companion/game_lib/generated')
    p.add_argument('--project',type=Path,default=ROOT/'_BuildScratch/MaternalBound-Redux/Project')
    p.add_argument('--output',type=Path)
    p.add_argument('--original-assets',type=Path)
    p.add_argument('--scene-catalog',action='store_true')
    p.add_argument('--original-controls',action='store_true',help='Run Original warm/cold controls without the full numeric catalog.')
    p.add_argument('--diagnostic',action='store_true',help='Keep a zero exit for intentionally failing frozen baseline evidence.')
    p.add_argument('--dynamic-fixtures',type=Path,
                   help='Run dynamic portrait controls from a completed immutable run with the same binary/content hashes.')
    p.add_argument('--cinematic-fixtures',type=Path,
                   help='Run only the exact C2C3A4 cinematic stage using copied format16 fixtures from a completed review.')
    p.add_argument('--original-rom',type=Path,default=Path(r'E:/Consoles/snes/EarthBound (USA)/EarthBound (USA).sfc'))
    a=p.parse_args();scratch=local_scratch(a.scratch)
    if scratch.exists(): raise ValueError('Use a fresh isolated scratch directory.')
    scratch.mkdir(parents=True)
    native,exe,pak,project=[x.resolve() for x in (a.native_source,a.native_exe,a.assets,a.project)]
    sys.path.insert(0,str(native/'src/vendor/tamp'));import tamp
    offsets=get_layout(native,a.compiler.resolve(),a.generated.resolve(),scratch)
    _,_,assets=read_pack(pak,native/'src/data/runtime_generated/asset_ids.h')
    original_pak=a.original_assets.resolve() if a.original_assets else None
    original_assets=read_pack(original_pak,native/'src/data/runtime_generated/asset_ids.h')[2] if original_pak else None
    capacity=[audit_preload_capacity(assets,'Redux')]
    if original_assets is not None:capacity.append(audit_preload_capacity(original_assets,'Original'))
    action_source=(native/'src/game/battle_actions.c').read_text(encoding='utf-8')
    table=action_source.split('btlact_dispatch_table[]',1)[1].split('};',1)[0]
    callbacks=[int(x,16) for x in re.findall(r'\{ (0x[0-9A-Fa-f]+),',table)]
    if not callbacks:raise ValueError('Review action-dispatch table parsing.')
    revision=subprocess.check_output(['git','-C',str(project.parent),'rev-parse','HEAD'],text=True).strip()
    if revision!=PIN:raise ValueError('Review source revision changed.')
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    observations=[];mismatches=[];checks=[]
    rom=a.original_rom.read_bytes()
    expected_calls={0xC2C75B:0xC1DD41,0xC29302:0xC1DD41,0xC29388:0xC1DC1C,
                    0xC2C3A4:0xC1DD5F,0xC2C544:0xC1DC1C}
    mapped_calls=[]
    for address,target in expected_calls.items():
        data=rom[address-0xC00000:address-0xC00000+4]
        if data!=bytes((0x22,target&255,target>>8&255,target>>16)):
            raise ValueError(f'Original call-site mapping is different at {address:06X}: {data.hex()}')
        symbols={0xC1DC1C:'DISPLAY_IN_BATTLE_TEXT',0xC1DD41:'REDIRECT_HIDE_HPPP_WINDOWS',
                 0xC1DD5F:'CLOSE_ALL_WINDOWS_AND_HIDE_HPPP'}
        mapped_calls.append({'sourceHook':f'{address:06X}','originalJslTarget':f'{target:06X}',
                             'originalRoutine':symbols[target]})

    def check(name,condition,details):
        checks.append({'check':name,'passed':bool(condition),'details':details})
        if not condition: mismatches.append({'case':name,'kind':'assertion','details':details})

    def u16(blobs,section,field):return struct.unpack_from('<H',blobs[section],offsets[field])[0]
    def put16(blobs,section,field,value):struct.pack_into('<H',blobs[section],offsets[field],value)
    def describe(blobs):
        stack=blobs[21];depth=stack[offsets['ModeStack.depth']]
        modes=list(stack[offsets['ModeStack.mode']:offsets['ModeStack.mode']+depth])
        actions=[]
        for i,mode in enumerate(modes):
            start=offsets['ModeStack.state']+i*offsets['modeSize']
            if mode==offsets['actionMode']:
                index=struct.unpack_from('<H',stack,start+offsets['BattleActionState.table_index'])[0]
                actions.append({'callback':f'{callbacks[index]:06X}','pc':stack[start+offsets['BattleActionState.pc']]})
        battlers=[]
        for i in range(4):
            start=offsets['BattleState.battlers_table']+i*offsets['battlerSize']
            battlers.append({'id':struct.unpack_from('<H',blobs[6],start)[0],'conscious':blobs[6][start+12]})
        sp=blobs[47]
        gs=blobs[2]
        bg=[]
        for section in (24,25):
            data=blobs[section]
            bg.append({'targetLayer':data[offsets['LoadedBGData.target_layer']],
              'bitdepth':data[offsets['LoadedBGData.bitdepth']],
              'scrollingMovements':list(data[offsets['LoadedBGData.scrolling_movements']:offsets['LoadedBGData.scrolling_movements']+4]),
              'distortionStyles':list(data[offsets['LoadedBGData.distortion_styles']:offsets['LoadedBGData.distortion_styles']+4])})
            bg[-1]['stateSha256']=hashlib.sha256(data).hexdigest().upper()
        return {'battleGroup':u16(blobs,6,'BattleState.current_battle_group'),
          'giygasPhase':u16(blobs,6,'BattleState.giygas_phase'),'battleActive':u16(blobs,6,'BattleState.battle_mode_flag'),
          'selected':struct.unpack_from('<h',blobs[8],offsets['WindowSystemState.battle_menu_current_character_id'])[0],
          'portraitAnchors':list(struct.unpack_from('<4h',sp)),
          'portraitTargets':sp[8],'portraitVisible':sp[9],'portraitActive':sp[10],'portraitVictory':sp[11],
          'renderHppp':blobs[5][offsets['OverworldState.render_hppp_windows']],
          'partyCount':gs[offsets['GameState.party_count']],
          'controlledPartyCount':gs[offsets['GameState.player_controlled_party_count']],
          'party':list(gs[offsets['GameState.party_members']:offsets['GameState.party_members']+6]),
          'battlers':battlers,'bg':bg,'modes':modes,'actions':actions,
          'ppuMainLayers':blobs[10][offsets['PPUState.tm']],'ppuBgMode':blobs[10][offsets['PPUState.bgmode']],
          'letterboxBounds':[u16(blobs,6,'BattleState.letterbox_top_end'),u16(blobs,6,'BattleState.letterbox_bottom_start')],
          'layerConfig':u16(blobs,6,'BattleState.current_layer_config'),
          'viewportFill':list(blobs[10][offsets['PPUState.bg_viewport_fill']:offsets['PPUState.bg_viewport_fill']+4]),
          'bgMap':list(blobs[10][offsets['PPUState.bg_sc']:offsets['PPUState.bg_sc']+4]),
          'bgTileBase':list(blobs[10][offsets['PPUState.bg_nba']:offsets['PPUState.bg_nba']+2]),
          'distort30fps':struct.unpack_from('<H',blobs[41])[0]}

    def run(name,frame=140,source=None,mutate=None,group=None,actions=(),render=True,asset=None):
        folder=scratch/name;folder.mkdir()
        if source:
            shutil.copytree(source/'saves',folder/'saves')
            if mutate:
                state=latest(folder);blobs=sections(state,tamp);mutate(blobs);write_state(state,blobs,tamp)
        config=folder/'fixture.ini'
        config.write_text('companion=1\nfullscreen=0\nwidth=1280\nheight=720\nvolume=0\nfast_forward_multiplier=16\n',encoding='utf-8')
        replay=folder/'input.replay'
        replay.write_text('\n'.join(f'{f} {mask:04X}' for t,mask in actions for f,mask in ((t,mask),(t+2,0))),encoding='utf-8')
        command=[str(exe),'--assets',str(asset or pak),'--session-dir',str(folder),'--save',str(folder/'fixture.srm'),
            '--config',str(config),'--allow-redux-development','--skip-intro','--input-script',str(replay),
            '--frames',str(frame+(1200 if group is not None else 180 if render else 40)),'--capture-state',str(frame)]
        command+=['--redux-battle-fixture',str(group)] if group is not None else ['--load-state']
        command+=['--windowed','--dump-frame',str(frame+5)] if render else ['--headless','--fast-forward']
        proc=subprocess.run(command,env=env,capture_output=True,timeout=45)
        log=(proc.stdout+proc.stderr).decode(errors='replace');(folder/'runtime.log').write_text(log,encoding='utf-8')
        if proc.returncode or 'savestate: wrote slot' not in log or re.search(r'FATAL|unknown bank|unknown opcode|unimplemented|ERROR',log,re.I):
            raise RuntimeError(name+': '+log[-1800:])
        blobs=sections(latest(folder),tamp);details=describe(blobs)
        observation={'case':name,'profile':'Original' if asset==original_pak else 'Redux','preparedState':bool(mutate),'captureFrame':frame,
                     'renderRequestFrame':frame+5 if render else None,'actual':details}
        if render:
            with Image.open(folder/'screenshot.bmp') as im:
                image=im.convert('RGB')
                observation['image']={'size':list(image.size),'pixelSha256':hashlib.sha256(image.tobytes()).hexdigest().upper(),
                  'distinctColours':len(image.getcolors(image.width*image.height))}
        observations.append(observation)
        if not name.startswith('catalog-'):
            print(json.dumps({'case':name,'group':details['battleGroup'],'actions':details['actions'],
                              'portraitVisible':details['portraitVisible'],'party':details['party']}),flush=True)
        return folder,blobs

    def action(callback,pc=0,additional=None):
        if callback not in callbacks:raise ValueError(f'Missing real action {callback:06X}')
        def prepare(blobs):
            stack=blobs[21]
            # Preserve the real scripted encounter and battle parent. Resume
            # the action at its documented post-target child boundary.
            stack[offsets['ModeStack.depth']]=4
            stack[offsets['ModeStack.mode']+3]=offsets['actionMode']
            parent=offsets['ModeStack.state']+2*offsets['modeSize']
            stack[parent+offsets['BattleRoutineState.phase']]=offsets['targetPost']
            struct.pack_into('<h',stack,parent+offsets['BattleRoutineState.attacker'],8)
            struct.pack_into('<H',stack,parent+offsets['BattleRoutineState.target_i'],8)
            start=offsets['ModeStack.state']+3*offsets['modeSize']
            stack[start:start+offsets['modeSize']]=bytes(offsets['modeSize'])
            stack[start+offsets['BattleActionState.pc']]=pc
            struct.pack_into('<H',stack,start+offsets['BattleActionState.table_index'],callbacks.index(callback))
            put16(blobs,6,'BattleState.current_attacker',8*offsets['battlerSize'])
            put16(blobs,6,'BattleState.current_target',8*offsets['battlerSize'])
            if additional:additional(blobs)
        return prepare

    if a.cinematic_fixtures:
        previous=local_scratch(a.cinematic_fixtures)
        evidence=json.loads((previous/'results.json').read_text(encoding='utf-8'))
        if evidence['sourceRevision']!=PIN or evidence['packSha256']!=digest(pak) or original_pak is None:
            raise ValueError('Cinematic fixtures require the reviewed Redux pack and an Original control pack.')
        def cinematic(blobs):
            put16(blobs,6,'BattleState.giygas_phase',4)
            put16(blobs,8,'WindowSystemState.battle_menu_current_character_id',0xFFFF)
            blobs[47][:]=struct.pack('<4h4B',152,152,152,152,15,15,1,1)
            # pc1 is after the source fade wait. Preserve that prerequisite
            # while resuming the actual close-all/text production stage.
            blobs[10][offsets['PPUState.inidisp']]=0
        for profile,asset,basis in (('Redux',pak,previous/'giygas-ness-selected'),
                                     ('Original',original_pak,previous/'original-entry')):
            folder,blobs=run('cinematic-'+profile.lower()+'-close-stage',frame=1,source=basis,
                             mutate=action(0xC2C572,1,cinematic),asset=asset)
            actual=describe(blobs)
            expected=(0,0,0) if profile=='Redux' else (1,15,1)
            check('cinematic-'+profile.lower()+'-state',
                  tuple(actual[k] for k in ('portraitActive','portraitVisible','portraitVictory'))==expected and
                  actual['battleActive']==0 and actual['renderHppp']==0,
                  {'expectedActiveVisibleVictory':list(expected),'actual':actual,
                   'qualification':'Seeded native portrait marker proves Redux reset and Original unchanged path; original renderer never enables Redux portraits.'})
        report={'format':'redux-special-presentation-cinematic-qa-v1','sourceRevision':PIN,
          'nativeExeSha256':digest(exe),'packSha256':digest(pak),'originalPackSha256':digest(original_pak),
          'fixtureInputNativeExeSha256':evidence['nativeExeSha256'],'sourceHookMappings':mapped_calls,
          'nativeActionSourceSha256':digest(native/'src/game/battle_actions.c'),
          'cases':observations,'checks':checks,'mismatches':mismatches,'allPassed':not mismatches,
          'executedCases':len(observations),'executedAssertions':len(checks),
          'passedAssertions':sum(x['passed'] for x in checks),
          'failedAssertions':sum(not x['passed'] for x in checks),'skippedCases':[],'skippedCaseCount':0,
          'reviewToolSha256':digest(Path(__file__)),
          'limits':['Exact prepared C2C3A4 close/text boundary; complete cinematic entity/timing sequences are not covered.']}
        (scratch/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'cinematicCases':len(observations),'mismatches':mismatches}))
        if mismatches and not a.diagnostic:raise SystemExit(1)
        return

    if a.dynamic_fixtures:
        previous=local_scratch(a.dynamic_fixtures)
        previous_result=json.loads((previous/'results.json').read_text(encoding='utf-8'))
        if previous_result['nativeExeSha256']!=digest(exe) or previous_result['packSha256']!=digest(pak):
            raise ValueError('Dynamic fixtures must use the same immutable binary and pack as their initial run.')
        basis=previous/'barf-ness-selected'
        for active in (0,1):
            def legacy(blobs,active=active):
                blobs[47][10]=active
                blobs[47][11]=0
                put16(blobs,8,'WindowSystemState.battle_menu_current_character_id',0)
            folder,blobs=run(f'legacy-active-{active}-cold',frame=20,source=basis,mutate=legacy)
            actual=describe(blobs)
            check(f'legacy-active-{active}-accepted',actual['portraitActive']==1 and
                  actual['portraitVisible']==1 and actual['portraitTargets']==1 and actual['portraitAnchors'][0]==152,
                  {k:actual[k] for k in ('portraitActive','portraitVisible','portraitTargets','portraitAnchors')})
        images={}
        for mode,phase,label in ((0,0,'normal'),(4,0,'magicant'),(5,0,'robots'),(4,1,'giygas-override')):
            def pose(blobs,mode=mode,phase=phase):
                put16(blobs,2,'GameState.character_mode',mode)
                put16(blobs,6,'BattleState.giygas_phase',phase)
                blobs[47][:]=struct.pack('<4h4B',152,152,152,152,15,15,1,1)
                # Keep the same loaded art/palettes while removing animation
                # from this prepared renderer checkpoint. The real native
                # portrait helper/compositor still selects and draws frames.
                for tag in (24,25):
                    data=blobs[tag];data[offsets['LoadedBGData.freeze_palette_scrolling']]=1
                    for name in ('scrolling_movements','distortion_styles'):
                        at=offsets['LoadedBGData.'+name];data[at:at+4]=bytes(4)
                    data[offsets['LoadedBGData.distortion_type']]=0
                    for name in ('horizontal_velocity','vertical_velocity','horizontal_acceleration','vertical_acceleration'):
                        struct.pack_into('<h',data,offsets['LoadedBGData.'+name],0)
            folder,blobs=run('dynamic-portrait-'+label,frame=20,source=basis,mutate=pose)
            current=observations[-1];images[label]=current['image']['pixelSha256']
            check('dynamic-portrait-'+label+'-visible',describe(blobs)['portraitVisible']==15,
                  {'expectedGroupIds':([1,2,3,4] if label=='normal' else [6,2,3,4] if label=='magicant' else [5,343,355,457]),
                   'visibleMask':describe(blobs)['portraitVisible'],'pixels':current['image']})
        check('dynamic-sprite-mode-branches',len({images['normal'],images['magicant'],images['robots']})==3,
              {'imageHashes':images,'qualification':'Distinct real compositor outputs with identical prepared background.'})
        check('dynamic-giygas-overrides-magicant',images['giygas-override']==images['robots'],
              {'robotPixels':images['robots'],'giygasOverridePixels':images['giygas-override'],
               'source':'Actual m3sbs_sprite_detect checks GIYGAS_PHASE before CHARACTER_MODE.'})
        report={'format':'redux-special-presentation-dynamic-qa-v1','sourceRevision':PIN,
                'nativeExeSha256':digest(exe),'packSha256':digest(pak),'cases':observations,
                'checks':checks,'mismatches':mismatches,
                'allPassed':not mismatches,'executedCases':len(observations),
                'executedAssertions':len(checks),'passedAssertions':sum(x['passed'] for x in checks),
                'failedAssertions':sum(not x['passed'] for x in checks),'skippedCases':[],'skippedCaseCount':0,
                'reviewToolSha256':digest(Path(__file__)),
                'limits':['Prepared renderer comparison, not progression or exact SNES-frame audiovisual parity.']}
        (scratch/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'dynamicCases':len(observations),'mismatches':mismatches}))
        if mismatches and not a.diagnostic:raise SystemExit(1)
        return

    intro,_=run('giygas-initial-entry',frame=500,group=475)
    ness,_=run('giygas-ness-selected',source=intro,actions=((10,0x20),))
    def death_stage(blobs):
        put16(blobs,6,'BattleState.giygas_phase',12)
        blobs[47][:]=struct.pack('<4h4B',152,152,152,152,1,1,1,0)
        put16(blobs,8,'WindowSystemState.battle_menu_current_character_id',0)
    death,b=run('giygas-death-stage-first-frame',frame=1,source=ness,
                mutate=action(0xC2C6F0,12,death_stage))
    actual=describe(b)
    checks.append({'check':'giygas-final-prayer-clears-portraits',
                   'passed':not(actual['portraitVisible'] or actual['portraitTargets']),
                   'details':{k:actual[k] for k in ('portraitVisible','portraitTargets','portraitActive')}})
    if actual['portraitVisible'] or actual['portraitTargets']:
        mismatches.append({'case':'giygas-death-stage-first-frame','kind':'source-reset-timing',
          'source':'m3sprites.ccs C2C75B giygas_fix_3 ends Bowspr and clears m3sbs before death tail.',
          'native':'The real prayer9 pc12 closes/hides HP/PP and window-ticks without resetting portrait state.',
          'actual':{k:actual[k] for k in ('portraitActive','portraitVisible','portraitAnchors','selected','renderHppp')},
          'expected':{'portraitTargets':0,'portraitVisible':0},
          'qualification':'Prepared action-stage checkpoint; full preceding prayer sequence is not claimed.'})

    def expected_bg(group,asset_data=assets):
        ids=struct.unpack_from('<2H',asset_data['data/btl_entry_bg_table.bin'],group*4)
        configs=[]
        for bg_id in ids:
            data=asset_data['data/bg_data_table.bin'][bg_id*17:bg_id*17+17]
            configs.append({'bgId':bg_id,'bitdepth':data[2],
                            'scrollingMovements':list(data[9:13]),'distortionStyles':list(data[13:17])})
        return configs

    def bind_bg(name,blobs,group,asset_data=assets):
        actual=describe(blobs);expected=expected_bg(group,asset_data);matches=actual['battleGroup']==group
        for index,e in enumerate(expected):
            if index==0 or e['bgId']:
                matches &= all(actual['bg'][index][k]==e[k] for k in ('bitdepth','scrollingMovements','distortionStyles'))
                matches &= actual['bg'][index]['targetLayer']!=0
            else: matches &= actual['bg'][index]['targetLayer']==0
        style=asset_data['data/btl_entry_ptr_table.bin'][group*8+7]
        targets=[2 if expected[0]['bitdepth']==4 else 3,
                 0 if not expected[1]['bgId'] else (1 if style&4 else 2) if expected[0]['bitdepth']==4 else 4]
        bounds=[(0,47,57,67)[style&3],(224,176,166,156)[style&3]]
        matches &= [x['targetLayer'] for x in actual['bg']]==targets
        matches &= actual['letterboxBounds']==bounds
        matches &= actual['ppuBgMode']==(9 if expected[0]['bitdepth']==4 else 8)
        expected_fill=[1,1,0] if expected[0]['bitdepth']==4 else [0,1,1,1]
        matches &= actual['viewportFill'][:len(expected_fill)]==expected_fill
        expected_30=int(targets[1]!=0 and expected[1]['distortionStyles'][0]!=0)
        matches &= actual['distort30fps']==expected_30
        check(name,matches,{'expectedGroup':group,'expectedConfig':expected,'actualBg':actual['bg'],
          'sourceLetterboxStyle':style,'expectedBounds':bounds,'actualBounds':actual['letterboxBounds'],
          'expectedTargets':targets,'actualTargets':[x['targetLayer'] for x in actual['bg']],
          'expectedDistort30fps':expected_30,'actualDistort30fps':actual['distort30fps'],
          'viewportFill':actual['viewportFill'],'ppuBgMode':actual['ppuBgMode']})

    bind_bg('giygas-entry-background-config',sections(latest(intro),tamp),475)
    def post_speech(blobs):
        put16(blobs,6,'BattleState.giygas_phase',4)
        put16(blobs,8,'WindowSystemState.battle_menu_current_character_id',0xFFFF)
        blobs[47][:]=struct.pack('<4h4B',152,152,152,152,15,15,1,1)
    speech,sb=run('giygas-speech2-posttext-reset',frame=1,source=ness,
                  mutate=action(0xC2C516,2,post_speech))
    check('giygas-speech2-posttext-reset',describe(sb)['portraitVisible']==0 and
          describe(sb)['portraitTargets']==0 and describe(sb)['portraitVictory']==0,
          {'sourceHook':'m3sprites.ccs C2C544 after DISPLAY_IN_BATTLE_TEXT',
           'actual':{k:describe(sb)[k] for k in ('portraitVisible','portraitTargets','portraitVictory')}})
    scenes={475:intro}
    for callback,pc,group,phase in ((0xC2C4C0,0,476,2),(0xC2C4C0,2,477,3),
                                    (0xC2C516,3,478,4),(0xC2C572,8,479,5),
                                    (0xC2C69E,8,480,11),(0xC2C6F0,23,483,0)):
        def prepare_phase(blobs,value=phase):put16(blobs,6,'BattleState.giygas_phase',value)
        folder,blobs=run(f'giygas-load-{group}',frame=220,source=ness,
                          mutate=action(callback,pc,prepare_phase))
        scenes[group]=folder;bind_bg(f'giygas-load-{group}-background-config',blobs,group)
        check(f'giygas-load-{group}-phase',describe(blobs)['giygasPhase']==phase,
              {'expectedPhase':phase,'actualPhase':describe(blobs)['giygasPhase']})

    # Independent cold starts from the same checkpoint must rebuild the
    # animated layer state and pixels identically, then actually advance it.
    c1,b1=run('giygas-animation-cold-a',frame=30,source=scenes[478])
    c2,b2=run('giygas-animation-cold-b',frame=30,source=scenes[478])
    check('giygas-animation-cold-repeat',describe(b1)==describe(b2) and
          observations[-1]['image']==observations[-2]['image'],
          {'stateEqual':describe(b1)==describe(b2),'pixelsEqual':observations[-1]['image']==observations[-2]['image']})
    c3,b3=run('giygas-animation-cold-later',frame=90,source=scenes[478])
    check('giygas-animation-advances',describe(b3)['bg']!=describe(b1)['bg'] and
          observations[-1]['image']['pixelSha256']!=observations[-3]['image']['pixelSha256'],
          {'layerStateChanged':describe(b3)['bg']!=describe(b1)['bg'],
           'pixelsChanged':observations[-1]['image']['pixelSha256']!=observations[-3]['image']['pixelSha256']})

    barf,_=run('barf-entry',frame=500,group=469)
    barf_ness,_=run('barf-ness-selected',source=barf,actions=((10,0x20),))
    def without_poo(blobs):
        gs=blobs[2]
        for field in ('party_members','party_order','player_controlled_party_members'):
            at=offsets['GameState.'+field];gs[at:at+6]=bytes((1,2,3,0,0,0))
        for field in ('party_count','player_controlled_party_count'):gs[offsets['GameState.'+field]]=3
        put16(blobs,2,'GameState.current_party_members',7)
        at=offsets['BattleState.battlers_table']+3*offsets['battlerSize']
        blobs[6][at:at+offsets['battlerSize']]=bytes(offsets['battlerSize'])
        blobs[47][:]=struct.pack('<4h4B',152,168,168,168,1,1,1,0)
        put16(blobs,8,'WindowSystemState.battle_menu_current_character_id',0)
    entrance,eb=run('barf-poo-entrance-first-frame',frame=1,source=barf_ness,
                     mutate=action(0xC292EE,0,without_poo))
    ea=describe(eb)
    check('barf-poo-joins-once',ea['controlledPartyCount']==4 and ea['partyCount']==sum(x!=0 for x in ea['party']) and
          ea['party'][:4]==[1,2,3,4] and ea['battlers'][3]=={'id':4,'conscious':1} and ea['selected']==3,
          {'party':ea['party'],'counts':[ea['partyCount'],ea['controlledPartyCount']],
           'pooBattler':ea['battlers'][3],'selected':ea['selected']})
    checks.append({'check':'barf-portraits-suspended-during-entrance',
                   'passed':ea['portraitVisible']==0 and ea['portraitActive']==2,
                   'details':{k:ea[k] for k in ('portraitVisible','portraitActive')}})
    if ea['portraitVisible'] or ea['portraitActive']!=2:
        mismatches.append({'case':'barf-poo-entrance-first-frame','kind':'source-reinitialization-timing',
          'source':'m3sprites.ccs C29302 ends Bowspr before hiding HP/PP; C29388 calls m3sbs_init after entrance DISPLAY_IN_BATTLE_TEXT returns.',
          'native':'Actual MasterBarfDeath pc0 must suspend portraits until its entrance text returns to pc1.',
          'actual':{k:ea[k] for k in ('portraitVisible','portraitAnchors','portraitTargets','selected')},
          'expected':{'portraitVisible':0,'portraitActive':2},
          'qualification':'Prepared three-member party at actual event callback; no preceding Barf battle claimed.'})
    entrance_later,elb=run('barf-poo-entrance-cold-later',frame=40,source=entrance)
    check('barf-poo-entrance-cold-stays-suspended',describe(elb)['portraitVisible']==0 and
          describe(elb)['portraitActive']==2,
          {k:describe(elb)[k] for k in ('portraitVisible','portraitActive','portraitAnchors')})
    entrance_done,edb=run('barf-poo-entrance-text-complete',frame=220,source=entrance,
                         actions=tuple((t,0x20) for t in range(10,211,12)))
    actual_done=describe(edb)
    check('barf-poo-entrance-resumes-after-text',actual_done['portraitActive']==1 and
          actual_done['portraitVisible']==8 and actual_done['portraitTargets']==8 and
          not any(x['callback']=='C292EE' and x['pc']==1 for x in actual_done['actions']),
          {'actual':{k:actual_done[k] for k in ('portraitActive','portraitVisible','portraitTargets','portraitAnchors','actions')},
           'qualification':'Ordinary replayed A inputs advance the actual entrance child; no result/state mutation in continuation.'})
    bind_bg('barf-background-config',elb,469)

    def load_scene(group):
        def prepare(blobs):
            stack=blobs[21];stack[offsets['ModeStack.depth']]=4
            stack[offsets['ModeStack.mode']+3]=offsets['sceneMode']
            start=offsets['ModeStack.state']+3*offsets['modeSize']
            stack[start:start+offsets['modeSize']]=bytes(offsets['modeSize'])
            struct.pack_into('<H',stack,start+offsets['LoadBattleSceneState.group'],group)
            # Legitimate first-load branch: no swirl, actual LBS_ENTER then
            # LBS_LOAD/fade. This fixture does not fabricate loaded results.
            put16(blobs,6,'BattleState.battle_mode_flag',0)
        return prepare

    catalogs=[]
    if a.scene_catalog or a.original_controls:
        if original_pak is None:raise ValueError('Both profiles are required for the scene catalog.')
        def ordinary_battle_entry(blobs):
            stack=blobs[21];stack[offsets['ModeStack.depth']]=3
            stack[offsets['ModeStack.mode']+2]=offsets['battleMode']
            start=offsets['ModeStack.state']+2*offsets['modeSize']
            stack[start:start+offsets['modeSize']]=bytes(offsets['modeSize'])
            stack[start+offsets['BattleRoutineState.phase']]=offsets['battleBegin']
            put16(blobs,6,'BattleState.current_battle_group',475)
            put16(blobs,5,'OverworldState.battle_mode',1)
        # The convenience CLI fixture is intentionally Redux-only. This
        # Original control runs actual BTL_BEGIN with prepared party/enemy
        # input, binding tables through the warm ordinary entry path.
        original_intro,ob=run('original-entry',frame=500,source=intro,
                              mutate=ordinary_battle_entry,asset=original_pak)
        bind_bg('original-entry-background-config',ob,475,original_assets)
        original_death,ob=run('original-prayer9-death-stage',frame=1,source=original_intro,
                            mutate=action(0xC2C6F0,12,death_stage),asset=original_pak)
        check('original-portrait-state-remains-disabled',describe(ob)['portraitActive']==0 and
              describe(ob)['portraitVisible']==0,
              {k:describe(ob)[k] for k in ('portraitActive','portraitVisible','portraitTargets')})
        profile_runs=(('Redux',pak,assets,intro),('Original',original_pak,original_assets,original_intro)) if a.scene_catalog else ()
        for profile,profile_pak,asset_data,basis in profile_runs:
            slot_count=min(len(asset_data['data/btl_entry_bg_table.bin'])//4,
                           len(asset_data['data/btl_entry_ptr_table.bin'])//8)
            config_count=len(asset_data['data/bg_data_table.bin'])//17
            tested=[];invalid=[];classes=set();start_checks=len(checks)
            for group in range(slot_count):
                ids=struct.unpack_from('<2H',asset_data['data/btl_entry_bg_table.bin'],group*4)
                if any(x>=config_count for x in ids):invalid.append(group);continue
                style=asset_data['data/btl_entry_ptr_table.bin'][group*8+7]
                classes.add((*ids,style))
                folder,blobs=run(f'catalog-{profile.lower()}-{group:03}',frame=2,source=basis,
                                 mutate=load_scene(group),render=False,asset=profile_pak)
                bind_bg(f'catalog-{profile.lower()}-{group:03}',blobs,group,asset_data);tested.append(group)
                if group%32==0:
                    print(json.dumps({'catalogProfile':profile,'completedSlot':group,'slots':slot_count}),flush=True)
                    (scratch/'partial-results.json').write_text(json.dumps({'cases':observations,'checks':checks,'mismatches':mismatches},indent=2)+'\n',encoding='utf-8')
            catalogs.append({'profile':profile,'tableSlots':slot_count,'testedSlots':tested,
              'untestedInvalidBackgroundSlots':invalid,'uniqueBackgroundLetterboxConfigs':len(classes),
              'allChecksPassed':all(x['passed'] for x in checks[start_checks:]),
              'qualification':'Numeric table slots through production scene loader, not legal encounter/progression claims.'})
        warm,wb=run('giygas-warm-entry-478',frame=500,group=478)
        bind_bg('giygas-warm-entry-478-background-config',wb,478)

    report={'format':'redux-special-presentation-qa-v1','sourceRevision':PIN,
      'nativeExeSha256':digest(exe),'packSha256':digest(pak),'originalRomSha256':digest(a.original_rom),
      'sourceHookMappings':mapped_calls,'cases':observations,'checks':checks,'mismatches':mismatches,
      'sceneCatalogs':catalogs,'originalPackSha256':digest(original_pak) if original_pak else None,
      'preloadCapacityEvidence':capacity,
      'allPassed':not mismatches,'executedCases':len(observations),'executedAssertions':len(checks),
      'passedAssertions':sum(x['passed'] for x in checks),
      'failedAssertions':sum(not x['passed'] for x in checks),
      'skippedCaseCount':sum(len(x['untestedInvalidBackgroundSlots']) for x in catalogs),
      'reviewToolSha256':digest(Path(__file__)),
      'skippedCases':[{'profile':x['profile'],'group':i,'reason':'invalid background table index'}
                      for x in catalogs for i in x['untestedInvalidBackgroundSlots']],
      'sourceFiles':{str(path.relative_to(ROOT)).replace('\\','/'):digest(path) for path in (
          project/'ccscript/redux/m3sprites.ccs',project/'ccscript/redux/Bowspr.ccs',
          native/'src/game/battle_actions.c',native/'src/game/battle_ui.c',
          native/'src/game/maternalbound_battle_sprites.c',native/'src/game/maternalbound_battle_sprites.h',
          native/'asm/battle/actions/master_barf_death.asm',native/'asm/battle/actions/giygas_prayer_9.asm',
          native/'asm/battle/actions/pokey_speech_2.asm',native/'asm/text/display_in_battle_text.asm')},
      'stateInterpretation':{'portraitActive':'0 uninitialized, 1 initialized, 2 suspended; native initialized state is not proof that source Bowspr objects are visible.'},
      'limits':['Prepared production action/menu/render states, not a complete Giygas story encounter.',
                'Numeric scene catalog retains a template enemy/party set: it covers rendering configurations, not all encounter participants.',
                'Image hashes and structural source bindings do not prove audiovisual parity.',
                'Full prayers1-7 entity cutscene timelines and exact source C2C3A4 reset timing remain outside this suite.']}
    (scratch/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cases':len(observations),'mismatches':mismatches},indent=2))
    if mismatches and not a.diagnostic:raise SystemExit(1)


if __name__=='__main__':main()
