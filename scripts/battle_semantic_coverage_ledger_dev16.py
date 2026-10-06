# SPDX-License-Identifier: GPL-3.0-or-later
"""Extend the frozen dev15 ledger with separately identified physical evidence."""
import battle_semantic_coverage_ledger as ledger


ledger.REPORTS += (
    ('research/redux-battle-physical-coverage-dev16.json',
     'Prepared nonlethal physical callbacks and DoubleBash children; distinct actual action types, weapon miss parameters, crying/nausea penalties, critical/dodge/floor/guard/shield/boss/strangeness branches. Every outer turn and all row variants remain unevaluated.'),
)


if __name__=='__main__':ledger.main()
