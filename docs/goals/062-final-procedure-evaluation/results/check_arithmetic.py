#!/usr/bin/env python3
"""Independently verify Goal 062 arithmetic from persisted history rows.

This checker deliberately does not import the production synthesis module.  It
reconstructs the registered estimands, PCG64 whole-history bootstrap, and
independent-cell contrasts directly from ``histories.json`` and compares them
with ``summary.json``.  It does not inspect or alter scientific source files.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np


BOOTSTRAP_ROOT = 2026101102
NAMESPACE = 62
BOOTSTRAP_DOMAIN = 2
REPLICATES = 500
BOOTSTRAP_DRAWS = 2_000
WILSON_Z = 1.959963984540054
H_BOUNDS = (1.0, 10.0)
LOG_RECOVERY_LIMIT = math.log(1.5)

MODEL_NAMES = (
    "constant_free_h",
    "adjusted_free_h",
    "constant_h1",
    "adjusted_h1",
)
PAIR_NAMES = tuple(itertools.combinations(MODEL_NAMES, 2))
PRIMARY_PAIRS = (
    ("adjusted_free_h", "constant_free_h"),
    ("adjusted_free_h", "adjusted_h1"),
)
CELL_SPEC = {
    0: ("L1", "exact", 1.0, 0.001),
    1: ("L3", "exact", 3.0, 0.001),
    2: ("L5", "exact", 5.0, 0.001),
    3: ("H1", "exact", 1.0, 0.004),
    4: ("H3", "exact", 3.0, 0.004),
    5: ("H5", "exact", 5.0, 0.004),
    6: ("B_L1", "B100-A", 1.0, 0.001),
    7: ("B_L3", "B100-A", 3.0, 0.001),
    8: ("B_H1", "B100-A", 1.0, 0.004),
    9: ("B_H3", "B100-A", 3.0, 0.004),
}
CELL_CONTRASTS = (
    ("L3_minus_L1", "L3", "L1"),
    ("H3_minus_H1", "H3", "H1"),
    ("B_L3_minus_B_L1", "B_L3", "B_L1"),
    ("B_H3_minus_B_H1", "B_H3", "B_H1"),
    ("B_L1_minus_L1", "B_L1", "L1"),
    ("B_L3_minus_L3", "B_L3", "L3"),
    ("B_H1_minus_H1", "B_H1", "H1"),
    ("B_H3_minus_H3", "B_H3", "H3"),
)
LOG_ENDPOINTS: dict[str, Callable[[np.ndarray], float]] = {
    "signed_log_bias": lambda x: float(np.mean(x)),
    "mean_absolute_log_h_error": lambda x: float(np.mean(x)),
    "median_absolute_log_h_error": lambda x: float(np.median(x)),
    **{
        f"absolute_log_h_error_quantile_{q:.2f}": (
            lambda x, q=q: float(np.quantile(x, q, method="linear"))
        )
        for q in (0.05, 0.25, 0.50, 0.75, 0.95)
    },
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def finite(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def normal_status(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def first(record: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in record:
            return record[key]
    return default


def nested(record: Mapping[str, Any], keys: Sequence[str]) -> Any:
    value: Any = record
    for key in keys:
        if not isinstance(value, Mapping) or key not in value:
            return None
        value = value[key]
    return value


def wilson(count: int, denominator: int) -> tuple[float, float]:
    if denominator <= 0 or count < 0 or count > denominator:
        raise ValueError("invalid Wilson inputs")
    proportion = count / denominator
    z2 = WILSON_Z**2
    scale = 1.0 + z2 / denominator
    midpoint = (proportion + z2 / (2.0 * denominator)) / scale
    radius = WILSON_Z * math.sqrt(
        proportion * (1.0 - proportion) / denominator
        + z2 / (4.0 * denominator**2)
    ) / scale
    return max(0.0, midpoint - radius), min(1.0, midpoint + radius)


def decision_class(row: Mapping[str, Any]) -> tuple[str, str | None]:
    decision = row.get("decision")
    if not isinstance(decision, Mapping):
        decision = row.get("selecteddecision")
    if not isinstance(decision, Mapping):
        decision = row
    status = normal_status(first(decision, "declaration_status", "status", "outcome"))
    stated = first(decision, "declared", "declaration")
    declared = bool(stated) if stated is not None else status in {"declared", "declaration"}
    if declared:
        return "declaration", None
    reason = first(decision, "abstention_reason", "reason", "failure_reason")
    valid_statuses = {
        "valid_non_declaration",
        "valid_nondeclare",
        "valid_nondeclaration",
        "non_declaration",
        "nondeclare",
        "not_declared",
        "ready_non_declaration",
        "valid",
        "ready",
    }
    if status in valid_statuses and not str(reason or "").lower().startswith("abstain"):
        return "valid_non_declaration", None
    key = normal_status(reason or status or "unspecified_abstention")
    if "shared" in key or "table" in key:
        key = "shared_table"
    elif "screen" in key:
        key = "observed_screen"
    elif "fit" in key or "pair" in key:
        key = "observed_fit"
    return "abstention", key


def adjusted_fit(row: Mapping[str, Any]) -> Mapping[str, Any]:
    fits = row.get("fits")
    if isinstance(fits, Mapping) and isinstance(fits.get("adjusted_free_h"), Mapping):
        return fits["adjusted_free_h"]
    return {}


def replay_passed(row: Mapping[str, Any], fit: Mapping[str, Any]) -> bool:
    replay = row.get("compressed_score_replay")
    if isinstance(replay, Mapping) and isinstance(replay.get("adjusted_free_h"), Mapping):
        item = replay["adjusted_free_h"]
        delta = finite(item.get("difference"))
        return item.get("status") == "passed" and delta is not None and abs(delta) <= 1e-8
    stored = first(fit, "score_replay_passed", "replay_passed", "main_score_replay_passed")
    if stored is not None:
        return stored is True
    return row.get("all_main_replays_passed") is True


def independent_h_validity(row: Mapping[str, Any]) -> tuple[bool, list[str]]:
    """Reconstruct h validity while retaining disagreement with the audit flag."""

    fit = adjusted_fit(row)
    failures: list[str] = []
    statuses = row.get("main_statuses_converged")
    if isinstance(statuses, Mapping) and statuses.get("adjusted_free_h") is not True:
        failures.append("main_status_not_converged")
    status = normal_status(first(fit, "numerical_status", "status", "fit_status"))
    if status and status not in {"converged", "valid", "available", "passed", "ok"}:
        failures.append("fit_status_invalid")
    h_hat = finite(first(fit, "h", "h_hat", "effect_hat"))
    lower = H_BOUNDS[0] - 8.0 * math.ulp(H_BOUNDS[0])
    upper = H_BOUNDS[1] + 8.0 * math.ulp(H_BOUNDS[1])
    if h_hat is None or not lower <= h_hat <= upper:
        failures.append("h_nonfinite_or_out_of_bounds")
    if finite(first(fit, "raw_logjoint", "main_score", "score", "logjoint")) is None:
        failures.append("main_score_nonfinite")
    if not replay_passed(row, fit):
        failures.append("score_replay_failed")
    audit_flag = row.get("free_h_valid")
    if audit_flag is not True:
        failures.append("independent_audit_unavailable")
    return not failures, failures


def model_scores(row: Mapping[str, Any]) -> dict[str, float | None]:
    holdout = row.get("holdout")
    if not isinstance(holdout, Mapping):
        return dict.fromkeys(MODEL_NAMES)
    source = holdout.get("models", holdout.get("scores", {}))
    result: dict[str, float | None] = {}
    for model in MODEL_NAMES:
        value = source.get(model) if isinstance(source, Mapping) else None
        if isinstance(value, Mapping):
            value = first(value, "total_nats", "total_score", "score")
        result[model] = finite(value)
    return result


def stored_pairs(row: Mapping[str, Any]) -> dict[tuple[str, str], float | None]:
    holdout = row.get("holdout")
    pairs = holdout.get("pair_contrasts") if isinstance(holdout, Mapping) else None
    result: dict[tuple[str, str], float | None] = {}
    if isinstance(pairs, Sequence) and not isinstance(pairs, (str, bytes)):
        for item in pairs:
            if isinstance(item, Mapping):
                key = (str(item.get("left")), str(item.get("right")))
                result[key] = finite(first(item, "left_minus_right_nats", "contrast", "value"))
    elif isinstance(pairs, Mapping):
        for left, right in PAIR_NAMES:
            value = pairs.get(f"{left}_minus_{right}", pairs.get(f"{left}-{right}"))
            if isinstance(value, Mapping):
                value = first(value, "left_minus_right_nats", "contrast", "value")
            result[(left, right)] = finite(value)
    return result


def seed_for(cell: int, draw: int) -> int:
    address = [BOOTSTRAP_ROOT, NAMESPACE, BOOTSTRAP_DOMAIN, cell, draw]
    return int(np.random.SeedSequence(address).generate_state(1, dtype=np.uint64)[0])


def indices_for(cell: int, draw: int) -> np.ndarray:
    return np.random.default_rng(seed_for(cell, draw)).integers(
        0, REPLICATES, size=REPLICATES, dtype=np.int64
    )


def numeric(values: Sequence[Any]) -> np.ndarray:
    parsed: list[float] = []
    for value in values:
        if isinstance(value, (bool, np.bool_)):
            parsed.append(float(value))
            continue
        number = finite(value)
        parsed.append(math.nan if number is None else number)
    return np.asarray(parsed, dtype=float)


def original_stat(values: np.ndarray, statistic: Callable[[np.ndarray], float]) -> float | None:
    kept = values[np.isfinite(values)]
    return float(statistic(kept)) if kept.size else None


def bootstrap_stat(
    values: np.ndarray,
    statistic: Callable[[np.ndarray], float],
    index_rows: Sequence[np.ndarray],
) -> dict[str, Any]:
    valid_count = int(np.isfinite(values).sum())
    estimate = original_stat(values, statistic)
    draws = np.full(len(index_rows), np.nan, dtype=float)
    undefined = 0
    for draw, index in enumerate(index_rows):
        sample = values[index]
        sample = sample[np.isfinite(sample)]
        if sample.size == 0:
            undefined += 1
            continue
        value = float(statistic(sample))
        if math.isfinite(value):
            draws[draw] = value
        else:
            undefined += 1
    if valid_count < 2:
        status = "unavailable_fewer_than_two_valid"
        interval = None
    elif undefined:
        status = "unavailable_undefined_bootstrap_draw"
        interval = None
    else:
        status = "supported"
        interval = {
            "lower": float(np.quantile(draws, 0.025, method="linear")),
            "upper": float(np.quantile(draws, 0.975, method="linear")),
        }
    return {
        "estimate": estimate,
        "valid_count": valid_count,
        "undefined_draws": undefined,
        "interval_status": status,
        "interval": interval,
        "bootstrap_draw_values": draws,
    }


class Comparator:
    def __init__(self, *, atol: float = 5e-12, rtol: float = 5e-13) -> None:
        self.atol = atol
        self.rtol = rtol
        self.comparisons = 0
        self.max_abs_difference = 0.0
        self.discrepancies: list[dict[str, Any]] = []

    def compare(self, path: str, computed: Any, reported: Any) -> None:
        self.comparisons += 1
        if isinstance(computed, (int, np.integer)) and not isinstance(computed, bool):
            ok = isinstance(reported, (int, np.integer)) and int(computed) == int(reported)
            difference = None
        elif isinstance(computed, (float, np.floating)):
            parsed = finite(reported)
            difference = None if parsed is None else abs(float(computed) - parsed)
            ok = parsed is not None and math.isclose(
                float(computed), parsed, abs_tol=self.atol, rel_tol=self.rtol
            )
            if difference is not None:
                self.max_abs_difference = max(self.max_abs_difference, difference)
        else:
            ok = computed == reported
            difference = None
        if not ok:
            item = {"path": path, "computed": computed, "reported": reported}
            if difference is not None:
                item["absolute_difference"] = difference
            self.discrepancies.append(item)

    def compare_optional_float(self, path: str, computed: float | None, reported: Any) -> None:
        if computed is None:
            self.compare(path, None, reported)
        else:
            self.compare(path, float(computed), reported)


def compare_proportion(
    cmp: Comparator,
    path: str,
    count: int,
    denominator: int,
    reported: Mapping[str, Any],
) -> None:
    low, high = wilson(count, denominator)
    cmp.compare(f"{path}.count", count, reported.get("count"))
    cmp.compare(f"{path}.denominator", denominator, reported.get("denominator"))
    cmp.compare(f"{path}.estimate", count / denominator, reported.get("estimate"))
    cmp.compare(f"{path}.interval.lower", low, nested(reported, ("interval", "lower")))
    cmp.compare(f"{path}.interval.upper", high, nested(reported, ("interval", "upper")))


def compare_bootstrap(
    cmp: Comparator, path: str, calculated: Mapping[str, Any], reported: Mapping[str, Any]
) -> None:
    cmp.compare_optional_float(f"{path}.estimate", calculated["estimate"], reported.get("estimate"))
    cmp.compare(f"{path}.valid_count", calculated["valid_count"], reported.get("valid_count"))
    cmp.compare(
        f"{path}.undefined_draws",
        calculated["undefined_draws"],
        reported.get("undefined_draws"),
    )
    cmp.compare(
        f"{path}.interval_status",
        calculated["interval_status"],
        reported.get("interval_status"),
    )
    for endpoint in ("lower", "upper"):
        value = calculated["interval"][endpoint] if calculated["interval"] else None
        cmp.compare_optional_float(
            f"{path}.interval.{endpoint}", value, nested(reported, ("interval", endpoint))
        )


def raw_cell_metrics(
    rows: Sequence[Mapping[str, Any]],
    validity: Sequence[bool],
    log_errors: Sequence[float | None],
) -> dict[str, np.ndarray]:
    classes = [decision_class(row)[0] for row in rows]
    absolute = [None if value is None else abs(value) for value in log_errors]
    result: dict[str, np.ndarray] = {
        "declaration_probability": numeric([kind == "declaration" for kind in classes]),
        "valid_non_declaration_probability": numeric(
            [kind == "valid_non_declaration" for kind in classes]
        ),
        "abstention_probability": numeric([kind == "abstention" for kind in classes]),
        "recovery_within_1_5_fold_probability": numeric(
            [value is not None and value < LOG_RECOVERY_LIMIT for value in absolute]
        ),
        "valid_outside_1_5_fold_probability": numeric(
            [value is not None and value >= LOG_RECOVERY_LIMIT for value in absolute]
        ),
        "h_unavailable_probability": numeric([not item for item in validity]),
        "signed_log_bias": numeric(log_errors),
        "mean_absolute_log_h_error": numeric(absolute),
    }
    scores_by_row = [model_scores(row) for row in rows]
    for model in MODEL_NAMES:
        result[f"score:model:{model}"] = numeric([scores[model] for scores in scores_by_row])
    for left, right in PAIR_NAMES:
        values = []
        for scores in scores_by_row:
            left_value, right_value = scores[left], scores[right]
            values.append(
                None
                if left_value is None or right_value is None
                else left_value - right_value
            )
        result[f"score:pair:{left}_minus_{right}"] = numeric(values)
    return result


def validate_rows(rows: list[Mapping[str, Any]]) -> dict[int, list[Mapping[str, Any]]]:
    if len(rows) != 10 * REPLICATES:
        raise ValueError(f"expected 5000 rows, found {len(rows)}")
    grouped: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        cell = row.get("cell_index")
        replicate = row.get("replicate")
        if type(cell) is not int or cell not in CELL_SPEC:
            raise ValueError(f"invalid cell index: {cell!r}")
        if type(replicate) is not int or replicate not in range(REPLICATES):
            raise ValueError(f"invalid replicate: {replicate!r}")
        grouped[cell].append(row)
    if set(grouped) != set(CELL_SPEC):
        raise ValueError("missing registered cell")
    for cell, items in grouped.items():
        items.sort(key=lambda row: int(row["replicate"]))
        if [row["replicate"] for row in items] != list(range(REPLICATES)):
            raise ValueError(f"cell {cell} does not contain replicates 0..499 exactly once")
        label, background, effect, mu = CELL_SPEC[cell]
        for row in items:
            observed = (
                row.get("cell_label"),
                row.get("background"),
                finite(first(row, "effect", "h_truth", "true_h")),
                finite(first(row, "mean_hazard", "mu_truth", "true_mu")),
            )
            expected = (label, background, effect, mu)
            if observed != expected:
                raise ValueError(f"registered truth mismatch at cell {cell}: {observed!r}")
    return grouped


def compare_cell(
    cell: int,
    rows: Sequence[Mapping[str, Any]],
    reported: Mapping[str, Any],
    indices: Sequence[np.ndarray],
    cmp: Comparator,
    internal_discrepancies: list[dict[str, Any]],
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    label = CELL_SPEC[cell][0]
    base = f"cells.{label}"
    classes = [decision_class(row) for row in rows]
    status_counts = Counter(kind for kind, _ in classes)
    reasons = Counter(reason for kind, reason in classes if kind == "abstention")
    for reason in ("observed_fit", "observed_screen", "shared_table"):
        reasons.setdefault(reason, 0)
    for name in ("declaration", "valid_non_declaration", "abstention"):
        compare_proportion(
            cmp,
            f"{base}.outcomes.{name}",
            status_counts[name],
            REPLICATES,
            nested(reported, ("outcomes", name)) or {},
        )
    for reason, count in sorted(reasons.items()):
        compare_proportion(
            cmp,
            f"{base}.outcomes.abstention_reasons.{reason}",
            count,
            REPLICATES,
            nested(reported, ("outcomes", "abstention_reasons", reason)) or {},
        )

    validity: list[bool] = []
    log_errors: list[float | None] = []
    audit_disagreement = 0
    for row in rows:
        valid, failures = independent_h_validity(row)
        validity.append(valid)
        structural_failures = [reason for reason in failures if reason != "independent_audit_unavailable"]
        if bool(row.get("free_h_valid")) != (not structural_failures):
            audit_disagreement += 1
            if len(internal_discrepancies) < 100:
                internal_discrepancies.append(
                    {
                        "type": "free_h_valid_vs_reconstructed",
                        "cell": cell,
                        "replicate": row["replicate"],
                        "audit_flag": row.get("free_h_valid"),
                        "reconstructed_failures": structural_failures,
                    }
                )
        fit = adjusted_fit(row)
        h_hat = finite(first(fit, "h", "h_hat", "effect_hat")) if valid else None
        truth = finite(first(row, "effect", "h_truth", "true_h"))
        log_errors.append(
            math.log(h_hat / truth)
            if h_hat is not None and truth is not None and truth > 0
            else None
        )
    absolute = [None if value is None else abs(value) for value in log_errors]
    within = sum(value is not None and value < LOG_RECOVERY_LIMIT for value in absolute)
    outside = sum(value is not None and value >= LOG_RECOVERY_LIMIT for value in absolute)
    unavailable = sum(value is None for value in log_errors)
    for key, count in (
        ("within_1_5_fold", within),
        ("valid_outside_1_5_fold", outside),
        ("unavailable", unavailable),
    ):
        compare_proportion(
            cmp,
            f"{base}.h_recovery.{key}",
            count,
            REPLICATES,
            nested(reported, ("h_recovery", key)) or {},
        )
    cmp.compare(f"{base}.h_recovery.partition_check", True, nested(reported, ("h_recovery", "partition_check")))
    cmp.compare(f"{base}.valid_h_n", REPLICATES - unavailable, reported.get("valid_h_n"))

    declarations = [kind == "declaration" for kind, _ in classes]
    selected_n = sum(declarations)
    selected_recovered = sum(
        declared and value is not None and value < LOG_RECOVERY_LIMIT
        for declared, value in zip(declarations, absolute, strict=True)
    )
    selection = reported.get("recovery_among_declarations", {})
    cmp.compare(f"{base}.recovery_among_declarations.denominator", selected_n, selection.get("denominator"))
    cmp.compare(f"{base}.recovery_among_declarations.count", selected_recovered, selection.get("count"))
    cmp.compare_optional_float(
        f"{base}.recovery_among_declarations.estimate",
        selected_recovered / selected_n if selected_n else None,
        selection.get("estimate"),
    )

    log_arrays = {
        "signed_log_bias": numeric(log_errors),
        **{name: numeric(absolute) for name in LOG_ENDPOINTS if name != "signed_log_bias"},
    }
    bootstrap_draws: dict[str, np.ndarray] = {}
    for endpoint, statistic in LOG_ENDPOINTS.items():
        calculated = bootstrap_stat(log_arrays[endpoint], statistic, indices)
        compare_bootstrap(
            cmp,
            f"{base}.continuous.{endpoint}",
            calculated,
            nested(reported, ("continuous", endpoint)) or {},
        )
        bootstrap_draws[endpoint] = calculated["bootstrap_draw_values"]

    scores_by_row = [model_scores(row) for row in rows]
    pair_values: dict[tuple[str, str], list[float | None]] = {}
    for left, right in PAIR_NAMES:
        values: list[float | None] = []
        for row, scores in zip(rows, scores_by_row, strict=True):
            left_value, right_value = scores[left], scores[right]
            derived = (
                None
                if left_value is None or right_value is None
                else left_value - right_value
            )
            values.append(derived)
            persisted = stored_pairs(row).get((left, right))
            coherent = (derived is None and persisted is None) or (
                derived is not None
                and persisted is not None
                and math.isclose(derived, persisted, abs_tol=5e-12, rel_tol=5e-13)
            )
            if not coherent and len(internal_discrepancies) < 100:
                internal_discrepancies.append(
                    {
                        "type": "stored_holdout_pair_vs_model_difference",
                        "cell": cell,
                        "replicate": row["replicate"],
                        "pair": f"{left}_minus_{right}",
                        "derived": derived,
                        "stored": persisted,
                    }
                )
        pair_values[(left, right)] = values

    for left, right in PRIMARY_PAIRS:
        key = f"{left}_minus_{right}"
        if (left, right) in pair_values:
            values = pair_values[(left, right)]
        else:
            values = [
                None if value is None else -value for value in pair_values[(right, left)]
            ]
        calculated = bootstrap_stat(numeric(values), lambda x: float(np.mean(x)), indices)
        reported_pair = nested(reported, ("heldout", "primary_means", key)) or {}
        cmp.compare(
            f"{base}.heldout.primary_means.{key}.missing_count",
            REPLICATES - calculated["valid_count"],
            reported_pair.get("missing_count"),
        )
        cmp.compare(
            f"{base}.heldout.primary_means.{key}.denominator",
            REPLICATES,
            reported_pair.get("denominator"),
        )
        compare_bootstrap(
            cmp,
            f"{base}.heldout.primary_means.{key}.mean",
            calculated,
            reported_pair.get("mean", {}),
        )

    raw = raw_cell_metrics(rows, validity, log_errors)
    mean_draws: dict[str, np.ndarray] = {}
    for metric, values in raw.items():
        calculated = bootstrap_stat(values, lambda x: float(np.mean(x)), indices)
        mean_draws[metric] = calculated["bootstrap_draw_values"]
    return raw, mean_draws


def compare_contrasts(
    raw_by_label: Mapping[str, Mapping[str, np.ndarray]],
    draws_by_label: Mapping[str, Mapping[str, np.ndarray]],
    reported_rows: Sequence[Mapping[str, Any]],
    cmp: Comparator,
) -> None:
    reported = {
        (row.get("label"), row.get("metric")): row
        for row in reported_rows
        if isinstance(row, Mapping)
    }
    expected_keys: set[tuple[str, str]] = set()
    for contrast, left, right in CELL_CONTRASTS:
        for metric in raw_by_label[left]:
            expected_keys.add((contrast, metric))
            record = reported.get((contrast, metric), {})
            base = f"between_cell_contrasts.{contrast}.{metric}"
            left_values = raw_by_label[left][metric]
            right_values = raw_by_label[right][metric]
            left_valid = left_values[np.isfinite(left_values)]
            right_valid = right_values[np.isfinite(right_values)]
            point = (
                float(np.mean(left_valid) - np.mean(right_valid))
                if left_valid.size and right_valid.size
                else None
            )
            left_draws = draws_by_label[left][metric]
            right_draws = draws_by_label[right][metric]
            contrast_draws = left_draws - right_draws
            undefined = int((~np.isfinite(contrast_draws)).sum())
            supported = (
                point is not None
                and left_valid.size >= 2
                and right_valid.size >= 2
                and undefined == 0
            )
            if undefined:
                status = "unavailable_undefined_bootstrap_draw"
            elif left_valid.size < 2 or right_valid.size < 2:
                status = "unavailable_fewer_than_two_valid"
            else:
                status = "supported"
            cmp.compare_optional_float(f"{base}.estimate", point, record.get("estimate"))
            cmp.compare(f"{base}.left_valid_count", int(left_valid.size), record.get("left_valid_count"))
            cmp.compare(f"{base}.right_valid_count", int(right_valid.size), record.get("right_valid_count"))
            cmp.compare(f"{base}.undefined_draws", undefined, record.get("undefined_draws"))
            cmp.compare(f"{base}.interval_status", status, record.get("interval_status"))
            for endpoint, q in (("lower", 0.025), ("upper", 0.975)):
                value = float(np.quantile(contrast_draws, q, method="linear")) if supported else None
                cmp.compare_optional_float(
                    f"{base}.interval.{endpoint}", value, nested(record, ("interval", endpoint))
                )
    extra = set(reported) - expected_keys
    missing = expected_keys - set(reported)
    cmp.compare("between_cell_contrasts.unexpected_keys", [], sorted(extra))
    cmp.compare("between_cell_contrasts.missing_keys", [], sorted(missing))


def run_check(
    histories_path: Path,
    summary_path: Path,
    bootstrap_ledger_path: Path | None = None,
) -> dict[str, Any]:
    raw_histories = load_json(histories_path)
    if not isinstance(raw_histories, list) or not all(
        isinstance(row, Mapping) for row in raw_histories
    ):
        raise ValueError("histories.json must be a list of mappings")
    histories = list(raw_histories)
    summary = load_json(summary_path)
    if not isinstance(summary, Mapping):
        raise ValueError("summary.json must be a mapping")
    grouped = validate_rows(histories)
    if summary.get("schema") != "goal062-final-procedure-evaluation-synthesis-v1":
        raise ValueError("summary schema is not registered Goal 062 synthesis v1")
    reported_cells = {
        int(cell["cell_index"]): cell
        for cell in summary.get("cells", ())
        if isinstance(cell, Mapping) and type(cell.get("cell_index")) is int
    }
    if set(reported_cells) != set(CELL_SPEC):
        raise ValueError("summary does not contain exactly the ten registered cells")

    ledger_lookup: dict[tuple[int, int], Mapping[str, Any]] | None = None
    if bootstrap_ledger_path is not None:
        ledger = load_json(bootstrap_ledger_path)
        if not isinstance(ledger, list) or len(ledger) != 10 * BOOTSTRAP_DRAWS:
            raise ValueError("bootstrap ledger must contain 20,000 rows")
        ledger_lookup = {}
        for item in ledger:
            if not isinstance(item, Mapping):
                raise ValueError("bootstrap ledger row is not a mapping")
            key = (item.get("cell"), item.get("draw"))
            if key in ledger_lookup:
                raise ValueError(f"duplicate bootstrap ledger key {key}")
            ledger_lookup[key] = item

    cmp = Comparator()
    internal_discrepancies: list[dict[str, Any]] = []
    raw_by_label: dict[str, dict[str, np.ndarray]] = {}
    draws_by_label: dict[str, dict[str, np.ndarray]] = {}
    seeds: set[int] = set()
    stream_mismatches: list[dict[str, Any]] = []
    for cell in range(10):
        index_rows: list[np.ndarray] = []
        for draw in range(BOOTSTRAP_DRAWS):
            seed = seed_for(cell, draw)
            if seed in seeds:
                stream_mismatches.append({"cell": cell, "draw": draw, "reason": "duplicate_seed"})
            seeds.add(seed)
            address = [BOOTSTRAP_ROOT, NAMESPACE, BOOTSTRAP_DOMAIN, cell, draw]
            if ledger_lookup is not None:
                stored = ledger_lookup.get((cell, draw))
                if stored is None or stored.get("address") != address or stored.get("seed") != seed:
                    stream_mismatches.append(
                        {
                            "cell": cell,
                            "draw": draw,
                            "reason": "ledger_mismatch",
                            "computed_address": address,
                            "computed_seed": seed,
                            "reported": stored,
                        }
                    )
            index_rows.append(indices_for(cell, draw))
        raw, draws = compare_cell(
            cell,
            grouped[cell],
            reported_cells[cell],
            index_rows,
            cmp,
            internal_discrepancies,
        )
        label = CELL_SPEC[cell][0]
        raw_by_label[label] = raw
        draws_by_label[label] = draws
    compare_contrasts(
        raw_by_label,
        draws_by_label,
        summary.get("between_cell_contrasts", ()),
        cmp,
    )
    passed = not cmp.discrepancies and not internal_discrepancies and not stream_mismatches
    return {
        "schema": "goal062-independent-arithmetic-check-v1",
        "created_utc": datetime.now(UTC).isoformat(),
        "passed": passed,
        "scientific_review_pending": True,
        "inputs": {
            "histories_path": str(histories_path),
            "histories_sha256": file_sha256(histories_path),
            "summary_path": str(summary_path),
            "summary_sha256": file_sha256(summary_path),
            "bootstrap_ledger_path": (
                str(bootstrap_ledger_path) if bootstrap_ledger_path is not None else None
            ),
            "bootstrap_ledger_sha256": (
                file_sha256(bootstrap_ledger_path) if bootstrap_ledger_path is not None else None
            ),
        },
        "registered_scope": {
            "cells": 10,
            "histories": 5000,
            "histories_per_cell": REPLICATES,
            "bootstrap_streams_reconstructed": 10 * BOOTSTRAP_DRAWS,
            "unique_bootstrap_seeds": len(seeds),
            "between_cell_contrasts": len(CELL_CONTRASTS),
            "between_cell_metrics_each": len(next(iter(raw_by_label.values()))),
            "inference": "conditional on fixed map, design, bank, algorithm, and one reference panel",
        },
        "comparison": {
            "comparisons": cmp.comparisons,
            "max_absolute_difference": cmp.max_abs_difference,
            "tolerances": {"absolute": cmp.atol, "relative": cmp.rtol},
            "discrepancy_count": len(cmp.discrepancies),
            "discrepancies": cmp.discrepancies,
        },
        "internal_history_checks": {
            "discrepancy_count": len(internal_discrepancies),
            "discrepancies": internal_discrepancies,
        },
        "bootstrap_stream_checks": {
            "mismatch_count": len(stream_mismatches),
            "mismatches": stream_mismatches,
        },
        "limitations": [
            "Arithmetic verification is not scientific interpretation or campaign closure.",
            "Intervals retain the registered conditioning on one map and one reference panel.",
            "Recovery among declarations is a selected-subset diagnostic.",
            "Between-cell contrasts compare independent generating regimes and are not causal effects.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--histories", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--bootstrap-ledger", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    result = run_check(
        arguments.histories.resolve(),
        arguments.summary.resolve(),
        arguments.bootstrap_ledger.resolve() if arguments.bootstrap_ledger else None,
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"passed": result["passed"], "output": str(arguments.output)}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
