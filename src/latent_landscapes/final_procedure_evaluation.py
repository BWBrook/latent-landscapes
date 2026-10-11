"""Goal 062 ten-cell evaluation adapter.

This module binds the approved evaluation cells and random addresses to the
frozen capstone generators, likelihood, fitter, profiles, and calibration
arithmetic.  It does not orchestrate a campaign or load reference databases.
In particular, the object passed to the fitter contains observations, the
fixed public exposure, and the fixed arrival bank only; evaluator truth and
random seeds remain in the separate generator return value.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import adjusted_background_likelihood as adjusted
from latent_landscapes import capstone_calibration as calibration
from latent_landscapes import capstone_public as public_api
from latent_landscapes import capstone_qualification as qualification
from latent_landscapes import preinvasion_calibration as ranks
from latent_landscapes import preinvasion_fitting as fitting
from latent_landscapes import preinvasion_likelihood as likelihood

FloatArray = NDArray[np.float64]

EVALUATION_ROOT = 2026101101
MECHANICAL_ROOT = 987654321
NAMESPACE = 62
DOMAIN = 1
REPLICATES = 500
TRAINING_SITES = 120
HOLDOUT_SITES = 40
SITE_COUNT = TRAINING_SITES + HOLDOUT_SITES
MAIN_REPLAY_TOLERANCE = 1e-8
NESTING_TOLERANCE = 1e-6
MODEL_NAMES = qualification.MODEL_NAMES
STAGES = {
    "spread": 1,
    "prey_loss": 2,
    "predator_visits": 3,
    "site_detection": 4,
    "prey_visits": 5,
    "background_field": 6,
}
BASE_STAGES = tuple(name for name in STAGES if name != "background_field")


@dataclass(frozen=True, slots=True)
class EvaluationCell:
    """One registered generating cell.

    ``beta`` is ``None`` for B100-A because that generating law has no
    adjusted-model beta parameter.
    """

    index: int
    label: str
    background: Literal["exact", "B100-A"]
    h: float
    mu: float
    beta: float | None
    detection_sd: float


CELLS = (
    EvaluationCell(0, "L1", "exact", 1.0, 0.001, 0.5, 0.2),
    EvaluationCell(1, "L3", "exact", 3.0, 0.001, 0.5, 0.2),
    EvaluationCell(2, "L5", "exact", 5.0, 0.001, 0.5, 0.2),
    EvaluationCell(3, "H1", "exact", 1.0, 0.004, 0.5, 0.2),
    EvaluationCell(4, "H3", "exact", 3.0, 0.004, 0.5, 0.2),
    EvaluationCell(5, "H5", "exact", 5.0, 0.004, 0.5, 0.2),
    EvaluationCell(6, "B_L1", "B100-A", 1.0, 0.001, None, 0.2),
    EvaluationCell(7, "B_L3", "B100-A", 3.0, 0.001, None, 0.2),
    EvaluationCell(8, "B_H1", "B100-A", 1.0, 0.004, None, 0.2),
    EvaluationCell(9, "B_H3", "B100-A", 3.0, 0.004, None, 0.2),
)


@dataclass(frozen=True, slots=True)
class ObservationData:
    """Full observations and disjoint analyst training/holdout fit data."""

    full: likelihood.PreInvasionObservations
    training: qualification.FitData
    holdout: qualification.FitData


def _cell(value: int | EvaluationCell) -> EvaluationCell:
    if isinstance(value, EvaluationCell):
        if value not in CELLS or CELLS[value.index] != value:
            raise ValueError("cell is not one of the ten registered cells")
        return value
    if type(value) is not int or not 0 <= value < len(CELLS):
        raise ValueError("cell index must be in 0..9")
    return CELLS[value]


def _replicate(value: int) -> int:
    if type(value) is not int or not 0 <= value < REPLICATES:
        raise ValueError("replicate must be in 0..499")
    return value


def _root(value: int) -> int:
    if type(value) is not int or value not in {EVALUATION_ROOT, MECHANICAL_ROOT}:
        raise ValueError("root must be the registered evaluation or mechanical root")
    return value


def _stage(cell: EvaluationCell, value: str | int) -> tuple[str, int]:
    if isinstance(value, str):
        if value not in STAGES:
            raise ValueError("unknown evaluation stage")
        name, number = value, STAGES[value]
    elif type(value) is int and value in STAGES.values():
        number = value
        name = next(name for name, stage in STAGES.items() if stage == value)
    else:
        raise ValueError("stage must be a registered name or integer")
    if name == "background_field" and cell.background != "B100-A":
        raise ValueError("background_field exists only for B100-A cells")
    return name, number


def stage_seed(
    cell: int | EvaluationCell,
    replicate: int,
    stage: str | int,
    *,
    root: int = EVALUATION_ROOT,
) -> int:
    """Return the first uint64 at the registered six-component address."""

    registered = _cell(cell)
    replicate = _replicate(replicate)
    root = _root(root)
    _name, number = _stage(registered, stage)
    address = [root, NAMESPACE, DOMAIN, registered.index, replicate, number]
    return int(np.random.SeedSequence(address).generate_state(1, dtype=np.uint64)[0])


def history_seeds(
    cell: int | EvaluationCell,
    replicate: int,
    *,
    root: int = EVALUATION_ROOT,
) -> dict[str, Any]:
    """Return all generator streams plus their explicit registered addresses."""

    registered = _cell(cell)
    replicate = _replicate(replicate)
    root = _root(root)
    names = BASE_STAGES + (("background_field",) if registered.background == "B100-A" else ())
    streams = {name: stage_seed(registered, replicate, name, root=root) for name in names}
    addresses = {
        name: [root, NAMESPACE, DOMAIN, registered.index, replicate, STAGES[name]] for name in names
    }
    return {
        "root": root,
        "namespace": NAMESPACE,
        "domain": DOMAIN,
        "cell": registered.index,
        "replicate": replicate,
        "address_order": ["root", "namespace", "domain", "cell", "replicate", "stage"],
        "streams": streams,
        "addresses": addresses,
        "stage_records": {
            name: {"stage": STAGES[name], "address": addresses[name], "seed": streams[name]}
            for name in names
        },
    }


def seed_ledger(
    *, root: int = EVALUATION_ROOT, replicates: int = REPLICATES
) -> list[dict[str, Any]]:
    """Materialize the registered stage ledger without drawing histories."""

    root = _root(root)
    if type(replicates) is not int or not 1 <= replicates <= REPLICATES:
        raise ValueError("replicates must be in 1..500")
    rows: list[dict[str, Any]] = []
    for cell in CELLS:
        names = BASE_STAGES + (("background_field",) if cell.background == "B100-A" else ())
        for replicate in range(replicates):
            for name in names:
                address = [root, NAMESPACE, DOMAIN, cell.index, replicate, STAGES[name]]
                rows.append(
                    {
                        "cell": cell.index,
                        "replicate": replicate,
                        "stage": name,
                        "stage_id": STAGES[name],
                        "address": address,
                        "seed": stage_seed(cell, replicate, name, root=root),
                    }
                )
    return rows


def validate_seed_ledger(
    ledger: Sequence[Mapping[str, Any]],
    *,
    root: int = EVALUATION_ROOT,
    replicates: int = REPLICATES,
) -> dict[str, Any]:
    """Verify exact membership, addresses, derived seeds, and uniqueness."""

    expected = seed_ledger(root=root, replicates=replicates)
    observed = [dict(row) for row in ledger]
    exact = observed == expected
    addresses = [tuple(int(value) for value in row.get("address", ())) for row in observed]
    seeds = [int(row.get("seed", -1)) for row in observed]
    expected_count = replicates * (6 * 5 + 4 * 6)
    address_unique = len(addresses) == len(set(addresses)) == expected_count
    seed_unique = len(seeds) == len(set(seeds)) == expected_count
    domain_separated = all(
        len(address) == 6
        and address[:3] == (root, NAMESPACE, DOMAIN)
        and address[2] not in calibration.DOMAINS.values()
        for address in addresses
    )
    passed = exact and address_unique and seed_unique and domain_separated
    return {
        "passed": passed,
        "root": root,
        "namespace": NAMESPACE,
        "domain": DOMAIN,
        "replicates": replicates,
        "expected_rows": expected_count,
        "observed_rows": len(observed),
        "address_unique": address_unique,
        "derived_seed_unique": seed_unique,
        "reference_domain_separated": domain_separated,
        "production_row_count": 27_000 if replicates == REPLICATES else None,
    }


def generate_history(
    public: public_api.PublicInputs,
    *,
    cell: int | EvaluationCell,
    replicate: int,
    root: int = EVALUATION_ROOT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Generate one exact-family or B100-A history through the frozen kernel."""

    registered = _cell(cell)
    replicate = _replicate(replicate)
    seeds = history_seeds(registered, replicate, root=root)
    history_index = registered.index * REPLICATES + replicate
    # GeneralTruth predates the B100-A amendment and requires a beta value.
    # The frozen B100-A generator never reads it; remove that placeholder from
    # the returned evaluator truth immediately.
    truth = public_api.GeneralTruth(
        history_index,
        registered.h,
        registered.mu,
        registered.beta if registered.beta is not None else 0.0,
        registered.detection_sd,
        registered.background,
    )
    if registered.background == "exact":
        observations, evaluator = public_api.generate_exact_history(
            public.fixed, public.setup, truth, seeds
        )
    else:
        observations, evaluator = public_api.generate_b100_history(
            public.fixed, public.setup, truth, seeds
        )
    evaluator = dict(evaluator)
    if registered.background == "exact":
        map_a = np.asarray(public.setup.exposure_score, dtype=np.float64)
        evaluator["map_hazard"] = adjusted.normalized_hazards(
            cast(float, registered.beta), map_a, map_a.reshape(-1), registered.mu
        ).reshape(map_a.shape)
    evaluator["truth"] = {
        "cell_index": registered.index,
        "label": registered.label,
        "background": registered.background,
        "effect": registered.h,
        "mean_hazard": registered.mu,
        "generating_beta": registered.beta,
        "detection_sd": registered.detection_sd,
    }
    evaluator["seeds"] = seeds
    observations = dict(observations)
    observations["index"] = history_index
    observations["site_ids"] = np.asarray(public.setup.site_ids)
    observations["training_mask"] = np.asarray(public.setup.site_splits, dtype="U16") == "training"
    return observations, evaluator


def _canonical_design(
    public: public_api.PublicInputs,
) -> tuple[tuple[str, ...], NDArray[np.bool_]]:
    ids = tuple(str(value) for value in public.setup.site_ids)
    splits = np.asarray(public.setup.site_splits, dtype="U16")
    if len(ids) != SITE_COUNT or ids != tuple(sorted(ids)) or len(set(ids)) != SITE_COUNT:
        raise ValueError("public inputs do not contain the canonical 160-site ordering")
    if splits.shape != (SITE_COUNT,) or int(np.sum(splits == "training")) != TRAINING_SITES:
        raise ValueError("public inputs do not contain the registered 120/40 split")
    if int(np.sum(splits == "holdout")) != HOLDOUT_SITES:
        raise ValueError("public inputs do not contain the registered 120/40 split")
    return ids, cast(NDArray[np.bool_], splits == "training")


def make_observation_data(
    public: public_api.PublicInputs,
    full_bank: likelihood.CompressedBank,
    observations: Mapping[str, Any] | likelihood.PreInvasionObservations,
) -> ObservationData:
    """Build disjoint FitData objects from observation arrays only."""

    site_ids, training_mask = _canonical_design(public)
    if full_bank.site_ids != site_ids or np.asarray(full_bank.bank_arrivals).shape[1:] != (
        SITE_COUNT,
    ):
        raise ValueError("arrival bank does not use the full canonical site ordering")
    if isinstance(observations, likelihood.PreInvasionObservations):
        full = observations
        if full.prey_counts.shape[0] != 1:
            raise ValueError("one history is required")
        if full.site_ids != site_ids or not np.array_equal(full.training_mask, training_mask):
            raise ValueError("observation object does not use the canonical public split")
    else:
        if "prey_counts" not in observations or "predator_counts" not in observations:
            raise ValueError("prey_counts and predator_counts are required")
        prey = np.asarray(observations["prey_counts"])
        predator = np.asarray(observations["predator_counts"])
        if prey.ndim == 2:
            prey = prey[None, ...]
        if predator.ndim == 2:
            predator = predator[None, ...]
        full = likelihood.prepare_observations(prey, predator, site_ids, training_mask)
    return ObservationData(
        full,
        qualification.make_fit_data(public, full_bank, full, history=0, training=True),
        qualification.make_fit_data(public, full_bank, full, history=0, training=False),
    )


def _case_identity(cell: EvaluationCell, replicate: int) -> dict[str, Any]:
    return {
        "history_index": cell.index * REPLICATES + replicate,
        "cell_index": cell.index,
        "cell_label": cell.label,
        "replicate": replicate,
    }


def _jsonable(value: Any) -> Any:
    return qualification.jsonable(value)


def _canonical_hash(value: Mapping[str, Any]) -> str:
    payload = json.dumps(_jsonable(dict(value)), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    if path.suffix != ".json":
        raise ValueError("main-fit output must be a JSON file path")
    if path.exists():
        raise FileExistsError("refusing to replace an existing main-fit result")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(_jsonable(dict(value)), sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _replay(data: qualification.FitData, fit: fitting.FitResult) -> dict[str, Any]:
    try:
        replayed = qualification.fit_loglikelihood(data, **fit.parameters)
        difference = float(replayed - fit.raw_logjoint)
    except (FloatingPointError, OverflowError, TypeError, ValueError):
        replayed = math.nan
        difference = math.nan
    passed = math.isfinite(difference) and abs(difference) <= MAIN_REPLAY_TOLERANCE
    return {
        "replayed_logjoint": replayed,
        "stored_logjoint": fit.raw_logjoint,
        "difference": difference,
        "tolerance": MAIN_REPLAY_TOLERANCE,
        "status": "passed" if passed else "failed",
    }


def _adjusted_validity(fits: Mapping[str, fitting.FitResult]) -> dict[str, Any]:
    null = fits["adjusted_h1"]
    free = fits["adjusted_free_h"]
    finite = math.isfinite(null.raw_logjoint) and math.isfinite(free.raw_logjoint)
    difference = float(free.raw_logjoint - null.raw_logjoint) if finite else math.nan
    valid = finite and null.converged and free.converged and difference >= -NESTING_TOLERANCE
    return {
        "valid": bool(valid),
        "null_finite": math.isfinite(null.raw_logjoint),
        "free_finite": math.isfinite(free.raw_logjoint),
        "null_converged": null.converged,
        "free_converged": free.converged,
        "free_minus_null": difference,
        "minimum_free_minus_null": -NESTING_TOLERANCE,
    }


def fit_main(
    public: public_api.PublicInputs,
    full_bank: likelihood.CompressedBank,
    observations: Mapping[str, Any] | likelihood.PreInvasionObservations,
    *,
    cell: int | EvaluationCell,
    replicate: int,
    output: Path | None = None,
) -> dict[str, Any]:
    """Fit and optionally create a main JSON before later phases.

    Existing output is never replaced; resume/orchestration code must verify
    its receipt and skip the already completed fit.
    """

    registered = _cell(cell)
    replicate = _replicate(replicate)
    if output is not None and output.exists():
        raise FileExistsError("refusing to replace an existing main-fit result")
    train = make_observation_data(public, full_bank, observations).training
    # No cell truth, evaluator field, seed, diagnostic, screen, or holdout is
    # passed through this boundary.
    paired = fitting.paired_fit(train, qualification.fit_loglikelihood)
    nesting_gaps = {
        "constant": float(
            paired.fits["constant_h1"].raw_logjoint - paired.fits["constant_free_h"].raw_logjoint
        ),
        "adjusted": float(
            paired.fits["adjusted_h1"].raw_logjoint - paired.fits["adjusted_free_h"].raw_logjoint
        ),
    }
    nesting_status = {
        name: ("passed" if math.isfinite(value) and value <= NESTING_TOLERANCE else "failed")
        for name, value in nesting_gaps.items()
    }
    replay = {name: _replay(train, fit) for name, fit in paired.fits.items()}
    adjusted_validity = _adjusted_validity(paired.fits)
    row = {
        "schema": "goal062-main-fit-v1",
        **_case_identity(registered, replicate),
        "representation": "full",
        "bank_size": int(full_bank.bank_size),
        "statistics": dict(paired.statistics),
        "fits": {name: asdict(fit) for name, fit in paired.fits.items()},
        "main_statuses_converged": {name: fit.converged for name, fit in paired.fits.items()},
        "nesting_gaps": nesting_gaps,
        "nesting_status": nesting_status,
        "observed_adjusted_validity": adjusted_validity,
        "observed_effect_statistic": (paired.adjusted_T if adjusted_validity["valid"] else None),
        "compressed_score_replay": replay,
        "all_main_replays_passed": all(record["status"] == "passed" for record in replay.values()),
    }
    encoded = cast(dict[str, Any], _jsonable(row))
    if output is not None:
        _write_json_atomic(output, encoded)
    return encoded


def pre_surface(training: qualification.FitData) -> FloatArray:
    """Return the frozen 765-node pre-only surface for one training history."""

    observations = training.observations
    if observations.prey_counts.shape[0] != 1 or len(observations.site_ids) != TRAINING_SITES:
        raise ValueError("pre-only scoring requires one 120-site training history")
    values = np.asarray(
        [
            calibration.pre_score(observations, training.map_a, training.site_a, index)[0]
            for index in range(calibration.GRID_SIZE)
        ],
        dtype=np.float64,
    )
    values.setflags(write=False)
    return values


def _float(value: Any) -> float:
    return math.nan if value is None else float(value)


def _fit_from_json(value: Mapping[str, Any]) -> fitting.FitResult:
    starts = tuple(
        fitting.StartRecord(
            initial_parameters={str(k): _float(v) for k, v in row["initial_parameters"].items()},
            final_parameters={str(k): _float(v) for k, v in row["final_parameters"].items()},
            raw_logjoint=_float(row.get("raw_logjoint")),
            objective=_float(row.get("objective")),
            success=bool(row.get("success")),
            status=cast(int | str, row.get("status", -1)),
            message=str(row.get("message", "")),
            nfev=int(row.get("nfev", 0)),
            method=str(row.get("method", "")),
        )
        for row in value.get("starts", ())
    )
    return fitting.FitResult(
        model=str(value["model"]),
        h=_float(value.get("h")),
        beta=_float(value.get("beta")),
        mu=_float(value.get("mu")),
        detection_sd=_float(value.get("detection_sd")),
        raw_logjoint=_float(value.get("raw_logjoint")),
        numerical_status=str(value.get("numerical_status", "invalid")),
        nfev=int(value.get("nfev", 0)),
        elapsed_seconds=float(value.get("elapsed_seconds", 0.0) or 0.0),
        starts=starts,
        objective_gap=_float(value.get("objective_gap")),
        boundary_flags=tuple(str(item) for item in value.get("boundary_flags", ())),
        warnings=tuple(str(item) for item in value.get("warnings", ())),
    )


def _stored_fits(main_row: Mapping[str, Any]) -> dict[str, fitting.FitResult]:
    if main_row.get("schema") != "goal062-main-fit-v1":
        raise ValueError("stored main row has the wrong schema")
    records = main_row.get("fits")
    if not isinstance(records, Mapping) or set(records) != set(MODEL_NAMES):
        raise ValueError("stored main row must contain exactly four model fits")
    fits = {name: _fit_from_json(cast(Mapping[str, Any], records[name])) for name in MODEL_NAMES}
    for name, fit in fits.items():
        if fit.model != name:
            raise ValueError("stored fit model does not match its model key")
        if name.endswith("h1") and math.isfinite(fit.h) and fit.h != 1.0:
            raise ValueError("stored null fit does not have fixed h=1")
        if name.startswith("constant") and math.isfinite(fit.beta) and fit.beta != 0.0:
            raise ValueError("stored constant-background fit does not have fixed beta=0")
    return fits


def _unavailable_profile(coordinate: str, reason: str) -> dict[str, Any]:
    return {
        "coordinate": coordinate,
        "grid": [],
        "values": [],
        "parameters": [],
        "statuses": [],
        "nfev": 0,
        "elapsed_seconds": 0.0,
        "better_than_main": False,
        "curvature": None,
        "warnings": [reason],
        "curvature_coordinate": "log_h" if coordinate == "h" else "beta",
    }


def _profile(
    name: str,
    training: qualification.FitData,
    fit: fitting.FitResult,
) -> dict[str, Any]:
    coordinate = "beta" if name == "adjusted_beta" else "h"
    point = (*fit.parameters.values(), fit.raw_logjoint)
    if not fit.converged or not np.isfinite(point).all():
        return _unavailable_profile(coordinate, "main fit is not finite and converged")
    callback = fitting.profile_beta if name == "adjusted_beta" else fitting.profile_h
    try:
        return cast(
            dict[str, Any],
            _jsonable(asdict(callback(training, qualification.fit_loglikelihood, fit))),
        )
    except (FloatingPointError, OverflowError, TypeError, ValueError) as error:
        return _unavailable_profile(coordinate, f"{type(error).__name__}: {error}")


def diagnose_main(training: qualification.FitData, main_row: Mapping[str, Any]) -> dict[str, Any]:
    """Run profiles and the fixed lattice from persisted main fits, without refitting."""

    fits = _stored_fits(main_row)
    profiles = {
        "constant_h": _profile("constant_h", training, fits["constant_free_h"]),
        "adjusted_h": _profile("adjusted_h", training, fits["adjusted_free_h"]),
        "adjusted_beta": _profile("adjusted_beta", training, fits["adjusted_free_h"]),
    }
    profile_models = {
        "constant_h": "constant_free_h",
        "adjusted_h": "adjusted_free_h",
        "adjusted_beta": "adjusted_free_h",
    }
    profile_gaps: dict[str, float | None] = {}
    for name, profile in profiles.items():
        values = np.asarray(profile["values"], dtype=np.float64)
        profile_gaps[name] = (
            float(np.nanmax(values) - fits[profile_models[name]].raw_logjoint)
            if values.size and np.isfinite(values).any()
            else None
        )
    lattice = qualification.coarse_grid_audit(training)
    lattice_check = qualification.check_grid_against_fits(lattice, fits)
    result = {
        "schema": "goal062-main-diagnostics-v1",
        **{
            key: main_row[key] for key in ("history_index", "cell_index", "cell_label", "replicate")
        },
        "main_binding_sha256": _canonical_hash(main_row),
        "diagnostic_only": True,
        "profiles": profiles,
        "profile_main_gaps": profile_gaps,
        "profile_statuses_converged": {
            name: bool(profile["statuses"])
            and all(status == "converged" for status in profile["statuses"])
            for name, profile in profiles.items()
        },
        "lattice": lattice,
        "lattice_main_check": lattice_check,
        "main_fits_unchanged": {
            name: cast(Mapping[str, Any], main_row["fits"])[name] for name in MODEL_NAMES
        },
    }
    return cast(dict[str, Any], _jsonable(result))


def _bound_ok(value: float, lower: float, upper: float) -> bool:
    return (
        math.isfinite(value)
        and lower - value <= 8.0 * math.ulp(lower)
        and value - upper <= 8.0 * math.ulp(upper)
    )


def _fit_available(fit: fitting.FitResult) -> bool:
    return bool(
        fit.converged
        and math.isfinite(fit.raw_logjoint)
        and _bound_ok(fit.h, *fitting.H_BOUNDS)
        and _bound_ok(fit.beta, *fitting.BETA_BOUNDS)
        and _bound_ok(fit.mu, *fitting.MU_BOUNDS)
        and _bound_ok(fit.detection_sd, *fitting.DETECTION_SD_BOUNDS)
    )


def score_holdout(
    public: public_api.PublicInputs,
    holdout: qualification.FitData,
    main_row: Mapping[str, Any],
) -> dict[str, Any]:
    """Score stored main fits on held-out prey counts, with no fitting or selection."""

    fits = _stored_fits(main_row)
    ids = tuple(str(value) for value in holdout.observations.site_ids)
    if len(ids) != HOLDOUT_SITES or holdout.observations.prey_counts.shape[0] != 1:
        raise ValueError("held-out scoring requires one canonical 40-site history")
    public_ids, training_mask = _canonical_design(public)
    expected_ids = tuple(np.asarray(public_ids)[~training_mask])
    if ids != expected_ids:
        raise ValueError("held-out sites do not match the canonical public split")
    public_clusters = np.asarray(public.setup.site_cluster_ids, dtype=str)
    clusters = public_clusters[~training_mask]
    models: dict[str, Any] = {}
    for name, fit in fits.items():
        row: dict[str, Any] = {
            "status": "unavailable",
            "fit_status": fit.numerical_status,
        }
        if _fit_available(fit):
            try:
                scored = likelihood.point_score(
                    holdout.observations,
                    holdout.bank,
                    fit.h,
                    fit.beta,
                    fit.mu,
                    holdout.map_a,
                    holdout.site_a,
                    detection_sd=fit.detection_sd,
                )
                values = np.asarray(scored.conditional_prey_site_loglikelihood[0], dtype=np.float64)
                if values.shape != (HOLDOUT_SITES,) or not np.isfinite(values).all():
                    raise ValueError("held-out score is nonfinite or has the wrong shape")
                row.update(
                    status="available",
                    total_nats=float(values.sum()),
                    mean_nats_per_site=float(values.mean()),
                    site_ids=list(ids),
                    site_nats=values.tolist(),
                    cluster_nats={
                        str(cluster): float(values[clusters == cluster].sum())
                        for cluster in sorted(set(str(value) for value in clusters))
                    },
                )
            except (FloatingPointError, OverflowError, TypeError, ValueError) as error:
                row["reason"] = f"{type(error).__name__}: {error}"
        else:
            row["reason"] = "stored main fit is not finite, converged, and in bounds"
        models[name] = row
    pair_contrasts = []
    for left, right in itertools.combinations(MODEL_NAMES, 2):
        left_value = models[left].get("total_nats")
        right_value = models[right].get("total_nats")
        pair_contrasts.append(
            {
                "left": left,
                "right": right,
                "left_minus_right_nats": (
                    float(left_value - right_value)
                    if left_value is not None and right_value is not None
                    else None
                ),
            }
        )
    return {
        "schema": "goal062-heldout-score-v1",
        **{
            key: main_row[key] for key in ("history_index", "cell_index", "cell_label", "replicate")
        },
        "main_binding_sha256": _canonical_hash(main_row),
        "conditioning": "heldout predator observations; prey observations scored",
        "models": models,
        "pair_contrasts": pair_contrasts,
    }


def decide_cached(
    case_ids: Sequence[str],
    observed_surfaces: Any,
    observed_effect_statistics: Sequence[float],
    screen_reference_contrasts: Any | None,
    effect_reference_statistics: Any,
    effect_table_valid: Any,
    *,
    computation_complete: bool,
) -> dict[str, Any]:
    """Apply unchanged scalar rank semantics to an in-memory full reference panel."""

    identifiers = tuple(str(value) for value in case_ids)
    if (
        not identifiers
        or any(not value for value in identifiers)
        or len(set(identifiers)) != len(identifiers)
    ):
        raise ValueError("case_ids must be unique and nonempty")
    if not computation_complete:
        raise calibration.CalibrationPendingError("reference computation remains pending")
    surfaces = np.asarray(observed_surfaces, dtype=np.float64)
    if surfaces.shape != (len(identifiers), calibration.GRID_SIZE):
        raise ValueError("observed surfaces must have one 765-node row per case")
    contrasts = np.full_like(surfaces, np.nan)
    for index, surface in enumerate(surfaces):
        if np.isfinite(surface).all():
            contrasts[index] = calibration.local_contrasts(surface)
    screens = calibration.screen_cases(identifiers, contrasts, screen_reference_contrasts)
    statistics = np.asarray(observed_effect_statistics, dtype=np.float64)
    if statistics.shape != (len(identifiers),):
        raise ValueError("one observed effect statistic is required per case")
    effect = np.asarray(effect_reference_statistics, dtype=np.float64)
    valid = np.asarray(effect_table_valid, dtype=bool)
    if effect.shape != (calibration.GRID_SIZE, calibration.EFFECT_REFERENCE_COUNT):
        raise ValueError("effect cache must have shape (765, 999)")
    if valid.shape != (calibration.GRID_SIZE,):
        raise ValueError("effect-table validity must have shape (765,)")
    tables = {
        index: effect[index] if valid[index] else np.full(999, np.nan)
        for index in range(calibration.GRID_SIZE)
    }
    combined = ranks.combine_casewise_effect_tests(
        screens,
        statistics.tolist(),
        tables,
        max_candidates=calibration.GRID_SIZE,
    )
    screen_rows = {
        screen.case_id: cast(dict[str, Any], _jsonable(asdict(screen))) for screen in screens
    }
    decision_rows = {
        decision.case_id: cast(dict[str, Any], _jsonable(asdict(decision)))
        for decision in combined.decisions
    }
    return {
        "schema": "goal062-cached-decisions-v1",
        "case_ids": list(identifiers),
        "screen_reference_shape": (
            None
            if screen_reference_contrasts is None
            else list(np.asarray(screen_reference_contrasts).shape)
        ),
        "effect_reference_shape": list(effect.shape),
        "valid_effect_tables": int(valid.sum()),
        "computation_complete": True,
        "screens": [screen_rows[identifier] for identifier in identifiers],
        "decisions": [decision_rows[identifier] for identifier in identifiers],
        "required_effect_nodes": list(combined.required_effect_nodes),
        "available_effect_nodes": list(combined.available_effect_nodes),
    }


__all__ = [
    "BASE_STAGES",
    "CELLS",
    "DOMAIN",
    "EVALUATION_ROOT",
    "HOLDOUT_SITES",
    "MAIN_REPLAY_TOLERANCE",
    "MECHANICAL_ROOT",
    "MODEL_NAMES",
    "NAMESPACE",
    "NESTING_TOLERANCE",
    "REPLICATES",
    "SITE_COUNT",
    "STAGES",
    "TRAINING_SITES",
    "EvaluationCell",
    "ObservationData",
    "decide_cached",
    "diagnose_main",
    "fit_main",
    "generate_history",
    "history_seeds",
    "make_observation_data",
    "pre_surface",
    "score_holdout",
    "seed_ledger",
    "stage_seed",
    "validate_seed_ledger",
]
