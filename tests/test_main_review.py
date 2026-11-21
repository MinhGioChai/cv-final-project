import json

import pytest

from vlmbench.io_utils import read_manifest,write_json,write_manifest
from vlmbench.main_review import MainDecision,context,export_batches,import_review,observed_truth


@pytest.fixture
def project(row_factory,tmp_path):
    rows=[row_factory(is_pilot=False,question_vi='synthetic_test_only',translation_status='requires_review')]
    manifest=tmp_path/'source.csv';write_manifest(manifest,rows)
    review=tmp_path/'review.json'
    pending={'context':context(rows,manifest),'decisions':[MainDecision(sample_id=r.sample_id,question_vi=r.question_vi).model_dump() for r in rows]}
    write_json(review,pending)
    return rows,dict(manifest_path=manifest,root=tmp_path,review_path=review,operator='synthetic_test_only')


def edit(options,callback):
    path=options['review_path'];payload=json.loads(path.read_text(encoding='utf-8'));callback(payload);write_json(path,payload)


def approve(payload,part,reviewer='synthetic_test_only_r1',**extra):
    payload['decisions'][0][part].update(status='approved',reviewer_id=reviewer,
        reviewed_at='2026-11-20T10:00:00+07:00',reviewed_question_vi=payload['decisions'][0]['question_vi'],**extra)


def test_pending_creates_no_approval(project):
    rows,options=project;result,audit=import_review(rows,**options)
    assert result[0].translation_status=='requires_review' and result[0].qa_status=='pending'


def test_two_translation_reviewers_and_qa_keep_source_fields(project):
    rows,options=project
    def decisions(p):
        approve(p,'translation_1');approve(p,'translation_2','synthetic_test_only_r2')
        approve(p,'image_qa',observed_answer='yes')
    edit(options,decisions);result,audit=import_review(rows,**options)
    assert result[0].translation_status==result[0].qa_status=='approved'
    for key in type(rows[0]).model_fields:
        if key not in {'metadata','qa_status','translation_status'}:assert getattr(result[0],key)==getattr(rows[0],key)


def test_one_language_reviewer_cannot_finish_translation(project):
    rows,options=project;edit(options,lambda p:approve(p,'translation_1'))
    result,_=import_review(rows,**options)
    assert result[0].translation_status=='requires_review'


def test_same_reviewer_twice_rejected(project):
    rows,options=project
    def decisions(p):approve(p,'translation_1');approve(p,'translation_2')
    edit(options,decisions)
    with pytest.raises(ValueError,match='different'):import_review(rows,**options)


def test_stale_translation_approval_rejected(project):
    rows,options=project
    def decisions(p):approve(p,'translation_1');p['decisions'][0]['question_vi']='synthetic_test_only_changed'
    edit(options,decisions)
    with pytest.raises(ValueError,match='another VI'):import_review(rows,**options)


def test_qa_mismatch_rejected(project):
    rows,options=project;edit(options,lambda p:approve(p,'image_qa',observed_answer='no'))
    with pytest.raises(ValueError,match='truth'):import_review(rows,**options)


@pytest.mark.parametrize('mutation',['ids','source','extra','time','uncertain'])
def test_invalid_input_never_changes_manifest(project,mutation):
    rows,options=project;before=options['manifest_path'].read_bytes()
    def change(p):
        if mutation=='ids':p['decisions']=[]
        if mutation=='source':p['context']['manifest_sha256']='changed'
        if mutation=='extra':p['decisions'][0]['ground_truth']='no'
        if mutation=='time':approve(p,'translation_1');p['decisions'][0]['translation_1']['reviewed_at']='2026-11-20T10:00:00'
        if mutation=='uncertain':p['decisions'][0]['image_qa']['observed_answer']='uncertain'
    edit(options,change)
    with pytest.raises(ValueError):import_review(rows,**options)
    assert options['manifest_path'].read_bytes()==before


def test_count_and_pet_observations(row_factory):
    assert observed_truth(row_factory(task='counting',ground_truth=0),'0')==0
    assert observed_truth(row_factory(task='fine_grained',ground_truth='A'),'H')=='H'
    with pytest.raises(ValueError):observed_truth(row_factory(task='counting',ground_truth=0),'1.0')
    with pytest.raises(ValueError):observed_truth(row_factory(task='fine_grained',ground_truth='A'),'dog')


def test_export_batches_context_and_preserve_edited_review(project):
    rows,options=project;root=options['root'];out=root/'packets';html=root/'html'
    report=export_batches(root,manifests=[options['manifest_path']],output=out,report_dir=html)
    batch=out/'repope_01.csv';review=out/'repope_01.json'
    data=json.loads(review.read_text());assert data['context']==context(read_manifest(batch),batch)
    rendered=(html/'repope_01.html').read_text(encoding='utf-8')
    assert 'data:image/png;base64,' in rendered and 'synthetic_test_only' in rendered
    assert 'repope_01.html' in (html/'index.html').read_text(encoding='utf-8')
    data['decisions'][0]['question_vi']='synthetic_test_only_edited';write_json(review,data)
    before=review.read_bytes()
    with pytest.raises(ValueError,match='differs'):export_batches(root,manifests=[options['manifest_path']],output=out,report_dir=html)
    assert review.read_bytes()==before
