# SPDX-License-Identifier: GPL-3.0-or-later
"""Real linked native map-music selection with warm and cold state restores.

Links an immutable existing library into a private driver. Uses previously
completed original-machine evidence and real local packs. Only private saves
are created; no CMake invocation, owner write, shared source/build edit.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

import battle_action_catalog_qa as linker
from build_maternalbound_pack import read_pack
from check_jev_observer_parity import local_scratch
from map_music_conditional_qa import music_tables,corpus,pack_tables,REDUX_ROM_SHA
from snes_movement_helpers_oracle import sha,US_SHA1
import hashlib

DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game_main.h"
#include "core/state_dump.h"
#include "core/mode_stack.h"
#include "game/game_state.h"
#include "game/map_loader.h"
#include "game/overworld.h"
#include "game/maternalbound.h"
#include "platform/platform.h"
#include "data/assets.h"
extern int eb_platform_main(int argc,char**argv);
static void prepare(unsigned x,unsigned y,unsigned n,const unsigned*flags){
 memset(event_flags,0,sizeof(event_flags));for(unsigned i=0;i<n;i++)event_flag_set(flags[i]);
 game_state.leader_x_coord=x;game_state.leader_y_coord=y;game_state.walking_style=0;
 ow.disable_music_changes=0;ml.current_map_music_track=ml.next_map_music_track=255;ml.do_map_music_fade=1;
 ml.loaded_map_music_entry_offset=0x7fff;
 const uint8_t*grid=ASSET_DATA(ASSET_DATA_GLOBAL_MAP_TILESETPALETTE_DATA_BIN);
 unsigned index=(y/128)*32+x/256;
 if(index>=ASSET_SIZE(ASSET_DATA_GLOBAL_MAP_TILESETPALETTE_DATA_BIN))exit(8);
 ml.loaded_tileset_combo=grid[index]>>3;ml.loaded_palette_index=-1;
 g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_NONE;memset(&g_mode_stack.state[0],0,sizeof(g_mode_stack.state[0]));
}
int main(int argc,char**argv){
 if(argc!=6)return 2;unsigned redux=atoi(argv[5]);char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 char *boot[]={"map-music-runtime-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,
  "--allow-redux-development","--headless","--frames","1",redux?"--redux-battle-fixture":"--inspect-shuffle","0"};
 int count=sizeof(boot)/sizeof(boot[0]);if(!redux)count--;
 if(eb_platform_main(count,boot)!=0||maternalbound_enabled()!=(redux!=0))return 3;
 FILE*f=fopen(argv[3],"r");if(!f)return 4;unsigned index,x,y,n,flags[1024];
 while(fscanf(f,"%u %u %u %u",&index,&x,&y,&n)==4){
  if(n>1023)return 5;for(unsigned i=0;i<n;i++)if(fscanf(f,"%u",&flags[i])!=1)return 5;
  if(strcmp(argv[4],"cold")==0){
   /* Fresh process, then explicitly discard all bootstrap map caches before
    * the real loader applies the saved sections and rebinds those caches. */
   map_loader_free();if(!state_dump_load_slots())return 6;
   if(game_state.leader_x_coord!=x||game_state.leader_y_coord!=y)return 7;
   for(unsigned flag=1;flag<=1023;flag++){unsigned want=0;for(unsigned i=0;i<n;i++)if(flags[i]==flag)want=1;
    if(event_flag_get(flag)!=(want!=0))return 7;}
  }else{
   if(!map_loader_init())return 8;prepare(x,y,n,flags);
   if(strcmp(argv[4],"prepare")==0){
    if(!state_dump_save_slots())return 9;
    printf("MUSIC_PREPARED {\"index\":%u,\"x\":%u,\"y\":%u,\"saved\":true}\n",index,x,y);continue;
   }
  }
  resolve_map_sector_music(game_state.leader_x_coord,game_state.leader_y_coord);
  printf("MUSIC_NATIVE {\"index\":%u,\"track\":%u,\"entryOffset\":%u,\"cold\":%s}\n",index,ml.next_map_music_track,ml.loaded_map_music_entry_offset,strcmp(argv[4],"cold")==0?"true":"false");fflush(stdout);
 }
 fclose(f);return 0;
}
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','runtime','native-source','rom','redux-rom','original-assets','redux-assets','conditional-review','conditional-scratch','scratch','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--diagnostic',action='store_true',help='Record baseline predicate failures; malformed/incomplete runs still fail.')
    p.add_argument('--previous-report',type=Path,help='Preserved frozen-library red baseline to link after a successful rerun.')
    a=p.parse_args();a.scratch=local_scratch(a.scratch);evidence=local_scratch(a.conditional_scratch)
    if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch/report required')
    red_or_green=json.loads(a.conditional_review.read_text(encoding='utf-8'))
    if red_or_green.get('format')!='map-music-conditional-review-v1':raise ValueError('Different independent evidence schema')
    identities={'originalRom':sha(a.rom),'reduxRom':sha(a.redux_rom),'originalAssets':sha(a.original_assets),'reduxAssets':sha(a.redux_assets)}
    if hashlib.sha1(a.rom.read_bytes()).hexdigest()!=US_SHA1 or identities['reduxRom']!=REDUX_ROM_SHA:raise ValueError('Pinned ROM differs')
    if any(red_or_green['InputIdentities'][k]!=v for k,v in identities.items()):raise ValueError('Independent evidence inputs differ')
    previous=None
    if a.previous_report:
        baseline=json.loads(a.previous_report.read_text(encoding='utf-8'))
        if baseline.get('format')!='map-music-native-runtime-review-v1' or baseline.get('Passed') is not False:
            raise ValueError('Expected a preserved failing native-runtime baseline')
        if baseline.get('InputIdentities')!=identities:raise ValueError('Baseline inputs differ')
        old_modes=baseline.get('Modes',[])
        if len(old_modes)!=2 or {m.get('mode') for m in old_modes}!={'original','redux'}:
            raise ValueError('Incomplete baseline modes')
        for row in old_modes:
            if any(row.get(k)!=v for k,v in {'WarmCases':624,'ColdCases':9,'WarmMismatchCount':6,'ColdMismatchCount':6}.items()):
                raise ValueError('Baseline differs from independently identified predicate defect')
        previous={'path':a.previous_report.as_posix(),'sha256':sha(a.previous_report),
                  'ImmutableNativeBuild':baseline['ImmutableNativeBuild'],'RuntimeSha256':baseline['RuntimeSha256'],
                  'Modes':[{k:m[k] for k in ('mode','WarmCases','ColdCases','WarmMismatchCount','ColdMismatchCount')} for m in old_modes]}
    a.scratch.mkdir(parents=True);linker.DRIVER=DRIVER
    exe,buildmeta=linker.private_build(a);modes=[]
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    for mode,rompath,pack in (('original',a.rom,a.original_assets),('redux',a.redux_rom,a.redux_assets)):
        rom=rompath.read_bytes();assets,packed=pack_tables(pack,a.native_source/'src/data/runtime_generated/asset_ids.h',rom)
        grid,_,chains=music_tables(rom);cases,_=corpus(grid,chains)
        samples=evidence/(mode+'-machine')/'samples.jsonl';meta=next(r for r in red_or_green['Modes'] if r['mode']==mode)
        if sha(samples)!=meta['OriginalMachineEvidence']['SamplesSha256']:raise ValueError('Independent machine samples changed')
        reference=[json.loads(line) for line in samples.read_text(encoding='utf-8').splitlines()]
        if len(reference)!=len(cases):raise ValueError('Independent evidence corpus differs')
        expected={}
        for case,row in zip(cases,reference):
            index,track,pointer,bank=row
            selected=next(i for i,(at,_,_) in enumerate(chains[case['zone']]) if at==pointer-0x5a39)
            expected[index]={'track':track,'entryOffset':packed[case['zone']][selected][0]}
        modeout=a.scratch/mode;modeout.mkdir();allrows=[]
        def run(stage,indices,session,label):
            session.mkdir(parents=True,exist_ok=True);inputs=modeout/(label+'.tsv')
            inputs.write_text(''.join(' '.join(map(str,[i,cases[i-1]['x'],cases[i-1]['y'],len(cases[i-1]['flagState']),*cases[i-1]['flagState']]))+'\n' for i in indices),encoding='utf-8')
            result=subprocess.run([str(exe),str(pack.resolve()),str(session.resolve()),str(inputs.resolve()),stage,'1' if mode=='redux' else '0'],
                                  cwd=session,env=env,capture_output=True,timeout=30)
            (modeout/(label+'.log')).write_bytes(result.stdout+result.stderr)
            if result.returncode:raise RuntimeError(mode+' '+label+' driver failed '+str(result.returncode))
            prefix='MUSIC_PREPARED ' if stage=='prepare' else 'MUSIC_NATIVE '
            rows=[json.loads(line[len(prefix):]) for line in result.stdout.decode(errors='replace').splitlines() if line.startswith(prefix)]
            if [r['index'] for r in rows]!=indices:raise RuntimeError('Native helper corpus incomplete '+label)
            return rows
        warm=run('warm',list(range(1,len(cases)+1)),modeout/'warm-session','warm-all')
        for row in warm:
            row.update(expected=expected[row['index']],passed=all(row[k]==v for k,v in expected[row['index']].items()),case=cases[row['index']-1]);allrows.append(row)
        cold_indices=[]
        for zone in (122,128,164):
            low=next(f for _,f,_ in packed[zone] if 0<f<0x8000);high=packed[zone][0][1]&0x7fff
            for active in ([],[low],[high]):
                cold_indices.append(next(i+1 for i,c in enumerate(cases) if c['zone']==zone and c['flagState']==active))
        for index in cold_indices:
            session=modeout/f'cold-session-{index:03}';run('prepare',[index],session,f'prepare-{index:03}')
            row=run('cold',[index],session,f'cold-{index:03}')[0]
            row.update(expected=expected[index],passed=all(row[k]==v for k,v in expected[index].items()),case=cases[index-1]);allrows.append(row)
        modes.append({'mode':mode,'WarmCases':len(warm),'ColdCases':len(cold_indices),'MismatchCount':sum(not row['passed'] for row in allrows),
                      'WarmMismatchCount':sum(not row['passed'] and not row['cold'] for row in allrows),
                      'ColdMismatchCount':sum(not row['passed'] and row['cold'] for row in allrows),'Cases':allrows})
    for key,path in (('originalRom',a.rom),('reduxRom',a.redux_rom),('originalAssets',a.original_assets),('reduxAssets',a.redux_assets)):
        if sha(path)!=identities[key]:raise RuntimeError('Immutable source/asset input changed during audit')
    if sha(a.build/'game_lib/libearthbound_game.a')!=buildmeta['productionLibrarySha256']:
        raise RuntimeError('Frozen production library changed during audit')
    if sha(a.runtime/'player.exe')!=buildmeta['productionExecutableSha256']:
        raise RuntimeError('Frozen production executable changed during audit')
    report={'format':'map-music-native-runtime-review-v1','Passed':all(not r['MismatchCount'] for r in modes),'InputIdentities':identities,
            'ImmutableNativeBuild':buildmeta,'RuntimeSha256':{name:sha(a.runtime/name) for name in ('player.exe','observer.exe')},
            'IndependentMachineReview':{'path':a.conditional_review.as_posix(),'sha256':sha(a.conditional_review)},'Modes':modes,
            'OwnerSavesTouched':False,'SharedSourceEdited':False,'SharedBuildsEdited':False,
            'ColdStateSaveAndLoadUsed':True,'ColdContextsAreSeparateNativeProcesses':True,'SavedCoordinatesAndAll1023FlagsVerified':True,
            'Runner':{'path':'tools/map_music_runtime_qa.py','sha256':sha(Path(__file__))},'FullPlaythroughVerified':False,'AudiblePlaybackVerified':False,
            'Limits':['Calls the real selector in an unchanged frozen production library; expected tracks/entries come from completed independent untouched original-machine calls.',
                      'Cold cases are prepared saved helper contexts, written at a post-startup root-mode boundary, then loaded in a new process. Bootstrap map caches are freed before actual state load/rebind.',
                      'Tileset combo is derived from the real map grid at each source-derived music coordinate. This is not a naturally reached story scene or physical F6 input test.',
                      'Cold coverage is nine cases per mode: three affected chains with low flags clear/set and preceding high-flag controls. All624 reachable-zone contexts run warm.',
                      'Fade is suppressed to isolate selection. Actual song decoding/MSU output, audible fade behavior and complete map transition/progression are outside this audit.']}
    if previous:report['PreservedRedBaseline']=previous
    (a.scratch/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'Passed':report['Passed'],'Modes':[{k:r[k] for k in ('mode','WarmCases','ColdCases','WarmMismatchCount','ColdMismatchCount')} for r in modes]}),flush=True)
    if not report['Passed'] and not a.diagnostic:raise SystemExit(1)


if __name__=='__main__':main()
