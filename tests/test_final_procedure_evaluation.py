from __future__ import annotations

import json
import math
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import numpy as np
import pytest

from latent_landscapes import capstone_calibration, capstone_public
from latent_landscapes import capstone_qualification as qualification
from latent_landscapes import final_procedure_evaluation as evaluation
from latent_landscapes import preinvasion_calibration as ranks
from latent_landscapes import preinvasion_fitting as fitting
from latent_landscapes import preinvasion_likelihood as likelihood


@pytest.fixture(scope="module")
def public() -> Any:
    site_ids = tuple(f"site-{index:03d}" for index in range(160))
    return SimpleNamespace(
        fixed=object(),
        setup=SimpleNamespace(
            site_ids=site_ids,
            site_splits=tuple("training" if index < 120 else "holdout" for index in range(160)),
            site_cluster_ids=tuple(f"cluster-{index // 5:02d}" for index in range(160)),
            exposure_score=np.asarray([[-0.5, 0.0], [0.5, 1.0]], dtype=np.float64),
            site_rows=np.asarray([index % 2 for index in range(160)]),
            site_cols=np.asarray([(index // 2) % 2 for index in range(160)]),
        ),
    )


@pytest.fixture(scope="module")
def bank(public: Any) -> likelihood.CompressedBank:
    arrivals = np.linspace(0.0, 65.0, 16 * 160, dtype=np.float64).reshape(16, 160)
    return likelihood.compress_bank(arrivals, public.setup.site_ids)


def observations(*, holdout_value: int = 0) -> dict[str, Any]:
    prey = np.zeros((160, 13), dtype=np.int8)
    prey[120:] = holdout_value
    predator = np.zeros((160, 6), dtype=np.int8)
    return {"prey_counts": prey, "predator_counts": predator}


def fit_result(
    model: str,
    index: int,
    *,
    status: str = "converged",
    h: float | None = None,
) -> fitting.FitResult:
    fixed_h = 1.0 if model.endswith("h1") else float(index + 1)
    return fitting.FitResult(
        model=model,
        h=fixed_h if h is None else h,
        beta=0.0 if model.startswith("constant") else 0.1,
        mu=0.001 + index * 0.0001,
        detection_sd=0.1,
        raw_logjoint=-10.0 - index,
        numerical_status=status,
        nfev=10 + index,
        elapsed_seconds=0.1,
        objective_gap=0.0,
    )


def main_row(*, spill: bool = False, invalid: str | None = None) -> dict[str, Any]:
    fits = {}
    for index, model in enumerate(evaluation.MODEL_NAMES):
        h = np.nextafter(10.0, math.inf) if spill and model == "adjusted_free_h" else None
        fit = fit_result(model, index, status="invalid" if model == invalid else "converged", h=h)
        fits[model] = qualification.jsonable(asdict(fit))
    return {
        "schema": "goal062-main-fit-v1",
        "history_index": 0,
        "cell_index": 0,
        "cell_label": "L1",
        "replicate": 0,
        "fits": fits,
    }


def test_fixed_cells_and_mechanical_seed_ledger_preserve_addresses() -> None:
    assert [(cell.index, cell.label) for cell in evaluation.CELLS] == [
        (0, "L1"),
        (1, "L3"),
        (2, "L5"),
        (3, "H1"),
        (4, "H3"),
        (5, "H5"),
        (6, "B_L1"),
        (7, "B_L3"),
        (8, "B_H1"),
        (9, "B_H3"),
    ]
    assert all(cell.beta == 0.5 for cell in evaluation.CELLS[:6])
    assert all(cell.beta is None for cell in evaluation.CELLS[6:])

    ledger = evaluation.seed_ledger(root=evaluation.MECHANICAL_ROOT)
    check = evaluation.validate_seed_ledger(ledger, root=evaluation.MECHANICAL_ROOT)
    assert check["passed"]
    assert check["expected_rows"] == 27_000
    assert len(ledger) == 27_000
    assert sum(row["stage"] == "background_field" for row in ledger) == 2_000
    expected_address = [evaluation.MECHANICAL_ROOT, 62, 1, 0, 0, 1]
    expected_seed = int(
        np.random.SeedSequence(expected_address).generate_state(1, dtype=np.uint64)[0]
    )
    assert ledger[0]["address"] == expected_address
    assert ledger[0]["seed"] == expected_seed
    with pytest.raises(ValueError, match="only for B100"):
        evaluation.stage_seed(0, 0, "background_field", root=evaluation.MECHANICAL_ROOT)


def test_history_seed_records_and_generators_keep_b100_beta_undefined(
    public: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, Any, dict[str, Any]]] = []

    def exact(
        _fixed: Any, _setup: Any, truth: Any, seeds: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        calls.append(("exact", truth, seeds))
        return observations(), {"arrival": np.arange(160.0), "truth": asdict(truth)}

    def b100(
        _fixed: Any, _setup: Any, truth: Any, seeds: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        calls.append(("B100-A", truth, seeds))
        return observations(), {
            "arrival": np.arange(160.0),
            "map_hazard": np.full((2, 2), truth.mean_hazard),
            "truth": asdict(truth),
        }

    monkeypatch.setattr(capstone_public, "generate_exact_history", exact)
    monkeypatch.setattr(capstone_public, "generate_b100_history", b100)
    exact_observed, exact_evaluator = evaluation.generate_history(
        public, cell=0, replicate=2, root=evaluation.MECHANICAL_ROOT
    )
    b_observed, b_evaluator = evaluation.generate_history(
        public, cell=6, replicate=2, root=evaluation.MECHANICAL_ROOT
    )

    assert exact_observed["index"] == 2
    assert b_observed["index"] == 3002
    assert exact_observed["site_ids"].shape == (160,)
    assert exact_observed["training_mask"].sum() == 120
    assert exact_evaluator["truth"]["generating_beta"] == 0.5
    assert b_evaluator["truth"]["generating_beta"] is None
    assert "beta" not in b_evaluator["truth"]
    assert set(calls[0][2]["streams"]) == set(evaluation.BASE_STAGES)
    assert set(calls[1][2]["streams"]) == set(evaluation.STAGES)
    assert calls[1][2]["addresses"]["background_field"] == [
        evaluation.MECHANICAL_ROOT,
        62,
        1,
        6,
        2,
        6,
    ]
    assert exact_evaluator["map_hazard"].shape == (2, 2)
    assert exact_evaluator["map_hazard"].mean() == pytest.approx(0.001)


def test_observation_data_uses_canonical_disjoint_split_and_ignores_holdout_for_training(
    public: Any, bank: likelihood.CompressedBank
) -> None:
    first = evaluation.make_observation_data(public, bank, observations(holdout_value=0))
    changed = evaluation.make_observation_data(public, bank, observations(holdout_value=2))
    assert len(first.training.observations.site_ids) == 120
    assert len(first.holdout.observations.site_ids) == 40
    assert first.training.bank.site_ids == public.setup.site_ids[:120]
    assert first.holdout.bank.site_ids == public.setup.site_ids[120:]
    np.testing.assert_array_equal(
        first.training.observations.prey_counts,
        changed.training.observations.prey_counts,
    )
    assert not np.array_equal(
        first.holdout.observations.prey_counts,
        changed.holdout.observations.prey_counts,
    )


def test_fit_main_persists_before_any_diagnostic_and_contains_only_main_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fits = {model: fit_result(model, index) for index, model in enumerate(evaluation.MODEL_NAMES)}
    paired = fitting.PairedFitResult(
        2.0,
        fits,
        {"adjusted": 2.0, "constant": 1.0},
        fitting.CostSummary(40, 0, 40, 1.0, 0.0, 1.0),
    )
    train = SimpleNamespace()
    monkeypatch.setattr(
        evaluation,
        "make_observation_data",
        lambda *_args, **_kwargs: SimpleNamespace(training=train),
    )
    monkeypatch.setattr(fitting, "paired_fit", lambda data, callback: paired)
    monkeypatch.setattr(
        qualification,
        "fit_loglikelihood",
        lambda _data, **parameters: next(
            fit.raw_logjoint for fit in fits.values() if fit.parameters == parameters
        ),
    )
    monkeypatch.setattr(
        fitting,
        "profile_h",
        lambda *_args, **_kwargs: pytest.fail("fit_main ran a diagnostic"),
    )
    path = tmp_path / "main.json"
    row = evaluation.fit_main(
        cast(Any, object()),
        cast(Any, SimpleNamespace(bank_size=131072)),
        {},
        cell=0,
        replicate=4,
        output=path,
    )
    assert path.is_file()
    assert json.loads(path.read_text(encoding="utf-8")) == row
    assert row["schema"] == "goal062-main-fit-v1"
    assert row["history_index"] == 4
    assert row["all_main_replays_passed"]
    assert row["observed_effect_statistic"] == 2.0
    assert set(row["fits"]) == set(evaluation.MODEL_NAMES)
    assert "profiles" not in row and "heldout" not in row and "truth" not in row
    with pytest.raises(FileExistsError, match="replace"):
        evaluation.fit_main(
            cast(Any, object()),
            cast(Any, SimpleNamespace(bank_size=131072)),
            {},
            cell=0,
            replicate=4,
            output=path,
        )


def test_pre_surface_is_exactly_765_nodes(
    public: Any, bank: likelihood.CompressedBank, monkeypatch: pytest.MonkeyPatch
) -> None:
    training = evaluation.make_observation_data(public, bank, observations()).training
    monkeypatch.setattr(
        capstone_calibration,
        "pre_score",
        lambda _obs, _map, _site, node: np.asarray([float(node)]),
    )
    surface = evaluation.pre_surface(training)
    np.testing.assert_array_equal(surface, np.arange(765, dtype=np.float64))
    assert not surface.flags.writeable


def test_diagnostics_use_stored_main_and_do_not_replace_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    main = main_row()
    monkeypatch.setattr(
        fitting,
        "paired_fit",
        lambda *_args, **_kwargs: pytest.fail("diagnostics refitted the main models"),
    )

    def profile(_data: Any, _callback: Any, fit: fitting.FitResult) -> fitting.ProfileResult:
        coordinate = "h" if fit.model != "adjusted_free_h" else "beta"
        return fitting.ProfileResult(
            coordinate,
            np.asarray([1.0, 2.0]),
            np.asarray([fit.raw_logjoint, fit.raw_logjoint + 1.0]),
            (fit.parameters, fit.parameters),
            ("converged", "converged"),
            2,
            0.0,
            True,
            None,
        )

    monkeypatch.setattr(fitting, "profile_h", profile)
    monkeypatch.setattr(fitting, "profile_beta", profile)
    monkeypatch.setattr(
        qualification,
        "coarse_grid_audit",
        lambda _data: {
            "points": 1350,
            "max_logjoint": {name: np.asarray([-9.0]) for name in evaluation.MODEL_NAMES},
            "raw_points": [{"point": {}, "training_logjoint_by_history_and_h": [0.0]}],
        },
    )
    monkeypatch.setattr(
        qualification,
        "check_grid_against_fits",
        lambda _grid, _fits: {"passed": False, "gaps": {"constant_free_h": 1.0}},
    )
    result = evaluation.diagnose_main(cast(Any, SimpleNamespace()), main)
    assert result["schema"] == "goal062-main-diagnostics-v1"
    assert result["lattice"]["points"] == 1350
    assert result["profile_main_gaps"] == dict.fromkeys(
        ("constant_h", "adjusted_h", "adjusted_beta"), 1.0
    )
    assert result["main_fits_unchanged"] == main["fits"]


def test_holdout_scores_fixed_fits_with_site_cluster_and_six_contrasts(
    public: Any, bank: likelihood.CompressedBank, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = evaluation.make_observation_data(public, bank, observations()).holdout
    main = main_row(spill=True)
    seen_h: list[float] = []

    def point_score(
        _observed: Any,
        _bank: Any,
        h: float,
        beta: float,
        mu: float,
        _map: Any,
        _site: Any,
        *,
        detection_sd: float,
    ) -> Any:
        del beta, mu, detection_sd
        seen_h.append(h)
        return SimpleNamespace(
            conditional_prey_site_loglikelihood=np.full((1, 40), h, dtype=np.float64)
        )

    monkeypatch.setattr(likelihood, "point_score", point_score)
    result = evaluation.score_holdout(public, data, main)
    assert len(result["models"]) == 4
    assert all(row["status"] == "available" for row in result["models"].values())
    assert all(len(row["site_nats"]) == 40 for row in result["models"].values())
    assert all(len(row["cluster_nats"]) == 8 for row in result["models"].values())
    assert len(result["pair_contrasts"]) == 6
    assert np.nextafter(10.0, math.inf) in seen_h
    assert main["fits"]["adjusted_free_h"]["h"] == np.nextafter(10.0, math.inf)

    invalid_main = main_row(invalid="constant_h1")
    invalid_main["fits"]["constant_h1"]["starts"] = [
        {
            "initial_parameters": {"h": None, "beta": None, "mu": None, "detection_sd": None},
            "final_parameters": {"h": None, "beta": None, "mu": None, "detection_sd": None},
            "raw_logjoint": None,
            "objective": None,
            "success": False,
            "status": -1,
            "message": "invalid mechanical fixture",
            "nfev": 0,
            "method": "L-BFGS-B",
        }
    ]
    unavailable = evaluation.score_holdout(public, data, invalid_main)
    assert unavailable["models"]["constant_h1"]["status"] == "unavailable"
    affected = [
        row for row in unavailable["pair_contrasts"] if "constant_h1" in (row["left"], row["right"])
    ]
    assert all(row["left_minus_right_nats"] is None for row in affected)


def reference_cache() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    screen = np.zeros((99, 765), dtype=np.float64)
    effect = np.zeros((765, 999), dtype=np.float64)
    effect[:, :39] = 1.0
    valid = np.ones(765, dtype=bool)
    return screen, effect, valid


def test_cached_decision_uses_inclusive_ties_and_exact_point05_rule() -> None:
    screen, effect, valid = reference_cache()
    result = evaluation.decide_cached(
        ["case"],
        np.zeros((1, 765)),
        [1.0],
        screen,
        effect,
        valid,
        computation_complete=True,
    )
    decision = result["decisions"][0]
    assert result["screens"][0]["candidate_indices"] == list(range(765))
    assert decision["p_value"] == pytest.approx(0.05)
    assert decision["status"] == "declared"
    assert decision["declared"] is True
    assert decision["node_pvalues"][0] == [0, pytest.approx(0.04)]


def test_cached_decision_fail_closed_table_screen_and_empty_set_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    screen, effect, valid = reference_cache()
    valid[17] = False
    invalid_table = evaluation.decide_cached(
        ["case"], np.zeros((1, 765)), [1.0], screen, effect, valid, computation_complete=True
    )
    assert invalid_table["decisions"][0]["status"] == "abstain_no_fit"

    invalid_screen = screen.copy()
    invalid_screen[0, 0] = np.nan
    shared = evaluation.decide_cached(
        ["case"],
        np.zeros((1, 765)),
        [1.0],
        invalid_screen,
        effect,
        np.ones(765, dtype=bool),
        computation_complete=True,
    )
    assert shared["decisions"][0]["status"] == "abstain_missing_screen_table"

    monkeypatch.setattr(
        capstone_calibration,
        "screen_cases",
        lambda *_args, **_kwargs: (
            ranks.ScreenResult("case", "empty", (), np.zeros(765), "empty nuisance set"),
        ),
    )
    empty = evaluation.decide_cached(
        ["case"],
        np.zeros((1, 765)),
        [1.0],
        screen,
        effect,
        np.ones(765, dtype=bool),
        computation_complete=True,
    )
    assert empty["decisions"][0]["status"] == "abstain_empty"
    assert empty["decisions"][0]["p_value"] == 1.0

    with pytest.raises(capstone_calibration.CalibrationPendingError, match="pending"):
        evaluation.decide_cached(
            ["case"],
            np.zeros((1, 765)),
            [1.0],
            screen,
            effect,
            np.ones(765, dtype=bool),
            computation_complete=False,
        )
