# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare native transition arithmetic with actual untouched local SNES code.

Runs complete INIT_TRANSITION_SCROLL_VELOCITY and real Mode7 multiplication.
UPDATE is sampled at its source SCROLL_MAP_TO_POSITION call boundary; map
streaming is explicitly outside scope. No input ROM/save/build is modified.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess

from check_jev_observer_parity import local_scratch
import snes_position_arithmetic_oracle as mapping
from snes_menu_text_oracle import REDUX_SHA


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def identify(a,out,rom,redux):
    saved=mapping.ROUTINES;mapping.ROUTINES=()
    try:globals_,known,evidence=mapping.identify(a,out,rom)
    finally:mapping.ROUTINES=saved
    folder=out/'source-mapping';prelude=(folder/'movement_speeds.asm').read_text(encoding='utf-8').split('.SEGMENT "CODE"')[0]
    cfg=folder/'code.cfg';include=['--cpu','65816','-D','USA','-I',folder/'include-overlay','-I',a.native_source/'include','-I',a.native_source/'asm']
    def assemble(name,relative,extra=''):
        source=folder/(name.lower()+'.asm');obj=source.with_suffix('.o');blob=source.with_suffix('.bin')
        source.write_text(prelude+''.join(f'{n} := ${v:06X}\n'for n,v in known.items())+'.A16\n.I16\n.EXPORT '+name+extra+'\n.SEGMENT "CODE"\n.INCLUDE "'+relative+'"\n',encoding='utf-8')
        mapping.run([a.ca65,*include,source,'-o',obj],source.with_suffix('.compile.log'))
        mapping.run([a.ld65,'-C',cfg,'-o',blob,'-Ln',source.with_suffix('.lbl'),obj],source.with_suffix('.link.log'))
        return source,blob
    for name,relative in (('SINE_LOOKUP_TABLE','data/sine_table.asm'),('SCREEN_TRANSITION_CONFIG_TABLE','data/screen_transition_config_table.asm')):
        source,blob=assemble(name,relative);raw=blob.read_bytes();address=mapping.find_unique(rom,raw,name);known[name]=address
        evidence.append({'symbol':name,'source':relative,'address':f'{address:06X}','byteEqualLength':len(raw),'sha256':sha(blob),'pinnedReduxBodyUnchanged':raw==redux[address-0xC00000:address-0xC00000+len(raw)]})
    config=rom[known['SCREEN_TRANSITION_CONFIG_TABLE']-0xC00000:known['SCREEN_TRANSITION_CONFIG_TABLE']-0xC00000+408]
    if len(config)!=408:raise ValueError('Expected34 source transition records')
    for name,relative,extra in (('COSINE','system/math/cosine_sine.asm',', COSINE_SINE'),('INIT_TRANSITION_SCROLL_VELOCITY','misc/init_transition_scroll_velocity.asm','')):
        source,blob=assemble(name,relative,extra);raw=blob.read_bytes();address=mapping.find_unique(rom,raw,name);known[name]=address
        if name=='COSINE':
            labels=mapping.labels(source.with_suffix('.lbl'));known['COSINE_SINE']=address+labels['COSINE_SINE']-labels['COSINE']
        evidence.append({'symbol':name,'source':relative,'address':f'{address:06X}','byteEqualLength':len(raw),'sha256':sha(blob),'pinnedReduxBodyUnchanged':raw==redux[address-0xC00000:address-0xC00000+len(raw)]})
    # Bind the external map child from the complete source UPDATE call site.
    # Its three target bytes are the only provisional unknown. Reassemble
    # with that target and require complete unmasked identity before execution.
    known['SCROLL_MAP_TO_POSITION']=0
    source,blob=assemble('UPDATE_TRANSITION_SCROLL','misc/update_transition_scroll.asm');raw=blob.read_bytes()
    if raw[-5]!=0x22 or raw[-1]!=0x6b:raise ValueError('Review changed source update child tail')
    pattern=re.escape(raw[:-4])+b'...'+re.escape(raw[-1:]);hits=list(re.finditer(pattern,rom,re.S))
    if len(hits)!=1:raise ValueError('Complete update call-site identity is not unique')
    address=hits[0].start()+0xC00000;known['SCROLL_MAP_TO_POSITION']=int.from_bytes(hits[0].group()[-4:-1],'little')
    source,blob=assemble('UPDATE_TRANSITION_SCROLL','misc/update_transition_scroll.asm');raw=blob.read_bytes()
    if mapping.find_unique(rom,raw,'UPDATE_TRANSITION_SCROLL')!=address:raise ValueError('Unmasked full update identity changed')
    known['UPDATE_TRANSITION_SCROLL']=address;known['UPDATE_MAP_CHILD_BOUNDARY']=address+len(raw)-5
    evidence.append({'symbol':'UPDATE_TRANSITION_SCROLL','source':'misc/update_transition_scroll.asm','address':f'{address:06X}','byteEqualLength':len(raw),'sha256':sha(blob),'pinnedReduxBodyUnchanged':raw==redux[address-0xC00000:address-0xC00000+len(raw)],'excludedChildBoundary':f'{known["UPDATE_MAP_CHILD_BOUNDARY"]:06X}','excludedChildTarget':f'{known["SCROLL_MAP_TO_POSITION"]:06X}'})
    if any(not e['pinnedReduxBodyUnchanged']for e in evidence if 'pinnedReduxBodyUnchanged'in e and e['symbol']!='SCREEN_TRANSITION_CONFIG_TABLE'):
        raise ValueError('Pinned routine/table changed; inspect active hook before reference use')
    return globals_,known,evidence,config


def corpus(config):
    speeds=sorted(set(config[5::12]));cases=[]
    for speed in speeds:
        for angle in range(256):
            for x,y in ((0,0),(1,65535),(32767,32768),(32768,32767),(65535,1)):
                cases.append(dict(group='actual-config-speeds-all-byte-angles',speed=speed,direction=angle,x=x,y=y))
    for speed in (1,127,128,255,256,32767,32768,65535):
        for angle in range(256):cases.append(dict(group='synthetic-signed-speed-controls',speed=speed,direction=angle,x=32768,y=65535))
    for direction in (256,511,32768,65535):
        for speed in speeds:cases.append(dict(group='synthetic-high-angle-normalization',speed=speed,direction=direction,x=65535,y=32768))
    return cases,speeds


def machine(a,out,path,globals_,known,cases):
    out.mkdir();samples=out/'samples.jsonl';w=lambda name:globals_[name]&65535
    code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230');entry=0xC1FE00+len(code)
    code+=bytes.fromhex('af02717eaaaf00717e22')+known['INIT_TRANSITION_SCROLL_VELOCITY'].to_bytes(3,'little')
    code+=bytes.fromhex('7b8f08707e3b8f0a707e');sampled=0xC1FE00+len(code);code+=bytes((0x4c,entry&255,(entry>>8)&255))
    names=('TRANSITION_X_VELOCITY_FRAC','TRANSITION_Y_VELOCITY_FRAC','TRANSITION_X_POSITION_FRAC','TRANSITION_Y_POSITION_FRAC')
    lua=['local output=assert(io.open('+json.dumps(samples.as_posix())+',"wb"))','local cases='+re.sub(r'"(\w+)":',r'\1=',json.dumps(cases)).replace('[','{').replace(']','}'),
         'local mem=emu.memType.snesWorkRam','local function w16(a,v)emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256)%256,mem)end',
         'local function r16(a)return emu.read(a,mem)+256*emu.read(a+1,mem)end','local function r32(a)return r16(a)+65536*r16(a+2)end',
         'local index=0;local init=0;local cosine=0;local sine=0;w16(0x7a00,0x55aa)',
         f'emu.addMemoryCallback(function()init=init+1 end,emu.callbackType.exec,{known["INIT_TRANSITION_SCROLL_VELOCITY"]})',
         f'emu.addMemoryCallback(function()cosine=cosine+1 end,emu.callbackType.exec,{known["COSINE"]})',
         f'emu.addMemoryCallback(function()sine=sine+1 end,emu.callbackType.exec,{known["COSINE_SINE"]})',
         'emu.addMemoryCallback(function()index=index+1;local c=assert(cases[index]);w16(0x7100,c.speed);w16(0x7102,c.direction);'+f'w16({w("BG1_X_POS")},c.x);w16({w("BG1_Y_POS")},c.y);'+''.join(f'w16({w(n)},0xaaaa);w16({w(n)}+2,0x5555);'for n in names)+f'end,emu.callbackType.exec,{entry})',
         'emu.addMemoryCallback(function()assert(r16(0x7008)==0x1000 and r16(0x700a)==0x1fff,"source frame changed");assert(r16(0x7a00)==0x55aa,"source canary changed");output:write(string.format("[%d,%u,%u,%u,%u]\\n",index,'+','.join(f'r32({w(n)})'for n in names)+'));if index==#cases then assert(init==#cases and cosine==#cases and sine==2*#cases,"source call counts changed");output:flush();output:close();emu.log("TRANSITION_INIT_COMPLETE "..index.." init="..init.." cosine="..cosine.." sine="..sine);emu.breakExecution()end '+f'end,emu.callbackType.exec,{sampled})']
    script=out/'init.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
    result=subprocess.run([str(a.oracle),str(path),'--home',str(out/'home'),'--frames','10000','--timeout','60','--lua-timeout','10','--lua-allow-io','--lua',str(script),'--write-memory','SnesPrgRom:0x1fe00:'+code.hex(),'--set-pc','0xc1fe00','--cpu','Snes'],capture_output=True,timeout=70)
    (out/'oracle.jsonl').write_bytes(result.stdout);(out/'oracle.stderr').write_bytes(result.stderr)
    logs=[json.loads(line)for line in result.stdout.decode().splitlines()]
    if result.returncode or not logs[-1].get('ok')or logs[-1].get('reason')!='debugger_break'or any(r.get('error_count',0)for r in logs):raise ValueError('Actual init CPU failed')
    if sum('TRANSITION_INIT_COMPLETE 'in r.get('text','')for r in logs)!=1:raise ValueError('Source completion marker missing')
    rows=[json.loads(line)for line in samples.read_text(encoding='utf-8').splitlines()]
    if [r[0]for r in rows]!=list(range(1,len(cases)+1)):raise ValueError('Source corpus incomplete/unordered')
    return dict(cases=cases,results=rows,count=len(rows),sourceCallCounts=dict(init=len(cases),cosine=len(cases),cosineSine=2*len(cases)),sourceFrameCanariesPassed=True,inputRomSha256=sha(path),ownCallerSha256=hashlib.sha256(code).hexdigest(),luaSha256=sha(script),samplesSha256=sha(samples))


def update_prefix(a,out,path,globals_,known,cases):
    out.mkdir();w=lambda name:globals_[name]&65535
    names=('TRANSITION_X_VELOCITY_FRAC','TRANSITION_Y_VELOCITY_FRAC','TRANSITION_X_POSITION_FRAC','TRANSITION_Y_POSITION_FRAC')
    rows=[]
    def one(pair):
        index,c=pair;folder=out/str(index);folder.mkdir();sample=folder/'sample.txt'
        code=bytearray.fromhex('78d818fbc230a2ff1f9aa900105be220a97e48abc230')
        code+=bytes((0x22,))+known['UPDATE_TRANSITION_SCROLL'].to_bytes(3,'little')+bytes((0,))
        lua=['local mem=emu.memType.snesWorkRam','local function w16(a,v)emu.write(a,v%256,mem);emu.write(a+1,math.floor(v/256)%256,mem)end','local function r16(a)return emu.read(a,mem)+256*emu.read(a+1,mem)end','local function r32(a)return r16(a)+65536*r16(a+2)end','w16(0x7a00,0x55aa)']
        for n,value in zip(names,c):lua.append(f'w16({w(n)},{value%65536});w16({w(n)}+2,{value//65536})')
        lua+=['local calls=0;local child=0',f'emu.addMemoryCallback(function()calls=calls+1 end,emu.callbackType.exec,{known["UPDATE_TRANSITION_SCROLL"]})',f'emu.addMemoryCallback(function()child=child+1 end,emu.callbackType.exec,{known["SCROLL_MAP_TO_POSITION"]})',
              f'emu.addMemoryCallback(function()assert(calls==1 and child==0 and r16(0x7a00)==0x55aa,"update prefix/canary failed");local f=assert(io.open({json.dumps(sample.as_posix())},"wb"));f:write(string.format("[%u,%u,%u,%u,%u,%u,%u,%u]",'+','.join([f'r32({w(n)})'for n in names]+[f'r16({w(n)})'for n in ('BG1_X_POS','BG1_Y_POS','BG2_X_POS','BG2_Y_POS')])+f'));f:close();emu.log("UPDATE_PREFIX_COMPLETE {index}");emu.breakExecution()end,emu.callbackType.exec,{known["UPDATE_MAP_CHILD_BOUNDARY"]})']
        script=folder/'update.lua';script.write_text('\n'.join(lua)+'\n',encoding='utf-8')
        proc=subprocess.run([str(a.oracle),str(path),'--home',str(folder/'home'),'--frames','10','--timeout','20','--lua-timeout','10','--lua-allow-io','--lua',str(script),'--write-memory','SnesPrgRom:0x1fe00:'+code.hex(),'--set-pc','0xc1fe00','--cpu','Snes'],capture_output=True,timeout=30)
        (folder/'oracle.jsonl').write_bytes(proc.stdout);logs=[json.loads(line)for line in proc.stdout.decode().splitlines()]
        if proc.returncode or not logs[-1].get('ok')or logs[-1].get('reason')!='debugger_break'or sum(f'UPDATE_PREFIX_COMPLETE {index}'in r.get('text','')for r in logs)!=1:raise ValueError('Update prefix CPU failed')
        return dict(index=index,inputs=c,result=json.loads(sample.read_text(encoding='utf-8')),childExecuted=False)
    # Own isolated homes prevent cross-process state; immutable input is read only.
    with ThreadPoolExecutor(max_workers=3)as executor:rows=list(executor.map(one,enumerate(cases,1)))
    return rows


def native(a,out,source,cases,updates,exact_table=False):
    out.mkdir();text=(source/'src/game/door.c').read_text(encoding='utf-8')
    body=mapping.native_body(text,'init_transition_scroll_velocity')+mapping.native_body(text,'update_transition_scroll')
    mathpath=source/'src/core/math.c';bgpath=source/'src/game/battle_bg.c'
    if not mathpath.exists():mathpath=a.native_source/'src/core/math.c'
    if not bgpath.exists():bgpath=a.native_source/'src/game/battle_bg.c'
    maths=mathpath.read_text(encoding='utf-8');mathbody=mapping.native_body(maths,'cosine_sine')+mapping.native_body(maths,'cosine_func')
    bg=bgpath.read_text(encoding='utf-8');table=re.search(r'const int8_t sine_table\[256\] = \{.*?\};',bg,re.S).group()
    if exact_table:
        sourcebytes=[int(v,16)for v in re.findall(r'\.BYTE\s+\$([0-9A-Fa-f]{2})',(a.native_source/'asm/data/sine_table.asm').read_text(encoding='utf-8'))]
        if len(sourcebytes)!=256:raise ValueError('Exact source table control requires256bytes')
        table='const int8_t sine_table[256] = {'+','.join(str(v if v<128 else v-256)for v in sourcebytes)+'};'
    prefix='#include <stdio.h>\n#include <stdint.h>\n#include <math.h>\n#define EB_VIEWPORT_CENTER_X 128\n#define EB_VIEWPORT_CENTER_Y 112\nstruct {int32_t transition_x_velocity,transition_y_velocity,transition_x_accum,transition_y_accum;} dr;\nstruct {uint16_t bg_hofs[2],bg_vofs[2];} ppu;\nstatic void map_refresh_tilemaps(unsigned x,unsigned y){(void)x;(void)y;}\n'
    driver=out/'native.c';driver.write_text(prefix+table+'\n'+mathbody+body+r'''
int main(void){unsigned kind,s,d,x,y;while(scanf("%u %u %u %u %u",&kind,&s,&d,&x,&y)==5){
 if(!kind){ppu.bg_hofs[0]=x;ppu.bg_vofs[0]=y;init_transition_scroll_velocity(s,d);printf("[%u,%u,%u,%u]\n",(uint32_t)dr.transition_x_velocity,(uint32_t)dr.transition_y_velocity,(uint32_t)dr.transition_x_accum,(uint32_t)dr.transition_y_accum);}
 else {dr.transition_x_velocity=(int32_t)s;dr.transition_y_velocity=(int32_t)d;dr.transition_x_accum=(int32_t)x;dr.transition_y_accum=(int32_t)y;update_transition_scroll();printf("[%u,%u,%u,%u,%u,%u,%u,%u]\n",(uint32_t)dr.transition_x_velocity,(uint32_t)dr.transition_y_velocity,(uint32_t)dr.transition_x_accum,(uint32_t)dr.transition_y_accum,ppu.bg_hofs[0],ppu.bg_vofs[0],ppu.bg_hofs[1],ppu.bg_vofs[1]);}
}return 0;}
''',encoding='utf-8')
    exe=out/'native.exe';mapping.run([a.compiler,'-O2','-fwrapv',driver,'-lm','-o',exe],out/'compile.log')
    stdin='\n'.join(' '.join(map(str,(0,c['speed'],c['direction'],c['x'],c['y'])))for c in cases)+'\n'+'\n'.join(' '.join(map(str,(1,*c)))for c in updates)+'\n'
    proc=subprocess.run([str(exe)],input=stdin,capture_output=True,text=True,timeout=20)
    (out/'native.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
    if proc.returncode:raise ValueError('Actual source native harness failed')
    rows=[json.loads(line)for line in proc.stdout.splitlines()]
    if len(rows)!=len(cases)+len(updates):raise ValueError('Native corpus incomplete')
    return dict(sourceSha256=sha(source/'src/game/door.c'),mathSourcePath=str(mathpath),mathSha256=sha(mathpath),tableSourcePath=str(bgpath),tableSha256=sha(bgpath),exactSourceTablePrivateControl=exact_table,testedBodySha256=hashlib.sha256(body.encode()).hexdigest(),driverSha256=sha(driver),privateExeSha256=sha(exe),init=rows[:len(cases)],update=rows[len(cases):])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('rom','redux-rom','oracle','ca65','ld65','compiler','native-source','scratch','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--previous-source',type=Path)
    p.add_argument('--exact-source-table-control',action='store_true',help='Also compile an explicitly private source-exact sine table control, never edit production source.')
    a=p.parse_args()
    for n,v in vars(a).items():
        if isinstance(v,Path):setattr(a,n,v.resolve())
    a.scratch=local_scratch(a.scratch)
    if a.scratch.exists()or a.output.exists():raise ValueError('Fresh scratch/report required')
    rom=a.rom.read_bytes();redux=a.redux_rom.read_bytes()
    if len(rom)!=0x300000 or hashlib.sha1(rom).hexdigest()!=mapping.US_SHA1 or sha(a.redux_rom)!=REDUX_SHA:raise ValueError('Exact clean USA and pinned Redux inputs required')
    a.scratch.mkdir(parents=True);globals_,known,evidence,config=identify(a,a.scratch,rom,redux);cases,speeds=corpus(config)
    updates=[]
    for xv,yv in ((0,0),(0x100,0xffffff00),(0x7fff00,0xff800100),(0xffffffff,1)):
        for xp,yp in ((0,0),(0xffff,0xffff),(0x7fffffff,0x80000000),(0xffffffff,0xfffffffe),(0x8000ffff,0x7fff0000)):
            updates.append((xv,yv,xp,yp))
    actual=native(a,a.scratch/'native-current',a.native_source,cases,updates)
    control=native(a,a.scratch/'native-source-table-control',a.native_source,cases,updates,True)if a.exact_source_table_control else None
    previous=native(a,a.scratch/'native-previous',a.previous_source,cases,updates)if a.previous_source else None
    profiles=[]
    for mode,path in (('original',a.rom),('redux',a.redux_rom)):
        cpu=machine(a,a.scratch/mode,path,globals_,known,cases);u=update_prefix(a,a.scratch/(mode+'-update'),path,globals_,known,updates)
        mismatches=[i for i,(x,y)in enumerate(zip(cpu['results'],actual['init']),1)if x[1:]!=y]
        um=[i for i,(x,y)in enumerate(zip(u,actual['update']),1)if x['result']!=y]
        old=[i for i,(x,y)in enumerate(zip(cpu['results'],previous['init']),1)if x[1:]!=y]if previous else []
        cm=[i for i,(x,y)in enumerate(zip(cpu['results'],control['init']),1)if x[1:]!=y]if control else None
        profiles.append(dict(profile=mode,cpu=cpu,updatePrefix=u,currentInitMismatchIndices=mismatches,currentUpdateMismatchIndices=um,previousInitMismatchIndices=old,privateExactTableMismatchIndices=cm))
    if a.rom.read_bytes()!=rom or a.redux_rom.read_bytes()!=redux:raise ValueError('Input ROM changed')
    report=dict(format='transition-scroll-source-cpu-v1',toolSha256=sha(Path(__file__)),sourceMapping=evidence,actualConfigSpeeds=speeds,actualConfigCount=34,currentNative=actual,previousNative=previous,privateExactSourceTableControl=control,profiles=profiles,allCurrentPassed=all(not r['currentInitMismatchIndices']and not r['currentUpdateMismatchIndices']for r in profiles),ownerSavesOrInputRomsModified=False,limits=['Full original/pinned INIT executes actual COSINE/COSINE_SINE, Mode7 hardware and source256byte sine table. Native harness compiles exact held source function bodies/table; this is not frozen production-archive linkage.', 'UPDATE source instructions execute unchanged up to its SCROLL_MAP_TO_POSITION JSL boundary; child streaming, camera side effects, child return and full map transitions are explicitly excluded.', 'All actual source-config speeds/all byte angles plus synthetic signed-speed/high-angle/BGposition controls; actual34record reachability and every real door are not exercised.', 'Previous compiler observations include signed-shift/overflow undefined behavior; they establish this tested binary outcome, not portable C semantics. Root independently owns sanitizer evidence.'])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([(r['profile'],r['cpu']['count'],len(r['previousInitMismatchIndices']),len(r['currentInitMismatchIndices']),len(r['currentUpdateMismatchIndices']))for r in profiles]))


if __name__=='__main__':main()
