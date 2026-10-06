# SPDX-License-Identifier: GPL-3.0-or-later
"""Use final dev16v1 Thunder/Flash execution without relabeling older evidence."""
import argparse,json
from pathlib import Path
import battle_semantic_coverage_ledger_dev16_flash as flash

ledger=flash.thunder.ledger
ledger.REPORTS=tuple((path.replace('battle-thunder-coverage-dev16.json','battle-thunder-coverage-dev16-v1.json')
    .replace('battle-flash-coverage-dev16.json','battle-flash-coverage-dev16-v1.json'),scope)for path,scope in ledger.REPORTS)


def main():
    flash.thunder.main()
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--output',type=Path,required=True)
    args,_=parser.parse_known_args();result=json.loads(args.output.read_text())
    result['limits'].append('Thunder and Flash were rerun on final dev16v1. Other callback evidence retains its own earlier executed identity; this is a cumulative mixed-build evidence ledger, not a rerun of all 99 callbacks on dev16v1.')
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
