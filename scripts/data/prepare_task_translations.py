"""Generate versioned source-bound proposals and merge available image drafts."""
import json
from pathlib import Path

from vlmbench.io_utils import atomic_bytes,manifest_bytes,read_manifest,sha256_file,write_json
from vlmbench.task_images import selected_source
from vlmbench.task_translations import propose_vsr,propose_tallyqa
from vlmbench.translate import load_dictionary
from vlmbench.schemas import ManifestRow

TALLY_SELECTION_SHA256='e507751701739160d43beb6de3eff6271d20216910a4c39efad627ba4d4697e0'


def prepare(root):
    nouns={k:' '.join(x for x in (v['classifier_vi'],v['object_vi']) if x)
           for k,v in load_dictionary(root/'data/dictionaries/object_en_vi.csv').items()}
    nouns.update(json.loads((root/'data/dictionaries/main_object_vi_proposals_v1.json').read_text(encoding='utf-8'))['phrases'])
    glossary_path=root/'data/dictionaries/vsr_relations_vi_draft_v1.json'
    lines_path=root/'data/dictionaries/tallyqa_vi_draft_lines_v1.txt'
    glossary=json.loads(glossary_path.read_text(encoding='utf-8'))
    outputs={};reports={}
    for dataset in ['vsr','tallyqa','oxford_pet']:
        rows,selection=selected_source(root,dataset)
        if dataset=='vsr':proposals=propose_vsr(rows,nouns,glossary)
        elif dataset=='tallyqa':proposals=propose_tallyqa(rows,lines_path.read_text(encoding='utf-8').splitlines(),
            expected_selection_sha256=TALLY_SELECTION_SHA256,actual_selection_sha256=sha256_file(selection))
        else:
            proposals=[{'sample_id':r.sample_id,'question_en':r.question_en,'question_vi':'Con chó trong ảnh thuộc giống nào?',
                'source_record_sha256':r.source_record_sha256,'translation_status':'requires_review',
                'review_note':'Giữ tên giống và mapping A–H giống hệt EN; đây là phân loại tám giống chó đã chọn.',
                'human_approval_created':False} for r in rows]
        payload={'scope':'assistant_draft_not_human_review','selection_sha256':sha256_file(selection),
            'glossary_sha256':sha256_file(glossary_path) if dataset=='vsr' else sha256_file(lines_path) if dataset=='tallyqa' else None,
            'rows':proposals,'human_approvals_created':0}
        path=root/f'data/main/preparation_v3/{dataset}_vi_proposals.json'
        outputs[path]=(json.dumps(payload,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
        images=root/f'data/main/preparation_v3/{dataset}_image_draft.csv'
        merged=False
        if images.exists():
            materialized=read_manifest(images);by_id={r.sample_id:r for r in rows};drafts={r['sample_id']:r for r in proposals}
            if len(materialized)!=len(rows) or {r.sample_id for r in materialized}!=set(by_id):
                raise ValueError('Image draft IDs differ')
            bilingual=[]
            for image in materialized:
                source=by_id[image.sample_id];proposal=drafts[image.sample_id]
                if image.question_en!=source.question_en or image.ground_truth!=source.ground_truth or image.translation_status=='approved':
                    raise ValueError('Source fields changed or translation already approved')
                data=image.model_dump();data.update(question_vi=proposal['question_vi'],translation_status='requires_review')
                data['metadata']['translation_draft']={'selection_sha256':payload['selection_sha256'],
                    'origin':'assistant_draft','review_note':proposal['review_note'],'human_approval_created':False}
                if dataset=='oxford_pet':
                    data['metadata']['candidate_labels']={v:k.replace('_',' ').title() for k,v in source.metadata['candidate_map'].items()}
                bilingual.append(ManifestRow.model_validate(data))
            outputs[root/f'data/main/preparation_v3/{dataset}_bilingual_draft.csv']=manifest_bytes(bilingual)
            merged=True
        reports[dataset]={'rows':len(rows),'requires_review':len(proposals),'approved':0,'bilingual_draft_created':merged}
    # Validate every existing output before publishing any new version.
    for path,content in outputs.items():
        if path.exists() and path.read_bytes()!=content:raise ValueError('Output changed; use a new version')
    for path,content in outputs.items():
        if not path.exists():atomic_bytes(path,content)
    return {'datasets':reports,'human_approvals_created':0,
        'outputs':{p.relative_to(root).as_posix():sha256_file(p) for p in outputs}}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',required=True);args=p.parse_args()
    root=Path.cwd().resolve();path=(root/args.report).resolve()
    if not path.is_relative_to(root) or path.exists():raise ValueError('Use a new report path inside project')
    result=prepare(root);write_json(path,result);print(json.dumps(result,indent=2))
