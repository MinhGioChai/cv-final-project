import json
from pathlib import Path
import zipfile

import pytest

from vlmbench.io_utils import sha256_file
from vlmbench.team_bundle import BINDINGS,allowed,build,restore


@pytest.fixture
def snapshot(tmp_path):
    root=tmp_path/'source';root.mkdir()
    for name in BINDINGS:
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('synthetic_test_only',encoding='utf-8')
    for name,text in {'data/raw/task/images/1.jpg':'synthetic_test_only_jpeg',
        'data/raw/task/receipt.json':'{}','data/raw/task/pool.json':'excluded_signed_pool',
        'data/raw/task/pages/0.json':'excluded_signed_page','data/raw/task/image_index.json':'excluded_signed_index',
        'reports/stage1/v10/main_review/index.html':'synthetic_test_only_index'}.items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    target=tmp_path/'clone';target.mkdir()
    for name in BINDINGS:
        path=target/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((root/name).read_bytes())
    return root,target,root/'exports/team.zip'


def test_private_bundle_roundtrip_and_identical_resume(snapshot):
    root,target,archive=snapshot;report=build(root,archive)
    assert report['contains_model_weights'] is False
    with zipfile.ZipFile(archive) as z:
        assert not any('pool.json' in n or '/pages/' in n or 'image_index.json' in n for n in z.namelist())
        assert not any(n.startswith('src/') for n in z.namelist())
    result=restore(target,archive)
    assert result['restored_files']==report['files']
    assert restore(target,archive)['restored_files']==0
    assert (target/'data/raw/task/images/1.jpg').read_bytes()==(root/'data/raw/task/images/1.jpg').read_bytes()


def test_existing_bundle_never_overwritten(snapshot):
    root,target,archive=snapshot;build(root,archive);before=archive.read_bytes()
    with pytest.raises(ValueError):build(root,archive)
    assert archive.read_bytes()==before


def test_restore_conflict_validated_before_any_write(snapshot):
    root,target,archive=snapshot;build(root,archive)
    path=target/'data/raw/task/receipt.json';path.parent.mkdir(parents=True);path.write_text('local changes')
    with pytest.raises(ValueError,match='differs'):restore(target,archive)
    assert path.read_text()=='local changes'
    assert not (target/'data/raw/task/images/1.jpg').exists()


def test_context_mismatch_prevents_restore(snapshot):
    root,target,archive=snapshot;build(root,archive);(target/BINDINGS[0]).write_text('changed')
    with pytest.raises(ValueError,match='another project'):restore(target,archive)
    assert not (target/'data/raw').exists()


def test_signed_asset_query_blocks_bundle(snapshot):
    root,target,archive=snapshot
    (root/'data/raw/task/receipt.json').write_text(json.dumps({'url':'https://example.invalid/image?'+'X-Amz-Signature=synthetic_test_only'}))
    with pytest.raises(ValueError,match='Signed URL'):build(root,archive)
    assert not archive.exists()


@pytest.mark.parametrize('path',['../outside.jpg','data/raw/../../outside.jpg','data/raw/evil.py','C:/bad.jpg','data\\raw\\bad.jpg','reports/stage1/v10/main_review/../../evil.html'])
def test_archive_allowlist_rejects_unsafe_or_executable_paths(path):
    assert not allowed(path)


def test_malicious_zip_member_not_extracted(snapshot):
    root,target,archive=snapshot;archive.parent.mkdir()
    metadata={'schema_version':'team_workspace_v1','bindings':{n:sha256_file(root/n) for n in BINDINGS},
        'files':{'../escape.jpg':{'bytes':4,'sha256':'0'*64}}}
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('TEAM_BUNDLE_CONTENTS.json',json.dumps(metadata));z.writestr('../escape.jpg',b'evil')
    with pytest.raises(ValueError,match='Unsafe'):restore(target,archive)
    assert not (target.parent/'escape.jpg').exists()
