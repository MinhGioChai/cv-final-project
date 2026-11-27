"""Phase-A assignment planning and integrity checks, separate from frozen inference."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path,PurePosixPath
import stat
import zipfile

from pydantic import BaseModel,ConfigDict,Field,model_validator
import yaml

from .io_utils import atomic_bytes,sha256_file
from .reviews import canonical_hash

ROLES={
    'TV1':('qwen','en','colab','work/main-qwen-en'),
    'TV2':('qwen','vi','kaggle','work/main-qwen-vi'),
    'TV3':('gemma','en','colab','work/main-gemma-en'),
    'TV4':('gemma','vi','kaggle','work/main-gemma-vi'),
}
ASSET_SCHEMA='main_team_private_assets_v1'
MAX_EXPANDED=500*1024**2


class Assignment(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    schema_version: str=Field(pattern='^main_team_assignment_v1$')
    role: str
    model: str
    language: str
    preferred_platform: str
    branch: str
    expected_cells: int
    audit_protocol: str
    phase_b_protocol: str
    release_record: str
    bf16_fallback: str | None=None

    @model_validator(mode='after')
    def assignment_matches(self):
        if self.role not in ROLES or (self.model,self.language,self.preferred_platform,self.branch)!=ROLES[self.role]:
            raise ValueError('Assignment differs from the four user-defined roles')
        if self.expected_cells!=1000:raise ValueError('Each model-language shard must contain exactly 1,000 cells')
        if self.role=='TV4' and self.bf16_fallback!='verified_bf16_environment':
            raise ValueError('TV4 requires an explicitly verified BF16 alternative, not FP16 fallback')
        return self


def inside(root,name):
    target=(root/name).resolve()
    if not target.is_relative_to(root.resolve()):raise ValueError('Path outside workspace')
    return target


def assignment_plan(root,path):
    from .baseline_contract import build_plan
    root=root.resolve();assignment=Assignment.model_validate(yaml.safe_load(inside(root,path).read_text(encoding='utf-8')))
    plan=build_plan(root,inside(root,assignment.audit_protocol))
    selected=[c for c in plan.cells if c.model==assignment.model and c.language==assignment.language]
    if len(plan.cells)!=4000 or len(selected)!=1000:raise ValueError('Assignment does not match the complete main grid')
    if len({c.cell_id for c in selected})!=1000:raise ValueError('Duplicate assignment cells')
    lookup={r.sample_id:r for r in plan.rows}
    return {'scope':'Phase_A_assignment_plan_not_inference','role':assignment.role,'model':assignment.model,
        'language':assignment.language,'platform':assignment.preferred_platform,'expected_cells':1000,
        'full_grid_cells':4000,'cell_ids':[c.cell_id for c in selected],
        'tasks':dict(Counter(lookup[c.sample_id].task for c in selected)),
        'historical_local_protocol_hash':plan.protocol_hash,'historical_protocol_gates':plan.summary()['blocking_counts'],
        'phase_b_execution_ready':False,
        'phase_b_blockers':['TV1 language sharding PR not integrated','Common pinned code/release and implementation freeze v2 not approved',
            'Role cloud setup, assets and GPU smoke not yet verified'],
        'no_inference_calls':True}


def asset_name_allowed(name):
    p=PurePosixPath(name)
    return bool(name and not p.is_absolute() and '..' not in p.parts and '\\' not in name and ':' not in name
        and name.startswith('data/raw/') and (p.suffix.lower() in {'.jpg','.json'} or name.endswith('/pet_annotations.tar.gz')))


def restore_assets(root,archive_path):
    """Validate every member/conflict before restoring only the approved asset allowlist."""
    root=root.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)) or 'MAIN_ASSETS.json' not in names:raise ValueError('Missing/duplicate asset index')
        meta=json.loads(archive.read('MAIN_ASSETS.json'))
        if meta.get('schema_version')!=ASSET_SCHEMA:raise ValueError('Unknown main asset bundle')
        files=meta.get('files',{})
        if not isinstance(files,dict) or not files or set(names)!=set(files)|{'MAIN_ASSETS.json'}:
            raise ValueError('Unexpected or missing archive members')
        if sum(i.file_size for i in archive.infolist())>MAX_EXPANDED:raise ValueError('Expanded asset budget exceeded')
        for name,digest in meta['bindings'].items():
            if sha256_file(inside(root,name))!=digest:raise ValueError('Assets belong to another approved manifest/source selection')
        manifest=meta.get('approved_manifest')
        if manifest not in meta['bindings']:raise ValueError('Approved manifest must be bound before asset restore')
        with inside(root,manifest).open(encoding='utf-8-sig',newline='') as handle:
            approved_images={r['image_path']:r['image_sha256'] for r in csv.DictReader(handle)}
        archived_images={n:r['sha256'] for n,r in files.items() if PurePosixPath(n).suffix.lower()=='.jpg'}
        if approved_images!=archived_images or len(approved_images)!=meta.get('unique_main_images'):
            raise ValueError('JPEG paths/hashes differ from the approved manifest')
        for name,record in files.items():
            info=archive.getinfo(name);target=inside(root,name)
            if not asset_name_allowed(name) or stat.S_ISLNK(info.external_attr>>16):raise ValueError('Unsafe asset path/type')
            if info.file_size!=record['bytes'] or hashlib.sha256(archive.read(name)).hexdigest()!=record['sha256']:
                raise ValueError('Asset hash/size mismatch')
            if target.exists() and sha256_file(target)!=record['sha256']:raise ValueError('Existing asset differs; no overwrite')
        written=0
        for name in files:
            target=root/name
            if not target.exists():atomic_bytes(target,archive.read(name));written+=1
    return {'verified_files':len(files),'restored_files':written,'existing_identical':len(files)-written,
        'network_calls':0,'inference_calls':0}


def verify_bundle(archive_path):
    """Verify the whole private master without executing or extracting project code."""
    prefix='VLM_ENVI_Main_Inference_Team_v1/'
    with zipfile.ZipFile(archive_path) as archive:
        names=archive.namelist();index=prefix+'BUNDLE_MANIFEST.json'
        if len(names)!=len(set(names)) or index not in names:raise ValueError('Missing/duplicate master index')
        meta=json.loads(archive.read(index))
        if meta.get('schema_version')!='main_team_handoff_v1':raise ValueError('Unknown handoff schema')
        if sum(i.file_size for i in archive.infolist())>MAX_EXPANDED:raise ValueError('Expanded master budget exceeded')
        expected={prefix+n for n in meta['files']}|{index}
        if set(names)!=expected:raise ValueError('Master entry set differs')
        for name,record in meta['files'].items():
            p=PurePosixPath(name);info=archive.getinfo(prefix+name)
            if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name or stat.S_ISLNK(info.external_attr>>16):
                raise ValueError('Unsafe master member')
            if info.file_size!=record['bytes'] or hashlib.sha256(archive.read(prefix+name)).hexdigest()!=record['sha256']:
                raise ValueError('Master hash/size mismatch')
        if canonical_hash(meta['project_source_sha256'])!=meta['project_source_digest']:raise ValueError('Source snapshot fingerprint differs')
    return {'verified_files':len(meta['files']),'master_sha256':sha256_file(archive_path),
        'phase':meta['phase'],'phase_b_ready':False,'private_assets':True,'project_source_digest':meta['project_source_digest']}
