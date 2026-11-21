import json

import pytest

from vlmbench.datasets.repope_frame import parse_repope_frame
from vlmbench.main_sampling import sample_repope_candidates
from vlmbench.sampling import SamplingError


def frame():
    content={}
    for category in ('random','popular','adversarial'):
        records=[]
        for i in range(20):
            records.append({'image':f'COCO_val2014_{i:012}.jpg','text':f'synthetic_test_only {i}?',
                            'label':'yes' if i%2 else 'no','question_id':i})
        content[category]='\n'.join(json.dumps(r) for r in records).encode()
    return parse_repope_frame(content,revision='synthetic_test_only')


def test_main_sampling_reproducible_unique_content_and_six_quotas():
    a,report=sample_repope_candidates(frame(),size=12,seed=42,max_rows_per_image=2,unique_content=True)
    b,_=sample_repope_candidates(list(reversed(frame())),size=12,seed=42,max_rows_per_image=2,unique_content=True)
    assert [r.sample_id for r in a]==[r.sample_id for r in b]
    assert report['content_duplicates']==0 and set(report['strata'].values())=={2}
    assert report['max_rows_per_image']<=2


def test_source_category_duplicates_are_only_retained_when_explicitly_requested():
    rows,report=sample_repope_candidates(frame(),size=60,max_rows_per_image=3,unique_content=False)
    assert len(rows)==60 and report['content_duplicates']==40


def test_infeasible_quotas_never_relax_cap_or_target():
    with pytest.raises(SamplingError):sample_repope_candidates(frame(),size=60,max_rows_per_image=1,unique_content=True)


def test_conflicting_source_labels_need_audit_not_deduplication():
    rows=frame()
    rows[-1]=rows[-1].model_copy(update={'ground_truth':'no' if rows[-1].ground_truth=='yes' else 'yes'})
    with pytest.raises(ValueError,match='Conflicting'):sample_repope_candidates(rows,size=6)


@pytest.mark.parametrize('size',[0,7])
def test_main_sampling_equal_quota_contract(size):
    with pytest.raises(ValueError):sample_repope_candidates(frame(),size=size)
