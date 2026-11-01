from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any, cast

import pytest


@pytest.fixture
def module() -> Any:
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "development_challenge_summary_test",
        root / "scripts/summarize_development_challenge.py",
    )
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def selected_fit(
    x: float,
    *,
    positive_criterion: float = 10.0,
    zero_criterion: float = 8.0,
    log_sigma: float = -1.0,
    sigma_contacts: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "log_h": x,
        "h": math.exp(x),
        "criterion": max(positive_criterion, zero_criterion),
        "positive_sigma": {
            "criterion": positive_criterion,
            "h": math.exp(x),
            "parameters": {"log_sigma": log_sigma},
            "nuisance_bound_contacts": sigma_contacts or [],
        },
        "sigma_zero": {
            "criterion": zero_criterion,
            "h": math.exp(x),
            "parameters": {},
            "nuisance_bound_contacts": [],
        },
    }


def dense_receipt(
    *,
    roots: tuple[float, float] = (0.0, 2.0),
    component: tuple[float, float] | None = None,
    domain_contact: bool = False,
    owner: str = "positive_sigma",
) -> dict[str, Any]:
    lower, upper = component or roots
    criteria = (10.0, 8.0) if owner == "positive_sigma" else (8.0, 10.0)
    points = [
        selected_fit(
            0.0,
            positive_criterion=criteria[0],
            zero_criterion=criteria[1],
            log_sigma=0.0,
        ),
        selected_fit(
            1.0,
            positive_criterion=criteria[0],
            zero_criterion=criteria[1],
            log_sigma=0.0,
        ),
        selected_fit(
            2.0,
            positive_criterion=criteria[0],
            zero_criterion=criteria[1],
            log_sigma=2.0,
        ),
    ]
    free = selected_fit(
        1.2,
        positive_criterion=criteria[0],
        zero_criterion=criteria[1],
        log_sigma=math.log(0.4),
    )
    return {
        "schema": "development-profile-search-v1",
        "mode": "dense",
        "status": "profile_numerically_resolved",
        "free": {"True": free},
        "maximum": {
            "True": {
                "status": "selected_maximum",
                "effect_estimate": math.exp(1.2),
                "selected_computational_h": math.exp(1.2),
            }
        },
        "points": {"True": points},
        "tight_level_sets": [
            {
                "status": "available",
                "cutoff": 3.84,
                "set_class": "bounded",
                "components": [
                    {
                        "lower_log_h": lower,
                        "upper_log_h": upper,
                        "lower_domain_contact": domain_contact,
                        "upper_domain_contact": False,
                        "singleton": False,
                    }
                ],
                "roots": [{"log_h": roots[0]}, {"log_h": roots[1]}],
            }
        ],
        "tight_family_switches": {"isolated": [], "tie_intervals": []},
        "post_search_diagnostics": {
            "status": "available",
            "points": [
                {"log_h": 0.0, "tight_w": 2.5},
                {"log_h": 1.0, "tight_w": 1.25},
            ],
        },
        "cost": {
            "search": {
                "elapsed_seconds": 12.0,
                "standard_unique_h": 21,
                "tight_unique_h": 23,
                "fixed_fit_events": 88,
            },
            "post_search_seconds": 3.5,
            "total_fixed_fit_events": 104,
        },
    }


def profile_run(
    tmp_path: Path, dense: dict[str, Any], *, name: str = "profile", paired: bool = True
) -> Path:
    directory = tmp_path / name
    dense_path = directory / "dense" / "receipt.json"
    write_json(dense_path, dense)
    digest = __import__("hashlib").sha256(dense_path.read_bytes()).hexdigest()
    searches = {"dense": {"path": str(dense_path), "sha256": digest}}
    if paired:
        lean = json.loads(json.dumps(dense))
        lean["mode"] = "lean"
        lean_path = directory / "lean" / "receipt.json"
        write_json(lean_path, lean)
        searches["lean"] = {
            "path": str(lean_path),
            "sha256": hashlib.sha256(lean_path.read_bytes()).hexdigest(),
        }
    write_json(
        directory / "receipt.json",
        {
            "schema": "development-profile-run-v1",
            "status": "within_prespecified_gates" if paired else "profile_numerically_resolved",
            "searches": searches,
        },
    )
    return directory


def job(profile: Path, **overrides: Any) -> dict[str, Any]:
    result = {
        "dataset_id": "d-A",
        "biological_history_id": "history-1",
        "arm": "A",
        "bank_role": "B0",
        "profile_dir": str(profile),
        "report_h": math.e,
        "site_count": 120,
    }
    result.update(overrides)
    dataset_id = str(result["dataset_id"])
    bank_role = str(result["bank_role"])
    input_dir = Path(str(result.get("input_dir", profile / "inputs" / dataset_id)))
    observations = Path(
        str(result.get("observations", profile / "inputs" / dataset_id / "observations.npz"))
    )
    arrival_bank = Path(
        str(result.get("arrival_bank", profile / "inputs" / f"arrivals-{bank_role}.npy"))
    )
    compressed_bank = Path(
        str(result.get("compressed_bank", profile / "inputs" / f"compressed-{bank_role}.npz"))
    )
    paths = (
        observations,
        arrival_bank,
        compressed_bank,
        input_dir / "public_inputs.npz",
        input_dir / "exposure.npz",
    )
    input_sha256 = {
        str(path.resolve()): hashlib.sha256(str(path.resolve()).encode()).hexdigest()
        for path in paths
    }
    result.update(
        input_dir=str(input_dir),
        observations=str(observations),
        observations_sha256=input_sha256[str(observations.resolve())],
        arrival_bank=str(arrival_bank),
        compressed_bank=str(compressed_bank),
        input_sha256=input_sha256,
    )
    parent_path = profile / "receipt.json"
    parent = json.loads(parent_path.read_text())
    parent["source_input_sha256"] = input_sha256
    parent["data_identity"] = {
        "site_count": int(cast(int, result["site_count"])),
        "fixture": dataset_id,
    }
    write_json(parent_path, parent)
    return result


def test_uniform_piecewise_linear_slope_integrates_the_ridge(module: Any) -> None:
    first = module.uniform_piecewise_linear_slope([(0.0, 0.0), (1.0, 0.0), (2.0, 2.0)])
    second = module.uniform_piecewise_linear_slope([(0.0, 3.0), (0.5, 2.0), (2.0, -1.0)])
    assert first == pytest.approx(1.0)
    assert second == pytest.approx(-2.0)


def test_dataset_summary_binds_dense_receipt_and_optional_screens(
    module: Any, tmp_path: Path
) -> None:
    profile = profile_run(tmp_path, dense_receipt())
    primary_job = job(profile)
    independent_profile = profile_run(
        tmp_path, dense_receipt(), name="profile-A-bank", paired=False
    )
    independent_job = job(
        independent_profile,
        dataset_id=primary_job["dataset_id"],
        biological_history_id=primary_job["biological_history_id"],
        arm=primary_job["arm"],
        bank_role="A",
        input_dir=primary_job["input_dir"],
        observations=primary_job["observations"],
    )
    primary_evidence = module._profile_evidence(primary_job)
    independent_evidence = module._profile_evidence(independent_job)
    bound_sources = {
        **primary_job["input_sha256"],
        **independent_job["input_sha256"],
        **module._bound_receipts(primary_evidence),
        **module._bound_receipts(independent_evidence),
    }
    bank = tmp_path / "bank"
    write_json(
        bank / "receipt.json",
        {
            "schema": "development-bank-comparison-v1",
            "status": "failed",
            "reason": "bank sensitivity detected",
            "source_input_sha256": bound_sources,
            "points": [
                {
                    "delta_w": 0.2,
                    "ownership_agreement": True,
                    "inside_either_diagnostic_set": True,
                    "boundary_contact_agreement": True,
                }
            ],
            "level_set_checks": [{"cutoff": 3.84, "passed": False}],
        },
    )
    integration = tmp_path / "integration"
    integration_sources = {
        **primary_job["input_sha256"],
        **module._bound_receipts(primary_evidence),
    }
    write_json(
        integration / "receipt.json",
        {
            "schema": "fixed-outer-importance-screen-v1",
            "status": "indeterminate",
            "reoptimised_profile": False,
            "optimized_root_movement_quantified": False,
            "identity": primary_job["dataset_id"],
            "source_input_sha256": integration_sources,
            "data_identity": primary_evidence["data_identity"],
            "history": [
                {
                    "draws_per_point_per_stream": 16384,
                    "doubling_stable": False,
                    "status": "indeterminate",
                    "streams": [
                        {
                            "weight_gates_passed": False,
                            "contrast_precision_passed": False,
                            "ownership_resolved": True,
                        }
                    ],
                }
            ],
        },
    )
    primary_job["bank_comparison_dir"] = str(bank)
    primary_job["integration_dir"] = str(integration)
    result = module.summarize_dataset(
        primary_job,
        evidence=primary_evidence,
        independent_evidence=independent_evidence,
    )
    assert result["dense_child_binding_verified"] is True
    assert result["numerical_summary_available"] is True
    assert result["free"]["sigma"] == pytest.approx(0.4)
    assert result["free"]["effect_status"] == "selected_maximum"
    assert result["w1"] == {"status": "available", "value": 2.5}
    assert result["w_truth"] == {"status": "available", "value": 1.25}
    assert result["diagnostic_level"]["actual_root_log_h"] == [0.0, 2.0]
    assert result["ridge"]["category"] == "available"
    assert result["ridge"]["slope"] == pytest.approx(1.0)
    assert result["cost"]["dense"]["search"]["fixed_fit_events"] == 88
    assert result["cost"]["dense"]["post_search_seconds"] == pytest.approx(3.5)
    assert result["bank_comparison"]["nonpassing_point_count"] == 1
    assert result["bank_comparison"]["nonpassing_level_checks"] == [
        {"cutoff": 3.84, "passed": False}
    ]
    assert result["integration_screen"]["final_stream_gates"][0][
        "weight_gates_passed"
    ] is False

    unrelated = json.loads((integration / "receipt.json").read_text())
    dense_key = str((profile / "dense" / "receipt.json").resolve())
    unrelated["source_input_sha256"][dense_key] = "0" * 64
    write_json(integration / "receipt.json", unrelated)
    rejected = module.summarize_dataset(
        primary_job,
        evidence=primary_evidence,
        independent_evidence=independent_evidence,
    )
    assert rejected["integration_screen"]["state"] == "binding_error"
    assert rejected["integration_screen"]["status"] == "indeterminate"
    assert dense_key in rejected["integration_screen"]["failure"]["mismatches"]


def test_zero_family_and_missing_receipt_remain_categorical(module: Any, tmp_path: Path) -> None:
    zero = module.summarize_dataset(job(profile_run(tmp_path, dense_receipt(owner="sigma_zero"))))
    assert zero["free"]["sigma_status"] == "zero_family"
    assert zero["free"]["sigma"] == 0.0
    assert zero["ridge"] == {"category": "zero_family", "slope": None, "nodes": []}

    missing_job = job(profile_run(tmp_path, dense_receipt(), name="missing-template"))
    missing_job["profile_dir"] = str(tmp_path / "absent")
    missing = module.summarize_dataset(missing_job)
    assert missing["numerical_summary_available"] is False
    assert missing["diagnostic_level"]["category"] == "unresolved"
    assert missing["ridge"]["slope"] is None
    assert missing["failures"]["profile_run"]["type"] == "FileNotFoundError"
    assert missing["failures"]["dense_search"]["type"] == "FileNotFoundError"

    unresolved_receipt = dense_receipt()
    unresolved_receipt["status"] = "indeterminate"
    unresolved_receipt["failure"] = {"type": "RuntimeError", "message": "root unresolved"}
    unresolved = module.summarize_dataset(
        job(profile_run(tmp_path, unresolved_receipt, name="unresolved-profile"))
    )
    assert unresolved["numerical_summary_available"] is False
    assert unresolved["free"]["effect_status"] == "unresolved"
    assert unresolved["free"]["effect_estimate"] is None
    assert unresolved["free"]["sigma"] is None
    assert unresolved["w1"] == {"status": "unavailable", "value": None}


def test_invalid_hash_binding_suppresses_all_scientific_numbers(
    module: Any, tmp_path: Path
) -> None:
    profile = profile_run(tmp_path, dense_receipt())
    invalid_job = job(profile)
    dense_path = profile / "dense" / "receipt.json"
    changed = json.loads(dense_path.read_text())
    changed["cost"]["post_search_seconds"] = 99.0
    write_json(dense_path, changed)
    invalid = module.summarize_dataset(invalid_job)
    assert invalid["dense_child_binding_verified"] is False
    assert invalid["numerical_summary_available"] is False
    assert invalid["free"]["effect_estimate"] is None
    assert invalid["free"]["sigma"] is None
    assert invalid["w1"]["value"] is None
    assert invalid["w_truth"]["value"] is None
    assert invalid["diagnostic_level"]["reported_root_log_h"] == []
    assert invalid["ridge"]["slope"] is None
    assert invalid["cost"]["dense"] is None
    paired = module._pair_summary(invalid, pair_row("B", (0.2, 2.4), slope=0.2))
    assert paired["dL"] is None
    assert paired["slope_B_minus_A"] is None
    assert paired["prediction_slope_B_minus_A_ge_0"] is None

    dense_only = profile_run(
        tmp_path, dense_receipt(), name="b0-without-lean", paired=False
    )
    dense_only_result = module.summarize_dataset(job(dense_only))
    assert dense_only_result["dense_child_binding_verified"] is True
    assert dense_only_result["numerical_summary_available"] is True
    assert dense_only_result["free"]["effect_estimate"] is not None
    assert dense_only_result["lean_candidate_available"] is False

    failed_lean = profile_run(tmp_path, dense_receipt(), name="b0-failed-lean")
    failed_lean_job = job(failed_lean)
    lean_path = failed_lean / "lean" / "receipt.json"
    lean = json.loads(lean_path.read_text())
    lean["status"] = "indeterminate"
    lean["failure"] = {"type": "RuntimeError", "message": "component missed"}
    write_json(lean_path, lean)
    parent_path = failed_lean / "receipt.json"
    parent = json.loads(parent_path.read_text())
    parent["status"] = "failed"
    parent["searches"]["lean"]["sha256"] = hashlib.sha256(lean_path.read_bytes()).hexdigest()
    write_json(parent_path, parent)
    failed = module.summarize_dataset(failed_lean_job)
    assert failed["dense_lean_comparison_status"] == "failed"
    assert failed["lean_candidate_available"] is False
    assert failed["numerical_summary_available"] is True
    assert failed["free"]["effect_estimate"] is not None
    assert failed["diagnostic_level"]["actual_root_log_h"] == [0.0, 2.0]


def test_malformed_receipt_is_categorical_and_missing_directory_path_is_exact(
    module: Any, tmp_path: Path
) -> None:
    profile = profile_run(tmp_path, dense_receipt())
    malformed_job = job(profile)
    (profile / "receipt.json").write_text('{"truncated":')
    result = module.summarize_dataset(malformed_job)
    assert result["numerical_summary_available"] is False
    assert result["profile_run_status"] == "indeterminate"
    assert result["failures"]["profile_run"]["type"] == "JSONDecodeError"
    absent = tmp_path / "not-created-integration"
    state = module._receipt_state(absent)
    assert state["state"] == "missing"
    assert state["path"] == str((absent / "receipt.json").resolve())


def test_tied_owner_and_sigma_bound_suppress_ridge_slope(module: Any, tmp_path: Path) -> None:
    tied_receipt = dense_receipt()
    for fit in tied_receipt["points"]["True"]:
        fit["sigma_zero"]["criterion"] = fit["positive_sigma"]["criterion"]
        fit["criterion"] = fit["positive_sigma"]["criterion"]
    tied = module.summarize_dataset(
        job(profile_run(tmp_path, tied_receipt, name="tied-profile"))
    )
    assert tied["ridge"]["category"] == "tied"
    assert tied["ridge"]["slope"] is None

    bound_receipt = dense_receipt()
    for fit in bound_receipt["points"]["True"]:
        fit["positive_sigma"]["nuisance_bound_contacts"] = ["log_sigma:lower"]
    bound = module.summarize_dataset(
        job(profile_run(tmp_path, bound_receipt, name="bound-profile"))
    )
    assert bound["ridge"]["category"] == "sigma_bound_contact"
    assert bound["ridge"]["slope"] is None


def pair_row(
    dataset: str,
    roots: tuple[float, float],
    *,
    category: str = "available",
    slope: float | None = 0.0,
) -> dict[str, Any]:
    return {
        "dataset_id": dataset,
        "biological_history_id": "history-1",
        "numerical_summary_available": True,
        "diagnostic_level": {
            "category": category,
            "actual_root_log_h": list(roots) if category == "available" else [],
            "components": [
                {"lower_log_h": roots[0] + 0.002, "upper_log_h": roots[1] + 0.002}
            ],
        },
        "ridge": {
            "category": "available" if slope is not None else category,
            "slope": slope,
        },
    }


def test_pair_directions_use_actual_roots_and_predictions_are_not_gates(module: Any) -> None:
    result = module._pair_summary(
        pair_row("A", (0.1, 2.1), slope=-0.2),
        pair_row("B", (0.2, 2.4), slope=0.1),
    )
    assert result["dL"] == pytest.approx(-0.1)
    assert result["dU"] == pytest.approx(0.3)
    assert result["prediction_dU_gt_dL"] is True
    assert result["slope_B_minus_A"] == pytest.approx(0.3)
    assert result["prediction_slope_B_minus_A_ge_0"] is True
    assert result["descriptive_only"] is True
    assert result["numerical_acceptance_gate"] is False


def test_truncated_root_is_not_imputed_as_an_expansion(module: Any, tmp_path: Path) -> None:
    truncated = module.summarize_dataset(
        job(profile_run(tmp_path, dense_receipt(domain_contact=True)))
    )
    assert truncated["diagnostic_level"]["category"] == "truncated"
    assert truncated["diagnostic_level"]["reported_root_log_h"] == [0.0, 2.0]
    assert truncated["diagnostic_level"]["actual_root_log_h"] == []
    pair = module._pair_summary(truncated, pair_row("B", (0.2, 2.4)))
    assert pair["expansion_category"] == "A:truncated|B:available"
    assert pair["dL"] is None
    assert pair["dU"] is None
    assert pair["prediction_dU_gt_dL"] is None

    full_receipt = dense_receipt()
    level = full_receipt["tight_level_sets"][0]
    level["set_class"] = "full_domain"
    level["components"][0]["lower_domain_contact"] = True
    level["components"][0]["upper_domain_contact"] = True
    level["roots"] = []
    full = module.summarize_dataset(
        job(profile_run(tmp_path, full_receipt, name="full-domain-profile"))
    )
    assert full["diagnostic_level"]["category"] == "full_domain"
    assert full["ridge"]["category"] == "full_domain"
    assert full["ridge"]["slope"] is None


def complete_panel_fixture(
    tmp_path: Path,
) -> tuple[
    dict[str, Any], dict[str, Any], dict[str, dict[str, Any]], list[dict[str, Any]], str
]:
    frozen_hash = "f" * 64
    manifest: dict[str, Any] = {
        "schema": "development-challenge-manifest-v1",
        "datasets": [],
        "optional_c_cases": [],
        "reporting": {},
    }
    c_receipts: dict[str, dict[str, Any]] = {}
    prepared: dict[str, Any] = {
        "schema": "development-challenge-manifest-v1",
        "frozen_manifest_sha256": frozen_hash,
        "datasets": [],
    }
    jobs: list[dict[str, Any]] = []
    for index in range(16):
        history = f"cell-{index:02d}-rep-005"
        report_h = 1.0 if index % 2 == 0 else 3.0
        manifest["reporting"][history] = {"h": report_h}
        roles = ["B0", "A"] if index >= 8 else ["B0"]
        source_hash = hashlib.sha256(f"source-{history}".encode()).hexdigest()
        for arm in ("A", "B"):
            dataset_id = f"{history}-arm-{arm}"
            input_dir = tmp_path / "panel-inputs" / dataset_id / "public"
            observations = tmp_path / "panel-inputs" / dataset_id / "observations.npz"
            manifest["datasets"].append(
                {
                    "dataset_id": dataset_id,
                    "biological_history_id": history,
                    "arm": arm,
                    "bank_roles": roles,
                    "site_count": 120,
                    "source_observations_sha256": source_hash,
                }
            )
            for role in roles:
                profile = profile_run(
                    tmp_path,
                    dense_receipt(),
                    name=f"profile-{dataset_id}-{role}",
                    paired=role == "B0",
                )
                jobs.append(
                    job(
                        profile,
                        dataset_id=dataset_id,
                        biological_history_id=history,
                        arm=arm,
                        bank_role=role,
                        report_h=report_h,
                        site_count=120,
                        input_dir=str(input_dir),
                        observations=str(observations),
                        source_observations_sha256=source_hash,
                    )
                )
            prepared["datasets"].append(
                {
                    **manifest["datasets"][-1],
                    "observations": str(observations),
                    "observations_sha256": jobs[-1]["observations_sha256"],
                }
            )
    for index in range(6):
        dataset_id = f"C-map-{index // 2:02d}-case-{index % 2:02d}"
        report_h = 1.0 if index % 2 == 0 else 3.0
        manifest["optional_c_cases"].append(
            {
                "dataset_id": dataset_id,
                "arm": "C",
                "site_count": 260,
                "reporting": {"h": report_h},
            }
        )
        input_dir = tmp_path / "panel-inputs" / dataset_id / "public"
        observations = tmp_path / "panel-inputs" / dataset_id / "observations.npz"
        for role in ("B0", "A"):
            profile = profile_run(
                tmp_path,
                dense_receipt(),
                name=f"profile-{dataset_id}-{role}",
                paired=role == "B0",
            )
            jobs.append(
                job(
                    profile,
                    dataset_id=dataset_id,
                    biological_history_id=dataset_id,
                    arm="C",
                    bank_role=role,
                    report_h=report_h,
                    site_count=260,
                    input_dir=str(input_dir),
                    observations=str(observations),
                )
            )
        c_receipts[dataset_id] = {
            "state": "generated_development_only",
            "dataset_id": dataset_id,
            "arm": "C",
            "site_count": 260,
            "observations": str(observations),
            "observations_sha256": jobs[-1]["observations_sha256"],
            "input_dir": str(input_dir),
            "reporting": {"h": report_h},
            "source_input_sha256": {"frozen_manifest": frozen_hash},
        }
        write_json(observations.parent / "receipt.json", c_receipts[dataset_id])
    return manifest, prepared, c_receipts, jobs, frozen_hash


def test_cli_writes_complete_38_dataset_json_and_csv(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, prepared, c_receipts, jobs, _ = complete_panel_fixture(tmp_path)
    fake_low_comparison = tmp_path / "unrelated-low-comparison"
    write_json(
        fake_low_comparison / "receipt.json",
        {"schema": "development-bank-comparison-v1", "status": "within_prespecified_gates"},
    )
    next(
        row
        for row in jobs
        if row["bank_role"] == "B0" and row["dataset_id"].startswith("cell-00")
    )["bank_comparison_dir"] = str(fake_low_comparison)
    jobs_path = tmp_path / "jobs.json"
    manifest_path = tmp_path / "panel-manifest.json"
    prepared_path = tmp_path / "prepared-manifest.json"
    write_json(manifest_path, manifest)
    frozen_hash = module.sha256(manifest_path)
    prepared["frozen_manifest_sha256"] = frozen_hash
    for dataset_id, receipt in c_receipts.items():
        receipt["source_input_sha256"]["frozen_manifest"] = frozen_hash
        row = next(job for job in jobs if job["dataset_id"] == dataset_id)
        write_json(Path(row["observations"]).parent / "receipt.json", receipt)
    write_json(prepared_path, prepared)
    c_bindings = {
        dataset_id: {
            "path": str(Path(row["observations"]).parent / "receipt.json"),
            "sha256": module.sha256(Path(row["observations"]).parent / "receipt.json"),
        }
        for dataset_id in c_receipts
        for row in [next(job for job in jobs if job["dataset_id"] == dataset_id)]
    }
    write_json(
        jobs_path,
        {
            "frozen_panel_sha256": frozen_hash,
            "prepared_inputs": {
                "archived": {"path": str(prepared_path), "sha256": module.sha256(prepared_path)},
                "C": c_bindings,
            },
            "jobs": jobs,
        },
    )
    monkeypatch.setattr(module, "FROZEN_MANIFEST_SHA256", frozen_hash)
    output = tmp_path / "summary"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "summarize_development_challenge.py",
            "--jobs",
            str(jobs_path),
            "--manifest",
            str(manifest_path),
            "--output-dir",
            str(output),
        ],
    )
    module.main()
    summary = json.loads((output / "summary.json").read_text())
    assert summary["dataset_count"] == 38
    assert summary["paired_history_count"] == 16
    assert summary["separate_c_history_count"] == 6
    assert summary["profile_role_count"] == 60
    assert summary["profile_role_binding_counts"] == {"verified": 60}
    assert summary["scientific_claim"] is False
    assert summary["bank_comparison_status_counts"] == {"not_requested": 38}
    assert summary["integration_screen_status_counts"] == {"not_requested": 38}
    with (output / "datasets.csv").open(newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 38
    with (output / "paired_descriptives.csv").open(newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 16


def test_jobs_cannot_reuse_a_profile_or_change_frozen_identity(
    module: Any, tmp_path: Path
) -> None:
    manifest, prepared, c_receipts, jobs, frozen_hash = complete_panel_fixture(tmp_path)
    jobs[1]["profile_dir"] = jobs[0]["profile_dir"]
    with pytest.raises(ValueError, match="distinct profile directory"):
        module.validate_jobs(
            jobs,
            manifest,
            prepared,
            c_receipts,
            frozen_manifest_sha256=frozen_hash,
        )

    manifest, prepared, c_receipts, jobs, frozen_hash = complete_panel_fixture(
        tmp_path / "second"
    )
    jobs[0]["source_observations_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source observation differs"):
        module.validate_jobs(
            jobs,
            manifest,
            prepared,
            c_receipts,
            frozen_manifest_sha256=frozen_hash,
        )

    manifest, prepared, c_receipts, jobs, frozen_hash = complete_panel_fixture(
        tmp_path / "third"
    )
    left, right = jobs[0], jobs[1]
    bundle_keys = (
        "profile_dir",
        "input_dir",
        "observations",
        "observations_sha256",
        "arrival_bank",
        "compressed_bank",
        "input_sha256",
    )
    left_bundle = {key: left[key] for key in bundle_keys}
    right_bundle = {key: right[key] for key in bundle_keys}
    left.update(right_bundle)
    right.update(left_bundle)
    with pytest.raises(ValueError, match="prepared observation differs"):
        module.validate_jobs(
            jobs,
            manifest,
            prepared,
            c_receipts,
            frozen_manifest_sha256=frozen_hash,
        )

