# SPDX-License-Identifier: GPL-3.0-or-later
"""Replay a full pinned Threek hotel transaction from a copied room checkpoint.

The checkpoint must already have a valid room/party. Only fresh diagnostic
copies are modified. This prepares the caller prerequisites, not a whole quest
or a walk to the receptionist, and never writes the input save or asset pack.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

from check_jev_observer_parity import latest, local_scratch, sections
from build_maternalbound_pack import read_pack
from redux_recovery_qa import write_state
from redux_reset_qa import ResetSession, layout as base_layout

ROOT=Path(__file__).resolve().parents[1]
CONFIRM,RIGHT,DOWN=0x20,0x100,0x400

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def layout(native,compiler,out):
    result=base_layout(native,compiler,out)
    source=out/'hotel-layout.c';exe=out/'hotel-layout.exe'
    source.write_text(r'''#include <stdio.h>
#include <stddef.h>
#include "game/game_state.h"
#include "game/overworld.h"
#include "game/inventory.h"
#include "core/mode_stack.h"
#define F(T,N) printf("\"" #T "." #N "\":%zu,",offsetof(T,N))
int main(void){printf("{");
F(GameState,money_carried);F(GameState,bank_balance);
F(GameState,leader_x_coord);F(GameState,leader_y_coord);
F(CharStruct,max_hp);F(CharStruct,max_pp);F(CharStruct,afflictions);F(CharStruct,items);
F(CharStruct,current_hp);F(CharStruct,current_hp_target);
F(CharStruct,current_pp);F(CharStruct,current_pp_target);
F(OverworldState,redux_primary_timer);F(OverworldState,redux_secondary_timer);F(ItemConfig,type);
printf("\"itemRecordBytes\":%zu,\"brokenType\":%u,\"overworldMode\":%u,\"choiceMode\":%u}",sizeof(ItemConfig),ITEM_TYPE_BROKEN,GAME_MODE_OVERWORLD,GAME_MODE_SELECTION_MENU);
return 0;}''',encoding='utf-8')
    p=subprocess.run([str(compiler),'-std=c2x','-I',str(native/'src'),'-I',str(ROOT/'build/companion/game_lib/generated'),str(source),'-o',str(exe)],capture_output=True,timeout=40)
    if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace'))
    result.update(json.loads(subprocess.check_output([str(exe)],timeout=10)))
    return result

def flags_from(project):
    text=(project/'ccscript/definitions/flags.ccs').read_text(encoding='utf-8-sig')
    names=('FLG_HOTEL_PAPERBOY_APPEAR','FLG_ONET_POLA_TELEPATHY','FLG_TWSN_POLA_TELEPATHY','FLG_WINS_POLA_TELEPATHY','FLG_PUT_ZOMBI_HOIHOI')
    return {n:int(re.search(r'define\s+'+n+r'\s*=\s*flag\s+(\d+)',text)[1]) for n in names}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('player','observer','assets','checkpoint','project','scratch'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--native-source',type=Path,default=ROOT/'native-source')
    p.add_argument('--compiler',type=Path,default=ROOT/'tools/mingw64/bin/gcc.exe')
    a=p.parse_args();out=local_scratch(a.scratch)
    if out.exists():raise ValueError('Use a fresh diagnostic directory.')
    out.mkdir(parents=True)
    sys.path.insert(0,str(a.native_source/'src/vendor/tamp'));import tamp
    source=a.project/'ccscript/data/data_48.ccs';text=source.read_text(encoding='utf-8-sig')
    block=text[text.index('l_0xc9067d:'):text.index('l_0xc906f0:')]
    for token in ('get_party_size_times(60) swap','two_choice_menu("Yes", l_0xc906b6, "No", l_0xc906b0)','warp(17)','call(data_49.l_0xc91582)'):
        if token not in block:raise ValueError('Re-review changed hotel transaction: '+token)
    offsets=layout(a.native_source.resolve(),a.compiler.resolve(),out)
    _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h')
    dialogue=assets['dialogue/dialogue.bin'];footer=dialogue[-32:]
    if footer[:8]!=b'MRDXNV01':raise ValueError('Only the reviewed mapped Redux pack is supported.')
    mapoff,count=struct.unpack_from('<II',footer,12)
    mapping=dict(struct.iter_unpack('<II',dialogue[mapoff:mapoff+count*8]))
    items=assets['data/item_configuration_table.bin']
    if not items or len(items)%offsets['itemRecordBytes']:raise ValueError('Incomplete native item records.')
    flags=flags_from(a.project);save=latest(a.checkpoint)
    inputs={str(path):sha(path) for path in (save,a.assets,a.player,a.observer,source)}
    rows=[]
    def snapshot(session):
        b=session.blobs;l=session.layout;g=b[2]
        members=list(g[l['GameState.player_controlled_party_members']:l['GameState.player_controlled_party_members']+6])
        members=members[:g[l['GameState.player_controlled_party_count']]]
        characters=[]
        for n in members:
            at=n*l['CharStruct.size']
            characters.append({field:struct.unpack_from('<H',b[3],at+l['CharStruct.'+field])[0] for field in ('max_hp','max_pp','current_hp_target','current_pp_target')})
        f=flags['FLG_HOTEL_PAPERBOY_APPEAR']-1
        inventory=b''.join(b[3][n*l['CharStruct.size']+l['CharStruct.items']:n*l['CharStruct.size']+l['CharStruct.items']+14] for n in members)
        return {'modes':session.last['modes'],'money':struct.unpack_from('<I',g,l['GameState.money_carried'])[0],
                'bank':struct.unpack_from('<I',g,l['GameState.bank_balance'])[0],
                'position':[struct.unpack_from('<H',g,l['GameState.'+key])[0] for key in ('leader_x_coord','leader_y_coord')],
                'controlledCharacterIndices':members,'characters':characters,'inventorySha256':hashlib.sha256(inventory).hexdigest(),
                'partyOrder':list(g[l['GameState.party_order']:l['GameState.party_order']+6]),
                'hotelFlag':bool(b[4][f//8]&(1<<(f%8)))}
    for engine,exe in (('player',a.player),('observer',a.observer)):
        # Ordinary Talk opens the standard text window before DISPLAY_TEXT.
        # Obtain that prerequisite from the actual native fixture constructor;
        # a bare reader on a roaming checkpoint has no menu option storage.
        window_seed=ResetSession(exe.resolve(),a.assets.resolve(),out/(engine+'-window-constructor'),offsets,tamp)
        window_seed.run('native-standard-window',[(0,0)],0,load=False,entry=0xC9067D)
        text_state={tag:bytearray(window_seed.blobs[tag]) for tag in (7,8,27,28,29,30,31,32,33,39)}
        for branch in ('pay','decline','insufficient'):
            session=ResetSession(exe.resolve(),a.assets.resolve(),out/(engine+'-'+branch),offsets,tamp)
            (session.folder/'saves').mkdir();target=session.folder/'saves'/save.name;shutil.copy2(save,target)
            blobs=sections(target,tamp);l=offsets;g=blobs[2]
            for tag,data in text_state.items():blobs[tag]=bytearray(data)
            players=list(g[l['GameState.player_controlled_party_members']:l['GameState.player_controlled_party_members']+6])[:g[l['GameState.player_controlled_party_count']]]
            # This native array stores zero-based character/entity offsets,
            # not the one-based IDs stored in party_order/party_members.
            if not players or any(n not in range(4) for n in players):raise ValueError('Checkpoint requires a valid controlled party.')
            for n in players:
                at=n*l['CharStruct.size'];blobs[3][at+l['CharStruct.afflictions']:at+l['CharStruct.afflictions']+7]=bytes(7)
                # Preserve ordinary inventory/equipment/Teddy prerequisites.
                # Only remove Jeff's source-defined broken repair candidates;
                # testing each repair is a separate scenario.
                if n==2:
                    for slot in range(14):
                        index=at+l['CharStruct.items']+slot;item=blobs[3][index]
                        if item:
                            item_at=item*l['itemRecordBytes']+l['ItemConfig.type']
                            if item_at>=len(items):raise ValueError('Out-of-range saved item: '+str(item))
                            if items[item_at]==l['brokenType']:blobs[3][index]=0
                pp=min(2,struct.unpack_from('<H',blobs[3],at+l['CharStruct.max_pp'])[0])
                for field,value in (('current_hp',10),('current_hp_target',10),('current_pp',pp),('current_pp_target',pp)):
                    struct.pack_into('<H',blobs[3],at+l['CharStruct.'+field],value)
            for flag in flags.values():blobs[4][(flag-1)//8]&=255^(1<<((flag-1)%8))
            struct.pack_into('<I',g,l['GameState.money_carried'],0 if branch=='insufficient' else 5000)
            ms=blobs[21];ms[l['ModeStack.depth']]=2;ms[l['ModeStack.mode']+1]=l['displayMode']
            at=l['ModeStack.state']+l['ModeState.size'];ms[at:at+l['ModeState.size']]=bytes(l['ModeState.size'])
            ms[at+l['DisplayTextModeState.phase']]=l['textEnter'];reader=at+l['DisplayTextModeState.reader']
            ms[reader+l['ScriptReader.source']]=l['dialogueSource']
            struct.pack_into('<IIi',ms,reader+l['ScriptReader.ptr_off'],mapping[0xC9067D]-0x100000,len(dialogue),-1)
            write_state(target,blobs,tamp)
            session.run('entry',[(0,0)],60);start=snapshot(session)
            for i in range(12):
                if l['choiceMode'] in session.last['modes']:break
                session.run('advance-'+str(i),[(0,0),(10,CONFIRM),(12,0)],80)
            else:raise RuntimeError('Full entry did not reach Yes/No choice: '+str(session.last))
            session.run('cold-choice',[(0,0)],2)
            if l['choiceMode'] not in session.last['modes']:raise AssertionError('Cold transaction menu vanished')
            actions=[(0,0)]
            if branch=='decline':actions.extend(((10,RIGHT),(12,0)))
            actions.extend(((30,CONFIRM),(32,0)))
            for frame in range(90,2500,60):actions.extend(((frame,CONFIRM),(frame+2,0)))
            session.run('choice-rest-return',actions,2550);final=snapshot(session)
            if final['modes']!=[l['overworldMode']]:raise AssertionError('Hotel transaction did not return to roaming: '+str(final))
            assert final['bank']==start['bank'] and final['controlledCharacterIndices']==start['controlledCharacterIndices']
            assert final['inventorySha256']==start['inventorySha256'] and final['partyOrder']==start['partyOrder']
            assert final['money']==start['money']-(60*len(players) if branch=='pay' else 0)
            assert final['hotelFlag']==(branch=='pay')
            for before,ch in zip(start['characters'],final['characters'],strict=True):
                assert ch['current_hp_target']==(ch['max_hp'] if branch=='pay' else before['current_hp_target'])
                assert ch['current_pp_target']==(ch['max_pp'] if branch=='pay' else before['current_pp_target'])
            session.run('cold-roaming',[(0,0)],2)
            cold=snapshot(session);assert cold==final
            if branch=='pay':
                session.run('ordinary-down-egress',[(0,0),(10,DOWN),(30,0)],40)
                moved=snapshot(session);assert moved['position'][1]>final['position'][1] and moved['money']==final['money']
            rows.append({'engine':engine,'branch':branch,'start':start,'final':final,'passed':True})
    assert all(sha(Path(path))==digest for path,digest in inputs.items()),'Input save or asset changed'
    report={'Passed':True,'InputsUnchanged':True,'Identities':inputs,'Cases':rows,'FullPlaythroughVerified':False,
            'Limits':['Prepared full source dialogue entry from an existing copied hotel-room checkpoint, with standard text/window state from the native fixture constructor; not an ordinary receptionist interaction.',
                      'Explicitly clears sleep diversion flags and removes scratch Jeff repair candidates; zombie trap, telepathy and broken-item repair branches are separate.',
                      'Healthy party, no real controller or audiovisual parity proof.']}
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
