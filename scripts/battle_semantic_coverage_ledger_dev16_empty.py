# SPDX-License-Identifier: GPL-3.0-or-later
"""Append real-dispatch state invariants for exact source-empty callbacks."""
import argparse,json
from pathlib import Path
import battle_semantic_coverage_ledger_dev16_v1 as latest

latest.ledger.REPORTS += (
    ('research/redux-battle-empty-callback-coverage-dev16-v1.json',
     'Twelve exact source-empty callbacks match both owner ROM bodies and preserve seeded native gameplay/RNG state through real production dispatch for all81matching actual action rows. Caller text, item/PP consumption and outer turn remain unevaluated.'),
)


def main():
    latest.flash.thunder.main()
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--output',type=Path,required=True)
    args,_=parser.parse_known_args();result=json.loads(args.output.read_text())
    result['limits'].append('Thunder, Flash and twelve source-empty callbacks execute on final dev16v1. Other callback evidence keeps earlier exact executed identities; this cumulative ledger does not certify a current-build rerun of every listed callback.')
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
