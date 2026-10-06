# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual file-menu label rendering and fresh-process F6 controls.

Private phone prerequisites are written by native load/name/save APIs. The
complete immutable executables build the real slot menu and handle real input.
Expected pixels use packed source-font bytes, never the candidate label decoder.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from check_jev_observer_parity import latest, local_scratch
import redux_title_cold_qa_dev18 as qa
import file_select_cold_qa_dev18 as focused
import redux_title_producers_qa_dev18 as producers

ROOT = Path(__file__).resolve().parents[1]
DRIVER = r'''
#define SDL_MAIN_HANDLED
#include <stdio.h>
#include <stdlib.h>
#include "game/game_state.h"
#include "game/maternalbound.h"
extern int eb_platform_main(int,char**);
int main(int argc,char**argv){
 if(argc!=5)return 2;
 char*boot[]={"private-file-slot-phone","--assets",argv[1],"--session-dir",argv[2],"--save",argv[3],"--allow-redux-development","--headless","--frames","1","--inspect-shuffle"};
 if(eb_platform_main(12,boot)||!load_game(0))return 3;
 FILE*f=fopen(argv[4],"r");if(!f)return 4;
 for(unsigned slot=0;slot<SAVE_COUNT;slot++){
  unsigned length;if(fscanf(f,"%u",&length)!=1||length>(unsigned)maternalbound_name_capacity())return 5;
  uint8_t name[7]={0};for(unsigned i=0;i<length;i++){unsigned glyph;if(fscanf(f,"%u",&glyph)!=1||glyph>255)return 6;name[i]=(uint8_t)glyph;}
  if(length){maternalbound_set_character_name(0,name,length);if(!save_game(slot))return 7;printf("PHONE [%u,%u]\n",slot,length);}
 }
 fclose(f);return 0;
}
'''

def compile_layout(source, build, out):
    l = qa.layout(source, ROOT/'tools/mingw64/bin/gcc.exe', build, out)
    c = out/'file-slot-layout.c'; exe = out/'file-slot-layout.exe'
    c.write_text(r'''#include <stddef.h>
#include <stdio.h>
#include "game/window.h"
#define F(T,N) printf("\"" #T "." #N "\":%zu,",offsetof(T,N))
int main(void){printf("{");F(WindowInfo,font);F(WindowInfo,width);F(WindowInfo,height);F(WindowInfo,content_tilemap_offset);F(WindowSystemState,tilemap_pool);F(MenuItem,label);F(MenuItem,userdata);F(MenuItem,text_x);F(MenuItem,text_y);printf("\"MenuItem.size\":%zu}",sizeof(MenuItem));return 0;}''', encoding='utf-8')
    p = subprocess.run([str(ROOT/'tools/mingw64/bin/gcc.exe'),'-std=c2x','-I',str(source/'src'),'-I',str(build/'game_lib/generated'),str(c),'-o',str(exe)],capture_output=True,timeout=45)
    if p.returncode:raise ValueError(p.stderr.decode(errors='replace'))
    l.update(json.loads(subprocess.check_output([str(exe)],timeout=10)))
    return l

class Session(qa.Session):
    def read(self):
        result = super().read(); l=self.layout; w=self.blobs[8]; ppu=self.blobs[10]
        slots=[]
        for index in range(8):
            at=l['WindowSystemState.windows']+index*l['WindowInfo.size']
            if not w[at+l['WindowInfo.active']] or w[at+l['WindowInfo.id']]!=19:continue
            width=w[at+l['WindowInfo.width']]-2
            height=w[at+l['WindowInfo.height']]-2
            pool=struct.unpack_from('<H',w,at+l['WindowInfo.content_tilemap_offset'])[0]
            for slot in range(3):
                item=at+l['WindowInfo.menu_items']+slot*l['MenuItem.size']
                raw=bytes(w[item+l['MenuItem.label']:item+l['MenuItem.label']+26]).split(b'\0',1)[0]
                tx=w[item+l['MenuItem.text_x']]+1;ty=w[item+l['MenuItem.text_y']]*2
                tilemaps=[]; columns=[]
                for x in range(tx,width):
                    tiles=[struct.unpack_from('<H',w,l['WindowSystemState.tilemap_pool']+2*(pool+(ty+y)*width+x))[0] for y in (0,1)]
                    tilemaps.append(tiles)
                    columns.append(b''.join(bytes(ppu[l['PPUState.vram']+0xC000+(v&0x3FF)*16:l['PPUState.vram']+0xC000+(v&0x3FF)*16+16]) for v in tiles))
                slots.append(dict(slot=slot,raw=list(raw),userdata=struct.unpack_from('<H',w,item+l['MenuItem.userdata'])[0],font=w[at+l['WindowInfo.font']],textX=tx,textY=ty,interiorWidth=width,interiorHeight=height,columns=columns,tilemaps=tilemaps,currentOption=w[at+l['WindowInfo.current_option']],selectedOption=w[at+l['WindowInfo.selected_option']]))
        self.slot_rows=slots
        return result

def observe(session, names):
    out=[]
    for row,name in zip(session.slot_rows,names):
        if row['font']!=0:raise ValueError('Source slot font is not normal')
        expected=[0x61+row['slot'],0x6A,0x50]+list(name) if name else [ord(c)+0x30 for c in str(row['slot']+1)+': Start New Game']
        # Independent encoding check. EarthBound reorders these punctuation
        # glyphs; letters/digits and remaining source punctuation use +0x30.
        # Expected glyphs still come directly from the raw source name above.
        punctuation={ord('&'):0x52,ord('{'):0x53,ord('}'):0x56,
                     ord('~'):0x8B,ord('^'):0x8C,ord('['):0x8D,
                     ord(']'):0x8E,ord('#'):0x8F,ord('_'):0x90}
        actual_glyphs=[b if b>=128 else punctuation.get(b,b+0x30) for b in row['raw']]
        padding=session.blobs[31][0]; widths=session.qa_assets['US/fonts/main.bin']; graphics=session.qa_assets['US/fonts/main.gfx']
        bitmaps=qa.naming.raster_tiles(expected,widths,graphics,padding)
        actual=row['columns'][:len(bitmaps)];pixels=sum(widths[g-0x50]+padding for g in expected)
        out.append(dict(slot=row['slot'],rawLabel=row['raw'],actualGlyphs=actual_glyphs,expectedGlyphs=expected,sourceGlyphsMatch=actual_glyphs==expected,sourceFontColumnsMatch=actual==bitmaps,sourceFontDiffBytes=sum(sum(a!=b for a,b in zip(actual[i],bitmap)) for i,bitmap in enumerate(bitmaps)),actualVramSha256=hashlib.sha256(b''.join(actual)).hexdigest(),expectedVramSha256=hashlib.sha256(b''.join(bitmaps)).hexdigest(),pixels=pixels,columns=len(bitmaps),labelBytesBounded=len(row['raw'])<26,occupiedLabelBeforeLevelColumn=not name or row['textX']+len(bitmaps)<=9,userdata=row['userdata'],currentOption=row['currentOption'],selectedOption=row['selectedOption'],tilemaps=row['tilemaps'][:len(bitmaps)],remainingTilemaps=row['tilemaps'][len(bitmaps):]))
    if len(out)!=3:raise ValueError('Actual source file menu with three slots not present')
    return out

def cases(profile):
    if profile=='original':
        return {'ascii-three':[[0x7E,0x95,0xA3,0xA3],[0x71,0x91,0x60,0x79,0xA3],[0x7D,0x87,0x79,0x99,0x61]],'one-ascii-two-empty':[[0x7E,0x95,0xA3,0xA3],[],[]]}
    return {
      'mixed-six': [qa.MIXED,[0x7A,0xB1,0xC1,0x61,0xB9,0xB8],[0x7B,0xB2,0xC2,0x62,0xB8,0xB9]],
      'accent-six': [list(range(0xB0,0xB6)),list(range(0xC0,0xC6)),[0xB7,0xC7,0xB0,0xC0,0xB5,0xC5]],
      'symbol-six': [[0xB7,0xC7,0xB8,0xB9,0xAC,0xAF],[0xAE,0x57,0x53,0x5F,0x5D,0x6F],[0xAC,0xB8,0xB9,0xAF,0x50,0x61]],
      'width-boundary-ascii': [[0x87,0x87,0x71,0x78,0x78,0x95],[0x79,0x99,0x61]*2,[0x71,0x91,0x60,0x79,0xA3,0xA4]],
      'one-six-two-empty': [qa.MIXED,[],[]],
    }

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('source','builds','runtime','original-assets','redux-assets','original-phone-seed','redux-phone-seed','scratch','output'):
        ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--pilot',action='store_true')
    a=ap.parse_args()
    for n,v in vars(a).items():
        if isinstance(v,Path):setattr(a,n,v.resolve())
    a.scratch=local_scratch(a.scratch)
    if a.scratch.exists() or a.output.exists():raise ValueError('Fresh scratch/report required')
    a.scratch.mkdir();sys.path.insert(0,str(a.source/'src/vendor/tamp'));import tamp
    l=compile_layout(a.source,a.builds/'player',a.scratch);producers.DRIVER=DRIVER;results=[]
    for mode in (('player',) if a.pilot else ('player','observer')):
        exe=a.runtime/(mode+'.exe')
        if qa.sha(exe)!=qa.sha(a.builds/mode/'earthbound.exe'):raise ValueError('Complete archive/runtime mismatch')
        driver,linkid=producers.link(a.source,a.builds/mode,a.runtime,a.scratch/(mode+'-phone-link'))
        for profile,pack,phone in [('original',a.original_assets,a.original_phone_seed),('redux',a.redux_assets,a.redux_phone_seed)]:
            _,_,assets=qa.read_pack(pack,a.source/'src/data/runtime_generated/asset_ids.h')
            for label,names in cases(profile).items():
                if a.pilot and (profile!='redux' or label!='mixed-six'):continue
                folder=a.scratch/(mode+'-'+profile+'-'+label);folder.mkdir();prepared=folder/'prepared.srm';shutil.copy2(phone,prepared)
                inp=folder/'names.txt';inp.write_text('\n'.join(' '.join(map(str,[len(name),*name])) for name in names)+'\n',encoding='ascii')
                p=subprocess.run([str(driver),str(pack),str(folder),str(prepared),str(inp)],cwd=driver.parent,env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=60);(folder/'phone-native.log').write_bytes(p.stdout+p.stderr)
                if p.returncode:raise ValueError('Actual native private phone writer failed')
                initial=qa.sha(prepared);session=Session(exe,pack,folder/'actual-slot-list',l,tamp);session.qa_assets=assets;shutil.copy2(prepared,session.folder/'fixture.srm');session.run('actual-source-file-slot-list',focused.first_rows(),1300,load=False)
                warm=observe(session,names);capture=qa.sha(latest(session.folder));session.step('fresh-f6-restore-slot-list',wait=30);cold=observe(session,names)
                stable=warm==cold; selections=[]
                # Actual cursor movement, confirm, and cancellation rebuild both
                # occupied file rows and the ordinary ASCII/empty controls.
                for slot in range(3):
                    current=session.slot_rows[0]['currentOption']
                    if current!=slot:
                        button=qa.naming.DOWN if current<slot else qa.naming.UP
                        session.step('actual-cursor-to-slot-'+str(slot+1),[button]*abs(slot-current),wait=30)
                    if session.slot_rows[0]['currentOption']!=slot:raise ValueError('Actual slot cursor prerequisite failed')
                    session.step('actual-confirm-slot-'+str(slot+1),[qa.naming.CONFIRM],wait=80)
                    after=observe(session,names) if names[slot] else None
                    occupied=any(r['id']==20 for r in session.last['titles']);empty=any(r['id']==24 for r in session.last['titles'])
                    selectpass=occupied==bool(names[slot]) and empty!=bool(names[slot])
                    highlight=None
                    if after is not None and profile=='redux':
                        selected=after[slot]; attrs=[[(v>>10)&7 for v in pair] for pair in selected['tilemaps']]
                        outside=[[(v>>10)&7 for v in pair] for pair in selected['remainingTilemaps']]
                        highlight=dict(attributes=attrs,allSourceMeasuredColumnsPalette6=all(v==6 for pair in attrs for v in pair),trailingColumnsUnhighlighted=all(v==0 for pair in outside for v in pair),glyphsAndTilesPreserved=selected['sourceGlyphsMatch'] and selected['sourceFontColumnsMatch'])
                        selectpass &= highlight['allSourceMeasuredColumnsPalette6'] and highlight['trailingColumnsUnhighlighted'] and highlight['glyphsAndTilesPreserved']
                    selections.append(dict(slot=slot,occupiedSubmenu=occupied,emptyNewGameMenu=empty,highlight=highlight,Passed=selectpass))
                    if not names[slot]:break
                    session.step('actual-cancel-back-to-slot-list-'+str(slot+1),[qa.naming.B],wait=60)
                    rebuilt=observe(session,names)
                    selectpass &= all(r['sourceGlyphsMatch'] and r['sourceFontColumnsMatch'] for r in rebuilt)
                    selections[-1]['rebuiltSourceLabelsPass']=selectpass;selections[-1]['Passed']=selectpass
                phone_same=qa.sha(session.folder/'fixture.srm')==initial
                legal=True
                if profile=='redux':legal=all(len(n)<=6 and sum(assets['US/fonts/main.bin'][g-0x50]+1 for g in n)<=40 for n in names)
                sourcepass=all(r['sourceGlyphsMatch'] and r['sourceFontColumnsMatch'] and r['labelBytesBounded'] and r['occupiedLabelBeforeLevelColumn'] for r in warm+cold)
                row=dict(build=mode,profile=profile,case=label,preparedNames=names,sourceNamingCapacityAndFortyPixelLimitRespected=legal,packSha256=qa.sha(pack),executableSha256=qa.sha(exe),archiveSha256=linkid['archiveSha256'],phoneWriterLink=linkid,phoneSeedSha256=qa.sha(phone),nativePreparedPhoneSha256=initial,externalPhoneBytesPreserved=phone_same,actualF6CaptureSha256=capture,stateVersion=session.last['stateVersion'],warm=warm,cold=cold,freshF6LabelsAndTilesPreserved=stable,actualInputSelections=selections,sourceExpectedPassed=sourcepass,Passed=sourcepass and stable and legal and phone_same and all(r['Passed'] for r in selections))
                results.append(row);print(json.dumps(dict(completed=mode+'-'+profile+'-'+label,sourceExpectedPassed=sourcepass,Passed=row['Passed'])),flush=True)
    report=dict(format='actual-complete-file-slot-glyph-warm-cold-dev18-v1',toolSha256=qa.sha(Path(__file__)),phoneWriterDriverSha256=hashlib.sha256(DRIVER.encode()).hexdigest(),candidateSourceIdentities={p:qa.sha(a.source/p) for p in ('src/intro/file_select.c','src/game/window.c','src/game/window.h','src/core/state_dump.c')},results=results,allPassed=all(r['Passed'] for r in results),allExternalPhoneControlsPassed=all(r['externalPhoneBytesPreserved'] for r in results),dependencies={p:qa.sha(ROOT/p) for p in ('tools/redux_title_cold_qa_dev18.py','tools/file_select_cold_qa_dev18.py','tools/redux_title_producers_qa_dev18.py','tools/redux_naming_qa.py')},sourceContracts=['asm/intro/file_select_menu.asm directly copies raw character-name glyphs to TEMPORARY_TEXT_BUFFER after numbered prefix.', 'Pinned ccscript/redux/six_letters.ccs NAMES_LENGTH=6 and MAX_LENGTH_ALLOWED=40; source naming glyphs derive naming_screen_table.ccs.', 'Pinned bugfixes/text_highlights_fix.ccs indexes the selected window font with source glyph minus50/mask7F, accumulating width+1. The native adapter retains the measured-column highlight implementation and corrects its glyph input only.'],limits=['Private prepared names/phone slots are persisted through actual native APIs into valid checksummed phone saves. This covers real file-menu producers/rendering/input and fresh-process F6 continuation, not natural story acquisition or newly typed names.', 'Pixel/VRAM identity uses an independent packed-font compositor. No original CPU full file-menu/whole-screen renderer is claimed.', 'Capture-state uses the actual F6 save writer; the physical F6 key is not synthesized. File-menu copy/delete/config and every phase are not exhaustive.', 'Only ordinary file-slot labels are in scope. Existing captured labels that already contain question marks cannot recover glyphs until rebuilt. Format16 and MenuItem/WindowInfo remain unchanged.', 'Root/source/builds, owner saves, ROMs/packs and frozen prior evidence are untouched.'],rootOrOwnerInputsModified=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(report=str(a.output),allPassed=report['allPassed'],sha256=qa.sha(a.output))))

if __name__=='__main__':main()
