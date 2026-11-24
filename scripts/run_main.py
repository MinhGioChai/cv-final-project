"""CPU plan by default; execute only against QA-approved, protocol-frozen main data."""
import argparse
import json
from pathlib import Path

from vlmbench.baseline_contract import build_plan, inside, smoke_selection
from vlmbench.baseline_runtime import run_main
from vlmbench.io_utils import atomic_bytes, write_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'run'], nargs='?', default='plan')
    parser.add_argument('--config', default='configs/baseline_v3_option_b_v1.yaml')
    parser.add_argument('--report', help='New preflight report path (plan only)')
    parser.add_argument('--grid-output', help='New full grid JSONL under results/ (plan only)')
    parser.add_argument('--model', choices=['qwen', 'gemma'], default='qwen')
    parser.add_argument('--run-id', default='main_smoke_v1')
    parser.add_argument('--platform', choices=['local', 'colab', 'kaggle'], default='local')
    parser.add_argument('--output')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--execute', action='store_true')
    group.add_argument('--dry-run', action='store_true')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--retry-failed', action='store_true')
    parser.add_argument('--max-cells', type=int)
    parser.add_argument('--smoke-per-task', type=int, choices=[1, 2], help='Bounded smoke with both languages for each of four tasks; full QA/freeze gates still required')
    parser.add_argument('--online', action='store_true', help='Permit Hub download only on explicit execution')
    args = parser.parse_args(argv)
    root = Path.cwd().resolve()
    if args.action == 'plan' and (args.execute or args.output or args.resume or args.retry_failed or args.online or args.max_cells is not None):
        parser.error('Execution/resume/output flags belong to run, not plan')
    if args.action == 'run' and (args.report or args.grid_output):
        parser.error('report/grid-output belong to plan')
    outputs = [inside(root, p) for p in (args.report, args.grid_output) if p]
    if len(set(outputs)) != len(outputs) or any(p.exists() for p in outputs):
        raise ValueError('Use distinct new report/grid paths; preserve existing artifacts')
    if args.grid_output and not inside(root, args.grid_output).is_relative_to(root / 'results'):
        raise ValueError('Full grid JSONL stays under results, outside Git')
    plan = build_plan(root, args.config)
    if args.action == 'plan':
        result = plan.summary()
        if args.smoke_per_task is not None:
            result['bounded_smoke'] = smoke_selection(plan, args.smoke_per_task)
        if args.report: write_json(inside(root, args.report), result)
        if args.grid_output:
            atomic_bytes(inside(root, args.grid_output), ''.join(c.model_dump_json() + '\n' for c in plan.cells).encode('utf-8'))
    else:
        output = args.output or f'results/main/{args.platform}/{args.run_id}/{args.model}.jsonl'
        result = run_main(plan, alias=args.model, run_id=args.run_id, platform_name=args.platform, output=output,
            execute=args.execute, resume=args.resume, retry_failed=args.retry_failed, offline=not args.online,
            max_cells=args.max_cells, smoke_per_task=args.smoke_per_task)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
