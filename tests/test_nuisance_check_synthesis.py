from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

from latent_landscapes import nuisance_check_synthesis as checks
from latent_landscapes import null_effect_synthesis as frozen


def fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    rng = np.random.default_rng(9055)
    n, r, j = 20, 99, 3
    betas, effects = np.asarray([-1.0, 0, 1]), np.asarray([1.0, 2, 3])
    result = []
    for cells in (checks.NEW_CELLS, frozen.CELL_IDS):
        c = len(cells)
        panel = {
            key: rng.exponential(4, size=(n, c, j) if key.endswith("d_beta") else (n, c))
            for key in checks.EVALUATION_KEYS
        }
        for key in ("evaluation_h_hat_adj", "evaluation_h_hat_constant"):
            panel[key] = rng.choice(effects, size=(n, c))
        for key in ("evaluation_beta_hat_adj", "evaluation_beta_hat_null"):
            panel[key] = rng.choice(betas, size=(n, c))
        panel.update(
            cell_ids=np.asarray(cells),
            truth_h=np.tile([1.0, 3.0], c // 2),
            betas=betas,
            effects=effects,
        )
        result.append(panel)
    result[1].update(
        reference_t_adj=rng.exponential(1, size=(r, j)),
        reference_t_constant=rng.exponential(1, size=r),
        reference_d_beta=rng.exponential(1, size=(r, j)),
    )
    ids054 = np.asarray([[f"054-{i}-{j}" for j in range(4)] for i in range(n)])
    ids051 = np.asarray([[f"051-{i}-{j}" for j in range(4)] for i in range(n)])
    result[0].update(
        supplied_mean=np.repeat([0.0016, 0.0025, 0.002], 4),
        archive_ids=np.concatenate((ids054, ids054, ids051), axis=1),
    )
    return result[0], result[1]


def direct_primary(values: dict[str, Any], index: NDArray[Any]) -> NDArray[Any]:
    # Independently count the conservative plus-one upper tails at every node.
    tail = 1 + (
        values["reference_t_adj"][index][None, None, :, :]
        >= values["evaluation_t_adj"][:, :, None, None] - 1e-12
    ).sum(axis=2)
    return np.all(tail / (len(index) + 1) <= 0.05, axis=-1)


def test_join_preserves_correct_mean_pairing_and_refuses_ambiguous_archives() -> None:
    new, reference = fixture()
    joined = checks.combine_inputs(new, reference, strict=False)
    for key in checks.EVALUATION_KEYS:
        np.testing.assert_array_equal(joined[key][:, :12], new[key])
        np.testing.assert_array_equal(joined[key][:, 12:], reference[key][:, :4])
    wrong = dict(new)
    wrong["cell_ids"] = new["cell_ids"][::-1]
    with pytest.raises(ValueError, match="cell order"):
        checks.combine_inputs(wrong, reference, strict=False)
    wrong = dict(new)
    wrong["effects"] = new["effects"] + 0.01
    with pytest.raises(ValueError, match="grid differs"):
        checks.combine_inputs(wrong, reference, strict=False)
    with pytest.raises(ValueError, match="dimensions"):
        checks.combine_inputs(new, reference)


def test_join_rejects_mean_and_archive_pairing_metadata_corruption() -> None:
    new, reference = fixture()
    wrong = {**new, "supplied_mean": np.full(12, 0.002)}
    with pytest.raises(ValueError, match="supplied mean"):
        checks.combine_inputs(wrong, reference, strict=False)
    wrong = {**new, "archive_ids": new["archive_ids"].copy()}
    wrong["archive_ids"][:, 4:8] = wrong["archive_ids"][::-1, 4:8]
    with pytest.raises(ValueError, match="identical Goal054 histories"):
        checks.combine_inputs(wrong, reference, strict=False)
    wrong = {**new, "archive_ids": new["archive_ids"].copy()}
    wrong["archive_ids"][1, 8:] = wrong["archive_ids"][0, 8:]
    with pytest.raises(ValueError, match="duplicate histories"):
        checks.combine_inputs(wrong, reference, strict=False)


def test_resampling_pairs_only_within_each_archive() -> None:
    array = np.arange(5 * 16 * 2).reshape(5, 16, 2)
    a, b = np.asarray([4, 4, 1]), np.asarray([0, 2, 3])
    sampled = checks.paired_sample(array, a, b)
    for col in range(16):
        np.testing.assert_array_equal(sampled[:, col], array[b if 8 <= col < 12 else a, col])


def test_registered_rule_counting_retains_ties_at_full_supremum_cutoff() -> None:
    new, reference = fixture()
    reference["reference_t_adj"] = np.repeat(np.arange(99.0)[:, None], 3, axis=1)
    new["evaluation_t_adj"][:] = 95
    new["evaluation_t_adj"][:, 0] = 94
    new["evaluation_t_adj"][:, 1] = 94 + 0.5e-12
    values = checks.combine_inputs(new, reference, strict=False)
    rules, _ = checks.rules_for_reference(values, verify_direct=True)
    expected = direct_primary(values, np.arange(99))
    np.testing.assert_array_equal(rules[..., 0], expected)
    assert not rules[:, :2, 0].any()
    assert rules[:, 2:12, 0].all()


def test_saved_bootstrap_reconstructs_two_archive_counts_and_design_flags(tmp_path: Path) -> None:
    new, reference = fixture()
    new_path, ref_path = tmp_path / "new.npz", tmp_path / "reference.npz"
    np.savez(new_path, **new)
    np.savez(ref_path, **reference)
    output = tmp_path / "synthesis"
    summary = checks.synthesize(new_path, ref_path, output, bootstrap_draws=8, strict=False)
    values = checks.combine_inputs(new, reference, strict=False)
    with np.load(output / "bootstrap_draws.npz") as saved:
        for draw in range(8):
            decisions = direct_primary(values, saved["reference_indices"][draw])
            expected = np.empty(16)
            for col in range(16):
                which = "goal051_indices" if 8 <= col < 12 else "goal054_indices"
                expected[col] = decisions[saved[which][draw], col].mean()
            np.testing.assert_array_equal(
                saved["rule_rates_calibration_aware"][draw, :, 0], expected
            )
        rates = saved["rule_rates_calibration_aware"]
        absolute = np.quantile(rates[:, 10, 0], 0.025) > 0.05
        paired = np.quantile(rates[:, 10, 0] - rates[:, 8, 0], 0.025) > 0
        assert summary["detection_absolute_failure"] == absolute
        assert summary["detection_paired_increase"] == paired
        assert summary["detection_repair_prerequisite"] == (absolute or paired)
    for filename, expected_hash in summary["output_hashes"].items():
        assert checks.sha256(output / filename) == expected_hash
    assert json.loads((output / "summary.json").read_text()) == summary
    assert (output / "nuisance_checks.png").is_file()
    assert summary["no_recalibration_adopted"]
    with pytest.raises(FileExistsError):
        checks.synthesize(new_path, ref_path, output, bootstrap_draws=8, strict=False)


def test_production_refuses_different_reference_or_draw_count(tmp_path: Path) -> None:
    new, reference = fixture()
    new_path, ref_path = tmp_path / "new.npz", tmp_path / "reference.npz"
    np.savez(new_path, **new)
    np.savez(ref_path, **reference)
    with pytest.raises(ValueError, match="2,000"):
        checks.synthesize(new_path, ref_path, tmp_path / "bad_draws", bootstrap_draws=8)
    with pytest.raises(ValueError, match="reference/evaluation table changed"):
        checks.synthesize(new_path, ref_path, tmp_path / "bad_reference")
