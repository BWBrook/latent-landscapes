from __future__ import annotations

import importlib
import math
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.development_challenge_data import PREDATOR_TIMES, PREY_TIMES
from latent_landscapes.spatial_profile import SpatialProfileCriterion, SpatialProfileData


@pytest.fixture
def fit(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("fit_dataset")


@pytest.fixture
def generate(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("generate_history")


def small_criterion(sites: int = 6, *, h_penalty: bool = False) -> SpatialProfileCriterion:
    ids = tuple(f"s{i}" for i in range(sites))
    bank = likelihood.compress_bank(np.zeros((3, sites)), ids)
    observed = likelihood.prepare_observations(
        np.zeros((1, sites, 13), dtype=np.int64),
        np.zeros((1, sites, 6), dtype=np.int64),
        ids,
        np.ones(sites, dtype=bool),
    )
    exposure = np.linspace(-0.8, 1.0, sites)
    distance = np.abs(np.arange(sites)[:, None] - np.arange(sites)[None, :])
    data = SpatialProfileData(bank, observed, exposure, np.exp(-distance / 1.7))
    index = np.arange(sites, dtype=float)
    count = 0.18 + 0.025 * index
    weight = 0.75 + 0.08 * index

    def build(h: float, detection_sd: float, grid: np.ndarray) -> np.ndarray:
        shifted = grid[None, :] + (0.0 if h_penalty else 0.045 * math.log(h)) - 0.12 * detection_sd
        values = count[:, None] * shifted - weight[:, None] * np.exp(shifted)
        if h_penalty:
            values = values - 0.5 * (math.log(h) - 1.2) ** 2
        return values

    return SpatialProfileCriterion(data, grid=np.linspace(-8.0, 1.0, 361), curve_builder=build)


def fake_search(fit: Any, tmp_path: Path) -> Any:
    q = fit.FitSearch.__new__(fit.FitSearch)
    q.mode = "lean"
    q.args = SimpleNamespace(dense_baseline=False)
    q.refine_numerical_ties = False
    q.midpoint_spacing = fit.LOG_MAX
    q.reference_points = {}
    q.points = {False: {}, True: {}}
    q.free = {}
    q.directional = {}
    q.midpoint_triggers = []
    q.closure_history = []
    q.started = time.perf_counter()
    q.events = tmp_path / "evaluations.jsonl"
    q.mesh, q.tight_mesh = [], []
    q.result, q.search_cost, q.stats = {}, {}, {}
    q.post_search_seconds = 0.0
    q.fixed_fit_events = 0

    def candidates(**kwargs: Any) -> list[dict[str, Any]]:
        family = "sigma_zero" if kwargs["sigma_zero"] else "positive_sigma"
        free = kwargs["fixed_h"] is None
        x = 1.4 if free else math.log(kwargs["fixed_h"])
        parameters = {"alpha": -5.0, "beta": 0.3, "detection_sd": 0.2}
        if family == "positive_sigma":
            parameters["log_sigma"] = math.log(0.3)
        if free:
            parameters["log_h"] = x
        return [
            {
                "family": family,
                "criterion": -3 * (x - 1.4) ** 2 - (family == "sigma_zero"),
                "eligible": True,
                "h": min(30.0, math.exp(x)),
                "parameters": parameters,
                "source": "fixture",
                "projected_gradient_inf": 0.0,
                "mode": None,
            }
        ]

    q.criterion = SimpleNamespace(_fit_family=candidates, stats={})
    return q


def test_cutoff_grid_reaches_level_sets_roots_and_domain_contacts(
    fit: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(fit.adapter, "_candidate_summary", lambda row, **kwargs: dict(row))
    search = fake_search(fit, tmp_path)
    result = search.run()
    assert result["status"] == "profile_numerically_resolved", result.get("failure")
    assert tuple(result["cutoffs"]) == fit.CUTOFF_GRID
    for regime in ("level_sets", "tight_level_sets"):
        levels = [fit.summarise_level(level) for level in result[regime]]
        assert [level["cutoff"] for level in levels] == list(fit.CUTOFF_GRID)
        for level in levels:
            half = math.sqrt(level["cutoff"] / 6.0)
            lower, upper = 1.4 - half, 1.4 + half
            expected = [v for v in (lower, upper) if 0.0 < v < fit.LOG_MAX]
            assert level["roots_log_h"] == pytest.approx(expected, abs=2e-4)
            assert level["touches_h1"] == (lower <= 0.0)
            assert level["touches_h30"] == (upper >= fit.LOG_MAX)
            assert level["empty"] is False


def make_family(fit: Any, *, beta_free: bool) -> Any:
    return fit.ReducedFamily(
        "exposure" if beta_free else "constant",
        small_criterion(h_penalty=True),
        beta_free=beta_free,
    )


def test_reduced_families_are_nested_and_constant_has_zero_beta(fit: Any) -> None:
    nodes = [float(x) for x in np.linspace(0.0, fit.LOG_MAX, 5)]
    cutoffs = (2.71, 3.84, 15.0)
    exposure, constant = make_family(fit, beta_free=True), make_family(fit, beta_free=False)
    results = {}
    for name, family in (("exposure", exposure), ("constant", constant)):
        results[name] = family.result(family.run(nodes, cutoffs))
    assert results["constant"]["free"]["parameters"]["beta"] == 0.0
    assert all(row["w"] >= -1e-6 for r in results.values() for row in r["profile"])
    assert (
        results["constant"]["free"]["criterion"] <= results["exposure"]["free"]["criterion"] + 1e-6
    )
    for r in results.values():
        assert r["lr1"] >= -1e-6
        assert r["null"]["h"] == 1.0
        assert [level["cutoff"] for level in r["level_sets"]] == list(cutoffs)
        profile = {row["log_h"]: row["w"] for row in r["profile"]}
        for level in r["level_sets"]:
            assert level["status"] == "available"
            for x, w in profile.items():
                inside = any(
                    c["lower_log_h"] - 1e-9 <= x <= c["upper_log_h"] + 1e-9
                    for c in level["components"]
                )
                assert inside == (w <= level["cutoff"] + 1e-9) or abs(w - level["cutoff"]) < 1e-3


@pytest.mark.parametrize("beta_free", [True, False])
def test_reduced_family_sets_match_the_analytic_profile(fit: Any, beta_free: bool) -> None:
    family = make_family(fit, beta_free=beta_free)
    nodes = [float(x) for x in np.linspace(0.0, fit.LOG_MAX, 12)]
    result = family.result(family.run(nodes, fit.CUTOFF_GRID))
    assert result["free"]["h"] == pytest.approx(math.exp(1.2), rel=2e-3)
    for level in result["level_sets"]:
        half = math.sqrt(level["cutoff"] / 6.0)
        lower, upper = 1.2 - half, 1.2 + half
        assert level["roots_log_h"] == pytest.approx(
            [v for v in (lower, upper) if 0.0 < v < fit.LOG_MAX], abs=3e-4
        )
        assert level["touches_h1"] == (lower <= 0.0)
        assert level["touches_h30"] is False
    assert result["lr1"] == pytest.approx(6 * 1.2**2, rel=2e-3)


def test_tie_rule_drops_only_the_redundant_lower_sigma_contact(fit: Any) -> None:
    def fit_with(positive: float, zero: float) -> dict[str, Any]:
        return {
            "criterion": max(positive, zero),
            "positive_sigma": {
                "criterion": positive,
                "nuisance_bound_contacts": ["log_sigma:lower", "alpha:upper"],
                "h_domain_contacts": [],
            },
            "sigma_zero": {
                "criterion": zero,
                "nuisance_bound_contacts": ["alpha:upper"],
                "h_domain_contacts": [],
            },
        }

    tied, contacts = fit.tie_adjusted(fit_with(-10.0, -10.00005))
    assert tied
    assert contacts["positive_sigma"] == ["alpha:upper"]
    assert contacts["sigma_zero"] == ["alpha:upper"]
    untied, contacts = fit.tie_adjusted(fit_with(-10.0, -10.5))
    assert not untied
    assert contacts["positive_sigma"] == ["log_sigma:lower", "alpha:upper"]
    summary = fit.owner_contacts(fit_with(-10.0, -10.00005))
    assert summary["nuisance_contacts_raw"]["positive_sigma"] == ["log_sigma:lower", "alpha:upper"]
    assert summary["owners"] == ["positive_sigma", "sigma_zero"]


def test_latent_audit_skips_small_sigma_and_runs_thirteen_starts(fit: Any) -> None:
    criterion = small_criterion()
    diagnosis = fit.load_mode_diagnosis()
    parameters = {"alpha": -1.4, "beta": 0.2, "log_sigma": math.log(0.4), "detection_sd": 0.18}
    row = {"parameters": parameters, "h": 3.0}
    audit = fit.latent_audit(criterion, row, diagnosis)
    assert audit["performed"]
    assert len(audit["starts"]) == 13
    assert not audit["multimodal_latent"]
    tiny = {"parameters": {**parameters, "log_sigma": math.log(5e-4)}, "h": 3.0}
    assert fit.latent_audit(criterion, tiny, diagnosis)["performed"] is False


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({}, "resolved"),
        ({"multimodal": True}, "multimodal_latent"),
        (
            {"search_status": "indeterminate", "search_failure": {"message": "x"}},
            "search_unresolved",
        ),
        (
            {
                "search_status": "indeterminate",
                "search_failure": {"message": "unresolved variance family: sigma_zero"},
            },
            "family_fit_failed",
        ),
        ({"family_failures": ["constant: unresolved"]}, "family_fit_failed"),
        (
            {"errors": [{"stage": "search", "message": "boom"}], "multimodal": True},
            "numerical_error",
        ),
    ],
)
def test_failure_class_is_exactly_one_from_the_closed_list(
    fit: Any, kwargs: dict[str, Any], expected: str
) -> None:
    arguments: dict[str, Any] = {
        "search_status": "profile_numerically_resolved",
        "search_failure": None,
        "family_failures": [],
        "multimodal": False,
        "errors": [],
    }
    arguments.update(kwargs)
    result = fit.classify(**arguments)
    assert result["failure_class"] == expected
    assert result["failure_class"] in fit.FAILURE_CLASSES
    assert (result["message"] is None) == (expected == "resolved")


def synthetic_map(sites: int = 12) -> tuple[dict[str, np.ndarray], dict[str, Any], dict[str, Any]]:
    ids = np.asarray([f"s{i:02d}" for i in range(sites)])
    splits = np.asarray(["training"] * (sites - 2) + ["holdout"] * 2)
    record = {
        "baseline_site_ids": list(ids[:4]),
        "c_site_ids": list(ids[: sites - 2]),
        "holdout_site_ids": list(ids[sites - 2 :]),
    }
    rng = np.random.default_rng(3)
    full = {
        "prey_counts": rng.integers(0, 3, (sites, len(PREY_TIMES))).astype(np.int8),
        "predator_counts": rng.integers(0, 3, (sites, len(PREDATOR_TIMES))).astype(np.int8),
    }
    return {"site_ids": ids, "site_splits": splits}, record, full


@pytest.mark.parametrize("arm", ["A", "B", "C"])
def test_arm_arrays_follow_the_design_and_exclude_holdout(
    generate: Any, monkeypatch: pytest.MonkeyPatch, arm: str
) -> None:
    public, record, full = synthetic_map()
    monkeypatch.setattr(generate, "ARM_SITES", {"A": 4, "B": 4, "C": 10})
    arrays = generate.arm_arrays(full, public, record, arm)
    sites = set(map(str, arrays["site_ids"]))
    assert not sites & set(record["holdout_site_ids"])
    assert len(sites) == (10 if arm == "C" else 4)
    assert arrays["training_mask"].all()
    early = np.asarray(PREY_TIMES) <= 0
    assert arrays["prey_observed"][:, early].all() == (arm == "A")
    if arm != "A":
        assert not arrays["prey_observed"][:, early].any()
        assert not arrays["prey_counts"][:, early].any()
    network = arrays["predator_observed"].any(axis=1)
    assert int(network.sum()) == (4 if arm == "C" else len(sites))
    if arm == "C":
        assert set(np.asarray(arrays["site_ids"])[network]) == set(record["baseline_site_ids"])


def test_audit_covers_relevant_points_and_roots(fit: Any) -> None:
    criterion = small_criterion()
    row = {
        "parameters": {
            "alpha": -1.4,
            "beta": 0.2,
            "log_sigma": math.log(0.4),
            "detection_sd": 0.18,
        },
        "h": 3.0,
        "criterion": -10.0,
    }
    point = {"positive_sigma": row, "sigma_zero": {"criterion": -10.5}}
    far = {"positive_sigma": {**row, "criterion": -30.0}, "sigma_zero": {"criterion": -31.0}}
    search = SimpleNamespace(
        criterion=criterion,
        free={False: point, True: point},
        points={False: {0.0: point, 1.0: point, 2.0: far}, True: {1.0: point}},
        result={"level_sets": [{"roots": [{"log_h": 1.0}]}], "tight_level_sets": []},
    )
    audit = fit.audit_all(search, fit.load_mode_diagnosis())
    assert audit["locations"] == 6
    assert audit["audit_count"] == 5
    assert audit["skipped_beyond_lr_limit"] == 1
    skipped = [r for r in audit["rows"] if not r["performed"]]
    assert skipped[0]["log_h"] == 2.0 and skipped[0]["envelope_lr"] == pytest.approx(40.0)
    assert [r["kind"] for r in audit["rows"]].count("root") == 1
    assert not audit["multimodal_latent"]
