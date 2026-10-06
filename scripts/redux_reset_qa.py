# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared native Dad/Gauss record-Continue/End and cold reset checks.

Only fresh private state-format-16 fixtures under _BuildScratch are prepared.
Entry readers mirror dt_setup_init; flags/party prerequisites come from pinned
source. Actual dialogue, save, choice, fade, reset and boot modes execute natively.
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

from build_maternalbound_pack import read_pack
from check_jev_observer_parity import latest, local_scratch, sections
from redux_recovery_qa import write_state
import redux_naming_qa as naming

ROOT=Path(__file__).resolve().parents[1]
PIN='897d00833f4a08a0a92f106abf631629a6a6a041'
CONFIRM,RIGHT=0x20,0x100


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def layout(native,compiler,out):
    src=out/'reset-layout.c';exe=out/'reset-layout.exe'
    src.write_text(r'''#include <stdio.h>
#include <stddef.h>
#include "core/mode_stack.h"
#include "game/game_state.h"
#define F(T,N) printf("\"" #T "." #N "\":%zu,",offsetof(T,N))
int main(void){printf("{");
 F(GameState,party_members);F(GameState,party_order);F(GameState,player_controlled_party_members);
 F(GameState,party_count);F(GameState,player_controlled_party_count);F(GameState,current_party_members);
 F(DisplayTextModeState,phase);F(DisplayTextModeState,reader);
 F(DisplayTextState,text_prompt_waiting_for_input);F(TextPromptState,phase);
 F(ScriptReader,source);F(ScriptReader,ptr_off);F(ScriptReader,end_off);F(ScriptReader,prefix_off);
 printf("\"displayMode\":%u,\"introMode\":%u,\"titleMode\":%u,\"fileMode\":%u,\"textEnter\":%u,\"dialogueSource\":%u,\"promptMode\":%u,\"fadeMode\":%u,\"delayMode\":%u}",
 GAME_MODE_DISPLAY_TEXT,GAME_MODE_INIT_INTRO,GAME_MODE_TITLE_SCREEN,GAME_MODE_FILE_MENU,DT_ENTER,TEXT_SRC_DIALOGUE,GAME_MODE_TEXT_PROMPT,GAME_MODE_FADE_WAIT,GAME_MODE_TEXT_DELAY);
return 0;}''',encoding='utf-8')
    p=subprocess.run([str(compiler),'-std=c2x','-I',str(native/'src'),'-I',str(ROOT/'build/companion/game_lib/generated'),str(src),'-o',str(exe)],capture_output=True,timeout=45)
    if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace'))
    result=naming.compile_layout(native,compiler,out)
    result.update(json.loads(subprocess.check_output([str(exe)],timeout=10)))
    return result


class ResetSession(naming.Session):
    def run(self,label,rows,frame,load=True,entry=None,dump=False):
        self.count+=1;prefix=f'{self.count:03d}-{label}';replay=self.folder/'inputs.replay'
        replay.write_text('\n'.join(f'{f} {pad:04X}' for f,pad in sorted(rows))+'\n',encoding='ascii')
        cmd=[str(self.exe),'--assets',str(self.pak),'--session-dir',str(self.folder),'--save',str(self.folder/'fixture.srm'),
             '--config',str(self.config),'--allow-redux-development','--windowed' if dump else '--headless','--fast-forward',
             '--input-script',str(replay),'--frames',str(frame+5),'--capture-state',str(frame)]
        if load:cmd+=['--load-state']
        elif entry:cmd+=['--redux-dialogue-fixture',hex(entry)]
        if dump:cmd+=['--dump-frame',str(frame+1)]
        p=subprocess.run(cmd,env=self.env,capture_output=True,timeout=60)
        self.log=(p.stdout+p.stderr).decode(errors='replace');(self.folder/(prefix+'.log')).write_text(self.log,encoding='utf-8')
        if p.returncode or 'savestate: wrote slot' not in self.log or re.search(r'\b(FATAL|unimplemented|unknown opcode|unknown bank|ERROR)\b',self.log,re.I):
            raise RuntimeError(prefix+': '+self.log[-1800:])
        self.blobs=sections(latest(self.folder),self.tamp);result=self.read()
        l=self.layout;gs=self.blobs[2]
        result['partyIds']=list(gs[l['GameState.party_members']:l['GameState.party_members']+6])
        result['menus']=re.findall(r'PC replay window[^\r\n]*menu: ([^\r\n]+)',self.log)
        result['phoneSaveExists']=(self.folder/'fixture.srm').exists()
        result['textInputLock']=struct.unpack_from('<H',self.blobs[7],self.layout['DisplayTextState.text_prompt_waiting_for_input'])[0]
        ms=self.blobs[21];result['displayReaders']=[];result['promptPhases']=[]
        for index,mode in enumerate(result['modes']):
            at=l['ModeStack.state']+index*l['ModeState.size']
            if mode==l['displayMode']:
                reader=at+l['DisplayTextModeState.reader']
                result['displayReaders'].append(struct.unpack_from('<I',ms,reader+l['ScriptReader.ptr_off'])[0])
            if mode==l['promptMode']:
                result['promptPhases'].append(ms[at+l['TextPromptState.phase']])
        self.last=result;(self.folder/(prefix+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        return result


def prerequisites(project):
    flag_text=(project/'ccscript/definitions/flags.ccs').read_text(encoding='utf-8-sig')
    names=('FLG_ITEM_GAUS','FLG_JEFF','FLG_THRK_URBAN_ZOMBI_GONE','FLG_WIN_GIEGU','FLG_PHONE_PAPA_FINAL','FLG_STEP_PAST')
    flags={n:int(re.search(r'define\s+'+n+r'\s*=\s*flag\s+(\d+)',flag_text)[1]) for n in names}
    source={name:(project/f'ccscript/data/data_{name}.ccs').read_text(encoding='utf-8-sig') for name in ('18','19','22')}
    for token in ('l_0xc631e3:','cc_asmcall(reset_routine.Reset, RET_NONE)','two_choice_menu("Continue", l_0xc631a1, "End", l_0xc631e3)'):
        if token not in source['18']:raise ValueError('Gauss record/End source changed: '+token)
    for token in ('l_0xc63506:','cc_asmcall(reset_routine.Reset, RET_NONE)','two_choice_menu("Continue", l_0xc634b4, "End", l_0xc63506)'):
        if token not in source['19']:raise ValueError('Dad record/End source changed: '+token)
    if 'call(data_18.l_0xc630ae)' not in source['22']:raise ValueError('Gauss phone caller changed')
    return flags


def prepare(session,entry,kind,assets,flags):
    # Initial native fixture creates actual world/window machinery. Re-seed a
    # fresh full-entry reader using the production dt_setup_init constructor.
    session.run('native-world-window-seed',[(0,0)],0,load=False,entry=0xC63229)
    state=latest(session.folder);blobs=sections(state,session.tamp);l=session.layout
    dialogue=assets['dialogue/dialogue.bin'];footer=dialogue[-32:]
    if footer[:8]!=b'MRDXNV01':raise ValueError('Redux dialogue footer missing')
    mapoff,count=struct.unpack_from('<II',footer,12)
    mapping=dict(struct.unpack_from('<II',dialogue,mapoff+i*8) for i in range(count))
    if entry not in mapping:raise ValueError('Full phone entry has no relocation')
    ms=blobs[21];ms[l['ModeStack.depth']]=2
    # File menu assigns the selected 1-indexed slot. The isolated world fixture
    # bypasses file selection, so supply that explicit required save context.
    if len(blobs[26])!=1:raise ValueError('Review current_save_slot ABI')
    blobs[26][0]=1
    ms[l['ModeStack.mode']+1]=l['displayMode']
    at=l['ModeStack.state']+l['ModeState.size'];ms[at:at+l['ModeState.size']]=bytes(l['ModeState.size'])
    ms[at+l['DisplayTextModeState.phase']]=l['textEnter']
    reader=at+l['DisplayTextModeState.reader'];ms[reader+l['ScriptReader.source']]=l['dialogueSource']
    struct.pack_into('<IIi',ms,reader+l['ScriptReader.ptr_off'],mapping[entry]-0x100000,len(dialogue),-1)
    def flag(name,on):
        # game_state.c GET/SET_EVENT_FLAG decrement source IDs before bit
        # indexing; flags are 1-indexed, including Gauss's flag88.
        n=flags[name]-1
        if on:blobs[4][n//8]|=1<<(n%8)
        else:blobs[4][n//8]&=255^(1<<(n%8))
    for name in ('FLG_WIN_GIEGU','FLG_PHONE_PAPA_FINAL','FLG_STEP_PAST'):flag(name,False)
    if kind=='gauss':
        flag('FLG_ITEM_GAUS',True);flag('FLG_JEFF',False);flag('FLG_THRK_URBAN_ZOMBI_GONE',False)
        gs=blobs[2]
        for field in ('party_members','player_controlled_party_members','party_order'):
            offset=l['GameState.'+field];gs[offset:offset+6]=bytes(6);gs[offset]=3
        gs[l['GameState.party_count']]=gs[l['GameState.player_controlled_party_count']]=1
        struct.pack_into('<H',gs,l['GameState.current_party_members'],4)
        # Jeff remains the source-defined character3; name storage ABI unchanged.
        char=l['CharStruct.size']*2+l['CharStruct.name'];blobs[3][char:char+5]=bytes((0x7A,0x95,0x96,0x96,0));blobs[45][2]=0
    write_state(state,blobs,session.tamp)
    session.step('full-native-phone-entry')


def reach_choice(session):
    for i in range(160):
        if any('[1:Continue] [2:End]' in m for m in session.last['menus']):return
        session.step('advance-phone-'+str(i),[CONFIRM],wait=45)
    raise RuntimeError('Native phone flow did not reach Continue/End: '+str(session.last))


def guard_checks(native,compiler,out,dialogue):
    """Compile the actual adapter, checking every lock-byte candidate plus
    suffix corruption and non-Redux binding. No substitute Python predicate."""
    source=out/'reset-guard.c';exe=out/'reset-guard.exe';data=out/'private-dialogue.bin'
    data.write_bytes(dialogue)
    # Link only the verbatim mapping/binding/guard function bodies. Windows PE
    # unwind sections otherwise retain unrelated gameplay symbols from this
    # module. These four functions have no game-state dependencies or mocks.
    native_text=(native/'src/game/maternalbound.c').read_text(encoding='utf-8')
    names=('redux_u32','maternalbound_bind_dialogue','maternalbound_resolve_entry','maternalbound_gauss_reset_prompt')
    bodies=[]
    for name in names:
        match=re.search(r'^(?:static )?(?:uint32_t|bool) '+name+r'\([^\n]*\) \{',native_text,re.M)
        if not match:raise ValueError('Review guard function signature: '+name)
        start=match.start();at=match.end();depth=1
        while depth:
            if native_text[at]=='{':depth+=1
            elif native_text[at]=='}':depth-=1
            at+=1
        bodies.append(native_text[start:at])
    harness=r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game/maternalbound.h"
static const uint8_t *redux_blob;
static uint32_t redux_map_offset,redux_map_count,redux_determiner_offset,redux_determiner_size;
'''+ '\n'.join(bodies)+r'''
int main(int argc,char **argv) {
 if(argc!=2)return 2; FILE *f=fopen(argv[1],"rb");if(!f)return 3;
 fseek(f,0,SEEK_END);size_t n=(size_t)ftell(f);rewind(f);unsigned char *b=malloc(n);
 if(!b||fread(b,1,n,f)!=n)return 4;fclose(f);
 if(!maternalbound_bind_dialogue(b,n))return 5;
 unsigned found=0,accepted=0;size_t match=0;
 size_t end=n-32;unsigned char *footer=b+end;
 end=(size_t)footer[12]|((size_t)footer[13]<<8)|((size_t)footer[14]<<16)|((size_t)footer[15]<<24);
 for(size_t i=0;i+1<end;i++)if(b[i]==0x1f&&b[i+1]==0x50) {
  ++found;if(maternalbound_gauss_reset_prompt((unsigned)i+2)){++accepted;match=i;}
 }
 if(accepted!=1)return 6;
 if(maternalbound_gauss_reset_prompt((unsigned)match+1)||maternalbound_gauss_reset_prompt((unsigned)match+3))return 7;
 for(size_t i=0;i<22;i++){b[match+i]^=1;if(maternalbound_gauss_reset_prompt((unsigned)match+2))return 8;b[match+i]^=1;}
 if(maternalbound_bind_dialogue(NULL,0)||maternalbound_gauss_reset_prompt((unsigned)match+2))return 9;
 printf("{\"Passed\":true,\"lockByteCandidates\":%u,\"matchedGaussOnly\":%u,\"suffixCorruptionCases\":22,\"neighborOffsetsRejected\":true,\"nonReduxRejected\":true,\"lockOffset\":%zu}",found,accepted,match);
 free(b);return 0;
}'''
    source.write_text(harness,encoding='utf-8')
    cmd=[str(compiler),'-std=c2x','-ffunction-sections','-fdata-sections','-Wl,--gc-sections','-I',str(native/'src'),
         '-I',str(native/'src/data/runtime_generated'),'-I',str(ROOT/'build/companion/game_lib/generated'),
         str(source),'-o',str(exe)]
    p=subprocess.run(cmd,capture_output=True,timeout=45)
    if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace'))
    check=json.loads(subprocess.check_output([str(exe),str(data)],timeout=15))
    check['nativeAdapterSha256']=sha(native/'src/game/maternalbound.c')
    check['verbatimFunctionBodiesSha256']=hashlib.sha256('\n'.join(bodies).encode()).hexdigest()
    check['sourceFunctions']=list(names)
    return check


def other_source_lock(engine,pak,out,offsets,tamp,assets,flags,project):
    source=(project/'ccscript/data/data_23.ccs').read_text(encoding='utf-8-sig')
    body=source.split('l_0xc687e4:',1)[1].split('l_0xc6880b:',1)[0]
    if 'disable_input' not in body or 'eob' not in body or 'reset_routine' in body:
        raise ValueError('Other source power-off lock changed')
    s=ResetSession(engine,pak,out/'other-source-power-off-lock',offsets,tamp)
    prepare(s,0xC687E4,'other-lock',assets,flags)
    for i in range(20):
        if s.last['textInputLock']==1:break
        s.step('other-lock-text-'+str(i),[CONFIRM],wait=45)
    else:raise RuntimeError('Unrelated source LOCK_INPUT was suppressed')
    before=s.last['modes'];s.step('other-lock-cold-resume',wait=80)
    if s.last['textInputLock']!=1 or any(m in s.last['modes'] for m in (offsets['introMode'],offsets['titleMode'])):
        raise RuntimeError('Other source lock lost original behavior')
    return {'Passed':True,'entry':'C687E4','inputLockStillSet':True,'coldRestoreLockPreserved':True,'resetInvoked':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('engine','assets','project','scratch'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--native-source',type=Path,default=ROOT/'native-source')
    p.add_argument('--compiler',type=Path,default=ROOT/'tools/mingw64/bin/gcc.exe')
    p.add_argument('--output',type=Path)
    a=p.parse_args();out=local_scratch(a.scratch)
    if out.exists():raise ValueError('Use a fresh isolated scratch folder')
    out.mkdir(parents=True);native=a.native_source.resolve();compiler=a.compiler.resolve()
    sys.path.insert(0,str(native/'src/vendor/tamp'));import tamp
    commit=subprocess.check_output(['git','-C',str(a.project.parent),'rev-parse','HEAD'],text=True).strip()
    if commit!=PIN:raise ValueError('Pinned source commit differs')
    flags=prerequisites(a.project);offsets=layout(native,compiler,out)
    _,_,assets=read_pack(a.assets,native/'src/data/runtime_generated/asset_ids.h')
    hashes={'engine':sha(a.engine),'assets':sha(a.assets),'fileSelectSource':sha(native/'src/intro/file_select.c')}
    guard=guard_checks(native,compiler,out,assets['dialogue/dialogue.bin'])
    other_lock=other_source_lock(a.engine.resolve(),a.assets.resolve(),out,offsets,tamp,assets,flags,a.project)
    cases=[]
    for kind,entry in (('gauss',0xC68091),('dad',0xC63229)):
        for outcome in ('continue','end'):
            s=ResetSession(a.engine.resolve(),a.assets.resolve(),out/f'{kind}-{outcome}',offsets,tamp)
            prepare(s,entry,kind,assets,flags);reach_choice(s)
            save=s.folder/'fixture.srm'
            if not save.exists():raise RuntimeError(kind+' record path did not write a native phone save')
            before=s.last.copy();phone_hash=sha(save)
            if kind=='gauss' and before['partyIds'][0]!=3:raise RuntimeError('Gauss scene did not retain Jeff')
            s.step('cold-record-choice')
            if s.last['menus']!=before['menus'] or s.last['names']!=before['names']:raise RuntimeError('Cold record-choice restore changed menus or names')
            s.step('choose-'+outcome,([RIGHT] if outcome=='end' else [])+[CONFIRM],wait=50)
            saw_boot=False;final_prompt=False;fade_seen=False;pause_seen=False
            for i in range(80):
                modes=s.last['modes']
                fade_seen |= offsets['fadeMode'] in modes
                pause_seen |= offsets['delayMode'] in modes
                if offsets['introMode'] in modes or offsets['titleMode'] in modes or offsets['fileMode'] in modes:
                    saw_boot=True;break
                if outcome=='continue' and len(modes)==1:break
                if kind=='gauss' and outcome=='end' and guard['lockOffset']+3 in s.last['displayReaders'] and offsets['promptMode'] in modes and not final_prompt:
                    if s.last['textInputLock']!=0:raise RuntimeError('Gauss final prompt is still input-locked')
                    s.step('cold-final-gauss-prompt',wait=60,dump=True)
                    if guard['lockOffset']+3 not in s.last['displayReaders'] or offsets['promptMode'] not in s.last['modes'] or s.last['textInputLock']:
                        raise RuntimeError('Gauss final confirmation skipped or changed on cold restore')
                    final_prompt=True
                    s.step('confirm-final-gauss-prompt',[CONFIRM],wait=1)
                elif final_prompt:
                    s.step('gauss-reset-tail-'+str(i),wait=10)
                else:
                    s.step('outcome-text-'+str(i),[CONFIRM],wait=45)
            if outcome=='continue':
                if saw_boot or len(s.last['modes'])!=1 or s.last['partyIds']!=before['partyIds']:raise RuntimeError('Continue failed to return to unchanged party/world')
                result={'normalWorldReturn':True,'titleReached':False}
            else:
                if not saw_boot:raise RuntimeError('End did not invoke a native boot/reset')
                s.step('cold-reset-resume',wait=400)
                for i in range(12):
                    if offsets['titleMode'] in s.last['modes']:break
                    s.step('boot-progress-'+str(i),wait=250)
                else:raise RuntimeError('Native reset never reached title: '+str(s.last))
                s.step('title-render',dump=True)
                if offsets['titleMode'] not in s.last['modes']:raise RuntimeError('Cold title render lost title mode')
                result={'nativeBootSeen':True,'coldBootResume':True,'titleReached':True,'titleColdRender':True}
                if kind=='gauss':
                    if not final_prompt:raise RuntimeError('Gauss End did not expose its final confirmation')
                    if not fade_seen or not pause_seen:raise RuntimeError('Gauss End did not execute its fade and pause modes')
                    result['finalGaussPromptColdRestore']=True
                    result['fadeAndPauseModesSeen']=True
            if sha(save)!=phone_hash:raise RuntimeError('Continue/reset changed the recorded phone save')
            cases.append({'branch':kind,'entry':f'{entry:06X}','outcome':outcome,'Passed':True,'coldRecordMenuResume':True,
                          'recordedPhoneSaveSha256':phone_hash,'phoneSaveUnchangedDuringOutcome':True,**result})
            print(json.dumps(cases[-1]),flush=True)
    # Current immutable build sample only: exact font pixels and cold cursor/case/name.
    sample=naming.Session(a.engine.resolve(),a.assets.resolve(),out/'naming-sample',offsets,tamp);naming.bootstrap(sample)
    sample.step('accent-sample',sample.navigate((0,3))+[CONFIRM,naming.SELECT])
    before=sample.keyboard().copy();sample.step('cold-accent-keyboard',dump=True)
    if sample.keyboard()!=before or sample.keyboard()['name']!=[0xB0]:raise RuntimeError('Final-build naming cold sample failed')
    if hashes['engine']!=sha(a.engine) or hashes['assets']!=sha(a.assets):raise RuntimeError('Immutable inputs changed')
    prior=json.loads((ROOT/'research/redux-naming-runtime-review.json').read_text(encoding='utf-8'))
    naming_unchanged=prior['nativeAdapter']['sha256']==hashes['fileSelectSource']
    result={'format':'redux-reset-input-qa-v1','Passed':True,'upstreamCommit':PIN,'identities':hashes,'sourceDerivedFlags':flags,'cases':cases,
            'gaussSourceDefectAdaptationGuard':guard,'otherSourcePowerOffLock':other_lock,
            'namingFinalBuildSample':{'Passed':True,'coldAccentCaseCursorRestore':True,'renderedKeyboardStatesChecked':sample.render_checks,
                                     'full72StateSuiteClaimed':False,'fileSelectSourceUnchangedFromNamingReview':naming_unchanged},
            'sourceReferences':['ccscript/data/data_18.ccs:l_0xc63229/l_0xc631e3','ccscript/data/data_19.ccs:l_0xc63415/l_0xc63506',
                                'ccscript/data/data_22.ccs:l_0xc68091','ccscript/definitions/flags.ccs','ccscript/redux/reset_routine.ccs'],
            'ownerSavesTouched':False,'fullStoryCoverage':False,'preparedPhoneSaveSlot':1,
            'limits':['Prepared phone scenes replace only private entry readers and explicitly source-derived party/flags; not a full story or walk-to-phone playthrough.',
                      'C631E3 is Gauss Labs shared record/End flow, rather than a second Dad entry.','No full-world rendering parity or audio listening oracle.']}
    dest=a.output or out/'results.json';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'Passed':True,'cases':len(cases),'identities':hashes}),flush=True)


if __name__=='__main__':main()
