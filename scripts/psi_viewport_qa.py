# SPDX-License-Identifier: GPL-3.0-or-later
"""Assert PSI arrangements stay within the native slice for every arrangement change.
Prepared effects use diagnostic white ink; this is geometry, not color parity.
"""
import argparse,json,os,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import battle_action_catalog_qa as helper
helper.DRIVER=helper.DRIVER[:helper.DRIVER.index('static unsigned pump(void)')]+"#include \"snes/ppu.h\"\n"+r'''
#include "game/battle_bg.h"
#include "game/oval_window.h"
#include "game/maternalbound.h"
static pixel_t picture[EB_VIEWPORT_HEIGHT][EB_VIEWPORT_WIDTH];
static void collect(int y,const pixel_t*p){memcpy(picture[y],p,sizeof(picture[y]));}
static void shot(unsigned id,unsigned depth,unsigned target){
 char n[100];snprintf(n,sizeof(n),"psi-%u-depth-%u-target-%u.ppm",id,depth,target);FILE*f=fopen(n,"wb");fprintf(f,"P6\n%d %d\n255\n",EB_VIEWPORT_WIDTH,EB_VIEWPORT_HEIGHT);
 for(unsigned y=0;y<EB_VIEWPORT_HEIGHT;y++)for(unsigned x=0;x<EB_VIEWPORT_WIDTH;x++){uint32_t c=pixel_to_rgb888(picture[y][x]);unsigned char rgb[]={c>>16,c>>8,c};fwrite(rgb,1,3,f);}fclose(f);
}
int main(int argc,char**argv){int rc=eb_platform_main(argc,argv);if(rc)return rc;unsigned cases=0,frames=0,total=maternalbound_enabled()?68:34;
 for(unsigned depth=2;depth<=4;depth+=2)for(unsigned target=32;target<=224;target+=96)for(unsigned id=0;id<total;id++){
  memset(&psi_animation_state,0,sizeof(psi_animation_state));loaded_bg_data_layer1.bitdepth=depth;bt.battle_mode_flag=1;
  bt.current_target=8*sizeof(Battler);Battler*t=&bt.battlers_table[8];memset(t,0,sizeof(*t));t->id=216;t->sprite=enemy_config_table[216].battle_sprite;t->consciousness=1;t->ally_or_enemy=1;t->sprite_x=target;t->sprite_y=144;
  ppu_init();ppu.inidisp=15;ppu.bgmode=depth==2?0:9;unsigned layer=depth==2?1:0;ppu.bg_sc[layer]=0x58;ppu.bg_viewport_fill[layer]=BG_VIEWPORT_FILL;ppu.tm=1<<layer;
  show_psi_animation(id);unsigned visible=0;
  for(unsigned tick=0;tick<4096 && psi_animation_state.time_until_next_frame;tick++){
   unsigned prior=psi_animation_state.frame_data;update_psi_animation();if(tick && psi_animation_state.frame_data==prior && psi_animation_state.time_until_next_frame)continue;ppu.tm=1<<layer;ppu.ts=0;ppu.tm_hdma_active=false;ppu.window_hdma_active=false;ppu.window2_hdma_active=false;ppu.w12sel=ppu.w34sel=ppu.wobjsel=0;ppu.bgmode=depth==2?0:9;
   /* Diagnostic white ink isolates geometry from background fades/palettes. */
   for(unsigned c=0;c<256;c++)ppu.cgram[c]=(c%4)?0x7fff:0;
   ppu_render_frame(collect);unsigned outside=0,inside=0;
   for(unsigned y=0;y<EB_VIEWPORT_HEIGHT;y++)for(unsigned x=0;x<EB_VIEWPORT_WIDTH;x++)if(pixel_to_rgb888(picture[y][x])){if(x<EB_VIEWPORT_PAD_LEFT || x>=EB_VIEWPORT_PAD_LEFT+SNES_WIDTH)outside++;else inside++;}
   frames++;if(outside){printf("PSI_GUTTER_FAIL id %u depth %u target %u pixels %u inside %u\n",id,depth,target,outside,inside);shot(id,depth,target);return 7;}
   if(inside>10 && !visible){visible=1;if(target==128 && (id==6 || id==10 || id==34))shot(id,depth,target);}
  }
  if(psi_animation_state.time_until_next_frame){printf("PSI_TIMEOUT %u\n",id);return 9;}update_psi_animation();if(ppu.bg_viewport_fill[layer]!=BG_VIEWPORT_FILL)return 8;
  cases++;
 }
 printf("PSI_GUTTERS_PASS animations %u cases %u frames %u\n",total,cases,frames);return 0;}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('native-source','build','runtime','assets','scratch','output'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();a.scratch=a.scratch.resolve();a.scratch.mkdir(parents=True,exist_ok=False)
 exe,proof=helper.private_build(a)
 cmd=[str(exe),'--assets',str(a.assets.resolve()),'--session-dir',str(a.scratch),'--save',str(a.scratch/'fixture.srm'),'--headless','--allow-redux-development','--inspect-shuffle']
 cp=subprocess.run(cmd,cwd=a.scratch,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=180)
 log=cp.stdout+cp.stderr;(a.scratch/'native.log').write_bytes(log)
 if cp.returncode:raise RuntimeError(log.decode(errors='replace')[-1600:])
 import re
 m=re.search(rb'PSI_GUTTERS_PASS animations (\d+) cases (\d+) frames (\d+)',log)
 if not m:raise RuntimeError('Missing result marker')
 result=dict(passed=True,animations=int(m[1]),cases=int(m[2]),sampledFrames=int(m[3]),everyArrangementChangeSampled=True,privateBuild=proof,packSha256=helper.digest(a.assets),limits=['Prepared three horizontal targets and two bit depths; diagnostic white palette isolates geometry. No gameplay damage, color parity, physical-controller or full campaign claim.'])
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('passed','animations','cases','sampledFrames')}))
if __name__=='__main__':main()
