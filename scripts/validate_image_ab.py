"""Independent A/B pilot plan/run/analyze; no main freeze bypass and no branch C."""
import argparse
import json
from pathlib import Path

from vlmbench.image_ab import execute, hardware_check, plan, summarize
from vlmbench.baseline_contract import inside
from vlmbench.io_utils import write_json
from vlmbench.repope_diagnostic import diagnostic_plan,run_diagnostic,read_run,MODE


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['hardware','plan','run','analyze'])
    parser.add_argument('--manifest',default='data/pilot/stage1_qa_v1/pilot_manifest.csv')
    parser.add_argument('--model',choices=['qwen','gemma'])
    parser.add_argument('--output',required=True,help='New report file or new run directory')
    parser.add_argument('--inputs',nargs='*',help='Model run directories for analyze')
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--mode',choices=['full','repope-diagnostic'],default='full')
    parser.add_argument('--size',type=int,choices=[6,30],default=6,help='RePOPE diagnostic only')
    parser.add_argument('--phase1',help='Successful phase1 parent directory, required for diagnostic extension')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    target=inside(root,args.output)
    if args.action=='hardware':
        if target.exists() or not target.is_relative_to(root/'reports/validation'):
            parser.error('Use a NEW evidence path under reports/validation')
        result=hardware_check();write_json(target,result)
        print(json.dumps(result,ensure_ascii=False,indent=2));return int('error' in result)
    if args.mode=='repope-diagnostic' and args.manifest!='data/pilot/stage1_qa_v1/pilot_manifest.csv':
        parser.error('Diagnostic accepts the canonical human-approved pilot only')
    selected=diagnostic_plan(root,args.size) if args.mode=='repope-diagnostic' else plan(root,args.manifest)
    if args.action=='run':
        if not args.model:parser.error('--model required')
        try:
            result=(run_diagnostic(selected,args.model,args.output,execute=args.execute,phase1=args.phase1)
                    if args.mode=='repope-diagnostic' else execute(selected,args.model,args.output,execute=args.execute))
        except ValueError as exc:
            print(json.dumps({'status':'blocked','reason':str(exc),'plan':selected.summary},ensure_ascii=False,indent=2));return 2
    else:
        if target.exists():parser.error('Preserve existing output; use a new path')
        if not target.is_relative_to(root/'reports/validation') and not target.is_relative_to(root/'results/pilot'):
            parser.error('Write evidence under reports/validation or results/pilot/image_ab_v1')
        result=selected.summary
        if args.action=='analyze':
            records=[]
            for folder in args.inputs or []:
                if args.mode=='repope-diagnostic':
                    _,data=read_run(folder,selected);records.extend(data);continue
                directory=inside(root,folder)
                meta=json.loads((directory/'metadata.json').read_text(encoding='utf-8'))
                if meta['config_fingerprint']!=selected.summary['config_fingerprint']:raise ValueError('Input plan differs')
                for line in (directory/'predictions.jsonl').read_text(encoding='utf-8').splitlines():
                    record=json.loads(line)
                    if record['runtime_fingerprint']!=meta['runtime_fingerprint'] or record['model']!=meta['model']:
                        raise ValueError('Mixed runtime/model records')
                    records.append(record)
            result=summarize(selected,records)
            if args.mode=='repope-diagnostic':result.update(mode=MODE,M3_complete=False)
        write_json(target,result)
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
