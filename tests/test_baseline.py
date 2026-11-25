"""CPU synthetic tests; fake reviewers/models here never approve project data."""
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image
import pytest
import yaml

from vlmbench.baseline_contract import (BaselineConfig, MODEL_IDS, PET_LABELS, PromptSet,
                                       Preprocess, build_plan, inside, smoke_selection)
from vlmbench.baseline_runtime import MainAdapter, Prediction, hub_mode, run_main, prepare_main_image
from vlmbench.datasets.candidates import Candidate
from vlmbench.evaluate import evaluate_run, read_predictions, seal_report
from vlmbench.io_utils import read_manifest, sha256_file, write_json, write_manifest
from vlmbench.main_review_v2 import MainDecision, POLICY
from vlmbench.reviews import canonical_hash
from vlmbench.statistics import statistics_for_evaluation

REPO = Path(__file__).resolve().parents[1]


def fake_environment():
    return {'python': 'synthetic_test_only', 'os': 'test', 'packages': {}, 'gpus': []}


def test_pet_source_policy_cannot_be_used_to_approve_other_tasks(project):
    from vlmbench.pet_review import POLICY as PET_POLICY, SCHEMA as PET_SCHEMA
    root, path, _ = project
    rows = read_manifest(root/'main.csv')
    rows[0].qa_status = rows[0].translation_status = 'approved'
    rows[0].metadata['main_review'] = {'policy':PET_POLICY,'schema_version':PET_SCHEMA,
        'review_path':'missing.json','review_sha256':'0'*64,'original_row_sha256':'0'*64}
    write_manifest(root/'main.csv',rows)
    counts = build_plan(root,path).summary()['blocking_counts']
    assert counts['PET_SOURCE_REVIEW_PROOF_INVALID'] == 1
    assert counts['TWO_REVIEWER_PROOF_REQUIRED'] == 1


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


def option_b_project(project):
    root,path,config=project
    config['preprocess'].update(policy_id='original_rgb_processor_v1',image_max_edge=None)
    path.write_text(yaml.safe_dump(config),encoding='utf-8')
    return root,path,config


@pytest.mark.parametrize('policy,edge,valid',[
    ('rgb_thumbnail_lanczos_v1',512,True),('rgb_thumbnail_lanczos_v1',1024,True),
    ('rgb_thumbnail_lanczos_v1',None,False),('original_rgb_processor_v1',None,True),
    ('original_rgb_processor_v1',512,False),('unknown',None,False)])
def test_preprocessing_policy_has_explicit_resize_semantics(policy,edge,valid):
    if valid:assert Preprocess(policy_id=policy,image_max_edge=edge).image_max_edge==edge
    else:
        with pytest.raises(ValueError):Preprocess(policy_id=policy,image_max_edge=edge)


@pytest.mark.parametrize('size,mode',[((1024,768),'RGB'),((1600,160),'RGB'),((31,901),'L'),((19,13),'RGBA'),((1,1),'RGB')])
def test_option_b_preserves_source_dimensions_RGB_and_bytes(tmp_path,monkeypatch,size,mode):
    source=tmp_path/'synthetic_only.png';Image.new(mode,size).save(source)
    before=source.read_bytes()
    def forbidden(*args,**kwargs):raise AssertionError('Option B must not thumbnail')
    monkeypatch.setattr(Image.Image,'thumbnail',forbidden)
    image,original=prepare_main_image(source,Preprocess(policy_id='original_rgb_processor_v1',image_max_edge=None))
    assert image.mode=='RGB' and image.size==size and original==list(size)
    assert source.read_bytes()==before


def test_historical_A_resize_still_supported(tmp_path):
    source=tmp_path/'synthetic_only.png';Image.new('RGB',(1600,1200)).save(source)
    a,original=prepare_main_image(source,Preprocess())
    assert original==[1600,1200] and a.size==(512,384)
    a,_=prepare_main_image(source,Preprocess(image_max_edge=1024))
    assert a.size==(1024,768)


def test_B_main_path_both_models_languages_keep_pixels_and_processor_settings(project,adapter,monkeypatch):
    project=option_b_project(project);root,path,config=project
    rows=read_manifest(root/'main.csv')
    expected={}
    for i,row in enumerate(rows):
        Image.new('RGB',(1000+i,700+i),(i*20,40,80)).save(root/row.image_path)
        row.image_sha256=sha256_file(root/row.image_path)
        expected[row.sample_id]=(1000+i,700+i)
    write_manifest(root/'main.csv',rows)
    frozen=freeze_synthetic(project)
    def forbidden(*args,**kwargs):raise AssertionError('Main B must skip thumbnail')
    monkeypatch.setattr(Image.Image,'thumbnail',forbidden)
    seen=[]
    class Observe(adapter):
        def generate(self,image,prompt):
            seen.append((image.mode,image.size))
            return super().generate(image,prompt)
    for alias in ('qwen','gemma'):
        opts=options(frozen,Observe);opts.update(alias=alias,output=f'results/main/synthetic_test_only/{alias}.jsonl')
        assert run_main(**opts)['valid']==10
        records=read_predictions(root/opts['output'])
        for record in records:
            assert tuple(record['original_image_size_wh'])==expected[record['sample_id']]
            assert record['original_image_size_wh']==record['processor_input_size_wh']
            assert record['image_preprocess']['policy_id']=='original_rgb_processor_v1'
            assert record['image_preprocess']['image_max_edge'] is None
        routed=MainAdapter(frozen,alias,offline=True)
        assert routed.adapter.config.qwen_min_pixels==200704 and routed.adapter.config.qwen_max_pixels==401408
        assert routed.adapter.config.precision==('nf4_fp16' if alias=='qwen' else 'nf4_bf16')
        assert frozen.protocol['processor_policy'][alias]==({'min_pixels':200704,'max_pixels':401408,'use_fast':'checkpoint_default'}
            if alias=='qwen' else {'do_pan_and_scan':False,'use_fast':False})
    assert len(seen)==20 and all(mode=='RGB' and width>512 for mode,(width,height) in seen)


def test_B_changes_protocol_not_data_grid_or_ground_truth(project):
    root,path,config=project;a=build_plan(root,path)
    option_b_project(project);b=build_plan(root,path)
    assert a.protocol_hash!=b.protocol_hash
    assert a.protocol['grid_sha256']==b.protocol['grid_sha256']
    assert [r.model_dump() for r in a.rows]==[r.model_dump() for r in b.rows]
    assert a.config.models==b.config.models and a.config.generation==b.config.generation


def test_B_QA_freeze_and_smoke_gates_still_block_before_runtime(project,adapter):
    root,path,config=option_b_project(project);selected=build_plan(root,path)
    def forbidden():raise AssertionError('No GPU environment before gates')
    with pytest.raises(ValueError,match='blocked'):
        run_main(**{**options(selected,adapter),'environment_provider':forbidden},smoke_per_task=1)
    assert not (root/'results').exists()
    dry=run_main(**{**options(selected,adapter),'execute':False},smoke_per_task=1)
    assert dry['bounded_smoke']['expected_cells_per_model']==8 and dry['expected_inferences']==10


def test_four_task_bounded_smoke_leaves_full_grid_and_cannot_resume_as_full(project,adapter):
    selected=freeze_synthetic(option_b_project(project))
    chosen=smoke_selection(selected,1)
    assert len(chosen['tasks'])==4 and chosen['expected_cells_both_models']==16
    assert len(selected.cells)==20
    for alias in ('qwen','gemma'):
        opts=options(selected,adapter);opts.update(alias=alias,output=f'results/main/synthetic_test_only/{alias}.jsonl')
        result=run_main(**opts,smoke_per_task=1)
        assert result['valid']==8 and result['missing']==2
        assert result['bounded_smoke']['missing_smoke_cells']==0
        records=read_predictions(selected.root/opts['output'])
        assert {r['task'] for r in records}=={'object_existence','spatial','counting','fine_grained'}
        assert {r['language'] for r in records}=={'en','vi'}
        assert run_main(**opts,smoke_per_task=1,resume=True)['generation_calls_this_invocation']==0
        with pytest.raises(ValueError,match='metadata differs'):run_main(**opts,resume=True)
    with pytest.raises(ValueError,match='truncate'):run_main(**options(selected,adapter),smoke_per_task=1,max_cells=1)
    with pytest.raises(ValueError):smoke_selection(selected,0)


def test_A_prediction_without_new_size_fields_remains_readable(project,adapter):
    selected=freeze_synthetic(project);opts=options(selected,adapter)
    run_main(**opts,max_cells=1)
    record=json.loads((selected.root/opts['output']).read_text(encoding='utf-8').splitlines()[0])
    record.pop('original_image_size_wh');record.pop('processor_input_size_wh')
    assert Prediction.model_validate(record).valid


def test_cli_defaults_to_B_candidate_without_execution(tmp_path):
    command=[sys.executable,str(REPO/'scripts/run_main.py'),'plan','--report',str(tmp_path/'outside.json')]
    # A default CPU plan may write only within the repository; inspect stdout with no output argument.
    result=subprocess.run(command[:3],cwd=REPO,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    data=json.loads(result.stdout)
    assert 'configs/baseline_v3_option_b_v1.yaml' in data['inputs_sha256']
    assert data['expected_inferences']==4000 and not data['execution_ready']
