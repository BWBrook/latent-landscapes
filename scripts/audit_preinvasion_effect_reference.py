#!/usr/bin/env python3
"""Independent Goal 058 effect-reference audit.

The scorer reuses only the direct empirical-bank reconstruction from the Goal
056 independent audit.  It does not import the production likelihood,
emissions, hazard normalizer, fitter, or Goal 058 production module.  The CLI
reads completed artifacts and never fits or generates a reference history.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from audit_preinvasion_feasibility import (
    DirectBank,
    direct_survival_moments,
    load_direct_bank,
    normalized_hazards,
    predator_emissions,
    prey_factors,
)
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]
IntArray = NDArray[np.int64]

SCHEMA_VERSION = "goal058-effect-reference-v1"
ROOT_SEED = 2026100402
SEED_NAMESPACE = 58
REFERENCE_COUNT = 999
SCORE_TOLERANCE = 1e-8
STATISTIC_TOLERANCE = 1e-6
STREAM_NAMES = (
    "spread",
    "prey_loss",
    "predator_visits",
    "site_detection",
    "prey_visits",
)
STAGES = {name: stage for stage, name in enumerate(STREAM_NAMES, start=1)}
PREY_TIMES = np.arange(-60.0, 61.0, 10.0)
PREDATOR_TIMES = np.arange(10.0, 61.0, 10.0)
NODE_TRUTHS: dict[int, dict[str, float]] = {
    382: {"h": 1.0, "beta": 0.0, "mu": 0.0025, "detection_sd": 0.2},
    0: {"h": 1.0, "beta": -2.0, "mu": 0.0005, "detection_sd": 0.0},
    764: {"h": 1.0, "beta": 2.0, "mu": 0.006, "detection_sd": 0.4},
    44: {"h": 1.0, "beta": -2.0, "mu": 0.006, "detection_sd": 0.4},
}
NODE_ORDER = (382, 0, 764, 44)
REPLAY_REFERENCES = (0, 499, 998)


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def finite_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def stage_seed(node_id: int, reference: int, stage: int, *, root: int) -> int:
    sequence = np.random.SeedSequence(
        [int(root), SEED_NAMESPACE, int(node_id), int(reference), int(stage)]
    )
    return int(sequence.generate_state(1, dtype=np.uint64)[0])


def expected_streams(node_id: int, reference: int, *, root: int) -> dict[str, int]:
    return {
        name: stage_seed(node_id, reference, stage, root=root)
        for name, stage in STAGES.items()
    }


def expected_ledger(*, root: int, references: int = REFERENCE_COUNT) -> NDArray[np.uint64]:
    rows = []
    for node_id in NODE_ORDER:
        for reference in range(references):
            rows.append(
                tuple(
                    stage_seed(node_id, reference, stage, root=root)
                    for stage in range(1, 6)
                )
            )
    return np.asarray(rows, dtype=np.uint64)


def validate_ledger(
    ledger_path: Path,
    *,
    root: int = ROOT_SEED,
    references: int = REFERENCE_COUNT,
) -> dict[str, Any]:
    with np.load(ledger_path, allow_pickle=False) as saved:
        if set(saved.files) != {"ledger"}:
            raise ValueError("seed ledger archive has an unexpected schema")
        observed = np.asarray(saved["ledger"], dtype=np.uint64)
    expected = expected_ledger(root=root, references=references)
    matches = observed.shape == expected.shape and np.array_equal(observed, expected)
    digest = hashlib.sha256(np.ascontiguousarray(observed).tobytes()).hexdigest()
    return {
        "passed": bool(matches),
        "shape": list(observed.shape),
        "expected_shape": list(expected.shape),
        "sha256": digest,
        "root": root,
        "namespace": SEED_NAMESPACE,
        "references": references,
    }


@dataclass(frozen=True)
class AuditContext:
    site_ids: tuple[str, ...]
    training: BoolArray
    map_a: FloatArray
    site_a: FloatArray


def load_context(path: Path) -> AuditContext:
    with np.load(path, allow_pickle=False) as values:
        required = {
            "site_ids",
            "site_splits",
            "map_a",
            "site_a",
            "prey_times",
            "predator_times",
        }
        missing = required - set(values.files)
        if missing:
            raise ValueError(f"context is missing fields: {sorted(missing)}")
        site_ids = tuple(np.asarray(values["site_ids"]).astype(str))
        splits = np.asarray(values["site_splits"]).astype(str)
        map_a = np.asarray(values["map_a"], dtype=np.float64)
        site_a = np.asarray(values["site_a"], dtype=np.float64)
        prey_times = np.asarray(values["prey_times"], dtype=np.float64)
        predator_times = np.asarray(values["predator_times"], dtype=np.float64)
    training = splits == "training"
    if (
        len(site_ids) != 160
        or splits.shape != (160,)
        or site_a.shape != (160,)
        or int(training.sum()) != 120
        or not np.isfinite(map_a).all()
        or not np.isfinite(site_a).all()
    ):
        raise ValueError("context differs from the registered 160-site design")
    if len(set(site_ids)) != 160:
        raise ValueError("context site identifiers are not unique")
    if not np.array_equal(prey_times, PREY_TIMES) or not np.array_equal(
        predator_times, PREDATOR_TIMES
    ):
        raise ValueError("context observation calendar differs from registration")
    return AuditContext(site_ids, training, map_a, site_a)


def _truth_from_row(row: Mapping[str, Any]) -> dict[str, float] | None:
    raw = row.get("truth")
    if not isinstance(raw, Mapping):
        return None
    aliases = {
        "h": raw.get("h", raw.get("effect")),
        "beta": raw.get("beta"),
        "mu": raw.get("mu", raw.get("mean_hazard")),
        "detection_sd": raw.get("detection_sd"),
    }
    output = {name: finite_float(value) for name, value in aliases.items()}
    if any(value is None for value in output.values()):
        return None
    return {name: float(value) for name, value in output.items() if value is not None}


def _fit_point(fit: Any) -> dict[str, float] | None:
    if not isinstance(fit, Mapping):
        return None
    values = {name: finite_float(fit.get(name)) for name in ("h", "beta", "mu", "detection_sd")}
    if any(value is None for value in values.values()):
        parameters = fit.get("parameters")
        if isinstance(parameters, Mapping):
            values = {
                name: finite_float(parameters.get(name))
                for name in ("h", "beta", "mu", "detection_sd")
            }
    if any(value is None for value in values.values()):
        return None
    return {name: float(value) for name, value in values.items() if value is not None}


def _fit_converged(fit: Any) -> bool:
    return isinstance(fit, Mapping) and fit.get("numerical_status") == "converged"


def _score_from_moments(
    bank: DirectBank,
    moments: FloatArray,
    prey_counts: IntArray,
    predator_probability: FloatArray,
    detection_sd: float,
) -> FloatArray:
    events, alive = prey_factors(prey_counts, detection_sd)
    weighted = np.einsum("stc,sc->st", moments, predator_probability, optimize=True)
    probability = np.sum((weighted[:, :-1] - weighted[:, 1:]) * events, axis=1)
    probability += weighted[:, -1] * alive
    predator_marginal = np.sum(bank.category_mass * predator_probability, axis=1)
    if (
        not np.isfinite(probability).all()
        or not np.isfinite(predator_marginal).all()
        or (probability <= 0).any()
        or (predator_marginal <= 0).any()
    ):
        raise ValueError("independent observation probability is invalid")
    return np.log(probability)


def independent_training_score(
    bank: DirectBank,
    context: AuditContext,
    prey_counts: IntArray,
    predator_counts: IntArray,
    parameters: Mapping[str, float],
    *,
    moments: FloatArray | None = None,
) -> tuple[float, FloatArray]:
    if moments is None:
        hazards = normalized_hazards(
            parameters["beta"], parameters["mu"], context.map_a, context.site_a
        )
        moments = direct_survival_moments(bank, hazards, parameters["h"])
    emissions = predator_emissions(predator_counts)
    joint = _score_from_moments(
        bank,
        moments,
        prey_counts,
        emissions,
        parameters["detection_sd"],
    )
    return float(np.sum(joint[context.training], dtype=np.float64)), moments


def _opaque_id(prey: NDArray[np.generic], predator: NDArray[np.generic]) -> str:
    # Production hashes predator first and prey second.
    return hashlib.sha256(predator.tobytes() + prey.tobytes()).hexdigest()


def validate_latents(
    arrays: Mapping[str, NDArray[np.generic]],
    truth: Mapping[str, float],
    context: AuditContext,
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    prey = np.asarray(arrays["prey_counts"])
    predator = np.asarray(arrays["predator_counts"])
    checks["count_shapes"] = prey.shape == (160, 13) and predator.shape == (160, 6)
    checks["counts_integer_range"] = bool(
        np.issubdtype(prey.dtype, np.integer)
        and np.issubdtype(predator.dtype, np.integer)
        and (prey >= 0).all()
        and (prey <= 2).all()
        and (predator >= 0).all()
        and (predator <= 2).all()
    )
    if not checks["count_shapes"] or not checks["counts_integer_range"]:
        return {"passed": False, "checks": checks, "max_hazard_absdiff": None}
    required_latents = {"arrival", "loss", "site_hazard", "site_detection", "prey_alive"}
    if not required_latents.issubset(arrays):
        checks["latent_fields_present"] = False
        return {"passed": False, "checks": checks, "max_hazard_absdiff": None}
    arrival = np.asarray(arrays["arrival"], dtype=np.float64)
    loss = np.asarray(arrays["loss"], dtype=np.float64)
    hazard = np.asarray(arrays["site_hazard"], dtype=np.float64)
    detection = np.asarray(arrays["site_detection"], dtype=np.float64)
    prey_alive = np.asarray(arrays["prey_alive"], dtype=bool)
    checks["latent_fields_present"] = True
    checks["latent_shapes"] = bool(
        arrival.shape == loss.shape == hazard.shape == detection.shape == (160,)
        and prey_alive.shape == (160, 13)
    )
    if not checks["latent_shapes"]:
        return {"passed": False, "checks": checks, "max_hazard_absdiff": None}
    checks["latents_finite"] = bool(
        np.isfinite(arrival).all()
        and np.isfinite(loss).all()
        and np.isfinite(hazard).all()
        and np.isfinite(detection).all()
    )
    expected_hazard = normalized_hazards(
        truth["beta"], truth["mu"], context.map_a, context.site_a
    )
    hazard_difference = float(np.max(np.abs(hazard - expected_hazard)))
    checks["hazards_match_independent_normalizer"] = hazard_difference <= 1e-12
    checks["prey_alive_matches_loss"] = bool(
        np.array_equal(prey_alive, loss[:, None] > PREY_TIMES[None, :])
    )
    checks["counts_respect_latent_presence"] = bool(
        np.all(prey[~prey_alive] == 0)
        and np.all(predator[arrival[:, None] > PREDATOR_TIMES[None, :]] == 0)
    )
    checks["detection_domain"] = bool((detection >= 0).all() and (detection <= 1).all())
    if truth["detection_sd"] == 0.0:
        checks["zero_sd_detection_fixed"] = bool(np.array_equal(detection, np.full(160, 0.65)))
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "max_hazard_absdiff": hazard_difference,
    }


def _row_identity_checks(
    row: Mapping[str, Any], node_id: int, reference: int, *, root: int
) -> dict[str, bool]:
    truth = _truth_from_row(row)
    expected_truth = NODE_TRUTHS[node_id]
    seed_ids = row.get("seed_ids")
    streams = seed_ids.get("streams") if isinstance(seed_ids, Mapping) else None
    return {
        "schema_version": row.get("schema_version") == SCHEMA_VERSION,
        "node_id": row.get("node_id") == node_id,
        "reference": row.get("reference") == reference,
        "truth": truth == expected_truth,
        "seed_header": bool(
            isinstance(seed_ids, Mapping)
            and seed_ids.get("root") == root
            and seed_ids.get("namespace") == SEED_NAMESPACE
            and seed_ids.get("coarse_node") == node_id
            and seed_ids.get("reference") == reference
        ),
        "seed_streams": streams == expected_streams(node_id, reference, root=root),
    }


def audit_row(
    row: Mapping[str, Any],
    arrays: Mapping[str, NDArray[np.generic]] | None,
    bank: DirectBank,
    context: AuditContext,
    *,
    node_id: int,
    reference: int,
    root: int,
    true_moments: FloatArray | None = None,
) -> dict[str, Any]:
    identity = _row_identity_checks(row, node_id, reference, root=root)
    truth = _truth_from_row(row)
    result: dict[str, Any] = {
        "node_id": node_id,
        "reference": reference,
        "identity_checks": identity,
        "artifact_present": arrays is not None,
        "production_error": row.get("error"),
        "points": {},
        "score_mismatch": False,
        "kernel_failure": False,
    }
    if arrays is None or truth is None:
        result.update(
            {
                "latent_check": None,
                "statistic": None,
                "production_fit_valid": False,
                "audit_consistent": False,
                "audit_valid": False,
            }
        )
        return result

    latent = validate_latents(arrays, truth, context)
    result["latent_check"] = latent
    raw_prey = np.asarray(arrays["prey_counts"])
    raw_predator = np.asarray(arrays["predator_counts"])
    prey = np.asarray(raw_prey, dtype=np.int64)
    predator = np.asarray(raw_predator, dtype=np.int64)
    raw_seed_array = np.asarray(arrays.get("seed_ids", []), dtype=np.uint64)
    expected_seed_array = np.asarray(
        [expected_streams(node_id, reference, root=root)[name] for name in STREAM_NAMES],
        dtype=np.uint64,
    )
    result["seed_array_matches"] = bool(
        raw_seed_array.shape == (5,) and np.array_equal(raw_seed_array, expected_seed_array)
    )
    observations = row.get("observations")
    opaque = observations.get("opaque_id") if isinstance(observations, Mapping) else None
    result["opaque_id_matches"] = opaque == _opaque_id(raw_prey, raw_predator)

    null_fit = row.get("null_fit")
    free_fit = row.get("free_fit")
    null_parameters = _fit_point(null_fit)
    free_parameters = _fit_point(free_fit)
    points: tuple[tuple[str, dict[str, float] | None, Any], ...] = (
        ("truth", truth, (row.get("statistics") or {}).get("truth_logjoint")),
        (
            "null",
            null_parameters,
            null_fit.get("raw_logjoint") if isinstance(null_fit, Mapping) else None,
        ),
        (
            "free",
            free_parameters,
            free_fit.get("raw_logjoint") if isinstance(free_fit, Mapping) else None,
        ),
    )
    direct_scores: dict[str, float] = {}
    for name, parameters, stored_raw in points:
        point: dict[str, Any] = {
            "parameters_available": parameters is not None,
            "parameters": parameters,
            "stored": finite_float(stored_raw),
            "direct": None,
            "absolute_difference": None,
            "passed": False,
            "error": None,
        }
        if parameters is not None:
            try:
                direct, computed_moments = independent_training_score(
                    bank,
                    context,
                    prey,
                    predator,
                    parameters,
                    moments=true_moments if name == "truth" else None,
                )
                if name == "truth" and true_moments is None:
                    true_moments = computed_moments
                point["direct"] = direct
                direct_scores[name] = direct
                if point["stored"] is not None:
                    difference = abs(direct - point["stored"])
                    point["absolute_difference"] = difference
                    point["passed"] = difference <= SCORE_TOLERANCE
                    if not point["passed"]:
                        result["score_mismatch"] = True
            except (ArithmeticError, FloatingPointError, ValueError) as exc:
                point["error"] = f"{type(exc).__name__}: {exc}"
                result["kernel_failure"] = True
        result["points"][name] = point

    statistic: dict[str, Any] = {
        "stored": None,
        "direct": None,
        "absolute_difference": None,
        "passed": False,
        "null_ge_truth": False,
        "free_ge_null": False,
    }
    statistics = row.get("statistics")
    if isinstance(statistics, Mapping):
        statistic["stored"] = finite_float(statistics.get("T", statistics.get("T_clamped")))
    if "null" in direct_scores and "free" in direct_scores:
        statistic["direct"] = 2.0 * max(0.0, direct_scores["free"] - direct_scores["null"])
        if statistic["stored"] is not None:
            statistic["absolute_difference"] = abs(statistic["direct"] - statistic["stored"])
            statistic["passed"] = statistic["absolute_difference"] <= STATISTIC_TOLERANCE
    if "truth" in direct_scores and "null" in direct_scores:
        statistic["null_ge_truth"] = (
            direct_scores["null"] >= direct_scores["truth"] - STATISTIC_TOLERANCE
        )
    if "null" in direct_scores and "free" in direct_scores:
        statistic["free_ge_null"] = (
            direct_scores["free"] >= direct_scores["null"] - STATISTIC_TOLERANCE
        )
    result["statistic"] = statistic
    production_fit_valid = bool(
        _fit_converged(null_fit)
        and _fit_converged(free_fit)
        and finite_float(null_fit.get("raw_logjoint")) is not None
        and finite_float(free_fit.get("raw_logjoint")) is not None
    ) if isinstance(null_fit, Mapping) and isinstance(free_fit, Mapping) else False
    fit_contract = {
        "null_model": isinstance(null_fit, Mapping)
        and null_fit.get("model") == "adjusted_h1",
        "free_model": isinstance(free_fit, Mapping)
        and free_fit.get("model") == "adjusted_free_h",
        "null_point_or_explicit_failure": bool(
            (null_parameters is not None and null_parameters["h"] == 1.0)
            or (
                null_parameters is None
                and isinstance(null_fit, Mapping)
                and not _fit_converged(null_fit)
                and finite_float(null_fit.get("raw_logjoint")) is None
            )
        ),
        "free_point_or_explicit_failure": bool(
            free_parameters is not None
            or (
                isinstance(free_fit, Mapping)
                and not _fit_converged(free_fit)
                and finite_float(free_fit.get("raw_logjoint")) is None
            )
        ),
        "diagnostics_retained": bool(
            isinstance(null_fit, Mapping)
            and isinstance(free_fit, Mapping)
            and all(name in null_fit for name in ("starts", "nfev", "boundary_flags"))
            and all(name in free_fit for name in ("starts", "nfev", "boundary_flags"))
        ),
    }
    result["fit_contract"] = fit_contract
    result["production_fit_valid"] = production_fit_valid
    reference_valid = bool(
        all(identity.values())
        and latent["passed"]
        and result["seed_array_matches"]
        and result["opaque_id_matches"]
        and all(fit_contract.values())
        and production_fit_valid
        and all(point["passed"] for point in result["points"].values())
        and statistic["passed"]
        and statistic["null_ge_truth"]
        and statistic["free_ge_null"]
        and row.get("error") is None
    )
    result["audit_valid"] = reference_valid
    available_point_checks = [
        (not point["parameters_available"] and point["stored"] is None)
        or (
            point["parameters_available"]
            and point["direct"] is not None
            and point["stored"] is not None
            and point["passed"]
        )
        for point in result["points"].values()
    ]
    statistic_available = "null" in direct_scores and "free" in direct_scores
    statistic_consistent = (
        bool(statistic["passed"])
        if statistic_available
        else statistic["stored"] is None
    )
    declared_valid = statistics.get("valid") if isinstance(statistics, Mapping) else None
    result["declared_valid_matches"] = declared_valid is reference_valid
    result["audit_consistent"] = bool(
        all(identity.values())
        and latent["passed"]
        and result["seed_array_matches"]
        and result["opaque_id_matches"]
        and all(fit_contract.values())
        and all(available_point_checks)
        and statistic_consistent
        and not result["kernel_failure"]
        and not result["score_mismatch"]
        and result["declared_valid_matches"]
    )
    return result


def _load_history(path: Path) -> dict[str, NDArray[np.generic]]:
    with np.load(path, allow_pickle=False) as values:
        return {name: np.asarray(values[name]) for name in values.files}


def _history_paths(run: Path, node_id: int, reference: int) -> tuple[Path, Path]:
    stem = run / "histories" / f"node-{node_id:04d}" / f"ref-{reference:04d}"
    return stem.with_suffix(".json"), stem.with_suffix(".npz")


_WORKER_BANK: DirectBank | None = None
_WORKER_CONTEXT: AuditContext | None = None
_WORKER_ROOT = ROOT_SEED
_TRUE_MOMENT_CACHE: dict[int, FloatArray] = {}


def _initialize_worker(
    bank_path: str,
    expected_bank_sha256: str,
    context_path: str,
    root: int,
) -> None:
    global _WORKER_BANK, _WORKER_CONTEXT, _WORKER_ROOT, _TRUE_MOMENT_CACHE
    _WORKER_CONTEXT = load_context(Path(context_path))
    _WORKER_BANK = load_direct_bank(
        Path(bank_path), _WORKER_CONTEXT.site_ids, expected_bank_sha256
    )
    _WORKER_ROOT = root
    _TRUE_MOMENT_CACHE = {}


def _audit_path(task: tuple[str, int, int]) -> dict[str, Any]:
    run_raw, node_id, reference = task
    if _WORKER_BANK is None or _WORKER_CONTEXT is None:
        raise RuntimeError("audit worker was not initialized")
    run = Path(run_raw)
    row_path, array_path = _history_paths(run, node_id, reference)
    row = read_json(row_path) if row_path.is_file() else {
        "node_id": node_id,
        "reference": reference,
        "error": "missing row artifact",
    }
    arrays = _load_history(array_path) if array_path.is_file() else None
    moments = _TRUE_MOMENT_CACHE.get(node_id)
    audited = audit_row(
        row,
        arrays,
        _WORKER_BANK,
        _WORKER_CONTEXT,
        node_id=node_id,
        reference=reference,
        root=_WORKER_ROOT,
        true_moments=moments,
    )
    # Cache is populated lazily without calling a production scorer.  The
    # audit_row API intentionally does not expose the large array.
    if moments is None:
        truth = NODE_TRUTHS[node_id]
        hazards = normalized_hazards(
            truth["beta"], truth["mu"], _WORKER_CONTEXT.map_a, _WORKER_CONTEXT.site_a
        )
        _TRUE_MOMENT_CACHE[node_id] = direct_survival_moments(
            _WORKER_BANK, hazards, truth["h"]
        )
    return audited


def verify_file_hashes(run: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    raw_files = manifest.get("artifact_sha256", manifest.get("files"))
    if not isinstance(raw_files, Mapping):
        return {"passed": False, "reason": "manifest has no file hash mapping", "mismatches": []}
    mismatches = []
    for relative, expected in raw_files.items():
        path = run / str(relative)
        if not path.is_file() or sha256_file(path) != expected:
            mismatches.append(str(relative))
    return {"passed": not mismatches, "mismatches": mismatches, "count": len(raw_files)}


def verify_provenance(
    run: Path,
    manifest: Mapping[str, Any],
    *,
    registration: Path,
    source_freeze: Path,
    freeze: Path,
    qualification: Path,
    root: int,
    references: int,
) -> dict[str, Any]:
    source = read_json(source_freeze)
    qualification_payload = read_json(qualification)
    freeze_meta = read_json(freeze / "freeze.json")
    qualification_ok = bool(
        qualification_payload.get("passed") is True
        or qualification_payload.get("status") == "qualified"
    )
    frozen_nodes = freeze_meta.get("nodes")
    frozen_node_ids = (
        [entry.get("coarse_id") for entry in frozen_nodes if isinstance(entry, Mapping)]
        if isinstance(frozen_nodes, list)
        else []
    )
    manifest_nodes = manifest.get("nodes")
    manifest_node_ids = (
        [entry.get("node_id") for entry in manifest_nodes if isinstance(entry, Mapping)]
        if isinstance(manifest_nodes, list)
        else []
    )
    checks = {
        "schema_version": manifest.get("schema_version") == SCHEMA_VERSION,
        "root": manifest.get("root") == root,
        "namespace": manifest.get("namespace") == SEED_NAMESPACE,
        "references": manifest.get("refs_per_node") == references,
        "stream_stages": manifest.get("stream_stages") == STAGES,
        "node_order": manifest_node_ids == list(NODE_ORDER),
        "bank_receipt": manifest.get("bank_receipt")
        == qualification_payload.get("bank_receipt"),
        "context_sha256": manifest.get("context_sha256")
        == sha256_file(run / "context.npz"),
        "registration_sha256": manifest.get("registration_sha256")
        == sha256_file(registration),
        "source_freeze_sha256": manifest.get("source_freeze_sha256")
        == sha256_file(source_freeze),
        "freeze_sha256": manifest.get("freeze_sha256") == sha256_file(freeze / "freeze.json"),
        "qualification_sha256": manifest.get("qualification_sha256")
        == sha256_file(qualification),
        "ledger_sha256": manifest.get("ledger_sha256") == freeze_meta.get("sha256"),
        "freeze_root": freeze_meta.get("root") == root,
        "freeze_namespace": freeze_meta.get("namespace") == SEED_NAMESPACE,
        "freeze_references": freeze_meta.get("references") == references,
        "freeze_stage_order": freeze_meta.get("stage_order") == list(STREAM_NAMES),
        "freeze_node_order": frozen_node_ids == list(NODE_ORDER),
        "qualification_passed": qualification_ok,
        "source_freeze_has_hashes": isinstance(source.get("source_hashes"), Mapping),
    }
    live_mismatches = []
    source_hashes = source.get("source_hashes")
    repository_value = source.get("repository")
    if isinstance(source_hashes, Mapping) and isinstance(repository_value, str):
        repository = Path(repository_value)
        for relative, expected in source_hashes.items():
            path = repository / str(relative)
            if not path.is_file() or sha256_file(path) != expected:
                live_mismatches.append(str(relative))
        checks["live_source_matches_freeze"] = not live_mismatches
    else:
        checks["live_source_matches_freeze"] = False
    file_check = verify_file_hashes(run, manifest)
    checks["run_file_hashes"] = file_check["passed"]
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "live_source_mismatches": live_mismatches,
        "file_hashes": file_check,
    }


def validate_node_table(
    run: Path,
    node_id: int,
    rows: Sequence[Mapping[str, Any]],
    *,
    references: int,
) -> dict[str, Any]:
    path = run / f"node-{node_id:04d}.npz"
    if not path.is_file():
        return {"passed": False, "path": str(path), "reason": "missing table"}
    with np.load(path, allow_pickle=False) as saved:
        required = {
            "node_id",
            "reference",
            "T",
            "valid",
            "usable",
            "null_raw_logjoint",
            "free_raw_logjoint",
        }
        if not required.issubset(saved.files):
            return {"passed": False, "path": str(path), "reason": "table schema"}
        stored_node_id = int(np.asarray(saved["node_id"]).item())
        reference_ids = np.asarray(saved["reference"], dtype=np.int64)
        statistics = np.asarray(saved["T"], dtype=np.float64)
        valid = np.asarray(saved["valid"], dtype=bool)
        usable = bool(np.asarray(saved["usable"]).item())
        null_scores = np.asarray(saved["null_raw_logjoint"], dtype=np.float64)
        free_scores = np.asarray(saved["free_raw_logjoint"], dtype=np.float64)
    expected_references = np.arange(references, dtype=np.int64)
    audit_valid = np.asarray([bool(row["audit_valid"]) for row in rows], dtype=bool)
    audit_statistics = np.asarray(
        [
            float(row["statistic"]["direct"])
            if row.get("statistic") and row["statistic"].get("direct") is not None
            else np.nan
            for row in rows
        ],
        dtype=np.float64,
    )
    audit_null = np.asarray(
        [
            float(row["points"]["null"]["direct"])
            if row.get("points", {}).get("null", {}).get("direct") is not None
            else np.nan
            for row in rows
        ],
        dtype=np.float64,
    )
    audit_free = np.asarray(
        [
            float(row["points"]["free"]["direct"])
            if row.get("points", {}).get("free", {}).get("direct") is not None
            else np.nan
            for row in rows
        ],
        dtype=np.float64,
    )
    checks = {
        "node_id": stored_node_id == node_id,
        "shape": reference_ids.shape
        == statistics.shape
        == valid.shape
        == null_scores.shape
        == free_scores.shape
        == (len(expected_references),),
        "references": np.array_equal(reference_ids, expected_references),
        "valid_flags": np.array_equal(valid, audit_valid),
        "null_scores": bool(
            np.allclose(
                null_scores,
                audit_null,
                rtol=0.0,
                atol=SCORE_TOLERANCE,
                equal_nan=True,
            )
        ),
        "free_scores": bool(
            np.allclose(
                free_scores,
                audit_free,
                rtol=0.0,
                atol=SCORE_TOLERANCE,
                equal_nan=True,
            )
        ),
        "statistics": bool(
            np.allclose(
                statistics,
                audit_statistics,
                rtol=0.0,
                atol=STATISTIC_TOLERANCE,
                equal_nan=True,
            )
        ),
        "whole_table_valid_rule": bool(valid.all()) == bool(audit_valid.all()),
        "usable_flag": usable == bool(audit_valid.all()),
    }
    return {
        "passed": all(checks.values()),
        "path": str(path),
        "checks": checks,
        "usable": bool(audit_valid.all()),
        "invalid": int((~audit_valid).sum()),
    }


def validate_shared_table(
    run: Path,
    node_checks: Mapping[int, Mapping[str, Any]],
    *,
    references: int,
) -> dict[str, Any]:
    """Load the deterministic four-table mapping and verify abstention state."""
    summaries: dict[int, dict[str, Any]] = {}
    summary_hashes: dict[int, str] = {}
    for node_id in NODE_ORDER:
        path = run / f"node-{node_id:04d}.json"
        if path.is_file():
            summaries[node_id] = read_json(path)
            summary_hashes[node_id] = sha256_file(path)
    checks = {
        "four_tables_loaded": len(node_checks) == 4
        and all(node_checks[node_id]["table"]["passed"] for node_id in NODE_ORDER),
        "four_summaries_loaded": set(summaries) == set(NODE_ORDER),
        "summary_identities": all(
            summaries.get(node_id, {}).get("node_id") == node_id for node_id in NODE_ORDER
        ),
        "summary_counts": all(
            summaries.get(node_id, {}).get("attempted") == references
            and summaries.get(node_id, {}).get("valid") == node_checks[node_id]["valid"]
            and summaries.get(node_id, {}).get("invalid") == node_checks[node_id]["invalid"]
            for node_id in NODE_ORDER
        ),
        "summary_usability": all(
            summaries.get(node_id, {}).get("table_usable")
            == bool(node_checks[node_id]["usable"])
            for node_id in NODE_ORDER
        ),
        "summary_table_hashes": all(
            summaries.get(node_id, {}).get("table_sha256")
            == sha256_file(run / f"node-{node_id:04d}.npz")
            for node_id in NODE_ORDER
        ),
    }
    return {
        "passed": all(checks.values()),
        "kind": "deterministic shared mapping of four root node tables",
        "checks": checks,
        "summary_sha256": summary_hashes,
        "abstain_nodes": [
            node_id for node_id in NODE_ORDER if not bool(node_checks[node_id]["usable"])
        ],
    }


def replay_generators(run: Path, context: AuditContext) -> dict[str, Any]:
    """Same-generator determinism replay, explicitly not an independent DGP proof."""
    from latent_landscapes import preinvasion_campaign as campaign

    fixed, setup = campaign.public_inputs()
    results = []
    for node_id in NODE_ORDER:
        truth_values = NODE_TRUTHS[node_id]
        for reference in REPLAY_REFERENCES:
            row_path, array_path = _history_paths(run, node_id, reference)
            row = read_json(row_path)
            stored = _load_history(array_path)
            seeds = {
                "root": ROOT_SEED,
                "namespace": SEED_NAMESPACE,
                "coarse_node": node_id,
                "reference": reference,
                "streams": expected_streams(node_id, reference, root=ROOT_SEED),
            }
            truth = campaign.OpenTruth(
                reference,
                truth_values["h"],
                truth_values["mu"],
                truth_values["beta"],
                truth_values["detection_sd"],
            )
            raw, evaluator = campaign.generate_open_history(fixed, setup, truth, seeds)
            comparisons = {
                "prey_counts": np.array_equal(raw["prey_counts"], stored["prey_counts"]),
                "predator_counts": np.array_equal(
                    raw["predator_counts"], stored["predator_counts"]
                ),
                "arrival": np.array_equal(evaluator["arrival"], stored["arrival"]),
                "loss": np.array_equal(evaluator["loss"], stored["loss"]),
                "site_hazard": np.array_equal(
                    evaluator["site_hazard"], stored["site_hazard"]
                ),
                "site_detection": np.array_equal(
                    evaluator["site_detection"], stored["site_detection"]
                ),
                "prey_alive": np.array_equal(evaluator["prey_alive"], stored["prey_alive"]),
                "opaque_id": row.get("observations", {}).get("opaque_id") == raw["opaque_id"],
            }
            results.append(
                {
                    "node_id": node_id,
                    "reference": reference,
                    "passed": all(comparisons.values()),
                    "comparisons": comparisons,
                }
            )
    return {
        "passed": all(item["passed"] for item in results),
        "kind": "same-generator bitwise determinism replay; not independent spread validation",
        "count": len(results),
        "rows": results,
        "context_site_ids": len(context.site_ids),
    }


def run_audit(
    *,
    run: Path,
    bank_path: Path,
    qualification: Path,
    registration: Path,
    source_freeze: Path,
    freeze: Path,
    output: Path,
    workers: int,
    generator_replays: bool,
    root: int = ROOT_SEED,
    references: int = REFERENCE_COUNT,
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError("preserve an earlier independent audit")
    if not 1 <= workers <= 4:
        raise ValueError("independent audit uses one to four workers")
    if references < 1:
        raise ValueError("references must be positive")
    if generator_replays and (root != ROOT_SEED or references != REFERENCE_COUNT):
        raise ValueError("generator replays are limited to the completed registered campaign")
    output.mkdir(parents=True)
    started = time.perf_counter()
    provenance: dict[str, Any] = {"passed": False, "not_checked": True}
    ledger: dict[str, Any] = {"passed": False, "not_checked": True}
    try:
        manifest = read_json(run / "manifest.json")
        provenance = verify_provenance(
            run,
            manifest,
            registration=registration,
            source_freeze=source_freeze,
            freeze=freeze,
            qualification=qualification,
            root=root,
            references=references,
        )
        context_path = run / "context.npz"
        context = load_context(context_path)
        qualification_payload = read_json(qualification)
        bank_receipt = qualification_payload.get("bank_receipt")
        if not isinstance(bank_receipt, Mapping):
            raise ValueError("qualification has no bank receipt")
        expected_bank_hash = bank_receipt.get("bank_file_sha256")
        if not isinstance(expected_bank_hash, str):
            raise ValueError("qualification has no bank file hash")
        ledger = validate_ledger(
            freeze / "seed_ledger.npz", root=root, references=references
        )
        run_ledger = validate_ledger(
            run / "seed_ledger.npz", root=root, references=references
        )
        ledger["run_copy_passed"] = bool(
            run_ledger["passed"]
            and run_ledger["sha256"] == ledger["sha256"]
            and manifest.get("ledger_sha256") == ledger["sha256"]
        )
        ledger["passed"] = bool(ledger["passed"] and ledger["run_copy_passed"])
    except (OSError, KeyError, TypeError, ValueError) as exc:
        summary = {
            "schema_version": "goal058-independent-audit-v1",
            "passed": False,
            "campaign_safety_failure": True,
            "fatal_reason": f"predispatch {type(exc).__name__}: {exc}",
            "rows_expected": 4 * references,
            "rows_audited": 0,
            "ledger": ledger,
            "provenance": provenance,
            "elapsed_seconds": time.perf_counter() - started,
            "workers": workers,
            "root": root,
            "references_per_node": references,
        }
        write_json(output / "independent-audit.json", summary)
        return summary

    if not provenance["passed"] or not ledger["passed"]:
        summary = {
            "schema_version": "goal058-independent-audit-v1",
            "passed": False,
            "campaign_safety_failure": True,
            "fatal_reason": "predispatch provenance or address validation failed",
            "rows_expected": 4 * references,
            "rows_audited": 0,
            "ledger": ledger,
            "provenance": provenance,
            "elapsed_seconds": time.perf_counter() - started,
            "workers": workers,
            "root": root,
            "references_per_node": references,
        }
        write_json(output / "independent-audit.json", summary)
        return summary

    tasks = [
        (str(run), node_id, reference)
        for node_id in NODE_ORDER
        for reference in range(references)
    ]
    rows_by_key: dict[tuple[int, int], dict[str, Any]] = {}
    details_path = output / "independent-audit-rows.jsonl"
    task_iterator = iter(tasks)
    fatal_reason: str | None = None
    executor = ProcessPoolExecutor(
        max_workers=workers,
        initializer=_initialize_worker,
        initargs=(str(bank_path), expected_bank_hash, str(context_path), root),
    )
    pending: dict[Any, tuple[int, int]] = {}

    def submit_one() -> bool:
        try:
            task = next(task_iterator)
        except StopIteration:
            return False
        pending[executor.submit(_audit_path, task)] = (task[1], task[2])
        return True

    for _ in range(workers):
        submit_one()
    try:
        with details_path.open("x", encoding="utf-8") as handle:
            while pending and fatal_reason is None:
                completed, _ = wait(tuple(pending), return_when=FIRST_COMPLETED)
                for future in completed:
                    key = pending.pop(future)
                    try:
                        row = future.result()
                    except Exception as exc:  # worker failure is a campaign safety stop
                        row = {
                            "node_id": key[0],
                            "reference": key[1],
                            "audit_consistent": False,
                            "audit_valid": False,
                            "score_mismatch": False,
                            "kernel_failure": True,
                            "points": {},
                            "statistic": None,
                            "latent_check": None,
                            "worker_error": f"{type(exc).__name__}: {exc}",
                        }
                    rows_by_key[key] = row
                    handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                    handle.flush()
                    if not bool(row.get("audit_consistent")):
                        fatal_reason = (
                            f"row safety failure at node {key[0]} reference {key[1]}"
                        )
                        break
                if fatal_reason is None:
                    while len(pending) < workers and submit_one():
                        pass
                if len(rows_by_key) % 50 == 0 and rows_by_key:
                    print(
                        json.dumps({"audited": len(rows_by_key), "total": len(tasks)}),
                        flush=True,
                    )
    finally:
        for future in pending:
            future.cancel()
        executor.shutdown(wait=True, cancel_futures=True)

    ordered = [rows_by_key[key] for key in sorted(rows_by_key)]
    complete = len(rows_by_key) == len(tasks) and fatal_reason is None

    node_checks: dict[int, dict[str, Any]] = {}
    if complete:
        for node_id in NODE_ORDER:
            node_rows = [rows_by_key[(node_id, ref)] for ref in range(references)]
            table = validate_node_table(run, node_id, node_rows, references=references)
            node_checks[node_id] = {
                "node_id": node_id,
                "rows": len(node_rows),
                "valid": sum(bool(row["audit_valid"]) for row in node_rows),
                "invalid": sum(not bool(row["audit_valid"]) for row in node_rows),
                "score_mismatches": sum(bool(row["score_mismatch"]) for row in node_rows),
                "kernel_failures": sum(bool(row["kernel_failure"]) for row in node_rows),
                "usable": all(bool(row["audit_valid"]) for row in node_rows),
                "table": table,
            }
        shared = validate_shared_table(run, node_checks, references=references)
    else:
        shared = {"passed": False, "not_checked": "audit stopped before all rows"}
    replay = replay_generators(run, context) if generator_replays and complete else {
        "performed": False,
        "reason": "generator replays require a complete registered audit and explicit flag",
    }
    maxima = {
        "score_absolute_difference": max(
            (
                float(point["absolute_difference"])
                for row in ordered
                for point in row.get("points", {}).values()
                if point["absolute_difference"] is not None
            ),
            default=None,
        ),
        "statistic_absolute_difference": max(
            (
                float(row["statistic"]["absolute_difference"])
                for row in ordered
                if row.get("statistic")
                and row["statistic"]["absolute_difference"] is not None
            ),
            default=None,
        ),
        "hazard_absolute_difference": max(
            (
                float(row["latent_check"]["max_hazard_absdiff"])
                for row in ordered
                if row.get("latent_check")
                and row["latent_check"]["max_hazard_absdiff"] is not None
            ),
            default=None,
        ),
    }
    all_rows_consistent = complete and all(bool(row["audit_consistent"]) for row in ordered)
    campaign_safety_failure = any(
        bool(row.get("score_mismatch") or row.get("kernel_failure")) for row in ordered
    ) or fatal_reason is not None or not provenance["passed"] or not ledger["passed"]
    passed = bool(
        complete
        and all_rows_consistent
        and not campaign_safety_failure
        and all(check["table"]["passed"] for check in node_checks.values())
        and shared["passed"]
        and (not generator_replays or replay.get("passed") is True)
    )
    summary = {
        "schema_version": "goal058-independent-audit-v1",
        "passed": passed,
        "campaign_safety_failure": campaign_safety_failure,
        "all_rows_audit_consistent": all_rows_consistent,
        "fatal_reason": fatal_reason,
        "all_node_tables_usable": bool(node_checks)
        and all(check["usable"] for check in node_checks.values()),
        "rows_expected": len(tasks),
        "rows_audited": len(ordered),
        "score_tolerance": SCORE_TOLERANCE,
        "statistic_tolerance": STATISTIC_TOLERANCE,
        "maxima": maxima,
        "nodes": [
            node_checks[node_id]
            for node_id in NODE_ORDER
            if node_id in node_checks
        ],
        "ledger": ledger,
        "provenance": provenance,
        "shared_table": shared,
        "generator_replay": replay,
        "elapsed_seconds": time.perf_counter() - started,
        "workers": workers,
        "root": root,
        "references_per_node": references,
        "outputs": {"rows": details_path.name},
    }
    write_json(output / "independent-audit.json", summary)
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--bank-path", type=Path, required=True)
    parser.add_argument("--qualification", type=Path, required=True)
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--source-freeze", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--root", type=int, default=ROOT_SEED)
    parser.add_argument("--references", type=int, default=REFERENCE_COUNT)
    parser.add_argument("--replay-generators", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    result = run_audit(
        run=args.run,
        bank_path=args.bank_path,
        qualification=args.qualification,
        registration=args.registration,
        source_freeze=args.source_freeze,
        freeze=args.freeze,
        output=args.output,
        workers=args.workers,
        generator_replays=args.replay_generators,
        root=args.root,
        references=args.references,
    )
    print(json.dumps({"passed": result["passed"], "output": str(args.output)}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
