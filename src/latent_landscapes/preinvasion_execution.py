"""Bounded qualification and execution of the open Goal 056 development panel."""

from __future__ import annotations

import itertools
import json
import math
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import adjusted_background_likelihood as adjusted
from latent_landscapes import known_nuisance_calibration as legacy
from latent_landscapes import preinvasion_calibration as calibration
from latent_landscapes import preinvasion_campaign as campaign
from latent_landscapes import preinvasion_fitting as fitting
from latent_landscapes import preinvasion_likelihood as likelihood

FloatArray = NDArray[np.float64]
REGISTRATION = "docs/goals/056-observed-nuisance-feasibility/registration-2026-10-03.md"
COARSE_H = np.asarray([1.0, 1.5, 3.0, 6.0, 10.0])
COARSE_BETA = np.asarray([-2.0, -1.0, 0.0, 0.6, 1.0, 2.0])


def jsonable(value: Any) -> Any:
    """Keep unavailable diagnostics explicit while writing strict JSON."""
    if isinstance(value, np.ndarray):
        return jsonable(value.tolist())
    if isinstance(value, np.generic):
        return jsonable(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [jsonable(item) for item in value]
    return value


def source_hashes(repository: Path) -> dict[str, str]:
    files = sorted((repository / "src").rglob("*.py"))
    files += sorted((repository / "tests").glob("test_preinvasion*.py"))
    files += [
        repository / item
        for item in (
            "scripts/run_preinvasion_feasibility.py",
            "pyproject.toml",
            "uv.lock",
            REGISTRATION,
            "docs/goals/056-observed-nuisance-feasibility/methods-review.md",
        )
    ]
    return {str(path.relative_to(repository)): campaign.file_sha256(path) for path in files}


def subset_bank(
    bank: likelihood.CompressedBank, mask: NDArray[np.bool_]
) -> likelihood.CompressedBank:
    indices = np.flatnonzero(mask)
    return replace(
        bank,
        site_ids=tuple(bank.site_ids[i] for i in indices),
        category_counts=bank.category_counts[indices],
        category_mass=bank.category_mass[indices],
        power_moments=bank.power_moments[indices],
        bank_arrivals=bank.bank_arrivals[:, indices],
        bank_checksum=bank.bank_checksum + ":sites:" + ",".join(str(i) for i in indices),
    )


def subset_observations(
    observed: likelihood.PreInvasionObservations,
    mask: NDArray[np.bool_],
    *,
    history: int | None = None,
) -> likelihood.PreInvasionObservations:
    selected = slice(None) if history is None else slice(history, history + 1)
    return likelihood.prepare_observations(
        observed.prey_counts[selected][:, mask],
        observed.predator_counts[selected][:, mask],
        tuple(np.asarray(observed.site_ids)[mask]),
        np.ones(int(mask.sum()), dtype=bool),
        initial_alive=observed.initial_alive[mask],
        prey_times=observed.prey_times,
        predator_times=observed.predator_times,
        cohort_start=observed.cohort_start,
        predator_observed=(
            None
            if observed.predator_observed is None
            else observed.predator_observed[selected][:, mask]
        ),
        prey_observed=(
            None if observed.prey_observed is None else observed.prey_observed[selected][:, mask]
        ),
    )


@dataclass(frozen=True)
class FitData:
    observations: likelihood.PreInvasionObservations
    bank: likelihood.CompressedBank
    map_a: FloatArray
    site_a: FloatArray


def fit_loglikelihood(
    data: FitData, *, h: float, beta: float, mu: float, detection_sd: float
) -> float:
    return likelihood.point_score(
        data.observations,
        data.bank,
        h,
        beta,
        mu,
        data.map_a,
        data.site_a,
        detection_sd=detection_sd,
    ).training_logjoint


def pre_loglikelihood(data: FitData, *, beta: float, mu: float, detection_sd: float) -> float:
    hazards = adjusted.normalized_hazards(beta, data.map_a, data.site_a, mu)
    score = likelihood.pre_only_log_likelihood(
        data.observations, hazards, detection_sd=detection_sd, return_site=False
    )
    return float(np.asarray(score).reshape(-1)[0])


def _save_compressed(path: Path, bank: likelihood.CompressedBank) -> None:
    np.savez_compressed(
        path,
        site_ids=np.asarray(bank.site_ids),
        bank_size=bank.bank_size,
        category_counts=bank.category_counts,
        category_mass=bank.category_mass,
        power_moments=bank.power_moments,
        bank_checksum=bank.bank_checksum,
        series_order=bank.series_order,
        max_x=bank.max_x,
    )


def _load_compressed(path: Path, bank_path: Path) -> likelihood.CompressedBank:
    with np.load(path, allow_pickle=False) as saved:
        return likelihood.CompressedBank(
            tuple(str(item) for item in saved["site_ids"]),
            int(saved["bank_size"]),
            saved["category_counts"],
            saved["category_mass"],
            saved["power_moments"],
            np.load(bank_path, mmap_mode="r", allow_pickle=False),
            str(saved["bank_checksum"]),
            int(saved["series_order"]),
            float(saved["max_x"]),
        )


def qualify(repository: Path, bank_directory: Path, output: Path) -> dict[str, Any]:
    """Use four mechanical count patterns, never the registered panel outcomes."""
    if output.exists():
        raise FileExistsError("preserve earlier qualification attempts")
    output.mkdir(parents=True)
    started = time.perf_counter()
    fixed, setup = campaign.public_inputs()
    del fixed
    order = np.argsort(np.asarray(setup.site_ids), kind="stable")
    ids = tuple(np.asarray(setup.site_ids)[order])
    site_a = setup.exposure_score[setup.site_rows, setup.site_cols][order]
    training = np.asarray(setup.site_splits)[order] == "training"
    if int(training.sum()) != 120:
        raise ValueError("public training split changed")
    bank_started = time.perf_counter()
    raw, bank_receipt = legacy.load_verified_bank(
        bank_directory, legacy.production_config("timing"), ids
    )
    bank = likelihood.compress_bank(raw, ids)
    bank_seconds = time.perf_counter() - bank_started
    _save_compressed(output / "compressed-bank.npz", bank)
    certificate = campaign.hazard_box_certificate(setup.exposure_score, site_a)
    prey = np.zeros((4, len(ids), 13), dtype=np.int64)
    predator = np.zeros((4, len(ids), 6), dtype=np.int64)
    prey[1] = 2
    predator[1] = 2
    prey[2] = (np.arange(len(ids))[:, None] + np.arange(13)[None, :]) % 3
    predator[2] = (np.arange(len(ids))[:, None] + np.arange(6)[None, :]) % 3
    prey[3, :, :7] = 2
    predator[3, :, 3:] = 1
    observed = likelihood.prepare_observations(prey, predator, ids, training)
    points = list(itertools.product((1.0, 10.0), (-2.0, 2.0), (0.0005, 0.006), (0.0, 0.4)))
    points += [(3.0, 0.6, 0.0016, 0.2)]
    comparisons = []
    for h, beta, mu, sd in points:
        hazards = adjusted.normalized_hazards(beta, setup.exposure_score, site_a, mu)
        compressed = likelihood.build_integration(bank, (h,), hazards)
        exact = likelihood.build_integration(bank, (h,), hazards, exact=True)
        fast_score = likelihood.score_observations(observed, compressed, detection_sd=sd)
        exact_score = likelihood.score_observations(observed, exact, detection_sd=sd)
        errors = {
            "site_logjoint": float(
                np.max(np.abs(fast_score.joint_loglikelihood - exact_score.joint_loglikelihood))
            ),
            "training_logjoint": float(
                np.max(np.abs(fast_score.training_logjoint - exact_score.training_logjoint))
            ),
            "holdout_logjoint": float(
                np.max(np.abs(fast_score.holdout_logjoint - exact_score.holdout_logjoint))
            ),
        }
        comparisons.append({"h": h, "beta": beta, "mu": mu, "detection_sd": sd, **errors})
    training_data = FitData(
        subset_observations(observed, training, history=2),
        subset_bank(bank, training),
        setup.exposure_score,
        site_a[training],
    )
    point_started = time.perf_counter()
    for _ in range(50):
        fit_loglikelihood(training_data, h=3, beta=0.6, mu=0.0016, detection_sd=0.2)
    point_seconds = (time.perf_counter() - point_started) / 50
    pre_started = time.perf_counter()
    for _ in range(50):
        pre_loglikelihood(training_data, beta=0.6, mu=0.0016, detection_sd=0.2)
    pre_seconds = (time.perf_counter() - pre_started) / 50
    mechanical_fits = []
    for history in range(4):
        data = replace(
            training_data, observations=subset_observations(observed, training, history=history)
        )
        first = fitting.paired_fit(data, fit_loglikelihood)
        second = fitting.paired_fit(data, fit_loglikelihood)
        differences = {
            name: second.fits[name].raw_logjoint - fit.raw_logjoint
            for name, fit in first.fits.items()
        }
        fit_passed = all(
            fit.converged
            and second.fits[name].converged
            and math.isfinite(differences[name])
            and abs(differences[name]) <= 1e-8
            for name, fit in first.fits.items()
        )
        mechanical_fits.append(
            {
                "history": history,
                "passed": fit_passed,
                "first": asdict(first),
                "second": asdict(second),
                "repeat_logjoint_differences": differences,
            }
        )
    passed = bool(
        certificate["passes"]
        and all(row["passed"] for row in mechanical_fits)
        and all(
            max(row[key] for key in ("site_logjoint", "training_logjoint", "holdout_logjoint"))
            <= 1e-8
            for row in comparisons
        )
    )
    receipt = {
        "passed": passed,
        "created_utc": datetime.now(UTC).isoformat(),
        "source_hashes": source_hashes(repository),
        "bank_receipt": bank_receipt,
        "compressed_bank_sha256": campaign.file_sha256(output / "compressed-bank.npz"),
        "hazard_box_certificate": certificate,
        "full_bank_comparisons": comparisons,
        "mechanical_fits": jsonable(mechanical_fits),
        "bank_load_and_compress_seconds": bank_seconds,
        "scalar_point_seconds": point_seconds,
        "scalar_pre_only_seconds": pre_seconds,
        "elapsed_seconds": time.perf_counter() - started,
        "mechanical_patterns": [
            "all_zero",
            "all_two",
            "deterministic_modulo3",
            "early_prey_late_predator",
        ],
    }
    campaign.write_json(output / "qualification.json", receipt)
    return receipt


def coarse_grid_audit(data: FitData) -> dict[str, Any]:
    """A deterministic likelihood lower bound, never an optimizer warm start."""
    history_count = len(data.observations.prey_counts)
    maxima = {
        model: np.full(history_count, -np.inf)
        for model in ("constant_free_h", "adjusted_free_h", "constant_h1", "adjusted_h1")
    }
    best: dict[str, list[Any]] = {model: [None] * history_count for model in maxima}
    started = time.perf_counter()
    for beta, mu in itertools.product(COARSE_BETA, calibration.MU_GRID):
        hazards = adjusted.normalized_hazards(float(beta), data.map_a, data.site_a, mu)
        integrated = likelihood.build_integration(data.bank, tuple(COARSE_H), hazards)
        for sd in calibration.DETECTION_SD_GRID:
            score = likelihood.score_observations(data.observations, integrated, detection_sd=sd)
            values = score.training_logjoint
            for model in maxima:
                if model.startswith("constant") and beta != 0:
                    continue
                hi = (
                    np.argmax(values, axis=1)
                    if model.endswith("free_h")
                    else np.zeros(history_count, int)
                )
                proposed = values[np.arange(history_count), hi]
                improved = proposed > maxima[model]
                for index in np.flatnonzero(improved):
                    best[model][index] = {
                        "h": float(COARSE_H[hi[index]]),
                        "beta": float(beta),
                        "mu": mu,
                        "detection_sd": sd,
                    }
                maxima[model] = np.maximum(maxima[model], proposed)
    return cast(
        dict[str, Any],
        jsonable(
            {
                "max_logjoint": maxima,
                "parameters": best,
                "grid": {
                    "h": COARSE_H,
                    "beta": COARSE_BETA,
                    "mu": calibration.MU_GRID,
                    "detection_sd": calibration.DETECTION_SD_GRID,
                },
                "elapsed_seconds": time.perf_counter() - started,
                "diagnostic_only": True,
            }
        ),
    )


_WORKER_DATA: tuple[FitData, FitData] | None = None


def _worker_initialize(panel: str, compressed: str, bank_path: str) -> None:
    global _WORKER_DATA
    bank = _load_compressed(Path(compressed), Path(bank_path))
    with np.load(Path(panel) / "observations.npz", allow_pickle=False) as values:
        training = values["site_splits"] == "training"
        observed = likelihood.prepare_observations(
            values["prey_counts"], values["predator_counts"], values["site_ids"], training
        )
        order = np.argsort(values["site_ids"], kind="stable")
        site_a = values["site_a"][order]
        map_a = values["map_a"]
    training = observed.training_mask
    _WORKER_DATA = tuple(
        FitData(subset_observations(observed, mask), subset_bank(bank, mask), map_a, site_a[mask])
        for mask in (training, ~training)
    )  # type: ignore[assignment]


def _fit_cell(index: int, output: str) -> dict[str, Any]:
    if _WORKER_DATA is None:
        raise RuntimeError("worker was not initialized")
    started = time.perf_counter()
    full_train, full_holdout = _WORKER_DATA
    train = replace(
        full_train,
        observations=subset_observations(
            full_train.observations, np.ones(len(full_train.site_a), bool), history=index
        ),
    )
    holdout = replace(
        full_holdout,
        observations=subset_observations(
            full_holdout.observations, np.ones(len(full_holdout.site_a), bool), history=index
        ),
    )
    paired = fitting.paired_fit(train, fit_loglikelihood)
    pre = fitting.fit_pre_only_nuisance(train, pre_loglikelihood)
    # Persist main fits before expensive diagnostics; a timeout preserves them.
    result: dict[str, Any] = {"index": index, "paired": asdict(paired), "pre_only": asdict(pre)}
    campaign.write_json(Path(output) / f"cell-{index:02d}-main.json", jsonable(result))
    profiles = {
        "constant_h": fitting.profile_h(train, fit_loglikelihood, paired.fits["constant_free_h"]),
        "adjusted_h": fitting.profile_h(train, fit_loglikelihood, paired.fits["adjusted_free_h"]),
        "adjusted_beta": fitting.profile_beta(
            train, fit_loglikelihood, paired.fits["adjusted_free_h"]
        ),
    }
    heldout_scores = {}
    replays = {}
    for name, fit in paired.fits.items():
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
        conditional = scored.conditional_prey_site_loglikelihood[0]
        heldout_scores[name] = {
            "conditional_prey_total_nats": float(conditional.sum()),
            "conditional_prey_nats_per_site": float(conditional.mean()),
            "conditional_prey_site_nats": conditional,
        }
        replays[name] = fit_loglikelihood(train, **fit.parameters) - fit.raw_logjoint
    result.update(
        {
            "profiles": {name: asdict(profile) for name, profile in profiles.items()},
            "holdout_scores": heldout_scores,
            "main_replay_logjoint_differences": replays,
            "elapsed_seconds": time.perf_counter() - started,
        }
    )
    encoded = jsonable(result)
    campaign.write_json(Path(output) / f"cell-{index:02d}.json", encoded)
    return {
        "index": index,
        "elapsed_seconds": result["elapsed_seconds"],
        "main_seconds": paired.cost.main_seconds,
    }


def run_panel(
    repository: Path, qualification: Path, output: Path, *, workers: int = 16
) -> dict[str, Any]:
    if not 1 <= workers <= 16:
        raise ValueError("registered worker cap is 16")
    if output.exists():
        raise FileExistsError("preserve completed or failed panel attempts")
    qualified = json.loads((qualification / "qualification.json").read_text())
    if not qualified["passed"] or qualified["source_hashes"] != source_hashes(repository):
        raise ValueError("current source is not the qualified frozen source")
    compressed = qualification / "compressed-bank.npz"
    if campaign.file_sha256(compressed) != qualified["compressed_bank_sha256"]:
        raise ValueError("compressed bank changed after qualification")
    if (
        campaign.file_sha256(Path(qualified["bank_receipt"]["bank_path"]))
        != qualified["bank_receipt"]["bank_file_sha256"]
    ):
        raise ValueError("raw bank changed after qualification")
    output.mkdir(parents=True)
    started = time.perf_counter()
    campaign.write_json(
        output / "started.json",
        {
            "created_utc": datetime.now(UTC).isoformat(),
            "source_hashes": source_hashes(repository),
            "qualification_sha256": campaign.file_sha256(qualification / "qualification.json"),
            "workers": workers,
        },
    )
    panel = output / "panel"
    generator_started = time.perf_counter()
    campaign.generate_panel(panel)
    generation_seconds = time.perf_counter() - generator_started
    results_directory = output / "results"
    results_directory.mkdir()
    bank_path = qualified["bank_receipt"]["bank_path"]
    completed = []
    with ProcessPoolExecutor(
        max_workers=workers,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=_worker_initialize,
        initargs=(str(panel), str(compressed), bank_path),
    ) as pool:
        futures = [pool.submit(_fit_cell, index, str(results_directory)) for index in range(16)]
        for future in as_completed(futures):
            row = future.result()
            completed.append(row)
            print(json.dumps({"cell_complete": row}), flush=True)
    # All diagnostic-grid scores use only training arrays. No grid result modifies a main fit.
    _worker_initialize(str(panel), str(compressed), bank_path)
    if _WORKER_DATA is None:
        raise RuntimeError("coarse grid data missing")
    grid = coarse_grid_audit(_WORKER_DATA[0])
    campaign.write_json(output / "coarse-grid-audit.json", grid)
    audits = []
    profile_models = {
        "constant_h": "constant_free_h",
        "adjusted_h": "adjusted_free_h",
        "adjusted_beta": "adjusted_free_h",
    }
    for index in range(16):
        cell = json.loads((results_directory / f"cell-{index:02d}.json").read_text())
        for name, fit in cell["paired"]["fits"].items():
            main = fit["raw_logjoint"]
            grid_gap = None if main is None else grid["max_logjoint"][name][index] - main
            profile_gaps = {}
            profile_failed_nodes = {}
            for profile_name, model in profile_models.items():
                if model != name:
                    continue
                profile = cell["profiles"][profile_name]
                qualified_values = [
                    value
                    for value, status in zip(profile["values"], profile["statuses"], strict=True)
                    if value is not None and status == "converged"
                ]
                profile_gaps[profile_name] = (
                    max(qualified_values) - main if qualified_values and main is not None else None
                )
                profile_failed_nodes[profile_name] = sum(
                    status != "converged" for status in profile["statuses"]
                )
            passed = (
                fit["numerical_status"] == "converged"
                and grid_gap is not None
                and grid_gap <= 1e-6
                and all(gap is not None and gap <= 1e-6 for gap in profile_gaps.values())
            )
            audits.append(
                {
                    "index": index,
                    "model": name,
                    "passed": passed,
                    "grid_minus_main_logjoint": grid_gap,
                    "profile_minus_main_logjoint": profile_gaps,
                    "profile_failed_nodes": profile_failed_nodes,
                    "main_replay_difference": cell["main_replay_logjoint_differences"][name],
                }
            )
    end_hashes = source_hashes(repository)
    audit = {
        "passed": all(row["passed"] for row in audits),
        "rows": audits,
        "source_unchanged": end_hashes == qualified["source_hashes"],
        "loglikelihood_gap_tolerance": 1e-6,
    }
    campaign.write_json(output / "numerical-audit.json", audit)
    files = sorted(path for path in output.rglob("*") if path.is_file())
    receipt = {
        "status": (
            "panel_completed_pending_scientific_audit"
            if audit["passed"] and audit["source_unchanged"]
            else "panel_completed_with_numerical_failure"
        ),
        "created_utc": datetime.now(UTC).isoformat(),
        "histories": 16,
        "workers": workers,
        "generation_seconds": generation_seconds,
        "cell_times": sorted(completed, key=lambda row: row["index"]),
        "elapsed_seconds": time.perf_counter() - started,
        "files": {str(path.relative_to(output)): campaign.file_sha256(path) for path in files},
        "source_hashes": end_hashes,
    }
    campaign.write_json(output / "completed.json", receipt)
    return receipt
