#!/usr/bin/env python3
"""Stress the frozen log-loss derivative algebra without changing the criterion.

For z > 0, f(z) = log(1-exp(-z)); every derivative below is with
respect to log(z), i.e. D = z d/dz. With a = z/(exp(z)-1):
D f = a, D^2 f = a(1-z-a), and
D^3 f = a(1-3z+z^2)-3a^2(1-z)+2a^3.
The rearranged diagnostic algebra avoids large polynomial times zero. It is
not installed into the production evaluator. Decimal evaluates the same
identities with at least 100 digits beyond the small-z cancellation scale.
For z >= 1000, all four correctly rounded binary64 answers are zero:
12 z^3 exp(-z) is already below half the least binary64 subnormal at 1000
and decreases thereafter. This bound also covers the smaller derivatives.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
import warnings
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

import numpy as np

from latent_landscapes.differentiable_likelihood import _log_loss_derivatives

FROZEN_COMMIT = "99af5206b6a4e53f5b8e9d71cbf348f95e9ae574"
SOURCE = "src/latent_landscapes/differentiable_likelihood.py"
DERIVATIVES = ("log_loss", "d_log_z", "d2_log_z", "d3_log_z")
GRID = (
    float(np.nextafter(0.0, 1.0)),
    1e-320, 1e-300, 1e-200, 1e-100, 1e-20, 1e-12, 1e-8, 1e-5,
    float(np.nextafter(1e-3, 0.0)), 1e-3, float(np.nextafter(1e-3, math.inf)),
    0.00101, 0.01, 0.1, 0.5, 1.0, 2.0, 3.0, 10.0, 20.0, 30.0,
    36.0, 37.0, 40.0, 50.0, 100.0, 500.0, 700.0,
    709.0, 709.782712893384, 710.0, 720.0, 730.0, 740.0, 745.0, 746.0,
    750.0, 755.0, 760.0, 770.0, 800.0, 1000.0, 1e6, 1e50, 1e100,
    1e102, 1e103, 1e150, 1e154, 1e155, 1e200, 1e300, 1e308,
)


def decimal_reference(z: float) -> tuple[float, float, float, float]:
    if not math.isfinite(z) or z <= 0.0:
        raise ValueError("z must be finite and positive")
    if z >= 1000.0:
        return -0.0, 0.0, -0.0, 0.0
    with localcontext() as context:
        context.prec = max(100, 3 * int(max(0.0, -math.log10(z))) + 100)
        x = Decimal.from_float(z)
        q = (-x).exp()
        denominator = 1 - q
        if q < Decimal("0.01"):
            power, total, index = q, q, 1
            while True:
                index += 1
                power *= q
                updated = total + power / index
                if updated == total:
                    break
                total = updated
            value = -total
        else:
            value = denominator.ln()
        a = x * q / denominator
        second = a * (1 - x - a)
        third = a * (1 - 3 * x + x * x) - 3 * a * a * (1 - x) + 2 * a**3
        return tuple(float(item) for item in (value, a, second, third))


def rearranged_algebra(z: np.ndarray) -> tuple[np.ndarray, ...]:
    value = np.asarray(z, dtype=np.float64)
    if np.any(value <= 0.0) or not np.isfinite(value).all():
        raise ValueError("z must be finite and positive")
    result = [np.empty_like(value) for _ in DERIVATIVES]
    small = value < 1e-3
    middle = (value >= 1e-3) & (value < 50.0)
    large = value >= 50.0
    with np.errstate(under="ignore"):
        if np.any(small):
            x = value[small]
            x2 = x * x
            x4, x6 = x2 * x2, x2 * x2 * x2
            x8, x10 = x4 * x4, x4 * x6
            result[0][small] = np.log(-np.expm1(-x))
            result[1][small] = (
                1 - x / 2 + x2 / 12 - x4 / 720 + x6 / 30240
                - x8 / 1209600 + x10 / 47900160
            )
            result[2][small] = (
                -x / 2 + x2 / 6 - x4 / 180 + x6 / 5040
                - x8 / 151200 + x10 / 4790016
            )
            result[3][small] = (
                -x / 2 + x2 / 3 - x4 / 45 + x6 / 840
                - x8 / 18900 + 10 * x10 / 4790016
            )
        if np.any(middle):
            x = value[middle]
            denominator = -np.expm1(-x)
            a = x * np.exp(-x) / denominator
            result[0][middle] = np.where(
                x <= math.log(2.0), np.log(denominator), np.log1p(-np.exp(-x))
            )
            result[1][middle] = a
            result[2][middle] = a * (1 - x - a)
            result[3][middle] = a * (1 - 3 * x + x * x) - 3 * a * a * (1 - x) + 2 * a**3
        if np.any(large):
            x = value[large]
            lx = np.log(x)
            denominator = -np.expm1(-x)
            a = np.exp(lx - x) / denominator
            b = np.exp(2 * lx - x) / denominator
            c = np.exp(3 * lx - x) / denominator
            result[0][large] = np.log1p(-np.exp(-x))
            result[1][large] = a
            result[2][large] = a - b - a * a
            result[3][large] = a - 3 * b + c - 3 * a * a + 3 * a * b + 2 * a**3
    return tuple(result)


def json_value(value: float) -> float | str:
    return value if math.isfinite(value) else str(value)


def diagnose(grid: tuple[float, ...] = GRID) -> dict[str, Any]:
    rows = []
    for z in grid:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            with np.errstate(over="warn", invalid="warn", under="ignore"):
                frozen = [float(item[0]) for item in _log_loss_derivatives(np.asarray([z]))]
        stable = [float(item[0]) for item in rearranged_algebra(np.asarray([z]))]
        reference = list(decimal_reference(z))
        rows.append({
            "z": z,
            "frozen": [json_value(v) for v in frozen],
            "rearranged": stable,
            "decimal_reference": reference,
            "frozen_finite": [math.isfinite(v) for v in frozen],
            "frozen_absolute_error": [
                json_value(abs(v - ref)) for v, ref in zip(frozen, reference, strict=True)
            ],
            "rearranged_absolute_error": [
                abs(v - ref) for v, ref in zip(stable, reference, strict=True)
            ],
            "frozen_zero_reference_nonzero": [
                v == 0.0 and ref != 0.0 for v, ref in zip(frozen, reference, strict=True)
            ],
            "warnings": [{"category": w.category.__name__, "message": str(w.message)}
                         for w in captured],
        })
    return {
        "schema": "log-loss-scalar-stress-v1",
        "parameterization": "D = z d/dz; derivatives with respect to log(z)",
        "grid_prespecified": True,
        "derivative_order": list(DERIVATIVES),
        "limits": [
            "Diagnostic only; production evaluator and numerical candidate unchanged.",
            "No archived fit or dataset was read; warnings are not assigned causal status.",
            "Rearranged small-z series matches frozen algebra; Decimal is independent reference.",
            "Decimal precision is at least 100 digits past small-z cancellation scale.",
            "For z>=1000, an analytic bound justifies correctly rounded binary64 zeros.",
        ],
        "summary": {
            "grid_points": len(rows),
            "nonfinite_frozen_points": [r["z"] for r in rows if not all(r["frozen_finite"])],
            "warning_points": [r["z"] for r in rows if r["warnings"]],
            "premature_zero_points_by_derivative": {
                name: [r["z"] for r in rows if r["frozen_zero_reference_nonzero"][i]]
                for i, name in enumerate(DERIVATIVES)
            },
            "max_rearranged_absolute_error_by_derivative": {
                name: max(r["rearranged_absolute_error"][i] for r in rows)
                for i, name in enumerate(DERIVATIVES)
            },
        },
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = (root / SOURCE).read_bytes()
    frozen = subprocess.check_output(["git", "show", f"{FROZEN_COMMIT}:{SOURCE}"], cwd=root)
    if source != frozen:
        raise RuntimeError("production evaluator does not match frozen candidate")
    report = diagnose()
    report["provenance"] = {
        "candidate_commit": FROZEN_COMMIT,
        "source_path": SOURCE,
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "diagnostic_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python": platform.python_version(),
        "numpy": np.__version__,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
