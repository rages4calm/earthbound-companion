"""Keep Companion's asset IDs tied to the native engine's generated registry."""
from pathlib import Path
import re, json, struct

root = Path(__file__).resolve().parent.parent
names = re.findall(r'^\s*ASSET_\w+, /\* (.*?) \*/', (root / 'native-source/src/data/runtime_generated/asset_ids.h').read_text(), re.M)
header = (root / 'EarthBound Companion/Game/assets.pak').read_bytes()[:44]
native_hash = re.search(r'ASSET_PACK_LAYOUT_HASH "([a-f0-9]+)"', (root / 'native-source/src/data/runtime_generated/asset_pack_hash.h').read_text()).group(1)
if len(header) != 44 or struct.unpack_from('<I',header,8)[0] != len(names) or header[12:].hex() != native_hash:
    raise RuntimeError('Installed assets and generated native asset registry do not match; rebuild assets first.')
wanted = ['data/npc_config_table.bin', 'data/item_configuration_table.bin', 'data/store_table.bin', 'data/enemy_configuration_table.bin']
data = dict(Header=header.hex(), Assets={name: names.index(name) for name in wanted})
(root / 'Companion/randomizer-layout.json').write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
