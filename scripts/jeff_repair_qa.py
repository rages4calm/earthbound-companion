# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise the full pinned first-night Jeff repair dialogue in private saves.

Uses every broken-item record from the selected Redux pack and the actual
native text/window constructor. No owner save, ROM, pack or engine is edited.
This does not exercise walking to a hotel or later-night 25-percent RNG.
"""
import argparse, hashlib, json, re, shutil, struct, subprocess, sys
from pathlib import Path
from build_maternalbound_pack import read_pack
from check_jev_observer_parity import latest, local_scratch, sections
from hotel_transaction_qa import layout as hotel_layout
from redux_recovery_qa import write_state
from redux_reset_qa import ResetSession

ROOT=Path(__file__).resolve().parents[1]
ENTRY=0xC685DA
CONFIRM=0x20
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def layout(native,compiler,out):
    result=hotel_layout(native,compiler,out)
    source=out/'repair-layout.c';exe=out/'repair-layout.exe'
    source.write_text(r'''#include <stdio.h>
#include <stddef.h>
#include "game/game_state.h"
#include "game/inventory.h"
#include "game/battle.h"
int main(void){printf("{\"iq\":%zu,\"params\":%zu,\"epi\":%u,\"ep\":%u,\"unconscious\":%u,\"diamondized\":%u}",offsetof(CharStruct,iq),offsetof(ItemConfig,params),ITEM_PARAM_EPI,ITEM_PARAM_EP,STATUS_0_UNCONSCIOUS,STATUS_0_DIAMONDIZED);return 0;}''',encoding='utf-8')
    p=subprocess.run([str(compiler),'-std=c2x','-I',str(native/'src'),'-I',str(ROOT/'build/companion/game_lib/generated'),str(source),'-o',str(exe)],capture_output=True,timeout=40)
    if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace'))
    result.update(json.loads(subprocess.check_output([str(exe)],timeout=10)))
    return result

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
    source=a.project/'ccscript/data/data_23.ccs';text=source.read_text(encoding='utf-8-sig')
    block=text[text.index('l_0xc685da:'):text.index('l_0xc68659:')]
    for token in ('try_fixing_an_item(100)','character_has_status(3, SCR_STATUS_GROUP_0, SCR_STATUS_0_UNCONSCIOUS)','character_has_status(3, SCR_STATUS_GROUP_0, SCR_STATUS_0_DIAMONDIZED)','try_fixing_an_item(25)'):
        if token not in block:raise ValueError('Review changed repair entry: '+token)
    flag_file=a.project/'ccscript/definitions/flags.ccs';item_file=a.project/'ccscript/definitions/items.ccs'
    ftext=flag_file.read_text(encoding='utf-8-sig');itext=item_file.read_text(encoding='utf-8-sig')
    flags={name:int(n) for name,n in re.findall(r'define\s+(\w+)\s*=\s*flag\s+(\d+)',ftext)}
    items={name:int(n) for name,n in re.findall(r'define\s+(\w+)\s*=\s*(\d+)',itext)}
    tools={items[item]:flags[flag] for item,flag in re.findall(r'result_is\((\w+)\).*?set\((FLG_ITEM_\w+)\)',block,re.S)}
    if len(tools)!=8:raise ValueError('Re-review the eight repair-to-Tools branches.')
    l=layout(a.native_source.resolve(),a.compiler.resolve(),out)
    _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h')
    table=assets['data/item_configuration_table.bin'];dialogue=assets['dialogue/dialogue.bin'];footer=dialogue[-32:]
    if footer[:8]!=b'MRDXNV01' or len(table)%l['itemRecordBytes']:raise ValueError('Reviewed Redux pack required.')
    mapoff,count=struct.unpack_from('<II',footer,12)
    mapping=dict(struct.unpack_from('<II',dialogue,mapoff+i*8) for i in range(count))
    records=[]
    for item in range(len(table)//l['itemRecordBytes']):
        at=item*l['itemRecordBytes']
        if table[at+l['ItemConfig.type']]==l['brokenType']:
            records.append((item,table[at+l['params']+l['epi']],table[at+l['params']+l['ep']]))
    save=latest(a.checkpoint);identities={str(path):sha(path) for path in (save,a.assets,a.player,a.observer,source,flag_file,item_file)}
    rows=[]
    def flag(b,n,on):
        n-=1
        if on:b[4][n//8]|=1<<(n%8)
        else:b[4][n//8]&=255^(1<<(n%8))
    def hasflag(b,n):n-=1;return bool(b[4][n//8]&(1<<(n%8)))
    for engine,exe in (('player',a.player),('observer',a.observer)):
        seed=ResetSession(exe.resolve(),a.assets.resolve(),out/(engine+'-window-constructor'),l,tamp)
        seed.run('native-window-constructor',[(0,0)],0,load=False,entry=ENTRY)
        text_sections={tag:bytearray(seed.blobs[tag]) for tag in (7,8,27,28,29,30,31,32,33,39)}
        jobs=[(item,iq,fixed,'repair',mode) for item,iq,fixed in records for mode in (False,True)]
        first=next(r for r in records if r[1]>0)
        jobs.extend((*first,guard,True) for guard in ('low-iq','unconscious','diamondized'))
        for item,iq,fixed,guard,tool_mode in jobs:
            session=ResetSession(exe.resolve(),a.assets.resolve(),out/f'{engine}-{item}-{guard}-{int(tool_mode)}',l,tamp)
            (session.folder/'saves').mkdir();target=session.folder/'saves'/save.name;shutil.copy2(save,target)
            b=sections(target,tamp);b.update({tag:bytearray(data) for tag,data in text_sections.items()})
            members=list(b[2][l['GameState.party_members']:l['GameState.party_members']+6])
            if 3 not in members:raise ValueError('Copied checkpoint must contain Jeff.')
            jeff=2*l['CharStruct.size'];slot=jeff+l['CharStruct.items']
            b[3][slot:slot+14]=bytes((item,))+bytes(13);b[3][jeff+l['iq']]=iq-1 if guard=='low-iq' else iq
            b[3][jeff+l['CharStruct.afflictions']:jeff+l['CharStruct.afflictions']+7]=bytes(7)
            # Script status arguments are one-based; native affliction bytes
            # store value-1. Use actual native enums instead of script IDs.
            if guard in ('unconscious','diamondized'):b[3][jeff+l['CharStruct.afflictions']]=l[guard]
            flag(b,flags['FLG_WINS_JEFF_REPAIR'],False);flag(b,flags['FLG_TOOL_ITEMS'],tool_mode)
            for n in tools.values():flag(b,n,False)
            ms=b[21];ms[l['ModeStack.depth']]=2;ms[l['ModeStack.mode']+1]=l['displayMode']
            at=l['ModeStack.state']+l['ModeState.size'];ms[at:at+l['ModeState.size']]=bytes(l['ModeState.size'])
            ms[at+l['DisplayTextModeState.phase']]=l['textEnter'];reader=at+l['DisplayTextModeState.reader'];ms[reader+l['ScriptReader.source']]=l['dialogueSource']
            struct.pack_into('<IIi',ms,reader+l['ScriptReader.ptr_off'],mapping[ENTRY]-0x100000,len(dialogue),-1)
            write_state(target,b,tamp)
            session.run('first-cold-entry',[(0,0)],10)
            actions=[(0,0)]
            for frame in range(20,1800,45):actions.extend(((frame,CONFIRM),(frame+2,0)))
            session.run('repair-text-to-return',actions,1850)
            b=session.blobs;expected=item if guard!='repair' else 0 if tool_mode and fixed in tools else fixed
            assert session.last['modes']==[l['overworldMode']],session.last
            assert b[3][slot]==expected,(engine,item,guard,tool_mode,expected,b[3][slot])
            assert hasflag(b,flags['FLG_WINS_JEFF_REPAIR'])==(guard=='repair')
            for fixed_id,n in tools.items():assert hasflag(b,n)==(guard=='repair' and tool_mode and fixed==fixed_id)
            session.run('cold-roaming',[(0,0)],2)
            assert session.blobs[3][slot]==expected
            rows.append({'engine':engine,'brokenItem':item,'requiredIq':iq,'fixedItem':fixed,'branch':guard,'toolsEnabled':tool_mode,'finalJeffSlot':expected,'returnedToRoaming':True,'passed':True})
            print(json.dumps(rows[-1]),flush=True)
    assert all(sha(Path(path))==value for path,value in identities.items()),'Immutable input changed.'
    report={'Passed':True,'ExecutedCases':len(rows),'SkippedCases':0,'BrokenRecords':len(records),'Identities':identities,'Cases':rows,'NativeLayout':l,'Runner':{'path':'tools/jeff_repair_qa.py','sha256':sha(Path(__file__))},'InputsUnchanged':True,'OwnerSavesTouched':False,'FullPlaythroughVerified':False,
        'Limits':['Prepared full C685DA entry in a copied valid room checkpoint, with native text/window constructor state. No hotel walk, sleep cutscene or story chapter.',
        'Every packed broken item is tested at its required IQ under the first-night100-percent branch, with source Tools on/off controls and selected blocked-status/low-IQ controls.',
        'Later-night25-percent RNG, source audio/visual parity and physical controller are not covered.']}
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('Passed','ExecutedCases','BrokenRecords')}))

if __name__=='__main__':main()
