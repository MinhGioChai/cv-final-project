"""Aggregate source-bound v2 reviews and previously approved Pet without adjudicating labels."""
from collections import Counter
from datetime import datetime, timezone
import json
import re
from pathlib import Path

import yaml

from .baseline_contract import BaselineConfig, inside
from .io_utils import atomic_bytes, manifest_bytes, read_manifest, sha256_file, write_json
from .main_review import Decision, observed_truth
from .main_review_v2 import MainDecision, SLOTS, import_review
from .pet_review import validate_imported as validate_pet
from .reviews import row_hash


ACTIONS = {
    'observation_disagreement': 'A/B đối soát lại ảnh và cùng câu hỏi; giữ nguyên nhãn nguồn trong lúc chờ quyết định.',
    'agreed_observation_differs_from_source': 'Đối soát annotation nguồn và ảnh. Đây là đề nghị sửa nhãn, chưa phải nhãn mới được phê duyệt.',
    'rereview_after_translation_change': 'Reviewer có lượt pending cần mở bản VI cuối và duyệt lại; không suy approval từ góp ý trong history.',
    'translation_disagreement_or_incomplete': 'Xử lý góp ý dịch/mơ hồ câu nguồn; cần hai reviewer thật duyệt cùng bản VI cuối.',
    'image_qa_disagreement_or_incomplete': 'Reviewer có lượt pending/rejected cần kiểm lại và ghi quyết định thật; cùng đáp án chưa thay thế approved.',
}


def classify(row, decision):
    """Describe actual current decisions, never restore an archived approval or change truth."""
    rounds = [getattr(decision, slot) for slot in SLOTS]
    flags = []
    for part in ('translation', 'image_qa'):
        statuses = [getattr(review, part).status for review in rounds]
        if any(s != 'approved' for s in statuses): flags.append(part + '_not_fully_approved')
        if statuses[0] != statuses[1]: flags.append(part + '_status_disagreement')
    observations = [review.image_qa.observed_answer for review in rounds]
    if all(observations) and observations[0] != observations[1]:
        flags.append('observation_disagreement')
    if all(observations) and observations[0] == observations[1] and observations[0] != 'uncertain':
        if observed_truth(row, observations[0]) != row.ground_truth:
            flags.append('agreed_observation_differs_from_source')
    if decision.question_vi != row.question_vi:
        flags.append('translation_changed')
        if any(getattr(decision, s).translation == Decision() and any(
                h.reviewer_slot == s and h.reason == 'translation_changed' for h in decision.history) for s in SLOTS):
            flags.append('rereview_after_translation_change')
    for review in rounds:
        qa = review.image_qa
        if row.task == 'counting' and re.fullmatch(r'[0-9]+', qa.notes.strip()) and qa.notes.strip() != qa.observed_answer:
            flags.append('numeric_note_differs_from_observation')
    accepted = all(getattr(review, part).status == 'approved' for review in rounds for part in ('translation','image_qa'))
    primary = None
    if not accepted:
        for name in ('observation_disagreement','agreed_observation_differs_from_source','rereview_after_translation_change'):
            if name in flags:
                primary = name; break
        if primary is None:
            primary = 'translation_disagreement_or_incomplete' if 'translation_not_fully_approved' in flags else 'image_qa_disagreement_or_incomplete'
    return accepted, primary, sorted(set(flags))


def aggregate(root, *, config_path, input_dir, packet_dir, pet_manifest, operator):
    root = root.resolve()
    if not operator.strip(): raise ValueError('Import operator required')
    paths = [inside(root, p) for p in (config_path,input_dir,packet_dir,pet_manifest)]
    config_path, input_dir, packet_dir, pet_path = paths
    config = BaselineConfig.model_validate(yaml.safe_load(config_path.read_text(encoding='utf-8')))
    if config.frozen or config.freeze_receipt:
        raise ValueError('Aggregate into a new unfrozen version; do not alter a frozen protocol')
    original = [r for path in config.manifests for r in read_manifest(inside(root,path))]
    by_id = {r.sample_id:r for r in original}
    if len(by_id) != len(original) or dict(Counter(r.source_dataset for r in original)) != config.targets:
        raise ValueError('Original main IDs/counts differ from declared targets')
    if any(r.is_pilot or r.qa_status != 'pending' or r.translation_status != 'requires_review' for r in original):
        raise ValueError('Use original pending bilingual draft manifests')
    fingerprints = {p:sha256_file(p) for p in [config_path,pet_path,*[inside(root,p) for p in config.manifests]]}
    packets, packet_ids = {}, set()
    for path in sorted(packet_dir.glob('*.csv')):
        rows = read_manifest(path)
        if rows and all(r.source_dataset == 'oxford_pet' for r in rows): continue
        ids = {r.sample_id for r in rows}
        if not rows or len(ids) != len(rows) or not ids.issubset(by_id) or ids.intersection(packet_ids):
            raise ValueError('Packet membership is empty, duplicate or outside main selection')
        if any(r != by_id[r.sample_id] for r in rows):
            raise ValueError('Packet content differs from original draft')
        digest = sha256_file(path)
        if digest in packets: raise ValueError('Ambiguous packet manifest hash')
        packets[digest] = (path, rows); fingerprints[path] = digest; packet_ids.update(ids)
    expected_ids = {r.sample_id for r in original if r.source_dataset != 'oxford_pet'}
    if packet_ids != expected_ids: raise ValueError('Packet CSVs do not cover all non-Pet main IDs')
    pet = read_manifest(pet_path)
    valid_pet, proof_inputs = validate_pet(root,pet)
    if valid_pet != {r.sample_id for r in original if r.source_dataset == 'oxford_pet'}:
        raise ValueError('Pet manifest does not cover exactly the original Pet IDs')
    for path in proof_inputs: fingerprints[path] = sha256_file(path)
    for row in pet:
        before = by_id[row.sample_id].model_dump(); after = row.model_dump()
        for key in before:
            if key not in {'metadata','qa_status','translation_status'} and before[key] != after[key]:
                raise ValueError('Previously approved Pet source/content changed')
    imported = {r.sample_id:r for r in pet}
    seen_packets, sources, details, cases = set(), [], [], []
    for review_path in sorted(input_dir.rglob('*.json')):
        payload = json.loads(review_path.read_text(encoding='utf-8-sig'))
        key = payload.get('context',{}).get('manifest_sha256')
        if key not in packets: raise ValueError('Unknown/unbound review JSON: ' + review_path.name)
        if key in seen_packets: raise ValueError('Multiple submissions for one packet; choose explicitly before aggregation')
        path, rows = packets[key]
        # Reuse the existing strict context, history, identity, final-VI and image checks.
        result, audit = import_review(rows,manifest_path=path,root=root,review_path=review_path,operator=operator)
        seen_packets.add(key); fingerprints[review_path] = sha256_file(review_path)
        decisions = {item['sample_id']:MainDecision.model_validate(item) for item in payload['decisions']}
        approved = 0
        for before, after in zip(rows,result):
            decision = decisions[before.sample_id]
            accepted, primary, flags = classify(before,decision)
            if accepted != (after.qa_status == after.translation_status == 'approved'):
                raise ValueError('Classification differs from strict importer')
            imported[after.sample_id] = after; approved += accepted
            details.append({'sample_id':after.sample_id,'dataset':after.source_dataset,'packet':path.stem,
                'review_path':review_path.relative_to(root).as_posix(),'review_sha256':fingerprints[review_path],
                'translation_status':after.translation_status,'qa_status':after.qa_status,'accepted':accepted,
                'translation_changed':after.question_vi != before.question_vi,'flags':flags,
                'original_row_sha256':row_hash(before),'imported_row_sha256':row_hash(after)})
            if not accepted:
                cases.append({'sample_id':before.sample_id,'dataset':before.source_dataset,'packet':path.stem,
                    'image_path':before.image_path,'image_sha256':before.image_sha256,'category':before.category,
                    'question_en':before.question_en,'question_vi_original':before.question_vi,'question_vi_final':after.question_vi,
                    'source_ground_truth':before.ground_truth,'translation_status':after.translation_status,'qa_status':after.qa_status,
                    'primary_issue':primary,'flags':flags,'action':ACTIONS[primary],
                    'review_path':review_path.relative_to(root).as_posix(),'review_sha256':fingerprints[review_path],
                    'decision':decision.model_dump()})
        sources.append({'packet':path.stem,'manifest':path.relative_to(root).as_posix(),
            'review_path':review_path.relative_to(root).as_posix(),'review_sha256':fingerprints[review_path],
            'rows':len(rows),'accepted':approved,'needs_resolution':len(rows)-approved,
            'operator':audit['operator'],'scope':audit['scope']})
    missing = sorted(packets[key][0].stem for key in packets if key not in seen_packets)
    for row in original:
        if row.sample_id not in imported:
            imported[row.sample_id] = row
            cases.append({'sample_id':row.sample_id,'dataset':row.source_dataset,'packet':None,
                'image_path':row.image_path,'image_sha256':row.image_sha256,'category':row.category,
                'question_en':row.question_en,'question_vi_original':row.question_vi,'question_vi_final':row.question_vi,
                'source_ground_truth':row.ground_truth,'translation_status':row.translation_status,'qa_status':row.qa_status,
                'primary_issue':'missing_review_packet','flags':['missing_review_packet'],
                'action':'Bổ sung JSON review đúng gói; chưa có approval để import.', 'review_path':None,'decision':None})
    result = [imported[key] for key in sorted(by_id)]
    # Never change protected fields, source metadata, labels, IDs or the sample count.
    for row in result:
        before = by_id[row.sample_id].model_dump(); after = row.model_dump()
        for key in before:
            if key not in {'question_vi','qa_status','translation_status','metadata'} and before[key] != after[key]:
                raise ValueError('Aggregation changed protected source field: ' + key)
        expected_meta = dict(before['metadata']); actual_meta = dict(after['metadata'])
        actual_meta.pop('main_review',None)
        if actual_meta != expected_meta: raise ValueError('Aggregation changed source metadata')
    for path, digest in fingerprints.items():
        if sha256_file(path) != digest: raise ValueError('Input changed during aggregation')
    accepted_total = sum(r.qa_status == r.translation_status == 'approved' for r in result)
    summary = {'schema_version':'main_review_aggregation_v1','scope':'imported_human_reviews_not_adjudicated_or_frozen',
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),'rows':len(result),'unique_images':len({r.image_sha256 for r in result}),
        'submitted_packets':len(sources),'submitted_nonpet_rows':len(details),'missing_packets':missing,
        'accepted_nonpet':sum(d['accepted'] for d in details),'accepted_pet':len(pet),'accepted_total':accepted_total,
        'needs_resolution':len(result)-accepted_total,'translation_changed':sum(d['translation_changed'] for d in details),
        'unresolved_by_primary_issue':dict(Counter(c['primary_issue'] for c in cases)),
        'by_dataset':{dataset:{'rows':len(rs),'accepted':sum(r.qa_status == r.translation_status == 'approved' for r in rs),
            'needs_resolution':sum(r.qa_status != 'approved' or r.translation_status != 'approved' for r in rs),
            'qa_status':dict(Counter(r.qa_status for r in rs)), 'translation_status':dict(Counter(r.translation_status for r in rs))}
            for dataset in sorted(config.targets) if (rs := [r for r in result if r.source_dataset == dataset])},
        'inputs_sha256':{p.relative_to(root).as_posix():d for p,d in sorted(fingerprints.items())},
        'packets':sources,'row_index':details,'source_labels_changed':0,'new_human_approvals_created':0,
        'archived_approvals_restored':0,'frozen':False,'M1':'IN_PROGRESS' if cases else 'REVIEW_IMPORT_COMPLETE_PENDING_FINAL_AUDIT',
        'M2':'PENDING','M3':'NOT_RUN','new_model_inferences':0}
    return result,summary,sorted(cases,key=lambda c:(c['dataset'],c['packet'] or '',c['sample_id']))


def publish(root, rows, summary, cases, *, output_dir, report_dir):
    output, report = inside(root,output_dir),inside(root,report_dir)
    if not output.is_relative_to(root/'data/main') or not report.is_relative_to(root/'reports'):
        raise ValueError('Use new data/main and reports destinations')
    targets = [output/'main_reviewed.csv',report/'aggregation.json',report/'needs_resolution.json']
    if any(p.exists() for p in targets): raise ValueError('Preserve previous aggregation outputs; choose a new version')
    for path,digest in summary['inputs_sha256'].items():
        if sha256_file(inside(root,path)) != digest: raise ValueError('Input changed before publication')
    atomic_bytes(targets[0],manifest_bytes(rows))
    write_json(targets[1],summary)
    write_json(targets[2],{'scope':'pending_human_resolution_not_new_ground_truth','rows':len(cases),'cases':cases})
