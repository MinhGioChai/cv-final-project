import ast
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import stat
import zipfile

import pytest

from vlmbench import pilot_launcher as launcher


@pytest.fixture
def project(tmp_path):
    for model in ['qwen','gemma']:
        path=tmp_path/f'configs/inference/team_{model}_v1.yaml';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('synthetic_test_only')
    return tmp_path


def test_models_route_to_distinct_current_runners(project):
    q=launcher.command(project,python='python',model='qwen',platform='colab',limit=2)
    g=launcher.command(project,python='python',model='gemma',platform='kaggle',limit=2,online=True,resume=True)
    assert 'infer-pilot' in q and 'qwen' in q
    assert 'infer-gemma-trace' in g and 'infer-pilot' not in g and '--online' in g and '--resume' in g
    assert any(x.endswith('team_gemma_v1.yaml') for x in g)
    assert any('team_v1' in x and x.endswith('gemma.jsonl') for x in g)


@pytest.mark.parametrize('limit',[0,11,1000])
def test_no_accidental_main_or_unpaired_large_pilot(project,limit):
    with pytest.raises(ValueError):launcher.command(project,python='python',model='qwen',platform='local',limit=limit)


@pytest.mark.parametrize('output',['results/pilot/local/qwen_smoke_v1.jsonl','results/pilot/local/gemma_bf16_trace_v2.jsonl','reports/pilot_outputs/new.jsonl'])
def test_historical_evidence_paths_protected(project,output):
    with pytest.raises(ValueError):launcher.command(project,python='python',model='gemma',platform='local',limit=2,output=output)


def test_run_name_cannot_escape_output_namespace(project):
    with pytest.raises(ValueError):launcher.command(project,python='python',model='qwen',platform='local',limit=2,run_name='../other')


def test_offline_mode_never_leaks_to_later_online_child(project):
    parent={'HF_HOME':'synthetic_test_only_cache','HF_TOKEN':'synthetic_test_only_secret','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}
    online=launcher.child_environment(project,online=True,environment=parent)
    assert 'HF_HUB_OFFLINE' not in online and 'TRANSFORMERS_OFFLINE' not in online
    assert parent['HF_HUB_OFFLINE']=='1' and online['HF_TOKEN']==parent['HF_TOKEN']
    assert launcher.child_environment(project,online=False,environment={})['HF_HUB_OFFLINE']=='1'


def torch_stub(available=True,major=8,bf16=True):
    return SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:available,get_device_capability=lambda i:(major,0),
        is_bf16_supported=lambda:bf16,get_device_name=lambda i:'synthetic_test_only_gpu'))


def test_no_gpu_and_emulated_bf16_are_blocked_before_model_download():
    with pytest.raises(RuntimeError,match='CUDA'):launcher.gpu_preflight('qwen',torch_stub(available=False))
    with pytest.raises(RuntimeError,match='no FP16 fallback'):launcher.gpu_preflight('gemma',torch_stub(major=7,bf16=True))
    assert launcher.gpu_preflight('qwen',torch_stub(major=7))['precision']=='nf4_fp16'
    assert launcher.gpu_preflight('gemma',torch_stub())['precision']=='nf4_bf16'


def test_dry_run_never_prompts_or_preflights_gpu(monkeypatch):
    calls=[]
    monkeypatch.setattr(launcher.subprocess,'run',lambda argv,**kw:calls.append(argv) or SimpleNamespace(returncode=0))
    monkeypatch.setattr(launcher.getpass,'getpass',lambda *a:pytest.fail('Token prompt in dry-run'))
    assert launcher.main(['--model','gemma','--dry-run','--online'])==0
    assert len(calls)==1 and 'infer-gemma-trace' in calls[0] and '--dry-run' in calls[0]


def test_failed_gpu_preflight_never_attempts_run_or_token(monkeypatch):
    calls=[]
    monkeypatch.setattr(launcher.subprocess,'run',lambda argv,**kw:calls.append(argv) or SimpleNamespace(returncode=17))
    monkeypatch.setattr(launcher.getpass,'getpass',lambda *a:pytest.fail('Token prompt before failed GPU check'))
    assert launcher.main(['--model','gemma','--online'])==17
    assert len(calls)==1 and '-c' in calls[0]


def generator():
    root=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('notebook_generator',root/'scripts/generate_cloud_notebooks.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module,root


@pytest.mark.parametrize('platform',['colab','kaggle'])
def test_notebooks_are_regenerable_and_use_shared_launcher(platform):
    module,root=generator();notebook=module.generate(platform)
    assert notebook==json.loads((root/f'notebooks/pilot_{platform}.ipynb').read_text(encoding='utf-8'))
    code='\n'.join(''.join(c['source']) for c in notebook['cells'] if c['cell_type']=='code')
    assert 'scripts/run_pilot.py' in code and 'infer-pilot' not in code
    assert 'stage1_qa_v1' in code and 'RUN_NAME=' in code


def notebook_function(name):
    module,_=generator();notebook=module.generate('colab')
    for c in notebook['cells']:
        if c['cell_type']=='code':
            for node in ast.parse(''.join(c['source'])).body:
                if isinstance(node,ast.FunctionDef) and node.name==name:
                    return compile(ast.Module(body=[node],type_ignores=[]),'<synthetic_notebook_function>','exec')
    raise AssertionError('Missing notebook helper')


def test_notebook_zip_extraction_rejects_traversal_and_symlinks(tmp_path):
    namespace={'Path':Path,'zipfile':zipfile,'stat':stat};exec(notebook_function('safe_extract'),namespace)
    for name in ['../escape','vlmbench-pilot/../../escape','vlmbench-pilot/../escape']:
        path=tmp_path/'bad.zip'
        with zipfile.ZipFile(path,'w') as z:z.writestr(name,b'synthetic_test_only')
        with pytest.raises(ValueError):namespace['safe_extract'](path,tmp_path/'out')
    assert not (tmp_path/'escape').exists()
    path=tmp_path/'link.zip'
    with zipfile.ZipFile(path,'w') as z:
        member=zipfile.ZipInfo('vlmbench-pilot/link');member.external_attr=(stat.S_IFLNK|0o777)<<16
        z.writestr(member,'../outside')
    with pytest.raises(ValueError):namespace['safe_extract'](path,tmp_path/'out')


def test_notebook_pilot_passes_model_and_explicit_resume_download_flags(tmp_path):
    calls=[]
    namespace={'PYTHON':Path('/synthetic/python'),'ROOT':tmp_path,'MODEL':'gemma','PLATFORM':'colab','LIMIT':2,
        'RUN_NAME':'synthetic_test_only','RESULT':tmp_path/'result.jsonl','RESUME':True,'ALLOW_DOWNLOAD':False,
        'subprocess':SimpleNamespace(run=lambda argv,**kw:calls.append(argv))}
    exec(notebook_function('pilot'),namespace);namespace['pilot']('--dry-run')
    assert '--resume' in calls[0] and '--online' not in calls[0] and '--dry-run' in calls[0]
    assert calls[0][calls[0].index('--model')+1]=='gemma'
