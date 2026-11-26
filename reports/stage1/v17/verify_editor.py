"""Verify the actual exported pending editor and source preservation; no human saves or inference."""
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from vlmbench.io_utils import sha256_file,write_json
from vlmbench.review_adjudication import source_context,validate_payload


def main():
    folder=Path(__file__).resolve().parent
    receipt=json.loads((folder/'export.json').read_text(encoding='utf-8'))
    path=ROOT/receipt['html']
    assert sha256_file(path)==receipt['sha256']
    html=path.read_text(encoding='utf-8')
    payload=json.loads(re.search(r'<script type="application/json" id="payload">([\s\S]*?)</script>',html)[1])
    context,cards=source_context(ROOT,cases_path='reports/stage1/v16/needs_resolution.json',
        summary_path='reports/stage1/v16/aggregation.json',manifest_path='data/main/reviewed_final_v1/main_reviewed.csv')
    assert receipt['context']==context
    summary=validate_payload(payload['review'],context,cards)
    assert summary['status']=={'pending':28} and not summary['complete']
    assert len(payload['cards'])==len(cards)==28
    for rendered,source in zip(payload['cards'],cards):
        assert rendered['sample_id']==source['sample_id']
        raw=base64.b64decode(rendered['image'].split(',',1)[1])
        assert hashlib.sha256(raw).hexdigest()==source['image_sha256']
    script=re.search(r'<script>\s*([\s\S]*?)</script>',html)[1]
    check=subprocess.run(['node','--check'],input=script,text=True,capture_output=True,encoding='utf-8')
    assert check.returncode==0,check.stderr
    old=json.loads((ROOT/'reports/stage1/v16/resolution_report.json').read_text())
    assert sha256_file(ROOT/old['private_HTML'])==old['html_sha256']
    reference='866d100ff3ef73c3c5f9e2b96eac41da1ca3242d'
    allowed={'pyproject.toml','README.md','docs/README.md','reports/README.md','scripts/README.md',
        'docs/research/MAIN_REVIEW_V2.md','reports/completion.md'}
    count=0
    for name in subprocess.check_output(['git','ls-tree','-r','--name-only',reference],cwd=ROOT).decode().splitlines():
        if name in allowed:continue
        blob=subprocess.check_output(['git','show',f'{reference}:{name}'],cwd=ROOT)
        assert blob.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),name
        count+=1
    write_json(folder/'verification.json',{'date_local':'2026-11-26','html_sha256':receipt['sha256'],
        'actual_export_rows':28,'initial_pending':28,'initial_resolved':0,'original_JPEGs_embedded_exactly':28,
        'context_matches_current_sources':True,'source_file_hashes_verified':len(context['source_files_sha256']),
        'generated_JS_syntax_check':'node --check passed','reference_commit':reference,
        'old_git_files_preserved_outside_authorized_delta':count,'old_readonly_HTML_preserved':True,
        'source_review_JSON_and_labels_preserved':True,'new_real_human_decisions':0,'new_main_imports':0,
        'new_model_generations':0,'main_frozen':False,'M1':'IN_PROGRESS_28','M2':'PENDING','M3':'NOT_RUN',
        'UI_verification_scope':'real inline handlers with synthetic minimal DOM; no visual browser QA'})
    print(json.dumps({'pending_cases':28,'original_images_exact':28,'old_git_files_preserved':count,'actual_decisions_created':0}))


if __name__=='__main__':main()
