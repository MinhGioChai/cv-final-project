"""Seeded category × label selection with an explicit image cap."""

from collections import Counter, defaultdict
import random
from typing import Any

CATEGORIES = ("random", "popular", "adversarial")
STRATA = tuple((category, label) for category in CATEGORIES for label in ("yes", "no"))


class SamplingError(ValueError):
    def __init__(self, report: dict[str, Any]):
        self.report = report
        super().__init__("Sampling target is infeasible within the bounded pool; see feasibility report")


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(row["image_id"] for row in rows)
    values = sorted(counts.values())
    n = len(values)
    median = (values[n // 2] + values[(n - 1) // 2]) / 2 if n else 0
    return {
        "n_rows": len(rows),
        "n_unique_images": n,
        "rows_per_image": {"median": median, "max": max(values, default=0)},
        "strata": dict(sorted(Counter(f"{row['category']}/{row['answer']}" for row in rows).items())),
    }


def stratified_sample(
    pool: list[dict[str, Any]], *, size: int, seed: int,
    max_rows_per_image: int = 1, excluded_images: set[str] | None = None,
    retained_source_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if size < 6 or max_rows_per_image < 1:
        raise ValueError("Need at least 6 rows and a positive image cap")
    ids = [row["source_row_id"] for row in pool]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate source_row_id in candidate pool")
    if any((row["category"], row["answer"]) not in STRATA for row in pool):
        raise ValueError("Unknown category or label in candidate pool")
    # Base quota in each of six strata; paired remainders keep labels balanced.
    quotas = {key: size // 6 for key in STRATA}
    remainder_order = (STRATA[0], STRATA[1], STRATA[2], STRATA[5], STRATA[4], STRATA[3])
    for key in remainder_order[:size % 6]:
        quotas[key] += 1
    retained_ids = retained_source_ids or set()
    if not retained_ids.issubset(set(ids)):
        raise ValueError("Retained source IDs are missing from the candidate pool")
    selected = [row for row in sorted(pool, key=lambda row: row["source_row_id"]) if row["source_row_id"] in retained_ids]
    retained_counts = Counter((row["category"], row["answer"]) for row in selected)
    image_counts: Counter = Counter(row["image_id"] for row in selected)
    if (any(count > max_rows_per_image for count in image_counts.values())
            or any(retained_counts[key] > quotas[key] for key in STRATA)
            or any(row["image_id"] in (excluded_images or set()) for row in selected)):
        raise ValueError("Retained rows conflict with target quotas, image cap, or exclusions")
    buckets = defaultdict(list)
    for row in sorted(pool, key=lambda row: row["source_row_id"]):
        if row["image_id"] not in (excluded_images or set()) and row["source_row_id"] not in retained_ids:
            buckets[(row["category"], row["answer"])].append(row)
    rng = random.Random(seed)
    for key in STRATA:
        rng.shuffle(buckets[key])
    # Smallest candidate sets first reduces conflicts over shared image IDs.
    order = sorted(STRATA, key=lambda key: (len(buckets[key]), STRATA.index(key)))
    for key in order:
        needed = quotas[key] - retained_counts[key]
        picked = 0
        for row in buckets[key]:
            if picked >= needed:
                break
            if image_counts[row["image_id"]] >= max_rows_per_image:
                continue
            selected.append(row)
            image_counts[row["image_id"]] += 1
            picked += 1
        if picked != needed:
            raise SamplingError({
                "scope": "bounded_stage0_pool_not_full_dataset",
                "target": size, "seed": seed, "max_rows_per_image": max_rows_per_image,
                "available": summarize(pool), "selected": summarize(selected),
                "failed_stratum": "/".join(key),
                "reason": "Quota not reached with current deterministic greedy selection; no automatic cap relaxation",
            })
    selected.sort(key=lambda row: row["source_row_id"])
    report = {
        "scope": "bounded_stage0_pool_not_full_dataset", "seed": seed,
        "requested": size, "max_rows_per_image": max_rows_per_image,
        "quotas": {"/".join(key): value for key, value in quotas.items()},
        "available": summarize(pool), "selected": summarize(selected),
    }
    if retained_source_ids is not None:
        report["retained_rows"] = len(retained_ids)
        report["added_rows"] = len(selected) - len(retained_ids)
        report["scope"] = "bounded_pilot_pool_not_full_dataset"
    return selected, report
