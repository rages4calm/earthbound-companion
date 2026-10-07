"""Verify the title-only overlay, both production animations and launcher isolation.

Private driver links the unchanged production objects. Expected title bytes come
from the owner's Original pack; screenshots and game-derived dumps stay private.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, shutil, struct, subprocess
from PIL import Image

DRIVER = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "data/assets.h"
#include "data/runtime_assets.h"
#include "data/event_script_data.h"
#include "game/maternalbound.h"
#include "intro/title_screen.h"
#include "core/mode_stack.h"
#include "core/memory.h"
#include "entity/entity.h"
#include "snes/ppu.h"
#include "game_main.h"
int eb_platform_main(int,char**);
static const unsigned ids[]={ASSET_INTRO_TITLE_SCREEN_ARR_LZHAL,ASSET_INTRO_TITLE_SCREEN_GFX_LZHAL,
ASSET_INTRO_TITLE_SCREEN_PAL_LZHAL,ASSET_INTRO_TITLE_SCREEN_LETTERS_GFX_LZHAL,
ASSET_INTRO_TITLE_SCREEN_SCRIPT_POINTERS_BIN,ASSET_INTRO_TITLE_SCREEN_SCRIPTS_BIN,
ASSET_INTRO_TITLE_SCREEN_SPRITEMAPS_BIN,ASSET_E1AE7C_BIN_LZHAL,ASSET_E1AE83_BIN_LZHAL,ASSET_E1AEFD_BIN_LZHAL};
static int title(unsigned n){for(unsigned i=0;i<10;i++)if(n==ids[i])return 1;return 0;}
static void require(int ok,const char*message){if(!ok){fprintf(stderr,"FAIL: %s\n",message);exit(9);}}
static void registry(int title_first){
 free_event_script_data();free_title_screen_script_data();
 if(title_first)load_title_screen_script_data();
 load_event_script_data();int count=script_bank_count;
 load_title_screen_script_data();require(count==script_bank_count,"title registered twice");
 int found=0;for(int i=0;i<script_bank_count;i++)if(script_banks[i].rom_bank==0xC4&&script_banks[i].rom_base_addr==0x2172){
  require(script_banks[i].size==ASSET_SIZE(ASSET_INTRO_TITLE_SCREEN_SCRIPTS_BIN)&&
   !memcmp(script_banks[i].data,ASSET_DATA(ASSET_INTRO_TITLE_SCREEN_SCRIPTS_BIN),script_banks[i].size),"cold title bank differs");found++;
 }
 require(found==1,"ambiguous C4 title region");
 printf("registry order %d: %d banks, PASS\n",title_first,count);
}
int main(int argc,char**argv){
 if(argc==5){
  require(eb_runtime_assets_load(argv[1])==EB_ASSETS_OK,"gameplay pack");
  const void*before[ASSET_COUNT];size_t lengths[ASSET_COUNT];
  for(unsigned i=0;i<ASSET_COUNT;i++){before[i]=ASSET_DATA(i);lengths[i]=ASSET_SIZE(i);}
  if(strcmp(argv[3],"-")){
   require(eb_runtime_assets_use_original_title(argv[3])!=EB_ASSETS_OK,"invalid donor accepted");
   for(unsigned i=0;i<ASSET_COUNT;i++)require(before[i]==ASSET_DATA(i)&&lengths[i]==ASSET_SIZE(i),"partial invalid commit");
   require(!eb_runtime_assets_original_title(),"invalid donor enabled override");
  }
  require(eb_runtime_assets_use_original_title(argv[2])==EB_ASSETS_OK,"Original donor");
  unsigned untouched=0;for(unsigned i=0;i<ASSET_COUNT;i++)if(!title(i)){
   require(before[i]==ASSET_DATA(i)&&lengths[i]==ASSET_SIZE(i),"non-title asset changed");untouched++;
  }
  require(maternalbound_bind_dialogue(ASSET_DATA(ASSET_DIALOGUE_DIALOGUE_BIN),ASSET_SIZE(ASSET_DIALOGUE_DIALOGUE_BIN))&&maternalbound_enabled(),"Redux mode lost");registry(0);registry(1);
  FILE*f=fopen(argv[4],"wb");require(f!=NULL,"output");
  for(unsigned i=0;i<10;i++){unsigned length=ASSET_SIZE(ids[i]);fwrite(&ids[i],4,1,f);fwrite(&length,4,1,f);fwrite(ASSET_DATA(ids[i]),1,length,f);}fclose(f);
  free_event_script_data();free_title_screen_script_data();eb_runtime_assets_unload();
  require(!eb_runtime_assets_original_title()&&!eb_runtime_assets_ready(),"overlay unload");
  printf("%u non-title assets preserved, failure atomicity and unload PASS\n",untouched);return 0;
 }
 if(argc!=7)return 2;
 char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[3]);
 char*boot[]={"title-qa","--assets",argv[1],"--session-dir",argv[3],"--save",save,"--allow-redux-development","--headless","--inspect-shuffle","--original-title-assets",argv[2]};
 require(eb_platform_main(strcmp(argv[2],"-")?12:10,boot)==0,"production initialization");
 load_title_screen_script_data();g_mode_stack.depth=0;
 unsigned quick=atoi(argv[4]);title_screen_setup(quick);
 ModeState initial={0};initial.title_screen.phase=TS_WARMUP;initial.title_screen.quick_mode=quick;mode_push(GAME_MODE_TITLE_SCREEN,&initial);
 for(unsigned frame=0;frame<=600;frame++){
  game_loop_step();host_process_frame();host_root_boundary();
  if(frame==0||frame==30||frame==60||frame==150||frame==300||frame==500||frame==600){
   char path[4096];snprintf(path,sizeof(path),"%s/%s-%u.bin",argv[5],argv[6],frame);FILE*f=fopen(path,"wb");require(f!=NULL,"frame output");
   fwrite(ppu.vram,1,sizeof(ppu.vram),f);fwrite(ert.palettes,1,sizeof(ert.palettes),f);fwrite(ppu.oam,1,sizeof(ppu.oam),f);fwrite(ppu.oam_hi,1,sizeof(ppu.oam_hi),f);fclose(f);
  }
 }
 puts("production title frames PASS");return 0;
}
'''

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('source','build','original','redux','scratch'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();source,build,original,redux,scratch=(getattr(a,n).resolve() for n in ('source','build','original','redux','scratch'))
    scratch.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
    def run(cmd,log,cwd=scratch):
        r=subprocess.run(list(map(str,cmd)),cwd=cwd,env=env,capture_output=True,timeout=90)
        (scratch/log).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(log+': '+(r.stdout+r.stderr)[-1800:].decode(errors='replace'))
        return (r.stdout+r.stderr).decode(errors='replace')
    driver=scratch/'driver.c';driver.write_text(DRIVER,encoding='utf-8')
    entries=json.loads((build/'compile_commands.json').read_text());flags=next(x['command'] for x in entries if x['file'].endswith('/port/unix/main.c')).split()
    obj=scratch/'driver.c.obj';flags[flags.index('-o')+1]=str(obj);flags[flags.index('-c')+1]=str(driver);run(flags,'compile.log',build)
    ninja=(build/'build.ninja').read_text();match=re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_Release (.*?)\n(.*?)(?=\n\n)',ninja,re.M|re.S)
    objects=match[1].split(' | ',1)[0].split();libs=re.search(r'^  LINK_LIBRARIES = (.*)$',match[2],re.M)[1].split()
    mainobj=next(x for x in objects if x.replace('\\','/').endswith('/main.c.obj'));copy=scratch/'main.c.obj';shutil.copy2(build/mainobj,copy)
    run([Path(flags[0]).parent/'objcopy.exe','--redefine-sym','main=eb_platform_main',copy],'rename.log',build)
    exe=scratch/'title-driver.exe';run([flags[0],'-O3','-DNDEBUG',obj,*[copy if x==mainobj else build/x for x in objects],'-o',exe,*libs],'link.log',build)
    shutil.copy2(build/'SDL2.dll' if (build/'SDL2.dll').exists() else source.parent/'tools/SDL2-2.32.10/x86_64-w64-mingw32/bin/SDL2.dll',scratch/'SDL2.dll')
    names=re.findall(r'^\s+(ASSET_\w+),',(source/'src/data/runtime_generated/asset_ids.h').read_text(),re.M)
    ids=[i for i,n in enumerate(names) if n.startswith('ASSET_US_INTRO_TITLE_SCREEN_')]+[names.index('ASSET_US_'+n+'_BIN_LZHAL') for n in ('E1AE7C','E1AE83','E1AEFD')];assert len(ids)==10
    donor=original.read_bytes();count=struct.unpack_from('<I',donor,8)[0];blob=44+8*count
    expected={i:donor[blob+o:blob+o+n] for i in ids for o,n in [struct.unpack_from('<II',donor,44+8*i)]}
    bad={}
    for name,where,data in [('truncated',0,b'EBPK'),('magic',0,b'NOPE'),('layout',12,b'\0'*32),('count',8,struct.pack('<I',count+1)),('version',4,struct.pack('<I',2)),('late-title-bounds',44+8*ids[6],struct.pack('<II',0xffffffff,423)),('empty-title',44+8*ids[0]+4,struct.pack('<I',0))]:
        altered=bytearray(donor) if name!='truncated' else bytearray();altered[where:where+len(data)]=data;path=scratch/(name+'.pak');path.write_bytes(altered);bad[name]=path
    bad['missing']=scratch/'missing.pak'
    rows=[]
    for name,path in {'valid':'-',**bad}.items():
        output=scratch/(name+'.bin');run([exe,redux,original,path,output],name+'.log')
        actual=output.read_bytes();cursor=0
        for i in ids:
            ident,length=struct.unpack_from('<II',actual,cursor);cursor+=8;assert ident==i and actual[cursor:cursor+length]==expected[i];cursor+=length
        assert cursor==len(actual);rows.append(name)
    frame_cases=[]
    for quick in (0,1):
        for label,pack,donor_path in [('original',original,'-'),('redux-original-title',redux,original),('redux-default',redux,'-')]:
            session=scratch/(label+'-'+str(quick));session.mkdir(exist_ok=True)
            run([exe,pack,donor_path,session,quick,scratch,label+'-'+str(quick)],label+'-'+str(quick)+'.log')
        for frame in (0,30,60,150,300,500,600):
            baseline=(scratch/f'original-{quick}-{frame}.bin').read_bytes();selected=(scratch/f'redux-original-title-{quick}-{frame}.bin').read_bytes()
            assert baseline==selected,(quick,frame,'title render differs from Original')
        assert (scratch/f'original-{quick}-500.bin').read_bytes()!=(scratch/f'redux-default-{quick}-500.bin').read_bytes()
        frame_cases.append({'quick':quick,'matchingFrames':[0,30,60,150,300,500,600],'defaultReduxDistinct':True})
    captures=[]
    for choice in ('redux','original'):
        session=scratch/('capture-'+choice);session.mkdir(exist_ok=True);config=session/'fixture.ini';config.write_text('companion=1\nfullscreen=0\nwidth=1920\nheight=1080\n')
        for quick in (0,1):
            replay=session/'confirm.replay';replay.write_text('0 0000\n650 1000\n653 0000\n',encoding='ascii')
            game_log=session/f'game-{quick}.log'
            cmd=[build/'earthbound.exe','--assets',redux,'--session-dir',session,'--config',config,'--allow-redux-development','--redux-title-fixture',quick,'--windowed','--frames',1000,'--dump-frame',500,'--fast-forward','--input-script',replay,'--log-file',game_log]
            if choice=='original':cmd+=['--original-title-assets',original]
            run(cmd,f'capture-{choice}-{quick}.log')
            with Image.open(session/'screenshot.bmp') as im:im.convert('RGB').save(session/f'title-{quick}.png')
            completion=list(cmd);completion[completion.index('--windowed')]='--headless'
            pos=completion.index('--dump-frame');del completion[pos:pos+2]
            completion[completion.index('--log-file')+1]=session/f'completion-{quick}.log'
            run(completion,f'completion-{choice}-{quick}.log');log=(session/f'completion-{quick}.log').read_text();assert f'Redux title fixture {quick} completed' in log
            captures.append({'choice':choice,'quick':quick,'completionPassed':True})
    report={'version':'0.5.0-redux-dev.25','passed':True,'nativeExeSha256':sha(build/'earthbound.exe'),'driverSourceSha256':sha(driver),'originalPackSha256':sha(original),'reduxPackSha256':sha(redux),'titleAssets':len(ids),'unchangedOtherAssets':count-10,'transactionalDonorCases':rows,'productionFrameComparisons':frame_cases,'productionCapturesAndCompletion':captures,'saveFormat':16,'fullPlaythroughVerified':False}
    (scratch/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
