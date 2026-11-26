"""Export an offline unresolved-case editor or validate its returned JSON; no main import/freeze."""
import argparse
import json
from pathlib import Path

from vlmbench.baseline_contract import inside
from vlmbench.io_utils import write_json
from vlmbench.review_adjudication import export_html,source_context,validate_payload


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['export','validate'])
    p.add_argument('--cases',default='reports/stage1/v16/needs_resolution.json')
    p.add_argument('--summary',default='reports/stage1/v16/aggregation.json')
    p.add_argument('--manifest',default='data/main/reviewed_final_v1/main_reviewed.csv')
    p.add_argument('--html',default='exports/main_review_adjudication_v1.html')
    p.add_argument('--review');p.add_argument('--report');p.add_argument('--require-complete',action='store_true')
    args=p.parse_args();root=Path.cwd().resolve()
    report=inside(root,args.report) if args.report else None
    if report and report.exists():raise ValueError('Preserve previous report; use a new path')
    if args.action=='export':
        if args.review or args.require_complete:p.error('review/require-complete apply to validation')
        if report==inside(root,args.html):raise ValueError('HTML and report paths must be distinct')
        result=export_html(root,html_path=args.html,cases_path=args.cases,summary_path=args.summary,manifest_path=args.manifest)
    else:
        if not args.review:p.error('validate requires --review')
        context,cards=source_context(root,cases_path=args.cases,summary_path=args.summary,manifest_path=args.manifest)
        payload=json.loads(inside(root,args.review).read_text(encoding='utf-8-sig'))
        result=validate_payload(payload,context,cards,require_complete=args.require_complete)
    if report:write_json(report,result)
    print(json.dumps({k:v for k,v in result.items() if k!='context'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
