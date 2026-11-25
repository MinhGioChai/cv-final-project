"""Real CPU-only Pet provenance/import/main-gate and preservation verification."""
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import zipfile
import hashlib

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'src'))
from vlmbench.baseline_contract import build_plan
from vlmbench.baseline_runtime import run_main
from vlmbench.io_utils import read_manifest, sha256_file, write_json
from vlmbench.pet_review import import_review, validate_imported

REF = '5c7ff365d4ac2bdb945e0d740383ca1f70dc6813'
REVIEW = 'data/reviews/pet_source_review_v1/oxford_pet_reviewed_v1.json'
IMPORTED = 'data/main/reviewed_pet_source_v1/oxford_pet_reviewed.csv'


def main():
    folder = Path(__file__).resolve().parent
    expected, audit = import_review(ROOT, REVIEW)
    actual = read_manifest(ROOT/IMPORTED)
    assert actual == expected and len(actual) == 160
    assert Counter(r.ground_truth for r in actual) == dict.fromkeys('ABCDEFGH',20)
    valid, inputs = validate_imported(ROOT, actual)
    assert len(valid) == 160
    config_path = ROOT/'configs/baseline_v3_option_b_v1.yaml'
    draft = build_plan(ROOT, config_path)
    assert draft.summary()['blocking_counts']['MAIN_QA_NOT_APPROVED'] == 1000
    config = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    config['manifests'][-1] = IMPORTED
    # CPU integration fixture only; not the official main candidate or a freeze.
    fixture = folder/'pet_qa_preflight_config.yaml'
    text = '# CPU integration evidence only; not an official main/final config.\n' + yaml.safe_dump(config,sort_keys=False)
    if fixture.exists(): assert fixture.read_text(encoding='utf-8') == text
    else: fixture.write_text(text,encoding='utf-8')
    plan = build_plan(ROOT, fixture)
    summary = plan.summary()
    assert summary['blocking_counts'] == {'MAIN_QA_NOT_APPROVED':840,'BASELINE_NOT_FROZEN':1,'FREEZE_RECEIPT_REQUIRED':1}
    assert summary['expected_inferences'] == 4000 and not summary['execution_ready']
    assert [(c.cell_id,c.prompt_hash) for c in plan.cells] == [(c.cell_id,c.prompt_hash) for c in draft.cells]
    calls = []
    def forbidden(): raise AssertionError('Main gate must precede environment/model loading')
    for model in ('qwen','gemma'):
        path = f'results/main/pet_review_v1/{model}_blocked.jsonl'
        try:
            run_main(plan,alias=model,run_id='pet_review_cpu_gate',platform_name='local',output=path,
                execute=True,smoke_per_task=1,environment_provider=forbidden)
        except ValueError as exc:
            assert str(exc).startswith('Main execution blocked:')
            assert not (ROOT/path).exists() and not (ROOT/path).with_suffix('.meta.json').exists()
            calls.append({'model':model,'blocked_before_environment_model':True,'error':str(exc)})
        else: raise AssertionError('Unexpected main execute')
    write_json(folder/'staged_plan.json',summary)
    allowed = {'src/vlmbench/baseline_contract.py','tests/test_baseline.py','README.md','HUONG_DAN_NHOM.md',
        'docs/README.md','docs/research/BASELINE_V1.md','docs/research/MAIN_REVIEW_V2.md',
        'docs/research/MAIN_OPTION_B_V1.md','docs/research/RESEARCH_PROTOCOL_V3.md',
        'docs/research/IMPLEMENTATION_PLAN_V3.md','reports/README.md','reports/completion.md','scripts/README.md'}
    protected = 0
    for name in subprocess.check_output(['git','ls-tree','-r','--name-only',REF],cwd=ROOT).decode().splitlines():
        if name in allowed: continue
        before = subprocess.check_output(['git','show',f'{REF}:{name}'],cwd=ROOT)
        assert before.replace(b'\r\n',b'\n') == (ROOT/name).read_bytes().replace(b'\r\n',b'\n'), name
        protected += 1
    dimensions = [json.loads(line) for line in (ROOT/'reports/audits/2026-11-24/image_dimensions.jsonl').read_text().splitlines()]
    images = list({item['image_path']: item for item in dimensions}.values())
    for item in images: assert sha256_file(ROOT/item['image_path']) == item['image_sha256']
    history = json.loads((ROOT/'reports/validation/repope_image_ab_v1/metrics.json').read_text())['source_files']
    for item in history: assert sha256_file(ROOT/item['path']) == item['sha256']
    old = json.loads((ROOT/'reports/stage1/v11/before_update.json').read_text())['protected_sha256']
    golden = [(p,d) for p,d in old.items() if p.startswith('results/')]
    for path,digest in golden: assert sha256_file(ROOT/path) == digest
    archives = []
    for receipt,key in [('reports/stage1/v12/review_bundle.json','archive'),
                        ('reports/stage1/v11/pilot_bundle.json','output'),
                        ('reports/validation/repope_image_ab_v1/raw_bundle.json','path')]:
        data = json.loads((ROOT/receipt).read_text(encoding='utf-8'))
        assert sha256_file(ROOT/data[key]) == data['sha256']
        archives.append(data[key])
    assert sha256_file(ROOT/'exports/team_workspace_v1.zip') == old['exports/team_workspace_v1.zip']
    archives.append('exports/team_workspace_v1.zip')
    pages = 0
    with zipfile.ZipFile(ROOT/'exports/main_review_v2.zip') as archive:
        for name in archive.namelist():
            if name.endswith('.html'):
                assert sha256_file(ROOT/name) == hashlib.sha256(archive.read(name)).hexdigest()
                pages += 1
    write_json(folder/'verification.json',{'date_local':'2026-11-25','review_sha256':sha256_file(ROOT/REVIEW),
        'reviewed_manifest_sha256':sha256_file(ROOT/IMPORTED),'Pet_approved_under_source_policy':160,
        'Pet_label_counts':dict(Counter(r.ground_truth for r in actual)),'official_annotation_and_image_checks':160,
        'one_user_attestation':True,'human_breed_identification':False,'two_human_reviewers':False,
        'baseline_proof_validated':len(valid),'proof_inputs':[p.relative_to(ROOT).as_posix() for p in inputs],
        'staged_remaining_QA':840,'staged_expected_cells':4000,'cell_ids_and_prompts_unchanged':True,
        'official_main_config_unchanged':True,'official_draft_still_pending':1000,'execute_attempts':calls,
        'reference_commit':REF,'old_git_files_preserved_outside_authorized_delta':protected,
        'source_JPEG_hashes_matched':len(images),'historical_raw_files_matched':len(history)+len(golden),
        'original_review_HTML_matched':pages,'private_archives_preserved':archives,
        'main_frozen':False,'M1':'IN_PROGRESS','M2':'PENDING','M3':'NOT_RUN','new_GPU_generations':0})
    print(json.dumps({'Pet':160,'remaining_QA':840,'expected_cells':4000,'original_files_preserved':protected,
        'JPEG_hashes_matched':len(images),'main_execution':'blocked before environment/models'}))


if __name__ == '__main__': main()
