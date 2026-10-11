#!/usr/bin/env python3
"""Synthesize the registered Goal 062 ten-cell evaluation.

The producer and independent auditor persist one JSON object per history.  This
module is intentionally a small reporting adapter: it does not refit models,
read the raw observations, or regenerate reference tables.  ``summarize_rows``
is the pure entry point used by the parent runner and by the unit tests.

Accepted history-row contract (aliases are retained for the two adapters):

* identity: ``cell_index``, ``cell_label``/``label``, ``background``,
  ``effect``/``h_truth``, ``mean_hazard``/``mu_truth``, and optional
  ``generating_beta``;
* decision: either top-level decision fields, ``decision``, or the producer's
  flattened ``selecteddecision`` with
  ``declared``, ``status``/``declaration_status``, and ``reason``;
* fits: ``fits.adjusted_free_h`` (or ``free_h_fit``), with ``h``, ``beta``,
  ``mu``, ``detection_sd``, and a convergence/status field.  A finite main
  score and an explicit score-replay failure make the h estimate unavailable;
  producer rows may also carry ``main_statuses_converged``, ``nesting_status``,
  ``nesting_gaps``, ``compressed_score_replay``, ``all_main_replays_passed``,
  and audited ``free_h_valid``;
* screening: ``true_node_retained``, ``C_size``/``c_size``, and ``p_BB``/``p_bb``;
* holdout: ``holdout.models`` and/or ``holdout.pair_contrasts``.  Model names
  are ``constant_free_h``, ``adjusted_free_h``, ``constant_h1``, and
  ``adjusted_h1``;
* audit: a top-level ``audit_status``/``independent_audit_status`` or the
  explicit ``audit_status=`` argument to ``summarize_rows``.  A final summary
  is refused unless this is accepted.

The output is JSON-safe and keeps ``None`` for unavailable or inapplicable
quantities.  A summary is conditional on the one registered reference panel;
this adapter does not compute pooled power, confidence-interval coverage, or
an optimization threshold.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from itertools import combinations
from pathlib import Path
from typing import Any, cast

import numpy as np

BOOTSTRAP_ROOT = 2026101102
NAMESPACE = 62
BOOTSTRAP_DOMAIN = 2
REPLICATES = 500
BOOTSTRAP_DRAWS = 2_000
WILSON_Z = 1.959963984540054
H_RECOVERY_LOG_LIMIT = math.log(1.5)
H_BOUNDS = (1.0, 10.0)
MU_BOUNDS = (0.0005, 0.006)
BETA_BOUNDS = (-2.0, 2.0)
SD_BOUNDS = (0.0, 0.4)
MODEL_NAMES = (
    "constant_free_h",
    "adjusted_free_h",
    "constant_h1",
    "adjusted_h1",
)
PRIMARY_SCORE_PAIRS = (
    ("adjusted_free_h", "constant_free_h"),
    ("adjusted_free_h", "adjusted_h1"),
)
# The six persisted pair rows use the existing producer order.  The two
# registered primary means below are reported in their scientific direction
# (adjusted free minus constant free/adjusted null), with sign reversed from a
# persisted pair when necessary.
ALL_SCORE_PAIRS = tuple(combinations(MODEL_NAMES, 2))
REGISTERED_BETWEEN_CELL_PAIRS = (
    ("L3_minus_L1", "L3", "L1"),
    ("H3_minus_H1", "H3", "H1"),
    ("B_L3_minus_B_L1", "B_L3", "B_L1"),
    ("B_H3_minus_B_H1", "B_H3", "B_H1"),
    ("B_L1_minus_L1", "B_L1", "L1"),
    ("B_L3_minus_L3", "B_L3", "L3"),
    ("B_H1_minus_H1", "B_H1", "H1"),
    ("B_H3_minus_H3", "B_H3", "H3"),
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        return value.item()
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _finite(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _first(row: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return default


def _nested(row: Mapping[str, Any], path: Sequence[str], default: Any = None) -> Any:
    value: Any = row
    for name in path:
        if not isinstance(value, Mapping) or name not in value:
            return default
        value = value[name]
    return value


def _status(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def _finite_array(values: Iterable[Any]) -> np.ndarray:
    parsed = [_finite(value) for value in values]
    return np.asarray([value for value in parsed if value is not None], dtype=float)


def wilson_interval(count: int, denominator: int, z: float = WILSON_Z) -> tuple[float, float]:
    """Return a two-sided Wilson interval, including the zero-count case."""

    if denominator <= 0 or count < 0 or count > denominator:
        raise ValueError("Wilson count and denominator are inconsistent")
    p = count / denominator
    z2 = z * z
    centre = (p + z2 / (2 * denominator)) / (1 + z2 / denominator)
    half = (
        z
        / (1 + z2 / denominator)
        * math.sqrt(p * (1 - p) / denominator + z2 / (4 * denominator * denominator))
    )
    return max(0.0, centre - half), min(1.0, centre + half)


def proportion(count: int, denominator: int) -> dict[str, Any]:
    if denominator == 0:
        return {
            "count": int(count),
            "denominator": 0,
            "estimate": None,
            "interval": None,
        }
    low, high = wilson_interval(count, denominator)
    return {
        "count": int(count),
        "denominator": int(denominator),
        "estimate": count / denominator if denominator else None,
        "interval": {"level": 0.95, "method": "wilson", "lower": low, "upper": high},
    }


def _quantile(values: np.ndarray, q: float) -> float | None:
    if values.size == 0:
        return None
    return float(np.quantile(values, q, method="linear"))


def _distribution(values: Iterable[Any]) -> dict[str, Any]:
    array = _finite_array(values)
    return {
        "count": int(array.size),
        "mean": float(np.mean(array)) if array.size else None,
        "median": float(np.median(array)) if array.size else None,
        "quantiles": {str(q): _quantile(array, q) for q in (0.05, 0.25, 0.50, 0.75, 0.95)},
    }


def bootstrap_indices(
    cell_index: int,
    draw: int,
    *,
    sample_size: int = REPLICATES,
    root: int = BOOTSTRAP_ROOT,
) -> np.ndarray:
    """Generate one registered whole-history replacement sample.

    The address is ``[root, 62, 2, cell, draw]``.  The first uint64 from its
    ``SeedSequence`` seeds PCG64, making the generated index vector explicit
    and portable across the synthesis and parent CLI.
    """

    if type(cell_index) is not int or cell_index < 0:
        raise ValueError("cell_index must be a nonnegative integer")
    if type(draw) is not int or draw < 0:
        raise ValueError("draw must be a nonnegative integer")
    if type(sample_size) is not int or sample_size < 1:
        raise ValueError("sample_size must be positive")
    seed = _bootstrap_seed(cell_index, draw, root=root)
    return np.random.default_rng(seed).integers(0, sample_size, size=sample_size, dtype=np.int64)


def _bootstrap_seed(cell_index: int, draw: int, *, root: int = BOOTSTRAP_ROOT) -> int:
    return _address_seed(cell_index, draw, root=root, domain=BOOTSTRAP_DOMAIN)


def _address_seed(cell_index: int, draw: int, *, root: int, domain: int) -> int:
    return int(
        np.random.SeedSequence([root, NAMESPACE, domain, cell_index, draw]).generate_state(
            1, dtype=np.uint64
        )[0]
    )


def bootstrap_ledger(
    *, root: int = BOOTSTRAP_ROOT, draws: int = BOOTSTRAP_DRAWS
) -> list[dict[str, Any]]:
    """Return and validate all registered bootstrap addresses and first seeds."""

    if type(draws) is not int or draws < 1:
        raise ValueError("draws must be positive")
    ledger: list[dict[str, Any]] = []
    for cell in range(10):
        for draw in range(draws):
            address = [root, NAMESPACE, BOOTSTRAP_DOMAIN, cell, draw]
            ledger.append(
                {
                    "cell": cell,
                    "draw": draw,
                    "address": address,
                    "seed": _bootstrap_seed(cell, draw, root=root),
                }
            )
    addresses = {tuple(entry["address"]) for entry in ledger}
    seeds = {entry["seed"] for entry in ledger}
    if len(addresses) != len(ledger) or len(seeds) != len(ledger):
        raise RuntimeError("bootstrap ledger addresses and seeds must be unique")
    if BOOTSTRAP_DOMAIN != 2 or any(entry["address"][2] != 2 for entry in ledger):
        raise RuntimeError("bootstrap ledger must remain in domain 2")
    return ledger


def _bootstrap_metric(
    values: Sequence[Any],
    statistic: Callable[[np.ndarray], float],
    *,
    cell_index: int,
    draws: int,
    sample_size: int,
    root: int,
    indices: Sequence[np.ndarray] | None = None,
) -> dict[str, Any]:
    original = np.asarray(values, dtype=object)
    valid_original = np.asarray([_finite(value) is not None for value in original], dtype=bool)
    valid_count = int(valid_original.sum())
    numeric = np.full(original.shape, np.nan, dtype=float)
    for i, value in enumerate(original):
        parsed = _finite(value)
        if parsed is not None:
            numeric[i] = parsed
    point: float | None = None
    if valid_count:
        try:
            point = float(statistic(numeric[valid_original]))
        except (FloatingPointError, TypeError, ValueError, ZeroDivisionError):
            point = None
    boot: list[float] = []
    undefined = 0
    for draw in range(draws):
        draw_indices = (
            indices[draw]
            if indices is not None
            else bootstrap_indices(cell_index, draw, sample_size=sample_size, root=root)
        )
        if numeric.size == 0:
            undefined += 1
            continue
        try:
            sample = numeric[np.asarray(draw_indices, dtype=np.int64)]
        except IndexError:
            undefined += 1
            continue
        sample = sample[np.isfinite(sample)]
        if sample.size == 0:
            undefined += 1
            continue
        try:
            value = float(statistic(sample))
        except (FloatingPointError, ValueError, ZeroDivisionError):
            value = math.nan
        if not math.isfinite(value):
            undefined += 1
        else:
            boot.append(value)
    if valid_count < 2:
        interval = None
        interval_status = "unavailable_fewer_than_two_valid"
    elif undefined:
        interval = None
        interval_status = "unavailable_undefined_bootstrap_draw"
    else:
        boot_array = np.asarray(boot, dtype=float)
        interval = {
            "level": 0.95,
            "method": "whole_history_percentile",
            "quantile_method": "linear",
            "lower": float(np.quantile(boot_array, 0.025, method="linear")),
            "upper": float(np.quantile(boot_array, 0.975, method="linear")),
        }
        interval_status = "supported"
    return {
        "estimate": point,
        "interval": interval,
        "interval_status": interval_status,
        "valid_count": valid_count,
        "draws": draws,
        "undefined_draws": undefined,
    }


def _mean_statistic(values: np.ndarray) -> float:
    return float(np.mean(values))


def _median_statistic(values: np.ndarray) -> float:
    return float(np.median(values))


def _quantile_statistic(q: float) -> Callable[[np.ndarray], float]:
    return lambda values: float(np.quantile(values, q, method="linear"))


def _accepted_audit(status: Any) -> bool:
    if isinstance(status, Mapping):
        if status.get("release_blocked") is True:
            return False
        for key in ("status", "audit_status", "decision", "outcome"):
            if key in status:
                return _accepted_audit(status[key])
        return False
    return _status(status) in {
        "accepted",
        "audit_accepted",
        "audited_complete",
        "passed",
        "valid",
        "release_accepted",
    }


def _audit_gate(rows: Sequence[Mapping[str, Any]], audit_status: Any) -> Any:
    for row in rows:
        if any(
            row.get(key) is True
            for key in (
                "release_blocked",
                "source_defect",
                "scorer_defect",
                "audit_release_blocked",
            )
        ):
            raise ValueError("source/scorer/audit defect blocks final summary")
        row_status = _first(
            row,
            "audit_status",
            "independent_audit_status",
            "audit",
            default=None,
        )
        if row_status is not None and not _accepted_audit(row_status):
            raise ValueError("independent audit must be accepted before final summary")
    if audit_status is None:
        for row in rows:
            audit_status = _first(
                row,
                "audit_status",
                "independent_audit_status",
                "audit",
                default=None,
            )
            if audit_status is not None:
                break
    if not _accepted_audit(audit_status):
        raise ValueError("independent audit must be accepted before final summary")
    return audit_status


def _decision_class(row: Mapping[str, Any]) -> tuple[str, str | None]:
    decision = row.get("decision")
    if not isinstance(decision, Mapping):
        decision = row.get("selecteddecision")
    if not isinstance(decision, Mapping):
        decision = row.get("selected_decision")
    if not isinstance(decision, Mapping):
        decision = row
    status = _status(_first(decision, "declaration_status", "status", "outcome", default=""))
    declared_value = _first(decision, "declared", "declaration", default=None)
    declared = (
        bool(declared_value)
        if declared_value is not None
        else status
        in {
            "declared",
            "declaration",
        }
    )
    if declared:
        return "declaration", None
    reason = _first(
        decision,
        "abstention_reason",
        "reason",
        "failure_reason",
        default=None,
    )
    if status in {
        "valid_non_declaration",
        "valid_nondeclare",
        "valid_nondeclaration",
        "non_declaration",
        "nondeclare",
        "not_declared",
        "ready_non_declaration",
        "valid",
        "ready",
    } and not str(reason or "").lower().startswith("abstain"):
        return "valid_non_declaration", None
    if not reason:
        reason = status or "unspecified_abstention"
    reason_key = _status(reason)
    if "shared" in reason_key or "table" in reason_key:
        reason_key = "shared_table"
    elif "screen" in reason_key:
        reason_key = "observed_screen"
    elif "fit" in reason_key or "pair" in reason_key:
        reason_key = "observed_fit"
    return "abstention", reason_key


def _fit(row: Mapping[str, Any]) -> Mapping[str, Any]:
    fits = row.get("fits")
    if isinstance(fits, Mapping):
        result = fits.get("adjusted_free_h") or fits.get("free_h") or fits.get("adjusted_free")
        if isinstance(result, Mapping):
            return result
    for key in ("free_h_fit", "adjusted_free_h_fit", "adjusted_free_fit"):
        if isinstance(row.get(key), Mapping):
            return cast(Mapping[str, Any], row[key])
    return {}


def _fit_value(fit: Mapping[str, Any], *names: str) -> Any:
    return _first(fit, *names, default=None)


def _within_registered_bounds(value: Any, bounds: tuple[float, float]) -> bool:
    """Check a stored value against frozen bounds with the registered 8-ULP slack."""

    parsed = _finite(value)
    if parsed is None:
        return False
    lower, upper = bounds
    return parsed >= lower - 8.0 * math.ulp(lower) and parsed <= upper + 8.0 * math.ulp(upper)


def _main_fit(row: Mapping[str, Any], model: str) -> Mapping[str, Any]:
    fits = row.get("fits")
    if isinstance(fits, Mapping) and isinstance(fits.get(model), Mapping):
        return cast(Mapping[str, Any], fits[model])
    return {}


def _model_converged(row: Mapping[str, Any], model: str) -> bool:
    statuses = row.get("main_statuses_converged")
    if isinstance(statuses, Mapping) and model in statuses:
        return statuses[model] is True
    fit = _main_fit(row, model)
    return _status(_fit_value(fit, "numerical_status", "status", "fit_status")) in {
        "converged",
        "valid",
        "available",
        "passed",
        "ok",
    }


def _model_score(row: Mapping[str, Any], model: str) -> float | None:
    return _finite(
        _fit_value(_main_fit(row, model), "raw_logjoint", "main_score", "score", "logjoint")
    )


def _model_replay_passed(row: Mapping[str, Any], model: str) -> bool:
    replay = row.get("compressed_score_replay")
    if isinstance(replay, Mapping) and isinstance(replay.get(model), Mapping):
        record = replay[model]
        difference = _finite(record.get("difference"))
        return (
            record.get("status") == "passed" and difference is not None and abs(difference) <= 1e-8
        )
    fit = _main_fit(row, model)
    value = _first(
        fit, "score_replay_passed", "replay_passed", "main_score_replay_passed", default=None
    )
    if value is not None:
        return value is True
    all_passed = row.get("all_main_replays_passed")
    return all_passed is True


def _fit_is_valid(fit: Mapping[str, Any], row: Mapping[str, Any]) -> bool:
    main_audit_value = row.get("main_audit")
    main_audit: Mapping[str, Any] = (
        main_audit_value if isinstance(main_audit_value, Mapping) else {}
    )
    explicit = _first(
        row,
        "free_h_valid",
        "h_estimate_valid",
        default=_first(main_audit, "effect_recovery_available", default=None),
    )
    if explicit is False:
        return False
    if _first(row, "main_statuses_converged", default=None) is not None and not _model_converged(
        row, "adjusted_free_h"
    ):
        return False
    status = _status(_fit_value(fit, "numerical_status", "status", "fit_status") or "")
    if status and status not in {"converged", "valid", "available", "passed", "ok"}:
        return False
    h = _finite(_fit_value(fit, "h", "h_hat", "effect_hat"))
    if h is None or not _within_registered_bounds(h, H_BOUNDS):
        return False
    score = _finite(_fit_value(fit, "raw_logjoint", "main_score", "score", "logjoint"))
    if score is None:
        return False
    return _model_replay_passed(row, "adjusted_free_h")


def _truth(row: Mapping[str, Any], name: str) -> float | None:
    aliases = {
        "h": ("effect", "h_truth", "true_h"),
        "mu": ("mean_hazard", "mu_truth", "true_mu"),
        "beta": ("generating_beta", "beta_truth", "true_beta"),
        "detection_sd": ("detection_sd", "sd_truth", "true_detection_sd"),
    }
    return _finite(_first(row, *aliases[name], default=None))


def _boundary(value: Any, bounds: tuple[float, float]) -> bool:
    parsed = _finite(value)
    if parsed is None:
        return False
    scale = max(1.0, abs(bounds[0]), abs(bounds[1]))
    tolerance = 16 * np.finfo(float).eps * scale
    return bool(abs(parsed - bounds[0]) <= tolerance or abs(parsed - bounds[1]) <= tolerance)


def _screen_value(row: Mapping[str, Any], *names: str) -> Any:
    screen_value = row.get("screen")
    screen: Mapping[str, Any] = screen_value if isinstance(screen_value, Mapping) else {}
    return _first(row, *names, default=_first(screen, *names, default=None))


def _holdout_models(row: Mapping[str, Any]) -> dict[str, float | None]:
    holdout_value = row.get("holdout")
    holdout: Mapping[str, Any] = holdout_value if isinstance(holdout_value, Mapping) else {}
    source = holdout.get("models", holdout.get("scores", row.get("heldout_models", {})))
    result: dict[str, float | None] = {}
    if isinstance(source, Mapping):
        for model in MODEL_NAMES:
            value = source.get(model)
            if isinstance(value, Mapping):
                value = _first(value, "total_nats", "total_score", "score", default=None)
            result[model] = _finite(value)
    else:
        result = dict.fromkeys(MODEL_NAMES)
    return result


def _holdout_pairs(
    row: Mapping[str, Any], models: Mapping[str, float | None]
) -> dict[str, float | None]:
    holdout_value = row.get("holdout")
    holdout: Mapping[str, Any] = holdout_value if isinstance(holdout_value, Mapping) else {}
    pairs = holdout.get("pair_contrasts", holdout.get("pairs", row.get("pair_contrasts", {})))
    result: dict[str, float | None] = {}
    if isinstance(pairs, Mapping):
        for left, right in ALL_SCORE_PAIRS:
            key = f"{left}_minus_{right}"
            value = pairs.get(key)
            if value is None:
                value = pairs.get(f"{left}-{right}")
            if isinstance(value, Mapping):
                value = _first(value, "left_minus_right_nats", "contrast", "value", default=None)
            result[key] = _finite(value)
    elif isinstance(pairs, Sequence) and not isinstance(pairs, (str, bytes)):
        for item in pairs:
            if not isinstance(item, Mapping):
                continue
            left, right = str(item.get("left")), str(item.get("right"))
            key = f"{left}_minus_{right}"
            if (left, right) in ALL_SCORE_PAIRS:
                result[key] = _finite(
                    _first(item, "left_minus_right_nats", "contrast", "value", default=None)
                )
    for left, right in ALL_SCORE_PAIRS:
        key = f"{left}_minus_{right}"
        left_value = models.get(left)
        right_value = models.get(right)
        result.setdefault(
            key,
            None if left_value is None or right_value is None else float(left_value - right_value),
        )
    return result


def _summary_metric(
    values: Sequence[Any],
    statistic: Callable[[np.ndarray], float],
    *,
    cell_index: int,
    draws: int,
    sample_size: int,
    root: int,
    indices: Sequence[np.ndarray],
) -> dict[str, Any]:
    return _bootstrap_metric(
        values,
        statistic,
        cell_index=cell_index,
        draws=draws,
        sample_size=sample_size,
        root=root,
        indices=indices,
    )


def _bootstrap_distribution(
    values: Sequence[Any],
    *,
    cell_index: int,
    draws: int,
    sample_size: int,
    root: int,
    indices: Sequence[np.ndarray],
) -> dict[str, Any]:
    """Bootstrap mean, median and Type-7 quantiles on one endpoint."""

    result: dict[str, Any] = {
        "mean": _summary_metric(
            values,
            _mean_statistic,
            cell_index=cell_index,
            draws=draws,
            sample_size=sample_size,
            root=root,
            indices=indices,
        ),
        "median": _summary_metric(
            values,
            _median_statistic,
            cell_index=cell_index,
            draws=draws,
            sample_size=sample_size,
            root=root,
            indices=indices,
        ),
    }
    for q in (0.05, 0.25, 0.50, 0.75, 0.95):
        result[f"quantile_{q:.2f}"] = _summary_metric(
            values,
            _quantile_statistic(q),
            cell_index=cell_index,
            draws=draws,
            sample_size=sample_size,
            root=root,
            indices=indices,
        )
    return result


def _status_counts(values: Iterable[Any]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for value in values:
        counts[_status(value) or "missing"] += 1
    return dict(sorted(counts.items()))


def _numerical_aggregation(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    per_model: dict[str, Any] = {}
    for model in MODEL_NAMES:
        fit_statuses = [
            _fit_value(_main_fit(row, model), "numerical_status", "status", "fit_status")
            for row in rows
        ]
        scores = [_model_score(row, model) for row in rows]
        replay = [_model_replay_passed(row, model) for row in rows]
        warnings = [_first(_main_fit(row, model), "warnings", default=()) or () for row in rows]
        per_model[model] = {
            "status_counts": _status_counts(fit_statuses),
            "converged_count": sum(_model_converged(row, model) for row in rows),
            "nonconverged_count": sum(not _model_converged(row, model) for row in rows),
            "finite_score_count": sum(value is not None for value in scores),
            "nonfinite_score_count": sum(value is None for value in scores),
            "score_replay_passed_count": sum(replay),
            "score_replay_failed_count": sum(not value for value in replay),
            "warning_count": sum(
                len(value) if isinstance(value, Sequence) else 0 for value in warnings
            ),
        }
    nesting_statuses: dict[str, Any] = {}
    nesting_gaps: dict[str, Any] = {}
    for family in ("constant", "adjusted"):
        nesting_statuses[family] = _status_counts(
            _nested(row, ("nesting_status", family), default="missing") for row in rows
        )
        nesting_gaps[family] = _distribution(
            _nested(row, ("nesting_gaps", family), default=None) for row in rows
        )
    return {
        "models": per_model,
        "nesting_status": nesting_statuses,
        "nesting_gaps": nesting_gaps,
        "all_main_replays_passed_count": sum(
            row.get("all_main_replays_passed") is True for row in rows
        ),
        "all_main_replays_failed_count": sum(
            row.get("all_main_replays_passed") is False for row in rows
        ),
    }


def _null_miscalibration_flag(
    background: str | None,
    effect: float | None,
    declaration: Mapping[str, Any],
) -> dict[str, Any]:
    if background == "B100-A":
        return {
            "status": "excluded_B100-A",
            "flagged": None,
            "criterion": "exact-family h=1 only",
        }
    if background != "exact" or effect != 1.0:
        return {
            "status": "not_registered_null",
            "flagged": None,
            "criterion": "exact-family h=1 only",
        }
    interval = declaration.get("interval")
    lower = _finite(interval.get("lower")) if isinstance(interval, Mapping) else None
    flagged = lower is not None and lower > 0.05
    return {
        "status": "flagged" if flagged else "not_flagged",
        "flagged": flagged,
        "criterion": "declaration Wilson 95% lower bound > 0.05",
        "threshold": 0.05,
        "declaration_interval": interval,
    }


def _cell_summary(
    rows: Sequence[Mapping[str, Any]],
    *,
    cell_index: int,
    label: str,
    expected_replicates: int,
    bootstrap_draws: int,
    bootstrap_root: int,
) -> dict[str, Any]:
    if len(rows) != expected_replicates:
        raise ValueError(f"cell {label} has {len(rows)} rows, expected {expected_replicates}")
    replicate_ids = [_first(row, "replicate", default=None) for row in rows]
    if any(type(value) is not int for value in replicate_ids) or set(replicate_ids) != set(
        range(expected_replicates)
    ):
        raise ValueError(f"cell {label} does not contain each registered replicate exactly once")
    rows = sorted(rows, key=lambda row: int(_first(row, "replicate", default=0)))
    backgrounds = {_first(row, "background", "background_family", default=None) for row in rows}
    background = next(iter(backgrounds - {None}), None)
    effect = _truth(rows[0], "h")
    mu_truth = _truth(rows[0], "mu")
    beta_truth = _truth(rows[0], "beta")
    indices = [
        bootstrap_indices(cell_index, draw, sample_size=expected_replicates, root=bootstrap_root)
        for draw in range(bootstrap_draws)
    ]
    classes = [_decision_class(row) for row in rows]
    declaration = sum(kind == "declaration" for kind, _ in classes)
    valid_non_declaration = sum(kind == "valid_non_declaration" for kind, _ in classes)
    abstentions = sum(kind == "abstention" for kind, _ in classes)
    reasons = Counter(reason for kind, reason in classes if kind == "abstention")
    reasons.update({key: 0 for key in ("observed_fit", "observed_screen", "shared_table")})

    fits = [_fit(row) for row in rows]
    valid_h = [_fit_is_valid(fit, row) for fit, row in zip(fits, rows, strict=True)]
    h_values = [
        _finite(_fit_value(fit, "h", "h_hat", "effect_hat")) if valid else None
        for fit, valid in zip(fits, valid_h, strict=True)
    ]
    log_errors = [
        math.log(h_hat / effect) if h_hat is not None and effect not in (None, 0) else None
        for h_hat in h_values
    ]
    abs_log_errors = [abs(value) if value is not None else None for value in log_errors]
    within = [value is not None and value < H_RECOVERY_LOG_LIMIT for value in abs_log_errors]
    outside = [value is not None and value >= H_RECOVERY_LOG_LIMIT for value in abs_log_errors]
    unavailable = [not valid for valid in valid_h]
    declaration_count = sum(
        value for value, (kind, _) in zip(within, classes, strict=True) if kind == "declaration"
    )
    recovery = {
        "within_1_5_fold": proportion(sum(within), expected_replicates),
        "valid_outside_1_5_fold": proportion(sum(outside), expected_replicates),
        "unavailable": proportion(sum(unavailable), expected_replicates),
        "partition_check": sum(within) + sum(outside) + sum(unavailable) == expected_replicates,
    }
    declaration_recovery = {
        "selected_label": "recovery_within_1_5_fold_among_declarations",
        "denominator": declaration,
        "count": declaration_count,
        "estimate": (declaration_count / declaration if declaration else None),
    }
    # A Wilson interval is useful for this selection diagnostic but is undefined
    # when no declaration occurred; it is deliberately labelled separately.
    if declaration:
        declaration_recovery["interval"] = {
            **dict(
                zip(
                    ("lower", "upper"),
                    wilson_interval(declaration_count, declaration),
                    strict=True,
                )
            ),
            "level": 0.95,
            "method": "wilson",
        }
    else:
        declaration_recovery["interval"] = None

    valid_log = [value for value in log_errors if value is not None]
    continuous: dict[str, Any] = {
        "signed_log_bias": _summary_metric(
            log_errors,
            _mean_statistic,
            cell_index=cell_index,
            draws=bootstrap_draws,
            sample_size=expected_replicates,
            root=bootstrap_root,
            indices=indices,
        ),
        "mean_absolute_log_h_error": _summary_metric(
            abs_log_errors,
            _mean_statistic,
            cell_index=cell_index,
            draws=bootstrap_draws,
            sample_size=expected_replicates,
            root=bootstrap_root,
            indices=indices,
        ),
        "median_absolute_log_h_error": _summary_metric(
            abs_log_errors,
            _median_statistic,
            cell_index=cell_index,
            draws=bootstrap_draws,
            sample_size=expected_replicates,
            root=bootstrap_root,
            indices=indices,
        ),
    }
    for q in (0.05, 0.25, 0.50, 0.75, 0.95):
        continuous[f"absolute_log_h_error_quantile_{q:.2f}"] = _summary_metric(
            abs_log_errors,
            _quantile_statistic(q),
            cell_index=cell_index,
            draws=bootstrap_draws,
            sample_size=expected_replicates,
            root=bootstrap_root,
            indices=indices,
        )
    valid_h_array = np.asarray([value for value in h_values if value is not None], dtype=float)
    lower_boundary = [
        value is not None and _boundary(value, H_BOUNDS) and value <= H_BOUNDS[0]
        for value in h_values
    ]
    upper_boundary = [
        value is not None and _boundary(value, H_BOUNDS) and value >= H_BOUNDS[1]
        for value in h_values
    ]
    boundaries = {
        "h_lower": proportion(sum(lower_boundary), len(valid_h_array)),
        "h_upper": proportion(sum(upper_boundary), len(valid_h_array)),
        "h_any": proportion(
            sum(a or b for a, b in zip(lower_boundary, upper_boundary, strict=True)),
            len(valid_h_array),
        ),
    }

    nuisance: dict[str, Any] = {}
    boundary_counts: dict[str, int] = {}
    for parameter, truth_name, aliases, bounds, label_name in (
        ("mu", "mu", ("mu", "mu_hat"), MU_BOUNDS, "mu_mean_physical_discrepancy"),
        ("beta", "beta", ("beta", "beta_hat"), BETA_BOUNDS, "beta_working_model_error"),
        (
            "detection_sd",
            "detection_sd",
            ("detection_sd", "sd", "detection_sd_hat"),
            SD_BOUNDS,
            "detection_sd_error",
        ),
    ):
        truth = _truth(rows[0], truth_name)
        values = [
            _finite(_fit_value(fit, *aliases)) if valid else None
            for fit, valid in zip(fits, valid_h, strict=True)
        ]
        errors = [
            value - truth if value is not None and truth is not None else None for value in values
        ]
        n_values = sum(value is not None for value in values)
        if parameter == "beta" and background == "B100-A":
            nuisance[parameter] = {
                "truth": None,
                "truth_status": "not_applicable_B100-A",
                "working_model": _distribution(values),
                "error": _distribution([]),
                "error_bootstrap": None,
                "boundary_mass": proportion(
                    sum(_boundary(value, bounds) for value in values), n_values
                ),
                "label": "working_model_only; generating_beta_undefined",
            }
            boundary_counts[parameter] = sum(_boundary(value, bounds) for value in values)
            continue
        nuisance[parameter] = {
            "truth": truth,
            "error": _distribution(errors),
            "error_bootstrap": _bootstrap_distribution(
                errors,
                cell_index=cell_index,
                draws=bootstrap_draws,
                sample_size=expected_replicates,
                root=bootstrap_root,
                indices=indices,
            ),
            "boundary_mass": proportion(
                sum(_boundary(value, bounds) for value in values), n_values
            ),
            "label": label_name,
        }
        boundary_counts[parameter] = sum(_boundary(value, bounds) for value in values)
    if background == "B100-A":
        nuisance["mu"]["label"] = "descriptive_working_model_minus_generating_mean_hazard"
        nuisance["mu"]["physical_discrepancy"] = nuisance["mu"].pop("error")

    main_fit_scores = {
        model: _distribution(
            _finite(
                _fit_value(
                    row.get("fits", {}).get(model, {}), "raw_logjoint", "main_score", "score"
                )
            )
            for row in rows
        )
        for model in MODEL_NAMES
    }
    numerical = _numerical_aggregation(rows)
    numerical_warnings = sum(values["warning_count"] for values in numerical["models"].values())

    true_retention = [
        _screen_value(row, "true_node_retained", "truth_node_retained") for row in rows
    ]
    true_retention_valid = [bool(value) for value in true_retention if value is not None]
    if background == "B100-A":
        retention = {"status": "not_applicable_B100-A", "estimate": None}
    else:
        retention = {
            "status": "reported_exact_only",
            **proportion(sum(true_retention_valid), expected_replicates),
        }

    c_sizes = [_screen_value(row, "C_size", "c_size", "nuisance_set_size") for row in rows]
    p_bb = [_screen_value(row, "p_BB", "p_bb", "p_value") for row in rows]
    c_summary = _distribution(c_sizes)
    p_summary = _distribution(p_bb)

    model_scores = {
        model: [_holdout_models(row).get(model) for row in rows] for model in MODEL_NAMES
    }
    pair_scores = {
        f"{left}_minus_{right}": [
            _holdout_pairs(row, _holdout_models(row)).get(f"{left}_minus_{right}") for row in rows
        ]
        for left, right in ALL_SCORE_PAIRS
    }
    heldout_models: dict[str, Any] = {}
    for model, values in model_scores.items():
        missing = sum(_finite(value) is None for value in values)
        heldout_models[model] = {
            "missing_count": missing,
            "denominator": expected_replicates,
            "mean": _summary_metric(
                values,
                _mean_statistic,
                cell_index=cell_index,
                draws=bootstrap_draws,
                sample_size=expected_replicates,
                root=bootstrap_root,
                indices=indices,
            ),
        }
    heldout_pairs: dict[str, Any] = {}
    for key, values in pair_scores.items():
        heldout_pairs[key] = {
            "missing_count": sum(_finite(value) is None for value in values),
            "denominator": expected_replicates,
            "mean": _summary_metric(
                values,
                _mean_statistic,
                cell_index=cell_index,
                draws=bootstrap_draws,
                sample_size=expected_replicates,
                root=bootstrap_root,
                indices=indices,
            ),
        }
    primary_scores: dict[str, list[float | None]] = {}
    for left, right in PRIMARY_SCORE_PAIRS:
        direct_key = f"{left}_minus_{right}"
        reverse_key = f"{right}_minus_{left}"
        if direct_key in pair_scores:
            primary_scores[direct_key] = pair_scores[direct_key]
        else:
            primary_scores[direct_key] = [
                -value if value is not None else None for value in pair_scores[reverse_key]
            ]
    primary_means = {
        key: {
            "missing_count": sum(_finite(value) is None for value in values),
            "denominator": expected_replicates,
            "mean": _summary_metric(
                values,
                _mean_statistic,
                cell_index=cell_index,
                draws=bootstrap_draws,
                sample_size=expected_replicates,
                root=bootstrap_root,
                indices=indices,
            ),
        }
        for key, values in primary_scores.items()
    }

    point_metrics: dict[str, float | None] = {
        "declaration_probability": declaration / expected_replicates,
        "valid_non_declaration_probability": valid_non_declaration / expected_replicates,
        "abstention_probability": abstentions / expected_replicates,
        "recovery_within_1_5_fold_probability": sum(within) / expected_replicates,
        "valid_outside_1_5_fold_probability": sum(outside) / expected_replicates,
        "h_unavailable_probability": sum(unavailable) / expected_replicates,
    }
    declaration_summary = proportion(declaration, expected_replicates)
    return {
        "cell_index": cell_index,
        "cell_label": label,
        "background": background,
        "truth": {
            "effect_h": effect,
            "mean_hazard_mu": mu_truth,
            "generating_beta": None if background == "B100-A" else beta_truth,
            "detection_sd": _truth(rows[0], "detection_sd"),
        },
        "n_histories": expected_replicates,
        "denominator": expected_replicates,
        "outcomes": {
            "declaration": declaration_summary,
            "valid_non_declaration": proportion(valid_non_declaration, expected_replicates),
            "abstention": proportion(abstentions, expected_replicates),
            "abstention_reasons": {
                reason: proportion(count, expected_replicates)
                for reason, count in sorted(reasons.items())
            },
        },
        "h_recovery": recovery,
        "recovery_among_declarations": declaration_recovery,
        "valid_h_n": len(valid_log),
        "continuous": continuous,
        "boundaries": boundaries,
        "nuisance": nuisance,
        "nuisance_boundary_counts": boundary_counts,
        "main_fit_scores": main_fit_scores,
        "numerical_warnings": numerical_warnings,
        "numerical_aggregation": numerical,
        "true_grid_retention": retention,
        "C_size": c_summary,
        "p_BB": p_summary,
        "heldout": {
            "models": heldout_models,
            "pair_contrasts": heldout_pairs,
            "primary_pairs": [f"{left}_minus_{right}" for left, right in PRIMARY_SCORE_PAIRS],
            "primary_means": primary_means,
        },
        "point_metrics": point_metrics,
        "conditional_null_miscalibration": _null_miscalibration_flag(
            background,
            effect,
            declaration_summary,
        ),
        "bootstrap": {
            "root": bootstrap_root,
            "namespace": NAMESPACE,
            "domain": BOOTSTRAP_DOMAIN,
            "address_order": ["root", "namespace", "domain", "cell", "draw"],
            "draws": bootstrap_draws,
            "sample_size": expected_replicates,
            "index_rule": "SeedSequence(address)->first_uint64->PCG64 integers",
        },
    }


def _contrast_metric_value(cell: Mapping[str, Any], metric: str) -> float | None:
    if metric in cell.get("point_metrics", {}):
        return _finite(cell["point_metrics"][metric])
    if metric.startswith("score:"):
        _, model, pair = metric.split(":", 2)
        if model == "model":
            return _finite(_nested(cell, ("heldout", "models", pair, "mean", "estimate")))
        return _finite(_nested(cell, ("heldout", "pair_contrasts", pair, "mean", "estimate")))
    if metric == "signed_log_bias":
        return _finite(_nested(cell, ("continuous", metric, "estimate")))
    if metric == "mean_absolute_log_h_error":
        return _finite(_nested(cell, ("continuous", metric, "estimate")))
    return None


def _between_cell_contrasts(
    cells: Mapping[str, Mapping[str, Any]],
    rows_by_label: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    expected_replicates: int,
    draws: int,
    root: int,
) -> list[dict[str, Any]]:
    metrics = (
        "declaration_probability",
        "valid_non_declaration_probability",
        "abstention_probability",
        "recovery_within_1_5_fold_probability",
        "valid_outside_1_5_fold_probability",
        "h_unavailable_probability",
        "signed_log_bias",
        "mean_absolute_log_h_error",
        *(f"score:model:{model}" for model in MODEL_NAMES),
        *(f"score:pair:{left}_minus_{right}" for left, right in ALL_SCORE_PAIRS),
    )
    result: list[dict[str, Any]] = []
    for label, left_label, right_label in REGISTERED_BETWEEN_CELL_PAIRS:
        if left_label not in cells or right_label not in cells:
            continue
        left_rows = rows_by_label[left_label]
        right_rows = rows_by_label[right_label]
        if len(left_rows) != expected_replicates or len(right_rows) != expected_replicates:
            raise ValueError("between-cell contrasts require complete source cells")
        left_indices = [
            bootstrap_indices(
                int(cells[left_label]["cell_index"]),
                draw,
                sample_size=expected_replicates,
                root=root,
            )
            for draw in range(draws)
        ]
        right_indices = [
            bootstrap_indices(
                int(cells[right_label]["cell_index"]),
                draw,
                sample_size=expected_replicates,
                root=root,
            )
            for draw in range(draws)
        ]
        # Registered contrasts use independent cell resamples at each draw.
        for metric in metrics:
            left_values = _raw_metric_values(left_rows, metric)
            right_values = _raw_metric_values(right_rows, metric)
            point_left = _contrast_metric_value(cells[left_label], metric)
            point_right = _contrast_metric_value(cells[right_label], metric)
            point = (
                point_left - point_right
                if point_left is not None and point_right is not None
                else None
            )
            left_valid_count = int(_finite_array(left_values).size)
            right_valid_count = int(_finite_array(right_values).size)
            boot: list[float] = []
            undefined = 0
            for draw in range(draws):
                lv = np.asarray(left_values, dtype=object)[left_indices[draw]]
                rv = np.asarray(right_values, dtype=object)[right_indices[draw]]
                lv = _finite_array(lv)
                rv = _finite_array(rv)
                if lv.size == 0 or rv.size == 0:
                    undefined += 1
                    continue
                value = float(np.mean(lv) - np.mean(rv))
                if math.isfinite(value):
                    boot.append(value)
                else:
                    undefined += 1
            result.append(
                {
                    "label": label,
                    "left_cell": left_label,
                    "right_cell": right_label,
                    "metric": metric,
                    "estimate": point,
                    "left_valid_count": left_valid_count,
                    "right_valid_count": right_valid_count,
                    "interval": None
                    if (undefined or point is None or left_valid_count < 2 or right_valid_count < 2)
                    else {
                        "level": 0.95,
                        "method": "independent_cell_whole_history_percentile",
                        "quantile_method": "linear",
                        "lower": float(np.quantile(boot, 0.025, method="linear")),
                        "upper": float(np.quantile(boot, 0.975, method="linear")),
                    },
                    "interval_status": (
                        "unavailable_undefined_bootstrap_draw"
                        if undefined
                        else "unavailable_fewer_than_two_valid"
                        if left_valid_count < 2 or right_valid_count < 2
                        else "supported"
                    ),
                    "undefined_draws": undefined,
                    "bootstrap_root": root,
                    "bootstrap_address_order": ["root", "namespace", "domain", "cell", "draw"],
                    "description": (
                        "descriptive registered between-cell contrast; independent cell resamples"
                    ),
                }
            )
    return result


def _raw_metric_values(rows: Sequence[Mapping[str, Any]], metric: str) -> list[Any]:
    if metric.startswith("score:model:"):
        model = metric.removeprefix("score:model:")
        return [_holdout_models(row).get(model) for row in rows]
    if metric.startswith("score:pair:"):
        pair = metric.removeprefix("score:pair:")
        return [_holdout_pairs(row, _holdout_models(row)).get(pair) for row in rows]
    if metric == "signed_log_bias" or metric == "mean_absolute_log_h_error":
        values: list[Any] = []
        for row in rows:
            fit = _fit(row)
            if not _fit_is_valid(fit, row):
                values.append(None)
                continue
            h_hat = _finite(_fit_value(fit, "h", "h_hat", "effect_hat"))
            truth = _truth(row, "h")
            if h_hat is None or truth in (None, 0):
                values.append(None)
            else:
                error = math.log(h_hat / truth)
                values.append(error if metric == "signed_log_bias" else abs(error))
        return values
    point_metric_map: dict[str, Callable[[Mapping[str, Any]], float | None]] = {
        "declaration_probability": lambda row: (
            1.0 if _decision_class(row)[0] == "declaration" else 0.0
        ),
        "valid_non_declaration_probability": lambda row: (
            1.0 if _decision_class(row)[0] == "valid_non_declaration" else 0.0
        ),
        "abstention_probability": lambda row: (
            1.0 if _decision_class(row)[0] == "abstention" else 0.0
        ),
        "recovery_within_1_5_fold_probability": lambda row: _recovery_indicator(row, "within"),
        "valid_outside_1_5_fold_probability": lambda row: _recovery_indicator(row, "outside"),
        "h_unavailable_probability": lambda row: _recovery_indicator(row, "unavailable"),
    }
    if metric not in point_metric_map:
        return [None] * len(rows)
    return [point_metric_map[metric](row) for row in rows]


def _recovery_indicator(row: Mapping[str, Any], category: str) -> float | None:
    fit = _fit(row)
    if not _fit_is_valid(fit, row):
        return 1.0 if category == "unavailable" else 0.0
    h_hat = _finite(_fit_value(fit, "h", "h_hat", "effect_hat"))
    truth = _truth(row, "h")
    if h_hat is None or truth in (None, 0):
        return 1.0 if category == "unavailable" else 0.0
    outside = abs(math.log(h_hat / truth)) >= H_RECOVERY_LOG_LIMIT
    return float((category == "within" and not outside) or (category == "outside" and outside))


def summarize_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    audit_status: Any = None,
    expected_replicates: int = REPLICATES,
    bootstrap_draws: int = BOOTSTRAP_DRAWS,
    bootstrap_root: int = BOOTSTRAP_ROOT,
) -> dict[str, Any]:
    """Summarize complete per-history rows into the registered machine report."""

    materialized = [dict(row) for row in rows]
    if not materialized or not all(isinstance(row, Mapping) for row in materialized):
        raise ValueError("rows must be a nonempty iterable of mappings")
    if type(expected_replicates) is not int or expected_replicates < 1:
        raise ValueError("expected_replicates must be positive")
    if type(bootstrap_draws) is not int or bootstrap_draws < 1:
        raise ValueError("bootstrap_draws must be positive")
    accepted_status = _audit_gate(materialized, audit_status)
    by_index: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    labels: dict[int, str] = {}
    for row in materialized:
        cell_value = _first(row, "cell_index", "cell", default=None)
        if type(cell_value) is not int:
            raise ValueError("every history row requires integer cell_index")
        label = str(_first(row, "cell_label", "label", default=f"cell_{cell_value}"))
        by_index[cell_value].append(row)
        labels[cell_value] = label
    if set(by_index) != set(range(10)):
        raise ValueError(f"expected registered cell indices 0..9, found {sorted(by_index)}")
    cells: dict[str, dict[str, Any]] = {}
    rows_by_label: dict[str, Sequence[Mapping[str, Any]]] = {}
    for cell_index, cell_rows in sorted(by_index.items()):
        label = labels[cell_index]
        if label in rows_by_label:
            raise ValueError(f"duplicate cell label: {label}")
        cell = _cell_summary(
            cell_rows,
            cell_index=cell_index,
            label=label,
            expected_replicates=expected_replicates,
            bootstrap_draws=bootstrap_draws,
            bootstrap_root=bootstrap_root,
        )
        cells[label] = cell
        rows_by_label[label] = cell_rows
    between = _between_cell_contrasts(
        cells,
        rows_by_label,
        expected_replicates=expected_replicates,
        draws=bootstrap_draws,
        root=bootstrap_root,
    )
    return {
        "schema": "goal062-final-procedure-evaluation-synthesis-v1",
        "audit_status": _jsonable(accepted_status),
        "registered_scope": {
            "cells": 10,
            "histories_per_cell": expected_replicates,
            "bootstrap_draws": bootstrap_draws,
            "bootstrap_root": bootstrap_root,
            "namespace": NAMESPACE,
            "domain": BOOTSTRAP_DOMAIN,
            "wilson_level": 0.95,
            "quantile_method": "linear",
            "no_pooled_power": True,
            "no_confidence_coverage": True,
            "no_optimal_threshold": True,
        },
        "cells": [
            cells[label] for label in sorted(cells, key=lambda value: cells[value]["cell_index"])
        ],
        "between_cell_contrasts": between,
    }


def _read_json_rows(path: Path) -> list[Mapping[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, Mapping):
        for key in ("rows", "histories", "records"):
            if isinstance(value.get(key), list):
                return cast(list[Mapping[str, Any]], value[key])
        return [value]
    if isinstance(value, list):
        return value
    raise ValueError(f"JSON input must contain rows: {path}")


def load_rows(path: Path) -> list[Mapping[str, Any]]:
    """Read JSON/JSONL/CSV rows or recursively collect JSON row files."""

    if path.is_file():
        if path.suffix.lower() in {".json", ".jsonl"}:
            return _read_json_rows(path)
        if path.suffix.lower() == ".csv":
            with path.open(newline="", encoding="utf-8") as handle:
                return list(csv.DictReader(handle))
        raise ValueError(f"unsupported row input: {path}")
    if not path.is_dir():
        raise ValueError(f"row input does not exist: {path}")
    candidates = sorted(path.rglob("*.jsonl")) + sorted(path.rglob("*.json"))
    rows: list[Mapping[str, Any]] = []
    for candidate in candidates:
        try:
            candidate_rows = _read_json_rows(candidate)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
        # Artifact roots also contain manifests, audit receipts, and per-phase
        # records.  Only history-shaped objects belong in this synthesis.
        rows.extend(
            row
            for row in candidate_rows
            if isinstance(row, Mapping)
            and _first(row, "cell_index", "cell", default=None) is not None
            and _first(row, "replicate", default=None) is not None
        )
    if not rows:
        raise ValueError(f"no JSONL/history.json rows found under {path}")
    return rows


def write_summary(result: Mapping[str, Any], output_dir: Path) -> dict[str, str]:
    """Write machine-readable JSON and flat cell/contrast CSV files."""

    output_dir.mkdir(parents=True, exist_ok=False)
    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(_jsonable(result), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    cells = list(result.get("cells", ()))
    cell_path = output_dir / "cell_summary.csv"
    cell_fields = [
        "cell_index",
        "cell_label",
        "background",
        "n_histories",
        "declaration_probability",
        "valid_non_declaration_probability",
        "abstention_probability",
        "recovery_within_1_5_fold_probability",
        "valid_outside_1_5_fold_probability",
        "h_unavailable_probability",
    ]
    with cell_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=cell_fields)
        writer.writeheader()
        for cell in cells:
            point = cell.get("point_metrics", {})
            writer.writerow({field: cell.get(field, point.get(field)) for field in cell_fields})
    contrast_path = output_dir / "between_cell_contrasts.csv"
    contrast_fields = [
        "label",
        "left_cell",
        "right_cell",
        "metric",
        "estimate",
        "interval_status",
        "undefined_draws",
    ]
    with contrast_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=contrast_fields)
        writer.writeheader()
        writer.writerows(
            {field: row.get(field) for field in contrast_fields}
            for row in result.get("between_cell_contrasts", ())
        )
    return {
        "summary_json": str(summary_path),
        "cell_csv": str(cell_path),
        "contrast_csv": str(contrast_path),
    }


write_synthesis = write_summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, required=True, help="JSON, JSONL, CSV, or artifact root"
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--audit-status", type=Path, required=True, help="accepted independent-audit receipt JSON"
    )
    parser.add_argument("--bootstrap-draws", type=int, default=BOOTSTRAP_DRAWS)
    args = parser.parse_args(argv)
    audit_value = json.loads(args.audit_status.read_text(encoding="utf-8"))
    result = summarize_rows(
        load_rows(args.input),
        audit_status=audit_value,
        bootstrap_draws=args.bootstrap_draws,
    )
    paths = write_summary(result, args.output_dir)
    print(json.dumps(paths, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"Goal 062 synthesis failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
