from __future__ import annotations

import copy
import importlib.util
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest


@pytest.fixture
def module() -> Any:
    path = Path(__file__).resolve().parents[1] / "scripts/compare_profile_banks.py"
    spec = importlib.util.spec_from_file_location("profile_bank_comparisons_test", path)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def profile(role: str) -> dict[str, Any]:
    free = {
        "positive_sigma": {"h": 3.0, "criterion": -10.0},
        "sigma_zero": {"h": 2.5, "criterion": -11.0},
    }
    levels = [
        {
            "cutoff": c,
            "status": "available",
            "roots": [{"log_h": 0.5}, {"log_h": 2.0}],
            "components": [
                {"lower_domain_contact": False, "upper_domain_contact": False, "singleton": False}
            ],
        }
        for c in (1.0, 3.84, 6.63)
    ]
    return {
        "status": "profile_numerically_resolved",
        "free": free,
        "tight_free": free,
        "anchors": [
            {"log_h": float(x), "h": math.exp(x), "w": float((x - 1.0) ** 2 * 8)}
            for x in np.linspace(0.0, math.log(30.0), 35)
        ],
        "tight_level_sets": levels,
        "data_identity": {
            "observations_sha256": "history-one",
            "public_npz_sha256": "map",
            "exposure_sha256": "exposure",
            "training_site_ids_sha256": "ids",
            "training_site_count": 120,
            "covariance_range": 10.0,
            "prey_times": [0, 10],
            "predator_times": [10],
            "cohort_start": -60.0,
        },
        "bank_identity": {
            "role": role,
            "raw_sha256": role,
            "compressed_sha256": role,
            "bank_checksum": role,
        },
        "source_input_sha256": {"src/criterion.py": "same-code"},
    }


def inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    receipts = {role: profile(role) for role in ("B0", "A", "B", "AB")}
    pseudo = {
        "schema": "profile-pseudo-mass-fixed-fit-v1",
        "status": "evaluated",
        "requires_full_refit": False,
        "fixed_fit_only": True,
        "thresholds": {"centered_lr_shift": 0.05, "projected_gradient": 1e-3},
        "points": [{"delta_w": 0.0}],
        "family_replays": [
            {
                "family": f,
                "a_criterion": -10.0 - i,
                "adup_criterion": -10.0 - i,
                "adup_projected_gradient_inf": 0.0,
            }
            for i, f in enumerate(("positive_sigma", "sigma_zero"))
        ],
        "maximum_abs_centered_lr_shift": 0.0,
        "maximum_projected_gradient": 0.0,
        "material_family_ownership_changes": [],
        "a_receipt_sha256": "hash-A",
        "observations_sha256": "history-one",
        "bank_identities": {
            "A": receipts["A"]["bank_identity"],
            "Adup": profile("Adup")["bank_identity"],
        },
    }
    return receipts, pseudo, {role: f"hash-{role}" for role in receipts}


def test_casewise_gate_does_not_average_away_one_bad_anchor(module: Any) -> None:
    receipts, pseudo, hashes = inputs()
    assert module.aggregate(receipts, pseudo, hashes)["status"] == "within_prespecified_gates"
    receipts["B"]["anchors"][20]["w"] += 0.101
    result = module.aggregate(receipts, pseudo, hashes)
    assert result["status"] == "sensitive"
    assert {tuple((r["left"], r["right"])) for r in result["comparisons"] if not r["passed"]} == {
        ("B0", "B"),
        ("A", "B"),
        ("B", "AB"),
    }


def test_root_movement_and_topology_are_independent_gates(module: Any) -> None:
    left, right = profile("B0"), profile("A")
    right["tight_level_sets"][0]["roots"][1]["log_h"] += 0.051
    assert not module.compare(left, right)["passed"]
    right = profile("A")
    right["tight_level_sets"][0]["components"][0]["lower_domain_contact"] = True
    assert not module.compare(left, right)["passed"]


def test_required_pseudo_refit_cannot_be_replaced_by_fixed_fit_pass(module: Any) -> None:
    receipts, pseudo, hashes = inputs()
    pseudo["requires_full_refit"] = True
    pseudo["maximum_projected_gradient"] = 0.002
    pseudo["family_replays"][0]["adup_projected_gradient_inf"] = 0.002
    assert module.aggregate(receipts, pseudo, hashes)["status"] == "indeterminate"
    receipts["Adup"] = profile("Adup")
    hashes["Adup"] = "hash-Adup"
    result = module.aggregate(receipts, pseudo, hashes)
    assert result["status"] == "within_prespecified_gates"
    assert len(result["comparisons"]) == 7


@pytest.mark.parametrize(
    "field,value",
    [
        ("observations_sha256", "another-history"),
        ("training_site_ids_sha256", "other-sites"),
        ("covariance_range", 20.0),
    ],
)
def test_cross_history_or_model_comparison_is_rejected(module: Any, field: str, value: Any) -> None:
    receipts, pseudo, hashes = inputs()
    receipts["B"]["data_identity"][field] = value
    with pytest.raises(ValueError, match="histories"):
        module.aggregate(receipts, pseudo, hashes)


def test_stale_pseudo_receipt_and_incompatible_source_rejected(module: Any) -> None:
    receipts, pseudo, hashes = inputs()
    wrong = copy.deepcopy(pseudo)
    wrong["a_receipt_sha256"] = "older-A-fit"
    with pytest.raises(ValueError, match="supplied A receipt"):
        module.aggregate(receipts, wrong, hashes)
    receipts["B"]["source_input_sha256"]["src/criterion.py"] = "modified-code"
    with pytest.raises(ValueError, match="source bindings differ"):
        module.aggregate(receipts, pseudo, hashes)


def test_unavailable_profile_is_indeterminate_not_empty_or_bank_pass(module: Any) -> None:
    receipts, pseudo, hashes = inputs()
    receipts["A"]["status"] = "indeterminate"
    assert module.aggregate(receipts, pseudo, hashes)["status"] == "indeterminate"
    receipts["A"]["anchors"][2]["w"] = math.nan
    with pytest.raises(ValueError, match="nonfinite"):
        module.aggregate(receipts, pseudo, hashes)


def test_free_effect_summary_reports_selected_envelope_and_both_families(module: Any) -> None:
    receipt = profile("A")
    receipt["tight_free"]["sigma_zero"]["criterion"] = -9.0
    result = module.free_effects(receipt)
    assert result["envelope_owner"] == "sigma_zero"
    assert result["envelope_h"] == 2.5
    assert result["by_family"] == {"positive_sigma": 3.0, "sigma_zero": 2.5}


def test_false_pseudo_refit_flag_cannot_suppress_the_rule(module: Any) -> None:
    receipts, pseudo, hashes = inputs()
    pseudo["maximum_projected_gradient"] = 0.002
    pseudo["family_replays"][0]["adup_projected_gradient_inf"] = 0.002
    with pytest.raises(ValueError, match="refit flag"):
        module.aggregate(receipts, pseudo, hashes)
