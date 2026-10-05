# SPDX-License-Identifier: GPL-3.0-or-later
"""Check every item-box record and replay its real reward script locally.

Prepared states substitute the NPC identity of one reachable box. Loot, text,
placements and asset packs are never patched. This covers reward execution,
not a walk through every room or its story conditions. No Jev requests.
"""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import json
import hashlib
import re
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import yaml
from build_maternalbound_pack import read_pack
from check_jev_observer_parity import latest, local_scratch, sections
from redux_recovery_qa import write_state
from jev_gameplay_runner import observe_step, mode_names, sha

ROOT = Path(__file__).resolve().parents[1]


def placement_catalog(assets):
    ptrs = assets['data/sprite_placement_ptr_table.bin']
    data = assets['data/sprite_placement_table.bin']
    result = {}
    for sector, (pointer,) in enumerate(struct.iter_unpack('<H', ptrs)):
        if not pointer:
            continue
        offset = pointer - 0x6BE7
        if offset < 0 or offset + 2 > len(data):
            raise ValueError('Placement pointer outside native table')
        count = struct.unpack_from('<H', data, offset)[0]
        if offset + 2 + count*4 > len(data):
            raise ValueError('Truncated placement list')
        for row in range(count):
            npc, y, x = struct.unpack_from('<HBB', data, offset+2+row*4)
            result.setdefault(npc, []).append([sector//32, sector%32, x, y])
    return result


def catalog(original, redux, rom, project, original_rom):
    ids = ROOT/'native-source/src/data/runtime_generated/asset_ids.h'
    orig = read_pack(original, ids)[2]
    red = read_pack(redux, ids)[2]
    compiled = rom.read_bytes()
    code = compiled[0x23E5:0x23EF]
    if code[0] != 0xA9 or code[5] != 0xA9:
        raise ValueError('Relocated NPC table loader changed')
    address = int.from_bytes(code[1:3], 'little') | int.from_bytes(code[6:8], 'little') << 16
    expected = compiled[address-0xC00000:address-0xC00000+1584*17]
    retail=original_rom.read_bytes()
    if len(retail)%1024==512:retail=retail[512:]
    if hashlib.sha256(retail).hexdigest()!='a8fe2226728002786d68c27ddddf0b90a894db52e4dfe268fdf72a68cae5f02e':
        raise ValueError('Expected clean USA retail ROM')
    retail_table=retail[0xF8985:0xF8985+1584*17]
    source = yaml.safe_load((project/'npc_config_table.yml').read_text().replace('\t', ' '))
    item_def=(project/'ccscript/definitions/items.ccs').read_text()
    flag_def=(project/'ccscript/definitions/flags.ccs').read_text()
    flag_rewards={}
    for name in ('HP_SUCKER','NEUTRALIZER','CARROT_KEY'):
        item_match=re.search(r'^define '+name+r'\s*=\s*(\d+)',item_def,re.M)
        flag_match=re.search(r'^define FLG_ITEM_'+name+r'\s*=\s*flag\s+(\d+)',flag_def,re.M)
        if not item_match or not flag_match:raise ValueError('Missing source reward aliases')
        flag_rewards[int(item_match[1])]=int(flag_match[1])
    if flag_rewards!={135:855,195:870,253:904} or not re.search(r'^define FLG_KEY_ITEMS\s*=\s*flag\s+781',flag_def,re.M):
        raise ValueError('Review flag-backed reward implementation against source')
    source_placements = yaml.safe_load((project/'map_sprites.yml').read_text())
    locations = {}
    for y, row in source_placements.items():
        for x, objects in row.items():
            for obj in objects or []:
                locations.setdefault(obj['NPC ID'], []).append([y, x, obj['X'], obj['Y']])
    blob = red['dialogue/dialogue.bin']
    _, version, start, count, *_ = struct.unpack_from('<8s6I', blob, len(blob)-32)
    if version != 2:
        raise ValueError('Unreviewed dialogue mapping version')
    mapping = dict(struct.iter_unpack('<II', blob[start:start+count*8]))
    tables = [a['data/npc_config_table.bin'] for a in (orig,red)]
    if any(len(t) != 1584*17 for t in tables) or len(expected) != 1584*17:
        raise ValueError('Unexpected NPC table dimensions')
    placed = [placement_catalog(a) for a in (orig,red)]
    records = []
    for npc in range(1584):
        vanilla, native, raw = (t[npc*17:(npc+1)*17] for t in (*tables,expected))
        if native[0] != 2:
            if vanilla[0] == 2 or source[npc]['Type'] == 'item':
                raise ValueError(f'Lost item-box type: {npc}')
            continue
        flag, = struct.unpack_from('<H', native, 6)
        text, loot = struct.unpack_from('<II', native, 9)
        raw_text, = struct.unpack_from('<I', raw, 9)
        # Only dialogue pointers may differ from the compiled ROM.
        if native[:9] != raw[:9] or native[13:] != raw[13:] or text != mapping[raw_text]:
            raise ValueError(f'Converted present differs from compiled ROM: {npc}')
        retail_row=retail_table[npc*17:(npc+1)*17]
        if vanilla[:9] != retail_row[:9] or vanilla[13:] != retail_row[13:]:
            raise ValueError(f'Original present differs from retail ROM: {npc}')
        if vanilla[:9] != native[:9]:raise ValueError(f'Redux changed present config: {npc}')
        if source[npc]['Type'] != 'item' or source[npc]['Event Flag'] != flag or int(source[npc]['Text Pointer 2'][1:],16) != loot:
            raise ValueError(f'Present disagrees with source YAML: {npc}')
        if not 1 <= flag <= 1024 or not loot or loot > 65535 or not text:
            raise ValueError(f'Invalid present reward/flag/text: {npc}')
        if any(sorted(p.get(npc, [])) != sorted(locations.get(npc, [])) for p in placed) or not placed[1].get(npc):
            raise ValueError(f'Missing or altered present placement: {npc}')
        if loot < 256:
            item = red['data/item_configuration_table.bin'][loot*39:(loot+1)*39]
            if len(item) != 39 or not item[:25].split(b'\0')[0]:
                raise ValueError(f'Absent item definition: {npc}/{loot}')
        original_loot=int.from_bytes(vanilla[13:17],'little')
        reward_flag=flag_rewards.get(loot)
        if reward_flag is not None and reward_flag!=flag:raise ValueError('Reward unlock no longer aliases the container flag')
        records.append({'npcId':npc, 'openedFlag':flag, 'lootValue':loot,'originalLootValue':original_loot,
                        'reduxRewardFlag':reward_flag,
                        'itemId':loot if loot<256 else None,
                        'cash':loot-256 if loot>=256 else None,
                        'reduxTextPointer':text, 'originalTextPointer':int.from_bytes(vanilla[9:13],'little'),
                        'placements':placed[1][npc]})
    if len(records) != 177 or len({r['openedFlag'] for r in records}) != 177:
        raise ValueError('Present catalog count or unique flag coverage changed')
    return records, orig, red


def layout(output):
    code = output/'present-layout.c'
    code.write_text('''#include <stdio.h>
#include <stddef.h>
#include "entity/entity.h"
#include "game/map_loader.h"
int main(void){printf("%zu %zu %zu %zu %zu %zu %zu %zu %zu\\n",sizeof(EntitySystem),offsetof(EntitySystem,npc_ids),sizeof(((EntitySystem*)0)->npc_ids)/2,sizeof(CharStruct),offsetof(CharStruct,items),offsetof(CharStruct,equipment),offsetof(GameState,money_carried),offsetof(NpcConfig,event_flag),sizeof(NpcConfig));}
''')
    exe = output/'present-layout.exe'
    subprocess.run([str(ROOT/'tools/mingw64/bin/gcc.exe'),'-std=c2x','-I',str(ROOT/'native-source/src'),'-I',str(ROOT/'build/companion/game_lib/generated'),str(code),'-o',str(exe)],check=True,capture_output=True,timeout=60)
    values = list(map(int, subprocess.check_output([str(exe)],text=True).split()))
    if values[3:] != [95,35,49,60,6,17]:
        raise ValueError('Review save and table layout before preparing fixtures')
    return values[:3]


def prepare(folder, base, row, offsets, tamp, full=False, leader=1):
    folder.mkdir();(folder/'saves').mkdir()
    target = folder/'saves'/base[0].name
    shutil.copy2(base[0], target)
    blobs = {k: bytearray(v) for k,v in base[1].items()}
    size, npc_offset, count = offsets
    if len(blobs[14]) != size:
        raise ValueError('Entity section size changed')
    matching = [i for i in range(count) if struct.unpack_from('<H',blobs[14],npc_offset+i*2)[0] == 1415]
    if len(matching) != 1:
        raise ValueError('Fixture must contain exactly one reachable NPC 1415')
    struct.pack_into('<H',blobs[14],npc_offset+matching[0]*2,row['npcId'])
    flag = row['openedFlag']-1
    if flag>=0:blobs[4][flag//8] &= ~(1 << (flag%8))
    # Keep the copied game's existing key-item mode and all unrelated flags.
    # Inventories/pool are test fixtures, never edited owner data.
    for i in range(4):
        start = i*95
        blobs[3][start+35:start+49] = bytes([90 if full else 0]*14)
        blobs[3][start+49:start+53] = bytes(4)
    blobs[43][:] = bytes(len(blobs[43]))
    struct.pack_into('<I',blobs[2],60,0)
    if leader != 1:
        for at in (122,150,156):blobs[2][at:at+6]=bytes([leader,0,0,0,0,0])
        # A not-yet-joined solo Jeff keeps story items in his own inventory.
        blobs[44][0] &= ~(1 << (leader-1))
    write_state(target, blobs, tamp)
    (folder/'fixture.ini').write_text('companion=1\nfullscreen=0\nwidth=1920\nheight=1080\ninstant_text=1\n',encoding='ascii')


def reward_snapshot(folder, state, tamp):
    blobs = sections(latest(folder), tamp)
    items = Counter(i for p in state['party'] for i in p['items'] if i)
    items.update(i for i in blobs[43] if i)
    return {'items':dict(items),'pool':list(blobs[43]),'cash':state['cash'],'flags':state['eventFlags']}


def conversation(folder, run, state, index):
    texts = []
    for attempt in range(12):
        state = observe_step(folder,run,{'button':'confirm','frames':1,'settle':400},index,state)
        texts.extend(w['text'] for w in state['windows'] if w['text'] and w['textSource']=='rendered_this_batch')
        index += 1
        if attempt > 0 and state['modeNames'] == ['OVERWORLD']:
            return state,index,texts
    raise RuntimeError('Present conversation did not return to roaming: '+str(folder))


def execute(folder, run, row, tamp, full=False):
    state = observe_step(folder,run,{'button':None,'frames':1,'settle':80},0)
    if not any(n['id']==row['npcId'] for n in state['npcs']):
        raise RuntimeError('Prepared NPC identity did not survive cold load')
    before = reward_snapshot(folder,state,tamp)
    state,index,texts = conversation(folder,run,state,1)
    after = reward_snapshot(folder,state,tamp)
    bit = lambda s: bool(s['flags'][(row['openedFlag']-1)//8] & (1 << ((row['openedFlag']-1)%8)))
    item,cash = row['itemId'],row['cash']
    flag_backed=bool(state['redux'] and row.get('reduxRewardFlag') and before['flags'][(781-1)//8] & (1 << ((781-1)%8)))
    expected_items=Counter(before['items'])
    if item is not None and not flag_backed:expected_items[item]+=1
    delivered = (after['items']==dict(expected_items) and after['cash']==before['cash']
                 if item is not None else after['items']==before['items'] and after['cash']==before['cash']+cash)
    rejected = full and item is not None and not delivered
    if rejected:
        if bit(after) or after['items'] != before['items'] or after['cash']!=before['cash']:
            raise RuntimeError(f'Full inventory lost reward or closed box: {row["npcId"]}')
        # Leave one normal inventory slot free, preserving the failed attempt.
        save = latest(folder);blobs=sections(save,tamp);blobs[3][35+13]=0;write_state(save,blobs,tamp)
        state=observe_step(folder,run,{'button':None,'frames':1,'settle':80},index,state);index+=1
        before=reward_snapshot(folder,state,tamp)
        state,index,more=conversation(folder,run,state,index);texts+=more
        after=reward_snapshot(folder,state,tamp)
        expected_items=Counter(before['items']);expected_items[item]+=1
        delivered=after['items']==dict(expected_items) and after['cash']==before['cash']
    if not delivered or not bit(after) or bit(before):
        raise RuntimeError(f'Incorrect reward or opened flag: {row["npcId"]}; before={before}; after={after}; text={texts}')
    repeat,index,repeat_texts=conversation(folder,run,state,index)
    repeated=reward_snapshot(folder,repeat,tamp)
    if repeated['items'] != after['items'] or repeated['cash'] != after['cash'] or not bit(repeated):
        raise RuntimeError(f'Repeat duplicated reward: {row["npcId"]}')
    result={'npcId':row['npcId'],'lootValue':row['lootValue'],'openedFlag':row['openedFlag'],
            'rewardPassed':True,'repeatPassed':True,'fullInventoryPrepared':full,
            'fullInventoryRejectedAndRetryPassed':rejected,
            'keyItemBypassedFullInventory':full and not rejected,
            'flagBackedReward':flag_backed,'rewardUnlockFlag':row.get('reduxRewardFlag') if flag_backed else None,
            'ordinaryInputsAfterPreparation':True,'steps':index,'dialogue':texts+repeat_texts}
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def verify_final_rewards(output, results, tamp):
    """Independently reject extra/wrong items in all completed archived cases."""
    for result in results:
        folder=output/f'{result["profile"]}-{result["npcId"]}{"-full" if result["fullInventoryPrepared"] else ""}'
        initial=json.loads((folder/'0000/state.json').read_text())
        final=json.loads((folder/'last-state.json').read_text())
        initial_save=max((folder/'0001/before-saves').glob('quicksave_1.bin.*'),key=lambda p:struct.unpack_from('<I',p.read_bytes(),8)[0])
        initial_items=Counter(i for member in initial['party'] for i in member['items'] if i)
        initial_items.update(i for i in sections(initial_save,tamp)[43] if i)
        expected=initial_items.copy()
        if result['fullInventoryRejectedAndRetryPassed']:expected[90]-=1
        loot=result['lootValue']
        if loot<256 and not result.get('flagBackedReward'):expected[loot]+=1
        if result.get('flagBackedReward'):
            bit=result['rewardUnlockFlag']-1
            if initial['eventFlags'][bit//8] & (1 << (bit%8)) or not final['eventFlags'][bit//8] & (1 << (bit%8)):
                raise RuntimeError('Flag-backed reward was not newly unlocked: '+folder.name)
        expected=+expected
        actual=Counter(i for member in final['party'] for i in member['items'] if i)
        actual.update(i for i in sections(latest(folder),tamp)[43] if i)
        cash=initial['cash']+(loot-256 if loot>=256 else 0)
        if actual!=expected or final['cash']!=cash or final['modeNames']!=['OVERWORLD']:
            raise RuntimeError(f'Independent final reward mismatch: {folder.name}')
        result['ExactFinalInventoryAndCashPassed']=True
    return True


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('original','redux','compiled-rom','original-rom','project','checkpoint','engine','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--limit',type=int,default=0,help='Smoke check only; report explicitly says incomplete')
    p.add_argument('--profile',choices=('original','redux','both'),default='both')
    p.add_argument('--include-full-inventory',action='store_true')
    p.add_argument('--workers',type=int,default=4,choices=range(1,9),help='Independent scratch cases; immutable runtimes shared read-only')
    p.add_argument('--resume',action='store_true',help='Preserve completed cases; require identical immutable runtimes')
    a=p.parse_args();output=local_scratch(a.output)
    if output.exists() and not a.resume:raise ValueError('Use a fresh scratch output or explicitly resume')
    output.mkdir(parents=True,exist_ok=a.resume)
    rows,orig,red=catalog(a.original,a.redux,a.compiled_rom,a.project,a.original_rom)
    (output/'catalog.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
    offsets=layout(output)
    sys.path.insert(0,str(ROOT/'native-source/src/vendor/tamp'));import tamp
    save=latest(local_scratch(a.checkpoint));base=(save,sections(save,tamp))
    runtime=output/'runtime';runtime.mkdir(exist_ok=a.resume)
    for f in (a.engine,a.engine.with_name('SDL2.dll')):
        if a.resume:
            if sha(f)!=sha(runtime/f.name):raise ValueError('Resume engine changed')
        else:shutil.copy2(f,runtime/f.name)
    profiles={'original':a.original,'redux':a.redux}
    if a.profile!='both':profiles={a.profile:profiles[a.profile]}
    results=[];started=time.monotonic();jobs=[]
    for profile,pack in profiles.items():
        frozen=runtime/(profile+'.pak')
        if a.resume:
            if sha(pack)!=sha(frozen):raise ValueError('Resume asset pack changed')
        else:shutil.copy2(pack,frozen)
        run={'schema':1,'nativeExe':str(runtime/a.engine.name),'assets':str(frozen),'modeNames':mode_names(),
             'nativeExeSha256':sha(a.engine),'assetsSha256':sha(frozen),'ordinaryInputsOnly':True,
             'seededFixture':True,'fullPlaythroughVerified':False}
        for row in rows[:a.limit or len(rows)]:
            row=dict(row)
            if profile=='original':
                row['lootValue']=row['originalLootValue']
                row['itemId']=row['lootValue'] if row['lootValue']<256 else None
                row['cash']=row['lootValue']-256 if row['lootValue']>=256 else None
            for full in ([False,True] if a.include_full_inventory and row['itemId'] is not None else [False]):
                folder=output/f'{profile}-{row["npcId"]}{"-full" if full else ""}'
                if a.resume and (folder/'result.json').exists():
                    result=json.loads((folder/'result.json').read_text());result['profile']=profile
                    if result['npcId']!=row['npcId'] or result['lootValue']!=row['lootValue'] or not result['rewardPassed'] or not result['repeatPassed']:
                        raise ValueError('Completed case metadata changed')
                    results.append(result);continue
                if folder.exists():
                    target=output/(folder.name+'-incomplete-preserved')
                    if target.exists() or not folder.resolve().is_relative_to(output) or not target.resolve().is_relative_to(output):
                        raise ValueError('Preserve incomplete fixture; choose a fresh output')
                    local_scratch(folder);local_scratch(target);folder.rename(target)
                jobs.append((folder,dict(run),row,full,profile))
    def job(case):
        folder,run,row,full,profile=case
        prepare(folder,base,row,offsets,tamp,full)
        (folder/'run.json').write_text(json.dumps(run,indent=2)+'\n',encoding='utf-8')
        result=execute(folder,run,row,tamp,full);result['profile']=profile
        return result
    pending={};iterator=iter(jobs)
    with ThreadPoolExecutor(max_workers=a.workers) as executor:
        for _ in range(a.workers):
            case=next(iterator,None)
            if case is not None:pending[executor.submit(job,case)]=case
        while pending:
            done,_=wait(pending,return_when=FIRST_COMPLETED)
            for future in done:
                del pending[future]
                result=future.result();results.append(result)
                case=next(iterator,None)
                if case is not None:pending[executor.submit(job,case)]=case
                if len(results)%10==0:
                    print(json.dumps({'completedCases':len(results),'remainingNewCases':len(jobs),'profile':result['profile'],'npc':result['npcId'],'seconds':round(time.monotonic()-started)}),flush=True)
                    (output/'partial-results.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    results.sort(key=lambda r:(r['profile'],r['npcId'],r['fullInventoryPrepared']))
    verify_final_rewards(output,results,tamp)
    report={'Passed':True,'CompleteCatalogReplay':not a.limit,'format':'all-present-catalog-and-native-replay-v1',
            'PresentRecordsPerProfile':len(rows),'PlacedContainersPerProfile':sum(len(r['placements']) for r in rows),
            'ItemContainers':sum(r['itemId'] is not None for r in rows),'CashContainers':sum((r['cash'] or 0)>0 for r in rows),
            'SourceEmptyContainers':[r['npcId'] for r in rows if r['cash']==0],
            'UniqueOpenedFlags':len({r['openedFlag'] for r in rows}),
            'CatalogMatchesCompiledROMAndSource':True,'OriginalLootMatchesRetailROM':True,
            'SourceLootChanges':[{'npcId':r['npcId'],'original':r['originalLootValue'],'redux':r['lootValue']} for r in rows if r['originalLootValue']!=r['lootValue']],
            'PlacementsMatchSourceInBothPacks':True,'ProfilesReplayed':list(profiles),
            'NativeExeSha256':sha(a.engine),'OriginalPackSha256':sha(a.original),'ReduxPackSha256':sha(a.redux),
            'CompiledROMSha256':sha(a.compiled_rom),'Cases':results,
            'TypeSafeRequests':0,'OwnerSavesWritten':False,'FullPlaythroughVerified':False,
            'Boundary':'Prepared scratch states substitute one reachable NPC identity and clear its own opened flag; inventories/pool/cash are fixtures. Unmodified packs and normal confirm inputs execute each actual reward script. World placement data is compared exhaustively, but rooms and story conditions were not walked.'}
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'Passed':True,'complete':not a.limit,'records':len(rows),'cases':len(results)}))


if __name__=='__main__':main()
