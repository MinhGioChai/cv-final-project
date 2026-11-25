"""Synthetic source archives/attestations; no real approvals produced by tests."""
import copy
import io
import json
from pathlib import Path
import tarfile
import yaml

from PIL import Image
import pytest

from vlmbench import pet_review as pet
from vlmbench.datasets.oxford_pet import parse_oxford_pet
from vlmbench.io_utils import read_manifest, sha256_file, write_json, write_manifest
from vlmbench.reviews import row_hash

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def pet_project(tmp_path, row_factory, monkeypatch):
    archive = tmp_path / pet.ANNOTATIONS
    archive.parent.mkdir(parents=True)
    text = ''.join(f'{breed}_1 {i+1} 2 {i+1}\n' for i, breed in enumerate(pet.BREEDS)).encode()
    with tarfile.open(archive, 'w:gz') as target:
        info = tarfile.TarInfo('annotations/test.txt'); info.size = len(text)
        target.addfile(info, io.BytesIO(text))
    monkeypatch.setattr(pet, 'ANNOTATION_SHA256', sha256_file(archive))
    revision = 'sha256:' + sha256_file(archive)
    candidates = parse_oxford_pet(text, revision=revision, breeds=pet.BREEDS)
    selected = tmp_path / pet.SELECTION; selected.parent.mkdir(parents=True)
    selected.write_text(''.join(c.model_dump_json() + '\n' for c in candidates), encoding='utf-8')
    rows, receipts = [], {}
    for i, c in enumerate(candidates):
        relative = 'data/raw/task_images_v1/oxford_pet/images/' + c.source_image_ref
        path = tmp_path / relative; path.parent.mkdir(parents=True, exist_ok=True)
        Image.new('RGB', (10+i, 12), color=(i*25, 20, 30)).save(path)
        meta = {**c.metadata, 'candidate_labels': pet.PET_LABELS, 'source_revision': revision,
            'source_record_sha256': c.source_record_sha256, 'image_namespace': c.image_namespace,
            'synthetic_test_only': True}
        data = {k: getattr(c, k) for k in ('sample_id','source_dataset','source_split','source_row_id','image_id','task','category','question_en','ground_truth')}
        row = row_factory(**data, image_path=relative, image_sha256=sha256_file(path), is_pilot=False,
            question_vi='synthetic_test_only breed question', translation_status='requires_review', metadata=meta,
            ground_truth_source='oxford_pet:' + revision)
        rows.append(row)
        receipts[c.image_id] = {'path': relative, 'sha256': row.image_sha256, 'width': 10+i, 'height': 12}
    write_json(tmp_path / pet.IMAGES_RECEIPT, {'binding': {'dataset': 'oxford_pet',
        'policy': 'official_selected_original_jpeg_v1'}, 'images': receipts})
    pilot = row_factory(sample_id='synthetic_test_only_pilot', image_id='other')
    write_manifest(tmp_path / pet.PILOT, [pilot])
    write_json(tmp_path / pet.EXCLUSIONS, {'images': []})
    manifest = tmp_path / 'pet.csv'; write_manifest(manifest, rows)
    human = {'reviewer_id':'synthetic_test_only_user','identity_basis':'synthetic fixture',
        'source':'project_user_conversation','declaration':'synthetic_test_only declaration',
        'policy_acceptance':'synthetic_test_only policy acceptance', 'declared_on':'2026-11-25',
        'recorded_at_utc':'2026-11-25T15:30:59Z','actual_review_time':'not_provided',
        'coverage':'all_samples_in_bound_manifest','translation':'approved','image_quality':'approved',
        'breed_identity_human_verified':False,'source_labels':'accepted_from_official_annotations'}
    return tmp_path, manifest, human


def record(project):
    root, manifest, human = project
    value = pet.create_review(root, manifest, human)
    path = root / 'review.json'; write_json(path, value)
    return value, path


def test_record_import_and_proof_distinguish_source_labels_from_human_breed_id(pet_project):
    root, manifest, _ = pet_project
    before = manifest.read_bytes()
    review, path = record(pet_project)
    rows, audit = pet.import_review(root, path)
    ids, inputs = pet.validate_imported(root, rows)
    assert len(ids) == len(rows) == 8 and manifest.read_bytes() == before
    assert not audit['human_breed_identification'] and not audit['two_human_reviewers'] and not audit['frozen']
    assert review['human_attestation']['actual_review_time'] == 'not_provided'
    for old, row in zip(read_manifest(manifest), rows):
        assert row.qa_status == row.translation_status == 'approved'
        assert row.ground_truth == old.ground_truth and row.image_sha256 == old.image_sha256
        assert row.metadata['main_review']['original_row_sha256'] == row_hash(old)
        assert 'reviewer_a' not in row.metadata['main_review'] and 'reviewer_b' not in row.metadata['main_review']
    assert path in inputs and root / pet.ANNOTATIONS in inputs


@pytest.mark.parametrize('field,value', [('breed_identity_human_verified', True), ('image_quality','pending'),
    ('reviewer_id',''), ('recorded_at_utc','2026-11-25'), ('fake_second_reviewer','B')])
def test_human_scope_cannot_be_silently_expanded(pet_project, field, value):
    root, manifest, human = pet_project
    human[field] = value
    with pytest.raises(ValueError): pet.create_review(root, manifest, human)


@pytest.mark.parametrize('change', ['other_dataset','ground_truth','mapping','source_record','source_class',
    'image_bytes','annotation_bytes','missing_selection_row','pilot_registry','pilot_manifest','image_path'])
def test_source_identity_mapping_and_exclusion_tampering_blocks(pet_project, change):
    root, manifest, human = pet_project
    rows = read_manifest(manifest); row = rows[0]
    if change == 'other_dataset': row.source_dataset = 'repope'
    elif change == 'ground_truth': row.ground_truth = 'H'
    elif change == 'mapping': row.metadata['candidate_labels']['A'] = 'Wrong breed'
    elif change == 'source_record': row.metadata['source_record_sha256'] = '0'*64
    elif change == 'source_class': row.metadata['source_class_id'] = 37
    elif change == 'image_path': row.image_path = rows[1].image_path
    elif change == 'image_bytes': (root/row.image_path).write_bytes(b'corrupt')
    elif change == 'annotation_bytes': (root/pet.ANNOTATIONS).write_bytes(b'corrupt')
    elif change == 'missing_selection_row': rows.pop()
    elif change == 'pilot_registry': write_json(root/pet.EXCLUSIONS, {'images':[
        {'image_namespace':'oxford_iiit_pet','image_id':row.image_id,'image_sha256':row.image_sha256}]})
    elif change == 'pilot_manifest': write_manifest(root/pet.PILOT, [row.model_copy(update={'is_pilot':True})])
    write_manifest(manifest, rows)
    with pytest.raises(ValueError): pet.create_review(root, manifest, human)


@pytest.mark.parametrize('change', ['duplicate_decision','vi','label','audit','human_breed'])
def test_review_json_is_bound_to_exact_source_and_declaration(pet_project, change):
    root, _, _ = pet_project
    value, path = record(pet_project)
    if change == 'duplicate_decision': value['decisions'][1] = copy.deepcopy(value['decisions'][0])
    elif change == 'vi': value['decisions'][0]['question_vi'] = 'Changed'
    elif change == 'label': value['decisions'][0]['ground_truth'] = 'H'
    elif change == 'audit': value['decisions'][0]['automated_checks']['source_class_id'] = 37
    elif change == 'human_breed': value['human_attestation']['breed_identity_human_verified'] = True
    write_json(path, value)
    with pytest.raises(ValueError): pet.import_review(root, path)


@pytest.mark.parametrize('change', ['vi','status','label','review_hash','other_dataset','missing_row'])
def test_main_proof_rejects_changed_rows_and_missing_scope(pet_project, change):
    root, _, _ = pet_project
    _, path = record(pet_project)
    rows, _ = pet.import_review(root, path)
    row = rows[0]
    if change == 'vi': row.question_vi = 'Changed'
    elif change == 'status': row.qa_status = 'pending'
    elif change == 'label': row.ground_truth = 'H'
    elif change == 'review_hash': row.metadata['main_review']['review_sha256'] = '0'*64
    elif change == 'other_dataset': row.source_dataset = 'repope'
    elif change == 'missing_row': rows.pop()
    with pytest.raises(ValueError): pet.validate_imported(root, rows)


def test_pet_exception_keeps_other_tasks_pending_and_main_freeze_gate_closed(pet_project, row_factory):
    from vlmbench.baseline_contract import build_plan
    from vlmbench.baseline_runtime import run_main
    from vlmbench.datasets.candidates import Candidate
    root, _, _ = pet_project
    other, candidates = [], []
    for i, (dataset, task, truth) in enumerate([('repope','object_existence','no'),
            ('vsr','spatial','yes'), ('tallyqa','counting',2)]):
        path = root/f'other_{i}.jpg'; Image.new('RGB',(17+i,20),color=(90,i*35,70)).save(path)
        row = row_factory(sample_id=f'synthetic_test_only_{dataset}',source_dataset=dataset,
            task=task,ground_truth=truth,is_pilot=False,image_id=f'other_{i}',image_path=path.name,
            image_sha256=sha256_file(path),question_vi='synthetic question',translation_status='requires_review',
            metadata={'image_namespace':dataset,'source_revision':'a'*40,'source_record_sha256':'b'*64})
        other.append(row)
        candidates.append(Candidate(**{k:getattr(row,k) for k in ('sample_id','source_dataset','source_split',
            'source_row_id','image_id','task','category','question_en','ground_truth')}, source_revision='a'*40,
            source_record_sha256='b'*64,image_namespace=dataset,source_image_ref=path.name,metadata={}))
    selected = root/pet.SELECTION
    selected.write_text(selected.read_text(encoding='utf-8') + ''.join(c.model_dump_json()+'\n' for c in candidates),encoding='utf-8')
    _, path = record(pet_project)
    reviewed, _ = pet.import_review(root,path)
    write_manifest(root/'main.csv',other+reviewed)
    config = yaml.safe_load((REPO/'configs/baseline_v3_option_b_v1.yaml').read_text(encoding='utf-8'))
    config.update(manifests=['main.csv'],source_selection=pet.SELECTION,pilot_manifest=pet.PILOT,
        pilot_exclusions=pet.EXCLUSIONS,prompts='prompts.yaml', targets={'repope':1,'vsr':1,'tallyqa':1,'oxford_pet':8})
    (root/'prompts.yaml').write_bytes((REPO/'configs/prompts_baseline_v1.yaml').read_bytes())
    (root/'run.yaml').write_text(yaml.safe_dump(config),encoding='utf-8')
    plan = build_plan(root,root/'run.yaml')
    counts = plan.summary()['blocking_counts']
    assert counts == {'MAIN_QA_NOT_APPROVED':3,'BASELINE_NOT_FROZEN':1,'FREEZE_RECEIPT_REQUIRED':1}
    assert len(plan.cells) == 44 and not plan.summary()['execution_ready']
    assert path.relative_to(root).as_posix() in plan.protocol['inputs_sha256']
    def forbidden(): raise AssertionError('Must not load models/environment')
    with pytest.raises(ValueError,match='Main execution blocked'):
        run_main(plan,alias='qwen',run_id='test',platform_name='local',output='results/main/test.jsonl',
            execute=True,environment_provider=forbidden)
    reviewed[0].question_vi = 'Changed after acceptance'; write_manifest(root/'main.csv',other+reviewed)
    bad = build_plan(root,root/'run.yaml')
    assert bad.summary()['blocking_counts']['PET_SOURCE_REVIEW_PROOF_INVALID'] == 1
    assert bad.summary()['blocking_counts']['TWO_REVIEWER_PROOF_REQUIRED'] == 8
