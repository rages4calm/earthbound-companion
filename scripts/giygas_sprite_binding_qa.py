# SPDX-License-Identifier: GPL-3.0-or-later
"""Reproduce a scene-repacked Porky sprite with a stale cached allocation.
Checks real group loading and emitted OAM; no personal checkpoint is needed.
"""
import argparse,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
helper.DRIVER=helper.DRIVER[:helper.DRIVER.index('static unsigned pump(void)')]+r'''
#include "snes/ppu.h"
int main(int argc,char**argv){
 int rc=eb_platform_main(argc,argv);if(rc)return rc;
 memset(&bt,0,sizeof(bt));bt.current_battle_group=476;setup_battle_enemy_sprites();
 if(bt.current_battle_sprites_allocated!=1 || bt.current_battle_sprite_enemy_ids[0]!=216)return 4;
 Battler*b=&bt.battlers_table[8];b->id=216;b->sprite=enemy_config_table[216].battle_sprite;b->consciousness=1;b->ally_or_enemy=1;b->sprite_x=128;b->sprite_y=144;
 unsigned cases=0;
 for(unsigned row=0;row<2;row++)for(unsigned alt=0;alt<2;alt++){
  b->row=row;b->use_alt_spritemap=alt;b->vram_sprite_index=1;
  const uint8_t*map=alt?bt.alt_battle_spritemaps:bt.battle_spritemaps;
  uint8_t expected_tile=map[1],expected_attr=map[2];render_all_battle_sprites();
  if(!ert.oam_write_index || ppu.oam[0].tile!=expected_tile || ppu.oam[0].attr!=expected_attr){fprintf(stderr,"GIYGAS_OAM_FAIL row %u alt %u\n",row,alt);return 7;}
  cases++;
 }
 printf("GIYGAS_BINDING_PASS %u\n",cases);return 0;
}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('native-source','build','runtime','assets','scratch','output'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();a.scratch=a.scratch.resolve();a.scratch.mkdir(parents=True,exist_ok=False)
 exe,proof=helper.private_build(a)
 r=subprocess.run([str(exe),'--assets',str(a.assets.resolve()),'--session-dir',str(a.scratch),'--headless','--allow-redux-development','--inspect-shuffle'],cwd=a.scratch,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=30)
 log=r.stdout+r.stderr;(a.scratch/'native.log').write_bytes(log)
 if r.returncode or b'GIYGAS_BINDING_PASS 4' not in log:raise RuntimeError(log.decode(errors='replace')[-1400:])
 result=dict(passed=True,cases=4,privateBuild=proof,packSha256=helper.digest(a.assets),limits=['Prepared group 476 and stale live-battler binding, front/back and normal/alternate OAM. Natural fight/prayer timeline is checked separately.'])
 a.output.write_text(json.dumps(result,indent=2)+'\n');print('Giygas sprite binding: four cases passed')
if __name__=='__main__':main()
