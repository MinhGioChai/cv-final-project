"""Deterministic paired percentile bootstrap with image clusters."""

from collections import defaultdict
import math
import random

from .evaluate import PairedSample, image_key, is_correct


def _percentile(values: list[float], probability: float) -> float:
    position = (len(values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def paired_cluster_bootstrap(
    pairs: list[PairedSample], *, metric: str, n_resamples: int = 5000, seed: int = 42,
    confidence_level: float = 0.95,
) -> dict:
    if type(n_resamples) is not int or n_resamples < 1 or type(seed) is not int:
        raise ValueError("Bootstrap needs a positive integer resample count and an integer seed")
    if type(confidence_level) not in {int, float} or not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between zero and one")
    if metric not in {"delta_fpr_pp", "delta_accuracy_pp"}:
        raise ValueError("Choose delta_fpr_pp or delta_accuracy_pp")
    if len({pair.sample_id for pair in pairs}) != len(pairs):
        raise ValueError("Bootstrap paired sample IDs must be unique")
    clusters = defaultdict(lambda: [0, 0])
    for pair in sorted(pairs, key=lambda row: row.sample_id):
        if metric == "delta_fpr_pp":
            if (pair.dataset != "repope" or pair.task != "object_existence" or pair.ground_truth != "no"
                    or pair.en.status != "valid" or pair.vi.status != "valid"):
                continue
            difference = int(pair.vi.prediction == "yes") - int(pair.en.prediction == "yes")
        else:
            difference = int(is_correct(pair, "vi")) - int(is_correct(pair, "en"))
        cluster = clusters[image_key(pair)]
        cluster[0] += difference
        cluster[1] += 1
    values = [clusters[key] for key in sorted(clusters)]
    n_rows = sum(count for _, count in values)
    result = {"metric": metric, "unit": "image_namespace plus image_id", "weighting": "pooled rows within resampled images",
              "method": "percentile with linear quantile interpolation", "confidence_level": confidence_level,
              "seed": seed, "n_resamples_requested": n_resamples, "n_resamples_used": 0,
              "n_image_clusters": len(values), "n_rows": n_rows,
              "estimate_pp": 100 * sum(score for score, _ in values) / n_rows if n_rows else None,
              "lower_pp": None, "upper_pp": None}
    if len(values) < 2:
        result["status"] = "no_eligible_rows" if not values else "uncertainty_not_estimable_one_image"
        return result
    rng = random.Random(seed)
    estimates = []
    for _ in range(n_resamples):
        sampled = rng.choices(values, k=len(values))
        estimates.append(100 * sum(score for score, _ in sampled) / sum(count for _, count in sampled))
    estimates.sort()
    tail = (1 - confidence_level) / 2
    result.update(lower_pp=_percentile(estimates, tail), upper_pp=_percentile(estimates, 1 - tail),
                  n_resamples_used=n_resamples, status="ok",
                  empirical_distribution_degenerate=estimates[0] == estimates[-1])
    return result


def statistics_for_evaluation(report: dict, *, n_resamples: int = 5000, seed: int = 42) -> dict:
    pairs = [PairedSample.model_validate(row) for row in report["paired_rows"]]
    groups = defaultdict(list)
    for pair in pairs:
        groups[(pair.dataset, pair.task)].append(pair)
    return {"statistics_version": "paired_image_bootstrap_v1", "evaluation_hash": report["report_hash"],
            "scope": report["scope"], "run": report["run"],
            "primary_repope": paired_cluster_bootstrap(pairs, metric="delta_fpr_pp", n_resamples=n_resamples, seed=seed),
            "accuracy_by_task": [{"dataset": dataset, "task": task,
                                  **paired_cluster_bootstrap(subset, metric="delta_accuracy_pp", n_resamples=n_resamples, seed=seed)}
                                 for (dataset, task), subset in sorted(groups.items())],
            "interpretation": "Conditional empirical intervals on the selected data and scoring policy; scope and QA are recorded in the evaluation"}
