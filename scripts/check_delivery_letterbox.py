"""Focused delivery-exit mask checks against an existing Windows native build.

Requires a privately supplied Original or supported Redux asset pack. Does not
open a player's saves, launch a campaign, or change the supplied source/build.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess

DRIVER = r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include "game/game_state.h"
#include "game/overworld.h"
#include "game/maternalbound.h"
#include "game/audio.h"
#include "game/battle.h"
#include "snes/ppu.h"
#include "platform/pc_options.h"
#include "data/event_script_data.h"
extern int eb_platform_main(int,char**);
extern int16_t callroutine_dispatch(uint32_t,int16_t,int16_t,uint16_t,uint16_t*);
int main(int argc,char **argv) {
 char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 char *boot[]={"delivery-test","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
 if(eb_platform_main(12,boot))return 2;
 audio_init();unsigned checks=0;
 for(unsigned hidden=0;hidden<2;hidden++)for(unsigned pending=0;pending<2;pending++)for(unsigned direction=0;direction<3;direction++) {
  pc_options.disable_cinematic_letterbox=hidden;
  ow.pending_interactions=pending;ow.overworld_status_suppression=pending;
  ow.redux_letterbox_active=1;ow.redux_letterbox_top=39;ow.redux_letterbox_direction=direction;
  ppu.tm_hdma_active=true;bt.battle_mode_flag=0;
  uint16_t pc=0;callroutine_dispatch(ROM_ADDR_RESTORE_OVERWORLD_STATE,0,0,0,&pc);
  int clear=maternalbound_enabled()&&pending&&direction==0;
  if(clear) {
   if(ow.redux_letterbox_active||ow.redux_letterbox_top||ppu.tm_hdma_active)return 10;
   /* Later screens must not inherit a mask on their next effects tick. */
   maternalbound_effects_tick();if(ppu.tm_hdma_active)return 11;
  }else if(!ow.redux_letterbox_active||ow.redux_letterbox_top!=39||!ppu.tm_hdma_active)return 12;
  if(ow.pending_interactions)return 13;
  checks++;
 }
 audio_shutdown();printf("PASS delivery exit: %u cases; Redux=%d\n",checks,maternalbound_enabled());return 0;
}
'''

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('native-source','build','assets','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--callroutine-source',type=Path)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('Choose a fresh output directory')
    args.output.mkdir(parents=True)
    spec=importlib.util.spec_from_file_location('native_fixture',Path(__file__).with_name('check_native_render_lifecycle.py'))
    fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
    fixture.N=args.native_source.resolve();fixture.B=args.build.resolve();fixture.W=args.output.resolve()
    source=(args.callroutine_source or fixture.N/'src/entity/callroutine.c').resolve()
    exe=fixture.build('driver',DRIVER+'\n#include "'+source.as_posix()+'"\n')
    session=fixture.W/'session';session.mkdir()
    result=subprocess.run([str(exe),str(args.assets.resolve()),str(session)],capture_output=True,
                          env=dict(os.environ,SDL_AUDIODRIVER='dummy',SDL_VIDEODRIVER='dummy'),timeout=45)
    (fixture.W/'native.log').write_bytes(result.stdout+result.stderr)
    (fixture.W/'result.json').write_text(json.dumps({'passed':result.returncode==0,'exitCode':result.returncode,
        'fullEventPlaythrough':False,'scope':'Actual delivery restore callroutine; held mask cleanup, later effects tick, Original control, opening/closing and unrelated mask preservation'},indent=2)+'\n')
    print(result.stdout.decode(errors='replace').strip());raise SystemExit(result.returncode)

if __name__=='__main__':main()
