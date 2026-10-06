# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify reusing the Original story policy for the donor-extracted ghost pack."""
import argparse,hashlib,json
from pathlib import Path
from build_maternalbound_pack import read_pack

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('legacy-pack','fresh-pack','native-source','legacy-policy','derived-policy','source-audit','output'):
  p.add_argument('--'+name,required=True,type=Path)
 a=p.parse_args();old=json.loads(a.legacy_policy.read_text());new=json.loads(a.derived_policy.read_text())
 oe,oh,ob=read_pack(a.legacy_pack,a.native_source/'src/data/runtime_generated/asset_ids.h')
 ne,nh,nb=read_pack(a.fresh_pack,a.native_source/'src/data/runtime_generated/asset_ids.h')
 checks={
  'Legacy pack is the currently audited Original base':sha(a.legacy_pack)==old['BaseHash']=='4e01c943711d32c41e85cb858d9058169e7c8b1739fc7dc0a211e441f9631b9b',
  'New source-derived policy identifies the exact new Original pack':sha(a.fresh_pack)==new['BaseHash']=='01af4f4b590d9e83937b772399ee60a9181e2384e13c1567c94dfc92101b5549',
  'Asset IDs and layout header identical':oe==ne and oh==nh,
  'Only the movement container changes':sorted(k for k in ob if ob[k]!=nb[k])==['US/events/bank_c3_scripts_combined.bin'],
  'Item protections source-derived and identical':old['ProtectedItems']==new['ProtectedItems'],
  'Scripted-battle enemy protections source-derived and identical':old['ProtectedEnemies']==new['ProtectedEnemies'],
  'Content identity, display name and CRC polynomial identical':all(old[k]==new[k] for k in ('ContentId','DisplayName','SaveStateCrcPolynomial')),
  'Derived native save format is 16':new['SaveStateVersion']==16,
 }
 audit=json.loads(a.source_audit.read_text())
 checks['Full original dialogue decode contains no unknown control codes']=audit['UnknownCodes']=={} and audit['ScriptBlocks']==61 and audit['DecodedEntries']==61972
 report={'Passed':all(checks.values()),'Checks':checks,'LegacyPackSha256':sha(a.legacy_pack),'NewPackSha256':sha(a.fresh_pack),'LegacyPolicySha256':sha(a.legacy_policy),'DerivedPolicySha256':sha(a.derived_policy),'SourceAuditSha256':sha(a.source_audit),'ProtectedItemCount':len(new['ProtectedItems']),'ProtectedEnemyCount':len(new['ProtectedEnemies']),'UnchangedAssetCount':sum(ob[k]==nb[k] for k in ob),'OldRegistrySaveStateVersion':old['SaveStateVersion'],'ActualNativeSaveStateVersion':new['SaveStateVersion'],'Limits':['Source-derived story and table invariants; no full story or randomized playthrough proof.','New Original seeds use the exact new pack hash. Existing seeds retain their prior identity and must not be migrated by relabeling.','Missing ghost bytecode extraction/runtime is separately checked by the pack and interpreter reports.'],'FullPlaythroughVerified':False}
 a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))
 if not report['Passed']:raise SystemExit(1)
if __name__=='__main__':main()
