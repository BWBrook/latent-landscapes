from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from latent_landscapes.null_effect_synthesis import (
    CELL_IDS,
    decision_rule,
    pvalues,
    synthesize,
)


def test_plus_one_pvalues_retain_ties_and_scalar_observations() -> None:
    reference = np.arange(1.0, 20.0)[:, None]
    observed = np.asarray([19.0, 20.0])
    values = pvalues(observed, np.repeat(reference, 2, axis=1))
    np.testing.assert_allclose(values, [[0.10, 0.10], [0.05, 0.05]])


def test_decision_rule_matches_dynamic_order_statistics_and_empty_bb() -> None:
    reference = np.arange(1.0, 20.0)[:, None]
    t_adj = np.full((1, 8), 20.0)
    t_adj[0, 1] = 19.0
    result = decision_rule(
        t_adj,
        np.repeat(reference, 3, axis=1),
        t_constant=np.full((1, 8), 20.0),
        reference_t_constant=np.arange(1.0, 20.0),
        d_beta=np.full((1, 8, 3), 100.0),
        reference_d_beta=np.repeat(reference, 3, axis=1),
    )
    assert np.asarray(result["primary"])[0, 0]
    assert not np.asarray(result["primary"])[0, 1]
    # The small fixture has no attainable .04 tail, so Berger--Boos is empty
    # as a rejection rule even though q_j is above .01 for every candidate.
    np.testing.assert_array_equal(result["berger_boos"], False)


def test_registered_r999_cutoff_ranks_are_950_960_and_990() -> None:
    reference = np.repeat(np.arange(999.0)[:, None], 81, axis=1)
    result = decision_rule(
        np.asarray([[950.0]]),
        reference,
        t_constant=np.asarray([[950.0]]),
        reference_t_constant=np.arange(999.0),
        d_beta=np.full((1, 1, 81), 1001.0),
        reference_d_beta=reference,
    )
    np.testing.assert_array_equal(result["primary_cutoff"], 949.0)
    np.testing.assert_array_equal(result["berger_boos_t_cutoff"], 959.0)
    np.testing.assert_array_equal(result["q_d_cutoff"], 989.0)
    assert np.asarray(result["primary"])[0, 0]
    # A tied statistic at the 950th ordered reference value remains excluded.
    tied = decision_rule(
        np.asarray([[949.0]]),
        reference,
        t_constant=np.asarray([[949.0]]),
        reference_t_constant=np.arange(999.0),
        d_beta=np.full((1, 1, 81), 1001.0),
        reference_d_beta=reference,
    )
    assert not np.asarray(tied["primary"])[0, 0]


def _fixture(path: Path) -> None:
    rng = np.random.default_rng(12)
    n, r, j = 20, 19, 3
    np.savez(
        path,
        reference_t_adj=rng.normal(size=(r, j)),
        reference_t_constant=rng.normal(size=r),
        reference_d_beta=rng.normal(size=(r, j)),
        evaluation_t_adj=rng.normal(size=(n, 8)),
        evaluation_t_constant=rng.normal(size=(n, 8)),
        evaluation_d_beta=rng.normal(size=(n, 8, j)),
        evaluation_h_hat_adj=np.exp(rng.normal(size=(n, 8))),
        evaluation_beta_hat_adj=rng.normal(size=(n, 8)),
        evaluation_h_hat_constant=np.exp(rng.normal(size=(n, 8))),
        evaluation_beta_hat_null=rng.normal(size=(n, 8)),
        evaluation_delta_holdout_adj_constant=rng.normal(size=(n, 8)),
        evaluation_delta_holdout_adj_neutral=rng.normal(size=(n, 8)),
        evaluation_delta_holdout_constant_neutral=rng.normal(size=(n, 8)),
        betas=np.asarray([-1.0, 0.0, 1.0]),
        effects=np.linspace(1.0, 3.0, 5),
        cell_ids=np.asarray(CELL_IDS),
        truth_h=np.tile([1.0, 3.0], 4),
        truth_beta=np.zeros(8),
    )


def test_synthesize_writes_hash_bound_outputs_and_is_strict_about_production(
    tmp_path: Path,
) -> None:
    input_npz = tmp_path / "stats.npz"
    _fixture(input_npz)
    output = tmp_path / "synthesis"
    output.mkdir()
    (output / "launch.json").write_text("{}")
    (output / "attempts").mkdir()
    summary = synthesize(input_npz, output, bootstrap_draws=5, strict=False)
    assert summary["bootstrap_draws"] == 5
    assert summary["input_sha256"]
    assert "summary.json" not in summary["output_hashes"]
    assert (output / "cutoff_curve.png").is_file()
    assert (output / "cutoff_curve.pdf").is_file()
    assert (output / "declaration_rates.png").is_file()
    assert json.loads((output / "summary.json").read_text())["input_sha256"] == summary[
        "input_sha256"
    ]
    with pytest.raises(ValueError, match="2,000"):
        synthesize(input_npz, tmp_path / "strict", bootstrap_draws=5, strict=True)
