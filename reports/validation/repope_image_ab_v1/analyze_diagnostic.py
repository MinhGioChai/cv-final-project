"""Analyze real diagnostic runs; never generate or mix incompatible phase evidence."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from vlmbench import image_ab
from vlmbench.baseline_contract import inside,render_prompt
from vlmbench.io_utils import sha256_file,write_json
from vlmbench.repope_diagnostic import diagnostic_plan,read_run,stable_runtime,MODE
from vlmbench.reviews import canonical_hash,row_hash


def analyze(size,output,run_root='results/pilot/repope_image_ab_v1'):
    plan=diagnostic_plan(ROOT,size)
    rows={r.sample_id:r for r in plan.rows}
    phases=['phase1'] if size==6 else ['phase1','phase2']
    records=[];sources=[];status=[];references={};warmups=[]
    for phase in phases:
        for alias in ('qwen','gemma'):
            folder=inside(ROOT,run_root)/phase/alias
            meta,data=read_run(folder,plan,alias=alias)
            identity=meta.copy();stored=identity.pop('runtime_fingerprint')
            assert canonical_hash(identity)==stored
            processor=json.loads((folder/'processor.json').read_text(encoding='utf-8'))
            runtime=stable_runtime(meta,processor)
            if alias in references:assert runtime==references[alias],f'Incompatible phases: {alias}'
            else:references[alias]=runtime
            for record in data:
                row=rows[record['sample_id']]
                assert record['row_sha256']==row_hash(row) and record['image_sha256']==row.image_sha256
                prompt=render_prompt(row,record['language'],plan.prompts)
                assert record['prompt_text']==prompt and record['prompt_hash']==canonical_hash(prompt)
            if phase=='phase2':
                reuse=json.loads((folder/'reuse.json').read_text())
                origin=ROOT/reuse['source']
                assert reuse['predictions_sha256']==sha256_file(origin/'predictions.jsonl')
                assert reuse['metadata_sha256']==sha256_file(origin/'metadata.json')
                assert reuse['reused_cells']==24 and reuse['new_cells']==96
            excluded=json.loads((folder/'warmups.json').read_text(encoding='utf-8'))
            warmups.extend(excluded)
            records.extend(data)
            status.append({'phase':phase,'model':alias,'loaded':True,'new_measured_cells':len(data),
                'success':sum(r['run_status']=='success' for r in data),
                'valid':sum(r['valid'] for r in data),'oom':sum(r['oom'] for r in data),
                'warmups':len(excluded),'stop_report':(folder/'stop.json').exists()})
            sources.extend({'path':p.relative_to(ROOT).as_posix(),'sha256':sha256_file(p),'bytes':p.stat().st_size}
                           for p in sorted(folder.iterdir()) if p.is_file())
    result=image_ab.summarize(plan,records)
    for key in ['metrics','AB_comparisons','EN_VI_consistency']:
        result[key]=[r for r in result[key] if r['task']=='object_existence']
    branches=[]
    for alias in ('qwen','gemma'):
        for branch in ('A','B'):
            group=[r for r in records if r['model']==alias and r['branch']==branch]
            good=[r for r in group if r['run_status']=='success']
            branches.append({'model':alias,'branch':branch,'n':len(group),
                'latency_p50_ms':image_ab.percentile([r['latency_ms'] for r in good],.5),
                'latency_p95_ms':image_ab.percentile([r['latency_ms'] for r in good],.95),
                'peak_allocated_mib':max(r['peak_allocated_mib'] for r in group),
                'peak_reserved_mib':max(r['peak_reserved_mib'] for r in group),
                'peak_incremental_allocated_mib':max(r['incremental_peak_allocated_mib'] for r in group),
                'median_input_token_count':image_ab.percentile([r['input_token_count'] for r in good],.5),
                'processor_shapes':dict(Counter(str(r['processor_output_shape']) for r in group)),
                'correct':sum(r['correctness'] is True for r in group),'valid':sum(r['valid'] for r in group),
                'failed':sum(r['run_status']!='success' for r in group),'oom':sum(r['oom'] for r in group)})
    stability=[]
    for alias in ('qwen','gemma'):
        for branch in ('A','B'):
            group=[r for r in warmups if r['model']==alias and r['branch']==branch]
            stability.append({'model':alias,'branch':branch,'excluded_repeats':len(group),
                'sample_ids':sorted({r['sample_id'] for r in group}),
                'unique_parsed_responses':sorted({str(r['parsed_response']) for r in group}),
                'valid':sum(r['valid'] for r in group)})
    result.update(mode=MODE,M3_complete=False,config_fingerprint=plan.summary['config_fingerprint'],
        pilot_images=size,warmup_generations=len(warmups),new_model_generations=len(records)+len(warmups),
        reused_phase1_cells=48 if size==30 else 0,model_loading=status,
        branch_summary=branches,source_files=sources,warmup_stability=stability,
        limitations=['RePOPE only; not four-task validation or M3',
                     'Small pilot, one repeat; no general accuracy/significance claim',
                     'PyTorch allocated/reserved is not physical VRAM residency; dedicated/shared residency was not measured',
                     'Processor JSON is outer multimodal processor; image settings pinned by revision/settings/loader hashes'])
    target=inside(ROOT,output)
    if target.exists():raise ValueError('Use new output, preserve prior metrics')
    write_json(target,result)
    print(json.dumps({'pilot_images':size,'recorded':result['recorded'],'missing':result['missing'],
                     'warmups':len(warmups),'branches':branches,
                     'AB':result['AB_comparisons'],'EN_VI':result['EN_VI_consistency']},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--size',type=int,choices=[6,30],required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--run-root',default='results/pilot/repope_image_ab_v1')
    args=parser.parse_args();analyze(args.size,args.output,args.run_root)
