# SPDX-License-Identifier: GPL-3.0-or-later
"""Append final eight selected callback checks, preserving earlier runtimes."""
import battle_semantic_coverage_ledger_dev16_stats as stats

stats.party.items.steal.empty.latest.ledger.REPORTS += (
    ('research/redux-battle-bomb-coverage-dev16-v5.json',
     'Two complete prepared Bomb callbacks: compact1..4player parties, every primary party slot, source adjacency/order independently machine corroborated with stubbed machine children; actual native variance/damage/text children and restored context. Enemy splash, shields, lethal and full battle behavior unevaluated.'),
    ('research/redux-battle-equipment-coverage-dev16-v5.json',
     'Two complete prepared equipment callbacks: all packed equippable item IDs/four characters, usability/missing controls, source stat/resistance/slot/inventory/retained bonuses, actual weapon attack child completion. UI selection, Teddy compaction and full encounter unevaluated.'),
    ('research/redux-battle-transform-drain-coverage-dev16-v5.json',
     'HP-sucker alias plus Rainbow transformation: actual drain/text/heal and self/dead/luck/side controls; full real group471 constructor/art/layout then27to83 final callback with all78 source bytes, position, art index and cleanup/cursor. KO, species174 absent from initial groups, pixels/full encounters unevaluated.'),
    ('research/redux-battle-prayer-freeze-coverage-dev16-v5.json',
     'Two complete prepared outer callbacks: all ten weighted prayers/source masks/cyclic random selection/actual child order/selected effects, and time-freeze0..4actual hits/source mask filtering/wasted dead targets/entry and exit rolling state. Rockin/Flash child mutations, individual Bash damage, later rolling and full battle/story unevaluated.'),
)


if __name__ == '__main__':
    stats.party.items.steal.empty.main()
