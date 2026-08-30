from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from latent_landscapes import goal038, goal041


def test_nested_truths_extend_the_accepted_sobol_sequence() -> None:
    first = goal038.generate_pilot_truths()
    nested = goal041.generate_nested_truths()
    assert tuple(row.condition_id for row in nested) == tuple(
        f"S{index:02d}" for index in range(17, 33)
    )
    coordinates = {(row.rho, row.eta, row.p) for row in first}
    coordinates.update((row.rho, row.eta, row.probability) for row in nested)
    assert len(coordinates) == 32
    assert all(0.5 <= row.rho <= 2.0 for row in nested)
    assert all(0.25 <= row.eta <= 2.0 for row in nested)
    assert all(0.35 <= row.probability <= 0.85 for row in nested)


def test_prospective_predictions_are_frozen_and_complete() -> None:
    rows = goal041.load_frozen_predictions(goal041.DEFAULT_FROZEN_PREDICTIONS)
    assert len(rows) == 80
    assert {row.source_goal040_commit for row in rows} == {goal041.ACCEPTED_GOAL040_COMMIT}
    assert len({row.coefficient_sha256 for row in rows}) == 1
    assert all(np.isfinite(row.predicted) for row in rows)


def test_reduced_campaign_scores_and_writes_exact_bundle(tmp_path: Path) -> None:
    predictions = goal041.load_frozen_predictions(goal041.DEFAULT_FROZEN_PREDICTIONS)
    result = goal041.run_goal041(
        goal041.smoke_config(),
        predictions,
        workers=1,
        source_commit="test",
    )
    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    written = goal041.write_review_bundle(result, tmp_path)
    assert tuple(path.name for path in written) == goal041.EXPECTED_FILES
    assert {path.name for path in tmp_path.iterdir()} == set(goal041.EXPECTED_FILES)
    with (tmp_path / "prospective_scores.csv").open(encoding="utf-8", newline="") as handle:
        assert len(tuple(csv.DictReader(handle))) == 10
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["outcome"] == "non_scientific_smoke"
