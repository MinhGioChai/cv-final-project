"""Materialize selected RePOPE image bytes into an unfrozen, unreviewed draft."""
import argparse
import json
import logging
from pathlib import Path

from vlmbench.io_utils import write_json
from vlmbench.main_images import materialize_repope


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--selection',default='data/main/preparation_v1/repope_candidates.jsonl')
    p.add_argument('--cache',default='data/raw/main_images_v1/repope')
    p.add_argument('--manifest',default='data/main/preparation_v1/repope_draft_manifest.csv')
    p.add_argument('--limit-images',type=int,default=2)
    p.add_argument('--max-download-mb',type=int,default=200)
    p.add_argument('--offline',action='store_true')
    p.add_argument('--refresh-index',action='store_true')
    p.add_argument('--report',help='New report JSON; use separate paths for smoke/final runs')
    args=p.parse_args()
    if not 1<=args.max_download_mb<=250:p.error('Download budget must be 1..250 MiB')
    logging.basicConfig(level=logging.INFO,format='%(message)s')
    root=Path.cwd()
    report=materialize_repope(root=root,selection_path=root/args.selection,cache=root/args.cache,
        manifest_output=root/args.manifest,limit_images=args.limit_images,max_download_mb=args.max_download_mb,
        offline=args.offline,refresh_index=args.refresh_index)
    if args.report:
        target=root/args.report
        if target.exists() and json.loads(target.read_text())!=report:
            raise ValueError('Report differs; use a new report path')
        if not target.exists():write_json(target,report)
    print(json.dumps(report,indent=2))
