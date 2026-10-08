from __future__ import annotations

import ast
import hashlib
import importlib.util
import io
import json
import math
import sqlite3
import sys
from itertools import product
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit_capstone_training.py"
sys.path.insert(0, str(_SCRIPT.parent))
_SPEC = importlib.util.spec_from_file_location("audit_capstone_training", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
audit = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = audit
_SPEC.loader.exec_module(audit)


COMMON_RECEIPT_FIELDS = {
    "schema",
    "kind",
    "passed",
    "status",
    "numerical_status",
    "diagnostic_passed",
    "release_blocked",
    "audit_binding",
}


def _assert_common_receipt(value: dict[str, Any]) -> None:
    assert set(value) >= COMMON_RECEIPT_FIELDS
    json.dumps(value["audit_binding"], sort_keys=True, allow_nan=False)


def _resources() -> Any:
    site_ids = tuple(f"site-{index:03d}" for index in range(160))
    training = np.asarray([True] * 120 + [False] * 40)
    context = audit.AuditContext(
        site_ids,
        training,
        np.zeros((72, 84), dtype=np.float64),
        np.zeros(160, dtype=np.float64),
        tuple(f"cluster-{index // 5:02d}" for index in range(160)),
    )
    arrivals = np.tile(np.linspace(5.0, 70.0, 160), (8, 1))
    bank = audit.make_direct_bank(arrivals, site_ids)
    setup = SimpleNamespace(
        site_rows=np.zeros(160, dtype=np.int64),
        site_cols=np.arange(160, dtype=np.int64),
    )
    return audit.AuditResources(SimpleNamespace(landscape=None), setup, context, bank, {})


def _training_npz(path: Path, resources: Any) -> Path:
    output = path / "training.npz"
    np.savez_compressed(
        output,
        case_ids=np.asarray([f"case-{index:02d}" for index in range(4)]),
        site_ids=np.asarray(resources.context.site_ids[:120]),
        prey_counts=np.zeros((4, 120, 13), dtype=np.int8),
        predator_counts=np.zeros((4, 120, 6), dtype=np.int8),
    )
    digest = audit.sha256_file(output)
    output.with_name("training_manifest.json").write_text(
        json.dumps(
            {
                "schema_version": audit.TRAINING_SCHEMA,
                "case_count": 4,
                "site_count": 120,
                "prey_visits": 13,
                "predator_visits": 6,
                "arrays_sha256": digest,
            },
            sort_keys=True,
        )
        + "\n"
    )
    return output


def _training_kwargs(training: Path) -> dict[str, Any]:
    return {"expected_npz_sha256": audit.sha256_file(training)}


def _fake_score(
    _bank: Any,
    _context: Any,
    _prey: Any,
    _predator: Any,
    parameters: Any,
) -> float:
    return -(
        (float(parameters["h"]) - 2.0) ** 2
        + (float(parameters["beta"]) - 0.2) ** 2
        + 100.0 * (float(parameters["mu"]) - 0.0025) ** 2
        + (float(parameters["detection_sd"]) - 0.2) ** 2
    )


def _nextafter_steps(value: float, direction: float, steps: int) -> float:
    result = value
    for _ in range(steps):
        result = math.nextafter(result, direction)
    return result


@pytest.mark.parametrize(
    ("name", "bound", "direction"),
    [
        ("h", 1.0, -math.inf),
        ("h", 10.0, math.inf),
        ("beta", -2.0, -math.inf),
        ("beta", 2.0, math.inf),
        ("mu", 0.0005, -math.inf),
        ("mu", 0.006, math.inf),
        ("detection_sd", 0.0, -math.inf),
        ("detection_sd", 0.4, math.inf),
    ],
)
def test_fit_point_accepts_representation_spill_without_snapping(
    name: str, bound: float, direction: float
) -> None:
    point = {"h": 2.0, "beta": 0.0, "mu": 0.0025, "detection_sd": 0.2}
    spill = math.nextafter(bound, direction)
    point[name] = spill
    parsed = audit._fit_point(point)
    assert parsed is not None
    assert parsed[name] == spill


def test_fit_point_accepts_eight_ulps_but_rejects_nine() -> None:
    point = {"h": 2.0, "beta": 0.0, "mu": 0.0025, "detection_sd": 0.2}
    point["h"] = _nextafter_steps(10.0, math.inf, 8)
    parsed = audit._fit_point(point)
    assert parsed is not None
    assert parsed["h"] == point["h"]

    point["h"] = _nextafter_steps(10.0, math.inf, 9)
    with pytest.raises(audit.AuditStopError, match="parameter bounds"):
        audit._fit_point(point)


def _fit(model: str, h: float, beta: float, *, status: str = "converged") -> dict[str, Any]:
    point = {"h": h, "beta": beta, "mu": 0.0025, "detection_sd": 0.2}
    return {
        "model": model,
        **point,
        "raw_logjoint": _fake_score(None, None, None, None, point),
        "numerical_status": status,
        "nfev": 1,
        "elapsed_seconds": 0.0,
        "starts": [],
        "objective_gap": 0.0,
        "boundary_flags": [],
        "warnings": [],
    }


def _profile(
    name: str,
    fits: dict[str, dict[str, Any]],
    *,
    failed: bool = False,
) -> dict[str, Any]:
    coordinate, grid, model = audit.PROFILE_SPECS[name]
    parameters = []
    values = []
    statuses = []
    for index, value in enumerate(grid):
        point = {
            key: float(item)
            for key, item in fits[model].items()
            if key in {"h", "beta", "mu", "detection_sd"}
        }
        point[coordinate] = float(value)
        parameters.append(point)
        values.append(_fake_score(None, None, None, None, point))
        statuses.append("failed_optimizer" if failed and index == 0 else "converged")
    return {
        "coordinate": coordinate,
        "grid": grid.tolist(),
        "values": values,
        "parameters": parameters,
        "statuses": statuses,
        "nfev": len(grid),
        "elapsed_seconds": 0.0,
        "better_than_main": False,
        "curvature": None,
        "warnings": [],
        "curvature_coordinate": None,
    }


def _training_result(*, free_h: float = 2.0, failed_profile: bool = False) -> dict[str, Any]:
    fits = {
        "constant_free_h": _fit("constant_free_h", 2.0, 0.0),
        "adjusted_free_h": _fit("adjusted_free_h", free_h, 0.2),
        "constant_h1": _fit("constant_h1", 1.0, 0.0),
        "adjusted_h1": _fit("adjusted_h1", 1.0, 0.2),
    }
    adjusted_delta = fits["adjusted_free_h"]["raw_logjoint"] - fits["adjusted_h1"]["raw_logjoint"]
    constant_delta = fits["constant_free_h"]["raw_logjoint"] - fits["constant_h1"]["raw_logjoint"]
    adjusted_t = 2.0 * max(0.0, adjusted_delta)
    constant_t = 2.0 * max(0.0, constant_delta)
    profiles = {
        name: _profile(name, fits, failed=failed_profile and name == "adjusted_beta")
        for name in audit.PROFILE_SPECS
    }
    profile_models = {
        "constant_h": "constant_free_h",
        "adjusted_h": "adjusted_free_h",
        "adjusted_beta": "adjusted_free_h",
    }
    profile_gaps = {
        name: max(profile["values"]) - fits[profile_models[name]]["raw_logjoint"]
        for name, profile in profiles.items()
    }
    nesting = {
        "constant": -constant_delta,
        "adjusted": -adjusted_delta,
    }
    valid = adjusted_delta >= -1e-6
    paired = {
        "T": adjusted_t,
        "fits": fits,
        "statistics": {"adjusted": adjusted_t, "constant": constant_t},
        "cost": {
            "main_nfev": 4,
            "diagnostic_nfev": 0,
            "total_nfev": 4,
            "main_seconds": 0.0,
            "diagnostic_seconds": 0.0,
            "total_seconds": 0.0,
        },
    }
    return {
        "history": 0,
        "representation": "full",
        "bank_size": 8,
        "paired": paired,
        "adjusted_T": adjusted_t,
        "constant_T": constant_t,
        "fits": fits,
        "profiles": profiles,
        "profile_main_gaps": profile_gaps,
        "profile_statuses_converged": {
            name: all(status == "converged" for status in profile["statuses"])
            for name, profile in profiles.items()
        },
        "main_statuses_converged": dict.fromkeys(fits, True),
        "nesting_gaps": nesting,
        "nesting_gap_diagnostic_passed": all(value <= 1e-6 for value in nesting.values()),
        "observed_adjusted_validity": {
            "valid": valid,
            "null_finite": True,
            "free_finite": True,
            "null_converged": True,
            "free_converged": True,
            "both_converged": True,
            "free_minus_null": adjusted_delta,
            "minimum_free_minus_null": -1e-6,
        },
        "main_replay_logjoint_differences": dict.fromkeys(fits, 0.0),
    }


def _coarse_grid() -> dict[str, Any]:
    raw_points = []
    maxima = dict.fromkeys(audit.MODEL_NAMES, -np.inf)
    for h, beta, mu, sd in product(
        audit.COARSE_H, audit.COARSE_BETA, audit.COARSE_MU, audit.COARSE_SD
    ):
        point = {"h": h, "beta": beta, "mu": mu, "detection_sd": sd}
        values = [
            _fake_score(None, None, None, None, {**point, "h": candidate})
            for candidate in audit.COARSE_H
        ]
        models = list(audit.MODEL_NAMES) if beta == 0.0 else ["adjusted_free_h", "adjusted_h1"]
        raw_points.append(
            {
                "point": point,
                "applicable_models": models,
                "training_logjoint_by_history_and_h": [values],
            }
        )
        selected = values[audit.COARSE_H.index(h)]
        for model in models:
            if model.endswith("h1") and h != 1.0:
                continue
            maxima[model] = max(maxima[model], selected)
    return {
        "points": 1350,
        "expected_points": 1350,
        "grid": {
            "h": list(audit.COARSE_H),
            "beta": list(audit.COARSE_BETA),
            "mu": list(audit.COARSE_MU),
            "detection_sd": list(audit.COARSE_SD),
        },
        "raw_points": raw_points,
        "max_logjoint": {name: [value] for name, value in maxima.items()},
    }


def test_auditor_does_not_import_frozen_producer_modules() -> None:
    tree = ast.parse(_SCRIPT.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    )
    forbidden = {
        "latent_landscapes.capstone_calibration",
        "latent_landscapes.capstone_references",
        "latent_landscapes.capstone_training",
        "latent_landscapes.preinvasion_fitting",
        "latent_landscapes.preinvasion_likelihood",
    }
    assert imported.isdisjoint(forbidden)


def test_observed_screen_audit_reconstructs_all_four_by_765_scores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resources = _resources()
    monkeypatch.setattr(audit, "load_audit_resources", lambda _package: resources)

    def fake_pre_score(
        _observations: Any,
        _map_a: Any,
        _site_a: Any,
        *,
        beta: float,
        mu: float,
        detection_sd: float,
    ) -> np.ndarray[Any, Any]:
        offset = beta + 100.0 * mu + detection_sd
        return np.arange(4, dtype=np.float64) + offset

    monkeypatch.setattr(audit, "independent_pre_log_likelihood", fake_pre_score)
    training = _training_npz(tmp_path, resources)
    expected = np.stack(
        [
            np.arange(4, dtype=np.float64) + beta + 100.0 * mu + detection_sd
            for beta, mu, detection_sd in audit.nuisance_grid()
        ],
        axis=1,
    )
    result = audit.audit_observed_screen(tmp_path, training, expected, **_training_kwargs(training))
    _assert_common_receipt(result)
    assert result["passed"] is True
    assert result["numerical_status"] == "valid"
    assert result["maximum_score_abs_error"] <= audit.SCORE_TOLERANCE
    assert np.allclose(result["scores"], expected, atol=audit.SCORE_TOLERANCE, rtol=0.0)

    changed = expected.copy()
    changed[3, 764] += 2.0 * audit.SCORE_TOLERANCE
    with pytest.raises(audit.AuditStopError, match="independent scores"):
        audit.audit_observed_screen(tmp_path, training, changed, **_training_kwargs(training))


def test_training_identity_rejects_a_coherent_substituted_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resources = _resources()
    monkeypatch.setattr(audit, "load_audit_resources", lambda _package: resources)
    training = _training_npz(tmp_path, resources)
    registered_digest = audit.sha256_file(training)
    with np.load(training, allow_pickle=False) as saved:
        arrays = {name: np.asarray(saved[name]) for name in saved.files}
    arrays["prey_counts"] = arrays["prey_counts"].copy()
    arrays["prey_counts"][0, 0, 0] = 1
    np.savez_compressed(training, **arrays)
    substituted_digest = audit.sha256_file(training)
    manifest = training.with_name("training_manifest.json")
    payload = json.loads(manifest.read_text())
    payload["arrays_sha256"] = substituted_digest
    manifest.write_text(json.dumps(payload, sort_keys=True) + "\n")
    with pytest.raises(audit.AuditStopError, match="expected sealed digest"):
        audit.audit_observed_screen(
            tmp_path,
            training,
            np.zeros((4, 765)),
            expected_npz_sha256=registered_digest,
        )


def test_training_audit_separates_adjusted_validity_from_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resources = _resources()
    monkeypatch.setattr(audit, "load_audit_resources", lambda _package: resources)
    monkeypatch.setattr(audit, "direct_training_score", _fake_score)
    training = _training_npz(tmp_path, resources)
    result = _training_result(failed_profile=True)
    audited = audit.audit_training_case(
        tmp_path, training, result, None, **_training_kwargs(training)
    )
    _assert_common_receipt(audited)
    assert audited["passed"] is False
    assert audited["adjusted_valid"] is True
    assert audited["status"] == "audited_valid"
    assert audited["diagnostic_passed"] is False
    assert audited["release_blocked_for_diagnosis"] is True
    assert audited["diagnostics_change_declaration"] is False


def test_training_audit_rejects_negative_adjusted_nesting_without_clamped_rescue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resources = _resources()
    monkeypatch.setattr(audit, "load_audit_resources", lambda _package: resources)
    monkeypatch.setattr(audit, "direct_training_score", _fake_score)
    training = _training_npz(tmp_path, resources)
    result = _training_result(free_h=4.0)
    audited = audit.audit_training_case(
        tmp_path, training, result, None, **_training_kwargs(training)
    )
    assert audited["adjusted_valid"] is False
    assert audited["adjusted_T"] == 0.0
    assert audited["status"] == "audited_casewise_abstention"


def test_training_failed_fit_with_finite_parameters_is_terminal_not_audit_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resources = _resources()
    monkeypatch.setattr(audit, "load_audit_resources", lambda _package: resources)
    monkeypatch.setattr(audit, "direct_training_score", _fake_score)
    training = _training_npz(tmp_path, resources)
    result = _training_result()
    failed = result["fits"]["adjusted_free_h"]
    failed["raw_logjoint"] = None
    failed["numerical_status"] = "failed_optimizer"
    result["adjusted_T"] = None
    result["paired"]["T"] = None
    result["paired"]["statistics"]["adjusted"] = None
    result["main_replay_logjoint_differences"]["adjusted_free_h"] = None
    result["main_statuses_converged"]["adjusted_free_h"] = False
    result["observed_adjusted_validity"] = {
        "valid": False,
        "null_finite": True,
        "free_finite": False,
        "null_converged": True,
        "free_converged": False,
        "both_converged": False,
        "free_minus_null": None,
        "minimum_free_minus_null": -1e-6,
    }
    result["profile_main_gaps"]["adjusted_h"] = None
    result["profile_main_gaps"]["adjusted_beta"] = None
    result["nesting_gaps"]["adjusted"] = None
    result["nesting_gap_diagnostic_passed"] = False

    audited = audit.audit_training_case(
        tmp_path, training, result, None, **_training_kwargs(training)
    )
    _assert_common_receipt(audited)
    assert audited["numerical_status"] == "terminal_invalid"
    assert audited["adjusted_valid"] is False
    assert audited["main_score_abs_error"]["adjusted_free_h"] is None


def test_unavailable_profile_is_reconstructed_and_blocks_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resources = _resources()
    monkeypatch.setattr(audit, "load_audit_resources", lambda _package: resources)
    monkeypatch.setattr(audit, "direct_training_score", _fake_score)
    training = _training_npz(tmp_path, resources)
    result = _training_result()
    result["profiles"]["adjusted_beta"] = {
        "coordinate": "beta",
        "grid": [],
        "values": [],
        "parameters": [],
        "statuses": [],
        "statuses_converged": False,
        "nfev": 0,
        "elapsed_seconds": 0.0,
        "better_than_main": False,
        "curvature": None,
        "warnings": ["diagnostic unavailable: bounded failure"],
        "curvature_coordinate": "beta",
    }
    result["profile_main_gaps"]["adjusted_beta"] = None
    result["profile_statuses_converged"]["adjusted_beta"] = False

    audited = audit.audit_training_case(
        tmp_path, training, result, None, **_training_kwargs(training)
    )
    _assert_common_receipt(audited)
    assert audited["adjusted_valid"] is True
    assert audited["diagnostic_passed"] is False
    assert audited["release_blocked"] is True
    assert audited["profiles"]["unavailable_reconstruction_gaps"]["adjusted_beta"] is not None


def test_training_audit_scores_all_1350_coarse_points(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resources = _resources()
    monkeypatch.setattr(audit, "load_audit_resources", lambda _package: resources)
    monkeypatch.setattr(audit, "direct_training_score", _fake_score)
    training = _training_npz(tmp_path, resources)
    audited = audit.audit_training_case(
        tmp_path,
        training,
        _training_result(),
        _coarse_grid(),
        **_training_kwargs(training),
    )
    _assert_common_receipt(audited)
    assert audited["passed"] is True
    assert audited["coarse_grid"]["points_audited"] == 1350
    assert audited["audit_complete"] is True
    assert audited["release_blocked_for_diagnosis"] is False


def _write_screen_node(
    directory: Path,
    resources: Any,
    *,
    node: int,
    references: int,
    root: int,
    binding: str,
) -> None:
    prey, predator = zip(
        *[
            audit._screen_replay(resources, node, reference, root=root)
            for reference in range(references)
        ],
        strict=True,
    )
    prey_array = np.stack(prey).astype(np.int8)
    predator_array = np.stack(predator).astype(np.int8)
    neighbours = np.asarray(audit._screen_neighbors(node), dtype=np.int64)
    observations = audit.PreOnlyData(
        resources.context.site_ids,
        prey_array.astype(np.int64),
        resources.context.training,
        np.ones(160, dtype=bool),
    )
    scores = np.stack(
        [
            audit.independent_pre_log_likelihood(
                observations,
                resources.context.map_a,
                resources.context.site_a,
                beta=audit.nuisance_grid()[neighbour][0],
                mu=audit.nuisance_grid()[neighbour][1],
                detection_sd=audit.nuisance_grid()[neighbour][2],
            )
            for neighbour in neighbours
        ],
        axis=1,
    )
    contrasts = 2.0 * np.maximum(0.0, scores.max(axis=1) - scores[:, 0])
    seeds = np.asarray(
        [
            list(
                audit._expected_streams(
                    audit.SCREEN_DOMAIN,
                    node,
                    reference,
                    audit.SCREEN_STAGES,
                    root=root,
                ).values()
            )
            for reference in range(references)
        ],
        dtype=np.uint64,
    )
    path = directory / f"node-{node:04d}.npz"
    np.savez_compressed(
        path,
        prey_counts=prey_array,
        predator_counts=predator_array,
        neighbour_indices=neighbours,
        local_scores=scores,
        contrasts=contrasts,
        seeds=seeds,
    )
    receipt = {
        **audit._expected_metadata("screen", binding, node, root, references),
        "sha256": audit.sha256_file(path),
        "elapsed_seconds": 0.0,
    }
    (directory / f"node-{node:04d}.json").write_text(json.dumps(receipt))


def test_screen_audit_replays_every_mechanical_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert audit._screen_neighbors(382) == (382, 337, 427, 377, 387, 381, 383)
    resources = _resources()
    monkeypatch.setattr(audit, "load_audit_resources", lambda _package: resources)
    _write_screen_node(
        tmp_path,
        resources,
        node=382,
        references=2,
        root=audit.MECHANICAL_ROOT,
        binding="abc",
    )
    result = audit.audit_screen_node(
        tmp_path,
        tmp_path,
        382,
        binding="abc",
        root=audit.MECHANICAL_ROOT,
        references=2,
    )
    _assert_common_receipt(result)
    assert result["passed"] is True
    assert result["numerical_status"] == "valid"
    assert result["status"] == "audited_complete"
    assert result["generator_replays"] == 2
    assert result["maximum_score_abs_error"] <= audit.SCORE_TOLERANCE


def test_screen_unreceipted_checkpoint_is_pending_not_abstention(tmp_path: Path) -> None:
    (tmp_path / "node-0382.npz").write_bytes(b"interrupted")
    result = audit.audit_screen_node(
        tmp_path,
        tmp_path,
        382,
        binding="abc",
        root=audit.MECHANICAL_ROOT,
        references=2,
    )
    _assert_common_receipt(result)
    assert result["passed"] is False
    assert result["numerical_status"] == "pending"
    assert result["status"] == "pending_unreceipted"
    assert result["release_blocked"] is True
    assert result["abstain"] is False


def _effect_arrays(resources: Any, node: int) -> dict[str, np.ndarray[Any, Any]]:
    truth = audit._truth(node)
    return {
        "prey_counts": np.zeros((160, 13), dtype=np.int8),
        "predator_counts": np.zeros((160, 6), dtype=np.int8),
        "arrival": np.zeros(160, dtype=np.float64),
        "loss": np.full(160, 100.0, dtype=np.float64),
        "site_hazard": np.full(160, truth["mu"], dtype=np.float64),
        "site_detection": np.full(160, 0.65, dtype=np.float64),
        "prey_alive": np.ones((160, 13), dtype=bool),
    }


def _effect_blob(arrays: dict[str, np.ndarray[Any, Any]]) -> bytes:
    stream = io.BytesIO()
    np.savez_compressed(
        stream,
        prey_counts=arrays["prey_counts"],
        predator_counts=arrays["predator_counts"],
        evaluator_arrival=arrays["arrival"],
        evaluator_loss=arrays["loss"],
        evaluator_site_hazard=arrays["site_hazard"],
        evaluator_site_detection=arrays["site_detection"],
        evaluator_prey_alive=arrays["prey_alive"],
    )
    return stream.getvalue()


def _effect_payload(
    resources: Any,
    arrays: dict[str, np.ndarray[Any, Any]],
    node: int,
    reference: int,
    *,
    root: int,
    valid: bool,
) -> dict[str, Any]:
    truth = audit._truth(node)
    context = audit._effect_context(resources)
    score, _ = audit.independent_training_score(
        resources.bank,
        context,
        arrays["prey_counts"].astype(np.int64),
        arrays["predator_counts"].astype(np.int64),
        truth,
    )
    null_fit = {
        "model": "adjusted_h1",
        **truth,
        "raw_logjoint": score,
        "numerical_status": "converged",
        "nfev": 1,
        "starts": [],
        "boundary_flags": [],
    }
    free_fit = {
        **null_fit,
        "model": "adjusted_free_h",
        "numerical_status": "converged" if valid else "failed_optimizer",
    }
    if not valid:
        free_fit["raw_logjoint"] = None
    return {
        "node": node,
        "reference": reference,
        "truth": truth,
        "seeds": {
            "root": root,
            "namespace": audit.NAMESPACE,
            "domain": audit.EFFECT_DOMAIN,
            "node": node,
            "reference": reference,
            "streams": audit._expected_streams(
                audit.EFFECT_DOMAIN,
                node,
                reference,
                audit.EFFECT_STAGES,
                root=root,
            ),
        },
        "null_fit": null_fit,
        "free_fit": free_fit,
        "statistics": {
            "T": 0.0 if valid else None,
            "raw_T": 0.0 if valid else None,
            "free_minus_null": 0.0 if valid else None,
            "null_converged": True,
            "free_converged": valid,
            "finite_fits": valid,
            "free_ge_null": valid,
            "truth_logjoint": score,
            "null_minus_truth": 0.0,
            "null_ge_truth": True,
            "valid": valid,
        },
    }


def _write_effect_node(
    directory: Path,
    resources: Any,
    *,
    node: int,
    references: int,
    root: int,
    binding: str,
    invalid_reference: int | None = None,
    incomplete_reference: int | None = None,
) -> dict[int, dict[str, np.ndarray[Any, Any]]]:
    path = directory / f"node-{node:04d}.sqlite"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE metadata (id INTEGER PRIMARY KEY, value TEXT)")
    connection.execute(
        "CREATE TABLE results (reference INTEGER PRIMARY KEY, observations BLOB NOT NULL, "
        "observations_sha256 TEXT NOT NULL, payload TEXT NOT NULL, "
        "payload_sha256 TEXT NOT NULL, complete INTEGER NOT NULL)"
    )
    metadata = audit._expected_metadata("effect", binding, node, root, references)
    connection.execute("INSERT INTO metadata VALUES (1, ?)", (audit._canonical_json(metadata),))
    arrays_by_reference = {}
    invalid = 0
    for reference in range(references):
        arrays = _effect_arrays(resources, node)
        arrays_by_reference[reference] = arrays
        valid = reference != invalid_reference
        invalid += not valid
        payload = _effect_payload(resources, arrays, node, reference, root=root, valid=valid)
        blob = _effect_blob(arrays)
        encoded = json.dumps(payload, sort_keys=True, allow_nan=False)
        complete = 0 if reference == incomplete_reference else 1
        connection.execute(
            "INSERT INTO results VALUES (?, ?, ?, ?, ?, ?)",
            (
                reference,
                blob,
                hashlib.sha256(blob).hexdigest(),
                encoded,
                hashlib.sha256(encoded.encode()).hexdigest(),
                complete,
            ),
        )
    connection.commit()
    connection.close()
    if incomplete_reference is None:
        receipt = {
            **metadata,
            "completed": references,
            "invalid": invalid,
            "reused": 0,
            "elapsed_seconds": 0.0,
            "database_sha256": audit.sha256_file(path),
        }
        (directory / f"node-{node:04d}-complete.json").write_text(json.dumps(receipt))
    return arrays_by_reference


def test_effect_audit_scores_all_rows_and_terminal_failure_is_not_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resources = _resources()
    monkeypatch.setattr(audit, "load_audit_resources", lambda _package: resources)
    arrays = _write_effect_node(
        tmp_path,
        resources,
        node=382,
        references=3,
        root=audit.MECHANICAL_ROOT,
        binding="abc",
        invalid_reference=1,
    )
    monkeypatch.setattr(
        audit,
        "_effect_replay",
        lambda _resources, _node, reference, root: arrays[reference],
    )
    result = audit.audit_effect_node(
        tmp_path,
        tmp_path,
        382,
        binding="abc",
        root=audit.MECHANICAL_ROOT,
        references=3,
    )
    _assert_common_receipt(result)
    assert result["passed"] is True
    assert result["numerical_status"] == "terminal_invalid"
    assert result["status"] == "terminal_invalid"
    assert result["release_blocked"] is False
    assert result["abstain"] is True
    assert result["invalid_references"] == [1]
    assert result["generator_replays"] == 3


def test_effect_audit_rejects_weakened_sqlite_identity_constraints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resources = _resources()
    monkeypatch.setattr(audit, "load_audit_resources", lambda _package: resources)
    _write_effect_node(
        tmp_path,
        resources,
        node=382,
        references=2,
        root=audit.MECHANICAL_ROOT,
        binding="abc",
    )
    path = tmp_path / "node-0382.sqlite"
    connection = sqlite3.connect(path)
    connection.execute("ALTER TABLE results RENAME TO original_results")
    connection.execute(
        "CREATE TABLE results (reference INTEGER, observations BLOB, "
        "observations_sha256 TEXT, payload TEXT, payload_sha256 TEXT, complete INTEGER)"
    )
    connection.execute("INSERT INTO results SELECT * FROM original_results")
    connection.execute("INSERT INTO results SELECT * FROM original_results WHERE reference=0")
    connection.execute("DROP TABLE original_results")
    connection.commit()
    connection.close()
    receipt = tmp_path / "node-0382-complete.json"
    payload = json.loads(receipt.read_text())
    payload["database_sha256"] = audit.sha256_file(path)
    receipt.write_text(json.dumps(payload))
    with pytest.raises(audit.AuditStopError, match="schema changed"):
        audit.audit_effect_node(
            tmp_path,
            tmp_path,
            382,
            binding="abc",
            root=audit.MECHANICAL_ROOT,
            references=2,
        )


def test_effect_incomplete_row_is_pending_not_abstention(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resources = _resources()
    monkeypatch.setattr(audit, "load_audit_resources", lambda _package: resources)
    arrays = _write_effect_node(
        tmp_path,
        resources,
        node=382,
        references=2,
        root=audit.MECHANICAL_ROOT,
        binding="abc",
        incomplete_reference=1,
    )
    monkeypatch.setattr(
        audit,
        "_effect_replay",
        lambda _resources, _node, reference, root: arrays[reference],
    )
    result = audit.audit_effect_node(
        tmp_path,
        tmp_path,
        382,
        binding="abc",
        root=audit.MECHANICAL_ROOT,
        references=2,
    )
    _assert_common_receipt(result)
    assert result["passed"] is False
    assert result["numerical_status"] == "pending"
    assert result["status"] == "pending"
    assert result["release_blocked"] is True
    assert result["abstain"] is False


def test_rank_chain_distinguishes_missing_from_invalid_effect_tables() -> None:
    observed = np.zeros((4, 765), dtype=np.float64)
    screen = np.zeros((99, 765), dtype=np.float64)
    observed_t = np.ones(4, dtype=np.float64)
    tables = {node: np.zeros(999, dtype=np.float64) for node in range(765)}
    ready = audit.audit_rank_chain(observed, screen, observed_t, tables)
    _assert_common_receipt(ready)
    assert ready["passed"] is True
    assert ready["status"] == "complete"
    assert all(row["declare"] for row in ready["decisions"])

    missing = dict(tables)
    del missing[764]
    pending = audit.audit_rank_chain(observed, screen, observed_t, missing)
    _assert_common_receipt(pending)
    assert pending["passed"] is False
    assert pending["status"] == "pending"
    assert all(row["status"] == "pending_effect_tables" for row in pending["decisions"])

    invalid = dict(tables)
    invalid[764] = np.full(999, np.nan)
    abstain = audit.audit_rank_chain(observed, screen, observed_t, invalid)
    assert all(row["status"] == "abstain_invalid_effect_table" for row in abstain["decisions"])

    negative = dict(tables)
    negative[764] = np.full(999, -1e-6)
    abstain_negative = audit.audit_rank_chain(observed, screen, observed_t, negative)
    assert all(
        row["status"] == "abstain_invalid_effect_table" for row in abstain_negative["decisions"]
    )


def test_rank_chain_uses_inclusive_ties_and_berger_boos_addition() -> None:
    observed = np.zeros((4, 765), dtype=np.float64)
    screen = np.zeros((99, 765), dtype=np.float64)
    observed_t = np.zeros(4, dtype=np.float64)
    tables = {node: np.zeros(999, dtype=np.float64) for node in range(765)}
    result = audit.audit_rank_chain(observed, screen, observed_t, tables)
    assert all(row["p_BB"] == 1.0 for row in result["decisions"])
    assert all(row["declare"] is False for row in result["decisions"])

    with pytest.raises(audit.AuditStopError, match="wrong exact schema"):
        audit.audit_rank_chain(observed, screen, observed_t, tables, stored={})

    stored = {
        "q_values": result["q_values"].tolist(),
        "candidate_indices": result["candidate_indices"],
        "union": result["union"],
        "decisions": result["decisions"],
    }
    repeated = audit.audit_rank_chain(observed, screen, observed_t, tables, stored=stored)
    assert repeated["passed"] is True

    invalid_screen = screen.copy()
    invalid_screen[0, 0] = np.nan
    with pytest.raises(audit.AuditStopError, match="wrong exact schema"):
        audit.audit_rank_chain(observed, invalid_screen, observed_t, tables, stored={})
