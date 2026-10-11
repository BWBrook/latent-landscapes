#!/usr/bin/env python3
"""Independent per-history numerical audit for Goal 062.

This module deliberately does not import the Goal 062 producer, production
likelihood, or fitter.  It reuses the frozen public-input reconstruction,
direct empirical-bank scorer, analytic pre-only scorer, and shared spread
kernel already accepted for the Goal 061 independent audit.

The public functions return compact receipts.  A malformed schema, identity,
source binding, generator replay, or score mismatch sets ``release_blocked``.
Undefined or nonconverged fits and unusable audited reference tables are kept
as terminal numerical outcomes and do not become source defects.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
from audit_capstone_public import (
    direct_point_score,
    inclusive_rank,
    local_discrepancy,
    nuisance_grid,
)
from audit_capstone_training import (
    AuditResources,
    PreOnlyData,
    _audit_coarse_grid,
    _audit_profiles,
    load_audit_resources,
)
from numpy.typing import NDArray

from latent_landscapes.goal006.spread import (
    compute_contrast_spread,
    sample_edge_shock_vector,
)
from latent_landscapes.preinvasion_independent import independent_pre_log_likelihood

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]

SCHEMA = "goal062-independent-history-audit-v1"
HISTORY_SCHEMA = "goal062-history-v1"
MAIN_SCHEMA = "goal062-main-fit-v1"
DECISION_SCHEMA = "goal062-cached-decisions-v1"
DIAGNOSTIC_SCHEMA = "goal062-main-diagnostics-v1"
HOLDOUT_SCHEMA = "goal062-heldout-score-v1"

EVALUATION_ROOT = 2026101101
MECHANICAL_ROOT = 987654321
NAMESPACE = 62
DOMAIN = 1
REPLICATES = 500
SITE_COUNT = 160
TRAINING_SITE_COUNT = 120
HOLDOUT_SITE_COUNT = 40
BANK_SIZE = 131_072
SCORE_TOLERANCE = 1e-8
STATISTIC_TOLERANCE = 1e-6
PARAMETER_BOUND_ULPS = 8
BOUNDARY_EPS = 1e-7
SUCCESS_TIE_TOLERANCE = 1e-8

PREY_TIMES = np.arange(-60.0, 61.0, 10.0)
PREDATOR_TIMES = np.arange(10.0, 61.0, 10.0)
ADDRESS_ORDER = ("root", "namespace", "domain", "cell", "replicate", "stage")
BASE_STAGES = {
    "spread": 1,
    "prey_loss": 2,
    "predator_visits": 3,
    "site_detection": 4,
    "prey_visits": 5,
}
B100_STAGES = {**BASE_STAGES, "background_field": 6}
GENERATOR_ARRAY_NAMES = (
    "prey_counts",
    "predator_counts",
    "arrival",
    "loss",
    "site_hazard",
    "site_detection",
    "prey_alive",
    "map_hazard",
)
MODEL_NAMES = (
    "constant_free_h",
    "adjusted_free_h",
    "constant_h1",
    "adjusted_h1",
)
PARAMETER_NAMES = ("h", "beta", "mu", "detection_sd")
PARAMETER_BOUNDS = {
    "h": (1.0, 10.0),
    "beta": (-2.0, 2.0),
    "mu": (0.0005, 0.006),
    "detection_sd": (0.0, 0.4),
}
DOMAIN_STARTS = (
    {"h": 1.0, "beta": 0.0, "mu": 0.002, "detection_sd": 0.0},
    {"h": 1.0, "beta": -1.0, "mu": 0.002, "detection_sd": 0.4},
    {"h": 1.0, "beta": 1.0, "mu": 0.002, "detection_sd": 0.4},
    {"h": 3.0, "beta": 0.0, "mu": 0.002, "detection_sd": 0.2},
    {"h": 3.0, "beta": -1.0, "mu": 0.002, "detection_sd": 0.0},
    {"h": 3.0, "beta": 1.0, "mu": 0.002, "detection_sd": 0.4},
    {"h": 10.0, "beta": 0.0, "mu": 0.002, "detection_sd": 0.4},
    {"h": 10.0, "beta": -1.0, "mu": 0.002, "detection_sd": 0.2},
    {"h": 10.0, "beta": 1.0, "mu": 0.002, "detection_sd": 0.0},
)
FIT_KEYS = {
    "model",
    *PARAMETER_NAMES,
    "raw_logjoint",
    "numerical_status",
    "nfev",
    "elapsed_seconds",
    "starts",
    "objective_gap",
    "boundary_flags",
    "warnings",
}
START_KEYS = {
    "initial_parameters",
    "final_parameters",
    "raw_logjoint",
    "objective",
    "success",
    "status",
    "message",
    "nfev",
    "method",
}
FITTER_WARNINGS = {
    "likelihood callback returned an invalid value",
    "likelihood callback returned NaN or infinity",
    "Powell refinement did not improve the best L-BFGS-B objective",
}
PROFILE_POINTS = 181 + 181 + 81
LATTICE_POINTS = 1_350


@dataclass(frozen=True)
class Cell:
    index: int
    label: str
    background: str
    effect: float
    mean_hazard: float
    generating_beta: float | None
    detection_sd: float = 0.2


CELLS = (
    Cell(0, "L1", "exact", 1.0, 0.001, 0.5),
    Cell(1, "L3", "exact", 3.0, 0.001, 0.5),
    Cell(2, "L5", "exact", 5.0, 0.001, 0.5),
    Cell(3, "H1", "exact", 1.0, 0.004, 0.5),
    Cell(4, "H3", "exact", 3.0, 0.004, 0.5),
    Cell(5, "H5", "exact", 5.0, 0.004, 0.5),
    Cell(6, "B_L1", "B100-A", 1.0, 0.001, None),
    Cell(7, "B_L3", "B100-A", 3.0, 0.001, None),
    Cell(8, "B_H1", "B100-A", 1.0, 0.004, None),
    Cell(9, "B_H3", "B100-A", 3.0, 0.004, None),
)


class AuditStopError(ValueError):
    """A schema, identity, source, generator, or score mismatch blocks release."""


@dataclass(frozen=True)
class AuditedStart:
    initial: dict[str, float]
    final: dict[str, float] | None
    raw_logjoint: float | None
    objective: float | None
    success: bool
    nfev: int
    method: str


@dataclass(frozen=True)
class ReferenceCache:
    """Validated, immutable reference statistics cached once for many histories."""

    screen_statistics: FloatArray
    screen_usable: BoolArray
    effect_statistics: FloatArray
    effect_usable: BoolArray
    binding: Mapping[str, Any]


def _finite(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, np.ndarray):
        return {"__array_binding__": array_binding(value)}
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_jsonable(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return {"__nonfinite_float__": repr(value)}
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(f"unsupported binding value: {type(value).__name__}")


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        _jsonable(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def array_binding(value: Any) -> dict[str, Any]:
    array = np.ascontiguousarray(np.asarray(value))
    return {
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "sha256": hashlib.sha256(array.tobytes(order="C")).hexdigest(),
    }


def _artifact_binding(metadata: Mapping[str, Any], arrays: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "metadata_sha256": canonical_sha256(metadata),
        "arrays": {
            name: array_binding(arrays[name])
            for name in sorted(arrays)
        },
    }


def history_seed(cell: int, replicate: int, stage: int, *, root: int) -> int:
    if root not in {EVALUATION_ROOT, MECHANICAL_ROOT}:
        raise AuditStopError("history root is neither registered nor mechanical")
    if not 0 <= cell < len(CELLS) or not 0 <= replicate < REPLICATES:
        raise AuditStopError("history cell or replicate is outside the frozen design")
    if stage not in range(1, 7):
        raise AuditStopError("history stage is outside the frozen address space")
    return int(
        np.random.SeedSequence([root, NAMESPACE, DOMAIN, cell, replicate, stage])
        .generate_state(1, dtype=np.uint64)[0]
    )


def expected_truth(cell: int) -> dict[str, Any]:
    if not 0 <= cell < len(CELLS):
        raise AuditStopError("cell index is outside the frozen table")
    row = CELLS[cell]
    return {
        "cell_index": row.index,
        "label": row.label,
        "background": row.background,
        "effect": row.effect,
        "mean_hazard": row.mean_hazard,
        "generating_beta": row.generating_beta,
        "detection_sd": row.detection_sd,
    }


def make_reference_cache(
    screen_statistics: Any,
    effect_statistics: Any,
    *,
    screen_usable: Any | None = None,
    effect_usable: Any | None = None,
    binding: Mapping[str, Any] | None = None,
) -> ReferenceCache:
    screen = np.asarray(screen_statistics, dtype=np.float64)
    effect = np.asarray(effect_statistics, dtype=np.float64)
    if screen.shape == (99, 765):
        screen = screen.T
    if screen.shape != (765, 99) or effect.shape != (765, 999):
        raise AuditStopError("reference cache has the wrong frozen shape")
    screen_ok = (
        np.ones(765, dtype=bool)
        if screen_usable is None
        else np.asarray(screen_usable, dtype=bool)
    )
    effect_ok = (
        np.ones(765, dtype=bool)
        if effect_usable is None
        else np.asarray(effect_usable, dtype=bool)
    )
    if screen_ok.shape != (765,) or effect_ok.shape != (765,):
        raise AuditStopError("reference usability masks have the wrong shape")
    if np.any(screen_ok & ~np.isfinite(screen).all(axis=1)):
        raise AuditStopError("a usable screen table contains a nonfinite row")
    if np.any(effect_ok & ~np.isfinite(effect).all(axis=1)):
        raise AuditStopError("a usable effect table contains a nonfinite row")
    if np.any(screen_ok & (screen < -1e-10).any(axis=1)):
        raise AuditStopError("a usable screen table contains a negative statistic")
    if np.any(effect_ok & (effect < -1e-10).any(axis=1)):
        raise AuditStopError("a usable effect table contains a negative statistic")
    cache_binding = {
        "screen_statistics": array_binding(screen),
        "screen_usable": array_binding(screen_ok),
        "effect_statistics": array_binding(effect),
        "effect_usable": array_binding(effect_ok),
        "source": dict(binding or {}),
    }
    return ReferenceCache(screen, screen_ok, effect, effect_ok, cache_binding)


def _blocked_receipt(
    kind: str,
    error: Exception,
    *,
    binding: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "kind": kind,
        "passed": False,
        "status": "release_blocked",
        "numerical_status": "not_assessed",
        "release_blocked": True,
        "reason": str(error),
        "error_type": type(error).__name__,
        "counts": {},
        "max_abs_discrepancy": {},
        "artifact_binding": dict(binding or {}),
    }


def _receipt(
    kind: str,
    *,
    numerical_status: str,
    counts: Mapping[str, int],
    maxima: Mapping[str, float | None],
    binding: Mapping[str, Any],
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "kind": kind,
        "passed": True,
        "status": "audited_complete",
        "numerical_status": numerical_status,
        "release_blocked": False,
        "counts": dict(counts),
        "max_abs_discrepancy": dict(maxima),
        "artifact_binding": dict(binding),
        **dict(details or {}),
    }


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AuditStopError(f"{label} is not a mapping")
    return value


def _identity(metadata: Mapping[str, Any]) -> tuple[int, int, int]:
    if metadata.get("schema") != HISTORY_SCHEMA:
        raise AuditStopError("history metadata schema changed")
    cell = metadata.get("cell_index")
    replicate = metadata.get("replicate")
    history = metadata.get("history_index")
    if type(cell) is not int or type(replicate) is not int or type(history) is not int:
        raise AuditStopError("history identity fields are not integers")
    if not 0 <= cell < len(CELLS) or not 0 <= replicate < REPLICATES:
        raise AuditStopError("history identity is outside the frozen design")
    if history != cell * REPLICATES + replicate:
        raise AuditStopError("history index is not cell-major")
    if metadata.get("cell_label") != CELLS[cell].label:
        raise AuditStopError("history cell label changed")
    return history, cell, replicate


def _validate_truth_and_seeds(metadata: Mapping[str, Any]) -> tuple[Cell, dict[str, int]]:
    _history, cell_index, replicate = _identity(metadata)
    cell = CELLS[cell_index]
    if metadata.get("truth") != expected_truth(cell_index):
        raise AuditStopError("history truth differs from the registered cell")
    seed_record = _require_mapping(metadata.get("seeds"), "history seed record")
    root = seed_record.get("root")
    if type(root) is not int or root not in {EVALUATION_ROOT, MECHANICAL_ROOT}:
        raise AuditStopError("history seed root changed")
    expected_header = {
        "namespace": NAMESPACE,
        "domain": DOMAIN,
        "cell": cell_index,
        "replicate": replicate,
    }
    if any(seed_record.get(name) != value for name, value in expected_header.items()):
        raise AuditStopError("history seed header changed")
    if tuple(seed_record.get("address_order", ())) != ADDRESS_ORDER:
        raise AuditStopError("history seed address order changed")
    stages = B100_STAGES if cell.background == "B100-A" else BASE_STAGES
    streams = _require_mapping(seed_record.get("streams"), "history seed streams")
    addresses = _require_mapping(seed_record.get("addresses"), "history seed addresses")
    stage_records = _require_mapping(
        seed_record.get("stage_records"), "history seed stage records"
    )
    stream_sets_match = (
        set(streams) == set(stages)
        and set(addresses) == set(stages)
        and set(stage_records) == set(stages)
    )
    if not stream_sets_match:
        raise AuditStopError("history seed stream set changed")
    result: dict[str, int] = {}
    for name, stage in stages.items():
        row = _require_mapping(stage_records[name], f"seed stage record {name}")
        address = [root, NAMESPACE, DOMAIN, cell_index, replicate, stage]
        expected = history_seed(cell_index, replicate, stage, root=root)
        if (
            row.get("stage") != stage
            or row.get("address") != address
            or row.get("seed") != expected
            or streams.get(name) != expected
            or addresses.get(name) != address
        ):
            raise AuditStopError(f"history seed address changed for {name}")
        result[name] = expected
    if len(set(result.values())) != len(result):
        raise AuditStopError("history seed streams collide")
    return cell, result


def _validate_array_schema(
    arrays: Mapping[str, Any], resources: AuditResources
) -> dict[str, NDArray[Any]]:
    required = {
        "site_ids",
        "training_mask",
        *GENERATOR_ARRAY_NAMES,
    }
    if set(arrays) != required:
        raise AuditStopError("history array schema contains missing or undocumented arrays")
    values = {name: np.asarray(arrays[name]) for name in required}
    expected_sites = tuple(resources.context.site_ids)
    site_ids = tuple(str(value) for value in values["site_ids"].reshape(-1))
    training = np.asarray(values["training_mask"], dtype=bool)
    expected_training = np.asarray(resources.context.training, dtype=bool)
    if site_ids != expected_sites:
        raise AuditStopError("history site order differs from the public design")
    if training.shape != (SITE_COUNT,) or not np.array_equal(training, expected_training):
        raise AuditStopError("history training mask differs from the public split")
    if int(training.sum()) != TRAINING_SITE_COUNT:
        raise AuditStopError("history training mask has the wrong count")
    prey = values["prey_counts"]
    predator = values["predator_counts"]
    if (
        prey.shape != (SITE_COUNT, 13)
        or predator.shape != (SITE_COUNT, 6)
        or not np.issubdtype(prey.dtype, np.integer)
        or not np.issubdtype(predator.dtype, np.integer)
        or not np.isin(prey, (0, 1, 2)).all()
        or not np.isin(predator, (0, 1, 2)).all()
    ):
        raise AuditStopError("history observation counts violate the frozen schema")
    expected_shapes = {
        "arrival": (SITE_COUNT,),
        "loss": (SITE_COUNT,),
        "site_hazard": (SITE_COUNT,),
        "site_detection": (SITE_COUNT,),
        "prey_alive": (SITE_COUNT, 13),
        "map_hazard": (72, 84),
    }
    for name, shape in expected_shapes.items():
        if values[name].shape != shape:
            raise AuditStopError(f"history array {name} has the wrong shape")
    for name in ("arrival", "loss", "site_hazard", "site_detection", "map_hazard"):
        if not np.isfinite(values[name]).all():
            raise AuditStopError(f"history array {name} is nonfinite")
    if not np.issubdtype(values["prey_alive"].dtype, np.bool_):
        raise AuditStopError("history prey-alive array is not boolean")
    return values


def _loss_times(
    arrivals: FloatArray, hazards: FloatArray, effect: float, thresholds: FloatArray
) -> FloatArray:
    result = np.empty_like(arrivals)
    for index, (arrival, hazard, threshold) in enumerate(
        zip(arrivals, hazards, thresholds, strict=True)
    ):
        predator_arrival = float(arrival) + 60.0
        before = float(hazard) * predator_arrival
        if threshold <= before:
            calendar = threshold / hazard
        else:
            calendar = predator_arrival + (threshold - before) / (hazard * effect)
        result[index] = calendar - 60.0
    return result


def _hazard_map(resources: AuditResources, cell: Cell, streams: Mapping[str, int]) -> FloatArray:
    exposure = np.asarray(resources.setup.exposure_score, dtype=np.float64)
    if cell.background == "exact":
        if cell.generating_beta is None:
            raise AuditStopError("exact cell has no generating beta")
        scaled = cell.generating_beta * exposure
        shift = float(np.max(scaled))
        raw = np.exp(scaled - shift)
    else:
        gaussian = resources.setup.field_sampler.sample(
            np.random.default_rng(streams["background_field"])
        )
        z = 0.7 * exposure + math.sqrt(0.51) * gaussian
        raw = np.exp(math.sqrt(math.log(2.0)) * z)
    result = cell.mean_hazard * raw / float(np.mean(raw))
    if result.shape != (72, 84) or not np.isfinite(result).all() or (result <= 0).any():
        raise AuditStopError("independent generator produced an invalid hazard map")
    return np.asarray(result, dtype=np.float64)


def replay_history(
    resources: AuditResources, cell: Cell, streams: Mapping[str, int]
) -> dict[str, NDArray[Any]]:
    """Replay one complete history without importing the producer adapter."""
    shocks = sample_edge_shock_vector(
        resources.fixed.landscape, np.random.default_rng(streams["spread"])
    )
    spread = compute_contrast_spread(
        resources.fixed.landscape, 1.0, edge_shocks=shocks, rho=1.0
    )
    rows = np.asarray(resources.setup.site_rows, dtype=np.int64)
    columns = np.asarray(resources.setup.site_cols, dtype=np.int64)
    arrival = np.asarray(spread.arrival[rows, columns], dtype=np.float64)
    map_hazard = _hazard_map(resources, cell, streams)
    site_hazard = np.asarray(map_hazard[rows, columns], dtype=np.float64)
    thresholds = np.random.default_rng(streams["prey_loss"]).exponential(size=SITE_COUNT)
    loss = _loss_times(arrival, site_hazard, cell.effect, thresholds)
    concentration = 0.65 * 0.35 / cell.detection_sd**2 - 1.0
    site_detection = np.random.default_rng(streams["site_detection"]).beta(
        0.65 * concentration, 0.35 * concentration, size=SITE_COUNT
    )
    predator_alive = arrival[:, None] <= PREDATOR_TIMES[None, :]
    prey_alive = loss[:, None] > PREY_TIMES[None, :]
    predator = (
        (
            np.random.default_rng(streams["predator_visits"]).random((SITE_COUNT, 6, 2))
            < 0.65
        ).sum(axis=2)
        * predator_alive
    ).astype(np.int64)
    prey = (
        (
            np.random.default_rng(streams["prey_visits"]).random((SITE_COUNT, 13, 2))
            < site_detection[:, None, None]
        ).sum(axis=2)
        * prey_alive
    ).astype(np.int64)
    return {
        "prey_counts": prey,
        "predator_counts": predator,
        "arrival": arrival,
        "loss": loss,
        "site_hazard": site_hazard,
        "site_detection": site_detection,
        "prey_alive": np.asarray(prey_alive, dtype=bool),
        "map_hazard": map_hazard,
    }


def _audit_history_inputs(
    metadata: Mapping[str, Any], arrays: Mapping[str, Any], resources: AuditResources
) -> dict[str, Any]:
    cell, streams = _validate_truth_and_seeds(metadata)
    stored = _validate_array_schema(arrays, resources)
    replay = replay_history(resources, cell, streams)
    mismatches = [
        name
        for name, expected in replay.items()
        if not np.array_equal(np.asarray(stored[name]), expected, equal_nan=True)
    ]
    if mismatches:
        raise AuditStopError(f"whole-generator replay differs for {mismatches}")
    return _receipt(
        "history_inputs",
        numerical_status="valid",
        counts={
            "sites": SITE_COUNT,
            "training_sites": TRAINING_SITE_COUNT,
            "streams": len(streams),
        },
        maxima={"generator_replay": 0.0},
        binding=_artifact_binding(metadata, arrays),
        details={
            "history_index": metadata["history_index"],
            "cell_index": cell.index,
            "replicate": metadata["replicate"],
            "background": cell.background,
            "all_generator_arrays_bitwise": True,
        },
    )


def audit_history_inputs(
    metadata: Mapping[str, Any], arrays: Mapping[str, Any], resources: AuditResources
) -> dict[str, Any]:
    try:
        return _audit_history_inputs(metadata, arrays, resources)
    except Exception as error:
        return _blocked_receipt(
            "history_inputs",
            error,
            binding=_artifact_binding(metadata, arrays) if isinstance(arrays, Mapping) else {},
        )


def _fit_point(value: Any) -> dict[str, float] | None:
    if not isinstance(value, Mapping):
        return None
    if any(
        raw is not None
        and (
            isinstance(raw, bool)
            or not isinstance(raw, (int, float, np.integer, np.floating))
        )
        for raw in (value.get(name) for name in PARAMETER_NAMES)
    ):
        return None
    parsed = {name: _finite(value.get(name)) for name in PARAMETER_NAMES}
    if any(item is None for item in parsed.values()):
        return None
    point = {name: float(item) for name, item in parsed.items() if item is not None}
    for name, (lower, upper) in PARAMETER_BOUNDS.items():
        observed = point[name]
        if (
            lower - observed > PARAMETER_BOUND_ULPS * math.ulp(lower)
            or observed - upper > PARAMETER_BOUND_ULPS * math.ulp(upper)
        ):
            raise AuditStopError("stored fit point violates the frozen parameter bounds")
    return point


def _parameter_mapping(value: Any, label: str, *, finite: bool) -> dict[str, float] | None:
    mapping = _require_mapping(value, label)
    if set(mapping) != set(PARAMETER_NAMES):
        raise AuditStopError(f"{label} parameter schema changed")
    for name, raw in mapping.items():
        if raw is not None and (
            isinstance(raw, bool)
            or not isinstance(raw, (int, float, np.integer, np.floating))
        ):
            raise AuditStopError(f"{label} parameter {name} changed type")
        parsed = _finite(raw)
        if raw is not None and parsed is None:
            raise AuditStopError(f"{label} parameter {name} changed type")
        if parsed is not None:
            lower, upper = PARAMETER_BOUNDS[name]
            if (
                lower - parsed > PARAMETER_BOUND_ULPS * math.ulp(lower)
                or parsed - upper > PARAMETER_BOUND_ULPS * math.ulp(upper)
            ):
                raise AuditStopError(f"{label} parameter {name} violates its bounds")
    point = _fit_point(mapping)
    if point is None and finite:
        raise AuditStopError(f"{label} parameters are not finite")
    return point


def _parameters_match(left: Mapping[str, float], right: Mapping[str, float]) -> bool:
    return all(
        abs(float(left[name]) - float(right[name]))
        <= PARAMETER_BOUND_ULPS
        * max(math.ulp(float(left[name])), math.ulp(float(right[name])))
        for name in PARAMETER_NAMES
    )


def _require_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AuditStopError(f"{label} is not a nonnegative integer")
    return value


def _compare_mechanical_numeric(stored: Any, expected: float | None, label: str) -> None:
    value = _finite(stored)
    if expected is None:
        if stored is not None:
            raise AuditStopError(f"{label} is finite when the fitter result is nonfinite")
    elif (
        isinstance(stored, bool)
        or not isinstance(stored, (int, float, np.integer, np.floating))
        or value is None
        or abs(value - expected) > SCORE_TOLERANCE
    ):
        raise AuditStopError(f"{label} changed from the fitter records")


def _expected_boundary_flags(point: Mapping[str, float]) -> tuple[str, ...]:
    flags: list[str] = []
    for name, (lower, upper) in PARAMETER_BOUNDS.items():
        value = float(point[name])
        scale = max(abs(lower), abs(upper), 1.0)
        if abs(value - lower) <= BOUNDARY_EPS * scale:
            flags.append(f"{name}_lower")
        if abs(value - upper) <= BOUNDARY_EPS * scale:
            flags.append(f"{name}_upper")
    return tuple(flags)


def _audit_start(
    value: Any,
    *,
    model: str,
    position: int,
    expected_method: str,
    expected_initial: Mapping[str, float],
    expected_candidate_success: bool | None = None,
) -> AuditedStart:
    row = _require_mapping(value, f"{model} start {position}")
    if set(row) != START_KEYS:
        raise AuditStopError(f"{model} start {position} schema changed")
    initial = _parameter_mapping(
        row.get("initial_parameters"), f"{model} start {position} initial", finite=True
    )
    assert initial is not None
    if not _parameters_match(initial, expected_initial):
        raise AuditStopError(f"{model} start {position} initial parameters changed")
    final = _parameter_mapping(
        row.get("final_parameters"), f"{model} start {position} final", finite=False
    )
    method = row.get("method")
    if method != expected_method:
        raise AuditStopError(f"{model} start {position} method changed")
    status = row.get("status")
    message = row.get("message")
    if not isinstance(message, str):
        raise AuditStopError(f"{model} start {position} message is not text")
    if method == "candidate":
        expected_status = (
            "nested_converged" if expected_candidate_success else "nested_unconverged"
        )
        expected_message = (
            "nested candidate"
            if expected_candidate_success
            else "nested candidate from unconverged fit"
        )
        if status != expected_status or message != expected_message:
            raise AuditStopError(f"{model} nested candidate status changed")
    elif isinstance(status, bool) or not isinstance(status, int):
        raise AuditStopError(f"{model} start {position} optimizer status changed type")
    stored_objective = row.get("objective")
    stored_raw = row.get("raw_logjoint")
    for label, stored in (("objective", stored_objective), ("raw score", stored_raw)):
        if stored is not None and (
            isinstance(stored, bool)
            or not isinstance(stored, (int, float, np.integer, np.floating))
        ):
            raise AuditStopError(f"{model} start {position} {label} changed type")
    objective = _finite(stored_objective)
    raw = _finite(stored_raw)
    if stored_objective is not None and objective is None:
        raise AuditStopError(f"{model} start {position} objective changed type")
    if stored_raw is not None and raw is None:
        raise AuditStopError(f"{model} start {position} raw score changed type")
    objective_valid = objective is not None and objective < 1e299
    expected_raw = -objective if objective is not None and objective_valid else None
    _compare_mechanical_numeric(
        row.get("raw_logjoint"), expected_raw, f"{model} start raw score"
    )
    success = row.get("success")
    if not isinstance(success, bool):
        raise AuditStopError(f"{model} start {position} success flag changed type")
    if success and (not objective_valid or final is None):
        raise AuditStopError(f"{model} start {position} reports impossible success")
    if method == "candidate":
        expected_success = bool(objective_valid and expected_candidate_success)
        if success is not expected_success:
            raise AuditStopError(f"{model} nested candidate success changed")
        if row.get("nfev") != 1:
            raise AuditStopError(f"{model} nested candidate nfev changed")
    nfev = _require_integer(row.get("nfev"), f"{model} start {position} nfev")
    if final is not None:
        if model.startswith("constant") and final["beta"] != 0.0:
            raise AuditStopError(f"{model} start {position} changed fixed beta")
        if model.endswith("h1") and final["h"] != 1.0:
            raise AuditStopError(f"{model} start {position} changed fixed h")
    return AuditedStart(initial, final, raw, objective, success, nfev, method)


def _fit_sort_key(start: AuditedStart) -> tuple[float, tuple[float, ...]]:
    assert start.objective is not None and start.final is not None
    return start.objective, tuple(start.final[name] for name in PARAMETER_NAMES)


def _audit_fit_records(
    model: str,
    row: Mapping[str, Any],
    *,
    null_row: Mapping[str, Any] | None,
    null_point: Mapping[str, float] | None,
    null_status: str | None,
) -> bool:
    if set(row) != FIT_KEYS:
        raise AuditStopError(f"main fit {model} schema changed")
    stored_elapsed = row.get("elapsed_seconds")
    elapsed = _finite(stored_elapsed)
    if (
        isinstance(stored_elapsed, bool)
        or not isinstance(stored_elapsed, (int, float, np.integer, np.floating))
        or elapsed is None
        or elapsed < 0.0
    ):
        raise AuditStopError(f"main fit {model} elapsed time is invalid")
    warnings = row.get("warnings")
    if (
        not isinstance(warnings, Sequence)
        or isinstance(warnings, (str, bytes))
        or any(not isinstance(item, str) or item not in FITTER_WARNINGS for item in warnings)
        or len(set(warnings)) != len(warnings)
    ):
        raise AuditStopError(f"main fit {model} warnings changed schema")
    starts = row.get("starts")
    if not isinstance(starts, Sequence) or isinstance(starts, (str, bytes)):
        raise AuditStopError(f"main fit {model} starts are malformed")
    free_model = model.endswith("free_h")
    prefix_count = len(DOMAIN_STARTS) + int(free_model)
    if len(starts) not in {prefix_count, prefix_count + 1}:
        raise AuditStopError(f"main fit {model} start count changed")
    audited: list[AuditedStart] = []
    for index, initial in enumerate(DOMAIN_STARTS):
        audited.append(
            _audit_start(
                starts[index],
                model=model,
                position=index,
                expected_method="L-BFGS-B",
                expected_initial=initial,
            )
        )
    if free_model:
        if null_row is None or null_point is None or null_status is None:
            raise AuditStopError(f"main fit {model} lacks a finite nested null candidate")
        candidate = _audit_start(
            starts[len(DOMAIN_STARTS)],
            model=model,
            position=len(DOMAIN_STARTS),
            expected_method="candidate",
            expected_initial=null_point,
            expected_candidate_success=null_status == "converged",
        )
        if candidate.final is None or not _parameters_match(candidate.final, null_point):
            raise AuditStopError(f"main fit {model} nested candidate point changed")
        _compare_mechanical_numeric(
            candidate.raw_logjoint,
            _finite(null_row.get("raw_logjoint")),
            f"main fit {model} nested candidate score",
        )
        audited.append(candidate)

    valid_prefix = [
        start
        for start in audited
        if start.objective is not None and start.objective < 1e299 and start.final is not None
    ]
    raw_valid_count = sum(
        start.objective is not None and start.objective < 1e299 for start in audited
    )
    if raw_valid_count != len(valid_prefix):
        raise AuditStopError(
            f"main fit {model} has a finite objective with nonfinite final coordinates"
        )
    expected_powell_warning = "Powell refinement did not improve the best L-BFGS-B objective"
    if not valid_prefix:
        if len(starts) != prefix_count:
            raise AuditStopError(f"main fit {model} ran Powell without a valid base outcome")
        if (
            _fit_status(row) != "invalid"
            or _fit_point(row) is not None
            or any(row.get(name) is not None for name in PARAMETER_NAMES)
        ):
            raise AuditStopError(f"main fit {model} invalid sentinel changed")
        _compare_mechanical_numeric(row.get("raw_logjoint"), None, f"main fit {model} score")
        _compare_mechanical_numeric(row.get("objective_gap"), None, f"main fit {model} gap")
        selected: AuditedStart | None = None
    else:
        ordered = sorted(valid_prefix, key=_fit_sort_key)
        floor = ordered[0].objective
        assert floor is not None
        converged = [start for start in ordered if start.success]
        best = (
            converged[0]
            if converged
            and converged[0].objective is not None
            and converged[0].objective <= floor + SUCCESS_TIE_TOLERANCE
            else ordered[0]
        )
        needs_powell = not best.success
        if len(starts) != prefix_count + int(needs_powell):
            raise AuditStopError(f"main fit {model} Powell fallback rule changed")
        selected = best
        if needs_powell:
            assert best.final is not None
            powell = _audit_start(
                starts[-1],
                model=model,
                position=len(starts) - 1,
                expected_method="Powell",
                expected_initial=best.final,
            )
            audited.append(powell)
            if (
                powell.success
                and powell.objective is not None
                and best.objective is not None
                and powell.objective <= best.objective + SUCCESS_TIE_TOLERANCE
            ):
                selected = powell
                if expected_powell_warning in warnings:
                    raise AuditStopError(f"main fit {model} has a spurious Powell warning")
            elif expected_powell_warning not in warnings:
                raise AuditStopError(f"main fit {model} lost its Powell warning")
        elif expected_powell_warning in warnings:
            raise AuditStopError(f"main fit {model} has a spurious Powell warning")
        assert selected.objective is not None and selected.final is not None
        expected_status = "converged" if selected.success else "failed_optimizer"
        if _fit_status(row) != expected_status:
            raise AuditStopError(f"main fit {model} selected status changed")
        point = _fit_point(row)
        if point is None or not _parameters_match(point, selected.final):
            raise AuditStopError(f"main fit {model} selected point changed")
        _compare_mechanical_numeric(
            row.get("raw_logjoint"), -selected.objective, f"main fit {model} selected score"
        )
        objectives = sorted(
            start.objective for start in valid_prefix if start.objective is not None
        )
        gap = None if len(objectives) < 2 else objectives[1] - selected.objective
        _compare_mechanical_numeric(row.get("objective_gap"), gap, f"main fit {model} gap")

    if row.get("nfev") != sum(start.nfev for start in audited):
        raise AuditStopError(f"main fit {model} nfev total changed")
    point = _fit_point(row)
    expected_flags = () if point is None else _expected_boundary_flags(point)
    flags = row.get("boundary_flags")
    if not isinstance(flags, Sequence) or isinstance(flags, (str, bytes)):
        raise AuditStopError(f"main fit {model} boundary flags are malformed")
    if tuple(flags) != expected_flags:
        raise AuditStopError(f"main fit {model} boundary flags changed")
    return True


def _fit_status(row: Mapping[str, Any]) -> str:
    return str(row.get("numerical_status", row.get("status", "missing")))


def _compare_optional_numeric(stored: Any, expected: float | None, label: str) -> None:
    value = _finite(stored)
    if expected is None:
        if value is not None:
            raise AuditStopError(f"{label} is finite when reconstruction is unavailable")
    elif value is None or abs(value - expected) > STATISTIC_TOLERANCE:
        raise AuditStopError(f"{label} differs from independent reconstruction")


def _validate_identity_record(
    record: Mapping[str, Any], metadata: Mapping[str, Any], *, schema: str
) -> None:
    history, cell, replicate = _identity(metadata)
    if record.get("schema") != schema:
        raise AuditStopError(f"{schema} record schema changed")
    expected = {
        "history_index": history,
        "cell_index": cell,
        "cell_label": CELLS[cell].label,
        "replicate": replicate,
    }
    if any(record.get(name) != value for name, value in expected.items()):
        raise AuditStopError(f"{schema} record identity changed")


def _audit_history_main(
    metadata: Mapping[str, Any],
    arrays: Mapping[str, Any],
    main: Mapping[str, Any],
    resources: AuditResources,
) -> dict[str, Any]:
    _validate_truth_and_seeds(metadata)
    stored_arrays = _validate_array_schema(arrays, resources)
    _validate_identity_record(main, metadata, schema=MAIN_SCHEMA)
    if main.get("representation") != "full" or main.get("bank_size") != BANK_SIZE:
        raise AuditStopError("main fit did not use the full frozen bank")
    fits = _require_mapping(main.get("fits"), "main fits")
    if set(fits) != set(MODEL_NAMES):
        raise AuditStopError("main fit model set changed")
    prey = np.asarray(stored_arrays["prey_counts"], dtype=np.int64)
    predator = np.asarray(stored_arrays["predator_counts"], dtype=np.int64)
    scores: dict[str, float | None] = {}
    points: dict[str, dict[str, float] | None] = {}
    statuses: dict[str, str] = {}
    errors: dict[str, float | None] = {}
    for model in MODEL_NAMES:
        row = _require_mapping(fits[model], f"main fit {model}")
        if set(row) != FIT_KEYS:
            raise AuditStopError(f"main fit {model} schema changed")
        if row.get("model") != model:
            raise AuditStopError(f"main fit identity changed for {model}")
        point = _fit_point(row)
        stored_score = _finite(row.get("raw_logjoint"))
        status = _fit_status(row)
        points[model] = point
        statuses[model] = status
        if point is None:
            if stored_score is not None or status == "converged":
                raise AuditStopError(f"main fit {model} has an inconsistent missing point")
            scores[model] = None
            errors[model] = None
            continue
        if model.startswith("constant") and point["beta"] != 0.0:
            raise AuditStopError(f"constant fit {model} changed beta")
        if model.endswith("h1") and point["h"] != 1.0:
            raise AuditStopError(f"null fit {model} changed h")
        direct = float(
            direct_point_score(resources.bank, resources.context, prey, predator, point)[
                "training_logjoint"
            ]
        )
        if not math.isfinite(direct):
            raise AuditStopError(f"independent main score is nonfinite for {model}")
        scores[model] = direct
        if stored_score is None:
            if status == "converged":
                raise AuditStopError(f"converged main fit {model} has no finite score")
            errors[model] = None
        else:
            error = abs(direct - stored_score)
            errors[model] = error
            if error > SCORE_TOLERANCE:
                raise AuditStopError(f"main score mismatch for {model}")

    fit_record_checks: dict[str, bool] = {}
    for model in ("constant_h1", "adjusted_h1", "constant_free_h", "adjusted_free_h"):
        family = "constant" if model.startswith("constant") else "adjusted"
        null_name = f"{family}_h1"
        null_row = (
            _require_mapping(fits[null_name], f"main fit {null_name}")
            if model.endswith("free_h")
            else None
        )
        fit_record_checks[model] = _audit_fit_records(
            model,
            _require_mapping(fits[model], f"main fit {model}"),
            null_row=null_row,
            null_point=points[null_name] if null_row is not None else None,
            null_status=statuses[null_name] if null_row is not None else None,
        )

    statistics = _require_mapping(main.get("statistics"), "main statistics")
    deltas: dict[str, float | None] = {}
    for family, free_name, null_name in (
        ("constant", "constant_free_h", "constant_h1"),
        ("adjusted", "adjusted_free_h", "adjusted_h1"),
    ):
        free = scores[free_name]
        null = scores[null_name]
        delta = free - null if free is not None and null is not None else None
        deltas[family] = delta
        statistic = 2.0 * max(0.0, delta) if delta is not None else None
        _compare_optional_numeric(statistics.get(family), statistic, f"{family} statistic")

    nesting = _require_mapping(main.get("nesting_gaps"), "main nesting gaps")
    nesting_status = _require_mapping(main.get("nesting_status"), "main nesting status")
    for family, delta in deltas.items():
        _compare_optional_numeric(
            nesting.get(family), None if delta is None else -delta, f"{family} nesting gap"
        )
        expected_status = (
            "passed"
            if delta is not None and -delta <= STATISTIC_TOLERANCE
            else "failed"
        )
        if nesting_status.get(family) != expected_status:
            raise AuditStopError(f"{family} nesting status changed")

    adjusted_delta = deltas["adjusted"]
    expected_validity = {
        "valid": bool(
            adjusted_delta is not None
            and statuses["adjusted_h1"] == "converged"
            and statuses["adjusted_free_h"] == "converged"
            and adjusted_delta >= -STATISTIC_TOLERANCE
        ),
        "null_finite": scores["adjusted_h1"] is not None,
        "free_finite": scores["adjusted_free_h"] is not None,
        "null_converged": statuses["adjusted_h1"] == "converged",
        "free_converged": statuses["adjusted_free_h"] == "converged",
        "free_minus_null": adjusted_delta,
        "minimum_free_minus_null": -STATISTIC_TOLERANCE,
    }
    validity = _require_mapping(main.get("observed_adjusted_validity"), "adjusted validity")
    for name, expected in expected_validity.items():
        if isinstance(expected, bool):
            if validity.get(name) is not expected:
                raise AuditStopError(f"adjusted validity flag {name} changed")
        else:
            _compare_optional_numeric(validity.get(name), expected, f"adjusted validity {name}")

    reconstructed_adjusted_statistic = (
        2.0 * max(0.0, adjusted_delta) if adjusted_delta is not None else None
    )
    expected_observed_effect_statistic = (
        reconstructed_adjusted_statistic if expected_validity["valid"] else None
    )
    _compare_optional_numeric(
        main.get("observed_effect_statistic"),
        expected_observed_effect_statistic,
        "observed effect statistic",
    )

    converged = main.get("main_statuses_converged")
    if not isinstance(converged, Mapping) or any(
        converged.get(model) is not (statuses[model] == "converged") for model in MODEL_NAMES
    ):
        raise AuditStopError("main convergence summary changed")
    compressed = _require_mapping(main.get("compressed_score_replay"), "compressed replay")
    if set(compressed) != set(MODEL_NAMES):
        raise AuditStopError("compressed replay model set changed")
    compressed_passed: dict[str, bool] = {}
    for model in MODEL_NAMES:
        row = _require_mapping(compressed[model], f"compressed replay {model}")
        difference = _finite(row.get("difference"))
        status = str(row.get("status"))
        if difference is None:
            if status == "passed":
                raise AuditStopError(f"compressed replay status is inconsistent for {model}")
            compressed_passed[model] = False
        else:
            if abs(difference) > SCORE_TOLERANCE:
                raise AuditStopError(f"compressed score replay failed for {model}")
            compressed_passed[model] = status == "passed"
            if not compressed_passed[model]:
                raise AuditStopError(f"compressed replay status changed for {model}")
        tolerance = _finite(row.get("tolerance"))
        if tolerance is None or tolerance != SCORE_TOLERANCE:
            raise AuditStopError("compressed replay tolerance changed")
    if main.get("all_main_replays_passed") is not all(compressed_passed.values()):
        raise AuditStopError("compressed replay summary changed")

    adjusted_point = points["adjusted_free_h"]
    recovery_available = bool(
        adjusted_point is not None
        and statuses["adjusted_free_h"] == "converged"
        and errors["adjusted_free_h"] is not None
        and errors["adjusted_free_h"] <= SCORE_TOLERANCE
    )
    finite_errors = [value for value in errors.values() if value is not None]
    numeric_valid = (
        all(status == "converged" for status in statuses.values())
        and all(value is not None for value in scores.values())
        and all(fit_record_checks.values())
    )
    return _receipt(
        "history_main",
        numerical_status="valid" if numeric_valid else "terminal_invalid",
        counts={
            "main_fits": len(MODEL_NAMES),
            "direct_scores": sum(value is not None for value in scores.values()),
            "converged_fits": sum(status == "converged" for status in statuses.values()),
            "start_records": sum(
                len(_require_mapping(fits[model], f"main fit {model}")["starts"])
                for model in MODEL_NAMES
            ),
        },
        maxima={"main_score_nats": max(finite_errors, default=0.0)},
        binding={
            **_artifact_binding(metadata, arrays),
            "main_sha256": canonical_sha256(main),
        },
        details={
            "history_index": metadata["history_index"],
            "fit_statuses": statuses,
            "direct_scores": scores,
            "score_abs_discrepancy": errors,
            "fit_record_selection_audited": fit_record_checks,
            "adjusted_statistic": reconstructed_adjusted_statistic,
            "declaration_pair_valid": expected_validity["valid"],
            "effect_recovery_available": recovery_available,
            "effect_estimate": (
                adjusted_point["h"] if recovery_available and adjusted_point else None
            ),
            "main_record_sha256": canonical_sha256(main),
        },
    )


def audit_history_main(
    metadata: Mapping[str, Any],
    arrays: Mapping[str, Any],
    main: Mapping[str, Any],
    resources: AuditResources,
) -> dict[str, Any]:
    try:
        return _audit_history_main(metadata, arrays, main, resources)
    except Exception as error:
        return _blocked_receipt(
            "history_main",
            error,
            binding={
                **(_artifact_binding(metadata, arrays) if isinstance(arrays, Mapping) else {}),
                "main_sha256": canonical_sha256(main),
            },
        )


def _observed_surface(
    arrays: Mapping[str, Any], resources: AuditResources
) -> FloatArray:
    values = _validate_array_schema(arrays, resources)
    mask = np.asarray(resources.context.training, dtype=bool)
    site_ids = tuple(np.asarray(resources.context.site_ids)[mask])
    prey = np.asarray(values["prey_counts"], dtype=np.int64)[mask][None, :, :]
    observations = PreOnlyData(
        site_ids,
        prey,
        np.ones(TRAINING_SITE_COUNT, dtype=bool),
        np.ones(TRAINING_SITE_COUNT, dtype=bool),
    )
    result = np.empty(765, dtype=np.float64)
    for node, (beta, mu, detection_sd) in enumerate(nuisance_grid()):
        score = independent_pre_log_likelihood(
            observations,
            np.asarray(resources.context.map_a, dtype=np.float64),
            np.asarray(resources.context.site_a, dtype=np.float64)[mask],
            beta=beta,
            mu=mu,
            detection_sd=detection_sd,
        )
        result[node] = float(np.asarray(score, dtype=np.float64).reshape(-1)[0])
    return result


def _cached_case(
    stored: Mapping[str, Any], history: int, case_id: str | None
) -> Mapping[str, Any]:
    if stored.get("schema") != DECISION_SCHEMA:
        raise AuditStopError("cached decision schema changed")
    screens = stored.get("screens")
    decisions = stored.get("decisions")
    if screens is not None or decisions is not None:
        if (
            not isinstance(screens, Sequence)
            or isinstance(screens, (str, bytes))
            or not isinstance(decisions, Sequence)
            or isinstance(decisions, (str, bytes))
            or len(screens) != len(decisions)
        ):
            raise AuditStopError("cached decision screen/decision rows are malformed")
        case_ids = stored.get("case_ids")
        if not isinstance(case_ids, Sequence) or isinstance(case_ids, (str, bytes)):
            raise AuditStopError("cached decision case identities are malformed")
        preferred = case_id or f"history-{history:04d}"
        if list(case_ids).count(preferred) != 1:
            raise AuditStopError("cached decision cannot identify this history")
        index = list(case_ids).index(preferred)
        screen = screens[index]
        decision = decisions[index]
        if not isinstance(screen, Mapping) or not isinstance(decision, Mapping):
            raise AuditStopError("cached decision rows are not mappings")
        if screen.get("case_id") != preferred or decision.get("case_id") != preferred:
            raise AuditStopError("cached decision row identity changed")
        return {"screen": screen, "decision": decision}
    cases = stored.get("cases")
    if cases is None:
        expected = case_id or f"history-{history:04d}"
        if stored.get("case_id") != expected:
            raise AuditStopError("cached decision cannot identify this history")
        return stored
    if isinstance(cases, Mapping):
        row = cases.get(str(history), cases.get(history))
    elif isinstance(cases, Sequence) and not isinstance(cases, (str, bytes)):
        matches = [
            row for row in cases if isinstance(row, Mapping) and row.get("history_index") == history
        ]
        row = matches[0] if len(matches) == 1 else None
    else:
        row = None
    if not isinstance(row, Mapping):
        raise AuditStopError("cached decision has no unique history row")
    expected = case_id or f"history-{history:04d}"
    if row.get("case_id", expected) != expected:
        raise AuditStopError("cached decision row identity changed")
    return row


def _compare_sequence(stored: Any, expected: Sequence[Any], label: str) -> None:
    value = stored.tolist() if isinstance(stored, np.ndarray) else stored
    observed = (
        list(value)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes))
        else None
    )
    if observed != list(expected):
        raise AuditStopError(f"{label} changed")


def _compare_float_vector(stored: Any, expected: FloatArray, label: str) -> None:
    try:
        value = np.asarray(stored, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise AuditStopError(f"{label} is not numeric") from error
    if value.shape != expected.shape or not np.array_equal(
        np.isfinite(value), np.isfinite(expected)
    ):
        raise AuditStopError(f"{label} finite pattern changed")
    finite = np.isfinite(expected)
    if np.any(finite) and float(np.max(np.abs(value[finite] - expected[finite]))) > SCORE_TOLERANCE:
        raise AuditStopError(f"{label} differs from reconstruction")


def _audit_history_screen_decision(
    metadata: Mapping[str, Any],
    arrays: Mapping[str, Any],
    stored_surface: Any,
    cached_decision: Mapping[str, Any],
    main_audit: Mapping[str, Any],
    references: ReferenceCache,
    resources: AuditResources,
) -> dict[str, Any]:
    history, _cell, _replicate = _identity(metadata)
    _validate_truth_and_seeds(metadata)
    direct_surface = _observed_surface(arrays, resources)
    surface = np.asarray(stored_surface, dtype=np.float64)
    if surface.shape != (765,):
        raise AuditStopError("observed score surface has the wrong shape")
    if not np.array_equal(np.isnan(surface), np.isnan(direct_surface)) or not np.array_equal(
        np.isposinf(surface), np.isposinf(direct_surface)
    ) or not np.array_equal(np.isneginf(surface), np.isneginf(direct_surface)):
        raise AuditStopError("observed score surface nonfinite pattern changed")
    finite = np.isfinite(direct_surface)
    surface_error = (
        float(np.max(np.abs(surface[finite] - direct_surface[finite]))) if finite.any() else 0.0
    )
    if surface_error > SCORE_TOLERANCE:
        raise AuditStopError("observed score surface differs from independent reconstruction")
    expected_screen_shape = [99, 765]
    if (
        cached_decision.get("computation_complete") is not True
        or cached_decision.get("screen_reference_shape") != expected_screen_shape
        or cached_decision.get("effect_reference_shape") != [765, 999]
        or cached_decision.get("valid_effect_tables")
        != int(np.sum(references.effect_usable))
    ):
        raise AuditStopError("cached decision reference-cache binding changed")
    raw_case_id = metadata.get("case_id")
    if raw_case_id is not None and (not isinstance(raw_case_id, str) or not raw_case_id):
        raise AuditStopError("history case_id is invalid")
    expected_case_id = f"history-{history:04d}"
    if raw_case_id is not None and raw_case_id != expected_case_id:
        raise AuditStopError("history case_id does not match history identity")
    case = _cached_case(cached_decision, history, raw_case_id)
    screen_row = _require_mapping(case.get("screen"), "cached screen row")
    decision_row = _require_mapping(case.get("decision"), "cached decision row")

    q_values: FloatArray | None = None
    candidates: tuple[int, ...] = ()
    node_p: dict[int, float] = {}
    p_bb = 1.0
    declared = False
    screen_reason: str | None
    decision_reason: str | None
    if not references.screen_usable.all():
        screen_status = "missing_screen_table"
        screen_reason = "shared screen table absent, incomplete or invalid"
        decision_status = "abstain_missing_screen_table"
        decision_reason = screen_reason
    elif not finite.all():
        screen_status = "no_fit"
        screen_reason = "nonfinite or invalid observed screen"
        decision_status = "abstain_no_fit"
        decision_reason = "a required fit failed"
    else:
        q_values = np.asarray(
            [
                inclusive_rank(
                    local_discrepancy(cast(Sequence[float], direct_surface), node),
                    references.screen_statistics[node],
                )
                for node in range(765)
            ],
            dtype=np.float64,
        )
        candidates = tuple(int(value) for value in np.flatnonzero(q_values > 0.01))
        screen_status = "ready" if candidates else "empty"
        screen_reason = None if candidates else "empty nuisance set"
        if not candidates:
            decision_status = "abstain_empty"
            decision_reason = screen_reason
        elif main_audit.get("release_blocked") is True:
            raise AuditStopError("main audit is release-blocked")
        elif main_audit.get("declaration_pair_valid") is not True:
            decision_status = "abstain_no_fit"
            decision_reason = "a required fit failed"
        elif any(not references.effect_usable[node] for node in candidates):
            decision_status = "abstain_no_fit"
            decision_reason = "an effect reference fit failed"
        else:
            observed_t = _finite(main_audit.get("adjusted_statistic"))
            if observed_t is None or observed_t < -1e-10:
                decision_status = "abstain_no_fit"
                decision_reason = "a required fit failed"
            else:
                node_p = {
                    node: inclusive_rank(observed_t, references.effect_statistics[node])
                    for node in candidates
                }
                p_bb = min(1.0, 0.01 + max(node_p.values()))
                declared = p_bb <= 0.05
                decision_status = "declared" if declared else "not_declared"
                decision_reason = None

    if screen_row.get("status") != screen_status:
        raise AuditStopError("cached screen status changed")
    stored_candidates = screen_row.get("candidates", screen_row.get("candidate_indices", ()))
    _compare_sequence(stored_candidates, candidates, "cached screen candidates")
    if q_values is None:
        if screen_row.get("q_values") not in (None, []):
            raise AuditStopError("cached screen q-values should be unavailable")
    else:
        _compare_float_vector(screen_row.get("q_values"), q_values, "cached screen q-values")
    if screen_row.get("reason") != screen_reason:
        raise AuditStopError("cached screen reason changed")
    if decision_row.get("status") != decision_status:
        raise AuditStopError("cached decision status changed")
    stored_p = decision_row.get("p_value", decision_row.get("p_BB"))
    _compare_optional_numeric(stored_p, p_bb, "cached Berger-Boos p-value")
    if decision_row.get("declared") is not declared:
        raise AuditStopError("cached declaration changed")
    decision_candidates = decision_row.get("candidate_indices", ())
    _compare_sequence(decision_candidates, candidates, "cached decision candidates")
    if decision_row.get("reason") != decision_reason:
        raise AuditStopError("cached abstention reason changed")
    stored_node_p = decision_row.get("node_pvalues", decision_row.get("node_p", ()))
    if isinstance(stored_node_p, Mapping):
        normalized = {int(key): float(value) for key, value in stored_node_p.items()}
    elif isinstance(stored_node_p, Sequence) and not isinstance(stored_node_p, (str, bytes)):
        try:
            normalized = {int(row[0]): float(row[1]) for row in stored_node_p}
        except (IndexError, TypeError, ValueError) as error:
            raise AuditStopError("cached node p-values are malformed") from error
    else:
        raise AuditStopError("cached node p-values are malformed")
    if normalized != node_p:
        raise AuditStopError("cached node p-values changed")
    if screen_row.get("case_id") != decision_row.get("case_id"):
        raise AuditStopError("cached screen and decision case identities differ")
    numerical_status = (
        "valid" if decision_status in {"declared", "not_declared"} else "terminal_invalid"
    )
    return _receipt(
        "history_screen_decision",
        numerical_status=numerical_status,
        counts={
            "screen_nodes": 765,
            "retained_nodes": len(candidates),
            "effect_ranks": len(node_p),
        },
        maxima={"observed_surface_nats": surface_error, "rank_probability": 0.0},
        binding={
            **_artifact_binding(metadata, arrays),
            "observed_surface": array_binding(surface),
            "cached_decision_sha256": canonical_sha256(cached_decision),
            "reference_cache_sha256": canonical_sha256(references.binding),
            "main_record_sha256": main_audit.get("main_record_sha256"),
        },
        details={
            "history_index": history,
            "screen_status": screen_status,
            "decision_status": decision_status,
            "retained_nodes": list(candidates),
            "p_BB": p_bb,
            "declared": declared,
            "reason": decision_reason,
        },
    )


def audit_history_screen_decision(
    metadata: Mapping[str, Any],
    arrays: Mapping[str, Any],
    stored_surface: Any,
    cached_decision: Mapping[str, Any],
    main_audit: Mapping[str, Any],
    references: ReferenceCache,
    resources: AuditResources,
) -> dict[str, Any]:
    try:
        return _audit_history_screen_decision(
            metadata,
            arrays,
            stored_surface,
            cached_decision,
            main_audit,
            references,
            resources,
        )
    except Exception as error:
        return _blocked_receipt(
            "history_screen_decision",
            error,
            binding={
                **(_artifact_binding(metadata, arrays) if isinstance(arrays, Mapping) else {}),
                "observed_surface": array_binding(stored_surface),
                "cached_decision_sha256": canonical_sha256(cached_decision),
                "reference_cache_sha256": canonical_sha256(references.binding),
                "main_record_sha256": main_audit.get("main_record_sha256"),
            },
        )


def _profiles_for_legacy_auditor(profiles: Mapping[str, Any]) -> dict[str, Any]:
    """Adapt only the older auditor's unavailable sentinel, never its scores."""
    output: dict[str, Any] = {}
    for name, raw in profiles.items():
        row = dict(_require_mapping(raw, f"diagnostic profile {name}"))
        if row.get("grid") == [] and row.get("values") == []:
            row["statuses_converged"] = False
            warnings = row.get("warnings")
            if not isinstance(warnings, Sequence) or isinstance(warnings, (str, bytes)):
                raise AuditStopError(f"unavailable profile {name} has invalid warnings")
            reason = str(warnings[0]) if len(warnings) == 1 else "missing reason"
            row["warnings"] = [f"diagnostic unavailable: {reason}"]
        output[str(name)] = row
    return output


def _audit_history_diagnostics(
    metadata: Mapping[str, Any],
    arrays: Mapping[str, Any],
    main: Mapping[str, Any],
    diagnostics: Mapping[str, Any],
    resources: AuditResources,
) -> dict[str, Any]:
    _validate_truth_and_seeds(metadata)
    values = _validate_array_schema(arrays, resources)
    _validate_identity_record(diagnostics, metadata, schema=DIAGNOSTIC_SCHEMA)
    main_hash = canonical_sha256(main)
    if diagnostics.get("main_binding_sha256") != main_hash:
        raise AuditStopError("diagnostics changed the persisted main-fit binding")
    fits = _require_mapping(main.get("fits"), "diagnostic main fits")
    if diagnostics.get("main_fits_unchanged") != fits:
        raise AuditStopError("diagnostics changed a persisted main fit")
    profiles = _require_mapping(diagnostics.get("profiles"), "diagnostic profiles")
    lattice = _require_mapping(diagnostics.get("lattice"), "diagnostic lattice")
    profile = _audit_profiles(
        _profiles_for_legacy_auditor(profiles),
        fits,
        resources.bank,
        resources.context,
        np.asarray(values["prey_counts"], dtype=np.int64),
        np.asarray(values["predator_counts"], dtype=np.int64),
    )
    coarse = _audit_coarse_grid(
        lattice,
        fits,
        resources.bank,
        resources.context,
        np.asarray(values["prey_counts"], dtype=np.int64),
        np.asarray(values["predator_counts"], dtype=np.int64),
    )
    stored_profile_gaps = _require_mapping(
        diagnostics.get("profile_main_gaps"), "stored profile/main gaps"
    )
    for name, expected in profile["main_gaps"].items():
        _compare_optional_numeric(
            stored_profile_gaps.get(name), expected, f"stored profile/main gap {name}"
        )
    if diagnostics.get("profile_statuses_converged") != profile["statuses_converged"]:
        raise AuditStopError("stored profile convergence summary changed")
    lattice_check = _require_mapping(
        diagnostics.get("lattice_main_check"), "stored lattice/main check"
    )
    stored_lattice_gaps = _require_mapping(
        lattice_check.get("gaps"), "stored lattice/main gaps"
    )
    for name, expected in coarse["main_fit_gaps"].items():
        _compare_optional_numeric(
            stored_lattice_gaps.get(name), expected, f"stored lattice/main gap {name}"
        )
    if lattice_check.get("passed") is not coarse["diagnostic_passed"]:
        raise AuditStopError("stored lattice/main pass flag changed")
    if _finite(lattice_check.get("tolerance")) != STATISTIC_TOLERANCE:
        raise AuditStopError("stored lattice/main tolerance changed")
    numeric_valid = bool(profile["diagnostic_passed"] and coarse["diagnostic_passed"])
    return _receipt(
        "history_diagnostics",
        numerical_status="valid" if numeric_valid else "terminal_invalid",
        counts={"profile_points": PROFILE_POINTS, "lattice_points": LATTICE_POINTS},
        maxima={
            "profile_score_nats": float(profile["maximum_score_abs_error"]),
            "lattice_score_nats": float(coarse["maximum_score_abs_error"]),
        },
        binding={
            **_artifact_binding(metadata, arrays),
            "main_sha256": main_hash,
            "diagnostics_sha256": canonical_sha256(diagnostics),
        },
        details={
            "history_index": metadata["history_index"],
            "profiles_diagnostic_passed": profile["diagnostic_passed"],
            "lattice_diagnostic_passed": coarse["diagnostic_passed"],
            "profile_statuses_converged": profile["statuses_converged"],
            "profile_main_gaps": profile["main_gaps"],
            "lattice_main_gaps": coarse["main_fit_gaps"],
        },
    )


def audit_history_diagnostics(
    metadata: Mapping[str, Any],
    arrays: Mapping[str, Any],
    main: Mapping[str, Any],
    diagnostics: Mapping[str, Any],
    resources: AuditResources,
) -> dict[str, Any]:
    try:
        return _audit_history_diagnostics(metadata, arrays, main, diagnostics, resources)
    except Exception as error:
        return _blocked_receipt(
            "history_diagnostics",
            error,
            binding={
                **(_artifact_binding(metadata, arrays) if isinstance(arrays, Mapping) else {}),
                "main_sha256": canonical_sha256(main),
                "diagnostics_sha256": canonical_sha256(diagnostics),
            },
        )


def _maximum_abs_difference(left: Any, right: Any, label: str) -> float:
    try:
        first = np.asarray(left, dtype=np.float64)
        second = np.asarray(right, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise AuditStopError(f"{label} is not numeric") from error
    if first.shape != second.shape or not np.isfinite(first).all() or not np.isfinite(second).all():
        raise AuditStopError(f"{label} has a wrong shape or nonfinite value")
    return float(np.max(np.abs(first - second))) if first.size else 0.0


def _audit_history_holdout(
    metadata: Mapping[str, Any],
    arrays: Mapping[str, Any],
    main: Mapping[str, Any],
    holdout: Mapping[str, Any],
    resources: AuditResources,
) -> dict[str, Any]:
    _validate_truth_and_seeds(metadata)
    values = _validate_array_schema(arrays, resources)
    _validate_identity_record(holdout, metadata, schema=HOLDOUT_SCHEMA)
    main_hash = canonical_sha256(main)
    if holdout.get("main_binding_sha256") != main_hash:
        raise AuditStopError("holdout scores changed the persisted main-fit binding")
    fits = _require_mapping(main.get("fits"), "holdout main fits")
    models = _require_mapping(holdout.get("models"), "holdout models")
    if set(fits) != set(MODEL_NAMES) or set(models) != set(MODEL_NAMES):
        raise AuditStopError("holdout model set changed")
    mask = np.asarray(resources.context.training, dtype=bool)
    expected_sites = list(np.asarray(resources.context.site_ids)[~mask])
    cluster_array = np.asarray(resources.context.cluster_ids)[~mask]
    expected_clusters = sorted(set(str(value) for value in cluster_array))
    if len(expected_sites) != HOLDOUT_SITE_COUNT or len(expected_clusters) != 8:
        raise AuditStopError("public holdout partition changed")
    prey = np.asarray(values["prey_counts"], dtype=np.int64)
    predator = np.asarray(values["predator_counts"], dtype=np.int64)
    totals: dict[str, float | None] = {}
    maximum = 0.0
    available = 0
    for model in MODEL_NAMES:
        fit = _require_mapping(fits[model], f"holdout fit {model}")
        if set(fit) != FIT_KEYS:
            raise AuditStopError(f"holdout fit {model} schema changed")
        row = _require_mapping(models[model], f"holdout result {model}")
        point = _fit_point(fit)
        converged = _fit_status(fit) == "converged"
        expected_available = (
            point is not None
            and converged
            and _finite(fit.get("raw_logjoint")) is not None
        )
        status = str(row.get("status"))
        if not expected_available:
            if status != "unavailable":
                raise AuditStopError(f"holdout model {model} should be unavailable")
            totals[model] = None
            continue
        if status != "available" or point is None:
            raise AuditStopError(f"holdout model {model} should be available")
        direct = direct_point_score(resources.bank, resources.context, prey, predator, point)
        site = np.asarray(direct["holdout_conditional_prey_site"], dtype=np.float64)
        total = float(np.sum(site, dtype=np.float64))
        mean = float(np.mean(site, dtype=np.float64))
        clusters = {
            cluster: float(np.sum(site[np.asarray(cluster_array, dtype=str) == cluster]))
            for cluster in expected_clusters
        }
        if row.get("fit_status") != "converged" or row.get("site_ids") != expected_sites:
            raise AuditStopError(f"holdout identity changed for {model}")
        stored_total = _finite(row.get("total_nats"))
        stored_mean = _finite(row.get("mean_nats_per_site"))
        if stored_total is None or stored_mean is None:
            raise AuditStopError(f"holdout total is missing for {model}")
        discrepancies = [abs(stored_total - total), abs(stored_mean - mean)]
        discrepancies.append(
            _maximum_abs_difference(row.get("site_nats"), site, f"holdout site scores {model}")
        )
        stored_clusters = row.get("cluster_nats")
        if not isinstance(stored_clusters, Mapping) or set(stored_clusters) != set(clusters):
            raise AuditStopError(f"holdout clusters changed for {model}")
        discrepancies.extend(
            abs(float(stored_clusters[cluster]) - clusters[cluster]) for cluster in clusters
        )
        row_maximum = max(discrepancies)
        if row_maximum > SCORE_TOLERANCE:
            raise AuditStopError(f"holdout score mismatch for {model}")
        maximum = max(maximum, row_maximum)
        totals[model] = total
        available += 1

    pairs = holdout.get("pair_contrasts")
    if not isinstance(pairs, Sequence) or isinstance(pairs, (str, bytes)) or len(pairs) != 6:
        raise AuditStopError("holdout does not contain six pairwise contrasts")
    observed: dict[tuple[str, str], float | None] = {}
    for row in pairs:
        if not isinstance(row, Mapping):
            raise AuditStopError("holdout pairwise contrast is malformed")
        key = (str(row.get("left")), str(row.get("right")))
        observed[key] = _finite(row.get("left_minus_right_nats"))
    expected_keys = set(itertools.combinations(MODEL_NAMES, 2))
    if set(observed) != expected_keys:
        raise AuditStopError("holdout pairwise identities changed")
    for left, right in expected_keys:
        left_total = totals[left]
        right_total = totals[right]
        expected = None if left_total is None or right_total is None else left_total - right_total
        _compare_optional_numeric(observed[(left, right)], expected, f"holdout pair {left}/{right}")
    return _receipt(
        "history_holdout",
        numerical_status="valid" if available == 4 else "terminal_invalid",
        counts={
            "models": 4,
            "available_models": available,
            "holdout_sites_per_available_model": HOLDOUT_SITE_COUNT,
            "clusters_per_available_model": 8,
            "pairwise_contrasts": 6,
        },
        maxima={"holdout_score_nats": maximum},
        binding={
            **_artifact_binding(metadata, arrays),
            "main_sha256": main_hash,
            "holdout_sha256": canonical_sha256(holdout),
        },
        details={"history_index": metadata["history_index"], "available_models": available},
    )


def audit_history_holdout(
    metadata: Mapping[str, Any],
    arrays: Mapping[str, Any],
    main: Mapping[str, Any],
    holdout: Mapping[str, Any],
    resources: AuditResources,
) -> dict[str, Any]:
    try:
        return _audit_history_holdout(metadata, arrays, main, holdout, resources)
    except Exception as error:
        return _blocked_receipt(
            "history_holdout",
            error,
            binding={
                **(_artifact_binding(metadata, arrays) if isinstance(arrays, Mapping) else {}),
                "main_sha256": canonical_sha256(main),
                "holdout_sha256": canonical_sha256(holdout),
            },
        )


def audit_history(
    metadata: Mapping[str, Any],
    arrays: Mapping[str, Any],
    resources: AuditResources,
    *,
    main: Mapping[str, Any] | None = None,
    stored_surface: Any | None = None,
    cached_decision: Mapping[str, Any] | None = None,
    references: ReferenceCache | None = None,
    diagnostics: Mapping[str, Any] | None = None,
    holdout: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Audit any persisted phases available for one history.

    Main and holdout can be called in separate passes.  No declaration or
    holdout data is required for the input/truth-only audit.
    """
    phases = {"inputs": audit_history_inputs(metadata, arrays, resources)}
    main_receipt: Mapping[str, Any] | None = None
    if main is not None:
        main_receipt = audit_history_main(metadata, arrays, main, resources)
        phases["main"] = main_receipt
    if any(value is not None for value in (stored_surface, cached_decision, references)):
        if (
            stored_surface is None
            or cached_decision is None
            or references is None
            or main_receipt is None
        ):
            phases["screen_decision"] = _blocked_receipt(
                "history_screen_decision",
                AuditStopError("screen audit requires surface, decision, references, and main"),
            )
        else:
            phases["screen_decision"] = audit_history_screen_decision(
                metadata,
                arrays,
                stored_surface,
                cached_decision,
                main_receipt,
                references,
                resources,
            )
    if diagnostics is not None:
        if main is None:
            phases["diagnostics"] = _blocked_receipt(
                "history_diagnostics", AuditStopError("diagnostics require persisted main fits")
            )
        else:
            phases["diagnostics"] = audit_history_diagnostics(
                metadata, arrays, main, diagnostics, resources
            )
    if holdout is not None:
        if main is None:
            phases["holdout"] = _blocked_receipt(
                "history_holdout", AuditStopError("holdout audit requires persisted main fits")
            )
        else:
            phases["holdout"] = audit_history_holdout(
                metadata, arrays, main, holdout, resources
            )
    blocked = any(bool(row.get("release_blocked")) for row in phases.values())
    terminal = any(row.get("numerical_status") == "terminal_invalid" for row in phases.values())
    maxima = {
        key: value
        for phase, row in phases.items()
        for key, value in row.get("max_abs_discrepancy", {}).items()
    }
    numerical_status = (
        "not_assessed" if blocked else "terminal_invalid" if terminal else "valid"
    )
    return {
        "schema": SCHEMA,
        "kind": "history",
        "passed": not blocked,
        "status": "release_blocked" if blocked else "audited_complete",
        "numerical_status": numerical_status,
        "release_blocked": blocked,
        "counts": {
            "phases": len(phases),
            "release_blocked_phases": sum(
                bool(row.get("release_blocked")) for row in phases.values()
            ),
        },
        "max_abs_discrepancy": maxima,
        "artifact_binding": _artifact_binding(metadata, arrays),
        "phases": phases,
    }


def read_history_artifacts(
    metadata_path: Path, arrays_path: Path
) -> tuple[dict[str, Any], dict[str, NDArray[Any]]]:
    """Load a persisted JSON/NPZ history without permitting object arrays."""
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AuditStopError("history metadata JSON is missing or invalid") from error
    if not isinstance(metadata, dict):
        raise AuditStopError("history metadata JSON root is not an object")
    try:
        with np.load(arrays_path, allow_pickle=False) as saved:
            arrays = {name: np.asarray(saved[name]) for name in saved.files}
    except (OSError, ValueError) as error:
        raise AuditStopError("history NPZ is missing or invalid") from error
    return metadata, arrays


__all__ = [
    "CELLS",
    "GENERATOR_ARRAY_NAMES",
    "AuditResources",
    "AuditStopError",
    "ReferenceCache",
    "audit_history",
    "audit_history_diagnostics",
    "audit_history_holdout",
    "audit_history_inputs",
    "audit_history_main",
    "audit_history_screen_decision",
    "canonical_sha256",
    "expected_truth",
    "history_seed",
    "load_audit_resources",
    "make_reference_cache",
    "read_history_artifacts",
    "replay_history",
]
