"""Independent A/B pilot plan/run/analyze; no main freeze bypass and no branch C."""
import argparse
import json
from pathlib import Path

from vlmbench.image_ab import execute, hardware_check, plan, summarize
from vlmbench.baseline_contract import inside
from vlmbench.io_utils import write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['hardware','plan','run','analyze'])
    parser.add_argument('--manifest',default='data/pilot/stage1_qa_v1/pilot_manifest.csv')
    parser.add_argument('--model',choices=['qwen','gemma'])
    parser.add_argument('--output',required=True,help='New report file or new run directory')
    parser.add_argument('--inputs',nargs='*',help='Model run directories for analyze')
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    target=inside(root,args.output)
    if args.action=='hardware':
        if target.exists() or not target.is_relative_to(root/'reports/validation'):
            parser.error('Use a NEW evidence path under reports/validation')
        result=hardware_check();write_json(target,result)
        print(json.dumps(result,ensure_ascii=False,indent=2));return int('error' in result)
    selected=plan(root,args.manifest)
    if args.action=='run':
        if not args.model:parser.error('--model required')
        try:result=execute(selected,args.model,args.output,execute=args.execute)
        except ValueError as exc:
            print(json.dumps({'status':'blocked','reason':str(exc),'plan':selected.summary},ensure_ascii=False,indent=2));return 2
    else:
        if target.exists():parser.error('Preserve existing output; use a new path')
        if not target.is_relative_to(root/'reports/validation') and not target.is_relative_to(root/'results/pilot/image_ab_v1'):
            parser.error('Write evidence under reports/validation or results/pilot/image_ab_v1')
        result=selected.summary
        if args.action=='analyze':
            records=[]
            for folder in args.inputs or []:
                directory=inside(root,folder)
                meta=json.loads((directory/'metadata.json').read_text(encoding='utf-8'))
                if meta['config_fingerprint']!=selected.summary['config_fingerprint']:raise ValueError('Input plan differs')
                for line in (directory/'predictions.jsonl').read_text(encoding='utf-8').splitlines():
                    record=json.loads(line)
                    if record['runtime_fingerprint']!=meta['runtime_fingerprint'] or record['model']!=meta['model']:
                        raise ValueError('Mixed runtime/model records')
                    records.append(record)
            result=summarize(selected,records)
        write_json(target,result)
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
