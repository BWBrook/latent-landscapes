from __future__ import annotations

import json
import math
from pathlib import Path

from latent_landscapes.goal002.calibration import EstimateInterval
from latent_landscapes.goal026 import (
    EXPECTED_FILES,
    DatasetSeed,
    PreyHistory,
    classify_outcome,
    generate_prey_dataset,
    hazard_ratio_profile,
    log_likelihood_neutral,
    observed_extirpation_interval,
    run_goal026,
    smoke_config,
    write_review_bundle,
)


def _history(*, arrival: float, left: float, right: float | None) -> PreyHistory:
    return PreyHistory(
        dataset_phase="test",
        dataset_index=0,
        site_id="site",
        cluster_id="cluster",
        split="training",
        row=0,
        col=0,
        predator_arrival_time=arrival,
        true_extirpation_time=(left + float(right)) / 2.0 if right is not None else 70.0,
        interval_left=left,
        interval_right=right,
        event_observed=right is not None,
    )


def test_interval_likelihood_is_finite_and_uses_known_arrival() -> None:
    histories = (
        _history(arrival=5.0, left=10.0, right=20.0),
        _history(arrival=40.0, left=60.0, right=None),
    )

    profile = hazard_ratio_profile(histories, (1.0, 5.0, 9.0))

    assert all(math.isfinite(value) for value in profile.log_likelihoods)
    assert math.isfinite(log_likelihood_neutral(histories, 0.005))
    assert observed_extirpation_interval(20.1) == (20.0, 30.0, True)
    assert observed_extirpation_interval(70.0) == (60.0, None, False)


def test_generated_dataset_has_complete_perfectly_observed_histories() -> None:
    _, histories = generate_prey_dataset(DatasetSeed("validation", 0, 101, 202), smoke_config())

    assert len(histories) == 160
    assert sum(row.split == "training" for row in histories) == 120
    assert sum(row.split == "holdout" for row in histories) == 40
    assert all(row.interval_right is not None for row in histories if row.event_observed)
    assert all(row.interval_right is None for row in histories if not row.event_observed)


def test_positive_control_decision_requires_every_scientific_gate() -> None:
    calibrated = EstimateInterval(0.95, 0.92, 0.97)
    advantage = EstimateInterval(0.02, 0.01, 0.03)

    def decision(*, null_count: int = 250, lower_advantage: float = 0.01) -> str:
        return classify_outcome(
            invariants={"valid": True},
            coverage=calibrated,
            connected_interior_count=250,
            null_exclusion_count=null_count,
            validation_count=250,
            median_absolute_log_error=0.10,
            median_log_support_width=0.60,
            score_advantage=EstimateInterval(
                advantage.estimate,
                lower_advantage,
                advantage.upper,
            ),
        )

    assert decision() == "known_arrival_prey_effect_recovered"
    assert decision(null_count=237) == "known_arrival_prey_effect_not_recovered"
    assert decision(lower_advantage=-0.001) == "known_arrival_prey_effect_not_recovered"


def test_goal026_smoke_writes_exact_compact_review_surface(tmp_path: Path) -> None:
    result = run_goal026(smoke_config())
    written = write_review_bundle(result, tmp_path)

    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    assert {path.name for path in written} == set(EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)
    payload = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert payload["run_mode"] == "reduced_smoke"
    assert "implementation check only" in (tmp_path / "review.md").read_text(encoding="utf-8")
