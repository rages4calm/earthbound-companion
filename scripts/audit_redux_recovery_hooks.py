# SPDX-License-Identifier: GPL-3.0-or-later
"""Check the three pinned rest hooks and their explicit native adaptation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

from build_maternalbound_pack import read_pack
from maternalbound_dialogue import without_comments

PIN='897d00833f4a08a0a92f106abf631629a6a6a041'
ROM_SHA='c2a2fc98c7e6518b797959ffadf24ca4db8b4d7745ed3a9eb92eee106db1d0ab'
HOOKS={0xC91582:'SleepoverHealHijack',0xC915F4:'FullHealHijack',0xC9162C:'HotSpringHealHijack'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('project','native-source','bridge','compiled-rom','assets','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();upstream=a.project.parent
    if subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()!=PIN:
        raise ValueError('Upstream changed; repeat the manual review.')
    relative='ccscript/redux/refill_stamina_on_heal.ccs'
    data=(a.project/relative).read_bytes()
    expected=subprocess.check_output(['git','-C',str(upstream),'show','HEAD:Project/'+relative])
    if data.replace(b'\r\n',b'\n')!=expected.replace(b'\r\n',b'\n'):
        raise ValueError('Source differs from pinned module.')
    writes={int(address,16):label for address,label in re.findall(r'ROM\[(0x[0-9a-fA-F]+)\]\s*=\s*goto\((\w+)\)',without_comments(data.decode('utf-8-sig')))}
    if writes!=HOOKS:raise ValueError('Recovery writes changed.')
    rom=a.compiled_rom.read_bytes()
    if hashlib.sha256(rom).hexdigest()!=ROM_SHA:raise ValueError('Compiled content differs.')
    bridge=json.loads(a.bridge.read_text(encoding='utf-8-sig'))
    labels={(x['module'],x['name']):x['snesAddress'] for x in bridge['labels']}
    _,_,assets=read_pack(a.assets,a.native_source/'src/data/runtime_generated/asset_ids.h')
    blob=assets['dialogue/dialogue.bin']
    _,version,offset,count,*_=struct.unpack_from('<8s6I',blob,len(blob)-32)
    if version!=2:raise ValueError('Expected version 2 native mapping.')
    mapping=dict(struct.iter_unpack('<II',blob[offset:offset+count*8]))
    refs=[]
    for path,anchor in [('src/game/maternalbound.c','void maternalbound_rest_entry('),
                        ('src/game/display_text.c','maternalbound_rest_entry(DIALOGUE_BLOB_BASE+r->ptr_off)'),
                        ('src/game/display_text.c','maternalbound_rest_entry(DIALOGUE_BLOB_BASE+st->reader.ptr_off)'),
                        ('src/game/display_text.c','Redux rest continuation')]:
        source=(a.native_source/path).read_text(encoding='utf-8');at=source.find(anchor)
        if at<0:raise ValueError('Native review binding missing: '+anchor)
        refs.append({'path':path,'line':source[:at].count('\n')+1,'anchor':anchor})
    reviews=[]
    for address,name in HOOKS.items():
        offset=address-0xC00000;trampoline=rom[offset:offset+5]
        target=labels[('refill_stamina_on_heal',name)]
        original=labels[('data_49','l_0x'+f'{address:06x}')]
        if trampoline[0]!=0x0a or int.from_bytes(trampoline[1:],'little')!=target:
            raise ValueError('Compiled trampoline differs.')
        body=rom[target-0xC00000:target-0xC00000+6]
        if body!=b'\x1a\x0c'+labels[('run_stamina_mechanic','stamina_reset')].to_bytes(3,'little')+b'\0':
            raise ValueError('Recovery reset prelude changed.')
        if mapping[address]!=mapping[original]:raise ValueError('Reviewed native recovery alias changed.')
        reviews.append({'originalAddress':f'{address:06X}','compiledOriginalBody':f'{original:06X}',
                        'compiledHookTarget':f'{target:06X}','nativeEntryAddress':mapping[address],
                        'classification':'native-script-entry-adaptation',
                        'reviewDecision':'Reset stamina once on entry, then execute the existing converted recovery body. Loop continuations do not reset stamina.',
                        'compiledTrampolineAndResetCallChecked':True,'originalAndCompiledNativeAliasesMatch':True})
    report={'Passed':True,'format':'redux-recovery-hook-review-v1','upstreamCommit':PIN,
            'module':relative,'sourceSha256':hashlib.sha256(data).hexdigest(),
            'compiledRomSha256':ROM_SHA,'packSha256':hashlib.sha256(a.assets.read_bytes()).hexdigest(),
            'activeWritesReviewed':len(reviews),'reviews':reviews,'nativeReferences':refs,
            'portingIssue':'Original bodies and callers were relocated; the literal ROM trampolines and excluded helper module did not intercept the converted calls. Native hooks now bind both CALL/direct starts and JUMP entry paths.',
            'runtimeEvidence':'validation/native-redux-recovery-dev6.json; validation/native-runtime-regressions-dev6.json',
            'symbolPresenceProvesBehavior':False,'completePatchAudit':False,'fullPlaythroughVerified':False,
            'limits':['Prepared four-member recovery fixtures and real dispatcher checks, not ordinary hotel/hot-spring gameplay or every rest location.','Other active patch modules require separate semantic review.']}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'Passed':True,'activeWritesReviewed':len(reviews),'completePatchAudit':False}))


if __name__=='__main__':main()
