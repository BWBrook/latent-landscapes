from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest


@pytest.fixture
def module() -> Any:
    path = Path(__file__).resolve().parents[1] / "scripts/profile_level_sets.py"
    spec = importlib.util.spec_from_file_location("profile_level_sets_test", path)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_refines_every_disconnected_component(module: Any) -> None:
    roots = [0.31, 0.79, 1.61, 2.24]

    def polynomial(value: float) -> float:
        return math.prod(value - root for root in roots)

    result = module.refine_level_set(polynomial, np.linspace(0, math.log(30), 15), 0.0)
    assert result["status"] == "available"
    assert result["topology_scope"] == "mesh_conditioned"
    assert not result["global_topology_proven"]
    assert len(result["components"]) == 2
    np.testing.assert_allclose([row["log_h"] for row in result["roots"]], roots, atol=1e-4)
    np.testing.assert_allclose(
        [[row["lower_log_h"], row["upper_log_h"]] for row in result["components"]],
        [[roots[0], roots[1]], [roots[2], roots[3]]],
        atol=1e-4,
    )
    assert all(abs(row["residual"]) <= 0.01 for row in result["roots"])
    for row in result["roots"]:
        lower, upper = row["verification_bracket_log_h"]
        assert lower <= row["log_h"] <= upper
        assert upper - lower == row["verification_bracket_width_log_h"] <= 0.005
        lo, hi = row["verification_endpoint_residuals"]
        assert lo <= 0 <= hi or hi <= 0 <= lo
        assert row["bracket_log_h"][1] - row["bracket_log_h"][0] > upper - lower
    assert all(
        not row["lower_domain_contact"] and not row["upper_domain_contact"]
        for row in result["components"]
    )
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("value, expected", [(1.0, "empty"), (-1.0, "full_domain")])
def test_empty_and_full_domain(module: Any, value: float, expected: str) -> None:
    result = module.refine_level_set(lambda _: value, [0.0, math.log(30)], 0.0)
    assert result["status"] == "available"
    assert result["set_class"] == expected
    assert result["roots"] == []
    if expected == "empty":
        assert result["components"] == []
    else:
        component = result["components"][0]
        assert component["lower_domain_contact"] and component["upper_domain_contact"]
        assert component["lower_h"] == 1.0 and component["upper_h"] == 30.0


def test_sampled_tangency_is_retained_as_singleton(module: Any) -> None:
    result = module.refine_level_set(lambda x: (x - 1.0) ** 2, [0.0, 1.0, math.log(30)], 0.0)
    assert result["status"] == "available"
    assert len(result["components"]) == 1
    assert result["components"][0]["singleton"]
    assert result["components"][0]["lower_log_h"] == 1.0
    assert result["roots"][0]["source"] == "sampled_equality"
    assert result["roots"][0]["verification_bracket_log_h"] == [1.0, 1.0]
    assert result["roots"][0]["verification_endpoint_residuals"] == [0.0, 0.0]


def test_endpoint_equality_and_equality_plateau(module: Any) -> None:
    result = module.refine_level_set(lambda x: x, [0.0, 1.0, math.log(30)], 0.0)
    assert result["components"][0]["singleton"]
    assert result["components"][0]["lower_domain_contact"]
    assert not result["components"][0]["upper_domain_contact"]
    flat = module.refine_level_set(lambda _: 3.0, [0.0, 1.0, math.log(30)], 3.0)
    assert flat["set_class"] == "full_domain"
    assert len(flat["roots"]) == 3
    assert len(flat["components"]) == 1


@pytest.mark.parametrize("inside", [False, True])
def test_nonfinite_sample_or_brent_evaluation_invalidates_whole_set(
    module: Any, inside: bool
) -> None:
    def value(x: float) -> float:
        if (inside and 0 < x < math.log(30)) or (not inside and x == 0):
            return math.nan
        return x - 1.0

    result = module.refine_level_set(value, [0.0, math.log(30)], 0.0)
    assert result["status"] == "unavailable"
    assert result["components"] is None
    assert "nonfinite" in result["failure"]["message"]
    json.dumps(result, allow_nan=False)


def test_failed_later_bracket_does_not_drop_a_component(
    module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = module.brentq

    def fail_later(function: Any, left: float, right: float, **kwargs: Any) -> float:
        if left > 1.0:
            raise RuntimeError("second crossing unresolved")
        return float(original(function, left, right, **kwargs))

    monkeypatch.setattr(module, "brentq", fail_later)
    result = module.refine_level_set(
        lambda x: (x - 0.5) * (x - 2.0), [0.0, 1.0, 1.5, math.log(30)], 0.0
    )
    assert result["status"] == "unavailable"
    assert result["components"] is None
    assert len(result["roots"]) == 1
    assert result["failure"]["bracket_log_h"] == [1.5, math.log(30)]


def test_residual_failure_is_not_a_certified_crossing(
    module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "brentq", lambda *args, **kwargs: 0.6)
    result = module.refine_level_set(lambda x: x - 0.5, [0.0, math.log(30)], 0.0)
    assert result["status"] == "unavailable"
    assert "residual tolerance" in result["failure"]["message"]
    assert result["components"] is None


def test_small_root_residual_without_verified_sign_change_is_unavailable(
    module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "brentq", lambda *args, **kwargs: 0.5001)
    result = module.refine_level_set(lambda x: x - 0.5, [0.0, math.log(30)], 0.0, xtol=1e-5)
    assert result["status"] == "unavailable"
    assert "does not straddle" in result["failure"]["message"]
    assert result["components"] is None


def test_verification_bracket_width_is_checked_separately_from_brent_tolerance(module: Any) -> None:
    result = module.refine_level_set(lambda x: x - 0.5, [0.0, math.log(30)], 0.0, xtol=0.01)
    assert result["status"] == "unavailable"
    assert "width tolerance" in result["failure"]["message"]
    assert result["components"] is None


@pytest.mark.parametrize(
    "mesh", [[0.0, 1.0], [0.0, 1.0, 1.0, math.log(30)], [0.0, math.nan, math.log(30)]]
)
def test_invalid_mesh_is_rejected(module: Any, mesh: list[float]) -> None:
    with pytest.raises(ValueError, match="mesh"):
        module.refine_level_set(lambda _: 0.0, mesh, 0.0)
