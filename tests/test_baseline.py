"""CPU synthetic tests; fake reviewers/models here never approve project data."""
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image
import pytest
import yaml

from vlmbench.baseline_contract import (BaselineConfig, MODEL_IDS, PET_LABELS, PromptSet,
                                       build_plan, inside)
from vlmbench.baseline_runtime import MainAdapter, Prediction, hub_mode, run_main
from vlmbench.datasets.candidates import Candidate
from vlmbench.evaluate import evaluate_run, read_predictions, seal_report
from vlmbench.io_utils import read_manifest, sha256_file, write_json, write_manifest
from vlmbench.main_review_v2 import MainDecision, POLICY
from vlmbench.reviews import canonical_hash
from vlmbench.statistics import statistics_for_evaluation

REPO = Path(__file__).resolve().parents[1]


def fake_environment():
    return {'python': 'synthetic_test_only', 'os': 'test', 'packages': {}, 'gpus': []}


@pytest.fixture
def project(tmp_path, row_factory):
    config = yaml.safe_load((REPO / 'configs/baseline_v3_draft.yaml').read_text(encoding='utf-8'))
    config.update(experiment_id='synthetic_test_only', manifests=['main.csv'],
        source_selection='selection.jsonl', pilot_manifest='pilot.csv', pilot_exclusions='exclusions.json',
        prompts='prompts.yaml', targets={'repope': 2, 'vsr': 1, 'tallyqa': 1, 'oxford_pet': 1})
    (tmp_path / 'prompts.yaml').write_bytes((REPO / 'configs/prompts_baseline_v1.yaml').read_bytes())
    rows, sources = [], []
    tasks = [('repope', 'object_existence', 'no'), ('repope', 'object_existence', 'no'),
             ('vsr', 'spatial', 'no'), ('tallyqa', 'counting', 2), ('oxford_pet', 'fine_grained', 'A')]
    for i, (dataset, task, truth) in enumerate(tasks):
        path = tmp_path / f'image_{i}.png'
        Image.new('RGB', (8, 6), color=(i * 30, 40, 90)).save(path)
        meta = {'synthetic_test_only': True, 'image_namespace': dataset, 'source_revision': 'a' * 40,
                'source_record_sha256': canonical_hash({'synthetic': i})}
        if dataset == 'oxford_pet': meta['candidate_labels'] = PET_LABELS
        row = row_factory(sample_id=f'synthetic_test_only_{i}', source_dataset=dataset, task=task,
            ground_truth=truth, is_pilot=False, question_en=f'synthetic_test_only_{dataset} question {i}',
            question_vi=f'synthetic_test_only_vi {dataset} {i}', image_path=path.name, image_sha256=sha256_file(path),
            image_id=str(i), translation_status='requires_review', metadata=meta)
        rows.append(row)
        sources.append(Candidate(**{k: getattr(row, k) for k in ['sample_id', 'source_dataset', 'source_split',
            'source_row_id', 'image_id', 'task', 'category', 'question_en', 'ground_truth']},
            source_revision=meta['source_revision'], source_record_sha256=meta['source_record_sha256'],
            image_namespace=meta['image_namespace'], source_image_ref=path.name, metadata={}))
    write_manifest(tmp_path / 'main.csv', rows)
    (tmp_path / 'selection.jsonl').write_text(''.join(s.model_dump_json() + '\n' for s in sources), encoding='utf-8')
    pilot = row_factory(sample_id='synthetic_test_only_pilot', image_id='999', question_vi='synthetic',
                        translation_status='approved', qa_status='approved')
    write_manifest(tmp_path / 'pilot.csv', [pilot])
    write_json(tmp_path / 'exclusions.json', {'images': [{'image_namespace': 'coco',
        'image_id': pilot.image_id, 'image_sha256': pilot.image_sha256}]})
    path = tmp_path / 'run.yaml'; path.write_text(yaml.safe_dump(config), encoding='utf-8')
    return tmp_path, path, config


def approve_synthetic_rows(root):
    rows = read_manifest(root / 'main.csv')
    for row in rows:
        d = MainDecision(sample_id=row.sample_id, question_vi=row.question_vi)
        for slot, owner in [('reviewer_a', 'synthetic_test_only_A'), ('reviewer_b', 'synthetic_test_only_B')]:
            review = getattr(d, slot)
            for name in ('translation', 'image_qa'):
                part = getattr(review, name)
                part.status = 'approved'; part.reviewer_id = owner
                part.reviewed_at = '2026-11-22T10:00:00+07:00'; part.reviewed_question_vi = row.question_vi
                if name == 'image_qa': part.observed_answer = str(row.ground_truth)
        row.qa_status = row.translation_status = 'approved'
        row.metadata['main_review'] = {'schema_version': 'main_review_v2', 'policy': POLICY, 'decision': d.model_dump()}
    write_manifest(root / 'main.csv', rows)


def freeze_synthetic(project):
    root, path, config = project
    approve_synthetic_rows(root)
    config.update(frozen=True, freeze_receipt='freeze.json')
    path.write_text(yaml.safe_dump(config), encoding='utf-8')
    plan = build_plan(root, path)
    write_json(root / 'freeze.json', {'schema_version': 'baseline_freeze_v1', 'protocol_hash': plan.protocol_hash,
        'approved_by': 'synthetic_test_only_operator', 'approved_at': '2026-11-22T10:00:00+07:00',
        'notes': 'synthetic_test_only fixture, never real human approval'})
    return build_plan(root, path)


@pytest.fixture
def adapter():
    class Fake:
        calls = 0
        loads = 0
        unloads = 0
        def __init__(self, *args): pass
        def load_model(self): type(self).loads += 1
        def unload_model(self): type(self).unloads += 1
        def generate(self, image, prompt):
            type(self).calls += 1
            raw = '2' if 'tallyqa' in prompt else 'A' if 'oxford_pet' in prompt else 'FALSE' if 'vsr' in prompt else 'NO'
            return {'raw_response': raw, 'elapsed_ms': 1.0, 'peak_allocated_mib': 0.0}
    return Fake


def options(plan, adapter, **changes):
    return dict(plan=plan, alias='qwen', run_id='synthetic_test_only', platform_name='local',
        output='results/main/synthetic_test_only/qwen.jsonl', execute=True,
        adapter_factory=adapter, synthetic_test_only=True, environment_provider=fake_environment, **changes)


def test_draft_grid_is_deterministic_and_gate_blocks_before_environment_or_adapter(project, adapter):
    root, path, _ = project
    plan = build_plan(root, path)
    assert len(plan.cells) == 20 and len({c.cell_id for c in plan.cells}) == 20
    assert plan.summary()['expected_per_model'] == {'gemma': 10, 'qwen': 10}
    assert build_plan(root, path).summary() == plan.summary()
    def forbidden(): raise AssertionError('No runtime inventory before closed QA gates')
    opts = options(plan, adapter); opts['environment_provider'] = forbidden
    with pytest.raises(ValueError, match='blocked'): run_main(**opts)
    assert not (root / 'results').exists() and adapter.calls == adapter.loads == 0
    dry = run_main(**{**opts, 'execute': False})
    assert dry['expected_inferences'] == 10 and dry['model_inferences'] == 0


def test_prompts_keep_manifest_question_and_fixed_labels(project):
    root, path, _ = project; plan = build_plan(root, path)
    by_id = {r.sample_id: r for r in plan.rows}
    for cell in plan.cells:
        row = by_id[cell.sample_id]
        assert getattr(row, 'question_' + cell.language) in cell.prompt_text
        if row.task == 'spatial': assert 'TRUE' in cell.prompt_text and 'FALSE' in cell.prompt_text
        if row.task == 'fine_grained':
            assert all(f'{k}: {v}' in cell.prompt_text for k, v in PET_LABELS.items())


@pytest.mark.parametrize('mutation', ['labels', 'source_question', 'source_revision', 'duplicates', 'scope', 'path'])
def test_source_routing_and_path_tampering_rejected(project, mutation):
    root, path, config = project; rows = read_manifest(root / 'main.csv')
    if mutation == 'labels': rows[-1].metadata['candidate_labels'] = {'A': 'changed'}
    if mutation == 'source_question': rows[0].question_en = 'changed'
    if mutation == 'source_revision': rows[0].metadata['source_revision'] = 'changed'
    if mutation == 'duplicates': rows.append(rows[0])
    if mutation == 'scope': rows[0].task = 'negation'
    if mutation == 'path': rows[0].image_path = '../outside.png'
    write_manifest(root / 'main.csv', rows)
    with pytest.raises(ValueError): build_plan(root, path)


@pytest.mark.parametrize('mutation', ['same_reviewer', 'one_qa', 'stale_qa', 'missing_proof'])
def test_approved_flags_alone_cannot_bypass_two_reviewer_proof(project, mutation):
    root, path, _ = project; approve_synthetic_rows(root); rows = read_manifest(root / 'main.csv')
    d = rows[0].metadata['main_review']['decision']
    if mutation == 'same_reviewer':
        d['reviewer_b']['translation']['reviewer_id'] = d['reviewer_b']['image_qa']['reviewer_id'] = 'synthetic_test_only_A'
    if mutation == 'one_qa': d['reviewer_b']['image_qa']['status'] = 'pending'
    if mutation == 'stale_qa': d['reviewer_b']['image_qa']['reviewed_question_vi'] = 'old'
    if mutation == 'missing_proof': rows[0].metadata.pop('main_review')
    write_manifest(root / 'main.csv', rows)
    plan = build_plan(root, path)
    assert 'TWO_REVIEWER_PROOF_REQUIRED' in plan.summary()['blocking_counts']


def test_freeze_receipt_is_protocol_bound_and_not_an_approval_shortcut(project, adapter):
    plan = freeze_synthetic(project); assert not plan.issues
    root, path, config = project
    receipt = json.loads((root / 'freeze.json').read_text())
    receipt['protocol_hash'] = '0' * 64; write_json(root / 'freeze.json', receipt)
    invalid = build_plan(root, path)
    assert invalid.summary()['blocking_counts'] == {'FREEZE_RECEIPT_INVALID_OR_MISSING': 1}
    with pytest.raises(ValueError, match='blocked'): run_main(**options(invalid, adapter))


def test_pilot_registry_and_image_byte_leakage_both_block(project):
    root, path, _ = project; rows = read_manifest(root / 'main.csv')
    write_json(root / 'exclusions.json', {'images': [{'image_namespace': rows[0].metadata['image_namespace'],
        'image_id': rows[0].image_id, 'image_sha256': rows[1].image_sha256}]})
    assert build_plan(root, path).summary()['blocking_counts']['PILOT_REGISTRY_OVERLAP'] == 2


def test_both_models_resume_and_feed_existing_evaluation_ci(project, adapter):
    plan = freeze_synthetic(project)
    for alias in ('qwen', 'gemma'):
        opts = options(plan, adapter)
        opts.update(alias=alias, output=f'results/main/synthetic_test_only/{alias}.jsonl')
        summary = run_main(**opts)
        assert summary['valid'] == 10 and summary['missing'] == 0 and summary['scope'] == 'synthetic_test_only'
        calls = adapter.calls
        again = run_main(**opts, resume=True)
        assert adapter.calls == calls and again['generation_calls_this_invocation'] == 0
        path = plan.root / opts['output']
        records = read_predictions(path)
        assert all(r['valid'] and r['invalid_reason'] is None for r in records)
        evaluation = seal_report(evaluate_run(plan.rows, records, summary))
        stats = statistics_for_evaluation(evaluation, n_resamples=100, seed=42)
        assert len(evaluation['groups']) == 4
        assert all(g['languages']['en']['accuracy'] == g['languages']['vi']['accuracy'] == 1 for g in evaluation['groups'])
        assert evaluation['primary_repope']['delta_fpr_pp'] == stats['primary_repope']['estimate_pp'] == 0
        assert stats['primary_repope']['n_image_clusters'] == 2


def test_invalid_generation_is_retained_and_never_retried_as_failure(project, adapter):
    class Invalid(adapter):
        def generate(self, image, prompt):
            type(self).calls += 1
            return {'raw_response': 'yes and no', 'elapsed_ms': 1.0}
    plan = freeze_synthetic(project); opts = options(plan, Invalid)
    result = run_main(**opts)
    assert result['invalid'] == 10 and result['failed'] == 0
    assert run_main(**opts, resume=True, retry_failed=True)['total_attempts_in_file'] == 10
    assert Invalid.calls == 10


@pytest.mark.parametrize('mutation', ['nan_logits', 'negative_time', 'none_trace', 'forged_label'])
def test_adapter_diagnostics_cannot_corrupt_json_or_replace_source(project, adapter, mutation):
    class Broken(adapter):
        def generate(self, image, prompt):
            result = super().generate(image, prompt)
            if mutation == 'nan_logits': result['generation_trace'] = {'all_raw_logits_finite': False, 'n_nan': 1}
            if mutation == 'negative_time': result['elapsed_ms'] = -1.0
            if mutation == 'none_trace': result['generation_trace'] = None
            if mutation == 'forged_label': result['ground_truth'] = 'changed'
            return result
    plan = freeze_synthetic(project); opts = options(plan, Broken)
    summary = run_main(**opts)
    assert summary['valid' if mutation == 'none_trace' else 'failed'] == 10
    records = read_predictions(plan.root / opts['output'])
    assert all(r['raw_response'] is not None for r in records)
    assert records[0]['ground_truth'] == plan.rows[0].ground_truth
    assert 'NaN' not in (plan.root / opts['output']).read_text(encoding='utf-8')


def test_metadata_selection_tampering_cannot_change_expected_grid(project, adapter):
    plan = freeze_synthetic(project); opts = options(plan, adapter)
    run_main(**opts, max_cells=2)
    meta = (plan.root / opts['output']).with_suffix('.meta.json')
    data = json.loads(meta.read_text(encoding='utf-8')); data['sample_ids'] = [data['sample_ids'][0]]
    write_json(meta, data)
    with pytest.raises(ValueError, match='metadata differs'): run_main(**opts, resume=True)


def test_failure_only_retries_explicitly_and_attempt_history_is_preserved(project, adapter):
    class FailOnce(adapter):
        def generate(self, image, prompt):
            result = super().generate(image, prompt)
            if type(self).calls == 1: raise ValueError('synthetic_test_only failure')
            return result
    plan = freeze_synthetic(project); opts = options(plan, FailOnce)
    assert run_main(**opts)['failed'] == 1
    assert run_main(**opts, resume=True)['failed'] == 1
    result = run_main(**opts, resume=True, retry_failed=True)
    assert result['valid'] == 10 and result['total_attempts_in_file'] == 11
    assert len(read_predictions(plan.root / opts['output'])) == 11


def test_oom_stops_leaves_missing_and_never_changes_precision(project, adapter):
    class OOM(adapter):
        def generate(self, image, prompt): raise RuntimeError('CUDA out of memory synthetic_test_only')
    plan = freeze_synthetic(project); opts = options(plan, OOM)
    result = run_main(**opts)
    assert result['failed'] == 1 and result['missing'] == 9
    assert 'oom' in result['stop_reason']
    record = read_predictions(plan.root / opts['output'])[0]
    assert record['precision'] == 'nf4_fp16' and record['invalid_reason'] == 'GENERATION_FAILED'


def test_ctrl_c_preserves_previous_atomic_checkpoint(project, adapter):
    class Interrupt(adapter):
        def generate(self, image, prompt):
            result = super().generate(image, prompt)
            if type(self).calls == 2: raise KeyboardInterrupt()
            return result
    plan = freeze_synthetic(project); opts = options(plan, Interrupt)
    with pytest.raises(KeyboardInterrupt): run_main(**opts)
    assert len(read_predictions(plan.root / opts['output'])) == 1
    assert Interrupt.unloads == 1
    opts['adapter_factory'] = adapter
    result = run_main(**opts, resume=True)
    assert result['total_attempts_in_file'] == 10 and result['generation_calls_this_invocation'] == 9


@pytest.mark.parametrize('mutation', ['duplicate', 'prompt', 'raw_parse', 'identity', 'truncated', 'missing_meta'])
def test_corrupt_checkpoints_rejected_before_any_new_generation(project, adapter, mutation):
    plan = freeze_synthetic(project); opts = options(plan, adapter)
    run_main(**opts, max_cells=2)
    path = plan.root / opts['output']; data = path.read_text(encoding='utf-8').splitlines()
    if mutation == 'duplicate': data.append(data[0])
    elif mutation == 'truncated': data.append('{"incomplete":')
    elif mutation == 'missing_meta': path.with_suffix('.meta.json').unlink()
    else:
        r = json.loads(data[0])
        if mutation == 'prompt': r['prompt_text'] += 'changed'
        if mutation == 'raw_parse': r['raw_response'] = 'YES'
        if mutation == 'identity': r['run_id'] = 'another_run'
        data[0] = json.dumps(r)
    path.write_text('\n'.join(data) + '\n', encoding='utf-8'); before = path.read_bytes(); calls = adapter.calls
    with pytest.raises(ValueError): run_main(**opts, resume=True)
    assert adapter.calls == calls and path.read_bytes() == before


def test_changed_runtime_or_input_blocks_resume(project, adapter):
    plan = freeze_synthetic(project); opts = options(plan, adapter)
    run_main(**opts, max_cells=2)
    changed = {**opts, 'platform_name': 'kaggle'}
    with pytest.raises(ValueError, match='metadata differs'): run_main(**changed, resume=True)
    root, path, config = project
    config['generation']['max_new_tokens'] = 9; path.write_text(yaml.safe_dump(config), encoding='utf-8')
    with pytest.raises(ValueError, match='stale'): run_main(**opts, resume=True)


def test_mutated_plan_issues_or_rows_cannot_bypass_real_files(project, adapter):
    root, path, _ = project; plan = build_plan(root, path)
    plan.issues.clear(); plan.rows[0].qa_status = plan.rows[0].translation_status = 'approved'
    with pytest.raises(ValueError, match='blocked'): run_main(**options(plan, adapter))


def test_image_change_is_blocked_before_model_load(project, adapter):
    plan = freeze_synthetic(project)
    (plan.root / plan.rows[0].image_path).write_bytes(b'synthetic corrupt image')
    with pytest.raises(ValueError, match='blocked'): run_main(**options(plan, adapter))
    assert adapter.loads == 0


def test_load_failure_redacts_token_and_creates_no_prediction(project, adapter):
    class BadLoad(adapter):
        def load_model(self): raise RuntimeError('hf_SYNTHETICSECRET https://example.invalid/private')
    plan = freeze_synthetic(project); opts = options(plan, BadLoad)
    with pytest.raises(RuntimeError, match='load failed'): run_main(**opts)
    path = plan.root / opts['output']
    assert not path.exists()
    report = path.with_suffix('.load_error.json').read_text()
    assert 'hf_SYNTHETICSECRET' not in report and 'https://' not in report


def test_actual_adapter_routing_uses_existing_qwen_fp16_gemma_bf16(project):
    root, path, _ = project; plan = build_plan(root, path)
    for alias, expected in [('qwen', 'nf4_fp16'), ('gemma', 'nf4_bf16')]:
        routed = MainAdapter(plan, alias, offline=True)
        assert routed.adapter.config.precision == expected
        assert routed.adapter.spec['model_id'] == MODEL_IDS[alias]
        assert routed.adapter.config.max_new_tokens == 8


def test_hub_flags_restore_and_path_guards(project, monkeypatch):
    monkeypatch.setenv('HF_HUB_OFFLINE', 'previous')
    with hub_mode(True):
        import os
        assert os.environ['HF_HUB_OFFLINE'] == '1'
    assert os.environ['HF_HUB_OFFLINE'] == 'previous'
    root, path, _ = project
    with pytest.raises(ValueError): inside(root, '../escape')
    plan = build_plan(root, path)
    with pytest.raises(ValueError, match='results/main'):
        run_main(plan, alias='qwen', run_id='synthetic', platform_name='local', output='reports/bad.jsonl')


def test_cli_plan_dry_run_preserves_outputs_and_never_imports_torch(project):
    root, path, _ = project
    script = REPO / 'scripts/run_main.py'
    cmd = [sys.executable, str(script), 'plan', '--config', str(path), '--report', 'report.json',
           '--grid-output', 'results/grid.jsonl']
    first = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    report = json.loads(first.stdout)
    assert report['expected_inferences'] == 20 and not report['execution_ready']
    assert len((root / 'results/grid.jsonl').read_text(encoding='utf-8').splitlines()) == 20
    before = (root / 'report.json').read_bytes()
    assert subprocess.run(cmd, cwd=root, capture_output=True).returncode != 0
    assert (root / 'report.json').read_bytes() == before
    run = subprocess.run([sys.executable, str(script), 'run', '--config', str(path), '--execute'],
                         cwd=root, capture_output=True, text=True)
    assert run.returncode != 0 and 'blocked' in run.stderr
    probe = 'import sys; from pathlib import Path; from vlmbench.baseline_contract import build_plan; build_plan(Path.cwd(),Path("run.yaml")); assert "torch" not in sys.modules and "transformers" not in sys.modules'
    assert subprocess.run([sys.executable, '-c', probe], cwd=root, capture_output=True).returncode == 0
