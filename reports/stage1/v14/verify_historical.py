"""Replay immutable diagnostic evidence with the exact published historical source; CPU only."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
REF='1a253f6dc94e4432f657493241daa28d9d4d5f11'


def main():
    snapshot=ROOT/'reports/maintenance/2026-11-24/option_b/legacy_source_1a253f6'
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only',REF,'--','src'],cwd=ROOT).decode().splitlines()
    for relative in paths:
        target=(snapshot/relative).resolve()
        assert target.is_relative_to(snapshot.resolve())
        content=subprocess.check_output(['git','show',f'{REF}:{relative}'],cwd=ROOT)
        if target.exists():assert target.read_bytes()==content,relative
        else:
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
    code=r'''
import json,sys
from pathlib import Path
from vlmbench.baseline_contract import build_plan
from vlmbench.repope_diagnostic import diagnostic_plan,read_run
from vlmbench.image_ab import summarize
root=Path.cwd()
import vlmbench
assert 'legacy_source_1a253f6' in str(Path(vlmbench.__file__).resolve())
plan=diagnostic_plan(root,30)
historical=json.loads((root/'reports/validation/repope_image_ab_v1/metrics.json').read_text(encoding='utf-8'))
assert plan.summary['config_fingerprint']==historical['config_fingerprint']
records=[]
for phase in ['phase1','phase2']:
    for model in ['qwen','gemma']:
        records.extend(read_run(root/f'results/pilot/repope_image_ab_v1/{phase}/{model}',plan,alias=model)[1])
result=summarize(plan,records)
for key in ['metrics','AB_comparisons','EN_VI_consistency']:
    assert [r for r in result[key] if r['task']=='object_existence']==historical[key],key
legacy=build_plan(root,root/'configs/baseline_v3_draft.yaml')
assert legacy.config.preprocess.policy_id=='rgb_thumbnail_lanczos_v1'
assert legacy.summary()['expected_inferences']==4000
assert 'torch' not in sys.modules and 'transformers' not in sys.modules
print(json.dumps({'historical_source_module':str(Path(vlmbench.__file__).resolve()),
    'diagnostic_fingerprint':plan.summary['config_fingerprint'],'historical_records_replayed':len(records),
    'metrics_exact_match':True,'legacy_A_grid_cells':4000,'model_generation_calls':0,
    'torch_or_transformers_imported':False}))
'''
    env=dict(os.environ,PYTHONPATH=str(snapshot/'src'))
    result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8')
    if result.returncode:raise RuntimeError(result.stderr)
    report={'source_commit':REF,'source_files_restored':len(paths),'scope':'CPU replay with historical source; no historical files rewritten',
        'result':json.loads(result.stdout),'exit_code':result.returncode}
    target=Path(__file__).with_name('historical_replay.json')
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
