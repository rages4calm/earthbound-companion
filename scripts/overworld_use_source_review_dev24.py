# SPDX-License-Identifier: GPL-3.0-or-later
"""Check selected item/PSI contracts against owner ROM and pinned source tables.

Numeric fields, addresses and hashes only are published. ASM control-flow review
is checked for exact ordered tokens, not represented as SNES CPU execution.
"""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
import yaml
from build_maternalbound_pack import read_pack


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def bounded_yaml(path, item):
    text=Path(path).read_text(encoding='utf-8')
    match=re.search(r'^'+str(item)+r':\s*\n(.*?)(?=^\d+:|\Z)',text,re.M|re.S)
    if not match:raise ValueError('Source row not found')
    return yaml.safe_load(match.group(1))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('native-source','project','original-assets','redux-assets','rom','output'):ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args();checks=[];metadata=[];rom=a.rom.read_bytes()
    _,_,original=read_pack(a.original_assets,a.native_source/'src/data/runtime_generated/asset_ids.h')
    _,_,redux=read_pack(a.redux_assets,a.native_source/'src/data/runtime_generated/asset_ids.h')
    def check(id,passed): checks.append(dict(id=id,passed=bool(passed)))
    raw_tables={}
    doc=(a.native_source/'earthbound.yml').read_text(encoding='utf-8')
    for name,width,ids in [('item_configuration_table',39,[127,128,129,130,133]),('psi_ability_table',15,list(range(23,31))),('battle_action_table',12,[32,33,34,35,36,37,38,39,149,150,151,152,310])]:
        match=re.search(r"name: '"+name+r"'\s+offset: (0x[\dA-F]+)\s+size: (\d+)",doc,re.I)
        offset,size=int(match[1],16),int(match[2]);raw=rom[offset:offset+size];raw_tables[name]=raw
        metadata.append(dict(asset=name,offset=offset,size=size,ownerRomSpanSha256=hashlib.sha256(raw).hexdigest()))
        pack=original['data/'+name+'.bin']
        for i in ids:
            if i*width>=size:continue
            x,y=raw[i*width:(i+1)*width],pack[i*width:(i+1)*width]
            # Native packed dialogue pointers are relocated; numerical fields
            # and original callback addresses remain comparable.
            numeric=(x[25:35]==y[25:35]) if width==39 else (x[:11]==y[:11]) if width==15 else (x[:4]==y[:4] and x[8:]==y[8:])
            check('original-'+name+'-'+str(i)+'-numeric-source',numeric)
    flagbits={'ness can use':1,'paula can use':2,'jeff can use':4,'poo can use':8,
              'item can be transformed':16,'cannot be given away':32,'cannot be dropped':64,'item disappears when used':128}
    for i in [127,128,129,130,133]:
        row=bounded_yaml(a.project/'item_configuration_table.yml',i);raw=redux['data/item_configuration_table.bin'][i*39:(i+1)*39]
        flags=row['Misc Flags'];unknown=set(flags)-set(flagbits)
        check('redux-item-'+str(i)+'-flags-known',not unknown)
        check('redux-item-'+str(i)+'-type-effect-flags',raw[25]==row['Type'] and struct.unpack_from('<H',raw,29)[0]==row['Action'] and raw[28]==sum(flagbits.get(x,0)for x in flags))
    targets={'none':0,'one':1,'random':2,'row':3,'all':4}
    for i in [32,33,34,35,36,37,38,39,149,150,151,152,310]:
        row=bounded_yaml(a.project/'battle_action_table.yml',i);raw=redux['data/battle_action_table.bin'][i*12:(i+1)*12]
        check('redux-action-'+str(i)+'-target-cost-callback',raw[0]=={'party':1,'enemy':0}[row['Direction']] and raw[1]==targets[row['Target']] and raw[3]==row['PP Cost'] and struct.unpack_from('<I',raw,8)[0]==int(row['Code Address'].lstrip('$'),16))
    for i in range(23,31):
        row=bounded_yaml(a.project/'psi_ability_table.yml',i);raw=redux['data/psi_ability_table.bin'][i*15:(i+1)*15]
        check('redux-psi-'+str(i)+'-availability-action',raw[2]==row['Type'] and bool(raw[3]&1)==(row['Usability Outside of Battle']=='usable') and struct.unpack_from('<H',raw,4)[0]==row['Action'] and list(raw[6:9])==[row['Level learned by Ness'],row['Level learned by Paula'],row['Level learned by Poo']])
    flows={
        'asm/overworld/use_item.asm': [('target-cancel-before-consume',['JSR DETERMINE_TARGETTING','BNE @CHECK_CONSUME_ITEM','LDA #0','JMP @RETURN','@CHECK_CONSUME_ITEM:','AND #ITEM_FLAGS::CONSUMED_ON_USE','JSR REMOVE_ITEM_FROM_INVENTORY','@SETUP_ACTION_WINDOW:'])],
        'asm/overworld/open_menu.asm': [('exact-primary-guard',['@GOODS_ITEM_SELECTED:','LDA #4','CLC','SBC @VIRTUAL02','BRANCHLTEQS @GOODS_ITEM_SELECTED_ALIVE','LDX #1','@GOODS_ITEM_SELECTED_ALIVE:','LDX #$0000'])],
        'asm/text/menu/overworld_psi_menu.asm':[('cancel-before-charge',['@HANDLE_RESULT:','BEQL @PSI_ABILITY_LOOP','BEQL @CHARACTER_SELECT','LDY #1','JSL REDUCE_PP_TARGET']),('all-party-loop',['CPY #$00FF','BNEL @AFTER_CHAR_SELECT0','@MULTI_CHARACTER2:','game_state::party_members','JSR SET_BATTLE_TARGET_NAME','JSL BATTLE_INIT_PLAYER_STATS','JSL JUMP_TEMP_FUNCTION_POINTER','char_struct::afflictions'])],
        'asm/battle/actions/healing_alpha.asm':[('alpha-priority',['CMP #STATUS_0::COLD','CMP #STATUS_0::SUNSTROKE','CMP #STATUS_2::ASLEEP'])],
        'asm/battle/actions/healing_beta.asm':[('beta-priority',['CMP #STATUS_0::POISONED','CMP #STATUS_0::NAUSEOUS','CMP #STATUS_2::CRYING','CMP #STATUS_3::STRANGE','JSL BTLACT_HEALING_A'])],
        'asm/battle/actions/healing_gamma.asm':[('gamma-priority',['CMP #STATUS_0::PARALYZED','CMP #STATUS_0::DIAMONDIZED','CMP #STATUS_0::UNCONSCIOUS']),('gamma-revival',['LDA #192','JSR SUCCESS_255','BEQ @REVIVE_FAILED','LSR','LSR','JSR REVIVE_TARGET'])],
        'asm/battle/actions/healing_omega.asm':[('omega-revival',['CMP #STATUS_0::UNCONSCIOUS','LDA a:battler::hp_max,X','JSR REVIVE_TARGET','JSL BTLACT_HEALING_G'])],
        'asm/battle/success_255.asm':[('strict-192-comparison',['JSR RAND_LONG','CMP @VIRTUAL00','BCS @FAIL'])],
        'asm/battle/revive_target.asm':[('revive-clears-all-groups',['STATUS_GROUP::SHIELD','STATUS_GROUP::HOMESICKNESS','STATUS_GROUP::CONCENTRATION','STATUS_GROUP::STRANGENESS','STATUS_GROUP::TEMPORARY','STATUS_GROUP::PERSISTENT_HARDHEAL','STATUS_GROUP::PERSISTENT_EASYHEAL'])],
        'asm/battle/recover_hp.asm':[('lifeup-KO-guard',['CMP #1','BNE @RETURN','CMP #1','BEQ @HEAL_BLOCKED','JSR SET_HP'])]
    }
    source=[]
    for path,contracts in flows.items():
        text=(a.native_source/path).read_text(encoding='utf-8');source.append(dict(path=path,sha256=sha(a.native_source/path)))
        for id,tokens in contracts:
            pos=0;ok=True
            for token in tokens:
                found=text.find(token,pos)
                if found<0:ok=False;break
                pos=found+len(token)
            check('source-flow-'+id,ok)
    output=dict(schemaVersion=1,toolVersion='dev24-source-selected-overworld-use-contracts',toolSha256=sha(__file__),reduxRevision='897d00833f4a08a0a92f106abf631629a6a6a041',
                ownerRomSha256=sha(a.rom),originalPackSha256=sha(a.original_assets),reduxPackSha256=sha(a.redux_assets),
                nativeSnapshot=str(a.native_source),sourceReferences=source,originalTableSpans=metadata,
                pinnedTables=[dict(path=p,sha256=sha(a.project/p))for p in ('item_configuration_table.yml','psi_ability_table.yml','battle_action_table.yml')],checks=checks,allPassed=all(c['passed']for c in checks),
                limits=['Selected numeric Original ROM table rows, active pinned table rows and ordered disassembly/source tokens only. This is not original SNES CPU execution or every source branch proof.','No ROM/dialogue/graphics bytes published. Full-menu runtime execution and cold children are recorded separately.'])
    a.output.write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(checks=len(checks),failed=[c for c in checks if not c['passed']])))
    if not output['allPassed']:raise SystemExit(1)


if __name__=='__main__':main()
