# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare live production render callbacks with actual SNES ABI samples.

The frozen native library is unchanged. Native pixel uploads also compare with
a separately identified old build when supplied, making return-value changes
reviewable without silently changing the existing sprite rendering behavior.
"""
import argparse, hashlib, json, os, subprocess
from pathlib import Path
import battle_action_catalog_qa as frozen
from check_jev_observer_parity import local_scratch
from snes_sprite_render_abi_oracle import corpus

DRIVER=r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "game_main.h"
#include "game/game_state.h"
#include "game/overworld.h"
#include "game/maternalbound.h"
#include "entity/entity.h"
#include "entity/sprite.h"
#include "entity/callroutine_internal.h"
#include "data/assets.h"
#include "platform/platform.h"
#include "snes/ppu.h"
extern int eb_platform_main(int argc,char **argv);
static uint64_t hash_vram(void){const unsigned char *p=(const unsigned char*)ppu.vram;uint64_t v=1469598103934665603ULL;for(unsigned i=0;i<sizeof(ppu.vram);i++)v=(v^p[i])*1099511628211ULL;return v;}
int main(int argc,char **argv){
 if(argc!=5)return 2;unsigned original=atoi(argv[3]);char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 char *boot[]={"render-abi-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1",original?"--inspect-shuffle":"--redux-battle-fixture","0"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0])-(original?1:0),boot)!=0 || maternalbound_enabled()==original)return 3;
 platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 4;
 entity_system_init();ow.entity_prepared_x=1280;ow.entity_prepared_y=10032;ow.entity_prepared_direction=2;
 const uint8_t *npc=ASSET_DATA(ASSET_DATA_NPC_CONFIG_TABLE_BIN);unsigned initial=npc[773*17+4]|npc[773*17+5]<<8;
 int e=create_prepared_entity_npc(773,initial);if(e<0)return 5;
 uint16_t low=entities.graphics_ptr_lo[e],bank=entities.graphics_sprite_bank[e];unsigned size=sprite_grouping_data_size;
 const uint8_t *group=sprite_grouping_data_buf;int bi=(bank&63)-SPRITE_BANK_FIRST;
 if(bi<0 || bi>=SPRITE_BANK_COUNT || !sprite_banks[bi])return 6;
 const uint8_t *pixels=sprite_banks[bi];unsigned pixel_size=sprite_bank_sizes[bi];
 printf("QA_SETUP {\"actor\":%d,\"sprite\":%d,\"width\":%u,\"height\":%u}\n",e,entities.sprite_ids[e],entities.byte_widths[e],entities.tile_heights[e]);
 FILE *f=fopen(argv[4],"rb");if(!f)return 7;unsigned v[10];
 while(fscanf(f,"%u %u %u %u %u %u %u %u %u %u",&v[0],&v[1],&v[2],&v[3],&v[4],&v[5],&v[6],&v[7],&v[8],&v[9])==10){
  entities.directions[e]=v[2];entities.animation_frame[e]=v[3];entities.surface_flags[e]=v[4];entities.vram_address[e]=v[5];entities.byte_widths[e]=v[6];entities.tile_heights[e]=v[7];
  entities.graphics_ptr_lo[e]=low;entities.graphics_sprite_bank[e]=bank;entities.use_8dir_sprites[e]=0;entities.current_displayed_sprites[e]=0xa55a;
  entities.screen_x[e]=v[8]?128:512;entities.screen_y[e]=100;sprite_grouping_data_buf=group;sprite_grouping_data_size=size;sprite_banks[bi]=pixels;sprite_bank_sizes[bi]=pixel_size;
  if(v[9]==1)entities.tile_heights[e]=0;
  if(v[9]==2)entities.byte_widths[e]=0;
  if(v[9]==3)entities.graphics_ptr_lo[e]=65535;
  if(v[9]==4)entities.graphics_sprite_bank[e]=0;
  if(v[9]==5)sprite_banks[bi]=NULL;
  if(v[9]==6)sprite_bank_sizes[bi]=0;
  if(v[9]==7){sprite_grouping_data_buf=NULL;sprite_grouping_data_size=0;}
  memset(ppu.vram,0xa5,sizeof(ppu.vram));uint16_t pc=0;int16_t got;
  if(v[1]==1)got=cr_render_entity_sprite_me1(e,0,0x1234,&pc);
  else if(v[1]==2)got=cr_render_entity_sprite_me2(e,0,0x1234,&pc);
  else got=cr_render_entity_sprite_me3(e,0,0x1234,&pc);
  printf("QA_RENDER {\"id\":%u,\"value\":%u,\"pc\":%u,\"frame\":%u,\"displayedFlags\":%u,\"vramHash\":\"%016llX\"}\n",v[0],(uint16_t)got,pc,(uint16_t)entities.animation_frame[e],entities.current_displayed_sprites[e]&3,(unsigned long long)hash_vram());
 }
 fclose(f);sprite_grouping_data_buf=group;sprite_grouping_data_size=size;sprite_banks[bi]=pixels;sprite_bank_sizes[bi]=pixel_size;return 0;
}
'''

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('build','runtime','native-source','original-assets','assets','machine-review','machine-scratch','scratch','frozen-source','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--baseline-review',type=Path);p.add_argument('--diagnostic',action='store_true');a=p.parse_args();a.scratch=local_scratch(a.scratch)
    if a.scratch.exists():raise ValueError('Fresh scratch required')
    machine=json.loads(a.machine_review.read_text())
    if not machine['Passed'] or machine['format']!='snes-sprite-render-live-abi-oracle-v1':raise ValueError('Passed actual machine proof required')
    oracle_tool=Path(corpus.__code__.co_filename).resolve()
    if machine['InputIdentities'].get(str(oracle_tool))!=sha(oracle_tool):raise ValueError('Actual machine corpus tool identity changed')
    a.scratch.mkdir(parents=True);frozen.DRIVER=DRIVER;exe,build=frozen.private_build(a);cases=[];failures=[];assertions=0
    baseline=json.loads(a.baseline_review.read_text()) if a.baseline_review else None
    if baseline and (baseline['format']!='native-sprite-render-live-abi-qa-v1' or baseline['machineReportSha256']!=sha(a.machine_review)):raise ValueError('Unrelated baseline machine corpus')
    def check(name,ok,detail):
        nonlocal assertions
        assertions+=1
        if not ok:failures.append({'check':name,'detail':detail})
    for mode in machine['modes']:
        profile=mode['profile'];folder=a.scratch/profile.lower();folder.mkdir();rows=corpus(mode['spriteIdentity'])
        source_samples=a.machine_scratch/profile.lower()/'samples.jsonl'
        if sha(source_samples)!=mode['samplesSha256']:raise ValueError('Machine sample identity changed')
        samples=[json.loads(s) for s in source_samples.read_text().splitlines()]
        rows.extend(dict(rows[0],method=3,surface=0,guard=i) for i in range(1,8))
        data=folder/'cases.tsv';data.write_text(''.join(' '.join(str(v) for v in (i,r['method'],r['direction'],r['frame'],r['surface'],r['vram'],r['width'],r['height'],int(r['onScreen']),r.get('guard',0)))+'\n' for i,r in enumerate(rows)))
        run=subprocess.run([str(exe.resolve()),str((a.original_assets if profile=='Original' else a.assets).resolve()),str(folder.resolve()),str(int(profile=='Original')),str(data.resolve())],cwd=folder,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=120)
        log=run.stdout.decode(errors='replace')+'\n'+run.stderr.decode(errors='replace');(folder/'native.log').write_text(log)
        actual=[json.loads(s.split(' ',1)[1]) for s in log.splitlines() if s.startswith('QA_RENDER ')];setup=[json.loads(s.split(' ',1)[1]) for s in log.splitlines() if s.startswith('QA_SETUP ')]
        check(profile+' process',run.returncode==0,run.returncode);check(profile+' corpus',len(actual)==len(rows) and [r['id'] for r in actual]==list(range(len(rows))),len(actual))
        check(profile+' actual NPC geometry',len(setup)==1 and all(setup[0][n]==mode['spriteIdentity'][n] for n in ('sprite','width','height')),setup)
        previous=[r for r in baseline['cases'] if r['profile']==profile] if baseline else []
        if baseline:check(profile+' baseline corpus',len(previous)==len(rows),len(previous))
        for i,(row,native) in enumerate(zip(rows,actual)):
            expected=samples[i][1] if i<len(samples) else 0
            check(profile+f' case{i} source live return',native['value']==expected,{'got':native['value'],'expected':expected,'method':row['method'],'guard':row.get('guard',0)})
            check(profile+f' case{i} PC/frame',native['pc']==0x1234 and native['frame']==(1 if row['method']==1 else 0 if row['method']==2 else row['frame']),native)
            if baseline and i<len(previous):check(profile+f' case{i} unchanged VRAM upload',native['vramHash']==previous[i]['vramHash'],{'before':previous[i]['vramHash'],'after':native['vramHash']})
            cases.append({'profile':profile,'id':i,'method':row['method'],'guard':row.get('guard',0),'value':native['value'],'vramHash':native['vramHash']})
    report={'format':'native-sprite-render-live-abi-qa-v1','Passed':not failures,'allPassed':not failures,'executedCases':len(cases),'executedAssertions':assertions,'skippedCases':0,'failures':failures,'cases':cases,'privateBuild':build,'runtimeSha256':{n:sha(a.runtime/n) for n in ('player.exe','observer.exe')},'packSha256':{'Original':sha(a.original_assets),'Redux':sha(a.assets)},'machineReportSha256':sha(a.machine_review),'baselineReportSha256':sha(a.baseline_review) if a.baseline_review else None,'frozenFullPatchSha256':sha(a.frozen_source/'native-companion.patch'),'toolSha256':sha(Path(__file__)),'ownerSavesTouched':False,'sharedBuildModified':False,'limits':['Actual frozen production ME1/ME2/ME3 callbacks run on a normally allocated NPC773 sprite, then valid scalar direction/frame/water/VRAM contexts match actual source machine samples.','Seven additional invalid-data guards per profile assert native safe-zero behavior only; invalid source zero-sized sprites are not claimed as a legitimate SNES render domain.','Off-screen native cases preserve preexisting rendering, matching the tested nonzero-direct-page machine context. No broad visibility rule is introduced.','When a baseline report is provided, every VRAM upload checksum must remain identical while the live return changes. Hash equality covers full native VRAM bytes within these fixtures; it is not universal audiovisual equivalence.','Observer hash is paired provenance; the private caller links unchanged player production objects. No owner save, ROM bytecode or original pixels appear in the public report.']}
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ('Passed','executedCases','executedAssertions','skippedCases')}));print(json.dumps(failures[:8]))
    if failures and not a.diagnostic:raise SystemExit(1)

if __name__=='__main__':main()
