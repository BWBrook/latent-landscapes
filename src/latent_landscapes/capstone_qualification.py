"""Bounded numerical qualification for the Goal 059 public capstone.

This module owns numerical checks only.  It does not choose a map, create an
arrival bank, draw a registered history, or reveal a private seed.  Public
inputs and banks are supplied by :mod:`latent_landscapes.capstone_public` and
the caller may use the small helpers below with sacrificial (tiny) banks in
tests before running the production qualification.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import adjusted_background_likelihood as adjusted
from latent_landscapes import capstone_public as public_api
from latent_landscapes import preinvasion_campaign as pre_campaign
from latent_landscapes import preinvasion_effect_reference as effect_reference
from latent_landscapes import preinvasion_fitting as fitting
from latent_landscapes import preinvasion_likelihood as likelihood

FloatArray = NDArray[np.float64]

MECHANICAL_ROOT = 987654321
PUBLIC_ROOT = 2026100403
PUBLIC_STAGE = 4
PUBLIC_STREAM_STAGES = {
    "spread": 1,
    "prey_loss": 2,
    "predator_visits": 3,
    "site_detection": 4,
    "prey_visits": 5,
    "background_field": 6,
}
MAX_WORKERS = 16
BANK_SIZE = 131072
SITE_COUNT = 160
HALF_BANK_SIZE = BANK_SIZE // 2
MECHANICAL_TOLERANCE = 1e-8
GRID_TOLERANCE = 1e-6
COARSE_H = (1.0, 1.5, 3.0, 6.0, 10.0)
COARSE_BETA = (-2.0, -1.0, 0.0, 0.6, 1.0, 2.0)
COARSE_MU = (0.0005, 0.001, 0.0016, 0.002, 0.0025, 0.0032, 0.004, 0.005, 0.006)
COARSE_SD = (0.0, 0.1, 0.2, 0.3, 0.4)
MODEL_NAMES = ("constant_free_h", "adjusted_free_h", "constant_h1", "adjusted_h1")


class QualificationFailure(RuntimeError):
    """Raised after an incomplete or negative qualification is recorded."""


@dataclass(frozen=True, slots=True)
class FitData:
    observations: likelihood.PreInvasionObservations
    bank: likelihood.CompressedBank
    map_a: FloatArray
    site_a: FloatArray


@dataclass(frozen=True, slots=True)
class DomainPoint:
    h: float
    beta: float
    mu: float
    detection_sd: float


def jsonable(value: Any) -> Any:
    """Convert numpy/dataclass values to strict-JSON-compatible objects."""
    if hasattr(value, "__dataclass_fields__"):
        return jsonable(asdict(value))
    if isinstance(value, np.ndarray):
        return jsonable(value.tolist())
    if isinstance(value, np.generic):
        return jsonable(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(item) for item in value]
    return value


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _array_sha(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).view(np.uint8)).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(jsonable(value), sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def domain_points() -> tuple[DomainPoint, ...]:
    """Return the frozen 17-point mechanical domain."""
    points = tuple(
        DomainPoint(float(h), float(beta), float(mu), float(sd))
        for h, beta, mu, sd in itertools.product(
            (1.0, 10.0), (-2.0, 2.0), (0.0005, 0.006), (0.0, 0.4)
        )
    )
    return (*points, DomainPoint(3.0, 0.0, 0.0025, 0.2))


def mechanical_domain() -> tuple[DomainPoint, ...]:
    """Compatibility alias used by independent auditors."""
    return domain_points()


def _site_ids(public: public_api.PublicInputs) -> tuple[str, ...]:
    ids = tuple(str(value) for value in public.setup.site_ids)
    if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
        raise ValueError("public site identifiers must be unique and canonically sorted")
    return ids


def subset_bank(bank: likelihood.CompressedBank, mask: NDArray[Any]) -> likelihood.CompressedBank:
    """Subset a compressed bank without changing site order or its alpha=1 law."""
    selected = np.flatnonzero(np.asarray(mask, dtype=bool))
    if selected.ndim != 1 or not len(selected):
        raise ValueError("bank subset must contain at least one site")
    return replace(
        bank,
        site_ids=tuple(bank.site_ids[index] for index in selected),
        category_counts=np.asarray(bank.category_counts)[selected],
        category_mass=np.asarray(bank.category_mass)[selected],
        power_moments=np.asarray(bank.power_moments)[selected],
        bank_arrivals=np.asarray(bank.bank_arrivals)[:, selected],
        bank_checksum=bank.bank_checksum + ":sites:" + ",".join(str(int(i)) for i in selected),
    )


def subset_observations(
    observed: likelihood.PreInvasionObservations,
    mask: NDArray[Any] | Sequence[bool],
    *,
    history: int | None = None,
) -> likelihood.PreInvasionObservations:
    """Select sites and optionally one history, retaining the frozen calendar."""
    selected = np.asarray(mask, dtype=bool)
    if selected.shape != (len(observed.site_ids),):
        raise ValueError("site mask must have one value per observation site")
    row = slice(None) if history is None else slice(history, history + 1)
    return likelihood.prepare_observations(
        observed.prey_counts[row][:, selected],
        observed.predator_counts[row][:, selected],
        tuple(np.asarray(observed.site_ids)[selected]),
        np.ones(int(selected.sum()), dtype=bool),
        initial_alive=observed.initial_alive[selected],
        prey_times=observed.prey_times,
        predator_times=observed.predator_times,
        cohort_start=observed.cohort_start,
        predator_observed=(
            None
            if observed.predator_observed is None
            else observed.predator_observed[row][:, selected]
        ),
    )


def fit_loglikelihood(
    data: FitData, *, h: float, beta: float, mu: float, detection_sd: float
) -> float:
    """Fixed alpha=1 training log likelihood used by all four models."""
    score = likelihood.point_score(
        data.observations,
        data.bank,
        h,
        beta,
        mu,
        data.map_a,
        data.site_a,
        detection_sd=detection_sd,
    )
    return float(score.training_logjoint)


def pre_loglikelihood(data: FitData, *, beta: float, mu: float, detection_sd: float) -> float:
    hazards = adjusted.normalized_hazards(beta, data.map_a, data.site_a, mu)
    value = likelihood.pre_only_log_likelihood(
        data.observations, hazards, detection_sd=detection_sd, return_site=False
    )
    return float(np.asarray(value).reshape(-1)[0])


def mechanical_observations(
    public: public_api.PublicInputs, *, history_count: int = 4
) -> likelihood.PreInvasionObservations:
    """Construct the four deterministic count patterns without private draws."""
    ids = _site_ids(public)
    if history_count != 4:
        raise ValueError("the mechanical stage has exactly four count patterns")
    sites = len(ids)
    prey = np.zeros((4, sites, len(pre_campaign.PREY_TIMES)), dtype=np.int64)
    predator = np.zeros((4, sites, len(pre_campaign.PREDATOR_TIMES)), dtype=np.int64)
    prey[1] = 2
    predator[1] = 2
    prey[2] = (np.arange(sites)[:, None] + np.arange(prey.shape[2])[None, :]) % 3
    predator[2] = (np.arange(sites)[:, None] + np.arange(predator.shape[2])[None, :]) % 3
    prey[3, :, :7] = 2
    predator[3, :, 3:] = 1
    training = np.asarray(public.setup.site_splits) == "training"
    return likelihood.prepare_observations(prey, predator, ids, training)


def make_fit_data(
    public: public_api.PublicInputs,
    bank: likelihood.CompressedBank,
    observed: likelihood.PreInvasionObservations,
    *,
    history: int | None = None,
    training: bool = True,
) -> FitData:
    mask = observed.training_mask if training else ~observed.training_mask
    return FitData(
        subset_observations(observed, mask, history=history),
        subset_bank(bank, mask),
        np.asarray(public.setup.exposure_score),
        np.asarray(public.setup.exposure_score[public.setup.site_rows, public.setup.site_cols])[
            mask
        ],
    )


def compare_compressed_exact(
    public: public_api.PublicInputs,
    bank: likelihood.CompressedBank,
    observed: likelihood.PreInvasionObservations,
    *,
    points: Sequence[DomainPoint] = domain_points(),
    tolerance: float = MECHANICAL_TOLERANCE,
) -> dict[str, Any]:
    """Compare compressed and direct integrations at every frozen domain point."""
    site_a = np.asarray(public.setup.exposure_score[public.setup.site_rows, public.setup.site_cols])
    rows: list[dict[str, Any]] = []
    for point in points:
        hazards = adjusted.normalized_hazards(
            point.beta, public.setup.exposure_score, site_a, point.mu
        )
        compressed = likelihood.build_integration(bank, (point.h,), hazards)
        exact = likelihood.build_exact_integration(bank, (point.h,), hazards)
        fast = likelihood.score_observations(observed, compressed, detection_sd=point.detection_sd)
        direct = likelihood.score_observations(observed, exact, detection_sd=point.detection_sd)
        site_error = float(np.max(np.abs(fast.joint_loglikelihood - direct.joint_loglikelihood)))
        train_error = float(np.max(np.abs(fast.training_logjoint - direct.training_logjoint)))
        holdout_error = float(np.max(np.abs(fast.holdout_logjoint - direct.holdout_logjoint)))
        train_site_error = train_error / max(1, int(observed.training_mask.sum()))
        holdout_site_error = holdout_error / max(1, int((~observed.training_mask).sum()))
        rows.append(
            {
                "point": asdict(point),
                "site_logjoint_max_abs": site_error,
                "training_logjoint_max_abs": train_error,
                "holdout_logjoint_max_abs": holdout_error,
                "training_nats_per_site_max_abs": train_site_error,
                "holdout_nats_per_site_max_abs": holdout_site_error,
                "site_logjoint": site_error,
                "training_logjoint": train_error,
                "holdout_logjoint": holdout_error,
                "passed": max(site_error, train_error, holdout_error) <= tolerance,
            }
        )
    return {
        "passed": bool(rows) and all(row["passed"] for row in rows),
        "tolerance": tolerance,
        "points": len(rows),
        "rows": rows,
    }


def full_vs_exact(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Compatibility alias for the compressed-versus-exact mechanical check."""
    return compare_compressed_exact(*args, **kwargs)


def repeat_mechanical_fits(
    public: public_api.PublicInputs,
    bank: likelihood.CompressedBank,
    observed: likelihood.PreInvasionObservations,
    *,
    tolerance: float = MECHANICAL_TOLERANCE,
) -> dict[str, Any]:
    """Run each mechanical four-model fit twice with the unchanged fitter."""
    rows: list[dict[str, Any]] = []
    for history in range(4):
        data = make_fit_data(public, bank, observed, history=history, training=True)
        first = fitting.paired_fit(data, fit_loglikelihood)
        second = fitting.paired_fit(data, fit_loglikelihood)
        differences = {
            name: float(second.fits[name].raw_logjoint - first.fits[name].raw_logjoint)
            for name in MODEL_NAMES
        }
        parameter_differences = {
            name: float(
                max(
                    abs(second.fits[name].parameters[key] - first.fits[name].parameters[key])
                    for key in first.fits[name].parameters
                )
            )
            for name in MODEL_NAMES
        }
        valid = all(
            first.fits[name].converged and second.fits[name].converged for name in MODEL_NAMES
        )
        passed = valid and all(
            math.isfinite(value) and abs(value) <= tolerance for value in differences.values()
        )
        rows.append(
            {
                "history": history,
                "passed": passed,
                "valid_status": valid,
                "repeat_logjoint_differences": differences,
                "repeat_parameter_max_abs_differences": parameter_differences,
                "first": asdict(first),
                "second": asdict(second),
            }
        )
    return {"passed": all(row["passed"] for row in rows), "tolerance": tolerance, "histories": rows}


def adjusted_pair_primitive(
    data: FitData,
    *,
    holdout_data: FitData | None = None,
    full_public: public_api.PublicInputs | None = None,
    full_bank: likelihood.CompressedBank | None = None,
    full_observed: likelihood.PreInvasionObservations | None = None,
    history: int = 0,
    tolerance: float = MECHANICAL_TOLERANCE,
) -> dict[str, Any]:
    """Check the registered adjusted pair and holdout isolation primitives."""
    paired = fitting.paired_fit(data, fit_loglikelihood)
    independent = fitting.fit_four_models(data, fit_loglikelihood)
    fit_differences = {
        name: float(independent[name].raw_logjoint - paired.fits[name].raw_logjoint)
        for name in MODEL_NAMES
    }
    arithmetic = float(
        2.0
        * (paired.fits["adjusted_free_h"].raw_logjoint - paired.fits["adjusted_h1"].raw_logjoint)
    )
    reference_pair = effect_reference.fit_effect_pair(data, fit_loglikelihood)
    reference_differences = {
        "adjusted_h1_raw_logjoint": float(
            reference_pair.null_fit.raw_logjoint - paired.fits["adjusted_h1"].raw_logjoint
        ),
        "adjusted_free_h_raw_logjoint": float(
            reference_pair.free_fit.raw_logjoint - paired.fits["adjusted_free_h"].raw_logjoint
        ),
        "adjusted_h1_h": float(reference_pair.null_fit.h - paired.fits["adjusted_h1"].h),
        "adjusted_free_h_h": float(reference_pair.free_fit.h - paired.fits["adjusted_free_h"].h),
        "adjusted_h1_beta": float(reference_pair.null_fit.beta - paired.fits["adjusted_h1"].beta),
        "adjusted_free_h_beta": float(
            reference_pair.free_fit.beta - paired.fits["adjusted_free_h"].beta
        ),
        "adjusted_h1_mu": float(reference_pair.null_fit.mu - paired.fits["adjusted_h1"].mu),
        "adjusted_free_h_mu": float(reference_pair.free_fit.mu - paired.fits["adjusted_free_h"].mu),
        "adjusted_h1_detection_sd": float(
            reference_pair.null_fit.detection_sd - paired.fits["adjusted_h1"].detection_sd
        ),
        "adjusted_free_h_detection_sd": float(
            reference_pair.free_fit.detection_sd - paired.fits["adjusted_free_h"].detection_sd
        ),
    }
    reference_statuses_match = (
        reference_pair.null_fit.numerical_status == paired.fits["adjusted_h1"].numerical_status
        and reference_pair.free_fit.numerical_status
        == paired.fits["adjusted_free_h"].numerical_status
    )
    reference_t = float(reference_pair.statistics["T"])
    result: dict[str, Any] = {
        "four_model_max_abs_difference": max(abs(value) for value in fit_differences.values()),
        "fit_differences": fit_differences,
        "effect_reference_pair_max_abs_difference": max(
            abs(value) for value in reference_differences.values()
        ),
        "effect_reference_pair_differences": reference_differences,
        "effect_reference_pair_T_difference": float(reference_t - paired.adjusted_T),
        "effect_reference_pair_statuses_match": reference_statuses_match,
        "adjusted_T_difference": float(paired.adjusted_T - max(0.0, arithmetic)),
        "passed": all(abs(value) <= tolerance for value in fit_differences.values())
        and abs(paired.adjusted_T - max(0.0, arithmetic)) <= tolerance
        and all(abs(value) <= tolerance for value in reference_differences.values())
        and abs(reference_t - paired.adjusted_T) <= tolerance
        and reference_statuses_match,
    }
    if holdout_data is not None:
        before = {name: paired.fits[name].raw_logjoint for name in MODEL_NAMES}
        scores = fitting.score_heldout(
            paired.fits,
            holdout_data,
            fit_loglikelihood,
            site_count=len(holdout_data.observations.site_ids),
        )
        prey = np.array(holdout_data.observations.prey_counts, copy=True)
        prey[0, 0, 0] = (int(prey[0, 0, 0]) + 1) % 3
        perturbed_obs = replace(holdout_data.observations, prey_counts=prey)
        perturbed = replace(holdout_data, observations=perturbed_obs)
        perturbed_scores = fitting.score_heldout(
            paired.fits,
            perturbed,
            fit_loglikelihood,
            site_count=len(perturbed.observations.site_ids),
        )
        result["holdout_scores"] = scores
        result["perturbed_holdout_scores"] = perturbed_scores
        result["holdout_changed"] = any(
            scores[name].raw_logjoint != perturbed_scores[name].raw_logjoint for name in MODEL_NAMES
        )
        result["training_unchanged"] = all(
            before[name] == paired.fits[name].raw_logjoint for name in MODEL_NAMES
        )
        if full_public is not None or full_bank is not None or full_observed is not None:
            if full_public is None or full_bank is None or full_observed is None:
                raise ValueError(
                    "full_public, full_bank, and full_observed must be supplied together"
                )
            training_mask = np.asarray(full_observed.training_mask, dtype=bool)
            holdout_sites = np.flatnonzero(~training_mask)
            if not len(holdout_sites):
                raise ValueError("holdout isolation requires at least one holdout site")
            site_index = int(holdout_sites[0])
            prey = np.array(full_observed.prey_counts, copy=True)
            prey[history, site_index, 0] = (int(prey[history, site_index, 0]) + 1) % 3
            perturbed_full = replace(full_observed, prey_counts=prey)
            rebuilt = make_fit_data(
                full_public,
                full_bank,
                perturbed_full,
                history=history,
                training=True,
            )
            same_training_arrays = (
                np.array_equal(rebuilt.observations.prey_counts, data.observations.prey_counts)
                and np.array_equal(
                    rebuilt.observations.predator_counts, data.observations.predator_counts
                )
                and tuple(rebuilt.observations.site_ids) == tuple(data.observations.site_ids)
                and np.array_equal(
                    rebuilt.observations.training_mask, data.observations.training_mask
                )
                and tuple(rebuilt.bank.site_ids) == tuple(data.bank.site_ids)
            )
            objective_differences = {
                name: float(
                    fit_loglikelihood(rebuilt, **paired.fits[name].parameters)
                    - fit_loglikelihood(data, **paired.fits[name].parameters)
                )
                for name in MODEL_NAMES
            }
            result["training_rebuild_unchanged"] = same_training_arrays
            result["training_rebuild_objective_differences"] = objective_differences
            result["training_unchanged"] = bool(
                result["training_unchanged"]
                and same_training_arrays
                and all(abs(value) <= tolerance for value in objective_differences.values())
            )
        result["passed"] = bool(
            result["passed"] and result["holdout_changed"] and result["training_unchanged"]
        )
    return cast(dict[str, Any], jsonable(result))


def holdout_perturbation_isolation(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return adjusted_pair_primitive(*args, **kwargs)


def coarse_grid_audit(data: FitData) -> dict[str, Any]:
    """Evaluate the fixed 1,350-point diagnostic grid without warm starts."""
    histories = data.observations.prey_counts.shape[0]
    maxima = {model: np.full(histories, -np.inf, dtype=np.float64) for model in MODEL_NAMES}
    best: dict[str, list[Any]] = {model: [None] * histories for model in MODEL_NAMES}
    point_rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    count = 0
    for h, beta, mu, sd in itertools.product(COARSE_H, COARSE_BETA, COARSE_MU, COARSE_SD):
        count += 1
        models = MODEL_NAMES if beta == 0.0 else ("adjusted_free_h", "adjusted_h1")
        hazards = adjusted.normalized_hazards(beta, data.map_a, data.site_a, mu)
        integration = likelihood.build_integration(data.bank, COARSE_H, hazards)
        values = likelihood.score_observations(
            data.observations, integration, detection_sd=sd
        ).training_logjoint
        point_rows.append(
            {
                "point": {
                    "h": float(h),
                    "beta": float(beta),
                    "mu": float(mu),
                    "detection_sd": float(sd),
                },
                "applicable_models": list(models),
                "training_logjoint_by_history_and_h": values,
            }
        )
        free_index = int(np.flatnonzero(np.asarray(COARSE_H) == h)[0])
        for model in models:
            index = free_index if model.endswith("free_h") else 0
            proposed = values[:, index]
            improved = proposed > maxima[model]
            for history in np.flatnonzero(improved):
                best[model][int(history)] = {
                    "h": float(h if model.endswith("free_h") else 1.0),
                    "beta": float(beta),
                    "mu": float(mu),
                    "detection_sd": float(sd),
                }
            maxima[model] = np.maximum(maxima[model], proposed)
    return {
        "points": count,
        "expected_points": 1350,
        "max_logjoint": maxima,
        "parameters": best,
        "raw_points": point_rows,
        "grid": {"h": COARSE_H, "beta": COARSE_BETA, "mu": COARSE_MU, "detection_sd": COARSE_SD},
        "elapsed_seconds": time.perf_counter() - started,
        "diagnostic_only": True,
    }


def check_grid_against_fits(
    grid: Mapping[str, Any],
    fits: Mapping[str, fitting.FitResult],
    *,
    tolerance: float = GRID_TOLERANCE,
) -> dict[str, Any]:
    maxima = grid["max_logjoint"]
    gaps = {model: float(np.max(maxima[model]) - fits[model].raw_logjoint) for model in fits}
    return {
        "passed": all(value <= tolerance for value in gaps.values()),
        "tolerance": tolerance,
        "gaps": gaps,
    }


def _validate_manifest(
    public: public_api.PublicInputs,
    directory: Path,
    *,
    expected_bank_size: int = BANK_SIZE,
    expected_site_count: int = SITE_COUNT,
) -> tuple[np.ndarray, dict[str, Any]]:
    site_a = np.asarray(public.setup.exposure_score[public.setup.site_rows, public.setup.site_cols])
    max_x = 0.0
    for beta in (-2.0, 2.0):
        hazards = adjusted.normalized_hazards(beta, public.setup.exposure_score, site_a, 0.006)
        max_x = max(max_x, float(10.0 * np.max(hazards) * 9.0))
    if max_x > likelihood.SERIES_DOMAIN * (1.0 + 1e-14):
        raise ValueError(
            "public map exceeds compressed integration domain: "
            f"x={max_x:g} > {likelihood.SERIES_DOMAIN:g}"
        )
    manifest_path = directory / "manifest.json"
    array_path = directory / "arrivals.npy"
    if not manifest_path.exists() or not array_path.exists():
        raise ValueError("frozen arrival bank requires manifest.json and arrivals.npy")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_ids = list(_site_ids(public))
    public_root = public.metadata.get("root")
    if manifest.get("root") != public_root:
        raise ValueError("arrival-bank root does not match public inputs")
    if (
        manifest.get("namespace") != public_api.NAMESPACE
        or manifest.get("stage") != public_api.BANK_STAGE
    ):
        raise ValueError("arrival-bank namespace or stage is not registered")
    if (
        manifest.get("array_shape") != [expected_bank_size, expected_site_count]
        or manifest.get("bank_size") != expected_bank_size
    ):
        raise ValueError("arrival-bank manifest has the wrong frozen shape")
    if manifest.get("site_ids") != expected_ids:
        raise ValueError("arrival-bank manifest site order does not match public inputs")
    started_path = directory / "started.json"
    ledger_path = directory / "seed_ledger.npz"
    if not started_path.is_file() or not ledger_path.is_file():
        raise ValueError("arrival-bank started receipt and seed ledger are required")
    if manifest.get("started_receipt_sha256") != _sha(started_path):
        raise ValueError("arrival-bank started receipt hash mismatch")
    started = json.loads(started_path.read_text(encoding="utf-8"))
    for key in ("root", "namespace", "stage", "bank_size", "site_ids"):
        if started.get(key) != manifest.get(key):
            raise ValueError(f"arrival-bank started receipt mismatch for {key}")
    with np.load(ledger_path, allow_pickle=False) as ledger:
        seeds = np.asarray(ledger["seeds"], dtype=np.uint64)
        if seeds.shape != (expected_bank_size,):
            raise ValueError("arrival-bank seed ledger shape mismatch")
        expected_seeds = np.asarray(
            [
                public_api._u64_seed(int(manifest["root"]), public_api.BANK_STAGE, index)
                for index in range(expected_bank_size)
            ],
            dtype=np.uint64,
        )
        if not np.array_equal(seeds, expected_seeds):
            raise ValueError("arrival-bank seed ledger mismatch")
        if manifest.get("ledger_sha256") != _array_sha(seeds):
            raise ValueError("arrival-bank seed ledger checksum mismatch")
    if manifest.get("ledger_file_sha256") != _sha(ledger_path):
        raise ValueError("arrival-bank seed ledger file checksum mismatch")
    chunks = sorted(manifest.get("chunks", []), key=lambda row: int(row["offset"]))
    if not chunks or sum(int(row["rows"]) for row in chunks) != expected_bank_size:
        raise ValueError("arrival-bank chunk ledger is incomplete")
    next_offset = 0
    for chunk in chunks:
        if int(chunk["offset"]) != next_offset:
            raise ValueError("arrival-bank chunk offsets are not contiguous")
        chunk_path = directory / f"chunk-{int(chunk['offset']):08d}.npz"
        if not chunk_path.is_file() or chunk.get("file_sha256") != _sha(chunk_path):
            raise ValueError("arrival-bank chunk file checksum mismatch")
        next_offset += int(chunk["rows"])
    arrivals = np.load(array_path, mmap_mode="r", allow_pickle=False)
    if (
        tuple(arrivals.shape) != (expected_bank_size, expected_site_count)
        or not np.isfinite(arrivals).all()
        or (arrivals < 0).any()
    ):
        raise ValueError("arrival bank array shape or values are invalid")
    checksum = _array_sha(arrivals)
    if manifest.get("array_sha256") != checksum:
        raise ValueError("arrival-bank checksum mismatch")
    if manifest.get("arrivals_file_sha256") != _sha(array_path):
        raise ValueError("arrival-bank file checksum mismatch")
    if manifest.get("public_input_array_sha256") != public_api._array_hashes(public.fixed):
        raise ValueError("arrival-bank public input identity mismatch")
    if manifest.get("map_a_sha256") != _array_sha(public.setup.exposure_score):
        raise ValueError("arrival-bank map covariate identity mismatch")
    fixed = public.fixed
    invariants = fixed.invariants
    if (
        tuple(fixed.landscape.shape) != (72, 84)
        or len(public.setup.site_ids) != expected_site_count
        or not all(bool(value) for value in invariants.values())
    ):
        raise ValueError("public map/design certificate failed")
    if int(np.asarray(public.setup.site_splits).tolist().count("training")) != 120:
        raise ValueError("public training split certificate failed")
    manifest = dict(manifest)
    manifest["manifest_sha256"] = _sha(manifest_path)
    return arrivals, manifest


def validate_bank_manifest(
    public: public_api.PublicInputs,
    directory: Path,
    *,
    expected_bank_size: int = BANK_SIZE,
    expected_site_count: int = SITE_COUNT,
) -> dict[str, Any]:
    _, manifest = _validate_manifest(
        public,
        directory,
        expected_bank_size=expected_bank_size,
        expected_site_count=expected_site_count,
    )
    return manifest


def _fixture_seed(root: int, index: int, stage: int) -> int:
    """Return the registered five-word child address for one stream."""
    return int(
        np.random.SeedSequence(
            [root, public_api.NAMESPACE, PUBLIC_STAGE, index, stage]
        ).generate_state(1, dtype=np.uint64)[0]
    )


def _registered_truths() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for index, effect, beta, mu, sd in (
        (0, 1.0, 0.0, 0.0025, 0.2),
        (1, 3.0, 0.0, 0.0025, 0.2),
        (2, 1.0, -1.0, 0.001, 0.0),
        (3, 3.0, -1.0, 0.001, 0.0),
        (4, 1.0, 1.0, 0.004, 0.3),
        (5, 3.0, 1.0, 0.004, 0.3),
    ):
        rows.append(
            {
                "index": index,
                "effect": effect,
                "mean_hazard": mu,
                "beta": beta,
                "detection_sd": sd,
                "background": "exact",
            }
        )
    rows.extend(
        {
            "index": index,
            "effect": effect,
            "mean_hazard": 0.0025,
            "beta": None,
            "detection_sd": 0.2,
            "background": "B100-A",
        }
        for index, effect in ((6, 1.0), (7, 3.0))
    )
    return tuple(rows)


def _fixture_seeds(root: int, index: int) -> dict[str, Any]:
    streams = {
        name: _fixture_seed(root, index, stage) for name, stage in PUBLIC_STREAM_STAGES.items()
    }
    return {
        "root": root,
        "namespace": public_api.NAMESPACE,
        "stage": PUBLIC_STAGE,
        "index": index,
        "stream_stages": dict(PUBLIC_STREAM_STAGES),
        "streams": streams,
    }


def _truth_object(row: Mapping[str, Any]) -> public_api.GeneralTruth:
    return public_api.GeneralTruth(
        int(row["index"]),
        float(row["effect"]),
        float(row["mean_hazard"]),
        float(row["beta"] if row["beta"] is not None else 0.0),
        float(row["detection_sd"]),
        str(row["background"]),
    )


def generate_public_panel(
    public_inputs_dir: Path,
    qualification_dir: Path,
    output: Path,
    *,
    root: int,
) -> dict[str, Any]:
    """Freeze and generate the eight registered public fixtures exactly once."""
    if type(root) is not int or root < 0:
        raise ValueError("root must be a nonnegative integer")
    if output.exists():
        raise FileExistsError("refusing to replace registered public fixtures")
    qualification_path = qualification_dir / "qualification.json"
    mechanical_path = qualification_dir / "mechanical-receipt.json"
    if not qualification_path.is_file() or not mechanical_path.is_file():
        raise ValueError("qualification and mechanical receipt are required before generation")
    qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
    mechanical = json.loads(mechanical_path.read_text(encoding="utf-8"))
    if not qualification.get("passed") or not mechanical.get("passed"):
        raise ValueError("public generation requires passed mechanical qualification")
    public = public_api.load_public_inputs(public_inputs_dir)
    if root != public.metadata.get("root"):
        raise ValueError("fixture root must match frozen public-input root")
    output.mkdir(parents=True)
    truths = _registered_truths()
    ledger = {
        "schema_version": "goal059-public-fixture-ledger-v1",
        "root": root,
        "namespace": public_api.NAMESPACE,
        "stage": PUBLIC_STAGE,
        "stream_stages": PUBLIC_STREAM_STAGES,
        "indices": list(range(8)),
        "seeds": [_fixture_seeds(root, index) for index in range(8)],
    }
    qualification_hash = _sha(qualification_path)
    mechanical_hash = _sha(mechanical_path)
    public_hash = str(
        public.metadata.get("public_inputs_sha256", _sha(public_inputs_dir / "public_inputs.npz"))
    )
    _write_json(output / "seed_ledger.json", ledger)
    _write_json(output / "truths.json", {"truths": truths})
    pre_draw = {
        "schema_version": "goal059-public-fixture-predraw-v1",
        "root": root,
        "namespace": public_api.NAMESPACE,
        "stage": PUBLIC_STAGE,
        "qualification_sha256": qualification_hash,
        "mechanical_receipt_sha256": mechanical_hash,
        "public_inputs_sha256": public_hash,
        "seed_ledger_sha256": _sha(output / "seed_ledger.json"),
        "truths_sha256": _sha(output / "truths.json"),
    }
    _write_json(output / "pre_draw.json", pre_draw)
    observations: list[dict[str, Any]] = []
    evaluators: list[dict[str, Any]] = []
    map_hazards: list[np.ndarray] = []
    for row in truths:
        truth = _truth_object(row)
        seeds = _fixture_seeds(root, truth.index)
        if truth.background == "exact":
            observed, evaluator = public_api.generate_exact_history(
                public.fixed, public.setup, truth, seeds
            )
            hazards = adjusted.normalized_hazards(
                truth.beta,
                public.setup.exposure_score,
                np.asarray(public.setup.exposure_score).reshape(-1),
                truth.mean_hazard,
            ).reshape(public.setup.exposure_score.shape)
        else:
            observed, evaluator = public_api.generate_b100_history(
                public.fixed, public.setup, truth, seeds
            )
            if "map_hazard" in evaluator:
                hazards = np.asarray(evaluator["map_hazard"], dtype=np.float64)
            else:
                hazards = public_api._b100_hazard(
                    public.setup,
                    np.random.default_rng(seeds["streams"]["background_field"]),
                    truth.mean_hazard,
                )
        observations.append(observed)
        evaluators.append(evaluator)
        map_hazards.append(np.asarray(hazards, dtype=np.float64))
    # Keep every numeric evaluator field emitted by the generator.  The map
    # hazard is added for exact histories as a derived, replayable array and
    # is already present in the B100 evaluator.  This makes the released NPZ
    # sufficient for a raw-score audit without rerunning generation.
    evaluator_arrays: dict[str, np.ndarray] = {}
    evaluator_keys = sorted(
        {
            str(key)
            for evaluator in evaluators
            for key, value in evaluator.items()
            if isinstance(value, np.ndarray)
        }
        | {"map_hazard"}
    )
    for key in evaluator_keys:
        values: list[np.ndarray] = []
        for evaluator, fallback_hazard in zip(evaluators, map_hazards, strict=True):
            value = fallback_hazard if key == "map_hazard" else evaluator.get(key)
            if not isinstance(value, np.ndarray):
                raise ValueError(f"evaluator array {key!r} is missing from a history")
            values.append(np.asarray(value))
        try:
            evaluator_arrays[key] = np.stack(values)
        except ValueError as error:
            raise ValueError(f"evaluator array {key!r} has inconsistent shapes") from error
    np.savez_compressed(
        output / "observations.npz",
        prey_counts=np.stack([item["prey_counts"] for item in observations]),
        predator_counts=np.stack([item["predator_counts"] for item in observations]),
        site_ids=np.asarray(public.setup.site_ids),
        initial_alive=np.ones(len(public.setup.site_ids), dtype=bool),
    )
    evaluator_payload: dict[str, Any] = {
        **evaluator_arrays,
        "stream_seeds": np.asarray(
            [
                [_fixture_seed(root, index, stage) for stage in PUBLIC_STREAM_STAGES.values()]
                for index in range(8)
            ],
            dtype=np.uint64,
        ),
    }
    np.savez_compressed(output / "evaluator.npz", **cast(Any, evaluator_payload))
    evaluator_json = {
        "schema_version": "goal059-evaluator-v1",
        "truths": truths,
        "seed_ledger_sha256": _sha(output / "seed_ledger.json"),
        "array_names": [*sorted(evaluator_arrays), "stream_seeds"],
        "arrays": {
            "observations_sha256": _sha(output / "observations.npz"),
            "evaluator_sha256": _sha(output / "evaluator.npz"),
        },
    }
    _write_json(output / "evaluator.json", evaluator_json)
    manifest = {
        **pre_draw,
        "state": "generated",
        "observations_sha256": _sha(output / "observations.npz"),
        "evaluator_npz_sha256": _sha(output / "evaluator.npz"),
        "evaluator_json_sha256": _sha(output / "evaluator.json"),
        "truths_sha256": _sha(output / "truths.json"),
        "site_ids": list(public.setup.site_ids),
        "observation_shape": list(np.asarray(observations[0]["prey_counts"]).shape),
    }
    _write_json(output / "manifest.json", manifest)
    return manifest


def compress_and_save_bank(
    bank: np.ndarray, site_ids: Sequence[str], output: Path
) -> likelihood.CompressedBank:
    compressed = likelihood.compress_bank(bank, site_ids)
    np.savez_compressed(
        output,
        site_ids=np.asarray(compressed.site_ids),
        bank_size=compressed.bank_size,
        category_counts=compressed.category_counts,
        category_mass=compressed.category_mass,
        power_moments=compressed.power_moments,
        bank_checksum=compressed.bank_checksum,
        series_order=compressed.series_order,
        max_x=compressed.max_x,
    )
    return compressed


def bank_representations(
    arrivals: NDArray[Any], site_ids: Sequence[str]
) -> dict[str, likelihood.CompressedBank]:
    """Build the registered full and two disjoint half-bank alpha=1 views."""
    values = np.asarray(arrivals, dtype=np.float64)
    if values.ndim != 2 or values.shape[0] < 2 or values.shape[0] % 2:
        raise ValueError("arrival bank must have an even number of rows")
    midpoint = values.shape[0] // 2
    return {
        "full": likelihood.compress_bank(values, site_ids),
        "first_half": likelihood.compress_bank(values[:midpoint], site_ids),
        "second_half": likelihood.compress_bank(values[midpoint:], site_ids),
    }


def _heldout_row(
    public: public_api.PublicInputs,
    bank: likelihood.CompressedBank,
    observed: likelihood.PreInvasionObservations,
    fit: fitting.FitResult,
    *,
    history: int,
) -> dict[str, Any]:
    data = make_fit_data(public, bank, observed, history=history, training=False)
    score = likelihood.point_score(
        data.observations,
        data.bank,
        fit.h,
        fit.beta,
        fit.mu,
        data.map_a,
        data.site_a,
        detection_sd=fit.detection_sd,
    )
    values = np.asarray(score.conditional_prey_site_loglikelihood[0], dtype=np.float64)
    clusters = np.asarray(public.setup.site_cluster_ids)[~observed.training_mask]
    cluster_values = {
        str(cluster): float(values[clusters == cluster].sum())
        for cluster in sorted(set(str(value) for value in clusters))
    }
    return {
        "conditional_prey_total_nats": float(values.sum()),
        "conditional_prey_nats_per_site": float(values.mean()),
        "conditional_prey_site_nats": values,
        "cluster_contributions_nats": cluster_values,
    }


def fit_panel_task(
    public: public_api.PublicInputs,
    bank: likelihood.CompressedBank,
    observed: likelihood.PreInvasionObservations,
    *,
    history: int,
    representation: str,
    output: Path | None = None,
) -> dict[str, Any]:
    """Fit one history/representation task and retain main fits before profiles."""
    train = make_fit_data(public, bank, observed, history=history, training=True)
    paired = fitting.paired_fit(train, fit_loglikelihood)
    main: dict[str, Any] = {
        "history": history,
        "representation": representation,
        "bank_size": bank.bank_size,
        "paired": asdict(paired),
        "adjusted_T": paired.adjusted_T,
        "constant_T": paired.constant_T,
        "fits": jsonable(paired.fits),
    }
    if output is not None:
        output.mkdir(parents=True, exist_ok=True)
        _write_json(output / f"history-{history:02d}-{representation}-main.json", main)
    profiles = {
        "constant_h": fitting.profile_h(train, fit_loglikelihood, paired.fits["constant_free_h"]),
        "adjusted_h": fitting.profile_h(train, fit_loglikelihood, paired.fits["adjusted_free_h"]),
        "adjusted_beta": fitting.profile_beta(
            train, fit_loglikelihood, paired.fits["adjusted_free_h"]
        ),
    }
    profile_models = {
        "constant_h": "constant_free_h",
        "adjusted_h": "adjusted_free_h",
        "adjusted_beta": "adjusted_free_h",
    }
    profile_main_gaps = {
        name: float(
            np.nanmax(np.asarray(profile.values, dtype=float))
            - paired.fits[profile_models[name]].raw_logjoint
        )
        for name, profile in profiles.items()
    }
    profile_statuses = {
        name: all(status == "converged" for status in profile.statuses)
        for name, profile in profiles.items()
    }
    main_statuses = {name: fit.converged for name, fit in paired.fits.items()}
    nesting_gaps = {
        "constant": float(
            paired.fits["constant_h1"].raw_logjoint - paired.fits["constant_free_h"].raw_logjoint
        ),
        "adjusted": float(
            paired.fits["adjusted_h1"].raw_logjoint - paired.fits["adjusted_free_h"].raw_logjoint
        ),
    }
    heldout = {
        name: _heldout_row(public, bank, observed, fit, history=history)
        for name, fit in paired.fits.items()
    }
    result = {
        **main,
        "profiles": {name: asdict(profile) for name, profile in profiles.items()},
        "profile_main_gaps": profile_main_gaps,
        "profile_statuses_converged": profile_statuses,
        "main_statuses_converged": main_statuses,
        "nesting_gaps": nesting_gaps,
        "nesting_gap_gate": all(value <= GRID_TOLERANCE for value in nesting_gaps.values()),
        "heldout_scores": heldout,
        "main_replay_logjoint_differences": {
            name: float(fit_loglikelihood(train, **fit.parameters) - fit.raw_logjoint)
            for name, fit in paired.fits.items()
        },
    }
    if output is not None:
        _write_json(output / f"history-{history:02d}-{representation}.json", result)
    return result


def bank_stability_summary(
    rows: Mapping[str, Mapping[str, Any]],
    *,
    generating_h: float | None = None,
    generating_beta: float | None = None,
    tolerance: float = 0.5,
) -> dict[str, Any]:
    """Apply descriptive full/half-bank gates to already stored task rows."""
    if set(rows) != {"full", "first_half", "second_half"}:
        raise ValueError("stability requires full, first_half, and second_half rows")
    fits = {name: rows[name]["paired"]["fits"] for name in rows}
    adjusted_movement = {
        name: abs(
            float(fits[name]["adjusted_free_h"]["h"]) - float(fits["full"]["adjusted_free_h"]["h"])
        )
        for name in ("first_half", "second_half")
    }
    profile_movement: dict[str, dict[str, float]] = {}
    profile_support: dict[str, dict[str, float]] = {}
    for profile_name in ("constant_h", "adjusted_h", "adjusted_beta"):
        full_values = np.asarray(rows["full"]["profiles"][profile_name]["values"], dtype=float)
        full_r = 2.0 * (np.nanmax(full_values) - full_values)
        profile_support[profile_name] = {"full": float(np.nanmax(full_r))}
        profile_movement[profile_name] = {}
        for name in ("first_half", "second_half"):
            values = np.asarray(rows[name]["profiles"][profile_name]["values"], dtype=float)
            r = 2.0 * (np.nanmax(values) - values)
            profile_support[profile_name][name] = float(np.nanmax(r))
            union = (full_r <= 10.0) | (r <= 10.0)
            profile_movement[profile_name][name] = float(
                np.nanmax(np.abs(r[union] - full_r[union]))
            )
    generating_profile_movement: dict[str, float] = {}
    for profile_name, coordinate in (
        ("constant_h", generating_h),
        ("adjusted_h", generating_h),
        ("adjusted_beta", generating_beta),
    ):
        if coordinate is None:
            continue
        grid = np.asarray(rows["full"]["profiles"][profile_name]["grid"], dtype=float)
        locations = np.flatnonzero(np.isclose(grid, coordinate, atol=1e-12))
        if not len(locations):
            raise ValueError(
                f"generating {profile_name} node is outside the registered profile grid"
            )
        index = int(locations[0])
        full_values = np.asarray(rows["full"]["profiles"][profile_name]["values"], dtype=float)
        full_r = 2.0 * (np.nanmax(full_values) - full_values)
        for name in ("first_half", "second_half"):
            values = np.asarray(rows[name]["profiles"][profile_name]["values"], dtype=float)
            r = 2.0 * (np.nanmax(values) - values)
            generating_profile_movement[f"{profile_name}:{name}"] = abs(
                float(r[index] - full_r[index])
            )
    heldout_movement: dict[str, float] = {}
    for left, right in itertools.combinations(MODEL_NAMES, 2):
        full_contrast = float(
            rows["full"]["heldout_scores"][left]["conditional_prey_total_nats"]
            - rows["full"]["heldout_scores"][right]["conditional_prey_total_nats"]
        )
        for name in ("first_half", "second_half"):
            contrast = float(
                rows[name]["heldout_scores"][left]["conditional_prey_total_nats"]
                - rows[name]["heldout_scores"][right]["conditional_prey_total_nats"]
            )
            heldout_movement[f"{name}:{left}:{right}"] = abs(contrast - full_contrast)
    profile_main_gates = {
        name: (
            all(
                float(value) <= GRID_TOLERANCE for value in rows[name]["profile_main_gaps"].values()
            )
            and all(rows[name]["profile_statuses_converged"].values())
            and all(rows[name]["main_statuses_converged"].values())
            and rows[name]["nesting_gap_gate"]
        )
        for name in rows
    }
    adjusted_t_movement = {
        name: abs(float(rows[name]["adjusted_T"]) - float(rows["full"]["adjusted_T"]))
        for name in ("first_half", "second_half")
    }
    gates = {
        "adjusted_T_movement": all(value <= tolerance for value in adjusted_t_movement.values()),
        "centered_profile_R_movement": all(
            value <= tolerance for values in profile_movement.values() for value in values.values()
        ),
        "heldout_candidate_contrasts": all(
            value <= tolerance for value in heldout_movement.values()
        ),
        "main_and_profile_status": all(profile_main_gates.values()),
        "generating_profile_R_movement": all(
            value <= tolerance for value in generating_profile_movement.values()
        ),
    }
    return {
        "status": "operational_nested_bank_stability",
        "gates": gates,
        "passed": all(gates.values()),
        "tolerance": tolerance,
        "adjusted_h_movement": adjusted_movement,
        "adjusted_T_movement": adjusted_t_movement,
        "centered_profile_R_movement": profile_movement,
        "profile_support_R": profile_support,
        "generating_profile_R_movement": generating_profile_movement,
        "heldout_candidate_contrast_movement": heldout_movement,
        "main_and_profile_status": profile_main_gates,
        "generating_nodes": {"h": generating_h, "beta": generating_beta},
        "interpretation": (
            "descriptive operational nested-bank stability; not convergence or type-I proof"
        ),
    }


def load_panel_observations(
    public: public_api.PublicInputs, panel_directory: Path
) -> likelihood.PreInvasionObservations:
    """Load the released observation package after the public draw."""
    path = panel_directory / "observations.npz"
    if not path.is_file():
        raise FileNotFoundError(path)
    with np.load(path, allow_pickle=False) as values:
        required = {"prey_counts", "predator_counts", "site_ids"}
        missing = required.difference(values.files)
        if missing:
            raise ValueError(f"observation package is missing {sorted(missing)}")
        ids = tuple(str(value) for value in values["site_ids"])
        expected = _site_ids(public)
        if ids != expected:
            raise ValueError("observation site order does not match public inputs")
        split = np.asarray(public.setup.site_splits) == "training"
        return likelihood.prepare_observations(
            values["prey_counts"],
            values["predator_counts"],
            ids,
            split,
            initial_alive=values["initial_alive"] if "initial_alive" in values.files else True,
        )


def _validate_panel_release(
    public: public_api.PublicInputs, panel_directory: Path
) -> dict[str, Any]:
    """Bind panel observations, evaluator arrays, and truth metadata together."""
    required = (
        "manifest.json",
        "seed_ledger.json",
        "truths.json",
        "pre_draw.json",
        "observations.npz",
        "evaluator.npz",
        "evaluator.json",
    )
    if any(not (panel_directory / name).is_file() for name in required):
        raise ValueError("registered panel release is missing a provenance artifact")
    manifest = json.loads((panel_directory / "manifest.json").read_text(encoding="utf-8"))
    expected_root = public.metadata.get("root")
    if (
        manifest.get("root") != expected_root
        or manifest.get("namespace") != public_api.NAMESPACE
        or manifest.get("stage") != PUBLIC_STAGE
        or manifest.get("state") != "generated"
    ):
        raise ValueError("panel release address or state is not registered")
    truths_payload = json.loads((panel_directory / "truths.json").read_text(encoding="utf-8"))
    truth_rows = truths_payload.get("truths")
    expected_truths = jsonable(_registered_truths())
    if truth_rows != expected_truths:
        raise ValueError("panel truth metadata does not match the registered design")
    ledger = json.loads((panel_directory / "seed_ledger.json").read_text(encoding="utf-8"))
    expected_ledger = {
        "schema_version": "goal059-public-fixture-ledger-v1",
        "root": expected_root,
        "namespace": public_api.NAMESPACE,
        "stage": PUBLIC_STAGE,
        "stream_stages": PUBLIC_STREAM_STAGES,
        "indices": list(range(8)),
        "seeds": [_fixture_seeds(int(expected_root), index) for index in range(8)],
    }
    if ledger != expected_ledger:
        raise ValueError("panel fixture seed ledger does not match the registered address law")
    pre_draw = json.loads((panel_directory / "pre_draw.json").read_text(encoding="utf-8"))
    if pre_draw.get("seed_ledger_sha256") != _sha(
        panel_directory / "seed_ledger.json"
    ) or pre_draw.get("truths_sha256") != _sha(panel_directory / "truths.json"):
        raise ValueError("panel pre-draw receipt hash mismatch")
    evaluator_json = json.loads((panel_directory / "evaluator.json").read_text(encoding="utf-8"))
    if (
        evaluator_json.get("seed_ledger_sha256") != _sha(panel_directory / "seed_ledger.json")
        or evaluator_json.get("arrays", {}).get("observations_sha256")
        != _sha(panel_directory / "observations.npz")
        or evaluator_json.get("arrays", {}).get("evaluator_sha256")
        != _sha(panel_directory / "evaluator.npz")
    ):
        raise ValueError("panel evaluator receipt hash mismatch")
    expected_hashes = {
        "observations_sha256": _sha(panel_directory / "observations.npz"),
        "evaluator_npz_sha256": _sha(panel_directory / "evaluator.npz"),
        "evaluator_json_sha256": _sha(panel_directory / "evaluator.json"),
        "truths_sha256": _sha(panel_directory / "truths.json"),
    }
    if any(manifest.get(key) != value for key, value in expected_hashes.items()):
        raise ValueError("panel manifest hash mismatch")
    return cast(dict[str, Any], manifest)


def _panel_worker(
    task: tuple[
        public_api.PublicInputs,
        likelihood.CompressedBank,
        likelihood.PreInvasionObservations,
        int,
        str,
        Path,
    ],
) -> tuple[tuple[int, str], dict[str, Any]]:
    public, bank, observed, history, representation, output = task
    return (
        (history, representation),
        fit_panel_task(
            public,
            bank,
            observed,
            history=history,
            representation=representation,
            output=output,
        ),
    )


def run_panel(
    public_inputs_dir: Path,
    bank_dir: Path,
    panel_directory: Path,
    output: Path,
    *,
    workers: int = 1,
    expected_bank_size: int = BANK_SIZE,
) -> dict[str, Any]:
    """Fit the released eight-history panel over three fixed bank views.

    The function consumes an observation package; it never creates or draws
    one.  Main fits are written before profiles, so interruption leaves an
    auditable partial result.
    """
    if output.exists():
        raise FileExistsError("refusing to replace an earlier panel analysis")
    if not 1 <= workers <= MAX_WORKERS:
        raise ValueError("workers must lie in [1, 16]")
    public = public_api.load_public_inputs(public_inputs_dir)
    arrivals, manifest = _validate_manifest(public, bank_dir, expected_bank_size=expected_bank_size)
    panel_manifest = _validate_panel_release(public, panel_directory)
    observed = load_panel_observations(public, panel_directory)
    if observed.prey_counts.shape[0] != 8:
        raise ValueError("registered public panel must contain exactly eight histories")
    truths_path = panel_directory / "truths.json"
    if not truths_path.is_file():
        raise ValueError("registered panel truths metadata is required for stability nodes")
    truth_rows = json.loads(truths_path.read_text(encoding="utf-8"))["truths"]
    if [int(row["index"]) for row in truth_rows] != list(range(8)):
        raise ValueError("panel truth indices must be exactly 0..7")
    output.mkdir(parents=True)
    results_directory = output / "results"
    results_directory.mkdir()
    representations = bank_representations(arrivals, _site_ids(public))
    task_arguments = [
        (public, bank, observed, history, representation, results_directory)
        for history in range(8)
        for representation, bank in representations.items()
    ]
    started = time.perf_counter()
    rows: dict[tuple[int, str], dict[str, Any]] = {}

    with ProcessPoolExecutor(max_workers=workers) as pool:
        for key, row in pool.map(_panel_worker, task_arguments):
            rows[key] = row
    coarse: dict[str, Any] = {}
    for representation, bank in representations.items():
        grid = coarse_grid_audit(make_fit_data(public, bank, observed, training=True))
        grid_gaps = {
            model: {
                str(history): float(
                    grid["max_logjoint"][model][history]
                    - rows[(history, representation)]["paired"]["fits"][model]["raw_logjoint"]
                )
                for history in range(8)
            }
            for model in MODEL_NAMES
        }
        grid["main_fit_gaps"] = grid_gaps
        grid["main_fit_gate"] = all(
            gap <= GRID_TOLERANCE for model in grid_gaps.values() for gap in model.values()
        )
        coarse[representation] = grid
        _write_json(output / f"coarse-grid-{representation}.json", grid)
    stability = {
        str(history): bank_stability_summary(
            {representation: rows[(history, representation)] for representation in representations},
            generating_h=float(truth_rows[history]["effect"]),
            generating_beta=(
                None
                if truth_rows[history].get("beta") is None
                else float(truth_rows[history]["beta"])
            ),
        )
        for history in range(8)
    }
    _write_json(output / "bank-stability.json", stability)
    all_task_status_gate = all(
        row["nesting_gap_gate"]
        and all(row["main_statuses_converged"].values())
        and all(row["profile_statuses_converged"].values())
        and all(value <= GRID_TOLERANCE for value in row["profile_main_gaps"].values())
        for row in rows.values()
    )
    all_coarse_gate = all(bool(grid["main_fit_gate"]) for grid in coarse.values())
    receipt = {
        "schema_version": "goal059-public-panel-v1",
        "status": "completed",
        "histories": 8,
        "representations": list(representations),
        "workers": workers,
        "bank_manifest": manifest,
        "raw_arrivals_sha256": _array_sha(arrivals),
        "compressed_bank_checksums": {
            name: bank.bank_checksum for name, bank in representations.items()
        },
        "observations_sha256": _sha(panel_directory / "observations.npz"),
        "evaluator_sha256": _sha(panel_directory / "evaluator.npz"),
        "panel_manifest_sha256": _sha(panel_directory / "manifest.json"),
        "panel_release": panel_manifest,
        "coarse_grid": {name: {"points": grid["points"]} for name, grid in coarse.items()},
        "coarse_grid_main_fit_gate": {
            name: bool(grid["main_fit_gate"]) for name, grid in coarse.items()
        },
        "all_task_status_gate": all_task_status_gate,
        "all_coarse_grid_main_fit_gate": all_coarse_gate,
        "passed": bool(
            all_task_status_gate
            and all_coarse_gate
            and all(item["passed"] for item in stability.values())
        ),
        "bank_stability": stability,
        "elapsed_seconds": time.perf_counter() - started,
    }
    _write_json(output / "completed.json", receipt)
    if not receipt["passed"]:
        raise QualificationFailure("public panel qualification failed; outputs preserved")
    return receipt


def qualify(
    public_inputs_dir: Path,
    bank_dir: Path,
    output: Path,
    *,
    workers: int = 1,
    expected_bank_size: int = BANK_SIZE,
) -> dict[str, Any]:
    """Run mechanical qualification and persist a receipt before panel work."""
    if output.exists():
        raise FileExistsError("refusing to replace an earlier qualification")
    if not 1 <= workers <= MAX_WORKERS:
        raise ValueError("workers must lie in [1, 16]")
    output.mkdir(parents=True)
    started = time.perf_counter()
    receipt: dict[str, Any] = {
        "schema_version": "goal059-qualification-v1",
        "status": "incomplete",
        "workers": workers,
        "expected_bank_size": expected_bank_size,
    }
    try:
        public = public_api.load_public_inputs(public_inputs_dir)
        raw, manifest = _validate_manifest(
            public, bank_dir, expected_bank_size=expected_bank_size, expected_site_count=SITE_COUNT
        )
        ids = _site_ids(public)
        bank = likelihood.compress_bank(raw, ids)
        np.savez_compressed(
            output / "compressed-bank.npz",
            site_ids=np.asarray(bank.site_ids),
            bank_size=bank.bank_size,
            category_counts=bank.category_counts,
            category_mass=bank.category_mass,
            power_moments=bank.power_moments,
            bank_checksum=bank.bank_checksum,
            series_order=bank.series_order,
            max_x=bank.max_x,
        )
        observed = mechanical_observations(public)
        comparisons = compare_compressed_exact(public, bank, observed)
        fits = repeat_mechanical_fits(public, bank, observed)
        train = make_fit_data(public, bank, observed, history=0, training=True)
        holdout = make_fit_data(public, bank, observed, history=0, training=False)
        primitive = adjusted_pair_primitive(
            train,
            holdout_data=holdout,
            full_public=public,
            full_bank=bank,
            full_observed=observed,
            history=0,
        )
        passed = bool(comparisons["passed"] and fits["passed"] and primitive["passed"])
        mechanical_receipt = {
            "schema_version": "goal059-mechanical-receipt-v1",
            "root": MECHANICAL_ROOT,
            "bank_manifest": manifest,
            "mechanical_domain": [asdict(point) for point in domain_points()],
            "compressed_exact": comparisons,
            "mechanical_fits": fits,
            "adjusted_pair_primitive": primitive,
            "passed": passed,
        }
        # This is the handoff gate: the receipt is complete before any caller
        # is permitted to draw or launch the registered public panel.
        _write_json(output / "mechanical-receipt.json", mechanical_receipt)
        receipt.update(
            {
                "status": "passed" if passed else "failed",
                "passed": passed,
                "bank_manifest": manifest,
                "mechanical_patterns": [
                    "all_zero",
                    "all_two",
                    "deterministic_modulo3",
                    "early_prey_late_predator",
                ],
                "mechanical_domain": [asdict(point) for point in domain_points()],
                "compressed_exact": comparisons,
                "mechanical_fits": fits,
                "adjusted_pair_primitive": primitive,
                "compressed_bank_sha256": _sha(output / "compressed-bank.npz"),
                "mechanical_receipt_sha256": _sha(output / "mechanical-receipt.json"),
                "elapsed_seconds": time.perf_counter() - started,
            }
        )
    except Exception as error:
        receipt.update(
            {
                "status": "failed",
                "passed": False,
                "error": f"{type(error).__name__}: {error}",
                "elapsed_seconds": time.perf_counter() - started,
            }
        )
        _write_json(output / "qualification.json", receipt)
        raise
    _write_json(output / "qualification.json", receipt)
    if not receipt["passed"]:
        raise QualificationFailure("mechanical qualification failed; receipt preserved")
    return receipt


run_qualification = qualify
run_public_panel = run_panel


__all__ = [
    "BANK_SIZE",
    "COARSE_BETA",
    "COARSE_H",
    "COARSE_MU",
    "COARSE_SD",
    "DomainPoint",
    "FitData",
    "QualificationFailure",
    "adjusted_pair_primitive",
    "bank_representations",
    "bank_stability_summary",
    "coarse_grid_audit",
    "compare_compressed_exact",
    "domain_points",
    "fit_loglikelihood",
    "fit_panel_task",
    "generate_public_panel",
    "holdout_perturbation_isolation",
    "load_panel_observations",
    "make_fit_data",
    "mechanical_domain",
    "mechanical_observations",
    "pre_loglikelihood",
    "qualify",
    "repeat_mechanical_fits",
    "run_panel",
    "run_public_panel",
    "run_qualification",
    "subset_bank",
    "subset_observations",
    "validate_bank_manifest",
]
