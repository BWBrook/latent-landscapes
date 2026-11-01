from __future__ import annotations

import copy
import importlib.util
import math
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest


@pytest.fixture
def module(monkeypatch: pytest.MonkeyPatch) -> Any:
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "development_profile_test", root / "scripts/run_development_profile.py"
    )
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    monkeypatch.setattr(result.adapter, "_candidate_summary", lambda row, **kwargs: dict(row))
    return result


def candidate(family: str, value: float, x: float, *, free: bool) -> dict[str, Any]:
    parameters = {"alpha": -5.0, "beta": 0.3, "detection_sd": 0.2}
    if family == "positive_sigma":
        parameters["log_sigma"] = math.log(0.3)
    if free:
        parameters["log_h"] = x
    return {
        "family": family,
        "criterion": value,
        "eligible": True,
        "h": min(30.0, math.exp(x)),
        "parameters": parameters,
        "source": "fixture",
        "projected_gradient_inf": 0.0,
        "mode": None,
    }


def search(module: Any, tmp_path: Path, mode: str, *, shape: str = "parabola") -> Any:
    q = module.PanelSearch.__new__(module.PanelSearch)
    q.mode = mode
    q.args = SimpleNamespace(dense_baseline=mode == "dense")
    q.refine_numerical_ties = mode == "dense"
    q.midpoint_spacing = module.LOG_MAX / 34 if mode == "dense" else module.LOG_MAX
    q.reference_points = {}
    q.points = {False: {}, True: {}}
    q.free = {}
    q.directional = {}
    q.midpoint_triggers = []
    q.closure_history = []
    q.started = time.perf_counter()
    directory = tmp_path / mode
    directory.mkdir(exist_ok=True)
    q.events = directory / "evaluations.jsonl"
    q.mesh, q.tight_mesh = [], []
    q.result, q.search_cost, q.stats = {}, {}, {}
    q.post_search_seconds = 0.0
    q.fixed_fit_events = 0
    maximum = 0.0 if shape == "boundary" else 1.8 if shape in {"hidden", "narrow_island"} else 1.4

    def value(x: float) -> float:
        if shape == "flat":
            return 0.0
        if shape == "disconnected":
            return max(-15 * (x - 0.7) ** 2, -15 * (x - 2.5) ** 2 - 0.2)
        if shape == "hidden":
            return max(-3 * (x - maximum) ** 2, -1000 * (x - 0.3) ** 2 - 0.2)
        if shape == "narrow_island":
            return max(-3 * (x - maximum) ** 2, -100000 * (x - 0.321) ** 2 - 0.2)
        if shape == "narrow_hole":
            return min(-3 * (x - maximum) ** 2, -10 + 100000000 * (x - 1.113217) ** 2)
        return -3 * (x - maximum) ** 2

    def fit(**kwargs: Any) -> list[dict[str, Any]]:
        family = "sigma_zero" if kwargs["sigma_zero"] else "positive_sigma"
        free = kwargs["fixed_h"] is None
        x = (0.7 if shape == "disconnected" else maximum) if free else math.log(kwargs["fixed_h"])
        criterion = value(x) - (family == "sigma_zero")
        if shape == "narrow_owner" and family == "sigma_zero":
            criterion = max(criterion, -100000 * (x - 2.123456) ** 2 - 1.2)
        if shape == "cross_owner" and family == "sigma_zero":
            criterion = max(criterion, -200 * (x - 21 * module.LOG_MAX / 34) ** 2 - 1.47)
        return [candidate(family, criterion, x, free=free)]

    q.criterion = SimpleNamespace(_fit_family=fit, stats={})
    return q


@pytest.mark.parametrize("shape", ["parabola", "boundary", "flat", "disconnected"])
def test_independent_dense_and_lean_searches_close(module: Any, tmp_path: Path, shape: str) -> None:
    dense = search(module, tmp_path, "dense", shape=shape)
    lean = search(module, tmp_path, "lean", shape=shape)
    dr, lr = dense.run(), lean.run()
    assert dr["status"] == lr["status"] == "profile_numerically_resolved", (
        dr.get("failure"),
        lr.get("failure"),
    )
    assert dense.points is not lean.points
    assert dense.criterion is not lean.criterion
    comparison = module.compare_searches(dense, lean, [1.0, 3.0])
    assert comparison["status"] == "within_prespecified_gates", comparison
    if shape == "flat":
        assert lr["maximum"]["True"]["effect_estimate"] is None
        assert lr["maximum"]["True"]["status"] == "flat_on_evaluated_domain"
        assert lr["tight_level_sets"][0]["set_class"] == "full_domain"
    if shape == "boundary":
        assert lr["tight_level_sets"][0]["components"][0]["lower_domain_contact"]
    if shape == "disconnected":
        assert len(lr["tight_level_sets"][0]["components"]) == 2


def test_post_search_superior_candidate_is_indeterminate(module: Any, tmp_path: Path) -> None:
    q = search(module, tmp_path, "lean")
    assert q.run()["status"] == "profile_numerically_resolved"
    old = q.criterion._fit_family

    def fit(**kwargs: Any) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = old(**kwargs)
        if kwargs["fixed_h"] == pytest.approx(1.2345):
            for row in rows:
                row["criterion"] += 100.0
        return rows

    q.criterion._fit_family = fit
    result = q.post_search_points([math.log(1.2345)])
    assert result["status"] == "unavailable"
    assert q.result["status"] == "indeterminate"
    assert "superior" in result["failure"]["message"]


def test_missing_component_cannot_pass_dense_comparison(module: Any, tmp_path: Path) -> None:
    dense = search(module, tmp_path, "dense", shape="disconnected")
    lean = search(module, tmp_path, "lean", shape="disconnected")
    dense.run()
    lean.run()
    lean.result["tight_level_sets"][0]["components"].pop()
    result = module.compare_searches(dense, lean, [1.0, 3.0])
    assert result["status"] == "indeterminate"
    assert lean.result["status"] == "indeterminate"


def test_failed_root_evaluation_is_not_an_empty_set(module: Any, tmp_path: Path) -> None:
    q = search(module, tmp_path, "lean")
    old = q.point

    def point(x: float, **kwargs: Any) -> Any:
        if 2.19 < x < 2.21:
            raise RuntimeError("root fit unresolved")
        return old(x, **kwargs)

    q.point = point
    result = q.run()
    assert result["status"] == "indeterminate"
    assert result.get("failure")


def test_reporting_does_not_mutate_search_cost(module: Any, tmp_path: Path) -> None:
    q = search(module, tmp_path, "lean")
    result = q.run()
    before = dict(result["cost"]["search"])
    q.post_search_points([math.log(1.2345)])
    after = q.receipt()
    assert after["cost"]["search"] == before
    assert after["cost"]["post_search_seconds"] > 0
    assert after["cost"]["total_fixed_fit_events"] > before["fixed_fit_events"]
    assert all("candidates" not in point for values in after["points"].values() for point in values)


def test_report_h_is_not_a_search_argument(module: Any, tmp_path: Path) -> None:
    q = search(module, tmp_path, "lean")
    assert q.run()["status"] == "profile_numerically_resolved"
    nodes = set(q.points[False])
    x = math.log(1.2345)
    assert x not in nodes
    q.post_search_points(module.comparison_locations([q], [1.2345]))
    assert x in q.points[False]


def test_tied_variance_owners_are_exempt(module: Any, tmp_path: Path) -> None:
    dense = search(module, tmp_path, "dense")
    lean = search(module, tmp_path, "lean")
    dense.run()
    lean.run()
    for q in (dense, lean):
        for points in q.points.values():
            for fit in points.values():
                fit["sigma_zero"]["criterion"] = fit["positive_sigma"]["criterion"] - 1e-5
    result = module.compare_searches(dense, lean, [1.0])
    assert result["status"] == "within_prespecified_gates"


def test_panel_direct_factory_matches_raw_zero_family(module: Any, tmp_path: Path) -> None:
    from latent_landscapes import log_domain_likelihood
    from latent_landscapes import preinvasion_likelihood as likelihood
    from latent_landscapes.spatial_profile import SpatialProfileData

    ids = ("a", "b", "c")
    raw = np.random.default_rng(81).uniform(0.0, 80.0, size=(31, 3))
    bank = likelihood.compress_bank(raw, ids, series_order=48)
    prey = np.zeros((1, 3, 13), dtype=np.int64)
    prey[:, :, :3] = 1
    predator = np.ones((1, 3, 6), dtype=np.int64)
    observed = likelihood.prepare_observations(prey, predator, ids, np.ones(3, dtype=bool))
    exposure = np.array([-0.4, 0.0, 0.5])
    data = SpatialProfileData(bank, observed, exposure, np.eye(3))
    q = module.PanelSearch(data, "lean", tmp_path)
    parameters = np.array([-5.0, 0.3, 0.2])
    actual = q.criterion.evaluate_sigma_zero(parameters, fixed_h=3.0)
    exact = log_domain_likelihood.exact_log_scores(
        observed, bank, [3.0], np.exp(parameters[0] + parameters[1] * exposure), detection_sd=0.2
    )
    assert actual.success
    assert actual.criterion == pytest.approx(
        float(exact.joint_loglikelihood[0, 0].sum()), abs=1e-10
    )


def test_unseen_narrow_component_fails_lean_qualification(module: Any, tmp_path: Path) -> None:
    dense = search(module, tmp_path, "dense", shape="hidden")
    lean = search(module, tmp_path, "lean", shape="hidden")
    assert dense.run()["status"] == "profile_numerically_resolved"
    assert lean.run()["status"] == "profile_numerically_resolved"
    assert len(dense.result["tight_level_sets"][0]["components"]) == 2
    assert len(lean.result["tight_level_sets"][0]["components"]) == 1
    assert module.compare_searches(dense, lean, [1.0, 3.0])["status"] == "indeterminate"
    assert lean.result["status"] == "indeterminate"


@pytest.mark.parametrize("shape,x", [("narrow_island", 0.321), ("narrow_hole", 1.113217)])
def test_reported_topology_contradiction_invalidates_frozen_searches(
    module: Any, tmp_path: Path, shape: str, x: float
) -> None:
    dense = search(module, tmp_path, "dense", shape=shape)
    lean = search(module, tmp_path, "lean", shape=shape)
    snapshots = []
    for q in (dense, lean):
        assert q.run()["status"] == "profile_numerically_resolved"
        snapshots.append(
            copy.deepcopy(
                (
                    q.result["level_sets"],
                    q.result["tight_level_sets"],
                    q.mesh,
                    q.tight_mesh,
                    q.search_cost,
                    q.free,
                )
            )
        )
    result = module.compare_searches(dense, lean, [math.exp(x)])
    assert result["status"] == "indeterminate"
    for q, snapshot in zip((dense, lean), snapshots, strict=True):
        assert q.result["status"] == "indeterminate"
        assert "membership" in q.result["post_search_failure"]["message"]
        assert (
            q.result["level_sets"],
            q.result["tight_level_sets"],
            q.mesh,
            q.tight_mesh,
            q.search_cost,
            q.free,
        ) == snapshot
        checks = q.result["post_search_diagnostics"]["points"][-1]["frozen_membership_checks"]
        assert not all(row["passed"] for rows in checks.values() for row in rows)


@pytest.mark.parametrize(
    "x,residual,expected",
    [
        (0.321, -0.005, False),
        (0.321, 0.0, False),
        (0.321, 0.005, True),
        (1.5, 0.005, False),
        (1.5, 0.0, True),
        (1.5, -0.005, True),
        (1.0, 0.01, True),
        (0.9999, -0.01, True),
        (2.0, 0.01, True),
        (2.0001, -0.01, True),
        (1.0, 0.011, False),
        (2.0001, -0.011, False),
    ],
)
def test_frozen_membership_tolerance_is_confined_to_verified_roots(
    module: Any, x: float, residual: float, expected: bool
) -> None:
    level = {
        "cutoff": 3.84,
        "residual_tolerance": 0.01,
        "components": [{"lower_log_h": 1.0, "upper_log_h": 2.0}],
        "roots": [{"verification_bracket_log_h": [r - 0.0002, r + 0.0002]} for r in (1.0, 2.0)],
    }
    check = module.frozen_membership_check(level, x, 3.84 + residual)
    assert check["passed"] == expected


@pytest.mark.parametrize("x", [0.0, math.log(30.0)])
def test_domain_contacts_are_closed_without_unverified_tolerance(module: Any, x: float) -> None:
    level = {
        "cutoff": 3.84,
        "residual_tolerance": 0.01,
        "roots": [],
        "components": [{"lower_log_h": 0.0, "upper_log_h": math.log(30.0)}],
    }
    assert module.frozen_membership_check(level, x, 3.84)["passed"]
    assert not module.frozen_membership_check(level, x, 3.845)["passed"]


def test_cross_search_location_also_checks_frozen_membership(module: Any, tmp_path: Path) -> None:
    q = search(module, tmp_path, "lean", shape="narrow_island")
    assert q.run()["status"] == "profile_numerically_resolved"
    other = SimpleNamespace(free={}, result={"tight_level_sets": [{"roots": [{"log_h": 0.321}]}]})
    locations = module.comparison_locations([other], [])
    diagnostics = q.post_search_points(locations)
    assert diagnostics["status"] == "unavailable"
    assert q.result["status"] == "indeterminate"
    assert diagnostics["points"][-1]["log_h"] == 0.321
    assert "membership" in diagnostics["failure"]["message"]


def test_post_search_non_tied_owner_island_is_indeterminate(module: Any, tmp_path: Path) -> None:
    dense = search(module, tmp_path, "dense", shape="narrow_owner")
    lean = search(module, tmp_path, "lean", shape="narrow_owner")
    for q in (dense, lean):
        assert q.run()["status"] == "profile_numerically_resolved"
    assert module.compare_searches(dense, lean, [math.exp(2.123456)])["status"] == "indeterminate"
    for q in (dense, lean):
        assert q.result["status"] == "indeterminate"
        checks = q.result["post_search_retained_topology_checks"]
        assert not checks["membership_failures"]
        assert any(not c["passed"] for c in checks["ownership_transitions"]["True"])


def test_recorded_switch_requires_a_retained_numerical_tie(module: Any) -> None:
    def fit(positive: float, zero: float) -> dict[str, Any]:
        return {
            "criterion": max(positive, zero),
            "positive_sigma": {"criterion": positive},
            "sigma_zero": {"criterion": zero},
        }

    points = {0.0: fit(0.0, -1.0), 1.0: fit(0.0, -1e-5), 2.0: fit(-1.0, 0.0)}
    unrecorded: dict[str, Any] = {"isolated": [], "tie_intervals": []}
    recorded = {"isolated": [{"log_h": 1.0}], "tie_intervals": []}
    assert not all(c["passed"] for c in module.frozen_ownership_checks(points, unrecorded))
    assert all(c["passed"] for c in module.frozen_ownership_checks(points, recorded))
    points[1.0] = fit(-0.1, 0.0)
    assert not all(c["passed"] for c in module.frozen_ownership_checks(points, recorded))


def test_dense_ownership_feature_is_cross_evaluated_without_truth_hint(
    module: Any, tmp_path: Path
) -> None:
    dense = search(module, tmp_path, "dense", shape="cross_owner")
    lean = search(module, tmp_path, "lean", shape="cross_owner")
    for q in (dense, lean):
        assert q.run()["status"] == "profile_numerically_resolved"
    dense_checks = dense.result["final_retained_topology_checks"]["ownership_transitions"]
    assert any("bracket_log_h" in row for row in dense_checks["True"])
    assert not lean.result["final_retained_topology_checks"]["ownership_transitions"]["True"]
    costs = [dict(q.search_cost) for q in (dense, lean)]
    levels = [copy.deepcopy(q.result["tight_level_sets"]) for q in (dense, lean)]
    comparison = module.compare_searches(dense, lean, [1.0, 3.0])
    assert comparison["status"] == "indeterminate"
    assert lean.result["status"] == "indeterminate"
    assert "ownership" in lean.result["post_search_failure"]["message"]
    for q, cost, level in zip((dense, lean), costs, levels, strict=True):
        assert q.search_cost == cost
        assert q.result["tight_level_sets"] == level


@pytest.mark.parametrize("shape,x", [("narrow_island", 0.321), ("narrow_owner", 2.123456)])
def test_final_free_replay_cannot_leave_unchecked_retained_points(
    module: Any, tmp_path: Path, shape: str, x: float
) -> None:
    q = search(module, tmp_path, "lean", shape=shape)
    fit_free = q.fit_free

    def inject(**kwargs: Any) -> Any:
        result = fit_free(**kwargs)
        if any(entry.get("tight") is True for entry in q.closure_history):
            q.point(x)
            q.point(x, tight=True)
        return result

    q.fit_free = inject
    result = q.run()
    assert result["status"] == "indeterminate"
    assert not result["final_retained_topology_checks"]["passed"]
    assert "final retained points" in result["failure"]["message"]
