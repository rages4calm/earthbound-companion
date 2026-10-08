# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify corrected cast extraction against source operands and a previous pack."""
import argparse,hashlib,json
from pathlib import Path
from build_maternalbound_pack import read_pack

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('native-source','rom','previous-pack','current-pack','output'):
  p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
 hashes={k:digest(getattr(a,k.replace('-','_'))) for k in ('rom','previous-pack','current-pack')}
 raw=a.rom.read_bytes()
 if len(raw)%32768==512:raw=raw[512:]
 # The actual LDA.l instruction consuming PARTY_MEMBER_CAST_TILE_IDS, not
 # merely a pattern search that can match other copies of these words.
 assert raw[0x4e814:0x4e818]==bytes.fromhex('bfb5fdc3'),'source consumer operand'
 wanted=raw[0x3fdb5:0x3fdbd]
 assert wanted==bytes.fromhex('80019001a001b001'),'source tile layout'
 ids=a.native_source/'src/data/runtime_generated/asset_ids.h'
 before=read_pack(a.previous_pack,ids)[2];after=read_pack(a.current_pack,ids)[2]
 changed=[k for k in before if before[k]!=after[k]]
 assert changed==['ending/party_cast_tile_ids.bin'],changed
 assert after[changed[0]]==wanted
 assert hashes=={k:digest(getattr(a,k.replace('-','_'))) for k in hashes},'read-only inputs'
 a.output.write_text(json.dumps(dict(passed=True,inputSha256=hashes,assetCount=len(before),changedAssets=changed,unchangedAssets=len(before)-1,consumerRomOffset=0x4e814,tableRomOffset=0x3fdb5,sourceTileIds=[384,400,416,432],inputsUnchanged=True,limits=['Pack contents and actual source operand checked; serialization padding can differ. Native cast rendering is checked by cast_name_raster_qa.py separately.']),indent=2)+'\n')
 print(json.dumps(dict(passed=True,assetCount=len(before),unchangedAssets=len(before)-1)))
if __name__=='__main__':main()
