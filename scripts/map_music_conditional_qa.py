# SPDX-License-Identifier: GPL-3.0-or-later
"""Source-backed map music branch and real native warm/cold selector checks.

Local explicit ROMs/packs and frozen build inputs only. Never writes owner
files, shared sources or shared builds; private state/caller/probes only.
Reports bounded music selection, not audible playback or story parity.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess

import battle_action_catalog_qa as linker
from build_maternalbound_pack import read_pack
from check_jev_observer_parity import local_scratch
from snes_movement_helpers_oracle import function,sha,US_SHA1

PIN='897d00833f4a08a0a92f106abf631629a6a6a041'
REDUX_ROM_SHA='c2a2fc98c7e6518b797959ffadf24ca4db8b4d7745ed3a9eb92eee106db1d0ab'
NAMES=('data/per_sector_music.bin','data/overworld_event_music_ptr_table.bin','data/overworld_event_music_table.bin')


def music_tables(rom):
    ptr_address=int.from_bytes(rom[0x6939:0x693c],'little')
    if not 0xC00000<=ptr_address<0x1000000:raise ValueError('Unknown source music pointer mapping')
    ptrs=rom[ptr_address-0xC00000:ptr_address-0xC00000+330]
    grid=rom[0x1cd637:0x1cd637+2560];chains=[]
    for zone in range(165):
        pointer=struct.unpack_from('<H',ptrs,zone*2)[0]&0x7fff
        if not zone:chains.append([]);continue
        at=0x0f0000+pointer;rows=[]
        for _ in range(1024):
            flag,track=struct.unpack_from('<HH',rom,at);rows.append((at-0xf5a39,flag,track));at+=4
            if track>191 or flag&0x7fff>1023:raise ValueError('Invalid source music record')
            if not flag:break
        else:raise ValueError('Unterminated source music chain')
        chains.append(rows)
    return grid,ptrs,chains


def pack_tables(path,ids,rom):
    _,_,assets=read_pack(path,ids);grid,ptrs,chains=music_tables(rom)
    pgrid,pptrs,table=(assets[n] for n in NAMES)
    if pgrid!=grid or len(pptrs)!=330:raise ValueError('Pack music grid differs from pinned source')
    packed=[]
    for zone in range(165):
        start=(struct.unpack_from('<H',pptrs,zone*2)[0]&0x7fff)-0x5a39
        if not zone:packed.append([]);continue
        rows=[];at=start
        for _ in range(1024):
            if at<0 or at+4>len(table):raise ValueError('Pack music pointer out of bounds')
            flag,track=struct.unpack_from('<HH',table,at);rows.append((at,flag,track));at+=4
            if not flag:break
        else:raise ValueError('Unterminated packed music chain')
        if [(f,t) for _,f,t in rows]!=[(f,t) for _,f,t in chains[zone]]:raise ValueError('Music conversion changed flags/tracks')
        packed.append(rows)
    return assets,packed


def corpus(grid,chains):
    cases=[];unreachable=[]
    for zone in range(1,165):
        cells=[i for i,v in enumerate(grid) if v==zone]
        if not cells:unreachable.append(zone);continue
        index=cells[0];x=(index%32)*256+16;y=(index//32)*128+16
        flags=sorted({f&0x7fff for _,f,_ in chains[zone] if f})
        patterns=[('all-clear',[])]+[('single-flag-set',[f]) for f in flags]+[('all-chain-flags-set',flags)]
        for label,active in patterns:cases.append({'zone':zone,'x':x,'y':y,'flagState':active,'caseGroup':label})
    return cases,unreachable


def machine(a,out,rompath,rom,cases):
    out.mkdir();samples=out/'samples.jsonl'
    # Original untouched far selector, original signed divide and event-flag
    # getter all execute. The caller alone is temporary emulator memory.
    code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
    entry=0xc0ff00+len(code)
    code+=bytes.fromhex('af04717eaaaf02717e22f468c07b8f08707e3b8f0a707e')
    finish=0xc0ff00+len(code);code+=bytes((0x4c,entry&255,(entry>>8)&255))
    lua=['local output=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))','local cases={']
    lua+=['{'+str(c['x'])+','+str(c['y'])+',{'+','.join(map(str,c['flagState']))+'}},' for c in cases]
    lua+=['}','local mem=emu.memType.snesWorkRam',
          'local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256),mem) end',
          'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end',
          'local index=0;local calls=0;w16(0x7200,0x55aa)',
          'emu.addMemoryCallback(function()',
          ' index=index+1;local c=assert(cases[index],"past corpus")',
          ' for i=0,127 do emu.write(0x9c08+i,0,mem) end',
          ' for _,f in ipairs(c[3]) do local at=0x9c08+math.floor((f-1)/8);local mask=1<<((f-1)%8);emu.write(at,emu.read(at,mem)|mask,mem) end',
          ' w16(0x7102,c[1]);w16(0x7104,c[2]);w16(0x5dd8,0);w16(0x5dda,1);w16(0x5dd4,255);w16(0x5dd6,255);w16(0x5e38,0xda38);w16(0x5e3a,0x00cf)',
          f'end,emu.callbackType.exec,{entry})',
          'emu.addMemoryCallback(function() calls=calls+1 end,emu.callbackType.exec,0xc068f4)',
          'emu.addMemoryCallback(function()',
          ' assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"CPU frame corrupted");assert(r16(0x7200)==0x55aa,"protected RAM corrupted")',
          ' output:write(string.format("[%d,%d,%d,%d]\\n",index,r16(0x5dd6),r16(0x5e38),r16(0x5e3a)))',
          ' if index==#cases then assert(calls==#cases,"selector call count differs");output:flush();output:close();emu.log("MUSIC_CORPUS_COMPLETE "..calls);emu.breakExecution() end',
          f'end,emu.callbackType.exec,{finish})']
    script=out/'music.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
    run=subprocess.run([str(a.oracle.resolve()),str(rompath.resolve()),'--home',str(out/'oracle-home'),'--frames','1000','--timeout','60',
                        '--lua-timeout','10','--lua-allow-io','--lua',str(script),'--write-memory','SnesPrgRom:0xff00:'+code.hex(),
                        '--set-pc','0xc0ff00','--cpu','Snes'],capture_output=True,timeout=70)
    (out/'oracle.jsonl').write_bytes(run.stdout);(out/'oracle.stderr').write_bytes(run.stderr)
    records=[json.loads(x) for x in run.stdout.decode().splitlines()];logs=[r for r in records if r['event']=='lua_log']
    if run.returncode or not records[-1].get('ok') or records[-1].get('reason')!='debugger_break' or any(r['error_count'] for r in logs):raise RuntimeError('Machine music corpus incomplete')
    if sum('MUSIC_CORPUS_COMPLETE ' in r['text'] for r in logs)!=1:raise RuntimeError('Machine completion marker missing/duplicated')
    rows=[json.loads(x) for x in samples.read_text(encoding='utf-8').splitlines()]
    if [r[0] for r in rows]!=list(range(1,len(cases)+1)) or any(r[3]!=0xcf for r in rows):raise RuntimeError('Machine samples incomplete or original pointer bank changed')
    return rows,{'ExecutedCases':len(rows),'StackDirectPageAndProtectedRamCanariesPassed':True,'CompleteOrderedCorpusVerified':True,
                 'SelectorCallsVerified':len(rows),'OwnCallerSha256':hashlib.sha256(code).hexdigest(),'OracleLuaSha256':sha(script),'SamplesSha256':sha(samples)}


def micro_native(a,out,source,assets,cases):
    out.mkdir();body=function(source,'resolve_map_sector_music')
    # Actual selector and actual event getter; dependencies are the real pack
    # tables and ordinary APU command instrumentation, not canned results.
    event=function((a.native_source/'src/game/game_state.c').read_text(encoding='utf-8'),'event_flag_get')
    prefix='''#include "game/map_loader.h"
#include "game/overworld.h"
#include "game/game_state.h"
#include "include/binary.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
MapLoaderState ml;OverworldState ow;GameState game_state;
uint8_t event_flags[EVENT_FLAG_COUNT/8];
static const uint8_t *per_sector_music_data,*event_music_ptr_table,*event_music_table;
static size_t per_sector_music_size,event_music_ptr_table_size,event_music_table_size;
#define EVENT_MUSIC_TABLE_LOWORD 0x5A39
#define WALKING_STYLE_BICYCLE 3
static unsigned fades;static void write_apu_port1(uint8_t v){if(v==2)fades++;}
static unsigned char*load(const char*p,size_t*n){FILE*f=fopen(p,"rb");if(!f)return NULL;fseek(f,0,SEEK_END);*n=ftell(f);rewind(f);unsigned char*b=malloc(*n);if(fread(b,1,*n,f)!=*n)exit(9);fclose(f);return b;}
'''
    driver=r'''
int main(int argc,char**argv){if(argc!=5)return 2;
 per_sector_music_data=load(argv[1],&per_sector_music_size);event_music_ptr_table=load(argv[2],&event_music_ptr_table_size);event_music_table=load(argv[3],&event_music_table_size);
 if(!per_sector_music_data||!event_music_ptr_table||!event_music_table)return 3;
 FILE*f=fopen(argv[4],"r");if(!f)return 4;unsigned index,x,y,n;
 while(fscanf(f,"%u %u %u %u",&index,&x,&y,&n)==4){memset(event_flags,0,sizeof(event_flags));
  for(unsigned j=0;j<n;j++){unsigned flag;if(fscanf(f,"%u",&flag)!=1||flag<1||flag>1023)return 5;flag--;event_flags[flag/8]|=1<<(flag%8);}
  ml.loaded_map_music_entry_offset=0x7fff;ml.current_map_music_track=ml.next_map_music_track=255;ml.do_map_music_fade=1;
  ow.disable_music_changes=0;game_state.walking_style=0;
  resolve_map_sector_music(x,y);printf("[%u,%u,%u]\n",index,ml.next_map_music_track,ml.loaded_map_music_entry_offset);
 }fclose(f);return 0;}
'''
    c=out/'native-selector.c';c.write_text(prefix+event+body+driver,encoding='utf-8');files=[]
    for name in NAMES:
        path=out/Path(name).name;path.write_bytes(assets[name]);files.append(path)
    inputs=out/'cases.tsv';inputs.write_text(''.join(' '.join(map(str,[i+1,c['x'],c['y'],len(c['flagState']),*c['flagState']]))+'\n' for i,c in enumerate(cases)),encoding='utf-8')
    exe=out/'native-selector.exe';cmd=[str(a.compiler.resolve()),'-O2','-std=c11','-DUSA=1','-DEB_VIEWPORT_WIDTH=512','-DEB_VIEWPORT_HEIGHT=256']
    cmd+=['-I'+str(p.resolve()) for p in (a.native_source/'src',a.native_source/'src/include',a.generated,a.native_source/'src/data/runtime_generated')]+[str(c),'-o',str(exe)]
    run=subprocess.run(cmd,capture_output=True,timeout=30);(out/'compile.log').write_bytes(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError('Native selector compile failed')
    run=subprocess.run([str(exe),*map(str,files),str(inputs)],capture_output=True,timeout=30);(out/'samples.jsonl').write_bytes(run.stdout)
    if run.returncode:raise RuntimeError('Native selector corpus failed')
    rows=[json.loads(x) for x in run.stdout.decode().splitlines()]
    if [r[0] for r in rows]!=list(range(1,len(cases)+1)):raise RuntimeError('Native corpus incomplete')
    return rows,{'ProbeSha256':sha(exe),'ActualSelectorBodySha256':hashlib.sha256(body.encode()).hexdigest(),'ActualEventGetterSha256':hashlib.sha256(event.encode()).hexdigest()}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','redux-rom','oracle','compiler','native-source','generated','original-assets','redux-assets','scratch','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--diagnostic',action='store_true',help='Retain known native mismatches and return success; machine evidence still must complete.')
    p.add_argument('--previous-report',type=Path,help='Preserved completed red report; records its exact identity without overwriting it.')
    a=p.parse_args();out=local_scratch(a.scratch)
    if out.exists() or a.output.exists():raise ValueError('Fresh scratch/report required')
    original=a.rom.read_bytes();redux=a.redux_rom.read_bytes()
    if len(original)!=0x300000 or hashlib.sha1(original).hexdigest()!=US_SHA1 or sha(a.redux_rom)!=REDUX_ROM_SHA:raise ValueError('Pinned ROM identity differs')
    sourcepath=a.native_source/'src/game/map_loader.c';source=sourcepath.read_text(encoding='utf-8');sourcehash=sha(sourcepath)
    identities={'originalRom':sha(a.rom),'reduxRom':sha(a.redux_rom),'originalAssets':sha(a.original_assets),'reduxAssets':sha(a.redux_assets),
                'nativeSource':sourcehash,'oracle':sha(a.oracle),'oracleCore':sha(a.oracle.parent/'MesenCore.dll'),'compiler':sha(a.compiler)}
    macros=(a.native_source/'include/macros.asm').read_text(encoding='utf-8')
    if '.MACRO BLTEQ dest\n    BCC dest\n    BEQ dest\n.ENDMACRO' not in macros:raise ValueError('Original macro changed')
    # Runtime decode of actual CMP immediate16, BCC, BEQ and LDX immediate16.
    for rom in (original,redux):
        at=0x695e
        if rom[at]!=0xc9 or struct.unpack_from('<H',rom,at+1)[0]!=0x8000 or rom[at+3]!=0x90 or rom[at+5]!=0xf0 or rom[at+7]!=0xa2 or struct.unpack_from('<H',rom,at+8)[0]!=1:
            raise ValueError('Pinned original unsigned comparison no longer matches reviewed source')
        if at+5+int.from_bytes(rom[at+4:at+5],'little',signed=True)!=0x6968 or at+7+int.from_bytes(rom[at+6:at+7],'little',signed=True)!=0x6968:
            raise ValueError('Unsigned branch destinations changed')
    out.mkdir(parents=True);results=[]
    for mode,rom,rompath,packpath in (('original',original,a.rom,a.original_assets),('redux',redux,a.redux_rom,a.redux_assets)):
        assets,packed=pack_tables(packpath,a.native_source/'src/data/runtime_generated/asset_ids.h',rom)
        grid,_,chains=music_tables(rom);cases,unused=corpus(grid,chains)
        reference,refmeta=machine(a,out/(mode+'-machine'),rompath,rom,cases)
        native,nmeta=micro_native(a,out/(mode+'-native'),source,assets,cases)
        differences=[]
        # Compare tracks and matched semantic entry; Redux normalizes offsets.
        for c,ref,actual in zip(cases,reference,native):
            source_offset=ref[2]-0x5a39;row=next((i for i,(at,_,_) in enumerate(chains[c['zone']]) if at==source_offset),None)
            if row is None:raise RuntimeError('Original result points outside selected source music chain')
            expected_offset=packed[c['zone']][row][0]
            if actual[1:]!=[ref[1],expected_offset]:differences.append(dict(c,nativeTrack=actual[1],originalMachineTrack=ref[1],nativeEntryOffset=actual[2],expectedPackedEntryOffset=expected_offset))
        low=[{'zone':z,'flagId':f,'track':t,'offset':at} for z,rows in enumerate(packed) for at,f,t in rows if 0<f<0x8000]
        results.append({'mode':mode,'ExecutedCases':len(cases),'NativeMismatchCount':len(differences),'NativeMismatches':differences,
                        'ActualLowFlagRecords':low,'UnreachableMusicZones':unused,'AllReachableZoneChainsPreservePinnedFlagAndTrackSequence':True,
                        'OriginalMachineEvidence':refmeta,'CompiledActualNativeEvidence':nmeta,
                        'CasesPrivateArtifact':mode+'-machine/music.lua'})
    if sha(sourcepath)!=sourcehash:raise RuntimeError('Native source changed during audit; preserve this evidence and rerun')
    for key,path in (('originalRom',a.rom),('reduxRom',a.redux_rom),('originalAssets',a.original_assets),('reduxAssets',a.redux_assets)):
        if sha(path)!=identities[key]:raise RuntimeError('Immutable source/asset input changed')
    previous=None
    if a.previous_report:
        red=json.loads(a.previous_report.read_text(encoding='utf-8'))
        if red.get('format')!='map-music-conditional-review-v1' or red['Passed'] or len(red['Modes'])!=2 or any(r['NativeMismatchCount']!=6 for r in red['Modes']):
            raise ValueError('Review unexpected red baseline before linking it')
        for key in ('originalRom','reduxRom','originalAssets','reduxAssets'):
            if red['InputIdentities'][key]!=identities[key]:raise ValueError('Red baseline has different immutable inputs')
        previous={'path':a.previous_report.as_posix(),'sha256':sha(a.previous_report),'Passed':red['Passed'],
                  'Modes':[{'mode':r['mode'],'ExecutedCases':r['ExecutedCases'],'NativeMismatchCount':r['NativeMismatchCount']} for r in red['Modes']]}
    report={'format':'map-music-conditional-review-v1','Passed':not any(r['NativeMismatchCount'] for r in results),'InputIdentities':identities,
            'PreservedRedBaseline':previous,'PinnedReduxRevision':PIN,'UnsignedPredicate':{'CompareInstructionAddress':'C0695E','ConditionalBranches':['BCC','BEQ'],
                'BothDestinationAddresses':'C06968','ExpectedState':'0 when unsigned flag word <=0x8000; 1 when >0x8000',
                'OriginalAndPinnedReduxMachineBranchesVerified':True},'Modes':results,
            'OwnerSavesTouched':False,'OwnerRomsAndAssetPacksUnchanged':True,'SharedSourceEdited':False,'SharedBuildsEdited':False,
            'FullPlaythroughVerified':False,'AudiblePlaybackVerified':False,
            'Runner':{'path':'tools/map_music_conditional_qa.py','sha256':sha(Path(__file__))},
            'Limits':['Actual untouched full selector executes original divide/event-flag helpers with real source chains. Native actual selector/event getter are compiled in isolation.',
                      'Prepared reachable-zone flag states are function evidence; flags are not legal-story progression proof. Zone-zero upstream conversion repair is outside this audit.',
                      'Fade is suppressed in these selection probes. Track selection and semantic matched entry are compared; music decoding, MSU playback and actual audio are not certified.',
                      'Packed Redux offsets differ by normalization; source record sequence is checked independently rather than comparing pointer numbers blindly.']}
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'Passed':report['Passed'],'Modes':[{'mode':r['mode'],'ExecutedCases':r['ExecutedCases'],'NativeMismatchCount':r['NativeMismatchCount'],'FirstMismatches':r['NativeMismatches'][:3]} for r in results]}),flush=True)
    if not report['Passed'] and not a.diagnostic:raise SystemExit(1)


if __name__=='__main__':main()
