from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import numpy as np
import pytest

from latent_landscapes import adjusted_background_replay as replay
from latent_landscapes import misspecification_generator as generator
from latent_landscapes import model_adequacy_campaign as adequacy


def _generated_cells() -> tuple[generator.GeneratedCell, ...]:
    """Small analyst-only stand-ins; latent truth is deliberately unusable."""

    class NoEvaluatorAccess:
        def __getattribute__(self, name: str) -> object:
            raise AssertionError(f"verification accessed evaluator field {name}")

    return cast(
        tuple[generator.GeneratedCell, ...],
        tuple(
            SimpleNamespace(
                cell=SimpleNamespace(cell_id=spec.cell_id),
                dataset=SimpleNamespace(opaque_id=f"opaque-{index}"),
                latent_truth=NoEvaluatorAccess(),
            )
            for index, spec in enumerate(generator.CELL_SPECS)
        ),
    )


def _archive() -> dict[str, np.ndarray]:
    profiles = np.zeros((17, 2, 3), dtype=np.float64)
    holdout = np.zeros_like(profiles)
    prey = np.zeros((17, 2), dtype=np.float64)
    predator = np.zeros_like(prey)
    mle = np.zeros((17, 2), dtype=np.int64)
    opaque = np.empty((17, 2), dtype="<U64")
    for cell_index, _spec in enumerate(generator.CELL_SPECS):
        for replicate_index in range(2):
            profiles[cell_index, replicate_index] = (cell_index, replicate_index, 2.0)
            holdout[cell_index, replicate_index] = (3.0, cell_index, replicate_index)
            prey[cell_index, replicate_index] = cell_index + 0.25
            predator[cell_index, replicate_index] = replicate_index + 0.5
            mle[cell_index, replicate_index] = 2
            opaque[cell_index, replicate_index] = f"opaque-{cell_index}"
    return {
        "profiles": profiles,
        "holdout_joint": holdout,
        "prey_score": prey,
        "predator_score": predator,
        "mle_index": mle,
        "opaque_ids": opaque,
        "cell_ids": np.asarray([spec.cell_id for spec in generator.CELL_SPECS]),
        "truths": np.ones(17, dtype=np.float64),
    }


def test_production_seed_selection_matches_registered_prefix() -> None:
    prefix = generator.spawn_generator_seeds(
        replay.PRODUCTION_ROOT, "production", replay.PRODUCTION_REPLICATES
    )[:6]
    assert tuple(replay.production_replicate_seed(index) for index in range(6)) == prefix
    assert tuple(range(6)) == replay.REPLAY_REPLICATE_INDICES


def test_selection_preserves_generator_order_and_opaque_ids() -> None:
    cells = _generated_cells()
    selected = replay.select_replay_cells(cells)
    assert tuple(cell.cell.cell_id for cell in selected) == replay.REPLAY_CELL_IDS
    assert tuple(cell.dataset.opaque_id for cell in selected) == (
        "opaque-0",
        "opaque-1",
        "opaque-15",
        "opaque-16",
    )
    with pytest.raises(ValueError, match="fixed"):
        replay.select_replay_cells(cells, tuple(reversed(replay.REPLAY_CELL_IDS)))


def test_replay_generation_uses_selected_production_seed_and_frozen_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cells = _generated_cells()
    seen: list[generator.GeneratorSeed] = []

    def fake_generate(
        fixed: Any, setup: Any, seed: generator.GeneratorSeed
    ) -> tuple[generator.GeneratedCell, ...]:
        seen.append(seed)
        return cells

    monkeypatch.setattr(generator, "generate_replicate", fake_generate)
    result = replay.replay_production_replicate(cast(Any, object()), cast(Any, object()), 3)
    assert result == cells
    assert seen == [replay.production_replicate_seed(3)]


def test_verification_uses_analyst_datasets_only_and_rejects_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cells = _generated_cells()
    archive = _archive()

    def fake_score(
        dataset: Any, integration: Any
    ) -> tuple[float, float, int, np.ndarray, np.ndarray]:
        assert integration == "caller-integration"
        cell_index = int(dataset.opaque_id.split("-")[1])
        return (
            cell_index + 0.25,
            0.5,
            2,
            np.asarray((cell_index, 0.0, 2.0)),
            np.asarray((3.0, cell_index, 0.0)),
        )

    monkeypatch.setattr(adequacy, "_score_dataset", fake_score)
    receipt = replay.verify_original_replay(
        cells, "caller-integration", 0, archive=archive
    )
    assert receipt.passed
    assert receipt.archive_sha256 is None
    assert receipt.profile_max_abs_diff == 0.0
    assert receipt.opaque_ids_equal
    selected_receipt = replay.verify_original_replay(
        replay.select_replay_cells(cells), "caller-integration", 0, archive=archive
    )
    assert selected_receipt.passed

    archive["profiles"] = archive["profiles"].copy()
    archive["profiles"][0, 0, 0] = 99.0
    with pytest.raises(ValueError, match="profiles_exact"):
        replay.verify_original_replay(cells, "caller-integration", 0, archive=archive)


def test_archive_loader_checks_frozen_sha256() -> None:
    archive = replay.load_production_archive()
    assert archive.sha256 == replay.ARCHIVE_SHA256
    assert archive["profiles"].shape == (17, 1000, 181)
    with pytest.raises(ValueError, match="SHA256"):
        replay.load_production_archive(expected_sha256="0" * 64)
