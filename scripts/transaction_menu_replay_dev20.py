# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only geometry planner for actual platform button replay, no menu writes."""
C_SOURCE = r'''
static int qa_at(WindowInfo*w,unsigned page,int x,int y){
 for(unsigned i=0;i<w->menu_count;i++){MenuItem*t=&w->menu_items[i];if((!t->page||t->page==page)&&t->text_x==x&&t->text_y==y)return i;}return -1;
}
/* Read-only counterpart of the production spatial search, only to plan buttons.
 * Every selected result is still produced by the unmodified native dispatcher. */
static int qa_find(WindowInfo*w,unsigned page,int sx,int sy,int dy,int dx){
 int width=w->width-2,rows=(w->height-2)/2,found;
 if(dx){
  for(int x=sx+dx;x>=0&&x<width;x+=dx)if((found=qa_at(w,page,x,sy))>=0)return found;
  for(int x=sx+dx;x>=0&&x<width;x+=dx)for(int y=sy-1;y>=0&&y<rows;y--)if((found=qa_at(w,page,x,y))>=0)return found;
  for(int x=sx+dx;x>=0&&x<width;x+=dx)for(int y=sy+1;y>=0&&y<rows;y++)if((found=qa_at(w,page,x,y))>=0)return found;
 }else{
  for(int y=sy+dy;y>=0&&y<rows;y+=dy)if((found=qa_at(w,page,sx,y))>=0)return found;
  for(int y=sy+dy;y>=0&&y<rows;y+=dy)for(int x=sx-1;x>=0&&x<width;x--)if((found=qa_at(w,page,x,y))>=0)return found;
  for(int y=sy+dy;y>=0&&y<rows;y+=dy)for(int x=sx+1;x>=0&&x<width;x++)if((found=qa_at(w,page,x,y))>=0)return found;
 }return -1;
}
static int qa_move(WindowInfo*w,unsigned page,unsigned current,unsigned key){
 MenuItem*t=&w->menu_items[current];int dx=key==PAD_RIGHT?1:key==PAD_LEFT?-1:0,dy=key==PAD_DOWN?1:key==PAD_UP?-1:0;
 int n=qa_find(w,page,t->text_x,t->text_y,dy,dx);if(n>=0)return n;
 int wx=dx<0?w->width-2:dx>0?-1:t->text_x,wy=dy<0?(w->height-2)/2:dy>0?-1:t->text_y;
 n=qa_find(w,page,wx,wy,dy,dx);if(n>=0&&(dx?w->menu_items[n].text_y==t->text_y:w->menu_items[n].text_x==t->text_x))return n;return -1;
}
static void replay_menu(WindowInfo*w,unsigned pick,unsigned initial){
 if(!w||pick==999){replay(0,0,1);return;}if(pick>=w->menu_count)exit(30);
 enum{N=MAX_MENU_ITEMS*(MAX_MENU_ITEMS+1)};int prev[N],q[N],head=0,tail=0,goal=-1;unsigned keys[N],path[N],count=0,lastpage=1;
 for(unsigned i=0;i<w->menu_count;i++)if(w->menu_items[i].page>lastpage)lastpage=w->menu_items[i].page;
 for(unsigned i=0;i<N;i++)prev[i]=-2;
 unsigned start=w->menu_page_number*MAX_MENU_ITEMS+initial;if(start>=N)exit(31);prev[start]=-1;q[tail++]=start;
 while(head<tail){unsigned at=q[head++],page=at/MAX_MENU_ITEMS,current=at%MAX_MENU_ITEMS;if(current==pick){goal=at;break;}
  unsigned buttons[]={PAD_UP,PAD_LEFT,PAD_DOWN,PAD_RIGHT,PAD_A};
  for(unsigned k=0;k<5;k++){unsigned np=page;int ni;
   if(k==4){if(w->menu_items[current].page||lastpage==1)continue;np=page==lastpage?1:page+1;ni=-1;for(unsigned i=0;i<w->menu_count;i++)if(w->menu_items[i].page==np){ni=i;break;}}
   else ni=qa_move(w,page,current,buttons[k]);
   if(ni<0)continue;unsigned dest=np*MAX_MENU_ITEMS+ni;if(dest>=N)exit(32);if(prev[dest]!=-2)continue;prev[dest]=at;keys[dest]=buttons[k];q[tail++]=dest;
  }
 }
 if(goal<0){fprintf(stderr,"QA navigation unreachable target %u/%u\n",pick,w->menu_count);exit(33);}
 for(int at=goal;prev[at]>=0;at=prev[at])path[count++]=keys[at];
 printf("QA_NAV {\"pick\":%u,\"userdata\":%u,\"keys\":[",pick,w->menu_items[pick].userdata);for(unsigned i=0;i<count;i++)printf("%s%u",i?",":"",path[count-i-1]);printf("]}\n");
 FILE*f=fopen(replay_path,"w");if(!f)exit(10);unsigned end=5+count*16+10;
 for(unsigned frame=0;frame<100000;frame++){unsigned key=0;if(frame>=5&&frame<5+count*16&&(frame-5)%16==0)key=path[count-1-(frame-5)/16];else if(frame>=end&&(frame-end)%16==0)key=PAD_A;fprintf(f,"%u %04x\n",frame,key);}fclose(f);pc_input_script_path=replay_path;platform_input_shutdown();if(!platform_input_init())exit(11);core.pad1_pressed=core.pad1_held=core.pad1_autorepeat=0;
}
'''
