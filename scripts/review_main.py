"""Export main QA packets or validate/import a reviewed packet into a new version."""
import argparse
import json
from pathlib import Path

from vlmbench.io_utils import atomic_bytes,manifest_bytes,read_manifest,write_json
from vlmbench.main_review import export_batches,import_review

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['export','import'])
    p.add_argument('--manifest');p.add_argument('--review');p.add_argument('--output');p.add_argument('--audit')
    p.add_argument('--operator');p.add_argument('--dry-run',action='store_true');args=p.parse_args();root=Path.cwd().resolve()
    if args.action=='export':
        manifests=[root/'data/main/preparation_v2/repope_bilingual_draft_manifest.csv']+[
            root/f'data/main/preparation_v3/{d}_bilingual_draft.csv' for d in ['vsr','tallyqa','oxford_pet']]
        report=export_batches(root,manifests=manifests,output=root/'data/reviews/main_review_v1',report_dir=root/'reports/stage1/v10/main_review')
        target=root/'reports/stage1/v10/main_review/packets.json'
        content=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
        if target.exists() and target.read_bytes()!=content:raise ValueError('Packet index changed')
        if not target.exists():atomic_bytes(target,content)
        print(json.dumps({'rows':report['rows'],'packets':len(report['packets']),'approvals_created':0}))
    else:
        if not all([args.manifest,args.review,args.output,args.audit,args.operator]):p.error('Import requires manifest/review/output/audit/operator')
        manifest,review,output,audit=[(root/x).resolve() for x in [args.manifest,args.review,args.output,args.audit]]
        if len({manifest,review,output,audit})!=4 or not all(x.is_relative_to(root) for x in [manifest,review,output,audit]):
            raise ValueError('Distinct paths inside project required')
        if output.exists() or audit.exists():raise ValueError('Preserve existing outputs; use new paths')
        rows,report=import_review(read_manifest(manifest),manifest_path=manifest,root=root,review_path=review,operator=args.operator)
        if not args.dry_run:
            atomic_bytes(output,manifest_bytes(rows));write_json(audit,report)
        print(json.dumps({'dry_run':args.dry_run,'qa_status':report['qa_status'],'translation_status':report['translation_status']}))
