"""Synthetic reviewers/data only. Real submitted human decisions are never changed by tests."""
import copy
import json
from pathlib import Path

from PIL import Image
import pytest
import yaml

from vlmbench import review_aggregation as agg
from vlmbench.io_utils import read_manifest, write_manifest, write_json
from vlmbench.main_review_v2 import MainDecision, ArchivedRound, context

REPO=Path(__file__).resolve().parents[1]


def approve(decision, slot, row, status='approved', observation=None):
    review=getattr(decision,slot)
    for part in ('translation','image_qa'):
        value=getattr(review,part)
        value.status=status;value.reviewer_id='synthetic_test_only_'+slot
        value.reviewed_at='2026-11-26T08:00:00Z';value.reviewed_question_vi=decision.question_vi
        value.notes='synthetic rejection' if status=='rejected' else ''
        if part=='image_qa': value.observed_answer=str(row.ground_truth) if observation is None else observation


def test_current_approval_and_final_translation_are_preserved(row_factory):
    row=row_factory(question_vi='original',translation_status='requires_review')
    d=MainDecision(sample_id=row.sample_id,question_vi='edited final')
    for slot in agg.SLOTS:approve(d,slot,row)
    assert agg.classify(row,d)==(True,None,['translation_changed'])


def test_suggestion_in_history_is_not_approval_on_final_vi(row_factory):
    row=row_factory(question_vi='original',translation_status='requires_review')
    old=MainDecision(sample_id=row.sample_id,question_vi='original')
    approve(old,'reviewer_a',row,status='rejected')
    old.reviewer_a.translation.notes='suggested final'
    d=MainDecision(sample_id=row.sample_id,question_vi='suggested final',history=[ArchivedRound(
        reviewer_slot='reviewer_a',question_vi='original',review=old.reviewer_a,
        archived_at='2026-11-26T08:00:00Z',reason='translation_changed')])
    approve(d,'reviewer_b',row)
    snapshot=d.model_dump()
    accepted,primary,flags=agg.classify(row,d)
    assert not accepted and primary=='rereview_after_translation_change'
    assert d.model_dump()==snapshot and d.reviewer_a.translation.status=='pending'


@pytest.mark.parametrize('kind',['both_source_dispute','different_observations','same_observation_pending','translation_rejected'])
def test_disagreements_are_described_without_adjudication(row_factory,kind):
    row=row_factory(question_vi='original',ground_truth='yes',translation_status='requires_review')
    d=MainDecision(sample_id=row.sample_id,question_vi=row.question_vi)
    for slot in agg.SLOTS:approve(d,slot,row)
    if kind=='both_source_dispute':
        for slot in agg.SLOTS:
            qa=getattr(d,slot).image_qa;qa.status='rejected';qa.notes='source dispute';qa.observed_answer='no'
        expected='agreed_observation_differs_from_source'
    elif kind=='different_observations':
        d.reviewer_a.image_qa.status='rejected';d.reviewer_a.image_qa.observed_answer='no'
        expected='observation_disagreement'
    elif kind=='same_observation_pending':
        d.reviewer_b.image_qa.status='pending';expected='image_qa_disagreement_or_incomplete'
    else:
        d.reviewer_a.translation.status='rejected';expected='translation_disagreement_or_incomplete'
    before=d.model_dump()
    accepted,primary,_=agg.classify(row,d)
    assert not accepted and primary==expected and d.model_dump()==before and row.ground_truth=='yes'


def test_numeric_notes_do_not_replace_count_observations(row_factory):
    row=row_factory(task='counting',ground_truth=2,question_vi='synthetic count',translation_status='requires_review')
    d=MainDecision(sample_id=row.sample_id,question_vi=row.question_vi)
    for slot,answer in [('reviewer_a','10000'),('reviewer_b','5')]:approve(d,slot,row,'rejected',answer)
    d.reviewer_b.image_qa.notes='4'
    accepted,primary,flags=agg.classify(row,d)
    assert not accepted and primary=='observation_disagreement'
    assert 'numeric_note_differs_from_observation' in flags and d.reviewer_b.image_qa.observed_answer=='5'


@pytest.fixture
def submitted(tmp_path,row_factory,monkeypatch):
    root=tmp_path
    config=yaml.safe_load((REPO/'configs/baseline_v3_option_b_v1.yaml').read_text(encoding='utf-8'))
    config.update(manifests=['original.csv'],targets={'repope':2,'vsr':1,'tallyqa':1,'oxford_pet':1})
    config_path=root/'config.yaml';config_path.write_text(yaml.safe_dump(config),encoding='utf-8')
    rows=[]
    for i,(dataset,task,truth) in enumerate([('repope','object_existence','yes'),('repope','object_existence','no'),
            ('vsr','spatial','yes'),('tallyqa','counting',2),('oxford_pet','fine_grained','A')]):
        path=root/f'img{i}.png';Image.new('RGB',(12+i,10),color=(30*i,40,50)).save(path)
        from vlmbench.io_utils import sha256_file
        rows.append(row_factory(sample_id=f'synthetic_test_only_{i}',source_dataset=dataset,task=task,
            ground_truth=truth,is_pilot=False,image_path=path.name,image_sha256=sha256_file(path),image_id=str(i),
            translation_status='requires_review',question_vi='synthetic original'))
    write_manifest(root/'original.csv',rows)
    pet=rows[-1].model_copy(deep=True);pet.qa_status=pet.translation_status='approved'
    write_manifest(root/'pet.csv',[pet])
    # Existing Pet checker has separate real/synthetic tests; stub only this fixture's synthetic source.
    monkeypatch.setattr(agg,'validate_pet',lambda root,rs:({pet.sample_id},[]))
    packets=root/'packets';packets.mkdir();inputs=root/'submitted';inputs.mkdir()
    for dataset in ['repope','vsr','tallyqa']:
        group=[r for r in rows if r.source_dataset==dataset];path=packets/f'{dataset}_01.csv';write_manifest(path,group)
        decisions=[]
        for row in group:
            d=MainDecision(sample_id=row.sample_id,question_vi=row.question_vi)
            for slot in agg.SLOTS:approve(d,slot,row)
            if row.sample_id==rows[1].sample_id:d.reviewer_b.image_qa.status='pending'
            decisions.append(d.model_dump())
        write_json(inputs/f'{dataset}.json',{'context':context(group,path),'decisions':decisions})
    args=dict(config_path='config.yaml',input_dir='submitted',packet_dir='packets',pet_manifest='pet.csv',operator='synthetic_test_only_importer')
    return root,args


def test_strict_import_retains_all_ids_pending_and_pet(submitted):
    root,args=submitted
    originals={r.sample_id:r for r in read_manifest(root/'original.csv')}
    rows,summary,cases=agg.aggregate(root,**args)
    assert summary['rows']==5 and summary['accepted_total']==4 and summary['accepted_nonpet']==3
    assert summary['needs_resolution']==len(cases)==1 and summary['archived_approvals_restored']==0
    assert {r.sample_id for r in rows}==set(originals)
    assert all(r.ground_truth==originals[r.sample_id].ground_truth for r in rows)
    assert not summary['frozen'] and summary['new_model_inferences']==0
    agg.publish(root,rows,summary,cases,output_dir='data/main/new',report_dir='reports/new')
    assert read_manifest(root/'data/main/new/main_reviewed.csv')==rows
    before=(root/'data/main/new/main_reviewed.csv').read_bytes()
    with pytest.raises(ValueError,match='Preserve previous'):agg.publish(root,rows,summary,cases,output_dir='data/main/new',report_dir='reports/new')
    assert (root/'data/main/new/main_reviewed.csv').read_bytes()==before


def test_missing_packet_preserves_expected_rows_as_pending(submitted):
    root,args=submitted;(root/'submitted/vsr.json').unlink()
    rows,summary,cases=agg.aggregate(root,**args)
    assert len(rows)==5 and summary['missing_packets']==['vsr_01']
    assert any(c['primary_issue']=='missing_review_packet' for c in cases)


def test_input_changed_after_validation_is_not_published(submitted):
    root,args=submitted
    rows,summary,cases=agg.aggregate(root,**args)
    path=root/'submitted/repope.json'
    path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='Input changed before publication'):
        agg.publish(root,rows,summary,cases,output_dir='data/main/new',report_dir='reports/new')
    assert not (root/'data/main/new/main_reviewed.csv').exists()


@pytest.mark.parametrize('mutation',['duplicate_submission','wrong_context','same_identity','stale_final_vi','wrong_approved_observation','changed_packet','frozen_config'])
def test_incompatible_or_invalid_inputs_abort_before_publishing(submitted,mutation):
    root,args=submitted;path=root/'submitted/repope.json';payload=json.loads(path.read_text())
    if mutation=='duplicate_submission':write_json(root/'submitted/duplicate.json',payload)
    elif mutation=='wrong_context':payload['context']['manifest_sha256']='0'*64;write_json(path,payload)
    elif mutation=='same_identity':
        for part in ['translation','image_qa']:
            payload['decisions'][0]['reviewer_b'][part]['reviewer_id']=payload['decisions'][0]['reviewer_a'][part]['reviewer_id']
        write_json(path,payload)
    elif mutation=='stale_final_vi':payload['decisions'][0]['question_vi']='changed final';write_json(path,payload)
    elif mutation=='wrong_approved_observation':payload['decisions'][0]['reviewer_a']['image_qa']['observed_answer']='no';write_json(path,payload)
    elif mutation=='changed_packet':
        rs=read_manifest(root/'packets/repope_01.csv');rs[0].question_en='changed source';write_manifest(root/'packets/repope_01.csv',rs)
    else:
        cfg=yaml.safe_load((root/'config.yaml').read_text());cfg['frozen']=True;(root/'config.yaml').write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError):agg.aggregate(root,**args)
    assert not (root/'data/main/new').exists()
