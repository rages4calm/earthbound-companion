"""Exercise generated data through native consumers and isolated game sessions."""
from pathlib import Path
import subprocess, struct, json, re, os, hashlib
from PIL import Image

root = Path(__file__).resolve().parent.parent
app = root / 'EarthBound Companion'
qa = root / 'validation/randomizer'
exe = app / 'Game/earthbound.exe'
pak = Path((qa / 'native-seed-path.txt').read_text())
session = Path((qa / 'native-session-path.txt').read_text())
env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
layout = json.loads((root / 'Companion/randomizer-layout.json').read_text())
data = pak.read_bytes()
blob = 44 + struct.unpack_from('<I', data, 8)[0] * 8

def table(name):
    offset, length = struct.unpack_from('<II', data, 44 + layout['Assets'][name] * 8)
    return data[blob + offset:blob + offset + length]

def snapshot_story():
    paths = list((app/'Game/saves').glob('*')) + list((app/'Game/screenshots').glob('*'))
    paths += [app/'Game/settings.dat', app/'Game/earthbound.ini', app/'Game/assets.pak']
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}

before = snapshot_story()
def run(name, *args, allow_fail=False):
    result = subprocess.run([str(exe), '--session-dir', str(session), '--assets', str(pak), *args], env=env, capture_output=True, timeout=55)
    log = result.stdout + result.stderr
    (qa / (name+'.log')).write_bytes(log)
    if result.returncode and not allow_fail:
        raise RuntimeError(f'{name} failed ({result.returncode}): ' + log.decode(errors='replace')[-1500:])
    return log.decode(errors='replace')

log = run('native-consumers', '--inspect-shuffle')
npcs = table('data/npc_config_table.bin')
gifts = re.findall(r'SHUFFLE_GIFT (\d+) (\d+)', log)
expected_count = sum(npcs[i] == 2 for i in range(0, len(npcs), 17))
assert len(gifts) == expected_count
for npc, item in gifts:
    assert int(item) == struct.unpack_from('<I', npcs, int(npc)*17+13)[0]
enemies = table('data/enemy_configuration_table.bin')
battlers = re.findall(r'SHUFFLE_ENEMY (\d+) (\d+) (\d+) (\d+) (\d+)', log)
assert len(battlers) == 230
for enemy, hp, offense, defense, speed in battlers:
    index = int(enemy)*94
    assert int(hp) == struct.unpack_from('<H', enemies, index+33)[0]
    assert int(offense) == enemies[index+56] and int(defense) == enemies[index+58]
    assert int(speed) == enemies[index+60]
print(f'PASS: native gift lookup consumes {len(gifts)} randomized gift records; battle initialization consumes {len(battlers)} enemy records', flush=True)

# A nonexistent session directory must fail before any story save/config access.
missing = qa / 'does-not-exist'
result = subprocess.run([str(exe), '--session-dir', str(missing), '--assets', str(pak), '--headless', '--frames', '1'], env=env, capture_output=True, timeout=15)
(qa/'invalid-session.log').write_bytes(result.stdout+result.stderr)
assert result.returncode != 0 and b'Cannot enter requested session directory' in result.stderr

ini = (session/'earthbound.ini').read_text(encoding='utf-8')
ini = '\n'.join(line for line in ini.splitlines() if not line.startswith(('msu_dir=', 'fullscreen=')))
(session/'earthbound.ini').write_text(ini + '\nfullscreen=0\nmsu_dir='+str(app/'msu')+'\n', encoding='utf-8')
rows=[]
for frame in range(300, 5000, 80):
    rows.extend([(frame,'0020'), (frame+2,'0000'), (frame+35,'1000'), (frame+37,'0000')])
replay = qa/'opening.replay'
replay.write_text('\n'.join(f'{frame} {pad}' for frame,pad in rows))
log = run('opening', '--headless', '--input-script', str(replay), '--frames', '12020', '--capture-state', '12000')
assert 'party=1' in log and 'level=1 HP=30' in log and 'savestate: wrote slot' in log
assert (session/'saves/quicksave_1.bin.0').exists() or (session/'saves/quicksave_1.bin.1').exists()
print('PASS: fresh randomized game boots through intro; Ness reaches level 1 / 30 HP; native quick save is written inside this seed session', flush=True)

log = run('resume-1080p', '--windowed', '--load-state', '--frames', '100', '--dump-frame', '20')
assert 'savestate: loaded slot' in log
im=Image.open(session/'screenshot.bmp');assert im.size == (1920,1080) and im.convert('RGB').getbbox() is not None
im.save(qa/'native-1080p.png')
print('PASS: seed resumes in native 1080p output', flush=True)
# Headless checkpoints omit APU state. Start an audio-enabled native session to
# verify the seed's configured absolute MSU path against real PCM playback.
log=run('msu-start', '--windowed', '--skip-intro', '--frames', '480')
assert 'msu: native PCM track 121 (loop)' in log and 'msu: native PCM track 7 (loop)' in log
print('PASS: native seed startup plays shared MSU tracks 121 and 7', flush=True)
assert before == snapshot_story(), 'Normal-story saves, screenshots, original assets or settings changed during isolated native tests'
print('PASS: original story saves/config/assets unchanged; invalid session refuses fallback', flush=True)
(qa/'native-tests.txt').write_text('PASS: native gift/enemy consumers, fresh opening, isolated quick save, resume, 1080p output, shared MSU, invalid-session rejection, original story files unchanged\n')
