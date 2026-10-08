"""Blinded, training-only adapter for the public capstone analysis.

The adapter accepts the analyst-facing training package and delegates all
likelihood, fitting, profiling, and nuisance-grid calculations to the frozen
capstone modules.  It deliberately has no access path for holdout, truth, or
private evaluator fields.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import capstone_calibration as calibration
from latent_landscapes import capstone_public as public_api
from latent_landscapes import capstone_qualification as qualification
from latent_landscapes import preinvasion_fitting as fitting
from latent_landscapes import preinvasion_likelihood as likelihood
from latent_landscapes.preinvasion_effect_gate import EffectFitBatch

TRAINING_SCHEMA = "goal060-training-v1"
TRAINING_CASE_IDS = tuple(f"case-{index:02d}" for index in range(4))
TRAINING_COUNT = 120
SITE_COUNT = 160
ALLOWED_ARRAYS = frozenset({"case_ids", "site_ids", "prey_counts", "predator_counts"})
ALLOWED_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "case_count",
        "site_count",
        "prey_visits",
        "predator_visits",
        "arrays_sha256",
    }
)


@dataclass(frozen=True, slots=True)
class TrainingCases:
    """Neutral case identifiers and the 120-site public observations."""

    case_ids: tuple[str, ...]
    observations: likelihood.PreInvasionObservations


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _training_site_ids(public: public_api.PublicInputs) -> tuple[str, ...]:
    ids = tuple(str(value) for value in public.setup.site_ids)
    splits = tuple(str(value) for value in public.setup.site_splits)
    if len(ids) != SITE_COUNT or len(ids) != len(splits):
        raise ValueError("public inputs must contain the registered 160-site design")
    if ids != tuple(sorted(ids)) or len(set(ids)) != SITE_COUNT:
        raise ValueError("public site identifiers are not in canonical order")
    training = tuple(
        site_id for site_id, split in zip(ids, splits, strict=True) if split == "training"
    )
    if len(training) != TRAINING_COUNT:
        raise ValueError("public training split is not the registered 120 sites")
    return training


def _training_mask(public: public_api.PublicInputs) -> NDArray[np.bool_]:
    _training_site_ids(public)
    return cast(
        NDArray[np.bool_], np.asarray(public.setup.site_splits, dtype="U16") == "training"
    )


def _validate_cases(cases: TrainingCases, public: public_api.PublicInputs) -> None:
    if cases.case_ids != TRAINING_CASE_IDS:
        raise ValueError("training case identifiers must be the four neutral case IDs")
    observations = cases.observations
    expected_sites = _training_site_ids(public)
    if observations.site_ids != expected_sites:
        raise ValueError("training observation site order does not match public inputs")
    if observations.prey_counts.shape != (4, TRAINING_COUNT, 13):
        raise ValueError("training prey counts must have shape (4, 120, 13)")
    if observations.predator_counts.shape != (4, TRAINING_COUNT, 6):
        raise ValueError("training predator counts must have shape (4, 120, 6)")
    if not np.all(observations.training_mask):
        raise ValueError("training observations must contain only training sites")
    if not np.all(observations.initial_alive):
        raise ValueError("training initial cohort state must retain the default alive state")
    if observations.prey_times != likelihood.DEFAULT_PREY_TIMES:
        raise ValueError("training prey calendar differs from the frozen default")
    if observations.predator_times != likelihood.DEFAULT_PREDATOR_TIMES:
        raise ValueError("training predator calendar differs from the frozen default")
    if observations.cohort_start != -60.0:
        raise ValueError("training cohort start differs from the frozen default")
    if observations.predator_emissions is None:
        raise ValueError("training predator emissions were not prepared")


def load_training(
    public: public_api.PublicInputs,
    training_npz: Path,
    training_manifest: Path,
    expected_npz_sha256: str | None = None,
) -> TrainingCases:
    """Load and validate the sealed-v1 analyst training package."""
    if not training_npz.is_file() or not training_manifest.is_file():
        raise FileNotFoundError("training NPZ and manifest are required")
    npz_sha256 = _sha256(training_npz)
    if expected_npz_sha256 is not None and npz_sha256 != expected_npz_sha256:
        raise ValueError("training NPZ checksum does not match the expected digest")
    try:
        manifest = json.loads(training_manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("training manifest is not valid JSON") from error
    if not isinstance(manifest, dict) or set(manifest) != ALLOWED_MANIFEST_FIELDS:
        raise ValueError("training manifest contains undocumented or missing fields")
    expected_counts = {
        "schema_version": TRAINING_SCHEMA,
        "case_count": 4,
        "site_count": TRAINING_COUNT,
        "prey_visits": 13,
        "predator_visits": 6,
        "arrays_sha256": npz_sha256,
    }
    if manifest != expected_counts:
        raise ValueError("training manifest does not match the sealed-v1 schema or package")
    with np.load(training_npz, allow_pickle=False) as values:
        if set(values.files) != ALLOWED_ARRAYS:
            raise ValueError("training NPZ contains undocumented or missing arrays")
        case_ids = tuple(str(value) for value in np.asarray(values["case_ids"]).reshape(-1))
        site_ids = tuple(str(value) for value in np.asarray(values["site_ids"]).reshape(-1))
        prey = np.asarray(values["prey_counts"])
        predator = np.asarray(values["predator_counts"])
    if case_ids != TRAINING_CASE_IDS:
        raise ValueError("training case IDs are not the four neutral IDs")
    if site_ids != _training_site_ids(public):
        raise ValueError("training site IDs are not the canonical public training sites")
    if prey.shape != (4, TRAINING_COUNT, 13) or predator.shape != (4, TRAINING_COUNT, 6):
        raise ValueError("training arrays have the wrong dimensions")
    observations = likelihood.prepare_observations(
        prey,
        predator,
        site_ids,
        np.ones(TRAINING_COUNT, dtype=bool),
    )
    cases = TrainingCases(case_ids, observations)
    _validate_cases(cases, public)
    return cases


def _fit_data(
    public: public_api.PublicInputs,
    full_bank: likelihood.CompressedBank,
    cases: TrainingCases,
    *,
    history: int,
) -> qualification.FitData:
    _validate_cases(cases, public)
    if type(history) is not int or not 0 <= history < len(cases.case_ids):
        raise ValueError("history must be one of the four training cases")
    full_ids = tuple(str(value) for value in public.setup.site_ids)
    arrivals = np.asarray(full_bank.bank_arrivals)
    if (
        full_bank.site_ids != full_ids
        or len(full_bank.site_ids) != SITE_COUNT
        or arrivals.ndim != 2
        or arrivals.shape[1] != SITE_COUNT
    ):
        raise ValueError("fit bank must contain the full canonical 160-site bank")
    full_mask = _training_mask(public)
    selected_bank = qualification.subset_bank(full_bank, full_mask)
    selected_observations = qualification.subset_observations(
        cases.observations,
        np.ones(TRAINING_COUNT, dtype=bool),
        history=history,
    )
    site_values = np.asarray(
        public.setup.exposure_score[public.setup.site_rows, public.setup.site_cols]
    )
    site_a = site_values[full_mask]
    return qualification.FitData(
        selected_observations,
        selected_bank,
        np.asarray(public.setup.exposure_score),
        site_a,
    )


def make_training_data(
    public: public_api.PublicInputs,
    full_bank: likelihood.CompressedBank,
    cases: TrainingCases,
    history: int,
) -> qualification.FitData:
    """Build the unchanged fit data with the real 120-site training subset."""
    return _fit_data(public, full_bank, cases, history=history)


def observed_adjusted_validity(paired: fitting.PairedFitResult) -> dict[str, Any]:
    """Describe the adjusted null/free fit validity without changing its T."""
    null_fit = paired.fits["adjusted_h1"]
    free_fit = paired.fits["adjusted_free_h"]
    null_finite = math.isfinite(float(null_fit.raw_logjoint))
    free_finite = math.isfinite(float(free_fit.raw_logjoint))
    free_minus_null = (
        float(free_fit.raw_logjoint - null_fit.raw_logjoint)
        if null_finite and free_finite
        else math.nan
    )
    both_converged = null_fit.converged and free_fit.converged
    valid = bool(
        null_finite and free_finite and both_converged and free_minus_null >= -1e-6
    )
    return {
        "valid": valid,
        "null_finite": null_finite,
        "free_finite": free_finite,
        "null_converged": null_fit.converged,
        "free_converged": free_fit.converged,
        "both_converged": both_converged,
        "free_minus_null": free_minus_null,
        "minimum_free_minus_null": -1e-6,
    }


def observed_adjusted_effect_batch(paired: fitting.PairedFitResult) -> EffectFitBatch:
    """Return one observed adjusted pair, fail-closed for invalid fits.

    Invalid pairs retain their raw scores but receive ``"invalid"`` statuses,
    so :meth:`EffectFitBatch.statistics` yields NaN instead of clamping a
    negative or failed pair into a finite effect statistic.
    """
    validity = observed_adjusted_validity(paired)
    null_fit = paired.fits["adjusted_h1"]
    free_fit = paired.fits["adjusted_free_h"]
    status = "converged" if validity["valid"] else "invalid"
    return EffectFitBatch(
        [float(null_fit.raw_logjoint)],
        [float(free_fit.raw_logjoint)],
        [status],
        [status],
    )


def _unavailable_profile(coordinate: str, reason: str) -> dict[str, Any]:
    """Represent a diagnostic that cannot run after an invalid main fit."""
    return {
        "coordinate": coordinate,
        "grid": [],
        "values": [],
        "parameters": [],
        "statuses": [],
        "statuses_converged": False,
        "nfev": 0,
        "elapsed_seconds": 0.0,
        "better_than_main": False,
        "curvature": None,
        "warnings": [f"diagnostic unavailable: {reason}"],
        "curvature_coordinate": "log_h" if coordinate == "h" else "beta",
    }


def _run_profile(
    name: str, callback: Any, *args: Any
) -> dict[str, Any]:
    try:
        return asdict(callback(*args))
    except (FloatingPointError, OverflowError, ValueError, TypeError) as error:
        coordinate = "beta" if name == "adjusted_beta" else "h"
        return _unavailable_profile(
            coordinate, f"{type(error).__name__}: {error}"
        )


def _replay_difference(data: qualification.FitData, fit: fitting.FitResult) -> float:
    try:
        value = qualification.fit_loglikelihood(data, **fit.parameters)
    except (FloatingPointError, OverflowError, ValueError, TypeError):
        return math.nan
    return float(value - fit.raw_logjoint) if math.isfinite(value) else math.nan


def fit_training_case(
    public: public_api.PublicInputs,
    bank: likelihood.CompressedBank,
    cases: TrainingCases,
    *,
    history: int,
    representation: str = "full",
    output: Path | None = None,
) -> dict[str, Any]:
    """Fit one blinded training case and retain public-style diagnostics."""
    data = _fit_data(public, bank, cases, history=history)
    paired = fitting.paired_fit(data, qualification.fit_loglikelihood)
    main: dict[str, Any] = {
        "history": history,
        "representation": representation,
        "bank_size": bank.bank_size,
        "paired": asdict(paired),
        "adjusted_T": paired.adjusted_T,
        "constant_T": paired.constant_T,
        "fits": qualification.jsonable(paired.fits),
    }
    if output is not None:
        output.mkdir(parents=True, exist_ok=True)
        qualification._write_json(
            output / f"history-{history:02d}-{representation}-main.json", main
        )
    profiles = {
        "constant_h": _run_profile(
            "constant_h",
            fitting.profile_h,
            data,
            qualification.fit_loglikelihood,
            paired.fits["constant_free_h"],
        ),
        "adjusted_h": _run_profile(
            "adjusted_h",
            fitting.profile_h,
            data,
            qualification.fit_loglikelihood,
            paired.fits["adjusted_free_h"],
        ),
        "adjusted_beta": _run_profile(
            "adjusted_beta",
            fitting.profile_beta,
            data,
            qualification.fit_loglikelihood,
            paired.fits["adjusted_free_h"],
        ),
    }
    profile_models = {
        "constant_h": "constant_free_h",
        "adjusted_h": "adjusted_free_h",
        "adjusted_beta": "adjusted_free_h",
    }
    profile_main_gaps = {
        name: (
            float(np.nanmax(np.asarray(profile["values"], dtype=float)))
            - paired.fits[profile_models[name]].raw_logjoint
            if np.isfinite(np.asarray(profile["values"], dtype=float)).any()
            else math.nan
        )
        for name, profile in profiles.items()
    }
    nesting_gaps = {
        "constant": float(
            paired.fits["constant_h1"].raw_logjoint
            - paired.fits["constant_free_h"].raw_logjoint
        ),
        "adjusted": float(
            paired.fits["adjusted_h1"].raw_logjoint
            - paired.fits["adjusted_free_h"].raw_logjoint
        ),
    }
    result = {
        **main,
        "profiles": profiles,
        "profile_main_gaps": profile_main_gaps,
        "profile_statuses_converged": {
            name: bool(profile["statuses"]) and all(
                status == "converged" for status in profile["statuses"]
            )
            for name, profile in profiles.items()
        },
        "main_statuses_converged": {name: fit.converged for name, fit in paired.fits.items()},
        "nesting_gaps": nesting_gaps,
        "nesting_gap_diagnostic_passed": all(
            value <= qualification.GRID_TOLERANCE for value in nesting_gaps.values()
        ),
        "observed_adjusted_validity": observed_adjusted_validity(paired),
        "main_replay_logjoint_differences": {
            name: _replay_difference(data, fit)
            for name, fit in paired.fits.items()
        },
    }
    if output is not None:
        qualification._write_json(output / f"history-{history:02d}-{representation}.json", result)
    return result


def observed_pre_scores(
    public: public_api.PublicInputs, cases: TrainingCases
) -> NDArray[np.float64]:
    """Return the four case by 765-node pre-invasion likelihood surface."""
    _validate_cases(cases, public)
    map_a = np.asarray(public.setup.exposure_score)
    site_values = np.asarray(
        public.setup.exposure_score[public.setup.site_rows, public.setup.site_cols]
    )
    site_a = site_values[_training_mask(public)]
    rows = []
    for history in range(4):
        observations = qualification.subset_observations(
            cases.observations,
            np.ones(TRAINING_COUNT, dtype=bool),
            history=history,
        )
        rows.append(
            np.asarray(
                [
                    calibration.pre_score(observations, map_a, site_a, index)[0]
                    for index in range(765)
                ],
                dtype=np.float64,
            )
        )
    result = np.stack(rows)
    result.setflags(write=False)
    return result


def qualified1350coarse_grid(
    public: public_api.PublicInputs,
    bank: likelihood.CompressedBank,
    cases: TrainingCases,
    *,
    history: int,
) -> dict[str, Any]:
    """Compute the frozen 1,350-point diagnostic lattice for one case."""
    return qualification.coarse_grid_audit(make_training_data(public, bank, cases, history))
