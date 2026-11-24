"""Main baseline execution with closed QA/freeze gates and auditable checkpoints."""
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
from types import SimpleNamespace
from typing import Literal, Self

from PIL import Image
from pydantic import Field, StrictInt, model_validator

from .baseline_contract import Hex40, Hex64, StrictModel, build_plan, inside, smoke_selection
from .environment import inspect_environment
from .gemma_diagnostic import GemmaTraceAdapter
from .io_utils import atomic_bytes, sha256_file, write_json
from .parse import parse_response
from .pilot_runtime import HuggingFaceAdapter, safe_error
from .reviews import canonical_hash


class Prediction(StrictModel):
    schema_version: Literal['baseline_prediction_v1'] = 'baseline_prediction_v1'
    run_id: str
    experiment_id: str
    cell_id: Hex64
    sample_id: str
    source_dataset: str
    source_split: str
    source_row_id: str
    source_revision: str
    source_record_sha256: Hex64
    ground_truth_source: str
    task: Literal['object_existence', 'spatial', 'counting', 'fine_grained']
    image_namespace: str
    image_id: str
    image_sha256: Hex64
    source_row_sha256: Hex64
    language: Literal['en', 'vi']
    model_alias: Literal['qwen', 'gemma']
    model_id: str
    model_revision: Hex40
    processor_revision: Hex40
    tokenizer_revision: Hex40
    precision: Literal['nf4_fp16', 'nf4_bf16']
    dtype: Literal['float16', 'bfloat16']
    device: Literal['cuda:0', 'synthetic_test_only_cpu']
    quantization_config: dict
    platform: Literal['local', 'colab', 'kaggle']
    prompt_variant: Literal['baseline']
    image_variant: Literal['original']
    prompt_version: str
    prompt_text: str
    prompt_hash: Hex64
    ground_truth: str | StrictInt
    protocol_hash: Hex64
    run_config_hash: Hex64
    generation_config: dict
    image_preprocess: dict
    code_commit: str | None
    code_dirty: bool | None
    recorded_at_utc: str
    qa_status: Literal['approved']
    translation_status: Literal['approved']
    scope: Literal['main_baseline', 'main_gpu_smoke', 'synthetic_test_only']
    attempt: int = Field(ge=1)
    raw_response: str | None = None
    parsed_prediction: str | StrictInt | None = None
    run_status: Literal['success', 'failed']
    parse_status: Literal['valid', 'invalid', 'not_attempted'] = 'not_attempted'
    parse_reason: str | None = None
    valid: bool = False
    invalid_reason: str | None = None
    used_alias: bool = False
    elapsed_ms: float | None = Field(default=None, ge=0)
    peak_allocated_mib: float | None = Field(default=None, ge=0)
    generation_trace: dict | None = None
    error: dict[str, str] | None = None
    original_image_size_wh: list[StrictInt] | None = Field(default=None, min_length=2, max_length=2)
    processor_input_size_wh: list[StrictInt] | None = Field(default=None, min_length=2, max_length=2)

    @model_validator(mode='after')
    def semantics(self) -> Self:
        for size in (self.original_image_size_wh, self.processor_input_size_wh):
            if size is not None and any(value < 1 for value in size):
                raise ValueError('Image dimensions must be positive')
        if self.image_preprocess.get('policy_id') == 'original_rgb_processor_v1' and self.run_status == 'success':
            if self.original_image_size_wh is None or self.processor_input_size_wh != self.original_image_size_wh:
                raise ValueError('Option B processor input must retain source dimensions')
        if self.run_status == 'success':
            if self.raw_response is None:
                raise ValueError('A successful generation requires a raw text response')
            parsed = parse_response(self.raw_response, self.task)
            if (self.parse_status != parsed.status or self.valid != (parsed.status == 'valid')
                or type(self.parsed_prediction) is not type(parsed.prediction) or self.parsed_prediction != parsed.prediction
                or self.parse_reason != parsed.reason or self.used_alias != parsed.used_alias
                or self.invalid_reason != (None if self.valid else parsed.reason) or self.error is not None):
                raise ValueError('Saved parse/validity differs from the full-answer parser')
        elif (self.parse_status != 'not_attempted' or self.parsed_prediction is not None or self.valid
              or not self.error or self.invalid_reason != 'GENERATION_FAILED'):
            raise ValueError('Failed generation must retain failure, not a parsed answer')
        return self


class GenerationResult(StrictModel):
    raw_response: str
    elapsed_ms: float | None = Field(default=None, ge=0)
    peak_allocated_mib: float | None = Field(default=None, ge=0)
    generation_trace: dict | None = None


@contextmanager
def hub_mode(offline):
    names = ('HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE')
    previous = {name: os.environ.get(name) for name in names}
    try:
        for name in names:
            if offline: os.environ[name] = '1'
            else: os.environ.pop(name, None)
        yield
    finally:
        for name, value in previous.items():
            if value is None: os.environ.pop(name, None)
            else: os.environ[name] = value


class MainAdapter:
    """Reuse verified pilot adapters; no pilot selection or precision fallback."""
    def __init__(self, plan, alias, offline):
        spec = plan.config.models[alias]
        config = SimpleNamespace(**plan.config.preprocess.model_dump(), **spec.model_dump(),
            seed=plan.config.seed, max_new_tokens=plan.config.generation.max_new_tokens,
            trace_version='gemma_token_logits_v1')
        self.alias, self.offline = alias, offline
        model = {'model_id': spec.model_id, 'revision': spec.revision}
        self.adapter = (HuggingFaceAdapter(alias, model, config) if alias == 'qwen'
                        else GemmaTraceAdapter(model, config, offline=offline))

    def load_model(self):
        # Hardware is tested only after plan gates and explicit execute, before Hub access.
        import torch
        from .pilot_launcher import gpu_preflight
        gpu_preflight(self.alias, torch)
        with hub_mode(self.offline):
            self.adapter.load_model()

    def generate(self, image, prompt):
        return self.adapter.generate(image, prompt)

    def unload_model(self):
        self.adapter.unload_model()


def code_state(root):
    if not (root / '.git').exists():
        return {'code_commit': None, 'code_dirty': None}
    try:
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, stderr=subprocess.DEVNULL).decode().strip()
        dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=root))
        return {'code_commit': head, 'code_dirty': dirty}
    except (OSError, subprocess.SubprocessError):
        return {'code_commit': None, 'code_dirty': None}


def _history(output, cells, expected):
    records, by_key = [], defaultdict(list)
    if not output.exists():
        return records, by_key
    by_cell = {c.cell_id: c for c in cells}
    for number, text in enumerate(output.read_text(encoding='utf-8').splitlines(), 1):
        try:
            record = Prediction.model_validate_json(text)
        except ValueError:
            raise ValueError(f'Corrupt baseline JSONL at line {number}; preserve the file before repair') from None
        if record.cell_id not in by_cell:
            raise ValueError('Checkpoint contains a cell outside this run grid')
        cell = by_cell[record.cell_id]
        data = record.model_dump()
        for key, value in expected[cell.cell_id].items():
            if key not in {'recorded_at_utc', 'attempt', 'run_status'} and data[key] != value:
                raise ValueError('Checkpoint identity/content differs: ' + key)
        history = by_key[record.cell_id]
        if record.attempt != len(history) + 1 or any(r['run_status'] == 'success' for r in history):
            raise ValueError('Duplicate/nonconsecutive attempt or retry after success')
        records.append(data)
        history.append(data)
    return records, by_key


def prepare_main_image(path, preprocess):
    """Decode/RGB once; only historical Option A adds a thumbnail. Never writes source bytes."""
    with Image.open(path) as original:
        original_wh = list(original.size)
        image = original.convert('RGB')
    if preprocess.policy_id == 'rgb_thumbnail_lanczos_v1':
        image.thumbnail((preprocess.image_max_edge,) * 2, Image.Resampling.LANCZOS)
    elif preprocess.policy_id != 'original_rgb_processor_v1':
        raise ValueError('Unknown main preprocessing policy')
    return image, original_wh


def run_main(plan, *, alias, run_id, platform_name, output, execute=False, resume=False,
             retry_failed=False, offline=True, max_cells=None, adapter_factory=None,
             synthetic_test_only=False, environment_provider=inspect_environment, smoke_per_task=None):
    if alias not in plan.config.models or platform_name not in {'local', 'colab', 'kaggle'}:
        raise ValueError('Choose qwen/gemma and local/colab/kaggle')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', run_id):
        raise ValueError('Use a simple run_id with letters/numbers/underscore/hyphen')
    output = inside(plan.root, output)
    if not output.is_relative_to(plan.root / 'results/main') or output.suffix != '.jsonl':
        raise ValueError('New baseline output must be JSONL under results/main')
    if max_cells is not None and (type(max_cells) is not int or max_cells < 1):
        raise ValueError('max_cells must be a positive explicit execution bound')
    bounded = smoke_selection(plan, smoke_per_task) if smoke_per_task is not None else None
    if bounded and max_cells is not None:
        raise ValueError('Do not truncate the four-task smoke with max_cells')
    cells = [c for c in plan.cells if c.model == alias]
    if not execute:
        return {**plan.summary(), **({'bounded_smoke': bounded} if bounded else {}), 'dry_run': True, 'model': alias,
                'expected_inferences': len(cells), 'sample_ids': [r.sample_id for r in plan.rows]}
    # Rebuild from source before heavy imports: never trust a mutated/stale plan object.
    fresh = build_plan(plan.root, plan.config_path)
    if fresh.protocol_hash != plan.protocol_hash:
        raise ValueError('Plan is stale; input/config/code changed since preflight')
    plan = fresh
    bounded = smoke_selection(plan, smoke_per_task) if smoke_per_task is not None else None
    cells = [c for c in plan.cells if c.model == alias]
    if plan.issues:
        raise ValueError('Main execution blocked: ' + ', '.join(sorted({i['code'] for i in plan.issues})))
    if adapter_factory is not None and not synthetic_test_only:
        raise ValueError('Injected adapters must be marked synthetic_test_only')
    if synthetic_test_only and adapter_factory is None:
        raise ValueError('Synthetic execution requires an injected adapter; never call a real model')
    spec = plan.config.models[alias]
    environment = environment_provider()
    code = code_state(plan.root)
    scope = 'synthetic_test_only' if synthetic_test_only else 'main_gpu_smoke' if bounded else 'main_baseline'
    identity = {'protocol_hash': plan.protocol_hash, 'model': alias, 'platform': platform_name, 'run_id': run_id,
        'scope': scope, 'freeze_sha256': plan.freeze_sha256, **code,
        'environment': {k: environment[k] for k in ('python', 'os', 'packages', 'gpus')}}
    if bounded:
        identity['bounded_smoke'] = bounded
    run_hash = canonical_hash(identity)
    expected = {}
    by_id = {r.sample_id: r for r in plan.rows}
    for cell in cells:
        row = by_id[cell.sample_id]
        expected[cell.cell_id] = {'run_id': run_id, 'experiment_id': plan.config.experiment_id,
            **cell.model_dump(exclude={'model'}), 'model_alias': alias, 'source_dataset': row.source_dataset,
            'source_split': row.source_split, 'source_row_id': row.source_row_id,
            'source_revision': row.metadata['source_revision'], 'source_record_sha256': row.metadata['source_record_sha256'],
            'ground_truth_source': row.ground_truth_source,
            'task': row.task, 'image_namespace': row.metadata['image_namespace'], 'image_id': row.image_id,
            'image_sha256': row.image_sha256, 'model_id': spec.model_id, 'model_revision': spec.revision,
            'processor_revision': spec.processor_revision, 'tokenizer_revision': spec.tokenizer_revision,
            'precision': spec.precision, 'dtype': 'float16' if alias == 'qwen' else 'bfloat16',
            'device': 'synthetic_test_only_cpu' if synthetic_test_only else 'cuda:0',
            'quantization_config': {'load_in_4bit': True, 'bnb_4bit_quant_type': 'nf4', 'bnb_4bit_use_double_quant': True,
                                   'bnb_4bit_compute_dtype': 'float16' if alias == 'qwen' else 'bfloat16'},
            'platform': platform_name, 'prompt_version': plan.protocol['prompt_version'],
            'ground_truth': row.ground_truth, 'protocol_hash': plan.protocol_hash, 'run_config_hash': run_hash,
            'generation_config': plan.config.generation.model_dump(), 'image_preprocess': {
                **plan.config.preprocess.model_dump(), 'processor': plan.protocol['processor_policy'][alias]},
            **code, 'qa_status': row.qa_status, 'translation_status': row.translation_status, 'scope': scope}
    meta_path = output.with_suffix('.meta.json')
    summary_path = output.with_suffix('.summary.json')
    if not resume and any(p.exists() for p in (output, meta_path, summary_path, output.with_suffix('.load_error.json'))):
        raise ValueError('Run output already exists; use explicit resume or a new run path')
    if meta_path.exists():
        metadata = json.loads(meta_path.read_text(encoding='utf-8'))
        if not isinstance(metadata, dict) or not isinstance(metadata.get('environment'), dict):
            raise ValueError('Corrupt baseline run metadata; preserve it before repair')
        if (metadata.get('identity') != identity or metadata.get('run_config_hash') != run_hash
            or metadata.get('schema_version') != 'baseline_run_v1' or metadata.get('protocol') != plan.protocol
            or metadata.get('expected_inferences') != len(cells) or metadata.get('selected_rows') != len(plan.rows)
            or metadata.get('sample_ids') != [r.sample_id for r in plan.rows]
            or {k: metadata.get('environment', {}).get(k) for k in ('python', 'os', 'packages', 'gpus')} != identity['environment']):
            raise ValueError('Resume metadata differs in protocol/model/runtime/code/run ID')
    elif output.exists() or summary_path.exists():
        raise ValueError('Prediction metadata is missing; restore it before resume')
    records, by_key = _history(output, cells, expected)
    allowed_smoke = {c.cell_id for c in cells if bounded and c.sample_id in bounded['sample_ids']}
    if bounded and any(r['cell_id'] not in allowed_smoke for r in records):
        raise ValueError('Checkpoint contains cells outside bounded smoke selection')
    pending = [c for c in cells if not by_key[c.cell_id] or
               (retry_failed and by_key[c.cell_id][-1]['run_status'] == 'failed')]
    if bounded:
        pending = [c for c in pending if c.cell_id in allowed_smoke]
    if max_cells is not None:
        pending = pending[:max_cells]
    if not meta_path.exists():
        write_json(meta_path, {'schema_version': 'baseline_run_v1', 'identity': identity,
            'run_config_hash': run_hash, 'protocol': plan.protocol, 'environment': environment,
            'expected_inferences': len(cells), 'selected_rows': len(plan.rows),
            'sample_ids': [r.sample_id for r in plan.rows], 'offline_at_creation': offline})
    adapter = None
    processor_observer = None
    stop_reason = None
    calls = 0
    try:
        if pending:
            adapter = adapter_factory(plan, alias, offline) if adapter_factory else MainAdapter(plan, alias, offline)
            try:
                adapter.load_model()
                if adapter_factory is None:
                    # Reuse the diagnostic's tested pass-through observer, only for main execution.
                    from .image_ab import ObservedProcessor
                    processor_observer = ObservedProcessor(adapter.adapter.processor)
                    adapter.adapter.processor = processor_observer
            except Exception as exc:
                write_json(output.with_suffix('.load_error.json'), {'phase': 'model_load',
                    'error': safe_error(exc), 'protocol_hash': plan.protocol_hash, 'run_config_hash': run_hash})
                raise RuntimeError('Main model load failed; see sanitized .load_error.json') from None
        for cell in pending:
            row = by_id[cell.sample_id]
            record = {**expected[cell.cell_id], 'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
                'attempt': len(by_key[cell.cell_id]) + 1, 'run_status': 'failed', 'invalid_reason': 'GENERATION_FAILED'}
            memory_before = None
            if processor_observer is not None:
                processor_observer.last = {}
            try:
                if sha256_file(inside(plan.root, row.image_path)) != row.image_sha256:
                    raise ValueError('Image bytes changed after preflight')
                image, original_wh = prepare_main_image(inside(plan.root, row.image_path), plan.config.preprocess)
                record.update(original_image_size_wh=original_wh, processor_input_size_wh=list(image.size))
                calls += 1
                if processor_observer is not None:
                    cuda = adapter.adapter.torch.cuda
                    memory_before = {'allocated_mib': cuda.memory_allocated(0) / 1024 ** 2,
                                     'reserved_mib': cuda.memory_reserved(0) / 1024 ** 2}
                raw_result = adapter.generate(image, cell.prompt_text)
                if processor_observer is not None and isinstance(raw_result, dict):
                    trace = dict(raw_result.get('generation_trace') or {})
                    trace['image_processor_observation'] = processor_observer.last
                    trace['gpu_memory'] = {'before': memory_before,
                        'peak_reserved_mib': cuda.max_memory_reserved(0) / 1024 ** 2}
                    raw_result['generation_trace'] = trace
                # Retain raw text even if the adapter's diagnostic fields fail validation.
                if isinstance(raw_result, dict) and isinstance(raw_result.get('raw_response'), str):
                    record['raw_response'] = raw_result['raw_response']
                result = GenerationResult.model_validate(raw_result)
                record.update(result.model_dump(exclude_none=True))
                if (record.get('generation_trace') or {}).get('all_raw_logits_finite') is False:
                    raise RuntimeError('Non-finite raw generation logits; original trace retained')
                parsed = parse_response(record.get('raw_response'), row.task)
                record.update(run_status='success', parsed_prediction=parsed.prediction, parse_status=parsed.status,
                    parse_reason=parsed.reason, valid=parsed.status == 'valid', used_alias=parsed.used_alias,
                    invalid_reason=None if parsed.status == 'valid' else parsed.reason)
                # Serialization problems are run failures, never silent dropped records.
                record = Prediction.model_validate(record).model_dump()
                json.dumps(record, allow_nan=False)
            except Exception as exc:
                record.update(run_status='failed', parsed_prediction=None, parse_status='not_attempted',
                    parse_reason=None, valid=False, used_alias=False, invalid_reason='GENERATION_FAILED', error=safe_error(exc))
                if processor_observer is not None:
                    trace = dict(record.get('generation_trace') or {})
                    trace['image_processor_observation'] = processor_observer.last
                    try:
                        trace['gpu_memory'] = {'before': memory_before,
                            'peak_reserved_mib': adapter.adapter.torch.cuda.max_memory_reserved(0) / 1024 ** 2}
                    except Exception as memory_exc:
                        trace['memory_observation_error'] = safe_error(memory_exc)
                    record['generation_trace'] = trace
                # NaN diagnostic tensors must not corrupt JSONL; keep finite trace summaries.
                for key in ('elapsed_ms', 'peak_allocated_mib', 'generation_trace'):
                    try: json.dumps(record.get(key), allow_nan=False)
                    except (ValueError, TypeError): record[key] = None
                record = Prediction.model_validate(record).model_dump()
                if 'outofmemory' in type(exc).__name__.lower() or 'out of memory' in str(exc).lower():
                    stop_reason = 'stopped_after_oom_no_automatic_config_change'
            records.append(record)
            by_key[cell.cell_id].append(record)
            atomic_bytes(output, ''.join(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n' for r in records).encode('utf-8'))
            if stop_reason:
                break
    finally:
        if adapter is not None:
            adapter.unload_model()
    latest = [by_key[c.cell_id][-1] for c in cells if by_key[c.cell_id]]
    counts = Counter('failed' if r['run_status'] == 'failed' else r['parse_status'] for r in latest)
    summary = {'schema_version': 'baseline_summary_v1', 'scope': scope, 'dry_run': False,
        'model': alias, 'run_id': run_id, 'protocol_hash': plan.protocol_hash, 'run_config_hash': run_hash,
        'model_revision': spec.revision, 'selected_rows': len(plan.rows), 'expected_inferences': len(cells),
        'sample_ids': [r.sample_id for r in plan.rows], 'valid': counts['valid'], 'invalid': counts['invalid'],
        'failed': counts['failed'], 'missing': len(cells) - len(latest), 'generation_calls_this_invocation': calls,
        'total_attempts_in_file': len(records), 'stop_reason': stop_reason}
    if bounded:
        smoke_latest = [r for r in latest if r['cell_id'] in allowed_smoke]
        summary['bounded_smoke'] = {**bounded, 'recorded_cells': len(smoke_latest),
            'missing_smoke_cells': len(allowed_smoke) - len(smoke_latest)}
    write_json(summary_path, summary)
    return summary
