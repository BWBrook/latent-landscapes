from __future__ import annotations

import copy
import importlib
import json
import math
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest


@pytest.fixture
def module(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    result = importlib.import_module("compare_development_banks")
    monkeypatch.setattr(result.adapter, "_candidate_summary", lambda row, **kwargs: dict(row))
    return result


def analytic(
    module: Any,
    directory: Path,
    *,
    center: float = 1.4,
    curvature: float = 3.0,
    offset: float = 0.0,
    alpha: float = -5.0,
    zero_gap: float = 1.0,
    detection: float = 0.2,
    shape: str = "parabola",
) -> Any:
    q = module.profile.PanelSearch.__new__(module.profile.PanelSearch)
    q.mode = "lean"
    q.args = SimpleNamespace(dense_baseline=False)
    q.refine_numerical_ties = False
    q.midpoint_spacing = module.profile.LOG_MAX
    q.reference_points, q.free, q.directional = {}, {}, {}
    q.points = {False: {}, True: {}}
    q.midpoint_triggers, q.closure_history = [], []
    q.mesh, q.tight_mesh = [], []
    q.result, q.search_cost, q.stats = {}, {}, {}
    q.post_search_seconds, q.fixed_fit_events = 0.0, 0
    q.started = time.perf_counter()
    directory.mkdir()
    q.events = directory / "evaluations.jsonl"
    q.calls = []

    def fit(**kwargs: Any) -> list[dict[str, Any]]:
        family = "sigma_zero" if kwargs["sigma_zero"] else "positive_sigma"
        free = kwargs["fixed_h"] is None
        x = center if free else math.log(kwargs["fixed_h"])
        q.calls.append(
            {"free": free, "x": x, "alphas": [float(row[0]) for row in kwargs["starts"]]}
        )
        value = -curvature * (x - center) ** 2
        if shape == "disconnected":
            value = max(-15 * (x - 0.7) ** 2, -15 * (x - 2.5) ** 2 - 0.2)
        if shape == "missed_island":
            value = max(value, -100000 * (x - 0.321) ** 2 - 0.2)
        parameters = {"alpha": alpha, "beta": 0.3, "detection_sd": detection}
        if family == "positive_sigma":
            parameters["log_sigma"] = math.log(0.3)
        if free:
            parameters["log_h"] = x
        return [
            {
                "family": family,
                "criterion": value + offset - (family == "sigma_zero") * zero_gap,
                "eligible": True,
                "h": min(30.0, math.exp(x)),
                "parameters": parameters,
                "source": "analytic_bank",
                "projected_gradient_inf": 0.0,
                "mode": None,
            }
        ]

    q.criterion = SimpleNamespace(_fit_family=fit, stats={})
    assert q.run()["status"] == "profile_numerically_resolved"
    q.calls.clear()
    return q


def test_distinct_banks_get_fresh_common_points_and_only_own_starts(
    module: Any, tmp_path: Path
) -> None:
    b0 = analytic(module, tmp_path / "B0", alpha=-4.0)
    independent = analytic(module, tmp_path / "A", center=1.402, offset=20, alpha=-6.0)
    original = [copy.deepcopy(q.search_cost) for q in (b0, independent)]
    result = module.compare_banks(b0, independent, [1.0, math.exp(0.12345)])
    assert result["status"] == "within_prespecified_gates", result.get("reason")
    assert result["free_criterion_difference_descriptive_only"] == pytest.approx(20)
    expected = result["locations_log_h"]
    for q, alpha, cost in zip((b0, independent), (-4.0, -6.0), original, strict=True):
        assert q.search_cost == cost
        assert sorted({call["x"] for call in q.calls}) == pytest.approx(expected)
        assert all(not call["free"] for call in q.calls)
        assert all(set(call["alphas"]) <= {alpha, -5.5} for call in q.calls)
    for diagnostic in result["cross_evaluations"].values():
        assert diagnostic["cost"]["fixed_fit_events"] == 2 * len(expected)
        assert diagnostic["cost"]["family_fit_batches"] == 4 * len(expected)


def test_w_threshold_fails_with_stable_components(module: Any, tmp_path: Path) -> None:
    b0 = analytic(module, tmp_path / "B0")
    independent = analytic(module, tmp_path / "A", curvature=3.12)
    result = module.compare_banks(b0, independent, [1.0, 3.0])
    assert result["status"] == "failed"
    assert all(row["passed"] for row in result["level_set_checks"])
    assert max(abs(row["delta_w"]) for row in result["points"]) > 0.1


@pytest.mark.parametrize("shift,passes", [(0.049, True), (0.051, False)])
def test_log_root_threshold(module: Any, tmp_path: Path, shift: float, passes: bool) -> None:
    q = analytic(module, tmp_path / "bank")
    first = q.result["tight_level_sets"][0]
    second = copy.deepcopy(first)
    for component in second["components"]:
        component["lower_log_h"] += shift
        component["upper_log_h"] += shift
    for root in second["roots"]:
        root["log_h"] += shift
    assert module.compare_levels(first, second)["passed"] == passes


def test_component_and_domain_contact_differences_fail(module: Any, tmp_path: Path) -> None:
    b0 = analytic(module, tmp_path / "B0")
    independent = analytic(module, tmp_path / "A", center=0.7, shape="disconnected")
    result = module.compare_banks(b0, independent, [1.0, 3.0])
    assert result["status"] == "failed"
    assert not result["level_set_checks"][0]["passed"]
    changed = copy.deepcopy(b0.result["tight_level_sets"][0])
    changed["components"][0]["lower_domain_contact"] = True
    assert not module.compare_levels(b0.result["tight_level_sets"][0], changed)["passed"]


@pytest.mark.parametrize(
    "zero_gap,detection,expected",
    [(-1.0, 0.2, "failed"), (0.0, 0.2, "within_prespecified_gates"), (1.0, 0.0, "failed")],
)
def test_ownership_ties_and_nuisance_contacts(
    module: Any, tmp_path: Path, zero_gap: float, detection: float, expected: str
) -> None:
    b0 = analytic(module, tmp_path / "B0")
    independent = analytic(module, tmp_path / "A", zero_gap=zero_gap, detection=detection)
    result = module.compare_banks(b0, independent, [1.0, 3.0])
    assert result["status"] == expected, result.get("reason")
    assert max(abs(row["delta_w"]) for row in result["points"]) < 1e-10


def test_missed_feature_is_indeterminate_without_repair(module: Any, tmp_path: Path) -> None:
    b0 = analytic(module, tmp_path / "B0", center=1.8)
    independent = analytic(module, tmp_path / "A", center=1.8, shape="missed_island")
    frozen = copy.deepcopy(independent.result["tight_level_sets"])
    result = module.compare_banks(b0, independent, [math.exp(0.321)])
    assert result["status"] == "indeterminate"
    assert independent.result["tight_level_sets"] == frozen
    assert "membership" in result["cross_evaluations"]["A"]["failure"]["message"]


def test_unresolved_bank_does_not_start_cross_evaluations(module: Any, tmp_path: Path) -> None:
    b0 = analytic(module, tmp_path / "B0")
    independent = analytic(module, tmp_path / "A")
    independent.result["status"] = "indeterminate"
    assert module.compare_banks(b0, independent, [1.0])["status"] == "indeterminate"
    assert not b0.calls and not independent.calls


def test_restore_receipt_keeps_original_and_uses_own_fit_winners(
    module: Any, tmp_path: Path
) -> None:
    from latent_landscapes import preinvasion_likelihood as likelihood
    from latent_landscapes.spatial_profile import SpatialProfileData

    q = analytic(module, tmp_path / "original", alpha=-4.0)
    receipt = json.loads(json.dumps(q.receipt()))
    original = copy.deepcopy(receipt)
    ids = ("a", "b", "c")
    raw = np.random.default_rng(37).uniform(0, 80, size=(16, 3))
    bank = likelihood.compress_bank(raw, ids, series_order=192)
    observed = likelihood.prepare_observations(
        np.zeros((1, 3, 13), dtype=int), np.zeros((1, 3, 6), dtype=int), ids, np.ones(3, dtype=bool)
    )
    data = SpatialProfileData(bank, observed, np.zeros(3), np.eye(3))
    destination = tmp_path / "crosscheck"
    destination.mkdir()
    restored = module.restore_search(data, receipt, destination)
    assert receipt == original
    assert restored.search_cost == receipt["cost"]["search"]
    assert restored.events.parent == destination
    assert len(restored.free[True]["candidates"]) == 2
    assert all(row["parameters"]["alpha"] == -4 for row in restored.free[True]["candidates"])
    assert restored.retained_topology_checks()["passed"]


def test_original_receipt_and_input_hashes_are_enforced(module: Any, tmp_path: Path) -> None:
    directory = tmp_path / "run"
    (directory / "lean").mkdir(parents=True)
    search_path = directory / "lean" / "receipt.json"
    search_path.write_text(json.dumps({"schema": "development-profile-search-v1", "mode": "lean"}))
    observation = tmp_path / "observations.npz"
    observation.write_bytes(b"fixture observations")
    names = (
        "scripts/run_development_profile.py",
        "scripts/qualify_spatial_profiles.py",
        "scripts/profile_level_sets.py",
        "scripts/benchmark_spatial_profile.py",
        "src/latent_landscapes/spatial_profile.py",
    )
    bindings = {
        str(module.ROOT / name): module.adapter.sha256_file(module.ROOT / name) for name in names
    }
    bindings[str(observation)] = module.adapter.sha256_file(observation)
    parent = {
        "schema": "development-profile-run-v1",
        "source_input_sha256": bindings,
        "searches": {"lean": {"sha256": module.adapter.sha256_file(search_path)}},
    }
    (directory / "receipt.json").write_text(json.dumps(parent))
    module.verify_run(directory, "lean", {"observations": observation})
    observation.write_bytes(b"different history")
    with pytest.raises(ValueError, match="supplied observations"):
        module.verify_run(directory, "lean", {"observations": observation})
    search_path.write_text("{}")
    with pytest.raises(ValueError, match="search receipt hash"):
        module.verify_run(directory, "lean", {})
