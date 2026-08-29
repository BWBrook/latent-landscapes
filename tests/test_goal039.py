from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from latent_landscapes import goal039
from latent_landscapes.goal011 import benchmark as goal011
from latent_landscapes.goal023 import TruthCell, generate_truth_dataset


def test_exact_truth_grids_and_paired_generator_reconcile_arc1() -> None:
    config = goal039.smoke_config()
    fixed = goal011.build_fixed_inputs()
    manifest = goal011.spawn_seed_manifest(config.seed_config)
    central = goal039.TruthCondition("central", "test", 1.0, 1.0, 0.65)
    generated = goal039.generate_paired_datasets(fixed, manifest.calibration[0], (central,))[0]
    reference_truth, reference_records = generate_truth_dataset(
        fixed,
        manifest.calibration[0],
        TruthCell("central", 1.0, 1.0, 0.65),
    )
    assert np.array_equal(generated.truth.arrival, reference_truth.arrival)
    assert generated.records == reference_records
    for truth in config.truths:
        assert goal039.candidate_grid(config.base_rhos, truth.rho).count(truth.rho) == 1
        assert goal039.candidate_grid(config.base_etas, truth.eta).count(truth.eta) == 1
        assert (
            goal039.candidate_grid(config.base_probabilities, truth.probability).count(
                truth.probability
            )
            == 1
        )


def test_reduced_campaign_is_paired_complete_and_finite() -> None:
    result = goal039.run_goal039(goal039.smoke_config(), workers=1, source_commit="test")
    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    assert len(result.truth_summaries) == 3
    assert len(result.calibration_metrics) == 12
    assert len(result.validation_metrics) == 12
    by_dataset: dict[int, list[str]] = {}
    for row in result.validation_metrics:
        by_dataset.setdefault(row.dataset_index, []).append(row.condition_id)
    assert all(len(ids) == 3 and len(set(ids)) == 3 for ids in by_dataset.values())
    timing = goal039.timing_config()
    assert len(timing.truths) == 17
    assert timing.base_rhos == goal039.DEFAULT_CONFIG.base_rhos
    assert timing.base_etas == goal039.DEFAULT_CONFIG.base_etas
    assert timing.base_probabilities == goal039.DEFAULT_CONFIG.base_probabilities


def test_review_bundle_is_compact_and_reconciled(tmp_path: Path) -> None:
    result = goal039.run_goal039(goal039.smoke_config(), workers=1, source_commit="test")
    written = goal039.write_review_bundle(result, tmp_path)
    assert tuple(path.name for path in written) == goal039.EXPECTED_FILES
    assert {path.name for path in tmp_path.iterdir()} == set(goal039.EXPECTED_FILES)
    with (tmp_path / "truth_summary.csv").open(encoding="utf-8", newline="") as handle:
        assert len(tuple(csv.DictReader(handle))) == 3
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["outcome"] == "non_scientific_smoke"
    assert summary["common_random_numbers"]["process_shocks_paired_across_truths"] is True
    assert summary["common_random_numbers"]["detection_streams_paired_across_truths"] is True
    assert (tmp_path / "truth_level_recovery.svg").stat().st_size > 1000
