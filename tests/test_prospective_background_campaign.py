from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from latent_landscapes import adjusted_background_likelihood as likelihood
from latent_landscapes import adjusted_background_pilot as pilot
from latent_landscapes import prospective_background_campaign as campaign
from latent_landscapes import prospective_background_generator as generator
from latent_landscapes.goal011.benchmark import build_fixed_inputs


@pytest.fixture(scope="module")
def smoke_context() -> tuple[object, object, dict[str, np.ndarray]]:
    fixed = build_fixed_inputs()
    setup = generator.build_generator_setup(fixed)
    seeds = generator.spawn_generator_seeds(generator.SMOKE_ROOT, "smoke", 2)
    cells = [cell for seed in seeds for cell in generator.generate_replicate(fixed, setup, seed)]
    count = 2
    data = {
        "effects": np.asarray(pilot.EFFECTS),
        "betas": np.asarray(pilot.BETAS),
        "cell_ids": np.asarray([cell.cell.cell_id for cell in cells]),
        "replicate_indices": np.repeat(np.arange(count), 6),
        "truth_h": np.tile(np.asarray(generator.TRUTH_H), count),
        "truth_beta": np.tile(np.asarray(generator.TRUTH_BETA), count),
        "opaque_ids": np.asarray([cell.dataset.opaque_id for cell in cells]),
        "site_ids": np.asarray(setup.site_ids),
        "site_cluster_ids": np.asarray(setup.site_cluster_ids),
        "site_splits": np.asarray(setup.site_splits),
        "training_mask": np.asarray([split == "training" for split in setup.site_splits]),
        "site_A": setup.exposure_score[setup.site_rows, setup.site_cols],
        "map_A": setup.exposure_score,
        "true_arrival": np.stack([cell.latent_truth.arrival for cell in cells]),
        "true_extirpation": np.stack([cell.latent_truth.prey_extirpation for cell in cells]),
        "true_hazards": np.stack([cell.latent_truth.background_hazard for cell in cells]),
        "predator_counts": np.asarray(
            [
                [history.predator_detection_counts for history in cell.dataset.histories]
                for cell in cells
            ],
            dtype=np.uint8,
        ),
        "prey_counts": np.asarray(
            [
                [history.prey_detection_counts for history in cell.dataset.histories]
                for cell in cells
            ],
            dtype=np.uint8,
        ),
        "oracle_history_indices": np.asarray([0, 1, 2, 3, 6, 7, 8, 9]),
    }
    return fixed, setup, data


def test_seed_controls_include_prior_goal051_timing_and_smoke() -> None:
    controls = campaign.seed_controls()
    assert controls["all_disjoint"] is True
    assert controls["phase_seed_counts"] == {
        "production": 7_000,
        "timing": 140,
        "bootstrap": 14_000,
        "smoke": 14,
    }
    assert controls["previous_roots"] == [
        2026092301,
        2026092302,
        2026092303,
        2026092304,
    ]
    assert controls["audit_root_reserved"] is True
    assert controls["root_identifiers_distinct"] is True


def test_receipt_last_commit_records_serialization_and_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "cache.npz"
    record = {"identity": "a" * 64}
    values = {"score": np.arange(4, dtype=np.float64)}
    campaign.commit_npz(path, values, record)
    assert path.exists()
    assert path.with_suffix(".json").exists()
    loaded = campaign.read_committed(path, "a" * 64)
    assert loaded is not None
    arrays, receipt = loaded
    assert np.array_equal(arrays["score"], values["score"])
    assert receipt["sha256"] == pilot.sha256(path)
    assert receipt["serialization_seconds"] >= 0


def test_observation_metadata_rejects_wrong_cell_order(
    smoke_context: tuple[Any, Any, dict[str, np.ndarray]],
) -> None:
    _, setup, data = smoke_context
    record = {
        "identity": "b" * 64,
        "sha256": "c" * 64,
        "phase": "timing",
        "blocks": 2,
        "histories": 12,
        "generation_seconds": 0.0,
        "cache_io_seconds": 0.0,
        "serialization_seconds": 0.0,
        "seeds": [
            asdict(seed)
            for seed in generator.spawn_generator_seeds(generator.TIMING_ROOT, "timing", 2)
        ],
    }
    campaign.validate_observations(data, record, "b" * 64, 2, setup)
    broken = dict(data, cell_ids=data["cell_ids"][::-1])
    with pytest.raises(ValueError, match="cell ordering"):
        campaign.validate_observations(broken, record, "b" * 64, 2, setup)


def test_small_bank_scores_and_reuses_authenticated_integration_cache(
    tmp_path: Path, smoke_context: tuple[Any, Any, dict[str, np.ndarray]]
) -> None:
    _, setup, data = smoke_context
    bank = np.linspace(0.0, 60.0, 8 * 160, dtype=np.float64).reshape(8, 160)
    prepared = likelihood.prepare_bank(bank, setup.site_ids)
    histories = campaign.histories_from_arrays(data)
    first, construction, cache_seconds, receipt = campaign.get_integration_timed(
        tmp_path, campaign.TIMING_INDICES[0], "core", prepared, data
    )
    scores = campaign.score_panel(histories, first, data, campaign.TIMING_INDICES[0])
    campaign.validate_row(scores | {"reference_error": np.asarray(0.0)}, len(histories), 8)
    second, second_construction, _, second_receipt = campaign.get_integration_timed(
        tmp_path, campaign.TIMING_INDICES[0], "core", prepared, data
    )
    assert construction > 0
    assert cache_seconds >= 0
    assert second_construction == 0
    assert receipt == second_receipt
    assert np.array_equal(first.survival_moments[0], second.survival_moments[0])


def test_timing_output_hashes_detect_tampering(tmp_path: Path) -> None:
    target = tmp_path / "row.json"
    target.write_text(json.dumps({"ok": True}), encoding="utf-8")
    expected = {"row.json": pilot.sha256(target)}
    campaign.validate_output_hashes(tmp_path, expected)
    target.write_text(json.dumps({"ok": False}), encoding="utf-8")
    with pytest.raises(ValueError, match="timing output hashes"):
        campaign.validate_output_hashes(tmp_path, expected)
