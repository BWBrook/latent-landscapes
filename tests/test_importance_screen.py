from __future__ import annotations

import copy
import importlib
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from latent_landscapes.importance_reference import Estimate


@pytest.fixture
def screen(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("screen_spatial_importance")


def summary(value: float, half_width: float = 0.002) -> dict[str, Any]:
    return {
        "weight_gates_passed": True,
        "ownership_resolved": True,
        "contrast_precision_passed": half_width <= 0.01,
        "contrasts": {
            "1": {
                "estimate": value,
                "half_width": half_width,
                "lower": value - half_width,
                "upper": value + half_width,
            }
        },
    }


@pytest.mark.parametrize(
    "value,status",
    [
        (0.0, "pointwise_screen_passed"),
        (0.12, "repair_required"),
        (-0.12, "repair_required"),
        (0.10, "indeterminate"),
    ],
)
def test_threshold_requires_interval_evidence(screen: Any, value: float, status: str) -> None:
    result = summary(value)
    assert screen.decision(result, copy.deepcopy(result), True) == status


@pytest.mark.parametrize("field", ["weight_gates_passed", "contrast_precision_passed"])
def test_bad_primary_or_confirmation_is_never_qualified(screen: Any, field: str) -> None:
    good, bad = summary(0.2), summary(0.2)
    bad[field] = False
    assert screen.decision(good, bad, True) == "indeterminate"
    assert screen.decision(bad, good, True) == "indeterminate"
    assert screen.decision(good, good, False) == "indeterminate"


def test_independent_confirmation_must_agree(screen: Any) -> None:
    assert screen.decision(summary(0.12), summary(0.16), True) == "indeterminate"


def test_envelope_uses_exact_zero_and_preserves_ambiguous_ownership(screen: Any) -> None:
    estimate = Estimate(-2.0, np.linspace(-2.01, -1.99, 16), 16384, {"weight_gates_passed": True})
    chosen, row = screen.envelope(estimate, -1.0)
    assert chosen.draws == 0 and chosen.log_integral == -1.0
    assert row["ownership_resolved"]
    chosen, row = screen.envelope(estimate, -2.0)
    assert not row["ownership_resolved"]


def test_unresolved_profile_cannot_feed_screen(screen: Any) -> None:
    with pytest.raises(ValueError, match="profile unresolved"):
        screen.selected_fits({"status": "indeterminate"}, 3.0)


def test_material_ownership_reversal_cannot_cancel_out_of_w(screen: Any) -> None:
    fits: dict[str, Any] = {
        key: {
            "criterion": value,
            "positive_sigma": {"criterion": value},
            "sigma_zero": {"criterion": value - 0.001},
        }
        for key, value in [("free", 5.0), ("1", 4.0)]
    }
    estimates = {
        key: Estimate(
            fit["criterion"] - 0.002,
            np.full(16, fit["criterion"] - 0.002),
            16384,
            {"weight_gates_passed": True},
        )
        for key, fit in fits.items()
    }
    result = screen.summarize(estimates, fits)
    assert result["contrasts"]["1"]["estimate"] == pytest.approx(0.0, abs=1e-12)
    assert screen.decision(result, result, True) == "repair_required"


def test_ambiguous_owner_can_have_precisely_bounded_envelope(screen: Any) -> None:
    fits: dict[str, Any] = {
        key: {
            "criterion": value,
            "positive_sigma": {"criterion": value},
            "sigma_zero": {"criterion": value},
        }
        for key, value in [("free", 5.0), ("1", 4.0)]
    }
    estimates = {
        key: Estimate(
            fit["criterion"],
            fit["criterion"] + np.linspace(-1e-5, 1e-5, 16),
            16384,
            {"weight_gates_passed": True},
        )
        for key, fit in fits.items()
    }
    result = screen.summarize(estimates, fits)
    assert not result["ownership_resolved"]
    assert screen.decision(result, result, True) == "pointwise_screen_passed"
    interval = result["contrasts"]["1"]
    assert interval["lower"] < 0 < interval["upper"]


def test_input_substitution_and_modified_child_are_rejected(screen: Any, tmp_path: Path) -> None:
    import argparse
    import json

    root = tmp_path / "run"
    (root / "dense").mkdir(parents=True)
    args = argparse.Namespace(
        report_h=3.0,
        profile=root / "dense" / "receipt.json",
        observations=tmp_path / "obs.npz",
        arrival_bank=tmp_path / "raw.npy",
        compressed_bank=tmp_path / "compressed.npz",
        input_dir=tmp_path,
    )
    files = [
        args.observations,
        args.arrival_bank,
        args.compressed_bank,
        tmp_path / "public_inputs.npz",
        tmp_path / "exposure.npz",
    ]
    for path in files:
        path.write_text("original")
    args.profile.write_text("{}")
    parent = {
        "schema": "development-profile-run-v1",
        "searches": {"dense": {"sha256": screen.adapter.sha256_file(args.profile)}},
        "source_input_sha256": {str(p.resolve()): screen.adapter.sha256_file(p) for p in files},
    }
    (root / "receipt.json").write_text(json.dumps(parent))
    (root / "started.json").write_text(
        json.dumps(
            {
                "source_input_sha256": parent["source_input_sha256"],
                "report_h_used_only_after_search": [3.0],
            }
        )
    )
    screen.verify_profile_binding(args)
    args.observations.write_text("other")
    with pytest.raises(ValueError, match="inputs differ"):
        screen.verify_profile_binding(args)
    args.observations.write_text("original")
    args.profile.write_text('{"modified":true}')
    with pytest.raises(ValueError, match="child receipt binding"):
        screen.verify_profile_binding(args)


def anchor_receipt() -> dict[str, Any]:
    import math

    return {
        "status": "profile_numerically_resolved",
        "free": {"True": {"positive_sigma": {"h": 2.0}, "sigma_zero": {"h": 1.0}}},
        "tight_level_sets": [
            {
                "cutoff": 3.84,
                "status": "available",
                "roots": [{"log_h": math.log(h)} for h in (1.5, 4.0)],
            }
        ],
        "post_search_diagnostics": {
            "status": "available",
            "points": [
                {"h": h, "log_h": math.log(h), "tight_fit": {"location": h}}
                for h in (1.0, 1.5, 2.0, 3.0, 4.0, 7.0)
            ],
        },
    }


def test_screen_uses_required_dense_anchors_without_topology_only_points(screen: Any) -> None:
    fits, anchors = screen.selected_fits(anchor_receipt(), 3.0)
    assert list(fits) == ["free", "1", "1.5", "2", "3", "4"]
    assert [row["h"] for row in anchors] == [1.0, 1.5, 2.0, 3.0, 4.0]
    assert set(anchors[0]["roles"]) == {"null", "dense_free_sigma_zero"}
    assert "7" not in fits


def test_required_anchor_cannot_be_interpolated_or_silently_omitted(screen: Any) -> None:
    receipt = anchor_receipt()
    receipt["post_search_diagnostics"]["points"] = [
        row for row in receipt["post_search_diagnostics"]["points"] if row["h"] != 3.0
    ]
    with pytest.raises(ValueError, match="required fixed-outer anchor missing"):
        screen.selected_fits(receipt, 3.0)
