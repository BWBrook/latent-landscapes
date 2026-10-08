from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from latent_landscapes import capstone_calibration as calibration
from latent_landscapes import capstone_public as public_api
from latent_landscapes import capstone_references as references
from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.misspecification_generator import build_generator_setup


@pytest.fixture(scope="module")
def mechanical_context() -> references.ReferenceContext:
    root = references.MECHANICAL_ROOT
    fixed = public_api._make_fixed(
        public_api._u64_seed(root, public_api.MAP_STAGE, 0),
        public_api._u64_seed(root, public_api.SAMPLING_STAGE, 0),
    )
    public = public_api.PublicInputs(fixed, build_generator_setup(fixed), {"root": root})
    arrivals = (
        np.arange(16, dtype=float)[:, None] * 3.25 + np.arange(160, dtype=float)[None, :]
    ) % 60.0
    return references.ReferenceContext(
        public, likelihood.compress_bank(arrivals, public.setup.site_ids)
    )


def test_single_history_adapter_preserves_batch_and_rejects_mixed_dimensions(
    mechanical_context: references.ReferenceContext,
) -> None:
    prey = np.zeros((160, 13), dtype=np.int8)
    predator = np.zeros((160, 6), dtype=np.int8)
    single = references.make_observations(mechanical_context, prey, predator)
    batched = references.make_observations(mechanical_context, prey[None], predator[None])
    assert single.prey_counts.shape == (1, 160, 13)
    assert single.predator_counts.shape == (1, 160, 6)
    np.testing.assert_array_equal(single.prey_counts, batched.prey_counts)
    np.testing.assert_array_equal(single.predator_counts, batched.predator_counts)
    with pytest.raises(ValueError, match="shape"):
        references.make_observations(mechanical_context, prey, predator[None])


def test_real_effect_reference_is_fitted_checkpointed_and_resumed_without_replacement(
    mechanical_context: references.ReferenceContext, tmp_path: Path
) -> None:
    node = 382
    options: dict[str, Any] = {
        "binding": "mechanical-integration",
        "root": references.MECHANICAL_ROOT,
        "references": 1,
    }
    completed = references.run_effect_node(mechanical_context, tmp_path, node, **options)
    assert completed["completed"] == 1
    database = tmp_path / f"node-{node:04d}.sqlite"
    expected = references.sha256(database)
    metadata = references._metadata(
        "effect", options["binding"], node, references.MECHANICAL_ROOT, 1
    )
    store = references.EffectStore(database, metadata, readonly=True)
    saved = store.get(0)
    assert saved is not None and saved[2]
    assert set(saved[1]) >= {"null_fit", "free_fit", "statistics", "truth", "seeds"}
    store.close()
    batch = references.load_effect_batch(database, metadata=metadata)
    assert batch.statistics().shape == (1,)
    assert references.run_effect_node(mechanical_context, tmp_path, node, **options) == completed
    assert references.sha256(database) == expected


def metadata(count: int = 2) -> dict[str, Any]:
    return references._metadata("effect", "frozen-binding", 3, 987654321, count)


def payload(valid: bool = True) -> dict[str, Any]:
    return {
        "node": 3,
        "reference": 0,
        "statistics": {"valid": valid, "T": 4.0},
        "null_fit": {"raw_logjoint": -10.0, "numerical_status": "converged"},
        "free_fit": {"raw_logjoint": -8.0, "numerical_status": "converged"},
    }


@pytest.mark.parametrize("kind,count", [("screen", 98), ("effect", 998)])
def test_production_counts_cannot_be_reduced(kind: str, count: int) -> None:
    with pytest.raises(ValueError, match="cannot be reduced"):
        references.validate_reference_request(kind, calibration.ROOT_SEED, count)
    references.validate_reference_request(kind, 987654321, count)
    with pytest.raises(ValueError, match="root"):
        references.validate_reference_request(kind, 123456, count)


def test_generated_reference_survives_reopen_and_completed_failure_is_terminal(
    tmp_path: Path,
) -> None:
    path = tmp_path / "node.sqlite"
    original = b"mechanical observation bytes"
    store = references.EffectStore(path, metadata())
    store.generated(0, original, {"reference": 0, "phase": "generated"})
    store.close()
    store = references.EffectStore(path, metadata())
    saved = store.get(0)
    assert saved is not None and saved[0] == original and not saved[2]
    failed = payload(valid=False)
    store.completed(0, failed)
    with pytest.raises(ValueError, match="cannot replace"):
        store.completed(0, payload())
    with pytest.raises(sqlite3.IntegrityError):
        store.generated(0, b"replacement", {})
    assert store.get(0) == (original, failed, True)
    store.close()


def test_wrong_freeze_binding_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "node.sqlite"
    store = references.EffectStore(path, metadata())
    store.close()
    wrong = {**metadata(), "binding_sha256": "different"}
    with pytest.raises(ValueError, match="different frozen run"):
        references.EffectStore(path, wrong)


@pytest.mark.parametrize("field", ["observations", "payload"])
def test_checkpoint_corruption_is_detected(tmp_path: Path, field: str) -> None:
    path = tmp_path / "node.sqlite"
    store = references.EffectStore(path, metadata())
    store.generated(0, b"original", {"reference": 0})
    with store.connection:
        if field == "observations":
            store.connection.execute("UPDATE results SET observations=?", (b"changed",))
        else:
            store.connection.execute("UPDATE results SET payload=?", ('{"reference":1}',))
    with pytest.raises(ValueError, match="hash mismatch"):
        store.get(0)
    store.close()


def test_missing_and_partial_nodes_are_pending_without_mutation(tmp_path: Path) -> None:
    path = tmp_path / "node.sqlite"
    with pytest.raises(calibration.CalibrationPendingError):
        references.load_effect_batch(path, metadata=metadata())
    assert not path.exists()
    store = references.EffectStore(path, metadata())
    store.generated(0, b"original", {"reference": 0})
    store.completed(0, payload())
    store.close()
    before = references.sha256(path)
    with pytest.raises(calibration.CalibrationPendingError):
        references.load_effect_batch(path, metadata=metadata())
    assert references.sha256(path) == before


def test_invalid_complete_reference_cannot_be_rescued_by_finite_clamped_statistic(
    tmp_path: Path,
) -> None:
    path = tmp_path / "node.sqlite"
    store = references.EffectStore(path, metadata())
    for index in range(2):
        store.generated(index, f"reference-{index}".encode(), {"reference": index})
        row = {**payload(valid=index == 0), "reference": index}
        store.completed(index, row)
    store.close()
    before = references.sha256(path)
    batch = references.load_effect_batch(path, metadata=metadata())
    statistics = batch.statistics()
    assert statistics[0] == 4.0
    assert np.isnan(statistics[1])
    assert references.sha256(path) == before


def test_readonly_store_retains_hash_and_rejects_corrupt_source(tmp_path: Path) -> None:
    path = tmp_path / "node.sqlite"
    store = references.EffectStore(path, metadata())
    store.generated(0, b"a", {"reference": 0})
    store.completed(0, payload())
    store.close()
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    reader = references.EffectStore(path, metadata(), readonly=True)
    assert reader.get(0) is not None
    reader.close()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
