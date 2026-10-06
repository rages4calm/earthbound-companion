"""Derive conservative Story Shuffle protections from the original game's scripts.

Decode control codes, never scan arbitrary byte patterns. Preserve every literal
item referenced by dialogue (including trade foods), item transformations, and
every enemy in a literal scripted battle. This retains the original story's
dependencies; it does not solve a newly shuffled world.
"""
from pathlib import Path
import argparse, sys, re, json, struct, hashlib
from collections import defaultdict

root = Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pack',type=Path,default=root/'EarthBound Companion/Game/assets.pak')
parser.add_argument('--rom',type=Path,default=root/'ROM/EarthBound (USA).sfc')
parser.add_argument('--native-source',type=Path,default=root/'native-source')
parser.add_argument('--policy-output',type=Path,default=root/'Companion/progression-policy.json')
parser.add_argument('--report-output',type=Path,default=root/'validation/randomizer/progression-audit.json')
args=parser.parse_args()
sys.path.insert(0, str(args.native_source.resolve()))
from ebtools.text_dsl.decoder import decode_text_block
from ebtools.text_dsl.opcodes import OPCODES, ArgType

pack = args.pack.read_bytes()
rom = args.rom.read_bytes()
if hashlib.sha256(rom).hexdigest() != 'a8fe2226728002786d68c27ddddf0b90a894db52e4dfe268fdf72a68cae5f02e':
    raise RuntimeError('Progression audit requires this build\'s verified original USA donor ROM.')
names = re.findall(r'^\s*ASSET_\w+, /\* (.*?) \*/', (args.native_source/'src/data/runtime_generated/asset_ids.h').read_text(), re.M)
blob = 44 + len(names) * 8
def table(name):
    start, size = struct.unpack_from('<II', pack, 44 + names.index(name) * 8)
    return pack[blob + start:blob + start + size]

item_ops = {op.yaml_name: [a.name for a in op.args if a.type == ArgType.ITEM] for op in OPCODES}
item_reasons = defaultdict(set)
battles = defaultdict(set)
source = (args.native_source/'src/data/runtime_generated/text_dialogue_source.c').read_text()
blocks = re.findall(r'\{ (\d+)u, (\d+)u, \d+u, \d+u \}, /\* (\w+) \*/', source)
unknown = defaultdict(int)
operations = 0
for offset, size, name in blocks:
    entries = decode_text_block(rom[int(offset):int(offset)+int(size)], {b: chr(b) for b in range(0x20, 256)})
    for entry in entries:
        operations += 1
        if entry['op'] == 'unknown':
            unknown[name] += 1
        # Debug inventory menus enumerate every item. Preserve even literal
        # name/price lookups in real scripts: trades can pass their requested
        # item through working memory rather than a literal inventory test.
        dependent = name not in ('EDEBUG', 'DEBUG_TEXT') and not (
            name == 'EEXPLGDS' and entry['op'] == 'print_item_name')
        for arg in item_ops.get(entry['op'], []) if dependent else []:
            item = entry[arg]
            if item: item_reasons[item].add(name + ':' + entry['op'])
        if entry['op'] == 'trigger_battle' and entry['enemy_group']:
            battles[entry['enemy_group']].add(name)

transforms = table('data/timed_item_transformation_table.bin')
if unknown: raise RuntimeError(f'Cannot certify script coverage with unknown opcodes: {dict(unknown)}')
for i in range(0, len(transforms), 5):
    for j in (0, 3):
        if transforms[i+j]: item_reasons[transforms[i+j]].add('Timed item transformation')
# Deliberately exclude the Casey bat from replacement pools: its 75% miss rate
# makes it unsuitable as the sole randomized weapon for a story playthrough.
item_reasons[0x1B].add('Casey bat high miss rate')
# Monkey Cave's generic trade handler also passes item IDs through working
# memory. Keep the complete request list explicitly as a second safety net.
for i in (0x5A, 0x5D, 0x5F, 0x7F, 0x8C, 0xA6, 0xB8, 0xBE, 0xE0):
    item_reasons[i].add('Monkey Cave trade request; includes dynamic item arguments')

ptr = table('data/btl_entry_ptr_table.bin')
groups = table('data/enemy_battle_groups_table.bin')
enemy_reasons = defaultdict(set)
for group, locations in battles.items():
    if group * 8 + 8 > len(ptr): raise RuntimeError(f'Invalid scripted battle group {group}')
    pos = struct.unpack_from('<I', ptr, group*8)[0] - 0xD0D52D
    while True:
        if pos < 0 or pos + 1 > len(groups): raise RuntimeError(f'Invalid battle pointer {group}')
        count = groups[pos]
        if count == 0xFF: break
        if pos + 3 > len(groups): raise RuntimeError('Truncated battle group')
        enemy = struct.unpack_from('<H', groups, pos+1)[0]
        if enemy >= 231: raise RuntimeError(f'Invalid enemy {enemy}')
        enemy_reasons[enemy].add(f'Scripted battle {group}: ' + ', '.join(sorted(locations)))
        pos += 3

items = table('data/item_configuration_table.bin')
def item_name(i): return ''.join(chr(b-0x30) for b in items[i*39:i*39+25] if 0x50 <= b <= 0xAD)
state_source = (args.native_source/'src/core/state_dump.c').read_text()
state_version = int(re.search(r'#define STATE_DUMP_VERSION (\d+)', state_source).group(1))
state_polynomial = int(re.search(r'crc = \(crc >> 1\) \^ \((0x[0-9A-F]+)u', state_source).group(1), 16)
policy = dict(ContentId='earthbound-usa', DisplayName='EarthBound (USA)', BaseHash=hashlib.sha256(pack).hexdigest(), ProtectedItems=sorted(item_reasons), ProtectedEnemies=sorted(enemy_reasons), SaveStateVersion=state_version, SaveStateCrcPolynomial=state_polynomial)
args.policy_output.parent.mkdir(parents=True,exist_ok=True)
args.policy_output.write_text(json.dumps(policy, indent=2)+'\n', encoding='utf-8')
report = dict(**policy, ScriptBlocks=len(blocks), DecodedEntries=operations, UnknownCodes=dict(unknown),
              Items=[dict(Id=i, Name=item_name(i), Reasons=sorted(v)) for i,v in sorted(item_reasons.items())],
              Enemies=[dict(Id=i, Reasons=sorted(v)) for i,v in sorted(enemy_reasons.items())])
args.report_output.parent.mkdir(parents=True,exist_ok=True)
args.report_output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(f'Decoded {len(blocks)} script blocks / {operations} entries. Protected {len(item_reasons)} items and {len(enemy_reasons)} scripted-battle enemies.')
print('Unknown opcode counts:', dict(unknown))
print('Protected trade/food items:', [(i, item_name(i)) for i in item_reasons if items[i*39+25] in (32,36,40,44,48)])
