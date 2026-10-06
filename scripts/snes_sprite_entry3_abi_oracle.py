# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify the C0A4A8 entry actually encoded by the retained ME3 event macro.

This addendum preserves the separate frozen movement-entry3 C0A480 proof. The
source macro and complete reassembled body establish the actual live entry;
the untouched ROM executes it with source sprite data and real DMA children.
"""
import argparse, hashlib, json, re
from pathlib import Path
import snes_sprite_render_abi_oracle as base
from check_jev_observer_parity import local_scratch
from maternalbound_graphics import slice_rom
from snes_movement_helpers_oracle import US_SHA1

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('rom','redux-rom','original-assets','redux-assets','oracle','ca65','ld65','native-source','scratch','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.scratch=local_scratch(a.scratch)
    if a.scratch.exists():raise ValueError('Fresh scratch required')
    original=a.rom.read_bytes();redux=a.redux_rom.read_bytes()
    if len(original)!=0x300000 or hashlib.sha1(original).hexdigest()!=US_SHA1:raise ValueError('Exact clean USA owner ROM required')
    a.scratch.mkdir(parents=True);ram,addresses,proof=base.identify(a,a.scratch,original)
    macros=a.native_source/'include/eventmacros.asm';text=macros.read_text()
    if not re.search(r'\.MACRO EVENT_RENDER_ENTITY_SPRITE_ME3\s+EVENT_CALLROUTINE RENDER_ENTITY_SPRITE_ENTRY3\s+\.ENDMACRO',text):raise ValueError('Actual retained ME3 macro changed')
    listing=(a.scratch/'source-mapping/render_entity_sprite.lst').read_text()
    matches=re.findall(r'^([0-9A-F]{6})r\s+\d+\s+RENDER_ENTITY_SPRITE_ENTRY3:\s*$',listing,re.M)
    if len(matches)!=1:raise ValueError('Actual render ENTRY3 source alias not unique')
    address=addresses['RENDER_ENTITY_SPRITE']+int(matches[0],16)
    if address!=0xc0a4a8:raise ValueError('Actual render ENTRY3 alias changed')
    # Reuse the already frozen caller machinery, but its third target is the
    # actual ENTRY3 alias rather than the different movement-entry3 alias.
    addresses['RENDER_ENTITY_SPRITE_MOVEMENT_ENTRY_3']=address
    for r in proof:
        if r['symbol'] in ('MOVEMENT_SPEEDS','ALLOWED_INPUT_DIRECTIONS'):continue
        off=int(r['address'],16)-0xc00000;n=r['byteEqualLength']
        if original[off:off+n]!=redux[off:off+n]:raise ValueError('Pinned Redux full source body changed '+r['symbol'])
    identities={str(x.resolve()):base.sha(x) for x in (a.rom,a.redux_rom,a.original_assets,a.redux_assets,a.oracle,a.ca65,a.ld65,macros,Path(base.__file__),Path(__file__))};modes=[]
    direction_map=(0,0,1,2,2,2,3,0)
    for profile,path,rom in (('Original',a.rom,original),('Redux',a.redux_rom,redux)):
        info=base.sprite(a,profile,rom);rows=[r for r in base.corpus(info) if r['method']==3]
        got,metadata=base.machine(a,a.scratch/profile.lower(),path,ram,addresses,info,rows)
        failures=[]
        for i,(row,sample) in enumerate(zip(rows,got)):
            offset=info['pointer']+direction_map[row['direction']]*4
            frame0=int.from_bytes(slice_rom(rom,offset,2),'little')
            if sample[1]!=sample[2] or not sample[1]:failures.append({'case':i,'kind':'live-return'})
            if sample[3]!=frame0:failures.append({'case':i,'kind':'source-transient-frame-zero'})
        modes.append({'profile':profile,'Passed':not failures,'executedCases':len(got),'mismatches':failures,'sourceTransientFrameZeroCases':len(got),'spriteIdentity':info,**metadata})
    report={'format':'snes-sprite-entry3-live-abi-oracle-v1','Passed':all(r['Passed'] for r in modes),'allPassed':all(r['Passed'] for r in modes),'executedCases':sum(r['executedCases'] for r in modes),'skippedCases':0,'actualEventMacro':'EVENT_RENDER_ENTITY_SPRITE_ME3','actualRoutine':'RENDER_ENTITY_SPRITE_ENTRY3','actualRoutineAddress':f'{address:06X}','SourceMapping':proof,'modes':modes,'InputIdentities':identities,'OwnerRomUnchanged':all(base.sha(Path(n))==v for n,v in identities.items()),'Limits':['The source event macro ME3 targets C0A4A8 ENTRY3; it does not target the differently named movement-entry3 C0A480. Both independent machine proofs remain identified separately.','The complete original/pinned render routine and real DMA children execute in the same prepared nonzero direct-page context as the other render proof.','ENTRY3 renders transient frame0 even when ENTITY_ANIMATION_FRAME stores1. That selection is checked against actual source sprite pointers; original pixels remain private.','This machine-only proof establishes exact callback ABI/frame selection, not completion of surrounding story scenes.']}
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ('Passed','executedCases','skippedCases')}))
    if not report['Passed']:raise SystemExit(1)

if __name__=='__main__':main()
