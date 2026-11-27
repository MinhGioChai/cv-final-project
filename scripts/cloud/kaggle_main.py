"""Kaggle workflow for the main benchmark: locate/verify the private bundle, record diagnostics.

Phase A tool. It never loads a model or calls generation; the shared runner of TV1
(`scripts/run_main.py`) stays the only inference entry point. Subcommands:

  locate       find exactly one master bundle under the read-only input mount
  prepare      verify SHA/manifest, then extract or copy into a fresh working dir
  diagnose     record Python/GPU/Internet/secret-presence evidence (never secret values)
  runner-check report whether the Phase B runner command is available yet
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import platform
import shutil
import socket
import subprocess
import sys
import zipfile

BUNDLE_NAME='VLM_ENVI_Main_Inference_Team_v1'
MASTER_ZIP=BUNDLE_NAME+'.zip'
# Master SHA256 published by TV5 in the shared team guide (v1, 2026-11-27).
EXPECTED_MASTER_SHA256='29f7b3326df239df1f2bea8286ea38c4cd12ed11f0438cae861b3b998d0689f5'
MANIFEST='BUNDLE_MANIFEST.json'
KAGGLE_ROLES={'TV2':'qwen','TV4':'gemma'}  # both Kaggle shards use language vi
PHASE_B_CONFIG='configs/baseline_v3_team_final_v2.yaml'
SECRET_NAMES=('HF_TOKEN',)


class KaggleSetupError(RuntimeError):
    """Raised with a message meant to be read in the notebook output."""


def sha256_file(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()


def dataset_label(input_root,path):
    """Kaggle mounts each attached Dataset as /kaggle/input/<slug>/..."""
    parts=Path(path).relative_to(input_root).parts
    return parts[0] if len(parts)>1 else None


def locate(input_root):
    """Return the single bundle candidate; refuse zero or ambiguous candidates."""
    input_root=Path(input_root)
    if not input_root.is_dir():
        raise KaggleSetupError(f'{input_root} not found: attach the private Dataset with Add Input first')
    zips=sorted(p for p in input_root.rglob(MASTER_ZIP) if p.is_file())
    dirs=sorted(p.parent for p in input_root.rglob(MANIFEST) if p.parent.name==BUNDLE_NAME)
    # A directory that holds the ZIP is not a second bundle; only extracted trees count.
    dirs=[d for d in dirs if not any(z.is_relative_to(d) for z in zips)]
    candidates=[('zip',p) for p in zips]+[('extracted',p) for p in dirs]
    if not candidates:
        other=sorted(str(p) for p in input_root.rglob('*.zip'))[:20]
        raise KaggleSetupError(f'No {MASTER_ZIP} or extracted {BUNDLE_NAME}/{MANIFEST} under {input_root}. '
            f'ZIP files seen: {other or "none"}')
    if len(candidates)>1:
        listing=', '.join(f'{kind}:{path}' for kind,path in candidates)
        raise KaggleSetupError(f'Ambiguous bundles ({len(candidates)}): {listing}. '
            'Detach extra Datasets/versions or pass --master explicitly; the first match is never chosen.')
    kind,path=candidates[0]
    return {'kind':kind,'path':str(path),'dataset':dataset_label(input_root,path)}


def safe_member(name):
    p=PurePosixPath(name)
    return bool(name) and not p.is_absolute() and '..' not in p.parts and '\\' not in name and ':' not in name


def check_manifest(meta,actual):
    """Compare manifest records with {relative_name: (bytes, sha256)} of the actual files."""
    if meta.get('schema_version')!='main_team_handoff_v1':raise KaggleSetupError('Unknown handoff schema')
    files=meta.get('files')
    if not isinstance(files,dict) or not files:raise KaggleSetupError('Manifest has no file records')
    missing=sorted(set(files)-set(actual));extra=sorted(set(actual)-set(files))
    if missing or extra:
        raise KaggleSetupError(f'Bundle file set differs from manifest: missing={missing[:10]} extra={extra[:10]}')
    bad=sorted(n for n,(size,digest) in actual.items() if (size,digest)!=(files[n]['bytes'],files[n]['sha256']))
    if bad:raise KaggleSetupError(f'Hash/size mismatch in {len(bad)} file(s): {bad[:10]}')
    if canonical_hash(meta['project_source_sha256'])!=meta['project_source_digest']:
        raise KaggleSetupError('Source snapshot fingerprint differs from manifest')
    return len(files)


def verify_zip(archive_path,expected_sha256=EXPECTED_MASTER_SHA256):
    actual_sha=sha256_file(archive_path)
    if actual_sha!=expected_sha256:
        raise KaggleSetupError(f'Master SHA256 mismatch: got {actual_sha}, expected {expected_sha256}. '
            'Get the correct bundle from TV5; do not edit the expected value.')
    prefix=BUNDLE_NAME+'/'
    with zipfile.ZipFile(archive_path) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)):raise KaggleSetupError('Duplicate ZIP members')
        unsafe=[n for n in names if not safe_member(n) or not n.startswith(prefix)]
        if unsafe:raise KaggleSetupError(f'Unsafe ZIP members: {unsafe[:5]}')
        meta=json.loads(archive.read(prefix+MANIFEST))
        actual={}
        for info in archive.infolist():
            if info.is_dir() or info.filename==prefix+MANIFEST:continue
            actual[info.filename[len(prefix):]]=(info.file_size,hashlib.sha256(archive.read(info)).hexdigest())
    count=check_manifest(meta,actual)
    return {'verified_files':count,'master_sha256':actual_sha,'provenance':'master_zip_sha_pinned',
        'project_source_digest':meta['project_source_digest'],'phase':meta.get('phase')}


def verify_tree(root):
    root=Path(root);meta=json.loads((root/MANIFEST).read_text(encoding='utf-8'))
    actual={}
    for path in root.rglob('*'):
        if path.is_symlink():raise KaggleSetupError(f'Symlink in bundle: {path}')
        if path.is_file() and path!=root/MANIFEST:
            actual[path.relative_to(root).as_posix()]=(path.stat().st_size,sha256_file(path))
    count=check_manifest(meta,actual)
    return {'verified_files':count,'manifest_sha256':sha256_file(root/MANIFEST),
        'provenance':'extracted_tree_manifest_only_needs_TV5_confirmation',
        'project_source_digest':meta['project_source_digest'],'phase':meta.get('phase')}


def ensure_writable_target(target,input_root,working_root):
    target=Path(target).resolve();working_root=Path(working_root).resolve()
    if target.is_relative_to(Path(input_root).resolve()):
        raise KaggleSetupError(f'{target} is inside the read-only input mount; write under {working_root}')
    if not target.is_relative_to(working_root):raise KaggleSetupError(f'Write only under {working_root}, not {target}')
    return target


def prepare(input_root,working_root,master=None,allow_extracted=False,expected_sha256=EXPECTED_MASTER_SHA256):
    """Verify, then materialise the bundle once in a fresh working directory."""
    input_root=Path(input_root);working_root=Path(working_root)
    found={'kind':'zip' if Path(master).is_file() else 'extracted','path':str(master),
        'dataset':None} if master else locate(input_root)
    source=Path(found['path'])
    if found['kind']=='zip' and not source.is_file():raise KaggleSetupError(f'{source} is not a file')
    target=ensure_writable_target(working_root/BUNDLE_NAME,input_root,working_root)
    if target.exists():
        raise KaggleSetupError(f'{target} already exists. Reuse the verified workspace or start a fresh session; '
            'this tool never overwrites it.')
    if found['kind']=='zip':
        report=verify_zip(source,expected_sha256)
        staging=working_root/(BUNDLE_NAME+'.partial')
        if staging.exists():raise KaggleSetupError(f'Leftover {staging}; inspect it and remove it manually')
        with zipfile.ZipFile(source) as archive:archive.extractall(staging)
        (staging/BUNDLE_NAME).rename(target);staging.rmdir()
    else:
        if not allow_extracted:
            raise KaggleSetupError(f'Only an extracted tree was found at {source}. Its manifest can be checked but '
                'not pinned to the master SHA. Ask TV5 to confirm, then rerun with --allow-extracted, '
                'or upload the ZIP so it is not auto-extracted.')
        report=verify_tree(source)
        shutil.copytree(source,target,symlinks=False)
    copied=verify_tree(target)
    if copied['project_source_digest']!=report['project_source_digest']:
        raise KaggleSetupError('Working copy differs from the verified source')
    return {**report,'source_kind':found['kind'],'source_path':str(source),'dataset':found['dataset'],
        'bundle_root':str(target),'project':str(target/'project'),'working_copy_verified':True,
        'inference_calls':0}


def run_text(argv,timeout=30,cwd=None):
    try:
        done=subprocess.run(argv,capture_output=True,text=True,timeout=timeout,cwd=cwd)
    except (OSError,subprocess.SubprocessError) as exc:
        return {'ok':False,'error':f'{type(exc).__name__}: {exc}'}
    return {'ok':done.returncode==0,'returncode':done.returncode,'stdout':done.stdout.strip(),
        'stderr':done.stderr.strip()[-2000:]}


def parse_gpus(stdout):
    gpus=[]
    for line in stdout.splitlines():
        fields=[f.strip() for f in line.split(',')]
        if len(fields)==4:gpus.append(dict(zip(['name','memory_total','driver','compute_cap'],fields)))
    return gpus


def internet_reachable(host='pypi.org',port=443,timeout=5):
    try:
        with socket.create_connection((host,port),timeout=timeout):return True
    except OSError:return False


def diagnose(*,role='TV2',inference_python=None,project=None,check_internet=False,environ=None,runner=run_text):
    environ=os.environ if environ is None else environ
    smi=runner(['nvidia-smi','--query-gpu=name,memory.total,driver_version,compute_cap','--format=csv,noheader'])
    result={'scope':'Phase_A_kaggle_diagnostics_no_model_load','role':role,'model':KAGGLE_ROLES[role],
        'utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'kernel_python':sys.version.split()[0],'platform':platform.platform(),
        'kaggle_kernel':environ.get('KAGGLE_KERNEL_RUN_TYPE'),
        'gpus':parse_gpus(smi.get('stdout','')) if smi['ok'] else [],
        'nvidia_smi_error':None if smi['ok'] else smi.get('error') or smi.get('stderr'),
        # Presence only: values are never read into the report.
        'secrets_present':{name:bool(environ.get(name)) for name in SECRET_NAMES},
        'internet':internet_reachable() if check_internet else 'not_checked',
        'model_loaded':False,'generation_calls':0}
    if inference_python:
        probe=('import json,sys,torch; from vlmbench.pilot_launcher import gpu_preflight; '
            "print(json.dumps({'python':sys.version.split()[0],'torch':torch.__version__,"
            "'cuda_build':torch.version.cuda,'cuda_available':torch.cuda.is_available(),"
            "'preflight':gpu_preflight('"+KAGGLE_ROLES[role]+"',torch) if torch.cuda.is_available() else None,"
            "'mem_free_total':torch.cuda.mem_get_info() if torch.cuda.is_available() else None}))")
        out=runner([str(inference_python),'-c',probe],timeout=300,cwd=project)
        result['inference_env']=json.loads(out['stdout'].splitlines()[-1]) if out['ok'] and out['stdout'] else \
            {'error':out.get('error') or out.get('stderr')}
        freeze=runner([str(inference_python),'-m','pip','freeze'],timeout=120)
        if freeze['ok']:
            result['package_fingerprint']=hashlib.sha256(freeze['stdout'].encode('utf-8')).hexdigest()
            pins=('torch==','torchvision==','transformers==','accelerate==','bitsandbytes==')
            result['key_packages']=[l for l in freeze['stdout'].splitlines() if l.lower().startswith(pins)]
    return result


def runner_check(project,python=None,runner=run_text,role='TV2'):
    """Phase B readiness of the shared runner for TV2; prints the target command, never runs it."""
    project=Path(project);python=str(python or sys.executable);blockers=[]
    if not (project/'scripts/run_main.py').is_file():blockers.append('scripts/run_main.py missing')
    else:
        helptext=runner([python,'scripts/run_main.py','run','--help'],timeout=120,cwd=project)
        if '--language' not in helptext.get('stdout',''):blockers.append('run_main.py has no --language (TV1 PR not integrated)')
    if not (project/PHASE_B_CONFIG).is_file():blockers.append(f'{PHASE_B_CONFIG} missing (TV5 freeze v2 not released)')
    blockers.append('Execution approval is granted by TV5 outside this tool')
    argv=[python,'scripts/run_main.py','run','--config',PHASE_B_CONFIG,'--model',KAGGLE_ROLES[role],'--language','vi',
        '--platform','kaggle','--run-id',role.lower()+'_smoke_v2','--smoke-per-task','2','--execute']
    return {'role':role,'ready':False,'blockers':blockers,'target_smoke_command':argv,'executed':False}


def write_report(path,value,input_root,working_root):
    target=ensure_writable_target(path,input_root,working_root)
    if target.exists():raise KaggleSetupError(f'{target} exists; choose a new report name')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return str(target)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('action',choices=['locate','prepare','diagnose','runner-check'])
    p.add_argument('--role',choices=sorted(KAGGLE_ROLES),default='TV2')
    p.add_argument('--input-root',default='/kaggle/input');p.add_argument('--working-root',default='/kaggle/working')
    p.add_argument('--master',help='Explicit bundle path when several Datasets are attached')
    p.add_argument('--allow-extracted',action='store_true',help='Accept an extracted tree after TV5 confirmed it')
    p.add_argument('--inference-python',help='Python of .venv-cloud for diagnose/runner-check')
    p.add_argument('--project',help='Project directory inside the prepared bundle')
    p.add_argument('--check-internet',action='store_true',help='Open one TCP connection to pypi.org:443')
    p.add_argument('--report',help='New JSON evidence file under --working-root')
    args=p.parse_args(argv)
    try:
        if args.action=='locate':result=locate(args.input_root)
        elif args.action=='prepare':
            result=prepare(args.input_root,args.working_root,master=args.master,allow_extracted=args.allow_extracted)
        elif args.action=='diagnose':
            result=diagnose(role=args.role,inference_python=args.inference_python,project=args.project,
                check_internet=args.check_internet)
        else:
            if not args.project:p.error('runner-check needs --project')
            result=runner_check(args.project,args.inference_python,role=args.role)
        if args.report:result['report']=write_report(args.report,result,args.input_root,args.working_root)
    except KaggleSetupError as exc:
        print(f'ERROR: {exc}',file=sys.stderr);return 2
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':
    sys.exit(main())
