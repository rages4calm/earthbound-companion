# SPDX-License-Identifier: GPL-3.0-or-later
"""Observe actual SPC command acceptance, channel PCM and the SDL audio mixer.

Private instrumentation changes copied COFF symbol visibility only. Every raw
section remains byte-identical. Existing SPC memory callbacks are forwarded once
per call, then observed. No production source, assets, saves or builds are edited.
"""
import argparse, hashlib, json, os, re, shutil, struct, subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import battle_action_catalog_qa as helper
import shop_transaction_qa_dev18 as shop
import battle_full_encounter_qa_dev18 as encounter
from build_maternalbound_pack import read_pack

OBSERVE = r'''
#include <SDL.h>
#include "apu.h"
#include "spc.h"
#include "dsp.h"
#include "game/settings.h"
#include "game/ending.h"
extern Apu *qa_apu;
extern SDL_AudioDeviceID qa_audio_device;
extern int qa_overflow_count;
extern void qa_audio_callback(void *,Uint8 *,int);
extern void qa_production_play_sfx(uint16_t);
extern void platform_audio_msu_load(const char*,const char*);
extern bool qa_msu_active;
extern double qa_msu_read_pos;
static unsigned qa_tick,qa_observing,qa_last_ack,qa_sample_offset,qa_last_music;
static unsigned qa_requests[128],qa_acks[128],qa_accepts[128],qa_samples[128],qa_peaks[128];
static unsigned qa_mix_peak,qa_callback_count,qa_muted_samples,qa_nonzero_samples;
static unsigned qa_hq,qa_track,qa_suppress=255,qa_callback_pattern,qa_rate_remainder,qa_output_pending;
static uint64_t qa_sample_sum[128],qa_mix_sum,qa_pcm_hash;
static FILE *qa_pcm_file;
static SpcReadHandler qa_read_original;
static SpcWriteHandler qa_write_original;
static SpcIdleHandler qa_idle_original;
static frame_callback_fn qa_frame_original;
static void qa_observe_sample(void){
 if(!qa_observing||qa_apu->dsp->sampleOffset==qa_sample_offset)return;
 qa_sample_offset=qa_apu->dsp->sampleOffset;
 unsigned id=qa_apu->ram[0x04b7]&127;
 if(id&&(qa_apu->ram[0x001a]&0x80)){
  DspChannel *c=&qa_apu->dsp->channel[7];
  int l=((int)c->sampleOut*c->volumeL)>>7,r=((int)c->sampleOut*c->volumeR)>>7;
  unsigned magnitude=(unsigned)(abs(l)>abs(r)?abs(l):abs(r));
  if(magnitude){qa_samples[id]++;qa_sample_sum[id]+=magnitude;if(magnitude>qa_peaks[id])qa_peaks[id]=magnitude;}
 }
}
static uint8_t qa_read(void *mem,uint16_t adr){uint8_t value=qa_read_original(mem,adr);qa_observe_sample();return value;}
static void qa_idle(void *mem,bool waiting){qa_idle_original(mem,waiting);qa_observe_sample();}
static void qa_write(void *mem,uint16_t adr,uint8_t val){
 unsigned dsp=qa_apu->dspAdr;
 qa_write_original(mem,adr,val);qa_observe_sample();
 if(!qa_observing)return;
 if(adr==0xf7&&val!=qa_last_ack){
  qa_last_ack=val;qa_acks[val&127]++;
  printf("QA_AUDIO_ACK {\"tick\":%u,\"command\":%u,\"cycle\":%u}\n",qa_tick,val,qa_apu->cycles);
 }
 if(adr==0x04b7&&val){
  qa_accepts[val&127]++;
  printf("QA_AUDIO_ACCEPT {\"tick\":%u,\"id\":%u,\"cycle\":%u}\n",qa_tick,val,qa_apu->cycles);
 }
 if(adr==0xf3&&dsp==0x4c&&(val&128))
  printf("QA_AUDIO_KEYON {\"tick\":%u,\"id\":%u,\"mask\":%u,\"cycle\":%u}\n",qa_tick,qa_apu->ram[0x04b7]&127,val,qa_apu->cycles);
}
void play_sfx(uint16_t id){
 if(qa_observing&&id<128){qa_requests[id]++;printf("QA_AUDIO_REQUEST {\"tick\":%u,\"id\":%u,\"suppressedControl\":%s}\n",qa_tick,id,(qa_suppress==id)?"true":"false");}
 if(!qa_observing||qa_suppress!=id)qa_production_play_sfx(id);
}
static void qa_callback(unsigned frames){
 int16_t buffer[2048*2];if(frames>2048)exit(21);
 if(qa_observing&&audio_state.current_music_track!=qa_last_music){qa_last_music=audio_state.current_music_track;printf("QA_AUDIO_MUSIC {\"tick\":%u,\"track\":%u,\"msuActive\":%s}\n",qa_tick,qa_last_music,qa_msu_active?"true":"false");}
 qa_audio_callback(NULL,(Uint8*)buffer,(int)(frames*4));qa_callback_count++;
 for(unsigned i=0;i<frames*2;i++){
  unsigned v=(unsigned)abs((int)buffer[i]);if(v>qa_mix_peak)qa_mix_peak=v;qa_mix_sum+=v;
  if(v)qa_nonzero_samples++;else qa_muted_samples++;
  qa_pcm_hash^=(uint16_t)buffer[i];qa_pcm_hash*=1099511628211ULL;
 }
 if(qa_pcm_file)fwrite(buffer,4,frames,qa_pcm_file);
}
static void qa_audio_frame(void){
 qa_tick++;
 /* Normal host fixtures execute at 60Hz. SDL runs 32000 output frames/s.
  * Both callback layouts below emit precisely the same sample total. */
 qa_rate_remainder+=32000;unsigned frames=qa_rate_remainder/60;qa_rate_remainder%=60;
 if(qa_callback_pattern==2){qa_output_pending+=frames;while(qa_output_pending>=1024){qa_callback(1024);qa_output_pending-=1024;}}
 else if(qa_callback_pattern){while(frames){unsigned n=frames>128?128:frames;qa_callback(n);frames-=n;}}
 else qa_callback(frames);
}
static void qa_frame_hook(void){
 if(qa_frame_original)qa_frame_original();else process_overworld_tasks();
 qa_audio_frame();
}
static void qa_audio_open(unsigned track,unsigned hq,const char*msu,const char*output){
 qa_observing=0;qa_track=track;qa_hq=hq;
 /* The one-frame bootstrap has closed its SDL device. This private process
  * reopens the production device, pauses it, then resets its own APU. */
 if(SDL_InitSubSystem(SDL_INIT_AUDIO)!=0||!platform_audio_init())exit(22);SDL_PauseAudioDevice(qa_audio_device,1);
 audio_shutdown();audio_init();qa_overflow_count=0;
 qa_read_original=qa_apu->spc->read;qa_write_original=qa_apu->spc->write;qa_idle_original=qa_apu->spc->idle;
 qa_apu->spc->read=qa_read;qa_apu->spc->write=qa_write;qa_apu->spc->idle=qa_idle;
 platform_audio_msu_load(msu,"eb_msu1");engine_hq_audio=hq?HQ_AUDIO_ON:HQ_AUDIO_OFF;
 pc_options.volume=100;pc_paused=false;game_set_fast_forward(false);
 change_music(track);for(unsigned i=0;i<60;i++)qa_audio_frame();if(qa_output_pending){qa_callback(qa_output_pending);qa_output_pending=0;}
 memset(qa_requests,0,sizeof(qa_requests));memset(qa_acks,0,sizeof(qa_acks));memset(qa_accepts,0,sizeof(qa_accepts));
 memset(qa_samples,0,sizeof(qa_samples));memset(qa_peaks,0,sizeof(qa_peaks));memset(qa_sample_sum,0,sizeof(qa_sample_sum));
 qa_tick=qa_callback_count=qa_mix_peak=qa_muted_samples=qa_nonzero_samples=0;qa_mix_sum=0;qa_pcm_hash=1469598103934665603ULL;
 qa_last_ack=qa_apu->outPorts[3];qa_sample_offset=qa_apu->dsp->sampleOffset;qa_last_music=audio_state.current_music_track;qa_observing=1;
 qa_frame_original=frame_callback;frame_callback=qa_frame_hook;
 qa_pcm_file=fopen(output,"wb");if(!qa_pcm_file)exit(23);
 printf("QA_AUDIO_INIT {\"track\":%u,\"hq\":%u,\"msuActive\":%s,\"spcPc\":%u}\n",track,hq,qa_msu_active?"true":"false",qa_apu->spc->pc);
}
static void qa_audio_finish(void){
 for(unsigned i=0;i<180;i++)qa_audio_frame();
 if(qa_output_pending){qa_callback(qa_output_pending);qa_output_pending=0;}
 printf("QA_AUDIO_SUMMARY {\"ticks\":%u,\"callbacks\":%u,\"mixPeak\":%u,\"mixSum\":%llu,\"pcmHash\":\"%016llx\",\"nonzeroSamples\":%u,\"zeroSamples\":%u,\"music\":%u,\"msuActive\":%s,\"msuReadPos\":%.4f,\"pending\":%s,\"effects\":[",qa_tick,qa_callback_count,qa_mix_peak,(unsigned long long)qa_mix_sum,(unsigned long long)qa_pcm_hash,qa_nonzero_samples,qa_muted_samples,audio_state.current_music_track,qa_msu_active?"true":"false",qa_msu_read_pos,qa_apu->inPorts[3]!=qa_apu->outPorts[3]?"true":"false");
 unsigned count=0;for(unsigned i=0;i<128;i++)if(qa_requests[i]||qa_acks[i]||qa_accepts[i]||qa_samples[i])
  printf("%s{\"id\":%u,\"requests\":%u,\"acks\":%u,\"starts\":%u,\"nonzeroVoice7Samples\":%u,\"voice7Peak\":%u,\"voice7AbsSum\":%llu}",count++?",":"",i,qa_requests[i],qa_acks[i],qa_accepts[i],qa_samples[i],qa_peaks[i],(unsigned long long)qa_sample_sum[i]);
 printf("]}\n");fclose(qa_pcm_file);qa_pcm_file=NULL;qa_observing=0;frame_callback=qa_frame_original;platform_audio_shutdown();
}
'''

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def sections(p):
    b=Path(p).read_bytes();n=struct.unpack_from('<H',b,2)[0];opt=struct.unpack_from('<H',b,16)[0]
    symbol_offset,symbol_count=struct.unpack_from('<II',b,8);string_offset=symbol_offset+symbol_count*18
    out={}
    for i in range(n):
        off=20+opt+i*40;name=b[off:off+8].rstrip(b'\0').decode()
        if name.startswith('/'):
            pos=string_offset+int(name[1:]);name=b[pos:b.index(0,pos)].decode()
        size,raw=struct.unpack_from('<II',b,off+16)
        out[name]=dict(size=size,sha256=hashlib.sha256(b[raw:raw+size]if raw else b'').hexdigest(),uninitialized=not bool(raw))
    return out

def private_build(a,source):
    build=a.build.resolve();scratch=a.scratch.resolve();scratch.mkdir(parents=True)
    if digest(build/'earthbound.exe') not in {digest(a.runtime/n) for n in('player.exe','observer.exe')}:
        raise ValueError('Frozen runtime does not match private linked object collection')
    entry=next(r for r in json.loads((build/'compile_commands.json').read_text()) if r['file'].endswith('/port/unix/main.c'))
    flags=entry['command'].split();gcc=Path(flags[0]);objcopy=gcc.parent/'objcopy.exe';ar=gcc.parent/'ar.exe'
    def run(cmd,name):
        result=subprocess.run(list(map(str,cmd)),cwd=build,capture_output=True,timeout=120)
        (scratch/name).write_bytes(result.stdout+result.stderr)
        if result.returncode: raise RuntimeError(result.stderr.decode(errors='replace'))
    changes=[]
    def expose(old,new,names):
        shutil.copy2(old,new);before=sections(old);cmd=[objcopy]
        for oldname,newname in names.items():cmd+=['--redefine-sym',oldname+'='+newname,'--globalize-symbol',newname]
        run([*cmd,new],new.name+'.symbols.log');after=sections(new)
        if before!=after:raise ValueError('Instrumentation altered raw COFF section bytes')
        changes.append(dict(object=old.relative_to(build).as_posix(),productionSha256=digest(old),privateSha256=digest(new),symbolChanges=names,sectionCount=len(before),allRawSectionsByteIdentical=True,sectionHashes=before))
    audio=scratch/'audio.c.obj'
    expose(build/'game_lib/CMakeFiles/earthbound_game.dir/game/audio.c.obj',audio,{'apu':'qa_apu','play_sfx':'qa_production_play_sfx'})
    library=scratch/'libearthbound_game.a';shutil.copy2(build/'game_lib/libearthbound_game.a',library)
    run([ar,'r',library,audio],'archive.log')
    sdl=scratch/'sdl2_audio.c.obj';expose(build/'CMakeFiles/earthbound.dir/platform/sdl2_audio.c.obj',sdl,{'audio_device':'qa_audio_device','audio_callback':'qa_audio_callback','overflow_count':'qa_overflow_count'})
    msu=scratch/'msu_audio.c.obj';expose(build/'CMakeFiles/earthbound.dir/platform/msu_audio.c.obj',msu,{'msu_active':'qa_msu_active','msu_read_pos':'qa_msu_read_pos'})
    sourcefile=scratch/'audio_delivery_driver.c';sourcefile.write_text(source,encoding='utf-8');obj=scratch/'audio_delivery_driver.c.obj'
    flags[flags.index('-o')+1]=str(obj);flags[flags.index('-c')+1]=str(sourcefile);run(flags,'compile.log')
    match=re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_Release (.*?)\n(.*?)(?=\n\n)',(build/'build.ninja').read_text(),re.M|re.S)
    objects=match[1].split(' | ',1)[0].split();libraries=re.search(r'^  LINK_LIBRARIES = (.*)$',match[2],re.M)[1].split()
    main=next(t for t in objects if t.replace('\\','/').endswith('/main.c.obj'));copied=scratch/'platform_main.c.obj';expose(build/main,copied,{'main':'eb_platform_main'})
    replacements={main:copied,'CMakeFiles/earthbound.dir/platform/sdl2_audio.c.obj':sdl,'CMakeFiles/earthbound.dir/platform/msu_audio.c.obj':msu}
    objects=[str(replacements.get(t.replace('\\','/'),build/t))for t in objects]
    libraries=[str(library)if t=='game_lib/libearthbound_game.a'else str(build/t)if t.startswith('game_lib/')else t for t in libraries]
    exe=scratch/'audio-delivery-driver.exe';run([gcc,'-O3','-DNDEBUG',obj,*objects,'-o',exe,'-Wl,--major-image-version,0,--minor-image-version,0',*libraries],'link.log');shutil.copy2(a.runtime/'SDL2.dll',scratch/'SDL2.dll')
    return exe,dict(productionExecutableSha256=digest(build/'earthbound.exe'),productionLibrarySha256=digest(build/'game_lib/libearthbound_game.a'),privateLibrarySha256=digest(library),driverSourceSha256=digest(sourcefile),privateExecutableSha256=digest(exe),objects=changes,sharedBuildModified=False,sharedSourceModified=False,method='Copied COFF symbol rename/global visibility only; all raw sections byte-identical. SPC callback observers forward each original memory callback once. Existing SDL callback executes with the private SDL device paused; deterministic sample-count scheduling replaces operating-system thread scheduling.')

def driver_source(original,shop_mode,encounter_mode=False):
    if encounter_mode:
        s=encounter.driver_source(original)
        at=s.index('static unsigned steps');s=s[:at]+'\n#include "game/position_buffer.h"\n#include "game/map_loader.h"\n#include "include/constants.h"\n'+OBSERVE+s[at:]
        s=s.replace('if(argc!=4)return 2;', 'if(argc!=10)return 2;qa_hq=strtoul(argv[5],NULL,10);qa_track=strtoul(argv[7],NULL,10);qa_suppress=strtoul(argv[8],NULL,10);qa_callback_pattern=strtoul(argv[9],NULL,10);')
        s=s.replace('game_set_fast_forward(true);audio_init();','game_set_fast_forward(false);')
        s=s.replace('  initialize_overworld_state();','  game_state.leader_x_coord=3414;game_state.leader_y_coord=7129;game_state.camera_mode=0;initialize_overworld_state();')
        s=s.replace('  mode_push(GAME_MODE_BATTLE_SCRIPTED,&encounter);pump();',r'''
  update_party();refresh_party_entities();ow.disable_music_changes=0;game_state.leader_moved=0;
  char pcm[4096];snprintf(pcm,sizeof(pcm),"%s/output.pcm",argv[2]);qa_audio_open(qa_track,qa_hq,argv[6],pcm);get_on_bicycle();
  printf("QA_BICYCLE_BEGIN {\"walkingStyle\":%u,\"music\":%u,\"msuActive\":%s}\n",game_state.walking_style,get_current_music(),qa_msu_active?"true":"false");
  if(v[8]){
   const uint8_t*ptrs=ASSET_DATA(ASSET_DATA_BTL_ENTRY_PTR_TABLE_BIN),*groups=ASSET_DATA(ASSET_DATA_ENEMY_BATTLE_GROUPS_TABLE_BIN);
   unsigned p=v[1]*8,offset=(ptrs[p]|(ptrs[p+1]<<8)|(ptrs[p+2]<<16))-0xd0d52d;
   bt.current_battle_group=v[1];bt.enemies_in_battle=0;bt.battle_initiative=0;
   while(groups[offset]!=255){for(unsigned j=0;j<groups[offset];j++)bt.enemies_in_battle_ids[bt.enemies_in_battle++]=groups[offset+1]|(groups[offset+2]<<8);offset+=3;}
   ow.battle_mode=0xffff;encounter=(ModeState){0};encounter.battle_entry.phase=BE_ENTER;mode_push(GAME_MODE_BATTLE_ENTRY,&encounter);
  }else mode_push(GAME_MODE_BATTLE_SCRIPTED,&encounter);
  pump();
  /* Same R-button consumer used by the production bicycle movement dispatch.
   * The saved prepared leader is stationary; this avoids fixture coasting. */
  game_state.leader_moved=0;game_state.camera_mode=0;core.pad1_pressed=PAD_R;core.pad1_held=core.pad1_autorepeat=0;update_leader_movement(0);
  for(unsigned i=0;i<180;i++)host_process_frame();
  printf("QA_BICYCLE_END {\"walkingStyle\":%u,\"music\":%u,\"msuActive\":%s,\"instant\":%u,\"depth\":%u}\n",game_state.walking_style,get_current_music(),qa_msu_active?"true":"false",v[8],g_mode_stack.depth);
''')
        s=s.replace(' fclose(input);audio_shutdown();',' fclose(input);qa_audio_finish();')
        return s
    if shop_mode:
        s=shop.driver_source(original)
        at=s.index('static char replay_path');s=s[:at]+OBSERVE+s[at:]
        s=s.replace('if(argc!=5)return 2;', 'if(argc!=10)return 2;qa_hq=strtoul(argv[5],NULL,10);qa_track=strtoul(argv[7],NULL,10);qa_suppress=strtoul(argv[8],NULL,10);qa_callback_pattern=strtoul(argv[9],NULL,10);')
        s=s.replace('game_set_fast_forward(true);audio_init();','game_set_fast_forward(false);')
        s=s.replace('replay(0,0,0);snap("before-entry");','replay(0,0,0);char pcm[4096];snprintf(pcm,sizeof(pcm),"%s/output.pcm",argv[2]);qa_audio_open(qa_track,qa_hq,argv[6],pcm);snap("before-entry");')
        s=s.replace('snap("after-entry");audio_shutdown();','snap("after-entry");qa_audio_finish();')
        return s
    prefix=helper.DRIVER[:helper.DRIVER.index('static unsigned pump(void)')]
    prefix+='\n#include "game/audio.h"\n#include "platform/pc_options.h"\n'+OBSERVE
    body=r'''
int main(int argc,char**argv){
 setvbuf(stdout,NULL,_IOLBF,65536);if(argc!=10)return 2;
 char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 char *boot[]={"audio-delivery-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--redux-battle-fixture","0"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot)!=0)return 3;
 unsigned effect=strtoul(argv[3],NULL,10),pattern=strtoul(argv[4],NULL,10);qa_suppress=strtoul(argv[8],NULL,10);qa_callback_pattern=strtoul(argv[9],NULL,10);
 ow.disabled_transitions=0;qa_audio_open(strtoul(argv[7],NULL,10),strtoul(argv[5],NULL,10),argv[6],save);
 if(pattern==2){for(unsigned i=0;i<256;i++)play_sfx((i%3==0)?effect:7);}
 else if(pattern==3){play_sfx(effect);play_sfx(7);play_sfx(effect);play_sfx(7);}
 else if(pattern==4){game_set_fast_forward(true);play_sfx(effect);unsigned before=qa_apu->cycles;for(unsigned i=0;i<60;i++)qa_audio_frame();printf("QA_AUDIO_MUTED {\"beforeCycles\":%u,\"afterCycles\":%u,\"nonzeroSamples\":%u,\"pendingRequest\":%u}\n",before,qa_apu->cycles,qa_nonzero_samples,effect);game_set_fast_forward(false);}
 else play_sfx(effect);
 for(unsigned i=0;i<120;i++){
  if(pattern==1&&i<60)play_sfx(7);
  if(pattern==5&&i==20){change_music(96);play_sfx(23);}
  if(pattern==5&&i==50){change_music(5);play_sfx(12);}
  if(pattern==5&&i==80){change_music(82);play_sfx(23);}
  audio_process_sfx_queue();qa_audio_frame();
 }
 qa_audio_finish();return 0;
}
'''
    if original:body=body.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"')
    return prefix+body

def spc_source_contract(a):
    _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h')
    pack_id=assets['music/dataset_table.bin'][2];pack=assets[f'audiopacks/{pack_id}.ebm'];ram=bytearray(65536);pos=0
    while pos+4<=len(pack):
        size,addr=struct.unpack_from('<HH',pack,pos);pos+=4
        if not size:break
        ram[addr:addr+size]=pack[pos:pos+size];pos+=size
    spc=a.upstream/'asm/spc700';defs=(spc/'sfx.spc700.s').read_text();main=(spc/'main.spc700.s').read_text()
    table=main.split('UNK16C7:',1)[1].split('UNK17C5:',1)[0];labels=re.findall(r'^\s*DW (FX[0-9A-F]+)',table,re.M)
    rows=[]
    for effect in(7,12,23,27,115,120):
        label=labels[effect-1];addr=int(label[2:],16);body=defs.split(label+':',1)[1].split('%SFXEND()',1)[0]+'%SFXEND()'
        expected=[]
        for macro,args in re.findall(r'%([A-Z0-9]+)\((.*?)\)',body):
            values=[int(v.strip().replace('$','0x'),0)for v in args.split(',')if v.strip()]
            if macro.startswith('SFXHEADERTYPE')or macro in('SFXNOTE','SFXNOTELENGTH'):expected+=values
            elif macro=='SFXVOLUME':expected+=[0xed,*values]
            elif macro=='SFXEND':expected+=[0]
            elif macro=='SFXREST':expected+=[0xc9]
            else:raise ValueError('Unsupported selected source macro '+macro)
        pointer=int.from_bytes(ram[0x16c7+(effect-1)*2:0x16c7+effect*2],'little')
        actual=bytes(ram[addr:addr+len(expected)])
        # Match the last DB type directly preceding the selected FX label.
        header_type=int(re.search(r'DB (\d+)\s*$',defs.split(label+':',1)[0].rstrip())[1])
        rows.append(dict(effect=effect,sourceLabel=label,pointerMatched=pointer==addr,definitionBytesChecked=len(expected),definitionMatched=actual==bytes(expected),headerTypeMatched=ram[addr-1]==header_type,definitionSha256=hashlib.sha256(actual).hexdigest()))
    return dict(initialPack=pack_id,initialPackSha256=hashlib.sha256(pack).hexdigest(),firmwareRegionSha256=hashlib.sha256(ram[0x0500:0x3000]).hexdigest(),definitions=rows,sourceReferences=[dict(path='asm/spc700/'+n,sha256=digest(spc/n))for n in('main.spc700.s','sfx.spc700.s','globals.spc700.s')],passed=all(v['pointerMatched']and v['definitionMatched']and v['headerTypeMatched']for v in rows))

def main():
    tool_sha256=digest(Path(__file__))
    ap=argparse.ArgumentParser(description=__doc__)
    for n in('build','runtime','native-source','assets','scratch','output','msu','upstream','executed-source','project'):ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--original',action='store_true');ap.add_argument('--shops',type=Path);ap.add_argument('--encounters',action='store_true');ap.add_argument('--diagnostic',action='store_true');ap.add_argument('--pilot',action='store_true');ap.add_argument('--jobs',type=int,default=2);a=ap.parse_args()
    if a.scratch.exists():raise ValueError('Fresh private scratch required')
    contract=spc_source_contract(a)
    exe,build=private_build(a,driver_source(a.original,bool(a.shops),a.encounters))
    cases=[]
    if a.shops:
        for c in json.loads(a.shops.read_text()):
            if c['id'] in ('Onett-bat-equip','Onett-bat-keep-unequipped','Onett-sell-cookie-confirm','Onett-sell-cookie-cancel','Onett-sell-unsellable','Onett-equip-upgrade-sell-old','Onett-insufficient-single','custom66-good','custom66-capacity2','custom66-party4-full56','ordinary-Onett-good','moonside-single'):
                for hq in (0,1):cases.append(dict(id=c['id']+'-'+str(hq),effect=c.get('sound',12),hq=hq,track=46,shop=c,pattern=0,effectTargets=[c.get('sound',12),115]if c['id']in('Onett-bat-equip','Onett-equip-upgrade-sell-old')else[c.get('sound',12)]))
    elif a.encounters:
        for hq in(0,1):
            for instant in(0,1):cases.append(dict(id=f'bicycle-encounter-{instant}-{hq}',effect=23,hq=hq,track=46,pattern=0,encounter=True,instant=instant))
    else:
        for hq in(0,1):
            for track in(46,52,82,96):
                for effect in(12,115,120,23,27):cases.append(dict(id=f'isolated-{track}-{effect}-{hq}',effect=effect,hq=hq,track=track,pattern=0))
            for pattern in(1,2,3,4,5):
                for effect in(12,115,120):cases.append(dict(id=f'schedule-{pattern}-{effect}-{hq}',effect=effect,hq=hq,track=46,pattern=pattern))
    if a.pilot:cases=cases[:2]
    def execute(c):
        session=a.scratch/c['id'];session.mkdir();cfg=session/'case.txt'
        if 'shop'in c:
            v=c['shop'];p=v['plan'];cfg.write_text(' '.join(map(str,[v['entry'],v.get('money',80000),v.get('party',1),v.get('freeSlots',14),v.get('freeSlotsSecond',v.get('freeSlots',14)),v.get('seed',1234567),v.get('flag',0),v.get('item',0),v.get('oldItem',0),v.get('quantity',3),len(p),0,*p])))
        elif c.get('encounter'):
            cfg.write_text(' '.join(map(str,[0,1,0x9e3779b9,1,9999,255,255,0,c['instant']]))+'\n')
            (session/'input.replay').write_text('\n'.join(f'{i} '+('0080'if i%4==1 else'0000')for i in range(120000))+'\n')
        runs=[]
        targets=c.get('effectTargets',[c['effect']])
        variants=[(255,0),(c['effect'],0),(255,1),(255,2),(c['effect'],2)]+[(v,layout)for v in targets if v!=c['effect']for layout in(0,2)]
        for suppress,layout in variants:
            stage=f'suppress{suppress}-layout{layout}';log=session/(stage+'.log')
            command=[exe,a.assets.resolve(),session.resolve(),cfg.resolve()if'shop'in c or c.get('encounter')else c['effect'],'warm'if'shop'in c or c.get('encounter')else c['pattern'],c['hq'],a.msu.resolve(),c['track'],suppress,layout]
            trace=session/(stage+'.trace.log')
            with log.open('wb')as out,trace.open('wb')as diagnostic:
                run=subprocess.run(list(map(str,command)),cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),stdout=out,stderr=diagnostic,timeout=240)
            events=[]
            for line in log.read_text(errors='replace').splitlines():
                if line.startswith('QA_'):
                    prefix,value=line.split(' ',1)
                    try:events.append(dict(type=prefix,value=json.loads(value)))
                    except json.JSONDecodeError:raise RuntimeError('Invalid trace JSON '+line)
            pcm=session/('output.pcm'if'shop'in c or c.get('encounter')else'fixture.srm');private_pcm=session/(stage+'.pcm')
            if pcm.exists():shutil.copyfile(pcm,private_pcm)
            else:private_pcm.write_bytes(b'')
            runs.append(dict(stage=stage,exit=run.returncode,events=events,logSha256=digest(log),diagnosticStreamSha256=digest(trace),pcmSha256=digest(private_pcm),pcmBytes=private_pcm.stat().st_size))
        errors=[]
        if any(r['exit'] for r in runs):errors.append('Private driver failed')
        summaries=[next((e['value']for e in r['events']if e['type']=='QA_AUDIO_SUMMARY'),{})for r in runs]
        actual=summaries[0];effects={v['id']:v for v in actual.get('effects',[])};target=effects.get(c['effect'],{})
        if not actual:errors.append('Missing final production audio summary')
        if 'shop'in c:
            before=next((e['value']for e in runs[0]['events']if e['type']=='QA_SNAP'and e['value']['stage']=='before-entry'),{})
            after=next((e['value']for e in runs[0]['events']if e['type']=='QA_SNAP'and e['value']['stage']=='after-entry'),{})
            if after.get('wallet',0)-before.get('wallet',0)!=c['shop']['expectedDelta']:errors.append('Actual source transaction wallet delta failed')
            if target.get('requests',0)!=c['shop'].get('soundCount',c['shop'].get('expectedCount',1)):errors.append('Source-selected transaction sound count differs')
            if not c['shop'].get('soundCount',c['shop'].get('expectedCount',1))and target.get('nonzeroVoice7Samples',0):errors.append('Declined/failed transaction emitted its success sound')
            for candidate in runs[1:]:
                other=next((e['value']for e in candidate['events']if e['type']=='QA_SNAP'and e['value']['stage']=='after-entry'),{})
                if other!=after:errors.append('Audio negative control or callback layout changed shop transaction state')
        if c.get('encounter'):
            before=next((e['value']for e in runs[0]['events']if e['type']=='QA_BICYCLE_BEGIN'),{})
            after=next((e['value']for e in runs[0]['events']if e['type']=='QA_BICYCLE_END'),{})
            if before.get('walkingStyle')!=3 or before.get('music')!=82:errors.append('Actual bicycle mount did not establish source bicycle style/music')
            if after.get('depth')!=1 or after.get('walkingStyle')!=3 or after.get('music')!=82:errors.append('Full encounter did not restore and retain bicycle style/music')
            if c['hq']and not after.get('msuActive'):errors.append('Bicycle MSU stream did not remain active after full encounter')
            tracks=[v['value']['track']for v in runs[0]['events']if v['type']=='QA_AUDIO_MUSIC']
            if (183 if c['instant']else 5)not in tracks:errors.append('Expected source victory music was not observed')
            outcome=next((e['value']for e in runs[0]['events']if e['type']=='QA_ENCOUNTER'),{})
            for candidate in runs[1:]:
                other=next((e['value']for e in candidate['events']if e['type']=='QA_ENCOUNTER'),{})
                if other!=outcome:errors.append('Audio negative control or callback layout changed complete encounter state')
        if c['hq']and not next((e['value']['msuActive']for e in runs[0]['events']if e['type']=='QA_AUDIO_INIT'),False):errors.append('Requested actual MSU track did not start')
        if runs[0]['pcmSha256']!=runs[2]['pcmSha256']:errors.append('Same sample schedule with split callback sizes changed output PCM')
        if c['pattern']==2:
            sequence=[c['effect']if i%3==0 else 7 for i in range(256)][-63:]
            consumed=[e['value']['command']&127 for e in runs[0]['events']if e['type']=='QA_AUDIO_ACK']
            if consumed!=sequence:errors.append('Native 64-slot queue policy did not retain/consume the most recent 63 commands in order')
        if c['pattern']==4:
            muted=next((e['value']for e in runs[0]['events']if e['type']=='QA_AUDIO_MUTED'),{})
            if not muted or muted['beforeCycles']!=muted['afterCycles']or muted['nonzeroSamples']:errors.append('Explicit fast-forward mute did not suspend SPC and emit silence')
            if not target.get('nonzeroVoice7Samples'):errors.append('Queued sound did not emit PCM after fast-forward was released')
        if c['pattern']==0 and ('shop'not in c or c['shop'].get('soundCount',1)):
            for value in targets:
                for layout in(0,2):
                    positive=next(i for i,v in enumerate(variants)if v==(255,layout));negative=next(i for i,v in enumerate(variants)if v==(value,layout))
                    item=next((v for v in summaries[positive].get('effects',[])if v['id']==value),{})
                    if not item.get('starts'):errors.append(f'Target {value} layout{layout} was never accepted by actual SPC engine')
                    if not item.get('nonzeroVoice7Samples'):errors.append(f'Target {value} layout{layout} emitted no voice7 samples')
                    if runs[positive]['pcmSha256']==runs[negative]['pcmSha256']:errors.append(f'Removing target {value} layout{layout} request did not alter final mixed PCM')
        row=dict(fixture=c,runs=runs,errors=errors,passed=not errors)
        print(json.dumps(dict(id=c['id'],target=target,layoutAudioEqual=runs[0]['pcmSha256']==runs[2]['pcmSha256'],errors=errors)),flush=True)
        return row
    with ThreadPoolExecutor(max_workers=max(1,min(3,a.jobs)))as pool:rows=list(pool.map(execute,cases))
    refs=('src/game/audio.c','src/game_main.c','src/game/position_buffer.c','src/game/overworld.c','src/game/battle.c','src/game/map_loader.c','src/game/display_text_cc.c','port/unix/platform/sdl2_audio.c','port/unix/platform/msu_audio.c')
    audio_inputs=[]
    for track in (5,46,52,53,82,96,101,176,183):
        path=a.msu/f'eb_msu1-{track}.pcm'
        if path.is_file():
            header=path.open('rb').read(8)
            audio_inputs.append(dict(track=track,sha256=digest(path),fileBytes=path.stat().st_size,validHeader=header[:4]==b'MSU1',loopFrame=int.from_bytes(header[4:8],'little')))
        else:audio_inputs.append(dict(track=track,missing=True))
    report=dict(schemaVersion=1,toolVersion='dev19-production-audio-delivery',toolSha256=tool_sha256,privateBuild=build,runtimeSha256={n:digest(a.runtime/n)for n in('player.exe','observer.exe')},assetsSha256=digest(a.assets),originalProfile=a.original,spcSourceContract=contract,executedSourceSnapshot=str(a.executed_source),sourcePatchSha256=digest(a.executed_source/'native-companion.patch'),executedSourceReferences=[dict(path=p,sha256=digest(a.executed_source/p))for p in refs if(a.executed_source/p).exists()],pinnedReduxRevision=helper.PIN,pinnedSourceReferences=[dict(path=p,sha256=digest(a.project/p))for p in('ccscript/shops/ShopSys.ccs','ccscript/shops/ShopMain.ccs','ccscript/redux/msu1.ccs')],readOnlyInstalledAudioInputs=audio_inputs,executedCases=len(rows),skippedCases=0,executedProcesses=sum(len(r['runs'])for r in rows),cases=rows,allPassed=contract['passed']and all(r['passed']for r in rows),limits=['SPC firmware executes under the production Lakesnes interpreter/DSP; not a comparison against an independent SPC emulator or physical SNES.', 'Instrumented memory callbacks forward the production implementation once then observe DSP samples and driver command acceptance. The real SDL callback generates and mixes actual PCM with the private audio device paused.', 'Paired negative controls suppress the selected sound request only; all other requests and shop transaction logic execute normally. Output differences prove emitted PCM changes, not listening, subjective loudness or speaker delivery.', 'The private per-frame callback forwards the existing production overworld callback and emits a 60Hz sample schedule for every host yield, including nested yields. 533/534 and split128 sample callbacks are continuity controls; actual1024 sample callbacks are separately paired delivery controls, with different request latency. Not an exhaustive asynchronous OS scheduling test.', 'Prepared shop/battle source entries execute production parents/children. Full encounters use level99/HP9999/speed/offense255 party1 and actual bicycle mount, normal scripted battle or actual BE_ENTER instant-win predicate. Not natural NPC/enemy-contact reachability or whole playthrough.', 'The 64-slot acknowledgment-aware native queue intentionally adapts the original eight-slot hardware queue. Overflow tests assert the native recent-63 policy, not original hardware queue parity.', 'Fast-forward intentionally mutes the existing callback and suspends SPC execution; bounded release tests prove a retained request plays afterward. They do not promise preservation of every request during prolonged muted overflow.', 'This audits delivery for selected existing sound producers. It does not fix or certify the separate CC19 scripted-choice producer default defect reported by the hook audit.', 'Generated PCM and source-derived ROM/audio data stay private and are never included in reports.'],fullAudioParityVerified=False,fullPlaythroughVerified=False)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    if not report['allPassed']and not a.diagnostic:raise SystemExit(1)
if __name__=='__main__':main()
