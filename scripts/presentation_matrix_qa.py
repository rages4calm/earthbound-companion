# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise native SDL presentation offscreen across output sizes and aspect settings.
Optional checkpoint is copied; software rendering does not certify physical displays.
"""
import argparse,json,os,shutil,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
helper.DRIVER=helper.DRIVER[:helper.DRIVER.index('static unsigned pump(void)')]+r'''
#include "snes/ppu.h"
#include <SDL.h>
#include "game/settings.h"
#include "platform/pc_options.h"
extern void platform_video_request_screenshot(const char*);
extern bool platform_headless;
int main(int argc,char**argv){
 int rc=eb_platform_main(argc,argv);if(rc)return rc;
 platform_headless=false;if(SDL_Init(SDL_INIT_VIDEO|SDL_INIT_TIMER))return 3;
 const int sizes[][2]={{1280,720},{1920,1080},{2560,1440},{3840,2160},{3440,1440}};
 unsigned cases=0;pc_options.companion=1;pc_options.fullscreen=0;
 for(unsigned size=0;size<5;size++)for(unsigned aspect=0;aspect<3;aspect++)for(unsigned filter=0;filter<3;filter++){
  pc_options.width=sizes[size][0];pc_options.height=sizes[size][1];pc_options.filter=filter;engine_aspect_ratio=aspect;
  if(!platform_video_init())return 4;engine_fx_antialiasing=filter==1;pc_video_apply();
  platform_video_set_zoom(EB_ZOOM_OFF);platform_video_begin_frame();ppu_render_frame(platform_video_send_scanline);
  char name[100];snprintf(name,sizeof(name),"%dx%d-aspect-%u-filter-%u.bmp",sizes[size][0],sizes[size][1],aspect,filter);
  platform_video_request_screenshot(name);platform_video_end_frame();platform_video_shutdown();cases++;
 }
 SDL_Quit();printf("PRESENTATION_MATRIX_PASS %u\n",cases);return 0;
}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('native-source','build','runtime','assets','scratch','output'):p.add_argument('--'+key,type=Path,required=True)
 p.add_argument('--checkpoint',type=Path)
 a=p.parse_args();a.scratch=a.scratch.resolve();a.scratch.mkdir(parents=True,exist_ok=False)
 exe,proof=helper.private_build(a);cmd=[str(exe),'--assets',str(a.assets.resolve()),'--session-dir',str(a.scratch),'--headless','--allow-redux-development','--frames','240','--skip-intro']
 if a.checkpoint:
  (a.scratch/'saves').mkdir();shutil.copy2(a.checkpoint,a.scratch/'saves/quicksave_1.bin.0');cmd+=['--load-state']
 r=subprocess.run(cmd,cwd=a.scratch,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=180)
 log=r.stdout+r.stderr;(a.scratch/'native.log').write_bytes(log)
 if r.returncode or b'PRESENTATION_MATRIX_PASS 45' not in log:raise RuntimeError(log.decode(errors='replace')[-1600:])
 from PIL import Image
 rows=[]
 for image in sorted(a.scratch.glob('*.bmp')):
  expected=tuple(map(int,image.name.split('-')[0].split('x')));im=Image.open(image).convert('RGB')
  if im.size!=expected or im.getbbox() is None:raise RuntimeError('Wrong size/blank frame: '+image.name)
  im.save(image.with_suffix('.png'));rows.append(dict(name=image.name,size=expected,nonBlackBounds=im.getbbox(),passed=True))
 if len(rows)!=45:raise RuntimeError('Missing matrix captures')
 result=dict(passed=True,cases=45,privateBuild=proof,packSha256=helper.digest(a.assets),screens=rows,limits=['SDL dummy/software output verifies requested sizes, aspect/filter paths and nonblank captures; no physical monitor/GPU-driver, controller, every-scene or pixel-perfect claim.'])
 a.output.write_text(json.dumps(result,indent=2)+'\n');print('45 offscreen presentation cases passed')
if __name__=='__main__':main()
