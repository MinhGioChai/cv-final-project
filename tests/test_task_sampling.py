import pytest

from vlmbench.datasets.candidates import candidate
from vlmbench.task_sampling import count_bin,proportional_quotas,sample_task,select_quotas


def make(i,*,dataset,truth,category,task):
    return candidate(dataset=dataset,split='synthetic_test_only',revision='synthetic_test_only',row_id=str(i),
        record={'synthetic_test_only':i},namespace='synthetic_test_only',image_id=str(i),image_ref=str(i)+'.jpg',
        task=task,category=category,question='synthetic_test_only?',truth=truth)


def test_vsr_preserves_60_per_label_and_relation_diversity():
    rows=[make(i,dataset='vsr',truth='yes' if i<70 else 'no',category='relation_'+str(i%5),task='spatial') for i in range(140)]
    a,report=sample_task(rows,dataset='vsr')
    b,_=sample_task(list(reversed(rows)),dataset='vsr')
    assert [r.sample_id for r in a]==[r.sample_id for r in b]
    assert report['labels']=={'yes':60,'no':60} or report['labels']=={'no':60,'yes':60}
    assert len(a)==report['unique_image_refs']==120 and len(report['categories'])==5


def test_tally_preserves_counts_and_group_targets():
    rows=[]
    for group in ('simple','complex'):
        for value,n in ((0,10),(1,40),(2,30),(3,20),(4,10),(8,10)):
            for _ in range(n):rows.append(make(len(rows),dataset='tallyqa',truth=value,category=group,task='counting'))
    chosen,report=sample_task(rows,dataset='tallyqa')
    assert report['categories']=={'simple':60,'complex':60}
    assert len(chosen)==120 and set(report['quotas'])=={g+'/'+b for g in ('simple','complex') for b in ('0','1','2','3','4-7','8+')}
    source={r.sample_id:r for r in rows}
    assert all(source[r.sample_id]==r for r in chosen)


def test_pet_fixed_20_per_label():
    rows=[make(i,dataset='oxford_pet',truth='ABCDEFGH'[i//25],category='breed_'+str(i//25),task='fine_grained') for i in range(200)]
    chosen,report=sample_task(rows,dataset='oxford_pet')
    assert len(chosen)==160 and set(report['labels'].values())=={20}


def test_image_collision_cannot_silently_relax_quota():
    rows=[make(i,dataset='vsr',truth='yes' if i==0 else 'no',category='synthetic',task='spatial') for i in range(2)]
    rows[1]=rows[1].model_copy(update={'image_id':rows[0].image_id})
    with pytest.raises(ValueError,match='cap'):
        select_quotas(rows,{'yes':1,'no':1},stratum=lambda r:r.ground_truth)


@pytest.mark.parametrize('total',[1,20])
def test_infeasible_proportional_quotas_rejected(total):
    with pytest.raises(ValueError):proportional_quotas({'0':3,'1':4},total)


def test_proportional_sum_minimum_and_capacity():
    result=proportional_quotas({'0':1,'1':20,'8+':2},10)
    assert sum(result.values())==10 and result['0']==1 and 1<=result['8+']<=2


@pytest.mark.parametrize('value',[-1,True,'2'])
def test_bad_count_bin_input_rejected(value):
    with pytest.raises(ValueError):count_bin(value)
