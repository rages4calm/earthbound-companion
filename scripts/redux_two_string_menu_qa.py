# SPDX-License-Identifier: GPL-3.0-or-later
"""Audit the installed two-string menu adapter using an immutable native build.

Local asset packs are read only. By default the private driver links unchanged
production objects. The explicit private-corrected-objects option compiles only
the two owned menu files into a copied private archive. Its narrow reader wrapper
supplies source-macro operand fixtures; it
does not substitute the dispatcher, font renderer, windows or highlight code.
The extended macros have no caller in the pinned source graph, so their API
fixtures are not represented as ordinary gameplay or full story coverage.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from check_jev_observer_parity import local_scratch
from maternalbound_dialogue import without_comments


DRIVER = r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "game/game_state.h"
#include "game/maternalbound.h"
#include "game/window.h"
#include "game/text.h"
#include "game/display_text.h"
#include "game/display_text_internal.h"
#include "game/overworld.h"
#include "core/memory.h"
#include "include/pad.h"
#include "data/text_refs.h"
#include "snes/ppu.h"
#include "include/constants.h"
extern int eb_platform_main(int,char**);
extern void cc_19_dispatch(ScriptReader*);
extern uint16_t vwf_x,vwf_tile,vwf_pixels_rendered;
static uint8_t operands[256];
static unsigned supplied;
static unsigned force_input,sfx_capture,sfx_count,sfx_last;
static uint16_t input_mask;
extern uint16_t __real_platform_input_get_pad_new(void);
uint16_t __wrap_platform_input_get_pad_new(void){return force_input?input_mask:__real_platform_input_get_pad_new();}
extern void __real_play_sfx(uint16_t);
void __wrap_play_sfx(uint16_t id){if(sfx_capture){sfx_count++;sfx_last=id;}__real_play_sfx(id);}
extern uint8_t __real_script_read_byte(ScriptReader*);
extern uint32_t __real_script_read_dword(ScriptReader*);
uint8_t __wrap_script_read_byte(ScriptReader*r){
 if(!supplied)return __real_script_read_byte(r);
 if(r->ptr_off>=r->end_off){fprintf(stderr,"private input exhausted\n");exit(10);}
 return operands[r->ptr_off++];
}
uint32_t __wrap_script_read_dword(ScriptReader*r){
 if(!supplied)return __real_script_read_dword(r);
 uint32_t v=0;for(unsigned i=0;i<4;i++)v|=(uint32_t)__wrap_script_read_byte(r)<<(8*i);return v;
}
static void setup(unsigned font){
 window_system_init();init_used_bg2_tile_map();text_setup_bg3();text_load_window_gfx();
 vwf_init();clear_vwf_indent_new_line();
 memset(&dt,0,sizeof(dt));dt.instant_printing=1;dt.enable_word_wrap=1;
 create_window(WINDOW_FILE_SELECT_CONFIRM_MSG);set_window_focus(WINDOW_FILE_SELECT_CONFIRM_MSG);
 WindowInfo*w=get_window(WINDOW_FILE_SELECT_CONFIRM_MSG);if(!w)exit(11);
 w->font=font;w->menu_page_number=1;character_padding=1;
}
static unsigned menu(unsigned term,const char*left,const char*right){
 unsigned n=0;operands[n++]=2;
 for(unsigned i=0;left[i];i++)operands[n++]=ascii_to_eb_char(left[i]);
 operands[n++]=term;
 if(term>=3){for(unsigned i=0;right[i];i++)operands[n++]=ascii_to_eb_char(right[i]);operands[n++]=0;}
 if(term==1||term==3){uint32_t callback=0x00300080;for(unsigned i=0;i<4;i++)operands[n++]=(uint8_t)(callback>>(8*i));}
 ScriptReader r={TEXT_SRC_DIALOGUE,0,n,-1};supplied=1;cc_19_dispatch(&r);supplied=0;
 if(r.ptr_off!=n)exit(12);return r.ptr_off;
}
static unsigned width(const char*s){
 uint8_t eb[128]={0};for(unsigned i=0;s[i];i++)eb[i]=ascii_to_eb_char(s[i]);return get_string_pixel_width(eb,-1);
}
static void pixels(WindowInfo*w,uint8_t*out){
 unsigned cw=w->width-2,ch=w->height-2;
 for(unsigned y=0;y<ch*8;y++)for(unsigned x=0;x<cw*8;x++){
  unsigned tile=w->content_tilemap[(y/8)*cw+x/8]&1023;
  unsigned off=VRAM_TEXT_LAYER_TILES*2+tile*16+(y%8)*2;
  if(off+1>=sizeof(ppu.vram))exit(13);
  unsigned bit=7-(x%8);out[y*cw*8+x]=(tile&&((ppu.vram[off]>>bit)&1)&&!((ppu.vram[off+1]>>bit)&1))?1:0;
 }
}
static void bbox(const uint8_t*map,unsigned cw,unsigned ch,int*out){
 out[0]=out[1]=65535;out[2]=out[3]=-1;
 for(unsigned y=0;y<ch;y++)for(unsigned x=0;x<cw;x++)if(map[y*cw+x]){
  if((int)x<out[0])out[0]=x;if((int)y<out[1])out[1]=y;
  if((int)x>out[2])out[2]=x;if((int)y>out[3])out[3]=y;
 }
}
int main(int argc,char**argv){
 if(argc!=5)return 2;unsigned redux=atoi(argv[3]);char save[4096];snprintf(save,sizeof(save),"%s/private.srm",argv[2]);
 char*boot[]={"two-string-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
 if(eb_platform_main(12,boot)||maternalbound_enabled()!=(redux!=0))return 3;
 const char*lefts[]={"Choice","iiii","MMMM","It is","Yes","No"};
 const char*rights[]={"42","7","123456"};
 unsigned index=0;
 for(unsigned font=0;font<5;font++)for(unsigned l=0;l<6;l++)for(unsigned r=0;r<3;r++){
  unsigned pos;uint8_t actual[65536],expected[65536],left[65536],delta[65536];
  setup(font);pos=menu(2,lefts[l],"");WindowInfo*w=get_window(WINDOW_FILE_SELECT_CONFIRM_MSG);
  unsigned cw=(w->width-2)*8,ch=(w->height-2)*8,size=cw*ch;
  if(size>sizeof(actual))return 14;
  unsigned sw=width(rights[r]),edge=cw-1;if(sw>edge)return 15;
  print_menu_items();pixels(w,left);
  clear_vwf_indent_new_line();set_text_pixel_position(0,edge-sw);print_string(rights[r]);pixels(w,expected);
  setup(font);pos=menu(4,lefts[l],rights[r]);w=get_window(WINDOW_FILE_SELECT_CONFIRM_MSG);
  unsigned type=w->menu_items[0].type,page=w->menu_items[0].page,sound=w->menu_items[0].sound_effect;
  print_menu_items();pixels(w,actual);
  unsigned differing=0,lostleft=0;for(unsigned i=0;i<size;i++){differing+=actual[i]!=expected[i];lostleft+=left[i]&&!actual[i];delta[i]=actual[i]&&!left[i];}
  int ab[4],eb[4];bbox(delta,cw,ch,ab);for(unsigned i=0;i<size;i++)delta[i]=expected[i]&&!left[i];bbox(delta,cw,ch,eb);
  printf("RENDER [%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,[%d,%d,%d,%d],[%d,%d,%d,%d],%u,%u,%u,%u]\n",++index,font,l,r,cw,ch,sw,edge,differing,lostleft,ab[0],ab[1],ab[2],ab[3],eb[0],eb[1],eb[2],eb[3],type,page,sound,pos);
  char path[4096];snprintf(path,sizeof(path),"%s/render-%u.raw",argv[2],index);FILE*f=fopen(path,"wb");if(!f)return 16;fwrite(actual,1,size,f);fwrite(expected,1,size,f);fclose(f);
 }
 for(unsigned term=1;term<=4;term++){
  if(!redux&&term>=3)continue;setup(0);unsigned pos=menu(term,"Choice",term>=3?"42":"");WindowInfo*w=get_window(WINDOW_FILE_SELECT_CONFIRM_MSG);MenuItem*i=&w->menu_items[0];
  printf("OPERANDS [%u,%u,%u,%u,%u,%u,%u,%u,%u]\n",term,pos,w->menu_count,i->type,i->page,i->sound_effect,i->userdata,i->script,(unsigned)strlen(i->right_label));
 }
 for(unsigned len=29;len<=32;len++){
  setup(0);char right[64];memset(right,'1',len);right[len]=0;menu(4,"Choice",right);WindowInfo*w=get_window(WINDOW_FILE_SELECT_CONFIRM_MSG);
  printf("BOUNDARY [%u,%u]\n",len,(unsigned)strlen(w->menu_items[0].right_label));
 }
 const char*widthtexts[]={"42","7","123456","Choice","iiii","MMMM","It is","Yes","No"};
 const int caps[]={1,2,30,65535};
 for(unsigned font=0;font<5;font++)for(unsigned padding=0;padding<3;padding++)for(unsigned t=0;t<9;t++)for(unsigned cap=0;cap<4;cap++){
  setup(font);character_padding=padding;uint8_t eb[128]={0};for(unsigned i=0;widthtexts[t][i];i++)eb[i]=ascii_to_eb_char(widthtexts[t][i]);
  printf("WIDTH [%u,%u,%u,%u,%u]\n",font,padding,t,caps[cap],get_string_pixel_width(eb,caps[cap]));
 }
 /* Execute the packed source common Yes/No builder, then the actual native
  * confirmation input phase. The optional source-default state
  * assignment is a private diagnostic control, never a production override. */
 for(unsigned control=0;control<2;control++)for(unsigned choice=0;choice<2;choice++){
  setup(0);ScriptReader real={TEXT_SRC_DIALOGUE,0,0,-1};resolve_text_jump(&real,redux?0xC7DD4F:MSG_SYS_YESNO_PROMPT);
  if(script_read_byte(&real)!=0x19)return 27;cc_19_dispatch(&real);
  if(script_read_byte(&real)!=0x19)return 28;cc_19_dispatch(&real);
  if(script_read_byte(&real)!=0x1c)return 29;ModeState child={0};GameMode childmode=0;if(cc_1c_dispatch(&real,&child,&childmode))return 30;
  if(script_read_byte(&real)!=2)return 31;WindowInfo*w=get_window(WINDOW_FILE_SELECT_CONFIRM_MSG);
  if(w->menu_count!=2||strcmp(w->menu_items[0].label,"Yes")||strcmp(w->menu_items[1].label,"No"))return 20;
  unsigned initialtype=w->menu_items[choice].type,initialpage=w->menu_items[choice].page,initialsound=w->menu_items[choice].sound_effect;
  if(control)for(unsigned i=0;i<2;i++){w->menu_items[i].type=1;w->menu_items[i].page=1;w->menu_items[i].sound_effect=1;}
  /* Enter the completed, primed selection input phase with its actual
   * packed-menu prerequisites. Full overworld/menu frame setup is excluded. */
  ModeState ms={0};ms.selection_menu.allow_cancel=1;ms.selection_menu.phase=SM_MAIN;ms.selection_menu.primed=1;w->current_option=choice;force_input=1;
  input_mask=PAD_A;sfx_count=0;sfx_last=0;sfx_capture=1;StepResult step=mode_step_selection_menu(&ms);sfx_capture=0;force_input=0;
  if(step.kind!=STEP_POP||step.pop_result!=(int)(choice+1))return 26;
  printf("PACKED_SELECTION [%u,%u,%u,%u,%u,%u,%u,%u,%u]\n",control,choice,initialtype,initialpage,initialsound,step.kind,step.pop_result,sfx_count,sfx_last);
 }
 for(unsigned font=0;font<5;font++)for(unsigned l=0;l<6;l++)for(unsigned enabled=0;enabled<2;enabled++){
  setup(font);menu(2,lefts[l],"");WindowInfo*w=get_window(WINDOW_FILE_SELECT_CONFIRM_MSG);unsigned cw=w->width-2;
  for(unsigned i=0;i<w->content_tilemap_size;i++)w->content_tilemap[i]=enabled?65:0x1841;
  highlight_menu_item(w,0,6,enabled!=0);
  printf("HIGHLIGHT [%u,%u,%u,[",font,l,enabled);for(unsigned i=0;i<cw*2;i++){if(i)printf(",");printf("%u",w->content_tilemap[i]);}puts("]]");
 }
 for(unsigned font=0;font<5;font++)for(unsigned indent=0;indent<2;indent++)for(unsigned page=0;page<3;page++){
  uint8_t actual[65536],expected[65536],left[65536];setup(font);menu(2,"Choice","");menu(2,"It is","");WindowInfo*w=get_window(WINDOW_FILE_SELECT_CONFIRM_MSG);
  for(unsigned i=0;i<2;i++){w->menu_items[i].text_x=0;w->menu_items[i].text_y=i;w->menu_items[i].page=page?i+1:1;}w->menu_page_number=page?page:1;
  vwf_indent_new_line=indent;print_menu_items();unsigned expectedindent=vwf_indent_new_line;unsigned cw=(w->width-2)*8,ch=(w->height-2)*8,size=cw*ch;pixels(w,left);
  clear_vwf_indent_new_line();for(unsigned i=0;i<2;i++){if(page&&page!=i+1)continue;const char*right=i?"7":"42";set_text_pixel_position(i,cw-1-width(right));print_string(right);}vwf_indent_new_line=expectedindent;pixels(w,expected);
  setup(font);menu(4,"Choice","42");menu(4,"It is","7");w=get_window(WINDOW_FILE_SELECT_CONFIRM_MSG);for(unsigned i=0;i<2;i++){w->menu_items[i].text_x=0;w->menu_items[i].text_y=i;w->menu_items[i].page=page?i+1:1;}w->menu_page_number=page?page:1;
  vwf_indent_new_line=indent;print_menu_items();pixels(w,actual);unsigned diff=0,lost=0;for(unsigned i=0;i<size;i++){diff+=actual[i]!=expected[i];lost+=left[i]&&!actual[i];}
  printf("MULTI [%u,%u,%u,%u,%u,%u,%u]\n",font,indent,page,diff,lost,vwf_indent_new_line,expectedindent);
 }
 return 0;
}
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def private_driver(args, out):
    build = args.build.resolve()
    if sha(build / 'earthbound.exe') != sha(args.runtime / 'player.exe'):
        raise ValueError('Frozen build/runtime player identity mismatch')
    library = build / 'game_lib/libearthbound_game.a'
    library_sha = sha(library)
    commands = json.loads((build / 'compile_commands.json').read_text(encoding='utf-8'))
    entry = next(row for row in commands if row['file'].endswith('/port/unix/main.c'))
    if '"' in entry['command'] or "'" in entry['command']:
        raise ValueError('Review quoted frozen compiler flags')
    flags = entry['command'].split()
    compiler = Path(flags[0])
    source = out / 'two-string-driver.c'
    source.write_text(DRIVER, encoding='utf-8')
    obj = source.with_suffix('.c.obj')
    flags[flags.index('-c') + 1] = str(source)
    flags[flags.index('-o') + 1] = str(obj)

    def run(command, name):
        proc = subprocess.run(list(map(str, command)), cwd=build, capture_output=True, timeout=40)
        (out / name).write_bytes(proc.stdout + proc.stderr)
        if proc.returncode:
            raise ValueError(name + ': ' + proc.stderr.decode(errors='replace'))

    run(flags, 'compile-driver.log')
    ninja = (build / 'build.ninja').read_text(encoding='utf-8')
    match = re.search(r'^build earthbound.exe: C_EXECUTABLE_LINKER__earthbound_Release (.*?)\n(.*?)(?=\n\n)', ninja, re.M | re.S)
    objects = match[1].split(' | ', 1)[0].split()
    libraries = re.search(r'^  LINK_LIBRARIES = (.*)$', match[2], re.M)[1].split()
    main = next(v for v in objects if v.replace('\\', '/').endswith('/main.c.obj'))
    copied = out / 'platform-main.c.obj'
    shutil.copy2(build / main, copied)
    run([compiler.parent / 'objcopy.exe', '--redefine-sym', 'main=eb_platform_main', copied], 'rename-main.log')
    objects = [str(copied) if v == main else str(build / v) for v in objects]
    overrides = []
    if args.private_corrected_objects:
        private_library = out / 'private-source-menu.a'
        shutil.copy2(library, private_library)
        for relative in ('src/game/window.c', 'src/game/display_text_cc.c'):
            entry = next(row for row in commands if row['file'].endswith('/' + relative))
            argv = entry['command'].split()
            actual = args.native_source / relative
            corrected = out / (actual.name + '.obj')
            argv[argv.index('-c') + 1] = str(actual)
            argv[argv.index('-o') + 1] = str(corrected)
            run(argv, actual.name + '-private-compile.log')
            run([compiler.parent / 'ar.exe', 'r', private_library, corrected], actual.name + '-private-archive.log')
            overrides.append({'source': relative, 'sourceSha256': sha(actual), 'privateObjectSha256': sha(corrected)})
        libraries = [str(private_library) if v.replace('\\', '/') == 'game_lib/libearthbound_game.a' else v for v in libraries]
    exe = out / 'two-string-driver.exe'
    run([compiler, '-O3', '-DNDEBUG', obj, *objects, '-o', exe,
         '-Wl,--wrap=script_read_byte', '-Wl,--wrap=script_read_dword',
         '-Wl,--wrap=platform_input_get_pad_new', '-Wl,--wrap=play_sfx',
         '-Wl,--major-image-version,0,--minor-image-version,0', *libraries], 'link-driver.log')
    shutil.copy2(args.runtime / 'SDL2.dll', out / 'SDL2.dll')
    if sha(library) != library_sha:
        raise ValueError('Frozen production archive changed')
    snapshot = build.parent.parent / build.parent.name.replace('-build', '-source')
    frozen_sources = {relative: sha(snapshot / relative) for relative in ('src/game/window.c', 'src/game/display_text_cc.c') if (snapshot / relative).exists()}
    return exe, {'driverSourceSha256': sha(source), 'privateExeSha256': sha(exe),
                 'unchangedProductionLibrarySha256': library_sha,
                 'wrappers': ['script_read_byte', 'script_read_dword', 'platform_input_get_pad_new', 'play_sfx'],
                 'productionObjectsRecompiledOrReplaced': bool(overrides), 'privateSourceObjectOverrides': overrides,
                 'frozenSourceSnapshotIdentities': frozen_sources,
                 'sourceInputsAreCurrentReviewContext': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('native-source', 'build', 'runtime', 'original-assets', 'redux-assets',
                 'redux-source', 'bridge', 'scratch', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--private-corrected-objects', action='store_true', help='Compile only the two owned menu C files into a private copied archive; never replace the frozen input library.')
    args = parser.parse_args()
    for name, path in vars(args).items():
        if isinstance(path, Path): setattr(args, name, path.resolve())
    args.scratch = local_scratch(args.scratch)
    if args.scratch.exists() or args.output.exists():
        raise ValueError('Fresh scratch/output required')
    graph = json.loads(args.bridge.read_text(encoding='utf-8'))
    if graph['source']['revision'] != '897d00833f4a08a0a92f106abf631629a6a6a041' or len(graph['sourceGraph']['files']) != 191:
        raise ValueError('Exact existing pinned source graph required')
    definitions = []; invocations = []
    for row in graph['sourceGraph']['files']:
        path = args.redux_source / row['path']
        if sha(path).upper() != row['sha256'].upper():
            raise ValueError('Pinned source changed: ' + row['path'])
        code = without_comments(path.read_text(encoding='utf-8-sig'))
        for match in re.finditer(r'\b(load_two_str(?:_callonhover)?)\s*\(', code):
            line_start = code.rfind('\n', 0, match.start()) + 1
            entry = {'path': row['path'], 'line': code.count('\n', 0, match.start()) + 1, 'name': match[1]}
            (definitions if re.search(r'\bcommand\s*$', code[line_start:match.start()]) else invocations).append(entry)
    if len(definitions) != 2:
        raise ValueError('Source macro definitions changed')
    args.scratch.mkdir(parents=True)
    production = args.scratch / 'production'
    production.mkdir()
    exe, link = private_driver(args, production)
    modes = []
    env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
    for mode, assets, redux in (('original', args.original_assets, 0), ('redux', args.redux_assets, 1)):
        scene = args.scratch / mode
        scene.mkdir()
        proc = subprocess.run([str(exe), str(assets), str(scene), str(redux), 'prepared'],
                              capture_output=True, env=env, timeout=40)
        log = scene / 'native.log'; log.write_bytes(proc.stdout + proc.stderr)
        if proc.returncode:
            raise ValueError(mode + ' driver failed: ' + proc.stderr.decode(errors='replace')[-2500:])
        def records(prefix):
            return [json.loads(line[len(prefix):]) for line in proc.stdout.decode().splitlines() if line.startswith(prefix)]
        rendered = records('RENDER ')
        if len(rendered) != 90 or [row[0] for row in rendered] != list(range(1, 91)):
            raise ValueError('Incomplete render corpus')
        if len(records('WIDTH ')) != 540 or len(records('HIGHLIGHT ')) != 60 or len(records('PACKED_SELECTION ')) != 4 or len(records('MULTI ')) != 30:
            raise ValueError('Incomplete width/highlight/packed-selection corpus')
        modes.append({'profile': mode, 'assetsSha256': sha(assets), 'renderCases': len(rendered),
                      'renderDifferences': sum(row[8] != 0 for row in rendered),
                      'leftLabelPixelLossCases': sum(row[9] != 0 for row in rendered),
                      'renderRecords': rendered, 'operandRecords': records('OPERANDS '),
                      'widthRecords': records('WIDTH '), 'packedSelectionRecords': records('PACKED_SELECTION '),
                      'highlightRecords': records('HIGHLIGHT '),
                      'multirowRecords': records('MULTI '),
                      'rightLabelBoundaryRecords': records('BOUNDARY '), 'nativeLogSha256': sha(log)})
    files = [args.runtime / 'player.exe', args.runtime / 'observer.exe', args.bridge,
             args.native_source / 'src/game/window.c', args.native_source / 'src/game/display_text_cc.c',
             args.native_source / 'src/game/display_text.c', args.native_source / 'src/game/text.c',
             args.redux_source / 'ccscript/essential/cc_load_two_str.ccs']
    report = {'format': 'redux-two-string-menu-behavior-v1', 'status': 'prepared-native-measurement',
              'toolSha256': sha(Path(__file__)), 'inputs': {str(p): sha(p) for p in files},
              'existingPinnedSourceFilesChecked': 191, 'extendedMacroDefinitions': definitions,
              'extendedMacroInvocations': invocations, 'link': link, 'profiles': modes,
              'productionSourceBuildPackOrOwnerSaveModified': False,
              'limits': ['Reader wrappers supply encoded operand fixtures for the extended API tests; packed common Yes/No choices use the unwrapped real reader and source banks.',
                         'Pixel references use the existing native SET_TEXT_PIXEL_POSITION path with source-defined right edge; an independent CPU oracle must qualify this measurement.',
                         'Source extended macros have no named invocation in the pinned graph; right-label API differences are not shown reachable in ordinary story.',
                         'Packed choices execute their real two CC19 instructions and CC1C07 layout, then actual SM_MAIN primed confirm input with prepared current-option prerequisites. Full parent story, setup frames, navigation, hover and cold continuation remain unproved.',
                         'platform_input_get_pad_new supplies only the private confirmation pad. play_sfx is forwarded to production audio and observed; the source-default state control sets type/page/sound only in private RAM.',
                         'Encoded callback addresses in synthetic API rows are consumed/stored, not executed. The failed exploratory uninitialized full-frame setup is excluded from passing coverage.',
                         'Synthetic right-label lengths29..32 characterize a dormant API boundary, not a shipped source caller.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(str(args.output));print([(m['profile'], m['renderDifferences'], m['leftLabelPixelLossCases']) for m in modes])


if __name__ == '__main__':
    main()
