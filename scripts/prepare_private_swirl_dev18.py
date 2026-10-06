# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepare isolated two-window swirl correction and source-resolved importer."""
import argparse,hashlib,json,shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
IMPORTER=r'''# SPDX-License-Identifier: GPL-3.0-or-later
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
'''

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native-baseline',type=Path,required=True);p.add_argument('--tools-baseline',type=Path,required=True);p.add_argument('--scratch',type=Path,required=True);a=p.parse_args();a.scratch=a.scratch.resolve()
    if a.scratch.exists()or not a.scratch.is_relative_to(ROOT/'_BuildScratch'):raise ValueError('Fresh private scratch required')
    a.scratch.mkdir(parents=True);native=a.scratch/'native-source';shutil.copytree(a.native_baseline,native,ignore=shutil.ignore_patterns('.git','.venv','__pycache__'))
    tools=a.scratch/'tools';shutil.copytree(a.tools_baseline,tools,ignore=shutil.ignore_patterns('__pycache__'))
    module=tools/'maternalbound_swirls.py';module.write_text(IMPORTER,encoding='utf-8');builder=tools/'build_maternalbound_pack.py';text=builder.read_text(encoding='utf-8')
    if sha(builder)!='97f3c8cea7d1f5155ad4fd218ead2876f6693c6ead748860cc322fb8a41cece1':raise ValueError('Expected frozen teleport builder')
    for needle in ('from maternalbound_sequence_animations import convert_sequence_animations\n','    sequence_animations = convert_sequence_animations(rom,assets)\n'):
        if text.count(needle)!=1:raise ValueError('Builder sequence boundary changed')
    text=text.replace('from maternalbound_sequence_animations import convert_sequence_animations\n','from maternalbound_sequence_animations import convert_sequence_animations\nfrom maternalbound_swirls import convert_swirls\n')
    text=text.replace('    sequence_animations = convert_sequence_animations(rom,assets)\n','    sequence_animations = convert_sequence_animations(rom,assets)\n    swirls = convert_swirls(rom,assets)\n')
    text=text.replace('+sequence_animations["assets"]+audio["assets"]','+sequence_animations["assets"]+swirls["assets"]+audio["assets"]');text=text.replace('"sequenceAnimations":sequence_animations,"audio":audio','"sequenceAnimations":sequence_animations,"swirls":swirls,"audio":audio');builder.write_text(text,encoding='utf-8')
    source=native/'src/game/oval_window.c';baseline=source.read_bytes();s=baseline.decode('utf-8');newline='\r\n'if b'\r\n'in baseline else'\n';s=s.replace('\r\n','\n')
    def replace(before,after):
        nonlocal s
        if s.count(before)!=1:raise ValueError('Native exact boundary changed: '+before[:55])
        s=s.replace(before,after)
    replace('static uint16_t swirl_window_hdma_buffer[EB_VIEWPORT_HEIGHT];','''static uint16_t swirl_window_hdma_buffer[EB_VIEWPORT_HEIGHT];
/* DMAP4 writes WH0/WH1/WH2/WH3. Both buffers are derived render caches. */
static uint16_t swirl_window2_hdma_buffer[EB_VIEWPORT_HEIGHT];
static bool swirl_window2_enabled;
static void rebuild_active_swirl_window_cache(void);''')
    replace('''    if (s->loaded_oval_window_seq == 0 || s->loaded_oval_window_seq > OVAL_SEQ_COUNT) {
        loaded_oval_window = NULL;
    } else {
        loaded_oval_window = oval_seq_table[s->loaded_oval_window_seq - 1].base
                           + s->loaded_oval_window_index;
    }
}''','''    if (s->loaded_oval_window_seq == 0 || s->loaded_oval_window_seq > OVAL_SEQ_COUNT) {
        loaded_oval_window = NULL;
    } else {
        loaded_oval_window = oval_seq_table[s->loaded_oval_window_seq - 1].base
                           + s->loaded_oval_window_index;
    }
    rebuild_active_swirl_window_cache();
}''')
    replace('''    for (int i = 0; i < EB_VIEWPORT_HEIGHT; i++)
        swirl_window_hdma_buffer[i] = 0xFF00;

    if (data_size < 2) return;''','''    for (int i = 0; i < EB_VIEWPORT_HEIGHT; i++) {
        swirl_window_hdma_buffer[i] = 0xFF00;
        swirl_window2_hdma_buffer[i] = 0xFF00;
    }
    swirl_window2_enabled = false;
    if (data_size < 2) return;''')
    replace('''    int bytes_per_entry = (dmap == 0x04) ? 4 : 2;''','''    int bytes_per_entry = (dmap == 0x04) ? 4 : 2;
    swirl_window2_enabled = (dmap == 0x04);''')
    replace('''                swirl_window_hdma_buffer[scanline++] = (uint16_t)((wh0 << 8) | wh1);
                /* Skip WH2/WH3 in 4-register mode */
                if (bytes_per_entry == 4 && p + 1 < end)
                    p += 2;''','''                swirl_window_hdma_buffer[scanline] = (uint16_t)((wh0 << 8) | wh1);
                if (bytes_per_entry == 4 && p + 1 < end) {
                    swirl_window2_hdma_buffer[scanline] = (uint16_t)((p[0] << 8) | p[1]);
                    p += 2;
                }
                scanline++;''')
    replace('''            /* Skip WH2/WH3 in 4-register mode */
            if (bytes_per_entry == 4 && p + 1 < end)
                p += 2;
            for (int i = 0; i < count && scanline < max_scanline; i++) {
                swirl_window_hdma_buffer[scanline++] = (uint16_t)((wh0 << 8) | wh1);
            }''','''            uint16_t second = 0xFF00;
            if (bytes_per_entry == 4 && p + 1 < end) {
                second = (uint16_t)((p[0] << 8) | p[1]);
                p += 2;
            }
            for (int i = 0; i < count && scanline < max_scanline; i++) {
                swirl_window_hdma_buffer[scanline] = (uint16_t)((wh0 << 8) | wh1);
                swirl_window2_hdma_buffer[scanline++] = second;
            }''')
    replace('''        for (int i = 0; i < EB_VIEWPORT_PAD_TOP; i++)
            swirl_window_hdma_buffer[i] = top_val;''','''        for (int i = 0; i < EB_VIEWPORT_PAD_TOP; i++) {
            swirl_window_hdma_buffer[i] = top_val;
            swirl_window2_hdma_buffer[i] = swirl_window2_hdma_buffer[EB_VIEWPORT_PAD_TOP];
        }''')
    replace('''        for (int i = last + 1; i < EB_VIEWPORT_HEIGHT; i++)
            swirl_window_hdma_buffer[i] = bot_val;''','''        for (int i = last + 1; i < EB_VIEWPORT_HEIGHT; i++) {
            swirl_window_hdma_buffer[i] = bot_val;
            swirl_window2_hdma_buffer[i] = swirl_window2_hdma_buffer[last];
        }''')
    replace('''static void generate_oval_window_data(int16_t centre_x, int16_t centre_y,
                                       uint16_t half_width, uint16_t half_height) {''','''static void generate_oval_window_data(int16_t centre_x, int16_t centre_y,
                                       uint16_t half_width, uint16_t half_height) {
    swirl_window2_enabled = false;''')
    replace('''        ppu.wh1_table[i] = packed & 0xFF;         /* right */
    }
    ppu.window_hdma_active = true;
}''','''        ppu.wh1_table[i] = packed & 0xFF;         /* right */
        uint16_t second = swirl_window2_hdma_buffer[i];
        ppu.wh2_table[i] = (second >> 8) & 0xFF;
        ppu.wh3_table[i] = second & 0xFF;
    }
    ppu.window_hdma_active = true;
    ppu.window2_hdma_active = swirl_window2_enabled;
}

/* F6 excludes per-scanline caches. Reconstruct the current already-consumed
 * frame from the serialized cursor without advancing timing or frame state. */
static void rebuild_active_swirl_window_cache(void) {
    if (!frames_until_next_swirl_update || !ppu.window_hdma_active)
        return;
    if (loaded_oval_window) {
        generate_oval_window_data(loaded_oval_window_centre_x,
            loaded_oval_window_centre_y, (loaded_oval_window_width >> 8) & 0xFF,
            (loaded_oval_window_height >> 8) & 0xFF);
        apply_hdma_to_ppu();
        return;
    }
    int id = swirl_reversed ? swirl_hdma_table_id : swirl_hdma_table_id - 1;
    if (id >= 0 && id < SWIRL_DATA_COUNT) {
        const uint8_t *data = ASSET_DATA(ASSET_SWIRLS(id));
        size_t size = ASSET_SIZE(ASSET_SWIRLS(id));
        if (data && size >= 2) {
            parse_hdma_to_window_buffer(data, size);
            apply_hdma_to_ppu();
        }
    }
}''')
    if s.count('ppu.window_hdma_active = false;')!=3:raise ValueError('HDMA stop boundaries changed')
    s=s.replace('ppu.window_hdma_active = false;','ppu.window_hdma_active = false;\n    ppu.window2_hdma_active = false;')
    source.write_bytes(s.replace('\n',newline).encode('utf-8'))
    result=dict(toolSha256=sha(__file__),baselineSourceSha256=hashlib.sha256(baseline).hexdigest(),candidateSourceSha256=sha(source),candidateImporterSha256=sha(module),candidateBuilderSha256=sha(builder),sharedSourceModified=False,sharedBuildModified=False,ownerWrites=False)
    (a.scratch/'preparation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
