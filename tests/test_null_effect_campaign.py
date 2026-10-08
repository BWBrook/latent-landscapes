from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from latent_landscapes import null_effect_campaign as campaign


def _stable_argmax(surface: np.ndarray) -> tuple[int, int]:
    index = int(np.argmax(surface.ravel(order="C")))
    return tuple(int(value) for value in np.unravel_index(index, surface.shape))  # type: ignore[return-value]


def _crafted_rows() -> tuple[list[tuple[int, dict[str, np.ndarray]]], dict[str, np.ndarray]]:
    """Build one reference and one evaluation block from known full surfaces."""

    rows: list[tuple[int, dict[str, np.ndarray]]] = []
    reference = np.full((81, 81, 181), -100.0, dtype=np.float64)
    evaluation = np.full((8, 81, 181), -100.0, dtype=np.float64)
    reference_holdout = np.zeros_like(reference)
    evaluation_holdout = np.zeros_like(evaluation)
    reference_predator = np.zeros(81, dtype=np.float64)
    evaluation_predator = np.arange(8, dtype=np.float64) / 10.0

    for truth in range(81):
        null_fit = (truth + 2) % 81
        adjusted_fit = (truth + 3) % 81
        reference[truth, :, 0] = -np.abs(np.arange(81) - null_fit)
        reference[truth, adjusted_fit, 7] = 10.0 + truth / 100.0
        reference[truth, :, 4] = np.maximum(reference[truth, :, 4], -40.0)
        reference_holdout[truth] = np.arange(81 * 181, dtype=np.float64).reshape(81, 181) / 1000.0

    for cell in range(8):
        null_fit = (cell + 5) % 81
        adjusted_fit = (cell + 8) % 81
        evaluation[cell, :, 0] = -np.abs(np.arange(81) - null_fit)
        evaluation[cell, adjusted_fit, 9] = 40.0 + cell / 10.0
        evaluation[cell, 40, 12] = 30.0 + cell
        evaluation_holdout[cell] = (
            np.arange(81 * 181, dtype=np.float64).reshape(81, 181) / 100.0 + cell
        )

    for beta_index in range(81):
        rows.append(
            (
                beta_index,
                {
                    "latent_training": np.concatenate(
                        (reference[:, beta_index], evaluation[:, beta_index]), axis=0
                    ),
                    "latent_holdout_joint": np.concatenate(
                        (reference_holdout[:, beta_index], evaluation_holdout[:, beta_index]),
                        axis=0,
                    ),
                    "latent_holdout_predator": np.concatenate(
                        (reference_predator, evaluation_predator), axis=0
                    ),
                },
            )
        )
    expected = {
        "reference": reference,
        "evaluation": evaluation,
        "reference_holdout": reference_holdout,
        "evaluation_holdout": evaluation_holdout,
        "evaluation_predator": evaluation_predator,
    }
    return rows, expected


def test_reduce_rows_reconstructs_reference_and_evaluation_statistics() -> None:
    rows, expected = _crafted_rows()
    result = campaign.reduce_rows(rows, reference_blocks=1, evaluation_blocks=1)
    reference = expected["reference"]
    evaluation = expected["evaluation"]

    ref_global = np.max(reference, axis=(1, 2))
    ref_null = np.max(reference[:, :, 0], axis=1)
    ref_true_h1 = reference[np.arange(81), np.arange(81), 0]
    expected_t = 2.0 * (ref_global - ref_null)
    expected_d = 2.0 * (ref_null - ref_true_h1)
    expected_const = 2.0 * (np.max(reference[:, 40], axis=1)[40] - reference[40, 40, 0])
    assert np.allclose(result["reference_t_adj"][0], expected_t)
    assert np.allclose(result["reference_d_beta"][0], expected_d)
    assert np.isclose(result["reference_t_constant"][0], expected_const)

    for cell in range(8):
        surface = evaluation[cell]
        beta, h = _stable_argmax(surface)
        null_beta = int(np.argmax(surface[:, 0]))
        constant_h = int(np.argmax(surface[40]))
        assert result["evaluation_h_hat_adj"][0, cell] == campaign.EFFECTS[h]
        assert result["evaluation_beta_hat_adj"][0, cell] == campaign.BETAS[beta]
        assert result["evaluation_h_hat_constant"][0, cell] == campaign.EFFECTS[constant_h]
        assert result["evaluation_beta_hat_null"][0, cell] == campaign.BETAS[null_beta]
        assert result["evaluation_t_adj"][0, cell] == pytest.approx(
            2.0 * (surface.max() - surface[:, 0].max())
        )
        assert result["evaluation_t_constant"][0, cell] == pytest.approx(
            2.0 * (surface[40].max() - surface[40, 0])
        )
        hold = expected["evaluation_holdout"][cell]
        pred = expected["evaluation_predator"][cell]
        adjusted = hold[beta, h] - pred
        constant = hold[40, constant_h] - pred
        adjusted_neutral = hold[null_beta, 0] - pred
        constant_neutral = hold[40, 0] - pred
        assert result["evaluation_delta_holdout_adj_constant"][0, cell] == pytest.approx(
            adjusted - constant
        )
        assert result["evaluation_delta_holdout_adj_neutral"][0, cell] == pytest.approx(
            adjusted - adjusted_neutral
        )
        assert result["evaluation_delta_holdout_constant_neutral"][0, cell] == pytest.approx(
            constant - constant_neutral
        )


def test_reduce_rows_uses_first_beta_major_h_minor_tie() -> None:
    rows, _ = _crafted_rows()
    for _, values in rows:
        values["latent_training"][81:, :] = 0.0
    result = campaign.reduce_rows(rows, reference_blocks=1, evaluation_blocks=1)
    assert np.all(result["evaluation_beta_hat_adj"] == campaign.BETAS[0])
    assert np.all(result["evaluation_h_hat_adj"] == campaign.EFFECTS[0])
    assert np.all(result["evaluation_beta_hat_null"] == campaign.BETAS[0])


def test_reduce_rows_rejects_incomplete_and_duplicate_rows() -> None:
    rows, _ = _crafted_rows()
    with pytest.raises(ValueError, match="coverage"):
        campaign.reduce_rows(rows[:-1], reference_blocks=1, evaluation_blocks=1)
    duplicate = rows.copy()
    duplicate[-1] = duplicate[-2]
    with pytest.raises(ValueError, match=r"incomplete|duplicate|unordered"):
        campaign.reduce_rows(duplicate, reference_blocks=1, evaluation_blocks=1)


def test_authenticated_cache_rejects_tampering(tmp_path: Path) -> None:
    path = tmp_path / "row.npz"
    campaign.commit_npz(path, {"x": np.arange(3, dtype=np.float64)}, {"identity": "i"})
    assert campaign.read_committed(path, "i") is not None
    path.write_bytes(path.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="checksum"):
        campaign.read_committed(path, "i")


def test_archived_integration_partial_input_is_rejected_without_mutation(tmp_path: Path) -> None:
    path = tmp_path / "integrations" / "000.npz"
    path.parent.mkdir()
    path.write_bytes(b"archived-input")
    before = path.read_bytes()
    with pytest.raises(ValueError, match="missing or partial"):
        campaign._load_old_integration(tmp_path, 0, ("site",), "a" * 64)
    assert path.read_bytes() == before
