# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze compact public audio evidence while retaining full private raw reports.

This does not run or alter the game. Every production result, input/source/object
identity, final PCM/log hash and runtime pass/fail is retained. Repetitive memory
callback events remain in unchanged private reports and native event logs.
"""
import argparse,collections,hashlib,json
from pathlib import Path

REPORTS=[f'{profile}-audio-delivery-dev19-v9-{kind}-review.json'
         for profile in('original','redux')for kind in('direct','shops','encounters')]
RETAIN={'QA_AUDIO_INIT','QA_AUDIO_MUSIC','QA_AUDIO_SUMMARY','QA_AUDIO_MUTED',
        'QA_BICYCLE_BEGIN','QA_BICYCLE_END','QA_ENCOUNTER','QA_SNAP','QA_END'}
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in('research','private-archive','tool','runtime','build','output'):
        ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args()
    if a.private_archive.exists():raise ValueError('Use a fresh private archive')
    tool_hash=digest(a.tool)
    expected_runtime={name:digest(a.runtime/name)for name in('player.exe','observer.exe')}
    expected_library=digest(a.build/'game_lib/libearthbound_game.a')
    loaded=[]
    for name in REPORTS:
        path=a.research/name;data=json.loads(path.read_text())
        if data.get('compactEvidence'):raise ValueError('Evidence already compacted')
        if data['toolSha256']!=tool_hash or data['runtimeSha256']!=expected_runtime:
            raise ValueError('Runtime/tool identity mismatch')
        if data['privateBuild']['productionLibrarySha256']!=expected_library:
            raise ValueError('Production library identity mismatch')
        if not data['allPassed']or data['skippedCases']:
            raise ValueError('Cannot freeze failing/skipped suite as all-green evidence')
        if not all(obj['allRawSectionsByteIdentical']for obj in data['privateBuild']['objects']):
            raise ValueError('Instrumented object code/data bytes changed')
        if not all(case['passed']and not case['errors']for case in data['cases']):
            raise ValueError('Actual case failed')
        loaded.append((name,path,data))
    a.private_archive.mkdir(parents=True)
    files=[];cases=processes=0
    for name,path,data in loaded:
        raw_hash=digest(path);(a.private_archive/name).write_bytes(path.read_bytes())
        for case in data['cases']:
            for run in case['runs']:
                events=run['events'];counts=collections.Counter(e['type']for e in events)
                run['eventTypeCounts']=dict(sorted(counts.items()))
                run['actualRequestSequence']=[e['value']['id']for e in events if e['type']=='QA_AUDIO_REQUEST']
                run['actualSpcAcknowledgmentSequence']=[e['value']['command']for e in events if e['type']=='QA_AUDIO_ACK']
                run['actualSpcStartTimeline']=[[e['value']['tick'],e['value']['id']]for e in events if e['type']=='QA_AUDIO_ACCEPT']
                run['actualVoice7KeyOnTimeline']=[[e['value']['tick'],e['value']['id']]for e in events if e['type']=='QA_AUDIO_KEYON']
                run['events']=[e for e in events if e['type']in RETAIN]
        data['compactEvidence']=dict(rawReportSha256=raw_hash,fullRawReportRetainedPrivately=True,
            nativeEventStreamsRetainedPrivately=True,pcmRetainedPrivately=True,
            method='Repeated SPC/DSP callback events compacted into exact ordered numeric request/acknowledgment/start/keyon timelines and event-type counts. All per-run final audio metrics, selected gameplay state, input/source/object/PCM/log identities and pass/fail remain unchanged.',
            compactorToolSha256=digest(Path(__file__)))
        path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
        files.append(dict(path='research/'+name,sha256=digest(path),
            rawReportSha256=raw_hash,cases=data['executedCases'],processExecutions=data['executedProcesses'],
            originalProfile=data['originalProfile'],allPassed=data['allPassed']))
        cases+=data['executedCases'];processes+=data['executedProcesses']
    dependencies=['tools/audio_delivery_qa_dev19.py','tools/freeze_audio_delivery_evidence_dev19.py',
        'tools/shop_transaction_qa_dev18.py','tools/battle_full_encounter_qa_dev18.py',
        'tools/battle_action_catalog_qa.py','tools/battle_food_summon_qa_dev15.py',
        'tools/build_maternalbound_pack.py','research/redux-shop-transaction-fixtures-dev18.json',
        'research/original-shop-transaction-fixtures-dev18.json']
    root=a.tool.parent.parent
    artifact_files=[dict(path=p,sha256=digest(root/p))for p in dependencies]
    manifest=dict(schemaVersion=1,toolVersion='dev19-final-audio-delivery-evidence',
        runtimeVersion='dev16-v9',runtimeSha256=expected_runtime,
        productionLibrarySha256=expected_library,
        sourcePatchSha256=loaded[0][2]['sourcePatchSha256'],
        reduxRevision=loaded[0][2]['pinnedReduxRevision'],
        executedCases=cases,executedProcesses=processes,skippedCases=0,allPassed=True,
        files=[*artifact_files,*files],noNativeChanges=True,noOwnerWrites=True,
        conclusion='No independent audio-delivery defect reproduced in the bounded selected v9 production tests. Cash-register, shop equip, bulk ping and bicycle bell effects reach SPC command starts, generate nonzero voice7 samples and alter the real final SDL mixed PCM against sound-suppressed controls.',
        evidence=[
            'Both Original and pinned Redux profile assets, with normal SPC music and the installed real MSU soundtrack.',
            'Six selected SFX table pointers, preceding header types and complete source macro definitions bytechecked against the actual uploaded initial audio pack. This is separate from runtime consumption/PCM proof.',
            'Forty isolated effect/track/HQ fixtures per profile plus thirty queue/scheduling/mute/track-transition fixtures per profile; actual production queue and SPC interpreter/DSP, no effect engine replaced.',
            'Thirty-eight source-selected real shop transaction fixtures across both profiles: buy, sell, equip and sell old weapon, failed/cancelled purchases, Redux bulk3 and bulk56. Actual text/menu/number children and input replay. Negative audio controls preserve final wallet/inventory/equipment/flags.',
            'Eight full prepared bicycle encounters: actual mount, group1 scripted battle or actual BE_ENTER instant-win predicate, victory, native map reload/exit, retained track82 and R-button movement-consumer bell. Complete encounter state unchanged by audio negative/layout controls.',
            '533/534 versus split128 callback output is byte-identical at equal sample schedules. Real1024 callback delivery uses separate target-suppressed PCM controls; different request latency is allowed.',
            'Private SPC memory callback observers forward each production call exactly once. Copied objects alter symbol visibility/names only, with every raw section hash and uninitialized section size unchanged.',
        ],
        sourceMechanisms=[
            dict(reference='Original asm/spc700/main.spc700.s: READ_PORT / UNK0596 / UNK11DC / UNK1505',
                contract='SPC reads and echoes new port3 commands, then its existing shared effect logic accepts a channel7 sequence and stores its current effect ID at 04B4+X for X=3. Observers separately record port acknowledgment, starts, DSP keyon and generated channel samples. An acknowledgment alone is not an audible effect guarantee.'),
            dict(reference='Pinned ccscript/shops/ShopSys.ccs: Sound_Cash_Register / Sound_Ping / List_Stat_Change',
                contract='Cash register12 or flag-selected ping120; the stat-change/equip stage requests115. The active source parents and production control-code children execute these requests. Declined/insufficient/full-inventory branches assert the expected absence of the transaction-success effect.'),
            dict(reference='Native src/game/audio.c / port/unix/platform/sdl2_audio.c',
                contract='Acknowledgment-aware bounded native64-slot queue; 17066-cycle SPC frame plus DSP resampling and SDL fractional-frame overflow; real MSU mixing and volume applied by the actual callback. Queue overflow deliberately retains recent63, adapting the original eight-slot hardware queue.'),
        ],
        openBoundaries=[
            'Separate source-proven CC19 scripted Yes/No menu sound-default producer gap is owned by the hook audit. These delivery passes do not certify missing producer requests or repair CC19.',
            'No independent SPC emulator or physical SNES audio comparison, subjective listening or speaker/device delivery proof.',
            'Deterministic private scheduling at60Hz and three callback layouts, not exhaustive asynchronous operating-system thread scheduling.',
            'Prepared source-entry fixtures, not natural quest/enemy-contact reachability or whole-game audiovisual parity.',
            'Full effect/track coverage and long fast-forward-overflow retention are not certified; fast-forward intentionally mutes and suspends SPC while the native queue may retain only recent requests.',
        ],fullAudioParityVerified=False,fullPlaythroughVerified=False)
    a.output.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(cases=cases,processExecutions=processes,allPassed=True,
        compactBytes=sum(path.stat().st_size for _,path,_ in loaded),
        manifestSha256=digest(a.output))))
if __name__=='__main__':main()
