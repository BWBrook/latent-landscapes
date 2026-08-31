from __future__ import annotations

from pathlib import Path

import numpy as np

from latent_landscapes import arc2a_campaign
from latent_landscapes.arc2a_design import TruthCondition
from latent_landscapes.goal011 import benchmark as goal011
from latent_landscapes.goal023 import TruthCell, generate_truth_dataset


def test_exact_truth_grids_and_paired_generator_reconcile_arc1() -> None:
    config = arc2a_campaign.smoke_config()
    fixed = goal011.build_fixed_inputs()
    manifest = goal011.spawn_seed_manifest(config.seed_config)
    central = TruthCondition("central", "test", 1.0, 1.0, 0.65)
    generated = arc2a_campaign.generate_paired_datasets(fixed, manifest.calibration[0], (central,))[
        0
    ]
    reference_truth, reference_records = generate_truth_dataset(
        fixed,
        manifest.calibration[0],
        TruthCell("central", 1.0, 1.0, 0.65),
    )
    assert np.array_equal(generated.truth.arrival, reference_truth.arrival)
    assert generated.records == reference_records
    for truth in config.truths:
        assert arc2a_campaign.candidate_grid(config.base_rhos, truth.rho).count(truth.rho) == 1
        assert arc2a_campaign.candidate_grid(config.base_etas, truth.eta).count(truth.eta) == 1
        assert (
            arc2a_campaign.candidate_grid(config.base_probabilities, truth.probability).count(
                truth.probability
            )
            == 1
        )


def test_prospective_smoke_is_paired_and_writes_one_compact_bundle(tmp_path: Path) -> None:
    result = arc2a_campaign.run_campaign(
        arc2a_campaign.smoke_config("prospective"), workers=1, source_commit="test"
    )
    assert result.outcome == "non_scientific_smoke"
    assert all(result.invariants.values())
    assert len(result.truth_summaries) == 2
    assert len(result.calibration_metrics) == 8
    assert len(result.validation_metrics) == 8
    by_dataset: dict[int, list[str]] = {}
    for row in result.validation_metrics:
        by_dataset.setdefault(row.dataset_index, []).append(row.condition_id)
    assert all(len(ids) == 2 and len(set(ids)) == 2 for ids in by_dataset.values())
    written = arc2a_campaign.write_review_bundle(result, tmp_path)
    assert tuple(path.name for path in written) == arc2a_campaign.EXPECTED_FILES
    assert {path.name for path in tmp_path.iterdir()} == set(arc2a_campaign.EXPECTED_FILES)
    assert (tmp_path / "truth_level_recovery.svg").stat().st_size > 1000
