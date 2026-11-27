"""Verify the private master or restore its approved main assets without overwriting files."""
import argparse
import json
from pathlib import Path

from vlmbench.team_handoff import restore_assets,verify_bundle

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['verify','restore-assets'])
    p.add_argument('--archive',required=True);p.add_argument('--root',default='.')
    args=p.parse_args()
    result=verify_bundle(Path(args.archive)) if args.action=='verify' else restore_assets(Path(args.root),Path(args.archive))
    print(json.dumps(result,ensure_ascii=False,indent=2))
