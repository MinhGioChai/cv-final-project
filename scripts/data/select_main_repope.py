"""Select metadata candidates under the confirmed cap; never freeze/run inference."""
import argparse
import json
from pathlib import Path

import yaml

from vlmbench.datasets.candidates import Candidate
from vlmbench.io_utils import atomic_bytes, sha256_file, write_json
from vlmbench.main_sampling import sample_repope_candidates


def select(root, config_path, output, report_path):
    config=yaml.safe_load(config_path.read_text())
    if config['frozen'] is not False:raise ValueError('Selection does not freeze the benchmark')
    frame=root/'data/raw/main_metadata_v1/candidate_frames/repope.jsonl'
    rows=[Candidate.model_validate_json(s) for s in frame.read_text(encoding='utf-8').splitlines()]
    registry=root/'data/pilot/image_exclusions.json'
    excluded={(r['image_namespace'],r['image_id']) for r in json.loads(registry.read_text())['images']}
    if any((r.image_namespace,r.image_id) in excluded for r in rows):raise ValueError('Pilot image leaked into frame')
    selected,report=sample_repope_candidates(rows,size=config['targets']['repope'],seed=config['seed'],
        max_rows_per_image=config['repope_max_rows_per_image'],unique_content=config['repope_avoid_exact_content_duplicates'])
    payload=''.join(r.model_dump_json()+'\n' for r in selected).encode('utf-8')
    report.update(config_sha256=sha256_file(config_path),source_frame_sha256=sha256_file(frame),
        pilot_registry_sha256=sha256_file(registry),user_confirmed_image_cap=config['repope_max_rows_per_image'],
        content_policy_status=config['repope_content_policy_status'],frozen=False,main_ready=False,
        source_field_changes=0,images_materialized=0,human_approvals_created=0,
        outstanding=['Image acquisition + hash exclusions','Human image/label QA and translations',
                     'Review exact-content deduplication policy before freeze','Baseline metadata/runner/freeze'])
    import hashlib
    report['selection_sha256']=hashlib.sha256(payload).hexdigest()
    if output.exists() and output.read_bytes()!=payload:raise ValueError('Selection differs; use a new output version')
    if report_path.exists() and json.loads(report_path.read_text())!=report:raise ValueError('Report differs; use a new version')
    if not output.exists():atomic_bytes(output,payload)
    if not report_path.exists():write_json(report_path,report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',default='configs/main_preparation_v2.yaml')
    p.add_argument('--output',default='data/main/preparation_v1/repope_candidates.jsonl')
    p.add_argument('--report',default='reports/stage1/v8/repope_sampling_v1.json')
    args=p.parse_args()
    print(json.dumps(select(Path.cwd(),Path(args.config),Path(args.output),Path(args.report)),indent=2))
