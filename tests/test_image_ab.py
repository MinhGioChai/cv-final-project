"""Synthetic unit tests only; never GPU evidence or human approval."""
from copy import deepcopy
from collections import Counter
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
import pytest
import yaml

from vlmbench import image_ab
from vlmbench.baseline_contract import PET_LABELS
from vlmbench.io_utils import sha256_file, write_manifest

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def ab_project(tmp_path,row_factory):
    cfg=yaml.safe_load((ROOT/'configs/baseline_v3_draft.yaml').read_text(encoding='utf-8'))
    cfg.update(manifests=['main.csv'],pilot_manifest='trusted.csv',prompts='prompts.yaml')
    (tmp_path/'configs').mkdir()
    (tmp_path/'configs/baseline_v3_draft.yaml').write_text(yaml.safe_dump(cfg),encoding='utf-8')
    (tmp_path/'prompts.yaml').write_bytes((ROOT/'configs/prompts_baseline_v1.yaml').read_bytes())
    rows=[]
    for i in range(30):
        path=tmp_path/f'pilot_{i}.png';Image.new('RGB',(12,8),(i,30,60)).save(path)
        row=row_factory(sample_id=f'synthetic_test_only_{i:02}',image_id=str(i),image_path=path.name,
            image_sha256=sha256_file(path),question_vi='synthetic test only',qa_status='approved',translation_status='approved')
        rows.append(row)
    write_manifest(tmp_path/'trusted.csv',rows);write_manifest(tmp_path/'pilot.csv',rows)
    main=row_factory(sample_id='synthetic_main',image_id='outside',is_pilot=False,question_vi='synthetic',translation_status='requires_review')
    write_manifest(tmp_path/'main.csv',[main])
    return tmp_path,rows


def test_missing_tasks_blocks_before_environment_or_model_load(ab_project,monkeypatch):
    root,rows=ab_project;selected=image_ab.plan(root,'pilot.csv')
    assert selected.summary['expected_cells']==240
    assert {i['task'] for i in selected.summary['issues'] if i['code']=='TASK_COVERAGE_MISSING'}=={'spatial','counting','fine_grained'}
    def forbidden():raise AssertionError('Environment/model must not be touched')
    monkeypatch.setattr(image_ab,'inspect_environment',forbidden)
    with pytest.raises(ValueError,match='four-task'):image_ab.execute(selected,'qwen','results/pilot/image_ab_v1/test',execute=True)
    assert not (root/'results').exists()


@pytest.mark.parametrize('change', ['qa','translation','untrusted','nonpilot','duplicate','main_overlap','changed_image'])
def test_pilot_integrity_gates(ab_project,change):
    root,rows=ab_project
    if change=='qa':rows[0].qa_status='pending'
    if change=='translation':rows[0].translation_status='requires_review'
    if change=='untrusted':rows[0].question_vi='unapproved change'
    if change=='nonpilot':rows[0].is_pilot=False
    if change=='duplicate':rows[1].image_sha256=rows[0].image_sha256
    if change=='main_overlap':write_manifest(root/'main.csv',[rows[0].model_copy(update={'is_pilot':False})])
    if change=='changed_image':(root/rows[0].image_path).write_bytes((root/rows[1].image_path).read_bytes())
    write_manifest(root/'pilot.csv',rows)
    issues=image_ab.plan(root,'pilot.csv').summary['issues']
    assert any(i['code']!='TASK_COVERAGE_MISSING' for i in issues)


def four_task_plan(ab_project):
    root,rows=ab_project
    settings=[('vsr','spatial','no'),('tallyqa','counting',2),('oxford_pet','fine_grained','A')]
    for row,(dataset,task,truth) in zip(rows,settings):
        row.source_dataset=dataset;row.task=task;row.ground_truth=truth
        if task=='fine_grained':row.metadata['candidate_labels']=PET_LABELS
    write_manifest(root/'trusted.csv',rows);write_manifest(root/'pilot.csv',rows)
    return image_ab.plan(root,'pilot.csv')


def test_four_task_plan_requires_real_QA_and_excludes_main(ab_project):
    selected=four_task_plan(ab_project)
    assert selected.summary['execution_ready'] and selected.summary['expected_cells']==240
    assert selected.config.frozen is False
    with pytest.raises(ValueError,match='Explicit'):image_ab.execute(selected,'qwen','results/main/wrong')
    with pytest.raises(ValueError,match='NEW'):image_ab.execute(selected,'qwen','results/main/wrong',execute=True)


def test_synthetic_orchestration_one_load_balanced_cells_and_separate_warmup(ab_project,monkeypatch):
    selected=four_task_plan(ab_project);root,_=ab_project
    cuda=SimpleNamespace(synchronize=lambda _:None,reset_peak_memory_stats=lambda _:None,
        memory_allocated=lambda _:1024**2,memory_reserved=lambda _:2*1024**2,
        max_memory_allocated=lambda _:3*1024**2,max_memory_reserved=lambda _:4*1024**2)
    fake_torch=SimpleNamespace(cuda=cuda)
    monkeypatch.setitem(sys.modules,'torch',fake_torch)
    monkeypatch.setattr(image_ab,'gpu_preflight',lambda *args:{'scope':'synthetic_test_only'})
    monkeypatch.setattr(image_ab,'inspect_environment',lambda:{'scope':'synthetic_test_only'})
    counts=Counter()
    class Processor:
        def to_dict(self):return {'scope':'synthetic_test_only'}
        def __call__(self,**kwargs):return {'pixel_values':SimpleNamespace(shape=(1,3,896,896)),
            'input_ids':SimpleNamespace(shape=(1,10))}
    class Adapter:
        def __init__(self,*args,**kwargs):self.adapter=SimpleNamespace(torch=fake_torch,processor=Processor())
        def load_model(self):counts['load']+=1
        def unload_model(self):counts['unload']+=1
        def generate(self,image,prompt):
            counts['calls']+=1
            self.adapter.processor(images=[image],text=[prompt])
            return {'raw_response':'NO','elapsed_ms':1.}
    monkeypatch.setattr(image_ab,'MainAdapter',Adapter)
    target='results/pilot/image_ab_v1/synthetic_test_only/qwen'
    result=image_ab.execute(selected,'qwen',target,execute=True)
    assert result['measured_records']==120 and result['warmup_records']==4
    assert counts=={'load':1,'unload':1,'calls':124}
    records=[json.loads(x) for x in (root/target/'predictions.jsonl').read_text(encoding='utf-8').splitlines()]
    assert Counter(r['branch'] for r in records)=={'A':60,'B':60}
    assert len({r['config_fingerprint'] for r in records})==1
    assert all(r['processor_output_shape']==[1,3,896,896] for r in records)
    metadata=json.loads((root/target/'metadata.json').read_text(encoding='utf-8'))
    assert metadata['settings_snapshot']['generation']['max_new_tokens']==8
    assert metadata['prompts_snapshot']['tasks']==selected.prompts.tasks
    warmups=json.loads((root/target/'warmups.json').read_text(encoding='utf-8'))
    assert all(r['config_fingerprint']==records[0]['config_fingerprint'] for r in warmups)
    with pytest.raises(ValueError,match='Preserve'):image_ab.execute(selected,'qwen',target,execute=True)


def test_only_thumbnail_differs_and_original_is_unchanged(tmp_path):
    path=tmp_path/'source.png';Image.new('RGB',(640,480),'red').save(path)
    before=path.read_bytes()
    a,original=image_ab.prepare_image(path,'A');b,_=image_ab.prepare_image(path,'B')
    assert original==[640,480] and a.size==(512,384) and b.size==(640,480)
    assert path.read_bytes()==before
    with pytest.raises(ValueError):image_ab.prepare_image(path,'C')


def test_small_images_are_identical_across_AB(tmp_path):
    path=tmp_path/'small.png';Image.new('RGB',(333,500),'red').save(path)
    a,_=image_ab.prepare_image(path,'A');b,_=image_ab.prepare_image(path,'B')
    assert a.size==b.size and a.tobytes()==b.tobytes()


def test_observer_preserves_processor_result_and_arguments():
    tensor=SimpleNamespace(shape=(1,3,896,896))
    result={'pixel_values':tensor,'input_ids':SimpleNamespace(shape=(1,17))}
    class Processor:
        def __call__(self,*args,**kwargs):
            assert args==('image',) and kwargs=={'return_tensors':'pt'}
            return result
    observer=image_ab.ObservedProcessor(Processor())
    assert observer('image',return_tensors='pt') is result
    assert observer.last['processor_output_shape']==[1,3,896,896]


def test_measurement_success_and_OOM_are_not_confused(ab_project):
    root,rows=ab_project
    cuda=SimpleNamespace(synchronize=lambda _:None,reset_peak_memory_stats=lambda _:None,
        memory_allocated=lambda _:1024**2,memory_reserved=lambda _:2*1024**2,
        max_memory_allocated=lambda _:3*1024**2,max_memory_reserved=lambda _:4*1024**2)
    torch=SimpleNamespace(cuda=cuda)
    processor=SimpleNamespace(last={})
    calls=[]
    def generate(image,prompt):
        calls.append((image.size,prompt));processor.last={'processor_output_shape':[1,3,896,896]}
        return {'raw_response':'NO','elapsed_ms':2.0}
    adapter=SimpleNamespace(adapter=SimpleNamespace(torch=torch,processor=processor),generate=generate)
    result=image_ab.measure(adapter,rows[0],'B',root,prompt='same prompt')
    assert calls==[((12,8),'same prompt')]
    assert result['run_status']=='success' and result['parsed_response']=='no'
    assert result['peak_allocated_mib']==3 and result['incremental_peak_reserved_mib']==2
    def oom(*args):raise RuntimeError('CUDA out of memory')
    adapter.generate=oom
    failed=image_ab.measure(adapter,rows[0],'A',root,prompt='same prompt')
    assert failed['run_status']=='failed' and failed['oom'] and failed['correctness'] is None


def record(row,language,branch,raw='YES',**updates):
    parsed=image_ab.parse_response(raw,row.task)
    return dict(scope='gpu_image_ab_pilot',model='qwen',sample_id=row.sample_id,task=row.task,
        language=language,branch=branch,raw_response=raw,parsed_response=parsed.prediction,
        valid=parsed.status=='valid',run_status='success',correctness=parsed.status=='valid' and parsed.prediction==row.ground_truth,
        config_fingerprint='synthetic_test_only',latency_ms=10.,peak_allocated_mib=100.,peak_reserved_mib=150.,**updates)


def test_metrics_pairing_and_four_way_disagreement_denominator(row_factory):
    row=row_factory(ground_truth='yes')
    selected=SimpleNamespace(rows=[row],summary={'config_fingerprint':'synthetic_test_only'})
    records=[record(row,'en','A'),record(row,'vi','A'),record(row,'en','B'),record(row,'vi','B','NO')]
    metrics=image_ab.summarize(selected,records)
    comparison=next(r for r in metrics['AB_comparisons'] if r['model']=='qwen' and r['language']=='vi' and r['task']==row.task)
    assert comparison['jointly_valid_AB']==1 and comparison['prediction_flips']==1 and comparison['A_correct_B_incorrect']==1
    consistency=next(r for r in metrics['EN_VI_consistency'] if r['model']=='qwen' and r['task']==row.task)
    assert consistency['four_way_valid']==1 and consistency['change_B_minus_A']==1
    records[-1]=record(row,'vi','B','explanation invalid')
    updated=image_ab.summarize(selected,records)
    consistency=next(r for r in updated['EN_VI_consistency'] if r['model']=='qwen' and r['task']==row.task)
    assert consistency['four_way_valid']==0 and consistency['change_B_minus_A'] is None


def test_empty_results_have_no_fabricated_performance(row_factory):
    selected=SimpleNamespace(rows=[row_factory()],summary={'config_fingerprint':'synthetic_test_only'})
    result=image_ab.summarize(selected,[])
    assert result['recorded']==0 and result['missing']==8
    assert all(r['latency_p50_ms'] is None and r['accuracy_all_expected'] is None for r in result['metrics'])
    assert image_ab.percentile([0,100],.95)==95


@pytest.mark.parametrize('tamper',['duplicate','fingerprint','correctness','synthetic_scope'])
def test_analysis_rejects_incompatible_or_tampered_records(row_factory,tamper):
    row=row_factory();selected=SimpleNamespace(rows=[row],summary={'config_fingerprint':'synthetic_test_only'})
    saved=record(row,'en','A');records=[saved]
    if tamper=='duplicate':records.append(deepcopy(saved))
    if tamper=='fingerprint':saved['config_fingerprint']='other'
    if tamper=='correctness':saved['correctness']=not saved['correctness']
    if tamper=='synthetic_scope':saved['scope']='synthetic_test_only'
    with pytest.raises(ValueError):image_ab.summarize(selected,records)
