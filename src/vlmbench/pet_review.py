"""Pet-only human translation/image-quality attestation with inherited source labels.

This is not a two-reviewer visual breed identification and cannot approve other tasks.
"""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import tarfile
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .datasets.candidates import Candidate
from .datasets.oxford_pet import parse_oxford_pet
from .io_utils import read_manifest, sha256_file
from .qa import preflight_image, leakage_issues
from .reviews import row_hash
from .schemas import ManifestRow
from .translate import require_review_identity

POLICY = 'pet_human_translation_image_quality_source_labels_v1'
SCHEMA = 'pet_source_review_v1'
ANNOTATION_SHA256 = '52425fb6de5c424942b7626b428656fcbd798db970a937df61750c0f1d358e91'
BREEDS = ['american_bulldog', 'american_pit_bull_terrier', 'basset_hound', 'beagle',
          'boxer', 'chihuahua', 'english_cocker_spaniel', 'english_setter']
PET_LABELS = dict(zip('ABCDEFGH', ['American Bulldog', 'American Pit Bull Terrier', 'Basset Hound',
    'Beagle', 'Boxer', 'Chihuahua', 'English Cocker Spaniel', 'English Setter']))
SELECTION = 'data/main/preparation_v2/all_candidates.jsonl'
ANNOTATIONS = 'data/raw/main_metadata_v1/pet_annotations.tar.gz'
IMAGES_RECEIPT = 'data/raw/task_images_v1/oxford_pet/receipt.json'
PILOT = 'data/pilot/stage1_qa_v1/pilot_manifest.csv'
EXCLUSIONS = 'data/pilot/image_exclusions.json'


class HumanAttestation(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    reviewer_id: str = Field(min_length=1)
    identity_basis: str = Field(min_length=1)
    source: Literal['project_user_conversation']
    declaration: str = Field(min_length=1)
    policy_acceptance: str = Field(min_length=1)
    declared_on: str
    recorded_at_utc: str
    actual_review_time: Literal['not_provided']
    coverage: Literal['all_samples_in_bound_manifest']
    translation: Literal['approved']
    image_quality: Literal['approved']
    breed_identity_human_verified: Literal[False]
    source_labels: Literal['accepted_from_official_annotations']


def inside(root, path):
    target = (root / path).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError('Pet review paths must stay inside project')
    return target


def _attestation(value):
    attestation = HumanAttestation.model_validate(value)
    require_review_identity(attestation.reviewer_id, attestation.recorded_at_utc, field='attestation recording')
    datetime.strptime(attestation.declared_on, '%Y-%m-%d')
    return attestation.model_dump()


def _audit(root, rows):
    if not rows or len({r.sample_id for r in rows}) != len(rows):
        raise ValueError('Nonempty unique Pet rows required')
    if any(r.source_dataset != 'oxford_pet' or r.task != 'fine_grained' or r.is_pilot for r in rows):
        raise ValueError('This policy is only for nonpilot Oxford Pet fine-grained rows')
    paths = [SELECTION, ANNOTATIONS, IMAGES_RECEIPT, PILOT, EXCLUSIONS]
    archive = inside(root, ANNOTATIONS)
    if sha256_file(archive) != ANNOTATION_SHA256:
        raise ValueError('Official Pet annotation archive checksum differs')
    with tarfile.open(archive, 'r:gz') as source:
        member = source.getmember('annotations/test.txt')
        if not member.isfile() or member.size > 1_000_000:
            raise ValueError('Unexpected official test list')
        payload = source.extractfile(member).read()
    revision = 'sha256:' + ANNOTATION_SHA256
    official = {c.sample_id: c for c in parse_oxford_pet(payload, revision=revision, breeds=BREEDS)}
    selection = [Candidate.model_validate_json(line) for line in inside(root, SELECTION).read_text(encoding='utf-8').splitlines() if line.strip()]
    selected = {c.sample_id: c for c in selection if c.source_dataset == 'oxford_pet'}
    if len(selected) != sum(c.source_dataset == 'oxford_pet' for c in selection) or set(selected) != {r.sample_id for r in rows}:
        raise ValueError('Pet review must cover exactly the pinned Pet selection')
    receipt = json.loads(inside(root, IMAGES_RECEIPT).read_text(encoding='utf-8'))
    if receipt['binding']['dataset'] != 'oxford_pet' or receipt['binding']['policy'] != 'official_selected_original_jpeg_v1':
        raise ValueError('Pet image receipt binding differs')
    pilot = read_manifest(inside(root, PILOT))
    exclusions = json.loads(inside(root, EXCLUSIONS).read_text(encoding='utf-8'))['images']
    blocked_ids = {(r['image_namespace'], r['image_id']) for r in exclusions}
    blocked_sha = {r['image_sha256'] for r in exclusions}
    if leakage_issues(pilot, rows):
        raise ValueError('Pet pilot overlap')
    if len({r.image_id for r in rows}) != len(rows) or len({r.image_sha256 for r in rows}) != len(rows):
        raise ValueError('Duplicate Pet image identity or bytes')
    checks = {}
    for row in rows:
        candidate = official.get(row.sample_id)
        if candidate is None or selected[row.sample_id] != candidate:
            raise ValueError('Pet selected candidate differs from official test annotation')
        for field in ('source_dataset', 'source_split', 'source_row_id', 'image_id', 'task', 'category', 'question_en', 'ground_truth'):
            if getattr(row, field) != getattr(candidate, field):
                raise ValueError('Pet protected source field differs: ' + field)
        for field in ('source_revision', 'source_record_sha256', 'image_namespace'):
            if row.metadata.get(field) != getattr(candidate, field):
                raise ValueError('Pet source provenance differs: ' + field)
        if any(row.metadata.get(k) != v for k, v in candidate.metadata.items()):
            raise ValueError('Pet source breed/class/map metadata differs')
        if row.metadata.get('candidate_labels') != PET_LABELS or row.ground_truth_source != 'oxford_pet:' + revision:
            raise ValueError('Pet A-H mapping/ground truth source differs')
        expected_path = 'data/raw/task_images_v1/oxford_pet/images/' + candidate.source_image_ref
        info = preflight_image(inside(root, row.image_path))
        recorded = receipt['images'][row.image_id]
        if (row.image_path != expected_path or info['format'] != 'JPEG' or info['sha256'] != row.image_sha256
                or recorded['path'] != row.image_path or recorded['sha256'] != row.image_sha256
                or recorded['width'] != info['width'] or recorded['height'] != info['height']):
            raise ValueError('Pet image identity/checksum/receipt differs')
        if (candidate.image_namespace, row.image_id) in blocked_ids or row.image_sha256 in blocked_sha:
            raise ValueError('Pet pilot registry overlap')
        checks[row.sample_id] = {'official_test_annotation_match': True, 'mapping_A_H_match': True,
            'source_record_sha256': candidate.source_record_sha256, 'source_class_id': candidate.metadata['source_class_id'],
            'source_breed_id': candidate.metadata['source_breed_id'], 'breed': candidate.category,
            'source_species': 2, 'image_sha256': row.image_sha256,
            'original_size_wh': [info['width'], info['height']], 'image_receipt_match': True, 'pilot_overlap': False}
    return checks, {p: sha256_file(inside(root, p)) for p in paths}


def create_review(root, manifest_path, attestation):
    """Materialize an explicit user's declaration, never infer human review from checks."""
    root = root.resolve()
    manifest_path = inside(root, manifest_path)
    rows = read_manifest(manifest_path)
    if any(r.qa_status != 'pending' or r.translation_status != 'requires_review' for r in rows):
        raise ValueError('Use original pending Pet bilingual draft')
    human = _attestation(attestation)
    checks, sources = _audit(root, rows)
    return {'schema_version': SCHEMA, 'policy': POLICY,
        'context': {'manifest': manifest_path.relative_to(root).as_posix(), 'manifest_sha256': sha256_file(manifest_path),
            'sample_ids': [r.sample_id for r in rows], 'source_files_sha256': sources, 'candidate_labels': PET_LABELS},
        'human_attestation': human,
        'decisions': [{'sample_id': r.sample_id, 'original_row_sha256': row_hash(r), 'question_en': r.question_en,
            'question_vi': r.question_vi, 'image_id': r.image_id, 'image_path': r.image_path,
            'translation': 'approved', 'image_quality': 'approved', 'ground_truth': r.ground_truth,
            'label_basis': 'official_dataset_annotation_not_human_breed_identification',
            'automated_checks': checks[r.sample_id]} for r in rows]}


def import_review(root, review_path):
    root = root.resolve()
    review_path = inside(root, review_path)
    review = json.loads(review_path.read_text(encoding='utf-8'))
    original = inside(root, review['context']['manifest'])
    expected = create_review(root, original, review['human_attestation'])
    if review != expected:
        raise ValueError('Pet review content/provenance differs from current bound inputs')
    result = []
    for row in read_manifest(original):
        data = row.model_dump()
        data.update(qa_status='approved', translation_status='approved')
        data['metadata']['main_review'] = {'schema_version': SCHEMA, 'policy': POLICY,
            'review_path': review_path.relative_to(root).as_posix(), 'review_sha256': sha256_file(review_path),
            'original_row_sha256': row_hash(row)}
        result.append(ManifestRow.model_validate(data))
    return result, {'schema_version': SCHEMA, 'policy': POLICY, 'rows': len(result),
        'scope': 'recorded_single_user_translation_and_image_quality_with_inherited_source_labels',
        'human_breed_identification': False, 'two_human_reviewers': False,
        'review_sha256': sha256_file(review_path), 'manifest_sha256': sha256_file(original),
        'qa_status': dict(Counter(r.qa_status for r in result)),
        'translation_status': dict(Counter(r.translation_status for r in result)),
        'imported_at_utc': datetime.now(timezone.utc).isoformat(), 'frozen': False}


def validate_imported(root, rows):
    """Recheck source evidence and exact imported rows before the main freeze gate."""
    groups = {}
    for row in rows:
        proof = row.metadata.get('main_review', {})
        if row.source_dataset != 'oxford_pet' or proof.get('policy') != POLICY:
            raise ValueError('Pet source proof cannot approve another dataset')
        groups.setdefault(proof['review_path'], []).append(row)
    valid, inputs = set(), set()
    for path, group in groups.items():
        expected, _ = import_review(root, path)
        by_id = {r.sample_id: r for r in expected}
        if {r.sample_id for r in group} != set(by_id):
            raise ValueError('Imported Pet proof must retain its complete bound selection')
        for row in group:
            if row != by_id[row.sample_id]:
                raise ValueError('Imported Pet row differs from bound declaration')
            valid.add(row.sample_id)
        payload = json.loads(inside(root, path).read_text(encoding='utf-8'))
        inputs.update([path, payload['context']['manifest'], *payload['context']['source_files_sha256']])
    return valid, [inside(root, p) for p in sorted(inputs)]
