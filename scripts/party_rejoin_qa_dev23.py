# SPDX-License-Identifier: GPL-3.0-or-later
"""Real native party add/remove regression fixtures; no owner files are written."""
import argparse,json,os,subprocess
from pathlib import Path
import battle_action_catalog_qa as helper

DRIVER=helper.DRIVER[:helper.DRIVER.index('static unsigned pump(void)')]+r'''
#include "game/map_loader.h"
static unsigned long long known(unsigned id){
 unsigned long long bits=0;for(unsigned ability=0;ability<64;ability++)if(check_if_psi_known(id,ability))bits|=1ull<<ability;return bits;
}
static int progress_equal(CharStruct*a,CharStruct*b){
 return !memcmp((unsigned char*)a+5,(unsigned char*)b+5,30) &&
        !memcmp((unsigned char*)a+67,(unsigned char*)b+67,12) &&
        !memcmp((unsigned char*)a+87,(unsigned char*)b+87,5);
}
int main(int argc,char**argv){
 if(argc!=3)return 2;char save[4096];snprintf(save,sizeof(save),"%s/fixture.srm",argv[2]);
 char*boot[]={"party-rejoin-qa","--assets",argv[1],"--session-dir",argv[2],"--save",save,"--allow-redux-development","--headless","--frames","1","--redux-battle-fixture","0"};
 if(eb_platform_main(sizeof(boot)/sizeof(boot[0]),boot)!=0 || !maternalbound_enabled())return 3;
 platform_max_frames=0;platform_input_shutdown();if(!platform_input_init())return 4;
 unsigned cases[][3]={{2,3,1},{2,20,1},{2,65,1},{2,99,1},{4,2,1},{4,16,1},{4,65,1},{4,99,1},
                      {2,65,0},{4,65,0},{2,1,0},{4,15,0},{3,30,1}};
 for(unsigned test=0;test<sizeof(cases)/sizeof(cases[0]);test++){
  unsigned id=cases[test][0],level=cases[test][1],returning=cases[test][2];
  memset(&g_mode_stack,0,sizeof(g_mode_stack));g_mode_stack.depth=1;g_mode_stack.mode[0]=GAME_MODE_NONE;
  initialize_overworld_state();entity_system_init();
  memset(game_state.party_members,0,6);memset(game_state.party_order,0,6);memset(game_state.player_controlled_party_members,0,6);
  game_state.party_members[0]=game_state.party_order[0]=game_state.player_controlled_party_members[0]=1;
  game_state.party_count=game_state.player_controlled_party_count=1;game_state.current_party_members=1;
  game_state.party_npc_1=game_state.party_npc_2=0;
  for(unsigned j=0;j<6;j++){memset(party_characters[j].items,0,14);memset(party_characters[j].equipment,0,4);}
  party_characters[0].level=81;party_ever_joined_mask=1|(returning?(1u<<(id-1)):0);
  reset_char_level_one(id,level,1);CharStruct*c=&party_characters[id-1];
  c->exp+=321;c->base_offense++;recalc_character_postmath_offense(id);
  c->current_hp=c->current_hp_target=c->max_hp-7;c->current_pp=c->current_pp_target=c->max_pp>3?c->max_pp-3:0;
  c->current_hp_fraction=17;c->current_pp_fraction=11;
  initialize_map(5967,5976,0);
  CharStruct before=*c;unsigned long long psi_before=known(id);
  add_char_to_party(id);CharStruct first=*c;unsigned long long psi_after=known(id);
  int preserved=progress_equal(&before,&first);
  remove_char_from_party(id);add_char_to_party(id);int repeat_preserved=progress_equal(&first,c);
  CharStruct duplicate=*c;add_char_to_party(id);int duplicate_preserved=progress_equal(&duplicate,c);
  printf("QA_REJOIN {\"case\":%u,\"character\":%u,\"returning\":%s,\"levelBefore\":%u,\"levelAfter\":%u,\"expBefore\":%u,\"expAfter\":%u,\"progressPreserved\":%s,\"repeatPreserved\":%s,\"duplicatePreserved\":%s,\"knownPsiBefore\":%llu,\"knownPsiAfter\":%llu,\"maskAfter\":%u}\n",test,id,returning?"true":"false",before.level,first.level,(unsigned)before.exp,(unsigned)first.exp,preserved?"true":"false",repeat_preserved?"true":"false",duplicate_preserved?"true":"false",psi_before,psi_after,party_ever_joined_mask);
 }
 return 0;
}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native-source','build','runtime','assets','scratch','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--original',action='store_true');p.add_argument('--expect-regression',action='store_true');a=p.parse_args()
    a.scratch=a.scratch.resolve();a.scratch.mkdir(parents=True,exist_ok=False)
    helper.DRIVER=DRIVER
    if a.original:helper.DRIVER=DRIVER.replace('"--redux-battle-fixture","0"','"--inspect-shuffle"').replace(' || !maternalbound_enabled()',' || maternalbound_enabled()')
    exe,proof=helper.private_build(a)
    result=subprocess.run([str(exe),str(a.assets.resolve()),str(a.scratch)],cwd=a.scratch,
                           env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),capture_output=True,timeout=60)
    log=a.scratch/'native.log';log.write_bytes(result.stdout+result.stderr)
    assert result.returncode==0,result.stderr.decode(errors='replace')[-1600:]
    rows=[json.loads(line[10:]) for line in result.stdout.decode(errors='replace').splitlines() if line.startswith('QA_REJOIN ')]
    assert len(rows)==13,len(rows)
    for row in rows:
        assert row['duplicatePreserved'],row
        assert row['maskAfter']&(1<<(row['character']-1)),row
        if a.expect_regression:
            if row['character'] in (2,4):assert not row['repeatPreserved'],row
            else:assert row['progressPreserved'] and row['repeatPreserved'],row
        else:
            assert row['repeatPreserved'],row
            if row['returning'] or row['levelBefore']>=20:
                assert row['progressPreserved'] and row['knownPsiBefore']==row['knownPsiAfter'],row
            else:
                assert row['levelAfter']==(20 if row['character']==2 else 16) and not row['progressPreserved'],row
    report=dict(version='0.5.0-redux-dev.23',edition='original' if a.original else 'redux',expectedPreviousBuildRegression=a.expect_regression,
                passed=True,privateBuild=proof,packSha256=helper.digest(a.assets),logSha256=helper.digest(log),cases=rows,
                limits=['Prepared live-map fixtures execute production add_char_to_party/remove_char_from_party twice plus a duplicate add.',
                        'Progress compares level, EXP, max HP/PP, ailments, stats, current/fractional HP/PP and boosted stats; native known-PSI masks are compared.',
                        'First-join catch-up, already-higher first joins, returned Paula/Poo, Jeff and duplicate joins are covered. Not every story script, equipment combination or a full playthrough.'],fullPlaythroughVerified=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(edition=report['edition'],regression=a.expect_regression,passed=True,cases=len(rows),returnedLevels=[(r['character'],r['levelBefore'],r['levelAfter']) for r in rows[:8]]),indent=2))

if __name__=='__main__':main()
