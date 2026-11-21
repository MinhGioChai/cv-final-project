from collections import Counter
import random

import pytest

from vlmbench.sampling import SamplingError, STRATA, stratified_sample


def candidate_pool():
    return [dict(source_row_id=f"{category}:{label}:{i}", category=category, answer=label,
                 image_id=f"{i:012}") for category, label in STRATA for i in range(30)]


def test_balanced_seeded_selection_with_image_cap():
    pool = candidate_pool()
    first, report = stratified_sample(pool, size=10, seed=42)
    shuffled = pool.copy()
    random.Random(7).shuffle(shuffled)
    second, _ = stratified_sample(shuffled, size=10, seed=42)
    assert first == second
    assert len(first) == len({row["source_row_id"] for row in first}) == 10
    assert len({row["image_id"] for row in first}) == 10
    assert Counter(row["answer"] for row in first) == {"yes": 5, "no": 5}
    assert set((row["category"], row["answer"]) for row in first) == set(STRATA)
    assert report["selected"]["rows_per_image"]["max"] == 1


def test_excluded_images_never_selected():
    excluded = {f"{i:012}" for i in range(10)}
    selected, _ = stratified_sample(candidate_pool(), size=10, seed=42, excluded_images=excluded)
    assert not excluded.intersection(row["image_id"] for row in selected)


def test_cannot_silently_relax_cap_or_duplicate_rows():
    pool = candidate_pool()
    for row in pool:
        row["image_id"] = "same_image"
    with pytest.raises(SamplingError) as exc:
        stratified_sample(pool, size=10, seed=42)
    assert exc.value.report["max_rows_per_image"] == 1


def test_missing_stratum_has_feasibility_report():
    pool = [row for row in candidate_pool() if row["answer"] == "yes"]
    with pytest.raises(SamplingError) as exc:
        stratified_sample(pool, size=10, seed=42)
    assert exc.value.report["target"] == 10


def test_duplicate_source_ids_fail():
    pool = candidate_pool()
    with pytest.raises(ValueError, match="Duplicate"):
        stratified_sample(pool + [pool[0]], size=10, seed=42)


def test_expansion_keeps_previous_rows_and_fills_total_quotas():
    pool = candidate_pool()
    base, _ = stratified_sample(pool, size=10, seed=42)
    ids = {row["source_row_id"] for row in base}
    expanded, report = stratified_sample(pool, size=30, seed=42, retained_source_ids=ids)
    assert ids.issubset(row["source_row_id"] for row in expanded)
    assert len({row["image_id"] for row in expanded}) == 30
    assert Counter((row["category"], row["answer"]) for row in expanded) == {key: 5 for key in STRATA}
    assert report["retained_rows"] == 10 and report["added_rows"] == 20
    shuffled = pool.copy()
    random.Random(11).shuffle(shuffled)
    assert stratified_sample(shuffled, size=30, seed=42, retained_source_ids=ids)[0] == expanded


def test_retained_unknown_row_cannot_be_dropped_silently():
    with pytest.raises(ValueError, match="missing"):
        stratified_sample(candidate_pool(), size=30, seed=42, retained_source_ids={"unknown"})


def test_retained_rows_exceeding_final_stratum_quota_fail():
    pool = candidate_pool()
    ids = {row["source_row_id"] for row in pool if row["category"] == "random" and row["answer"] == "yes" and int(row["image_id"]) < 6}
    with pytest.raises(ValueError, match="conflict"):
        stratified_sample(pool, size=30, seed=42, retained_source_ids=ids)


def test_retention_cannot_override_image_exclusions():
    pool = candidate_pool()
    base, _ = stratified_sample(pool, size=10, seed=42)
    with pytest.raises(ValueError, match="conflict"):
        stratified_sample(pool, size=30, seed=42, retained_source_ids={row["source_row_id"] for row in base}, excluded_images={base[0]["image_id"]})
