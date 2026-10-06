# SPDX-License-Identifier: GPL-3.0-or-later
"""Cold format16 art-only pack migration: real save/load, cached continuation.

The prepared battle-frame-wait checkpoint contains real loaded background state.
It does not represent a natural quest/combat action continuation. Old/new cold
processes load the same checkpoint and execute the same actual native waits.
"""
import argparse, json, os, shutil, subprocess, hashlib
from pathlib import Path
import battle_art_decode_qa_dev20 as art
import battle_action_catalog_qa as helper

DRIVER=art.DRIVER.replace('#include "core/decomp.h"','#include "core/decomp.h"\n#include "core/state_dump.h"')
DRIVER=DRIVER.replace(' }else return 5;',r'''
 }else if(strcmp(argv[3],"save-cold")==0||strcmp(argv[3],"load-cold")==0){
  if(strcmp(argv[3],"save-cold")==0){
   memset(&bt,0,sizeof(bt));bt.battle_mode_flag=1;memset(&psi_animation_state,0,sizeof(psi_animation_state));memset(&ppu,0,sizeof(ppu));
   battle_bg_init();load_enemy_battle_sprites();load_battle_bg(284,0,0);reset_swirl_update_timer();window_system_init();
   memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_NONE;
   ModeState wait={0};wait.battle_wait.kind=BW_FRAMES;wait.battle_wait.remaining=1000;mode_push(GAME_MODE_BATTLE_WAIT,&wait);
   for(unsigned i=0;i<37;i++){mode_dispatch_step(GAME_MODE_BATTLE_WAIT,&g_mode_stack.state[1]);core.frame_counter++;core.nmi_count++;}
   if(!state_dump_save_slots())return 20;
  }else if(!state_dump_load_slots())return 21;
  printf("QA_COLD_LOADED {\"vram\":\"%016llx\",\"palettes\":\"%016llx\",\"bg1\":\"%016llx\",\"game\":\"%016llx\",\"party\":\"%016llx\",\"depth\":%u,\"mode\":%u,\"remaining\":%u,\"frame\":%u}\n",hash(ppu.vram,65536),hash((unsigned char*)ert.palettes,sizeof(ert.palettes)),hash((unsigned char*)&loaded_bg_data_layer1,sizeof(loaded_bg_data_layer1)),hash((unsigned char*)&game_state,sizeof(game_state)),hash((unsigned char*)party_characters,sizeof(party_characters)),g_mode_stack.depth,g_mode_stack.mode[1],g_mode_stack.state[1].battle_wait.remaining,core.frame_counter);
  for(unsigned i=0;i<96;i++){StepResult step=mode_dispatch_step(GAME_MODE_BATTLE_WAIT,&g_mode_stack.state[1]);if(step.kind!=STEP_CONTINUE)return 22;core.frame_counter++;core.nmi_count++;}
  printf("QA_COLD_CONTINUED {\"vram\":\"%016llx\",\"palettes\":\"%016llx\",\"bg1\":\"%016llx\",\"game\":\"%016llx\",\"party\":\"%016llx\",\"depth\":%u,\"mode\":%u,\"remaining\":%u,\"frame\":%u}\n",hash(ppu.vram,65536),hash((unsigned char*)ert.palettes,sizeof(ert.palettes)),hash((unsigned char*)&loaded_bg_data_layer1,sizeof(loaded_bg_data_layer1)),hash((unsigned char*)&game_state,sizeof(game_state)),hash((unsigned char*)party_characters,sizeof(party_characters)),g_mode_stack.depth,g_mode_stack.mode[1],g_mode_stack.state[1].battle_wait.remaining,core.frame_counter);
  load_battle_bg(284,0,0);
  save(argv[2],"reloaded-palette",284,loaded_bg_data_layer1.palette2,32);
  save(argv[2],"reloaded-vram",284,ppu.vram,sizeof(ppu.vram));
  printf("QA_COLD_RELOADED {\"vram\":\"%016llx\",\"palette\":\"%016llx\",\"game\":\"%016llx\",\"party\":\"%016llx\"}\n",hash(ppu.vram,65536),hash((unsigned char*)loaded_bg_data_layer1.palette2,32),hash((unsigned char*)&game_state,sizeof(game_state)),hash((unsigned char*)party_characters,sizeof(party_characters)));
 }else return 5;
''')

def main():
 p=argparse.ArgumentParser()
 for name in ('build','runtime','native-source','old-assets','new-assets','compiled-rom','scratch','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();a.scratch=a.scratch.resolve()
 if a.scratch.exists():raise ValueError('Fresh scratch required')
 a.scratch.mkdir(parents=True);helper.DRIVER=DRIVER;exe,proof=helper.private_build(a)
 env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy');runs={}
 for name,pack,kind in [('prepared',a.old_assets,'save-cold'),('oldCold',a.old_assets,'load-cold'),('newCold',a.new_assets,'load-cold')]:
  folder=a.scratch/name;folder.mkdir()
  if name!='prepared':shutil.copytree(a.scratch/'prepared'/'saves',folder/'saves')
  cp=subprocess.run([str(exe),str(pack.resolve()),str(folder),kind],env=env,capture_output=True,timeout=45)
  (folder/'stdout.log').write_bytes(cp.stdout);(folder/'stderr.log').write_bytes(cp.stderr)
  events={line.split(' ',1)[0]:json.loads(line.split(' ',1)[1])for line in cp.stdout.decode(errors='replace').splitlines()if line.startswith('QA_COLD_')}
  if cp.returncode or len(events)!=3:raise RuntimeError(name+': '+cp.stderr.decode(errors='replace'))
  runs[name]=dict(events=events,stdoutSha256=art.digest(folder/'stdout.log'),stderrSha256=art.digest(folder/'stderr.log'))
 checks=[]
 def check(name,value):checks.append(dict(check=name,passed=bool(value)))
 old=runs['oldCold']['events'];new=runs['newCold']['events'];prepared=runs['prepared']['events']
 check('same-prepared-presentation-restored-old-and-new',old['QA_COLD_LOADED']==new['QA_COLD_LOADED']==prepared['QA_COLD_LOADED'])
 check('same96actual-native-waits-old-and-new',old['QA_COLD_CONTINUED']==new['QA_COLD_CONTINUED']==prepared['QA_COLD_CONTINUED'])
 check('same-expected-wait-state',new['QA_COLD_LOADED']['remaining']==963 and new['QA_COLD_CONTINUED']['remaining']==867 and new['QA_COLD_CONTINUED']['frame']==(new['QA_COLD_LOADED']['frame']+96)&65535)
 check('new-production-load-refreshes-art',old['QA_COLD_RELOADED']['vram']!=new['QA_COLD_RELOADED']['vram']and old['QA_COLD_RELOADED']['palette']!=new['QA_COLD_RELOADED']['palette'])
 source=a.compiled_rom.read_bytes()
 def table(at):
  if source[at]!=0xA9 or source[at+5]!=0xA9:raise ValueError('Unexpected pinned pointer-load code')
  address=int.from_bytes(source[at+1:at+3],'little')|int.from_bytes(source[at+6:at+8],'little')<<16
  return address-0xC00000
 def pointer(at):
  address=int.from_bytes(source[at:at+4],'little');offset=address-0xC00000 if address>=0xC00000 else address
  if not 0<=offset<len(source):raise ValueError('Source pointer outside ROM')
  return offset
 graphics_offset=pointer(table(0x2D1BA)+80*4);palette_offset=pointer(table(0x2D3BB)+102*4)
 expected_graphics,_,_=art.strict_decode(source[graphics_offset:]);expected_palette=source[palette_offset:palette_offset+32]
 actual_graphics=(a.scratch/'newCold'/'reloaded-vram-284.raw').read_bytes()[0x2000:0x4000]
 actual_palette=(a.scratch/'newCold'/'reloaded-palette-284.raw').read_bytes()
 check('new-production-reload-graphics-equal-pinned-source',actual_graphics==expected_graphics[:8192])
 check('new-production-reload-palette-equal-pinned-source',actual_palette==expected_palette and len(expected_palette)==32)
 for name in ('oldCold','newCold'):
  row=runs[name]['events'];check(name+'-story-stats-items-unchanged',all(row[e]['game']==row['QA_COLD_LOADED']['game']and row[e]['party']==row['QA_COLD_LOADED']['party']for e in ('QA_COLD_CONTINUED','QA_COLD_RELOADED')))
 result=dict(toolSha256=art.digest(__file__),artToolSha256=art.digest(art.__file__),provenance=proof,oldPackSha256=art.digest(a.old_assets),newPackSha256=art.digest(a.new_assets),compiledRomSha256=art.digest(a.compiled_rom),sourceGraphicsOffset=graphics_offset,sourcePaletteOffset=palette_offset,expectedGraphicsSha256=art.h(expected_graphics[:8192]),expectedPaletteSha256=art.h(expected_palette),runtimeIdentities={name:art.digest(a.runtime/name)for name in ('player.exe','observer.exe')},executedCases=3,executedAssertions=len(checks),skippedCases=0,allPassed=all(x['passed']for x in checks),checks=checks,runs=runs,scope='Prepared real background 284 + native BW_FRAMES checkpoint, actual format16 writer/loader and 96 actual native wait continuations in three fresh processes. No natural full encounter/quest claim.',cachedOldArtUntilNextLoad=True,fullVisualParityVerified=False,ownerWrites=False)
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(allPassed=result['allPassed'],checks=checks)))
 raise SystemExit(0 if result['allPassed'] else 1)

if __name__=='__main__':main()
