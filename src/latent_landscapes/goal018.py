"""Detection-probability positive control with known spread parameters."""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from itertools import pairwise
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
from latent_landscapes.goal004.observations import (
    DETECTION_PROBABILITY,
    REPLICATES,
    SURVEY_TIMES,
)
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal011 import benchmark as goal011

TRUTH_PROBABILITY = DETECTION_PROBABILITY
PROBABILITY_GRID = tuple(round(0.05 + 0.01 * index, 2) for index in range(91))
EXPECTED_FILES = (
    "replicate_results.csv",
    "summary.json",
    "review.md",
    "detection_recovery.svg",
)


@dataclass(frozen=True, slots=True)
class Goal018Config:
    """Frozen positive-control campaign size and candidate grid."""

    master_seed: int = goal011.MASTER_SEED
    bank_size: int = goal011.INTEGRATION_BANK_SIZE
    calibration_replicates: int = goal011.CALIBRATION_REPLICATES
    validation_replicates: int = goal011.VALIDATION_REPLICATES
    calibration_rank_one_based: int = goal011.CALIBRATION_RANK_ONE_BASED
    probabilities: tuple[float, ...] = PROBABILITY_GRID

    def __post_init__(self) -> None:
        if self.bank_size <= 0:
            raise ValueError("integration bank size must be positive")
        if self.calibration_replicates <= 0 or self.validation_replicates <= 0:
            raise ValueError("calibration and validation counts must be positive")
        if not 1 <= self.calibration_rank_one_based <= self.calibration_replicates:
            raise ValueError("calibration rank must lie within calibration replicates")
        values = np.asarray(self.probabilities, dtype=np.float64)
        if (
            values.ndim != 1
            or len(values) == 0
            or not np.isfinite(values).all()
            or (values <= 0.0).any()
            or (values >= 1.0).any()
            or (np.diff(values) <= 0.0).any()
        ):
            raise ValueError("probability grid must be finite, interior, and increasing")
        if sum(value == TRUTH_PROBABILITY for value in self.probabilities) != 1:
            raise ValueError("probability grid must contain generating p = 0.65 exactly once")

    @property
    def is_production(self) -> bool:
        return self == Goal018Config()

    @property
    def goal011_config(self) -> goal011.Goal011Config:
        return goal011.Goal011Config(
            master_seed=self.master_seed,
            bank_size=self.bank_size,
            calibration_replicates=self.calibration_replicates,
            validation_replicates=self.validation_replicates,
            calibration_rank_one_based=self.calibration_rank_one_based,
        )


DEFAULT_CONFIG = Goal018Config()


def smoke_config() -> Goal018Config:
    """Return a reduced implementation check with no scientific meaning."""
    return Goal018Config(
        bank_size=8,
        calibration_replicates=4,
        validation_replicates=4,
        calibration_rank_one_based=4,
    )


@dataclass(frozen=True, slots=True)
class DetectionProfile:
    probabilities: NDArray[np.float64]
    log_likelihoods: NDArray[np.float64]
    maximum_log_likelihood: float
    mle_indices: tuple[int, ...]
    mle_probabilities: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class ReplicateResult:
    phase: str
    dataset_index: int
    record_count: int
    no_false_positives: bool
    lr_at_truth: float
    mle_probabilities: tuple[float, ...]
    minimum_absolute_error: float
    truth_included: bool | None = None
    support_component_count: int | None = None
    support_boundary_contact: bool | None = None
    support_lower: float | None = None
    support_upper: float | None = None
    support_width: float | None = None


@dataclass(frozen=True, slots=True)
class CampaignSummary:
    cutoff: CutoffResult
    validation_count: int
    coverage_success_count: int
    coverage: EstimateInterval
    connected_interior_count: int
    boundary_contact_count: int
    median_absolute_error: float
    median_support_width: float
    mean_mle_bias: float


@dataclass(frozen=True, slots=True)
class Goal018Result:
    config: Goal018Config
    replicate_results: tuple[ReplicateResult, ...]
    summary: CampaignSummary
    representative_profile: DetectionProfile
    invariants: dict[str, bool]
    outcome: str


def detection_profile(
    *,
    site_ids: tuple[str, ...],
    records: Sequence[HistoryRecordLike],
    category_weights: NDArray[np.float64],
    probabilities: Sequence[float],
) -> DetectionProfile:
    """Profile detection probability while process-category weights remain fixed."""
    weights = np.asarray(category_weights, dtype=np.float64)
    candidates = np.asarray(tuple(probabilities), dtype=np.float64)
    if weights.shape != (len(site_ids), CATEGORY_COUNT):
        raise ValueError("category weights have an invalid shape")
    if (
        not np.isfinite(weights).all()
        or (weights <= 0.0).any()
        or not np.allclose(weights.sum(axis=1), 1.0, rtol=0.0, atol=1e-12)
    ):
        raise ValueError("category weights must be positive finite probabilities")
    if (
        candidates.ndim != 1
        or len(candidates) == 0
        or not np.isfinite(candidates).all()
        or (candidates <= 0.0).any()
        or (candidates >= 1.0).any()
        or (np.diff(candidates) <= 0.0).any()
    ):
        raise ValueError("candidate probabilities must be interior and increasing")
    selected, detections, nondetections, valid = _history_exponents(site_ids, records)
    site_index = {site_id: index for index, site_id in enumerate(site_ids)}
    selected_weights = weights[[site_index[site_id] for site_id in selected]]
    p = candidates[:, None, None]
    histories = np.where(
        valid[None, :, :],
        np.power(p, detections[None, :, :]) * np.power(1.0 - p, nondetections[None, :, :]),
        0.0,
    )
    site_probabilities = np.einsum("sc,psc->ps", selected_weights, histories, optimize=True)
    if not np.isfinite(site_probabilities).all() or (site_probabilities <= 0.0).any():
        raise ValueError("site-history probabilities must be finite and positive")
    log_likelihoods = np.log(site_probabilities).sum(axis=1)
    maximum = float(log_likelihoods.max())
    mle_indices = tuple(
        int(index)
        for index in np.flatnonzero(
            np.isclose(log_likelihoods, maximum, rtol=0.0, atol=MLE_TOLERANCE)
        )
    )
    return DetectionProfile(
        probabilities=candidates.copy(),
        log_likelihoods=log_likelihoods,
        maximum_log_likelihood=maximum,
        mle_indices=mle_indices,
        mle_probabilities=tuple(float(candidates[index]) for index in mle_indices),
    )


def classify_outcome(
    *,
    invariants: dict[str, bool],
    connected_interior_count: int,
    validation_count: int,
    coverage: EstimateInterval,
    median_absolute_error: float,
    median_support_width: float,
) -> str:
    """Apply the prespecified detection-only progression rules."""
    if not invariants or not all(invariants.values()):
        return "implementation_blocked"
    if validation_count <= 0 or connected_interior_count < math.ceil(0.95 * validation_count):
        return "detection_support_design_limited"
    if not coverage.lower <= 0.95 <= coverage.upper:
        return "detection_calibration_not_ready"
    if median_absolute_error > 0.05 or median_support_width > 0.20:
        return "detection_parameter_imprecise"
    return "advance_to_joint_unknown_detection"


def run_goal018(config: Goal018Config = DEFAULT_CONFIG) -> Goal018Result:
    """Run one detection-only calibration and validation campaign."""
    fixed = goal011.build_fixed_inputs()
    manifest = goal011.spawn_seed_manifest(config.goal011_config)
    bank = goal007.build_integration_bank(fixed, manifest.integration_bank, (1.0,))
    weights = category_weights(
        bank.arrivals[:, 0, :],
        np.asarray([1.0], dtype=np.float64),
    )[0]
    probabilities = np.asarray(config.probabilities, dtype=np.float64)
    truth_index = config.probabilities.index(TRUTH_PROBABILITY)

    rows: list[ReplicateResult] = []
    calibration_statistics: list[float] = []
    all_record_counts_valid = True
    all_no_false_positives = True
    for seed in manifest.calibration:
        truth, records = goal011.generate_dataset(fixed, seed)
        profile = detection_profile(
            site_ids=bank.site_ids,
            records=records,
            category_weights=weights,
            probabilities=config.probabilities,
        )
        statistic = _lr_at_truth(profile, truth_index)
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
    representative: DetectionProfile | None = None
    for seed in manifest.validation:
        truth, records = goal011.generate_dataset(fixed, seed)
        profile = detection_profile(
            site_ids=bank.site_ids,
            records=records,
            category_weights=weights,
            probabilities=config.probabilities,
        )
        if representative is None:
            representative = profile
        statistic = _lr_at_truth(profile, truth_index)
        support = _support(profile, cutoff.cutoff, truth_index)
        no_false_positives = goal011.no_false_positives(records, truth)
        all_record_counts_valid &= len(records) == 1920
        all_no_false_positives &= no_false_positives
        rows.append(
            replace(
                _base_row(
                    "validation", seed.index, records, profile, statistic, no_false_positives
                ),
                truth_included=support[0],
                support_component_count=support[1],
                support_boundary_contact=support[2],
                support_lower=support[3],
                support_upper=support[4],
                support_width=support[5],
            )
        )
    if representative is None:
        raise RuntimeError("validation produced no representative profile")

    validation_rows = [row for row in rows if row.phase == "validation"]
    summary = _campaign_summary(cutoff, validation_rows)
    invariants = {
        **fixed.invariants,
        "goal011_seed_replay": config.master_seed == goal011.MASTER_SEED,
        "known_process_truth": True,
        "truth_probability_on_grid": bool(probabilities[truth_index] == TRUTH_PROBABILITY),
        "integration_weights_valid": bool(
            weights.shape == (160, CATEGORY_COUNT)
            and np.isfinite(weights).all()
            and np.allclose(weights.sum(axis=1), 1.0, rtol=0.0, atol=1e-12)
        ),
        "complete_record_counts": all_record_counts_valid,
        "zero_false_positives": all_no_false_positives,
        "phase_counts": (len(rows) == config.calibration_replicates + config.validation_replicates),
    }
    scientific_outcome = classify_outcome(
        invariants=invariants,
        connected_interior_count=summary.connected_interior_count,
        validation_count=summary.validation_count,
        coverage=summary.coverage,
        median_absolute_error=summary.median_absolute_error,
        median_support_width=summary.median_support_width,
    )
    return Goal018Result(
        config=config,
        replicate_results=tuple(rows),
        summary=summary,
        representative_profile=representative,
        invariants=invariants,
        outcome=scientific_outcome if config.is_production else "non_scientific_smoke",
    )


def write_review_bundle(result: Goal018Result, output_dir: Path) -> tuple[Path, ...]:
    """Write the four-file Goal 018 human review surface."""
    if not all(result.invariants.values()):
        raise ValueError("cannot write review artifacts for failed invariants")
    target = Path(output_dir)
    if target.exists() and any(target.iterdir()):
        raise RuntimeError("refusing to overwrite a nonempty output directory")
    target.mkdir(parents=True, exist_ok=True)
    _write_replicates(target / "replicate_results.csv", result.replicate_results)
    (target / "summary.json").write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / "review.md").write_text(_review(result), encoding="utf-8")
    _save_figure(target / "detection_recovery.svg", _review_figure(result))
    written = tuple(target / name for name in EXPECTED_FILES)
    if not all(path.is_file() and path.stat().st_size > 0 for path in written):
        raise RuntimeError("Goal 018 review surface is incomplete")
    return written


def _history_exponents(
    site_ids: tuple[str, ...],
    records: Sequence[HistoryRecordLike],
) -> tuple[tuple[str, ...], NDArray[np.int64], NDArray[np.int64], NDArray[np.bool_]]:
    if not records or len(set(site_ids)) != len(site_ids):
        raise ValueError("site identifiers must be unique and records nonempty")
    expected = {(time, replicate) for time in SURVEY_TIMES for replicate in REPLICATES}
    histories: dict[str, dict[tuple[int, int], int]] = {}
    for record in records:
        if record.site_id not in site_ids or record.detected not in (0, 1):
            raise ValueError("record has an unknown site or nonbinary detection")
        key = (record.time, record.replicate)
        if key not in expected:
            raise ValueError("record has an unknown survey time or replicate")
        site_history = histories.setdefault(record.site_id, {})
        if key in site_history:
            raise ValueError("site history contains a duplicate record")
        site_history[key] = record.detected
    selected = tuple(site_id for site_id in site_ids if site_id in histories)
    if any(set(histories[site_id]) != expected for site_id in selected):
        raise ValueError("each observed site must have a complete history")

    detections = np.zeros((len(selected), CATEGORY_COUNT), dtype=np.int64)
    nondetections = np.zeros_like(detections)
    valid = np.ones((len(selected), CATEGORY_COUNT), dtype=np.bool_)
    for site_index, site_id in enumerate(selected):
        for survey_index, time in enumerate(SURVEY_TIMES):
            for replicate in REPLICATES:
                detected = histories[site_id][(time, replicate)]
                for category in range(CATEGORY_COUNT):
                    if category <= survey_index:
                        if detected:
                            detections[site_index, category] += 1
                        else:
                            nondetections[site_index, category] += 1
                    elif detected:
                        valid[site_index, category] = False
    return selected, detections, nondetections, valid


def _base_row(
    phase: str,
    dataset_index: int,
    records: Sequence[HistoryRecordLike],
    profile: DetectionProfile,
    statistic: float,
    no_false_positives: bool,
) -> ReplicateResult:
    return ReplicateResult(
        phase=phase,
        dataset_index=dataset_index,
        record_count=len(records),
        no_false_positives=no_false_positives,
        lr_at_truth=statistic,
        mle_probabilities=profile.mle_probabilities,
        minimum_absolute_error=min(
            abs(value - TRUTH_PROBABILITY) for value in profile.mle_probabilities
        ),
    )


def _lr_at_truth(profile: DetectionProfile, truth_index: int) -> float:
    return max(
        0.0,
        2.0 * (profile.maximum_log_likelihood - float(profile.log_likelihoods[truth_index])),
    )


def _support(
    profile: DetectionProfile,
    cutoff: float,
    truth_index: int,
) -> tuple[bool, int, bool, float, float, float]:
    statistics = 2.0 * (profile.maximum_log_likelihood - profile.log_likelihoods)
    indices = tuple(int(index) for index in np.flatnonzero(statistics <= cutoff))
    if not indices:
        raise ValueError("calibrated support must not be empty")
    components = 1 + sum(right != left + 1 for left, right in pairwise(indices))
    width = sum(
        float(profile.probabilities[end] - profile.probabilities[start])
        for start, end in _component_bounds(indices)
    )
    return (
        truth_index in indices,
        components,
        indices[0] == 0 or indices[-1] == len(profile.probabilities) - 1,
        float(profile.probabilities[indices[0]]),
        float(profile.probabilities[indices[-1]]),
        width,
    )


def _component_bounds(indices: tuple[int, ...]) -> tuple[tuple[int, int], ...]:
    bounds: list[tuple[int, int]] = []
    start = previous = indices[0]
    for index in indices[1:]:
        if index != previous + 1:
            bounds.append((start, previous))
            start = index
        previous = index
    bounds.append((start, previous))
    return tuple(bounds)


def _campaign_summary(
    cutoff: CutoffResult,
    rows: list[ReplicateResult],
) -> CampaignSummary:
    if not rows or any(row.truth_included is None for row in rows):
        raise ValueError("validation rows must contain support summaries")
    coverage_count = sum(row.truth_included is True for row in rows)
    midpoints = [fmean(row.mle_probabilities) for row in rows]
    widths = [float(row.support_width) for row in rows if row.support_width is not None]
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
        median_absolute_error=median(row.minimum_absolute_error for row in rows),
        median_support_width=median(widths),
        mean_mle_bias=fmean(midpoint - TRUTH_PROBABILITY for midpoint in midpoints),
    )


def _write_replicates(path: Path, rows: tuple[ReplicateResult, ...]) -> None:
    fields = tuple(ReplicateResult.__dataclass_fields__)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            payload = {field: getattr(row, field) for field in fields}
            payload["mle_probabilities"] = json.dumps(row.mle_probabilities)
            writer.writerow(payload)


def _summary_payload(result: Goal018Result) -> dict[str, object]:
    summary = result.summary
    return {
        "goal": "018-detection-probability-positive-control",
        "run_mode": "production" if result.config.is_production else "reduced_smoke",
        "outcome": result.outcome,
        "scientific_interpretation": (
            result.outcome if result.config.is_production else "non_scientific_smoke"
        ),
        "truth_probability": TRUTH_PROBABILITY,
        "probability_domain": [result.config.probabilities[0], result.config.probabilities[-1]],
        "probability_step": 0.01,
        "bank_size": result.config.bank_size,
        "calibration_replicates": result.config.calibration_replicates,
        "validation_replicates": result.config.validation_replicates,
        "cutoff": summary.cutoff.cutoff,
        "coverage_count": summary.coverage_success_count,
        "coverage": summary.coverage.estimate,
        "coverage_interval": [summary.coverage.lower, summary.coverage.upper],
        "connected_interior_count": summary.connected_interior_count,
        "boundary_contact_count": summary.boundary_contact_count,
        "median_absolute_error": summary.median_absolute_error,
        "median_support_width": summary.median_support_width,
        "mean_mle_bias": summary.mean_mle_bias,
        "invariants": result.invariants,
    }


def _review(result: Goal018Result) -> str:
    if not result.config.is_production:
        return (
            "# Goal 018: Detection-Probability Positive Control\n\n"
            "This reduced smoke is an implementation check only and has no scientific meaning.\n"
        )
    summary = result.summary
    return "\n".join(
        [
            "# Goal 018: Detection-Probability Positive Control",
            "",
            f"Outcome: `{result.outcome}`.",
            "",
            (
                f"With rho and eta fixed at their generating values, validation coverage was "
                f"{summary.coverage_success_count}/{summary.validation_count} "
                f"({summary.coverage.estimate:.3f}; 95% Wilson interval "
                f"{summary.coverage.lower:.3f}-{summary.coverage.upper:.3f})."
            ),
            (
                f"Median absolute error in p was {summary.median_absolute_error:.3f}; median "
                f"support width was {summary.median_support_width:.3f}; "
                f"{summary.connected_interior_count}/{summary.validation_count} supports were "
                "connected and interior."
            ),
            "",
            (
                "This is an observation-layer positive control. It does not show that detection "
                "remains estimable when rho and eta are also unknown."
            ),
            "",
        ]
    )


def _review_figure(result: Goal018Result) -> Figure:
    validation = [row for row in result.replicate_results if row.phase == "validation"]
    estimates = [fmean(row.mle_probabilities) for row in validation]
    profile = result.representative_profile
    statistic = 2.0 * (profile.maximum_log_likelihood - profile.log_likelihoods)
    figure, axes = plt.subplots(1, 2, figsize=(9.5, 3.8), constrained_layout=True)
    axes[0].hist(estimates, bins=np.arange(0.545, 0.766, 0.01), color="#3B6FB6")
    axes[0].axvline(
        TRUTH_PROBABILITY,
        color="#C44E52",
        linestyle="--",
        label="Generating p = 0.65",
    )
    axes[0].set(xlabel="Estimated detection probability", ylabel="Validation histories")
    axes[0].set_title("Detection-probability estimates")
    axes[0].legend(frameon=False)
    axes[1].plot(profile.probabilities, statistic, color="#3B6FB6")
    cutoff = result.summary.cutoff.cutoff
    axes[1].axhline(
        cutoff,
        color="#C44E52",
        linestyle="--",
        label=f"Calibrated cutoff = {cutoff:.2f}",
    )
    axes[1].axvline(
        TRUTH_PROBABILITY,
        color="#2A9D8F",
        linestyle=":",
        label="Generating p = 0.65",
    )
    axes[1].set_ylim(-0.25, max(8.0, 1.5 * cutoff))
    axes[1].set(xlabel="Detection probability", ylabel="Likelihood-ratio distance")
    axes[1].set_title("Prespecified validation profile 0")
    axes[1].legend(frameon=False)
    return figure


def _save_figure(path: Path, figure: Figure) -> None:
    figure.savefig(path, format="svg", metadata={"Date": None})
    plt.close(figure)
