from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "summarize_final_procedure_evaluation.py"
SPEC = importlib.util.spec_from_file_location("goal062_synthesis", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
SYNTHESIS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNTHESIS)


LABELS = ("L1", "L3", "L5", "H1", "H3", "H5", "B_L1", "B_L3", "B_H1", "B_H3")
EFFECTS = (1.0, 3.0, 5.0, 1.0, 3.0, 5.0, 1.0, 3.0, 1.0, 3.0)
MUS = (0.001, 0.001, 0.001, 0.004, 0.004, 0.004, 0.001, 0.001, 0.004, 0.004)


def _rows(replicates: int = 6) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cell, (label, effect, mu) in enumerate(zip(LABELS, EFFECTS, MUS, strict=True)):
        background = "B100-A" if label.startswith("B_") else "exact"
        for replicate in range(replicates):
            if replicate == 0:
                status, reason, declared = "declared", None, True
            elif replicate == 1:
                status, reason, declared = "valid_non_declaration", None, False
            elif replicate == 2:
                status, reason, declared = "abstain_observed_fit", "observed_fit", False
            elif replicate == 3:
                status, reason, declared = "abstain_observed_screen", "observed_screen", False
            elif replicate == 4:
                status, reason, declared = "abstain_shared_table", "shared_table", False
            else:
                status, reason, declared = "valid_non_declaration", None, False
            h_hat = effect if replicate % 2 == 0 else min(10.0, effect * 2.0)
            free_status = "converged"
            if replicate == 5:
                free_status = "invalid"
            fits = {
                model: {
                    "h": h_hat if model.endswith("free_h") else 1.0,
                    "beta": 0.4,
                    "mu": mu * 1.1,
                    "detection_sd": 0.21,
                    "raw_logjoint": -10.0,
                    "numerical_status": free_status if model == "adjusted_free_h" else "converged",
                    "score_replay_passed": True,
                }
                for model in SYNTHESIS.MODEL_NAMES
            }
            statuses = {
                model: (free_status == "converged" if model == "adjusted_free_h" else True)
                for model in SYNTHESIS.MODEL_NAMES
            }
            rows.append(
                {
                    "cell_index": cell,
                    "cell_label": label,
                    "replicate": replicate,
                    "background": background,
                    "effect": effect,
                    "mean_hazard": mu,
                    "generating_beta": None if background == "B100-A" else 0.5,
                    "detection_sd": 0.2,
                    "selecteddecision": {"status": status, "declared": declared, "reason": reason},
                    "fits": fits,
                    "main_statuses_converged": statuses,
                    "nesting_gaps": {"constant": 0.0, "adjusted": 0.0},
                    "nesting_status": {"constant": "passed", "adjusted": "passed"},
                    "compressed_score_replay": {
                        model: {"status": "passed", "difference": 0.0}
                        for model in SYNTHESIS.MODEL_NAMES
                    },
                    "all_main_replays_passed": True,
                    "free_h_valid": free_status == "converged",
                    "true_node_retained": True if background == "exact" else None,
                    "C_size": 3 + replicate,
                    "p_BB": 0.01 + replicate / 100.0,
                    "holdout": {
                        "models": {
                            model: {"total_nats": float(replicate + index)}
                            for index, model in enumerate(SYNTHESIS.MODEL_NAMES)
                        }
                    },
                    "audit_status": "accepted",
                }
            )
    return rows


def test_bootstrap_indices_follow_registered_seed_sequence() -> None:
    address = [SYNTHESIS.BOOTSTRAP_ROOT, 62, 2, 3, 7]
    seed = int(np.random.SeedSequence(address).generate_state(1, dtype=np.uint64)[0])
    expected = np.random.default_rng(seed).integers(0, 6, size=6, dtype=np.int64)
    np.testing.assert_array_equal(SYNTHESIS.bootstrap_indices(3, 7, sample_size=6), expected)


def test_free_h_valid_uses_audited_flag_and_registered_eight_ulp_bounds() -> None:
    row = _rows(6)[0]
    fit = row["fits"]["adjusted_free_h"]
    fit["h"] = np.nextafter(10.0, np.inf)
    row["free_h_valid"] = True
    assert SYNTHESIS._fit_is_valid(fit, row)
    row["free_h_valid"] = False
    assert not SYNTHESIS._fit_is_valid(fit, row)


def test_summarize_rows_emits_registered_partitions_and_b100_labels() -> None:
    result = SYNTHESIS.summarize_rows(_rows(), expected_replicates=6, bootstrap_draws=12)
    assert result["schema"] == "goal062-final-procedure-evaluation-synthesis-v1"
    assert len(result["cells"]) == 10
    l1 = result["cells"][0]
    assert l1["outcomes"]["declaration"]["denominator"] == 6
    assert l1["h_recovery"]["partition_check"]
    assert (
        l1["h_recovery"]["within_1_5_fold"]["count"]
        + l1["h_recovery"]["valid_outside_1_5_fold"]["count"]
        + l1["h_recovery"]["unavailable"]["count"]
        == 6
    )
    assert l1["heldout"]["primary_pairs"] == [
        "adjusted_free_h_minus_constant_free_h",
        "adjusted_free_h_minus_adjusted_h1",
    ]
    assert len(l1["heldout"]["pair_contrasts"]) == 6
    assert set(l1["heldout"]["primary_means"]) == set(l1["heldout"]["primary_pairs"])
    b_l1 = next(cell for cell in result["cells"] if cell["cell_label"] == "B_L1")
    assert b_l1["truth"]["generating_beta"] is None
    assert b_l1["nuisance"]["beta"]["truth_status"] == "not_applicable_B100-A"
    assert (
        b_l1["nuisance"]["mu"]["label"] == "descriptive_working_model_minus_generating_mean_hazard"
    )
    assert set(l1["nuisance"]["mu"]["error_bootstrap"]) == {
        "mean",
        "median",
        "quantile_0.05",
        "quantile_0.25",
        "quantile_0.50",
        "quantile_0.75",
        "quantile_0.95",
    }
    assert b_l1["nuisance"]["beta"]["error_bootstrap"] is None
    labels = {row["label"] for row in result["between_cell_contrasts"]}
    assert labels == {
        "L3_minus_L1",
        "H3_minus_H1",
        "B_L3_minus_B_L1",
        "B_H3_minus_B_H1",
        "B_L1_minus_L1",
        "B_L3_minus_L3",
        "B_H1_minus_H1",
        "B_H3_minus_H3",
    }
    assert l1["conditional_null_miscalibration"]["status"] == "not_flagged"
    assert b_l1["conditional_null_miscalibration"]["status"] == "excluded_B100-A"


def test_exact_null_flag_uses_declaration_wilson_lower_bound() -> None:
    rows = _rows()
    for row in rows:
        if row["cell_label"] == "L1":
            row["selecteddecision"] = {"status": "declared", "declared": True}
    result = SYNTHESIS.summarize_rows(rows, expected_replicates=6, bootstrap_draws=2)
    assert result["cells"][0]["conditional_null_miscalibration"]["flagged"] is True


def test_exact_null_flag_keeps_abstentions_in_all_history_denominator() -> None:
    rows = _rows(500)
    for row in rows:
        if row["cell_label"] == "L1":
            if row["replicate"] < 10:
                row["selecteddecision"] = {"status": "declared", "declared": True}
            else:
                row["selecteddecision"] = {
                    "status": "abstain_observed_screen",
                    "declared": False,
                    "reason": "observed_screen",
                }
    result = SYNTHESIS.summarize_rows(rows, expected_replicates=500, bootstrap_draws=1)
    l1 = result["cells"][0]
    assert l1["outcomes"]["declaration"]["denominator"] == 500
    assert l1["conditional_null_miscalibration"]["flagged"] is False


def test_numerical_aggregation_retains_failures_for_each_model() -> None:
    rows = _rows()
    row = next(item for item in rows if item["cell_label"] == "L1" and item["replicate"] == 0)
    row["fits"]["constant_h1"]["numerical_status"] = "invalid"
    row["main_statuses_converged"]["constant_h1"] = False
    row["compressed_score_replay"]["constant_h1"] = {"status": "failed", "difference": 1.0}
    row["all_main_replays_passed"] = False
    result = SYNTHESIS.summarize_rows(rows, expected_replicates=6, bootstrap_draws=2)
    aggregation = result["cells"][0]["numerical_aggregation"]
    assert aggregation["models"]["constant_h1"]["nonconverged_count"] == 1
    assert aggregation["models"]["constant_h1"]["score_replay_failed_count"] == 1
    assert aggregation["all_main_replays_failed_count"] == 1
    assert aggregation["models"]["adjusted_free_h"]["nonconverged_count"] == 1


def test_bootstrap_interval_is_unavailable_when_any_draw_is_undefined() -> None:
    result = SYNTHESIS._bootstrap_metric(
        [1.0, 2.0, None],
        SYNTHESIS._mean_statistic,
        cell_index=0,
        draws=20,
        sample_size=2,
        root=SYNTHESIS.BOOTSTRAP_ROOT,
        indices=[np.asarray([0, 2]), np.asarray([2, 2])] * 10,
    )
    assert result["interval"] is None
    assert result["undefined_draws"] > 0
    assert result["interval_status"] == "unavailable_undefined_bootstrap_draw"


def test_bootstrap_n_zero_runs_draws_and_reports_all_undefined() -> None:
    result = SYNTHESIS._bootstrap_metric(
        [],
        SYNTHESIS._mean_statistic,
        cell_index=0,
        draws=4,
        sample_size=1,
        root=SYNTHESIS.BOOTSTRAP_ROOT,
    )
    assert result["estimate"] is None
    assert result["interval"] is None
    assert result["undefined_draws"] == 4
    assert result["interval_status"] == "unavailable_fewer_than_two_valid"


def test_n_equals_one_preserves_point_estimate_when_interval_is_unavailable() -> None:
    result = SYNTHESIS._bootstrap_metric(
        [4.0],
        SYNTHESIS._mean_statistic,
        cell_index=0,
        draws=4,
        sample_size=1,
        root=SYNTHESIS.BOOTSTRAP_ROOT,
    )
    assert result["estimate"] == 4.0
    assert result["interval"] is None
    assert result["valid_count"] == 1
    assert result["undefined_draws"] == 0


def test_bootstrap_sample_size_one_is_supported_with_original_two_valid() -> None:
    result = SYNTHESIS._bootstrap_metric(
        [1.0, 2.0],
        SYNTHESIS._mean_statistic,
        cell_index=0,
        draws=4,
        sample_size=1,
        root=SYNTHESIS.BOOTSTRAP_ROOT,
    )
    assert result["estimate"] == 1.5
    assert result["interval"] is not None
    assert result["undefined_draws"] == 0


def test_bootstrap_counts_zero_valid_draws_but_keeps_one_valid_draws() -> None:
    result = SYNTHESIS._bootstrap_metric(
        [1.0, None, 2.0],
        SYNTHESIS._mean_statistic,
        cell_index=0,
        draws=2,
        sample_size=2,
        root=SYNTHESIS.BOOTSTRAP_ROOT,
        indices=[np.asarray([0, 1]), np.asarray([1, 1])],
    )
    assert result["estimate"] == 1.5
    assert result["undefined_draws"] == 1
    assert result["interval"] is None


def test_bootstrap_ledger_has_unique_domain_two_addresses_and_seeds() -> None:
    ledger = SYNTHESIS.bootstrap_ledger(draws=4)
    assert len(ledger) == 40
    assert len({tuple(entry["address"]) for entry in ledger}) == 40
    assert len({entry["seed"] for entry in ledger}) == 40
    assert {entry["address"][2] for entry in ledger} == {2}
    first = ledger[0]
    expected_seed = int(
        np.random.SeedSequence([2026101102, 62, 2, 0, 0]).generate_state(1, dtype=np.uint64)[0]
    )
    assert first["seed"] == expected_seed


def test_audit_gate_and_machine_writers(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="independent audit"):
        SYNTHESIS.summarize_rows(
            _rows(), expected_replicates=6, bootstrap_draws=2, audit_status="pending"
        )
    result = SYNTHESIS.summarize_rows(
        _rows(), expected_replicates=6, bootstrap_draws=2, audit_status={"status": "accepted"}
    )
    paths = SYNTHESIS.write_summary(result, tmp_path / "summary")
    assert set(paths) == {"summary_json", "cell_csv", "contrast_csv"}
    assert json.loads(Path(paths["summary_json"]).read_text())["schema"] == result["schema"]
    assert Path(paths["cell_csv"]).is_file()
    assert Path(paths["contrast_csv"]).is_file()
