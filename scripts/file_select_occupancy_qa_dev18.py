# SPDX-License-Identifier: GPL-3.0-or-later
"""Pure occupancy and actual warm/cold menus over local checksum controls.

No shared source/build or owner data is modified. Private SRAM fixtures copy a
real native phone seed and damage checksum headers only, or clear blocks while
retaining its existing global SRAM tail. Reports publish metadata, not payload.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from check_jev_observer_parity import local_scratch
import redux_title_cold_qa_dev18 as qa
import file_select_cold_qa_dev18 as focused
import redux_title_producers_qa_dev18 as producers

ROOT=Path(__file__).resolve().parents[1]
PEEK_DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game/game_state.h"
#include "game/maternalbound.h"
#include "entity/entity.h"
extern int eb_platform_main(int,char**);
int main(int argc,char**argv){
 if(argc!=4)return 2;char*boot[]={"private-pure-occupancy","--assets",argv[1],"--session-dir",argv[2],"--save",argv[3],"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};if(eb_platform_main(12,boot))return 3;
 EntityRuntimeState*entity=malloc(sizeof(ert));if(!entity)return 4;
 for(int slot=-1;slot<=3;slot++){
  GameState game=game_state;CharStruct chars[TOTAL_PARTY_COUNT];uint8_t flags[sizeof(event_flags)],pool[sizeof(key_items_pool)],names[sizeof(maternalbound_name_extra)],food[sizeof(maternalbound_food_extra)];memcpy(chars,party_characters,sizeof(chars));memcpy(flags,event_flags,sizeof(flags));memcpy(pool,key_items_pool,sizeof(pool));memcpy(names,maternalbound_name_extra,sizeof(names));memcpy(food,maternalbound_food_extra,sizeof(food));memcpy(entity,&ert,sizeof(ert));unsigned mask=party_ever_joined_mask,current=current_save_slot;
  unsigned actual=save_game_slot_occupied(slot);unsigned mutated=memcmp(&game,&game_state,sizeof(game))||memcmp(chars,party_characters,sizeof(chars))||memcmp(flags,event_flags,sizeof(flags))||memcmp(pool,key_items_pool,sizeof(pool))||memcmp(names,maternalbound_name_extra,sizeof(names))||memcmp(food,maternalbound_food_extra,sizeof(food))||memcmp(entity,&ert,sizeof(ert))||mask!=party_ever_joined_mask||current!=current_save_slot;
  unsigned source=load_game(slot)&&game_state.favourite_thing[1]!=0;printf("PEEK [%d,%u,%u,%u]\n",slot,actual,source,mutated);
 }
 free(entity);return 0;
}
'''

def fixtures(phone,out):
    data=phone.read_bytes()
    if len(data)!=8192:raise ValueError('Expected actual native 8KB phone SRAM seed')
    block=1280;cases={}
    def add(name,payload,occupied,copy_present):
        path=out/(name+'.srm');path.write_bytes(payload);cases[name]=dict(path=path,sha256=qa.sha(path),occupied=occupied,copyPresent=copy_present)
    add('one-occupied',data,[1,0,0],True)
    full=bytearray(data)
    for index in range(6):full[index*block:(index+1)*block]=data[:block]
    add('all-three-occupied',full,[1,1,1],False)
    empty=bytearray(data);empty[:6*block]=bytes(6*block);add('valid-empty-slots',empty,[0,0,0],None)
    primary=bytearray(data);primary[28]^=1;add('damaged-primary-valid-secondary',primary,[1,0,0],True)
    both=bytearray(primary);both[block+28]^=1;add('both-copies-damaged',both,[0,0,0],None)
    secondary=bytearray(data);secondary[block+28]^=1;add('valid-primary-damaged-secondary',secondary,[1,0,0],True)
    firstempty=bytearray(data);firstempty[:block]=bytes(block);add('valid-empty-primary-occupied-secondary',firstempty,[0,0,0],None)
    return cases

def menu_labels(session):
    # Native diagnostic emits actual serialized window MenuItem labels.
    log=(session.folder/f'{session.count:03d}-{session.qa_label}.log').read_text(encoding='utf-8')
    line=next((line for line in log.splitlines() if line.startswith('PC replay window 20 ')),None)
    return dict(line=line,copyPresent=bool(line and '[2:Copy]' in line))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('source','builds','runtime','original-assets','redux-assets','original-phone-seed','redux-phone-seed','scratch','output'):ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args()
    for n,v in vars(a).items():setattr(a,n,v.resolve())
    a.scratch=local_scratch(a.scratch)
    if a.scratch.exists() or a.output.exists():raise ValueError('Fresh private scratch/report required')
    a.scratch.mkdir();sys.path.insert(0,str(a.source/'src/vendor/tamp'));import tamp
    l=qa.layout(a.source,ROOT/'tools/mingw64/bin/gcc.exe',a.builds/'player',a.scratch);results=[];producers.DRIVER=PEEK_DRIVER
    for mode in ('player','observer'):
        exe=a.runtime/(mode+'.exe');driver,linkid=producers.link(a.source,a.builds/mode,a.runtime,a.scratch/(mode+'-peek-link'))
        if qa.sha(exe)!=qa.sha(a.builds/mode/'earthbound.exe'):raise ValueError('Complete executable/build mismatch')
        for profile,pack,phone in (('original',a.original_assets,a.original_phone_seed),('redux',a.redux_assets,a.redux_phone_seed)):
            parent=a.scratch/(mode+'-'+profile);parent.mkdir();fixture_dir=parent/'fixtures';fixture_dir.mkdir();cases=fixtures(phone,fixture_dir);_,_,assets=qa.read_pack(pack,a.source/'src/data/runtime_generated/asset_ids.h')
            for case_name,case in cases.items():
                path=case['path'];pure_dir=parent/(case_name+'-peek');pure_dir.mkdir();before=qa.sha(path)
                proc=qa.subprocess.run([str(driver),str(pack),str(pure_dir),str(path)],cwd=driver.parent,env=dict(os.environ,SDL_AUDIODRIVER='dummy',SDL_VIDEODRIVER='dummy'),capture_output=True,timeout=60);log=pure_dir/'native.log';log.write_bytes(proc.stdout+proc.stderr)
                if proc.returncode or qa.sha(path)!=before:raise ValueError('Pure occupancy control failed: '+str(log))
                rows=[json.loads(line[5:]) for line in proc.stdout.decode(errors='replace').splitlines() if line.startswith('PEEK ')]
                if len(rows)!=5:raise ValueError('Pure occupancy corpus incomplete')
                pure_pass=all(row[1]==row[2] and not row[3] and row[1]==([0]+case['occupied']+[0])[row[0]+1] for row in rows)
                warm=focused.boot_case(exe,pack,parent,case_name+'-warm',path,l,tamp,focused.first_rows(1400),1450,assets);warm.qa_label=case_name+'-warm';warm_sub=any(r['id']==20 for r in warm.last['titles']);warm_new=any(r['id']==24 for r in warm.last['titles']);warm_labels=menu_labels(warm)
                cold=focused.boot_case(exe,pack,parent,case_name+'-cold',path,l,tamp,focused.first_rows(),1300,assets);pre=dict(cold.last);phone_before=qa.sha(cold.folder/'fixture.srm');cold.step('actual-cold-file-select-same-slot',[qa.naming.CONFIRM],wait=130);cold.qa_label='actual-cold-file-select-same-slot';cold_sub=any(r['id']==20 for r in cold.last['titles']);cold_new=any(r['id']==24 for r in cold.last['titles']);cold_labels=menu_labels(cold);phone_same=phone_before==qa.sha(cold.folder/'fixture.srm')==before
                occupied=bool(case['occupied'][0]);menu_pass=(warm_sub==occupied and cold_sub==occupied and warm_new!=occupied and cold_new!=occupied and phone_same)
                if occupied:menu_pass &= warm_labels['copyPresent']==cold_labels['copyPresent']==case['copyPresent']
                normal=None
                if occupied:
                    normal=focused.boot_case(exe,pack,parent,case_name+'-normal-continue',path,l,tamp,focused.first_rows(1600),2200,assets);menu_pass &= normal.last['modes']==[l['worldMode']] and normal.last['partyCount']==1
                row=dict(build=mode,profile=profile,case=case_name,fixtureSha256=before,expectedOccupiedSlots=case['occupied'],purePeek=dict(link=linkid,records=rows,nativeLogSha256=qa.sha(log),Passed=pure_pass,comparedLiveGlobals=['GameState','all CharStructs','event_flags','key_items_pool','maternalbound_name_extra','maternalbound_food_extra','EntityRuntimeState including save_scratch','party_ever_joined_mask','current_save_slot']),warm=dict(sourceSubmenu=warm_sub,sourceNewGame=warm_new,menu=warm_labels),cold=dict(beforeModes=pre['modes'],afterModes=cold.last['modes'],sourceSubmenu=cold_sub,sourceNewGame=cold_new,menu=cold_labels,sameExternalPhonePath=str((cold.folder/'fixture.srm').resolve()),externalPhoneBytesPreserved=phone_same),normalPhoneContinue=None if normal is None else dict(worldReached=normal.last['modes']==[l['worldMode']],partyCount=normal.last['partyCount']),Passed=pure_pass and menu_pass)
                results.append(row);print(json.dumps(dict(completed=mode+'-'+profile+'-'+case_name,Passed=row['Passed'])),flush=True)
    report=dict(format='actual-complete-phone-occupancy-warm-cold-dev18-v1',toolSha256=qa.sha(Path(__file__)),pureDriverSha256=qa.hashlib.sha256(PEEK_DRIVER.encode()).hexdigest(),results=results,allPassed=all(r['Passed'] for r in results),candidateSourceIdentities={p:qa.sha(a.source/p) for p in ('src/game/game_state.c','src/game/game_state.h','src/intro/file_select.c','src/core/state_dump.c')},completeCandidateBinaries={n:qa.sha(a.runtime/(n+'.exe')) for n in ('player','observer')},dependencies={p:qa.sha(ROOT/p) for p in ('tools/file_select_cold_qa_dev18.py','tools/redux_title_cold_qa_dev18.py','tools/redux_title_producers_qa_dev18.py')},limits=['Actual candidate archives run pure occupancy against the existing load_game checksum/sentinel contract; the reference is native source, not an independent original CPU SRAM routine.', 'Five slot indices (-1,0,1,2,3), seven local checksum/copy/empty patterns, two profiles and both complete binaries are covered. Source Copy availability is observed, but actual Copy/Delete actions and every configuration phase are not executed.', 'Real occupied/empty slot selection, F6 writer/fresh cold restore and normal phone Continue are driven through complete executables; private fixture checksum/header changes are stated prerequisites, not naturally produced story saves.', 'Live global purity is checked on each direct peek, including save_scratch. Format16 is unchanged; physical F6 is not synthesized. Frozen title proposal and root/source/builds/owner data remain untouched.', 'Ordinary file-slot menu labels still convert extended names through eb_char_to_ascii. Their glyph loss is separate from title-only rendering and is not silently fixed by this proposal.'],rootOrOwnerInputsModified=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(allPassed=report['allPassed'],report=str(a.output),sha256=qa.sha(a.output))))

if __name__=='__main__':main()
