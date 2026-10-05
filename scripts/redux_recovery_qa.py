# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared native rest-script checks; no player saves or Jev requests.

The fixture changes one scratch NPC's text pointer and prepares scratch party
ailments/HP/PP/stamina. It tests the real converted recovery bodies, not ordinary
story progress. Source and engine hashes are recorded with every result.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from types import SimpleNamespace

from build_maternalbound_pack import read_pack, write_pack
from check_jev_observer_parity import latest, local_scratch, sections
from jev_gameplay_runner import initialize, load_run, observe_step, sha

ROOT = Path(__file__).resolve().parents[1]
HOOKS = {'hotel': 0xC91582, 'full': 0xC915F4, 'spring': 0xC9162C}


def layout(native, generated, compiler, output):
    source = output/'recovery-layout.c'
    source.write_text('''#include <stdio.h>
#include <stddef.h>
#include "game/game_state.h"
#include "game/overworld.h"
#define FIELD(T,F) printf("\\\"" #F "\\\":%zu,",offsetof(T,F))
int main(void) {
 printf("{\\\"characterSize\\\":%zu,",sizeof(CharStruct));
 FIELD(OverworldState,redux_primary_timer); FIELD(OverworldState,redux_secondary_timer);
 printf("\\\"overworldSize\\\":%zu}",sizeof(OverworldState)); return 0;
}
''', encoding='utf-8')
    exe = output/'recovery-layout.exe'
    compiled=subprocess.run([str(compiler), '-std=c2x', '-I',str(native/'src'),'-I',str(generated),str(source),'-o',str(exe)],capture_output=True,timeout=60)
    if compiled.returncode:raise RuntimeError(compiled.stderr.decode(errors='replace'))
    result=json.loads(subprocess.check_output([str(exe)],timeout=10))
    if result['characterSize'] != 95 or result['overworldSize'] != 392:
        raise ValueError('Review state layout before preparing fixtures.')
    return result


def write_state(path, blobs, tamp):
    header=bytearray(path.read_bytes()[:20])
    raw=b''.join(struct.pack('<HI',tag,len(data))+data for tag,data in blobs.items())+b'\xff\xff'
    payload=tamp.compress(raw,window=8,literal=8,extended=False)
    # State format 16 uses upstream's 0xEDB88420 polynomial, despite its
    # CRC-32 comment. Preserve that on-disk contract; zlib uses 0xEDB88320.
    crc=0xffffffff
    for byte in payload:
        crc ^= byte
        for _ in range(8):crc=(crc>>1) ^ (0xEDB88420 if crc&1 else 0)
    struct.pack_into('<II',header,12,crc^0xffffffff,len(payload))
    path.write_bytes(header+payload)


def prepare(source, output, rotation, offsets, tamp):
    output.mkdir()
    (output/'saves').mkdir()
    save=latest(source)
    target=output/'saves'/save.name
    shutil.copy2(save,target)
    shutil.copy2(source/'fixture.srm',output/'fixture.srm')
    blobs=sections(target,tamp)
    gs,party,ow=blobs[2],blobs[3],blobs[5]
    for start in (122,150,156): gs[start:start+6]=bytes((1,2,3,4,0,0))
    gs[174]=gs[175]=4
    # Conscious but poisoned/cold/homesick, unconscious, diamondized, healthy.
    conditions=([3,1,0,0,0,1,0],[1,1,0,0,0,1,0],[2,1,0,0,0,1,0],[0]*7)
    for i in range(4):
        base=i*95; ailments=conditions[(i+rotation)%4]
        party[base+14:base+21]=bytes(ailments)
        for offset,value in ((10,100+20*i),(12,40+10*i),(67,0),(69,0 if ailments[0]==1 else 10),(71,0 if ailments[0]==1 else 10),(73,0),(75,2),(77,2)):
            struct.pack_into('<H',party,base+offset,value)
    ow[offsets['redux_primary_timer']]=128
    ow[offsets['redux_secondary_timer']]=120
    write_state(target,blobs,tamp)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','engine','checkpoint','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--native-source',type=Path,default=ROOT/'native-source')
    p.add_argument('--compiler',type=Path,default=ROOT/'tools/mingw64/bin/gcc.exe')
    p.add_argument('--generated-headers',type=Path,default=ROOT/'build/companion/game_lib/generated')
    p.add_argument('--expect-reset',action='store_true')
    a=p.parse_args();output=local_scratch(a.output)
    if output.exists():raise ValueError('Use a fresh scratch output.')
    output.mkdir(parents=True)
    sys.path.insert(0,str(a.native_source/'src/vendor/tamp'))
    import tamp
    offsets=layout(a.native_source.resolve(),a.generated_headers.resolve(),a.compiler.resolve(),output)
    state_source=(a.native_source/'src/core/state_dump.c').read_text(encoding='utf-8')
    if '0xEDB88420u &' not in state_source:raise ValueError('Review the state checksum contract.')
    entries,header,assets=read_pack(a.assets, a.native_source/'src/data/runtime_generated/asset_ids.h')
    blob=assets['dialogue/dialogue.bin']
    _,version,mapoff,count,*_=struct.unpack_from('<8s6I',blob,len(blob)-32)
    if version != 2:raise ValueError('Expected version 2 Redux mapping.')
    mapping=dict(struct.iter_unpack('<II',blob[mapoff:mapoff+count*8]))
    rows=[]
    for kind,address in HOOKS.items():
        npc=bytearray(assets['data/npc_config_table.bin'])
        npc[1415*17]=3
        struct.pack_into('<I',npc,1415*17+9,mapping[address])
        fixture=dict(assets,**{'data/npc_config_table.bin':bytes(npc)})
        pack=output/(kind+'.pak');write_pack(pack,entries,header,fixture)
        for rotation in range(4):
            name=f'{output.name}-{kind}-{rotation}'
            checkpoint=output/f'checkpoint-{kind}-{rotation}'
            prepare(local_scratch(a.checkpoint),checkpoint,rotation,offsets,tamp)
            run_path=ROOT/'_BuildScratch/jev-runs'/name
            initialize(SimpleNamespace(directory=run_path,checkpoint=checkpoint,native_exe=a.engine.resolve(),assets=pack,fixture_checkpoint=True))
            folder,run=load_run(run_path)
            before=observe_step(folder,run,{'button':None,'frames':1,'settle':80},0)
            if before['partyCount']!=4 or [c['maxHp'] for c in before['party']]!=[100,120,140,160]:
                raise RuntimeError(name+': prepared party did not load')
            initial_state=sections(latest(folder),tamp)
            stamina_before=[initial_state[5][offsets[key]] for key in ('redux_primary_timer','redux_secondary_timer')]
            if stamina_before[1]&128:raise RuntimeError(name+': fixture recovered before interaction')
            after=observe_step(folder,run,{'button':'confirm','frames':1,'settle':200},1,before)
            # Recovery scripts contain no prompts. Return to roaming naturally.
            if after['modeNames'] != ['OVERWORLD']:raise RuntimeError(name+': recovery did not finish')
            final=sections(latest(folder),tamp)
            stamina=list(final[5][offsets[key]] for key in ('redux_primary_timer','redux_secondary_timer'))
            healing=True
            for old,new in zip(before['party'],after['party']):
                is_unconscious=old['afflictions'][0]==1
                is_diamond=old['afflictions'][0]==2
                hp,pp,ail=old['hp'],old['pp'],old['afflictions'][:]
                if kind=='full' or (kind=='hotel' and not(is_unconscious or is_diamond)) or (kind=='spring' and is_unconscious):
                    hp,pp=new['maxHp'],new['maxPp']
                if kind in ('full','spring'):
                    for group in (0,1,5):ail[group]=0
                healing &= (new['hp'],new['pp'],new['afflictions'])==(hp,pp,ail)
            reset=stamina==[191,143]
            row={'kind':kind,'rotation':rotation,'entryAddress':f'{address:06X}',
                 'nativeEntryAddress':mapping[address],'nativeExeSha256':run['nativeExeSha256'],
                 'preparedPackSha256':run['assetsSha256'],'returnedToRoaming':True,
                 'healingRulesPassed':healing,'staminaReset':reset,'staminaAfter':stamina,
                 'staminaBefore':stamina_before,
                 'before':before['party'],'after':after['party']}
            rows.append(row)
            (output/'partial-results.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
            if not healing or reset!=a.expect_reset:raise RuntimeError(name+': unexpected healing/reset result')
    report={'Passed':True,'format':'redux-recovery-prepared-fixtures-v1','cases':rows,
            'expectStaminaReset':a.expect_reset,'basePackSha256':sha(a.assets),'TypeSafeRequests':0,
            'OwnerSavesWritten':False,'FullPlaythroughVerified':False,
            'FixtureBoundary':'One scratch NPC invokes a real converted rest entry; scratch saves set four party members, HP/PP, ailments and depleted stamina. No ordinary story progress is claimed.'}
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'Passed':True,'recoveryCases':len(rows),'staminaReset':a.expect_reset}))


if __name__=='__main__':main()
