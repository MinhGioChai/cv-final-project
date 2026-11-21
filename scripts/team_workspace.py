"""Build/restore private team data; Git carries code, manifests, review JSON and reports."""
import argparse
import json
from pathlib import Path

from vlmbench.io_utils import write_json
from vlmbench.team_bundle import build,restore

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['build','restore'])
    p.add_argument('--archive',default='exports/team_workspace_v1.zip');p.add_argument('--report')
    args=p.parse_args();root=Path.cwd().resolve();path=(root/args.archive).resolve()
    if not path.is_relative_to(root):raise ValueError('Use an archive path inside the project')
    report=None
    if args.report:
        report=(root/args.report).resolve()
        if not report.is_relative_to(root) or report.exists():raise ValueError('Use a new report path inside project')
    result=build(root,path) if args.action=='build' else restore(root,path)
    if report:write_json(report,result)
    print(json.dumps(result,indent=2))
