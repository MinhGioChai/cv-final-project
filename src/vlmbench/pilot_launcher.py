"""One safe entry point for team reruns; historical adapters/config hashes stay intact."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def command(root,*,python,model,platform,limit,run_name='smoke_001',output=None,
            dry_run=False,resume=False,retry_failed=False,online=False):
    if model not in {'qwen','gemma'} or platform not in {'local','colab','kaggle'}:
        raise ValueError('Choose qwen/gemma and local/colab/kaggle')
    if not 1<=limit<=10:raise ValueError('Team pilot supports 1–10 rows/model, not main inference')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',run_name):raise ValueError('Run name must use letters/numbers/underscore/hyphen')
    root=root.resolve()
    target=(root/(output or f'results/pilot/{platform}/team_v1/{run_name}/{model}.jsonl')).resolve()
    if target.suffix!='.jsonl':raise ValueError('Output must end with .jsonl')
    if target.is_relative_to(root/'reports'):
        raise ValueError('Do not write new inference over report/evidence snapshots')
    historical={'qwen_smoke_v1.jsonl','gemma_smoke_v1.jsonl','gemma_bf16_trace_v1.jsonl',
                'gemma_bf16_trace_v2.jsonl','gemma_fp16_trace_v2.jsonl'}
    if target.parent==root/'results/pilot/local' and target.name in historical:
        raise ValueError('Historical pilot output is protected; choose a new output/run name')
    config=root/f'configs/inference/team_{model}_v1.yaml'
    if not config.is_file():raise ValueError('Current team pilot config missing; update checkout/bundle')
    argv=[str(python),'-m','vlmbench.cli','infer-pilot' if model=='qwen' else 'infer-gemma-trace',
          '--platform',platform,'--config',str(config),'--limit',str(limit),'--output',str(target)]
    if model=='qwen':argv.extend(['--model','qwen'])
    for enabled,flag in [(dry_run,'--dry-run'),(resume,'--resume'),(retry_failed,'--retry-failed')]:
        if enabled:argv.append(flag)
    if model=='gemma' and online:argv.append('--online')
    return argv


def child_environment(root,*,online,environment=None):
    env=dict(os.environ if environment is None else environment)
    env.setdefault('HF_HOME',str(root/'.cache/huggingface'))
    if online:
        env.pop('HF_HUB_OFFLINE',None);env.pop('TRANSFORMERS_OFFLINE',None)
    else:
        env['HF_HUB_OFFLINE']='1';env['TRANSFORMERS_OFFLINE']='1'
    return env


def gpu_preflight(model,torch):
    if not torch.cuda.is_available():raise RuntimeError('CUDA GPU unavailable. Use --dry-run/CPU analysis or enable a GPU runtime.')
    capability=tuple(torch.cuda.get_device_capability(0))
    if model=='gemma' and (capability[0]<8 or not torch.cuda.is_bf16_supported()):
        raise RuntimeError('Gemma pilot requires native BF16 (compute capability >= 8.0). Use Qwen on this GPU or select a BF16 GPU; no FP16 fallback.')
    return {'model':model,'gpu':torch.cuda.get_device_name(0),'capability':list(capability),
        'precision':'nf4_bf16' if model=='gemma' else 'nf4_fp16'}


def main(argv=None,*,default_model='qwen'):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',choices=['qwen','gemma'],default=default_model)
    parser.add_argument('--platform',choices=['local','colab','kaggle'],default='local')
    parser.add_argument('--limit',type=int,default=2)
    parser.add_argument('--run-name',default='smoke_001')
    parser.add_argument('--output');parser.add_argument('--python',help='Inference Python executable; otherwise local .venv-infer or current Python')
    parser.add_argument('--dry-run',action='store_true');parser.add_argument('--resume',action='store_true')
    parser.add_argument('--retry-failed',action='store_true');parser.add_argument('--online',action='store_true')
    parser.add_argument('--precision',choices=['bf16'],help='Compatibility option for Gemma helper; FP16 diagnostics use the legacy CLI explicitly')
    args=parser.parse_args(argv);root=Path(__file__).resolve().parents[2]
    if args.precision and args.model!='gemma':parser.error('--precision is only a Gemma compatibility option')
    local_python=root/'.venv-infer'/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
    python=Path(args.python) if args.python else local_python if args.platform=='local' and not args.dry_run and local_python.is_file() else Path(sys.executable)
    if not python.is_file():parser.error('Selected Python executable does not exist')
    try:
        cmd=command(root,python=python,model=args.model,platform=args.platform,limit=args.limit,
            run_name=args.run_name,output=args.output,dry_run=args.dry_run,resume=args.resume,
            retry_failed=args.retry_failed,online=args.online)
    except ValueError as exc:parser.error(str(exc))
    env=child_environment(root,online=args.online)
    if not args.dry_run:
        # Check before weights/auth downloads, using the actual inference interpreter.
        check='import json,torch; from vlmbench.pilot_launcher import gpu_preflight; print(json.dumps(gpu_preflight('+repr(args.model)+',torch)))'
        status=subprocess.run([str(python),'-c',check],cwd=root,env=env)
        if status.returncode:return status.returncode
        if args.model=='gemma' and args.online and not env.get('HF_TOKEN'):
            if not sys.stdin.isatty():
                parser.error('Set HF_TOKEN through the notebook secret or environment; token prompting requires an interactive terminal')
            env['HF_TOKEN']=getpass.getpass('HF token for your Gemma-licensed account (hidden, not saved): ')
    return subprocess.run(cmd,cwd=root,env=env).returncode
