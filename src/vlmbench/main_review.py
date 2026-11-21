"""Batched, source-bound main review with independent language and image decisions."""
import base64
from collections import Counter
from html import escape
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .io_utils import atomic_bytes, manifest_bytes, read_manifest, sha256_file
from .label_qa import _check_images
from .qa import preflight_image
from .reviews import canonical_hash, row_hash
from .schemas import ManifestRow
from .translate import require_review_identity


class Decision(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    status: Literal['pending','approved','rejected']='pending'
    reviewer_id: str=''
    reviewed_at: str=''
    notes: str=''
    reviewed_question_vi: str=''
    observed_answer: str=''


class MainDecision(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    sample_id: str
    question_vi: str
    translation_1: Decision=Field(default_factory=Decision)
    translation_2: Decision=Field(default_factory=Decision)
    image_qa: Decision=Field(default_factory=Decision)


def context(rows,manifest_path):
    return {'schema_version':'main_review_v1','manifest_sha256':sha256_file(manifest_path),
        'sample_ids':[r.sample_id for r in rows],
        'row_sha256':{r.sample_id:row_hash(r) for r in rows}}


def observed_truth(row,observed):
    if observed=='uncertain':return None
    if row.task in {'object_existence','spatial'}:
        if observed not in {'yes','no'}:raise ValueError('Binary observation must be yes/no/uncertain')
        return observed
    if row.task=='counting':
        import re
        if not re.fullmatch(r'0|[1-9][0-9]*',observed):raise ValueError('Counting observation must be a nonnegative integer')
        return int(observed)
    if row.task=='fine_grained' and observed in tuple('ABCDEFGH'):return observed
    raise ValueError('Pet observation must be A–H/uncertain')


def import_review(rows,*,manifest_path,root,review_path,operator):
    if not operator.strip():raise ValueError('Import operator required')
    _check_images(rows,root)
    payload=json.loads(review_path.read_text(encoding='utf-8'))
    if set(payload)!={'context','decisions'} or payload['context']!=context(rows,manifest_path):
        raise ValueError('Review context differs')
    decisions=[MainDecision.model_validate(d) for d in payload['decisions']]
    if len(decisions)!=len(rows) or {d.sample_id for d in decisions}!={r.sample_id for r in rows}:
        raise ValueError('Review IDs incomplete/duplicate')
    decisions={d.sample_id:d for d in decisions};result=[];events=[]
    for row in rows:
        d=decisions[row.sample_id]
        if row.is_pilot or row.translation_status=='approved' or row.qa_status=='approved':
            raise ValueError('Use this workflow only for unapproved main draft batches')
        if not d.question_vi.strip():raise ValueError('VI question cannot be empty')
        for name in ['translation_1','translation_2','image_qa']:
            part=getattr(d,name)
            if part.status!='pending':
                require_review_identity(part.reviewer_id,part.reviewed_at,field=name)
                if part.status=='rejected' and not part.notes.strip():raise ValueError('Rejection requires notes')
                if name!='image_qa' and part.reviewed_question_vi!=d.question_vi:
                    raise ValueError('Language decision belongs to another VI text; review again')
        qa=d.image_qa
        if qa.status!='pending' or qa.observed_answer:
            observed=observed_truth(row,qa.observed_answer)
            if qa.observed_answer=='uncertain' and not qa.notes.strip():raise ValueError('Uncertain observation requires notes')
            if qa.status=='approved' and observed!=row.ground_truth:raise ValueError('Approved observation differs from source truth')
        first,second=d.translation_1,d.translation_2
        approved=first.status==second.status=='approved'
        if approved and first.reviewer_id.strip().casefold()==second.reviewer_id.strip().casefold():
            raise ValueError('Two different translation reviewers required')
        language='approved' if approved else 'rejected' if 'rejected' in {first.status,second.status} else 'requires_review'
        data=row.model_dump();data.update(question_vi=d.question_vi,translation_status=language,qa_status=qa.status)
        data['metadata']['main_review']={'schema_version':'main_review_v1','operator':operator,
            'review_sha256':sha256_file(review_path),'decision':d.model_dump()}
        result.append(ManifestRow.model_validate(data))
        events.append({'sample_id':row.sample_id,'before':row_hash(row),'after':row_hash(result[-1]),'decision':d.model_dump()})
    return result,{'scope':'imported_human_attestations_not_identity_verification','operator':operator,
        'manifest_sha256':sha256_file(manifest_path),'review_sha256':sha256_file(review_path),'events':events,
        'qa_status':dict(Counter(r.qa_status for r in result)),
        'translation_status':dict(Counter(r.translation_status for r in result))}


def export_batches(root,*,manifests,output,report_dir,batch_size=50):
    if not 1<=batch_size<=50:raise ValueError('Batch size must be 1..50')
    template=Path(__file__).with_name('main_review_template.html').read_text(encoding='utf-8')
    outputs={};packets=[]
    for manifest_path in manifests:
        rows=read_manifest(manifest_path)
        if not rows or len({r.sample_id for r in rows})!=len(rows):raise ValueError('Empty/duplicate main rows')
        if any(r.is_pilot or r.translation_status=='approved' or r.qa_status=='approved' for r in rows):
            raise ValueError('Only unapproved main drafts can be exported')
        _check_images(rows,root)
        dataset=rows[0].source_dataset
        if any(r.source_dataset!=dataset for r in rows):raise ValueError('One task per manifest')
        for i,start in enumerate(range(0,len(rows),batch_size),1):
            batch=rows[start:start+batch_size];key=f'{dataset}_{i:02d}'
            path=output/f'{key}.csv';outputs[path]=manifest_bytes(batch)
            # Context hash must match the exact batch CSV before it is published.
            ctx={'schema_version':'main_review_v1',
                 'sample_ids':[r.sample_id for r in batch],'row_sha256':{r.sample_id:row_hash(r) for r in batch}}
            import hashlib
            ctx['manifest_sha256']=hashlib.sha256(outputs[path]).hexdigest()
            pending={'context':ctx,'decisions':[MainDecision(sample_id=r.sample_id,question_vi=r.question_vi).model_dump() for r in batch]}
            review_path=output/f'{key}.json'
            outputs[review_path]=(json.dumps(pending,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
            cards=[]
            for r in batch:
                image=root/r.image_path
                mime={'JPEG':'image/jpeg','PNG':'image/png','WEBP':'image/webp'}[preflight_image(image)['format']]
                cards.append({'sample_id':r.sample_id,'image_id':r.image_id,'task':r.task,'question_en':r.question_en,
                    'question_vi':r.question_vi,'ground_truth':r.ground_truth,
                    'labels':r.metadata.get('candidate_labels',{}),
                    'review_note':r.metadata.get('translation_draft',{}).get('review_note',''),
                    'image':'data:'+mime+';base64,'+base64.b64encode(image.read_bytes()).decode()})
            html=report_dir/f'{key}.html'
            payload=json.dumps({'review':pending,'cards':cards,'packet':key},ensure_ascii=False).replace('<','\\u003c')
            outputs[html]=template.replace('__MAIN_REVIEW_PAYLOAD__',payload).encode('utf-8')
            packets.append({'packet':key,'rows':len(batch),'manifest':path.relative_to(root).as_posix(),
                'pending_review':review_path.relative_to(root).as_posix(),'html':html.relative_to(root).as_posix()})
    links=''.join(f'<tr><td>{escape(p["packet"])}</td><td>{p["rows"]}</td>'
        f'<td><a href="{escape(Path(p["html"]).name)}">Mở review</a></td></tr>' for p in packets)
    index=('''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Review main EN–VI — mục lục</title><style>body{font:17px system-ui;max-width:950px;margin:auto;padding:24px;color:#17243c}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:10px;border-bottom:1px solid #ccc}a{color:#1957a3}p{line-height:1.6}</style>
<h1>Kiểm duyệt 1.000 mẫu main</h1><p>Mỗi gói tối đa 50 mẫu. Tất cả đang chờ review; các liên kết bên dưới không biểu thị đã duyệt. Pilot 30 mẫu đã được kiểm tra riêng.</p>
<p>Nhập ID của bạn; chọn bản dịch người 1, người 2 hoặc ảnh/nhãn. Hai người khác nhau cần duyệt đúng cùng bản dịch cuối cùng. Lưu từng mẫu, tải JSON trước khi đóng trang và chuyển JSON cho người review tiếp theo. Giữ pending nếu chưa chắc; ghi chú cho rejected/uncertain. Không đổi nhãn nguồn.</p>
<p>Trong QA ảnh/nhãn: RePOPE/VSR nhập yes/no (VSR yes=TRUE, no=FALSE); TallyQA nhập số nguyên không âm; Pet nhập A–H theo danh sách hiển thị. Trang không có đáp án model.</p>
<p>Lưu JSON đã tải vào <code>data/reviews/main_review_v1/</code>, giữ nguyên tên gói. Báo assistant kiểm tra/import sau mỗi đợt. Có thể làm từng gói, không cần hoàn thành tất cả trong một lần.</p>
<table><thead><tr><th>Gói</th><th>Số mẫu</th><th>Trang</th></tr></thead><tbody>'''+links+'</tbody></table></html>')
    outputs[report_dir/'index.html']=index.encode('utf-8')
    for path,content in outputs.items():
        if path.exists() and path.read_bytes()!=content:raise ValueError('Output already differs; preserve and use a new version')
    for path,content in outputs.items():
        if not path.exists():atomic_bytes(path,content)
    return {'scope':'unreviewed_main_packets','rows':sum(p['rows'] for p in packets),'packets':packets,
            'translation_reviewers_required':2,'new_human_approvals':0,'model_outputs_in_packets':False}
