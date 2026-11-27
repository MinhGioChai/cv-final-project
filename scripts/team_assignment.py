"""Plan one assigned shard; execution remains with TV1's future shared runner."""
import argparse
import json
from pathlib import Path

from vlmbench.team_handoff import assignment_plan

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['plan'])
    p.add_argument('--assignment',required=True);args=p.parse_args()
    result=assignment_plan(Path.cwd(),args.assignment)
    result.pop('cell_ids')
    print(json.dumps(result,ensure_ascii=False,indent=2))
