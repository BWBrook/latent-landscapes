from __future__ import annotations

import csv
import json
from pathlib import Path

from latent_landscapes.goal016.artifacts import EXPECTED_FILES, write_review_bundle
from latent_landscapes.goal016.benchmark import run_goal016, smoke_config


def test_goal016_writes_compact_review_bundle(tmp_path: Path) -> None:
    result = run_goal016(smoke_config())

    written = write_review_bundle(result, tmp_path)

    assert {path.relative_to(tmp_path).as_posix() for path in written} == set(EXPECTED_FILES)
    assert all(path.stat().st_size > 0 for path in written)
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["outcome"] == "reduced_smoke_complete"
    assert summary["scientific_interpretation"] == "non_scientific_smoke"
    with (tmp_path / "funnel_performance.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == len(result.funnel_performance)
    assert {row["representation"] for row in rows} == {
        row.representation for row in result.funnel_performance
    }
    with (tmp_path / "method_comparison.csv").open(newline="", encoding="utf-8") as handle:
        comparison = list(csv.DictReader(handle))
    assert len(comparison) == len(result.config.rho_values)
    assert {row["rho"] for row in comparison} == {"0.5", "1.0", "2.0"}
    review = (tmp_path / "review.md").read_text(encoding="utf-8")
    assert "non-scientific reduced smoke" in review
    assert "Information funnel" in review
