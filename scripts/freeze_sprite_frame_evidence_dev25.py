# SPDX-License-Identifier: GPL-3.0-or-later
"""Freeze all-frame sprite source/upload evidence against integrated dev.18-v2."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def identity(path):return dict(path=str(Path(path).resolve().relative_to(ROOT)).replace('\\','/'),sha256=sha(path))

def main():
    path=ROOT/'research/sprite-frame-upload-dev25-dev18-v2-final-review.json'
    output=ROOT/'research/sprite-frame-upload-dev25-dev18-v2-manifest.json'
    if output.exists():raise ValueError('Refusing to overwrite frozen manifest')
    report=json.loads(path.read_text(encoding='utf-8'));tool=ROOT/'tools/sprite_frame_upload_qa_dev25.py'
    if not report['allPassed']or report['failures']or report['toolSha256']!=sha(tool):raise ValueError('Final proof not green/identity changed')
    if report['executedAssertions']!=41430:raise ValueError('Final count incomplete')
    inventories=report['inventory']
    if [(x['profile'],x['groups'],x['frames'],x['preparedUploads'])for x in inventories]!=[
        ('Original',464,4029,4955),('Redux',483,4432,5396)]:raise ValueError('Source/consumer corpus changed')
    native=ROOT/'_BuildScratch/audit-dev18-v2-complete-source'
    for relative,digest in report['sourceIdentities'].items():
        if sha(native/relative)!=digest:raise ValueError('Frozen executed source changed')
    runtime=ROOT/'_BuildScratch/audit-dev18-v2-runtime'
    for name,digest in report['runtimeSha256'].items():
        if sha(runtime/name)!=digest:raise ValueError('Frozen runtime changed')
    record=dict(format='sprite-frame-upload-dev25-dev18-v2-manifest-v1',allPassed=True,
        evidenceReport=identity(path),evidenceTools=[identity(tool),identity(Path(__file__))],
        frozenRuntimeProvenance=identity(runtime/'provenance.json'),
        frozenFullNativePatch=identity(ROOT/'_BuildScratch/audit-dev18-v2-source/native-companion.patch'),
        production=report['production'],runtimeSha256=report['runtimeSha256'],
        sourceIdentities=report['sourceIdentities'],pinnedReduxCommit=report['pinnedReduxCommit'],
        executedAssertions=41430,preparedUploads=10351,sourceFrameComparisons=8461,
        registryGroups=947,zeroLengthPlaceholders=2,skippedCases=0,
        sourceScope='483 Redux project-declared groups/4432 frames;464 Original groups/4029 contiguous source slots. Only group0 is a zero-length placeholder in each profile.',
        normalizedBankCoverage='All packed source frame bytes and low pointer flag bits compare directly with compiled source. The actual Redux bank-container loader shadows retained banks12-15 correctly for this full frame corpus.',
        actualConsumerCoverage='Dry production render for every nonempty source frame; first frame of each group also runs shallow/deep water at two split/boundary VRAM destinations. Return value, displayed flags, geometry, full bounded OBJ-region upload checksum and surrounding sentinel guards agree with source assembly contracts.',
        directPaletteCoverage='All8 packed sprite palettes per profile equal source bytes; actual live palette consumers are separate coverage.',
        casesByProfile=[{key:item[key]for key in('profile','groups','frames','preparedUploads','zeroLengthGroups')}for item in inventories],
        profiles=report['profiles'],limits=report['limits'],
        naturalStoryCoverageExpanded=False,fullAudiovisualParityVerified=False,
        confirmedDefects=[],ownerWrites=False,sharedSourcesModifiedByThisTask=False,
        redistributableGameAssetsIncluded=False)
    output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(manifest=identity(output),allPassed=True,executedAssertions=41430,preparedUploads=10351)))

if __name__=='__main__':main()
