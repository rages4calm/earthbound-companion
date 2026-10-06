# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual v1 Down pulses at the source-selected full bag + pooled-item menu."""
import barter_delivery_qa_dev20 as runner
runner.MENU_REPLAY=runner.MENU_REPLAY.replace('static void replay_menu(', 'static void replay_menu_spatial(')+r'''
static void replay_menu(WindowInfo*w,unsigned pick,unsigned initial){
 if(w&&w->id==2&&w->menu_count==15&&pick==14){
  printf("QA_GEOMETRY_ATTEMPT {\"window\":2,\"height\":%u,\"targetIndex\":14,\"targetY\":%u,\"downPulses\":7}\n",w->height,w->menu_items[14].text_y);replay(PAD_DOWN,7,0);
 }else replay_menu_spatial(w,pick,initial);
}
'''
if __name__=='__main__':runner.main()
