# SPDX-License-Identifier: GPL-3.0-or-later
"""Private rendered-equipment fixtures and black staging-canvas regression.

Links the unchanged production library. Strong gear is injected only in a
fresh private process; no player saves or shipping cheat switches are changed.
"""
import argparse,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper
DRIVER=helper.DRIVER[:helper.DRIVER.index('static unsigned pump(void)')]+r'''
#include "snes/ppu.h"
#include "include/constants.h"
static unsigned checks,cases,max_end;
static unsigned char expected[16][128];
static pixel_t picture[EB_VIEWPORT_HEIGHT][EB_VIEWPORT_WIDTH];
static void fail(const char*why,unsigned a,unsigned b){fprintf(stderr,"FAIL %s %u %u\n",why,a,b);exit(5);}
static void collect(int y,const pixel_t*p){memcpy(picture[y],p,EB_VIEWPORT_WIDTH*sizeof(pixel_t));}
static void picture_save(const char*label){char path[256];snprintf(path,sizeof(path),"%s.ppm",label);FILE*f=fopen(path,"wb");fprintf(f,"P6\n%d %d\n255\n",EB_VIEWPORT_WIDTH,EB_VIEWPORT_HEIGHT);for(int y=0;y<EB_VIEWPORT_HEIGHT;y++)for(int x=0;x<EB_VIEWPORT_WIDTH;x++){uint32_t c=pixel_to_rgb888(picture[y][x]);unsigned char p[3]={c>>16,c>>8,c};fwrite(p,1,3,f);}fclose(f);}
static unsigned paint(const char*s,unsigned x,unsigned font){for(;*s;s++){unsigned code=ascii_to_eb_char(*s)-0x50;const uint8_t*g=font_get_glyph(font,code);unsigned h=font_get_height(font),w=font_get_width(font,code)+character_padding;while(w){unsigned step=w>8?8:w,old=x/8,next=(x+step)/8;if(x%8==0)for(unsigned y=0;y<16;y++)memset(expected[y]+old*8,0,8);if(next!=old)for(unsigned y=0;y<16;y++)memset(expected[y]+next*8,0,8);for(unsigned y=0;y<h;y++)for(unsigned dx=0;dx<8;dx++)if(((x+dx)/8==old||next!=old)&&!(g[y]&(128>>dx))&&x+dx<128)expected[y][x+dx]=1;x+=step;w-=step;g+=h;}}return x;}
static unsigned paint_number(unsigned value,unsigned x,unsigned font){char s[16];snprintf(s,sizeof(s),"%u",value);return paint(s,x,font);}
static unsigned ink(WindowInfo*w,unsigned x,unsigned y,unsigned row){unsigned cw=w->width-2,at=row*2*cw+(y/8)*cw+x/8;if(at>=w->content_tilemap_size)fail("tilemap bounds",at,w->content_tilemap_size);unsigned tile=w->content_tilemap[at]&1023,vram=0xc000+tile*16+(y&7)*2,mask=128>>(x&7);return !!(ppu.vram[vram]&mask)&&!(ppu.vram[vram+1]&mask);}
static void row_check(unsigned window,unsigned row,unsigned a,unsigned b,int percent,unsigned col){WindowInfo*w=get_window(window);if(!w)fail("missing window",window,0);memset(expected,0,sizeof(expected));unsigned end=paint_number(a,col,w->font);if(percent&&a==b)end=paint("%",end,w->font);if(a!=b){/* independent geometric arrow: horizontal shaft and two diagonal arms */for(unsigned dx=0;dx<=4;dx++)expected[6][end+dx]=1;expected[4][end+2]=expected[5][end+3]=expected[7][end+3]=expected[8][end+2]=1;end+=6;end=paint_number(b,end,w->font);if(percent)end=paint("%",end,w->font);}unsigned width=(w->width-2)*8;if(end>width)fail("comparison exceeds content",end,width);if(end>max_end)max_end=end;for(unsigned y=0;y<16;y++)for(unsigned x=col;x<width;x++){checks++;if(ink(w,x,y,row)!=expected[y][x]){fprintf(stderr,"window %u row %u values %u -> %u x %u y %u\n",window,row,a,b,x,y);fail("rendered glyph mismatch",cases,checks);}}}
static void equipment_cases(void){if(!maternalbound_enabled()){printf("QA_EQUIPMENT {\"cases\":0,\"applicable\":false,\"reason\":\"Redux extended preview only\"}\n");return;}static const unsigned damage[]={0,30,60,95},status[]={0,50,90,100};for(unsigned c=1;c<=4;c++){
 CharStruct*p=&party_characters[c-1];memset(p->items,0,sizeof(p->items));memset(p->equipment,0,sizeof(p->equipment));p->base_offense=120;p->base_defense=100;p->base_speed=80;p->base_guts=50;p->base_luck=70;p->boosted_guts=p->boosted_speed=p->boosted_luck=0;
 unsigned best[4]={0},strength[4]={0};for(unsigned item=1;item<255;item++){const ItemConfig*i=get_item_entry(item);unsigned slot=get_item_subtype(item);if(get_item_type(item)!=2||!slot||!check_item_usable_by(c,item))continue;if(i->params[0]>=strength[slot-1]){best[slot-1]=item;strength[slot-1]=i->params[0];}}
 for(unsigned slot=0;slot<4;slot++)if(best[slot]){p->items[slot]=best[slot];equip_item(c,slot+1);}
 printf("QA_BEST %u %u %u %u %u\n",c,best[0],best[1],best[2],best[3]);
 for(unsigned item=0;item<255;item++){
  unsigned slot=item?get_item_subtype(item):1;if(item&&(get_item_type(item)!=2||!slot||!check_item_usable_by(c,item)))continue;
  p->items[4]=item;uint8_t preview_slots[4];memcpy(preview_slots,p->equipment,4);preview_slots[slot-1]=item?5:0;uint8_t a[5],b[5],ar[6],br[6];if(!equipment_snapshot(c,p->equipment,a,ar)||!equipment_snapshot(c,preview_slots,b,br))fail("snapshot",c,item);
  close_all_windows();text_cursor_callback_from_id(CURSOR_CB_CS_EQUIPMENT)(c);TextMenuSaveState s;text_menus_savestate_pack(&s);s.compare_equipment_mode=1;s.character_for_equip_menu=c;text_menus_savestate_unpack(&s);text_cursor_callback_from_id(CURSOR_CB_EQUIP_PREVIEW_WEAPON+slot-1)(item?5:0xffff);render_all_windows();cases++;
  for(unsigned row=0;row<5;row++)row_check(WINDOW_EQUIPMENT_STATS,row,a[row],b[row],0,50);
  for(unsigned row=0;row<6;row++){const unsigned*percent=row<2?damage:status;row_check(WINDOW_EQUIPMENT_RESISTANCES,row,percent[ar[row]],percent[br[row]],1,64);}
  if(!item){ppu_render_frame(collect);char label[64];snprintf(label,sizeof(label),"best-gear-character-%u",c);picture_save(label);}
 }
}printf("QA_EQUIPMENT {\"cases\":%u,\"pixelsCompared\":%u,\"maxRunEnd\":%u,\"passed\":true}\n",cases,checks,max_end);}
static void black_canvas_cases(void){
 close_all_windows();memset(&ppu,0,sizeof(ppu));ppu.bgmode=9;ppu.inidisp=15;ppu.bg_sc[0]=0x39;ppu.bg_sc[1]=0x59;ppu.bg_sc[2]=0x7c;ppu.bg_nba[0]=0x20;ppu.bg_nba[1]=6;ppu.tm=3;ppu.cgram[1]=31;
 /* Transparent tile zero in the native view, red tile one in both gutters. */
 for(unsigned y=0;y<8;y++)ppu.vram[32+y*2]=255;
 for(unsigned ty=0;ty<32;ty++)for(unsigned tx=0;tx<64;tx++){unsigned at=2*(0x3800+(tx>=32?1024:0)+ty*32+tx%32);ppu.vram[at]=(tx<EB_VIEWPORT_PAD_LEFT/8||tx>=(EB_VIEWPORT_PAD_LEFT+256)/8)?1:0;}
 ppu_render_frame(collect);unsigned lit=0;for(unsigned y=0;y<EB_VIEWPORT_HEIGHT;y++)for(unsigned x=0;x<EB_VIEWPORT_WIDTH;x++)lit+=picture[y][x]!=0;if(lit)fail("black canvas leaks terrain",lit,0);
 /* Reveal one pixel in the native map: the ordinary wider terrain must return. */
 unsigned at=2*(0x3800+(EB_VIEWPORT_PAD_TOP/8)*32+(EB_VIEWPORT_PAD_LEFT/8));ppu.vram[at]=1;ppu_render_frame(collect);lit=0;for(unsigned y=0;y<EB_VIEWPORT_HEIGHT;y++)for(unsigned x=0;x<EB_VIEWPORT_WIDTH;x++)lit+=picture[y][x]!=0;if(lit<=64)fail("ordinary map hidden",lit,0);
 /* The overlay layer survives a blank map. */
 ppu.vram[at]=0;ppu.tm=7;ppu.bg_win_y_offset=EB_VIEWPORT_PAD_TOP;ppu.vram[0xc000+16]=255;ppu.vram[0xf800]=1;ppu_render_frame(collect);if(!picture[EB_VIEWPORT_PAD_TOP][EB_VIEWPORT_PAD_LEFT])fail("overlay hidden",0,0);
 printf("QA_CANVAS {\"hiddenStageBlack\":true,\"ordinaryTerrainRestored\":true,\"overlayPreserved\":true}\n");
}
int main(int argc,char**argv){if(argc!=3)return 2;char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);char*boot[]={"presentation-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot))return 3;platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 4;dt.instant_printing=1;equipment_cases();black_canvas_cases();platform_input_shutdown();return 0;}
'''
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('native-source','build','runtime','assets','scratch','output'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();a.scratch=a.scratch.resolve();a.scratch.mkdir(parents=True,exist_ok=False)
 helper.DRIVER=DRIVER;exe,proof=helper.private_build(a)
 r=subprocess.run([str(exe),str(a.assets.resolve()),str(a.scratch)],cwd=a.scratch,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=120)
 log=a.scratch/'native.log';log.write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError((r.stdout+r.stderr).decode(errors='replace')[-2000:])
 rows={s.split(' ',1)[0]:json.loads(s.split(' ',1)[1])for s in r.stdout.decode().splitlines()if s.startswith(('QA_EQUIPMENT ','QA_CANVAS '))};assert len(rows)==2
 report=dict(version='0.5.0-redux-dev.26',passed=True,privateBuild=proof,packSha256=helper.digest(a.assets),results=rows,limits=['Private fixture inventory; all usable equipment candidates for four characters, production preview callbacks and independently painted glyph pixels. No physical controller/audio or full campaign claim.'],ownerSavesTouched=False,shippingCheatsAdded=False)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(rows))
if __name__=='__main__':main()
