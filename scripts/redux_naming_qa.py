# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise Redux's source-defined naming keyboard through ordinary inputs.

Every process uses a new private session below _BuildScratch. No story flags,
positions, packs or saved-state bytes are injected. Raw EB glyphs are read from
captured states to avoid lossy ASCII logging. Cold keyboard resumes, committed
names, native phone-format saving and fresh phone-save loading are checked.
"""
import argparse
from collections import deque
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

from build_maternalbound_pack import read_pack
from check_jev_observer_parity import latest, local_scratch, sections

ROOT=Path(__file__).resolve().parents[1]
UP,DOWN,LEFT,RIGHT,CONFIRM,B,SELECT,START=0x800,0x400,0x200,0x100,0x20,0x8000,0x2000,0x1000
REDUX_STOPS=((0,2,4,6,8,10,12,14,16,22,24),)*3+((0,2,4,6,8,10,12,22,24),(0,2,4,6,8,10,12,14,16,18,22,24),(0,7,22,24),(0,17,25),())
RETAIL_STOPS=((0,2,4,6,8,10,12,14,16,22,24),)*3+((0,2,4,6,8,10,12,14,16,18,22,24),(0,7,22,24),(),(0,17,25),())
REDUX_UPPER=((0x71,0x72,0x73,0x74,0x75,0x76,0x77,0x78,0x79,0xFF,0xFF,0x5D,0x53,0xFF),
             (0x7A,0x7B,0x7C,0x7D,0x7E,0x7F,0x80,0x81,0x82,0xFF,0xFF,0x57,0xAE,0xFF),
             (0x83,0x84,0x85,0x86,0x87,0x88,0x89,0x8A,0x50,0xFF,0xFF,0x5E,0x5F,0xFF),
             (0xB0,0xB1,0xB2,0xB3,0xB4,0xB5,0xB7,0xFF,0xFF,0xFF,0xFF,0xB8,0x6F,0xFF),
             (0x60,0x61,0x62,0x63,0x64,0x65,0x66,0x67,0x68,0x69,0xFF,0xB9,0x51,0xFF),
             (0xFF,)*11+(0xAC,0xAF,0xFF))
REDUX_LOWER=tuple(tuple(c+0x20 if 0x71<=c<=0x8A else c+0x10 if 0xB0<=c<=0xB7 else c for c in row) for row in REDUX_UPPER)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def compile_layout(native, compiler, output):
    source=output/'naming-layout.c'
    source.write_text('''#include <stdio.h>
#include <stddef.h>
#include "core/mode_stack.h"
#include "game/game_state.h"
#include "game/window.h"
#include "snes/ppu.h"
#define FIELD(T,F) printf("\\\"" #T "." #F "\\\":%zu,",offsetof(T,F))
int main(void) {
 printf("{\\\"ModeStack.size\\\":%zu,\\\"ModeState.size\\\":%zu,\\\"TextInputMode\\\":%u,",sizeof(ModeStack),sizeof(ModeState),GAME_MODE_TEXT_INPUT);
 FIELD(ModeStack,state); FIELD(ModeStack,mode); FIELD(ModeStack,depth);
 FIELD(TextInputState,name_target); FIELD(TextInputState,is_lowercase); FIELD(TextInputState,name_pos);
 FIELD(TextInputState,cur_x); FIELD(TextInputState,cur_y); FIELD(TextInputState,eb_name);
 FIELD(TextInputState,max_len);
 FIELD(CharStruct,name); FIELD(SaveBlock,party_characters); FIELD(SaveBlock,redux_name_extra);
 FIELD(SaveBlock,redux_name_magic); FIELD(SaveBlock,game_state); FIELD(SaveBlock,redux_food_extra);
 FIELD(GameState,favourite_food); FIELD(GameState,party_count);
 FIELD(WindowSystemState,bg2_buffer); FIELD(WindowSystemState,windows);
 FIELD(WindowInfo,content_x); FIELD(WindowInfo,content_y); FIELD(WindowInfo,id); FIELD(WindowInfo,active);
 FIELD(PPUState,vram);
 printf("\\\"WindowInfo.size\\\":%zu,",sizeof(WindowInfo));
 printf("\\\"CharStruct.size\\\":%zu,\\\"SaveBlock.size\\\":%zu}",sizeof(CharStruct),sizeof(SaveBlock)); return 0;
}''',encoding='utf-8')
    exe=output/'naming-layout.exe'
    proc=subprocess.run([str(compiler.resolve()),'-std=c2x','-I',str((native/'src').resolve()),'-I',str((ROOT/'build/companion/game_lib/generated').resolve()),str(source),'-o',str(exe)],capture_output=True,timeout=45)
    if proc.returncode:raise RuntimeError(proc.stderr.decode(errors='replace'))
    return json.loads(subprocess.check_output([str(exe)],timeout=10))


def route(start,target,stops):
    def move(node,button):
        x,y=node
        if button in (LEFT,RIGHT):
            dx=1 if button==RIGHT else -1
            for _ in range(30):
                x=(x+dx)%30
                if x in stops[y]:return x,y
        else:
            dy=1 if button==DOWN else -1
            for _ in range(8):
                y=(y+dy)%8
                if x in stops[y]:return x,y
                left=[xx for xx in stops[y] if xx<x]
                if left:return max(left),y
                right=[xx for xx in stops[y] if xx>x]
                if right:return min(right),y
        return node
    pending=deque([(start,[])]);visited={start}
    while pending:
        node,buttons=pending.popleft()
        if node==target:return buttons
        for button in (DOWN,RIGHT,UP,LEFT):
            dest=move(node,button)
            if dest not in visited:visited.add(dest);pending.append((dest,buttons+[button]))
    raise ValueError('Unreachable keyboard cell '+str(target))


def raster_tiles(glyphs,widths,graphics,padding):
    """Independent pixel compositor for the converted inverted 1bpp font."""
    stride=len(graphics)//len(widths)
    pixels=sum(widths[g-0x50]+padding for g in glyphs)
    columns=(pixels+7)//8;result=bytearray([255]*(columns*32));x=0
    for glyph in glyphs:
        bitmap=graphics[(glyph-0x50)*stride:(glyph-0x50)*stride+16]
        for y,bits in enumerate(bitmap):
            for bit in range(8):
                at=x+bit
                if not bits&(128>>bit) and at<columns*8:
                    result[(at//8)*32+y*2+1]&=255^(128>>(at%8))
        x+=widths[glyph-0x50]+padding
    return [result[i*32:(i+1)*32] for i in range(columns)]


class Session:
    def __init__(self,exe,pak,folder,layout,tamp):
        self.exe,self.pak,self.folder,self.layout,self.tamp=exe,pak,folder,layout,tamp
        folder.mkdir();self.count=0;self.last=None
        self.config=folder/'fixture.ini'
        self.config.write_text('companion=1\nfullscreen=0\nwidth=1280\nheight=720\nmasterVolume=0\n',encoding='utf-8')
        self.env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
        _,_,assets=read_pack(pak,ROOT/'native-source/src/data/runtime_generated/asset_ids.h')
        self.widths,self.graphics=assets['US/fonts/main.bin'],assets['US/fonts/main.gfx']
        self.render_checks=0

    def read(self):
        blobs=sections(latest(self.folder),self.tamp);ms=blobs[21];l=self.layout
        depth=ms[l['ModeStack.depth']];modes=list(ms[l['ModeStack.mode']:l['ModeStack.mode']+depth]);keyboard=None
        for index,mode in enumerate(modes):
            if mode!=l['TextInputMode']:continue
            at=l['ModeStack.state']+index*l['ModeState.size'];state=ms[at:at+l['ModeState.size']]
            length=struct.unpack_from('<H',state,l['TextInputState.name_pos'])[0]
            keyboard={'target':state[l['TextInputState.name_target']], 'lowercase':bool(state[l['TextInputState.is_lowercase']]),
                      'cursor':tuple(struct.unpack_from('<hh',state,l['TextInputState.cur_x'])),
                      'name':list(state[l['TextInputState.eb_name']:l['TextInputState.eb_name']+length])}
        names=[list(blobs[3][i*l['CharStruct.size']+l['CharStruct.name']:i*l['CharStruct.size']+l['CharStruct.name']+5])+[blobs[45][i]] for i in range(4)]
        food=list(blobs[2][l['GameState.favourite_food']:l['GameState.favourite_food']+6])+list(blobs[46])
        self.last={'modes':modes,'keyboard':keyboard,'names':names,'food':food,'partyCount':blobs[2][l['GameState.party_count']]}
        if keyboard:
            w=blobs[8]
            at=next(l['WindowSystemState.windows']+i*l['WindowInfo.size'] for i in range(8) if w[l['WindowSystemState.windows']+i*l['WindowInfo.size']+l['WindowInfo.id']]==28 and w[l['WindowSystemState.windows']+i*l['WindowInfo.size']+l['WindowInfo.active']])
            bx=w[at+l['WindowInfo.content_x']];by=w[at+l['WindowInfo.content_y']]
            bg2=l['WindowSystemState.bg2_buffer']
            self.last['keyboardBottomRowTiles']=[f'{struct.unpack_from("<H",w,bg2+2*((by+12)*32+bx+x))[0]:04X}' for x in range(30) if bx+x<32]
            if len(self.widths)==128:
                ppu=blobs[10];padding=blobs[31][0];grid=REDUX_LOWER if keyboard['lowercase'] else REDUX_UPPER
                def tile(tx,ty):return struct.unpack_from('<H',w,bg2+2*((by+ty)*32+bx+tx))[0]&0x3FF
                def actual_pair(tx,ty):
                    return b''.join(ppu[l['PPUState.vram']+0xC000+tile(tx,ty+dy)*16:l['PPUState.vram']+0xC000+tile(tx,ty+dy)*16+16] for dy in (0,1))
                next_tile=0x200
                for row,values in enumerate(grid):
                    for col,glyph in enumerate(values):
                        if glyph==255:continue
                        tx=col*2+1
                        expected=raster_tiles([glyph],self.widths,self.graphics,padding)
                        if len(expected)!=1 or tile(tx,row*2)!=next_tile or tile(tx,row*2+1)!=next_tile+1 or actual_pair(tx,row*2)!=expected[0]:
                            raise RuntimeError(f'Grid font/VRAM mismatch at {col},{row} EB {glyph:02X}: tiles {tile(tx,row*2):03X}/{tile(tx,row*2+1):03X}, expected {next_tile:03X}')
                        next_tile+=2
                if next_tile!=0x270:raise RuntimeError('Grid range is not 0x200-0x26F')
                used=set(range(0x200,0x270))|{0x28D,0x29D}
                name_max=struct.unpack_from('<H',ms,l['ModeStack.state']+modes.index(l['TextInputMode'])*l['ModeState.size']+l['TextInputState.max_len'])[0]
                used.update(range(0x2E0,0x2E0+name_max*2))
                for text,tx,ty in (('CAPITAL',1,10),('small',8,10),("Don't Care",1,12),('Backspace',18,12),('OK',26,12)):
                    expected=raster_tiles([ord(c)+0x30 for c in text],self.widths,self.graphics,padding)
                    for column,bitmap in enumerate(expected):
                        upper,lower=tile(tx+column,ty),tile(tx+column,ty+1)
                        if not (0x2E0<=upper<0x380 and 0x2E0<=lower<0x380) or upper in used or lower in used or actual_pair(tx+column,ty)!=bitmap:
                            raise RuntimeError(f'Label font/VRAM collision for {text} column {column}: {upper:03X}/{lower:03X}')
                        used.update((upper,lower))
                self.render_checks+=1
                self.last['keyboardRenderingVerified']=True
        return self.last

    def run(self,label,rows,frame,load=True,dump=False):
        self.count+=1;prefix=f'{self.count:03d}-{label}';replay=self.folder/'inputs.replay'
        replay.write_text('\n'.join(f'{f} {pad:04X}' for f,pad in sorted(rows))+'\n',encoding='ascii')
        cmd=[str(self.exe),'--assets',str(self.pak),'--session-dir',str(self.folder),'--save',str(self.folder/'fixture.srm'),
             '--config',str(self.config),'--allow-redux-development','--windowed' if dump else '--headless','--fast-forward','--input-script',str(replay),
             '--frames',str(frame+300),'--capture-state',str(frame)]
        if load:cmd+=['--skip-intro','--load-state']
        if dump:cmd+=['--dump-frame',str(frame)]
        proc=subprocess.run(cmd,cwd=self.folder,env=self.env,capture_output=True,timeout=60)
        log=(proc.stdout+proc.stderr).decode(errors='replace');(self.folder/(prefix+'.log')).write_text(log,encoding='utf-8')
        if proc.returncode or 'PC replay checkpoint:' not in log or re.search(r'\b(FATAL|FAIL|unimplemented|unknown opcode)\b',log,re.I):
            raise RuntimeError(prefix+' failed: '+log[-1500:])
        result=self.read();(self.folder/(prefix+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        if dump:shutil.copy2(self.folder/'screenshot.bmp',self.folder/(prefix+'.bmp'))
        return result

    def step(self,label,buttons=(),wait=20,dump=False):
        rows=[(0,0)]
        for index,button in enumerate(buttons):rows.extend(((10+index*6,button),(12+index*6,0)))
        return self.run(label,rows,10+len(buttons)*6+wait,dump=dump)

    def keyboard(self):
        if not self.last or self.last['keyboard'] is None:raise RuntimeError('Expected an active naming keyboard: '+str(self.last))
        return self.last['keyboard']

    def navigate(self,cell,stops=REDUX_STOPS):
        return route(self.keyboard()['cursor'],cell,stops)

    def clear(self):
        length=len(self.keyboard()['name'])
        if length:self.step('clear-buffer',[B]*length)
        if self.keyboard()['name']:raise RuntimeError('Backspace did not clear entered glyphs')


def bootstrap(session):
    rows=[]
    for f in (300,460,500,650,670,690,710,730):rows.extend(((f,CONFIRM),(f+2,0)))
    session.run('first-keyboard',rows,760,load=False)
    if session.keyboard()['target']!=0:raise RuntimeError('Opening did not reach the first character keyboard')
    session.clear()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('engine','assets','scratch'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--original-assets',type=Path)
    p.add_argument('--native-source',type=Path,default=ROOT/'native-source')
    p.add_argument('--compiler',type=Path,default=ROOT/'tools/mingw64/bin/gcc.exe')
    a=p.parse_args();out=local_scratch(a.scratch)
    if out.exists():raise ValueError('Choose a fresh scratch directory')
    out.mkdir(parents=True);sys.path.insert(0,str(a.native_source/'src/vendor/tamp'));import tamp
    identities={'engine':sha(a.engine),'redux':sha(a.assets)}
    if a.original_assets:identities['original']=sha(a.original_assets)
    layout=compile_layout(a.native_source,a.compiler,out)
    session=Session(a.engine.resolve(),a.assets.resolve(),out/'redux',layout,tamp);bootstrap(session)
    # Seven upper and seven lower accents, two additional symbols, every digit.
    choices=[(False,(2*i,3),g) for i,g in enumerate((0xB0,0xB1,0xB2,0xB3,0xB4,0xB5,0xB7))]
    choices += [(True,(2*i,3),g) for i,g in enumerate((0xC0,0xC1,0xC2,0xC3,0xC4,0xC5,0xC7))]
    choices += [(False,(22,3),0xB8),(False,(22,4),0xB9)]+[(False,(2*i,4),0x60+i) for i in range(10)]
    checked=[]
    for lowercase,cell,glyph in choices:
        buttons=[]
        if session.keyboard()['lowercase']!=lowercase:buttons.append(SELECT)
        buttons+=session.navigate(cell)+[CONFIRM]
        session.step(f'glyph-{glyph:02x}',buttons)
        if session.keyboard()['cursor']!=cell or session.keyboard()['name']!=[glyph]:
            raise RuntimeError(f'Wrong selected EB glyph {glyph:02X}: '+str(session.keyboard()))
        checked.append({'glyph':f'{glyph:02X}','cell':list(cell),'lowercase':lowercase})
        session.step('erase-glyph',[B])
        if session.keyboard()['name']:raise RuntimeError('Selected glyph not erased with B')
    mixed=[0x79,0xB0,0xC0,0x60,0xB8,0xB9]
    cells=[(False,(16,0)),(False,(0,3)),(True,(0,3)),(True,(0,4)),(True,(22,3)),(True,(22,4))]
    for index,(lowercase,cell) in enumerate(cells):
        buttons=[]
        if session.keyboard()['lowercase']!=lowercase:buttons.append(SELECT)
        buttons+=session.navigate(cell)+[CONFIRM]
        session.step('mixed-name-'+str(index+1),buttons)
        if session.keyboard()['name']!=mixed[:index+1]:raise RuntimeError('Mixed six-letter name changed during entry')
    before=session.keyboard().copy();session.step('cold-keyboard-resume',dump=True)
    if session.keyboard()!=before:raise RuntimeError('Cold keyboard restore changed glyphs/case/cursor')
    session.step('confirm-six-letter-name',[START],wait=80)
    if session.last['names'][0]!=mixed:raise RuntimeError('Committed name lost an accented/symbol/sixth glyph')
    # Continue all remaining naming prompts by their real event/menu flows.
    for target in range(1,7):
        for attempt in range(25):
            k=session.last['keyboard']
            if k and k['target']==target:break
            session.step('next-naming-prompt',[CONFIRM],wait=100)
        else:raise RuntimeError('Naming flow did not reach target '+str(target))
        session.clear()
        if target==5:
            session.step('ten-letter-food',session.navigate((16,0))+[CONFIRM]*10)
            if session.keyboard()['name']!=[0x79]*10:raise RuntimeError('Food keyboard did not accept ten narrow glyphs')
        else:
            session.step('default-name',session.navigate((0,6))+[CONFIRM])
            if not session.keyboard()['name']:raise RuntimeError('Do not care name was empty')
        session.step('confirm-naming-target',[START],wait=100)
    session.step('finish-naming',[CONFIRM],wait=4000)
    if session.last['names'][0]!=mixed or session.last['food']!=[0x79]*10 or session.last['partyCount']!=1:
        raise RuntimeError('Opening did not preserve names/food/party: '+str(session.last))
    # Save invokes the same save_game() phone-format writer used by Dad.
    session.step('open-pause-menu',[0x40],wait=40)
    session.step('save-phone-format',[DOWN,DOWN,CONFIRM],wait=80)
    phone=session.folder/'fixture.srm';saved=phone.read_bytes();l=layout
    prefix=l['SaveBlock.party_characters']+l['CharStruct.name']
    actual=list(saved[prefix:prefix+5])+[saved[l['SaveBlock.redux_name_extra']]]
    foodat=l['SaveBlock.game_state']+l['GameState.favourite_food']
    if actual!=mixed or saved[l['SaveBlock.redux_name_magic']:l['SaveBlock.redux_name_magic']+4]!=b'MRN1' or list(saved[foodat:foodat+6])+list(saved[l['SaveBlock.redux_food_extra']:l['SaveBlock.redux_food_extra']+4])!=[0x79]*10:
        raise RuntimeError('Native phone-format save did not retain the keyboard glyphs')
    session.step('exit-pause-menu',[B]);session.step('cold-world-resume',dump=True)
    if session.last['names'][0]!=mixed or session.last['food']!=[0x79]*10:raise RuntimeError('World F6 cold restore lost names or food')
    restored=Session(a.engine.resolve(),a.assets.resolve(),out/'phone-boot',layout,tamp)
    shutil.copy2(phone,restored.folder/'fixture.srm')
    rows=[(0,0)]
    for f in (200,400,600,800):rows.extend(((f,CONFIRM),(f+2,0)))
    restored.run('fresh-phone-load',rows,1300,load=False)
    if restored.last['names'][0]!=mixed or restored.last['food']!=[0x79]*10 or restored.last['partyCount']!=1:
        raise RuntimeError('Fresh phone save load did not restore the committed glyphs: '+str(restored.last))
    retail=None
    if a.original_assets:
        original=Session(a.engine.resolve(),a.original_assets.resolve(),out/'original',layout,tamp);bootstrap(original)
        original.step('retail-digit-row',original.navigate((0,3),RETAIL_STOPS)+[CONFIRM])
        if original.keyboard()['name']!=[0x60]:raise RuntimeError('Original retail digit row changed')
        original.step('retail-select-backspace',[SELECT])
        if original.keyboard()['name'] or original.keyboard()['lowercase']:raise RuntimeError('Original Select backspace behavior changed')
        retail={'digitRow':3,'selectBackspaces':True,'alphabetRow':4}
    if identities['engine']!=sha(a.engine) or identities['redux']!=sha(a.assets) or (a.original_assets and identities['original']!=sha(a.original_assets)):
        raise RuntimeError('Immutable naming QA inputs changed during execution')
    result={'format':'redux-naming-input-qa-v1','Passed':True,'identities':identities,'glyphSelectionCases':checked,
            'sixLetterMixedNameRawEbIds':[f'{g:02X}' for g in mixed],'keyboardColdResumePreservesCaseCursorGlyphs':True,
            'committedSixLetterName':True,'tenLetterFoodKeyboard':True,'nativePhoneFormatWriteAndFreshLoad':True,
            'worldQuicksaveColdLoad':True,'originalRetailChecks':retail,'ownerSavesTouched':False,'fullPlaythroughVerified':False,
            'reduxKeyboardRenderedStatesChecked':session.render_checks,'reduxGridExactConvertedFontPixels':True,
            'buttonLabelsExactConvertedFontPixels':True,'gridNameCursorLabelTileRangesDisjoint':True,
            'limits':['Ordinary-input new-game/naming/opening and native menu Save only; no full story or complete rendering oracle.',
                      'Menu Save uses the production phone-format writer; actual Dad dialogue is not exercised by this fixture.',
                      'Raw glyph/state preservation and nonempty font data do not prove every UI renders every name perfectly.']}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
