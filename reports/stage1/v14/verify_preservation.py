"""Verify authorized code/docs delta and unchanged data/reviews/history; CPU read-only inputs."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[3]
REF='1a253f6dc94e4432f657493241daa28d9d4d5f11'
sys.path.insert(0,str(ROOT/'src'))
from vlmbench.io_utils import sha256_file,write_json
import yaml


def main():
    allowed={'README.md','HUONG_DAN_NHOM.md','docs/README.md','reports/README.md','scripts/README.md','reports/completion.md',
        'docs/research/BASELINE_V1.md','docs/research/RESEARCH_PROTOCOL_V3.md','docs/research/IMPLEMENTATION_PLAN_V3.md',
        'src/vlmbench/baseline_contract.py','src/vlmbench/baseline_runtime.py','scripts/run_main.py','tests/test_baseline.py'}
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only',REF],cwd=ROOT).decode().splitlines()
    unchanged=0;EOL=[];review_files=0
    for relative in paths:
        if relative in allowed:continue
        old=subprocess.check_output(['git','show',f'{REF}:{relative}'],cwd=ROOT)
        current=(ROOT/relative).read_bytes()
        if old!=current:
            assert old.replace(b'\r\n',b'\n')==current.replace(b'\r\n',b'\n'),relative
            EOL.append(relative)
        unchanged+=1
        if relative.startswith('data/reviews/main_review_v2/'):review_files+=1
    dims=[json.loads(line) for line in (ROOT/'reports/audits/2026-11-24/image_dimensions.jsonl').read_text().splitlines()]
    images={r['image_path']:r['image_sha256'] for r in dims}
    for relative,digest in images.items():assert sha256_file(ROOT/relative)==digest,relative
    raw=json.loads((ROOT/'reports/validation/repope_image_ab_v1/metrics.json').read_text(encoding='utf-8'))['source_files']
    for item in raw:assert sha256_file(ROOT/item['path'])==item['sha256'],item['path']
    before=json.loads((ROOT/'reports/stage1/v11/before_update.json').read_text())['protected_sha256']
    gold=[(p,d) for p,d in before.items() if p.startswith('results/')]
    for path,digest in gold:assert sha256_file(ROOT/path)==digest,path
    zip_checks=[]
    for receipt,key in [('reports/stage1/v12/review_bundle.json','archive'),
                        ('reports/stage1/v11/pilot_bundle.json','output'),
                        ('reports/validation/repope_image_ab_v1/raw_bundle.json','path')]:
        source=json.loads((ROOT/receipt).read_text(encoding='utf-8'))
        path=ROOT/source[key]
        if path.exists():
            assert sha256_file(path)==source['sha256'],str(path)
            zip_checks.append({'path':source[key],'sha256_matches_historical_receipt':True})
    workspace=ROOT/'exports/team_workspace_v1.zip'
    if workspace.exists():
        assert sha256_file(workspace)==before['exports/team_workspace_v1.zip']
        zip_checks.append({'path':'exports/team_workspace_v1.zip','sha256_matches_historical_receipt':True})
    html=0
    archive=ROOT/'exports/main_review_v2.zip'
    if archive.exists():
        with zipfile.ZipFile(archive) as zipped:
            for name in zipped.namelist():
                if name.endswith('.html'):
                    assert sha256_file(ROOT/name)==hashlib.sha256(zipped.read(name)).hexdigest(),name
                    html+=1
    a=yaml.safe_load((ROOT/'configs/baseline_v3_draft.yaml').read_text(encoding='utf-8'))
    b=yaml.safe_load((ROOT/'configs/baseline_v3_option_b_v1.yaml').read_text(encoding='utf-8'))
    assert {key for key in a if a[key]!=b[key]}=={'experiment_id','preprocess'}
    assert {key for key in a['preprocess'] if a['preprocess'][key]!=b['preprocess'][key]}=={'policy_id','image_max_edge'}
    assert b['frozen'] is False and b['freeze_receipt'] is None
    links=0
    for relative in ['README.md','HUONG_DAN_NHOM.md','docs/README.md','scripts/README.md','reports/README.md',
        'reports/completion.md','docs/research/MAIN_OPTION_B_V1.md','docs/research/RESEARCH_PROTOCOL_V3.md',
        'docs/research/IMPLEMENTATION_PLAN_V3.md','docs/research/BASELINE_V1.md','reports/stage1/v14/completion.md']:
        path=ROOT/relative
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if target.startswith(('http:','https:','#','mailto:')):continue
            if target=='preservation.json' and relative=='reports/stage1/v14/completion.md':continue
            assert (path.parent/target.split('#')[0]).exists(),(relative,target)
            links+=1
    for name in ['src/vlmbench/baseline_contract.py','src/vlmbench/baseline_runtime.py','scripts/run_main.py','tests/test_baseline.py']:
        ast.parse((ROOT/name).read_text(encoding='utf-8'))
    write_json(Path(__file__).with_name('preservation.json'),{'reference_commit':REF,
        'prior_git_files_unchanged_outside_authorized_delta':unchanged,'EOL_only_vs_Git':EOL,
        'authorized_existing_file_delta':sorted(allowed),'source_images_hash_matched':len(images),
        'historical_diagnostic_files_hash_matched':len(raw),'legacy_pilot_raw_hash_matched':len(gold),
        'review_v2_JSON_CSV_unchanged':review_files,'review_HTML_matches_original_archive':html,
        'private_archives':zip_checks,'local_links_checked':links,'only_candidate_changes':['experiment_id','preprocess.policy_id','preprocess.image_max_edge'],
        'human_review_or_data_changed':False,'source_JPEG_changed':False,'main_freeze_created':False,
        'main_GPU_smoke_executed':False,'new_model_generation_calls':0})
    print(json.dumps({'old_files_unchanged':unchanged,'images':len(images),'raw_history_files':len(raw)+len(gold),
        'review_packets_files':review_files,'HTML':html,'archives':len(zip_checks),'links':links}))


if __name__=='__main__':main()
