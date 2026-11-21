"""Synthetic review attestations only; never real QA or model predictions."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest

from vlmbench.io_utils import read_manifest, write_json, write_manifest
from vlmbench.main_review_v2 import (MainDecision, POLICY, context, export_batches,
                                     import_review, build_review_bundle, PACKET_DIR, REPORT_DIR)


@pytest.fixture
def project(row_factory, tmp_path):
    rows = [row_factory(is_pilot=False, question_vi='synthetic_test_only', translation_status='requires_review')]
    manifest = tmp_path / 'source.csv'
    write_manifest(manifest, rows)
    review = tmp_path / 'review.json'
    payload = {'context': context(rows, manifest), 'decisions': [
        MainDecision(sample_id=r.sample_id, question_vi=r.question_vi).model_dump() for r in rows]}
    write_json(review, payload)
    return rows, dict(root=tmp_path, manifest_path=manifest, review_path=review, operator='synthetic_test_only')


def edit(options, callback):
    path = options['review_path']
    payload = json.loads(path.read_text(encoding='utf-8'))
    callback(payload)
    write_json(path, payload)


def approve(payload, slot, reviewer, observed='yes'):
    d = payload['decisions'][0]
    for name in ('translation', 'image_qa'):
        d[slot][name].update(status='approved', reviewer_id=reviewer,
            reviewed_at='2026-11-21T10:00:00+07:00', reviewed_question_vi=d['question_vi'],
            observed_answer=observed if name == 'image_qa' else '')


def test_pending_and_a_alone_never_approve_either_gate(project):
    rows, options = project
    for callback in (lambda p: None, lambda p: approve(p, 'reviewer_a', 'synthetic_A')):
        edit(options, callback)
        result, audit = import_review(rows, **options)
        assert result[0].translation_status == 'requires_review'
        assert result[0].qa_status == 'pending'
        assert audit['policy'] == POLICY


def test_a_b_each_check_both_and_preserve_source(project):
    rows, options = project
    def change(p):
        approve(p, 'reviewer_a', 'synthetic_A')
        approve(p, 'reviewer_b', 'synthetic_B')
    edit(options, change)
    result, audit = import_review(rows, **options)
    assert result[0].translation_status == result[0].qa_status == 'approved'
    for field in type(rows[0]).model_fields:
        if field not in {'metadata', 'qa_status', 'translation_status'}:
            assert getattr(result[0], field) == getattr(rows[0], field)
    assert rows[0].metadata.get('main_review') is None
    assert len(audit['events']) == 1


def test_old_three_role_pattern_cannot_satisfy_two_image_reviews(project):
    rows, options = project
    def change(p):
        approve(p, 'reviewer_a', 'synthetic_A')
        approve(p, 'reviewer_b', 'synthetic_B')
        p['decisions'][0]['reviewer_b']['image_qa'] = MainDecision(sample_id='x', question_vi='x').reviewer_b.image_qa.model_dump()
    edit(options, change)
    result, _ = import_review(rows, **options)
    assert result[0].translation_status == 'approved'
    assert result[0].qa_status == 'pending'


@pytest.mark.parametrize('mutation', ['same_id', 'split_owner', 'stale_vi', 'stale_qa', 'wrong_observation',
    'uncertain', 'reject_without_note', 'time', 'extra_label', 'context', 'v1', 'duplicate', 'missing', 'missing_identity'])
def test_reject_forged_stale_or_conflicting_attestations_without_writes(project, mutation):
    rows, options = project
    before = options['manifest_path'].read_bytes()
    def change(p):
        approve(p, 'reviewer_a', 'synthetic_A')
        approve(p, 'reviewer_b', 'synthetic_B')
        d = p['decisions'][0]
        if mutation == 'same_id':
            approve(p, 'reviewer_b', ' SYNTHETIC_a ')
        if mutation == 'split_owner': d['reviewer_b']['image_qa']['reviewer_id'] = 'synthetic_C'
        if mutation == 'stale_vi': d['question_vi'] = 'synthetic_changed'
        if mutation == 'stale_qa': d['reviewer_b']['image_qa']['reviewed_question_vi'] = 'synthetic_old'
        if mutation == 'wrong_observation': d['reviewer_b']['image_qa']['observed_answer'] = 'no'
        if mutation == 'uncertain': d['reviewer_b']['image_qa'].update(status='pending', observed_answer='uncertain')
        if mutation == 'reject_without_note': d['reviewer_b']['translation']['status'] = 'rejected'
        if mutation == 'time': d['reviewer_b']['image_qa']['reviewed_at'] = '2026-11-21T10:00:00'
        if mutation == 'extra_label': d['ground_truth'] = 'no'
        if mutation == 'context': p['context']['manifest_sha256'] = 'changed'
        if mutation == 'v1': p['context']['schema_version'] = 'main_review_v1'
        if mutation == 'duplicate': p['decisions'].append(d.copy())
        if mutation == 'missing': p['decisions'] = []
        if mutation == 'missing_identity': d['reviewer_b']['image_qa']['reviewer_id'] = ''
    edit(options, change)
    with pytest.raises(ValueError):
        import_review(rows, **options)
    assert options['manifest_path'].read_bytes() == before


def test_rejections_are_not_overridden_by_other_approval(project):
    rows, options = project
    def change(p):
        approve(p, 'reviewer_a', 'synthetic_A')
        approve(p, 'reviewer_b', 'synthetic_B')
        d = p['decisions'][0]['reviewer_b']
        d['translation'].update(status='rejected', notes='synthetic ambiguity')
        d['image_qa'].update(status='rejected', observed_answer='no', notes='synthetic disagreement')
    edit(options, change)
    result, _ = import_review(rows, **options)
    assert result[0].translation_status == result[0].qa_status == 'rejected'


@pytest.mark.parametrize('task,truth,observed', [('counting', 0, '0'), ('fine_grained', 'H', 'H'), ('spatial', 'no', 'no')])
def test_observations_preserve_task_labels(row_factory, tmp_path, task, truth, observed):
    row = row_factory(is_pilot=False, question_vi='synthetic_test_only', translation_status='requires_review', task=task, ground_truth=truth)
    manifest = tmp_path / 'source.csv'; write_manifest(manifest, [row])
    payload = {'context': context([row], manifest), 'decisions': [MainDecision(sample_id=row.sample_id, question_vi=row.question_vi).model_dump()]}
    approve(payload, 'reviewer_a', 'synthetic_A', observed)
    approve(payload, 'reviewer_b', 'synthetic_B', observed)
    review = tmp_path / 'review.json'; write_json(review, payload)
    result, _ = import_review([row], manifest_path=manifest, root=tmp_path, review_path=review, operator='synthetic_test_only')
    assert result[0].qa_status == 'approved'
    assert result[0].ground_truth == truth


def test_export_roundtrip_idempotence_and_no_overwrite_of_human_edits(project):
    rows, options = project; root = options['root']
    kwargs = dict(manifests=[options['manifest_path']], output=root / PACKET_DIR, report_dir=root / REPORT_DIR)
    report = export_batches(root, **kwargs)
    batch = root / PACKET_DIR / 'repope_01.csv'; pending = root / PACKET_DIR / 'repope_01.json'
    data = json.loads(pending.read_text(encoding='utf-8'))
    assert data['context'] == context(read_manifest(batch), batch)
    assert report == export_batches(root, **kwargs)
    assert report['new_human_approvals'] == 0
    assert 'data:image/png;base64,' in (root / REPORT_DIR / 'repope_01.html').read_text(encoding='utf-8')
    edit(dict(review_path=pending), lambda p: approve(p, 'reviewer_a', 'synthetic_A'))
    before = pending.read_bytes()
    with pytest.raises(ValueError, match='differs'):
        export_batches(root, **kwargs)
    assert pending.read_bytes() == before


def test_private_review_bundle_and_preserved_existing_zip(project):
    rows, options = project; root = options['root']
    export_batches(root, manifests=[options['manifest_path']], output=root / PACKET_DIR, report_dir=root / REPORT_DIR)
    archive = root / 'exports/review.zip'
    report = build_review_bundle(root, archive)
    with zipfile.ZipFile(archive) as z:
        assert f'{REPORT_DIR}/index.html' in z.namelist()
        assert f'{REPORT_DIR}/repope_01.html' in z.namelist()
        assert not any(n.startswith(('results/', 'src/', '.venv/')) for n in z.namelist())
        metadata = json.loads(z.read('REVIEW_BUNDLE_CONTENTS.json'))
        assert metadata['policy'] == POLICY
    assert report['new_human_approvals'] == 0
    before = archive.read_bytes()
    with pytest.raises(ValueError): build_review_bundle(root, archive)
    assert archive.read_bytes() == before


def test_ui_save_restore_a_b_revision_and_backend_import(project, tmp_path):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is optional for JS interaction tests; Python approval gates still run')
    rows, options = project; root = options['root']
    export_batches(root, manifests=[options['manifest_path']], output=root / PACKET_DIR, report_dir=root / REPORT_DIR)
    output = root / 'ui_result.json'
    runner = Path(__file__).with_name('main_review_v2_ui.cjs')
    subprocess.run([node, str(runner), str(root / REPORT_DIR / 'repope_01.html'), str(output)], check=True, capture_output=True, text=True)
    result, audit = import_review(rows, root=root, manifest_path=root / PACKET_DIR / 'repope_01.csv', review_path=output, operator='synthetic_test_only')
    assert result[0].qa_status == result[0].translation_status == 'approved'
    d = audit['events'][0]['decision']
    assert d['question_vi'] == 'synthetic_test_only_changed'
    assert d['history'][0]['reviewer_slot'] == 'reviewer_a'
    assert d['history'][0]['review']['translation']['reviewer_id'] == 'synthetic_A'


def test_cli_defaults_to_v2_dry_run_then_real_import_and_explicit_v1(row_factory, tmp_path):
    # Four tiny synthetic tasks exercise the actual entry point without model calls.
    sources = [
        ('repope', 'object_existence', 'yes', 'data/main/preparation_v2/repope_bilingual_draft_manifest.csv'),
        ('vsr', 'spatial', 'yes', 'data/main/preparation_v3/vsr_bilingual_draft.csv'),
        ('tallyqa', 'counting', 1, 'data/main/preparation_v3/tallyqa_bilingual_draft.csv'),
        ('oxford_pet', 'fine_grained', 'A', 'data/main/preparation_v3/oxford_pet_bilingual_draft.csv')]
    for dataset, task, truth, path in sources:
        row = row_factory(sample_id='synthetic_' + dataset, source_dataset=dataset, task=task,
            ground_truth=truth, is_pilot=False, question_vi='synthetic_test_only', translation_status='requires_review')
        write_manifest(tmp_path / path, [row])
    script = Path(__file__).resolve().parents[1] / 'scripts/review_main.py'
    def run(*args):
        return subprocess.run([sys.executable, str(script), *args], cwd=tmp_path, capture_output=True, text=True)
    exported = run('export')
    assert exported.returncode == 0, exported.stderr
    assert json.loads(exported.stdout)['version'] == 'v2'
    packet = tmp_path / PACKET_DIR / 'repope_01.csv'
    pending = tmp_path / PACKET_DIR / 'repope_01.json'
    reviewed = tmp_path / PACKET_DIR / 'repope_01_reviewed_v2.json'
    payload = json.loads(pending.read_text(encoding='utf-8'))
    approve(payload, 'reviewer_a', 'synthetic_A')
    approve(payload, 'reviewer_b', 'synthetic_B')
    write_json(reviewed, payload)
    target = tmp_path / 'reviewed.csv'; audit = tmp_path / 'audit.json'
    args = ['import', '--manifest', str(packet), '--review', str(reviewed), '--output', str(target),
            '--audit', str(audit), '--operator', 'synthetic_test_only']
    wrong = run(*args, '--version', 'v1')
    assert wrong.returncode != 0 and not target.exists() and not audit.exists()
    dry = run(*args, '--dry-run')
    assert dry.returncode == 0, dry.stderr
    assert json.loads(dry.stdout)['qa_status'] == {'approved': 1}
    assert not target.exists() and not audit.exists()
    imported = run(*args)
    assert imported.returncode == 0, imported.stderr
    assert read_manifest(target)[0].qa_status == 'approved'
    assert json.loads(audit.read_text())['policy'] == POLICY
    preserved = target.read_bytes()
    assert run(*args).returncode != 0 and target.read_bytes() == preserved
