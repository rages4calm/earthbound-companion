# SPDX-License-Identifier: MIT
"""Bounded Jev-assisted native gameplay, using observations and ordinary inputs.

All writes are confined to a marked run below _BuildScratch/jev-runs. The
runner never edits SRAM, positions, flags, inventory, or decoded quick saves.
"""
from __future__ import annotations
import argparse
import hashlib
import heapq
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / '_BuildScratch' / 'jev-runs'
PAD = {'left': 0x0200, 'right': 0x0100, 'up': 0x0800, 'down': 0x0400,
       'confirm': 0x0020, 'cancel': 0x8000, 'menu': 0x0040}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def run_directory(path):
    original = Path(path).absolute()
    if any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction())
           for p in (original, *original.parents)):
        raise ValueError('A QA run cannot use redirected directories.')
    path = original.resolve()
    if not path.is_relative_to(RUNS.resolve()) or path == RUNS.resolve():
        raise ValueError('Use an isolated run inside _BuildScratch/jev-runs.')
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError('A QA run cannot use symlinked directories.')
    return path


def mode_names():
    header = (ROOT / 'native-source/src/core/mode_stack.h').read_text()
    header = re.sub(r'/\*.*?\*/', '', header, flags=re.S)
    body = header[header.index('GAME_MODE_NONE'):]
    body = body[:body.index('} GameMode')]
    return {str(i): name for i, name in enumerate(re.findall(r'GAME_MODE_([A-Z_]+)', body))}


def initialize(args):
    directory = run_directory(args.directory)
    if directory.exists():
        raise ValueError('Preserve existing runs; choose a new run name.')
    source = args.checkpoint.resolve()
    if not source.is_relative_to((ROOT / '_BuildScratch').resolve()):
        raise ValueError('Initialize only from a copied QA checkpoint, never player saves.')
    source_exe, source_assets = args.native_exe.resolve(), args.assets.resolve()
    source_saves = list((source / 'saves').glob('quicksave_1.bin.*'))
    if not source_saves:
        raise ValueError('An ordinary-input QA checkpoint is required.')
    for required in (source_exe, source_exe.with_name('SDL2.dll'), source_assets):
        if not required.is_file():
            raise ValueError('Missing QA runtime file: ' + str(required))
    directory.mkdir(parents=True)
    (directory / 'runtime').mkdir()
    exe, assets = directory / 'runtime/earthbound.exe', directory / 'runtime/assets.pak'
    shutil.copy2(source_exe, exe)
    shutil.copy2(source_exe.with_name('SDL2.dll'), exe.with_name('SDL2.dll'))
    shutil.copy2(source_assets, assets)
    (directory / 'saves').mkdir()
    for save in source_saves:
        shutil.copy2(save, directory / 'saves' / save.name)
    if (source / 'fixture.srm').exists():
        shutil.copy2(source / 'fixture.srm', directory / 'fixture.srm')
    (directory / 'fixture.ini').write_text('companion=1\nfullscreen=0\nwidth=1920\nheight=1080\ninstant_text=1\n', encoding='utf-8')
    write_json(directory / 'run.json', {'schema': 1, 'nativeExe': str(exe), 'assets': str(assets),
               'nativeExeSha256': sha(exe), 'assetsSha256': sha(assets), 'sourceCheckpoint': str(source),
               'runtimeFrozenPerRun': True,
               'modeNames': mode_names(), 'ordinaryInputsOnly': True, 'seededFixture': args.fixture_checkpoint,
               'fullPlaythroughVerified': False})
    print(json.dumps({'initialized': str(directory)}))


def load_run(directory):
    directory = run_directory(directory)
    run = json.loads((directory / 'run.json').read_text())
    if run['schema'] != 1 or not run['ordinaryInputsOnly']:
        raise ValueError('Unsupported QA run.')
    if sha(run['nativeExe']) != run['nativeExeSha256'] or sha(run['assets']) != run['assetsSha256']:
        raise ValueError('Engine or asset content changed; preserve this run and initialize a new one.')
    return directory, run


def observe_step(directory, run, action, index, previous=None):
    if (directory / 'STOP').exists():
        raise InterruptedError('STOP file requested termination.')
    held = int(action.get('frames', 1))
    if not 1 <= held <= 16:
        raise ValueError('Input batches must hold at most 16 frames.')
    button = action.get('button')
    if button is not None and button not in PAD:
        raise ValueError('Unsupported ordinary input.')
    prefix = f'{index:04d}'
    batch = directory / prefix
    batch.mkdir()
    before = batch / 'before-saves'
    shutil.copytree(directory / 'saves', before)
    if (directory / 'fixture.srm').exists():
        shutil.copy2(directory / 'fixture.srm', batch / 'before.srm')
    inputs = batch / 'inputs.replay'
    bits = PAD.get(button, 0)
    inputs.write_text(f'20 {bits:04X}\n{20 + held} 0000\n', encoding='ascii')
    observation = batch / 'observation.json'
    capture = int(action.get('settle', 140))
    if not 80 <= capture <= 600:
        raise ValueError('Unsupported observation interval.')
    command = [run['nativeExe'], '--assets', run['assets'], '--session-dir', str(directory),
               '--save', str(directory / 'fixture.srm'), '--config', str(directory / 'fixture.ini'),
               '--allow-redux-development', '--skip-intro', '--load-state', '--headless',
               '--input-script', str(inputs), '--frames', str(capture + 400),
               '--capture-state', str(capture), '--qa-observation', str(observation)]
    env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
    start = time.monotonic()
    process = subprocess.run(command, env=env, capture_output=True, timeout=30)
    (batch / 'native.log').write_bytes(process.stdout + process.stderr)
    if process.returncode or not observation.exists():
        raise RuntimeError(f'Native step failed: {process.returncode}; see {batch / "native.log"}')
    state = json.loads(observation.read_text())
    if state.get('schema') != 1:
        raise ValueError('Unsupported observation schema.')
    state['modeNames'] = [run['modeNames'].get(str(mode), f'UNKNOWN_{mode}') for mode in state['modes']]
    prior = {w['id']: w for w in (previous or {}).get('windows', [])}
    for window in state['windows']:
        window['textSource'] = 'rendered_this_batch'
        old = prior.get(window['id'])
        if not window['text'] and not window['textResetThisBatch'] and old and old['title'] == window['title']:
            window['text'] = old['text']
            window['textSource'] = 'carried_previous_observation'
    write_json(batch / 'state.json', state)
    write_json(batch / 'step.json', {'action': action, 'nativeSeconds': time.monotonic() - start,
               'ordinaryInputsOnly': True, 'position': state['position'], 'modes': state['modeNames']})
    write_json(directory / 'last-state.json', state)
    return state


def path_turn(state, target):
    """Conservative read-only A*: tile flags are circular 64x64; no game writes."""
    grid = bytes.fromhex(state['collisionHex'])
    if len(grid) != 4096:
        raise ValueError('Invalid collision grid.')
    start = tuple(state['position'])
    xmin, ymin = ((int(c) // 8 - 16) * 8 for c in state['camera'])
    def distance(q):
        return abs(q[0] - target[0]) + abs(q[1] - target[1])
    def clear(x, y):
        if not (xmin + 8 <= x < xmin + 504 and ymin <= y < ymin + 504):
            return False
        # NPCs have collision too. Keep a conservative margin; wandering NPCs
        # are re-observed after every batch instead of assuming a fixed route.
        for npc in state.get('npcs', []):
            nx,ny=npc['position']
            if abs(x-nx)<18 and abs(y-ny)<18:
                # A wandering NPC may already overlap the conservative margin.
                # Permit moving away from it so the planner can escape that
                # margin; forbid approaching or moving deeper into it.
                if not (abs(start[0]-nx)<18 and abs(start[1]-ny)<18 and
                        abs(x-nx)+abs(y-ny)>abs(start[0]-nx)+abs(start[1]-ny)):
                    return False
        return all(not (grid[((y + dy) // 8 % 64) * 64 + (x + dx) // 8 % 64] & 0xC0)
                   for dx in (-8, 0, 7) for dy in (0, 7))
    queue = [(distance(start), distance(start), 0, start)]
    best, parent = {start: 0}, {}
    end, nearest = None, start
    while queue and len(best) < 24000:
        _, _, cost, point = heapq.heappop(queue)
        if cost != best[point]:
            continue
        if distance(point) < distance(nearest):
            nearest = point
        if distance(point) <= 6:
            end = point
            break
        # Single-pixel nodes allow aligning with narrow doors after a movement
        # batch ends on an odd pixel. A 2px lattice can falsely block the exit.
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt, nc = (point[0] + dx, point[1] + dy), cost + 1
            if clear(*nxt) and nc < best.get(nxt, 1e9):
                best[nxt], parent[nxt] = nc, point
                # Equal-cost Manhattan paths prefer progress toward the goal,
                # rather than flooding an entire open rectangle first.
                heapq.heappush(queue, (nc + distance(nxt), distance(nxt), nc, nxt))
    if end is None and distance(nearest) < distance(start) - 12:
        # A far waypoint can lie outside the currently loaded map window.
        # Follow an ordinary, locally checked segment, then observe the next
        # window instead of exhausting the whole grid without moving.
        end = nearest
    if end is None:
        # Door triggers can sit on otherwise solid tiles. Probe only a nearby
        # waypoint with a short ordinary input; native collision still applies.
        if distance(start) <= 24:
            dx, dy = target[0] - start[0], target[1] - start[1]
            button = ('right' if dx > 0 else 'left') if abs(dx) >= abs(dy) and dx else ('down' if dy > 0 else 'up')
            return {'button': button, 'frames': 4, 'target': list(target), 'settle': 140, 'doorProbe': True}
        return None
    path = [end]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()
    if len(path) < 2:
        return None
    direction = (path[1][0] - start[0], path[1][1] - start[1])
    turn = path[1]
    for point in path[2:]:
        if (point[0] - turn[0], point[1] - turn[1]) != direction:
            break
        turn = point
    dx, dy = turn[0] - start[0], turn[1] - start[1]
    if abs(dx)+abs(dy)<=2 and turn!=path[-1]:
        # Fractional native movement can alternate across a one-pixel turn.
        # A short step along the following leg lets native corner sliding align
        # it, instead of repeatedly overshooting the same pixel up and down.
        following=path[path.index(turn)+1]
        nx,ny=following[0]-turn[0],following[1]-turn[1]
        button=('right' if nx>0 else 'left') if nx else ('down' if ny>0 else 'up')
        return {'button':button,'frames':4,'target':list(turn),'settle':140,'cornerProbe':True}
    button = ('right' if dx > 0 else 'left') if dx else ('down' if dy > 0 else 'up')
    return {'button': button, 'frames': min(16, max(1, round((abs(dx) + abs(dy)) / 1.4375))),
            'target': list(turn), 'settle': 140}


def candidates(state, target_npc=None, target=None, heal_character=None, seek_battle=False, check_required=False, known_door=False, use_key_item=None):
    options = {'stop': {'description': 'Stop and preserve the run if evidence is insufficient.', 'input': None}}
    top = state['modeNames'][-1] if state['modeNames'] else 'NONE'
    window = next((w for w in state['windows'] if w['id'] == state['focusWindow']), None)
    if top == 'TEXT_PROMPT':
        options['advance_dialogue'] = {'description': 'Advance the currently waiting dialogue page.',
                                      'input': {'button': 'confirm', 'frames': 1, 'settle': 400}}
    elif top in ('SELECTION_MENU', 'BATTLE_ROW_SELECT', 'BATTLE_ENEMY_SELECT') and window and window['menu']:
        options['cancel_menu'] = {'description': 'Cancel the current menu through the ordinary Back button, without confirming a purchase or item use.',
                                  'input': {'button': 'cancel', 'frames': 1, 'settle': 400}}
        current = next((m for m in window['menu'] if m['index'] == window['selected']), None)
        for item in window['menu']:
            if current is None:
                continue
            if current['index'] == item['index']:
                button = 'confirm'
            else:
                dx, dy = (item['position'][i] - current['position'][i] for i in (0, 1))
                button = ('down' if dy > 0 else 'up') if dy else ('right' if dx > 0 else 'left')
            options['menu_' + str(item['index'])] = {
                'description': f'Select {item["label"]!r} (one observed cursor step at a time; confirmation only when selected).',
                'input': {'button': button, 'frames': 1, 'settle': 140}}
    elif top == 'CHAR_SELECT':
        options['confirm_character_target'] = {'description': 'Confirm the currently selected character through the ordinary targeting interface.',
                                             'input': {'button': 'confirm', 'frames': 1, 'settle': 400}}
    elif top in ('BATTLE_ROW_SELECT', 'BATTLE_ENEMY_SELECT') and state['battle']:
        options['confirm_target'] = {'description': 'Confirm the current battle target using the ordinary targeting interface.',
                                     'input': {'button': 'confirm', 'frames': 1, 'settle': 140}}
    elif state['modeNames'] == ['OVERWORLD']:
        if check_required:
            options['check_empty'] = {'description': 'Press quick Talk/Check before approaching an enemy, reproducing the reported interaction sequence.',
                                      'input': {'button': 'confirm', 'frames': 1, 'settle': 140}}
        elif seek_battle:
            enemies = sorted(state.get('worldEnemies', []),
                key=lambda enemy: sum(abs(enemy['position'][i] - state['position'][i]) for i in (0,1)))
            for enemy in enemies:
                step = path_turn(state, enemy['position'])
                if step:
                    options['approach_enemy_' + str(enemy['slot'])] = {
                        'description': f'Follow the collision-checked path to naturally encounter enemy {enemy["id"]} at {enemy["position"]}.', 'input': step}
        elif heal_character is not None:
            options['open_menu'] = {'description': 'Open the Redux pause menu to choose PSI.',
                                    'input': {'button': 'menu', 'frames': 1, 'settle': 140}}
        elif target_npc is not None:
            npc = next((n for n in state['npcs'] if n['id'] == target_npc), None)
            if npc:
                x, y = npc['position']
                distance = abs(x - state['position'][0]) + abs(y - state['position'][1])
                if distance <= 48:
                    dx,dy=x-state['position'][0],y-state['position'][1]
                    direction,button=((2,'right') if dx>0 else (6,'left')) if abs(dx)>abs(dy) else ((4,'down') if dy>0 else (0,'up'))
                    if state['direction']!=direction:
                        options['face_target']={'description':f'Face NPC {target_npc} with one short ordinary movement input before talking.',
                                                'input':{'button':button,'frames':1,'settle':140}}
                    else:
                        options['talk_target'] = {'description': f'Use quick Talk/Check beside target NPC {target_npc}.',
                                                 'input': {'button': 'confirm', 'frames': 1, 'settle': 400}}
                if distance > 20:
                    # Approach a safe adjacent point, not the NPC's collision center.
                    adjacent = sorted(((x - 24, y), (x + 24, y), (x, y + 32), (x, y - 24)),
                                      key=lambda point: sum(abs(point[i] - state['position'][i]) for i in (0, 1)))
                    for point in adjacent:
                        step = path_turn(state, point)
                        if step:
                            side = 'left' if point[0] < x else 'right' if point[0] > x else 'below' if point[1] > y else 'above'
                            options['approach_target_' + side] = {'description': f'Approach NPC {target_npc} from {side} toward {point}. Try another side if a desk or another NPC blocks this route.', 'input': step}
        elif target is not None:
            step = path_turn(state, target)
            if step is None and known_door and sum(abs(target[i] - state['position'][i]) for i in (0, 1)) <= 64:
                # Door tiles can intentionally be marked solid. This opt-in
                # probe is only for a supplied doorway, never an inferred warp.
                dx, dy = (target[i] - state['position'][i] for i in (0, 1))
                button = ('right' if dx > 0 else 'left') if abs(dx) >= abs(dy) and dx else ('down' if dy > 0 else 'up')
                step = {'button': button, 'frames': 4, 'target': list(target), 'settle': 140, 'doorProbe': True}
            if step:
                options['follow_path'] = {'description': (f'Probe the nearby door waypoint {target} with a short ordinary movement input.' if step.get('doorProbe') else f'Follow the collision-checked path toward waypoint {target}.'), 'input': step}
        if use_key_item is not None and target is not None and sum(abs(target[i] - state['position'][i]) for i in (0, 1)) <= 48:
            options['open_key_menu'] = {'description': f'Open the ordinary pause menu, then choose Keys and the held quest item {use_key_item} to use it at this door. Item availability and use are enforced by the game.',
                                        'input': {'button': 'menu', 'frames': 1, 'settle': 140}}
        if target_npc is not None or target is not None or seek_battle:
            # Local map collision does not account for every movable/sprite
            # object. Offer bounded ordinary sidesteps when a planned route is
            # blocked; the game still enforces its complete collision rules.
            grid=bytes.fromhex(state['collisionHex']);x,y=state['position']
            has_path = any(name.startswith('approach_') or name == 'follow_path' for name in options)
            for button,dx,dy in (('up',0,-6),('down',0,6),('left',-6,0),('right',6,0)):
                map_clear = all(not (grid[((y+dy+sy)//8%64)*64+(x+dx+sx)//8%64]&0xc0) for sx in (-8,0,7) for sy in (0,7))
                if map_clear or not has_path:
                    note = '' if map_clear else ' The coarse map footprint is uncertain here; the native game enforces collision during this bounded probe.'
                    options['reposition_'+button]={'description':f'Take a short ordinary step {button} to get around a blocking NPC or object, then re-observe before continuing the goal.' + note,
                                                  'input':{'button':button,'frames':4,'settle':140}}
    else:
        options['wait_scene'] = {'description': 'Allow the current animation, script, or typewriter text to advance without input.',
                                 'input': {'button': None, 'frames': 1, 'settle': 400}}
    return options


def jev_decide(state, options, goal, recent, navigation_target=None):
    key = os.environ.get('TYPESAFE_API_KEY')
    if not key:
        raise RuntimeError('TypeSafe API credentials are not configured.')
    public_state = {k: state[k] for k in ('position', 'direction', 'partyCount', 'party', 'cash', 'bank',
                                         'music', 'modeNames', 'windows', 'battle', 'battlers', 'npcs', 'keyItems')}
    public_state['battleActor'] = state.get('battleActor')
    public_state['interactingNpc'] = state.get('interactingNpc')
    public_state['worldEnemies'] = state.get('worldEnemies', [])
    public_state['navigationTarget'] = navigation_target
    public_state['coordinateDirections'] = {'right': '+x', 'left': '-x', 'down': '+y', 'up': '-y'}
    body = {'model': 'jev-latest', 'state': {'goal': goal, 'observed': public_state, 'recentActions': recent[-6:]},
            'questions': {'next_action': {'type': 'choice',
                'instructions': 'Choose the available action that best advances `goal` from the current `observed` native game state. Use rendered dialogue and observed menu labels. Survive battles. Avoid repeating ineffective actions. Select stop only if no provided gameplay action can safely advance the goal.',
                'criteria': {key: value['description'] for key, value in options.items()}}}}
    request = urllib.request.Request('https://api.typesafe.ai/v1/systemone',
              data=json.dumps(body).encode(), headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'TypeSafe request failed with HTTP {error.code}.') from None
    answer = result['answers']['next_action']
    if answer['choice'] not in options:
        raise ValueError('Model selected an action outside the current candidate set.')
    return answer['choice'], {'model': result['model'], 'answer': answer, 'usage': result.get('usage'),
                              'seconds': time.monotonic() - start}


def fingerprint(state):
    # Ignore animation ticks, NPC wandering and audio; detect meaningful progress.
    value = {k: state[k] for k in ('position', 'modeNames', 'party', 'eventFlags', 'keyItems', 'battle')}
    value['windows'] = [{k: w[k] for k in ('id', 'selected', 'title', 'text')} for w in state['windows']]
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def avoid_blocked_movement(options, blocked_buttons):
    """Do not ask the model to retry movement already blocked at this position.

    This applies only to navigation actions. Talking, facing an NPC and menu
    inputs keep their ordinary game semantics even if position stays unchanged.
    """
    return {name: option for name, option in options.items()
            if not (name.startswith(('approach_', 'reposition_')) or name == 'follow_path')
            or option['input']['button'] not in blocked_buttons}


def play(args):
    directory, run = load_run(args.directory)
    lock = directory / '.runner.lock'
    with lock.open('x') as handle:
        handle.write(str(os.getpid()))
    requests, recent, steps = 0, [], []
    started, reason, dialogue_seen, repeats = time.monotonic(), 'step_limit', False, 0
    battle_seen, checked = False, False
    visited={}
    blocked_buttons = set()
    missed_interactions = set()
    state = None
    try:
        indexes = [int(p.name) for p in directory.iterdir() if p.is_dir() and p.name.isdigit()]
        index = max(indexes, default=-1) + 1
        previous = json.loads((directory / 'last-state.json').read_text()) if (directory / 'last-state.json').exists() else None
        state = observe_step(directory, run, {'button': None, 'frames': 1, 'settle': 140}, index, previous)
        dialogue_seen = args.target_npc is not None and state.get('interactingNpc') == args.target_npc and 'DISPLAY_TEXT' in state['modeNames']
        initial_position = list(state['position'])
        initial_party = {p['id']: dict(p) for p in state['party']}
        index += 1
        for _ in range(args.max_steps):
            if (directory / 'STOP').exists():
                reason = 'stop_file';break
            if time.monotonic() - started >= args.max_seconds:
                reason = 'time_limit';break
            if requests >= args.max_requests:
                reason = 'request_limit';break
            battle_seen |= state['battle']
            if args.heal_character is not None and state['modeNames'] == ['OVERWORLD']:
                player = next(p for p in state['party'] if p['id'] == args.heal_character)
                before = initial_party[args.heal_character]
                if player['hp'] > before['hp'] and player['pp'] < before['pp']:
                    reason = 'healing_completed';break
            if args.battle_complete and battle_seen and not state['battle'] and state['modeNames'] == ['OVERWORLD']:
                reason = 'battle_completed';break
            if args.target and state['modeNames'] == ['OVERWORLD'] and sum(abs(state['position'][i] - args.target[i]) for i in (0, 1)) <= 12:
                reason = 'waypoint_reached';break
            if args.door and state['modeNames'] == ['OVERWORLD']:
                travelled = sum(abs(state['position'][i] - initial_position[i]) for i in (0, 1))
                if args.door_destination:
                    arrived = sum(abs(state['position'][i] - args.door_destination[i]) for i in (0, 1)) <= 24
                    if arrived and travelled > 32:
                        reason = 'door_transition_completed';break
                    if travelled > 512 and not arrived:
                        reason = 'unexpected_door_transition';break
                elif travelled > 512:
                    reason = 'door_transition_completed';break
            if args.target_npc is not None and dialogue_seen and state['modeNames'] == ['OVERWORLD']:
                reason = 'target_conversation_completed';break
            options = candidates(state, args.target_npc, args.door or args.target, args.heal_character,
                                 args.seek_battle and not battle_seen, args.check_before_combat and not checked, args.door is not None, args.use_key_item)
            options = avoid_blocked_movement(options, blocked_buttons)
            options = {name: option for name, option in options.items() if name not in missed_interactions}
            if len(options) == 1 and state['modeNames'] == ['OVERWORLD'] and (args.target or args.door or args.target_npc is not None or args.seek_battle):
                # A blocked fractional corner can disagree with the cached
                # map footprint. Offer the remaining short ordinary probes;
                # the native game enforces collision and progress is observed.
                for button in ('up', 'down', 'left', 'right'):
                    if button not in blocked_buttons:
                        options['reposition_' + button] = {
                            'description': f'The cached path is blocked. Probe {button} for four ordinary frames to escape the corner; the game enforces collision, then re-observe.',
                            'input': {'button': button, 'frames': 4, 'settle': 140}}
            if len(options) == 1:
                reason = 'no_valid_candidate';break
            old_fingerprint = fingerprint(state)
            visited[old_fingerprint]=visited.get(old_fingerprint,0)+1
            if visited[old_fingerprint]>=4:
                reason='repeated_state_cycle';break
            choice, decision = jev_decide(state, options, args.goal, recent, args.door or args.target)
            requests += 1
            write_json(directory / f'decision-{index:04d}.json', {'goal': args.goal, 'candidates': options, **decision})
            if choice == 'stop':
                reason = 'model_requested_stop';break
            action = options[choice]['input']
            before_position, before_modes = list(state['position']), list(state['modeNames'])
            state = observe_step(directory, run, action, index, state)
            if state['position'] != before_position or state['modeNames'] != before_modes:
                blocked_buttons.clear()
                missed_interactions.clear()
            elif choice.startswith(('approach_', 'reposition_')) or choice == 'follow_path':
                blocked_buttons.add(action['button'])
            if choice == 'check_empty':
                checked = True
            if choice == 'talk_target' and 'DISPLAY_TEXT' in state['modeNames'] and state.get('interactingNpc') == args.target_npc:
                dialogue_seen = True
            new_fingerprint = fingerprint(state)
            if choice == 'talk_target' and new_fingerprint == old_fingerprint:
                # The coarse approach radius can offer Talk/Check while the
                # game's exact facing rectangle still misses the object. Try
                # another ordinary approach instead of repeating the miss.
                missed_interactions.add(choice)
            repeats = repeats + 1 if new_fingerprint == old_fingerprint else 0
            row = {'step': index, 'choice': choice, 'position': state['position'], 'modes': state['modeNames'],
                   'action': action, 'beforePosition': before_position,
                   'jevSeconds': decision['seconds'], 'changed': new_fingerprint != old_fingerprint}
            recent.append(row);steps.append(row);print(json.dumps(row), flush=True)
            index += 1
            if repeats >= 3:
                reason = 'no_progress';break
        else:
            reason = 'step_limit'
    except Exception as error:
        reason = 'error'
        write_json(directory / 'error.json', {'type': type(error).__name__, 'message': str(error)})
        raise
    finally:
        write_json(directory / 'results.json', {'stopReason': reason, 'goal': args.goal, 'steps': steps,
                   'requests': requests, 'seconds': time.monotonic() - started,
                   'position': state['position'] if state else None, 'ordinaryInputsOnly': True,
                   'seededFixture': run.get('seededFixture', False),
                   'fullPlaythroughVerified': False, 'nativeExeSha256': run['nativeExeSha256'],
                   'assetsSha256': run['assetsSha256']})
        lock.unlink(missing_ok=True)
    print(json.dumps({'stopReason': reason, 'requests': requests, 'run': str(directory)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    for option in ('directory', 'native-exe', 'assets', 'checkpoint'):
        init.add_argument('--' + option, type=Path, required=True)
    init.add_argument('--fixture-checkpoint', action='store_true', help='Label an explicitly seeded scenario; it cannot establish story progression.')
    run = sub.add_parser('run')
    run.add_argument('--directory', type=Path, required=True)
    run.add_argument('--goal', required=True)
    goal = run.add_mutually_exclusive_group(required=True)
    goal.add_argument('--target-npc', type=int)
    goal.add_argument('--target', type=int, nargs=2)
    goal.add_argument('--door', type=int, nargs=2, help='Approach a known doorway and stop after an ordinary room warp of more than 512 map pixels.')
    run.add_argument('--door-destination', type=int, nargs=2, help='With --door, verify arrival within 24 map pixels of a known destination, including nearby interior rooms.')
    run.add_argument('--use-key-item', type=int, help='With --door, offer ordinary pause-menu input near the door so Jev can select a held key through Keys and Use.')
    goal.add_argument('--battle-complete', action='store_true')
    goal.add_argument('--heal-character', type=int, choices=range(1,5), help='Verify an HP increase and PP use through ordinary PSI menus.')
    run.add_argument('--seek-battle', action='store_true', help='Approach observed overworld enemies before completing a natural battle.')
    run.add_argument('--check-before-combat', action='store_true', help='Press ordinary Talk/Check before approaching the enemy.')
    run.add_argument('--max-steps', type=int, default=30)
    run.add_argument('--max-requests', type=int, default=30)
    run.add_argument('--max-seconds', type=int, default=300)
    args = parser.parse_args()
    if args.command == 'init':
        initialize(args)
    else:
        if (args.seek_battle or args.check_before_combat) and not args.battle_complete:
            parser.error('Encounter options require --battle-complete.')
        if args.door_destination and not args.door:
            parser.error('--door-destination requires --door.')
        if args.use_key_item is not None and (not args.door or not 1 <= args.use_key_item <= 253):
            parser.error('--use-key-item requires --door and an item ID from 1 to 253.')
        if not 1 <= args.max_requests <= 500 or not 1 <= args.max_steps <= 1000 or not 1 <= args.max_seconds <= 3600:
            parser.error('Choose bounded request/step/time limits.')
        play(args)


if __name__ == '__main__':
    main()
