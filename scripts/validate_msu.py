from pathlib import Path
import hashlib,json,struct
r=Path(__file__).resolve().parent.parent
manifest=json.loads((r/'research/msu-manifest.json').read_text(encoding='utf-8-sig'))
if isinstance(manifest,dict):manifest=manifest.get('files',manifest)
checked=[]
for item in manifest:
 p=r/'EarthBound Companion/msu'/item['name']
 with p.open('rb') as f:
  header=f.read(8);digest=hashlib.md5(header)
  while b:=f.read(1024*1024):digest.update(b)
 frames=(p.stat().st_size-8)//4
 assert header[:4]==b'MSU1' and frames>0 and (p.stat().st_size-8)%4==0,p.name
 loop=struct.unpack('<I',header[4:])[0];assert loop<frames,(p.name,loop,frames)
 assert digest.hexdigest()==item['md5'],p.name
 checked.append({'track':p.name,'frames':frames,'loop_frame':loop,'md5':digest.hexdigest()})
(r/'validation/msu-audit.json').write_text(json.dumps({'count':len(checked),'all_headers_and_checksums_valid':True,'tracks':checked},indent=2))
print(f'PASS: {len(checked)} PCM headers, lengths, loop points, and MD5 checksums')
