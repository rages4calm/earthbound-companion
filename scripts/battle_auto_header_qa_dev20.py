# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual Auto Fight selection, complete scripted encounters and stale UI recovery."""
import argparse,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
from battle_full_encounter_qa_dev18 import driver_source as encounter_driver
from transaction_menu_replay_dev20 import C_SOURCE as MENU_REPLAY

EXTRA=r'''
#include "snes/ppu.h"
static char replay_path[4096];static unsigned auto_planned,auto_seen,header_seen;
static const uint16_t auto_tiles[4]={0x3a69,0x3a6a,0x3a6b,0x3a6c};
static unsigned header_offset(void){return maternalbound_enabled()?0x2b4:0x474;}
static unsigned has_auto(const uint8_t*p){return !memcmp(p,auto_tiles,8);}
static void replay(unsigned direction,unsigned moves,unsigned cancel){
 FILE*f=fopen(replay_path,"w");if(!f)exit(80);
 for(unsigned i=0;i<120000;i++)fprintf(f,"%u %04x\n",i,(i>=5&&i<5+moves*16&&(i-5)%16==0)?direction:(i>=5+moves*16&&(i-5-moves*16)%16==0)?(cancel?PAD_B:PAD_A):0);
 fclose(f);pc_input_script_path=replay_path;platform_input_shutdown();if(!platform_input_init())exit(81);core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=0;
}
'''

def driver_source(original,recovery):
 s=encounter_driver(original)
 s=s.replace('static unsigned pump(void){',EXTRA+MENU_REPLAY+'\nstatic unsigned pump(void){')
 s=s.replace('steps=turns=menu_choices=action_count=ko_count=0;', 'steps=turns=menu_choices=action_count=ko_count=auto_planned=auto_seen=header_seen=0;')
 needle='  core.pad1_pressed=platform_input_get_pad_new();'
 before=r'''
  unsigned qa_top=g_mode_stack.depth-1;ModeState*qa_state=&g_mode_stack.state[qa_top];
  if(!auto_planned&&g_mode_stack.mode[qa_top]==GAME_MODE_SELECTION_MENU&&qa_state->selection_menu.phase==SM_SETUP){
   WindowInfo*w=get_window(win.current_focus_window);if(w)for(unsigned i=0;i<w->menu_count;i++)if(w->menu_items[i].userdata==3){
    unsigned initial=win.restore_menu_backup?win.menu_backup_selected_option:w->selected_option;if(initial>=w->menu_count)initial=0;
    replay_menu(w,i,initial);auto_planned=1;break;
   }
  }
  if(game_state.auto_fight_enable){auto_seen++;if(has_auto(win.bg2_buffer+header_offset()))header_seen++;}
'''
 s=s.replace(needle,before+needle)
 s=s.replace('char replay_path[4096];snprintf(replay_path','snprintf(replay_path')
 marker='  printf("QA_ENCOUNTER '
 report=r'''
  unsigned off=header_offset();
  printf("QA_AUTO {\"id\":%u,\"autoSelected\":%u,\"autoTicks\":%u,\"visibleHeaderTicks\":%u,\"depth\":%u,\"enabled\":%u,\"shadowAfterExit\":%u,\"displayedAfterExit\":%u}\n",case_id,auto_planned,auto_seen,header_seen,g_mode_stack.depth,game_state.auto_fight_enable,has_auto(win.bg2_buffer+off),has_auto(ppu.vram+0xf800+off));
'''
 if recovery:
  report+=r'''
  /* Prepared older-state shape: actual source header draw/upload, then idle
   * flags from completed combat. No injected final cleanup result. */
  bt.battle_mode_flag=1;render_hppp_window_header();upload_battle_screen_to_vram();bt.battle_mode_flag=0;ow.battle_mode=0;game_state.auto_fight_enable=0;
  uint8_t before[BG2_BUFFER_SIZE],vram_before[0x800];memcpy(before,win.bg2_buffer,sizeof(before));memcpy(vram_before,ppu.vram+0xf800,0x800);
  clear_stale_battle_auto_header();unsigned outside=0;for(unsigned i=0;i<0x800;i++)if((i<off||i>=off+8)&&(before[i]!=win.bg2_buffer[i]||vram_before[i]!=ppu.vram[0xf800+i]))outside++;
  unsigned cleared=!has_auto(win.bg2_buffer+off)&&!has_auto(ppu.vram+0xf800+off);
  win.bg2_buffer[off]=0x34;ppu.vram[0xf800+off]=0x34;memcpy(before,win.bg2_buffer,sizeof(before));memcpy(vram_before,ppu.vram+0xf800,0x800);clear_stale_battle_auto_header();
  unsigned unrelated=!memcmp(before,win.bg2_buffer,sizeof(before))&&!memcmp(vram_before,ppu.vram+0xf800,0x800);
  bt.battle_mode_flag=1;render_hppp_window_header();upload_battle_screen_to_vram();clear_stale_battle_auto_header();unsigned active_preserved=has_auto(win.bg2_buffer+off)&&has_auto(ppu.vram+0xf800+off);bt.battle_mode_flag=0;clear_hppp_window_header();
  printf("QA_RECOVERY {\"id\":%u,\"cleared\":%u,\"outsideChanged\":%u,\"unrelatedPreserved\":%u,\"activePreserved\":%u}\n",case_id,cleared,outside,unrelated,active_preserved);
'''
 s=s.replace(marker,report+marker)
 return s

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in ('build','native-source','assets','runtime','scratch','output','project'):ap.add_argument('--'+n,type=Path,required=True)
 ap.add_argument('--original',action='store_true');ap.add_argument('--baseline',action='store_true');a=ap.parse_args()
 assert not a.scratch.exists();a.scratch.mkdir(parents=True);session=a.scratch/'session';session.mkdir()
 helper.DRIVER=driver_source(a.original,not a.baseline);exe,build=helper.private_build(a)
 (session/'input.replay').write_text('\n'.join(str(i)+' '+('0080' if i%4==1 else '0000') for i in range(120000))+'\n',encoding='utf-8')
 cfg=a.scratch/'cases.tsv';cfg.write_text('\n'.join(' '.join(map(str,[i,g,0x12345678,4,9999,255,255,0,1])) for i,g in enumerate((1,48,448)))+'\n',encoding='utf-8')
 run=subprocess.run([str(exe),str(a.assets.resolve()),str(session.resolve()),str(cfg.resolve())],cwd=session,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=120)
 log=a.scratch/'native.log';log.write_bytes(run.stdout+run.stderr);events=[]
 for line in run.stdout.decode(errors='replace').splitlines():
  if line.startswith(('QA_AUTO ','QA_RECOVERY ')):
   kind,value=line.split(' ',1);events.append(dict(type=kind,actual=json.loads(value)))
 rows=[]
 for i,g in enumerate((1,48,448)):
  e=[v for v in events if v['actual']['id']==i];auto=next((v['actual'] for v in e if v['type']=='QA_AUTO'),{});rec=next((v['actual'] for v in e if v['type']=='QA_RECOVERY'),{});errors=[]
  if run.returncode:errors.append('nativeExit:'+str(run.returncode))
  if not auto or not auto['autoSelected'] or not auto['autoTicks'] or not auto['visibleHeaderTicks'] or auto['depth']!=1 or auto['enabled']:errors.append('Auto Fight encounter did not finish normally')
  if auto and (auto['shadowAfterExit'] or auto['displayedAfterExit']):errors.append('AUTO leaked out of completed battle')
  if not a.baseline and (not rec or not rec['cleared'] or rec['outsideChanged'] or not rec['unrelatedPreserved'] or not rec['activePreserved']):errors.append('stale-header selective recovery/guard failed')
  rows.append(dict(group=g,passed=not errors,errors=errors,events=e))
 report=dict(toolVersion='dev20-auto-header',originalPack=a.original,privateBuild=build,assetsSha256=helper.digest(a.assets),nativeExit=run.returncode,logSha256=helper.digest(log),cases=rows,allPassed=all(r['passed'] for r in rows),limits=['Three prepared scripted encounter groups, actual platform menu navigation selects Auto Fight, real production battle AI/turn/ending. Not every enemy/escape/defeat/cold battle state.','Recovery fixtures use actual header draw/upload followed by completed idle flags. Exact four-tile clearing, unrelated tiles and active-battle preservation are checked; not an independent full pixel audit.'],fullPlaythroughVerified=False)
 a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(cases=len(rows),passed=sum(r['passed'] for r in rows),errors=[r['errors'] for r in rows])))
 if not report['allPassed'] and not a.baseline:raise SystemExit(1)
if __name__=='__main__':main()
