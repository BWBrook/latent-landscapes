from __future__ import annotations

import copy
import importlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest


@pytest.fixture
def audit(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("audit_sprint2_pair")


def level_sets(module: Any) -> list[dict[str, Any]]:
    centre = 1.5
    result = []
    for cutoff in module.fit.CUTOFF_GRID:
        half = math.sqrt(cutoff / 2.0)
        lower, upper = max(0.0, centre - half), min(module.LOG_MAX, centre + half)
        roots = [x for x in (centre - half, centre + half) if 0.0 < x < module.LOG_MAX]
        result.append(
            {
                "cutoff": cutoff,
                "status": "available",
                "set_class": "fixture",
                "roots_log_h": roots,
                "roots": [
                    {"log_h": x, "verification_bracket_log_h": [x - 2e-4, x + 2e-4]} for x in roots
                ],
                "residual_tolerance": 0.01,
                "components": [
                    {
                        "lower_log_h": lower,
                        "upper_log_h": upper,
                        "lower_domain_contact": lower == 0.0,
                        "upper_domain_contact": upper == module.LOG_MAX,
                        "singleton": False,
                    }
                ],
                "touches_h1": lower == 0.0,
                "touches_h30": upper == module.LOG_MAX,
                "empty": False,
            }
        )
    return result


def evidence(module: Any, mode: str, *, offset: float = 0.0) -> Any:
    nodes = [0.0, 0.5, 1.0, 2.0, module.LOG_MAX, 0.75 if mode == "dense" else 1.25]
    free_parameters = {"alpha": -5.0, "beta": 0.2, "log_h": 1.5, "detection_sd": 0.2}
    row = {
        "family": "sigma_zero",
        "h": math.exp(1.5),
        "criterion": offset,
        "parameters": free_parameters,
        "eligible": True,
        "nuisance_bound_contacts": [],
    }
    positive = {
        **row,
        "family": "positive_sigma",
        "criterion": offset - 0.5,
        "parameters": {**free_parameters, "log_sigma": math.log(0.3)},
    }
    spatial_free = {
        "criterion": offset,
        "h": math.exp(1.5),
        "selected_family": "sigma_zero",
        "positive_sigma": positive,
        "sigma_zero": row,
        "tied": False,
        "nuisance_contacts": {"sigma_zero": []},
    }
    spatial_profile = [
        {
            "log_h": x,
            "criterion": offset - (x - 1.5) ** 2,
            "w": 2.0 * (x - 1.5) ** 2,
            "tied": False,
            "nuisance_contacts": {"sigma_zero": []},
        }
        for x in nodes
    ]
    spatial = {
        "free": spatial_free,
        "null": {**spatial_free, "criterion": offset - 1.5**2},
        "profile": spatial_profile,
        "level_sets": level_sets(module),
    }
    reduced = {
        "status": "available",
        "free": row,
        "null": {**row, "h": 1.0, "criterion": offset - 1.5**2},
        "profile": [
            {**r, "nuisance_bound_contacts": [], "parameters": free_parameters, "eligible": True}
            for r in spatial_profile
        ],
        "level_sets": level_sets(module),
    }
    args = SimpleNamespace(
        input_dir=Path("/fixture"),
        observations=Path("/fixture/observations.npz"),
        arrival_bank=Path(f"/fixture/bank-{offset}.npz"),
        compressed_bank=Path(f"/fixture/compressed-{offset}.npz"),
    )
    hashes = {
        "/fixture/public_inputs.npz": "public",
        "/fixture/exposure.npz": "exposure",
        str(args.observations): "observations",
        str(args.arrival_bank): f"bank-{offset}",
        str(args.compressed_bank): f"compressed-{offset}",
    }
    receipt = {
        "schema": "fit-dataset-v1",
        "failure_class": "resolved",
        "cutoffs": list(module.fit.CUTOFF_GRID),
        "tight_replay": "always_on_inside_PanelSearch.run",
        "source": {"commit": "frozen", "working_tree_changes": []},
        "search_mode": mode,
        "data_identity": {"site_count": 6},
        "input_sha256": hashes,
        "families": {
            "spatial": {
                "status": "available",
                "standard": spatial,
                "tight": copy.deepcopy(spatial),
            },
            "exposure": reduced,
            "constant": copy.deepcopy(reduced),
        },
        "search": {"receipt": "/fixture/search.json", "receipt_sha256": "search"},
    }
    search = {"level_sets": level_sets(module), "tight_level_sets": level_sets(module)}
    return module.Evidence(
        Path(f"/fixture/{mode}-{offset}/receipt.json"), receipt, search, args, f"{mode}-{offset}"
    )


class QuadraticCriterion:
    def __init__(self, module: Any):
        self._bounds = module.fit.SpatialProfileCriterion._bounds
        self.calls: list[tuple[np.ndarray, bool]] = []

    def evaluate(self, point: np.ndarray, *, nuisance_fd: bool) -> Any:
        self.calls.append((point.copy(), nuisance_fd))
        weights = np.arange(1.0, len(point) + 1.0)
        return SimpleNamespace(
            success=True,
            criterion=float(np.dot(weights, point * point)),
            criterion_gradient=2.0 * weights * point,
        )

    evaluate_positive = evaluate
    evaluate_sigma_zero = evaluate


@pytest.mark.parametrize("family", ["positive_sigma", "sigma_zero"])
@pytest.mark.parametrize("scale", [1e-4, 3e-5])
def test_raw_gradient_uses_reoptimised_inward_and_central_stencils(
    audit: Any, family: str, scale: float
) -> None:
    criterion = QuadraticCriterion(audit)
    params = {"alpha": -12.0, "beta": 2.0, "log_h": audit.LOG_MAX, "detection_sd": 0.18}
    if family == "positive_sigma":
        params = {
            "alpha": -12.0,
            "beta": 2.0,
            "log_sigma": math.log(1e-4),
            "log_h": audit.LOG_MAX,
            "detection_sd": 0.18,
        }
    point = np.array(list(params.values()))
    value = criterion.evaluate(point, nuisance_fd=False).criterion
    criterion.calls.clear()
    result = audit.gradient_check(
        criterion, {"family": family, "parameters": params, "criterion": value}, scale
    )
    assert all(result["component_passed"])
    assert result["stencils"][0:2] == ["forward_second_order", "backward_second_order"]
    assert result["stencils"][-2:] == ["backward_second_order", "central"]
    assert result["analytic"][0] == -24.0
    assert result["reoptimized"] is True
    assert len(criterion.calls) == 1 + sum(len(r["offsets"]) for r in result["stencil_evaluations"])
    assert sum(analytic for _, analytic in criterion.calls) == 1


def test_gradient_failed_stencil_is_unavailable(audit: Any) -> None:
    criterion = QuadraticCriterion(audit)
    original = criterion.evaluate_sigma_zero

    def fail(point: np.ndarray, *, nuisance_fd: bool) -> Any:
        result = original(point, nuisance_fd=nuisance_fd)
        result.success = nuisance_fd
        return result

    criterion.evaluate_sigma_zero = fail  # type: ignore[method-assign]
    params = {"alpha": -5.0, "beta": 0.2, "log_h": 1.5, "detection_sd": 0.18}
    value = original(np.array(list(params.values())), nuisance_fd=False).criterion
    with pytest.raises(ValueError, match="unavailable reoptimised stencil"):
        audit.gradient_check(
            criterion, {"family": "sigma_zero", "parameters": params, "criterion": value}, 1e-4
        )


def test_original_anchor_keeps_score_but_reports_probe_failure(audit: Any) -> None:
    item = evidence(audit, "dense")
    x = 0.5
    original = audit.view_of(item.receipt, "constant")["profile"][1]["criterion"]
    probe = {"criterion": 1.0, "eligible": True, "nuisance_contacts": [], "fit": {}}
    result, failures = audit.anchor_record(item, "constant", x, probe)
    assert result["criterion"] == original
    assert result["probe_criterion"] == 1.0
    assert any("frozen free maximum" in failure for failure in failures)
    assert any("original node" in failure for failure in failures)
    assert item.receipt["families"]["constant"]["free"]["criterion"] == 0.0


def test_anchor_replay_uses_existing_pointwise_tolerance(audit: Any) -> None:
    item = evidence(audit, "dense")
    probe = {"criterion": -1.0 + 0.004, "eligible": True, "nuisance_contacts": [], "fit": {}}
    _, failures = audit.anchor_record(item, "constant", 0.5, probe)
    assert failures == []
    probe["criterion"] = -1.0 + 0.006
    _, failures = audit.anchor_record(item, "constant", 0.5, probe)
    assert any("0.01 W" in failure for failure in failures)


@pytest.mark.parametrize("bank", [False, True])
def test_exact_anchor_union_normalises_independent_score_offsets(
    audit: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bank: bool
) -> None:
    left, right = (
        evidence(audit, "lean" if bank else "dense"),
        evidence(audit, "lean", offset=100.0 if bank else 0.0),
    )
    calls: list[tuple[str, str, float]] = []

    class Probe:
        def __init__(self, item: Any, output: Path):
            self.item = item

        def evaluate(self, name: str, x: float, budget: int) -> dict[str, Any]:
            calls.append((self.item.sha256, name, x))
            maximum = audit.view_of(self.item.receipt, name)["free"]["criterion"]
            return {
                "criterion": maximum - (x - 1.5) ** 2,
                "eligible": True,
                "nuisance_contacts": [],
                "fit": {},
            }

    monkeypatch.setattr(audit, "Probe", Probe)
    monkeypatch.setattr(audit.Evidence, "verify_unchanged", lambda self: None)
    result = audit.audit_anchors(
        left, right, "independent_bank" if bank else "dense_lean", tmp_path
    )
    assert result["status"] == "available", result
    for view, group in result["views"].items():
        wanted = audit.required_nodes(audit.view_of(left.receipt, view)) | audit.required_nodes(
            audit.view_of(right.receipt, view)
        )
        assert {r["log_h"] for r in group["rows"]} == wanted
        assert all(
            (left.sha256, view, x) in calls and (right.sha256, view, x) in calls for x in wanted
        )
    reducer = importlib.import_module("summarise_sprint2_qualification")
    comparison = reducer.compare_receipts(left.receipt, right.receipt, bank=bank, anchors=result)
    assert comparison["passed"], comparison
    assert max(row["max_abs_delta_w"] for row in comparison["metrics"].values()) < 1e-12


def test_pair_rejects_identical_independent_banks_and_changed_observations(audit: Any) -> None:
    left, right = evidence(audit, "lean"), evidence(audit, "lean")
    with pytest.raises(ValueError, match="arrival_bank"):
        audit.verify_pair(left, right, "independent_bank")
    left.receipt["search_mode"] = "dense"
    right.receipt["input_sha256"]["/fixture/observations.npz"] = "other"
    with pytest.raises(ValueError, match="observations"):
        audit.verify_pair(left, right, "dense_lean")


def test_evidence_rejects_dirty_source_before_loading_data(
    audit: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "receipt.json"
    path.write_text(
        '{"schema":"fit-dataset-v1","failure_class":"resolved",'
        '"source":{"commit":"frozen","working_tree_changes":[" M changed.py"]}}'
    )
    monkeypatch.setattr(
        audit.fit.adapter,
        "_git_identity",
        lambda root: {"commit": "frozen", "working_tree_changes": []},
    )
    with pytest.raises(ValueError, match="original clean source"):
        audit.Evidence.load(path)


def test_evidence_binds_nested_receipt_and_rechecks_input_hashes(
    audit: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item = evidence(audit, "dense")
    source = {"commit": "frozen", "working_tree_changes": []}
    monkeypatch.setattr(audit.adapter, "_git_identity", lambda root: source)
    payload = tmp_path / "observations.npz"
    payload.write_bytes(b"initial")

    def hashes(args: Any) -> dict[str, str]:
        return {str(payload): audit.adapter.sha256_file(payload)}

    monkeypatch.setattr(audit.fit, "input_hashes", hashes)
    root = item.receipt
    root["inputs"] = {key: str(value) for key, value in vars(item.args).items()}
    root["input_sha256"] = hashes(None)
    nested = tmp_path / "search.json"
    nested.write_text(
        json.dumps(
            {
                "status": "profile_numerically_resolved",
                "free": {
                    str(t): root["families"]["spatial"][r]["free"]
                    for t, r in ((False, "standard"), (True, "tight"))
                },
            }
        )
    )
    root["search"] = {"receipt": str(nested), "receipt_sha256": audit.adapter.sha256_file(nested)}
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(root))
    loaded = audit.Evidence.load(path)
    assert loaded.sha256 == audit.adapter.sha256_file(path)
    payload.write_bytes(b"changed")
    with pytest.raises(ValueError, match="input/source bytes changed"):
        loaded.verify_unchanged()
    payload.write_bytes(b"initial")
    nested.write_text("{}")
    with pytest.raises(ValueError, match="nested search receipt hash changed"):
        audit.Evidence.load(path)


@pytest.mark.parametrize(
    "error,expected",
    [
        (MemoryError("memory"), "execution_error"),
        (OSError("filesystem"), "execution_error"),
        (RuntimeError("unresolved family"), "scientific_failure"),
        (FloatingPointError("numeric"), "scientific_failure"),
        (ValueError("missing stencil"), "unavailable"),
    ],
)
def test_audit_error_classes_preserve_retry_boundary(
    audit: Any, error: Exception, expected: str
) -> None:
    result = {"errors": [audit.error_record("probe", error, numerical=True)], "failures": []}
    assert audit.status_of(result) == expected
    assert audit.error_record("metadata", RuntimeError("identity"))["status"] == "unavailable"


def test_execution_error_writes_receipt_then_exits_nonzero(
    audit: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "audit"
    monkeypatch.setattr(
        "sys.argv",
        [
            "audit_sprint2_pair.py",
            "anchors",
            "--kind",
            "dense_lean",
            "--left-receipt",
            "left.json",
            "--right-receipt",
            "right.json",
            "--output-dir",
            str(output),
        ],
    )
    for name in audit.fit.THREAD_ENVIRONMENT:
        monkeypatch.setenv(name, "1")

    def fail(path: Path) -> Any:
        raise MemoryError("injected resource failure")

    monkeypatch.setattr(audit.Evidence, "load", fail)
    assert audit.main() == 2
    receipt = json.loads((output / "receipt.json").read_text())
    assert receipt["schema"] == "sprint2-common-anchors-v1"
    assert receipt["status"] == "execution_error"


def test_tight_probe_preserves_its_original_parameter_start(audit: Any) -> None:
    def row(alpha: float) -> dict[str, Any]:
        return {
            "family": "sigma_zero",
            "parameters": {"alpha": alpha, "beta": 0.2, "detection_sd": 0.18},
        }

    search = audit.AnchorSearch.__new__(audit.AnchorSearch)
    search.original_points = {False: {}, True: {1.0: {"sigma_zero": row(-5.0)}}}
    search.points = {False: {1.0: {"sigma_zero": row(-6.0)}}, True: {}}
    search.reference_points = {}
    search.free = {True: {"sigma_zero": row(-7.0)}}
    starts = search.neighbours(1.0, "sigma_zero", True)
    assert starts[0][0] == -5.0
    assert {-5.0, -6.0, -7.0} <= {start[0] for start in starts}


def test_gradient_sidecar_covers_eight_checks_and_matches_reducer(
    audit: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dense, lean = evidence(audit, "dense"), evidence(audit, "lean")
    for item in (dense, lean):
        for regime in ("standard", "tight"):
            free = audit.view_of(item.receipt, f"spatial.{regime}")["free"]
            row = free[free["selected_family"]]
            criterion = QuadraticCriterion(audit)
            row["criterion"] = criterion.evaluate(
                np.array(list(row["parameters"].values())), nuisance_fd=False
            ).criterion

    class Probe:
        def __init__(self, item: Any, output: Path):
            self.search = SimpleNamespace(criterion=QuadraticCriterion(audit))

    monkeypatch.setattr(audit, "Probe", Probe)
    monkeypatch.setattr(audit.Evidence, "verify_unchanged", lambda self: None)
    result = audit.audit_gradients(dense, lean, tmp_path)
    assert result["status"] == "available", result
    assert len(result["checks"]) == 8
    reducer = importlib.import_module("summarise_sprint2_qualification")
    checked = reducer.gradient_check(result, dense.receipt, lean.receipt)
    assert checked["passed"], checked
