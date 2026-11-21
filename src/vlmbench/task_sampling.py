"""Seeded metadata selection for VSR/TallyQA/Pet; no model outputs or approvals."""
from collections import Counter, defaultdict
import random


def proportional_quotas(counts, total):
    counts={k:v for k,v in counts.items() if v>0}
    if total<len(counts) or total>sum(counts.values()):raise ValueError('Stratum allocation infeasible')
    quotas={k:1 for k in counts}
    # Reserve one per available count bin, then proportional remainder.
    remaining=total-len(counts)
    weights={k:v-1 for k,v in counts.items()}
    denominator=sum(weights.values())
    if remaining:
        floors={k:remaining*v//denominator for k,v in weights.items()}
        for k,n in floors.items():quotas[k]+=n
        order=sorted(counts,key=lambda k:(-(remaining*weights[k]%denominator),k))
        for k in order[:remaining-sum(floors.values())]:quotas[k]+=1
    return quotas


def count_bin(value):
    if type(value) is not int or value<0:raise ValueError('Nonnegative source count required')
    return str(value) if value<=3 else '4-7' if value<=7 else '8+'


def select_quotas(rows, quotas, *, stratum, seed=42, diverse=None):
    if not rows or len({r.sample_id for r in rows})!=len(rows):raise ValueError('Empty/duplicate candidates')
    rng=random.Random(seed)
    buckets=defaultdict(list)
    for row in sorted(rows,key=lambda r:r.sample_id):buckets[stratum(row)].append(row)
    if any(type(n) is not int or n<0 or n>len(buckets[k]) for k,n in quotas.items()):
        raise ValueError('Requested quota infeasible; no automatic reduction')
    selected,seen=[],set()
    for key in sorted(quotas,key=lambda k:(len(buckets[k]),k)):
        groups=defaultdict(list)
        for row in buckets[key]:groups[diverse(row) if diverse else 'all'].append(row)
        names=sorted(groups)
        rng.shuffle(names)
        for name in names:rng.shuffle(groups[name])
        picked=0
        while picked<quotas[key]:
            changed=False
            for name in names:
                if picked==quotas[key]:break
                while groups[name]:
                    row=groups[name].pop()
                    image=(row.image_namespace,row.image_id)
                    if image in seen:continue
                    seen.add(image);selected.append(row);picked+=1;changed=True;break
            if not changed:raise ValueError('Quota infeasible under one-row-per-image cap; no silent relaxation')
    selected.sort(key=lambda r:r.sample_id)
    return selected


def sample_task(rows, *, dataset, seed=42):
    if any(r.source_dataset!=dataset for r in rows):raise ValueError('Mixed datasets in task selection')
    if dataset=='vsr':
        quotas={'yes':60,'no':60}
        selected=select_quotas(rows,quotas,stratum=lambda r:r.ground_truth,seed=seed,diverse=lambda r:r.category)
        policy='60 TRUE/60 FALSE; round-robin relation diversity within labels; image cap1'
    elif dataset=='tallyqa':
        quotas={}
        for category in ('simple','complex'):
            counts=Counter(count_bin(r.ground_truth) for r in rows if r.category==category)
            quotas.update({category+'/'+k:v for k,v in proportional_quotas(counts,60).items()})
        selected=select_quotas(rows,quotas,stratum=lambda r:r.category+'/'+count_bin(r.ground_truth),seed=seed)
        policy='60 simple/60 complex; count bins 0,1,2,3,4-7,8+; min1 per available bin then proportional largest-remainder; image cap1'
    elif dataset=='oxford_pet':
        quotas={label:20 for label in 'ABCDEFGH'}
        selected=select_quotas(rows,quotas,stratum=lambda r:r.ground_truth,seed=seed)
        policy='20 per fixed A-H breed; seeded uniform within class; image cap1'
    else:raise ValueError('Only VSR/TallyQA/Pet are supported')
    return selected,{'dataset':dataset,'rows':len(selected),'unique_image_refs':len({(r.image_namespace,r.image_id) for r in selected}),
        'quotas':quotas,'labels':dict(Counter(str(r.ground_truth) for r in selected)),
        'categories':dict(Counter(r.category for r in selected)),'policy':policy,'seed':seed}
