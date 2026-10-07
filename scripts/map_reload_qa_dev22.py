# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepared native map-cache and complete Clumsy Robot encounter regressions.

Links a private driver to unchanged production objects. Uses real dispatcher,
menus, attacks, KO, rewards and teleport; prepared party/flags are not ordinary
story reachability. Writes only a fresh scratch session and a JSON report.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

import battle_action_catalog_qa as helper
from battle_full_encounter_qa_dev18 import driver_source


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('native-source', 'build', 'runtime', 'assets', 'scratch', 'output'):
        p.add_argument('--' + name, required=True, type=Path)
    p.add_argument('--original', action='store_true')
    p.add_argument('--expect-regression', action='store_true')
    a = p.parse_args()
    a.scratch = a.scratch.resolve()
    a.scratch.mkdir(parents=True, exist_ok=False)
    source = driver_source(a.original)
    source = source.replace('#include "game/audio.h"', '#include "game/audio.h"\n#include "game/map_loader.h"\n#include "core/decomp.h"\n#include "snes/ppu.h"')
    needle = ' __typeof__(game_state)base_game=game_state;'
    assert source.count(needle) == 1
    cache_checks = r'''
 uint8_t expected_map[0x7000];
 size_t map_bytes=decomp(ASSET_DATA(ASSET_MAPS_GFX(10)),ASSET_SIZE(ASSET_MAPS_GFX(10)),expected_map,sizeof(expected_map));
 if(map_bytes!=sizeof(expected_map))return 10;
 for(unsigned test=0;test<5;test++){
  ow.loaded_map_tile_combo=-1;ml.loaded_tileset_combo=-1;
  initialize_map(5967,5976,0);
  ppu.vram[0]^=0x55;uint8_t changed=ppu.vram[0];
  if(test==1 || test==3)ow.loaded_map_tile_combo=-1;
  if(test==2 || test==3)ml.loaded_tileset_combo=-1;
  if(test==4){ow.loaded_map_tile_combo=9;ml.loaded_tileset_combo=9;}
  load_map_at_sector(5967>>8,5976>>7);
  unsigned mismatches=0;for(unsigned j=0;j<map_bytes;j++)mismatches+=expected_map[j]!=ppu.vram[j];
  printf("QA_CACHE {\"case\":%u,\"bytes\":%zu,\"mismatches\":%u,\"markerPreserved\":%s,\"loadedCombo\":%d,\"overworldCombo\":%d}\n",test,map_bytes,mismatches,ppu.vram[0]==changed?"true":"false",ml.loaded_tileset_combo,ow.loaded_map_tile_combo);
 }
 ow.loaded_map_tile_combo=-1;ml.loaded_tileset_combo=-1;initialize_map(5967,5976,0);
'''
    source = source.replace(needle, cache_checks + needle)
    needle = '  dt.instant_printing=0;case_id=v[0];'
    assert source.count(needle) == 1
    source = source.replace(needle, '  initialize_map(5967,5976,0);\n' + needle)
    needle = '  printf("QA_ENCOUNTER '
    assert source.count(needle) == 1
    source = source.replace(needle, r'''
  const uint8_t *table=ASSET_DATA(ASSET_DATA_TILESET_TABLE_BIN);
  unsigned tileset=table[ml.loaded_tileset_combo*2]+256u*table[ml.loaded_tileset_combo*2+1];
  uint8_t expected[0x7000];size_t size=decomp(ASSET_DATA(ASSET_MAPS_GFX(tileset)),ASSET_SIZE(ASSET_MAPS_GFX(tileset)),expected,sizeof(expected));
  unsigned mismatches=0;for(unsigned j=0;j<size;j++)mismatches+=expected[j]!=ppu.vram[j];
  printf("QA_GRAPHICS {\"case\":%u,\"bytes\":%zu,\"mismatches\":%u,\"loadedCombo\":%d,\"overworldCombo\":%d,\"position\":[%u,%u]}\n",v[0],size,mismatches,ml.loaded_tileset_combo,ow.loaded_map_tile_combo,game_state.leader_x_coord,game_state.leader_y_coord);
''' + needle)
    helper.DRIVER = source
    exe, provenance = helper.private_build(a)
    cases = a.scratch / 'cases.txt'
    cases.write_text('1 462 1 2 999 255 255 0 1\n2 1 1 2 999 255 255 0 1\n', encoding='ascii')
    (a.scratch / 'input.replay').write_text('0 0000\n' + ''.join(f'{frame} 0080\n{frame+2} 0000\n' for frame in range(10, 60000, 8)), encoding='ascii')
    run = subprocess.run([str(exe), str(a.assets.resolve()), str(a.scratch), str(cases)], cwd=a.scratch,
                         env=dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy'), capture_output=True, timeout=60)
    log = a.scratch / 'native.log'
    log.write_bytes(run.stdout + run.stderr)
    rows = {'cache': [], 'graphics': [], 'encounters': []}
    for line in run.stdout.decode(errors='replace').splitlines():
        for prefix, key in [('QA_CACHE ', 'cache'), ('QA_GRAPHICS ', 'graphics'), ('QA_ENCOUNTER ', 'encounters')]:
            if line.startswith(prefix):
                rows[key].append(json.loads(line[len(prefix):]))
    assert run.returncode == 0, run.stderr.decode(errors='replace')[-1500:]
    assert len(rows['cache']) == 5 and len(rows['graphics']) == len(rows['encounters']) == 2
    for row in rows['cache']:
        if row['case'] == 0 or (a.expect_regression and row['case'] == 1):
            assert row['markerPreserved'] and row['mismatches'] == 1, row
        else:
            assert not row['markerPreserved'] and row['mismatches'] == 0, row
    for row in rows['graphics']:
        assert (row['mismatches'] > 0 if a.expect_regression and row['case'] == 1 else row['mismatches'] == 0), row
    for row in rows['encounters']:
        assert row['depth'] == 1 and row['postBattleFlag'] == 0 and row['overworldBattleMode'] == 0 and row['metersStable'], row
    report = dict(version='0.5.0-redux-dev.22', edition='original' if a.original else 'redux',
                  expectedPreviousBuildRegression=a.expect_regression, passed=True, privateBuild=provenance,
                  packSha256=helper.digest(a.assets), logSha256=helper.digest(log), **rows,
                  limits=['Five prepared cache states and two prepared complete scripted encounters, with actual packed graphics compared byte-for-byte.',
                          'Valid unchanged caches preserve modified VRAM; overworld-only, native-only, both-invalid and changed-combo paths are exercised.',
                          'Prepared party, flags and map entry do not certify ordinary story reachability, every tile animation, physical input, audio or a full playthrough.'],
                  fullPlaythroughVerified=False)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(edition=report['edition'], regression=a.expect_regression, passed=True,
                         cache=rows['cache'], graphics=rows['graphics']), indent=2))


if __name__ == '__main__':
    main()
