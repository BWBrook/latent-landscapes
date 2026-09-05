from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from matplotlib import pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

from latent_landscapes import arc2c_synthesis as synthesis
from latent_landscapes.arc2c_design import LANES, TRUTHS, smoke_config
from latent_landscapes.goal002.calibration import wilson_interval


def _bundle() -> synthesis.CampaignBundle:
    config = smoke_config()
    c, n = len(TRUTHS), config.validation_replicates
    effects, rhos = np.asarray(config.effects), np.asarray(config.rhos)
    effect_truth = np.asarray([truth.effect for truth in TRUTHS])
    rho_truth = np.asarray([truth.rho for truth in TRUTHS])
    effect_drops = 2.0 * np.log(effects[None, :] / effect_truth[:, None]) ** 2
    rho_drops = 8.0 * np.log(rhos[None, :] / rho_truth[:, None]) ** 2
    effect_mle = np.broadcast_to(effect_truth[:, None, None], (c, 2, n)).copy()
    spread_mle = np.broadcast_to(rho_truth[:, None], (c, n)).copy()
    conditional = np.broadcast_to(np.arange(n) * 0.1, (c, 2, n)).copy()
    conditional[:, 1, :] += 0.2
    events = np.broadcast_to([30.0, 10.0, 20.0, 90.0, 1000.0, 400.0], (c, n, 6)).copy()
    profiles = {
        "condition_ids": np.asarray([truth.condition_id for truth in TRUTHS]),
        "lanes": np.asarray(LANES),
        "effects": effects,
        "rhos": rhos,
        "calibration_effect_lr": np.broadcast_to([0.5, 1.0, 2.0, 3.0], (c, 2, n)).copy(),
        "calibration_spread_lr": np.broadcast_to([0.5, 1.0, 2.0, 3.0], (c, n)).copy(),
        "validation_effect_drops": np.broadcast_to(
            effect_drops[:, None, None, :], (c, 2, n, len(effects))
        ).copy(),
        "validation_spread_drops": np.broadcast_to(rho_drops[:, None, :], (c, n, len(rhos))).copy(),
        "validation_effect_mle": effect_mle,
        "validation_spread_mle": spread_mle,
        "conditional_advantage": conditional,
        "joint_advantage": conditional + 0.03,
        "calibration_train_joint": np.broadcast_to(
            -0.5 * (rho_drops[:, None, :, None] + effect_drops[:, None, None, :]),
            (c, 2, len(rhos), len(effects)),
        ).copy(),
        "validation_train_joint": np.broadcast_to(
            -0.5 * (rho_drops[:, None, :, None] + effect_drops[:, None, None, :]),
            (c, 2, len(rhos), len(effects)),
        ).copy(),
        "event_diagnostics": events,
    }
    summary = {
        "config": asdict(config),
        "truths": [asdict(truth) for truth in TRUTHS],
        "mode": "smoke",
        "source_commit": "fixture-source",
        "bank_checksum": "fixture-bank",
        "invariants": {"paired_complete_datasets": True},
        "notes": {"event_diagnostics_sites": 120},
    }
    return synthesis.CampaignBundle(config, TRUTHS, profiles, summary, "fixture-digest")


def _write_bundle(bundle: synthesis.CampaignBundle, directory: Path) -> None:
    directory.mkdir()
    profile_path = directory / "profiles.npz"
    np.savez_compressed(profile_path, allow_pickle=False, **bundle.profiles)
    summary = dict(bundle.run_summary)
    with profile_path.open("rb") as handle:
        summary["profile_bundle_sha256"] = hashlib.file_digest(handle, "sha256").hexdigest()
    (directory / "run_summary.json").write_text(json.dumps(summary), encoding="utf-8")


def test_support_includes_equal_cutoff_null_and_preserves_disconnected_width() -> None:
    grid = np.asarray([1.0, 2.0, 3.0, 5.0])
    drops = np.asarray([[[[2.0, 0.0, 3.0, 1.0]]]])
    at_boundary = synthesis.support_metrics(drops, grid, np.asarray([1.0]), np.asarray([[2.0]]))
    below_boundary = synthesis.support_metrics(drops, grid, np.asarray([1.0]), np.asarray([[1.99]]))

    assert at_boundary["coverage"].item() == 1
    assert at_boundary["no_effect_exclusion"].item() == 0
    assert at_boundary["lower_boundary_contact"].item() == 1
    assert at_boundary["support_components"].item() == 2
    assert at_boundary["log_interval_width"].item() == pytest.approx(np.log(5.0))
    assert below_boundary["coverage"].item() == 0
    assert below_boundary["no_effect_exclusion"].item() == 1
    assert below_boundary["log_interval_width"].item() == pytest.approx(np.log(5.0 / 2.0))


def test_bootstrap_recalibrates_and_preserves_pairing_across_cases_and_lanes() -> None:
    bundle = _bundle()
    calibration = bundle.profiles["calibration_effect_lr"]
    calibration[:, 0, :] = 0.25
    calibration[:, 1, :] = [0.25, 0.25, 3.0, 3.0]
    samples = synthesis.paired_bootstrap(bundle, count=256, seed=17)

    # Evaluation profiles are identical within each case: width variation can only
    # come from the resampled calibration sample and recomputed order statistic.
    width = samples.effect["mean_log_interval_width"][:, 0, 1]
    assert len(np.unique(width)) == 2
    assert len(np.unique(samples.effect_cutoffs[:, 0, 1])) == 2
    assert np.quantile(width, 0.025) < np.quantile(width, 0.975)
    score = samples.effect["conditional_prey_advantage"]
    np.testing.assert_allclose(score[:, :, 1] - score[:, :, 0], 0.2)
    np.testing.assert_allclose(
        score[:, :, 0], np.broadcast_to(score[:, :1, 0], score[:, :, 0].shape)
    )
    np.testing.assert_array_equal(
        samples.effect_cutoffs[:, :, 1],
        np.broadcast_to(samples.effect_cutoffs[:, :1, 1], samples.effect_cutoffs[:, :, 1].shape),
    )
    # Reconstruct the first two independent draws to protect calibration/evaluation separation.
    rng = np.random.default_rng(17)
    calibration_indices = rng.integers(4, size=4)
    evaluation_indices = rng.integers(4, size=4)
    assert not np.array_equal(calibration_indices, evaluation_indices)
    assert samples.effect_cutoffs[0, 0, 1] == np.max(calibration[0, 1, calibration_indices])
    assert score[0, 0, 0] == pytest.approx(np.mean(np.arange(4)[evaluation_indices] * 0.1))


def test_summary_round_trip_and_figures_use_saved_profile_evidence(tmp_path: Path) -> None:
    original = _bundle()
    source = tmp_path / "input"
    _write_bundle(original, source)
    loaded = synthesis.load_campaign_bundle(source)
    np.testing.assert_array_equal(
        loaded.profiles["validation_effect_drops"], original.profiles["validation_effect_drops"]
    )
    result = synthesis.run_synthesis(loaded, bootstrap_count=32, bootstrap_seed=18)
    written = synthesis.write_review_bundle(result, tmp_path / "synthesis")

    assert len(result.conditions) == 18
    assert sum(row["parameter"] == "rho" for row in result.conditions) == 6
    assert len(result.paired_changes) == 30
    assert result.outcome == "non_scientific_smoke"
    assert all(path.stat().st_size > 0 for path in written)
    with (tmp_path / "synthesis" / "condition_summary.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 18
    null = next(
        row
        for row in rows
        if row["condition_id"] == "usual_1"
        and row["analysis"] == "known_speed"
        and row["parameter"] == "effect"
    )
    assert float(null["coverage"]) == 1.0
    assert float(null["no_effect_exclusion"]) == 0.0
    assert float(null["connected_interior"]) == 0.0
    assert float(null["no_effect_exclusion_wilson_upper"]) == pytest.approx(
        wilson_interval(0, 4).upper
    )
    summary = json.loads((tmp_path / "synthesis" / "summary.json").read_text())
    assert summary["provenance"]["profile_bundle_sha256"] == loaded.profile_sha256
    assert summary["bootstrap"]["count"] == 32
    assert {row["site_count"] for row in summary["event_information"]} == {120}
    for row in result.paired_changes:
        if row["metric"] == "conditional_prey_advantage":
            assert row["paired_mean_change"] == pytest.approx(0.2)
            assert row["bootstrap_lower"] == pytest.approx(0.2)
            assert row["bootstrap_upper"] == pytest.approx(0.2)
        if row["metric"] == "no_effect_exclusion":
            assert row["deterioration_direction"] == (
                "positive" if row["truth_effect"] == 1 else "negative"
            )
    for make_figure in (
        synthesis.paired_recovery_figure,
        synthesis.representative_likelihood_figure,
    ):
        figure = make_figure(result)
        canvas: Any = FigureCanvasAgg(figure)
        canvas.draw()
        pixels = np.asarray(canvas.buffer_rgba())
        assert np.std(pixels[:, :, :3]) > 20
        assert all(axis.get_xlabel() for axis in figure.axes[:6])
        plt.close(figure)


def test_bad_pairing_or_event_partition_is_rejected_but_weak_recovery_is_valid() -> None:
    bundle = _bundle()
    wrong_shape = dict(bundle.profiles)
    wrong_shape["validation_effect_mle"] = wrong_shape["validation_effect_mle"][:, :, :-1]
    with pytest.raises(ValueError):
        synthesis.validate_bundle(replace(bundle, profiles=wrong_shape))
    wrong_events = dict(bundle.profiles)
    wrong_events["event_diagnostics"] = wrong_events["event_diagnostics"].copy()
    wrong_events["event_diagnostics"][..., 3] = 130
    with pytest.raises(ValueError):
        synthesis.validate_bundle(replace(bundle, profiles=wrong_events))

    # Complete null false exclusion is a calibration signal, not a forced implementation failure.
    bundle.profiles["calibration_effect_lr"][:] = 0.0
    for c in (0, 3):
        bundle.profiles["validation_effect_drops"][c, :, :, 0] = 2.0
        bundle.profiles["validation_effect_drops"][c, :, :, 1] = 0.0
        bundle.profiles["validation_effect_mle"][c, :, :] = 2.0
    result = synthesis.run_synthesis(bundle, bootstrap_count=8)
    assert result.outcome == "non_scientific_smoke"
    assert any(
        flag.startswith("null_false_exclusion_above_nominal") for flag in result.caution_flags
    )
    assert all(
        row["secondary_context"] == "no_effect_control"
        for row in result.case_interpretations
        if row["condition_id"] in ("usual_1", "slow_1")
    )
