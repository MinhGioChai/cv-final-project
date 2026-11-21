"""Private data/review handoff separated from the lightweight Git repository."""
import json
import os
from pathlib import Path,PurePosixPath
import stat
import tempfile
import zipfile

from .io_utils import atomic_bytes,sha256_file

BINDINGS=[
    'data/main/preparation_v2/all_candidates.jsonl',
    'data/main/preparation_v2/repope_bilingual_draft_manifest.csv',
    *[f'data/main/preparation_v3/{d}_bilingual_draft.csv' for d in ['vsr','tallyqa','oxford_pet']],
    'data/pilot/stage1_qa_v1/pilot_manifest.csv',
    'src/vlmbench/main_review_template.html',
]


def allowed(name):
    path=PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:return False
    if name.startswith('data/raw/'):
        if any(p in {'pages','__pycache__'} for p in path.parts):return False
        return path.name not in {'pool.json','image_index.json'} and path.suffix in {'.jpg','.json','.jsonl','.txt','.gz','.zip',''}
    return name.startswith('reports/stage1/v10/main_review/') and len(path.parts)==5 and path.suffix=='.html'


def build(root,output):
    root=root.resolve();output=output.resolve()
    if not output.is_relative_to(root/'exports') or output.exists():raise ValueError('Use a new ZIP path under exports')
    paths=[p for p in (root/'data/raw').rglob('*') if p.is_file() and allowed(p.relative_to(root).as_posix())]
    paths.extend(p for p in (root/'reports/stage1/v10/main_review').glob('*.html') if p.is_file())
    if not paths or not (root/'reports/stage1/v10/main_review/index.html').exists():raise ValueError('Main data/review pages missing')
    bindings={name:sha256_file(root/name) for name in BINDINGS}
    files={}
    for path in sorted(paths):
        if path.is_symlink():raise ValueError('Do not package symlinks')
        name=path.relative_to(root).as_posix()
        # Public source/cache JSON may include stale signed URLs: omit them entirely.
        if path.suffix in {'.json','.jsonl','.txt'}:
            text=path.read_text(encoding='utf-8-sig')
            if any(s in text.lower() for s in ['x-amz-signature=','x-goog-signature=','?signature=','&signature=']):
                raise ValueError('Signed URL found in selected cache: '+name)
        files[name]={'bytes':path.stat().st_size,'sha256':sha256_file(path)}
    if sum(x['bytes'] for x in files.values())>500*1024**2:raise ValueError('Team snapshot exceeds 500 MiB expanded budget')
    metadata={'schema_version':'team_workspace_v1','scope':'private research data and offline main review; no code/venv/weights/secrets',
        'bindings':bindings,'files':files,'restore':'python scripts/team_workspace.py restore --archive <zip>'}
    output.parent.mkdir(parents=True,exist_ok=True)
    temp=None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent,delete=False) as handle:temp=Path(handle.name)
        with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for name in sorted(files):
                archive.writestr(zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0)),(root/name).read_bytes(),compress_type=zipfile.ZIP_DEFLATED)
            archive.writestr('TEAM_BUNDLE_CONTENTS.json',json.dumps(metadata,ensure_ascii=False,indent=2).encode('utf-8'),compress_type=zipfile.ZIP_DEFLATED)
        os.replace(temp,output);temp=None
    finally:
        if temp is not None and temp.exists():temp.unlink()
    return {'archive':output.relative_to(root).as_posix(),'bytes':output.stat().st_size,'sha256':sha256_file(output),
        'files':len(files),'expanded_bytes':sum(x['bytes'] for x in files.values()),'bindings':bindings,
        'contains_model_weights':False,'contains_signed_asset_urls':False,'publication':'private team handoff; ZIP ignored by Git'}


def restore(root,archive_path):
    root=root.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)) or 'TEAM_BUNDLE_CONTENTS.json' not in names:raise ValueError('Duplicate/missing ZIP index')
        metadata=json.loads(archive.read('TEAM_BUNDLE_CONTENTS.json'))
        if metadata['schema_version']!='team_workspace_v1':raise ValueError('Unknown bundle version')
        if metadata['bindings']!={name:sha256_file(root/name) for name in BINDINGS}:raise ValueError('Bundle belongs to another project data/template version')
        files=metadata['files']
        if set(names)!=(set(files)|{'TEAM_BUNDLE_CONTENTS.json'}):raise ValueError('Unexpected ZIP entries')
        if sum(i.file_size for i in archive.infolist())>500*1024**2:raise ValueError('Expanded ZIP exceeds budget')
        for name,item in files.items():
            info=archive.getinfo(name);target=(root/name).resolve()
            if not allowed(name) or not target.is_relative_to(root) or stat.S_ISLNK(info.external_attr>>16):raise ValueError('Unsafe archive member')
            if info.file_size!=item['bytes']:raise ValueError('Member size differs')
            import hashlib
            if hashlib.sha256(archive.read(name)).hexdigest()!=item['sha256']:raise ValueError('Member hash differs')
            if target.exists() and sha256_file(target)!=item['sha256']:raise ValueError('Existing local data differs; no files overwritten: '+name)
        # All entries and existing files are checked before the first write.
        written=0
        for name in files:
            target=root/name
            if not target.exists():atomic_bytes(target,archive.read(name));written+=1
    return {'verified_files':len(files),'restored_files':written,'existing_identical_preserved':len(files)-written,
        'network_calls':0,'model_inferences':0}
