"""Approved RePOPE-only diagnostic, independent of four-task validation and M3."""
from collections import Counter
import json
from pathlib import Path

from . import image_ab
from .baseline_contract import inside
from .io_utils import read_manifest, sha256_file, write_json
from .reviews import canonical_hash, row_hash
from .source_audit import audit_rows, load_upstream, read_audit_config

MODE='REPOPE_ONLY_DIAGNOSTIC'
NAMESPACE='results/pilot/repope_image_ab_v1'


def diagnostic_plan(root,size=6):
    if size not in (6,30):raise ValueError('Diagnostic supports phase1=6 or phase2=30 total only')
    base=image_ab.plan(root)
    rows=base.rows
    # Full validator remains unchanged: its missing-task issues are retained separately.
    issues=[i for i in base.summary['issues'] if i['code']!='TASK_COVERAGE_MISSING']
    if len(rows)!=30 or any(r.source_dataset!='repope' or r.task!='object_existence' for r in rows):
        issues.append({'code':'CANONICAL_30_REPOPE_PILOT_REQUIRED'})
    validation_path=base.root/'reports/stage1/v10/pilot_qa_validation.json'
    validation=json.loads(validation_path.read_text(encoding='utf-8'))
    manifest=base.root/base.summary['manifest']
    if sha256_file(manifest)!=validation['reviewed_manifest_sha256']:
        issues.append({'code':'HUMAN_APPROVED_MANIFEST_HASH_CHANGED'})
    audit_path=base.root/'reports/stage1/v10/label_qa_import_v1.json'
    audit=json.loads(audit_path.read_text(encoding='utf-8'))
    approved={e['sample_id']:e for e in audit['events']}
    review_path=base.root/'data/reviews/pilot_label_qa_v1/label_qa_reviewed_v1.json'
    if sha256_file(review_path)!=audit['review_sha256']:issues.append({'code':'HUMAN_QA_REVIEW_HASH_CHANGED'})
    registry_path=base.root/base.config.pilot_exclusions
    registry=json.loads(registry_path.read_text(encoding='utf-8'))['images']
    exclusions={(r['image_namespace'],r['image_id'],r['image_sha256']) for r in registry}
    for row in rows:
        attestation=approved.get(row.sample_id,{})
        if attestation.get('output_row_sha256')!=row_hash(row) or attestation.get('after')!='approved':
            issues.append({'code':'HUMAN_APPROVAL_ROW_BINDING_CHANGED','sample_id':row.sample_id})
        if (row.metadata.get('image_namespace'),row.image_id,row.image_sha256) not in exclusions:
            issues.append({'code':'PILOT_EXCLUSION_REGISTRY_MISSING','sample_id':row.sample_id})
    source_config=base.root/'configs/source_audit.yaml'
    content,receipt=load_upstream(read_audit_config(source_config),root=base.root,offline=True)
    _,source_report=audit_rows(rows,content,receipt)
    if not source_report['all_matched']:issues.append({'code':'PINNED_SOURCE_MISMATCH'})
    for row in rows:
        verified=row.metadata.get('upstream_verification',{})
        if (verified.get('status')!='matched' or verified.get('revision')!=receipt['revision']
            or verified.get('annotation_sha256')!=receipt['files'][row.category]['sha256']):
            issues.append({'code':'SOURCE_HASH_BINDING_CHANGED','sample_id':row.sample_id})
    buckets={}
    for row in rows:
        key=row.category,row.ground_truth
        rank=canonical_hash({'selection':'repope_diagnostic_v1','seed':42,'id':row.sample_id})
        if key not in buckets or rank<buckets[key][0]:buckets[key]=(rank,row)
    six=sorted([entry[1] for entry in buckets.values()],key=lambda r:r.sample_id)
    if len(six)!=6:issues.append({'code':'SIX_CATEGORY_LABEL_STRATA_REQUIRED'})
    binding={'mode':MODE,'base_fingerprint':base.summary['config_fingerprint'],
        'diagnostic_implementation_sha256':sha256_file(Path(__file__)),
        'qa_validation_sha256':sha256_file(validation_path),'qa_import_sha256':sha256_file(audit_path),
        'human_review_sha256':sha256_file(review_path),'exclusions_sha256':sha256_file(registry_path),
        'source_revision':receipt['revision'],'source_files':{k:v['sha256'] for k,v in receipt['files'].items()},
        'all_row_hashes':{r.sample_id:row_hash(r) for r in rows},'phase1_ids':[r.sample_id for r in six]}
    # Same fingerprint for phase1 and extension: selection/phase is explicit metadata, not a settings change.
    base.all_rows=rows;base.phase1_rows=six;base.warmup_row=six[0]
    base.order_indices={r.sample_id:i for i,r in enumerate(rows)}
    base.rows=six if size==6 else rows
    full_gate_issues=base.summary['issues']
    base.summary={**base.summary,'scope':MODE,'rows':len(base.rows),
        'config_fingerprint':canonical_hash(binding),'expected_cells':len(base.rows)*8,
        'expected_per_model':len(base.rows)*4,'tasks':{'object_existence':len(base.rows)},
        'execution_ready':not issues,'issues':issues,'full_validation_issues':full_gate_issues,
        'M3_complete':False,'binding':binding,'selected_ids':[r.sample_id for r in base.rows]}
    return base


def read_run(directory,plan,*,alias=None):
    directory=inside(plan.root,directory)
    meta=json.loads((directory/'metadata.json').read_text(encoding='utf-8'))
    if meta.get('validation_scope')!=MODE or meta['config_fingerprint']!=plan.summary['config_fingerprint'] or (alias and meta['model']!=alias):
        raise ValueError('Incompatible diagnostic model/config fingerprint')
    records=[json.loads(s) for s in (directory/'predictions.jsonl').read_text(encoding='utf-8').splitlines()]
    for record in records:
        if record.get('validation_scope')!=MODE or record['runtime_fingerprint']!=meta['runtime_fingerprint'] or record['model']!=meta['model']:
            raise ValueError('Mixed run records')
    # Uses the existing parser, exact IDs, A/B keys and fingerprint checks.
    image_ab.summarize(plan,records)
    return meta,records


def stable_runtime(meta,processor):
    return {'config_fingerprint':meta['config_fingerprint'],'model_spec':meta['model_spec'],
        'environment':{k:meta['environment'][k] for k in ('python','os','packages','gpus')},
        'hardware':meta['hardware'],'code':meta['code'],'settings':meta['settings_snapshot'],
        'prompts':meta['prompts_snapshot'],'processor':processor}


def run_diagnostic(plan,alias,output,*,execute=False,phase1=None):
    if not execute or plan.summary.get('scope')!=MODE or not plan.summary['execution_ready']:
        raise ValueError('Explicit diagnostic execution and all approved provenance/exclusion gates required')
    reused=[];reference=None
    if len(plan.rows)==30:
        if phase1 is None:raise ValueError('Successful two-model phase1 evidence is required before extension')
        parent=inside(plan.root,phase1)
        for model in ('qwen','gemma'):
            directory=parent/model
            meta,records=read_run(directory,plan,alias=model)
            expected={(r.sample_id,lang,branch) for r in plan.phase1_rows for lang in ('en','vi') for branch in ('A','B')}
            keys={(r['sample_id'],r['language'],r['branch']) for r in records}
            if keys!=expected or any(r['run_status']!='success' or not r['valid'] or r.get('oom') for r in records):
                raise ValueError('Phase1 incomplete/invalid/failed; do not expand')
            if model==alias:
                reused=records
                reference=(directory,meta,json.loads((directory/'processor.json').read_text(encoding='utf-8')))
        first_ids={r.sample_id for r in plan.phase1_rows}
        plan.rows=[r for r in plan.rows if r.sample_id not in first_ids]
    # Actual environment/code/processor compatibility is checked BEFORE warmup/generation.
    def before_generate(meta_now,processor_now):
        if reference and stable_runtime(meta_now,processor_now)!=stable_runtime(reference[1],reference[2]):
            raise ValueError('Runtime/code/processor changed; refuse reuse')
    result=image_ab._execute_approved_pilot(plan,alias,output,namespace=NAMESPACE,before_generate=before_generate)
    directory=inside(plan.root,output)
    if reference:
        source,meta,processor=reference
        current_meta=json.loads((directory/'metadata.json').read_text(encoding='utf-8'))
        current_processor=json.loads((directory/'processor.json').read_text(encoding='utf-8'))
        if stable_runtime(current_meta,current_processor)!=stable_runtime(meta,processor):raise ValueError('Incompatible runs')
        write_json(directory/'reuse.json',{'mode':MODE,'source':source.relative_to(plan.root).as_posix(),
            'predictions_sha256':sha256_file(source/'predictions.jsonl'),'metadata_sha256':sha256_file(source/'metadata.json'),
            'reused_cells':len(reused),'new_cells':result['measured_records'],'combined_cells':len(reused)+result['measured_records']})
    return {**result,'mode':MODE,'reused_cells':len(reused),'M3_complete':False}
