"""Export/package main review v2 or import A/B attestations; v1 remains explicit."""
import argparse
import json
from pathlib import Path

from vlmbench.io_utils import atomic_bytes,manifest_bytes,read_manifest,write_json
from vlmbench import main_review as v1
from vlmbench import main_review_v2 as v2

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['export','import','bundle'])
    p.add_argument('--version',choices=['v1','v2'],default='v2',help='Default v2: A/B each check translation and image/label')
    p.add_argument('--archive',default='exports/main_review_v2.zip');p.add_argument('--report')
    p.add_argument('--manifest');p.add_argument('--review');p.add_argument('--output');p.add_argument('--audit')
    p.add_argument('--operator');p.add_argument('--dry-run',action='store_true');args=p.parse_args();root=Path.cwd().resolve()
    workflow=v2 if args.version=='v2' else v1
    if args.action in {'export','bundle'}:
        if args.dry_run:p.error('--dry-run is only supported by import')
        if args.action=='bundle' and args.version!='v2':p.error('Standalone review bundle is v2; use team_workspace.py for v1 data')
        archive=(root/args.archive).resolve()
        report_path=(root/args.report).resolve() if args.report else None
        if report_path and (not report_path.is_relative_to(root) or report_path.exists()):raise ValueError('Use a new report path inside project')
        if args.action=='bundle' and (not archive.is_relative_to(root/'exports') or archive.exists()):raise ValueError('Use a new ZIP path under exports')
        manifests=[root/'data/main/preparation_v2/repope_bilingual_draft_manifest.csv']+[
            root/f'data/main/preparation_v3/{d}_bilingual_draft.csv' for d in ['vsr','tallyqa','oxford_pet']]
        output=root/('data/reviews/main_review_v2' if args.version=='v2' else 'data/reviews/main_review_v1')
        report_dir=root/('reports/stage1/v12/main_review' if args.version=='v2' else 'reports/stage1/v10/main_review')
        report=workflow.export_batches(root,manifests=manifests,output=output,report_dir=report_dir)
        if args.version=='v1':
            target=report_dir/'packets.json'
            content=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
            if target.exists() and target.read_bytes()!=content:raise ValueError('Packet index changed')
            if not target.exists():atomic_bytes(target,content)
        result=v2.build_review_bundle(root,archive) if args.action=='bundle' else {'version':args.version,'rows':report['rows'],'packets':len(report['packets']),'approvals_created':0}
        if report_path:write_json(report_path,result)
        print(json.dumps(result,indent=2))
    else:
        if not all([args.manifest,args.review,args.output,args.audit,args.operator]):p.error('Import requires manifest/review/output/audit/operator')
        manifest,review,output,audit=[(root/x).resolve() for x in [args.manifest,args.review,args.output,args.audit]]
        if len({manifest,review,output,audit})!=4 or not all(x.is_relative_to(root) for x in [manifest,review,output,audit]):
            raise ValueError('Distinct paths inside project required')
        if output.exists() or audit.exists():raise ValueError('Preserve existing outputs; use new paths')
        rows,report=workflow.import_review(read_manifest(manifest),manifest_path=manifest,root=root,review_path=review,operator=args.operator)
        if not args.dry_run:
            atomic_bytes(output,manifest_bytes(rows));write_json(audit,report)
        print(json.dumps({'version':args.version,'dry_run':args.dry_run,'qa_status':report['qa_status'],'translation_status':report['translation_status']}))
