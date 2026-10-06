# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual party-target name menu parents on immutable complete native archives.

Initial party/names/items are prepared before OPEN_MENU; all target navigation,
results and effects use production children and platform input. Added driver
code only reads rendered menu labels/VRAM and requests production cold captures.
"""
import argparse, copy, hashlib, json, os, subprocess
from pathlib import Path
from types import SimpleNamespace
import goods_equipment_qa_dev25 as gear
import overworld_use_cases_dev24 as use_cases
import goods_equipment_cases_dev25 as gear_cases
import redux_naming_qa as naming
import status_service_qa_dev23 as service
import status_service_cases_dev23 as service_cases
from build_maternalbound_pack import read_pack

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL_HELPER_DRIVER=gear.base.helper.DRIVER
C_NAMES=r'''
#include "snes/ppu.h"
static void names_fixture(const char*session){
 char path[4096];snprintf(path,sizeof(path),"%s/names-input.txt",session);FILE*f=fopen(path,"r");if(!f)exit(60);
 for(unsigned c=0;c<4;c++){unsigned n,g;uint8_t name[7]={0};if(fscanf(f,"%u",&n)!=1||n>(unsigned)maternalbound_name_capacity())exit(61);for(unsigned j=0;j<n;j++){if(fscanf(f,"%u",&g)!=1||g>255)exit(62);name[j]=g;}maternalbound_set_character_name(c,name,n);}fclose(f);
}
static void name_snap(const char*stage){
 for(unsigned index=0;index<MAX_WINDOWS;index++){
  WindowInfo*w=&win.windows[index];if(!w->active||!w->menu_count||!((w->id>=41&&w->id<=43)||w->id==WINDOW_SINGLE_CHARACTER_SELECT))continue;
  printf("QA_NAME_MENU {\"stage\":\"%s\",\"window\":%u,\"font\":%u,\"padding\":%u,\"current\":%u,\"selected\":%u,\"rows\":[",stage,w->id,w->font,character_padding,w->current_option,w->selected_option);
  unsigned width=w->width-2;
  for(unsigned i=0;i<w->menu_count;i++){
   MenuItem*t=&w->menu_items[i];unsigned tx=t->text_x+1,ty=t->text_y*2;
   printf("%s{\"id\":%u,\"x\":%u,\"y\":%u,\"label\":[",i?",":"",t->userdata,t->text_x,t->text_y);
   unsigned length=0;while(length<sizeof(t->label)&&t->label[length]){printf("%s%u",length?",":"",(uint8_t)t->label[length]);length++;}
   printf("],\"columns\":[");
   unsigned end=width; if(i+1<w->menu_count&&w->menu_items[i+1].text_y==t->text_y)end=w->menu_items[i+1].text_x;
   for(unsigned x=tx;x<end;x++){printf("%s\"",x==tx?"":",");for(unsigned y=0;y<2;y++){unsigned tile=w->content_tilemap[(ty+y)*width+x]&0x3ff;for(unsigned b=0;b<16;b++)printf("%02x",ppu.vram[0xc000+tile*16+b]);}printf("\"");}printf("]}");
  }printf("]}\n");fflush(stdout);
 }
}
static unsigned name_seen=0,previous_name_signature=~0u,resume_char_depth;
static void name_resume_buttons(void){
 if(!plan_pos)return;unsigned top=g_mode_stack.depth-1,mode=g_mode_stack.mode[top],pick=plan[plan_pos-1];ModeState*st=&g_mode_stack.state[top];
 if(mode==GAME_MODE_SELECTION_MENU&&st->selection_menu.phase==SM_MAIN){WindowInfo*w=get_window(win.current_focus_window);if(pick>=1000&&pick!=999){unsigned wanted=pick-1000;pick=998;if(w)for(unsigned i=0;i<w->menu_count;i++)if(w->menu_items[i].userdata==wanted){pick=i;break;}if(pick==998)exit(63);}replay_menu(w,pick,w?w->current_option:0);}
 else if(mode==GAME_MODE_CHAR_SELECT&&st->char_select.phase==CSP_INPUT){resume_char_depth=g_mode_stack.depth;unsigned from=st->char_select.current_index;replay(from<=pick?PAD_RIGHT:PAD_LEFT,pick==999?0:from<=pick?pick-from:from-pick,pick==999);}
}

static void name_observe(unsigned mode,ModeState*st){
 if(mode==GAME_MODE_SELECTION_MENU&&st->selection_menu.phase==SM_MAIN&&st->selection_menu.primed){WindowInfo*w=get_window(win.current_focus_window);if(w&&((w->id>=41&&w->id<=43)||w->id==WINDOW_SINGLE_CHARACTER_SELECT)){unsigned signature=w->id*256+w->current_option;if(signature!=previous_name_signature){previous_name_signature=signature;name_seen++;name_snap("actual-menu-input");}}}
 if(mode==GAME_MODE_CHAR_SELECT&&st->char_select.phase==CSP_INPUT&&pause_phase()==PM_GIVE_CHAR_RESULT&&!name_seen){
  printf("QA_GIVE_NAMES {\"phase\":%u,\"names\":[",st->char_select.phase);for(unsigned c=0;c<4;c++){printf("%s[",c?",":"");const uint8_t*n=maternalbound_character_name(c);for(unsigned j=0;j<(unsigned)maternalbound_name_capacity()&&n[j];j++)printf("%s%u",j?",":"",n[j]);printf("]");}printf("]}\n");name_seen=1;
 }
}
'''

def driver_source(original,services=False):
 gear.base.helper.DRIVER=ORIGINAL_HELPER_DRIVER
 s=service.driver_source(original) if services else gear.driver_source(original)
 if services:s=gear.replace_once(s,'static void snap(const char*stage){',gear.C_GEAR+'\nstatic void snap(const char*stage){')
 s=gear.replace_once(s,'static void snap(const char*stage){',C_NAMES+'\nstatic void snap(const char*stage){\n name_snap(stage);')
 s=gear.replace_once(s,'update_party();initialize_overworld_state();','names_fixture(argv[2]);update_party();initialize_overworld_state();')
 needle='if(capture_kind && ((capture_kind==5' if services else 'if(capture_kind && ((capture_kind==12'
 s=gear.replace_once(s,needle,'name_observe(mode,st);\n  if(capture_kind && ((capture_kind==20&&mode==GAME_MODE_SELECTION_MENU&&st->selection_menu.phase==SM_MAIN&&st->selection_menu.primed&&win.current_focus_window>=41&&win.current_focus_window<=43)||(capture_kind==21&&mode==GAME_MODE_CHAR_SELECT&&st->char_select.phase==CSP_INPUT&&pause_phase()==PM_GIVE_CHAR_RESULT)||(capture_kind=='+('5'if services else'12'))
 s=gear.replace_once(s,'snap("cold-loaded");}', 'snap("cold-loaded");name_resume_buttons();}')
 s=gear.replace_once(s,'unsigned number_depth=0,char_depth=0;', 'unsigned number_depth=0,char_depth=resume_char_depth;')
 # On cold resume, don't prepare buttons until the saved target menu is ready;
 # the original driver resumes the serialized script input at its preserved path.
 return s

def fixture_inputs(folder,case,names):
 flags={str(i):0 for i in range(451,465)};flags.update({'73':0,'770':0,'181':0,'645':0,'754':0,'779':0});flags.update(case.get('initialFlags',{}))
 inv=case.get('initialInventory',[[0]*14 for _ in range(4)])
 values=[x for bag in inv for x in bag]+[0]*36+[0]*6+[len(flags)]+[int(x)for pair in flags.items()for x in pair]+[0,0]
 (folder/'transaction-input.txt').write_text(' '.join(map(str,values)),encoding='ascii')
 values=[]
 for pc in case['initialParty']:values.extend([pc.get('level',1),pc['hp'],pc['pp'],pc.get('maxHP',100),pc.get('maxPP',50),*pc['status']])
 (folder/'effect-input.txt').write_text(' '.join(map(str,values)),encoding='ascii')
 (folder/'gear-input.txt').write_text(' '.join(str(x)for pc in case.get('initialEquipment',[[0]*4 for _ in range(4)])for x in pc),encoding='ascii')
 numbers=case.get('numbers',[]);service_values=[case.get('bank',0),len(numbers),case.get('captureNumberIndex',0),*numbers]
 for pc in case['initialParty']:service_values.extend([pc['hp'],pc['pp'],*pc['status']])
 (folder/'service-input.txt').write_text(' '.join(map(str,service_values)),encoding='ascii')
 (folder/'names-input.txt').write_text('\n'.join(' '.join(map(str,[len(n),*n]))for n in names)+'\n',encoding='ascii')

def names_for(profile,kind):
 if profile=='original' or kind=='ascii':return [[ord(c)+0x30 for c in s]for s in ('Ness','Paula','Jeff','Poo')]
 if kind=='mixed':return [[0x79,0xb0,0xc0,0x60,0xb8,0xb9],[0x7a,0xb1,0xc1,0x61,0xb9,0xb8],[0xb7,0xc7,0xb8,0xb9,0xac,0xaf],[0xae,0x57,0x53,0x5f,0x5d,0x6f]]
 return [[0xb0,0xb1,0xb2,0xb3,0xb4,0xb5],[0xc0,0xc1,0xc2,0xc3,0xc4,0xc5],[0xb7,0xc7,0xb0,0xc0,0xb5,0xc5],[0x87,0x87,0x71,0x78,0x78,0x95]]

PUNCT={ord('&'):0x52,ord('{'):0x53,ord('}'):0x56,ord('~'):0x8b,ord('^'):0x8c,ord('['):0x8d,ord(']'):0x8e,ord('#'):0x8f,ord('_'):0x90}
def glyph(b):return b if b>=128 else PUNCT.get(b,b+0x30)

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in ('source','builds','runtime','original-assets','redux-assets','scratch','output'):ap.add_argument('--'+n,type=Path,required=True)
 ap.add_argument('--pilot',action='store_true');ap.add_argument('--services',action='store_true');a=ap.parse_args()
 for n,v in vars(a).items():
  if isinstance(v,Path):setattr(a,n,v.resolve())
 if a.scratch.exists()or a.output.exists():raise ValueError('Fresh private scratch/report required')
 a.scratch.mkdir(parents=True);reports=[]
 for mode in (('player',)if a.pilot else('player','observer')):
  for profile,pack in [('original',a.original_assets),('redux',a.redux_assets)]:
   if a.pilot and profile=='original':continue
   _,_,assets=read_pack(pack,a.source/'src/data/runtime_generated/asset_ids.h')
   selected=[c for c in use_cases.generate(ROOT,pack,profile=='original',True)if c['id']in('refreshing-herb-poison-cold-target','psi-lifeup-alpha-clamp-full-parent','psi-healing-alpha-cold-action','psi-healing-target-cancel')]
   selected+= [c for c in gear_cases.generate(ROOT,pack,profile=='original',False)if c['id']=='give-target-cancel']
   if a.services:
    selected=[c for c in service_cases.generate(ROOT,profile=='original',False,native_source=a.source) if c['id'] in ('doctor-onett-illness5-pc2','nurse-onett-revive-pc1','healer-onett-treatment0-pc1')]
    if not selected:raise ValueError('Source service fixtures missing')
   link=a.scratch/(mode+'-'+profile+'-link');link.mkdir();gear.base.helper.DRIVER=driver_source(profile=='original',a.services)
   exe,linkproof=gear.base.helper.private_build(SimpleNamespace(build=a.builds/mode,scratch=link,native_source=a.source,runtime=a.runtime))
   for kind in (('mixed',)if a.pilot else('ascii','mixed','accent')if profile=='redux'else('ascii',)):
    names=names_for(profile,kind)
    for originalcase in selected:
     if a.pilot and not a.services and originalcase['id']!='psi-lifeup-alpha-clamp-full-parent':continue
     for cold in (False,True):
      case=copy.deepcopy(originalcase);case['checkpoint']=21 if case['id']=='give-target-cancel' else 20 if cold else 0
      if not cold:case['checkpoint']=0
      folder=a.scratch/(mode+'-'+profile+'-'+kind+'-'+case['id']+('-cold'if cold else'-warm'));folder.mkdir();fixture_inputs(folder,case,names)
      cfg=folder/'case.txt';vals=[case['entry'] if a.services else 0,case.get('money',1000),case.get('party',4),14,14,case.get('seed',1234567),0,0,0,3,len(case['plan']),case['checkpoint'],*case['plan']];cfg.write_text(' '.join(map(str,vals)),encoding='ascii')
      stages=[];events=[]
      for stage in (('capture','resume')if cold else('warm',)):
       p=subprocess.run([str(exe),str(pack),str(folder),str(cfg),stage],cwd=folder,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=180)
       (folder/(stage+'.log')).write_bytes(p.stdout+p.stderr);stages.append(dict(stage=stage,exit=p.returncode,stdoutSha256=hashlib.sha256(p.stdout).hexdigest(),stderrSha256=hashlib.sha256(p.stderr).hexdigest()))
       for line in p.stdout.decode(errors='replace').splitlines():
        if line.startswith('QA_'):
         t,v=line.split(' ',1);events.append(dict(type=t,actual=json.loads(v)))
       if p.returncode:break
      observations=[]
      for e in events:
       if e['type']!='QA_NAME_MENU':continue
       menu=e['actual']
       for row in menu['rows']:
        expected=names[row['id']-1];tiles=naming.raster_tiles(expected,assets['US/fonts/main.bin'],assets['US/fonts/main.gfx'],menu['padding']);actual=[bytes.fromhex(c)for c in row['columns'][:len(tiles)]]
        observations.append(dict(stage=menu['stage'],window=menu['window'],id=row['id'],rawLabel=row['label'],expectedGlyphs=expected,actualGlyphs=[glyph(b)for b in row['label']],sourceGlyphsMatch=[glyph(b)for b in row['label']]==expected,sourceFontColumnsMatch=actual==tiles,actualColumnsSha256=hashlib.sha256(b''.join(actual)).hexdigest(),expectedColumnsSha256=hashlib.sha256(b''.join(tiles)).hexdigest(),diffBytes=sum(sum(x!=y for x,y in zip(v,t))for v,t in zip(actual,tiles)),sourceNameWidth=sum(assets['US/fonts/main.bin'][g-0x50]+1 for g in expected),textX=row['x'],currentOption=menu['current']))
      give=[e['actual']for e in events if e['type']=='QA_GIVE_NAMES'];end=[e['actual']for e in events if e['type']=='QA_END']
      reached=bool(give)if case['id']=='give-target-cancel'else bool(observations)
      r=dict(build=mode,profile=profile,nameCase=kind,parent=case['id'],cold=cold,preparedNames=names,fixture=case,stages=stages,link=linkproof,assetsSha256=gear.base.helper.digest(pack),observations=observations,giveControl=give,actualParentEnds=end,serializedCaptureObserved=any(e['type']=='QA_SNAP'and e['actual']['stage']=='captured'for e in events),freshColdObserved=any(e['type']=='QA_SNAP'and e['actual']['stage']=='cold-loaded'for e in events),nativeControlPassed=all(x['exit']==0 for x in stages)and reached and end[-1]['depth']==1 and end[-1]['planUsed']==len(case['plan']),sourceLegalNames=all(len(n)<=(5 if profile=='original' else 6) and (profile=='original' or sum(assets['US/fonts/main.bin'][g-0x50]+1 for g in n)<=40) for n in names),sourceGlyphsPassed=all(o['sourceGlyphsMatch']and o['sourceFontColumnsMatch']for o in observations),sourceExpectedPassed=reached and all(o['sourceGlyphsMatch']and o['sourceFontColumnsMatch']for o in observations))
      if give:r['giveRawNamesMatch']=all(g['names']==names for g in give);r['sourceExpectedPassed'] &= r['giveRawNamesMatch']
      semantic=[]
      if a.services:
       actual=[e['actual']for e in events if e['type']=='QA_SERVICE'and e['actual']['stage']=='after-entry'];want=case['expectedService']
       if actual:
        semantic += [actual[-1][k]==want[k] for k in ('wallet','bank')]
        semantic += [actual[-1]['party'][i][k]==want['party'][i][k] for i in range(4) for k in ('hpTarget','ppTarget','status')]
      elif 'expectedEffect' in case:
       actual=[e['actual']for e in events if e['type']=='QA_EFFECT'and e['actual']['stage']=='after-entry']
       if actual:semantic += [actual[-1]['party'][i][k]==case['expectedEffect'][i][k] for i in range(4) for k in ('hpTarget','ppTarget','status')]
      r['selectedParentSemanticControlsPassed']=bool(semantic)and all(semantic)
      r['nativeControlPassed'] &= r['selectedParentSemanticControlsPassed']
      reports.append(r);print(json.dumps(dict(case=folder.name,native=r['nativeControlPassed'],source=r['sourceExpectedPassed'],observations=len(observations),exits=stages)),flush=True)
 report=dict(schemaVersion=1,toolVersion='dev19-party-name-parent-source-layout-v2',toolSha256=gear.base.helper.digest(Path(__file__)),results=reports,nativeControlsPassed=all(r['nativeControlPassed']for r in reports),sourceExpectedPassed=all(r['sourceExpectedPassed']for r in reports),rootOrOwnerInputsModified=False,fullConversionVerified=False,fullPlaythroughVerified=False,limits=['Prepared valid legal party names and source item/status prerequisites before OPEN_MENU. Real production Give/Goods/PSI parents, target children, platform D-pad/A/B replay and fresh-process production serialization; no physical-controller/natural story claim.','Independent packed-font compositor checks raw source-name glyphs and actual target-menu VRAM columns. Not an original CPU complete UI rasterizer. Give is a different HPPP selector; its raw names and actual child reachability are recorded as a control, not an ordinary-name-row equivalence.','Original uses its five-letter contract; mixed/accent naming fixtures are Redux only. Generic ASCII labels, tiny titles and file-slot labels are outside production-change scope.'])
 a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(report=str(a.output),native=report['nativeControlsPassed'],source=report['sourceExpectedPassed'])))
if __name__=='__main__':main()

