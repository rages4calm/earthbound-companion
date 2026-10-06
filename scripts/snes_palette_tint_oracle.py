# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare full actual SNES tint routines with frozen native map consumers.

Reassembly only identifies byte-equal original routine/RAM addresses. The owner
ROM and compiled pinned Redux ROM remain unchanged. Only a private own caller
is inserted into the reference runner's memory; source routines are not mocked.
Captured palettes remain private. Public output includes hashes/counts only.
"""
import argparse, hashlib, json, re, subprocess
from pathlib import Path
import snes_position_arithmetic_oracle as mapping
from check_jev_observer_parity import local_scratch
from snes_movement_helpers_oracle import US_SHA1

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def identify(a,out,rom):
    mapping.ROUTINES=(('MULT16','system/math/mult16.asm','far'),
                      ('ADJUST_SINGLE_COLOUR','overworld/adjust_single_colour.asm','near'))
    globals_,addresses,evidence=mapping.identify(a,out,rom)
    folder=out/'source-mapping'
    includes=['--cpu','65816','-D','USA','-I',folder/'include-overlay','-I',a.native_source/'include','-I',a.native_source/'asm']
    prelude='.INCLUDE "common.asm"\n.INCLUDE "config.asm"\n.INCLUDE "structs.asm"\n'
    prelude+=''.join(f'.IMPORT {n}: absolute\n' for n in globals_ if not n.startswith('__'))+'.IMPORT __BSS_START__: absolute\n'
    config=folder/'code.cfg'
    division=folder/'division16s.asm';obj=division.with_suffix('.o');blob=division.with_suffix('.bin')
    division.write_text(prelude+'.SEGMENT "CODE"\n.A16\n.I16\n.INCLUDE "system/math/division16s.asm"\n')
    mapping.run([a.ca65,*includes,division,'-o',obj,'-l',division.with_suffix('.lst')],division.with_suffix('.compile.log'))
    mapping.run([a.ld65,'-C',config,'-o',blob,obj],division.with_suffix('.link.log'))
    addresses['DIVISION16S']=mapping.find_unique(rom,blob.read_bytes(),'DIVISION16S')
    evidence.append({'symbol':'DIVISION16S','address':f'{addresses["DIVISION16S"]:06X}','originalSource':'system/math/division16s.asm','byteEqualLength':blob.stat().st_size,'byteEqualSha256':sha(blob)})
    listing=division.with_suffix('.lst').read_text()
    offsets=re.findall(r'^([0-9A-F]{6})r\s+\d+\s+DIVISION16S_DIVISOR_POSITIVE:\s*$',listing,re.M)
    if len(offsets)!=1:raise ValueError('Division positive alias is not unique')
    addresses['DIVISION16S_DIVISOR_POSITIVE']=addresses['DIVISION16S']+int(offsets[0],16)
    def locate(obj,blob,symbol):
        original=blob.read_bytes()
        try:entry=mapping.find_unique(rom,original,symbol)
        except ValueError:
            offsets=set();base=config.read_text()
            for delta in (1,256):
                cfg=folder/f'{symbol.lower()}-reloc-{delta}.cfg';cfg.write_text(base.replace('start=$C00000',f'start=${0xc00000+delta:06X}'))
                shifted=cfg.with_suffix('.bin');mapping.run([a.ld65,'-C',cfg,'-o',shifted,obj],cfg.with_suffix('.log'))
                candidate=shifted.read_bytes()
                if len(candidate)!=len(original):raise ValueError('Relocated body size changed')
                offsets.update(i for i,(x,y) in enumerate(zip(original,candidate)) if x!=y)
            pattern=b''.join(b'.' if i in offsets else re.escape(bytes((v,))) for i,v in enumerate(original))
            found=list(re.finditer(pattern,rom,re.S))
            if len(found)!=1:raise ValueError('Complete masked source body not unique: '+symbol)
            entry=found[0].start()+0xc00000
            cfg=folder/(symbol.lower()+'-located.cfg');cfg.write_text(base.replace('start=$C00000',f'start=${entry:06X}'))
            mapping.run([a.ld65,'-C',cfg,'-o',blob,obj],cfg.with_suffix('.log'))
            original=blob.read_bytes()
            if rom[entry-0xc00000:entry-0xc00000+len(original)]!=original:raise ValueError('Located full source body differs: '+symbol)
        return entry,original
    for symbol,relative in (('GET_COLOUR_AVERAGE','system/get_colour_average.asm'),
                            ('ADJUST_SPRITE_PALETTES_BY_AVERAGE','overworld/adjust_sprite_palettes_by_average.asm')):
        source=folder/(symbol.lower()+'.asm');obj=source.with_suffix('.o');blob=source.with_suffix('.bin')
        source.write_text(prelude+''.join(f'{n} := ${(v&65535) if n in ("GET_COLOUR_AVERAGE","ADJUST_SINGLE_COLOUR") else v:06X}\n' for n,v in addresses.items())+'.SEGMENT "CODE"\n.A16\n.I16\n.INCLUDE "'+relative+'"\n')
        mapping.run([a.ca65,*includes,source,'-o',obj,'-l',source.with_suffix('.lst')],source.with_suffix('.compile.log'))
        mapping.run([a.ld65,'-C',config,'-o',blob,obj],source.with_suffix('.link.log'))
        entry,body=locate(obj,blob,symbol);addresses[symbol]=entry
        evidence.append({'symbol':symbol,'address':f'{entry:06X}','originalSource':relative,'byteEqualLength':len(body),'byteEqualSha256':sha(blob)})
    return globals_,addresses,evidence

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('rom','redux-rom','oracle','ca65','ld65','native-source','native-review','captured-cases','scratch','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.scratch=local_scratch(a.scratch)
    if a.scratch.exists():raise ValueError('Fresh private scratch required')
    review=json.loads(a.native_review.read_text());cases=json.loads(a.captured_cases.read_text())
    if not review['Passed'] or review['format']!='redux-overlay-palette-behavior-qa-v1':raise ValueError('Completed native consumer report required')
    native_cases=[r for r in review['cases'] if r['kind']=='map-tint-consumer']
    if len(cases)!=len(native_cases):raise ValueError('Captured/native case count differs')
    rom=a.rom.read_bytes();redux=a.redux_rom.read_bytes()
    if len(rom)!=0x300000 or hashlib.sha1(rom).hexdigest()!=US_SHA1:raise ValueError('Exact clean USA owner ROM required')
    a.scratch.mkdir(parents=True);globals_,addresses,proof=identify(a,a.scratch,rom)
    identity_paths=[a.rom,a.redux_rom,a.oracle,a.ca65,a.ld65,a.native_review,a.captured_cases,Path(__file__)]
    identities={str(x.resolve()):sha(x) for x in identity_paths};modes=[]
    # The active patched bodies must be identical except the four source-proven
    # threshold operands in the existing shared channel-adjustment routine.
    patches={0xc00453:bytes((0xc9,4,0)),0xc0045d:bytes((0xe9,4,0)),0xc0046d:bytes((0xc9,4,0)),0xc00477:bytes((0x69,4,0))}
    for entry in proof:
        if entry['symbol'] in ('MOVEMENT_SPEEDS','ALLOWED_INPUT_DIRECTIONS'):continue
        address=int(entry['address'],16);offset=address-0xc00000;length=entry['byteEqualLength']
        expected=bytearray(rom[offset:offset+length])
        if entry['symbol']=='ADJUST_SINGLE_COLOUR':
            if address!=0xc00434:raise ValueError('Patched channel body mapping changed')
            for site,patch in patches.items():expected[site-address:site-address+3]=patch
        if redux[offset:offset+length]!=expected:raise ValueError('Redux full body differs from exact source patch: '+entry['symbol'])
        entry['reduxByteEqualSha256']=hashlib.sha256(expected).hexdigest().upper()
    palette=globals_['PALETTES']&65535
    refs=[globals_['SAVED_COLOUR_AVERAGE_'+c]&65535 for c in ('RED','GREEN','BLUE')]
    current=[globals_['COLOUR_AVERAGE_'+c]&65535 for c in ('RED','GREEN','BLUE')]
    for profile,path in (('Original',a.rom),('Redux',a.redux_rom)):
        rows=[r for r in cases if r['profile']==profile]
        folder=a.scratch/profile.lower();folder.mkdir();samples=folder/'samples.jsonl'
        # Caller runs in native mode A/X/Y16, SP1FFF, DP1000, DBR7E.
        code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
        begin=0xc0ff00+len(code)
        code+=bytes((0x22,))+addresses['ADJUST_SPRITE_PALETTES_BY_AVERAGE'].to_bytes(3,'little')
        code+=bytes.fromhex('7b8f08707e3b8f0a707e');end=0xc0ff00+len(code)
        code+=bytes((0x4c,begin&255,begin>>8&255))
        lua=['local out=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))',
             'local rows='+json.dumps([[r['reference'],r['bg'],r['initial']] for r in rows],separators=(',',':')).replace('[','{').replace(']','}'),
             'local m=emu.memType.snesWorkRam','local function w16(a,v) emu.write(a,v%256,m);emu.write(a+1,math.floor(v/256)%256,m) end',
             'local function r16(a) return emu.read(a,m)+256*emu.read(a+1,m) end',
             'local index=0;local calls=0;local averages=0;local channels=0;w16(0x7200,0x55aa)',
             f'emu.addMemoryCallback(function() index=index+1;local r=assert(rows[index],"past corpus");',
             ''.join(f'w16({address},r[1][{i+1}]);' for i,address in enumerate(refs)),
             f'for i=1,96 do w16({palette}+64+(i-1)*2,r[2][i]) end;for i=1,128 do w16({palette}+256+(i-1)*2,r[3][i]) end end,emu.callbackType.exec,{begin})',
             f'emu.addMemoryCallback(function() calls=calls+1 end,emu.callbackType.exec,{addresses["ADJUST_SPRITE_PALETTES_BY_AVERAGE"]})',
             f'emu.addMemoryCallback(function() averages=averages+1 end,emu.callbackType.exec,{addresses["GET_COLOUR_AVERAGE"]})',
             f'emu.addMemoryCallback(function() channels=channels+1 end,emu.callbackType.exec,{addresses["ADJUST_SINGLE_COLOUR"]})',
             'emu.addMemoryCallback(function() assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"CPU frame corrupted");assert(r16(0x7200)==0x55aa,"protected RAM corrupted");',
             'out:write(string.format("[%d,[%d,%d,%d],[",index,'+','.join(f'r16({x})' for x in current)+'));',
             f'for i=1,128 do if i>1 then out:write(",") end;out:write(tostring(r16({palette}+256+(i-1)*2))) end;out:write("]]\\n");',
             'if index==#rows then assert(calls==#rows and averages==#rows,"call count differs");out:flush();out:close();emu.log("PALETTE_COMPLETE "..calls.." "..channels);emu.breakExecution() end',f'end,emu.callbackType.exec,{end})']
        script=folder/'palette.lua';script.write_text('\n'.join(lua)+'\n')
        q=subprocess.run([str(a.oracle.resolve()),str(path.resolve()),'--home',str(folder/'oracle-home'),'--frames','10000','--timeout','90','--lua-timeout','20','--lua-allow-io','--lua',str(script),'--write-memory','SnesPrgRom:0xff00:'+code.hex(),'--set-pc','0xc0ff00','--cpu','Snes'],capture_output=True,timeout=100)
        (folder/'oracle.stdout.jsonl').write_bytes(q.stdout);(folder/'oracle.stderr.log').write_bytes(q.stderr)
        events=[json.loads(s) for s in q.stdout.decode().splitlines()];logs=[r for r in events if r['event']=='lua_log']
        markers=[r['text'] for r in logs if 'PALETTE_COMPLETE ' in r['text']]
        if q.returncode or not events[-1].get('ok') or events[-1].get('reason')!='debugger_break' or any(r['error_count'] for r in logs) or len(markers)!=1:
            raise RuntimeError(profile+' actual machine execution incomplete: '+q.stderr.decode(errors='replace'))
        got=[json.loads(s) for s in samples.read_text().splitlines()]
        if [r[0] for r in got]!=list(range(1,len(rows)+1)):raise ValueError('Machine corpus incomplete/out of order')
        differences=[];average_differences=[];channel_checks=0
        from redux_overlay_palette_qa import average
        for (i,avg,colors),row in zip(got,rows):
            if avg!=average(row['bg']):average_differences.append(i)
            special=row['specialIndex']
            if special:
                # The tested assembly function returns before its separate
                # map caller's LOAD_SPECIAL_SPRITE_PALETTE. Apply only that
                # verified source copy when comparing to native map output.
                full=[0]*32+row['bg']+colors
                colors[64:80]=full[special*16:special*16+16]
            indexes=[j for j,(machine,native) in enumerate(zip(colors,row['native'])) if machine!=native]
            channel_checks+=128
            if indexes:differences.append({'case':i,'mismatchingColorIndices':indexes})
        modes.append({'profile':profile,'Passed':not differences and not average_differences,'ExecutedCases':len(got),'ExecutedColorComparisons':channel_checks,'SkippedCases':0,'MismatchCount':len(differences),'FirstMismatches':differences[:10],'AverageMismatchCount':len(average_differences),'CompleteCallMarker':markers[0],'SamplesSha256':sha(samples),'CallerSha256':hashlib.sha256(code).hexdigest().upper(),'LuaSha256':sha(script),'StackDirectPageProtectedRamPassed':True})
    if any(sha(Path(path))!=value for path,value in identities.items()):raise RuntimeError('Read-only immutable input changed')
    report={'format':'snes-palette-tint-micro-oracle-v1','Passed':all(r['Passed'] for r in modes),'executedCases':sum(r['ExecutedCases'] for r in modes),'executedColorComparisons':sum(r['ExecutedColorComparisons'] for r in modes),'skippedCases':0,'modes':modes,'SourceMapping':proof,'InputIdentities':identities,'NativeRuntimeSha256':review['runtimeSha256'],'NativeProductionLibrarySha256':review['privateBuild']['productionLibrarySha256'],'NativeConsumerReportSha256':sha(a.native_review),'OwnerRomUnchanged':True,'SharedNativeSourceChanged':False,'Limits':['Actual complete source tint/average/multiply/division/channel routines execute in prepared CPU contexts with real native-consumer captured palettes; surrounding map loading and full SNES rendering are not executed.','Native map consumer includes a final LOAD_SPECIAL_SPRITE_PALETTE. This separate source copy is applied after the machine tint output where required, rather than mislabeling that caller difference as a tint defect.','The active pinned Redux threshold patch is verified across the complete original channel body and executed from the compiled pinned ROM, not an invented formula.','All 298 unique packed map combo/palette configurations use native representative sectors with fixed story-flag prerequisites; alternative event palette override branches remain separate.','Reference runner, compiled Redux ROM and all palette captures are private development inputs, never game runtime/release dependencies or public report data.']}
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ('Passed','executedCases','executedColorComparisons','skippedCases')}))
    if not report['Passed']:raise SystemExit(1)

if __name__=='__main__':main()
