"""Capture real CPU gates and NOT-RUN metrics; never launches model generation."""
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from vlmbench.baseline_contract import build_plan
from vlmbench.image_ab import plan, summarize
from vlmbench.io_utils import sha256_file, write_json


def main():
    folder=Path(__file__).resolve().parent
    selected=plan(ROOT)
    if selected.summary['execution_ready']:raise RuntimeError('This collector must not substitute for a real GPU run on eligible data')
    write_json(folder/'preflight_final.json',selected.summary)
    write_json(folder/'metrics.json',summarize(selected,[]))
    main_plan=build_plan(ROOT,ROOT/'configs/baseline_v3_draft.yaml')
    write_json(folder/'main_gates.json',main_plan.summary())
    attempts=[]
    for alias in ('qwen','gemma'):
        target=f'results/pilot/image_ab_v1/coverage_gate_check/{alias}'
        args=[sys.executable,'scripts/validate_image_ab.py','run','--model',alias,'--output',target,'--execute']
        completed=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        assert completed.returncode==2 and not (ROOT/target).exists()
        attempts.append({'model':alias,'command':' '.join(args),'exit_code':completed.returncode,
            'stdout':json.loads(completed.stdout),'stderr':completed.stderr,'run_directory_created':False})
    write_json(folder/'blocked_execute.json',{'scope':'real_gate_check_no_adapter_load_no_model_inference','attempts':attempts})
    dims=[json.loads(line) for line in (ROOT/'reports/audits/2026-11-24/image_dimensions.jsonl').read_text().splitlines()]
    unique={r['image_sha256']:r for r in dims}.values()
    report={'source':'reports/audits/2026-11-24/image_dimensions.jsonl',
        'source_sha256':sha256_file(ROOT/'reports/audits/2026-11-24/image_dimensions.jsonl'),
        'unique_images':len(unique),'longest_edge_bins':dict(Counter('<=512' if max(r['original_wh'])<=512 else '513-640' if max(r['original_wh'])<=640 else '>640' for r in unique)),
        'dataset_counts':dict(Counter(r['scope']+'/'+r['dataset'] for r in unique)),
        'max512_would_downscale':sum(r['resized_by_512'] for r in unique),
        'new_image_processing':False}
    write_json(folder/'resolution_distribution.json',report)
    print(json.dumps({'pilot_coverage':selected.summary['tasks'],'execution_ready':False,
        'main_blockers':main_plan.summary()['blocking_counts'],'resolution':report['longest_edge_bins'],
        'GPU_model_generations':0},indent=2))


if __name__=='__main__':main()
