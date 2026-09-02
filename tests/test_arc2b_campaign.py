from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from latent_landscapes.arc2b_campaign import (
    CATEGORY_COUNT,
    EXPECTED_FILES,
    PSEUDO_ARRIVALS,
    CrossLayerHistory,
    _classify_truth,
    build_arrival_integration,
    latent_arrival_profile,
    run_campaign,
    smoke_config,
    spawn_seed_manifest,
    write_review_bundle,
)


def test_seed_manifest_pairs_with_disjoint_phase_roots() -> None:
    manifest = spawn_seed_manifest(smoke_config("prospective"))
    calibration = {(row.process_seed, row.prey_seed) for row in manifest.calibration}
    validation = {(row.process_seed, row.prey_seed) for row in manifest.validation}
    assert calibration.isdisjoint(validation)
    assert len({row.process_seed for row in manifest.calibration}) == 4


def test_smoke_campaign_writes_compact_replayable_bundle(tmp_path: Path) -> None:
    result = run_campaign(smoke_config("prospective"), workers=1, source_commit="test")
    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    assert len(result.truth_summaries) == 2
    assert len(result.calibration_statistics) == 8
    assert len(result.validation_metrics) == 8
    written = write_review_bundle(result, tmp_path)
    assert tuple(path.name for path in written) == EXPECTED_FILES
    assert {path.name for path in tmp_path.iterdir()} == set(EXPECTED_FILES)
    assert json.loads((tmp_path / "summary.json").read_text())["run_mode"] == "reduced_smoke"


def test_provenance_records_supplied_frozen_prediction_digest(tmp_path: Path) -> None:
    frozen = tmp_path / "frozen_predictions.csv"
    frozen.write_bytes(b"condition_id,predicted\nS17,0.5\n")
    digest = hashlib.sha256(frozen.read_bytes()).hexdigest()
    result = run_campaign(
        smoke_config("prospective"),
        workers=1,
        source_commit="test",
        frozen_predictions_sha256=digest,
    )
    output = tmp_path / "bundle"
    write_review_bundle(result, output)
    payload = json.loads((output / "seed_provenance.json").read_text())
    assert payload["frozen_predictions_sha256"] == digest


def test_production_prospective_requires_frozen_predictions_path(tmp_path: Path) -> None:
    script = Path(__file__).parents[1] / "scripts" / "run_arc2b_campaign.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--production",
            "--block",
            "prospective",
            "--output-dir",
            str(tmp_path / "bundle"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "--frozen-predictions" in completed.stderr


def test_arrival_integration_has_reconciled_survival_moments() -> None:
    bank = np.asarray([[4.0], [14.0], [24.0], [34.0]])
    integration = build_arrival_integration(
        bank,
        ("site",),
        (1.0, 5.0),
        0.002,
    )
    assert np.allclose(integration.category_mass.sum(axis=1), 1.0)
    denominator = 4.0 + 3.5
    expected = (
        math.exp(-0.002 * (5.0 * 30.0 + (1.0 - 5.0) * 24.0))
        + 0.5 * math.exp(-0.002 * (5.0 * 30.0 + (1.0 - 5.0) * 25.0))
    ) / denominator
    assert integration.survival_moments[1, 0, 3, 2] == pytest.approx(expected)
    different_background = build_arrival_integration(bank, ("site",), (1.0, 5.0), 0.004)
    assert not np.isclose(
        integration.survival_moments[1, 0, 3, 2],
        different_background.survival_moments[1, 0, 3, 2],
    )
    assert np.all(np.diff(integration.survival_moments.sum(axis=3), axis=2) <= 1e-12)
    assert integration.survival_moments.shape == (2, 1, 7, CATEGORY_COUNT)


def test_latent_profile_uses_shared_arrival_for_both_observation_layers() -> None:
    history = CrossLayerHistory(
        "test",
        0,
        0,
        "site",
        "cluster",
        "training",
        0,
        0,
        25.0,
        45.0,
        (0, 0, 0, 0, 0, 0),
        (2, 1, 1, 0, 0, 0),
        (False, False, True, True, True, True),
        (True, True, True, True, False, False),
        0.65,
    )
    integration = build_arrival_integration(
        np.asarray([[5.0], [25.0], [45.0], [65.0]]), ("site",), (1.0, 5.0), 0.002
    )
    config = smoke_config("prospective")
    profile = latent_arrival_profile((history,), integration, config)
    pred = []
    prey = []
    augmented = (5.0, 25.0, 45.0, 65.0, *PSEUDO_ARRIVALS)
    weights = (1.0,) * 4 + (0.5,) * len(PSEUDO_ARRIVALS)
    for arrival in augmented:
        c = int(np.searchsorted(np.asarray((10, 20, 30, 40, 50, 60)), arrival, side="left"))
        pred_prob = 1.0
        for j, count in enumerate(history.predator_detection_counts):
            pred_prob *= 1.0 if c > j else math.comb(2, count) * 0.65**count * 0.35 ** (2 - count)
        survival = [
            math.exp(-0.002 * (t + 4.0 * min(max(t - arrival, 0), t)))
            for t in (0, 10, 20, 30, 40, 50, 60)
        ]
        alive = [
            math.comb(2, count) * 0.65**count * 0.35 ** (2 - count)
            for count in history.prey_detection_counts
        ]
        prey_prob = sum(
            (survival[j] - survival[j + 1])
            * math.prod(alive[:j])
            * math.prod([count == 0 for count in history.prey_detection_counts[j:]])
            for j in range(6)
        ) + survival[-1] * math.prod(alive)
        pred.append(pred_prob)
        prey.append(prey_prob)
    denominator = sum(weights)
    shared = sum(w * p * q for w, p, q in zip(weights, pred, prey, strict=True)) / denominator
    independent = (sum(w * p for w, p in zip(weights, pred, strict=True)) / denominator) * (
        sum(w * q for w, q in zip(weights, prey, strict=True)) / denominator
    )
    assert math.exp(float(profile.log_likelihoods[1])) == pytest.approx(shared, rel=1e-12)
    assert not math.isclose(shared, independent, rel_tol=1e-4)


def test_neutral_control_accepts_interval_spanning_zero_only() -> None:
    from latent_landscapes.arc2b_design import NEUTRAL_CONTROL

    assert (
        _classify_truth(
            NEUTRAL_CONTROL,
            score_interval=SimpleNamespace(lower=-0.01, upper=0.01),
            coverage=SimpleNamespace(lower=0.94, upper=0.96),
            connected=238,
            null_count=0,
            count=250,
            error=0.4,
            width=1.2,
        )
        == "neutral_control_valid"
    )
    assert (
        _classify_truth(
            NEUTRAL_CONTROL,
            score_interval=SimpleNamespace(lower=0.001, upper=0.01),
            coverage=SimpleNamespace(lower=0.94, upper=0.96),
            connected=238,
            null_count=0,
            count=250,
            error=0.4,
            width=1.2,
        )
        == "control_review_required"
    )
