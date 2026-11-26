"""Synthetic editor decisions only; never writes real review/source data."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from PIL import Image
import pytest

from vlmbench.io_utils import read_manifest,sha256_file,write_manifest,write_json
from vlmbench.main_review_v2 import MainDecision
from vlmbench.review_adjudication import CaseResolution,export_html,source_context,validate_payload

REPO=Path(__file__).resolve().parents[1]


@pytest.fixture
def editor(tmp_path,row_factory):
    rows=[];cases=[]
    for i,(task,truth) in enumerate([('object_existence','yes'),('counting',2)]):
        path=tmp_path/f'original{i}.jpg';Image.new('RGB',(17+i,13),color=(80,i*60,30)).save(path)
        row=row_factory(sample_id=f'synthetic_test_only_{i}',task=task,ground_truth=truth,is_pilot=False,
            image_path=path.name,image_sha256=sha256_file(path),image_id=str(i),
            question_en='Synthetic </script><script>bad()</script> question',question_vi='synthetic VI',
            translation_status='requires_review')
        rows.append(row)
        cases.append({'sample_id':row.sample_id,'packet':'synthetic_01','image_path':row.image_path,'image_sha256':row.image_sha256,
            'question_en':row.question_en,'question_vi_original':'synthetic draft','question_vi_final':row.question_vi,
            'source_ground_truth':truth,'primary_issue':'observation_disagreement','action':'synthetic action',
            'decision':MainDecision(sample_id=row.sample_id,question_vi=row.question_vi).model_dump()})
    write_manifest(tmp_path/'main.csv',rows)
    write_json(tmp_path/'cases.json',{'cases':cases})
    write_json(tmp_path/'source.json',{'synthetic_test_only':True})
    write_json(tmp_path/'summary.json',{'needs_resolution':2,'inputs_sha256':{'source.json':sha256_file(tmp_path/'source.json')}})
    args=dict(cases_path='cases.json',summary_path='summary.json',manifest_path='main.csv')
    ctx,cards=source_context(tmp_path,**args)
    pending={'context':ctx,'decisions':[CaseResolution(sample_id=c['sample_id'],question_vi=c['question_vi_final']).model_dump() for c in cards]}
    return tmp_path,args,ctx,cards,pending


def resolve(d,truth):
    d.update(status='resolved',resolved_ground_truth=truth,adjudicator_id='synthetic_test_only_user',
        recorded_at='2026-11-26T10:00:00Z',translation_checked=True,image_label_checked=True)


def test_export_initial_pending_exact_images_no_source_changes_and_safe_json(editor):
    root,args,ctx,cards,pending=editor
    before=(root/'main.csv').read_bytes()
    report=export_html(root,html_path='exports/editor.html',**args)
    html=(root/'exports/editor.html').read_text(encoding='utf-8')
    raw=re.search(r'<script type="application/json" id="payload">([\s\S]*?)</script>',html)[1]
    assert '<script>bad()' not in raw
    payload=json.loads(raw)
    assert payload['review']==pending and report['human_decisions_created']==0
    assert validate_payload(payload['review'],ctx,cards)['status']=={'pending':2}
    for card in payload['cards']:
        data=base64.b64decode(card['image'].split(',',1)[1])
        assert hashlib.sha256(data).hexdigest()==card['image_sha256']
    assert (root/'main.csv').read_bytes()==before
    with pytest.raises(ValueError,match='new HTML path'):export_html(root,html_path='exports/editor.html',**args)


def test_label_corrections_are_recorded_separately_with_rationale(editor):
    root,_,ctx,cards,payload=editor
    before=(root/'main.csv').read_bytes()
    resolve(payload['decisions'][0],'no');payload['decisions'][0]['notes']='synthetic label correction evidence'
    resolve(payload['decisions'][1],0);payload['decisions'][1]['notes']='synthetic counted zero'
    summary=validate_payload(payload,ctx,cards,require_complete=True)
    assert summary['complete'] and len(summary['label_changes'])==2 and not summary['source_labels_overwritten']
    assert summary['label_changes'][1]['resolved_ground_truth']==0
    assert (root/'main.csv').read_bytes()==before and read_manifest(root/'main.csv')[0].ground_truth=='yes'


@pytest.mark.parametrize('kind',['missing_identity','missing_timezone','unchecked_translation','unchecked_image','correction_without_reason',
    'binary_ambiguous','count_negative','count_decimal','count_bool','count_string','duplicate_ids','wrong_context','edited_unsigned',
    'empty_vi','discussion_without_notes','fake_history','added_source_label'])
def test_invalid_decisions_cannot_be_treated_as_resolved(editor,kind):
    _,_,ctx,cards,payload=editor
    for d,card in zip(payload['decisions'],cards):resolve(d,card['source_ground_truth'])
    d=payload['decisions'][0]
    if kind=='missing_identity':d['adjudicator_id']=''
    elif kind=='missing_timezone':d['recorded_at']='2026-11-26T10:00:00'
    elif kind=='unchecked_translation':d['translation_checked']=False
    elif kind=='unchecked_image':d['image_label_checked']=False
    elif kind=='correction_without_reason':d['resolved_ground_truth']='no'
    elif kind=='binary_ambiguous':d['resolved_ground_truth']='yes/no'
    elif kind.startswith('count_'):payload['decisions'][1]['resolved_ground_truth']={'count_negative':-1,'count_decimal':2.5,'count_bool':True,'count_string':'2'}[kind]
    elif kind=='duplicate_ids':payload['decisions'][1]['sample_id']=d['sample_id']
    elif kind=='wrong_context':payload['context']=copy.deepcopy(ctx);payload['context']['policy']='wrong'
    elif kind=='edited_unsigned':
        d.update(status='pending',adjudicator_id='',recorded_at='',question_vi='unsigned edit',resolved_ground_truth=None,
            translation_checked=False,image_label_checked=False)
    elif kind=='empty_vi':d['question_vi']=' '
    elif kind=='discussion_without_notes':d['status']='needs_discussion'
    elif kind=='fake_history':d['history']=[CaseResolution(sample_id=d['sample_id'],question_vi='synthetic VI').model_dump(exclude={'sample_id','history'})]
    elif kind=='added_source_label':d['source_ground_truth']='no'
    with pytest.raises(ValueError):validate_payload(payload,ctx,cards)


def test_partial_save_and_history_are_valid_without_fabricating_completion(editor):
    _,_,ctx,cards,payload=editor
    old=copy.deepcopy(payload['decisions'][0]);resolve(old,'yes')
    d=payload['decisions'][0];resolve(d,'no');d['notes']='synthetic correction'
    d['history']=[{k:v for k,v in old.items() if k not in {'sample_id','history'}}]
    assert validate_payload(payload,ctx,cards)['status']=={'resolved':1,'pending':1}
    with pytest.raises(ValueError,match='remain unresolved'):validate_payload(payload,ctx,cards,require_complete=True)


def test_changed_source_is_rejected_before_export(editor):
    root,args,_,_,_=editor
    (root/'source.json').write_text('{}')
    with pytest.raises(ValueError,match='source changed'):export_html(root,html_path='exports/editor.html',**args)
    assert not (root/'exports/editor.html').exists()


def test_cli_rejects_report_html_path_collision_before_writing(editor):
    root,_,_,_,_=editor
    result=subprocess.run([sys.executable,str(REPO/'scripts/adjudicate_reviews.py'),'export','--cases','cases.json',
        '--summary','summary.json','--manifest','main.csv','--html','exports/collision.html','--report','exports/collision.html'],
        cwd=root,capture_output=True,text=True,encoding='utf-8')
    assert result.returncode!=0 and 'must be distinct' in result.stderr
    assert not (root/'exports/collision.html').exists()


def test_real_ui_handlers_export_restore_history_and_backend_validation(editor):
    if not shutil.which('node'):pytest.skip('Node unavailable for inline handler test')
    root,args,ctx,cards,_=editor
    export_html(root,html_path='exports/editor.html',**args)
    out=root/'synthetic_output.json'
    result=subprocess.run(['node',str(REPO/'tests/review_adjudication_ui.cjs'),str(root/'exports/editor.html'),str(out)],
        capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==0,result.stdout+result.stderr
    payload=json.loads(out.read_text(encoding='utf-8'))
    report=validate_payload(payload,ctx,cards,require_complete=True)
    assert report['complete'] and len(payload['decisions'][0]['history'])>=1
