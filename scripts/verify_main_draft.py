"""Read-only full draft validation, with a new readiness report and no inference."""
import argparse
from collections import Counter
import json
from pathlib import Path

from vlmbench.datasets.candidates import Candidate
from vlmbench.io_utils import read_manifest,sha256_file,write_json
from vlmbench.qa import validate_manifest


def verify(root):
    root=root.resolve()
    paths=[root/'data/main/preparation_v2/repope_bilingual_draft_manifest.csv']+[
        root/f'data/main/preparation_v3/{d}_bilingual_draft.csv' for d in ['vsr','tallyqa','oxford_pet']]
    rows=[r for path in paths for r in read_manifest(path)]
    selection=root/'data/main/preparation_v2/all_candidates.jsonl'
    candidates=[Candidate.model_validate_json(s) for s in selection.read_text(encoding='utf-8').splitlines()]
    source={r.sample_id:r for r in candidates}
    if len(rows)!=1000 or len(source)!=1000 or len({r.sample_id for r in rows})!=1000 or {r.sample_id for r in rows}!=set(source):
        raise ValueError('Expected exactly the selected 1,000 unique samples')
    identities={};digests={}
    for row in rows:
        original=source[row.sample_id]
        for field in ['source_dataset','source_split','source_row_id','image_id','task','category','question_en','ground_truth']:
            if getattr(row,field)!=getattr(original,field):raise ValueError('Source field changed: '+field)
        if row.metadata['source_revision']!=original.source_revision or row.metadata['source_record_sha256']!=original.source_record_sha256:
            raise ValueError('Source provenance changed')
        if not (root/row.image_path).resolve().is_relative_to(root):raise ValueError('Image path outside project')
        identity=(original.image_namespace,original.image_id)
        if identity in identities and identities[identity]!=row.image_sha256:raise ValueError('One identity has multiple byte versions')
        if row.image_sha256 in digests and digests[row.image_sha256]!=identity:raise ValueError('Different identities share identical bytes')
        identities[identity]=row.image_sha256;digests[row.image_sha256]=identity
    pilot=read_manifest(root/'data/pilot/stage1_qa_v1/pilot_manifest.csv')
    pilot_report=validate_manifest(pilot,root=root,mode='pilot')
    if not pilot_report['valid'] or len(pilot)!=30 or any(r.qa_status!='approved' or r.translation_status!='approved' for r in pilot):
        raise ValueError('Pilot QA manifest is not complete')
    validation=validate_manifest(rows,root=root,mode='main',pilot=pilot)
    codes=Counter(i['code'] for i in validation['issues'])
    other=[i for i in validation['issues'] if i['code']!='MAIN_QA_NOT_APPROVED']
    if other:raise ValueError('Main technical/leakage validation issues: '+json.dumps(other))
    return {'scope':'unfrozen_full_main_draft_readiness_not_inference_authorization','frozen':False,
        'selected_rows':len(rows),'unique_images':len(identities),'unique_image_sha256':len(digests),
        'expected_main_inferences':4000,'main_ready':validation['valid'],
        'datasets':dict(Counter(r.source_dataset for r in rows)),
        'main_qa_status':validation['qa_status'],'main_translation_status':validation['translation_status'],
        'gate_codes':dict(codes),'other_technical_or_leakage_issues':len(other),
        'pilot_qa_status':pilot_report['qa_status'],'pilot_translation_status':pilot_report['translation_status'],
        'source_fields_preserved':True,'pilot_id_or_byte_overlap':0,'duplicate_bytes_across_image_identities':0,
        'inferences_run_by_this_command':0,
        'inputs_sha256':{p.relative_to(root).as_posix():sha256_file(p) for p in paths+[selection]}}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',required=True);args=p.parse_args()
    root=Path.cwd().resolve();target=(root/args.report).resolve()
    if not target.is_relative_to(root) or target.exists():raise ValueError('Use a new report path inside project')
    result=verify(root);write_json(target,result);print(json.dumps(result,indent=2))
