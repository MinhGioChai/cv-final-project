"""Acquire selected VSR/TallyQA/Pet images, preserving all historical manifests."""
import argparse
import json
import logging
from pathlib import Path

from vlmbench.io_utils import write_json
from vlmbench.task_images import materialize

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',choices=['vsr','tallyqa','oxford_pet'],required=True)
    parser.add_argument('--offline',action='store_true')
    parser.add_argument('--budget-mb',type=int,default=250)
    parser.add_argument('--report',required=True)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    report = (root/args.report).resolve()
    if not report.is_relative_to(root) or report.exists():
        raise ValueError('Use a new report path inside the project')
    if not 1 <= args.budget_mb <= 850:
        raise ValueError('Explicit budget must be 1..850 MiB')
    logging.basicConfig(level=logging.INFO,format='%(message)s')
    result = materialize(root,args.dataset,offline=args.offline,budget_mb=args.budget_mb)
    write_json(report,result)
    print(json.dumps(result,indent=2))
