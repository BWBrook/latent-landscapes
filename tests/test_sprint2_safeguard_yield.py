from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def safeguard(monkeypatch: Any) -> Any:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("sprint2_safeguard_yield")


def spatial(score: float, eligible: bool = True, **extra: Any) -> dict[str, Any]:
    return {
        "criterion": score,
        "positive_sigma": {"eligible": eligible},
        "sigma_zero": {"eligible": True},
        **extra,
    }


def test_prefix_uses_latest_pre_tight_winners_and_exact_coordinates(safeguard: Any) -> None:
    last = safeguard.qualification.LOG_MAX
    zero = spatial(8.5, log_h=0.0, tight=False)
    endpoint = spatial(7.0, log_h=last, tight=False)
    free = spatial(10.0)
    times = [
        {"kind": "fixed_fit", "fit": spatial(8.0, log_h=0.0, tight=False)},
        {"kind": "fixed_fit", "fit": zero},
        {"kind": "fixed_fit", "fit": endpoint},
        {"kind": "free_fit", "tight": False, "fit": free},
        {"kind": "fixed_fit", "fit": spatial(8.6, log_h=0.0, tight=True)},
        {"kind": "free_fit", "tight": False, "fit": spatial(12.0)},
    ]
    tight_points = [
        spatial(8.6, False, log_h=0.0),
        spatial(7.2, log_h=last),
        spatial(8.9, log_h=1e-15),
    ]
    search = {
        "free": {"False": spatial(12.0), "True": spatial(10.2)},
        "points": {"False": [zero, endpoint], "True": tight_points},
    }
    encoded = "\n".join(map(json.dumps, times)).encode()
    topology = {
        "operation_count": 4,
        "spatial_sha256": safeguard.digest({"free": free, "points": [zero, endpoint]}),
    }
    result = safeguard.prefix_fit({}, search, encoded, topology)
    assert result["marker_zero_based_event"] == 4
    assert result["post_marker_standard_fit_events"] == 1
    tight = result["comparisons"]["primary_tight"]
    assert tight["prefix_h1_lr"] == 3.0
    assert tight["comparator_h1_lr"] == pytest.approx(3.2)
    assert tight["shared_exact_nodes"] == 2
    assert tight["comparator_only_nodes"] == 1
    assert tight["eligibility_changes"] == [{"location": 0.0, "family": "positive_sigma"}]
    assert len(tight["lr_changes_above_threshold"]) == 1
    for key, value in (("operation_count", 3), ("spatial_sha256", "invalid")):
        with pytest.raises(ValueError, match="disagree"):
            safeguard.prefix_fit({}, search, encoded, {**topology, key: value})


def test_distinguishes_early_standard_guard_from_unlocated_failure(safeguard: Any) -> None:
    search = {
        "status": "indeterminate",
        "failure": {
            "type": "RuntimeError",
            "message": "unresolved candidate exceeds selected family envelope",
        },
    }
    fit = {"failure_class": "search_unresolved"}
    event = {
        "kind": "unresolved_fit",
        "candidates": [{"source": "standard_fixed_0x1_neighbour_or_default_0_fit_0"}],
    }
    result = safeguard.prefix_fit(fit, search, json.dumps(event).encode())
    assert result["status"] == "known_standard_failure"
    data = b'{"kind":"midpoint_refinement_stagnation"}'
    assert safeguard.prefix_fit(fit, search, data)["status"] == "prefix_unavailable"


def test_omitting_audit_preserves_non_audit_failures(safeguard: Any) -> None:
    fit = {
        "failure_class": "numerical_error",
        "all_triggered": ["numerical_error", "multimodal_latent"],
        "errors": [{"execution": False, "stage": "latent_audit"}],
        "latent_audit": {"multimodal_latent": True},
        "search": {"status": "profile_numerically_resolved"},
        "families": {name: {"status": "available"} for name in ("spatial", "exposure", "constant")},
    }
    assert safeguard.without_latent_audit(fit)["pre_audit_failure_class"] == "resolved"
    fit["errors"].append({"execution": False, "stage": "spatial_report"})
    retained = safeguard.without_latent_audit(fit)
    assert retained["pre_audit_failure_class"] == "numerical_error"
    assert retained["omitted_flags"] == ["multimodal_latent"]
    fit["all_triggered"] = ["multimodal_latent"]
    with pytest.raises(ValueError, match="triggering flags"):
        safeguard.without_latent_audit(fit)


def test_censoring_bounds_do_not_assume_monotone_empirical_score(safeguard: Any) -> None:
    rows = []
    gate = safeguard.qualification
    for index in range(9):
        for i in range(18):
            # An extra failure in the only clean map can reduce the score.
            failed = index != 0 and i < 1
            unknown = index == 0 and i == 0
            status = "indeterminate" if unknown else "failed" if failed else "passed"
            rows.append(
                {
                    "map": str(index),
                    "arm": "ABC"[i % 3],
                    "stratum": "base",
                    "passed": status == "passed",
                    "complete": not unknown,
                    "checks": {"fit": {"status": status}},
                }
            )
    scores = []
    for complete_passed in (True, False):
        completion = [dict(rows[0], passed=complete_passed), *rows[1:]]
        scores.append(gate.finite_panel_gate(completion)["empirical_acceptance_score"])
    assert scores[1] < scores[0]
    result = safeguard.bounds(rows, ("A", "B", "C"))
    assert result["empirical_score_range"] == pytest.approx(sorted(scores))


def test_prefix_checkpoint_precedes_first_tight_and_replay_checks_topology(
    safeguard: Any, tmp_path: Path
) -> None:
    module = importlib.import_module("run_development_profile")
    store = importlib.import_module("fit_checkpoints")
    search = module.PanelSearch.__new__(module.PanelSearch)
    search.mode = "lean"
    search.points = {False: {}, True: {}}
    free = spatial(10.0)
    for family in module.FAMILIES:
        free[family]["h"] = 1.0
    search.free = {False: free}
    search.mesh = [0.0, module.LOG_MAX]
    search.checkpoints = store.FitCheckpoints(tmp_path, {"fixture": True}, resume=False)
    search.operation_index = 0

    def point(x: float, tight: bool = False, **kwargs: Any) -> None:
        if tight:
            saved = search.checkpoints.load("search/standard_prefix_topology")
            assert saved["level_sets"] == [{"cutoff": 3.84}]
            assert saved["operation_count"] == 0
            raise SystemExit("first tight fit")
        search.points[False][x] = spatial(9.0, tight=False, log_h=x)

    search.point = point
    search.fit_free = lambda: None
    search.refine_lean_peaks = lambda mesh: None
    search.midpoint_mesh = lambda mesh: mesh
    search.close_profiles = lambda mesh: ([{"cutoff": 3.84}], {"isolated": []})
    for _ in range(2):
        with pytest.raises(SystemExit, match="first tight fit"):
            search.run()
    assert search.result == {
        "schema": "development-profile-search-v1",
        "mode": "lean",
        "status": "indeterminate",
        "development_only": True,
        "calibration_claim": False,
        "globality_proven": False,
        "cutoffs": (3.84,),
        "truth_used_in_search": False,
    }
    search.close_profiles = lambda mesh: ([{"cutoff": 3.84}], {"isolated": [0.0]})
    with pytest.raises(store.CheckpointError, match="pre-tight topology differs"):
        search.run()


def test_audit_omission_does_not_promote_a_rescued_fit_without_sidecars(
    safeguard: Any, monkeypatch: Any, tmp_path: Path
) -> None:
    gate = safeguard.qualification
    row = {
        "dataset_id": "case",
        "map": "m",
        "archetype": "arc",
        "arm": "A",
        "stratum": "base",
        "independent_bank": False,
        "exhaustive_audit": False,
    }
    fit = {
        "schema": "fit-dataset-v1",
        "cutoffs": list(gate.CUTOFFS),
        "tight_replay": "always_on_inside_PanelSearch.run",
        "source": {"commit": "frozen", "working_tree_changes": []},
        "failure_class": "multimodal_latent",
        "all_triggered": ["multimodal_latent"],
        "errors": [],
        "latent_audit": {"multimodal_latent": True},
        "search": {"status": "profile_numerically_resolved"},
        "families": {name: {"status": "available"} for name in ("spatial", "exposure", "constant")},
        "input_sha256": {"observations.npz": "data"},
    }
    entry: dict[str, Any] = {"observation_sha256": "data"}
    for role in ("dense", "lean"):
        path = tmp_path / f"{role}.json"
        path.write_text(json.dumps({**fit, "search_mode": role}))
        entry[role] = {"path": path.name, "sha256": gate.digest(path)}
    monkeypatch.setattr(safeguard, "unchanged_report_counts", lambda fit: {})
    original = gate.assess_case(row, entry, gate.Evidence(tmp_path), "frozen")
    result = safeguard.assess_variants(row, entry, original, tmp_path, "frozen")
    assert safeguard.verdict(result["primary"]) == "failed"
    assert safeguard.verdict(result["audit_omitted"]) == "indeterminate"
    assert result["fits"]["dense"]["audit_omitted"]["pre_audit_failure_class"] == "resolved"


def test_final_index_keeps_all_207_denominators_when_evidence_is_absent(
    safeguard: Any, tmp_path: Path
) -> None:
    gate = safeguard.qualification
    rows = [
        {
            "dataset_id": f"{stratum}-{i}",
            "stratum": stratum,
            "map": f"map-{i // 18}" if stratum == "base" else f"map-{i % 9}",
            "archetype": "corridor",
            "arm": "ABC"[i % 3],
            "independent_bank": i < 54 and stratum == "base",
            "exhaustive_audit": i < 18 and stratum == "base",
            "integration_screen": i < 9 and stratum == "base",
        }
        for stratum, count in gate.COUNTS.items()
        for i in range(count)
    ]
    panel = {"schema": "paper1-fresh-qualification-panel-v1", "datasets": rows}
    panel_path, index_path, primary_path = (
        tmp_path / name for name in ("panel.json", "index.json", "primary.json")
    )
    panel_path.write_text(json.dumps(panel))
    index = {
        "panel_sha256": gate.digest(panel_path),
        "schema": "sprint2-qualification-index-v1",
        "source_commit": "synthetic",
        "cases": {},
    }
    index_path.write_text(json.dumps(index))
    primary = gate.summarise(panel, index, gate.Evidence(tmp_path))
    primary.update(panel_sha256=gate.digest(panel_path), index_sha256=gate.digest(index_path))
    primary_path.write_text(json.dumps(primary))
    result = safeguard.read_fresh(panel_path, index_path, primary_path)
    assert result["point_summary"]["required_fits"] == 486
    for variant in ("standard_prefix", "audit_omitted"):
        assert result[variant]["numerical_status"] == "incomplete"
        assert result[variant]["denominators"]["base"] == {"indeterminate": 162}
        assert len(result[variant]["nonbase_indeterminate"]) == 45
        assert result[variant]["abc_base_completion_bounds"]["base_pass_possible"] is True
        assert result[variant]["abc_base_completion_bounds"]["base_pass_guaranteed"] is False
        assert result["transitions"][variant]["paired_known_verdicts"] == 0
