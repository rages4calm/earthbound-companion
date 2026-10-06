# SPDX-License-Identifier: GPL-3.0-or-later
"""Record actual final occupancy invocation/input identities around the old runner.

The existing frozen occupancy runner remains untouched; its final report does
not itself carry pack hashes, so this new receipt checks all explicit inputs
before and after a newly executed run. Only fresh private scratch/reports write.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    names=('source','builds','runtime','original-assets','redux-assets','original-phone-seed','redux-phone-seed','scratch','output')
    for n in (*names,'receipt'):ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args()
    for n,v in vars(a).items():setattr(a,n.replace('-','_'),v.resolve())
    if a.output.exists() or a.receipt.exists():raise ValueError('Fresh report/receipt required')
    tool=ROOT/'tools/file_select_occupancy_qa_dev18.py'
    inputs={n:getattr(a,n.replace('-','_')) for n in ('original-assets','redux-assets','original-phone-seed','redux-phone-seed')}
    inputs.update({mode+'-executable':a.runtime/(mode+'.exe') for mode in ('player','observer')})
    inputs.update({mode+'-archive':a.builds/mode/'game_lib/libearthbound_game.a' for mode in ('player','observer')})
    before={n:dict(path=str(p),sha256=sha(p)) for n,p in inputs.items()};toolhash=sha(tool)
    command=[sys.executable,str(tool)]
    for n in names:command.extend(('--'+n,str(getattr(a,n.replace('-','_')))))
    result=subprocess.run(command,timeout=900)
    if result.returncode:raise ValueError('Actual final occupancy run failed')
    after={n:dict(path=str(p),sha256=sha(p)) for n,p in inputs.items()}
    report=json.loads(a.output.read_text(encoding='utf-8'))
    if before!=after or toolhash!=sha(tool) or not report['allPassed']:raise ValueError('Final inputs drifted or selected proof failed')
    receipt=dict(format='actual-final-occupancy-invocation-receipt-dev18-v2',wrapperSha256=sha(Path(__file__)),runnerSha256=toolhash,command=command,inputsBefore=before,inputsAfter=after,allInputsBytePreserved=True,report=dict(path=str(a.output),sha256=sha(a.output)),nativeRunnerExit=0,allSelectedChecksPassed=True,limits=['This receipt executes the unchanged frozen occupancy runner again with explicit actual inputs, recording pack/runtime/phone hashes that its older row schema does not store. No old report is relabeled or overwritten.','Private fresh scratch only; source/builds/owner files and input packs are untouched.'])
    a.receipt.parent.mkdir(parents=True,exist_ok=True);a.receipt.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(receipt=str(a.receipt),sha256=sha(a.receipt),allPassed=True)))

if __name__=='__main__':main()
