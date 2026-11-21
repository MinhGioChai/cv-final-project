"""Unfrozen RePOPE main candidate sampling; no image materialization or approvals."""
from collections import Counter, defaultdict
import random

from .sampling import SamplingError, STRATA


def sample_repope_candidates(rows, *, size=600, seed=42, max_rows_per_image=2, unique_content=True):
    if size < 6 or size % 6 or max_rows_per_image < 1:
        raise ValueError("Use six equal quotas and a positive image cap")
    if not rows or len({r.sample_id for r in rows}) != len(rows):
        raise ValueError("Source candidates must be nonempty with unique IDs")
    if any(r.source_dataset != 'repope' or r.task != 'object_existence' or
           (r.category, r.ground_truth) not in STRATA for r in rows):
        raise ValueError("Expected RePOPE candidates in the six source strata")
    # An identical image/question with conflicting source labels needs audit, not deduplication.
    truths = defaultdict(set)
    for r in rows:truths[(r.image_namespace, r.image_id, r.question_en)].add(r.ground_truth)
    if any(len(s) > 1 for s in truths.values()):
        raise ValueError("Conflicting labels for identical image/question; audit before sampling")
    buckets = defaultdict(list)
    for r in sorted(rows, key=lambda r:r.source_row_id):buckets[(r.category,r.ground_truth)].append(r)
    rng = random.Random(seed)
    for key in STRATA:rng.shuffle(buckets[key])
    order = sorted(STRATA, key=lambda key:(len(buckets[key]),STRATA.index(key)))
    counts, seen, selected = Counter(), set(), []
    quota = size // 6
    for key in order:
        picked = 0
        for row in buckets[key]:
            if picked == quota:break
            image = (row.image_namespace,row.image_id)
            content = (*image,row.question_en,str(row.ground_truth))
            if counts[image] >= max_rows_per_image or (unique_content and content in seen):continue
            selected.append(row);counts[image]+=1;seen.add(content);picked+=1
        if picked != quota:
            raise SamplingError({'failed_stratum':'/'.join(key),'target':size,'selected':len(selected),
                                 'reason':'No automatic scope/cap relaxation'})
    selected.sort(key=lambda r:r.source_row_id)
    content_counts=Counter((r.image_namespace,r.image_id,r.question_en,str(r.ground_truth)) for r in selected)
    return selected, {'scope':'unfrozen_metadata_selection_not_main_manifest','seed':seed,'rows':len(selected),
        'unique_image_refs':len(counts),'max_rows_per_image':max(counts.values()),
        'content_duplicates':sum(n-1 for n in content_counts.values()),'unique_content_policy':unique_content,
        'quotas':{'/'.join(k):quota for k in STRATA},'strata':dict(Counter('/'.join((r.category,r.ground_truth)) for r in selected)),
        'algorithm':'stable-source-ID ordering, seeded bucket shuffles, scarcity-first greedy, global image cap and optional content uniqueness'}
