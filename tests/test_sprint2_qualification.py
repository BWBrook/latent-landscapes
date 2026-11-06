from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def reducer(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("summarise_sprint2_qualification")


def receipt(module: Any, mode: str = "lean") -> dict[str, Any]:
    points = [0.0, 0.5, 1.0, 2.0, module.LOG_MAX]
    parameters = {"alpha": -5.0, "beta": 0.1, "log_sigma": -1.0, "log_h": 0.0, "detection_sd": 0.2}

    def level(cutoff: float) -> dict[str, Any]:
        return {
            "cutoff": cutoff,
            "status": "available",
            "set_class": "full_domain",
            "roots_log_h": [],
            "touches_h1": True,
            "touches_h30": True,
            "empty": False,
            "components": [
                {
                    "lower_log_h": 0.0,
                    "upper_log_h": module.LOG_MAX,
                    "lower_domain_contact": True,
                    "upper_domain_contact": True,
                    "singleton": False,
                }
            ],
        }

    def view(spatial: bool) -> dict[str, Any]:
        free: dict[str, Any] = {"criterion": 0.0, "h": 1.0}
        free.update(
            {
                "tied": False,
                "nuisance_contacts": {"positive_sigma": []},
                "selected_family": "positive_sigma",
                "positive_sigma": {"h": 1.0, "parameters": parameters.copy()},
            }
            if spatial
            else {"nuisance_bound_contacts": []}
        )
        profile = []
        for x in points:
            row = {"log_h": x, "criterion": -0.1 * x, "w": 0.2 * x}
            row.update(
                {"tied": False, "nuisance_contacts": {"positive_sigma": []}}
                if spatial
                else {"eligible": True, "nuisance_bound_contacts": []}
            )
            profile.append(row)
        return {
            "free": free,
            "null": copy.deepcopy(free),
            "profile": profile,
            "level_sets": [level(c) for c in module.CUTOFFS],
        }

    return {
        "schema": "fit-dataset-v1",
        "failure_class": "resolved",
        "cutoffs": list(module.CUTOFFS),
        "search_mode": mode,
        "source": {"commit": "frozen", "working_tree_changes": []},
        "input_sha256": {"/input/observations.npz": "observations"},
        "tight_replay": "always_on_inside_PanelSearch.run",
        "families": {
            "spatial": {"status": "available", "standard": view(True), "tight": view(True)},
            "exposure": {"status": "available", **view(False)},
            "constant": {"status": "available", **view(False)},
        },
    }


def anchors(module: Any, left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "sprint2-common-anchors-v1",
        "status": "available",
        "views": {},
    }
    for name in module.VIEWS:
        lv, rv = module.view_of(left, name), module.view_of(right, name)
        xs = module.required_nodes(lv, module.profile_of(lv)) | module.required_nodes(
            rv, module.profile_of(rv)
        )
        result["views"][name] = {
            "rows": [
                {
                    "log_h": x,
                    "left": {"criterion": -0.1 * x, "nuisance_contacts": [], "eligible": True},
                    "right": {"criterion": -0.1 * x, "nuisance_contacts": [], "eligible": True},
                }
                for x in sorted(xs)
            ]
        }
    return result


def gradient(module: Any, left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "sprint2-free-gradient-v1",
        "status": "available",
        "checks": [],
    }
    for search, fit in (("dense", left), ("lean", right)):
        for regime in ("standard", "tight"):
            free = module.view_of(fit, f"spatial.{regime}")["free"]
            theta = free["positive_sigma"]["parameters"]
            for scale in (1e-4, 3e-5):
                result["checks"].append(
                    {
                        "search": search,
                        "regime": regime,
                        "step_scale": scale,
                        "family": "positive_sigma",
                        "coordinates": list(theta),
                        "parameters": theta.copy(),
                        "reoptimized": True,
                        "analytic": [0.0] * 5,
                        "finite_difference": [0.0] * 5,
                        "steps": [scale * max(1.0, abs(v)) for v in theta.values()],
                        "stencils": [
                            "central",
                            "central",
                            "central",
                            "forward_second_order",
                            "central",
                        ],
                    }
                )
    return result


def exhaustive(module: Any) -> dict[str, Any]:
    fit = receipt(module)
    rows = []
    for regime in ("standard", "tight"):
        view = module.view_of(fit, f"spatial.{regime}")
        for kind, x in [("free", 0.0), *[("point", p["log_h"]) for p in view["profile"]]]:
            rows.append(
                {
                    "tight": regime == "tight",
                    "kind": kind,
                    "log_h": x,
                    "sigma": 0.2,
                    "envelope_lr": 0.2 * x,
                    "performed": True,
                    "multimodal_latent": False,
                    "max_joint_gain": 0.0,
                    "max_criterion_gain": 0.0,
                    "beyond_lr_limit": False,
                }
            )
    fit["latent_audit"] = {
        "exhaustive": True,
        "multimodal_latent": False,
        "audit_count": len(rows),
        "locations": len(rows),
        "rows": rows,
    }
    return fit


def test_identical_receipts_pass_all_families_and_regimes(reducer: Any) -> None:
    result = reducer.compare_receipts(receipt(reducer, "dense"), receipt(reducer))
    assert result["passed"]
    assert set(result["metrics"]) == set(reducer.VIEWS)


def test_each_own_free_normalises_constant_criterion_offsets(reducer: Any) -> None:
    left, right = receipt(reducer), receipt(reducer)
    for name in reducer.VIEWS:
        view = reducer.view_of(right, name)
        for row in [view["free"], view["null"], *view["profile"]]:
            row["criterion"] += 2.0
    assert reducer.compare_receipts(left, right)["passed"]


@pytest.mark.parametrize("view", ["spatial.standard", "spatial.tight", "exposure", "constant"])
def test_w_threshold_applies_to_every_family_and_regime(reducer: Any, view: str) -> None:
    left, right = receipt(reducer), receipt(reducer)
    point = reducer.view_of(right, view)["profile"][2]
    point["criterion"] -= 0.015
    point["w"] += 0.03
    assert not reducer.compare_receipts(left, right)["passed"]
    assert reducer.compare_receipts(left, right, bank=True)["passed"]


def test_nonfinite_and_stale_w_are_not_passes(reducer: Any) -> None:
    left, right = receipt(reducer), receipt(reducer)
    right["families"]["constant"]["profile"][0]["w"] = 9.0
    assert reducer.compare_receipts(left, right)["status"] == "indeterminate"
    right["families"]["constant"]["profile"][0]["criterion"] = float("nan")
    assert not reducer.compare_receipts(left, right)["passed"]


def test_exact_union_anchors_required_and_detect_dense_only_discrepancy(reducer: Any) -> None:
    left, right = receipt(reducer), receipt(reducer)
    view = left["families"]["constant"]
    view["profile"].append(
        {
            "log_h": 1.5,
            "criterion": -0.15,
            "w": 0.3,
            "eligible": True,
            "nuisance_bound_contacts": [],
        }
    )
    assert not reducer.compare_receipts(left, right)["passed"]
    sidecar = anchors(reducer, left, right)
    assert reducer.compare_receipts(left, right, anchors=sidecar)["passed"]
    point = next(row for row in sidecar["views"]["constant"]["rows"] if row["log_h"] == 1.5)
    point["right"]["criterion"] -= 0.02
    assert reducer.compare_receipts(left, right, anchors=sidecar)["status"] == "failed"
    point["left"]["criterion"] += 0.01
    assert reducer.compare_receipts(left, right, anchors=sidecar)["status"] == "indeterminate"


def test_fewer_than_five_shared_nodes_do_not_pass_even_with_sidecar(reducer: Any) -> None:
    left, right = receipt(reducer), receipt(reducer)
    right["families"]["constant"]["profile"].pop(2)
    assert not reducer.compare_receipts(left, right, anchors=anchors(reducer, left, right))[
        "passed"
    ]


def test_topology_disagreement_has_no_tangency_waiver(reducer: Any) -> None:
    left, right = receipt(reducer), receipt(reducer)
    level = right["families"]["constant"]["level_sets"][0]
    level["components"].append(copy.deepcopy(level["components"][0]))
    level["tangency_margin"] = 0.0
    result = reducer.compare_receipts(left, right)
    assert not result["passed"]
    assert any("topology" in reason for reason in result["failures"])


@pytest.mark.parametrize("field", ["set_class", "touches_h1", "touches_h30", "empty"])
def test_set_flags_are_compared(reducer: Any, field: str) -> None:
    left, right = receipt(reducer), receipt(reducer)
    level = right["families"]["exposure"]["level_sets"][0]
    level[field] = "other" if field == "set_class" else not level[field]
    assert not reducer.compare_receipts(left, right)["passed"]


def test_missing_cutoff_is_indeterminate(reducer: Any) -> None:
    left, right = receipt(reducer), receipt(reducer)
    right["families"]["exposure"]["level_sets"].pop()
    assert reducer.compare_receipts(left, right)["status"] == "indeterminate"


def test_tie_rule_removes_only_redundant_contact(reducer: Any) -> None:
    left, right = receipt(reducer), receipt(reducer)
    free = right["families"]["spatial"]["standard"]["free"]
    free["tied"] = True
    free["nuisance_contacts"]["positive_sigma"] = ["log_sigma:lower"]
    assert reducer.compare_receipts(left, right)["passed"]
    free["nuisance_contacts"]["positive_sigma"].append("alpha:upper")
    assert not reducer.compare_receipts(left, right)["passed"]


def test_inside_contacts_are_checked(reducer: Any) -> None:
    left, right = receipt(reducer), receipt(reducer)
    right["families"]["constant"]["profile"][2]["nuisance_bound_contacts"] = ["alpha:upper"]
    result = reducer.compare_receipts(left, right)
    assert not result["passed"]
    assert any("inside-set contacts" in reason for reason in result["failures"])


def test_anchor_discovered_failure_is_scientific_not_missing(reducer: Any) -> None:
    result = reducer.compare_receipts(
        receipt(reducer),
        receipt(reducer),
        anchors={"status": "scientific_failure", "failures": ["new peak"]},
    )
    assert result["status"] == "failed"
    assert result["audit"]["failures"] == ["new peak"]


def test_gradient_requires_both_steps_and_inward_raw_boundary_derivative(reducer: Any) -> None:
    left, right = receipt(reducer, "dense"), receipt(reducer)
    sidecar = gradient(reducer, left, right)
    assert reducer.gradient_check(sidecar, left, right)["passed"]
    sidecar["checks"][0]["finite_difference"][3] = 0.01
    assert reducer.gradient_check(sidecar, left, right)["status"] == "failed"
    sidecar["checks"][0]["stencils"][3] = "central"
    assert reducer.gradient_check(sidecar, left, right)["status"] == "indeterminate"
    sidecar = gradient(reducer, left, right)
    sidecar["checks"].pop()
    assert reducer.gradient_check(sidecar, left, right)["status"] == "indeterminate"


def test_gradient_missing_status_cannot_be_success(reducer: Any) -> None:
    left = receipt(reducer)
    sidecar = gradient(reducer, left, left)
    del sidecar["status"]
    assert not reducer.gradient_check(sidecar, left, left)["passed"]


def test_exhaustive_margin_requires_complete_audit_and_checks_score_gain(reducer: Any) -> None:
    fit = exhaustive(reducer)
    assert reducer.exhaustive_check(fit)["passed"]
    row = fit["latent_audit"]["rows"][-1]
    row.update(beyond_lr_limit=True, envelope_lr=30.0, max_criterion_gain=5.01)
    assert reducer.exhaustive_check(fit)["status"] == "failed"
    fit["latent_audit"]["rows"].pop()
    assert reducer.exhaustive_check(fit)["status"] == "indeterminate"


def panel_rows() -> list[dict[str, Any]]:
    rows = []
    for index in range(9):
        for cell in range(6):
            for arm in "ABC":
                rows.append(
                    {
                        "dataset_id": f"base-{index}-{cell}-{arm}",
                        "map": f"map-{index}",
                        "archetype": f"archetype-{index // 3}",
                        "arm": arm,
                        "stratum": "base",
                        "independent_bank": False,
                        "exhaustive_audit": False,
                    }
                )
        for stratum, arms in (("boundary", "AC"), ("enriched", "BB"), ("trend", "A")):
            for j, arm in enumerate(arms):
                rows.append(
                    {
                        "dataset_id": f"{stratum}-{index}-{j}",
                        "map": f"map-{index}",
                        "archetype": f"archetype-{index // 3}",
                        "arm": arm,
                        "stratum": stratum,
                        "independent_bank": False,
                        "exhaustive_audit": False,
                    }
                )
    base = [r for r in rows if r["stratum"] == "base"]
    for i, row in enumerate(base):
        row.update(independent_bank=i < 54, exhaustive_audit=i < 18, integration_screen=i < 9)
    for row in rows:
        row.setdefault("integration_screen", False)
    return rows


def test_finite_panel_score_is_not_population_bound_and_missing_maps_fail(reducer: Any) -> None:
    rows = [{**r, "passed": True} for r in panel_rows()]
    gate = reducer.finite_panel_gate(rows)
    assert gate["passed"] and gate["empirical_acceptance_score"] == 0.0
    assert gate["population_confidence_bound"] is False
    assert not reducer.finite_panel_gate(rows[1:])["passed"]
    for row in rows:
        if row["map"] == "map-0" and row["stratum"] == "base" and row["arm"] == "C":
            row["passed"] = False
    assert not reducer.finite_panel_gate(rows)["passed"]
    assert reducer.finite_panel_gate(rows, arms=("A", "B"))["passed"]


def test_summary_ab_continuation_and_nonbase_repair(
    reducer: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    panel = {"datasets": panel_rows()}
    bad = {
        r["dataset_id"]
        for r in panel["datasets"]
        if r["stratum"] == "base" and r["map"] == "map-0" and r["arm"] == "C"
    }
    monkeypatch.setattr(
        reducer,
        "assess_case",
        lambda row, *args: {
            **row,
            "passed": row["dataset_id"] not in bad,
            "complete": True,
            "checks": {},
            "anchor_guard_evidence": {},
            "integration": {
                "complete": True,
                "status": "pointwise_screen_passed"
                if row["integration_screen"]
                else "not_selected",
            },
        },
    )
    index = {"schema": "sprint2-qualification-index-v1", "source_commit": "frozen", "cases": {}}
    result = reducer.summarise(panel, index, reducer.Evidence(tmp_path))
    assert result["status"] == "qualified_ab_only"
    assert result["training_authorised"] is False
    bad.add("enriched-0-0")
    result = reducer.summarise(panel, index, reducer.Evidence(tmp_path))
    assert result["status"] == "repair_required"
    assert result["denominators"]["enriched"] == {"total": 18, "passed": 17}


def test_missing_required_evidence_never_passes(reducer: Any, tmp_path: Path) -> None:
    row = panel_rows()[0]
    row.update(independent_bank=True, exhaustive_audit=True)
    result = reducer.assess_case(row, {}, reducer.Evidence(tmp_path), "frozen")
    assert not result["passed"] and not result["complete"]
    assert {"dense", "lean", "gradient", "bank_identity", "exhaustive"} <= result["checks"].keys()


def test_reference_hash_checked_before_loading(reducer: Any, tmp_path: Path) -> None:
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps({"schema": "example"}))
    evidence = reducer.Evidence(tmp_path)
    with pytest.raises(ValueError, match="checksum mismatch"):
        evidence.load({"path": path.name, "sha256": "wrong"})
    assert evidence.load({"path": path.name, "sha256": reducer.digest(path)})["schema"] == "example"


def write_reference(
    module: Any, directory: Path, name: str, value: dict[str, Any]
) -> dict[str, str]:
    path = directory / name
    path.write_text(json.dumps(value))
    return {"path": name, "sha256": module.digest(path)}


def test_terminal_scientific_failure_does_not_require_impossible_audits(
    reducer: Any, tmp_path: Path
) -> None:
    row = panel_rows()[0]
    row.update(independent_bank=False, exhaustive_audit=False, integration_screen=False)
    dense, lean = receipt(reducer, "dense"), receipt(reducer)
    dense.update(failure_class="family_fit_failed", families={})
    entry = {
        "observation_sha256": "observations",
        "dense": write_reference(reducer, tmp_path, "dense.json", dense),
        "lean": write_reference(reducer, tmp_path, "lean.json", lean),
    }
    result = reducer.assess_case(row, entry, reducer.Evidence(tmp_path), "frozen")
    assert result["complete"] and not result["passed"]
    assert (
        result["checks"]["dependent_audits"]["status"] == "not_applicable_due_to_scientific_failure"
    )
    del entry["lean"]
    result = reducer.assess_case(row, entry, reducer.Evidence(tmp_path), "frozen")
    assert not result["complete"] and not result["passed"]


def test_execution_failure_is_not_terminal_scientific_failure(reducer: Any, tmp_path: Path) -> None:
    row = panel_rows()[0]
    row.update(independent_bank=False, exhaustive_audit=False, integration_screen=False)
    dense, lean = receipt(reducer, "dense"), receipt(reducer)
    dense.update(failure_class="execution_error", families={})
    entry = {
        "observation_sha256": "observations",
        "dense": write_reference(reducer, tmp_path, "dense.json", dense),
        "lean": write_reference(reducer, tmp_path, "lean.json", lean),
    }
    result = reducer.assess_case(row, entry, reducer.Evidence(tmp_path), "frozen")
    assert not result["complete"] and not result["passed"]
    assert "dependent_audits" not in result["checks"]


def integration_receipt(fit: dict[str, Any], status: str = "indeterminate") -> dict[str, Any]:
    return {
        "schema": "sprint2-integration-screen-v1",
        "fit_receipt_sha256": "fit-hash",
        "maximum_draws": 262144,
        "descriptive_only": True,
        "status": status,
        "source_input_sha256": {**fit["input_sha256"], "/fit/receipt.json": "fit-hash"},
        "history": [{"draws_per_point_per_stream": 262144, "status": status}],
        "selected_anchors": [{"key": "free"}],
    }


def test_integration_indeterminate_is_completed_description_not_a_gate(reducer: Any) -> None:
    fit = receipt(reducer)
    sidecar = integration_receipt(fit)
    assert reducer.integration_check(sidecar, fit, "fit-hash")["complete"]
    sidecar["history"] = []
    assert not reducer.integration_check(sidecar, fit, "fit-hash")["complete"]
    sidecar.update(status="unavailable", reason="invalid importance target at retained fit")
    assert reducer.integration_check(sidecar, fit, "fit-hash")["complete"]
    del sidecar["source_input_sha256"]
    assert not reducer.integration_check(sidecar, fit, "fit-hash")["complete"]


def test_unavailable_scientific_screen_requires_failed_parent(reducer: Any) -> None:
    fit = receipt(reducer)
    sidecar = integration_receipt(fit, "unavailable_scientific_fit")
    sidecar["reason"] = "unresolved fit"
    assert not reducer.integration_check(sidecar, fit, "fit-hash")["complete"]
    fit["failure_class"] = "search_unresolved"
    assert reducer.integration_check(sidecar, fit, "fit-hash")["complete"]


def test_anchor_guard_counts_verified_sources_and_reports_missing_stream(
    reducer: Any, tmp_path: Path
) -> None:
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps(
            {
                "kind": "unresolved_fit",
                "candidates": [
                    {
                        "family": "positive_sigma",
                        "eligible": True,
                        "criterion": 10.0,
                        "source": "default",
                    },
                    {
                        "family": "sigma_zero",
                        "eligible": True,
                        "criterion": 9.0,
                        "source": "default",
                    },
                    {
                        "family": "positive_sigma",
                        "eligible": False,
                        "criterion": 10.2,
                        "source": "tight_fixed_high_sigma_anchor_1",
                    },
                    {
                        "family": "positive_sigma",
                        "eligible": False,
                        "criterion": 9.9,
                        "source": "neighbour",
                    },
                ],
            }
        )
        + "\n"
    )
    child = write_reference(
        reducer,
        tmp_path,
        "search.json",
        {"evaluation_stream": {"path": events.name, "sha256": reducer.digest(events)}},
    )
    fit = {"search": {"receipt": child["path"], "receipt_sha256": child["sha256"]}}
    evidence = reducer.Evidence(tmp_path)
    result = evidence.anchor_guards(fit)
    assert result["status"] == "available"
    assert result["high_sigma_anchor_offending_candidates"] == 1
    assert result["other_offending_candidates"] == 0
    events.write_text("{}\n")
    assert evidence.anchor_guards(fit)["status"] == "unavailable"


def test_missing_integration_stops_packet_completion_not_numerical_score(
    reducer: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    panel = {"datasets": panel_rows()}
    monkeypatch.setattr(
        reducer,
        "assess_case",
        lambda row, *args: {
            **row,
            "passed": True,
            "complete": True,
            "checks": {},
            "anchor_guard_evidence": {},
            "integration": {"complete": False, "status": "missing_or_invalid"},
        },
    )
    index = {"schema": "sprint2-qualification-index-v1", "source_commit": "frozen", "cases": {}}
    result = reducer.summarise(panel, index, reducer.Evidence(tmp_path))
    assert result["numerical_status"] == "qualified_finite_panel"
    assert result["status"] == "numerically_qualified_packet_incomplete"
    assert not result["packet_complete"]


def test_root_location_and_root_contacts_compared(reducer: Any) -> None:
    left, right = receipt(reducer), receipt(reducer)
    for fit in (left, right):
        level = fit["families"]["constant"]["level_sets"][0]
        level.update(set_class="bounded", roots_log_h=[0.5], touches_h1=False)
        level["components"][0].update(lower_log_h=0.5, lower_domain_contact=False)
    assert reducer.compare_receipts(left, right)["passed"]
    right["families"]["constant"]["profile"][1]["nuisance_bound_contacts"] = ["alpha:upper"]
    result = reducer.compare_receipts(left, right)
    assert not result["passed"]
    assert any("root contacts differ" in reason for reason in result["failures"])
    right["families"]["constant"]["profile"][1]["nuisance_bound_contacts"] = []
    level = right["families"]["constant"]["level_sets"][0]
    level["roots_log_h"] = [1.0]
    level["components"][0]["lower_log_h"] = 1.0
    assert any(
        "root moved" in reason for reason in reducer.compare_receipts(left, right)["failures"]
    )


def test_no_root_integration_is_descriptive_completion_without_lr_pass(reducer: Any) -> None:
    fit = receipt(reducer)
    sidecar = integration_receipt(fit, "no_root_contrasts")
    result = reducer.integration_check(sidecar, fit, "fit-hash")
    assert result["complete"] and result["status"] == "no_root_contrasts"
    assert result["lr_screen_passed"] is False
    sidecar["selected_anchors"].append({"key": "root-0"})
    assert not reducer.integration_check(sidecar, fit, "fit-hash")["complete"]
    sidecar = integration_receipt(fit, "pointwise_screen_passed")
    assert not reducer.integration_check(sidecar, fit, "fit-hash")["complete"]
    sidecar = integration_receipt(fit, "no_root_contrasts")
    reducer.levels_of(reducer.view_of(fit, "spatial.tight"))[3.84]["roots_log_h"] = [0.5]
    assert not reducer.integration_check(sidecar, fit, "fit-hash")["complete"]
