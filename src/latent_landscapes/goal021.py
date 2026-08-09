"""Central three-parameter positive-control benchmark."""

from __future__ import annotations

import csv
import json
import math
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import fmean, median

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from numpy.typing import NDArray

from latent_landscapes.goal002.calibration import (
    CutoffResult,
    EstimateInterval,
    order_statistic_cutoff,
    wilson_interval,
)
from latent_landscapes.goal004.likelihood import CATEGORY_COUNT, MLE_TOLERANCE, HistoryRecordLike
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal007.likelihood import joint_category_weights
from latent_landscapes.goal011 import benchmark as goal011
from latent_landscapes.goal019 import (
    PROBABILITY_GRID,
    RHO_GRID,
    parameter_detection_log_likelihoods,
)
from latent_landscapes.goal020 import ETA_GRID

TRUTH_RHO = 1.0
TRUTH_ETA = 1.0
TRUTH_PROBABILITY = 0.65
EXPECTED_FILES = (
    "replicate_results.csv",
    "summary.json",
    "review.md",
    "three_parameter_recovery.svg",
)


@dataclass(frozen=True, slots=True)
class Goal021Config:
    """Frozen central three-parameter campaign."""

    master_seed: int = goal011.MASTER_SEED
    bank_size: int = goal011.INTEGRATION_BANK_SIZE
    calibration_replicates: int = 250
    validation_replicates: int = 250
    calibration_rank_one_based: int = 239
    rhos: tuple[float, ...] = RHO_GRID
    etas: tuple[float, ...] = ETA_GRID
    probabilities: tuple[float, ...] = PROBABILITY_GRID

    def __post_init__(self) -> None:
        rho_values = np.asarray(self.rhos, dtype=np.float64)
        eta_values = np.asarray(self.etas, dtype=np.float64)
        p_values = np.asarray(self.probabilities, dtype=np.float64)
        if self.bank_size <= 0:
            raise ValueError("integration bank size must be positive")
        if self.calibration_replicates <= 0 or self.validation_replicates <= 0:
            raise ValueError("calibration and validation counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_replicates:
            raise ValueError("calibration rank must lie within calibration replicates")
        if (
            rho_values.ndim != 1
            or len(rho_values) == 0
            or not np.isfinite(rho_values).all()
            or (rho_values <= 0.0).any()
            or (np.diff(rho_values) <= 0.0).any()
        ):
            raise ValueError("rho grid must be finite, positive, and increasing")
        if (
            eta_values.ndim != 1
            or len(eta_values) == 0
            or not np.isfinite(eta_values).all()
            or (eta_values < 0.0).any()
            or (np.diff(eta_values) <= 0.0).any()
        ):
            raise ValueError("eta grid must be finite, nonnegative, and increasing")
        if (
            p_values.ndim != 1
            or len(p_values) == 0
            or not np.isfinite(p_values).all()
            or (p_values <= 0.0).any()
            or (p_values >= 1.0).any()
            or (np.diff(p_values) <= 0.0).any()
        ):
            raise ValueError("probability grid must be finite, interior, and increasing")
        if sum(value == TRUTH_RHO for value in self.rhos) != 1:
            raise ValueError("rho grid must contain generating rho = 1 exactly once")
        if sum(value == TRUTH_ETA for value in self.etas) != 1:
            raise ValueError("eta grid must contain generating eta = 1 exactly once")
        if sum(value == TRUTH_PROBABILITY for value in self.probabilities) != 1:
            raise ValueError("probability grid must contain generating p = 0.65 exactly once")

    @property
    def is_production(self) -> bool:
        return (
            self.bank_size == goal011.INTEGRATION_BANK_SIZE
            and self.calibration_replicates == 250
            and self.validation_replicates == 250
            and self.calibration_rank_one_based == 239
            and self.rhos == RHO_GRID
            and self.etas == ETA_GRID
            and self.probabilities == PROBABILITY_GRID
        )

    @property
    def goal011_config(self) -> goal011.Goal011Config:
        return goal011.Goal011Config(
            master_seed=self.master_seed,
            bank_size=self.bank_size,
            calibration_replicates=self.calibration_replicates,
            validation_replicates=self.validation_replicates,
            calibration_rank_one_based=self.calibration_rank_one_based,
        )


DEFAULT_CONFIG = Goal021Config()


def smoke_config() -> Goal021Config:
    """Return a reduced implementation check with no scientific meaning."""
    return Goal021Config(
        bank_size=8,
        calibration_replicates=4,
        validation_replicates=4,
        calibration_rank_one_based=4,
        rhos=(0.5, 1.0, 2.0),
        etas=(0.5, 1.0, 1.5),
        probabilities=(0.45, 0.65, 0.85),
    )


@dataclass(frozen=True, slots=True)
class ThreeParameterProfile:
    etas: NDArray[np.float64]
    rhos: NDArray[np.float64]
    probabilities: NDArray[np.float64]
    log_likelihoods: NDArray[np.float64]
    maximum_log_likelihood: float
    mle_indices: tuple[tuple[int, int, int], ...]
    mle_cells: tuple[tuple[float, float, float], ...]


@dataclass(frozen=True, slots=True)
class SupportSummary:
    truth_included: bool
    cell_count: int
    component_count: int
    boundary_contact: bool
    projected_log_rho_width: float
    projected_eta_width: float
    projected_probability_width: float
    minimum_log_rho_error: float
    minimum_eta_error: float
    minimum_probability_error: float
    rho_eta_correlation: float | None
    rho_probability_correlation: float | None
    eta_probability_correlation: float | None


@dataclass(frozen=True, slots=True)
class ReplicateResult:
    phase: str
    dataset_index: int
    record_count: int
    no_false_positives: bool
    lr_at_truth: float
    mle_cells: tuple[tuple[float, float, float], ...]
    minimum_log_rho_error: float
    minimum_eta_error: float
    minimum_probability_error: float
    truth_included: bool | None = None
    support_cell_count: int | None = None
    support_component_count: int | None = None
    support_boundary_contact: bool | None = None
    projected_log_rho_width: float | None = None
    projected_eta_width: float | None = None
    projected_probability_width: float | None = None
    rho_eta_correlation: float | None = None
    rho_probability_correlation: float | None = None
    eta_probability_correlation: float | None = None


@dataclass(frozen=True, slots=True)
class CampaignSummary:
    cutoff: CutoffResult
    validation_count: int
    coverage_success_count: int
    coverage: EstimateInterval
    connected_interior_count: int
    boundary_contact_count: int
    median_log_rho_error: float
    median_eta_error: float
    median_probability_error: float
    median_log_rho_width: float
    median_eta_width: float
    median_probability_width: float
    median_rho_eta_correlation: float | None
    rho_eta_correlation_count: int
    median_rho_probability_correlation: float | None
    rho_probability_correlation_count: int
    median_eta_probability_correlation: float | None
    eta_probability_correlation_count: int
    mean_log_rho_bias: float
    mean_eta_bias: float
    mean_probability_bias: float


@dataclass(frozen=True, slots=True)
class Goal021Result:
    config: Goal021Config
    replicate_results: tuple[ReplicateResult, ...]
    summary: CampaignSummary
    representative_profile: ThreeParameterProfile
    invariants: dict[str, bool]
    outcome: str


def three_parameter_profile(
    *,
    site_ids: tuple[str, ...],
    records: Sequence[HistoryRecordLike],
    category_weights: NDArray[np.float64],
    rhos: Sequence[float] | NDArray[np.float64],
    etas: Sequence[float] | NDArray[np.float64],
    probabilities: Sequence[float] | NDArray[np.float64],
) -> ThreeParameterProfile:
    """Profile rho, eta, and p jointly."""
    rho_values = np.asarray(tuple(rhos), dtype=np.float64)
    eta_values = np.asarray(tuple(etas), dtype=np.float64)
    weights = np.asarray(category_weights, dtype=np.float64)
    expected_shape = (len(eta_values), len(rho_values), len(site_ids), CATEGORY_COUNT)
    if weights.shape != expected_shape:
        raise ValueError("category weights have an invalid shape")
    flat_weights = weights.reshape(len(eta_values) * len(rho_values), len(site_ids), CATEGORY_COUNT)
    p_values, flat_log_likelihoods = parameter_detection_log_likelihoods(
        site_ids=site_ids,
        records=records,
        category_weights=flat_weights,
        probabilities=probabilities,
    )
    log_likelihoods = flat_log_likelihoods.reshape(len(eta_values), len(rho_values), len(p_values))
    maximum = float(log_likelihoods.max())
    mle_indices = tuple(
        (int(eta_index), int(rho_index), int(p_index))
        for eta_index, rho_index, p_index in np.argwhere(
            np.isclose(log_likelihoods, maximum, rtol=0.0, atol=MLE_TOLERANCE)
        )
    )
    return ThreeParameterProfile(
        etas=eta_values.copy(),
        rhos=rho_values.copy(),
        probabilities=p_values,
        log_likelihoods=log_likelihoods,
        maximum_log_likelihood=maximum,
        mle_indices=mle_indices,
        mle_cells=tuple(
            (
                float(rho_values[rho_index]),
                float(eta_values[eta_index]),
                float(p_values[p_index]),
            )
            for eta_index, rho_index, p_index in mle_indices
        ),
    )


def summarize_support(
    profile: ThreeParameterProfile,
    *,
    cutoff: float,
    truth_rho: float = TRUTH_RHO,
    truth_eta: float = TRUTH_ETA,
    truth_probability: float = TRUTH_PROBABILITY,
) -> SupportSummary:
    """Summarize a calibrated six-neighbour three-dimensional support."""
    if not math.isfinite(cutoff) or cutoff < 0.0:
        raise ValueError("support cutoff must be finite and nonnegative")
    if (
        not math.isfinite(truth_rho)
        or truth_rho <= 0.0
        or not math.isfinite(truth_eta)
        or not math.isfinite(truth_probability)
        or sum(value == truth_rho for value in profile.rhos) != 1
        or sum(value == truth_eta for value in profile.etas) != 1
        or sum(value == truth_probability for value in profile.probabilities) != 1
    ):
        raise ValueError("truth coordinates must be finite and occur once on the profile")
    statistic = 2.0 * (profile.maximum_log_likelihood - profile.log_likelihoods)
    support = tuple(
        (int(eta_index), int(rho_index), int(p_index))
        for eta_index, rho_index, p_index in np.argwhere(statistic <= cutoff)
    )
    if not support:
        raise ValueError("calibrated support must not be empty")
    eta_values = np.asarray([profile.etas[eta_index] for eta_index, _, _ in support])
    rho_values = np.asarray([profile.rhos[rho_index] for _, rho_index, _ in support])
    p_values = np.asarray([profile.probabilities[p_index] for _, _, p_index in support])
    log_rhos = np.log(rho_values)
    return SupportSummary(
        truth_included=any(
            profile.etas[eta_index] == truth_eta
            and profile.rhos[rho_index] == truth_rho
            and profile.probabilities[p_index] == truth_probability
            for eta_index, rho_index, p_index in support
        ),
        cell_count=len(support),
        component_count=_component_count(support),
        boundary_contact=any(
            eta_index in (0, len(profile.etas) - 1)
            or rho_index in (0, len(profile.rhos) - 1)
            or p_index in (0, len(profile.probabilities) - 1)
            for eta_index, rho_index, p_index in support
        ),
        projected_log_rho_width=float(log_rhos.max() - log_rhos.min()),
        projected_eta_width=float(eta_values.max() - eta_values.min()),
        projected_probability_width=float(p_values.max() - p_values.min()),
        minimum_log_rho_error=min(
            abs(math.log(rho / truth_rho)) for rho, _, _ in profile.mle_cells
        ),
        minimum_eta_error=min(abs(eta - truth_eta) for _, eta, _ in profile.mle_cells),
        minimum_probability_error=min(
            abs(probability - truth_probability) for _, _, probability in profile.mle_cells
        ),
        rho_eta_correlation=_correlation(log_rhos, eta_values),
        rho_probability_correlation=_correlation(log_rhos, p_values),
        eta_probability_correlation=_correlation(eta_values, p_values),
    )


def classify_outcome(
    *,
    invariants: dict[str, bool],
    connected_interior_count: int,
    validation_count: int,
    coverage: EstimateInterval,
    median_log_rho_error: float,
    median_eta_error: float,
    median_probability_error: float,
    median_log_rho_width: float,
    median_eta_width: float,
    median_probability_width: float,
) -> str:
    """Apply the prespecified full-joint progression rules."""
    if not invariants or not all(invariants.values()):
        return "implementation_blocked"
    if validation_count <= 0 or connected_interior_count < math.ceil(0.95 * validation_count):
        return "three_parameter_support_design_limited"
    if not coverage.lower <= 0.95 <= coverage.upper:
        return "three_parameter_calibration_not_ready"
    if any(
        _materially_exceeds(value, threshold)
        for value, threshold in (
            (median_log_rho_error, 0.10),
            (median_eta_error, 0.25),
            (median_probability_error, 0.05),
            (median_log_rho_width, 0.50),
            (median_eta_width, 0.75),
            (median_probability_width, 0.20),
        )
    ):
        return "three_parameter_recovery_imprecise"
    return "advance_to_cross_truth_three_parameter_benchmark"


def _materially_exceeds(value: float, threshold: float) -> bool:
    return value > threshold and not math.isclose(
        value,
        threshold,
        rel_tol=0.0,
        abs_tol=1e-12,
    )


def run_goal021(config: Goal021Config = DEFAULT_CONFIG) -> Goal021Result:
    """Run one calibrated central three-parameter campaign."""
    fixed = goal011.build_fixed_inputs()
    manifest = goal011.spawn_seed_manifest(config.goal011_config)
    bank = goal007.build_integration_bank(fixed, manifest.integration_bank, config.etas)
    rhos = np.asarray(config.rhos, dtype=np.float64)
    weights = joint_category_weights(bank.arrivals, rhos)
    truth_eta_index = config.etas.index(TRUTH_ETA)
    truth_rho_index = config.rhos.index(TRUTH_RHO)
    truth_p_index = config.probabilities.index(TRUTH_PROBABILITY)
    rows: list[ReplicateResult] = []
    calibration_statistics: list[float] = []
    all_record_counts_valid = True
    all_no_false_positives = True

    for seed in manifest.calibration:
        truth, records = goal011.generate_dataset(fixed, seed)
        profile = three_parameter_profile(
            site_ids=bank.site_ids,
            records=records,
            category_weights=weights,
            rhos=config.rhos,
            etas=config.etas,
            probabilities=config.probabilities,
        )
        statistic = _lr_at_truth(profile, truth_eta_index, truth_rho_index, truth_p_index)
        calibration_statistics.append(statistic)
        no_false_positives = goal011.no_false_positives(records, truth)
        all_record_counts_valid &= len(records) == 1920
        all_no_false_positives &= no_false_positives
        rows.append(
            _base_row("calibration", seed.index, records, profile, statistic, no_false_positives)
        )

    cutoff = order_statistic_cutoff(
        calibration_statistics,
        rank_one_based=config.calibration_rank_one_based,
    )
    representative: ThreeParameterProfile | None = None
    for seed in manifest.validation:
        truth, records = goal011.generate_dataset(fixed, seed)
        profile = three_parameter_profile(
            site_ids=bank.site_ids,
            records=records,
            category_weights=weights,
            rhos=config.rhos,
            etas=config.etas,
            probabilities=config.probabilities,
        )
        if representative is None:
            representative = profile
        statistic = _lr_at_truth(profile, truth_eta_index, truth_rho_index, truth_p_index)
        support = summarize_support(profile, cutoff=cutoff.cutoff)
        no_false_positives = goal011.no_false_positives(records, truth)
        all_record_counts_valid &= len(records) == 1920
        all_no_false_positives &= no_false_positives
        rows.append(
            replace(
                _base_row(
                    "validation", seed.index, records, profile, statistic, no_false_positives
                ),
                truth_included=support.truth_included,
                support_cell_count=support.cell_count,
                support_component_count=support.component_count,
                support_boundary_contact=support.boundary_contact,
                projected_log_rho_width=support.projected_log_rho_width,
                projected_eta_width=support.projected_eta_width,
                projected_probability_width=support.projected_probability_width,
                rho_eta_correlation=support.rho_eta_correlation,
                rho_probability_correlation=support.rho_probability_correlation,
                eta_probability_correlation=support.eta_probability_correlation,
            )
        )
    if representative is None:
        raise RuntimeError("validation produced no representative profile")

    validation_rows = [row for row in rows if row.phase == "validation"]
    summary = _campaign_summary(cutoff, validation_rows)
    fixed_invariants = {
        key: value
        for key, value in fixed.invariants.items()
        if key != "known_detection_probability"
    }
    invariants = {
        **fixed_invariants,
        "goal011_seed_replay": config.master_seed == goal011.MASTER_SEED,
        "all_three_parameters_estimated": True,
        "truth_rho_on_grid": config.rhos[truth_rho_index] == TRUTH_RHO,
        "truth_eta_on_grid": config.etas[truth_eta_index] == TRUTH_ETA,
        "truth_probability_on_grid": (config.probabilities[truth_p_index] == TRUTH_PROBABILITY),
        "integration_weights_valid": bool(
            weights.shape == (len(config.etas), len(config.rhos), 160, CATEGORY_COUNT)
            and np.isfinite(weights).all()
            and np.allclose(weights.sum(axis=-1), 1.0, rtol=0.0, atol=1e-12)
        ),
        "complete_record_counts": all_record_counts_valid,
        "zero_false_positives": all_no_false_positives,
        "phase_counts": (len(rows) == config.calibration_replicates + config.validation_replicates),
    }
    outcome = classify_outcome(
        invariants=invariants,
        connected_interior_count=summary.connected_interior_count,
        validation_count=summary.validation_count,
        coverage=summary.coverage,
        median_log_rho_error=summary.median_log_rho_error,
        median_eta_error=summary.median_eta_error,
        median_probability_error=summary.median_probability_error,
        median_log_rho_width=summary.median_log_rho_width,
        median_eta_width=summary.median_eta_width,
        median_probability_width=summary.median_probability_width,
    )
    if not config.is_production and outcome != "implementation_blocked":
        outcome = "non_scientific_smoke"
    return Goal021Result(
        config=config,
        replicate_results=tuple(rows),
        summary=summary,
        representative_profile=representative,
        invariants=invariants,
        outcome=outcome,
    )


def write_review_bundle(result: Goal021Result, output_dir: Path) -> tuple[Path, ...]:
    """Write the compact four-file human review surface."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        raise ValueError("output directory must be empty")
    _write_replicates(target / "replicate_results.csv", result.replicate_results)
    (target / "summary.json").write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "review.md").write_text(_review(result), encoding="utf-8")
    _save_figure(target / "three_parameter_recovery.svg", _review_figure(result))
    written = tuple(target / name for name in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 021 review surface is incomplete")
    return written


def _component_count(indices: tuple[tuple[int, int, int], ...]) -> int:
    remaining = set(indices)
    components = 0
    while remaining:
        components += 1
        queue = deque([remaining.pop()])
        while queue:
            first, second, third = queue.popleft()
            for neighbour in (
                (first - 1, second, third),
                (first + 1, second, third),
                (first, second - 1, third),
                (first, second + 1, third),
                (first, second, third - 1),
                (first, second, third + 1),
            ):
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    queue.append(neighbour)
    return components


def _correlation(first: NDArray[np.float64], second: NDArray[np.float64]) -> float | None:
    if len(first) <= 1 or np.ptp(first) == 0.0 or np.ptp(second) == 0.0:
        return None
    return float(np.corrcoef(first, second)[0, 1])


def _base_row(
    phase: str,
    dataset_index: int,
    records: Sequence[HistoryRecordLike],
    profile: ThreeParameterProfile,
    statistic: float,
    no_false_positives: bool,
) -> ReplicateResult:
    return ReplicateResult(
        phase=phase,
        dataset_index=dataset_index,
        record_count=len(records),
        no_false_positives=no_false_positives,
        lr_at_truth=statistic,
        mle_cells=profile.mle_cells,
        minimum_log_rho_error=min(
            abs(math.log(rho / TRUTH_RHO)) for rho, _, _ in profile.mle_cells
        ),
        minimum_eta_error=min(abs(eta - TRUTH_ETA) for _, eta, _ in profile.mle_cells),
        minimum_probability_error=min(
            abs(probability - TRUTH_PROBABILITY) for _, _, probability in profile.mle_cells
        ),
    )


def _lr_at_truth(
    profile: ThreeParameterProfile,
    eta_index: int,
    rho_index: int,
    probability_index: int,
) -> float:
    return float(
        2.0
        * (
            profile.maximum_log_likelihood
            - profile.log_likelihoods[eta_index, rho_index, probability_index]
        )
    )


def _campaign_summary(
    cutoff: CutoffResult,
    rows: list[ReplicateResult],
) -> CampaignSummary:
    if not rows or any(row.truth_included is None for row in rows):
        raise ValueError("validation rows must contain support summaries")
    coverage_count = sum(row.truth_included is True for row in rows)
    rho_eta = [row.rho_eta_correlation for row in rows if row.rho_eta_correlation is not None]
    rho_p = [
        row.rho_probability_correlation
        for row in rows
        if row.rho_probability_correlation is not None
    ]
    eta_p = [
        row.eta_probability_correlation
        for row in rows
        if row.eta_probability_correlation is not None
    ]
    return CampaignSummary(
        cutoff=cutoff,
        validation_count=len(rows),
        coverage_success_count=coverage_count,
        coverage=wilson_interval(coverage_count, len(rows)),
        connected_interior_count=sum(
            row.support_component_count == 1 and row.support_boundary_contact is False
            for row in rows
        ),
        boundary_contact_count=sum(row.support_boundary_contact is True for row in rows),
        median_log_rho_error=median(row.minimum_log_rho_error for row in rows),
        median_eta_error=median(row.minimum_eta_error for row in rows),
        median_probability_error=median(row.minimum_probability_error for row in rows),
        median_log_rho_width=median(_required_float(row.projected_log_rho_width) for row in rows),
        median_eta_width=median(_required_float(row.projected_eta_width) for row in rows),
        median_probability_width=median(
            _required_float(row.projected_probability_width) for row in rows
        ),
        median_rho_eta_correlation=median(rho_eta) if rho_eta else None,
        rho_eta_correlation_count=len(rho_eta),
        median_rho_probability_correlation=median(rho_p) if rho_p else None,
        rho_probability_correlation_count=len(rho_p),
        median_eta_probability_correlation=median(eta_p) if eta_p else None,
        eta_probability_correlation_count=len(eta_p),
        mean_log_rho_bias=fmean(
            fmean(math.log(rho / TRUTH_RHO) for rho, _, _ in row.mle_cells) for row in rows
        ),
        mean_eta_bias=fmean(fmean(eta - TRUTH_ETA for _, eta, _ in row.mle_cells) for row in rows),
        mean_probability_bias=fmean(
            fmean(probability - TRUTH_PROBABILITY for _, _, probability in row.mle_cells)
            for row in rows
        ),
    )


def _required_float(value: float | None) -> float:
    if value is None:
        raise ValueError("validation support metric is missing")
    return value


def _write_replicates(path: Path, rows: tuple[ReplicateResult, ...]) -> None:
    fields = tuple(ReplicateResult.__dataclass_fields__)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            payload = {field: getattr(row, field) for field in fields}
            payload["mle_cells"] = json.dumps(row.mle_cells, separators=(",", ":"))
            writer.writerow(payload)


def _summary_payload(result: Goal021Result) -> dict[str, object]:
    summary = result.summary
    return {
        "goal": "021-central-three-parameter-positive-control",
        "run_mode": "production" if result.config.is_production else "reduced_smoke",
        "scientific_interpretation": result.outcome,
        "outcome": result.outcome,
        "truth": {"rho": TRUTH_RHO, "eta": TRUTH_ETA, "p": TRUTH_PROBABILITY},
        "bank_size": result.config.bank_size,
        "rho_grid_size": len(result.config.rhos),
        "eta_grid_size": len(result.config.etas),
        "probability_grid_size": len(result.config.probabilities),
        "calibration_replicates": result.config.calibration_replicates,
        "validation_replicates": result.config.validation_replicates,
        "cutoff": summary.cutoff.cutoff,
        "coverage_count": summary.coverage_success_count,
        "coverage": summary.coverage.estimate,
        "coverage_interval": [summary.coverage.lower, summary.coverage.upper],
        "connected_interior_count": summary.connected_interior_count,
        "boundary_contact_count": summary.boundary_contact_count,
        "median_log_rho_error": summary.median_log_rho_error,
        "median_eta_error": summary.median_eta_error,
        "median_probability_error": summary.median_probability_error,
        "median_log_rho_width": summary.median_log_rho_width,
        "median_eta_width": summary.median_eta_width,
        "median_probability_width": summary.median_probability_width,
        "support_correlations": {
            "rho_eta": [summary.median_rho_eta_correlation, summary.rho_eta_correlation_count],
            "rho_probability": [
                summary.median_rho_probability_correlation,
                summary.rho_probability_correlation_count,
            ],
            "eta_probability": [
                summary.median_eta_probability_correlation,
                summary.eta_probability_correlation_count,
            ],
        },
        "mean_log_rho_bias": summary.mean_log_rho_bias,
        "mean_eta_bias": summary.mean_eta_bias,
        "mean_probability_bias": summary.mean_probability_bias,
        "invariants": result.invariants,
    }


def _review(result: Goal021Result) -> str:
    if not result.config.is_production:
        return (
            "# Goal 021: Central Three-Parameter Positive Control\n\n"
            "This reduced smoke is an implementation check only and has no scientific meaning.\n"
        )
    summary = result.summary
    return "\n".join(
        [
            "# Goal 021: Central Three-Parameter Positive Control",
            "",
            f"Outcome: `{result.outcome}`.",
            "",
            (
                f"Joint validation coverage was {summary.coverage_success_count}/"
                f"{summary.validation_count} ({summary.coverage.estimate:.3f}; 95% Wilson "
                f"interval {summary.coverage.lower:.3f}-{summary.coverage.upper:.3f})."
            ),
            (
                f"Median absolute errors were {summary.median_log_rho_error:.3f} in log-rho, "
                f"{summary.median_eta_error:.3f} in eta, and "
                f"{summary.median_probability_error:.3f} in p."
            ),
            (
                f"Median projected widths were {summary.median_log_rho_width:.3f}, "
                f"{summary.median_eta_width:.3f}, and "
                f"{summary.median_probability_width:.3f}, respectively."
            ),
            (
                f"{summary.connected_interior_count}/{summary.validation_count} supports were "
                "connected and interior. Correlation counts and medians are retained in "
                "summary.json."
            ),
            "",
            (
                "This is a single central-truth synthetic positive control. It does not "
                "establish cross-truth robustness."
            ),
            "",
        ]
    )


def _review_figure(result: Goal021Result) -> Figure:
    validation = [row for row in result.replicate_results if row.phase == "validation"]
    rho_estimates = np.asarray([fmean(cell[0] for cell in row.mle_cells) for row in validation])
    eta_estimates = np.asarray([fmean(cell[1] for cell in row.mle_cells) for row in validation])
    p_estimates = np.asarray([fmean(cell[2] for cell in row.mle_cells) for row in validation])
    figure, axes = plt.subplots(2, 3, figsize=(13.0, 7.2), constrained_layout=True)
    _histogram(axes[0, 0], np.log2(rho_estimates), 0.0, "log2 spread rate", "rho = 1")
    _histogram(axes[0, 1], eta_estimates, TRUTH_ETA, "resistance contrast", "eta = 1")
    _histogram(axes[0, 2], p_estimates, TRUTH_PROBABILITY, "detection probability", "p = 0.65")

    profile = result.representative_profile
    statistic = 2.0 * (profile.maximum_log_likelihood - profile.log_likelihoods)
    cutoff = result.summary.cutoff.cutoff
    ceiling = max(8.0, 1.5 * cutoff)
    eta_truth = int(np.flatnonzero(profile.etas == TRUTH_ETA)[0])
    rho_truth = int(np.flatnonzero(profile.rhos == TRUTH_RHO)[0])
    p_truth = int(np.flatnonzero(profile.probabilities == TRUTH_PROBABILITY)[0])
    _contour(
        axes[1, 0],
        np.log2(profile.rhos),
        profile.etas,
        statistic[:, :, p_truth],
        cutoff,
        ceiling,
        "log2 spread rate",
        "Resistance contrast",
        (0.0, TRUTH_ETA),
        "At generating p",
    )
    _contour(
        axes[1, 1],
        np.log2(profile.rhos),
        profile.probabilities,
        statistic[eta_truth, :, :].T,
        cutoff,
        ceiling,
        "log2 spread rate",
        "Detection probability",
        (0.0, TRUTH_PROBABILITY),
        "At generating eta",
    )
    filled = _contour(
        axes[1, 2],
        profile.etas,
        profile.probabilities,
        statistic[:, rho_truth, :].T,
        cutoff,
        ceiling,
        "Resistance contrast",
        "Detection probability",
        (TRUTH_ETA, TRUTH_PROBABILITY),
        "At generating rho",
    )
    figure.colorbar(filled, ax=axes[1, :].tolist(), label="Likelihood-ratio distance")
    return figure


def _histogram(
    axis: Axes, values: NDArray[np.float64], truth: float, label: str, truth_label: str
) -> None:
    padding = max(0.03, 0.12 * float(np.ptp(values)))
    limits = (float(values.min()) - padding, float(values.max()) + padding)
    axis.hist(values, bins=np.linspace(*limits, 14).tolist(), color="#3B6FB6")
    axis.axvline(truth, color="#C44E52", linestyle="--", label=f"Generating {truth_label}")
    axis.set(xlabel=f"Estimated {label}", ylabel="Validation histories", xlim=limits)
    axis.legend(frameon=False)


def _contour(
    axis: Axes,
    x_values: NDArray[np.float64],
    y_values: NDArray[np.float64],
    statistic: NDArray[np.float64],
    cutoff: float,
    ceiling: float,
    x_label: str,
    y_label: str,
    truth: tuple[float, float],
    title: str,
) -> mpl.contour.QuadContourSet:
    active = np.argwhere(statistic <= ceiling)
    if len(active):
        y_start = max(0, int(active[:, 0].min()) - 2)
        y_stop = min(len(y_values), int(active[:, 0].max()) + 3)
        x_start = max(0, int(active[:, 1].min()) - 2)
        x_stop = min(len(x_values), int(active[:, 1].max()) + 3)
    else:
        y_start, y_stop, x_start, x_stop = 0, len(y_values), 0, len(x_values)
    local = statistic[y_start:y_stop, x_start:x_stop]
    x, y = np.meshgrid(x_values[x_start:x_stop], y_values[y_start:y_stop])
    filled = axis.contourf(
        x,
        y,
        np.minimum(local, ceiling),
        levels=np.linspace(0.0, ceiling, 15),
        cmap="viridis_r",
    )
    if float(local.min()) <= cutoff <= float(local.max()):
        axis.contour(x, y, local, levels=[cutoff], colors=["#C44E52"])
    axis.scatter([truth[0]], [truth[1]], marker="x", s=70, color="white")
    axis.set(xlabel=x_label, ylabel=y_label)
    axis.set_title(title)
    return filled


def _save_figure(path: Path, figure: Figure) -> None:
    figure.savefig(path, format="svg", metadata={"Date": None})
    plt.close(figure)
