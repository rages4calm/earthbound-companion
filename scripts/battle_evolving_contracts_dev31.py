# SPDX-License-Identifier: GPL-3.0-or-later
"""Independent selected battle contracts derived from packed source and ASM.

The RNG algebra follows the original 65816 RAND instructions; this file is not
a native function extractor. Source review is distinct from CPU execution.
"""
import hashlib
import json
from pathlib import Path
import re
import yaml


def next_rng(state):
    a,b=state
    product=(a&255)*(b&255)
    total=((a&255)<<8)+(b&255)+109
    b=total&65535;carry=int(total>65535)
    v=product
    for _ in range(2):v,carry=(v>>1)|(carry<<15),v&1
    saved=v;total=a+(v&3);v=total&65535;carry=int(total>65535)
    v,carry=(v>>1)|(carry<<15),v&1
    if carry:v|=32768
    a=v;v=saved
    for _ in range(2):v,carry=(v>>1)|(carry<<15),v&1
    return v&255,[a,b]


def normal_ai(row,state,enemy_data):
    """One live enemy, no steal/mirror/NPC; retries real extender table entries."""
    enemy,conscious,hp,pp,variable,cursor=row
    if not conscious:return None
    chain=[];rng_calls=0
    for _ in range(32):
        raw=enemy_data[enemy*94:(enemy+1)*94]
        if len(raw)!=94:raise ValueError('Actual enemy outside packed source table')
        order=raw[69]
        if order>=4:return dict(scripted=True,enemy=enemy,cursor=cursor)
        if order in(0,1,3):roll,state=next_rng(state);rng_calls+=1
        if order==0:index=roll&3
        elif order==1:
            roll&=7;index=3 if roll==0 else 2 if roll==1 else 1 if roll<=3 else 0
        elif order==2:index=variable;variable=(variable+1)&3
        elif order==3:index=variable*2+(roll&1);variable=(variable+1)&1
        else:raise ValueError('Unreviewed action order')
        action=int.from_bytes(raw[70+index*2:72+index*2],'little');argument=raw[80+index]
        chain.append(dict(enemy=enemy,order=order,index=index,action=action,argument=argument))
        if action!=245:return dict(scripted=False,enemy=enemy,action=action,argument=argument,variable=variable,selectionRngCalls=rng_calls,chain=chain)
        enemy=argument
    raise ValueError('Source extender loop exceeds bounded selected contract')


def ai_checks(events,enemy_data,action_data):
    inputs={};checks=[]
    for event in events:
        actual=event['actual']
        if event['type']=='QA_AI_INPUT':inputs[actual['turn']]=actual
        if event['type']!='QA_AI':continue
        entry=inputs.get(actual['turn'])
        if entry is None:
            checks.append(dict(turn=actual['turn'],evaluated=False,reason='No actual AI-selection entry boundary.'))
            continue
        live=[(i,r)for i,r in enumerate(entry['enemies'])if r[1]]
        if len(live)!=1:raise ValueError('This source oracle is bounded to one conscious enemy')
        slot,row=live[0];expected=normal_ai(row,entry['rng'],enemy_data);got=actual['enemies'][slot]
        if expected['scripted']:
            # The only active scripted configs in this pin are Kraken49/182.
            # Allowed action/argument check does not certify CC random ordering.
            allowed={49:{(94,0),(248,0),(92,0),(27,18),(117,0)},182:{(94,0),(248,0),(92,0),(27,18),(84,0),(117,0)}}
            valid=got[0]==row[0]and(got[4],got[5])in allowed[row[0]]
            checks.append(dict(turn=actual['turn'],evaluated=True,scope='Active CC AI source actions and no original extender ID change; not independent CC RNG/path equivalence.',actual=got[:6],expectedEnemy=row[0],allowedActions=sorted(allowed[row[0]]),passed=valid))
        else:
            valid=(got[0],got[4],got[5])==(expected['enemy'],expected['action'],expected['argument'])
            checks.append(dict(turn=actual['turn'],evaluated=True,scope='Exact active original-pattern action/argument and extender retries from source RAND and actual pre-selector state.',actual=got[:6],expected=expected,passed=valid))
        data=action_data[got[4]*12:(got[4]+1)*12]
        if len(data)!=12:raise ValueError('Observed action outside packed table')
        # current_target is one-based for single/self targets. Rows/all targets
        # use encoded flags; their complete masks are reviewed at action entry.
        if data[1]==0:
            checks.append(dict(turn=actual['turn'],evaluated=True,scope='Self target from source choose_target',actual=got[6],expected=slot+1,passed=got[6]==slot+1))
    return checks


def source_review(source,project,pack,rom,original):
    references=['asm/system/math/rand.asm','asm/battle/main_battle_routine.asm','asm/battle/choose_target.asm','asm/battle/calc_damage_reduction.asm','asm/battle/ko_target.asm','asm/battle/init_scripted.asm','asm/battle/reset_post_battle_stats.asm',
                'src/game/battle.c','src/game/battle_calc.c','src/game/battle_actions.c','src/game/inventory.c','src/core/math.c','src/core/mode_stack.h']
    refs=[dict(path=p,sha256=hashlib.sha256((source/p).read_bytes()).hexdigest())for p in references]
    checks=[]
    ordered={
        'asm/battle/main_battle_routine.asm':[['@ACTION_PATTERN_1:','JSL RAND','AND #$0003'],['@ACTION_PATTERN_2:','JSL RAND','AND #$0007','@ACTION_PATTERN_2_4TH:','LDA #3'],['@ACTION_PATTERN_3:','battler::action_order_var','INC','AND #$0003'],['@ACTION_PATTERN_4:','ASL','JSL RAND','AND #$0001','AND #$0001'],['@EXTENDER_SET_ID:','battler::current_action_argument','battler::id','JMP @CHECK_POO_MIRROR_ENEMY']],
        'asm/battle/calc_damage_reduction.asm':[['@APPLY_RESIST:','CPY #$00FF','TRUNCATE_16_TO_8'],['@CHECK_CONSCIOUSNESS:','battler::guarding','ACTION_TYPE::PHYSICAL','ASR16'],['@SHIELD_HALVE_DAMAGE:','ASR16','@FLOOR_DAMAGE:','LDA #1'],['@SHIELD_POWER_REFLECT:','ENEMY_PERFORMING_FINAL_ATTACK','ASR16','STA @VIRTUAL02','SWAP_ATTACKER_WITH_TARGET','CALC_DAMAGE','SWAP_ATTACKER_WITH_TARGET'],['@WEAKEN_SHIELD:','battler::shield_hp','DEC','STATUS_GROUP::SHIELD','MSG_BTL_SHIELD_OFF']],
        'asm/battle/reset_post_battle_stats.asm':[['char_struct::afflictions+6','char_struct::afflictions+4','char_struct::afflictions+3','char_struct::afflictions+2']],
    }
    for path,sections in ordered.items():
        text=(source/path).read_text()
        for tokens in sections:
            at=0;found=True
            for token in tokens:
                hit=text.find(token,at)
                if hit<0:found=False;break
                at=hit+len(token)
            checks.append(dict(path=path,orderedTokens=tokens,passed=found,scope='Bounded ordered ASM review, not original CPU execution'))
    enemies=pack['data/enemy_configuration_table.bin'];count=min(231,len(enemies)//94)
    if original:
        owner=Path(rom).read_bytes()
        if hashlib.sha256(owner).hexdigest()!='a8fe2226728002786d68c27ddddf0b90a894db52e4dfe268fdf72a68cae5f02e':raise ValueError('Exact clean Original owner ROM required')
        # Native packing translates names and the two text pointers. Compare
        # all gameplay fields, including all five actions/arguments, rather
        # than incorrectly demanding identical relocated addresses/strings.
        for enemy in range(231):
            source_row=owner[0x159589+enemy*94:0x159589+(enemy+1)*94]
            native_row=enemies[enemy*94:(enemy+1)*94]
            checks.append(dict(enemy=enemy,scope='Original gameplay bytes25..44 and53..93 match the owner ROM; translated name/text pointer bytes excluded',passed=native_row[25:45]==source_row[25:45] and native_row[53:94]==source_row[53:94]))
        refs.extend(dict(path=p,sha256=hashlib.sha256((source/p).read_bytes()).hexdigest()) for p in ('ebtools/parsers/enemy.py','ebtools/cli/pack_all.py'))
    else:
        text=(project/'enemy_configuration_table.yml').read_text()
        fields={'HP':(33,2),'PP':(35,2),'Experience points':(37,4),'Money':(41,2),'Offense':(56,2),'Defense':(58,2),'Speed':(60,1),'Guts':(61,1),'Luck':(62,1),'Action Order':(69,1)}
        for j in range(4):fields[f'Action {j+1}']=(70+j*2,2);fields[f'Action {j+1} Argument']=(80+j,1)
        for enemy in (26,27,39,42,49,83,130,131,173,174,178,181,182,190,202):
            match=re.search(r'^'+str(enemy)+r':[^\n]*\n(.*?)(?=^\d+:|\Z)',text,re.M|re.S)
            if not match:raise ValueError('Pinned selected enemy row missing')
            row=yaml.safe_load(match[1].replace('\t',' '));raw=enemies[enemy*94:(enemy+1)*94]
            for field,(offset,length)in fields.items():
                expected=int(row[field]);actual=int.from_bytes(raw[offset:offset+length],'little')
                checks.append(dict(enemy=enemy,field=field,actual=actual,expected=expected,passed=actual==expected))
        active=[i for i in range(count)if enemies[i*94+69]>=4]
        checks.append(dict(scope='Actual pinned script-AI enablement; exported labels alone do not enable scripts',actual=active,expected=[49,182],passed=active==[49,182]))
        refs.extend(dict(path='pinned-redux/'+p,sha256=hashlib.sha256((project/p).read_bytes()).hexdigest())for p in ('enemy_configuration_table.yml','ccscript/main.ccs','ccscript/redux/enemy_ai.ccs','ccscript/redux/enemy_ai_actions.ccs'))
    return dict(references=refs,checks=checks,allPassed=all(x['passed']for x in checks),limits=['Selected table/ordered source contracts; independent original CPU full encounters are not executed here.','Read-only YAML fragment comments/tabs normalized in memory; pinned source files unchanged.'])
