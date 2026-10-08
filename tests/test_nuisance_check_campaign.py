from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from latent_landscapes import misspecification_generator as goal051
from latent_landscapes import nuisance_check_campaign as campaign
from latent_landscapes.goal011 import benchmark


def _rows(blocks: int = 2) -> list[tuple[int, dict[str, np.ndarray]]]:
    rows: list[tuple[int, dict[str, np.ndarray]]] = []
    for beta in range(81):
        train = np.full((blocks, 12, 181), -10.0)
        held = np.zeros_like(train)
        predator = np.arange(blocks * 12, dtype=np.float64).reshape(blocks, 12)
        train[:, :, 0] = -1.0
        train[:, :, 1] = 0.0
        train[:, :, (beta + 2) % 181] = 2.0 + beta / 100.0
        rows.append(
            (
                beta,
                {
                    "latent_training": train,
                    "latent_holdout_joint": held,
                    "latent_holdout_predator": predator,
                },
            )
        )
    return rows


def test_reducer_has_registered_dimensions_and_beta_major_h_minor_ties() -> None:
    result = campaign.reduce_rows(_rows(), blocks=2)
    assert result["evaluation_t_adj"].shape == (2, 12)
    assert result["evaluation_d_beta"].shape == (2, 12, 81)
    assert result["cell_ids"].shape == (12,)
    assert result["supplied_mean"].shape == (12,)
    assert np.all(result["evaluation_beta_hat_adj"] == campaign.BETAS[-1])
    assert np.all(result["evaluation_h_hat_adj"] == campaign.EFFECTS[82])


def test_reducer_rejects_partial_or_changed_rows() -> None:
    rows = _rows()
    with pytest.raises(ValueError, match="coverage"):
        campaign.reduce_rows(rows[:-1], blocks=2)
    changed = _rows()
    changed[1][1]["latent_holdout_predator"] = np.zeros((2, 12))
    with pytest.raises(ValueError, match="predator"):
        campaign.reduce_rows(changed, blocks=2)


def test_committed_row_rejects_partial_and_corrupt_payload(tmp_path: Path) -> None:
    path = tmp_path / "row.npz"
    campaign.commit_npz(path, {"x": np.arange(3, dtype=np.float64)}, {"identity": "x"})
    assert campaign.read_committed(path, "x") is not None
    path.with_suffix(".json").unlink()
    with pytest.raises(ValueError, match="partial"):
        campaign.read_committed(path, "x")
    campaign.commit_npz(path, {"x": np.arange(3, dtype=np.float64)}, {"identity": "x"})
    path.write_bytes(path.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        campaign.read_committed(path, "x")


def test_goal054_selection_rejects_opaque_id_mismatch(tmp_path: Path) -> None:
    n = 4
    cell_ids = np.asarray([cell for _ in range(n) for cell in campaign.GOAL054_CELLS])
    values = {
        "cell_ids": cell_ids,
        "replicate_indices": np.repeat(np.arange(n), 4),
        "opaque_ids": np.asarray([f"id-{i}" for i in range(len(cell_ids))]),
        "truth_h": np.tile([1.0, 3.0, 1.0, 3.0], n),
        "truth_beta": np.tile([0.0, 0.0, 0.6, 0.6], n),
        "predator_counts": np.zeros((len(cell_ids), 2, 6), dtype=np.uint8),
        "prey_counts": np.zeros((len(cell_ids), 2, 6), dtype=np.uint8),
        "site_ids": np.asarray(["s0", "s1"]),
        "site_cluster_ids": np.asarray(["c0", "c1"]),
        "site_splits": np.asarray(["training", "holdout"]),
        "effects": campaign.EFFECTS,
        "betas": campaign.BETAS,
    }
    values["opaque_ids"][1] = values["opaque_ids"][0]
    path = tmp_path / "observations.npz"
    np.savez_compressed(path, **values)
    with pytest.raises(ValueError, match="duplicate"):
        campaign.select_goal054_archive(path, expected_sha256=None, blocks=n)


def test_integration_identity_separates_supplied_means() -> None:
    common = {
        "core": "core",
        "beta": 0.0,
        "bank_checksum": "b" * 64,
        "map_A": np.arange(6, dtype=np.float64),
        "site_A": np.arange(2, dtype=np.float64),
    }
    low = campaign.integration_identity(**common, mean_hazard=0.0016)
    high = campaign.integration_identity(**common, mean_hazard=0.0025)
    assert low != high


def test_new_integration_passes_explicit_mean(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, float] = {}

    def normalized(beta, all_map, site, *, mean_hazard):  # type: ignore[no-untyped-def]
        seen["mean"] = mean_hazard
        return np.ones(2)

    monkeypatch.setattr(campaign.adjusted, "normalized_hazards", normalized)
    monkeypatch.setattr(
        campaign.adjusted, "build_integration", lambda prepared, effects, hazards: hazards
    )
    result = campaign.build_new_integration(
        object(), beta=0.0, map_A=np.ones(4), site_A=np.ones(2), mean_hazard=0.0016
    )
    assert seen["mean"] == 0.0016
    assert np.array_equal(result, np.ones(2))


def test_goal051_one_block_roundtrip_uses_frozen_history_fields() -> None:
    """The archive panel conversion preserves the generator's analyst fields."""

    fixed = benchmark.build_fixed_inputs()
    setup = goal051.build_generator_setup(fixed)
    seed = goal051.spawn_generator_seeds(campaign.GOAL051_PRODUCTION_ROOT, "production", 1000)[0]
    generated = goal051.generate_replicate(fixed, setup, seed)
    archive_ids = np.empty((len(goal051.CELL_SPECS), 1), dtype="<U64")
    for index, cell in enumerate(generated):
        archive_ids[index, 0] = cell.dataset.opaque_id

    panel = campaign.reconstruct_goal051_panel({"opaque_ids": archive_ids}, fixed, setup, blocks=1)
    selected = [generated[index] for index in campaign.GOAL051_INDICES]
    expected_predator = np.asarray(
        [
            [history.predator_detection_counts for history in cell.dataset.histories]
            for cell in selected
        ],
        dtype=np.uint8,
    )
    expected_prey = np.asarray(
        [
            [history.prey_detection_counts for history in cell.dataset.histories]
            for cell in selected
        ],
        dtype=np.uint8,
    )
    np.testing.assert_array_equal(panel["predator_counts"], expected_predator)
    np.testing.assert_array_equal(panel["prey_counts"], expected_prey)
    np.testing.assert_array_equal(
        panel["archive_ids"], [cell.dataset.opaque_id for cell in selected]
    )
    np.testing.assert_array_equal(panel["cell_ids"], [cell.cell.cell_id for cell in selected])
    np.testing.assert_array_equal(panel["truth_h"], [cell.cell.truth_h for cell in selected])
    np.testing.assert_array_equal(panel["site_ids"], setup.site_ids)
    np.testing.assert_array_equal(panel["site_cluster_ids"], setup.site_cluster_ids)
    np.testing.assert_array_equal(panel["site_splits"], setup.site_splits)


def test_panel_archive_ids_preserves_site_metadata_for_long_panels() -> None:
    """History rows may exceed the independent site metadata axis."""

    blocks = 1000
    site_ids = np.asarray(["site-0", "site-1"])
    clusters = np.asarray(["cluster-0", "cluster-1"])
    splits = np.asarray(["training", "holdout"])

    def panel(cells: tuple[str, ...], prefix: str) -> dict[str, np.ndarray]:
        return {
            "cell_ids": np.asarray([cell for block in range(blocks) for cell in cells]),
            "replicate_indices": np.repeat(np.arange(blocks), len(cells)),
            "archive_ids": np.asarray(
                [f"{prefix}-{block:04d}-{cell}" for block in range(blocks) for cell in cells]
            ),
            "site_ids": site_ids,
            "site_cluster_ids": clusters,
            "site_splits": splits,
        }

    goal054 = panel(campaign.GOAL054_CELLS, "g054")
    goal051 = panel(campaign.GOAL051_CELLS, "g051")
    identifiers = campaign.panel_archive_ids(goal054, goal051)
    expected_first = np.asarray(
        [f"g054-0000-{cell}" for cell in campaign.GOAL054_CELLS]
        + [f"g054-0000-{cell}" for cell in campaign.GOAL054_CELLS]
        + [f"g051-0000-{cell}" for cell in campaign.GOAL051_CELLS]
    )
    expected_last = np.asarray(
        [f"g054-0999-{cell}" for cell in campaign.GOAL054_CELLS]
        + [f"g054-0999-{cell}" for cell in campaign.GOAL054_CELLS]
        + [f"g051-0999-{cell}" for cell in campaign.GOAL051_CELLS]
    )
    np.testing.assert_array_equal(identifiers.shape, (blocks, 12))
    np.testing.assert_array_equal(identifiers[0], expected_first)
    np.testing.assert_array_equal(identifiers[-1], expected_last)
    for values, cells in ((goal054, campaign.GOAL054_CELLS), (goal051, campaign.GOAL051_CELLS)):
        for cell in cells:
            selected = campaign._cell_blocks(values, (cell,))[cell]
            np.testing.assert_array_equal(selected["site_ids"], site_ids)
            np.testing.assert_array_equal(selected["site_cluster_ids"], clusters)
            np.testing.assert_array_equal(selected["site_splits"], splits)


def test_old_integration_accepts_goal053_receipt_fingerprint(tmp_path: Path) -> None:
    """Legacy receipts use Goal053's default JSON separator encoding."""

    root = tmp_path / "old"
    path = root / "integrations" / "000.npz"
    identity_payload = {
        "core": campaign.GOAL053_CORE,
        "beta_index": 0,
        "beta": float(campaign.BETAS[0]),
    }
    legacy_identity = campaign._goal053_fingerprint(identity_payload)
    assert legacy_identity != campaign.fingerprint(identity_payload)
    campaign.commit_npz(
        path,
        {
            "category_mass": np.zeros((1, 2, 7), dtype=np.float64),
            "survival_moments": np.zeros((181, 2, 7, 7), dtype=np.float64),
        },
        {"identity": legacy_identity},
    )
    integration = campaign._load_old_integration(root, 0, ("site-0", "site-1"), "b" * 64)
    assert integration.category_mass.shape == (1, 2, 7)
    assert integration.survival_moments[0].shape == (181, 2, 7, 7)
