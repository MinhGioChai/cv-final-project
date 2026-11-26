"""Strictly aggregate submitted v2 reviews + previously approved Pet; never adjudicate/freeze."""
import argparse
import json
from pathlib import Path

from vlmbench.review_aggregation import aggregate,publish


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-dir',default='reviewed_final')
    p.add_argument('--config',default='configs/baseline_v3_option_b_v1.yaml')
    p.add_argument('--packet-dir',default='data/reviews/main_review_v2')
    p.add_argument('--pet-manifest',default='data/main/reviewed_pet_source_v1/oxford_pet_reviewed.csv')
    p.add_argument('--output-dir',required=True);p.add_argument('--report-dir',required=True)
    p.add_argument('--operator',required=True);p.add_argument('--dry-run',action='store_true')
    args=p.parse_args();root=Path.cwd().resolve()
    rows,summary,cases=aggregate(root,config_path=args.config,input_dir=args.input_dir,
        packet_dir=args.packet_dir,pet_manifest=args.pet_manifest,operator=args.operator)
    if not args.dry_run:publish(root,rows,summary,cases,output_dir=args.output_dir,report_dir=args.report_dir)
    print(json.dumps({k:summary[k] for k in ['rows','submitted_packets','accepted_nonpet','accepted_pet',
        'accepted_total','needs_resolution','translation_changed','unresolved_by_primary_issue','missing_packets']},ensure_ascii=False,indent=2))


if __name__=='__main__': main()
