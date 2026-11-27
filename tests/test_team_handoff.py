"""Synthetic assets/assignment plans only; no student authors, cloud runs or inference fabricated."""
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest
import yaml

from vlmbench.io_utils import sha256_file
from vlmbench.reviews import canonical_hash
from vlmbench.team_handoff import (Assignment,ROLES,ASSET_SCHEMA,assignment_plan,restore_assets,verify_bundle)

REPO=Path(__file__).resolve().parents[1]


def assignment(role):
    model,language,platform,branch=ROLES[role]
    return dict(schema_version='main_team_assignment_v1',role=role,model=model,language=language,
        preferred_platform=platform,branch=branch,expected_cells=1000,audit_protocol='audit.yaml',
        phase_b_protocol='future.yaml',release_record='future.json',
        bf16_fallback='verified_bf16_environment' if role=='TV4' else None)


def test_four_assignments_are_disjoint_cover_4000_and_never_execute(tmp_path,monkeypatch):
    cells=[SimpleNamespace(model=m,language=l,sample_id=str(i),cell_id=f'synthetic_{m}_{l}_{i}')
        for m in ['qwen','gemma'] for l in ['en','vi'] for i in range(1000)]
    rows=[SimpleNamespace(sample_id=str(i),task='object_existence' if i<600 else 'spatial' if i<720 else 'counting' if i<840 else 'fine_grained') for i in range(1000)]
    fake=SimpleNamespace(cells=cells,rows=rows,protocol_hash='a'*64,summary=lambda:{'blocking_counts':{}})
    monkeypatch.setattr('vlmbench.baseline_contract.build_plan',lambda *_:fake)
    sets=[]
    for role in ROLES:
        path=tmp_path/f'{role}.yaml';path.write_text(yaml.safe_dump(assignment(role)))
        result=assignment_plan(tmp_path,path)
        assert result['expected_cells']==1000 and result['full_grid_cells']==4000
        assert result['tasks']=={'object_existence':600,'spatial':120,'counting':120,'fine_grained':160}
        assert not result['phase_b_execution_ready'] and result['no_inference_calls']
        sets.append(set(result['cell_ids']))
    assert len(set.union(*sets))==4000 and sum(len(s) for s in sets)==4000
    assert all(not a&b for i,a in enumerate(sets) for b in sets[i+1:])


@pytest.mark.parametrize('mutation',[{'language':'both'},{'expected_cells':2000},{'model':'gemma'},{'branch':'main'}])
def test_assignment_scope_cannot_silently_change(mutation):
    raw=assignment('TV1');raw.update(mutation)
    with pytest.raises(ValueError):Assignment.model_validate(raw)


def test_tv4_requires_verified_bf16_fallback():
    raw=assignment('TV4');raw['bf16_fallback']=None
    with pytest.raises(ValueError):Assignment.model_validate(raw)


def make_assets(root,files=None,bindings=None):
    files=files or {'data/raw/synthetic/a.jpg':b'synthetic image A','data/raw/synthetic/b.jpg':b'synthetic image B'}
    (root/'approved.csv').write_text('image_path,image_sha256\n'+''.join(f'{n},{hashlib.sha256(raw).hexdigest()}\n' for n,raw in files.items() if n.endswith('.jpg')),encoding='utf-8')
    index={'schema_version':ASSET_SCHEMA,'approved_manifest':'approved.csv','unique_main_images':sum(n.endswith('.jpg') for n in files),
        'bindings':bindings or {'approved.csv':sha256_file(root/'approved.csv')},
        'files':{n:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for n,raw in files.items()}}
    archive=root/'assets.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for n,raw in files.items():z.writestr(n,raw)
        z.writestr('MAIN_ASSETS.json',json.dumps(index))
    return archive,index


def test_assets_restore_exact_bytes_and_identical_rerun(tmp_path):
    archive,index=make_assets(tmp_path)
    first=restore_assets(tmp_path,archive);second=restore_assets(tmp_path,archive)
    assert first['restored_files']==2 and second['restored_files']==0 and second['existing_identical']==2
    assert first['network_calls']==first['inference_calls']==0
    for name,record in index['files'].items():assert sha256_file(tmp_path/name)==record['sha256']


def test_assets_preflight_conflicts_before_first_write(tmp_path):
    archive,_=make_assets(tmp_path)
    conflict=tmp_path/'data/raw/synthetic/b.jpg';conflict.parent.mkdir(parents=True);conflict.write_bytes(b'changed')
    with pytest.raises(ValueError,match='no overwrite'):restore_assets(tmp_path,archive)
    assert not (tmp_path/'data/raw/synthetic/a.jpg').exists() and conflict.read_bytes()==b'changed'


@pytest.mark.parametrize('name',['../escape.jpg','data/raw/../../escape.jpg','data/raw\\escape.jpg','data/raw/c:escape.jpg','data/raw/model.safetensors'])
def test_assets_reject_unsafe_members(tmp_path,name):
    archive,_=make_assets(tmp_path,{name:b'synthetic'})
    with pytest.raises(ValueError):restore_assets(tmp_path,archive)


def test_assets_reject_wrong_binding_or_bad_hash(tmp_path):
    archive,_=make_assets(tmp_path)
    (tmp_path/'approved.csv').write_bytes(b'changed source')
    with pytest.raises(ValueError,match='another approved'):restore_assets(tmp_path,archive)
    archive,index=make_assets(tmp_path)
    index['files']['data/raw/synthetic/a.jpg']['sha256']='0'*64
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('MAIN_ASSETS.json',json.dumps(index))
        z.writestr('data/raw/synthetic/a.jpg',b'synthetic image A');z.writestr('data/raw/synthetic/b.jpg',b'synthetic image B')
    with pytest.raises(ValueError,match='mismatch|approved manifest'):restore_assets(tmp_path,archive)


def test_master_hashes_reject_corruption(tmp_path):
    prefix='VLM_ENVI_Main_Inference_Team_v1/'
    file=b'synthetic safe document';source={'example.py':'a'*64}
    meta={'schema_version':'main_team_handoff_v1','phase':'A','project_source_sha256':source,
        'project_source_digest':canonical_hash(source),'files':{'START_HERE.md':{'bytes':len(file),'sha256':hashlib.sha256(file).hexdigest()}}}
    path=tmp_path/'master.zip'
    def write(value):
        with zipfile.ZipFile(path,'w') as z:
            z.writestr(prefix+'START_HERE.md',value);z.writestr(prefix+'BUNDLE_MANIFEST.json',json.dumps(meta))
    write(file);assert verify_bundle(path)['verified_files']==1
    write(b'changed');
    with pytest.raises(ValueError):verify_bundle(path)


def test_notebook_starters_are_parseable_output_free_and_not_claimed_cloud_ready():
    for platform in ['colab','kaggle']:
        notebook=json.loads((REPO/f'notebooks/main_{platform}_starter.ipynb').read_text(encoding='utf-8'))
        assert not notebook['metadata']['vlmbench']['cloud_generation_verified']
        for cell in notebook['cells']:
            if cell['cell_type']=='code':
                assert cell['outputs']==[] and cell['execution_count'] is None
                ast.parse(''.join(cell['source']))
    for role in ROLES:
        data=yaml.safe_load((REPO/f'configs/team_assignments_v1/{role}.yaml').read_text())
        assert Assignment.model_validate(data).expected_cells==1000
