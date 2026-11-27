"""Synthetic Kaggle mounts only: no real bundle, GPU, network, secret value or inference."""
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest

REPO=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('kaggle_main',REPO/'scripts/cloud/kaggle_main.py')
km=importlib.util.module_from_spec(spec);spec.loader.exec_module(km)
NAME=km.BUNDLE_NAME


def manifest_for(files):
    source={n:hashlib.sha256(b).hexdigest() for n,b in files.items() if n.startswith('project/')}
    return {'schema_version':'main_team_handoff_v1','phase':'synthetic_test_only',
        'files':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in files.items()},
        'project_source_sha256':source,'project_source_digest':km.canonical_hash(source)}


FILES={'START_HERE.md':b'synthetic','project/scripts/setup_inference.py':b'# synthetic',
    'main_assets/main_assets_v1.zip':b'synthetic assets'}


def make_zip(path,files=FILES,meta=None,extra=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path,'w') as archive:
        archive.writestr(f'{NAME}/{km.MANIFEST}',json.dumps(meta or manifest_for(files)))
        for name,raw in files.items():archive.writestr(f'{NAME}/{name}',raw)
        for name,raw in (extra or {}).items():archive.writestr(name,raw)
    return path,km.sha256_file(path)


def make_tree(root,files=FILES,meta=None):
    for name,raw in files.items():
        (root/name).parent.mkdir(parents=True,exist_ok=True);(root/name).write_bytes(raw)
    (root/km.MANIFEST).write_text(json.dumps(meta or manifest_for(files)),encoding='utf-8')
    return root


@pytest.fixture
def mounts(tmp_path):
    inp=tmp_path/'kaggle/input';work=tmp_path/'kaggle/working';inp.mkdir(parents=True);work.mkdir(parents=True)
    return inp,work


def test_locate_single_zip_reports_dataset_slug(mounts):
    inp,_=mounts;make_zip(inp/'my-private-set'/km.MASTER_ZIP)
    found=km.locate(inp)
    assert found['kind']=='zip' and found['dataset']=='my-private-set'


def test_locate_reports_owner_and_slug_for_current_kaggle_mount(mounts):
    inp,_=mounts;make_zip(inp/'datasets/some-owner/my-private-set'/(km.MASTER_ZIP+'.bin'))
    assert km.locate(inp)['dataset']=='some-owner/my-private-set'


def test_renamed_zip_bin_avoids_kaggle_auto_extract_and_keeps_sha_check(mounts):
    inp,work=mounts;_,sha=make_zip(inp/'set'/(km.MASTER_ZIP+'.bin'))
    assert km.locate(inp)['kind']=='zip'
    assert km.prepare(inp,work,expected_sha256=sha)['provenance']=='master_zip_sha_pinned'


def test_auto_extracted_nested_assets_are_reported_with_hint(mounts):
    inp,work=mounts;tree=make_tree(inp/'set'/NAME)
    (tree/'main_assets/main_assets_v1/data').mkdir(parents=True);(tree/'main_assets/main_assets_v1/data/x.jpg').write_bytes(b'x')
    with pytest.raises(km.KaggleSetupError,match='zip.bin'):km.prepare(inp,work,allow_extracted=True)


def test_locate_refuses_missing_mount_and_empty_input(tmp_path,mounts):
    inp,_=mounts
    with pytest.raises(km.KaggleSetupError,match='Add Input'):km.locate(tmp_path/'absent')
    (inp/'other').mkdir();(inp/'other/unrelated.zip').write_bytes(b'x')
    with pytest.raises(km.KaggleSetupError,match='unrelated.zip'):km.locate(inp)


def test_locate_refuses_two_versions_instead_of_picking_first(mounts):
    inp,_=mounts
    make_zip(inp/'set-v1'/km.MASTER_ZIP);make_zip(inp/'set-v2'/km.MASTER_ZIP)
    with pytest.raises(km.KaggleSetupError,match='Ambiguous bundles \\(2\\)'):km.locate(inp)


def test_locate_refuses_zip_plus_separate_extracted_copy(mounts):
    inp,_=mounts
    make_zip(inp/'a'/km.MASTER_ZIP);make_tree(inp/'b'/NAME)
    with pytest.raises(km.KaggleSetupError,match='Ambiguous'):km.locate(inp)


def test_prepare_zip_verifies_sha_extracts_once_and_never_overwrites(mounts):
    inp,work=mounts;_,sha=make_zip(inp/'set'/km.MASTER_ZIP)
    result=km.prepare(inp,work,expected_sha256=sha)
    root=Path(result['bundle_root'])
    assert result['working_copy_verified'] and result['inference_calls']==0
    assert (root/'project/scripts/setup_inference.py').read_bytes()==b'# synthetic'
    assert root.is_relative_to(work) and not (work/(NAME+'.partial')).exists()
    with pytest.raises(km.KaggleSetupError,match='already exists'):km.prepare(inp,work,expected_sha256=sha)


def test_prepare_rejects_wrong_master_sha_before_extracting(mounts):
    inp,work=mounts;make_zip(inp/'set'/km.MASTER_ZIP)
    with pytest.raises(km.KaggleSetupError,match='SHA256 mismatch'):km.prepare(inp,work,expected_sha256='0'*64)
    assert not (work/NAME).exists()


@pytest.mark.parametrize('tamper',['hash','extra_file','path_traversal','source_digest'])
def test_zip_content_must_match_manifest(tmp_path,tamper):
    meta=manifest_for(FILES);extra=None;files=dict(FILES)
    if tamper=='hash':files['START_HERE.md']=b'changed'
    if tamper=='extra_file':files['surprise.txt']=b'x'
    if tamper=='path_traversal':extra={'../escape.txt':b'x'}
    if tamper=='source_digest':meta['project_source_digest']='f'*64
    path,sha=make_zip(tmp_path/km.MASTER_ZIP,files=files,meta=meta,extra=extra)
    with pytest.raises(km.KaggleSetupError):km.verify_zip(path,sha)


def test_extracted_tree_needs_explicit_confirmation_then_is_copied(mounts):
    inp,work=mounts;make_tree(inp/'set'/NAME)
    with pytest.raises(km.KaggleSetupError,match='--allow-extracted'):km.prepare(inp,work)
    result=km.prepare(inp,work,allow_extracted=True)
    assert result['provenance']=='extracted_tree_manifest_only_needs_TV5_confirmation'
    assert (work/NAME/'START_HERE.md').is_file() and (inp/'set'/NAME/'START_HERE.md').is_file()


def test_extracted_tree_with_modified_file_is_rejected(mounts):
    inp,work=mounts;tree=make_tree(inp/'set'/NAME);(tree/'START_HERE.md').write_bytes(b'edited')
    with pytest.raises(km.KaggleSetupError,match='mismatch'):km.prepare(inp,work,allow_extracted=True)
    assert not (work/NAME).exists()


def test_reports_are_written_only_as_new_files_under_working(mounts):
    inp,work=mounts
    with pytest.raises(km.KaggleSetupError,match='read-only'):km.write_report(inp/'r.json',{},inp,work)
    with pytest.raises(km.KaggleSetupError,match='Write only'):km.write_report(work.parent/'r.json',{},inp,work)
    km.write_report(work/'evidence/r.json',{'a':1},inp,work)
    with pytest.raises(km.KaggleSetupError,match='exists'):km.write_report(work/'evidence/r.json',{},inp,work)


def fake_runner(argv,timeout=30,cwd=None):
    if argv[0]=='nvidia-smi':return {'ok':True,'stdout':'Tesla T4, 15360 MiB, 550.54, 7.5'}
    if argv[1:3]==['-m','pip']:return {'ok':True,'stdout':'torch==2.7.1+cu126\ntransformers==4.57.1\nPillow==12.0.0'}
    return {'ok':True,'stdout':json.dumps({'cuda_available':True,'preflight':{'gpu':'Tesla T4'}})}


def test_diagnose_records_presence_of_secret_but_never_its_value():
    secret='hf_synthetic_value_must_not_leak'
    result=km.diagnose(inference_python='py',environ={'HF_TOKEN':secret},runner=fake_runner)
    assert result['secrets_present']=={'HF_TOKEN':True}
    assert secret not in json.dumps(result)
    assert result['gpus']==[{'name':'Tesla T4','memory_total':'15360 MiB','driver':'550.54','compute_cap':'7.5'}]
    assert result['key_packages']==['torch==2.7.1+cu126','transformers==4.57.1']
    assert result['model_loaded'] is False and result['generation_calls']==0 and result['internet']=='not_checked'


def test_diagnose_keeps_error_when_no_gpu():
    result=km.diagnose(environ={},runner=lambda *a,**k:{'ok':False,'error':'FileNotFoundError: nvidia-smi'})
    assert result['gpus']==[] and 'nvidia-smi' in result['nvidia_smi_error']
    assert result['secrets_present']=={'HF_TOKEN':False}


def test_runner_check_blocks_until_language_sharding_and_v2_config_exist(tmp_path):
    (tmp_path/'scripts').mkdir();(tmp_path/'scripts/run_main.py').write_text('')
    result=km.runner_check(tmp_path,'py',runner=lambda *a,**k:{'ok':True,'stdout':'--model --platform'})
    assert not result['ready'] and not result['executed']
    assert any('--language' in b for b in result['blockers']) and any('freeze v2' in b for b in result['blockers'])
    cmd=result['target_smoke_command']
    assert cmd[cmd.index('--model')+1]=='qwen' and cmd[cmd.index('--language')+1]=='vi'
    assert cmd[cmd.index('--platform')+1]=='kaggle' and '--max-cells' not in cmd


def test_tv4_targets_gemma_vi_and_probes_gemma():
    seen=[]
    def runner(argv,timeout=30,cwd=None):
        seen.append(argv);return fake_runner(argv,timeout,cwd)
    result=km.diagnose(role='TV4',inference_python='py',environ={},runner=runner)
    assert result['model']=='gemma' and any("gpu_preflight('gemma'" in a[-1] for a in seen if a[1:2]==['-c'])
    cmd=km.runner_check(Path('/nonexistent'),'py',role='TV4')['target_smoke_command']
    assert cmd[cmd.index('--model')+1]=='gemma' and 'tv4_smoke_v2' in cmd


def test_runner_check_is_never_ready_on_its_own(tmp_path):
    (tmp_path/'scripts').mkdir();(tmp_path/'scripts/run_main.py').write_text('')
    (tmp_path/km.PHASE_B_CONFIG).parent.mkdir(parents=True);(tmp_path/km.PHASE_B_CONFIG).write_text('')
    result=km.runner_check(tmp_path,'py',runner=lambda *a,**k:{'ok':True,'stdout':'--language'})
    assert result['blockers']==['Execution approval is granted by TV5 outside this tool'] and not result['ready']


def test_cli_returns_readable_error_code(mounts,capsys):
    inp,work=mounts
    assert km.main(['locate','--input-root',str(inp),'--working-root',str(work)])==2
    assert 'No VLM_ENVI' in capsys.readouterr().err
