#!/usr/bin/env python3
"""Independent numerical audit helpers for blinded capstone training.

The helpers read only analyst-facing training observations and open null
references.  They do not import the production likelihood, fitter, calibration
module, training adapter, or reference writer.  Direct scores use the empirical
bank reconstruction from the frozen public auditor; screening uses the separate
analytic pre-only likelihood.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from audit_capstone_public import (
    AuditContext,
    audit_arrival_bank,
    confirmatory_seed,
    direct_training_score,
    effect_decision,
    inclusive_rank,
    make_direct_bank,
    nuisance_grid,
    nuisance_neighbors,
    reconstruct_public_inputs,
    sha256_file,
    subset_direct_bank,
)
from audit_preinvasion_effect_reference import (
    AuditContext as EffectAuditContext,
)
from audit_preinvasion_effect_reference import (
    independent_training_score,
    validate_latents,
)
from audit_preinvasion_feasibility import (
    DirectBank,
    direct_survival_moments,
    normalized_hazards,
)
from numpy.typing import NDArray

from latent_landscapes.goal006.spread import (
    compute_contrast_spread,
    sample_edge_shock_vector,
)
from latent_landscapes.preinvasion_independent import independent_pre_log_likelihood

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

SCHEMA = "goal061-independent-training-audit-v1"
REFERENCE_SCHEMA = "goal061-capstone-reference-v1"
REGISTERED_ROOT = 2026100404
MECHANICAL_ROOT = 987654321
REGISTERED_TRAINING_SHA256 = "a884068ab5a2be36e21ba8c2688a5eff620ea436e60078ea200584eaa614b220"
TRAINING_SCHEMA = "goal060-training-v1"
NAMESPACE = 59
SCREEN_DOMAIN = 5
EFFECT_DOMAIN = 6
SCREEN_STAGES = {"prey_loss": 2, "site_detection": 4, "prey_visits": 5}
EFFECT_STAGES = {
    "spread": 1,
    "prey_loss": 2,
    "predator_visits": 3,
    "site_detection": 4,
    "prey_visits": 5,
}
MODEL_NAMES = (
    "constant_free_h",
    "adjusted_free_h",
    "constant_h1",
    "adjusted_h1",
)
PROFILE_SPECS = {
    "constant_h": ("h", np.linspace(1.0, 10.0, 181), "constant_free_h"),
    "adjusted_h": ("h", np.linspace(1.0, 10.0, 181), "adjusted_free_h"),
    "adjusted_beta": ("beta", np.linspace(-2.0, 2.0, 81), "adjusted_free_h"),
}
COARSE_H = (1.0, 1.5, 3.0, 6.0, 10.0)
COARSE_BETA = (-2.0, -1.0, 0.0, 0.6, 1.0, 2.0)
COARSE_MU = (0.0005, 0.001, 0.0016, 0.002, 0.0025, 0.0032, 0.004, 0.005, 0.006)
COARSE_SD = (0.0, 0.1, 0.2, 0.3, 0.4)
PREY_TIMES = tuple(float(value) for value in np.arange(-60.0, 61.0, 10.0))
PREDATOR_TIMES = tuple(float(value) for value in np.arange(10.0, 61.0, 10.0))
SCORE_TOLERANCE = 1e-8
STATISTIC_TOLERANCE = 1e-6


class AuditStopError(ValueError):
    """A source, schema, identity, hash, or independent-score mismatch."""


@dataclass(frozen=True)
class AuditResources:
    fixed: Any
    setup: Any
    context: AuditContext
    bank: DirectBank
    provenance: Mapping[str, Any]


@dataclass(frozen=True)
class PreOnlyData:
    site_ids: tuple[str, ...]
    prey_counts: IntArray
    training_mask: NDArray[np.bool_]
    initial_alive: NDArray[np.bool_]
    prey_times: tuple[float, ...] = PREY_TIMES
    cohort_start: float = -60.0


def _finite(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(dict(value), sort_keys=True, allow_nan=False)


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _array_binding(value: Any) -> dict[str, Any]:
    """Return a compact, exact binding for a numerical array."""
    array = np.ascontiguousarray(np.asarray(value))
    return {
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "sha256": _hash_bytes(array.tobytes(order="C")),
    }


def _jsonable(value: Any) -> Any:
    """Canonicalize audit inputs without materialising large arrays in JSON."""
    if isinstance(value, Mapping):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, np.ndarray):
        return {"__array_binding__": _array_binding(value)}
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return {"__nonfinite_float__": repr(value)}
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(f"unsupported audit-binding value: {type(value).__name__}")


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        _jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return _hash_bytes(encoded)


def _expected_streams(
    domain: int,
    node: int,
    reference: int,
    stages: Mapping[str, int],
    *,
    root: int,
) -> dict[str, int]:
    return {
        name: confirmatory_seed(domain, node, reference, stage, root=root)
        for name, stage in stages.items()
    }


def _validate_request(kind: str, node: int, root: int, references: int) -> None:
    expected = 99 if kind == "screen" else 999
    if not 0 <= node < 765:
        raise ValueError("node must be in [0,764]")
    if root not in (REGISTERED_ROOT, MECHANICAL_ROOT):
        raise ValueError("only the registered or mechanical root is permitted")
    if not 1 <= references <= expected:
        raise ValueError("reference count is outside the frozen bound")
    if root == REGISTERED_ROOT and references != expected:
        raise ValueError("registered reference counts cannot be reduced")


def _expected_metadata(
    kind: str, binding: str, node: int, root: int, references: int
) -> dict[str, Any]:
    _validate_request(kind, node, root, references)
    return {
        "schema": REFERENCE_SCHEMA,
        "kind": kind,
        "binding_sha256": binding,
        "node": node,
        "root": root,
        "namespace": NAMESPACE,
        "domain": SCREEN_DOMAIN if kind == "screen" else EFFECT_DOMAIN,
        "references": references,
    }


def _screen_neighbors(node: int) -> tuple[int, ...]:
    """Return the frozen centre-first immediate-axis screen stencil."""
    if not 0 <= node < 765:
        raise ValueError("node must be in [0,764]")
    coordinates = [node // 45, node % 45 // 5, node % 5]
    shape = (17, 9, 5)
    result = [node]
    for axis, size in enumerate(shape):
        for step in (-1, 1):
            neighbour = coordinates.copy()
            neighbour[axis] += step
            if 0 <= neighbour[axis] < size:
                result.append((neighbour[0] * 9 + neighbour[1]) * 5 + neighbour[2])
    if set(result) != set(nuisance_neighbors(node)):
        raise AssertionError("independent screen stencil disagrees with the grid")
    return tuple(result)


@lru_cache(maxsize=2)
def _load_resources_cached(package_raw: str) -> AuditResources:
    package = Path(package_raw)
    ready_path = package / "public-ready.json"
    if not ready_path.is_file():
        raise AuditStopError("qualified public readiness receipt is missing")
    ready = json.loads(ready_path.read_text(encoding="utf-8"))
    if not isinstance(ready, dict) or ready.get("public_ready") is not True:
        raise AuditStopError("public package is not qualified")
    files = ready.get("files")
    if not isinstance(files, Mapping):
        raise AuditStopError("public readiness receipt has no file bindings")
    mismatches = [
        str(relative)
        for relative, expected in files.items()
        if not (package / str(relative)).is_file()
        or sha256_file(package / str(relative)) != expected
    ]
    if mismatches:
        raise AuditStopError(f"qualified public files changed: {mismatches}")

    fixed, setup, context, public_receipt = reconstruct_public_inputs(package / "public_inputs")
    arrivals, bank_receipt = audit_arrival_bank(
        package / "arrival_bank",
        context.site_ids,
        fixed=fixed,
        map_a=context.map_a,
    )
    bank = make_direct_bank(arrivals, context.site_ids)
    return AuditResources(
        fixed,
        setup,
        context,
        bank,
        {
            "public_ready_sha256": sha256_file(ready_path),
            "public_inputs": public_receipt,
            "arrival_bank": bank_receipt,
        },
    )


def load_audit_resources(package: Path) -> AuditResources:
    """Reconstruct and cache the independently verified public map and bank."""
    return _load_resources_cached(str(package.resolve()))


def _training_arrays(
    training_npz: Path,
    resources: AuditResources,
    *,
    training_manifest: Path | None,
    expected_npz_sha256: str,
) -> tuple[tuple[str, ...], tuple[str, ...], IntArray, IntArray]:
    if (
        len(expected_npz_sha256) != 64
        or any(character not in "0123456789abcdef" for character in expected_npz_sha256)
        or sha256_file(training_npz) != expected_npz_sha256
    ):
        raise AuditStopError("training archive differs from the expected sealed digest")
    manifest_path = training_npz.with_name("training_manifest.json")
    if training_manifest is not None:
        manifest_path = training_manifest
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AuditStopError("training manifest is missing or invalid") from error
    expected_manifest = {
        "schema_version": TRAINING_SCHEMA,
        "case_count": 4,
        "site_count": 120,
        "prey_visits": 13,
        "predator_visits": 6,
        "arrays_sha256": expected_npz_sha256,
    }
    if manifest != expected_manifest:
        raise AuditStopError("training manifest differs from the sealed package contract")
    required = {"case_ids", "site_ids", "prey_counts", "predator_counts"}
    with np.load(training_npz, allow_pickle=False) as saved:
        if set(saved.files) != required:
            raise AuditStopError("training archive contains undocumented or missing arrays")
        case_ids = tuple(str(value) for value in np.asarray(saved["case_ids"]).reshape(-1))
        site_ids = tuple(str(value) for value in np.asarray(saved["site_ids"]).reshape(-1))
        prey_raw = np.asarray(saved["prey_counts"])
        predator_raw = np.asarray(saved["predator_counts"])
    training = np.asarray(resources.context.training, dtype=bool)
    expected_sites = tuple(np.asarray(resources.context.site_ids)[training])
    if case_ids != tuple(f"case-{index:02d}" for index in range(4)):
        raise AuditStopError("training case identities are not the four neutral IDs")
    if site_ids != expected_sites:
        raise AuditStopError("training site order differs from the public design")
    if (
        prey_raw.shape != (4, 120, 13)
        or predator_raw.shape != (4, 120, 6)
        or not np.issubdtype(prey_raw.dtype, np.integer)
        or not np.issubdtype(predator_raw.dtype, np.integer)
        or not np.isin(prey_raw, (0, 1, 2)).all()
        or not np.isin(predator_raw, (0, 1, 2)).all()
    ):
        raise AuditStopError("training observations violate the frozen count schema")
    return (
        case_ids,
        site_ids,
        np.asarray(prey_raw, dtype=np.int64),
        np.asarray(predator_raw, dtype=np.int64),
    )


def _training_context(resources: AuditResources) -> tuple[DirectBank, AuditContext]:
    mask = np.asarray(resources.context.training, dtype=bool)
    bank = subset_direct_bank(resources.bank, mask)
    context = AuditContext(
        tuple(np.asarray(resources.context.site_ids)[mask]),
        np.ones(int(mask.sum()), dtype=bool),
        np.asarray(resources.context.map_a, dtype=np.float64),
        np.asarray(resources.context.site_a, dtype=np.float64)[mask],
        tuple(np.asarray(resources.context.cluster_ids)[mask]),
    )
    return bank, context


def audit_observed_screen(
    package: Path,
    training_npz: Path,
    scores: Any,
    *,
    training_manifest: Path | None = None,
    expected_npz_sha256: str = REGISTERED_TRAINING_SHA256,
) -> dict[str, Any]:
    """Reconstruct the complete observed four-case pre-only score surface."""
    resources = load_audit_resources(package)
    _case_ids, site_ids, prey, _predator = _training_arrays(
        training_npz,
        resources,
        training_manifest=training_manifest,
        expected_npz_sha256=expected_npz_sha256,
    )
    mask = np.asarray(resources.context.training, dtype=bool)
    observations = PreOnlyData(
        site_ids,
        prey,
        np.ones(len(site_ids), dtype=bool),
        np.ones(len(site_ids), dtype=bool),
    )
    grid = nuisance_grid()
    direct = np.empty((4, len(grid)), dtype=np.float64)
    for node, (beta, mu, detection_sd) in enumerate(grid):
        direct[:, node] = independent_pre_log_likelihood(
            observations,
            np.asarray(resources.context.map_a, dtype=np.float64),
            np.asarray(resources.context.site_a, dtype=np.float64)[mask],
            beta=beta,
            mu=mu,
            detection_sd=detection_sd,
        )
    try:
        stored = np.asarray(scores, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise AuditStopError("observed pre-score surface is not numeric") from error
    if stored.shape != (4, 765) or direct.shape != stored.shape:
        raise AuditStopError("observed pre-score surface has the wrong frozen shape")
    if not np.array_equal(np.isfinite(stored), np.isfinite(direct)):
        raise AuditStopError("observed pre-score finite/nonfinite pattern changed")
    if (
        not np.array_equal(np.isnan(stored), np.isnan(direct))
        or not np.array_equal(np.isposinf(stored), np.isposinf(direct))
        or not np.array_equal(np.isneginf(stored), np.isneginf(direct))
    ):
        raise AuditStopError("observed pre-score nonfinite values changed")
    finite = np.isfinite(direct)
    maximum_error = (
        float(np.max(np.abs(direct[finite] - stored[finite]))) if np.any(finite) else 0.0
    )
    if maximum_error > SCORE_TOLERANCE:
        raise AuditStopError("observed pre-score surface differs from independent scores")
    numerical_status = "valid" if bool(finite.all()) else "terminal_invalid"
    training_hash = sha256_file(training_npz)
    manifest_path = training_manifest or training_npz.with_name("training_manifest.json")
    manifest_hash = sha256_file(manifest_path)
    return {
        "schema": SCHEMA,
        "kind": "observed_screen",
        "passed": True,
        "status": "audited_complete",
        "numerical_status": numerical_status,
        "diagnostic_passed": True,
        "release_blocked": False,
        "audit_binding": {
            "public_ready_sha256": resources.provenance.get("public_ready_sha256"),
            "training_npz_sha256": training_hash,
            "training_manifest_sha256": manifest_hash,
            "observed_pre_scores": _array_binding(stored),
        },
        "training_npz_sha256": training_hash,
        "training_manifest_sha256": manifest_hash,
        "maximum_score_abs_error": maximum_error,
        "scores": direct,
        "provenance": resources.provenance,
    }


def _fit_point(value: Any) -> dict[str, float] | None:
    if not isinstance(value, Mapping):
        return None
    source: Mapping[str, Any] = value
    if isinstance(value.get("parameters"), Mapping):
        source = value["parameters"]
    parsed = {name: _finite(source.get(name)) for name in ("h", "beta", "mu", "detection_sd")}
    if any(item is None for item in parsed.values()):
        return None
    point = {name: float(item) for name, item in parsed.items() if item is not None}
    bounds = {
        "h": (1.0, 10.0),
        "beta": (-2.0, 2.0),
        "mu": (0.0005, 0.006),
        "detection_sd": (0.0, 0.4),
    }
    for name, (lower, upper) in bounds.items():
        observed = point[name]
        below_by = lower - observed
        above_by = observed - upper
        if below_by > 8.0 * math.ulp(lower) or above_by > 8.0 * math.ulp(upper):
            raise AuditStopError("stored fit point violates the frozen parameter bounds")
    return point


def _audit_stored_point(
    bank: DirectBank,
    context: AuditContext,
    prey: IntArray,
    predator: IntArray,
    point: Mapping[str, float],
    stored: Any,
    *,
    label: str,
) -> tuple[float, float]:
    stored_value = _finite(stored)
    if stored_value is None:
        raise AuditStopError(f"{label} has a finite point but no finite stored score")
    direct = direct_training_score(bank, context, prey, predator, point)
    if not math.isfinite(direct):
        raise AuditStopError(f"independent score is nonfinite at {label}")
    difference = abs(direct - stored_value)
    if difference > SCORE_TOLERANCE:
        raise AuditStopError(f"independent score mismatch at {label}: {difference:.6g}")
    return direct, difference


def _audit_profiles(
    profiles: Mapping[str, Any],
    fits: Mapping[str, Any],
    bank: DirectBank,
    context: AuditContext,
    prey: IntArray,
    predator: IntArray,
) -> dict[str, Any]:
    if set(profiles) != set(PROFILE_SPECS):
        raise AuditStopError("training profiles are incomplete")
    maximum_error = 0.0
    status_passed: dict[str, bool] = {}
    main_gaps: dict[str, float | None] = {}
    unavailable_reconstruction_gaps: dict[str, float | None] = {}
    rows = 0
    for name, (coordinate, expected_grid, model) in PROFILE_SPECS.items():
        profile = profiles[name]
        if not isinstance(profile, Mapping):
            raise AuditStopError(f"profile {name} is not a mapping")
        grid = np.asarray(profile.get("grid"), dtype=np.float64)
        values = np.asarray(profile.get("values"), dtype=np.float64)
        parameters = profile.get("parameters")
        statuses = profile.get("statuses")
        warnings = profile.get("warnings")
        unavailable = (
            grid.shape == (0,)
            and values.shape == (0,)
            and isinstance(parameters, Sequence)
            and not isinstance(parameters, (str, bytes))
            and len(parameters) == 0
            and isinstance(statuses, Sequence)
            and not isinstance(statuses, (str, bytes))
            and len(statuses) == 0
        )
        if unavailable:
            expected_curvature_coordinate = "log_h" if coordinate == "h" else "beta"
            if (
                profile.get("coordinate") != coordinate
                or profile.get("statuses_converged") is not False
                or profile.get("nfev") != 0
                or _finite(profile.get("elapsed_seconds")) != 0.0
                or profile.get("better_than_main") is not False
                or profile.get("curvature") is not None
                or profile.get("curvature_coordinate") != expected_curvature_coordinate
                or not isinstance(warnings, Sequence)
                or isinstance(warnings, (str, bytes))
                or len(warnings) != 1
                or not str(warnings[0]).startswith("diagnostic unavailable: ")
            ):
                raise AuditStopError(f"unavailable profile {name} has the wrong sentinel schema")
            status_passed[name] = False
            main_gaps[name] = None
            base = _fit_point(fits[model])
            main_score = _finite(fits[model].get("raw_logjoint"))
            if base is None:
                unavailable_reconstruction_gaps[name] = None
                continue
            reconstructed_values = []
            for value in expected_grid:
                reconstructed_point = {**base, coordinate: float(value)}
                score = direct_training_score(bank, context, prey, predator, reconstructed_point)
                if not math.isfinite(score):
                    raise AuditStopError(
                        f"independent unavailable-profile score is nonfinite at {name}"
                    )
                reconstructed_values.append(score)
            rows += len(reconstructed_values)
            unavailable_reconstruction_gaps[name] = (
                max(reconstructed_values) - main_score if main_score is not None else None
            )
            continue
        if (
            profile.get("coordinate") != coordinate
            or not np.array_equal(grid, expected_grid)
            or values.shape != expected_grid.shape
            or not isinstance(parameters, Sequence)
            or isinstance(parameters, (str, bytes))
            or len(parameters) != len(expected_grid)
            or not isinstance(statuses, Sequence)
            or isinstance(statuses, (str, bytes))
            or len(statuses) != len(expected_grid)
        ):
            raise AuditStopError(f"profile {name} has the wrong frozen schema")
        status_passed[name] = all(status == "converged" for status in statuses)
        finite_values: list[float] = []
        for index, parameter_row in enumerate(parameters):
            stored_point = _fit_point(parameter_row)
            stored = _finite(values[index])
            status = str(statuses[index])
            if stored is None:
                if status == "converged":
                    raise AuditStopError(f"converged profile point {name}[{index}] is incomplete")
                continue
            if stored_point is None:
                raise AuditStopError(
                    f"profile point {name}[{index}] has a finite score without a finite point"
                )
            if stored_point[coordinate] != float(expected_grid[index]):
                raise AuditStopError(f"profile {name} changed its fixed coordinate")
            if name == "constant_h" and stored_point["beta"] != 0.0:
                raise AuditStopError("constant-h profile changed beta")
            _direct, error = _audit_stored_point(
                bank,
                context,
                prey,
                predator,
                stored_point,
                stored,
                label=f"profile {name}[{index}]",
            )
            maximum_error = max(maximum_error, error)
            finite_values.append(stored)
            rows += 1
        main_score = _finite(fits[model].get("raw_logjoint"))
        main_gaps[name] = (
            max(finite_values) - main_score if finite_values and main_score is not None else None
        )
    return {
        "rows_audited": rows,
        "maximum_score_abs_error": maximum_error,
        "statuses_converged": status_passed,
        "main_gaps": main_gaps,
        "unavailable_reconstruction_gaps": unavailable_reconstruction_gaps,
        "diagnostic_passed": all(status_passed.values())
        and all(value is not None and value <= STATISTIC_TOLERANCE for value in main_gaps.values()),
    }


def _coarse_value(raw: Any, h_index: int) -> float:
    values = np.asarray(raw, dtype=np.float64)
    if values.shape == (1, len(COARSE_H)):
        return float(values[0, h_index])
    if values.shape == (len(COARSE_H),):
        return float(values[h_index])
    raise AuditStopError("coarse-grid stored score has the wrong single-history shape")


def _audit_coarse_grid(
    grid: Mapping[str, Any],
    fits: Mapping[str, Any],
    bank: DirectBank,
    context: AuditContext,
    prey: IntArray,
    predator: IntArray,
) -> dict[str, Any]:
    expected_grid = {
        "h": COARSE_H,
        "beta": COARSE_BETA,
        "mu": COARSE_MU,
        "detection_sd": COARSE_SD,
    }
    stored_grid = grid.get("grid")
    grid_matches = isinstance(stored_grid, Mapping) and all(
        np.array_equal(
            np.asarray(stored_grid.get(name), dtype=np.float64),
            np.asarray(values, dtype=np.float64),
        )
        for name, values in expected_grid.items()
    )
    raw_points = grid.get("raw_points")
    if (
        grid.get("points") != 1350
        or grid.get("expected_points") != 1350
        or not grid_matches
        or not isinstance(raw_points, Sequence)
        or isinstance(raw_points, (str, bytes))
        or len(raw_points) != 1350
    ):
        raise AuditStopError("coarse diagnostic grid is incomplete or changed")
    support: set[tuple[float, float, float, float]] = set()
    maxima = dict.fromkeys(MODEL_NAMES, -math.inf)
    maximum_error = 0.0
    for index, row in enumerate(raw_points):
        if not isinstance(row, Mapping) or not isinstance(row.get("point"), Mapping):
            raise AuditStopError("coarse diagnostic row is malformed")
        point = _fit_point(row["point"])
        if point is None:
            raise AuditStopError("coarse diagnostic point is nonfinite")
        key = (point["h"], point["beta"], point["mu"], point["detection_sd"])
        if key in support:
            raise AuditStopError("coarse diagnostic grid duplicates a point")
        support.add(key)
        try:
            h_index = COARSE_H.index(point["h"])
        except ValueError as error:
            raise AuditStopError("coarse diagnostic h coordinate changed") from error
        expected_models = (
            list(MODEL_NAMES) if point["beta"] == 0.0 else ["adjusted_free_h", "adjusted_h1"]
        )
        if row.get("applicable_models") != expected_models:
            raise AuditStopError("coarse diagnostic applicable-model identity changed")
        stored = _coarse_value(row.get("training_logjoint_by_history_and_h"), h_index)
        direct, score_error = _audit_stored_point(
            bank,
            context,
            prey,
            predator,
            point,
            stored,
            label=f"coarse point {index}",
        )
        maximum_error = max(maximum_error, score_error)
        for model in expected_models:
            if model.endswith("h1") and point["h"] != 1.0:
                continue
            maxima[model] = max(maxima[model], direct)
    expected_support = {
        (h, beta, mu, sd)
        for h in COARSE_H
        for beta in COARSE_BETA
        for mu in COARSE_MU
        for sd in COARSE_SD
    }
    if support != expected_support:
        raise AuditStopError("coarse diagnostic support changed")
    stored_maxima = grid.get("max_logjoint")
    if not isinstance(stored_maxima, Mapping):
        raise AuditStopError("coarse diagnostic maxima are missing")
    for model, direct_maximum in maxima.items():
        saved = np.asarray(stored_maxima.get(model), dtype=np.float64).reshape(-1)
        if (
            saved.shape != (1,)
            or not np.isfinite(saved).all()
            or abs(float(saved[0]) - direct_maximum) > SCORE_TOLERANCE
        ):
            raise AuditStopError("coarse diagnostic maximum differs from reconstruction")
    gaps: dict[str, float | None] = {}
    for model in MODEL_NAMES:
        main_score = _finite(fits[model].get("raw_logjoint"))
        gaps[model] = None if main_score is None else maxima[model] - main_score
    return {
        "performed": True,
        "points_audited": len(support),
        "maximum_score_abs_error": maximum_error,
        "main_fit_gaps": gaps,
        "diagnostic_passed": all(
            value is not None and value <= STATISTIC_TOLERANCE for value in gaps.values()
        ),
    }


def audit_training_case(
    package: Path,
    training_npz: Path,
    result: Mapping[str, Any],
    grid: Mapping[str, Any] | None,
    *,
    training_manifest: Path | None = None,
    expected_npz_sha256: str = REGISTERED_TRAINING_SHA256,
) -> dict[str, Any]:
    """Audit one stored training result without accessing holdout or case truth."""
    resources = load_audit_resources(package)
    case_ids, _site_ids, prey_all, predator_all = _training_arrays(
        training_npz,
        resources,
        training_manifest=training_manifest,
        expected_npz_sha256=expected_npz_sha256,
    )
    if "heldout_scores" in result:
        raise AuditStopError("training result contains held-out scores")
    history = result.get("history")
    if type(history) is not int or not 0 <= history < 4:
        raise AuditStopError("training result has an invalid neutral history index")
    if result.get("representation") != "full":
        raise AuditStopError("training declaration must use the full registered bank")
    if result.get("bank_size") != resources.bank.bank_size:
        raise AuditStopError("training result bank size differs from the audited bank")
    fits_raw = result.get("fits")
    profiles = result.get("profiles")
    if not isinstance(fits_raw, Mapping) or set(fits_raw) != set(MODEL_NAMES):
        raise AuditStopError("training main fits are incomplete")
    if not isinstance(profiles, Mapping):
        raise AuditStopError("training profiles are missing")
    fits: Mapping[str, Any] = fits_raw
    bank, context = _training_context(resources)
    prey = prey_all[history]
    predator = predator_all[history]

    direct_scores: dict[str, float | None] = {}
    main_errors: dict[str, float | None] = {}
    statuses: dict[str, str] = {}
    for model in MODEL_NAMES:
        fit = fits[model]
        if not isinstance(fit, Mapping) or fit.get("model") != model:
            raise AuditStopError(f"main fit identity changed for {model}")
        statuses[model] = str(fit.get("numerical_status"))
        point = _fit_point(fit)
        stored = _finite(fit.get("raw_logjoint"))
        if stored is None:
            if statuses[model] == "converged":
                raise AuditStopError(f"converged main fit {model} is incomplete")
            direct_scores[model] = None
            main_errors[model] = None
            continue
        if point is None:
            raise AuditStopError(f"main fit {model} has a finite score without a finite point")
        if model.startswith("constant") and point["beta"] != 0.0:
            raise AuditStopError(f"constant fit {model} changed beta")
        if model.endswith("h1") and point["h"] != 1.0:
            raise AuditStopError(f"null fit {model} changed h")
        direct, error = _audit_stored_point(
            bank, context, prey, predator, point, stored, label=f"main fit {model}"
        )
        direct_scores[model] = direct
        main_errors[model] = error

    null = direct_scores["adjusted_h1"]
    free = direct_scores["adjusted_free_h"]
    adjusted_valid = bool(
        null is not None
        and free is not None
        and statuses["adjusted_h1"] == "converged"
        and statuses["adjusted_free_h"] == "converged"
        and free >= null - STATISTIC_TOLERANCE
    )
    direct_t = 2.0 * max(0.0, free - null) if null is not None and free is not None else None
    stored_t = _finite(result.get("adjusted_T"))
    t_error = abs(direct_t - stored_t) if direct_t is not None and stored_t is not None else None
    if direct_t is not None and (
        stored_t is None or t_error is None or t_error > STATISTIC_TOLERANCE
    ):
        raise AuditStopError("stored adjusted statistic differs from direct scores")
    if direct_t is None and stored_t is not None:
        raise AuditStopError("stored adjusted statistic is finite for an invalid score pair")
    paired = result.get("paired")
    if not isinstance(paired, Mapping):
        raise AuditStopError("training result lacks its paired-fit record")
    paired_t = _finite(paired.get("T"))
    paired_statistics = paired.get("statistics")
    paired_fits = paired.get("fits")
    if direct_t is not None and (
        paired_t is None or abs(paired_t - direct_t) > STATISTIC_TOLERANCE
    ):
        raise AuditStopError("paired-fit statistic differs from direct scores")
    if direct_t is None and paired_t is not None:
        raise AuditStopError("paired-fit statistic is finite for an invalid score pair")
    if not isinstance(paired_statistics, Mapping):
        raise AuditStopError("paired-fit adjusted statistic is inconsistent")
    stored_paired_adjusted = _finite(paired_statistics.get("adjusted"))
    if direct_t is not None and (
        stored_paired_adjusted is None
        or abs(stored_paired_adjusted - direct_t) > STATISTIC_TOLERANCE
    ):
        raise AuditStopError("paired-fit adjusted statistic is inconsistent")
    if direct_t is None and stored_paired_adjusted is not None:
        raise AuditStopError("paired-fit adjusted statistic is finite for an invalid score pair")
    if paired_fits != fits:
        raise AuditStopError("paired-fit and top-level fit records differ")
    constant_null = direct_scores["constant_h1"]
    constant_free = direct_scores["constant_free_h"]
    direct_constant_t = (
        2.0 * max(0.0, constant_free - constant_null)
        if constant_null is not None and constant_free is not None
        else None
    )
    for label, value in (
        ("top-level constant statistic", result.get("constant_T")),
        ("paired constant statistic", paired_statistics.get("constant")),
    ):
        stored_constant = _finite(value)
        if direct_constant_t is not None and (
            stored_constant is None
            or abs(stored_constant - direct_constant_t) > STATISTIC_TOLERANCE
        ):
            raise AuditStopError(f"{label} differs from direct scores")
        if direct_constant_t is None and stored_constant is not None:
            raise AuditStopError(f"{label} is finite for an invalid score pair")
    replay_differences = result.get("main_replay_logjoint_differences")
    if not isinstance(replay_differences, Mapping):
        raise AuditStopError("training result lacks main-score replay diagnostics")
    for model, replay_error in main_errors.items():
        stored_replay = _finite(replay_differences.get(model))
        if replay_error is None:
            if stored_replay is not None:
                raise AuditStopError("main replay diagnostic is unexpectedly finite")
        elif stored_replay is None or abs(stored_replay) > SCORE_TOLERANCE:
            raise AuditStopError("main replay diagnostic exceeds the score tolerance")
    stored_validity = result.get("observed_adjusted_validity")
    if not isinstance(stored_validity, Mapping):
        raise AuditStopError("training result lacks explicit adjusted-pair validity")
    expected_validity: dict[str, Any] = {
        "valid": adjusted_valid,
        "null_finite": null is not None,
        "free_finite": free is not None,
        "null_converged": statuses["adjusted_h1"] == "converged",
        "free_converged": statuses["adjusted_free_h"] == "converged",
        "both_converged": statuses["adjusted_h1"] == "converged"
        and statuses["adjusted_free_h"] == "converged",
        "free_minus_null": free - null if free is not None and null is not None else math.nan,
        "minimum_free_minus_null": -STATISTIC_TOLERANCE,
    }
    for name, expected in expected_validity.items():
        actual = stored_validity.get(name)
        if isinstance(expected, float):
            if math.isnan(expected):
                if _finite(actual) is not None:
                    raise AuditStopError(f"adjusted validity field {name} should be nonfinite")
            else:
                parsed_actual = _finite(actual)
                if parsed_actual is None or abs(parsed_actual - expected) > SCORE_TOLERANCE:
                    raise AuditStopError(f"adjusted validity field {name} is inconsistent")
        elif actual != expected:
            raise AuditStopError(f"adjusted validity field {name} is inconsistent")

    profile_audit = _audit_profiles(profiles, fits, bank, context, prey, predator)
    stored_profile_gaps = result.get("profile_main_gaps")
    if not isinstance(stored_profile_gaps, Mapping):
        raise AuditStopError("training result lacks profile/main diagnostics")
    for name, direct_gap in profile_audit["main_gaps"].items():
        stored_gap = _finite(stored_profile_gaps.get(name))
        if direct_gap is None:
            if stored_gap is not None:
                raise AuditStopError("stored profile/main gap is unexpectedly finite")
        elif stored_gap is None or abs(stored_gap - direct_gap) > SCORE_TOLERANCE:
            raise AuditStopError("stored profile/main gap arithmetic changed")
    nesting: dict[str, float | None] = {
        "constant": (
            direct_scores["constant_h1"] - direct_scores["constant_free_h"]
            if direct_scores["constant_h1"] is not None
            and direct_scores["constant_free_h"] is not None
            else None
        ),
        "adjusted": (null - free if null is not None and free is not None else None),
    }
    stored_nesting = result.get("nesting_gaps")
    if not isinstance(stored_nesting, Mapping):
        raise AuditStopError("training result lacks nesting diagnostics")
    for name, expected in nesting.items():
        actual = _finite(stored_nesting.get(name))
        if expected is None:
            if actual is not None:
                raise AuditStopError("stored nesting diagnostic is unexpectedly finite")
        elif actual is None or abs(actual - expected) > SCORE_TOLERANCE:
            raise AuditStopError("stored nesting diagnostic arithmetic changed")
    nesting_diagnostic = all(
        value is not None and value <= STATISTIC_TOLERANCE for value in nesting.values()
    )
    if result.get("nesting_gap_diagnostic_passed") is not nesting_diagnostic:
        raise AuditStopError("stored nesting diagnostic flag is inconsistent")
    stored_statuses = result.get("main_statuses_converged")
    expected_statuses = {name: status == "converged" for name, status in statuses.items()}
    if stored_statuses != expected_statuses:
        raise AuditStopError("stored main-fit status summary is inconsistent")
    stored_profile_statuses = result.get("profile_statuses_converged")
    if stored_profile_statuses != profile_audit["statuses_converged"]:
        raise AuditStopError("stored profile status summary is inconsistent")
    coarse = (
        {"performed": False, "reason": "coarse diagnostic was not supplied"}
        if grid is None
        else _audit_coarse_grid(grid, fits, bank, context, prey, predator)
    )
    diagnostic_flags = {
        "all_main_statuses_converged": all(value == "converged" for value in statuses.values()),
        "profiles": profile_audit["diagnostic_passed"],
        "nesting": nesting_diagnostic,
        "coarse_grid": coarse.get("diagnostic_passed") if grid is not None else None,
    }
    diagnostic_passed = grid is not None and all(
        value is True for value in diagnostic_flags.values() if value is not None
    )
    audit_complete = grid is not None
    training_hash = sha256_file(training_npz)
    manifest_path = training_manifest or training_npz.with_name("training_manifest.json")
    manifest_hash = sha256_file(manifest_path)
    audit_binding = {
        "public_ready_sha256": resources.provenance.get("public_ready_sha256"),
        "training_npz_sha256": training_hash,
        "training_manifest_sha256": manifest_hash,
        "result_sha256": _canonical_hash(result),
        "grid_sha256": None if grid is None else _canonical_hash(grid),
    }
    return {
        "schema": SCHEMA,
        "kind": "training_case",
        "passed": audit_complete,
        "status": "audited_valid" if adjusted_valid else "audited_casewise_abstention",
        "numerical_status": "valid" if adjusted_valid else "terminal_invalid",
        "audit_consistent": True,
        "audit_binding": audit_binding,
        "case_id": case_ids[history],
        "history": history,
        "training_npz_sha256": training_hash,
        "training_manifest_sha256": manifest_hash,
        "main_score_abs_error": main_errors,
        "maximum_main_score_abs_error": max(
            (value for value in main_errors.values() if value is not None), default=None
        ),
        "adjusted_valid": adjusted_valid,
        "adjusted_T": direct_t,
        "adjusted_T_abs_error": t_error,
        "profiles": profile_audit,
        "nesting_gaps": nesting,
        "coarse_grid": coarse,
        "diagnostic_flags": diagnostic_flags,
        "diagnostic_passed": diagnostic_passed,
        "audit_complete": audit_complete,
        "release_blocked": not diagnostic_passed,
        "release_blocked_for_diagnosis": not diagnostic_passed,
        "diagnostics_change_declaration": False,
        "provenance": resources.provenance,
    }


def _screen_replay(
    resources: AuditResources, node: int, reference: int, *, root: int
) -> tuple[IntArray, IntArray]:
    beta, mu, detection_sd = nuisance_grid()[node]
    streams = _expected_streams(SCREEN_DOMAIN, node, reference, SCREEN_STAGES, root=root)
    hazards = normalized_hazards(beta, mu, resources.context.map_a, resources.context.site_a)
    loss = (
        -60.0
        + np.random.default_rng(streams["prey_loss"]).exponential(
            size=len(resources.context.site_ids)
        )
        / hazards
    )
    if detection_sd == 0.0:
        detection = np.full(len(resources.context.site_ids), 0.65)
    else:
        concentration = 0.65 * 0.35 / detection_sd**2 - 1.0
        detection = np.random.default_rng(streams["site_detection"]).beta(
            0.65 * concentration,
            0.35 * concentration,
            size=len(resources.context.site_ids),
        )
    visits = np.random.default_rng(streams["prey_visits"]).random(
        (len(resources.context.site_ids), 7, 2)
    )
    alive = loss[:, None] > np.arange(-60.0, 1.0, 10.0)[None, :]
    prey = np.zeros((len(resources.context.site_ids), 13), dtype=np.int64)
    prey[:, :7] = (visits < detection[:, None, None]).sum(axis=2) * alive
    predator = np.zeros((len(resources.context.site_ids), 6), dtype=np.int64)
    return prey, predator


def audit_screen_node(
    package: Path,
    directory: Path,
    node: int,
    *,
    binding: str,
    root: int = REGISTERED_ROOT,
    references: int = 99,
) -> dict[str, Any]:
    """Audit every address, draw, pre-only score, and contrast for one node."""
    expected = _expected_metadata("screen", binding, node, root, references)
    path = directory / f"node-{node:04d}.npz"
    receipt_path = directory / f"node-{node:04d}.json"
    if not path.exists() and not receipt_path.exists():
        return {
            "schema": SCHEMA,
            "kind": "screen_node",
            "passed": False,
            "node": node,
            "status": "pending_missing",
            "numerical_status": "pending",
            "diagnostic_passed": None,
            "release_blocked": True,
            "abstain": False,
            "audit_binding": {
                **expected,
                "checkpoint_sha256": None,
                "receipt_sha256": None,
            },
        }
    if path.exists() and not receipt_path.exists():
        return {
            "schema": SCHEMA,
            "kind": "screen_node",
            "passed": False,
            "node": node,
            "status": "pending_unreceipted",
            "numerical_status": "pending",
            "diagnostic_passed": None,
            "release_blocked": True,
            "abstain": False,
            "audit_binding": {
                **expected,
                "checkpoint_sha256": sha256_file(path),
                "receipt_sha256": None,
            },
        }
    if not path.exists():
        raise AuditStopError("screen receipt exists without its array checkpoint")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AuditStopError("screen receipt is unreadable") from error
    if not isinstance(receipt, Mapping) or any(
        receipt.get(name) != value for name, value in expected.items()
    ):
        raise AuditStopError("screen receipt binding differs from the frozen request")
    if receipt.get("sha256") != sha256_file(path):
        raise AuditStopError("screen checkpoint hash mismatch")
    try:
        with np.load(path, allow_pickle=False) as saved:
            required = {
                "prey_counts",
                "predator_counts",
                "neighbour_indices",
                "local_scores",
                "contrasts",
                "seeds",
            }
            if set(saved.files) != required:
                raise AuditStopError("screen checkpoint array schema changed")
            prey = np.asarray(saved["prey_counts"])
            predator = np.asarray(saved["predator_counts"])
            neighbours = np.asarray(saved["neighbour_indices"], dtype=np.int64)
            stored_scores = np.asarray(saved["local_scores"], dtype=np.float64)
            stored_contrasts = np.asarray(saved["contrasts"], dtype=np.float64)
            stored_seeds = np.asarray(saved["seeds"], dtype=np.uint64)
    except (OSError, ValueError) as error:
        if isinstance(error, AuditStopError):
            raise
        raise AuditStopError("screen checkpoint is unreadable") from error
    resources = load_audit_resources(package)
    expected_neighbours = np.asarray(_screen_neighbors(node), dtype=np.int64)
    expected_shapes = (
        prey.shape == (references, 160, 13)
        and predator.shape == (references, 160, 6)
        and stored_scores.shape == (references, len(expected_neighbours))
        and stored_contrasts.shape == (references,)
        and stored_seeds.shape == (references, 3)
    )
    if not expected_shapes or not np.array_equal(neighbours, expected_neighbours):
        raise AuditStopError("screen checkpoint dimensions or neighbour stencil changed")
    if (
        not np.issubdtype(prey.dtype, np.integer)
        or not np.issubdtype(predator.dtype, np.integer)
        or not np.isin(prey, (0, 1, 2)).all()
        or not np.isin(predator, (0, 1, 2)).all()
    ):
        raise AuditStopError("screen count arrays are invalid")
    expected_seeds = np.asarray(
        [
            list(
                _expected_streams(SCREEN_DOMAIN, node, reference, SCREEN_STAGES, root=root).values()
            )
            for reference in range(references)
        ],
        dtype=np.uint64,
    )
    if not np.array_equal(stored_seeds, expected_seeds):
        raise AuditStopError("screen seed addresses changed")
    replay_failures = []
    for reference in range(references):
        replay_prey, replay_predator = _screen_replay(resources, node, reference, root=root)
        if not np.array_equal(replay_prey, prey[reference]) or not np.array_equal(
            replay_predator, predator[reference]
        ):
            replay_failures.append(reference)
    if replay_failures:
        raise AuditStopError(f"screen generator replay failed at {replay_failures}")
    observations = PreOnlyData(
        resources.context.site_ids,
        np.asarray(prey, dtype=np.int64),
        np.asarray(resources.context.training, dtype=bool),
        np.ones(160, dtype=bool),
    )
    direct_scores = np.stack(
        [
            independent_pre_log_likelihood(
                observations,
                resources.context.map_a,
                resources.context.site_a,
                beta=nuisance_grid()[neighbour][0],
                mu=nuisance_grid()[neighbour][1],
                detection_sd=nuisance_grid()[neighbour][2],
            )
            for neighbour in expected_neighbours
        ],
        axis=1,
    )
    direct_contrasts = 2.0 * np.maximum(0.0, np.max(direct_scores, axis=1) - direct_scores[:, 0])
    if (
        not np.isfinite(stored_scores).all()
        or not np.isfinite(stored_contrasts).all()
        or not np.isfinite(direct_scores).all()
        or not np.isfinite(direct_contrasts).all()
    ):
        raise AuditStopError("screen score or contrast is nonfinite")
    score_error = float(np.max(np.abs(direct_scores - stored_scores)))
    contrast_error = float(np.max(np.abs(direct_contrasts - stored_contrasts)))
    if score_error > SCORE_TOLERANCE or contrast_error > SCORE_TOLERANCE:
        raise AuditStopError("screen independent score or contrast mismatch")
    return {
        "schema": SCHEMA,
        "kind": "screen_node",
        "passed": True,
        "node": node,
        "status": "audited_complete",
        "numerical_status": "valid",
        "diagnostic_passed": True,
        "release_blocked": False,
        "abstain": False,
        "audit_binding": {
            **expected,
            "checkpoint_sha256": sha256_file(path),
            "receipt_sha256": sha256_file(receipt_path),
        },
        "references": references,
        "generator_replays": references,
        "maximum_score_abs_error": score_error,
        "maximum_contrast_abs_error": contrast_error,
        "contrasts": direct_contrasts,
        "checkpoint_sha256": sha256_file(path),
        "provenance": resources.provenance,
    }


def _effect_arrays(blob: bytes) -> dict[str, NDArray[np.generic]]:
    try:
        with np.load(io.BytesIO(blob), allow_pickle=False) as saved:
            required = {
                "prey_counts",
                "predator_counts",
                "evaluator_arrival",
                "evaluator_loss",
                "evaluator_site_hazard",
                "evaluator_site_detection",
                "evaluator_prey_alive",
            }
            if set(saved.files) != required:
                raise AuditStopError("effect observation blob schema changed")
            output = {name: np.asarray(saved[name]) for name in saved.files}
    except (OSError, ValueError) as error:
        if isinstance(error, AuditStopError):
            raise
        raise AuditStopError("effect observation blob is unreadable") from error
    return {
        "prey_counts": output["prey_counts"],
        "predator_counts": output["predator_counts"],
        "arrival": output["evaluator_arrival"],
        "loss": output["evaluator_loss"],
        "site_hazard": output["evaluator_site_hazard"],
        "site_detection": output["evaluator_site_detection"],
        "prey_alive": output["evaluator_prey_alive"],
    }


def _truth(node: int) -> dict[str, float]:
    beta, mu, detection_sd = nuisance_grid()[node]
    return {"h": 1.0, "beta": beta, "mu": mu, "detection_sd": detection_sd}


def _effect_context(resources: AuditResources) -> EffectAuditContext:
    return EffectAuditContext(
        resources.context.site_ids,
        np.asarray(resources.context.training, dtype=bool),
        np.asarray(resources.context.map_a, dtype=np.float64),
        np.asarray(resources.context.site_a, dtype=np.float64),
    )


def _effect_replay(
    resources: AuditResources, node: int, reference: int, *, root: int
) -> dict[str, NDArray[Any]]:
    truth = _truth(node)
    streams = _expected_streams(EFFECT_DOMAIN, node, reference, EFFECT_STAGES, root=root)
    shocks = sample_edge_shock_vector(
        resources.fixed.landscape, np.random.default_rng(streams["spread"])
    )
    spread = compute_contrast_spread(resources.fixed.landscape, 1.0, edge_shocks=shocks, rho=1.0)
    arrival = np.asarray(
        spread.arrival[resources.setup.site_rows, resources.setup.site_cols],
        dtype=np.float64,
    )
    hazard = normalized_hazards(
        truth["beta"], truth["mu"], resources.context.map_a, resources.context.site_a
    )
    threshold = np.random.default_rng(streams["prey_loss"]).exponential(size=160)
    loss = np.empty(160, dtype=np.float64)
    for index, (arrival_value, hazard_value, threshold_value) in enumerate(
        zip(arrival, hazard, threshold, strict=True)
    ):
        predator_arrival = float(arrival_value) + 60.0
        before = float(hazard_value) * predator_arrival
        if threshold_value <= before:
            calendar = float(threshold_value) / float(hazard_value)
        else:
            calendar = predator_arrival + (float(threshold_value) - before) / (
                float(hazard_value) * truth["h"]
            )
        loss[index] = calendar - 60.0
    if truth["detection_sd"] == 0.0:
        detection = np.full(160, 0.65)
    else:
        concentration = 0.65 * 0.35 / truth["detection_sd"] ** 2 - 1.0
        detection = np.random.default_rng(streams["site_detection"]).beta(
            0.65 * concentration, 0.35 * concentration, size=160
        )
    predator_alive = arrival[:, None] <= np.asarray(PREDATOR_TIMES)[None, :]
    prey_alive = loss[:, None] > np.asarray(PREY_TIMES)[None, :]
    predator = (
        (np.random.default_rng(streams["predator_visits"]).random((160, 6, 2)) < 0.65).sum(axis=2)
        * predator_alive
    ).astype(np.int64)
    prey = (
        (
            np.random.default_rng(streams["prey_visits"]).random((160, 13, 2))
            < detection[:, None, None]
        ).sum(axis=2)
        * prey_alive
    ).astype(np.int64)
    return {
        "prey_counts": prey,
        "predator_counts": predator,
        "arrival": arrival,
        "loss": loss,
        "site_hazard": hazard,
        "site_detection": detection,
        "prey_alive": prey_alive,
    }


def _audit_effect_row(
    payload: Mapping[str, Any],
    arrays: Mapping[str, NDArray[np.generic]],
    resources: AuditResources,
    *,
    node: int,
    reference: int,
    root: int,
    true_moments: FloatArray,
) -> dict[str, Any]:
    truth = _truth(node)
    if payload.get("node") != node or payload.get("reference") != reference:
        raise AuditStopError("effect payload identity changed")
    if payload.get("truth") != truth:
        raise AuditStopError("effect payload known-null truth changed")
    seeds = payload.get("seeds")
    expected_streams = _expected_streams(EFFECT_DOMAIN, node, reference, EFFECT_STAGES, root=root)
    if not isinstance(seeds, Mapping) or seeds != {
        "root": root,
        "namespace": NAMESPACE,
        "domain": EFFECT_DOMAIN,
        "node": node,
        "reference": reference,
        "streams": expected_streams,
    }:
        raise AuditStopError("effect payload seed address changed")
    latent = validate_latents(arrays, truth, _effect_context(resources))
    if not latent["passed"]:
        raise AuditStopError("effect latent arrays fail independent validation")
    prey = np.asarray(arrays["prey_counts"], dtype=np.int64)
    predator = np.asarray(arrays["predator_counts"], dtype=np.int64)
    truth_score, _ = independent_training_score(
        resources.bank,
        _effect_context(resources),
        prey,
        predator,
        truth,
        moments=true_moments,
    )
    if not math.isfinite(truth_score):
        raise AuditStopError("effect independent truth score is nonfinite")
    statistics = payload.get("statistics")
    if not isinstance(statistics, Mapping):
        raise AuditStopError("effect payload lacks statistics")
    stored_truth = _finite(statistics.get("truth_logjoint"))
    if stored_truth is None or abs(truth_score - stored_truth) > SCORE_TOLERANCE:
        raise AuditStopError("effect truth score mismatch")

    scores: dict[str, float | None] = {}
    statuses: dict[str, str] = {}
    errors: dict[str, float | None] = {}
    for name, model in (("null", "adjusted_h1"), ("free", "adjusted_free_h")):
        fit = payload.get(f"{name}_fit")
        if not isinstance(fit, Mapping) or fit.get("model") != model:
            raise AuditStopError(f"effect {name} fit identity changed")
        statuses[name] = str(fit.get("numerical_status"))
        point = _fit_point(fit)
        stored = _finite(fit.get("raw_logjoint"))
        if stored is None:
            if statuses[name] == "converged":
                raise AuditStopError(f"converged effect {name} fit is incomplete")
            scores[name] = None
            errors[name] = None
            continue
        if point is None:
            raise AuditStopError(f"effect {name} fit has a finite score without a finite point")
        if name == "null" and point["h"] != 1.0:
            raise AuditStopError("effect null fit changed h")
        direct, _moments = independent_training_score(
            resources.bank,
            _effect_context(resources),
            prey,
            predator,
            point,
        )
        if not math.isfinite(direct):
            raise AuditStopError(f"effect independent {name} score is nonfinite")
        difference = abs(direct - stored)
        if difference > SCORE_TOLERANCE:
            raise AuditStopError(f"effect {name} score mismatch")
        scores[name] = direct
        errors[name] = difference

    finite_fits = scores["null"] is not None and scores["free"] is not None
    delta = (
        scores["free"] - scores["null"]
        if scores["free"] is not None and scores["null"] is not None
        else None
    )
    null_minus_truth = scores["null"] - truth_score if scores["null"] is not None else None
    direct_t = 2.0 * max(0.0, delta) if delta is not None else None
    expected_valid = bool(
        finite_fits
        and statuses["null"] == "converged"
        and statuses["free"] == "converged"
        and delta is not None
        and delta >= -STATISTIC_TOLERANCE
        and null_minus_truth is not None
        and null_minus_truth >= -STATISTIC_TOLERANCE
    )
    boolean_checks = {
        "null_converged": statuses["null"] == "converged",
        "free_converged": statuses["free"] == "converged",
        "finite_fits": finite_fits,
        "free_ge_null": delta is not None and delta >= -STATISTIC_TOLERANCE,
        "null_ge_truth": null_minus_truth is not None and null_minus_truth >= -STATISTIC_TOLERANCE,
        "valid": expected_valid,
    }
    for name, expected in boolean_checks.items():
        if statistics.get(name) is not expected:
            raise AuditStopError(f"effect statistic flag {name} is inconsistent")
    numeric_checks: dict[str, float | None] = {
        "T": direct_t,
        "raw_T": 2.0 * delta if delta is not None else None,
        "free_minus_null": delta,
        "null_minus_truth": null_minus_truth,
    }
    for name, expected_score in numeric_checks.items():
        stored = _finite(statistics.get(name))
        if expected_score is None:
            if stored is not None:
                raise AuditStopError(f"effect statistic {name} should be nonfinite")
        elif stored is None or abs(stored - expected_score) > STATISTIC_TOLERANCE:
            raise AuditStopError(f"effect statistic {name} is inconsistent")
    return {
        "reference": reference,
        "audit_valid": expected_valid,
        "T": direct_t,
        "score_abs_error": {"truth": abs(truth_score - stored_truth), **errors},
        "latent": latent,
    }


def _replay_indices(references: int) -> set[int]:
    if references == 999:
        return {0, 499, 998}
    return {0, (references - 1) // 2, references - 1}


def audit_effect_node(
    package: Path,
    directory: Path,
    node: int,
    *,
    binding: str,
    root: int = REGISTERED_ROOT,
    references: int = 999,
) -> dict[str, Any]:
    """Audit all stored effect scores and selected deterministic generator replays."""
    expected = _expected_metadata("effect", binding, node, root, references)
    path = directory / f"node-{node:04d}.sqlite"
    receipt_path = directory / f"node-{node:04d}-complete.json"
    if not path.exists():
        if receipt_path.exists():
            raise AuditStopError("effect completion receipt exists without its database")
        return {
            "schema": SCHEMA,
            "kind": "effect_node",
            "passed": False,
            "node": node,
            "status": "pending_missing",
            "numerical_status": "pending",
            "diagnostic_passed": None,
            "release_blocked": True,
            "abstain": False,
            "audit_binding": {
                **expected,
                "database_sha256": None,
                "completion_receipt_sha256": None,
            },
        }
    resources = load_audit_resources(package)
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error as error:
        raise AuditStopError("effect database cannot be opened read-only") from error
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if integrity != ("ok",):
            raise AuditStopError("effect database integrity check failed")
        metadata_schema = [
            tuple(row[1:6]) for row in connection.execute("PRAGMA table_info(metadata)")
        ]
        result_schema = [
            tuple(row[1:6]) for row in connection.execute("PRAGMA table_info(results)")
        ]
        if metadata_schema != [
            ("id", "INTEGER", 0, None, 1),
            ("value", "TEXT", 0, None, 0),
        ]:
            raise AuditStopError("effect metadata table schema changed")
        if result_schema != [
            ("reference", "INTEGER", 0, None, 1),
            ("observations", "BLOB", 1, None, 0),
            ("observations_sha256", "TEXT", 1, None, 0),
            ("payload", "TEXT", 1, None, 0),
            ("payload_sha256", "TEXT", 1, None, 0),
            ("complete", "INTEGER", 1, None, 0),
        ]:
            raise AuditStopError("effect results table schema changed")
        metadata_rows = connection.execute("SELECT id,value FROM metadata ORDER BY id").fetchall()
        if metadata_rows != [(1, _canonical_json(expected))]:
            raise AuditStopError("effect database binding differs from the frozen request")
        rows = connection.execute(
            "SELECT reference,observations,observations_sha256,payload,"
            "payload_sha256,complete FROM results ORDER BY reference"
        ).fetchall()
    except sqlite3.Error as error:
        raise AuditStopError("effect database schema is unreadable") from error
    finally:
        connection.close()

    references_seen = [int(row[0]) for row in rows]
    if len(references_seen) != len(set(references_seen)):
        raise AuditStopError("effect database contains duplicate reference identities")
    if any(reference < 0 or reference >= references for reference in references_seen):
        raise AuditStopError("effect database contains an out-of-range reference")
    CompleteRow = tuple[bytes, Mapping[str, Any], Mapping[str, NDArray[np.generic]]]
    complete_rows: dict[int, CompleteRow] = {}
    pending = set(range(references)).difference(references_seen)
    for reference, blob, blob_hash, payload_raw, payload_hash, complete in rows:
        if complete not in (0, 1):
            raise AuditStopError("effect completion flag is outside {0,1}")
        blob_bytes = bytes(blob)
        if _hash_bytes(blob_bytes) != blob_hash:
            raise AuditStopError("effect observation checkpoint hash mismatch")
        if _hash_bytes(str(payload_raw).encode()) != payload_hash:
            raise AuditStopError("effect payload checkpoint hash mismatch")
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError as error:
            raise AuditStopError("effect payload is not valid JSON") from error
        if not isinstance(payload, Mapping):
            raise AuditStopError("effect payload is not a mapping")
        row_arrays = _effect_arrays(blob_bytes)
        if complete == 0:
            pending.add(int(reference))
        else:
            complete_rows[int(reference)] = (blob_bytes, payload, row_arrays)

    truth = _truth(node)
    effect_context = _effect_context(resources)
    hazards = normalized_hazards(
        truth["beta"], truth["mu"], effect_context.map_a, effect_context.site_a
    )
    true_moments = direct_survival_moments(resources.bank, hazards, truth["h"])
    audited: dict[int, dict[str, Any]] = {}
    for reference in sorted(complete_rows):
        _blob, payload, stored_arrays = complete_rows[reference]
        audited[reference] = _audit_effect_row(
            payload,
            stored_arrays,
            resources,
            node=node,
            reference=reference,
            root=root,
            true_moments=true_moments,
        )

    anomalous = {reference for reference, row in audited.items() if not bool(row["audit_valid"])}
    replay_targets = (_replay_indices(references) | anomalous).intersection(complete_rows)
    replay_failures = []
    for reference in sorted(replay_targets):
        expected_arrays = _effect_replay(resources, node, reference, root=root)
        stored_arrays = complete_rows[reference][2]
        comparisons = {
            name: np.array_equal(expected_arrays[name], stored_arrays[name])
            for name in expected_arrays
        }
        if not all(comparisons.values()):
            replay_failures.append(reference)
    if replay_failures:
        raise AuditStopError(f"effect deterministic generator replay failed at {replay_failures}")

    receipt = None
    if receipt_path.exists():
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise AuditStopError("effect completion receipt is unreadable") from error
        if not isinstance(receipt, Mapping) or any(
            receipt.get(name) != value for name, value in expected.items()
        ):
            raise AuditStopError("effect completion receipt binding changed")
        if receipt.get("database_sha256") != sha256_file(path):
            raise AuditStopError("effect database changed after completion receipt")
        if receipt.get("completed") != references:
            raise AuditStopError("effect completion receipt has the wrong row count")

    if pending:
        if receipt is not None:
            raise AuditStopError("effect completion receipt conflicts with pending rows")
        return {
            "schema": SCHEMA,
            "kind": "effect_node",
            "passed": False,
            "node": node,
            "status": "pending",
            "numerical_status": "pending",
            "diagnostic_passed": None,
            "release_blocked": True,
            "abstain": False,
            "audit_binding": {
                **expected,
                "database_sha256": sha256_file(path),
                "completion_receipt_sha256": None,
            },
            "completed": len(audited),
            "pending": len(pending),
            "terminal_invalid": len(anomalous),
            "generator_replays": len(replay_targets),
        }
    if receipt is None:
        return {
            "schema": SCHEMA,
            "kind": "effect_node",
            "passed": False,
            "node": node,
            "status": "pending_unreceipted",
            "numerical_status": "pending",
            "diagnostic_passed": None,
            "release_blocked": True,
            "abstain": False,
            "audit_binding": {
                **expected,
                "database_sha256": sha256_file(path),
                "completion_receipt_sha256": None,
            },
            "completed": len(audited),
            "pending": 0,
            "terminal_invalid": len(anomalous),
            "generator_replays": len(replay_targets),
        }
    if receipt.get("invalid") != len(anomalous):
        raise AuditStopError("effect completion receipt invalid-count is inconsistent")
    usable = not anomalous
    values = (
        np.asarray([audited[reference]["T"] for reference in range(references)], dtype=np.float64)
        if usable
        else np.full(references, np.nan, dtype=np.float64)
    )
    maximum_score_error = max(
        (
            float(error)
            for row in audited.values()
            for error in row["score_abs_error"].values()
            if error is not None
        ),
        default=None,
    )
    return {
        "schema": SCHEMA,
        "kind": "effect_node",
        "passed": True,
        "node": node,
        "status": "audited_complete" if usable else "terminal_invalid",
        "numerical_status": "valid" if usable else "terminal_invalid",
        "diagnostic_passed": True,
        "release_blocked": False,
        "abstain": not usable,
        "audit_binding": {
            **expected,
            "database_sha256": sha256_file(path),
            "completion_receipt_sha256": sha256_file(receipt_path),
        },
        "table_usable": usable,
        "completed": len(audited),
        "pending": 0,
        "terminal_invalid": len(anomalous),
        "invalid_references": sorted(anomalous),
        "generator_replays": len(replay_targets),
        "maximum_score_abs_error": maximum_score_error,
        "statistics": values,
        "database_sha256": sha256_file(path),
        "provenance": resources.provenance,
    }


def _validate_stored_rank(
    stored: Mapping[str, Any] | None,
    reconstructed: Mapping[str, Any],
    q_values: FloatArray,
) -> None:
    """Require a complete stored rank-chain record when one is supplied."""
    if stored is None:
        return
    required = {"q_values", "candidate_indices", "union", "decisions"}
    if set(stored) != required:
        raise AuditStopError("stored screen/rank/decision chain has the wrong exact schema")
    if any(
        stored[name] != reconstructed[name] for name in ("candidate_indices", "union", "decisions")
    ):
        raise AuditStopError("stored screen/rank/decision chain differs from reconstruction")
    try:
        stored_q = np.asarray(stored["q_values"], dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise AuditStopError("stored screening q-values are not numeric") from error
    if (
        stored_q.shape != q_values.shape
        or not np.array_equal(np.isfinite(stored_q), np.isfinite(q_values))
        or not np.allclose(stored_q, q_values, rtol=0.0, atol=1e-12, equal_nan=True)
    ):
        raise AuditStopError("stored screening q-values differ from reconstruction")


def audit_rank_chain(
    observed_pre_scores: Any,
    screen_reference_contrasts: Any,
    observed_effect_statistics: Any,
    effect_reference_statistics: Mapping[int, Sequence[float]],
    *,
    stored: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Independently reconstruct all four screens, ranks, and casewise decisions.

    Invalid observed or reference fits must be represented by nonfinite effect
    statistics.  A missing node table is pending; a present nonfinite table is
    a terminal casewise abstention.
    """
    observed = np.asarray(observed_pre_scores, dtype=np.float64)
    screen = np.asarray(screen_reference_contrasts, dtype=np.float64)
    observed_t = np.asarray(observed_effect_statistics, dtype=np.float64)
    audit_binding = {
        "observed_pre_scores": _array_binding(observed),
        "screen_reference_contrasts": _array_binding(screen),
        "observed_effect_statistics": _array_binding(observed_t),
        "effect_reference_statistics": {
            str(node): _array_binding(values)
            for node, values in sorted(effect_reference_statistics.items())
        },
        "stored_sha256": None if stored is None else _canonical_hash(stored),
    }
    if observed.shape != (4, 765) or screen.shape != (99, 765) or observed_t.shape != (4,):
        raise AuditStopError("rank inputs have the wrong frozen shapes")
    if not np.isfinite(screen).all() or (screen < -1e-10).any():
        q_values = np.full((4, 765), np.nan, dtype=np.float64)
        decisions = [
            {
                "case": index,
                "status": "abstain_invalid_shared_screen",
                "p_BB": 1.0,
                "declare": False,
                "release_blocked": False,
            }
            for index in range(4)
        ]
        reconstructed = {
            "candidate_indices": [[], [], [], []],
            "union": [],
            "decisions": decisions,
        }
        _validate_stored_rank(stored, reconstructed, q_values)
        return {
            "schema": SCHEMA,
            "kind": "rank_chain",
            "passed": True,
            "status": "complete_with_abstention",
            "numerical_status": "terminal_invalid",
            "diagnostic_passed": True,
            "release_blocked": False,
            "audit_binding": audit_binding,
            "q_values": q_values,
            **reconstructed,
        }
    q_values = np.full((4, 765), np.nan, dtype=np.float64)
    candidates: list[tuple[int, ...]] = []
    for case in range(4):
        if not np.isfinite(observed[case]).all():
            candidates.append(())
            continue
        discrepancies = np.asarray(
            [
                max(
                    0.0,
                    2.0
                    * (
                        float(np.max(observed[case, list(nuisance_neighbors(node))]))
                        - float(observed[case, node])
                    ),
                )
                for node in range(765)
            ]
        )
        q_values[case] = np.asarray(
            [inclusive_rank(discrepancies[node], screen[:, node].tolist()) for node in range(765)]
        )
        candidates.append(tuple(int(node) for node in np.flatnonzero(q_values[case] > 0.01)))
    union = tuple(sorted(set().union(*(set(nodes) for nodes in candidates))))
    decisions = []
    for case in range(4):
        nodes = candidates[case]
        if not np.isfinite(observed[case]).all():
            decisions.append(
                {
                    "case": case,
                    "status": "abstain_invalid_observed_screen",
                    "p_BB": 1.0,
                    "declare": False,
                    "release_blocked": False,
                }
            )
            continue
        if not nodes:
            decisions.append(
                {
                    "case": case,
                    "status": "abstain_empty_nuisance_set",
                    "p_BB": 1.0,
                    "declare": False,
                    "release_blocked": False,
                }
            )
            continue
        if not math.isfinite(float(observed_t[case])) or float(observed_t[case]) < -1e-10:
            decisions.append(
                {
                    "case": case,
                    "status": "abstain_invalid_observed_adjusted_fit",
                    "p_BB": 1.0,
                    "declare": False,
                    "release_blocked": False,
                }
            )
            continue
        missing = [node for node in nodes if node not in effect_reference_statistics]
        if missing:
            decisions.append(
                {
                    "case": case,
                    "status": "pending_effect_tables",
                    "p_BB": None,
                    "declare": False,
                    "release_blocked": True,
                    "missing_nodes": missing,
                }
            )
            continue
        tables = {
            node: np.asarray(effect_reference_statistics[node], dtype=np.float64) for node in nodes
        }
        if any(values.shape != (999,) for values in tables.values()):
            raise AuditStopError("effect rank table has the wrong frozen shape")
        invalid = [
            node
            for node, values in tables.items()
            if not np.isfinite(values).all() or bool((values < -1e-10).any())
        ]
        if invalid:
            decisions.append(
                {
                    "case": case,
                    "status": "abstain_invalid_effect_table",
                    "p_BB": 1.0,
                    "declare": False,
                    "release_blocked": False,
                    "invalid_nodes": invalid,
                }
            )
            continue
        decision = effect_decision(
            float(observed_t[case]),
            nodes,
            {node: values.tolist() for node, values in tables.items()},
        )
        decisions.append(
            {
                "case": case,
                "status": "ready",
                "p_BB": decision["p_BB"],
                "declare": decision["declare"],
                "release_blocked": False,
                "node_p": decision["node_p"],
            }
        )
    reconstructed = {
        "candidate_indices": [list(nodes) for nodes in candidates],
        "union": list(union),
        "decisions": decisions,
    }
    _validate_stored_rank(stored, reconstructed, q_values)
    pending = any(row["release_blocked"] for row in decisions)
    terminal_invalid = any(str(row["status"]).startswith("abstain_") for row in decisions)
    return {
        "schema": SCHEMA,
        "kind": "rank_chain",
        "passed": not pending,
        "status": "pending" if pending else "complete",
        "numerical_status": (
            "pending" if pending else "terminal_invalid" if terminal_invalid else "valid"
        ),
        "diagnostic_passed": None if pending else True,
        "release_blocked": pending,
        "audit_binding": audit_binding,
        "q_values": q_values,
        **reconstructed,
    }


__all__ = [
    "AuditResources",
    "AuditStopError",
    "audit_effect_node",
    "audit_observed_screen",
    "audit_rank_chain",
    "audit_screen_node",
    "audit_training_case",
    "load_audit_resources",
]
