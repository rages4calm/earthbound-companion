# SPDX-License-Identifier: GPL-3.0-or-later
"""Execute original and pinned Redux menu/width code from explicit local ROMs.

Reassembly identifies complete byte-equal original routines, never supplies
the CPU reference. Only an own caller is installed in isolated emulator memory.
No ROM/font/game payload is bundled or written back to the local input files.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

from check_jev_observer_parity import local_scratch
import snes_position_arithmetic_oracle as mapping


REDUX_SHA = 'c2a2fc98c7e6518b797959ffadf24ca4db8b4d7745ed3a9eb92eee106db1d0ab'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def identify(a, out, rom, redux):
    saved = mapping.ROUTINES
    mapping.ROUTINES = (
        ('MULT168', 'system/math/mult168.asm', 'far'),
        ('ASL32', 'system/math/asl32.asm', 'far'),
    )
    try:
        globals_, known, evidence = mapping.identify(a, out, rom)
    finally:
        mapping.ROUTINES = saved
    folder = out / 'source-mapping'
    include = ['--cpu', '65816', '-D', 'USA', '-I', folder / 'include-overlay',
               '-I', a.native_source / 'include', '-I', a.native_source / 'asm']
    prelude = (folder / 'movement_speeds.asm').read_text(encoding='utf-8').split('.SEGMENT "CODE"')[0]
    basecfg = (folder / 'code.cfg').read_text(encoding='utf-8')
    # The source entry label is explicitly exported; its offset is then applied
    # to the complete uniquely byte-equal ASL32 body, not guessed from bytes.
    source = folder / 'asl32-entry.asm'
    source.write_text(prelude + '.A16\n.I16\n.EXPORT ASL32, ASL32_ENTRY2\n.SEGMENT "CODE"\n.INCLUDE "system/math/asl32.asm"\n', encoding='utf-8')
    obj = source.with_suffix('.o'); blob = source.with_suffix('.bin')
    mapping.run([a.ca65, *include, source, '-o', obj], source.with_suffix('.compile.log'))
    mapping.run([a.ld65, '-C', folder / 'code.cfg', '-o', blob, '-Ln', source.with_suffix('.lbl'), obj], source.with_suffix('.link.log'))
    labels = mapping.labels(source.with_suffix('.lbl'))
    if mapping.find_unique(rom, blob.read_bytes(), 'ASL32') != known['ASL32']:
        raise ValueError('ASL32 export changed complete body identity')
    known['ASL32_ENTRY2'] = known['ASL32'] + labels['ASL32_ENTRY2'] - labels['ASL32']
    # Pinned source explicitly names this source data table address. Verify
    # all five actual pointer records and their mapped bounds in both ROMs.
    known['FONT_PTR_TABLE'] = 0xC3F054
    tables = []
    for mode, image in (('original', rom), ('redux', redux)):
        entries = []
        for i in range(5):
            row = image[0x3F054 + i * 12:0x3F054 + (i + 1) * 12]
            widthptr = int.from_bytes(row[:4], 'little')
            if len(row) != 12 or not 0xC00000 <= widthptr < 0xC00000 + len(image) - 128:
                raise ValueError('Actual font pointer is outside the mapped local image')
            entries.append({'font': i, 'widthPointer': f'{widthptr:06X}',
                            'widthBytesSha256': hashlib.sha256(image[widthptr-0xC00000:widthptr-0xC00000+128]).hexdigest()})
        tables.append({'profile': mode, 'entries': entries})
    for symbol, relative, abi in (
        ('FIND_FIRST_EMPTY_MENU_OPTION', 'text/menu/find_first_empty_menu_option.asm', 'near'),
        ('ADD_MENU_OPTION', 'text/menu/add_menu_option.asm', 'near'),
        ('ADD_POSITIONED_MENU_OPTION', 'text/menu/add_positioned_menu_option.asm', 'near'),
        ('CC_ADD_MENU_OPTION_WITH_CALLBACK', 'text/menu/cc_add_menu_option_with_callback.asm', 'near'),
        ('CC_GATHER_MENU_OPTION_TEXT', 'text/menu/cc_gather_menu_option_text.asm', 'near'),
        ('GET_STRING_PIXEL_WIDTH', 'text/get_string_pixel_width.asm', 'far'),
        ('MEMSET16', 'system/memset16.asm', 'far'),
        ('ADVANCE_VWF_TILE', 'text/vwf/advance_vwf_tile.asm', 'far'),
        ('SET_WINDOW_TEXT_POSITION', 'text/window/set_window_text_position.asm', 'far'),
        ('SET_FOCUS_TEXT_CURSOR', 'text/set_focus_text_cursor.asm', 'far'),
        ('REDIRECT_SET_FOCUS_TEXT_CURSOR', 'text/set_focus_text_cursor_redirect.asm', 'far'),
        ('SET_TEXT_CURSOR_WITH_PIXEL_OFFSET', 'text/set_text_cursor_with_pixel_offset.asm', 'far'),
        ('SET_TEXT_PIXEL_POSITION', 'text/set_text_pixel_position.asm', 'far'),
        ('MULT16', 'system/math/mult16.asm', 'far'),
        ('CLEAR_SPRITE_ATTRIBUTE_BITS', 'misc/clear_sprite_attribute_bits.asm', 'far'),
        ('SET_SPRITE_ATTRIBUTE_BITS', 'misc/set_sprite_attribute_bits.asm', 'far'),
        ('SET_FILE_SELECT_TEXT_HIGHLIGHT', 'text/set_file_select_text_highlight.asm', 'far'),
    ):
        source = folder / (symbol.lower() + '.asm')
        near_names = {'FIND_FIRST_EMPTY_MENU_OPTION', 'ADD_MENU_OPTION', 'ADD_POSITIONED_MENU_OPTION', 'CC_GATHER_MENU_OPTION_TEXT', 'CC_ADD_MENU_OPTION_WITH_CALLBACK'}
        source.write_text(prelude + ''.join(f'{n} := ${v & 65535 if n in near_names else v:06X}\n' for n, v in known.items()) +
                          '.A16\n.I16\n.EXPORT ' + symbol + '\n.SEGMENT "CODE"\n.INCLUDE "' + relative + '"\n', encoding='utf-8')
        obj = source.with_suffix('.o'); blob = source.with_suffix('.bin')
        mapping.run([a.ca65, *include, source, '-o', obj, '-l', source.with_suffix('.lst')], source.with_suffix('.compile.log'))
        mapping.run([a.ld65, '-C', folder / 'code.cfg', '-o', blob, obj], source.with_suffix('.link.log'))
        raw = blob.read_bytes(); reloc = set()
        for delta in (1, 256):
            cfg = source.with_suffix(f'.shift{delta}.cfg')
            cfg.write_text(basecfg.replace('start=$C00000', f'start=${0xC00000+delta:06X}'), encoding='utf-8')
            shifted = source.with_suffix(f'.shift{delta}.bin')
            mapping.run([a.ld65, '-C', cfg, '-o', shifted, obj], cfg.with_suffix('.log'))
            reloc.update(i for i, (x, y) in enumerate(zip(raw, shifted.read_bytes())) if x != y)
        pattern = b''.join(b'.' if i in reloc else re.escape(bytes((x,))) for i, x in enumerate(raw))
        hits = list(re.finditer(pattern, rom, re.S))
        if len(hits) != 1:
            raise ValueError(symbol + ': complete original body candidate not unique')
        address = hits[0].start() + 0xC00000
        cfg = source.with_suffix('.located.cfg')
        cfg.write_text(basecfg.replace('start=$C00000', f'start=${address:06X}'), encoding='utf-8')
        mapping.run([a.ld65, '-C', cfg, '-o', blob, '-Ln', source.with_suffix('.lbl'), obj], cfg.with_suffix('.log'))
        raw = blob.read_bytes()
        if raw != rom[address-0xC00000:address-0xC00000+len(raw)]:
            raise ValueError(symbol + ': unmasked relocated complete source body differs')
        known[symbol] = address
        evidence.append({'symbol': symbol, 'address': f'{address:06X}', 'abi': abi,
                         'originalSource': relative, 'byteEqualLength': len(raw), 'byteEqualSha256': sha(blob),
                         'pinnedReduxBodyUnchanged': raw == redux[address-0xC00000:address-0xC00000+len(raw)]})
    # Translate only the source wrapper/helper into a private identification
    # assembly. Every instruction must equal the complete actual Redux body.
    edge = folder / 'get_window_right_edge_x.asm'
    edge.write_text('.A16\n.I16\n.SEGMENT "CODE"\nREP #$31\nPHD\nPHA\nTDC\nADC #$FFEE\nTCD\nPLA\nTAX\nLDA a:$000A,X\nASL\nASL\nASL\nSEC\nSBC #1\nPLD\nRTL\n', encoding='utf-8')
    mapping.run([a.ca65, '--cpu', '65816', edge, '-o', edge.with_suffix('.o')], edge.with_suffix('.compile.log'))
    mapping.run([a.ld65, '-C', folder / 'code.cfg', '-o', edge.with_suffix('.bin'), edge.with_suffix('.o')], edge.with_suffix('.link.log'))
    raw = edge.with_suffix('.bin').read_bytes(); address = mapping.find_unique(redux, raw, 'GetWindowRightEdgeX')
    if address != 0xFC283C or len(raw) != 23:
        raise ValueError('Review changed pinned source wrapper/helper identity')
    known['GetWindowRightEdgeX'] = address
    evidence.append({'symbol': 'GetWindowRightEdgeX', 'address': f'{address:06X}',
                     'pinnedSource': 'ccscript/essential/cc_load_two_str.ccs', 'byteEqualLength': len(raw), 'byteEqualSha256': sha(edge.with_suffix('.bin'))})
    # Gate the overwritten entry jump as well as the unchanged surrounding
    # frame and continuation before executing the pinned dispatch.
    gather = known['CC_GATHER_MENU_OPTION_TEXT']
    if gather != 0xC17889 or redux[0x17893:0x17897] != bytes.fromhex('5cf629fc'):
        raise ValueError('Pinned dispatcher hook does not match exact active source')
    if redux[0x43C20:0x43C22] != bytes.fromhex('6400') or redux[0x43C59:0x43C5D] != bytes.fromhex('5c1156fc'):
        raise ValueError('Pinned font-aware highlight hooks changed')
    return globals_, known, evidence, tables


def corpus():
    cases = []
    for font in range(5):
        for padding in (0, 1, 2):
            for text in ('42', '7', '123456', 'Choice', 'iiii', 'MMMM', 'It is', 'Yes', 'No'):
                for cap in (1, 2, 30, 65535):
                    cases.append({'kind': 'width', 'font': font, 'padding': padding, 'force': 0, 'text': text, 'cap': cap})
    for font in range(5):
        cases.append({'kind': 'width', 'font': font, 'padding': 1, 'force': 1, 'text': 'MMMM', 'cap': 65535})
    for width in (1, 6, 16, 22, 30, 32, 64, 8191, 8192):
        cases.append({'kind': 'edge', 'width': width})
    for position in (1, 7, 8, 13, 127, 163, 175, 176, 255):
        for tile in (0, 2, 50, 51):
            for row in (0, 2):
                cases.append({'kind': 'position', 'position': position, 'tile': tile, 'row': row})
    for left in ('Yes', 'No', 'Choice'):
        for term in (1, 2, 3, 4):
            cases.append({'kind': 'menu', 'left': left, 'right': '42', 'term': term, 'callback': 0x00300080})
    for font in range(5):
        for text in ('Choice', 'iiii', 'MMMM', 'It is', 'Yes', 'No'):
            for enabled in (0, 1):
                cases.append({'kind': 'highlight', 'font': font, 'text': text, 'enabled': enabled})
    return cases


def machine(a, out, rom_path, globals_, known, cases, redux):
    out.mkdir(); samples = out / 'samples.jsonl'
    # Our near caller is in C1 so original source near RTS routines execute
    # without any changed original instruction or replaced callee. DP1000;
    # source 32-bit stack arguments live at caller DP+14/+18 by macros.asm.
    code = bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
    entry = 0xC1FE00 + len(code)
    code += bytes.fromhex('af00717e')
    branches = []
    for kind in range(5):
        code += bytes((0xC9, kind, 0, 0xF0, 0)); branches.append(len(code)-1)
    code.append(0)
    starts = []; jumps = []
    starts.append(0xC1FE00 + len(code))
    code += bytes.fromhex('af02717e22') + known['GET_STRING_PIXEL_WIDTH'].to_bytes(3, 'little')
    code += bytes.fromhex('8f00707e4c0000'); jumps.append(len(code)-2)
    starts.append(0xC1FE00 + len(code))
    code += bytes.fromhex('a9') + (globals_['WINDOW_STATS'] & 65535).to_bytes(2, 'little')
    if redux:
        code += bytes((0x22,)) + known['GetWindowRightEdgeX'].to_bytes(3, 'little')
    else:
        code += bytes.fromhex('a9ffff')  # sentinel: no original edge adapter
    code += bytes.fromhex('8f00707e4c0000'); jumps.append(len(code)-2)
    starts.append(0xC1FE00 + len(code))
    code += bytes.fromhex('af04717eaa20') + (known['CC_GATHER_MENU_OPTION_TEXT'] & 65535).to_bytes(2, 'little')
    jsr_operand = 0xC1FE00 + len(code)-2
    code += bytes.fromhex('8f00707e4c0000'); jumps.append(len(code)-2)
    starts.append(0xC1FE00 + len(code))
    code += bytes.fromhex('af04717eaaa9ffff22') + known['SET_FILE_SELECT_TEXT_HIGHLIGHT'].to_bytes(3, 'little')
    code += bytes.fromhex('8f00707e4c0000'); jumps.append(len(code)-2)
    starts.append(0xC1FE00 + len(code))
    code += bytes.fromhex('af04717eaaaf02717e22') + known['SET_TEXT_PIXEL_POSITION'].to_bytes(3, 'little')
    code += bytes.fromhex('8f00707e4c0000'); jumps.append(len(code)-2)
    finish = 0xC1FE00 + len(code)
    code += bytes.fromhex('7b8f08707e3b8f0a707e')
    sampled = 0xC1FE00 + len(code)
    code += bytes((0x4C, entry & 255, (entry >> 8) & 255))
    for branch, start in zip(branches, starts):
        diff = start - (0xC1FE00 + branch + 1)
        if not -128 <= diff <= 127:
            raise ValueError('Own caller branch exceeds range')
        code[branch] = diff & 255
    for at in jumps:
        code[at:at+2] = (finish & 65535).to_bytes(2, 'little')
    filtered = [c for c in cases if redux or (c['kind'] != 'edge' and (c['kind'] != 'menu' or c['term'] < 3))]
    w = lambda name: globals_[name] & 65535
    lua = ['local output=assert(io.open(' + json.dumps(samples.as_posix()) + ',"wb"))',
           'local cases=' + re.sub(r'"(\w+)":', r'\1=', json.dumps(filtered)).replace('[', '{').replace(']', '}'),
           'local mem=emu.memType.snesWorkRam;local prg=emu.memType.snesPrgRom',
           'local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256)%256,mem) end',
           'local function w32(a,v) w16(a,v%65536);w16(a+2,math.floor(v/65536)) end',
           'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end',
           'local function r32(a) return r16(a)+65536*r16(a+2) end',
           'local index=0;local byteindex=1;local stream={};local nextfn=0;local active=nil;local counts={width=0,edge=0,menu=0,position=0,highlight=0};local helpercalls={};w16(0x7400,0x55aa)',
           'local function str(a,s) for i=1,#s do emu.write(a+i-1,string.byte(s,i)+0x30,mem) end;emu.write(a+#s,0,mem) end',
           'local function begin(c)',
           f' for n=0,81 do emu.write({w("WINDOW_STATS")}+n,0,mem) end;for n=0,45*32-1 do emu.write({w("MENU_OPTIONS")}+n,0,mem) end',
           f' w16({w("CURRENT_FOCUS_WINDOW")},0);w16({w("OPEN_WINDOW_TABLE")},0);w16({w("WINDOW_HEAD")},0);w16({w("WINDOW_STATS")}+2,65535);w16({w("WINDOW_STATS")}+4,0);w16({w("WINDOW_STATS")}+10,c.width or 22);w16({w("WINDOW_STATS")}+12,6);w16({w("WINDOW_STATS")}+21,c.font or 0);w16({w("WINDOW_STATS")}+43,65535);w16({w("WINDOW_STATS")}+45,65535)',
           f' emu.write({w("CHARACTER_PADDING")},c.padding or 1,mem);emu.write({w("FORCE_NORMAL_FONT_FOR_LENGTH_CALCULATIONS")},c.force or 0,mem);w16({w("CC_ARGUMENT_GATHERING_LOOP_COUNTER")},0)',
           ' for n=0x122,0x210 do emu.write(n,0,mem) end;for n=0x720,0x74a do emu.write(n,0,mem) end',
           f' w16({w("VWF_TILE")},c.tile or 0);w16({w("VWF_X")},0);w16({w("NEW_TEXT_PIXEL_OFFSET")},0);w16({w("LAST_TEXT_PIXEL_OFFSET_SET")},0);w16({w("TEXT_RENDER_STATE")},0);w16({w("TEXT_RENDER_STATE")}+2,0)',
           ' if c.kind=="width" then str(0x7300,c.text);w32(0x100e,0x7e7300);w16(0x7102,c.cap)',
           ' elseif c.kind=="position" then w16(0x7102,c.position);w16(0x7104,c.row)',
           f' elseif c.kind=="highlight" then str(0x7300,c.text);w32(0x100e,0x7e7300);w16(0x7104,c.enabled);w16({w("CURRENT_FOCUS_WINDOW")},0x24);w16({w("OPEN_WINDOW_TABLE")}+0x48,0);emu.write({w("OPEN_WINDOW_TABLE")}+0x24,0,mem);w16({w("WINDOW_STATS")}+4,0x24);w16({w("WINDOW_STATS")}+14,1);w16({w("WINDOW_STATS")}+19,0x1800);w16({w("WINDOW_STATS")}+53,0x7600);for n=0,22*12-1 do w16(0x7600+n*2,c.enabled==0 and 0x1841 or 65) end',
           ' elseif c.kind=="menu" then stream={};for i=1,#c.left do stream[#stream+1]=string.byte(c.left,i)+0x30 end;stream[#stream+1]=c.term;if c.term>=3 then for i=1,#c.right do stream[#stream+1]=string.byte(c.right,i)+0x30 end;stream[#stream+1]=0 end;if c.term==1 or c.term==3 then for i=0,3 do stream[#stream+1]=math.floor(c.callback/256^i)%256 end end;byteindex=1;nextfn=' + str(known['CC_GATHER_MENU_OPTION_TEXT'] & 65535),
           ' end end',
           'emu.addMemoryCallback(function()',
           ' if not active then index=index+1;active=assert(cases[index]);begin(active) end;local c=active;w16(0x7100,c.kind=="width" and 0 or c.kind=="edge" and 1 or c.kind=="menu" and 2 or c.kind=="highlight" and 3 or 4)',
           f' if c.kind=="menu" then w16(0x7104,stream[byteindex]);emu.write({jsr_operand-0xC00000},nextfn%256,prg);emu.write({jsr_operand-0xC00000+1},math.floor(nextfn/256),prg) end',
           f'end,emu.callbackType.exec,{entry})']
    for symbol in ('GET_STRING_PIXEL_WIDTH', 'ADD_MENU_OPTION', 'CC_GATHER_MENU_OPTION_TEXT', 'CC_ADD_MENU_OPTION_WITH_CALLBACK', 'SET_TEXT_PIXEL_POSITION', 'SET_FILE_SELECT_TEXT_HIGHLIGHT') + (('GetWindowRightEdgeX',) if redux else ()):
        lua.append(f'helpercalls.{symbol}=0;emu.addMemoryCallback(function() helpercalls.{symbol}=helpercalls.{symbol}+1 end,emu.callbackType.exec,{known[symbol]})')
    lua += [
           'emu.addMemoryCallback(function()',
           ' assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"source frame corrupted");assert(r16(0x7400)==0x55aa,"protected RAM corrupted");local c=active;local value=r16(0x7000)',
           ' if c.kind=="menu" and byteindex<#stream then assert(value~=0,"early native menu completion");nextfn=value;byteindex=byteindex+1;return end',
           ' counts[c.kind]=counts[c.kind]+1',
           f' if c.kind=="menu" then assert(value==0,"menu continuation not finished");local b={w("MENU_OPTIONS")};local label="";for n=0,24 do local v=emu.read(b+19+n,mem);if v==0 then break end;label=label..string.char(v) end;output:write(string.format("[%d,2,%d,%d,%d,%d,%d,%d,%d,%d]\\n",index,r16(b),r16(b+6),emu.read(b+14,mem),r32(b+15),r16(b+8),r16(b+10),#label,r16(0x126)))',
           f' elseif c.kind=="position" then output:write(string.format("[%d,3,%d,%d,%d,%d,%d,%d,%d]\\n",index,r16({w("WINDOW_STATS")}+14),r16({w("WINDOW_STATS")}+16),r16({w("VWF_X")}),r16({w("VWF_TILE")}),emu.read({w("LAST_TEXT_PIXEL_OFFSET_SET")},mem),r16({w("TEXT_RENDER_STATE")}),r16({w("TEXT_RENDER_STATE")}+2)))',
           ' elseif c.kind=="highlight" then output:write(string.format("[%d,4,[",index));for n=0,43 do if n>0 then output:write(",") end;output:write(r16(0x7600+n*2)) end;output:write("]]\\n")',
           ' else output:write(string.format("[%d,%d,%d]\\n",index,c.kind=="width" and 0 or 1,value)) end;active=nil',
           ' if index==#cases then assert(helpercalls.GET_STRING_PIXEL_WIDTH==counts.width and helpercalls.ADD_MENU_OPTION==counts.menu and helpercalls.SET_TEXT_PIXEL_POSITION==counts.position and helpercalls.SET_FILE_SELECT_TEXT_HIGHLIGHT==counts.highlight,"actual source call count differs");if helpercalls.GetWindowRightEdgeX then assert(helpercalls.GetWindowRightEdgeX==counts.edge,"actual edge call count differs") end;output:flush();output:close();emu.log("MENU_TEXT_CORPUS_COMPLETE "..index.." width="..counts.width.." edge="..counts.edge.." menu="..counts.menu.." position="..counts.position.." highlight="..counts.highlight);for name,value in pairs(helpercalls) do emu.log("HELPER_CALLS "..name.." "..value) end;emu.breakExecution() end',
           f'end,emu.callbackType.exec,{sampled})']
    script = out / 'menu.lua'; script.write_text('\n'.join(lua) + '\n', encoding='utf-8')
    result = subprocess.run([str(a.oracle), str(rom_path), '--home', str(out / 'oracle-home'), '--frames', '10000', '--timeout', '60', '--lua-timeout', '10', '--lua-allow-io', '--lua', str(script), '--write-memory', 'SnesPrgRom:0x1fe00:' + code.hex(), '--set-pc', '0xc1fe00', '--cpu', 'Snes'], capture_output=True, timeout=70)
    (out / 'oracle.jsonl').write_bytes(result.stdout); (out / 'oracle.stderr').write_bytes(result.stderr)
    logs = [json.loads(line) for line in result.stdout.decode().splitlines()]
    if result.returncode or not logs[-1].get('ok') or logs[-1].get('reason') != 'debugger_break' or any(r.get('error_count', 0) for r in logs):
        raise RuntimeError('Actual menu CPU corpus did not complete; inspect private oracle logs')
    if sum('MENU_TEXT_CORPUS_COMPLETE ' in r.get('text', '') for r in logs) != 1:
        raise RuntimeError('Machine completion marker missing/duplicated')
    rows = [json.loads(line) for line in samples.read_text(encoding='utf-8').splitlines()]
    if [r[0] for r in rows] != list(range(1, len(filtered) + 1)):
        raise RuntimeError('Actual machine corpus incomplete/unordered')
    helpercalls = {name: int(count) for record in logs for name, count in re.findall(r'^HELPER_CALLS (\w+) (\d+)$', record.get('text', ''), re.M)}
    if len(helpercalls) != (7 if redux else 6): raise ValueError('Actual helper call accounting missing')
    return {'profile': 'redux' if redux else 'original', 'cases': filtered, 'results': rows,
            'counts': dict(Counter(c['kind'] for c in filtered)), 'actualHelperCalls': helpercalls, 'stackDirectPageCanariesPassed': True,
            'inputRomSha256': sha(rom_path), 'ownCallerSha256': hashlib.sha256(code).hexdigest(),
            'luaSha256': sha(script), 'samplesSha256': sha(samples)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('rom', 'redux-rom', 'oracle', 'ca65', 'ld65', 'native-source', 'redux-source', 'scratch', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    for name, value in vars(a).items(): setattr(a, name, value.resolve())
    a.scratch = local_scratch(a.scratch)
    if a.scratch.exists() or a.output.exists(): raise ValueError('Fresh scratch/report required')
    rom = a.rom.read_bytes(); redux = a.redux_rom.read_bytes()
    if len(rom) != 0x300000 or hashlib.sha1(rom).hexdigest() != mapping.US_SHA1 or sha(a.redux_rom) != REDUX_SHA:
        raise ValueError('Requires exact clean USA and pinned compiled Redux ROM inputs')
    a.scratch.mkdir(parents=True)
    globals_, known, evidence, tables = identify(a, a.scratch, rom, redux)
    cases = corpus()
    modes = [machine(a, a.scratch / mode, path, globals_, known, cases, isredux)
             for mode, path, isredux in (('original', a.rom, False), ('redux', a.redux_rom, True))]
    if a.rom.read_bytes() != rom or a.redux_rom.read_bytes() != redux:
        raise ValueError('Input ROM changed')
    report = {'format': 'menu-text-actual-cpu-contract-v1', 'completed': True, 'toolSha256': sha(Path(__file__)),
              'sourceMapping': evidence, 'fontTables': tables,
              'globalAddresses': {n: f'{v:06X}' for n, v in globals_.items() if n in ('CURRENT_FOCUS_WINDOW', 'OPEN_WINDOW_TABLE', 'WINDOW_STATS', 'WINDOW_HEAD', 'MENU_OPTIONS', 'CC_ARGUMENT_GATHERING_LOOP_COUNTER', 'TEXT_NEW_MENU_OPTION_BUFFER', 'CHARACTER_PADDING', 'FORCE_NORMAL_FONT_FOR_LENGTH_CALCULATIONS', 'VWF_X', 'VWF_TILE', 'NEW_TEXT_PIXEL_OFFSET', 'LAST_TEXT_PIXEL_OFFSET_SET', 'TEXT_RENDER_STATE')},
              'profiles': modes, 'inputSourceSha256': sha(a.redux_source / 'ccscript/essential/cc_load_two_str.ccs'),
              'inputRomsSourceBuildPackOwnerSavesModified': False,
              'limits': ['Actual untouched original bodies and actual compiled pinned Redux hooks execute from input images; source assembly is only an identity gate.',
                         'Own caller prepares a legal focused source window/menu state and encoded operands; this is not ordinary story control-flow coverage.',
                         'Measures width, interior right edge, complete actual source pixel-position chain, menu defaults, callback continuations and font-aware highlight set/clear. Does not execute full SNES glyph raster, hover target, selection audio or phone/cold save.',
                         'Highlight fixtures supply both Original word-indexed and pinned Redux byte-indexed existence entries for focused window36, matching expand_text_windows.ccs prerequisites.',
                         'Boundary widths8191/8192 and forced-font contexts characterize source API operations, not proven ordinary story reachability.']}
    a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps([(m['profile'], m['counts']) for m in modes]))


if __name__ == '__main__': main()
