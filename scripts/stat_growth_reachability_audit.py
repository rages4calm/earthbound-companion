# SPDX-License-Identifier: GPL-3.0-or-later
"""Record bounded source reachability of the stat-growth base0/1 discrepancy.

Consumes a completed independent CPU comparison. This is a source review and
transition check, not a claim of all script/state-write or story reachability.
Owner data is read-only; the sole output is a new JSON report.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from snes_movement_helpers_oracle import sha
from snes_position_arithmetic_oracle import native_body


def ref(path,text,needle):
 start=text.find(needle)
 if start<0:raise ValueError('Reviewed source anchor missing: '+needle)
 return {'Path':path.as_posix(),'Line':text[:start].count('\n')+1,'Anchor':needle}


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('native-source','rom','redux-rom','cpu-review','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args()
 if a.output.exists():raise ValueError('Fresh review output required')
 review=json.loads(a.cpu_review.read_text(encoding='utf-8'))
 if review['Pilot'] or review['ExecutedCalls']!=462237 or review['BaseStatAtLeastTwoMismatchCount'] or set(review['MismatchBaseStatCounts'])!={'0','1'}:raise ValueError('Unexpected completed helper evidence')
 native=a.native_source;inv=native/'src/game/inventory.c';initial=native/'src/intro/file_select.c';cfg=native/'include/config.asm';reset=native/'asm/misc/reset_char_level_one.asm';cc=native/'src/game/display_text_cc.c';battle=native/'src/game/battle_actions.c'
 sources={path:path.read_text(encoding='utf-8') for path in (inv,initial,cfg,reset,cc,battle)}
 if not re.search(r'^\.DEFINE STARTING_STATS 2\s*$',sources[cfg],re.M):raise ValueError('Original starting base stat changed')
 reset_body=native_body(sources[inv],'reset_char_level_one');stage_body=native_body(sources[inv],'level_up_apply_stage');join_body=native_body(sources[inv],'apply_join_level_scaling')
 for name in ('offense','defense','speed','guts','luck','vitality','iq'):
  if not re.search(r'ch->base_'+name+r'\s*=\s*2\s*;',reset_body):raise ValueError('Native starting base stat changed: '+name)
 if 'reset_char_level_one(c + 1, level, 0);' not in sources[initial] or 'reset_char_level_one(char_id, target_level, 1);' not in join_body:raise ValueError('Native initial/join route changed')
 original=a.rom.read_bytes();redux=a.redux_rom.read_bytes();calc=next(r for r in review['SourceMapping'] if r['symbol']=='CALCULATE_STAT_GAIN');pos=int(calc['address'],16)-0xc00000;size=calc['byteEqualLength']
 if original[pos:pos+size]!=redux[pos:pos+size] or hashlib.sha256(original[pos:pos+size]).hexdigest()!=calc['byteEqualSha256']:raise ValueError('Pinned Redux changes original stat helper')
 # Base-stat mutation inventory is bounded to literal member writes. This
 # deliberately does not claim that pointer/serialized/script writes are absent.
 writes=[]
 for path in sorted((native/'src').rglob('*.c')):
  text=path.read_text(encoding='utf-8')
  for m in re.finditer(r'\bbase_(offense|defense|speed|guts|luck|vitality|iq)\s*(?:=(?!=)|\+=|-=|\+\+|--)',text):
   line=text[:m.start()].count('\n')+1;snippet=text.splitlines()[line-1].strip()
   writes.append({'Path':path.as_posix(),'Line':line,'Text':snippet})
 refs=[ref(cfg,sources[cfg],'.DEFINE STARTING_STATS 2'),ref(reset,sources[reset],'LDA #STARTING_STATS'),ref(inv,sources[inv],'void reset_char_level_one('),ref(initial,sources[initial],'reset_char_level_one(c + 1, level, 0);'),ref(inv,sources[inv],'void apply_join_level_scaling('),ref(inv,sources[inv],'static int16_t level_up_apply_stage('),ref(cc,sources[cc],'case 0x0A: c->boosted_iq'),ref(battle,sources[battle],'party_characters[idx].boosted_iq = boost_stat_byte')]
 report={'format':'stat-growth-base-corner-reachability-review-v1','HelperDifferenceConfirmed':True,'CompletedCpuReview':{'Path':a.cpu_review.as_posix(),'Sha256':sha(a.cpu_review),'Calls':review['ExecutedCalls'],'Mismatches':review['MismatchCount'],'MismatchBaseStatCounts':review['MismatchBaseStatCounts']},
  'OriginalAndPinnedReduxHelperByteEqual':True,'HelperAddress':calc['address'],'HelperBytes':size,'HelperSha256':calc['byteEqualSha256'],'OriginalStartingBaseStat':2,'AllSevenNativeStartingBaseStats':2,'NewGameUsesResetPath':True,'JoinScalingUsesResetPath':True,
  'NormalStoryBaseZeroOrOneReachabilityDemonstrated':False,'InitialAndJoinSeedZeroOrOne':False,'ChangeApplied':False,
  'SourceBackedExplanation':'OPTIMIZED_MULT x10 emits ASL/ASL/ADC/ASL without clearing carry. For (base−2) negative at base0/1, original effective subtraction term is−18/−8, versus native full multiplication−20/−10. Positive base2..255 matches all completed contexts. The source branch correctly consumes RAND when diff=1.',
  'SourceReferences':refs,'LiteralBaseStatWrites':writes,'NativeResetBodySha256':hashlib.sha256(reset_body.encode()).hexdigest(),'NativeStageBodySha256':hashlib.sha256(stage_body.encode()).hexdigest(),
  'InputIdentities':{str(path):sha(path) for path in (*sources,a.rom,a.redux_rom,a.cpu_review,Path(__file__))},
  'Limits':['Source initial/reset/join seed review proves these routes initialize base stats to2, not that every later script or deserialized state can never contain0/1.',
   'Stat-boost item/text handlers write boosted_* fields, not the seven base_* growth inputs. Equipment and temporary combat buffs alter recalculated/battler fields.',
   'Literal member-write inventory includes Battler and selftest writes; it is not a complete alias, serialized-save or arbitrary-memory write analysis.',
   'The CPU corpus includes synthetic base bytes; no ordinary playthrough defect or movement/crash consequence is established from this corner.',
   'LEVEL_UP_CHAR silent full-function execution and low-level vitality/IQ branches were not executed in the helper corpus. Native source was left unchanged pending stronger reachability evidence.']}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:report[k] for k in ('HelperDifferenceConfirmed','OriginalAndPinnedReduxHelperByteEqual','InitialAndJoinSeedZeroOrOne','NormalStoryBaseZeroOrOneReachabilityDemonstrated','ChangeApplied')}),flush=True)

if __name__=='__main__':main()
