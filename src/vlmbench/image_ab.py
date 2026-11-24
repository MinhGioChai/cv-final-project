"""Bounded pre-freeze A/B diagnostic. Reuses adapters; never opens main execution."""
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
from types import SimpleNamespace

from PIL import Image
import yaml

from .baseline_contract import (BaselineConfig, PromptSet, TASKS, inside, render_prompt, review_proof)
from .baseline_runtime import MainAdapter, code_state
from .environment import inspect_environment
from .io_utils import atomic_bytes, read_manifest, sha256_file, write_json
from .parse import parse_response
from .pilot_launcher import gpu_preflight
from .pilot_runtime import safe_error
from .qa import leakage_issues, validate_manifest
from .reviews import canonical_hash, row_hash

NAMESPACE='results/pilot/image_ab_v1'
BRANCHES=('A','B')


def prepare_image(path, branch):
    if branch not in BRANCHES:raise ValueError('Only A/B supported')
    with Image.open(path) as original:
        original_wh=list(original.size)
        image=original.convert('RGB')
    if branch=='A':image.thumbnail((512,512),Image.Resampling.LANCZOS)
    return image,original_wh


def hardware_check():
    """Tiny real CUDA kernels only; this is not a VLM generation or A/B measurement."""
    environment=inspect_environment()
    import torch
    evidence={'scope':'hardware_kernel_preflight_not_VLM_inference','environment':environment,
        'torch_version':torch.__version__,'cuda_build':torch.version.cuda,
        'cuda_available':torch.cuda.is_available(),'model_generations':0}
    try:
        evidence['qwen']=gpu_preflight('qwen',torch)
        evidence['gemma']=gpu_preflight('gemma',torch)
        evidence['free_total_memory_bytes']=list(torch.cuda.mem_get_info(0))
        kernels={}
        for name,dtype in [('float16',torch.float16),('bfloat16',torch.bfloat16)]:
            tensor=torch.ones((32,32),device='cuda:0',dtype=dtype)
            product=tensor@tensor;torch.cuda.synchronize(0)
            value=product.float().sum().item()
            if value!=32768.:raise RuntimeError('Unexpected CUDA kernel output')
            kernels[name]={'matmul_shape':[32,32],'sum':value,'passed':True}
            del tensor,product
        evidence['CUDA_kernels']=kernels;environment['torch_cuda_runtime_tested']=True
    except Exception as exc:evidence['error']=safe_error(exc)
    return evidence


def plan(root, manifest='data/pilot/stage1_qa_v1/pilot_manifest.csv'):
    root=Path(root).resolve()
    config_path=root/'configs/baseline_v3_draft.yaml'
    config=BaselineConfig.model_validate(yaml.safe_load(config_path.read_text(encoding='utf-8')))
    # Read candidate settings only, never change frozen/config or invoke main runtime.
    if config.preprocess.image_max_edge!=512:raise ValueError('A must retain the audited 512 policy')
    manifest_path=inside(root,manifest)
    rows=sorted(read_manifest(manifest_path),key=lambda r:r.sample_id)
    prompts=PromptSet.model_validate(yaml.safe_load((root/config.prompts).read_text(encoding='utf-8')))
    issues=validate_manifest(rows,root=root,mode='pilot')['issues']
    if len(rows)!=30:issues.append({'code':'EXACTLY_30_PILOT_ROWS_REQUIRED'})
    if len({r.image_sha256 for r in rows})!=len(rows):issues.append({'code':'DUPLICATE_PILOT_IMAGE'})
    coverage=Counter(r.task for r in rows)
    for task in TASKS.values():
        if not coverage[task]:issues.append({'code':'TASK_COVERAGE_MISSING','task':task})
    if set(coverage)-set(TASKS.values()):issues.append({'code':'UNSUPPORTED_TASK'})
    main_rows=[r for path in config.manifests for r in read_manifest(root/path)]
    issues.extend(leakage_issues(rows,main_rows))
    main_ids={r.sample_id for r in main_rows}
    trusted={r.sample_id:row_hash(r) for r in read_manifest(root/config.pilot_manifest)}
    supplemental=[]
    for row in rows:
        inside(root,row.image_path)
        if row.sample_id in main_ids:issues.append({'code':'MAIN_SAMPLE_ID_OVERLAP','sample_id':row.sample_id})
        if row.qa_status!='approved' or row.translation_status!='approved':
            issues.append({'code':'PILOT_QA_REQUIRED','sample_id':row.sample_id})
        if trusted.get(row.sample_id)!=row_hash(row):
            if not review_proof(row):issues.append({'code':'SUPPLEMENT_REVIEW_PROOF_REQUIRED','sample_id':row.sample_id})
            else:supplemental.append(row)
        # Also validates routing and fixed Pet label mapping; both languages retain the same prompt bytes across A/B.
        for language in ('en','vi'):render_prompt(row,language,prompts)
    # Supplemental images must be selected from the already pinned source frames, not main outputs.
    inventory_path=root/'reports/stage1/v8/main_inventory_v2.json'
    source_hashes={}
    if supplemental:
        inventory=json.loads(inventory_path.read_text())['datasets']
        for dataset in sorted({r.source_dataset for r in supplemental}):
            info=inventory[dataset];path=inside(root,info['frame_path'])
            digest=sha256_file(path);source_hashes[info['frame_path']]=digest
            if digest!=info['frame_sha256']:raise ValueError('Source frame changed')
            wanted={r.sample_id:r for r in supplemental if r.source_dataset==dataset}
            found=set()
            with path.open(encoding='utf-8') as stream:
                for line in stream:
                    source=json.loads(line)
                    if source['sample_id'] not in wanted:continue
                    row=wanted[source['sample_id']];found.add(row.sample_id)
                    fields=['source_dataset','source_split','source_row_id','image_id','task','category','question_en','ground_truth']
                    if any(type(source[k]) is not type(getattr(row,k)) or source[k]!=getattr(row,k) for k in fields):
                        issues.append({'code':'SUPPLEMENT_SOURCE_MISMATCH','sample_id':row.sample_id})
                    for key in ['source_revision','source_record_sha256','image_namespace']:
                        if row.metadata.get(key)!=source[key]:issues.append({'code':'SUPPLEMENT_PROVENANCE_MISMATCH','sample_id':row.sample_id})
            if found!=set(wanted):issues.append({'code':'SUPPLEMENT_SOURCE_ID_MISSING','dataset':dataset})
    inputs=[config_path,manifest_path,root/config.prompts,root/config.pilot_manifest,
            *(root/p for p in config.manifests)]
    implementation=[Path(__file__),*(Path(__file__).parent/p for p in ['pilot_runtime.py','gemma_diagnostic.py','baseline_runtime.py','baseline_contract.py','parse.py'])]
    fingerprint=canonical_hash({'schema':'image_ab_v1','branches':{'A':'RGB_thumbnail512_LANCZOS','B':'RGB_original'},
        'config':config.model_dump(),'inputs':{str(p.relative_to(root)):sha256_file(p) for p in inputs},
        'implementation':{p.name:sha256_file(p) for p in implementation},'source_frames':source_hashes,
        'warmups_per_branch':2,'repeats':1})
    summary={'scope':'technical_image_AB_validation_not_main','config_fingerprint':fingerprint,
        'manifest':manifest_path.relative_to(root).as_posix(),'rows':len(rows),'tasks':dict(coverage),
        'expected_cells':len(rows)*8,'expected_per_model':len(rows)*4,
        'warmups_per_model':4,'repeats':1,'execution_ready':not issues,'issues':issues,
        'main_frozen':config.frozen,'main_freeze_receipt':config.freeze_receipt,
        'model_generations':0,'new_human_approvals':0}
    return SimpleNamespace(root=root,config=config,rows=rows,prompts=prompts,summary=summary)


class ObservedProcessor:
    """Read shapes without modifying processor arguments, outputs or tensor values."""
    def __init__(self,processor):self.processor=processor;self.last={}
    def __getattr__(self,key):return getattr(self.processor,key)
    def __call__(self,*args,**kwargs):
        started=time.perf_counter();result=self.processor(*args,**kwargs)
        self.last={'processor_cpu_ms':(time.perf_counter()-started)*1000,
            'processor_output_shape':list(result['pixel_values'].shape),
            'input_token_count':int(result['input_ids'].shape[-1])}
        if 'image_grid_thw' in result:self.last['image_grid_thw']=result['image_grid_thw'].tolist()
        if 'num_crops' in result:
            value=result['num_crops'];self.last['num_crops']=value.tolist() if hasattr(value,'tolist') else value
        return result


def measure(adapter,row,branch,root,*,prompt):
    torch=adapter.adapter.torch
    torch.cuda.synchronize(0)
    base_alloc=torch.cuda.memory_allocated(0)/1024**2
    base_reserved=torch.cuda.memory_reserved(0)/1024**2
    torch.cuda.reset_peak_memory_stats(0)
    adapter.adapter.processor.last={}
    start=time.perf_counter()
    record={'original_dimensions':None,'pre_processor_dimensions':None,
        'raw_response':None,'parsed_response':None,'correctness':None,'invalid_reason':None,
        'run_status':'failed','error':None,'oom':False,'processor_output_shape':None}
    try:
        if sha256_file(inside(root,row.image_path))!=row.image_sha256:raise ValueError('Image changed after plan')
        prep=time.perf_counter();image,original=prepare_image(inside(root,row.image_path),branch)
        record.update(original_dimensions=original,pre_processor_dimensions=list(image.size),
            image_prepare_ms=(time.perf_counter()-prep)*1000)
        result=adapter.generate(image,prompt)
        record.update(raw_response=result['raw_response'],adapter_elapsed_ms=result['elapsed_ms'])
        parsed=parse_response(result['raw_response'],row.task)
        record.update(parsed_response=parsed.prediction,run_status='success',valid=parsed.status=='valid',
            correctness=(parsed.prediction==row.ground_truth) if parsed.status=='valid' else False,
            invalid_reason=None if parsed.status=='valid' else parsed.reason)
        trace=result.get('generation_trace',{})
        record['generation_trace']=trace
        if trace.get('all_raw_logits_finite') is False:raise RuntimeError('Nonfinite logits')
    except Exception as exc:
        record.update(run_status='failed',valid=False,correctness=None,parsed_response=None,
            invalid_reason='GENERATION_FAILED',error=safe_error(exc),
            oom='outofmemory' in type(exc).__name__.lower() or 'out of memory' in str(exc).lower())
    finally:
        torch.cuda.synchronize(0)
        record.update(adapter.adapter.processor.last)
        record.update(latency_ms=(time.perf_counter()-start)*1000,
            baseline_allocated_mib=base_alloc,baseline_reserved_mib=base_reserved,
            peak_allocated_mib=torch.cuda.max_memory_allocated(0)/1024**2,
            peak_reserved_mib=torch.cuda.max_memory_reserved(0)/1024**2)
        for kind in ['allocated','reserved']:
            record[f'incremental_peak_{kind}_mib']=record[f'peak_{kind}_mib']-record[f'baseline_{kind}_mib']
    return record


def execute(plan,alias,output,*,execute=False):
    # No environment, torch or adapter load until the independent pilot gates pass.
    if not execute or not plan.summary['execution_ready']:
        raise ValueError('Explicit --execute and complete four-task, QA, provenance and exclusion gates required')
    if plan.summary.get('scope')!='technical_image_AB_validation_not_main':
        raise ValueError('Full validation requires the four-task plan; diagnostic is separate')
    return _execute_approved_pilot(plan,alias,output,namespace=NAMESPACE)


def _execute_approved_pilot(plan,alias,output,*,namespace,before_generate=None):
    """Shared instrumentation after the caller's independent pilot gates pass."""
    if alias not in {'qwen','gemma'}:raise ValueError('Unknown model')
    output=inside(plan.root,output)
    if not output.is_relative_to(plan.root/namespace):raise ValueError('Use a NEW '+namespace+' run directory')
    if output.exists():raise ValueError('Preserve existing run; use a new directory, no automatic retry/resume')
    environment=inspect_environment()
    import torch
    hardware=gpu_preflight(alias,torch)
    environment['torch_cuda_runtime_tested']=True
    spec=plan.config.models[alias]
    adapter=MainAdapter(plan,alias,offline=True)
    identity={'config_fingerprint':plan.summary['config_fingerprint'],'model':alias,
        'validation_scope':plan.summary['scope'],'M3_complete':False,
        'model_spec':spec.model_dump(),'environment':environment,'hardware':hardware,'code':code_state(plan.root),
        'settings_snapshot':plan.config.model_dump(),'prompts_snapshot':plan.prompts.model_dump(),
        'manifest':plan.summary['manifest'],'sample_ids':[r.sample_id for r in plan.rows]}
    identity['runtime_fingerprint']=canonical_hash(identity)
    output.mkdir(parents=True)
    write_json(output/'metadata.json',identity)
    records=[];warmups=[]
    try:
        adapter.load_model()
        adapter.adapter.processor=ObservedProcessor(adapter.adapter.processor)
        processor_identity={'class':type(adapter.adapter.processor.processor).__name__,
            'config':adapter.adapter.processor.processor.to_dict()}
        write_json(output/'processor.json',processor_identity)
        if before_generate:before_generate(identity,processor_identity)
        first=getattr(plan,'warmup_row',plan.rows[0])
        prompt=render_prompt(first,'en',plan.prompts)
        for branch in BRANCHES:
            for repeat in range(2):
                warmup=measure(adapter,first,branch,plan.root,prompt=prompt)
                warmups.append({**warmup,'sample_id':first.sample_id,'language':'en','branch':branch,
                    'validation_scope':plan.summary['scope'],
                    'task':first.task,'ground_truth':first.ground_truth,'prompt_text':prompt,
                    'config_fingerprint':identity['config_fingerprint'],'runtime_fingerprint':identity['runtime_fingerprint'],
                    'model':alias,'excluded_warmup':True,'repeat':repeat})
                write_json(output/'warmups.json',warmups)
                if warmup['run_status']!='success':raise RuntimeError('Warmup failed; no fallback')
        # Same adapter/model/processor instance for A/B. No policy-dependent generation kwargs.
        for index,row in enumerate(plan.rows):
            index=getattr(plan,'order_indices',{}).get(row.sample_id,index)
            for language in ('en','vi'):
                prompt=render_prompt(row,language,plan.prompts)
                branches=BRANCHES if (index+(language=='vi'))%2==0 else BRANCHES[::-1]
                for branch in branches:
                    result=measure(adapter,row,branch,plan.root,prompt=prompt)
                    record={**result,'scope':'gpu_image_ab_pilot','sample_id':row.sample_id,'task':row.task,
                        'validation_scope':plan.summary['scope'],
                        'language':language,'model':alias,'branch':branch,'ground_truth':row.ground_truth,
                        'image_sha256':row.image_sha256,'prompt_text':prompt,'prompt_hash':canonical_hash(prompt),
                        'config_fingerprint':identity['config_fingerprint'],'runtime_fingerprint':identity['runtime_fingerprint'],
                        'row_sha256':row_hash(row),'source_provenance':row.metadata.get('upstream_verification',{}),
                        'recorded_at_utc':datetime.now(timezone.utc).isoformat()}
                    records.append(record)
                    atomic_bytes(output/'predictions.jsonl',''.join(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n' for r in records).encode('utf-8'))
                    if record['oom']:raise RuntimeError('Stopped after OOM; preserve failure and remaining missing cells')
    except BaseException as exc:
        write_json(output/'stop.json',{'error':safe_error(exc),'measured_records':len(records),'warmup_records':len(warmups)})
        raise
    finally:adapter.unload_model()
    return {'measured_records':len(records),'warmup_records':len(warmups),'model':alias}


def percentile(values,p):
    if not values:return None
    values=sorted(values);at=(len(values)-1)*p;lo=math.floor(at);hi=math.ceil(at)
    return values[lo]+(values[hi]-values[lo])*(at-lo)


def summarize(plan,records):
    expected={(alias,r.sample_id,language,branch):(r,language) for alias in ('qwen','gemma')
              for r in plan.rows for language in ('en','vi') for branch in BRANCHES}
    indexed={}
    for record in records:
        key=tuple(record[k] for k in ('model','sample_id','language','branch'))
        if key not in expected or key in indexed or record['config_fingerprint']!=plan.summary['config_fingerprint']:
            raise ValueError('Unknown/duplicate cell or incompatible fingerprint')
        if record['scope']!='gpu_image_ab_pilot':raise ValueError('Non-GPU diagnostic data cannot be evidence')
        row,_=expected[key]
        if record['run_status']=='success':
            parsed=parse_response(record['raw_response'],row.task)
            if (record['parsed_response']!=parsed.prediction or record['valid']!=(parsed.status=='valid')
                or record['correctness']!=(parsed.status=='valid' and parsed.prediction==row.ground_truth)):
                raise ValueError('Saved prediction/validity/correctness differs from parser/source')
        indexed[key]=record
    metrics=[];comparisons=[];consistency=[]
    for alias in ('qwen','gemma'):
        for task in TASKS.values():
            rows=[r for r in plan.rows if r.task==task]
            for language in ('en','vi'):
                for branch in BRANCHES:
                    got=[indexed[alias,r.sample_id,language,branch] for r in rows if (alias,r.sample_id,language,branch) in indexed]
                    success=[r for r in got if r['run_status']=='success']
                    latency=[r['latency_ms'] for r in success]
                    metrics.append({'model':alias,'task':task,'language':language,'branch':branch,
                        'expected':len(rows),'recorded':len(got),'missing':len(rows)-len(got),
                        'valid':sum(r.get('valid',False) for r in success),
                        'invalid':sum(not r.get('valid',False) for r in success),
                        'failed':len(got)-len(success),'oom':sum(r.get('oom',False) for r in got),
                        'correct':sum(r.get('correctness') is True for r in success),
                        'accuracy_all_expected':sum(r.get('correctness') is True for r in success)/len(rows) if rows and got else None,
                        'latency_p50_ms':percentile(latency,.5),'latency_p95_ms':percentile(latency,.95),
                        'peak_allocated_mib':max((r['peak_allocated_mib'] for r in got),default=None),
                        'peak_reserved_mib':max((r['peak_reserved_mib'] for r in got),default=None)})
                pairs=[(indexed.get((alias,r.sample_id,language,'A')),indexed.get((alias,r.sample_id,language,'B'))) for r in rows]
                pairs=[(a,b) for a,b in pairs if a and b and a.get('valid') and b.get('valid') and a['run_status']==b['run_status']=='success']
                comparisons.append({'model':alias,'task':task,'language':language,'jointly_valid_AB':len(pairs),
                    'prediction_flips':sum(a['parsed_response']!=b['parsed_response'] for a,b in pairs),
                    'A_correct_B_incorrect':sum(a['correctness'] and not b['correctness'] for a,b in pairs),
                    'A_incorrect_B_correct':sum(not a['correctness'] and b['correctness'] for a,b in pairs)})
            # Same sample denominator for the EN/VI disagreement change across A and B.
            four=[{(lang,branch):indexed.get((alias,r.sample_id,lang,branch)) for lang in ('en','vi') for branch in BRANCHES} for r in rows]
            four=[x for x in four if all(v and v.get('valid') and v['run_status']=='success' for v in x.values())]
            a=sum(x['en','A']['parsed_response']!=x['vi','A']['parsed_response'] for x in four)
            b=sum(x['en','B']['parsed_response']!=x['vi','B']['parsed_response'] for x in four)
            consistency.append({'model':alias,'task':task,'four_way_valid':len(four),'A_disagreements':a,
                'B_disagreements':b,'change_B_minus_A':b-a if four else None})
    return {'scope':'real_GPU_records_only' if records else 'not_run_no_GPU_predictions',
        'expected':len(expected),'recorded':len(records),'missing':len(expected)-len(records),
        'metrics':metrics,'AB_comparisons':comparisons,'EN_VI_consistency':consistency}
