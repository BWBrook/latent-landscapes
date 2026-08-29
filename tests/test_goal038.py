from __future__ import annotations

import csv
import json
from itertools import pairwise
from pathlib import Path

import numpy as np

from latent_landscapes.goal001.landscape import build_landscape
from latent_landscapes.goal038 import (
    EXPECTED_FILES,
    build_eta_translation,
    generate_pilot_truths,
    run_goal038,
    write_review_bundle,
)


def test_eta_translation_exposes_ecological_cost_contrasts() -> None:
    rows = build_eta_translation(build_landscape())
    by_eta = {row.eta: row for row in rows}
    assert set(by_eta) == {0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0}
    assert by_eta[0.0].matrix_to_corridor_ratio == 1.0
    assert by_eta[0.0].global_max_to_min_ratio == 1.0
    assert np.allclose(
        [row.geometric_mean_cost for row in rows],
        rows[0].geometric_mean_cost,
        rtol=0.0,
        atol=1e-12,
    )
    assert 2.49 < by_eta[0.75].matrix_to_corridor_ratio < 2.51
    assert 3.39 < by_eta[1.0].matrix_to_corridor_ratio < 3.40
    assert 11.5 < by_eta[2.0].matrix_to_corridor_ratio < 11.6
    assert 23.3 < by_eta[2.0].global_max_to_min_ratio < 23.4
    assert all(
        left.matrix_to_corridor_ratio < right.matrix_to_corridor_ratio
        for left, right in pairwise(rows)
    )


def test_sobol_pilot_is_reproducible_bounded_and_stratified() -> None:
    first = generate_pilot_truths()
    second = generate_pilot_truths()
    assert first == second
    assert len(first) == 16
    assert len({(row.rho, row.eta, row.p) for row in first}) == 16
    assert all(0.5 <= row.rho <= 2.0 for row in first)
    assert all(0.25 <= row.eta <= 2.0 for row in first)
    assert all(0.35 <= row.p <= 0.85 for row in first)
    for field in ("unit_rho", "unit_eta", "unit_p"):
        strata = sorted(int(float(getattr(row, field)) * 16.0) for row in first)
        assert strata == list(range(16))


def test_goal038_writes_compact_human_review_surface(tmp_path: Path) -> None:
    result = run_goal038()
    assert result.outcome == "ready_for_human_arc2a_design_review"
    assert all(result.invariants.values())
    assert result.compute_budget[0].total_new_truth_count == 17
    assert result.compute_budget[0].total_history_count == 8500

    written = write_review_bundle(result, tmp_path)
    assert {path.name for path in written} == set(EXPECTED_FILES)
    assert {path.name for path in tmp_path.iterdir()} == set(EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)

    with (tmp_path / "arc2a_pilot_truths.csv").open(newline="") as handle:
        pilot_rows = list(csv.DictReader(handle))
    assert len(pilot_rows) == 17
    assert sum(row["design_role"] == "sobol_pilot" for row in pilot_rows) == 16
    assert sum(row["design_role"] == "no_resistance_diagnostic" for row in pilot_rows) == 1

    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["sobol_scramble_seed"] == 20260829
    assert summary["initial_compute_budget"]["total_history_count"] == 8500
    assert "human decisions" in (tmp_path / "review.md").read_text().lower()
