from __future__ import annotations

import ast
import copy
import importlib.util
import math
import sys
from itertools import combinations, product
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

import latent_landscapes.capstone_public as public_api
import latent_landscapes.final_procedure_evaluation as producer
from latent_landscapes.misspecification_generator import build_generator_setup

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit_final_procedure_evaluation.py"
sys.path.insert(0, str(_SCRIPT.parent))
_SPEC = importlib.util.spec_from_file_location("audit_final_procedure_evaluation", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
audit = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = audit
_SPEC.loader.exec_module(audit)


def _resources() -> Any:
    site_ids = tuple(f"site-{index:03d}" for index in range(160))
    training = np.asarray([True] * 120 + [False] * 40)
    context = SimpleNamespace(
        site_ids=site_ids,
        training=training,
        map_a=np.zeros((72, 84), dtype=np.float64),
        site_a=np.zeros(160, dtype=np.float64),
        cluster_ids=tuple(f"cluster-{index // 5:02d}" for index in range(160)),
    )
    setup = SimpleNamespace(
        site_rows=np.zeros(160, dtype=np.int64),
        site_cols=np.zeros(160, dtype=np.int64),
        exposure_score=np.zeros((72, 84), dtype=np.float64),
    )
    return audit.AuditResources(SimpleNamespace(landscape=None), setup, context, object(), {})


def _metadata(*, cell: int = 0, replicate: int = 0) -> dict[str, Any]:
    stages = audit.B100_STAGES if cell >= 6 else audit.BASE_STAGES
    streams = {
        name: audit.history_seed(cell, replicate, stage, root=audit.MECHANICAL_ROOT)
        for name, stage in stages.items()
    }
    addresses = {
        name: [audit.MECHANICAL_ROOT, 62, 1, cell, replicate, stage]
        for name, stage in stages.items()
    }
    return {
        "schema": audit.HISTORY_SCHEMA,
        "history_index": cell * 500 + replicate,
        "cell_index": cell,
        "cell_label": audit.CELLS[cell].label,
        "replicate": replicate,
        "truth": audit.expected_truth(cell),
        "seeds": {
            "root": audit.MECHANICAL_ROOT,
            "namespace": 62,
            "domain": 1,
            "cell": cell,
            "replicate": replicate,
            "address_order": list(audit.ADDRESS_ORDER),
            "streams": streams,
            "addresses": addresses,
            "stage_records": {
                name: {"stage": stages[name], "address": addresses[name], "seed": seed}
                for name, seed in streams.items()
            },
        },
    }


def _arrays(resources: Any) -> dict[str, Any]:
    return {
        "site_ids": np.asarray(resources.context.site_ids),
        "training_mask": np.asarray(resources.context.training, dtype=bool),
        "prey_counts": np.zeros((160, 13), dtype=np.int8),
        "predator_counts": np.zeros((160, 6), dtype=np.int8),
        "arrival": np.zeros(160, dtype=np.float64),
        "loss": np.ones(160, dtype=np.float64),
        "site_hazard": np.full(160, 0.001, dtype=np.float64),
        "site_detection": np.full(160, 0.65, dtype=np.float64),
        "prey_alive": np.ones((160, 13), dtype=bool),
        "map_hazard": np.full((72, 84), 0.001, dtype=np.float64),
    }


def _score(point: Any) -> float:
    return (
        float(point["h"])
        + float(point["beta"])
        + 100.0 * float(point["mu"])
        + float(point["detection_sd"])
    )


def _start_record(
    initial: dict[str, float],
    final: dict[str, float],
    objective: float,
    *,
    success: bool,
    status: int | str,
    message: str,
    method: str,
) -> dict[str, Any]:
    return {
        "initial_parameters": dict(initial),
        "final_parameters": dict(final),
        "raw_logjoint": -objective if objective < 1e299 else None,
        "objective": objective,
        "success": success,
        "status": status,
        "message": message,
        "nfev": 1,
        "method": method,
    }


def _fit(
    model: str,
    h: float,
    beta: float,
    *,
    status: str = "converged",
    null_fit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    point = {"h": h, "beta": beta, "mu": 0.0025, "detection_sd": 0.2}
    objective = -_score(point)
    converged = status == "converged"
    starts = [
        _start_record(
            dict(initial),
            point,
            objective + index,
            success=converged,
            status=0 if converged else 1,
            message="synthetic converged" if converged else "synthetic failure",
            method="L-BFGS-B",
        )
        for index, initial in enumerate(audit.DOMAIN_STARTS)
    ]
    if model.endswith("free_h"):
        assert null_fit is not None
        null_point = {name: float(null_fit[name]) for name in audit.PARAMETER_NAMES}
        null_converged = null_fit["numerical_status"] == "converged"
        starts.append(
            _start_record(
                null_point,
                null_point,
                -float(null_fit["raw_logjoint"]),
                success=null_converged,
                status="nested_converged" if null_converged else "nested_unconverged",
                message=(
                    "nested candidate"
                    if null_converged
                    else "nested candidate from unconverged fit"
                ),
                method="candidate",
            )
        )
    warnings: list[str] = []
    if not converged:
        starts.append(
            _start_record(
                point,
                point,
                objective + 2.0,
                success=False,
                status=1,
                message="synthetic Powell failure",
                method="Powell",
            )
        )
        warnings.append("Powell refinement did not improve the best L-BFGS-B objective")
    return {
        "model": model,
        **point,
        "raw_logjoint": _score(point),
        "numerical_status": status,
        "nfev": len(starts),
        "elapsed_seconds": 0.0,
        "starts": starts,
        "objective_gap": 1.0,
        "boundary_flags": list(audit._expected_boundary_flags(point)),
        "warnings": warnings,
    }


def _main(metadata: dict[str, Any], *, adjusted_status: str = "converged") -> dict[str, Any]:
    constant_null = _fit("constant_h1", 1.0, 0.0)
    adjusted_null = _fit("adjusted_h1", 1.0, 0.2, status=adjusted_status)
    fits = {
        "constant_free_h": _fit(
            "constant_free_h", 2.0, 0.0, null_fit=constant_null
        ),
        "adjusted_free_h": _fit(
            "adjusted_free_h",
            2.0,
            0.2,
            status=adjusted_status,
            null_fit=adjusted_null,
        ),
        "constant_h1": constant_null,
        "adjusted_h1": adjusted_null,
    }
    constant_delta = fits["constant_free_h"]["raw_logjoint"] - fits["constant_h1"][
        "raw_logjoint"
    ]
    adjusted_delta = fits["adjusted_free_h"]["raw_logjoint"] - fits["adjusted_h1"][
        "raw_logjoint"
    ]
    valid = adjusted_status == "converged" and adjusted_delta >= -1e-6
    return {
        "schema": audit.MAIN_SCHEMA,
        **{
            key: metadata[key]
            for key in ("history_index", "cell_index", "cell_label", "replicate")
        },
        "representation": "full",
        "bank_size": audit.BANK_SIZE,
        "statistics": {
            "constant": 2.0 * max(0.0, constant_delta),
            "adjusted": 2.0 * max(0.0, adjusted_delta),
        },
        "observed_effect_statistic": (
            2.0 * max(0.0, adjusted_delta) if valid else None
        ),
        "fits": fits,
        "main_statuses_converged": {
            name: row["numerical_status"] == "converged" for name, row in fits.items()
        },
        "nesting_gaps": {"constant": -constant_delta, "adjusted": -adjusted_delta},
        "nesting_status": {"constant": "passed", "adjusted": "passed"},
        "observed_adjusted_validity": {
            "valid": valid,
            "null_finite": True,
            "free_finite": True,
            "null_converged": adjusted_status == "converged",
            "free_converged": adjusted_status == "converged",
            "free_minus_null": adjusted_delta,
            "minimum_free_minus_null": -1e-6,
        },
        "compressed_score_replay": {
            name: {"difference": 0.0, "status": "passed", "tolerance": 1e-8}
            for name in fits
        },
        "all_main_replays_passed": True,
    }


def _fake_direct(
    _bank: Any,
    context: Any,
    _prey: Any,
    _predator: Any,
    point: Any,
) -> dict[str, Any]:
    base = _score(point)
    site = base + np.arange(40, dtype=np.float64) / 100.0
    clusters = np.asarray(context.cluster_ids)[~np.asarray(context.training, dtype=bool)]
    return {
        "training_logjoint": base,
        "holdout_conditional_prey_total": float(site.sum()),
        "holdout_conditional_prey_site": site,
        "holdout_cluster_totals": {
            str(cluster): float(site[clusters == cluster].sum())
            for cluster in sorted(set(clusters))
        },
    }


def test_auditor_import_boundary_excludes_producer_likelihood_and_fitter() -> None:
    tree = ast.parse(_SCRIPT.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    )
    forbidden = {
        "latent_landscapes.final_procedure_evaluation",
        "latent_landscapes.preinvasion_likelihood",
        "latent_landscapes.preinvasion_fitting",
    }
    assert imported.isdisjoint(forbidden)


@pytest.mark.parametrize("perturbation", ["seed", "truth", "mask"])
def test_input_audit_blocks_seed_truth_and_split_perturbations(
    perturbation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    resources = _resources()
    metadata = _metadata()
    arrays = _arrays(resources)
    replay = {name: np.asarray(arrays[name]) for name in audit.GENERATOR_ARRAY_NAMES}
    monkeypatch.setattr(audit, "replay_history", lambda *_args: replay)
    accepted = audit.audit_history_inputs(metadata, arrays, resources)
    assert accepted["passed"] is True
    assert accepted["counts"]["training_sites"] == 120

    changed_metadata = copy.deepcopy(metadata)
    changed_arrays = {name: np.asarray(value).copy() for name, value in arrays.items()}
    if perturbation == "seed":
        changed_metadata["seeds"]["streams"]["prey_loss"] += 1
    elif perturbation == "truth":
        changed_metadata["truth"]["effect"] = 3.0
    else:
        changed_arrays["training_mask"][[0, 159]] = [False, True]
    rejected = audit.audit_history_inputs(changed_metadata, changed_arrays, resources)
    assert rejected["release_blocked"] is True


@pytest.mark.parametrize("cell", [0, 6])
def test_whole_generator_replay_matches_mechanical_exact_and_b100(cell: int) -> None:
    map_seed = public_api._u64_seed(audit.MECHANICAL_ROOT, public_api.MAP_STAGE, 0)
    sampling_seed = public_api._u64_seed(audit.MECHANICAL_ROOT, public_api.SAMPLING_STAGE, 0)
    fixed = public_api._make_fixed(map_seed, sampling_seed)
    setup = build_generator_setup(fixed)
    public = public_api.PublicInputs(fixed, setup, {"root": audit.MECHANICAL_ROOT})
    observed, evaluator = producer.generate_history(
        public, cell=cell, replicate=0, root=audit.MECHANICAL_ROOT
    )
    training = np.asarray(observed["training_mask"], dtype=bool)
    context = SimpleNamespace(
        site_ids=tuple(str(value) for value in observed["site_ids"]),
        training=training,
        map_a=np.asarray(setup.exposure_score, dtype=np.float64),
        site_a=np.asarray(setup.exposure_score[setup.site_rows, setup.site_cols]),
        cluster_ids=tuple(str(value) for value in setup.site_cluster_ids),
    )
    resources = audit.AuditResources(fixed, setup, context, object(), {})
    metadata = {
        "schema": audit.HISTORY_SCHEMA,
        "history_index": cell * 500,
        "cell_index": cell,
        "cell_label": audit.CELLS[cell].label,
        "replicate": 0,
        "truth": evaluator["truth"],
        "seeds": evaluator["seeds"],
    }
    arrays = {
        "site_ids": observed["site_ids"],
        "training_mask": observed["training_mask"],
        "prey_counts": observed["prey_counts"],
        "predator_counts": observed["predator_counts"],
        **{name: evaluator[name] for name in audit.GENERATOR_ARRAY_NAMES[2:]},
    }
    receipt = audit.audit_history_inputs(metadata, arrays, resources)
    assert receipt["release_blocked"] is False
    assert receipt["all_generator_arrays_bitwise"] is True


def test_main_audit_preserves_nonconvergence_but_blocks_score_corruption(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = _resources()
    metadata = _metadata()
    arrays = _arrays(resources)
    monkeypatch.setattr(audit, "direct_point_score", _fake_direct)

    nonconverged = _main(metadata, adjusted_status="failed_optimizer")
    receipt = audit.audit_history_main(metadata, arrays, nonconverged, resources)
    assert receipt["release_blocked"] is False
    assert receipt["numerical_status"] == "terminal_invalid"
    assert receipt["declaration_pair_valid"] is False
    assert receipt["effect_recovery_available"] is False

    corrupted = _main(metadata)
    corrupted["fits"]["constant_free_h"]["raw_logjoint"] += 1e-4
    rejected = audit.audit_history_main(metadata, arrays, corrupted, resources)
    assert rejected["release_blocked"] is True
    assert "score mismatch" in rejected["reason"]


def test_main_audit_blocks_runner_statistic_corruption_with_unchanged_rank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = _resources()
    metadata = _metadata()
    arrays = _arrays(resources)
    monkeypatch.setattr(audit, "direct_point_score", _fake_direct)

    corrupted = _main(metadata)
    corrupted["observed_effect_statistic"] += 1e-4
    receipt = audit.audit_history_main(metadata, arrays, corrupted, resources)

    assert receipt["release_blocked"] is True
    assert "observed effect statistic" in receipt["reason"]


@pytest.mark.parametrize(
    ("perturbation", "reason"),
    [
        ("start_record", "start raw score"),
        ("nfev", "nfev total"),
        ("status", "selected status"),
        ("objective_gap", "gap"),
        ("boundary_flags", "boundary flags"),
        ("nested_parameters", "schema changed"),
    ],
)
def test_main_audit_blocks_fit_record_bookkeeping_mutations(
    perturbation: str,
    reason: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = _resources()
    metadata = _metadata()
    arrays = _arrays(resources)
    monkeypatch.setattr(audit, "direct_point_score", _fake_direct)
    corrupted = _main(metadata)
    fit = corrupted["fits"]["constant_h1"]
    if perturbation == "start_record":
        fit["starts"][0]["raw_logjoint"] += 0.1
    elif perturbation == "nfev":
        fit["nfev"] += 1
    elif perturbation == "status":
        fit["numerical_status"] = "failed_optimizer"
    elif perturbation == "objective_gap":
        fit["objective_gap"] += 0.1
    elif perturbation == "boundary_flags":
        fit["boundary_flags"] = []
    else:
        fit["parameters"] = {
            "h": 1.0,
            "beta": 0.0,
            "mu": 0.0025,
            "detection_sd": 0.2,
        }
        fit["h"] = 2.0

    receipt = audit.audit_history_main(metadata, arrays, corrupted, resources)

    assert receipt["release_blocked"] is True
    assert reason in receipt["reason"]


def test_main_audit_preserves_one_invalid_start_as_observed_numeric_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = _resources()
    metadata = _metadata()
    arrays = _arrays(resources)
    monkeypatch.setattr(audit, "direct_point_score", _fake_direct)
    main = _main(metadata)
    failed_start = main["fits"]["constant_h1"]["starts"][-1]
    failed_start.update(
        {
            "raw_logjoint": None,
            "objective": 1e300,
            "success": False,
            "status": 2,
            "message": "synthetic nonfinite objective",
        }
    )

    receipt = audit.audit_history_main(metadata, arrays, main, resources)

    assert receipt["release_blocked"] is False
    assert receipt["numerical_status"] == "valid"


def test_main_audit_blocks_finite_objective_with_nonfinite_final_coordinates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = _resources()
    metadata = _metadata()
    arrays = _arrays(resources)
    monkeypatch.setattr(audit, "direct_point_score", _fake_direct)
    main = _main(metadata)
    inconsistent = main["fits"]["constant_h1"]["starts"][-1]
    inconsistent["final_parameters"]["h"] = None
    inconsistent["success"] = False

    receipt = audit.audit_history_main(metadata, arrays, main, resources)

    assert receipt["release_blocked"] is True
    assert "finite objective with nonfinite final coordinates" in receipt["reason"]


def _decision(
    *,
    effect_bad: bool = False,
    perturb_rank: bool = False,
) -> dict[str, Any]:
    valid = np.ones(765, dtype=bool)
    if effect_bad:
        valid[17] = False
    result = producer.decide_cached(
        ["history-0000"],
        np.zeros((1, 765), dtype=np.float64),
        [2.0],
        np.zeros((99, 765), dtype=np.float64),
        np.zeros((765, 999), dtype=np.float64),
        valid,
        computation_complete=True,
    )
    if perturb_rank:
        result["decisions"][0]["node_pvalues"][9][1] = 0.002
    return result


def test_screen_rank_audit_handles_bad_rows_and_rejects_rank_substitution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = _resources()
    metadata = _metadata()
    arrays = _arrays(resources)
    surface = np.zeros(765, dtype=np.float64)
    monkeypatch.setattr(audit, "_observed_surface", lambda *_args: surface.copy())
    main_audit = {
        "release_blocked": False,
        "declaration_pair_valid": True,
        "adjusted_statistic": 2.0,
    }
    screen = np.zeros((765, 99), dtype=np.float64)
    effect = np.zeros((765, 999), dtype=np.float64)
    references = audit.make_reference_cache(screen, effect)

    accepted = audit.audit_history_screen_decision(
        metadata,
        arrays,
        surface,
        _decision(),
        main_audit,
        references,
        resources,
    )
    assert accepted["release_blocked"] is False
    assert accepted["declared"] is True
    assert accepted["counts"] == {
        "screen_nodes": 765,
        "retained_nodes": 765,
        "effect_ranks": 765,
    }

    usable = np.ones(765, dtype=bool)
    usable[17] = False
    bad_cache = audit.make_reference_cache(screen, effect, effect_usable=usable)
    abstained = audit.audit_history_screen_decision(
        metadata,
        arrays,
        surface,
        _decision(effect_bad=True),
        main_audit,
        bad_cache,
        resources,
    )
    assert abstained["release_blocked"] is False
    assert abstained["numerical_status"] == "terminal_invalid"
    assert abstained["decision_status"] == "abstain_no_fit"

    substituted = audit.audit_history_screen_decision(
        metadata,
        arrays,
        surface,
        _decision(perturb_rank=True),
        main_audit,
        references,
        resources,
    )
    assert substituted["release_blocked"] is True
    assert "node p-values" in substituted["reason"]


def test_screen_audit_rejects_wrong_single_case_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = _resources()
    metadata = _metadata()
    arrays = _arrays(resources)
    surface = np.zeros(765, dtype=np.float64)
    monkeypatch.setattr(audit, "_observed_surface", lambda *_args: surface.copy())
    main_audit = {
        "release_blocked": False,
        "declaration_pair_valid": True,
        "adjusted_statistic": 2.0,
    }
    references = audit.make_reference_cache(
        np.zeros((765, 99), dtype=np.float64),
        np.zeros((765, 999), dtype=np.float64),
    )
    wrong = _decision()
    wrong["case_ids"][0] = "history-wrong"
    wrong["screens"][0]["case_id"] = "history-wrong"
    wrong["decisions"][0]["case_id"] = "history-wrong"

    receipt = audit.audit_history_screen_decision(
        metadata,
        arrays,
        surface,
        wrong,
        main_audit,
        references,
        resources,
    )

    assert receipt["release_blocked"] is True
    assert "cannot identify this history" in receipt["reason"]


def test_inclusive_rank_retains_ties_at_the_frozen_tolerance() -> None:
    observed = 2.0
    tolerance = 1e-10 + 1e-12 * max(1.0, abs(observed))
    references = [observed - 0.5 * tolerance, observed - 2.0 * tolerance]
    assert audit.inclusive_rank(observed, references) == pytest.approx(2.0 / 3.0)


def _profiles(fits: dict[str, Any]) -> dict[str, Any]:
    specs = {
        "constant_h": ("h", np.linspace(1.0, 10.0, 181), "constant_free_h"),
        "adjusted_h": ("h", np.linspace(1.0, 10.0, 181), "adjusted_free_h"),
        "adjusted_beta": ("beta", np.linspace(-2.0, 2.0, 81), "adjusted_free_h"),
    }
    output = {}
    for name, (coordinate, grid, model) in specs.items():
        parameters = []
        values = []
        for value in grid:
            point = {
                key: float(fits[model][key])
                for key in ("h", "beta", "mu", "detection_sd")
            }
            point[coordinate] = float(value)
            parameters.append(point)
            values.append(_score(point))
        output[name] = {
            "coordinate": coordinate,
            "grid": grid.tolist(),
            "values": values,
            "parameters": parameters,
            "statuses": ["converged"] * len(grid),
            "nfev": len(grid),
            "elapsed_seconds": 0.0,
            "better_than_main": False,
            "curvature": None,
            "warnings": [],
            "curvature_coordinate": None,
        }
    return output


def _lattice() -> dict[str, Any]:
    h_values = (1.0, 1.5, 3.0, 6.0, 10.0)
    beta_values = (-2.0, -1.0, 0.0, 0.6, 1.0, 2.0)
    mu_values = (0.0005, 0.001, 0.0016, 0.002, 0.0025, 0.0032, 0.004, 0.005, 0.006)
    sd_values = (0.0, 0.1, 0.2, 0.3, 0.4)
    maxima = dict.fromkeys(audit.MODEL_NAMES, -math.inf)
    rows = []
    for h, beta, mu, sd in product(h_values, beta_values, mu_values, sd_values):
        point = {"h": h, "beta": beta, "mu": mu, "detection_sd": sd}
        values = [_score({**point, "h": candidate}) for candidate in h_values]
        models = list(audit.MODEL_NAMES) if beta == 0.0 else ["adjusted_free_h", "adjusted_h1"]
        rows.append(
            {
                "point": point,
                "applicable_models": models,
                "training_logjoint_by_history_and_h": [values],
            }
        )
        selected = values[h_values.index(h)]
        for model in models:
            if model.endswith("h1") and h != 1.0:
                continue
            maxima[model] = max(maxima[model], selected)
    return {
        "points": 1350,
        "expected_points": 1350,
        "grid": {
            "h": list(h_values),
            "beta": list(beta_values),
            "mu": list(mu_values),
            "detection_sd": list(sd_values),
        },
        "raw_points": rows,
        "max_logjoint": {name: [value] for name, value in maxima.items()},
    }


def test_diagnostics_reconstruct_all_443_profile_and_1350_lattice_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = _resources()
    metadata = _metadata()
    arrays = _arrays(resources)
    main = _main(metadata)
    monkeypatch.setitem(
        audit._audit_profiles.__globals__,
        "direct_training_score",
        lambda _bank, _context, _prey, _predator, point: _score(point),
    )
    profiles = _profiles(main["fits"])
    profile_models = {
        "constant_h": "constant_free_h",
        "adjusted_h": "adjusted_free_h",
        "adjusted_beta": "adjusted_free_h",
    }
    profile_gaps = {
        name: max(row["values"]) - main["fits"][profile_models[name]]["raw_logjoint"]
        for name, row in profiles.items()
    }
    lattice = _lattice()
    lattice_gaps = {
        name: float(np.asarray(lattice["max_logjoint"][name]).max())
        - main["fits"][name]["raw_logjoint"]
        for name in audit.MODEL_NAMES
    }
    diagnostics = {
        "schema": audit.DIAGNOSTIC_SCHEMA,
        **{
            key: metadata[key]
            for key in ("history_index", "cell_index", "cell_label", "replicate")
        },
        "main_binding_sha256": audit.canonical_sha256(main),
        "profiles": profiles,
        "profile_main_gaps": profile_gaps,
        "profile_statuses_converged": dict.fromkeys(profiles, True),
        "lattice": lattice,
        "lattice_main_check": {
            "passed": all(value <= 1e-6 for value in lattice_gaps.values()),
            "tolerance": 1e-6,
            "gaps": lattice_gaps,
        },
        "main_fits_unchanged": main["fits"],
    }
    receipt = audit.audit_history_diagnostics(metadata, arrays, main, diagnostics, resources)
    assert receipt["release_blocked"] is False
    assert receipt["counts"] == {"profile_points": 443, "lattice_points": 1350}

    changed = copy.deepcopy(diagnostics)
    changed["profiles"]["adjusted_beta"]["values"][40] += 2e-8
    rejected = audit.audit_history_diagnostics(metadata, arrays, main, changed, resources)
    assert rejected["release_blocked"] is True
    assert "score mismatch" in rejected["reason"]


def test_holdout_audit_checks_every_site_cluster_and_pairwise_contrast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources = _resources()
    metadata = _metadata()
    arrays = _arrays(resources)
    main = _main(metadata)
    monkeypatch.setattr(audit, "direct_point_score", _fake_direct)
    models = {}
    totals = {}
    holdout_ids = list(np.asarray(resources.context.site_ids)[~resources.context.training])
    clusters = np.asarray(resources.context.cluster_ids)[~resources.context.training]
    for model, fit in main["fits"].items():
        direct = _fake_direct(None, resources.context, None, None, fit)
        site = direct["holdout_conditional_prey_site"]
        total = float(site.sum())
        totals[model] = total
        models[model] = {
            "status": "available",
            "fit_status": "converged",
            "total_nats": total,
            "mean_nats_per_site": float(site.mean()),
            "site_ids": holdout_ids,
            "site_nats": site.tolist(),
            "cluster_nats": {
                str(cluster): float(site[clusters == cluster].sum())
                for cluster in sorted(set(clusters))
            },
        }
    pairs = [
        {"left": left, "right": right, "left_minus_right_nats": totals[left] - totals[right]}
        for left, right in combinations(audit.MODEL_NAMES, 2)
    ]
    holdout = {
        "schema": audit.HOLDOUT_SCHEMA,
        **{
            key: metadata[key]
            for key in ("history_index", "cell_index", "cell_label", "replicate")
        },
        "main_binding_sha256": audit.canonical_sha256(main),
        "models": models,
        "pair_contrasts": pairs,
    }
    receipt = audit.audit_history_holdout(metadata, arrays, main, holdout, resources)
    assert receipt["release_blocked"] is False
    assert receipt["counts"]["available_models"] == 4
    assert receipt["counts"]["pairwise_contrasts"] == 6

    changed = copy.deepcopy(holdout)
    changed["models"]["adjusted_free_h"]["site_nats"][7] += 2e-8
    rejected = audit.audit_history_holdout(metadata, arrays, main, changed, resources)
    assert rejected["release_blocked"] is True
    assert "holdout score mismatch" in rejected["reason"]
