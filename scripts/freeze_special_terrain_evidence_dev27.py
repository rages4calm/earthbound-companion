# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze bounded source-backed tiny-door parent proof identities."""
import argparse,hashlib,json
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('Preserve existing manifest')
 r=json.loads(a.report.read_text());tool=Path(__file__).with_name('special_terrain_parent_qa_dev27.py')
 if not r['allPassed']or r['skippedCases']or r['executedProcesses']!=48 or r['coldCases']!=16 or r['toolSha256']!=sha(tool):raise ValueError('Incomplete or changed final evidence')
 result=dict(schemaVersion=1,status='Passed',allPassed=True,report=dict(path=a.report.as_posix(),sha256=sha(a.report)),tools={p.as_posix():sha(p)for p in (tool,Path(__file__))},runtimeIdentities=r['runtimeIdentities'],production=r['privateBuild'],frozenPatchSha256=r['frozenPatchSha256'],sourceReview=r['sourceReview'],executedProcesses=r['executedProcesses'],coldCases=r['coldCases'],executedAssertions=r['executedAssertions'],executedFollowerAssertions=r['executedFollowerAssertions'],skippedCases=0,scope=r['scope'],nextUnverifiedIntegration=['Ghost/Magicant real source entry parent followed by ordinary movement','Robot landing real source entry parent followed by ordinary movement','Actual dry/shallow/deep route with ordinary input and follower history','Natural stair/rope entry and exit beyond prior selector/helper fixtures'],ownerSavesTouched=False,sharedSourceEdited=False)
 a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:result[k]for k in ('status','executedProcesses','coldCases','executedAssertions','executedFollowerAssertions')}));print('Manifest SHA256 '+sha(a.output))
if __name__=='__main__':main()
