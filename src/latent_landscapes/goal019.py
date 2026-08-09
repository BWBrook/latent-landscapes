"""Joint spread-rate and detection-probability positive control."""

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
from matplotlib.figure import Figure
from numpy.typing import NDArray

from latent_landscapes.goal002.calibration import (
    CutoffResult,
    EstimateInterval,
    order_statistic_cutoff,
    wilson_interval,
)
from latent_landscapes.goal004.likelihood import (
    CATEGORY_COUNT,
    MLE_TOLERANCE,
    HistoryRecordLike,
    category_weights,
)
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal011 import benchmark as goal011
from latent_landscapes.goal018 import history_exponents

TRUTH_RHO = 1.0
TRUTH_ETA = 1.0
TRUTH_PROBABILITY = 0.65
RHO_GRID = tuple(2.0 ** (-2.0 + 4.0 * index / 100.0) for index in range(101))
PROBABILITY_GRID = tuple(round(0.05 + 0.02 * index, 2) for index in range(46))
EXPECTED_FILES = (
    "replicate_results.csv",
    "summary.json",
    "review.md",
    "spread_detection_recovery.svg",
)


@dataclass(frozen=True, slots=True)
class Goal019Config:
    """Frozen joint positive-control campaign."""

    master_seed: int = goal011.MASTER_SEED
    bank_size: int = goal011.INTEGRATION_BANK_SIZE
    calibration_replicates: int = 250
    validation_replicates: int = 250
    calibration_rank_one_based: int = 239
    rhos: tuple[float, ...] = RHO_GRID
    probabilities: tuple[float, ...] = PROBABILITY_GRID

    def __post_init__(self) -> None:
        rho_values = np.asarray(self.rhos, dtype=np.float64)
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


DEFAULT_CONFIG = Goal019Config()


def smoke_config() -> Goal019Config:
    """Return a reduced implementation check with no scientific meaning."""
    return Goal019Config(
        bank_size=8,
        calibration_replicates=4,
        validation_replicates=4,
        calibration_rank_one_based=4,
        rhos=(0.5, 1.0, 2.0),
        probabilities=(0.45, 0.65, 0.85),
    )


@dataclass(frozen=True, slots=True)
class SpreadDetectionProfile:
    rhos: NDArray[np.float64]
    probabilities: NDArray[np.float64]
    log_likelihoods: NDArray[np.float64]
    maximum_log_likelihood: float
    mle_indices: tuple[tuple[int, int], ...]
    mle_cells: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class SupportSummary:
    truth_included: bool
    cell_count: int
    component_count: int
    boundary_contact: bool
    projected_log_rho_width: float
    projected_probability_width: float
    minimum_log_rho_error: float
    minimum_probability_error: float
    correlation: float | None


@dataclass(frozen=True, slots=True)
class ReplicateResult:
    phase: str
    dataset_index: int
    record_count: int
    no_false_positives: bool
    lr_at_truth: float
    mle_cells: tuple[tuple[float, float], ...]
    minimum_log_rho_error: float
    minimum_probability_error: float
    truth_included: bool | None = None
    support_cell_count: int | None = None
    support_component_count: int | None = None
    support_boundary_contact: bool | None = None
    projected_log_rho_width: float | None = None
    projected_probability_width: float | None = None
    support_correlation: float | None = None


@dataclass(frozen=True, slots=True)
class CampaignSummary:
    cutoff: CutoffResult
    validation_count: int
    coverage_success_count: int
    coverage: EstimateInterval
    connected_interior_count: int
    boundary_contact_count: int
    median_log_rho_error: float
    median_probability_error: float
    median_log_rho_width: float
    median_probability_width: float
    median_support_correlation: float | None
    mean_log_rho_bias: float
    mean_probability_bias: float


@dataclass(frozen=True, slots=True)
class Goal019Result:
    config: Goal019Config
    replicate_results: tuple[ReplicateResult, ...]
    summary: CampaignSummary
    representative_profile: SpreadDetectionProfile
    invariants: dict[str, bool]
    outcome: str


def spread_detection_profile(
    *,
    site_ids: tuple[str, ...],
    records: Sequence[HistoryRecordLike],
    category_weights: NDArray[np.float64],
    rhos: Sequence[float] | NDArray[np.float64],
    probabilities: Sequence[float] | NDArray[np.float64],
) -> SpreadDetectionProfile:
    """Profile rho and p jointly while resistance remains fixed."""
    weights = np.asarray(category_weights, dtype=np.float64)
    rho_values = np.asarray(tuple(rhos), dtype=np.float64)
    expected_shape = (len(rho_values), len(site_ids), CATEGORY_COUNT)
    if weights.shape != expected_shape:
        raise ValueError("category weights have an invalid shape")
    p_values, log_likelihoods = parameter_detection_log_likelihoods(
        site_ids=site_ids,
        records=records,
        category_weights=weights,
        probabilities=probabilities,
    )
    maximum = float(log_likelihoods.max())
    mle_indices = tuple(
        (int(rho_index), int(p_index))
        for rho_index, p_index in np.argwhere(
            np.isclose(log_likelihoods, maximum, rtol=0.0, atol=MLE_TOLERANCE)
        )
    )
    return SpreadDetectionProfile(
        rhos=rho_values.copy(),
        probabilities=p_values.copy(),
        log_likelihoods=log_likelihoods,
        maximum_log_likelihood=maximum,
        mle_indices=mle_indices,
        mle_cells=tuple(
            (float(rho_values[rho_index]), float(p_values[p_index]))
            for rho_index, p_index in mle_indices
        ),
    )


def parameter_detection_log_likelihoods(
    *,
    site_ids: tuple[str, ...],
    records: Sequence[HistoryRecordLike],
    category_weights: NDArray[np.float64],
    probabilities: Sequence[float] | NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Calculate a generic parameter-by-detection complete-history surface."""
    weights = np.asarray(category_weights, dtype=np.float64)
    p_values = np.asarray(tuple(probabilities), dtype=np.float64)
    if weights.ndim != 3 or weights.shape[1:] != (len(site_ids), CATEGORY_COUNT):
        raise ValueError("category weights have an invalid shape")
    if (
        p_values.ndim != 1
        or len(p_values) == 0
        or not np.isfinite(p_values).all()
        or (p_values <= 0.0).any()
        or (p_values >= 1.0).any()
        or (np.diff(p_values) <= 0.0).any()
    ):
        raise ValueError("probability grid must be finite, interior, and increasing")
    if (
        not np.isfinite(weights).all()
        or (weights <= 0.0).any()
        or not np.allclose(weights.sum(axis=-1), 1.0, rtol=0.0, atol=1e-12)
    ):
        raise ValueError("category weights must be positive finite probabilities")
    selected, detections, nondetections, valid = history_exponents(site_ids, records)
    site_index = {site_id: index for index, site_id in enumerate(site_ids)}
    selected_weights = weights[:, [site_index[site_id] for site_id in selected], :]
    p = p_values[:, None, None]
    histories = np.where(
        valid[None, :, :],
        np.power(p, detections[None, :, :]) * np.power(1.0 - p, nondetections[None, :, :]),
        0.0,
    )
    site_probabilities = np.einsum("rsc,psc->rps", selected_weights, histories, optimize=True)
    if not np.isfinite(site_probabilities).all() or (site_probabilities <= 0.0).any():
        raise ValueError("site-history probabilities must be finite and positive")
    log_likelihoods = np.log(site_probabilities).sum(axis=2)
    return p_values.copy(), log_likelihoods


def summarize_support(
    profile: SpreadDetectionProfile,
    *,
    cutoff: float,
) -> SupportSummary:
    """Summarize a calibrated support on the rho-by-p grid."""
    if not math.isfinite(cutoff) or cutoff < 0.0:
        raise ValueError("support cutoff must be finite and nonnegative")
    statistics = 2.0 * (profile.maximum_log_likelihood - profile.log_likelihoods)
    support = tuple(
        (int(rho_index), int(p_index)) for rho_index, p_index in np.argwhere(statistics <= cutoff)
    )
    if not support:
        raise ValueError("calibrated support must not be empty")
    rho_values = np.asarray([profile.rhos[rho_index] for rho_index, _ in support])
    p_values = np.asarray([profile.probabilities[p_index] for _, p_index in support])
    log_rhos = np.log(rho_values)
    correlation = None
    if len(support) > 1 and np.ptp(log_rhos) > 0.0 and np.ptp(p_values) > 0.0:
        correlation = float(np.corrcoef(log_rhos, p_values)[0, 1])
    return SupportSummary(
        truth_included=any(
            profile.rhos[rho_index] == TRUTH_RHO
            and profile.probabilities[p_index] == TRUTH_PROBABILITY
            for rho_index, p_index in support
        ),
        cell_count=len(support),
        component_count=rook_component_count(support),
        boundary_contact=any(
            rho_index in (0, len(profile.rhos) - 1)
            or p_index in (0, len(profile.probabilities) - 1)
            for rho_index, p_index in support
        ),
        projected_log_rho_width=float(log_rhos.max() - log_rhos.min()),
        projected_probability_width=float(p_values.max() - p_values.min()),
        minimum_log_rho_error=min(abs(math.log(rho / TRUTH_RHO)) for rho, _ in profile.mle_cells),
        minimum_probability_error=min(
            abs(probability - TRUTH_PROBABILITY) for _, probability in profile.mle_cells
        ),
        correlation=correlation,
    )


def classify_outcome(
    *,
    invariants: dict[str, bool],
    connected_interior_count: int,
    validation_count: int,
    coverage: EstimateInterval,
    median_log_rho_error: float,
    median_probability_error: float,
    median_log_rho_width: float,
    median_probability_width: float,
) -> str:
    """Apply the prespecified joint positive-control progression rules."""
    if not invariants or not all(invariants.values()):
        return "implementation_blocked"
    if validation_count <= 0 or connected_interior_count < math.ceil(0.95 * validation_count):
        return "spread_detection_support_design_limited"
    if not coverage.lower <= 0.95 <= coverage.upper:
        return "spread_detection_calibration_not_ready"
    if (
        median_log_rho_error > 0.10
        or median_probability_error > 0.05
        or median_log_rho_width > 0.50
        or median_probability_width > 0.20
    ):
        return "spread_detection_recovery_imprecise"
    return "advance_to_resistance_detection_pair"


def run_goal019(config: Goal019Config = DEFAULT_CONFIG) -> Goal019Result:
    """Run one calibrated joint spread-detection campaign."""
    fixed = goal011.build_fixed_inputs()
    manifest = goal011.spawn_seed_manifest(config.goal011_config)
    bank = goal007.build_integration_bank(fixed, manifest.integration_bank, (TRUTH_ETA,))
    rhos = np.asarray(config.rhos, dtype=np.float64)
    weights = category_weights(bank.arrivals[:, 0, :], rhos)
    truth_rho_index = config.rhos.index(TRUTH_RHO)
    truth_p_index = config.probabilities.index(TRUTH_PROBABILITY)
    rows: list[ReplicateResult] = []
    calibration_statistics: list[float] = []
    all_record_counts_valid = True
    all_no_false_positives = True

    for seed in manifest.calibration:
        truth, records = goal011.generate_dataset(fixed, seed)
        profile = spread_detection_profile(
            site_ids=bank.site_ids,
            records=records,
            category_weights=weights,
            rhos=config.rhos,
            probabilities=config.probabilities,
        )
        statistic = _lr_at_truth(profile, truth_rho_index, truth_p_index)
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
    representative: SpreadDetectionProfile | None = None
    for seed in manifest.validation:
        truth, records = goal011.generate_dataset(fixed, seed)
        profile = spread_detection_profile(
            site_ids=bank.site_ids,
            records=records,
            category_weights=weights,
            rhos=config.rhos,
            probabilities=config.probabilities,
        )
        if representative is None:
            representative = profile
        statistic = _lr_at_truth(profile, truth_rho_index, truth_p_index)
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
                projected_probability_width=support.projected_probability_width,
                support_correlation=support.correlation,
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
        "known_resistance_truth": True,
        "detection_probability_estimated": True,
        "truth_rho_on_grid": config.rhos[truth_rho_index] == TRUTH_RHO,
        "truth_probability_on_grid": (config.probabilities[truth_p_index] == TRUTH_PROBABILITY),
        "integration_weights_valid": bool(
            weights.shape == (len(config.rhos), 160, CATEGORY_COUNT)
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
        median_probability_error=summary.median_probability_error,
        median_log_rho_width=summary.median_log_rho_width,
        median_probability_width=summary.median_probability_width,
    )
    if not config.is_production and outcome != "implementation_blocked":
        outcome = "non_scientific_smoke"
    return Goal019Result(
        config=config,
        replicate_results=tuple(rows),
        summary=summary,
        representative_profile=representative,
        invariants=invariants,
        outcome=outcome,
    )


def write_review_bundle(result: Goal019Result, output_dir: Path) -> tuple[Path, ...]:
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
    _save_figure(target / "spread_detection_recovery.svg", _review_figure(result))
    written = tuple(target / name for name in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 019 review surface is incomplete")
    return written


def rook_component_count(indices: tuple[tuple[int, int], ...]) -> int:
    remaining = set(indices)
    components = 0
    while remaining:
        components += 1
        queue = deque([remaining.pop()])
        while queue:
            row, column = queue.popleft()
            for neighbour in (
                (row - 1, column),
                (row + 1, column),
                (row, column - 1),
                (row, column + 1),
            ):
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    queue.append(neighbour)
    return components


def _base_row(
    phase: str,
    dataset_index: int,
    records: Sequence[HistoryRecordLike],
    profile: SpreadDetectionProfile,
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
        minimum_log_rho_error=min(abs(math.log(rho / TRUTH_RHO)) for rho, _ in profile.mle_cells),
        minimum_probability_error=min(
            abs(probability - TRUTH_PROBABILITY) for _, probability in profile.mle_cells
        ),
    )


def _lr_at_truth(
    profile: SpreadDetectionProfile,
    rho_index: int,
    probability_index: int,
) -> float:
    return float(
        2.0
        * (profile.maximum_log_likelihood - profile.log_likelihoods[rho_index, probability_index])
    )


def _campaign_summary(
    cutoff: CutoffResult,
    rows: list[ReplicateResult],
) -> CampaignSummary:
    if not rows or any(row.truth_included is None for row in rows):
        raise ValueError("validation rows must contain support summaries")
    coverage_count = sum(row.truth_included is True for row in rows)
    correlations = [row.support_correlation for row in rows if row.support_correlation is not None]
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
        median_probability_error=median(row.minimum_probability_error for row in rows),
        median_log_rho_width=median(_required_float(row.projected_log_rho_width) for row in rows),
        median_probability_width=median(
            _required_float(row.projected_probability_width) for row in rows
        ),
        median_support_correlation=median(correlations) if correlations else None,
        mean_log_rho_bias=fmean(
            fmean(math.log(rho / TRUTH_RHO) for rho, _ in row.mle_cells) for row in rows
        ),
        mean_probability_bias=fmean(
            fmean(probability - TRUTH_PROBABILITY for _, probability in row.mle_cells)
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


def _summary_payload(result: Goal019Result) -> dict[str, object]:
    summary = result.summary
    return {
        "goal": "019-joint-spread-detection-positive-control",
        "run_mode": "production" if result.config.is_production else "reduced_smoke",
        "scientific_interpretation": result.outcome,
        "outcome": result.outcome,
        "truth": {"rho": TRUTH_RHO, "eta": TRUTH_ETA, "p": TRUTH_PROBABILITY},
        "bank_size": result.config.bank_size,
        "rho_grid_size": len(result.config.rhos),
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
        "median_probability_error": summary.median_probability_error,
        "median_log_rho_width": summary.median_log_rho_width,
        "median_probability_width": summary.median_probability_width,
        "median_support_correlation": summary.median_support_correlation,
        "mean_log_rho_bias": summary.mean_log_rho_bias,
        "mean_probability_bias": summary.mean_probability_bias,
        "invariants": result.invariants,
    }


def _review(result: Goal019Result) -> str:
    if not result.config.is_production:
        return (
            "# Goal 019: Joint Spread-Detection Positive Control\n\n"
            "This reduced smoke is an implementation check only and has no scientific meaning.\n"
        )
    summary = result.summary
    ridge = (
        "not defined"
        if summary.median_support_correlation is None
        else f"{summary.median_support_correlation:.3f}"
    )
    return "\n".join(
        [
            "# Goal 019: Joint Spread-Detection Positive Control",
            "",
            f"Outcome: `{result.outcome}`.",
            "",
            (
                f"Joint validation coverage was {summary.coverage_success_count}/"
                f"{summary.validation_count} ({summary.coverage.estimate:.3f}; 95% Wilson "
                f"interval {summary.coverage.lower:.3f}-{summary.coverage.upper:.3f})."
            ),
            (
                f"Median absolute errors were {summary.median_log_rho_error:.3f} in log-rho "
                f"and {summary.median_probability_error:.3f} in p. Median projected widths "
                f"were {summary.median_log_rho_width:.3f} and "
                f"{summary.median_probability_width:.3f}, respectively."
            ),
            (
                f"{summary.connected_interior_count}/{summary.validation_count} supports were "
                f"connected and interior; median support correlation was {ridge}."
            ),
            "",
            (
                "Resistance was fixed at its generating value. This benchmark asks only "
                "whether spread speed can be separated from missed detections."
            ),
            "",
        ]
    )


def _review_figure(result: Goal019Result) -> Figure:
    validation = [row for row in result.replicate_results if row.phase == "validation"]
    rho_estimates = [fmean(cell[0] for cell in row.mle_cells) for row in validation]
    p_estimates = [fmean(cell[1] for cell in row.mle_cells) for row in validation]
    log_rho_estimates = np.log2(rho_estimates)
    profile = result.representative_profile
    statistic = 2.0 * (profile.maximum_log_likelihood - profile.log_likelihoods)
    cutoff = result.summary.cutoff.cutoff
    figure, axes = plt.subplots(2, 2, figsize=(10.0, 7.2), constrained_layout=True)

    rho_padding = max(0.04, 0.12 * float(np.ptp(log_rho_estimates)))
    rho_limits = (
        float(np.min(log_rho_estimates)) - rho_padding,
        float(np.max(log_rho_estimates)) + rho_padding,
    )
    axes[0, 0].hist(log_rho_estimates, bins=np.linspace(*rho_limits, 16), color="#3B6FB6")
    axes[0, 0].axvline(0.0, color="#C44E52", linestyle="--", label="Generating rho = 1")
    axes[0, 0].set(
        xlabel="Estimated log2 spread rate",
        ylabel="Validation histories",
        xlim=rho_limits,
    )
    axes[0, 0].set_title("Spread-rate estimates")
    axes[0, 0].legend(frameon=False)

    p_padding = max(0.02, 0.12 * float(np.ptp(p_estimates)))
    p_limits = (
        float(np.min(p_estimates)) - p_padding,
        float(np.max(p_estimates)) + p_padding,
    )
    axes[0, 1].hist(p_estimates, bins=np.linspace(*p_limits, 14), color="#2A9D8F")
    axes[0, 1].axvline(
        TRUTH_PROBABILITY,
        color="#C44E52",
        linestyle="--",
        label="Generating p = 0.65",
    )
    axes[0, 1].set(
        xlabel="Estimated detection probability",
        ylabel="Validation histories",
        xlim=p_limits,
    )
    axes[0, 1].set_title("Detection-probability estimates")
    axes[0, 1].legend(frameon=False)

    axes[1, 0].scatter(log_rho_estimates, p_estimates, s=12, alpha=0.55, color="#3B6FB6")
    axes[1, 0].scatter([0.0], [TRUTH_PROBABILITY], marker="x", s=80, color="#C44E52")
    axes[1, 0].set(
        xlabel="Estimated log2 spread rate",
        ylabel="Estimated detection probability",
        xlim=rho_limits,
        ylim=p_limits,
    )
    axes[1, 0].set_title("Joint validation estimates")

    ceiling = max(8.0, 1.5 * cutoff)
    active = np.argwhere(statistic <= ceiling)
    rho_start = max(0, int(active[:, 0].min()) - 2)
    rho_stop = min(len(profile.rhos), int(active[:, 0].max()) + 3)
    p_start = max(0, int(active[:, 1].min()) - 2)
    p_stop = min(len(profile.probabilities), int(active[:, 1].max()) + 3)
    local_statistic = statistic[rho_start:rho_stop, p_start:p_stop]
    x, y = np.meshgrid(
        np.log2(profile.rhos[rho_start:rho_stop]),
        profile.probabilities[p_start:p_stop],
    )
    filled = axes[1, 1].contourf(
        x,
        y,
        np.minimum(local_statistic.T, ceiling),
        levels=np.linspace(0.0, ceiling, 15),
        cmap="viridis_r",
    )
    if float(local_statistic.min()) <= cutoff <= float(local_statistic.max()):
        axes[1, 1].contour(x, y, local_statistic.T, levels=[cutoff], colors=["#C44E52"])
    axes[1, 1].scatter([0.0], [TRUTH_PROBABILITY], marker="x", s=80, color="white")
    axes[1, 1].set(xlabel="log2 spread rate", ylabel="Detection probability")
    axes[1, 1].set_title("Prespecified validation profile 0")
    figure.colorbar(filled, ax=axes[1, 1], label="Likelihood-ratio distance")
    return figure


def _save_figure(path: Path, figure: Figure) -> None:
    figure.savefig(path, format="svg", metadata={"Date": None})
    plt.close(figure)
