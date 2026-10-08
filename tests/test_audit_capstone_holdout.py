from __future__ import annotations

import importlib.util
import itertools
import sys
from pathlib import Path

import numpy as np

_SPEC = importlib.util.spec_from_file_location(
    "audit_capstone_holdout",
    Path(__file__).parents[1] / "scripts" / "audit_capstone_holdout.py",
)
assert _SPEC is not None and _SPEC.loader is not None
audit = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = audit
_SPEC.loader.exec_module(audit)


def test_merge_uses_site_identity_for_interleaved_split_and_reordered_inputs() -> None:
    canonical = tuple(f"site-{index:03d}" for index in range(160))
    training_mask = np.asarray([index % 4 != 0 for index in range(160)], dtype=bool)
    training_ids = tuple(np.asarray(canonical)[training_mask][::-1])
    holdout_ids = tuple(np.asarray(canonical)[~training_mask][::-1])
    values = np.asarray([index % 3 for index in range(160)], dtype=np.int64)
    lookup = {site_id: index for index, site_id in enumerate(canonical)}

    train_positions = np.asarray([lookup[site_id] for site_id in training_ids])
    holdout_positions = np.asarray([lookup[site_id] for site_id in holdout_ids])
    training = audit.ObservationBundle(
        audit.EXPECTED_CASE_IDS,
        training_ids,
        np.broadcast_to(values[train_positions][None, :, None], (4, 120, 13)).copy(),
        np.broadcast_to(values[train_positions][None, :, None], (4, 120, 6)).copy(),
    )
    holdout = audit.ObservationBundle(
        audit.EXPECTED_CASE_IDS,
        holdout_ids,
        np.broadcast_to(values[holdout_positions][None, :, None], (4, 40, 13)).copy(),
        np.broadcast_to(values[holdout_positions][None, :, None], (4, 40, 6)).copy(),
    )
    prey, predator, receipt = audit.merge_canonical_observations(
        training, holdout, canonical, training_mask
    )
    np.testing.assert_array_equal(prey[0, :, 0], values)
    np.testing.assert_array_equal(predator[0, :, 0], values)
    assert receipt["method"].startswith("identifier-indexed")
    assert receipt["training_positions"] == train_positions.tolist()
    assert receipt["holdout_positions"] == holdout_positions.tolist()


def _comparison_fixture() -> tuple[dict, dict, dict]:
    diagnostics = {
        "main_statuses_converged": True,
        "audit_passed": True,
        "diagnostic_passed": True,
        "diagnostics_change_declaration": False,
    }
    direct_totals = {
        "case-00": (-10.0, -8.0, -9.0, -8.0),
        "case-01": (-10.0, -8.000000004, -9.0, -8.0),
        "case-02": (-8.0, -8.5, -9.0, -9.5),
        "case-03": (-10.0, -8.0, -9.0, -8.5),
    }
    main_totals = dict(direct_totals)
    main_totals["case-01"] = (-10.0, -7.999999999, -9.0, -8.0)
    independent: dict[str, dict] = {}
    main_cases: list[dict] = []
    receipts: dict[str, dict] = {}
    for history, case_id in enumerate(audit.EXPECTED_CASE_IDS):
        direct_by_model = dict(zip(audit.MODEL_ORDER, direct_totals[case_id], strict=True))
        main_by_model = dict(zip(audit.MODEL_ORDER, main_totals[case_id], strict=True))
        models = {}
        main_fits = {}
        hashes = {}
        flags = {}
        for model in audit.MODEL_ORDER:
            parameters = {"h": 1.0, "beta": 0.0, "mu": 0.002, "detection_sd": 0.1}
            fit = {
                "model": model,
                **parameters,
                "raw_logjoint": -100.0,
                "numerical_status": "converged",
            }
            direct_total = direct_by_model[model]
            main_total = main_by_model[model]
            models[model] = {
                "parameters": parameters,
                "conditional_prey_total_nats": direct_total,
                "conditional_prey_nats_per_site": direct_total / 40.0,
                "conditional_prey_site_nats": [direct_total / 40.0] * 40,
                "cluster_contributions_nats": {
                    f"cluster-{index}": direct_total / 8.0 for index in range(8)
                },
            }
            main_fits[model] = {
                "status": "available",
                "fit_status": "converged",
                "fit": fit,
                "diagnostic_flags": diagnostics,
                "total_nats": main_total,
                "mean_nats_per_site": main_total / 40.0,
                "site_nats": [main_total / 40.0] * 40,
                "cluster_nats": {f"cluster-{index}": main_total / 8.0 for index in range(8)},
            }
            hashes[model] = audit.canonical_json_sha256(fit)
            flags[model] = diagnostics
        direct_maximum = max(direct_by_model.values())
        direct_winners = [
            model for model in audit.MODEL_ORDER if direct_by_model[model] == direct_maximum
        ]
        direct_ordered = sorted(direct_by_model.values(), reverse=True)
        independent[case_id] = {
            "models": models,
            "pairwise_differences": [
                {
                    "left": left,
                    "right": right,
                    "left_minus_right_nats": direct_by_model[left] - direct_by_model[right],
                }
                for left, right in itertools.combinations(audit.MODEL_ORDER, 2)
            ],
            "winner_set": direct_winners,
            "winning_margin_nats": direct_ordered[0] - direct_ordered[1],
        }
        main_maximum = max(main_by_model.values())
        main_winners = [
            model for model in audit.MODEL_ORDER if main_by_model[model] == main_maximum
        ]
        main_ordered = sorted(main_by_model.values(), reverse=True)
        predicted = list(audit.LEADING_PAIRS[case_id])
        main_cases.append(
            {
                "case_id": case_id,
                "history": history,
                "fits": main_fits,
                "pair_differences": [
                    {
                        "left": left,
                        "right": right,
                        "left_minus_right_nats": main_by_model[left] - main_by_model[right],
                    }
                    for left, right in itertools.combinations(audit.MODEL_ORDER, 2)
                ],
                "winner_set": main_winners,
                "winning_margin_nats": main_ordered[0] - main_ordered[1],
                "predicted_pair": predicted,
                "pair_hit": bool(set(main_winners) & set(predicted)),
                "co_winners_outside_predicted_pair": [
                    model for model in main_winners if model not in predicted
                ],
                "named_two_of_four": True,
            }
        )
        receipts[case_id] = {
            "fit_record_sha256": hashes,
            "diagnostic_flags": flags,
        }
    return {"cases": main_cases}, independent, receipts


def test_subtolerance_rank_disagreement_is_preserved_without_failing_scores() -> None:
    main, independent, receipts = _comparison_fixture()
    comparison = audit.compare_main_results(
        main, independent, receipts, tolerance=audit.SCORE_TOLERANCE
    )
    assert comparison["passed"] is True
    rank_row = next(
        row
        for row in comparison["rows"]
        if row.get("case_id") == "case-01" and row.get("aggregation") == "pairwise_and_winner"
    )
    assert rank_row["main_winner_set"] == ["adjusted_free_h"]
    assert rank_row["independent_winner_set"] == ["adjusted_h1"]
    assert rank_row["winner_sets_match_exactly"] is False
    assert rank_row["ranking_numerically_resolved_at_audit_tolerance"] is False


def test_exact_tie_is_retained_as_zero_winning_margin() -> None:
    main, independent, receipts = _comparison_fixture()
    comparison = audit.compare_main_results(
        main, independent, receipts, tolerance=audit.SCORE_TOLERANCE
    )
    tie_row = next(
        row
        for row in comparison["rows"]
        if row.get("case_id") == "case-00" and row.get("aggregation") == "pairwise_and_winner"
    )
    assert tie_row["main_winner_set"] == ["adjusted_free_h", "adjusted_h1"]
    assert tie_row["main_minus_independent_winning_margin_nats"] == 0.0
    assert tie_row["ranking_numerically_resolved_at_audit_tolerance"] is False
