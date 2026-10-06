# SPDX-License-Identifier: GPL-3.0-or-later
"""Adapt actual relocated Redux swirl HDMA streams without namespace changes."""
from maternalbound_graphics import ConversionError,snes_offset

def decode_rows(data):
    if not data or data[0]not in (1,4):raise ConversionError('Unsupported swirl HDMA mode')
    width=2 if data[0]==1 else 4;at=1;rows=[]
    while True:
        if at>=len(data):raise ConversionError('Unterminated swirl HDMA')
        count=data[at];at+=1
        if not count:break
        n=count&127
        if not n:raise ConversionError('Unexpected128-row source swirl entry')
        length=width*n if count&128 else width
        if at+length>len(data):raise ConversionError('Truncated swirl HDMA')
        if count&128:
            for i in range(n):
                r=tuple(data[at+i*width:at+(i+1)*width]);rows.append(r if width==4 else(*r,255,0))
        else:
            r=tuple(data[at:at+width]);rows.extend([r if width==4 else(*r,255,0)]*n)
        at+=length
        if len(rows)>224:raise ConversionError('Swirl HDMA exceeds224 rows')
    if len(rows)!=224:raise ConversionError('Source swirl does not span224 rows')
    return rows,at

def convert_swirls(rom,assets):
    primary=rom[0xEDD41:0xEDD41+28]
    expected=bytes.fromhex('000000000200170004170f0003261600043c150002511c00036d1100')
    if primary!=expected:raise ConversionError('Native swirl metadata contract changed')
    pointer=int.from_bytes(rom[0x4AA8F:0x4AA92],'little')
    for at,delta in ((0x4AA95,2),(0x4AADC,0),(0x4AAE4,2)):
        if int.from_bytes(rom[at:at+3],'little')!=pointer+delta:raise ConversionError('Source swirl pointer consumers disagree')
    table=snes_offset(pointer,len(rom))
    if table+126*4>len(rom):raise ConversionError('Swirl pointer table outside ROM')
    changed=[];review=[]
    for i in range(126):
        address=int.from_bytes(rom[table+i*4:table+i*4+4],'little');off=snes_offset(address,len(rom));source=rom[off:off+1100];rows,used=decode_rows(source)
        key=f'swirls/{i}.swirl'
        if key not in assets:raise ConversionError('Native swirl registry entry missing')
        donor,_=decode_rows(assets[key]);different=rows!=donor
        if different:assets[key]=source[:used];changed.append(key)
        review.append(dict(frame=i,sourcePointer=address,sourceMode=source[0],sourceBytes=used,semanticRowsChanged=different))
    return dict(assets=changed,sourcePointerTable=pointer,sourceFrames=126,sourceAnimationTypes=6,namespaceUnchanged=True,reviewedFrames=review)
