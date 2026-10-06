# SPDX-License-Identifier: GPL-3.0-or-later
"""Execute actual sprite-render return ABI from untouched private SNES ROMs.

Full source reassembly identifies byte-equal bodies and their live dependencies.
Only an own caller is injected; source routines execute unchanged. Original
sprite data and generated machine samples stay private development inputs.
"""
import argparse, hashlib, json, re, subprocess
from pathlib import Path
import snes_position_arithmetic_oracle as mapping
from check_jev_observer_parity import local_scratch
from build_maternalbound_pack import read_pack
from maternalbound_graphics import asm_pointer, slice_rom
from snes_movement_helpers_oracle import US_SHA1

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()

def identify(a,out,rom):
    mapping.ROUTINES=()
    ram,addresses,proof=mapping.identify(a,out,rom)
    folder=out/'source-mapping';base=(folder/'code.cfg').read_text()
    include=['--cpu','65816','-D','USA','-I',folder/'include-overlay','-I',a.native_source/'include','-I',a.native_source/'asm']
    prelude='.INCLUDE "common.asm"\n.INCLUDE "config.asm"\n.INCLUDE "structs.asm"\n'
    prelude+=''.join(f'.IMPORT {n}: absolute\n' for n in ram if not n.startswith('__'))+'.IMPORT __BSS_START__: absolute\n'
    def body(symbol,relative,extern,aliases):
        source=folder/(symbol.lower()+'.asm');obj=source.with_suffix('.o');blob=source.with_suffix('.bin')
        near={'COPY_TO_VRAM'}
        source.write_text(prelude+''.join(f'.IMPORT {n}: '+('absolute' if n in near else 'far')+'\n' for n in extern)+'.SEGMENT "CODE"\n.A16\n.I16\n.INCLUDE "'+relative+'"\n'+''.join('.EXPORT '+n+'\n' for n in aliases))
        mapping.run([a.ca65,*include,source,'-o',obj,'-l',source.with_suffix('.lst')],source.with_suffix('.compile.log'))
        values={n:0x1122 if n in near else 0xe01122 for n in extern}
        def link(values,start,suffix):
            cfg=folder/(symbol.lower()+'-'+suffix+'.cfg');target=cfg.with_suffix('.bin');labels=cfg.with_suffix('.lbl')
            cfg.write_text(base.replace('start=$C00000',f'start=${start:06X}').replace('SYMBOLS {','SYMBOLS {\n'+''.join(f'{n}:type=export,value=${v:06X};\n' for n,v in values.items())))
            mapping.run([a.ld65,'-C',cfg,'-o',target,'-Ln',labels,obj],cfg.with_suffix('.log'))
            return target.read_bytes(),mapping.labels(labels)
        original,_=link(values,0xc00000,'dummy');mask=set();relocations={}
        for name in (*extern,'__START__'):
            changed=[]
            for delta in (1,256,65536) if name!='__START__' and name not in near else (1,256):
                changed_values=values.copy();start=0xc00000
                if name=='__START__':start+=delta
                else:changed_values[name]+=delta
                altered,_=link(changed_values,start,name.lower()+str(delta))
                positions=[i for i,(x,y) in enumerate(zip(original,altered)) if x!=y]
                if len(original)!=len(altered):raise ValueError('Source relocation changed size')
                mask.update(positions);changed.append((delta,positions))
            relocations[name]=changed
        pattern=b''.join(b'.' if i in mask else re.escape(bytes((v,))) for i,v in enumerate(original))
        found=list(re.finditer(pattern,rom,re.S))
        if len(found)!=1:raise ValueError(symbol+' full source body not unique: '+str(len(found)))
        offset=found[0].start();entry=offset+0xc00000;resolved={}
        for name in extern:
            v=0
            for delta,positions in relocations[name]:
                if not positions:continue
                octets={rom[offset+i] for i in positions}
                if len(octets)!=1:raise ValueError('Source operand relocation aliases disagree: '+name)
                v+=next(iter(octets))*delta
            resolved[name]=v
        actual,labels=link(resolved,entry,'located')
        if actual!=rom[offset:offset+len(actual)]:raise ValueError(symbol+' full body failed exact byte equality')
        blob.write_bytes(actual);addresses.update(resolved);addresses.update({n:labels[n] for n in aliases})
        proof.append({'symbol':symbol,'originalSource':relative,'address':f'{entry:06X}','byteEqualLength':len(actual),'byteEqualSha256':sha(blob),'dependencies':{n:f'{v:06X}' for n,v in resolved.items()},'aliases':{n:f'{labels[n]:06X}' for n in aliases}})
    body('RENDER_ENTITY_SPRITE','overworld/render_entity_sprite.asm',
         ('IS_ENTITY_ON_SCREEN','PREPARE_VRAM_COPY_ROW_SAFE','SPRITE_DIRECTION_MAPPING_4_DIRECTION','BLANK_TILE_DATA'),
         ('RENDER_ENTITY_SPRITE','RENDER_ENTITY_SPRITE_MOVEMENT_ENTRY_1','RENDER_ENTITY_SPRITE_MOVEMENT_ENTRY_2','RENDER_ENTITY_SPRITE_MOVEMENT_ENTRY_3','RENDER_ENTITY_SPRITE_ENTRY4'))
    body('PREPARE_VRAM_COPY_ROW_SAFE','system/dma/prepare_vram_copy_row_safe.asm',('PREPARE_VRAM_COPY_COMMON',),('PREPARE_VRAM_COPY_ROW_SAFE',))
    body('PREPARE_VRAM_COPY','system/prepare_vram_copy.asm',('COPY_TO_VRAM',),('PREPARE_VRAM_COPY_COMMON',))
    body('IS_ENTITY_ON_SCREEN','overworld/is_entity_on_screen.asm',('ENTITY_COLLISION_X_OFFSET','ENTITY_COLLISION_Y_OFFSET'),('IS_ENTITY_ON_SCREEN',))
    return ram,addresses,proof

def sprite(a,profile,rom):
    pack=read_pack(a.original_assets if profile=='Original' else a.redux_assets,Path('native-source/src/data/runtime_generated/asset_ids.h'))[2]
    npc=pack['data/npc_config_table.bin'];id=int.from_bytes(npc[773*17+1:773*17+3],'little')
    ptr=pack['overworld_sprites/sprite_grouping_ptr_table.bin'];data=pack['overworld_sprites/sprite_grouping_data.bin']
    offset=(int.from_bytes(ptr[id*4:id*4+4],'little')&65535)-0x1a7f
    group=data[offset:offset+25];table=asm_pointer(rom,0x1df9)
    raw=int.from_bytes(slice_rom(rom,table+id*4,4),'little');actual=slice_rom(rom,raw,25)
    if actual[:8]!=group[:8]:raise ValueError('Pack and actual source sprite geometry differ')
    if [int.from_bytes(actual[i:i+2],'little')&3 for i in range(9,25,2)]!=[int.from_bytes(group[i:i+2],'little')&3 for i in range(9,25,2)]:raise ValueError('Native/source frame flags differ')
    return {'sprite':id,'groupAddress':raw,'groupOffset':offset,'groupSha256':hashlib.sha256(group).hexdigest().upper(),'sourceGroupSha256':hashlib.sha256(actual).hexdigest().upper(),'pointer':raw+9,'bank':actual[8],'width':(group[1]>>4)*32,'height':group[0],'nativeSourceGeometryAndFrameFlagsEqual':True}

def corpus(info):
    rows=[]
    for method in (1,2,3):
        for direction in (0,1,2,3,4,5,6,7):
            for frame in (0,1):
                for surface in (0,8,12):
                    for vram in (0x4000,0x40f0,0x4100):
                        rows.append({'method':method,'direction':direction,'frame':frame,'surface':surface,'vram':vram,'width':info['width'],'height':info['height'],'onScreen':True})
    # Real source visibility guard on ME1 versus unconditional ME2/ME3.
    for method in (1,2,3):rows.append({'method':method,'direction':2,'frame':1,'surface':0,'vram':0x4000,'width':info['width'],'height':info['height'],'onScreen':False})
    return rows

def machine(a,folder,path,ram,addresses,info,rows):
    folder.mkdir();samples=folder/'samples.jsonl';w=lambda n:ram[n]&65535
    code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
    begin=0xc0ff00+len(code);code+=bytes.fromhex('af00717e');jumps=[];branches=[]
    for method in (1,2,3):code.extend((0xc9,method,0,0xf0,0));branches.append(len(code)-1)
    code.append(0);starts=[]
    for method in (1,2,3):
        starts.append(0xc0ff00+len(code));code.extend((0x22,)+tuple(addresses['RENDER_ENTITY_SPRITE_MOVEMENT_ENTRY_'+str(method)].to_bytes(3,'little')))
        code.extend((0x4c,0,0));jumps.append(len(code)-2)
    finish=0xc0ff00+len(code);code.extend(bytes.fromhex('8f06707e7b8f08707e3b8f0a707e'));end=0xc0ff00+len(code)
    code.extend((0x4c,begin&255,begin>>8&255))
    for at,start in zip(branches,starts):code[at]=(start-(0xc0ff00+at+1))&255
    for at in jumps:code[at:at+2]=(finish&65535).to_bytes(2,'little')
    fields=[('ENTITY_TILE_HEIGHTS','height'),('ENTITY_BYTE_WIDTHS','width'),('ENTITY_VRAM_ADDRESS','vram'),('ENTITY_DIRECTIONS','direction'),('ENTITY_ANIMATION_FRAME','frame'),('ENTITY_SURFACE_FLAGS','surface')]
    values=[[r[n] for n in ('method','direction','frame','surface','vram','width','height','onScreen')] for r in rows]
    lua=['local out=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))','local rows='+json.dumps(values,separators=(',',':')).replace('true','1').replace('false','0').replace('[','{').replace(']','}'),
         'local m=emu.memType.snesWorkRam','local function w16(a,v) emu.write(a,v%256,m);emu.write(a+1,math.floor(v/256)%256,m) end',
         'local function r16(a) return emu.read(a,m)+256*emu.read(a+1,m) end','local index=0;local render=0;local dma=0;w16(0x7200,0x55aa)',
         f'emu.addMemoryCallback(function() index=index+1;local r=assert(rows[index],"past corpus");w16(0x7100,r[1]);w16(0x1088,0);w16({w("CURRENT_ENTITY_SLOT")},0);',
         ''.join(f'w16({w(field)},r[{("method","direction","frame","surface","vram","width","height","onScreen").index(name)+1}]);' for field,name in fields),
         f'w16({w("ENTITY_GRAPHICS_PTR_LOW")},{info["pointer"]&65535});w16({w("ENTITY_GRAPHICS_PTR_HIGH")},{info["pointer"]>>16});w16({w("ENTITY_GRAPHICS_SPRITE_BANK")},{info["bank"]});',
         f'w16({w("ENTITY_SIZES")},0);w16({w("ENTITY_SCREEN_X_TABLE")},r[8]==1 and 128 or 512);w16({w("ENTITY_SCREEN_Y_TABLE")},100);',
         ''.join(f'w16({w(name)},0);' for name in ('DMA_BYTES_COPIED','DMA_QUEUE_INDEX','LAST_COMPLETED_DMA_INDEX','INIDISP_MIRROR')),f'w16({w("ENTITY_CURRENT_DISPLAYED_SPRITES")},0xa55a);end,emu.callbackType.exec,{begin})',
         f'emu.addMemoryCallback(function() render=render+1 end,emu.callbackType.exec,{addresses["RENDER_ENTITY_SPRITE_ENTRY4"]})',
         f'emu.addMemoryCallback(function() dma=dma+1 end,emu.callbackType.exec,{addresses["PREPARE_VRAM_COPY_ROW_SAFE"]})',
         f'emu.addMemoryCallback(function() assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"CPU frame corrupt");assert(r16(0x7200)==0x55aa,"protected RAM corrupt");out:write(string.format("[%d,%d,%d,%d]\\n",index,r16(0x7006),r16({w("DMA_COPY_VRAM_DEST")}),r16({w("ENTITY_CURRENT_DISPLAYED_SPRITES")})));if index==#rows then out:flush();out:close();emu.log("RENDER_ABI_COMPLETE "..index.." "..render.." "..dma);emu.breakExecution() end end,emu.callbackType.exec,{end})']
    script=folder/'render.lua';script.write_text('\n'.join(lua)+'\n')
    q=subprocess.run([str(a.oracle.resolve()),str(path.resolve()),'--home',str(folder/'oracle-home'),'--frames','10000','--timeout','90','--lua-timeout','20','--lua-allow-io','--lua',str(script),'--write-memory','SnesPrgRom:0xff00:'+code.hex(),'--set-pc','0xc0ff00','--cpu','Snes'],capture_output=True,timeout=100)
    (folder/'oracle.stdout.jsonl').write_bytes(q.stdout);(folder/'oracle.stderr.log').write_bytes(q.stderr)
    events=[json.loads(s) for s in q.stdout.decode().splitlines()];logs=[e for e in events if e['event']=='lua_log'];markers=[e['text'] for e in logs if 'RENDER_ABI_COMPLETE ' in e['text']]
    if q.returncode or not events[-1].get('ok') or events[-1].get('reason')!='debugger_break' or any(e['error_count'] for e in logs) or len(markers)!=1:raise RuntimeError('Actual machine run incomplete: '+q.stderr.decode(errors='replace'))
    got=[json.loads(s) for s in samples.read_text().splitlines()]
    if [r[0] for r in got]!=list(range(1,len(rows)+1)):raise ValueError('Machine corpus incomplete')
    return got,{'cases':len(got),'callMarker':markers[0],'samplesSha256':sha(samples),'callerSha256':hashlib.sha256(code).hexdigest().upper(),'luaSha256':sha(script),'stackDirectPageCanaryPassed':True}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('rom','redux-rom','original-assets','redux-assets','oracle','ca65','ld65','native-source','scratch','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.scratch=local_scratch(a.scratch)
    if a.scratch.exists():raise ValueError('Fresh scratch required')
    original=a.rom.read_bytes();redux=a.redux_rom.read_bytes()
    if len(original)!=0x300000 or hashlib.sha1(original).hexdigest()!=US_SHA1:raise ValueError('Exact clean USA owner ROM required')
    a.scratch.mkdir(parents=True);ram,addresses,proof=identify(a,a.scratch,original)
    for r in proof:
        if r['symbol'] in ('MOVEMENT_SPEEDS','ALLOWED_INPUT_DIRECTIONS'):continue
        offset=int(r['address'],16)-0xc00000;n=r['byteEqualLength']
        if redux[offset:offset+n]!=original[offset:offset+n]:raise ValueError('Pinned Redux source body differs: '+r['symbol'])
        r['reduxByteEqualSha256']=hashlib.sha256(redux[offset:offset+n]).hexdigest().upper()
    identities={str(p.resolve()):sha(p) for p in (a.rom,a.redux_rom,a.original_assets,a.redux_assets,a.oracle,a.ca65,a.ld65,Path(__file__))};modes=[]
    for profile,path,rom in (('Original',a.rom,original),('Redux',a.redux_rom,redux)):
        info=sprite(a,profile,rom);rows=corpus(info);got,metadata=machine(a,a.scratch/profile.lower(),path,ram,addresses,info,rows)
        failures=[];nonzero=0;offscreen=0
        for row,sample in zip(rows,got):
            _,value,dest,displayed=sample
            if not row['onScreen']:offscreen+=1
            nonzero+=value!=0
            if not value or value!=dest:failures.append({'case':sample[0],'kind':'live-vram-return','value':value,'dest':dest})
        modes.append({'profile':profile,'Passed':not failures,'executedCases':len(got),'renderedNonzeroReturns':nonzero,'offscreenGuardCases':offscreen,'mismatches':failures,'spriteIdentity':info,**metadata})
    report={'format':'snes-sprite-render-live-abi-oracle-v1','Passed':all(r['Passed'] for r in modes),'executedCases':sum(r['executedCases'] for r in modes),'skippedCases':0,'modes':modes,'SourceMapping':proof,'InputIdentities':identities,'OwnerRomUnchanged':all(sha(Path(p))==v for p,v in identities.items()),'Limits':['Actual complete original and pinned Redux render wrappers, visibility routine and DMA children execute in a prepared valid NPC773 sprite context with DP1000. The own caller and RAM prerequisites replace surrounding SNES gameplay only.','ME1 has a source BNE after IS_ENTITY_ON_SCREEN. In this nonzero direct-page context its PLD affects CPU flags, so even the prepared off-screen actor renders. The test does not replace that machine behavior with an invented visibility predicate; other direct-page contexts are not claimed.','The source return is the live accumulator after the final VRAM row, not an invented true/false value. Native production consumer comparison remains a separate evidence step.','Machine samples, actual group bytes, reassembled original code and owner ROMs remain private. No source bytecode or assets are embedded in this tool or public report.']}
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ('Passed','executedCases','skippedCases')}))
    if not report['Passed']:raise SystemExit(1)

if __name__=='__main__':main()
