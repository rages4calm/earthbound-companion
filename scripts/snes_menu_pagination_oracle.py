# SPDX-License-Identifier: GPL-3.0-or-later
"""Run complete original/pinned menu-layout code from explicit local ROMs.

Source reassembly is an identity/ABI gate, never the CPU reference. Only our
caller is installed in isolated emulator memory. No ROM/data payload is bundled.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

from check_jev_observer_parity import local_scratch
import snes_menu_text_oracle as menu
import snes_position_arithmetic_oracle as mapping


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identify(a, out, rom, redux):
    globals_, known, evidence, _ = menu.identify(a, out, rom, redux)
    folder = out / 'source-mapping'
    prelude = (folder / 'movement_speeds.asm').read_text(encoding='utf-8').split('.SEGMENT "CODE"')[0]
    cfgtext = (folder / 'code.cfg').read_text(encoding='utf-8')
    include = ['--cpu', '65816', '-D', 'USA', '-I', folder / 'include-overlay',
               '-I', a.native_source / 'include', '-I', a.native_source / 'asm']
    overflow = (a.native_source / 'asm/data/text/menu_overflow_text.asm').read_text(encoding='utf-8')
    values = [int(v, 16) for v in re.findall(r'\$([0-9A-Fa-f]{2})', overflow)]
    known['MENU_OVERFLOW_TEXT'] = mapping.find_unique(rom, bytes(values), 'MENU_OVERFLOW_TEXT')
    near = {'FIND_FIRST_EMPTY_MENU_OPTION', 'ADD_MENU_OPTION', 'ADD_POSITIONED_MENU_OPTION',
            'CC_GATHER_MENU_OPTION_TEXT', 'CC_ADD_MENU_OPTION_WITH_CALLBACK',
            'COUNT_MENU_OPTION_CHAIN', 'ADD_MENU_ITEM'}
    routines = (
        ('DIVISION16S', 'system/math/division16s.asm', 'far'),
        ('COUNT_MENU_OPTION_CHAIN', 'text/menu/count_menu_option_chain.asm', 'near'),
        ('COUNT_MENU_OPTION_CHAIN_FAR', 'text/menu/count_menu_option_chain_redirect.asm', 'far'),
        ('ADD_MENU_ITEM', 'text/menu/add_menu_item.asm', 'near'),
        ('ADD_MENU_ITEM_FAR', 'text/menu/add_menu_item_far.asm', 'far'),
        ('LAYOUT_MENU_OPTIONS', 'text/menu/layout_menu_options.asm', 'far'),
    )
    for name, relative, abi in routines:
        source = folder / (name.lower() + '-pagination.asm')
        extra = ', DIVISION16S_DIVISOR_POSITIVE' if name == 'DIVISION16S' else ''
        source.write_text(prelude + ''.join(f'{n} := ${v & 65535 if n in near else v:06X}\n' for n, v in known.items()) +
                          '.A16\n.I16\n.EXPORT ' + name + extra + '\n.SEGMENT "CODE"\n.INCLUDE "' + relative + '"\n', encoding='utf-8')
        obj = source.with_suffix('.o'); blob = source.with_suffix('.bin')
        mapping.run([a.ca65, *include, source, '-o', obj], source.with_suffix('.compile.log'))
        mapping.run([a.ld65, '-C', folder / 'code.cfg', '-o', blob, obj], source.with_suffix('.link.log'))
        raw = blob.read_bytes(); reloc = set()
        for delta in (1, 256):
            cfg = source.with_suffix(f'.shift{delta}.cfg')
            cfg.write_text(cfgtext.replace('start=$C00000', f'start=${0xC00000+delta:06X}'), encoding='utf-8')
            shifted = source.with_suffix(f'.shift{delta}.bin')
            mapping.run([a.ld65, '-C', cfg, '-o', shifted, obj], cfg.with_suffix('.log'))
            reloc.update(i for i, (x, y) in enumerate(zip(raw, shifted.read_bytes())) if x != y)
        pattern = b''.join(b'.' if i in reloc else re.escape(bytes((x,))) for i, x in enumerate(raw))
        hits = list(re.finditer(pattern, rom, re.S))
        if name == 'ADD_MENU_ITEM_FAR' and len(hits) > 1:
            # The clean image has a retained duplicate identical wrapper.
            # Resolve which alias is active from complete caller-body matching,
            # rather than claiming the wrapper bytes are unique.
            known['_ADD_MENU_ITEM_FAR_ALTERNATE'] = hits[1].start() + 0xC00000
        if name == 'LAYOUT_MENU_OPTIONS' and not hits and '_ADD_MENU_ITEM_FAR_ALTERNATE' in known:
            old = known['ADD_MENU_ITEM_FAR'];new = known['_ADD_MENU_ITEM_FAR_ALTERNATE']
            text = source.read_text(encoding='utf-8').replace(f'ADD_MENU_ITEM_FAR := ${old:06X}', f'ADD_MENU_ITEM_FAR := ${new:06X}')
            source.write_text(text,encoding='utf-8');known['ADD_MENU_ITEM_FAR']=new
            mapping.run([a.ca65,*include,source,'-o',obj],source.with_suffix('.compile.log'))
            mapping.run([a.ld65,'-C',folder/'code.cfg','-o',blob,obj],source.with_suffix('.link.log'))
            raw=blob.read_bytes()
            pattern=b''.join(b'.'if i in reloc else re.escape(bytes((x,)))for i,x in enumerate(raw))
            hits=list(re.finditer(pattern,rom,re.S))
        if len(hits) != 1 and name != 'ADD_MENU_ITEM_FAR':
            raise ValueError(name + ': full source body candidate is not unique')
        address = hits[0].start() + 0xC00000
        cfg = source.with_suffix('.located.cfg')
        cfg.write_text(cfgtext.replace('start=$C00000', f'start=${address:06X}'), encoding='utf-8')
        mapping.run([a.ld65, '-C', cfg, '-o', blob, '-Ln', source.with_suffix('.lbl'), obj], cfg.with_suffix('.log'))
        raw = blob.read_bytes()
        if raw != rom[address-0xC00000:address-0xC00000+len(raw)]:
            raise ValueError(name + ': full unmasked relocated body differs')
        known[name] = address
        if name == 'DIVISION16S':
            labels = mapping.labels(source.with_suffix('.lbl'))
            known['DIVISION16S_DIVISOR_POSITIVE'] = address + labels['DIVISION16S_DIVISOR_POSITIVE'] - labels[name]
        evidence.append({'symbol': name, 'address': f'{address:06X}', 'abi': abi,
                         'source': relative, 'byteEqualLength': len(raw), 'byteEqualSha256': sha(blob),
                         'pinnedReduxBodyUnchanged': raw == redux[address-0xC00000:address-0xC00000+len(raw)],
                         'identicalBodyAddresses':[f'{m.start()+0xC00000:06X}'for m in hits]})
    return globals_, known, evidence


def corpus():
    cases = []
    # Actual source windows store config height minus two. Their capacity is
    # 24 menu records; reserve one for overflow when paginated.
    for height in (4, 6, 8, 10, 12, 14, 16, 18, 20, 28):
        rows = (height - 2) // 2
        for columns in (1, 2, 3):
            counts = sorted({1, columns, max(1, rows*columns-1), rows*columns,
                             min(23, rows*columns+1), 14, 15, 23})
            for count in counts:
                if count > 23 or ((count+columns-1)//columns > rows and rows <= 2):
                    continue  # Source reserve-two-rows loop would be invalid.
                cases.append({'height': height, 'width': 16 if height == 28 else 24, 'columns': columns,
                              'count': count, 'textY': 0})
    return cases


def machine(a, out, path, globals_, known, cases):
    out.mkdir(); samples = out / 'samples.jsonl'
    code = bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
    entry = 0xC1FE00 + len(code)
    code += bytes.fromhex('af00717ea20000a0000022') + known['LAYOUT_MENU_OPTIONS'].to_bytes(3, 'little')
    code += bytes.fromhex('7b8f08707e3b8f0a707e')
    sampled = 0xC1FE00 + len(code)
    code += bytes((0x4C, entry & 255, (entry >> 8) & 255))
    w = lambda name: globals_[name] & 65535
    lua = [
        'local output=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))',
        'local cases='+re.sub(r'"(\w+)":', r'\1=', json.dumps(cases)).replace('[','{').replace(']','}'),
        'local mem=emu.memType.snesWorkRam',
        'local function w16(a,v) emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256)%256,mem) end',
        'local function r16(a) return emu.read(a,mem)+256*emu.read(a+1,mem) end',
        'local index=0;local layouts=0;local chains=0;w16(0x7a00,0x55aa)',
        f'emu.addMemoryCallback(function() layouts=layouts+1 end,emu.callbackType.exec,{known["LAYOUT_MENU_OPTIONS"]})',
        f'emu.addMemoryCallback(function() chains=chains+1 end,emu.callbackType.exec,{known["COUNT_MENU_OPTION_CHAIN_FAR"]})',
        'emu.addMemoryCallback(function()',
        ' index=index+1;local c=assert(cases[index]);w16(0x7100,c.columns)',
        f' for n=0,81 do emu.write({w("WINDOW_STATS")}+n,0,mem) end;for n=0,45*24-1 do emu.write({w("MENU_OPTIONS")}+n,0,mem) end',
        f' w16({w("CURRENT_FOCUS_WINDOW")},0);w16({w("OPEN_WINDOW_TABLE")},0);w16({w("WINDOW_HEAD")},0)',
        f' local s={w("WINDOW_STATS")};w16(s+10,c.width-2);w16(s+12,c.height-2);w16(s+16,c.textY);w16(s+43,0);w16(s+45,c.count-1);w16(s+47,65535);w16(s+51,1)',
        f' for i=0,c.count-1 do local b={w("MENU_OPTIONS")}+45*i;w16(b,1);w16(b+2,i==c.count-1 and 65535 or i+1);w16(b+4,i==0 and 65535 or i-1);w16(b+6,1);w16(b+12,i+1);emu.write(b+14,1,mem);emu.write(b+19,0x71,mem);emu.write(b+20,0,mem) end',
        f' emu.write({w("FORCE_LEFT_TEXT_ALIGNMENT")},0,mem)',
        f'end,emu.callbackType.exec,{entry})',
        'emu.addMemoryCallback(function()',
        ' assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"source frame changed");assert(r16(0x7a00)==0x55aa,"source canary changed")',
        f' local c=cases[index];local last=r16({w("WINDOW_STATS")}+45);output:write(string.format("[%d,%d,[",index,last+1));for i=0,last do if i>0 then output:write(",") end;local b={w("MENU_OPTIONS")}+45*i;output:write(string.format("[%d,%d,%d,%d]",r16(b+8),r16(b+10),r16(b+6),r16(b))) end;output:write("]]\\n")',
        ' if index==#cases then assert(layouts==#cases and chains==2*#cases,"source helper calls missing");output:flush();output:close();emu.log("MENU_LAYOUT_CORPUS_COMPLETE "..index.." layouts="..layouts.." chains="..chains);emu.breakExecution() end',
        f'end,emu.callbackType.exec,{sampled})'
    ]
    script = out/'layout.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
    result = subprocess.run([str(a.oracle),str(path),'--home',str(out/'oracle-home'),'--frames','10000','--timeout','60','--lua-timeout','10','--lua-allow-io','--lua',str(script),'--write-memory','SnesPrgRom:0x1fe00:'+code.hex(),'--set-pc','0xc1fe00','--cpu','Snes'],capture_output=True,timeout=70)
    (out/'oracle.jsonl').write_bytes(result.stdout);(out/'oracle.stderr').write_bytes(result.stderr)
    logs=[json.loads(line)for line in result.stdout.decode().splitlines()]
    if result.returncode or not logs[-1].get('ok') or logs[-1].get('reason')!='debugger_break' or any(r.get('error_count',0)for r in logs):
        raise ValueError('Source layout CPU failed; inspect private logs')
    if sum('MENU_LAYOUT_CORPUS_COMPLETE 'in r.get('text','')for r in logs)!=1:
        raise ValueError('Source completion marker missing')
    rows=[json.loads(line)for line in samples.read_text(encoding='utf-8').splitlines()]
    if [r[0]for r in rows]!=list(range(1,len(cases)+1)):
        raise ValueError('Source layout case count/order differs')
    return {'inputRomSha256':sha(path),'cases':cases,'results':rows,'count':len(rows),
            'sourceFrameAndProtectedCanariesPassed':True,'actualLayoutCalls':len(cases),
            'actualCountChainCalls':2*len(cases),'ownCallerSha256':hashlib.sha256(code).hexdigest(),
            'luaSha256':sha(script),'samplesSha256':sha(samples)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','redux-rom','oracle','ca65','ld65','native-source','redux-source','scratch','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    for name,value in vars(a).items():setattr(a,name,value.resolve())
    a.scratch=local_scratch(a.scratch)
    if a.scratch.exists()or a.output.exists():raise ValueError('Fresh scratch/report required')
    rom=a.rom.read_bytes();redux=a.redux_rom.read_bytes()
    if len(rom)!=0x300000 or hashlib.sha1(rom).hexdigest()!=mapping.US_SHA1 or sha(a.redux_rom)!=menu.REDUX_SHA:
        raise ValueError('Exact clean USA and pinned compiled Redux inputs required')
    a.scratch.mkdir(parents=True)
    globals_,known,evidence=identify(a,a.scratch,rom,redux)
    cases=corpus();profiles=[]
    for mode,path in (('original',a.rom),('redux',a.redux_rom)):
        profiles.append(dict(profile=mode,**machine(a,a.scratch/mode,path,globals_,known,cases)))
    if a.rom.read_bytes()!=rom or a.redux_rom.read_bytes()!=redux:raise ValueError('Input ROM changed')
    report={'format':'menu-pagination-actual-cpu-v1','completed':True,'toolSha256':sha(Path(__file__)),
            'sourceMapping':evidence,'profiles':profiles,
            'sourceHeightContract':{'createWindow':'asm/text/create_window.asm: config height DEC DEC before stored window height',
                                   'layout':'asm/text/menu/layout_menu_options.asm: stored height LSR; overflow reserves2rows',
                                   'cursor':'asm/battle/find_next_menu_option.asm: stored height LSR cursor bound'},
            'inputRomsOrOwnerSavesModified':False,
            'limits':['Complete original/pinned LAYOUT_MENU_OPTIONS and actual callees execute from local images with own prepared legal window/menu records.',
                      'Fixed-width row/page/overflow contract only; not auto-width labels, complete CREATE_WINDOW execution, all source menu parents, glyph raster or controller hardware.',
                      'Source has24 records. Cases requiring overflow in windows with<=2rows are excluded because reserve-two-rows becomes zero/underflows; native safety controls are tested separately.',
                      'Native outer height must be normalized before comparing with prepared source interior height.']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([(v['profile'],v['count'])for v in profiles]))


if __name__=='__main__':main()
