from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from latent_landscapes.misspecification_synthesis import (
    CELL_IDS,
    METRICS,
    _interval_status,
    _prediction_rows,
    classify_nomination,
    evaluate_histories,
    paired_bootstrap,
)

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts/synthesize_misspecification.py"
_SPEC = importlib.util.spec_from_file_location("synthesize_misspecification", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_CLI = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CLI)
_verify_production = _CLI._verify_production


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def test_paired_bootstrap_uses_one_replicate_draw_across_every_cell() -> None:
    base = np.arange(12.0)
    metrics = np.stack((base, base, base + 3.0), axis=0)[..., None]
    indices, means, deltas = paired_bootstrap(
        metrics, np.array([0, 0, 0]), draws=40, seed=7
    )
    assert indices.shape == (40, 12)
    np.testing.assert_array_equal(deltas[:, 0], 0.0)
    np.testing.assert_array_equal(deltas[:, 1], 0.0)
    np.testing.assert_allclose(deltas[:, 2], 3.0)
    np.testing.assert_array_equal(means[:, 0], means[:, 1])


def test_detector_includes_score_ties_and_plugin_uses_lowest_index_mle() -> None:
    effects = 1.0 + 0.05 * np.arange(181)
    profiles = np.full((1, 2, 181), 10.0)
    profiles[:, :, 0] = 0.0
    profiles[:, :, 1] = 0.4
    prey = np.array([[0.0, 2.0]])
    predator = np.array([[3.0, 3.0]])
    mle = np.zeros((1, 2), dtype=np.int64)
    joint = np.broadcast_to(predator[..., None], profiles.shape).copy()
    joint[np.arange(1)[:, None], np.arange(2)[None, :], mle] += prey
    reference = np.ones((181, 999))
    reference[0] = np.concatenate((np.zeros(999),))
    # At node 0, observed zero ties all 999 references: inclusive p is exactly 1.
    reference[1, :99] = -1.0
    effect_cutoffs = np.full(181, 0.5)
    c99_cutoffs = np.full(181, 0.5)
    evidence = evaluate_histories(
        effects,
        np.array([1.0]),
        profiles,
        prey,
        predator,
        mle,
        joint,
        reference,
        effect_cutoffs,
        c99_cutoffs,
    )
    assert evidence["candidate_p"][0, 0, 0] == 1.0
    assert evidence["candidate_p"][0, 0, 1] == 0.1
    assert evidence["plugin_p"][0, 0] == 1.0
    assert evidence["p_bb"][0, 0] == 1.0

    tied = profiles.copy()
    tied[..., 1] = 0.0
    with pytest.raises(ValueError, match="lowest-index"):
        evaluate_histories(
            effects, np.array([1.0]), tied, prey, predator, np.ones((1, 2), dtype=int),
            joint, reference, effect_cutoffs, c99_cutoffs,
        )


def test_nomination_selects_one_global_cell_and_breaks_ties_by_frozen_order() -> None:
    rows = [
        {
            "cell_id": "D20_h1",
            "departure_class": "prey_detection",
            "metric": "H_primary",
            "delta": 0.10,
            "bootstrap_low": 0.01,
            "bootstrap_high": 0.18,
        },
        {
            "cell_id": "D10_h1",
            "departure_class": "prey_detection",
            "metric": "H_primary",
            "delta": 0.10,
            "bootstrap_low": 0.02,
            "bootstrap_high": 0.17,
        },
        {
            "cell_id": "B100-A_h1",
            "departure_class": "background",
            "metric": "H_plugin",
            "delta": 0.50,
            "bootstrap_low": 0.40,
            "bootstrap_high": 0.60,
        },
    ]
    selected = classify_nomination(rows)
    assert selected["cell_id"] == "D10_h1"
    assert selected["departure_class"] == "prey_detection"


def test_nomination_requires_point_threshold_and_positive_paired_lower_limit() -> None:
    rows = [
        {
            "cell_id": "PD10_h1",
            "departure_class": "predator_detection",
            "metric": "H_primary",
            "delta": 0.07,
            "bootstrap_low": 0.0,
            "bootstrap_high": 0.12,
        },
        {
            "cell_id": "B100-A_h1",
            "departure_class": "background",
            "metric": "H_primary",
            "delta": 0.049,
            "bootstrap_low": 0.02,
            "bootstrap_high": 0.08,
        },
    ]
    assert classify_nomination(rows)["status"] == "none"


def test_predictions_preserve_interval_status_and_p4_absolute_mean_bias_definition() -> None:
    cell_index = {cell: index for index, cell in enumerate(CELL_IDS)}
    metric_index = {metric: index for index, metric in enumerate(METRICS)}
    point = np.zeros((len(CELL_IDS), len(METRICS)))
    boot = np.zeros((40, len(CELL_IDS), len(METRICS)))
    deltas = np.zeros_like(boot)
    bias = metric_index["signed_log_bias"]
    pd3, d203 = cell_index["PD10_h3"], cell_index["D20_h3"]
    pd5, d205 = cell_index["PD10_h5"], cell_index["D20_h5"]
    point[pd3, bias], point[d203, bias] = -0.40, 0.30
    point[pd5, bias], point[d205, bias] = -0.20, 0.10
    boot[:, pd3, bias], boot[:, d203, bias] = -0.40, 0.30
    boot[:, pd5, bias], boot[:, d205, bias] = -0.20, 0.10
    # P3 explicitly predicts an interval containing zero, rather than equivalence.
    sf = metric_index["strict_false_effect"]
    b50 = cell_index["B50-I_h1"]
    deltas[:, b50, sf] = np.linspace(-0.02, 0.02, 40)
    rows = _prediction_rows(cell_index, metric_index, point, boot, deltas)
    p4_h3 = next(row for row in rows if row["component"].startswith("h=3: abs(mean bias"))
    assert p4_h3["estimate"] == pytest.approx(0.10)
    assert p4_h3["interval_status"] == "supported"
    p3 = next(row for row in rows if row["component"].startswith("B50-I_h1: strict"))
    assert p3["relation"] == "interval_contains_zero"
    assert p3["interval_status"] == "met"
    p4_exclusion = [
        row
        for row in rows
        if row["prediction"] == "P4" and "truth-exclusion" in row["component"]
    ]
    assert len(p4_exclusion) == 1
    assert p4_exclusion[0]["component"].startswith("PD10: maximum")


def test_inclusive_prediction_bounds_support_intervals_ending_at_boundary() -> None:
    assert _interval_status(0.03, 0.05, "ge", lower=0.03) == "supported"
    assert _interval_status(-0.01, 0.02, "le", upper=0.02) == "supported"
    assert _interval_status(0.03, 0.05, "gt", lower=0.03) == "unresolved"
    assert _interval_status(-0.01, 0.02, "lt", upper=0.02) == "unresolved"


def test_cli_accepts_complete_runner_wire_contract_and_rejects_tamper(tmp_path: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    input_dir = tmp_path / "production"
    input_dir.mkdir()
    profiles = np.zeros((17, 1000, 181), dtype=np.float64)
    arrays_path = input_dir / "campaign_arrays.npz"
    np.savez_compressed(
        arrays_path,
        profiles=profiles,
        holdout_joint=np.zeros_like(profiles),
        prey_score=np.zeros((17, 1000)),
        predator_score=np.zeros((17, 1000)),
        mle_index=np.zeros((17, 1000), dtype=np.int64),
        opaque_ids=np.asarray(
            [[f"opaque-{cell}-{rep}" for rep in range(1000)] for cell in range(17)]
        ),
        cell_ids=np.asarray(CELL_IDS),
        truths=np.asarray((1, 3, 5, 1, 3, 5, 1, 3, 5, 1, 3, 5, 1, 1, 1, 1, 3)),
    )
    source_names = (
        "src/latent_landscapes/misspecification_generator.py",
        "src/latent_landscapes/misspecification_campaign.py",
        "src/latent_landscapes/misspecification_synthesis.py",
        "scripts/run_misspecification.py",
        "scripts/synthesize_misspecification.py",
        "docs/goals/051-misspecification-screen/registration-2026-09-23.md",
    )
    seed_controls = {"all_registered_streams_disjoint": True}
    config = {
        "mode": "production",
        "effects": (1.0 + 0.05 * np.arange(181)).tolist(),
        "truths": [1.0, 3.0, 5.0],
        "replicates": 1000,
        "bank_size": 131072,
        "campaign_root": 2026092301,
        "bank_root": 20260905,
        "bootstrap_root": 2026092304,
    }
    contract = {
        "schema_version": 1,
        "workflow": "goal051-misspecification-screen",
        "config": config,
        "cell_ids": list(CELL_IDS),
        "cell_truths": [1, 3, 5, 1, 3, 5, 1, 3, 5, 1, 3, 5, 1, 1, 1, 1, 3],
        "source_hashes": {name: _file_sha256(repository / name) for name in source_names},
        "reference_manifest": {"detector_sha256": "registered", "calibration_sha256": "registered"},
        "bank_provenance": {"bank_checksum": "fixture"},
        "seed_controls": seed_controls,
        "workers": 8,
        "pairing": {"complete_replicate_unit": True, "cells_per_replicate": 17},
    }
    contract["run_fingerprint"] = _json_sha256(contract)
    (input_dir / "run_contract.json").write_text(json.dumps(contract))
    frozen = {
        "schema_version": 1,
        "metadata_joined": True,
        "endpoints_evaluated": False,
        "run_fingerprint": contract["run_fingerprint"],
        "cell_ids": list(CELL_IDS),
        "truths": contract["cell_truths"],
        "grid": config["effects"],
        "files": {"campaign_arrays.npz": _file_sha256(arrays_path)},
        "reference_manifest": contract["reference_manifest"],
    }
    frozen_path = input_dir / "frozen_scores.json"
    frozen_path.write_text(json.dumps(frozen))
    summary = {
        **contract,
        "validation": {
            "profiles_shape": True,
            "holdout_shape": True,
            "score_shapes": True,
            "all_main_arrays_finite": True,
            "profile_minimum_zero": True,
            "mle_matches_lowest_index": True,
            "grid_is_registered": True,
            "cell_ids_in_registered_order": True,
            "truths_in_registered_order": True,
            "opaque_ids_nonempty_unique": True,
            "seed_controls": seed_controls,
        },
        "output_hashes": frozen["files"],
        "frozen_scores_sha256": _file_sha256(frozen_path),
        "outcome": "production_complete",
    }
    (input_dir / "run_summary.json").write_text(json.dumps(summary))
    loaded_summary, loaded_arrays = _verify_production(input_dir)
    assert loaded_summary["outcome"] == "production_complete"
    assert loaded_arrays["profiles"].shape == (17, 1000, 181)

    with arrays_path.open("ab") as handle:
        handle.write(b"tampered")
    with pytest.raises(ValueError, match="production output hash changed"):
        _verify_production(input_dir)
