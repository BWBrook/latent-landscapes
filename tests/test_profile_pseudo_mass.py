from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from latent_landscapes.arc2b_campaign import CATEGORY_COUNT, PSEUDO_ARRIVALS
from latent_landscapes.goal004.observations import SURVEY_TIMES


@pytest.fixture
def module(monkeypatch: pytest.MonkeyPatch) -> Any:
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    path = root / "scripts/assess_profile_pseudo_mass.py"
    spec = importlib.util.spec_from_file_location("profile_pseudo_mass_test", path)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def _array_sha(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).view(np.uint8)).hexdigest()


def test_duplicate_bank_changes_only_empirical_multiplicity_and_pseudo_mass(
    module: Any, tmp_path: Path
) -> None:
    k = 131_072
    source = ((np.arange(k, dtype=np.float64) % 70) + 0.25)[:, None]
    raw_path = tmp_path / "A.npy"
    np.save(raw_path, source)
    parent = tmp_path / "derived-manifest.json"
    parent.write_text(
        json.dumps(
            {
                "state": "complete",
                "products": {
                    "A": {
                        "bank_size": k,
                        "row_start": k,
                        "row_stop_exclusive": 2 * k,
                        "site_ids": ["site-0"],
                        "raw_path": str(raw_path),
                        "raw_sha256": module.adapter.sha256_file(raw_path),
                        "bank_checksum": _array_sha(source),
                    }
                },
            }
        )
    )
    original_file_sha = module.adapter.sha256_file(raw_path)

    result = module.duplicate_bank(parent, tmp_path / "Adup")

    duplicated = np.load(tmp_path / "Adup/arrivals.npy", mmap_mode="r")
    assert duplicated.shape == (2 * k, 1)
    np.testing.assert_array_equal(duplicated[:k], source)
    np.testing.assert_array_equal(duplicated[k:], source)
    assert module.adapter.sha256_file(raw_path) == original_file_sha
    with np.load(tmp_path / "Adup/compressed.npz", allow_pickle=False) as bank:
        categories = np.searchsorted(
            np.array(SURVEY_TIMES, dtype=np.float64), source[:, 0], side="left"
        )
        counts = np.bincount(categories, minlength=CATEGORY_COUNT)
        np.testing.assert_array_equal(bank["category_counts"][0], 2 * counts)
        expected_mass = (2 * counts + 1.0) / (2 * k + CATEGORY_COUNT)
        np.testing.assert_array_equal(bank["category_mass"][0], expected_mass)
        np.testing.assert_array_equal(bank["power_moments"][0, :, 0], expected_mass[:-1])
        for category in range(len(SURVEY_TIMES)):
            lower = 10.0 * category
            empirical = (source[categories == category, 0] - lower) / 10.0
            pseudo = (PSEUDO_ARRIVALS[category] - lower) / 10.0
            empirical_power = np.ones(len(empirical))
            expected_moments = []
            for order in range(bank["power_moments"].shape[-1]):
                expected_moments.append(
                    (2 * float(empirical_power.sum()) + pseudo**order)
                    / (2 * k + CATEGORY_COUNT)
                )
                empirical_power *= empirical
            np.testing.assert_allclose(
                bank["power_moments"][0, category],
                expected_moments,
                rtol=2e-15,
                atol=2e-15,
            )
    assert result["bank_size"] == 2 * k
    assert result["duplication_factor"] == 2
    assert result["normalisation"].startswith("2K+7")
    assert result["duplication_of_A"]["raw_sha256"] == original_file_sha

    changed = np.load(raw_path)
    changed[0, 0] += 1.0
    np.save(raw_path, changed)
    with pytest.raises(ValueError, match="source A file identity mismatch"):
        module.duplicate_bank(parent, tmp_path / "rejected")
    assert not (tmp_path / "rejected").exists()


def _row(family: str, h: float, criterion: float, *, free: bool = False) -> dict[str, Any]:
    parameters = {"alpha": criterion, "beta": 0.0, "detection_sd": 0.2}
    if family == "positive_sigma":
        parameters["log_sigma"] = math.log(0.4)
    if free:
        parameters["log_h"] = math.log(h)
    return {"family": family, "h": h, "criterion": criterion, "parameters": parameters}


def test_fixed_fit_replay_uses_both_families_tight_free_and_tight_roots(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observations = tmp_path / "observations.npz"
    observations.write_bytes(b"one fixed history")
    observation_sha = module.adapter.sha256_file(observations)
    reference = tmp_path / "reference.json"
    reference.write_text(
        json.dumps({"source_identity": {"observations": {"sha256": observation_sha}}})
    )
    a_identity = {
        "role": "A",
        "raw_sha256": "raw-A",
        "compressed_sha256": "compressed-A",
        "bank_checksum": "checksum-A",
    }
    dup_identity = {
        "role": "Adup",
        "raw_sha256": "raw-Adup",
        "compressed_sha256": "compressed-Adup",
        "bank_checksum": "checksum-Adup",
    }
    anchor_x, standard_root_x, tight_root_x = 0.0, 0.25, 0.5
    anchor = {
        "log_h": anchor_x,
        "h": 1.0,
        "positive_sigma": _row("positive_sigma", 1.0, -10.2),
        "sigma_zero": _row("sigma_zero", 1.0, -11.2),
    }
    tight_root = {
        "log_h": tight_root_x,
        "h": math.exp(tight_root_x),
        "positive_sigma": _row("positive_sigma", math.exp(tight_root_x), -10.5),
        "sigma_zero": _row("sigma_zero", math.exp(tight_root_x), -11.5),
    }
    receipt: dict[str, Any] = {
        "status": "profile_numerically_resolved",
        "data_identity": {"observations_sha256": observation_sha},
        "bank_identity": a_identity,
        "anchors": [{"log_h": anchor_x, "h": 1.0, "w": 0.4}],
        "level_sets": [{"roots": [{"log_h": standard_root_x}]}],
        "tight_level_sets": [{"roots": [{"log_h": tight_root_x}]}],
        "points": [anchor],
        "tight_points": [tight_root],
        "free": {
            "positive_sigma": _row("positive_sigma", 9.0, -100.0, free=True),
            "sigma_zero": _row("sigma_zero", 8.0, -101.0, free=True),
        },
        "tight_free": {
            "positive_sigma": _row("positive_sigma", 3.0, -10.0, free=True),
            "sigma_zero": _row("sigma_zero", 2.5, -11.0, free=True),
        },
    }
    a_receipt = tmp_path / "A-receipt.json"
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    (input_dir / "public_inputs.npz").write_bytes(b"public")
    (input_dir / "exposure.npz").write_bytes(b"exposure")
    receipt["data_identity"].update(
        public_npz_sha256=module.adapter.sha256_file(input_dir / "public_inputs.npz"),
        exposure_sha256=module.adapter.sha256_file(input_dir / "exposure.npz"),
    )
    receipt["source_input_sha256"] = {}
    a_receipt.write_text(json.dumps(receipt))
    a_dir = tmp_path / "derived/A"
    a_dir.mkdir(parents=True)
    parent_manifest = a_dir.parent / "manifest.json"
    parent_manifest.write_text("{}")
    dup_dir = tmp_path / "Adup"
    dup_dir.mkdir()
    (dup_dir / "manifest.json").write_text(
        json.dumps(
            {
                "duplication_of_A": {
                    "raw_sha256": a_identity["raw_sha256"],
                    "bank_checksum": a_identity["bank_checksum"],
                    "raw_path": str((a_dir / "arrivals.npy").resolve()),
                    "manifest_path": str(parent_manifest.resolve()),
                    "manifest_sha256": module.adapter.sha256_file(parent_manifest),
                }
            }
        )
    )

    def identity(args: Namespace, _: dict[str, Any]) -> dict[str, Any]:
        return a_identity if args.bank_role == "A" else dup_identity

    monkeypatch.setattr(module, "validate_bank_identity", identity)
    monkeypatch.setattr(
        module,
        "load_data",
        lambda args: SimpleNamespace(kind="duplicate" if args.bank_role == "Adup" else "base"),
    )

    scenario = SimpleNamespace(
        projected_gradient=0.0,
        positive_shift=0.01,
        zero_shift=-0.01,
    )

    class Criterion:
        def __init__(self, data: Any, **_: Any):
            self.kind = data.kind

        @staticmethod
        def _bounds(fixed_h: float | None, sigma_zero: bool) -> tuple[tuple[float, float], ...]:
            count = (4 if sigma_zero else 5) if fixed_h is None else (3 if sigma_zero else 4)
            return tuple((-200.0, 200.0) for _ in range(count))

        @staticmethod
        def _projected_gradient_inf(
            gradient: np.ndarray, point: np.ndarray, bounds: Any
        ) -> float:
            return float(np.max(np.abs(gradient)))

        def _evaluate(self, point: np.ndarray, *, positive: bool) -> Any:
            shift = scenario.positive_shift if positive else scenario.zero_shift
            criterion = float(point[0]) + (shift if self.kind == "duplicate" else 0.0)
            mode = SimpleNamespace(u=np.zeros(1)) if positive else None
            gradient = np.zeros_like(point)
            gradient[0] = scenario.projected_gradient if self.kind == "duplicate" else 0.0
            return SimpleNamespace(
                success=True,
                criterion=criterion,
                objective_gradient=gradient,
                mode=mode,
            )

        def evaluate_positive(self, point: np.ndarray, **_: Any) -> Any:
            return self._evaluate(point, positive=True)

        def evaluate_sigma_zero(self, point: np.ndarray, **_: Any) -> Any:
            return self._evaluate(point, positive=False)

    monkeypatch.setattr(module, "SpatialProfileCriterion", Criterion)
    args = Namespace(
        a_receipt=a_receipt,
        reference=reference,
        observations=observations,
        input_dir=input_dir,
        a_dir=a_dir,
        dup_dir=dup_dir,
    )

    result = module.evaluate(args)

    assert not result["requires_full_refit"]
    assert result["centering"] == "tight A free fits; standard anchors and tight final roots"
    assert {row["point_source"] for row in result["points"]} == {
        "standard_anchor",
        "tight_root",
    }
    assert {row["log_h"] for row in result["points"]} == {anchor_x, tight_root_x}
    assert standard_root_x not in {row["log_h"] for row in result["points"]}
    assert len(result["family_replays"]) == 6
    assert {row["family"] for row in result["family_replays"]} == {
        "positive_sigma",
        "sigma_zero",
    }
    assert result["A_pseudo_mass"] == 7 / (131_072 + 7)
    assert result["Adup_pseudo_mass"] == 7 / (262_144 + 7)
    assert result["a_receipt_sha256"] == module.adapter.sha256_file(a_receipt)

    scenario.projected_gradient = 1.001e-3
    gradient_trigger = module.evaluate(args)
    assert gradient_trigger["requires_full_refit"]
    assert gradient_trigger["maximum_projected_gradient"] == pytest.approx(1.001e-3)

    scenario.projected_gradient = 0.0
    scenario.positive_shift = -0.6
    scenario.zero_shift = 0.6
    ownership_trigger = module.evaluate(args)
    assert ownership_trigger["requires_full_refit"]
    assert {row["log_h"] for row in ownership_trigger["material_family_ownership_changes"]} == {
        None,
        anchor_x,
        tight_root_x,
    }


@pytest.mark.parametrize("mismatch", ["raw_path", "parent_manifest"])
def test_evaluate_rejects_adup_bound_to_a_different_source_a(
    module: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mismatch: str,
) -> None:
    observations = tmp_path / "observations.npz"
    observations.write_bytes(b"one fixed history")
    observation_sha = module.adapter.sha256_file(observations)
    reference = tmp_path / "reference.json"
    reference.write_text(
        json.dumps({"source_identity": {"observations": {"sha256": observation_sha}}})
    )
    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    (input_dir / "public_inputs.npz").write_bytes(b"public")
    (input_dir / "exposure.npz").write_bytes(b"exposure")
    a_identity = {
        "role": "A",
        "raw_sha256": "raw-A",
        "compressed_sha256": "compressed-A",
        "bank_checksum": "checksum-A",
    }
    dup_identity = {
        "role": "Adup",
        "raw_sha256": "raw-Adup",
        "compressed_sha256": "compressed-Adup",
        "bank_checksum": "checksum-Adup",
    }
    a_dir = tmp_path / "derived/A"
    a_dir.mkdir(parents=True)
    parent_manifest = a_dir.parent / "manifest.json"
    parent_manifest.write_text("{}")
    a_receipt = tmp_path / "A-receipt.json"
    a_receipt.write_text(
        json.dumps(
            {
                "status": "profile_numerically_resolved",
                "source_input_sha256": {},
                "data_identity": {
                    "observations_sha256": observation_sha,
                    "public_npz_sha256": module.adapter.sha256_file(
                        input_dir / "public_inputs.npz"
                    ),
                    "exposure_sha256": module.adapter.sha256_file(input_dir / "exposure.npz"),
                },
                "bank_identity": a_identity,
            }
        )
    )
    other_raw = tmp_path / "other-A.npy"
    other_raw.write_bytes(b"different source A")
    other_manifest = tmp_path / "other-derived-manifest.json"
    other_manifest.write_text("{}")
    duplication = {
        "raw_sha256": a_identity["raw_sha256"],
        "bank_checksum": a_identity["bank_checksum"],
        "raw_path": str((a_dir / "arrivals.npy").resolve()),
        "manifest_path": str(parent_manifest.resolve()),
        "manifest_sha256": module.adapter.sha256_file(parent_manifest),
    }
    if mismatch == "raw_path":
        duplication["raw_path"] = str(other_raw.resolve())
    else:
        duplication["manifest_path"] = str(other_manifest.resolve())
        duplication["manifest_sha256"] = module.adapter.sha256_file(other_manifest)
    dup_dir = tmp_path / "Adup"
    dup_dir.mkdir()
    (dup_dir / "manifest.json").write_text(json.dumps({"duplication_of_A": duplication}))

    def identity(args: Namespace, _: dict[str, Any]) -> dict[str, Any]:
        return a_identity if args.bank_role == "A" else dup_identity

    monkeypatch.setattr(module, "validate_bank_identity", identity)
    args = Namespace(
        a_receipt=a_receipt,
        reference=reference,
        observations=observations,
        input_dir=input_dir,
        a_dir=a_dir,
        dup_dir=dup_dir,
    )

    with pytest.raises(ValueError, match="not a duplicate of the supplied fitted A bank"):
        module.evaluate(args)
