from __future__ import annotations

import hashlib
import importlib.util
import math
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
        "qualify_spatial_profiles_test", root / "scripts/qualify_spatial_profiles.py"
    )
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def candidate(
    family: str,
    value: float,
    *,
    eligible: bool = True,
    h: float = 3.0,
    free: bool = False,
    source: str = "test",
) -> dict[str, Any]:
    values = {"alpha": -5.0, "beta": 0.3, "detection_sd": 0.2}
    if family == "positive_sigma":
        values["log_sigma"] = math.log(0.3)
    if free:
        values["log_h"] = math.log(h)
    return {
        "family": family,
        "criterion": value,
        "eligible": eligible,
        "h": h,
        "parameters": values,
        "source": source,
    }


def fit(module: Any, value: float, *, h: float = 3.0, free: bool = False) -> dict[str, Any]:
    return module.select_candidate_rows(
        [candidate(f, value, h=h, free=free) for f in module.FAMILIES]
    )


def bare_qualification(module: Any) -> Any:
    q = module.Qualification.__new__(module.Qualification)
    q.points = {False: {}, True: {}}
    q.free = {}
    q.directional = {}
    q.reference_points = {}
    q.closure_history = []
    q.midpoint_triggers = []
    q.record = lambda event: None
    return q


def parabolic_qualification(module: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    q = bare_qualification(module)
    q.args = SimpleNamespace(dense_baseline=True)
    q.reference = {
        "profile": {
            "best_positive": candidate("positive_sigma", 0.0, free=True),
            "best_sigma_zero": candidate("sigma_zero", -1.0, free=True),
        }
    }
    q.free[False] = fit(module, 0.0, free=True)
    q.direction_difference = lambda x: dict.fromkeys(module.FAMILIES, 0.0)

    def family_fit(**kwargs: Any) -> list[dict[str, Any]]:
        family = "sigma_zero" if kwargs["sigma_zero"] else "positive_sigma"
        value = -10000 * (math.log(kwargs["fixed_h"]) - 1.434) ** 2
        return [candidate(family, value - (family == "sigma_zero"), h=kwargs["fixed_h"])]

    q.criterion = SimpleNamespace(_fit_family=family_fit)
    monkeypatch.setattr(module.adapter, "_candidate_summary", lambda row, **kwargs: dict(row))
    return q


def test_midpoint_refines_smooth_peak_beyond_three_rounds(
    module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    q = parabolic_qualification(module, monkeypatch)
    mesh = np.linspace(0.0, module.LOG_MAX, 35).tolist()
    refined = q.midpoint_mesh(mesh)
    assert max(row["depth"] for row in q.midpoint_triggers) >= 3
    assert set(mesh).issubset(refined)
    assert len(refined) == len(q.points[False]) < 160
    assert max(q.points[False][x]["criterion"] for x in refined) >= -1e-4


def test_midpoint_refinement_stops_at_actual_unique_point_guard(
    module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    q = parabolic_qualification(module, monkeypatch)
    for x in np.linspace(0.0, 0.01, 158):
        q.point(float(x))
    q.point(module.LOG_MAX)
    with pytest.raises(RuntimeError, match="prespecified unique-point limit exhausted"):
        q.midpoint_mesh([0.0, module.LOG_MAX])
    assert len(q.points[False]) == 160
    assert max(row["depth"] for row in q.midpoint_triggers) == 1


def test_midpoint_stagnation_is_reported_as_unresolved(
    module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    q = parabolic_qualification(module, monkeypatch)
    events: list[dict[str, Any]] = []
    q.record = events.append
    a = 1.0
    b = math.nextafter(a, math.inf)
    with pytest.raises(RuntimeError, match="no representable midpoint"):
        q.midpoint_mesh([a, b])
    assert events[-1]["kind"] == "midpoint_refinement_stagnation"
    assert events[-1]["bracket_log_h"] == [a, b]
    assert len(q.points[False]) == 2


def test_up_and_down_candidates_are_preserved_and_best_is_not_overwritten(
    module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    q = bare_qualification(module)
    calls = {f: 0 for f in module.FAMILIES}

    def family_fit(**kwargs: Any) -> list[dict[str, Any]]:
        family = "sigma_zero" if kwargs["sigma_zero"] else "positive_sigma"
        calls[family] += 1
        return [
            candidate(
                family,
                10.0 if calls[family] == 1 else 9.0,
                h=kwargs["fixed_h"],
                source=str(calls[family]),
            )
        ]

    q.criterion = SimpleNamespace(_fit_family=family_fit)
    monkeypatch.setattr(module.adapter, "_candidate_summary", lambda row, **kwargs: dict(row))
    q.point(1.0, direction="up")
    down = q.point(1.0, refresh=True, direction="down")
    assert down["criterion"] == 10.0
    assert len(down["candidates"]) == 4
    assert q.direction_difference(1.0) == {f: -1.0 for f in module.FAMILIES}
    assert q.directional[1.0]["down"]["selected"]["positive_sigma"]["criterion"] == 9.0


def test_unresolved_candidate_above_local_or_free_envelope_is_not_dropped(module: Any) -> None:
    rows = [candidate(f, 5.0) for f in module.FAMILIES]
    rows.append(candidate("positive_sigma", 6.0, eligible=False))
    with pytest.raises(RuntimeError, match="unresolved candidate"):
        module.select_candidate_rows(rows)
    rows[-1]["criterion"] = 4.9
    resolved = module.select_candidate_rows(rows)
    violations = module.envelope_violations(fit(module, 4.0, free=True), [resolved])
    assert len(violations) == 3
    assert any(not row["eligible"] for row in violations)


def test_tight_points_and_superior_failed_points_seed_free_recovery(
    module: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    q = bare_qualification(module)
    q.reference = {
        "profile": {
            "best_positive": candidate("positive_sigma", 0.0, free=True),
            "best_sigma_zero": candidate("sigma_zero", 0.0, free=True),
        }
    }
    q.free[False] = fit(module, 1.0, free=True)
    q.points[False][0.2] = fit(module, 0.0, h=math.exp(0.2))
    q.points[True][1.0] = fit(module, 3.0, h=math.e)
    q.points[True][1.0]["candidates"].append(
        candidate("positive_sigma", 2.5, eligible=False, h=math.e)
    )
    starts = []

    def family_fit(**kwargs: Any) -> list[dict[str, Any]]:
        starts.extend(kwargs["starts"])
        f = "sigma_zero" if kwargs["sigma_zero"] else "positive_sigma"
        return [candidate(f, 3.1, free=True)]

    q.criterion = SimpleNamespace(_fit_family=family_fit)
    monkeypatch.setattr(module.adapter, "_candidate_summary", lambda row, **kwargs: dict(row))
    q.fit_free()
    assert q.free[False]["criterion"] == 3.1
    assert any(start[-2] == 1.0 for start in starts)


def test_dense_B0_rejects_reference_bank_identity_mismatch(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = np.zeros((131072, 1))
    path = tmp_path / "arrivals.npy"
    np.save(path, raw)
    compressed = tmp_path / "compressed.npz"
    compressed.write_bytes(b"mechanical compressed fixture")
    bank = SimpleNamespace(
        bank_size=131072,
        site_ids=("site",),
        series_order=192,
        max_x=40.0,
        bank_checksum=hashlib.sha256(raw.view(np.uint8)).hexdigest(),
    )
    monkeypatch.setattr(module.adapter, "load_compressed_bank", lambda _: bank)
    args = SimpleNamespace(
        bank_role="B0",
        dense_baseline=True,
        arrival_bank=path,
        compressed_bank=compressed,
        bank_manifest=None,
    )
    reference = {
        "inputs": {"bank_size": 131072},
        "source_identity": {
            "raw_arrival_bank": {"sha256": "wrong bank"},
            "arrival_bank": {"sha256": module.adapter.sha256_file(compressed)},
        },
    }
    with pytest.raises(ValueError, match="B0 must match"):
        module.validate_bank_identity(args, reference)
    args.bank_role = "A"
    with pytest.raises(ValueError, match="dense baseline"):
        module.validate_bank_identity(args, reference)


def test_tight_replay_cannot_omit_disconnected_component_or_move_endpoint(module: Any) -> None:
    reference = module.refine_level_set(
        lambda x: (x - 0.5) * (x - 1.0) * (x - 2.0) * (x - 2.5),
        np.linspace(0, math.log(30), 35),
        0.0,
    )
    omitted = module.refine_level_set(
        lambda x: (x - 0.5) * (x - 1.0), np.linspace(0, math.log(30), 35), 0.0
    )
    assert not module.compare_level_sets(reference, omitted)["passed"]
    moved = module.refine_level_set(
        lambda x: (x - 0.5) * (x - 1.02) * (x - 2.0) * (x - 2.5),
        np.linspace(0, math.log(30), 35),
        0.0,
    )
    assert not module.compare_level_sets(reference, moved)["passed"]
    assert module.compare_level_sets(reference, reference)["passed"]


def test_free_drift_recomputes_roots_and_unending_drift_stops(module: Any) -> None:
    def runner(drift_forever: bool) -> tuple[Any, int]:
        q = bare_qualification(module)
        q.free[False] = fit(module, 0.0, free=True)
        calls = 0

        def point(x: float, **kwargs: Any) -> dict[str, Any]:
            value = -0.5 * (x - 1.5) ** 2
            q.points[False].setdefault(x, fit(module, value, h=min(30, math.exp(x))))
            return q.points[False][x]

        q.point = point

        def fit_free(**kwargs: Any) -> None:
            nonlocal calls
            calls += 1
            value = 0.02 * calls if drift_forever else 0.02
            q.free[False] = fit(module, value, free=True)

        q.fit_free = fit_free
        q.switches = lambda *args, **kwargs: {"isolated": [], "tie_intervals": []}
        if drift_forever:
            with pytest.raises(RuntimeError, match="three passes"):
                q.close_profiles([0.0, 1.5, math.log(30)])
        else:
            levels, _ = q.close_profiles([0.0, 1.5, math.log(30)])
            assert calls == 2
            first = levels[0]["roots"][0]
            assert abs(first["log_h"] - (1.5 - math.sqrt(0.96))) < 1e-4
        return q, calls

    _, calls = runner(True)
    assert calls == 3
    runner(False)


@pytest.mark.parametrize(
    "matrix",
    [
        np.array([[math.nan]]),
        np.array([[math.inf]]),
        np.array([[-1.0]]),
        np.diag([1e-12, 1.0]),
        np.array([[1.0, 0.1], [0.0, 1.0]]),
    ],
)
def test_hessian_nonfinite_nonpositive_ill_conditioned_or_asymmetric_is_unavailable(
    module: Any, matrix: np.ndarray
) -> None:
    result = module.hessian_diagnostic(matrix, np.ones(len(matrix)))
    assert result["status"] == "unavailable"


def test_hessian_quadratic_scale_is_supplemental_and_explicit(module: Any) -> None:
    result = module.hessian_diagnostic(np.diag([2.0, 4.0]), np.array([0.2, 0.4]))
    assert result["status"] == "available"
    assert result["one_fit_lr_scale"] == pytest.approx(0.06)
    assert result["criterion_deficit"] == pytest.approx(0.03)


def test_constructor_filters_combined_rows_and_canonicalizes_log_keys(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    input_dir = tmp_path / "inputs"
    input_dir.mkdir()
    for name in ("public_inputs.npz", "exposure.npz"):
        (input_dir / name).write_bytes(b"mechanical identity")
    observations = tmp_path / "observations.npz"
    observations.write_bytes(b"mechanical observations")
    statuses = []
    for x in np.linspace(0, math.log(30), 35):
        for family in (*module.FAMILIES, "all_families"):
            statuses.append({"family": family, "h": float(np.exp(x)), "status": "resolved"})
    reference = tmp_path / "reference.json"
    reference.write_text(
        json.dumps(
            {
                "source_identity": {
                    "observations": {"sha256": module.adapter.sha256_file(observations)},
                    "public_inputs": {
                        "sha256": module.adapter.sha256_file(input_dir / "public_inputs.npz")
                    },
                    "exposure": {"sha256": module.adapter.sha256_file(input_dir / "exposure.npz")},
                },
                "profile": {"grid_statuses": statuses},
            }
        )
    )
    monkeypatch.setattr(module, "validate_bank_identity", lambda *args: {})
    monkeypatch.setattr(
        module,
        "load_data",
        lambda args: SimpleNamespace(
            observed=SimpleNamespace(
                site_ids=("site",),
                prey_times=(-60.0, 0.0),
                predator_times=(10.0,),
                cohort_start=-60.0,
            )
        ),
    )
    monkeypatch.setattr(
        module, "SpatialProfileCriterion", lambda *args, **kwargs: SimpleNamespace()
    )
    q = module.Qualification(
        SimpleNamespace(
            reference=reference, observations=observations, input_dir=input_dir, output_dir=tmp_path
        )
    )
    assert list(q.reference_points) == list(np.linspace(0, math.log(30), 35))
    assert all(set(row) == set(module.FAMILIES) for row in q.reference_points.values())


def test_archived_free_replay_compares_same_family_not_unknown_combined_envelope(
    module: Any,
) -> None:
    q = bare_qualification(module)
    q.args = SimpleNamespace(bank_role="B0")
    rows = [
        candidate("positive_sigma", 0.0, h=2.0, free=True),
        candidate("sigma_zero", -1.0, h=3.0, free=True),
    ]
    q.reference = {"profile": {"best_positive": rows[0], "best_sigma_zero": rows[1]}}
    q.reference_points = {
        0.0: {
            f: candidate(f, 0.0 if f == "positive_sigma" else -1.0, h=1.0) for f in module.FAMILIES
        }
    }
    q.free[False] = module.select_candidate_rows(rows)
    q.criterion = SimpleNamespace(
        evaluate_positive=lambda *args, **kwargs: SimpleNamespace(criterion=0.0, success=True),
        evaluate_sigma_zero=lambda *args, **kwargs: SimpleNamespace(criterion=-1.0, success=True),
    )
    q.point = lambda x, **kwargs: module.select_candidate_rows(
        [
            candidate("positive_sigma", 0.0, h=math.exp(x)),
            candidate("sigma_zero", -1.0, h=math.exp(x)),
        ]
    )
    replay = q.archived_replay()
    assert replay["passed"]
    zero = next(
        row for row in replay["comparisons"] if row["free"] and row["family"] == "sigma_zero"
    )
    assert zero["delta_w"] == 0.0
    assert zero["current_combined_w"] == 0.0
    assert not zero["archived_combined_w_available"]


def test_equality_plateau_does_not_fail_only_because_replay_has_more_knots(module: Any) -> None:
    standard = module.refine_level_set(lambda _: 1.0, [0.0, 1.0, math.log(30)], 1.0)
    tight = module.refine_level_set(lambda _: 1.0, [0.0, 0.5, 1.0, math.log(30)], 1.0)
    assert len(standard["roots"]) != len(tight["roots"])
    assert module.compare_level_sets(standard, tight)["passed"]


def test_complete_fake_profile_closes_before_reporting_and_hessian_is_supplemental(
    module: Any,
) -> None:
    import time

    q = bare_qualification(module)
    q.args = SimpleNamespace(bank_role="A", dense_baseline=False)
    q.bank_identity = {"role": "A"}
    q.data_identity = {"mechanical": True}
    q.started = time.perf_counter()
    q.stats = {}
    q.criterion = SimpleNamespace(stats={})
    maximum_h = math.exp(1.5)
    q.reference = {
        "profile": {
            "best_positive": candidate("positive_sigma", 0.0, h=maximum_h, free=True),
            "best_sigma_zero": candidate("sigma_zero", -1.0, h=maximum_h, free=True),
        }
    }

    def point(x: float, *, tight: bool = False, **kwargs: Any) -> dict[str, Any]:
        if x not in q.points[tight]:
            value = -0.5 * (x - 1.5) ** 2
            q.points[tight][x] = module.select_candidate_rows(
                [
                    candidate("positive_sigma", value, h=min(30.0, math.exp(x))),
                    candidate("sigma_zero", value - 1.0, h=min(30.0, math.exp(x))),
                ]
            )
        return q.points[tight][x]

    def free(*, tight: bool = False) -> None:
        q.free[tight] = module.select_candidate_rows(
            [
                candidate("positive_sigma", 0.0, h=maximum_h, free=True),
                candidate("sigma_zero", -1.0, h=maximum_h, free=True),
            ]
        )

    q.point = point
    q.fit_free = free
    q.midpoint_mesh = lambda mesh: mesh
    q.outer_diagnostic = lambda *args, **kwargs: {"status": "unavailable", "reason": "mechanical"}
    result = q.run()
    assert result["status"] == "profile_numerically_resolved", result.get("failure")
    assert all(row["passed"] for row in result["numerical_checks"])
    assert not any(result["final_envelope_violations"].values())
    assert result["bank_qualification"] == "external_cross_bank_gate_pending"
    assert result["diagnostic_w"]["3"]["standard"] == pytest.approx((math.log(3) - 1.5) ** 2)
