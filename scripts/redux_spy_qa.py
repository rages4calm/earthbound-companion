# SPDX-License-Identifier: GPL-3.0-or-later
"""Replay prepared Spy action stages with normal buttons and cold restores.

Uses a copied target-confirmed four-member battle fixture (enemy 159). No Jev
requests, story advancement claims or player-folder writes. Every run is
preserved below _BuildScratch/jev-runs.
"""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from jev_gameplay_runner import initialize, load_run, observe_step

BUTTONS = (None, 'right', 'down') + ('confirm',)*18
EXPECTED = {8: 'Offense is 5!', 9: 'Defense is 3!', 10: 'Speed is 77!'}


def review(directory):
    directory, run = load_run(directory)
    rows=[]
    for index, button in enumerate(BUTTONS):
        folder=directory/f'{index:04d}'
        action=json.loads((folder/'step.json').read_text(encoding='utf-8'))['action']
        if action != {'button':button,'frames':1,'settle':80}:
            raise ValueError('Recorded input differs from the reviewed route.')
        state=json.loads((folder/'state.json').read_text(encoding='utf-8'))
        log=(folder/'native.log').read_text(encoding='utf-8')
        if 'savestate: loaded slot' not in log or 'savestate: wrote slot' not in log:
            raise ValueError('Missing cold restore/capture: '+str(index))
        # Only freshly emitted text establishes the displayed number; carried
        # observer text from an earlier batch is not substituted for rendering.
        text=' | '.join(w['text'] for w in state['windows'] if w['textSource']=='rendered_this_batch')
        if index in EXPECTED and EXPECTED[index] not in text:
            raise ValueError('Missing Spy stat text: '+EXPECTED[index])
        rows.append({'step':index,'button':button,'coldLoaded':True,'captured':True,
                     'freshText':text,'modes':state['modeNames']})
    first=json.loads((directory/'0000/state.json').read_text(encoding='utf-8'))
    final=json.loads((directory/'0020/state.json').read_text(encoding='utf-8'))
    before=next(p for p in first['party'] if p['id']==3)
    after=next(p for p in final['party'] if p['id']==3)
    if before['items'].count(88)!=0 or after['items'].count(88)!=1:
        raise ValueError('Spy did not award exactly one Cookie to Jeff.')
    joined='\n'.join((directory/f'{i:04d}/native.log').read_text(encoding='utf-8') for i in range(len(BUTTONS)))
    if 'PC replay action start: actor=3 action=6 ' not in joined:
        raise ValueError('Spy execution was not entered.')
    if 'PC replay action done: actor=3 action=6 ' not in (directory/'0020/native.log').read_text(encoding='utf-8'):
        raise ValueError('Spy did not return to the battle loop.')
    if 'BATTLE_ACTION' in final['modeNames'] or 'BATTLE_MENU' not in final['modeNames']:
        raise ValueError('Fixture did not return to the next battle menu.')
    result={'Passed':True,'format':'redux-prepared-spy-stages-v1',
            'nativeExeSha256':run['nativeExeSha256'],'packSha256':run['assetsSha256'],
            'seededFixture':True,'ordinaryInputsOnly':True,'TypeSafeRequests':0,
            'expectedEnemy':{'id':159,'offense':5,'defense':3,'speed':77,'item':88},
            'targetStatTextPassed':True,'spyEnteredAndReturned':True,'cookieAwardedExactlyOnce':True,
            'coldStageCheckpoints':len(rows),'steps':rows,'FullPlaythroughVerified':False,
            'Limits':['Prepared four-member battle against Spiteful Crow; not ordinary story progress.',
                      'Covers this stat/vulnerability/item path with a cold restore between inputs; not every enemy, resistance, full-inventory or itemless branch.',
                      'Window text is native observer output; the production cold render and state-parity records are separate evidence.']}
    (directory/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('steps','Limits')},indent=2))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--review-run',type=Path)
    for name in ('checkpoint','native-exe','assets','output'):
        p.add_argument('--'+name,type=Path)
    a=p.parse_args()
    if a.review_run:
        if any((a.checkpoint,a.native_exe,a.assets,a.output)):
            p.error('Review an existing run or supply a fresh replay, not both.')
        review(a.review_run)
        return
    if not all((a.checkpoint,a.native_exe,a.assets,a.output)):
        p.error('Fresh replay requires checkpoint, native-exe, assets and output.')
    initialize(SimpleNamespace(directory=a.output,checkpoint=a.checkpoint,native_exe=a.native_exe,
                               assets=a.assets,fixture_checkpoint=True))
    directory,run=load_run(a.output)
    state=None
    for index,button in enumerate(BUTTONS):
        state=observe_step(directory,run,{'button':button,'frames':1,'settle':80},index,state)
    review(directory)


if __name__ == '__main__': main()
