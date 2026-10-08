"""Keep Companion's asset IDs tied to the native engine's generated registry."""
from pathlib import Path
import re, json, struct, argparse

root = Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--native-source',type=Path,required=True)
parser.add_argument('--assets',type=Path,required=True)
args=parser.parse_args()
names = re.findall(r'^\s*ASSET_\w+, /\* (.*?) \*/', (args.native_source / 'src/data/runtime_generated/asset_ids.h').read_text(), re.M)
header = args.assets.read_bytes()[:44]
native_hash = re.search(r'ASSET_PACK_LAYOUT_HASH "([a-f0-9]+)"', (args.native_source / 'src/data/runtime_generated/asset_pack_hash.h').read_text()).group(1)
if len(header) != 44 or struct.unpack_from('<I',header,8)[0] != len(names) or header[12:].hex() != native_hash:
    raise RuntimeError('Installed assets and generated native asset registry do not match; rebuild assets first.')
wanted = ['data/npc_config_table.bin', 'data/item_configuration_table.bin', 'data/store_table.bin', 'data/enemy_configuration_table.bin', 'US/events/bank_c3_scripts_combined.bin', 'data/enemy_placement_groups.bin', 'data/enemy_placement_groups_ptr_table.bin', 'data/btl_entry_ptr_table.bin', 'data/enemy_battle_groups_table.bin']
data = dict(Header=header.hex(), Assets={name: names.index(name) for name in wanted})
(root / 'Companion/randomizer-layout.json').write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
