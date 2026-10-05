# SPDX-License-Identifier: GPL-3.0-or-later
"""Record the manual native review of the pinned Redux active bugfix imports.

This checks activation, source identity and review references. It does not
execute the referenced branches or assert complete semantic equivalence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

PIN = '897d00833f4a08a0a92f106abf631629a6a6a041'

# Each decision is based on the active body of the pinned .ccs, not its title
# or commented-out suggestions. Tests listed here are targeted coverage only.
# References locate review material; finding a symbol is not a behavior test.
REVIEW = {
 'brainstone_fix': ('native-gameplay', 'Brain Stone possession is checked on the acting character rather than a battle-slot identity.', [('game/battle_actions.c', 'Brain Stone')], 'Production combat action fixture; whole-story inventory paths remain unverified.'),
 'chunked_dma_race_condition_fix': ('different-native-execution', 'Native DMA transfers immediately. There is no asynchronous SNES chunk queue race; movement reads of DMA_Total observe zero.', [('snes/dma.c', 'transfers happen immediately'), ('entity/opcodes.c', 'DMA_Total')], 'Native source review; hardware timing is not reproduced.'),
 'crying_fix': ('native-gameplay', 'Redux also applies the crying miss penalty to enemy attackers.', [('game/battle_calc.c', 'STATUS_2_CRYING')], 'Targeted calculation/action fixtures; all enemy combinations remain unverified.'),
 'dad_bike_phone_fix': ('native-gameplay', 'Suppress Dad phone interruption while bicycling in Redux.', [('game/overworld.c', 'game_state.walking_style == WALKING_STYLE_BICYCLE')], 'Bike/movement fixtures; a full live timed phone event remains unverified.'),
 'equip_anything_fix': ('native-gameplay', 'Equipment identity resolves character inventory and party shifts rather than treating battle slots as character IDs.', [('game/inventory.c', 'maternalbound_equipment_selftest')], '340 equipment previews plus targeted identity fixtures; all story party changes remain unverified.'),
 'enemy_in_walls_fix': ('native-viewport-adaptation', 'Spawn lines stay within loaded collision tiles; native widescreen uses viewport tile counts instead of a fixed 33-column SNES view.', [('game/map_loader.c', 'enemy_in_walls_fix')], 'Movement fixtures and natural Onett combat; all map edges remain unverified.'),
 'exp_overflow_fix': ('native-gameplay', 'Level-99 experience addition uses a wide intermediate and caps the displayed total at 9,999,999.', [('game/inventory.c', '9999999')], 'Targeted overflow fixture; a normal level-99 story run remains unverified.'),
 'gameover_oss_fix': ('native-gameplay', 'Scripted battle losses clear the OSS suppression state before returning to story handling.', [('game/battle.c', 'ow.overworld_status_suppression = 0')], 'Targeted battle result handling; later scripted losses remain unverified.'),
 'guts_fix': ('native-gameplay', 'Redux mortal-blow survival uses the defender Guts value.', [('game/battle_calc.c', 'guts')], '128 Guts trials in native combat fixtures.'),
 'heal_poison_fix': ('native-gameplay', 'Healing without poison returns the proper no-effect message.', [('game/battle_actions.c', 'heal_poison_decide')], 'Actual production action tests for poisoned and unaffected targets.'),
 'hppp_limit_fix': ('native-gameplay', 'Stat growth caps maximum HP and PP at 999 in Redux.', [('game/inventory.c', '999')], 'Targeted growth/limit fixtures; all level-up distributions remain unverified.'),
 'item_transformations_fix': ('native-gameplay', 'Redux invokes timed item transformation processing even after the loaded counter resets.', [('game/overworld.c', 'maternalbound_enabled() || item_transformations_loaded')], 'Native source review; full timed Egg/Chick/Chicken story sequence remains unverified.'),
 'moldyman_initial_frame_fix': ('converted-movement-hook', 'The converted C3 movement bank executes the relocated hook, resting frame 8 and original return address.', [('entity/opcodes.c', 'real patched Moldyman hook')], 'Actual converted movement interpreter fixture; later live encounter remains unverified.'),
 'mushroom_pos_fix': ('native-sprite-adaptation', 'Mushroom sprite positioning uses shallow/deep standing offsets of 8/16 in the native callback.', [('entity/callbacks.c', 'mushroom')], 'Native callback review; multiparty mushroom gameplay remains unverified.'),
 'objfx_controller_fix': ('native-allocation-adaptation', 'Transient object effects allocate from the 22 nonreserved entity slots and avoid party entity ownership.', [('entity/entity.c', '22')], '22-slot allocation fixture; every story effect remains unverified.'),
 'palette_tint_fix': ('native-and-converted-data', 'Native sprite tint uses reference RGB 8A/96/74 and threshold 4. Literal C34E0C elevator bytes 1F/1F/1F are retained in the converted C3 movement bank.', [('game/map_loader.c', 'palette_tint_fix')], 'Source review and converted literal-byte check; live elevator transitions remain unverified.'),
 'party_member_diagonal_fix': ('different-native-rendering', 'The native party callback recomputes screen coordinates from absolute position and camera each frame, avoiding the original direction-gated update. It does not reproduce the SNES 2-pixel threshold algorithm.', [('entity/callbacks.c', 'CB_MOVE_PARTY_SPRITE')], 'Native source review; actual multiparty diagonal speed-change gameplay remains unverified.'),
 'psi_teleport_disable_enemies': ('native-gameplay', 'Teleport begin saves and disables overworld enemy spawning; cleanup restores the saved state.', [('game/overworld_teleport.c', 'TP_BEGIN')], 'Targeted teleport lifecycle fixtures; every map/teleport interruption remains unverified.'),
 'region_crack': ('platform-specific-not-executed', 'Region/protection patches modify SNES boot code. Native PC startup does not execute that 65816 boot path.', [('port/unix/main.c', 'main(')], 'Native startup review; no SNES hardware claim.'),
 'return_item_fix': ('native-gameplay-corrected-dev4', 'CC 1D 15 stores the low 16 bits of the fetched argument before unsigned 16-to-32 multiplication by the first unconscious party position. The former C adapter incorrectly retained high argument bits.', [('game/display_text_cc.c', 'return_item_fix.ccs'), ('game/display_text.c', 'return_item_fix.ccs')], '25 real dispatcher cases, including first unconscious slots 0..4 and zero/direct/high-word operands. Correct fixture reproduced 8 failures before the fix; all 25 now pass.'),
 'rock_candy_fix': ('native-gameplay', 'The random stat choice includes Luck as the fifth outcome.', [('game/battle_actions.c', 'rand_limit(maternalbound_enabled() ? 5 : 4)')], 'Production action/random outcome fixtures; every condiment interaction remains unverified.'),
 'show_removed_battle_item_window': ('native-menu-adaptation', 'A removed battle item is named in the native item window; success and canceled targeting close it.', [('game/battle.c', 'bm_show_item_name')], 'Targeted menu/action tests; all cancel transitions remain unverified.'),
 'single_2bpp_battle_bg_fix': ('native-rendering', 'BG4 points to the blank SC tilemap in the corresponding battle background mode.', [('game/battle_ui.c', 'single_2bpp_battle_bg_fix')], 'Battle-art fixture; every battle backdrop and display setting remains unverified.'),
 'stairs_message_fix': ('native-door-adaptation', 'Stairs transitions avoid original single-pixel nudges and handle bounds/interrupted continuations.', [('game/door.c', 'stairs')], '6 door-bound and 8 interrupted-stairs fixtures; all map stairs remain unverified.'),
 'stats_limit_fix': ('native-gameplay', 'Recalculation, capsule actions and script stat boosts clamp Redux stats to 255.', [('game/inventory.c', '255'), ('game/battle_actions.c', 'capsule cap')], 'Targeted native stat and capsule fixtures; all story growth combinations remain unverified.'),
 'status_window_clear': ('native-menu-adaptation', 'Clear the status window before rendering the next status category.', [('game/text.c', 'clear_window_text(WINDOW_STATUS_MENU)')], 'Targeted UI rendering tests; all four-character condition combinations remain unverified.'),
 'swirls_without_ness_fix': ('native-gameplay', 'Battle swirl follows the current leading party member rather than assuming Ness entity 24.', [('entity/callroutine.c', 'current_party_members')], 'Movement/source review; later Jeff/Poo solo story branches remain unverified.'),
 'teleport_char_snap_fix': ('native-gameplay', 'Party refresh snaps the actual party-order leader before rebuilding follower positions.', [('game/overworld.c', 'refresh_party_entities')], 'Targeted teleport/movement fixtures; all party configurations remain unverified.'),
 'teleport_hardlock_fix': ('native-lifecycle-adaptation', 'Distant entities and their scheduler ownership are removed safely before teleport cleanup.', [('game/overworld_teleport.c', 'TP_CLEANUP')], '128 repeated teleport lifecycle cycles; every live story teleport remains unverified.'),
 'teleport_diamondization_fix': ('native-gameplay', 'The active upstream change shortens the failed-teleport wait from 10 frames to 1. The suggested FULL_PARTY_UPDATE hook is commented out and is not an active requirement.', [('game/overworld_teleport.c', 'maternalbound_enabled() ? 1 : 10')], 'Active-body/source review and teleport fixtures; diamondized-party live gameplay remains unverified.'),
 'tent_check_fix': ('native-bounds-adaptation', 'Reject overflow map coordinates before they wrap into another map sector.', [('game/door.c', 'tent_check_fix')], 'Door/map bounds fixtures; every tent interaction remains unverified.'),
 'text_highlights_fix': ('native-text-adaptation', 'Native highlight dimensions use glyph widths and row bounds instead of copying the original assembly operation.', [('game/window.c', 'maternalbound')], '10 highlight fixtures; every font/title/file-select combination remains unverified.'),
 'thunder_reflect_fix': ('native-gameplay', 'Lightning-badge reflection preserves shield state and restores action targeting after the reflected hit.', [('game/battle_actions.c', 'badge/shield targeting')], 'Production badge/shield/targeting fixtures; every multi-target combination remains unverified.'),
 'tie_zerodiv_fix': ('native-gameplay', 'Simultaneous party/enemy KOs follow defeat handling without entering victory division.', [('game/battle.c', 'tie_zerodiv_fix')], 'Targeted simultaneous-KO fixture; full later-story death sequences remain unverified.'),
 'try_give_money': ('native-command', 'The native adapter retains 32-bit operands and caps cash without signed overflow.', [('game/maternalbound.c', 'maternalbound_money')], '11 money/dispatcher fixtures across give and deposit commands.'),
 'try_deposit_money': ('native-command', 'The native adapter retains 32-bit operands and caps bank deposits without signed overflow.', [('game/maternalbound.c', 'maternalbound_money')], '11 money/dispatcher fixtures across give and deposit commands.'),
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'native-source', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    upstream = a.project.parent
    actual = subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != PIN:
        raise ValueError('Pinned Redux source changed; repeat the manual review.')
    def pinned_bytes(relative):
        expected = subprocess.check_output(['git', '-C', str(upstream), 'show', 'HEAD:Project/' + relative])
        actual = (a.project / relative).read_bytes()
        if expected.replace(b'\r\n', b'\n') != actual.replace(b'\r\n', b'\n'):
            raise ValueError('Working source differs from pin: ' + relative)
        return actual

    source = pinned_bytes('ccscript/main.ccs').decode('utf-8-sig')
    source = re.sub(r'/\*.*?\*/|//[^\n]*', '', source, flags=re.S)
    names = re.findall(r'^\s*import "bugfixes/([^"/]+)\.ccs"', source, re.M)
    if len(names) != len(set(names)) or set(names) != set(REVIEW):
        raise ValueError('Active bugfix imports changed; do not infer coverage.')
    rows = []
    for name in names:
        kind, note, bindings, tests = REVIEW[name]
        path = a.project / 'ccscript/bugfixes' / (name + '.ccs')
        data = pinned_bytes('ccscript/bugfixes/' + name + '.ccs')
        clean = re.sub(r'/\*.*?\*/|//[^\n]*', '', data.decode('utf-8-sig'), flags=re.S)
        refs = []
        for relative, anchor in bindings:
            relative = relative if relative.startswith('port/') else 'src/' + relative
            text = (a.native_source / relative).read_text(encoding='utf-8')
            at = text.find(anchor)
            if at < 0:
                raise ValueError('Review reference missing: ' + relative + ': ' + anchor)
            refs.append({'path': relative, 'line': text[:at].count('\n') + 1, 'anchor': anchor})
        rows.append({'module': name, 'source': 'ccscript/bugfixes/' + name + '.ccs',
                     'sourceSha256': hashlib.sha256(data).hexdigest(), 'classification': kind,
                     'reviewDecision': note, 'nativeReferences': refs, 'targetedCoverageAndLimits': tests,
                     'activeRomWriteExpressions': re.findall(r'^\s*ROM\[([^]\n]+)\]', clean, re.M)})
    record = {'format': 'redux-active-bugfix-review-v1', 'upstreamCommit': PIN,
              'status': 'manual-source-review-with-targeted-tests', 'activeModulesReviewed': len(rows),
              'scope': 'Only direct active bugfix imports in pinned main.ccs. Other modules and literal ROM writes need their separate conversion audit.',
              'symbolPresenceProvesBehavior': False, 'allBranchesVerified': False,
              'fullPlaythroughVerified': False, 'reviews': rows}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'activeModulesReviewed': len(rows), 'allBranchesVerified': False}))


if __name__ == '__main__':
    main()
