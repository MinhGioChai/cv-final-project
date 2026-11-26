"""CPU source preservation, strict replay and closed main gates; no model imports/generation."""
import base64
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import yaml

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from vlmbench.baseline_contract import build_plan
from vlmbench.baseline_runtime import run_main
from vlmbench.io_utils import read_manifest,sha256_file,write_json
from vlmbench.review_aggregation import aggregate

REFERENCE='52cbdd8'


class Images(HTMLParser):
    def __init__(self):super().__init__();self.images=[]
    def handle_starttag(self,tag,attrs):
        if tag=='img':self.images.append(dict(attrs)['src'])


def main():
    folder=Path(__file__).resolve().parent
    merged=read_manifest(ROOT/'data/main/reviewed_final_v1/main_reviewed.csv')
    rows,replay,cases=aggregate(ROOT,config_path='configs/baseline_v3_option_b_v1.yaml',input_dir='reviewed_final',
        packet_dir='data/reviews/main_review_v2',pet_manifest='data/main/reviewed_pet_source_v1/oxford_pet_reviewed.csv',operator='codex_review_aggregation')
    assert rows==merged and replay['accepted_total']==972 and len(cases)==28
    original=build_plan(ROOT,ROOT/'configs/baseline_v3_option_b_v1.yaml')
    cfg=original.config.model_dump();cfg['manifests']=['data/main/reviewed_final_v1/main_reviewed.csv']
    fixture=folder/'aggregation_preflight.yaml'
    text='# CPU aggregation integration only; not an approved final/main config.\n'+yaml.safe_dump(cfg,sort_keys=False)
    if fixture.exists():assert fixture.read_text(encoding='utf-8')==text
    else:fixture.write_text(text,encoding='utf-8')
    plan=build_plan(ROOT,fixture)
    assert plan.summary()['blocking_counts']=={'MAIN_QA_NOT_APPROVED':28,'BASELINE_NOT_FROZEN':1,'FREEZE_RECEIPT_REQUIRED':1}
    assert len(plan.cells)==4000 and not plan.summary()['execution_ready']
    assert [c.cell_id for c in plan.cells]==[c.cell_id for c in original.cells]
    changed_en=sum(a.prompt_hash!=b.prompt_hash for a,b in zip(plan.cells,original.cells) if a.language=='en')
    changed_vi=sum(a.prompt_hash!=b.prompt_hash for a,b in zip(plan.cells,original.cells) if a.language=='vi')
    assert changed_en==0 and changed_vi==70
    attempts=[]
    def forbidden():raise AssertionError('Environment/models must remain behind main QA/freeze')
    for model in ['qwen','gemma']:
        output=f'results/main/review_aggregation_v1/{model}_blocked.jsonl'
        try:run_main(plan,alias=model,run_id='review_aggregation_v1',platform_name='local',output=output,
            execute=True,smoke_per_task=1,environment_provider=forbidden)
        except ValueError as exc:
            assert str(exc).startswith('Main execution blocked:')
            assert not (ROOT/output).exists() and not (ROOT/output).with_suffix('.meta.json').exists()
            attempts.append({'model':model,'blocked_before_environment_model':True,'reason':str(exc)})
        else:raise AssertionError('Main execution must be blocked')
    write_json(folder/'preflight.json',plan.summary())
    source=json.loads((folder/'aggregation.json').read_text(encoding='utf-8'))
    for path,digest in source['inputs_sha256'].items():assert sha256_file(ROOT/path)==digest,path
    dimensions=[json.loads(line) for line in (ROOT/'reports/audits/2026-11-24/image_dimensions.jsonl').read_text().splitlines()]
    images={r['image_path']:r['image_sha256'] for r in dimensions}
    for path,digest in images.items():assert sha256_file(ROOT/path)==digest,path
    hist=json.loads((ROOT/'reports/validation/repope_image_ab_v1/metrics.json').read_text())['source_files']
    for item in hist:assert sha256_file(ROOT/item['path'])==item['sha256']
    before=json.loads((ROOT/'reports/stage1/v11/before_update.json').read_text())['protected_sha256']
    golden=[(p,d) for p,d in before.items() if p.startswith('results/')]
    for path,digest in golden:assert sha256_file(ROOT/path)==digest
    archive_receipts=[('reports/stage1/v12/review_bundle.json','archive'),('reports/stage1/v11/pilot_bundle.json','output'),
        ('reports/validation/repope_image_ab_v1/raw_bundle.json','path')]
    for report,key in archive_receipts:
        receipt=json.loads((ROOT/report).read_text(encoding='utf-8'))
        assert sha256_file(ROOT/receipt[key])==receipt['sha256']
    assert sha256_file(ROOT/'exports/team_workspace_v1.zip')==before['exports/team_workspace_v1.zip']
    pages=0
    with zipfile.ZipFile(ROOT/'exports/main_review_v2.zip') as archive:
        for name in archive.namelist():
            if name.endswith('.html'):
                assert sha256_file(ROOT/name)==hashlib.sha256(archive.read(name)).hexdigest();pages+=1
    parser=Images();parser.feed((ROOT/'exports/main_review_resolution_v1.html').read_text(encoding='utf-8'))
    assert len(parser.images)==len(cases)==28
    for src,case in zip(parser.images,cases):
        assert src.startswith('data:image/jpeg;base64,')
        assert hashlib.sha256(base64.b64decode(src.split(',',1)[1])).hexdigest()==case['image_sha256']
    # Retain the five input edits that were already present when this task began.
    input_edits={f'reviewed_final/repope_{i:02d}_reviewed_v2.json' for i in range(1,6)}
    allowed={'reports/completion.md','README.md','scripts/README.md','docs/README.md','reports/README.md',
        'docs/research/MAIN_REVIEW_V2.md','docs/research/RESEARCH_PROTOCOL_V3.md','docs/research/IMPLEMENTATION_PLAN_V3.md'}|input_edits
    preserved=0
    for name in subprocess.check_output(['git','ls-tree','-r','--name-only',REFERENCE],cwd=ROOT).decode().splitlines():
        if name in allowed:continue
        old=subprocess.check_output(['git','show',f'{REFERENCE}:{name}'],cwd=ROOT)
        assert old.replace(b'\r\n',b'\n')==(ROOT/name).read_bytes().replace(b'\r\n',b'\n'),name
        preserved+=1
    write_json(folder/'verification.json',{'date_local':'2026-11-26','reference_commit':REFERENCE,'strict_replay_rows':len(rows),
        'source_reviews_hash_verified':source['submitted_packets'],'original_source_fields_preserved':True,
        'source_labels_changed':0,'approved_total':972,'needs_resolution':28,'expected_cells':4000,
        'cell_ids_unchanged':True,'EN_prompts_changed':changed_en,'VI_prompts_changed':changed_vi,
        'VI_texts_changed':35,'VI_texts_changed_and_fully_approved':sum(d['translation_changed'] and d['accepted'] for d in replay['row_index']),
        'main_preflight_blocking_counts':plan.summary()['blocking_counts'],'blocked_attempts':attempts,
        'source_JPEG_hashes_verified':len(images),'historical_raw_files_verified':len(hist)+len(golden),
        'original_review_HTML_preserved':pages,'old_private_archives_preserved':4,
        'private_resolution_HTML_embeds_exact_source_JPEGs':28,'old_git_files_preserved':preserved,
        'preexisting_user_input_edits_preserved':sorted(input_edits),'new_human_approvals_created':0,
        'main_config_unchanged':True,'M1':'IN_PROGRESS','M2':'PENDING','M3':'NOT_RUN','new_model_generations':0})
    print(json.dumps({'rows':len(rows),'accepted':972,'unresolved':28,'main_gates':'closed','source_images':len(images),
        'protected_git_files':preserved,'private_HTML_exact_images':28,'new_generations':0}))


if __name__=='__main__':main()
