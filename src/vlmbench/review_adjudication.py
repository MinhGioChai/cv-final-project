"""A separate human adjudication form; never overwrites v2 decisions, source labels or gates."""
import base64
from collections import Counter
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from .baseline_contract import inside
from .io_utils import atomic_bytes, read_manifest, sha256_file
from .qa import preflight_image
from .reviews import canonical_hash
from .translate import require_review_identity

TEMPLATE=Path(__file__).with_name('review_adjudication_template.html')
SCHEMA='main_adjudication_v1'
POLICY='human_resolution_translation_and_label_v1'


class Resolution(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    question_vi: str
    resolved_ground_truth: str | StrictInt | None = None
    status: Literal['pending','resolved','needs_discussion'] = 'pending'
    adjudicator_id: str = ''
    recorded_at: str = ''
    translation_checked: bool = False
    image_label_checked: bool = False
    notes: str = ''


class CaseResolution(Resolution):
    sample_id: str
    history: list[Resolution] = Field(default_factory=list)


def source_context(root, *, cases_path, summary_path, manifest_path):
    root=root.resolve()
    paths=[inside(root,p) for p in (cases_path,summary_path,manifest_path)]
    cases=json.loads(paths[0].read_text(encoding='utf-8'))['cases']
    summary=json.loads(paths[1].read_text(encoding='utf-8'))
    rows={r.sample_id:r for r in read_manifest(paths[2])}
    ids=[c['sample_id'] for c in cases]
    if not ids or len(set(ids))!=len(ids) or set(ids)!={r.sample_id for r in rows.values()
            if r.qa_status!='approved' or r.translation_status!='approved'}:
        raise ValueError('Adjudication must bind exactly the unresolved manifest IDs')
    if summary['needs_resolution']!=len(ids):raise ValueError('Unresolved summary differs')
    sources={p.relative_to(root).as_posix():sha256_file(p) for p in paths}
    for name,digest in summary['inputs_sha256'].items():
        if sha256_file(inside(root,name))!=digest:raise ValueError('Review source changed; export a new version')
        sources[name]=digest
    cards=[]
    for case in cases:
        row=rows[case['sample_id']]
        if (row.ground_truth!=case['source_ground_truth'] or row.question_en!=case['question_en']
                or row.question_vi!=case['question_vi_final'] or row.image_sha256!=case['image_sha256']
                or row.image_path!=case['image_path']):raise ValueError('Case differs from source manifest')
        info=preflight_image(inside(root,row.image_path))
        if info['sha256']!=row.image_sha256 or info['format']!='JPEG':raise ValueError('Source image differs')
        cards.append({**case,'task':row.task,'original_size_wh':[info['width'],info['height']]})
    context={'schema_version':SCHEMA,'policy':POLICY,'source_files_sha256':sources,
        'template_sha256':sha256_file(TEMPLATE),'sample_ids':ids,
        'case_sha256':{c['sample_id']:canonical_hash(c) for c in cards}}
    return context,cards


def _validate_resolution(value,card):
    if not value.question_vi.strip():raise ValueError('Final VI cannot be empty')
    recorded=bool(value.adjudicator_id or value.recorded_at)
    if recorded:
        require_review_identity(value.adjudicator_id,value.recorded_at,field='adjudicator')
    elif (value.status!='pending' or value.resolved_ground_truth is not None or value.notes
            or value.translation_checked or value.image_label_checked or value.question_vi!=card['question_vi_final']):
        raise ValueError('Edited decisions require a real adjudicator ID and timestamp')
    label=value.resolved_ground_truth
    if label is not None:
        if card['task'] in {'object_existence','spatial'}:
            if type(label) is not str or label not in {'yes','no'}:raise ValueError('Binary label must be yes/no')
        elif card['task']=='counting':
            if type(label) is not int or not 0<=label<=999999999:raise ValueError('Count must be a nonnegative integer, at most 9 digits')
        elif card['task']=='fine_grained':
            if type(label) is not str or label not in tuple('ABCDEFGH'):raise ValueError('Pet label must be A-H')
        else:raise ValueError('Unknown task')
    if value.status=='needs_discussion' and not value.notes.strip():raise ValueError('Discussion requires notes')
    if value.status=='resolved':
        if label is None or not value.translation_checked or not value.image_label_checked:
            raise ValueError('Resolved requires final label and explicit translation/image checks')
        if label!=card['source_ground_truth'] and not value.notes.strip():raise ValueError('Changing a source label requires a reason')


def validate_payload(payload,context,cards,*,require_complete=False):
    if not isinstance(payload,dict) or set(payload)!= {'context','decisions'} or payload['context']!=context or not isinstance(payload['decisions'],list):
        raise ValueError('Adjudication context differs; use the matching form')
    decisions=[CaseResolution.model_validate(d) for d in payload['decisions']]
    if len(decisions)!=len(cards) or len({d.sample_id for d in decisions})!=len(cards) or {d.sample_id for d in decisions}!=set(context['sample_ids']):
        raise ValueError('Adjudication IDs incomplete/duplicate')
    lookup={c['sample_id']:c for c in cards}
    for decision in decisions:
        _validate_resolution(decision,lookup[decision.sample_id])
        for old in decision.history:
            _validate_resolution(old,lookup[decision.sample_id])
            if not old.adjudicator_id:raise ValueError('History must contain actual recorded decisions')
    counts=Counter(d.status for d in decisions)
    if require_complete and counts['resolved']!=len(cards):raise ValueError('Some cases remain unresolved')
    return {'schema_version':SCHEMA,'scope':'validated_human_resolution_not_imported_or_frozen',
        'rows':len(cards),'status':dict(counts),'complete':counts['resolved']==len(cards),
        'translation_changes':[d.sample_id for d in decisions if d.status=='resolved' and d.question_vi!=lookup[d.sample_id]['question_vi_final']],
        'label_changes':[{'sample_id':d.sample_id,'source_ground_truth':lookup[d.sample_id]['source_ground_truth'],
            'resolved_ground_truth':d.resolved_ground_truth,'reason':d.notes} for d in decisions
            if d.status=='resolved' and d.resolved_ground_truth!=lookup[d.sample_id]['source_ground_truth']],
        'human_identity_verification':'recorded attestations, not external identity verification',
        'source_labels_overwritten':False,'main_freeze_created':False,'new_inferences':0}


def export_html(root,*,html_path,cases_path,summary_path,manifest_path):
    context,cards=source_context(root,cases_path=cases_path,summary_path=summary_path,manifest_path=manifest_path)
    target=inside(root,html_path)
    if not target.is_relative_to(root/'exports') or target.exists():raise ValueError('Use a new HTML path under exports')
    pending={'context':context,'decisions':[CaseResolution(sample_id=c['sample_id'],question_vi=c['question_vi_final']).model_dump() for c in cards]}
    validate_payload(pending,context,cards)
    rendered=[]
    for card in cards:
        path=inside(root,card['image_path'])
        if sha256_file(path)!=card['image_sha256']:raise ValueError('Image changed during export')
        rendered.append({**card,'image':'data:image/jpeg;base64,'+base64.b64encode(path.read_bytes()).decode('ascii')})
    payload=json.dumps({'review':pending,'cards':rendered},ensure_ascii=False).replace('<',chr(92)+'u003c')
    template=TEMPLATE.read_text(encoding='utf-8')
    atomic_bytes(target,template.replace('__ADJUDICATION_PAYLOAD__',payload).encode('utf-8'))
    return {'schema_version':SCHEMA,'html':target.relative_to(root).as_posix(),'sha256':sha256_file(target),
        'bytes':target.stat().st_size,'rows':len(cards),'context':context,'initial_status':'all pending',
        'human_decisions_created':0,'source_images_modified':False,'source_labels_overwritten':False,
        'main_dataset_changed':False,'main_frozen':False,'image_policy':'exact original JPEG bytes; CSS display scaling only'}
