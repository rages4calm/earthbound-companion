# SPDX-License-Identifier: GPL-3.0-or-later
"""Independently compare relocated compiled swirl masks to all pinned PNG frames."""
import argparse,hashlib,json
from pathlib import Path
from PIL import Image
import yaml
from maternalbound_graphics import snes_offset
from swirl_source_consumer_qa_dev24 import decode

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('rom','project','source-review','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve frozen reports')
    report=json.loads(a.source_review.read_text(encoding='utf-8'));rom=a.rom.read_bytes()
    if report['romSha256']!=sha(a.rom)or len(report['sourceRecords'])!=126:raise ValueError('Wrong source record provenance')
    table_path=a.project/'Swirls/swirls.yml';spec=yaml.safe_load(table_path.read_text());checks=[]
    for seq in report['sourceRanges']:
        type=seq['type'];expected=spec[type]
        checks.append(dict(check=f'type{type}-source-metadata',passed=expected['speed']==seq['speed']and expected['frames']==seq['frameCount']))
        for f in range(seq['frameCount']):
            row=report['sourceRecords'][seq['firstFrame']+f];decoded,_=decode(rom[snes_offset(row['sourcePointer'],len(rom)):][:1100]);path=a.project/f'Swirls/{type}/{f:03d}.png'
            im=Image.open(path)
            if im.size!=(256,224)or im.mode!='P':raise ValueError('Pinned swirl PNG shape changed')
            pixels=bytes(im.getdata());derived=bytes(int(a1<=x<=b1 or a2<=x<=b2)for a1,b1,a2,b2 in decoded for x in range(256))
            checks.append(dict(check=f'type{type}-frame{f}-compiled-vs-project',passed=pixels==derived,assetFrame=row['id'],sourceMode=row['sourceMode'],pngSha256=sha(path),derivedMaskSha256=hashlib.sha256(derived).hexdigest(),differingPixels=sum(x!=y for x,y in zip(pixels,derived))))
    result=dict(toolSha256=sha(__file__),sourceReviewSha256=sha(a.source_review),romSha256=sha(a.rom),sourceYamlSha256=sha(table_path),pinnedReduxCommit=report['pinnedReduxCommit'],checks=checks,executedAssertions=len(checks),allPassed=all(x['passed']for x in checks),skippedCases=0,
                limits=['Independent project PNG union-of-two-intervals proof for all126 compiled frames; native production consumers/render evidence is in the separate referenced report.'],ownerWrites=False)
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:result[k]for k in ('allPassed','executedAssertions','skippedCases')}));raise SystemExit(0 if result['allPassed']else 1)
if __name__=='__main__':main()
