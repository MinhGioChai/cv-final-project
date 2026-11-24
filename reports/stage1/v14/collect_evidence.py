"""Actual CPU plan/input checks; never approves QA, freezes data or calls a model."""
from collections import Counter
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from vlmbench.baseline_contract import build_plan,smoke_selection
from vlmbench.baseline_runtime import prepare_main_image,run_main
from vlmbench.io_utils import atomic_bytes,read_manifest,sha256_file,write_json


def main():
    folder=Path(__file__).resolve().parent
    b=build_plan(ROOT,ROOT/'configs/baseline_v3_option_b_v1.yaml')
    a=build_plan(ROOT,ROOT/'configs/baseline_v3_draft.yaml')
    assert b.protocol_hash!=a.protocol_hash
    assert b.protocol['grid_sha256']==a.protocol['grid_sha256']
    assert [r.model_dump() for r in b.rows]==[r.model_dump() for r in a.rows]
    assert b.config.models==a.config.models and b.config.generation==a.config.generation
    assert b.summary()['expected_inferences']==4000 and not b.summary()['execution_ready']
    assert not b.config.frozen and b.config.freeze_receipt is None
    write_json(folder/'candidate_plan.json',b.summary());write_json(folder/'protocol.json',b.protocol)
    grid=ROOT/'results/main/option_b_preflight_v1/grid.jsonl'
    content=''.join(c.model_dump_json()+'\n' for c in b.cells).encode('utf-8')
    if grid.exists():assert grid.read_bytes()==content
    else:atomic_bytes(grid,content)
    selection=smoke_selection(b,1)
    write_json(folder/'smoke_plan.json',{'protocol_hash':b.protocol_hash,'selection':selection,
        'cells':[c.model_dump() for c in b.cells if c.sample_id in selection['sample_ids']],
        'execution_ready':False,'main_gates':b.summary()['blocking_counts'],'M3_complete':False})
    checks=[]
    def forbidden():raise AssertionError('Environment/model access before gate')
    for alias in ('qwen','gemma'):
        for platform in ('local','colab','kaggle'):
            result=run_main(b,alias=alias,run_id='option_b_cpu_preflight',platform_name=platform,
                output=f'results/main/option_b_preflight_v1/{platform}/{alias}.jsonl',execute=False,
                environment_provider=forbidden)
            assert result['expected_inferences']==2000 and result['model_inferences']==0
            checks.append({'model':alias,'platform_label':platform,'result':result,'real_platform_run':False})
    blocked=[]
    for alias in ('qwen','gemma'):
        output=f'results/main/option_b_preflight_v1/blocked/{alias}.jsonl'
        try:
            run_main(b,alias=alias,run_id='option_b_blocked',platform_name='local',output=output,
                     execute=True,smoke_per_task=1,environment_provider=forbidden)
        except ValueError as exc:
            assert 'blocked' in str(exc);blocked.append({'model':alias,'message':str(exc)})
        else:raise AssertionError('Pending main execution must fail')
        assert not (ROOT/output).exists() and not (ROOT/output).with_suffix('.meta.json').exists()
    original={r['image_path']:r for r in [json.loads(s) for s in
        (ROOT/'reports/audits/2026-11-24/image_dimensions.jsonl').read_text().splitlines()]}
    inputs=[]
    for path,row in original.items():
        before=sha256_file(ROOT/path);image,wh=prepare_main_image(ROOT/path,b.config.preprocess)
        assert before==row['image_sha256'] and before==sha256_file(ROOT/path)
        assert image.mode=='RGB' and list(image.size)==wh==row['original_wh']
        inputs.append({'dataset':row['dataset'],'source_wh':wh,'processor_input_wh':list(image.size)})
    assert len(inputs)==813 and 'torch' not in sys.modules and 'transformers' not in sys.modules
    write_json(folder/'cpu_checks.json',{'scope':'CPU only; no inference/no human approvals/no freeze',
        'grid_path':grid.relative_to(ROOT).as_posix(),'grid_sha256':sha256_file(grid),'grid_cells':4000,
        'legacy_A_grid_unchanged':True,'all_rows_source_and_ground_truth_unchanged':True,
        'dry_runs':checks,'blocked_execute':blocked,'source_images_checked':len(inputs),
        'datasets':dict(Counter(r['dataset'] for r in inputs)),
        'all_RGB_and_source_WH_preserved':True,'source_image_hashes_preserved':True,
        'examples':inputs[:6],'torch_or_transformers_imported':False,'new_model_generations':0})
    print(json.dumps({'cells':4000,'dry_runs':len(checks),'blocked_models':len(blocked),'RGB_original_size_images':813}))


if __name__=='__main__':main()
