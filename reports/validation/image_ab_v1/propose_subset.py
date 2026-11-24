"""Offline proposal only: no image downloads, new manifests or human approvals."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
import yaml

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from vlmbench.io_utils import read_manifest, sha256_file, write_json


def main():
    cfg=yaml.safe_load((ROOT/'configs/baseline_v3_draft.yaml').read_text(encoding='utf-8'))
    main_rows=[r for p in cfg['manifests'] for r in read_manifest(ROOT/p)]
    pilot=read_manifest(ROOT/cfg['pilot_manifest'])
    blocked={(r.metadata.get('image_namespace',r.source_dataset),r.image_id) for r in main_rows+pilot}
    main_ids={r.sample_id for r in main_rows}
    selected=[]
    buckets=defaultdict(list)
    rank=lambda r:hashlib.sha256(('image_ab_v1:42:'+r['sample_id']).encode()).hexdigest()
    for r in pilot:buckets[r.category,r.ground_truth].append(r)
    for key in sorted(buckets):
        row=min(buckets[key],key=lambda r:rank(r.model_dump()))
        selected.append({'sample_id':row.sample_id,'dataset':'repope','image_id':row.image_id,
                         'status':'existing_QA_approved','category':row.category,'ground_truth':row.ground_truth})
    assert len(selected)==6
    inventory=json.loads((ROOT/'reports/stage1/v8/main_inventory_v2.json').read_text())
    sources={}
    candidates=[]
    for dataset in ['vsr','tallyqa','oxford_pet']:
        info=inventory['datasets'][dataset];path=ROOT/info['frame_path']
        assert sha256_file(path)==info['frame_sha256']
        sources[dataset]={'path':info['frame_path'],'sha256':info['frame_sha256']}
        pools=defaultdict(list)
        for line in path.read_text(encoding='utf-8').splitlines():
            row=json.loads(line)
            if row['sample_id'] in main_ids or (row['image_namespace'],row['image_id']) in blocked:continue
            key=row['ground_truth'] if dataset in {'vsr','oxford_pet'} else row['category']
            pools[key].append(row)
        quotas={'yes':4,'no':4} if dataset=='vsr' else {'simple':4,'complex':4} if dataset=='tallyqa' else {k:1 for k in 'ABCDEFGH'}
        for key,quota in quotas.items():
            count=0
            for row in sorted(pools[key],key=rank):
                image_key=row['image_namespace'],row['image_id']
                if image_key in blocked:continue
                candidates.append(row);blocked.add(image_key);count+=1
                selected.append({'sample_id':row['sample_id'],'dataset':dataset,'image_id':row['image_id'],
                    'status':'metadata_only_pending_image_checksum_EN_VI_and_image_label_QA',
                    'category':row['category'],'ground_truth':row['ground_truth']})
                if count==quota:break
            assert count==quota,(dataset,key,count)
    output=Path(__file__).resolve().parent
    payload=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in candidates)
    path=output/'supplement_candidates.jsonl'
    if path.exists() and path.read_text(encoding='utf-8')!=payload:raise ValueError('Preserve earlier proposal')
    if not path.exists():path.write_text(payload,encoding='utf-8')
    report={'scope':'proposal_not_manifest_not_QA_not_inference','seed_policy':'sha256(image_ab_v1:42:sample_id)',
        'main_selection_read_only':True,'source_frames':sources,'selected':selected,
        'dataset_counts':dict(Counter(r['dataset'] for r in selected)),'supplement_count':len(candidates),
        'main_image_ID_overlap':0,'main_sample_ID_overlap':0,
        'checksum_overlap':'pending materialization; ID exclusion does not prove byte exclusion',
        'images_downloaded':0,'new_human_approvals':0,'generations':0,
        'next':'Acquire original assets to a NEW pilot-only directory, verify against 813 existing hashes, translate and review both languages/image labels; retain proof in new pilot manifest. Do not modify main or pilot history.'}
    write_json(output/'subset_proposal.json',report)
    print(json.dumps({k:report[k] for k in ['dataset_counts','supplement_count','checksum_overlap']}))


if __name__=='__main__':main()
