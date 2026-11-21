"""Complete the 1000-row metadata selection without downloading images or inference."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import yaml

from vlmbench.datasets.candidates import Candidate
from vlmbench.io_utils import atomic_bytes,sha256_file,write_json
from vlmbench.task_sampling import sample_task


def prepare(root, config_path, output_dir, report_path):
    root=root.resolve()
    config_path=config_path.resolve()
    output_dir=output_dir.resolve()
    report_path=report_path.resolve()
    cfg=yaml.safe_load(config_path.read_text())
    if cfg['frozen'] is not False or cfg['vsr_variant']!='random' or cfg['remaining_image_cap']!=1:
        raise ValueError('Only unfrozen random/test preparation and cap1 are implemented')
    inventory=json.loads((root/'reports/stage1/v8/main_inventory_v2.json').read_text())
    blocked={(r['image_namespace'],r['image_id']) for r in json.loads((root/'data/pilot/image_exclusions.json').read_text())['images']}
    selected,reports={},{}
    for dataset in ('repope','vsr','tallyqa','oxford_pet'):
        spec=inventory['datasets'][dataset]
        frame=root/spec['frame_path']
        if sha256_file(frame)!=spec['frame_sha256']:raise ValueError('Candidate frame checksum changed')
        rows=[Candidate.model_validate_json(s) for s in frame.read_text(encoding='utf-8').splitlines()]
        if any((r.image_namespace,r.image_id) in blocked for r in rows):raise ValueError('Pilot ID in main frame')
        if dataset=='repope':
            source=root/cfg['repope_selection']
            proof=json.loads((root/'reports/stage1/v8/repope_sampling_v1.json').read_text())
            if sha256_file(source)!=proof['selection_sha256']:raise ValueError('Confirmed RePOPE selection changed')
            chosen=[Candidate.model_validate_json(s) for s in source.read_text(encoding='utf-8').splitlines()]
            reports[dataset]={'rows':len(chosen),'unique_image_refs':len({r.image_id for r in chosen}),'policy':'Reused v8 selection byte-for-byte; cap2 and unique content'}
        else:
            if dataset=='oxford_pet' and rows[0].metadata['candidate_map']!=dict(zip(cfg['pet_breeds'],'ABCDEFGH')):
                raise ValueError('Pet class map differs from preparation config')
            chosen,reports[dataset]=sample_task(rows,dataset=dataset,seed=cfg['seed'])
        original={r.sample_id:r for r in rows}
        if len(chosen)!=cfg['targets'][dataset] or any(original.get(r.sample_id)!=r for r in chosen):
            raise ValueError('Selection target/source provenance mismatch')
        selected[dataset]=chosen
    all_rows=[r for dataset in selected for r in selected[dataset]]
    if len(all_rows)!=1000 or len({r.sample_id for r in all_rows})!=1000:raise ValueError('Expected 1000 unique candidate IDs')
    files={output_dir/(name+'_candidates.jsonl'):''.join(r.model_dump_json()+'\n' for r in rows).encode('utf-8') for name,rows in selected.items()}
    files[output_dir/'all_candidates.jsonl']=''.join(r.model_dump_json()+'\n' for r in all_rows).encode('utf-8')
    images=defaultdict(set)
    for row in all_rows:images[(row.image_namespace,row.image_id)].add(row.source_dataset)
    report={'scope':'unfrozen_metadata_selection_not_main_manifest','frozen':False,'main_ready':False,
        'rows':1000,'expected_main_inferences':4000,'unique_image_refs_all_tasks':len(images),
        'cross_task_shared_image_refs':sum(len(s)>1 for s in images.values()),'datasets':reports,
        'config_sha256':sha256_file(config_path),'inventory_sha256':sha256_file(root/'reports/stage1/v8/main_inventory_v2.json'),
        'decision_status':cfg['decision_status'],'pilot_image_id_overlap':0,'source_fields_changed':0,
        'human_approvals_created':0,'inferences_run':0,'outputs':{p.relative_to(root).as_posix():hashlib.sha256(b).hexdigest() for p,b in files.items()}}
    for p,b in files.items():
        if p.exists() and p.read_bytes()!=b:raise ValueError('Output differs; preserve history and use new paths')
    if report_path.exists() and json.loads(report_path.read_text())!=report:raise ValueError('Report differs; use new version')
    for p,b in files.items():
        if not p.exists():atomic_bytes(p,b)
    if not report_path.exists():write_json(report_path,report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',default='configs/main_preparation_v3.yaml')
    p.add_argument('--output-dir',default='data/main/preparation_v2')
    p.add_argument('--report',default='reports/stage1/v9/main_selection_v1.json')
    args=p.parse_args()
    print(json.dumps(prepare(Path.cwd(),Path(args.config),Path(args.output_dir),Path(args.report)),indent=2))
