"""Two named reviewers each attest translation and image/label QA (main v2)."""
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
from html import escape
import json
from pathlib import Path
from typing import Literal
import zipfile

from pydantic import BaseModel, ConfigDict, Field

from .io_utils import atomic_bytes, manifest_bytes, read_manifest, sha256_file
from .label_qa import _check_images
from .main_review import Decision, observed_truth
from .qa import preflight_image
from .reviews import row_hash
from .schemas import ManifestRow
from .translate import require_review_identity

POLICY = 'two_reviewers_translation_and_image_v2'
SLOTS = ('reviewer_a', 'reviewer_b')
PACKET_DIR = 'data/reviews/main_review_v2'
REPORT_DIR = 'reports/stage1/v12/main_review'
TEMPLATE = Path(__file__).with_name('main_review_v2_template.html')


class ReviewRound(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    translation: Decision = Field(default_factory=Decision)
    image_qa: Decision = Field(default_factory=Decision)


class ArchivedRound(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    reviewer_slot: Literal['reviewer_a', 'reviewer_b']
    question_vi: str
    review: ReviewRound
    archived_at: str
    reason: Literal['translation_changed', 'review_replaced']


class MainDecision(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    sample_id: str
    question_vi: str
    reviewer_a: ReviewRound = Field(default_factory=ReviewRound)
    reviewer_b: ReviewRound = Field(default_factory=ReviewRound)
    history: list[ArchivedRound] = Field(default_factory=list)


def context(rows, manifest_path):
    return _context(rows, sha256_file(manifest_path))


def _context(rows, manifest_sha256):
    return {'schema_version': 'main_review_v2', 'policy': POLICY,
            'manifest_sha256': manifest_sha256, 'template_sha256': sha256_file(TEMPLATE),
            'sample_ids': [r.sample_id for r in rows],
            'row_sha256': {r.sample_id: row_hash(r) for r in rows}}


def _validate_round(row, review, question_vi):
    owners = set()
    for name in ('translation', 'image_qa'):
        part = getattr(review, name)
        if part == Decision():
            continue
        require_review_identity(part.reviewer_id, part.reviewed_at, field=name)
        owners.add(part.reviewer_id.strip().casefold())
        if part.reviewed_question_vi != question_vi:
            raise ValueError('Decision belongs to another VI text; review again')
        if part.status == 'rejected' and not part.notes.strip():
            raise ValueError('Rejection requires notes')
        if name == 'translation':
            if part.observed_answer:
                raise ValueError('Translation decision cannot contain an image observation')
        elif part.status != 'pending' or part.observed_answer:
            observed = observed_truth(row, part.observed_answer)
            if part.observed_answer == 'uncertain' and not part.notes.strip():
                raise ValueError('Uncertain observation requires notes')
            if part.status == 'approved' and observed != row.ground_truth:
                raise ValueError('Approved observation differs from source truth')
    if len(owners) > 1:
        raise ValueError('One reviewer must own both decisions in a review round')
    return next(iter(owners), None)


def import_review(rows, *, manifest_path, root, review_path, operator):
    if not operator.strip():
        raise ValueError('Import operator required')
    if not rows or len({r.sample_id for r in rows}) != len(rows):
        raise ValueError('Nonempty unique main rows required')
    _check_images(rows, root)
    payload = json.loads(review_path.read_text(encoding='utf-8'))
    if set(payload) != {'context', 'decisions'} or payload['context'] != context(rows, manifest_path):
        raise ValueError('Review context differs; use the matching v2 packet')
    decisions = [MainDecision.model_validate(d) for d in payload['decisions']]
    if len(decisions) != len(rows) or {d.sample_id for d in decisions} != {r.sample_id for r in rows}:
        raise ValueError('Review IDs incomplete/duplicate')
    decisions = {d.sample_id: d for d in decisions}
    result, events = [], []
    for row in rows:
        if row.is_pilot or row.translation_status == 'approved' or row.qa_status == 'approved':
            raise ValueError('Use original unapproved main draft batches')
        d = decisions[row.sample_id]
        if not d.question_vi.strip():
            raise ValueError('VI question cannot be empty')
        owners = [_validate_round(row, getattr(d, slot), d.question_vi) for slot in SLOTS]
        if owners[0] and owners[0] == owners[1]:
            raise ValueError('Two different reviewers required for A and B')
        for old in d.history:
            require_review_identity('history', old.archived_at, field='history')
            if not old.question_vi.strip():
                raise ValueError('Archived VI cannot be empty')
            _validate_round(row, old.review, old.question_vi)
        rounds = [getattr(d, slot) for slot in SLOTS]
        language = _aggregate([p.translation.status for p in rounds], 'requires_review')
        qa = _aggregate([p.image_qa.status for p in rounds], 'pending')
        data = row.model_dump()
        data.update(question_vi=d.question_vi, translation_status=language, qa_status=qa)
        data['metadata']['main_review'] = {'schema_version': 'main_review_v2', 'policy': POLICY,
            'operator': operator.strip(), 'review_sha256': sha256_file(review_path),
            'decision': d.model_dump()}
        new = ManifestRow.model_validate(data)
        result.append(new)
        events.append({'sample_id': row.sample_id, 'before': row_hash(row), 'after': row_hash(new),
                       'decision': d.model_dump()})
    return result, {'scope': 'imported_human_attestations_not_identity_verification',
        'schema_version': 'main_review_v2', 'policy': POLICY, 'operator': operator.strip(),
        'imported_at_utc': datetime.now(timezone.utc).isoformat(),
        'manifest_sha256': sha256_file(manifest_path), 'review_sha256': sha256_file(review_path),
        'events': events, 'qa_status': dict(Counter(r.qa_status for r in result)),
        'translation_status': dict(Counter(r.translation_status for r in result))}


def _aggregate(statuses, pending):
    if all(s == 'approved' for s in statuses):
        return 'approved'
    return 'rejected' if 'rejected' in statuses else pending


def export_batches(root, *, manifests, output, report_dir, batch_size=50):
    root = root.resolve()
    if not 1 <= batch_size <= 50:
        raise ValueError('Batch size must be 1..50')
    if not all(p.resolve().is_relative_to(root) for p in (output, report_dir)):
        raise ValueError('Use output paths inside project')
    outputs, packets, seen = {}, [], set()
    for manifest in manifests:
        rows = read_manifest(manifest)
        if not rows or len({r.sample_id for r in rows}) != len(rows):
            raise ValueError('Nonempty unique main rows required')
        if any(r.is_pilot or r.translation_status == 'approved' or r.qa_status == 'approved' for r in rows):
            raise ValueError('Only unapproved main drafts can be exported')
        if seen.intersection(r.sample_id for r in rows):
            raise ValueError('Sample IDs overlap between input manifests')
        seen.update(r.sample_id for r in rows)
        dataset = rows[0].source_dataset
        if any(r.source_dataset != dataset for r in rows):
            raise ValueError('One task per manifest')
        _check_images(rows, root)
        for number, start in enumerate(range(0, len(rows), batch_size), 1):
            batch = rows[start:start + batch_size]
            key = f'{dataset}_{number:02d}'
            path = output / f'{key}.csv'
            if path in outputs:
                raise ValueError('Duplicate packet name')
            outputs[path] = manifest_bytes(batch)
            ctx = _context(batch, hashlib.sha256(outputs[path]).hexdigest())
            pending = {'context': ctx, 'decisions': [MainDecision(sample_id=r.sample_id,
                question_vi=r.question_vi).model_dump() for r in batch]}
            review_path = output / f'{key}.json'
            outputs[review_path] = _json_bytes(pending)
            cards = []
            for row in batch:
                image = root / row.image_path
                mime = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp'}[preflight_image(image)['format']]
                cards.append({'sample_id': row.sample_id, 'image_id': row.image_id, 'task': row.task,
                    'question_en': row.question_en, 'ground_truth': row.ground_truth,
                    'labels': row.metadata.get('candidate_labels', {}),
                    'review_note': row.metadata.get('translation_draft', {}).get('review_note', ''),
                    'image': 'data:' + mime + ';base64,' + base64.b64encode(image.read_bytes()).decode()})
            html = report_dir / f'{key}.html'
            payload = json.dumps({'review': pending, 'cards': cards, 'packet': key},
                                 ensure_ascii=False).replace('<', '\\u003c')
            outputs[html] = TEMPLATE.read_text(encoding='utf-8').replace('__MAIN_REVIEW_PAYLOAD__', payload).encode('utf-8')
            packets.append({'packet': key, 'rows': len(batch), 'manifest': path.relative_to(root).as_posix(),
                            'pending_review': review_path.relative_to(root).as_posix(),
                            'html': html.relative_to(root).as_posix()})
    report = {'scope': 'unreviewed_main_packets', 'schema_version': 'main_review_v2', 'policy': POLICY,
              'rows': len(seen), 'packets': packets, 'reviewers_required': 2,
              'each_reviewer_checks': ['translation', 'image_qa'],
              'new_human_approvals': 0, 'model_outputs_in_packets': False}
    links = ''.join(f'<tr><td>{escape(p["packet"])}</td><td>{p["rows"]}</td><td><a href="{escape(Path(p["html"]).name)}">Mở review</a></td></tr>' for p in packets)
    outputs[report_dir / 'index.html'] = ('''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Review main v2 — A/B</title><style>body{font:17px system-ui;max-width:950px;margin:auto;padding:24px}table{border-collapse:collapse;width:100%}td,th{padding:10px;border-bottom:1px solid #ccc;text-align:left}</style>
<h1>Review main v2 — mỗi người kiểm cả dịch và ảnh/nhãn</h1>
<p>A nhập ID của mình, chọn Lượt A, kiểm bản dịch và ảnh/nhãn, lưu từng mẫu rồi tải JSON gửi B. B mở cùng gói, nạp JSON của A, nhập ID của B và chọn Lượt B để kiểm lại cả hai phần. B tải JSON cuối để gửi tổng hợp.</p>
<p>Cần hai ID khác nhau; chỉ A làm thì chưa đủ duyệt. Nếu sửa VI, các lượt cũ vào lịch sử và cần duyệt lại bản cuối. Chưa chắc giữ pending, ghi chú vấn đề; không sửa nhãn nguồn. Không có đáp án model.</p>
<p>Mỗi gói nộp một JSON cuối; giữ các bản A/B làm backup. Thử lưu, tải và mở lại 2–3 mẫu trước khi làm cả gói. JSON v1 không dùng trực tiếp trên trang v2.</p>
<table><thead><tr><th>Gói</th><th>Số mẫu</th><th>Trang</th></tr></thead><tbody>''' + links + '</tbody></table></html>').encode('utf-8')
    outputs[report_dir / 'packets.json'] = _json_bytes(report)
    # Validate all existing outputs before writing any file, including human edits.
    for path, content in outputs.items():
        if path.exists() and path.read_bytes() != content:
            raise ValueError('Output already differs; preserve and use a new version')
    for path, content in outputs.items():
        if not path.exists():
            atomic_bytes(path, content)
    return report


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def build_review_bundle(root, output):
    """Standalone private offline review pages; never overwrite an older ZIP."""
    root, output = root.resolve(), output.resolve()
    if not output.is_relative_to(root / 'exports') or output.exists():
        raise ValueError('Use a new ZIP path under exports')
    report_path = root / REPORT_DIR / 'packets.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if report.get('policy') != POLICY or report.get('schema_version') != 'main_review_v2':
        raise ValueError('Expected v2 review packets')
    names = {f'{REPORT_DIR}/index.html', f'{REPORT_DIR}/packets.json'}
    for packet in report['packets']:
        key = packet['packet']
        expected = {'manifest': f'{PACKET_DIR}/{key}.csv', 'pending_review': f'{PACKET_DIR}/{key}.json',
                    'html': f'{REPORT_DIR}/{key}.html'}
        if any(packet[k] != v for k, v in expected.items()):
            raise ValueError('Packet paths differ from fixed v2 layout')
        if not key or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in key):
            raise ValueError('Unsafe packet name')
        names.update(expected.values())
    contents = {}
    for name in sorted(names):
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError('Invalid bundle input')
        contents[name] = {'bytes': path.stat().st_size, 'sha256': sha256_file(path)}
    if sum(p['bytes'] for p in contents.values()) > 500 * 1024 ** 2:
        raise ValueError('Review bundle exceeds 500 MiB budget')
    import io
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        def put(name, data):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
        for name in sorted(names):
            put(name, (root / name).read_bytes())
        put('REVIEW_README.txt', ('Review main v2: hai nguoi A/B, moi nguoi kiem ca dich va anh/nhan.\n'
            f'Giai nen vao thu muc moi; mo {REPORT_DIR}/index.html.\n'
            'A tai JSON gui B; B mo JSON cua A va review Luot B. Tai JSON cuoi gui tong hop.\n'
            'Khong can Python/GPU. JSON v1 khong tu dong chuyen sang v2.\n').encode('utf-8'))
        put('REVIEW_BUNDLE_CONTENTS.json', _json_bytes({'schema_version': 'main_review_bundle_v2',
            'policy': POLICY, 'files': contents, 'template_sha256': sha256_file(TEMPLATE)}))
    atomic_bytes(output, buffer.getvalue())
    return {'archive': output.relative_to(root).as_posix(), 'bytes': output.stat().st_size,
            'sha256': sha256_file(output), 'schema_version': 'main_review_bundle_v2',
            'rows': report['rows'], 'packets': len(report['packets']),
            'publication': 'private offline review; excluded from Git', 'new_human_approvals': 0}
