"""Build one private Phase-A master and four thin member ZIPs; never publishes or runs inference."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import zipfile

from vlmbench.baseline_contract import build_plan
from vlmbench.io_utils import atomic_bytes,sha256_file,write_json
from vlmbench.reviews import canonical_hash
from vlmbench.team_handoff import ASSET_SCHEMA,MAX_EXPANDED,ROLES,verify_bundle

ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs/team_inference_v1'
PREFIX='VLM_ENVI_Main_Inference_Team_v1'
MEMBERS={'TV1':'TV1_QWEN_EN','TV2':'TV2_QWEN_VI','TV3':'TV3_GEMMA_EN','TV4':'TV4_GEMMA_VI'}
SUFFIXES={'.py','.cjs','.md','.txt','.toml','.yaml','.yml','.json','.jsonl','.csv','.html','.ipynb','.ps1'}


def json_bytes(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')


def add_zip(archive,name,raw,compressed=True):
    info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
    archive.writestr(info,raw,compress_type=zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED,compresslevel=6 if compressed else None)


def project_paths():
    raw=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT)
    paths=[]
    for name in sorted(set(raw.decode('utf-8').split('\0'))):
        if not name:continue
        p=ROOT/name
        if not p.is_file():continue
        if name.startswith(('data/raw/','data/external_images/','exports/','results/','.git/','.venv','.cache/',
                            'reports/maintenance/','reports/stage1/v24/')):continue
        if '__pycache__' in p.parts or p.is_symlink():raise ValueError('Unexpected cache/symlink in source candidate')
        if p.suffix.lower() not in SUFFIXES and p.name not in {'.gitignore','.gitattributes','LICENSE'}:continue
        if p.name.startswith('.env') or p.stat().st_size>5*1024**2:raise ValueError('Unsafe/oversize source candidate: '+name)
        paths.append(name)
    return paths


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',default='reports/stage1/v24/bundle_build.json')
    args=parser.parse_args();report=(ROOT/args.report).resolve()
    archive_path=ROOT/'exports/VLM_ENVI_Main_Inference_Team_v1.zip'
    member_paths={r:ROOT/f'hướng dẫn thực nghiệm/{name}_Package.zip' for r,name in MEMBERS.items()}
    if not report.is_relative_to(ROOT) or report.exists() or archive_path.exists() or any(p.exists() for p in member_paths.values()):
        raise ValueError('Preserve existing artifacts; choose a new handoff version')
    plan=build_plan(ROOT,ROOT/'configs/baseline_v3_final_v1.yaml')
    if plan.issues:raise ValueError('Historical verified local source protocol changed before packaging')
    spec=importlib.util.spec_from_file_location('repository_check',ROOT/'scripts/check_repository.py')
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    paths=project_paths();audit=checker.audit(ROOT,paths)
    if not audit['ready']:raise ValueError('Source credential/artifact audit failed; inspect local candidate set')
    files={};project_hashes={}
    for name in paths:
        raw=(ROOT/name).read_bytes()
        if (ROOT/name).suffix=='.ipynb':
            notebook=json.loads(raw)
            if any(c.get('outputs') or c.get('execution_count') is not None for c in notebook['cells'] if c['cell_type']=='code'):
                raise ValueError('Notebook outputs must be cleared')
        files['project/'+name]=raw;project_hashes[name]=hashlib.sha256(raw).hexdigest()
    for path in DOC.rglob('*'):
        if path.is_file():files[path.relative_to(DOC).as_posix()]=path.read_bytes()
    for platform in ('colab','kaggle'):
        name=f'main_{platform}_starter.ipynb'
        files['shared/notebooks/'+name]=(ROOT/'notebooks'/name).read_bytes()
    for role,member in MEMBERS.items():
        if files[f'members/{member}/assignment_config.yaml']!=(ROOT/f'configs/team_assignments_v1/{role}.yaml').read_bytes():
            raise ValueError('Member config differs from shared source assignment')
    asset_paths={r.image_path:r.image_sha256 for r in plan.rows}
    for name,digest in plan.protocol['inputs_sha256'].items():
        if name.startswith('data/raw/'):asset_paths[name]=digest
    assets={}
    for name,digest in sorted(asset_paths.items()):
        path=ROOT/name
        if path.is_symlink() or sha256_file(path)!=digest:raise ValueError('Approved asset bytes differ')
        assets[name]={'sha256':digest,'bytes':path.stat().st_size}
    bindings={n:sha256_file(ROOT/n) for n in ['data/main/adjudicated_confirmed_v1/main_reviewed.csv',
        'data/main/preparation_v2/all_candidates.jsonl','data/pilot/stage1_qa_v1/pilot_manifest.csv']}
    asset_meta={'schema_version':ASSET_SCHEMA,'scope':'private approved main images and source provenance; no model weights',
        'unique_main_images':783,'approved_manifest':'data/main/adjudicated_confirmed_v1/main_reviewed.csv','bindings':bindings,'files':assets}
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as inner:
        for name in sorted(assets):add_zip(inner,name,(ROOT/name).read_bytes())
        add_zip(inner,'MAIN_ASSETS.json',json_bytes(asset_meta))
    files['main_assets/main_assets_v1.zip']=buffer.getvalue()
    files['main_assets/README.md']=('Private team assets only. 783 approved main JPEGs plus two pinned source inputs.\n'
        'Do not upload publicly; use a private Dataset only with appropriate team access.\n'
        'Restore via project/scripts/main_team_bundle.py restore-assets; conflicts are never overwritten.\n').encode()
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
    dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT))
    meta={'schema_version':'main_team_handoff_v1','phase':'A_DEVELOPMENT_HANDOFF_NOT_PHASE_B_RELEASE',
        'source_git_head':head,'source_dirty':dirty,'pinned_phase_b_commit':None,
        'historical_local_protocol_hash':plan.protocol_hash,'project_source_sha256':project_hashes,
        'project_source_digest':canonical_hash(project_hashes),'private_assets':True,
        'asset_images':783,'asset_files':len(assets),'contains_model_weights':False,'contains_credentials':False,
        'cloud_generation_verified':False,'language_sharding_implemented':False,
        'files':{n:{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)} for n,b in sorted(files.items())}}
    if sum(len(b) for b in files.values())>MAX_EXPANDED:raise ValueError('Expanded handoff budget exceeded')
    archive_path.parent.mkdir(parents=True,exist_ok=True)
    temp=archive_path.with_suffix('.zip.partial')
    if temp.exists():raise ValueError('Preserve previous partial ZIP')
    with zipfile.ZipFile(temp,'w') as archive:
        for name,raw in sorted(files.items()):add_zip(archive,PREFIX+'/'+name,raw,compressed=not name.endswith('.zip'))
        add_zip(archive,PREFIX+'/BUNDLE_MANIFEST.json',json_bytes(meta))
    temp.replace(archive_path)
    verified=verify_bundle(archive_path)
    master_sha=sha256_file(archive_path)
    thin=[]
    for role,member in MEMBERS.items():
        member_paths[role].parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(member_paths[role],'w') as archive:
            for name,raw in sorted(files.items()):
                if name.startswith('members/'+member+'/') or name.startswith('github/'):
                    add_zip(archive,member+'/'+name,raw)
            ref={'master_archive':archive_path.name,'master_sha256':master_sha,'project_source_digest':meta['project_source_digest'],
                'role':role,'member_folder':'members/'+member,'requires_shared_master':True,'contains_separate_source_copy':False}
            add_zip(archive,member+'/SHARED_BUNDLE_REF.json',json_bytes(ref))
            add_zip(archive,member+'/START_HERE.md',(f'# {role}\n\nGiải nén master {archive_path.name} có SHA256 `{master_sha}`.\n'
                f'Mở members/{member}/START_{role}.md trong master; dùng cùng project/shared/main_assets.\n'
                'ZIP này không có source/assets riêng; không thay thế master, không phải Phase-B release.\n').encode('utf-8'))
        thin.append({'role':role,'archive':member_paths[role].relative_to(ROOT).as_posix(),
            'sha256':sha256_file(member_paths[role]),'bytes':member_paths[role].stat().st_size})
    write_json(report,{'archive':archive_path.relative_to(ROOT).as_posix(),'sha256':master_sha,'bytes':archive_path.stat().st_size,
        'verified':verified,'source_files':len(paths),'unique_main_images':783,'asset_files':len(assets),
        'asset_sha256':hashlib.sha256(files['main_assets/main_assets_v1.zip']).hexdigest(),
        'source_git_head':head,'source_dirty':dirty,'project_source_digest':meta['project_source_digest'],
        'phase_b_ready':False,'cloud_GPU_verified':False,'raw_model_inferences_run':0,
        'member_packages':thin,'credential_audit_ready':audit['ready'],'private_only':True})
    print(json.dumps({'archive':str(archive_path),'MiB':round(archive_path.stat().st_size/1024**2,2),
        'sha256':master_sha,'member_packages':len(thin),'phase_b_ready':False},indent=2))


if __name__=='__main__':main()
