from pathlib import Path
root=Path(__file__).resolve().parent.parent
base=root/'native-source/src/data/tests/fixtures/bin'
files={'data/foo.bin':b'foo-bytes','data/bar.bin':b'bar-bytes-longer','US/data/greeting.bin':b'hello'}
for i in [0,1,3]:files[f'maps/palettes/{i}.pal']=bytes([i])*32
for name,data in files.items():
 p=base/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
