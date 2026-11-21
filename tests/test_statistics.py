"""Cluster bootstrap tests on analytically specified synthetic paired outcomes."""
import pytest

from vlmbench.evaluate import Observation, PairedSample
from vlmbench.statistics import paired_cluster_bootstrap


def pair(index, *, image=None, namespace="coco", en="no", vi="yes", truth="no"):
    return PairedSample(sample_id=f"synthetic_{index}", dataset="repope", task="object_existence", category="random",
                        image_namespace=namespace, image_id=str(index if image is None else image), image_sha256="0" * 64,
                        ground_truth=truth, ground_truth_source="synthetic_test_only", is_pilot=True,
                        qa_status="pending", translation_status="requires_review",
                        en=Observation(status="valid", prediction=en), vi=Observation(status="valid", prediction=vi))


def test_clusters_keep_multiple_questions_together_and_use_pooled_row_weighting():
    pairs = [pair(i, image="A") for i in range(3)] + [pair(4, image="B", en="yes", vi="no")]
    result = paired_cluster_bootstrap(pairs, metric="delta_fpr_pp", n_resamples=500, seed=11)
    # Cluster A contributes +3/3, B contributes -1/1. Pooled estimate is +2/4.
    # The three possible resampled estimates are +100, +50 and -100 pp.
    assert result["estimate_pp"] == 50
    assert (result["lower_pp"], result["upper_pp"]) == (-100, 100)
    assert result["n_image_clusters"] == 2 and result["n_rows"] == 4
    assert result == paired_cluster_bootstrap(list(reversed(pairs)), metric="delta_fpr_pp", n_resamples=500, seed=11)


def test_identical_predictions_produce_zero_gap_and_deterministic_degenerate_interval():
    pairs = [pair(i, en="no", vi="no") for i in range(5)]
    result = paired_cluster_bootstrap(pairs, metric="delta_fpr_pp", n_resamples=100)
    assert result["estimate_pp"] == result["lower_pp"] == result["upper_pp"] == 0
    assert result["empirical_distribution_degenerate"]


def test_primary_is_conditional_on_jointly_valid_negative_images():
    rows = [pair(1), pair(2), pair(3, truth="yes"), pair(4)]
    rows[3].vi = Observation(status="invalid", reason="INVALID_FORMAT")
    result = paired_cluster_bootstrap(rows, metric="delta_fpr_pp", n_resamples=100)
    assert result["n_rows"] == result["n_image_clusters"] == 2
    assert result["estimate_pp"] == 100


def test_accuracy_scores_missing_as_incorrect_and_preserves_pairing():
    rows = [pair(1, en="no", vi="no"), pair(2, en="no", vi="no")]
    rows[0].vi = Observation(status="missing")
    result = paired_cluster_bootstrap(rows, metric="delta_accuracy_pp", n_resamples=100)
    assert result["estimate_pp"] == -50
    assert result["lower_pp"] == -100 and result["upper_pp"] == 0


def test_empty_and_one_image_have_explicit_undefined_uncertainty():
    empty = paired_cluster_bootstrap([], metric="delta_fpr_pp")
    assert empty["estimate_pp"] is None and empty["status"] == "no_eligible_rows"
    one_image = paired_cluster_bootstrap([pair(1, image="A"), pair(2, image="A")], metric="delta_fpr_pp")
    assert one_image["estimate_pp"] == 100 and one_image["lower_pp"] is None
    assert one_image["n_resamples_used"] == 0 and one_image["status"] == "uncertainty_not_estimable_one_image"


def test_namespace_disambiguates_image_ids():
    result = paired_cluster_bootstrap([pair(1, image="1"), pair(2, image="1", namespace="other")],
                                      metric="delta_fpr_pp", n_resamples=100)
    assert result["n_image_clusters"] == 2


@pytest.mark.parametrize("kwargs", [{"n_resamples": 0}, {"n_resamples": True}, {"seed": False},
                                    {"confidence_level": 1}, {"metric": "unknown"}])
def test_invalid_bootstrap_settings_are_rejected(kwargs):
    settings = {"metric": "delta_fpr_pp", **kwargs}
    with pytest.raises(ValueError):
        paired_cluster_bootstrap([pair(1), pair(2)], **settings)


def test_duplicate_pair_cannot_inflate_bootstrap_sample():
    row = pair(1)
    with pytest.raises(ValueError, match="unique"):
        paired_cluster_bootstrap([row, row], metric="delta_fpr_pp")
