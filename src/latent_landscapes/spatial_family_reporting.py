"""Boundary-closed reports of a fitted positive-variance spatial family."""

from __future__ import annotations

import math
from typing import Any


def closed_positive_family(
    positive: dict[str, Any], sigma_zero: dict[str, Any], *, free: bool = False
) -> dict[str, Any]:
    """Report the better eligible endpoint, retaining sigma as the reported coordinate.

    This closes the mathematical positive-variance family at sigma=0; it does
    not change the optimizer's finite log-sigma domain or any raw fitted row.
    A free-family report compares the two free optima, whose h values may differ.
    """
    for row, family in ((positive, "positive_sigma"), (sigma_zero, "sigma_zero")):
        if row["family"] != family:
            raise ValueError("boundary closure requires positive and sigma-zero endpoints")
        if row["eligible"] is not True:
            raise ValueError("boundary closure requires both eligible endpoints")
        if isinstance(row["criterion"], bool) or not math.isfinite(row["criterion"]):
            raise ValueError("boundary closure requires finite endpoint criteria")
        if not math.isfinite(row["h"]) or not 1.0 <= row["h"] <= 30.0:
            raise ValueError("boundary closure requires fitted h in [1,30]")
    if not free and positive["h"] != sigma_zero["h"]:
        raise ValueError("fixed-h boundary closure requires identical h")
    boundary = sigma_zero["criterion"] > positive["criterion"]
    selected = sigma_zero if boundary else positive
    sigma = 0.0 if boundary else math.exp(positive["parameters"]["log_sigma"])
    if not math.isfinite(sigma) or (not boundary and sigma <= 0.0):
        raise ValueError("positive endpoint must have finite strictly positive sigma")
    parameters = {
        name: selected["parameters"][name] for name in ("alpha", "beta", "detection_sd")
    }
    if free:
        parameters["log_h"] = selected["parameters"]["log_h"]
    parameters["sigma"] = sigma
    if not all(math.isfinite(value) for value in parameters.values()):
        raise ValueError("boundary closure requires finite reported parameters")
    return {
        "family": "positive_sigma",
        "definition": "boundary_closed",
        "criterion": selected["criterion"],
        "eligible": True,
        "boundary_supremum": boundary,
        "selected_component": "sigma_zero_boundary" if boundary else "positive_endpoint",
        "h": selected["h"],
        "sigma": sigma,
        "parameters": parameters,
        "source": selected["source"],
        "positive_endpoint_criterion": positive["criterion"],
        "sigma_zero_boundary_criterion": sigma_zero["criterion"],
    }
