"""Refine mesh-conditioned level sets without assuming a connected profile."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from itertools import pairwise
from typing import Any

from scipy.optimize import brentq  # type: ignore[import-untyped]


def refine_level_set(
    evaluate: Callable[[float], float],
    mesh: Sequence[float],
    cutoff: float,
    *,
    xtol: float = 1e-4,
    residual_tolerance: float = 0.01,
    max_bracket_width: float = 0.005,
) -> dict[str, Any]:
    """Return {h: W(log(h)) <= cutoff}, conditional on sampled mesh topology.

    Callback failures invalidate the entire result. Unobserved crossings and
    tangencies between same-sign mesh nodes are not ruled out by this helper.
    """
    nodes = [float(value) for value in mesh]
    if (
        len(nodes) < 2
        or not all(math.isfinite(value) for value in nodes)
        or nodes[0] != 0.0
        or nodes[-1] != math.log(30.0)
        or any(right <= left for left, right in pairwise(nodes))
    ):
        raise ValueError("mesh must be finite, strictly increasing and span [0, log(30)]")
    if (
        not math.isfinite(cutoff)
        or not math.isfinite(xtol)
        or xtol <= 0.0
        or not math.isfinite(residual_tolerance)
        or residual_tolerance < 0.0
        or not math.isfinite(max_bracket_width)
        or max_bracket_width <= 0.0
    ):
        raise ValueError("cutoff and root tolerances must be finite with valid signs")
    result: dict[str, Any] = {
        "status": "unavailable",
        "topology_scope": "mesh_conditioned",
        "global_topology_proven": False,
        "cutoff": float(cutoff),
        "xtol_log_h": float(xtol),
        "residual_tolerance": float(residual_tolerance),
        "max_verification_bracket_width_log_h": float(max_bracket_width),
        "mesh_log_h": nodes,
        "sampled_values": [],
        "roots": [],
        "components": None,
        "failure": None,
    }
    last_point: float | None = None
    last_value: float | None = None
    current_bracket: list[float] | None = None
    verification_bracket: list[float] | None = None
    endpoint_residuals: list[float] = []

    def difference(log_h: float) -> float:
        nonlocal last_point, last_value
        last_point = float(log_h)
        value = float(evaluate(last_point))
        last_value = value
        delta = value - cutoff
        if not math.isfinite(value) or not math.isfinite(delta):
            raise ValueError("callback returned a nonfinite value or residual")
        return delta

    def root_record(
        log_h: float,
        bracket: list[float],
        residual: float,
        source: str,
        verification_bracket: list[float],
        endpoint_residuals: list[float],
    ) -> None:
        result["roots"].append(
            {
                "log_h": log_h,
                "h": min(30.0, math.exp(log_h)),
                "bracket_log_h": bracket,
                "residual": residual,
                "source": source,
                "verification_bracket_log_h": verification_bracket,
                "verification_endpoint_residuals": endpoint_residuals,
                "verification_bracket_width_log_h": (
                    verification_bracket[1] - verification_bracket[0]
                ),
            }
        )

    try:
        deltas = []
        for node in nodes:
            delta = difference(node)
            deltas.append(delta)
            result["sampled_values"].append({"log_h": node, "value": last_value})
            if delta == 0.0:
                root_record(node, [node, node], 0.0, "sampled_equality", [node, node], [0.0, 0.0])
        crossings: dict[int, float] = {}
        for index, (left, right) in enumerate(pairwise(nodes)):
            left_delta, right_delta = deltas[index : index + 2]
            if (left_delta < 0.0 < right_delta) or (right_delta < 0.0 < left_delta):
                current_bracket = [left, right]
                verification_bracket = None
                endpoint_residuals = []
                root = float(brentq(difference, left, right, xtol=xtol))
                if not math.isfinite(root) or not left <= root <= right:
                    raise ValueError("root solver returned a nonfinite or out-of-bracket root")
                residual = difference(root)
                if abs(residual) > residual_tolerance:
                    raise ValueError("refined root exceeds the residual tolerance")
                verification_bracket = [max(left, root - 2 * xtol), min(right, root + 2 * xtol)]
                if verification_bracket[1] - verification_bracket[0] > max_bracket_width:
                    raise ValueError("verification bracket exceeds the width tolerance")
                for node in verification_bracket:
                    endpoint_residuals.append(difference(node))
                lo_residual, hi_residual = endpoint_residuals
                if not (lo_residual <= 0.0 <= hi_residual or hi_residual <= 0.0 <= lo_residual):
                    raise ValueError("verification bracket does not straddle the cutoff")
                crossings[index] = root
                root_record(
                    root,
                    [left, right],
                    residual,
                    "bracket_refinement",
                    verification_bracket,
                    endpoint_residuals,
                )
        current_bracket = None
    except (MemoryError, OSError):
        raise
    except Exception as error:
        result["failure"] = {
            "type": type(error).__name__,
            "message": str(error),
            "log_h": last_point,
            "bracket_log_h": current_bracket,
            "verification_bracket_log_h": verification_bracket,
            "verification_endpoint_residuals": endpoint_residuals,
        }
        result["roots"].sort(key=lambda row: row["log_h"])
        return result

    pieces = [(node, node) for node, delta in zip(nodes, deltas, strict=True) if delta == 0.0]
    for index, (left, right) in enumerate(pairwise(nodes)):
        left_delta, right_delta = deltas[index : index + 2]
        if left_delta <= 0.0 and right_delta <= 0.0:
            pieces.append((left, right))
        elif index in crossings:
            root = crossings[index]
            pieces.append((left, root) if left_delta < 0.0 else (root, right))
    merged: list[tuple[float, float]] = []
    for left, right in sorted(pieces):
        if merged and left <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(right, merged[-1][1]))
        else:
            merged.append((left, right))
    result["components"] = [
        {
            "lower_log_h": left,
            "upper_log_h": right,
            "lower_h": min(30.0, math.exp(left)),
            "upper_h": min(30.0, math.exp(right)),
            "lower_domain_contact": left == nodes[0],
            "upper_domain_contact": right == nodes[-1],
            "singleton": left == right,
        }
        for left, right in merged
    ]
    result["roots"].sort(key=lambda row: row["log_h"])
    result["status"] = "available"
    result["set_class"] = (
        "empty"
        if not merged
        else "full_domain"
        if merged == [(nodes[0], nodes[-1])]
        else "proper_subset"
    )
    return result
