"""Audit the actual Git candidate set without staging, committing or printing secrets."""
import argparse
import json
from pathlib import Path
import re
import subprocess

from vlmbench.io_utils import write_json

PATTERNS={
    'hf_token':re.compile(r'\bhf_[A-Za-z0-9]{20,}\b'),
    'github_token':re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b'),
    'aws_access_key':re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'private_key':re.compile(r'-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----'),
    'signed_asset_url':re.compile(r'https?://[^\s"<>]+[?&](?:X-Amz-Signature|X-Goog-Signature|Signature)=',re.I),
    'url_password':re.compile(r'https?://[^/\s:@]+:[^/\s@]+@'),
}
TEXT_SUFFIXES={'.py','.cjs','.md','.txt','.toml','.yaml','.yml','.json','.jsonl','.csv','.html','.ipynb'}
LOCAL_PREFIXES=('.venv/','.venv-infer/','.cache/','.pytest_cache/','data/raw/','data/external_images/','exports/','results/','.git/')


def findings(content):
    return [{'rule':name,'line':content.count('\n',0,match.start())+1}
            for name,pattern in PATTERNS.items() for match in pattern.finditer(content)]


def audit(root,paths):
    issues=[];total=0;largest=[]
    for name in sorted(set(paths)):
        path=(root/name).resolve()
        if not path.is_relative_to(root.resolve()):raise ValueError('Candidate outside project')
        if not path.exists():continue  # tracked deletion, if any
        size=path.stat().st_size;total+=size;largest.append({'path':name,'bytes':size})
        if name.startswith(LOCAL_PREFIXES) or '__pycache__' in path.parts:
            issues.append({'path':name,'rule':'local_artifact_in_git'})
        if size>5*1024**2:issues.append({'path':name,'rule':'over_internal_5MiB_file_budget'})
        if path.suffix.lower() in TEXT_SUFFIXES or path.name.startswith('.git'):
            for issue in findings(path.read_text(encoding='utf-8-sig')):issues.append({'path':name,**issue})
    return {'scope':'local Git candidate audit; no remote publishing','ready':not issues,
        'candidate_files':len(set(paths)),'candidate_bytes':total,
        'largest_files':sorted(largest,key=lambda x:x['bytes'],reverse=True)[:10],
        'issues':issues,'credential_check':'pattern-based; reports paths/rules/line numbers only'}


def candidate_paths(root):
    raw=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root)
    return [s for s in raw.decode('utf-8').split('\0') if s]


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report');args=p.parse_args();root=Path.cwd().resolve()
    result=audit(root,candidate_paths(root))
    if args.report:
        path=(root/args.report).resolve()
        if not path.is_relative_to(root) or path.exists():raise ValueError('Use a new report path inside project')
        write_json(path,result)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['ready'] else 1)
