"""Create auditable VI proposals and, when images exist, a separate bilingual draft."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from vlmbench.datasets.candidates import Candidate
from vlmbench.io_utils import atomic_bytes,manifest_bytes,read_manifest,sha256_file
from vlmbench.main_translations import propose_repope
from vlmbench.schemas import ManifestRow
from vlmbench.translate import load_dictionary


def prepare(root, *, candidates, dictionary, extras, proposals_output, image_manifest, bilingual_output):
    paths=[candidates,dictionary,extras,proposals_output,image_manifest,bilingual_output]
    if len({p.resolve() for p in paths})!=len(paths):raise ValueError('Inputs and outputs must be distinct')
    rows=[Candidate.model_validate_json(s) for s in candidates.read_text(encoding='utf-8').splitlines()]
    extra_data=json.loads(extras.read_text(encoding='utf-8'))
    proposed=propose_repope(rows,pilot_dictionary=load_dictionary(dictionary),extras=extra_data)
    source_hashes={'candidates':sha256_file(candidates),'pilot_dictionary':sha256_file(dictionary),'extra_phrases':sha256_file(extras)}
    payload=(json.dumps({'schema_version':'repope_vi_proposals_v1','inputs':source_hashes,'rows':proposed,
        'human_approvals_created':0},ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    outputs={proposals_output:payload}
    if image_manifest.exists():
        materialized=read_manifest(image_manifest)
        by_id={r.sample_id:r for r in rows}
        by_proposal={r['sample_id']:r for r in proposed}
        if len(materialized)!=len(rows) or set(by_id)!={r.sample_id for r in materialized}:
            raise ValueError('Image manifest sample IDs differ from candidates')
        bilingual=[]
        for row in materialized:
            source=by_id[row.sample_id];proposal=by_proposal[row.sample_id]
            if row.question_en!=source.question_en or row.ground_truth!=source.ground_truth:raise ValueError('Source fields changed')
            if row.translation_status=='approved':raise ValueError('Do not replace approved translations with generated drafts')
            data=row.model_dump()
            data.update(question_vi=proposal['question_vi'],translation_status=proposal['translation_status'])
            data['metadata']['translation_draft']={'policy':'repope_noun_phrase_v1','inputs':source_hashes,
                'object_en':proposal['object_en'],'origin':proposal['origin'],'review_note':proposal['review_note'],
                'human_approval_created':False}
            bilingual.append(ManifestRow.model_validate(data))
        outputs[bilingual_output]=manifest_bytes(bilingual)
    for path,content in outputs.items():
        if path.exists() and path.read_bytes()!=content:raise ValueError('Output differs; use new paths to preserve history')
    for path,content in outputs.items():
        if not path.exists():atomic_bytes(path,content)
    return {'rows':len(proposed),'translation_status':dict(Counter(r['translation_status'] for r in proposed)),
        'vocabulary':len({r['object_en'] for r in proposed}),'human_approvals_created':0,
        'bilingual_manifest_created':bilingual_output in outputs,
        'outputs':{p.relative_to(root).as_posix():hashlib.sha256(b).hexdigest() for p,b in outputs.items()}}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report',help='New report path for this preparation state')
    args=p.parse_args();root=Path.cwd()
    report=prepare(root,candidates=root/'data/main/preparation_v2/repope_candidates.jsonl',
        dictionary=root/'data/dictionaries/object_en_vi.csv',extras=root/'data/dictionaries/main_object_vi_proposals_v1.json',
        proposals_output=root/'data/main/preparation_v2/repope_vi_proposals_v1.json',
        image_manifest=root/'data/main/preparation_v1/repope_draft_manifest.csv',
        bilingual_output=root/'data/main/preparation_v2/repope_bilingual_draft_manifest.csv')
    if args.report:
        target=root/args.report
        content=(json.dumps(report,indent=2)+'\n').encode()
        if target.exists() and target.read_bytes()!=content:raise ValueError('Report differs; use new path')
        if not target.exists():atomic_bytes(target,content)
    print(json.dumps(report,indent=2))
