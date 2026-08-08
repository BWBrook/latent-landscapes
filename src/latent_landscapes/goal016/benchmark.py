"""Weak-contrast information funnel on independent stochastic waves."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from typing import cast

import numpy as np
from numpy.typing import NDArray
from sklearn.linear_model import RidgeClassifier  # type: ignore[import-untyped]
from sklearn.metrics import balanced_accuracy_score, roc_auc_score  # type: ignore[import-untyped]

from latent_landscapes.goal002.calibration import EstimateInterval, wilson_interval
from latent_landscapes.goal004.likelihood import category_weights
from latent_landscapes.goal004.observations import DETECTION_PROBABILITY, SURVEY_TIMES
from latent_landscapes.goal006.spread import compute_contrast_spread, sample_edge_shock_vector
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.goal007.likelihood import rho_grid

from .discrimination import (
    FittedDiscriminator,
    centered_log_features,
    conservative_null_threshold,
    fit_ridge_discriminator,
    history_probabilities_from_detection_counts,
    profiled_composite_score,
    rank_features,
)

MASTER_SEED = 2026080716
ETA_VALUES = (0.0, 0.5)
RHO_VALUES = (0.5, 1.0, 2.0)
ALPHAS = (0.1, 1.0, 10.0, 100.0, 1000.0)
PARTITIONS = ("training", "validation", "null_calibration", "final")


@dataclass(frozen=True, slots=True)
class Goal016Config:
    master_seed: int = MASTER_SEED
    integration_bank_size: int = 4096
    train_per_class: int = 1000
    validation_per_class: int = 250
    null_calibration_count: int = 1000
    test_per_class: int = 1000
    eta_values: tuple[float, float] = ETA_VALUES
    rho_values: tuple[float, ...] = RHO_VALUES
    alphas: tuple[float, ...] = ALPHAS

    def __post_init__(self) -> None:
        if self.integration_bank_size <= 0 or self.integration_bank_size % 2:
            raise ValueError("integration_bank_size must be positive and even")
        if (
            min(
                self.train_per_class,
                self.validation_per_class,
                self.null_calibration_count,
                self.test_per_class,
            )
            < 2
        ):
            raise ValueError("every wave partition must contain at least two waves")
        if self.eta_values != ETA_VALUES:
            raise ValueError("Goal 016 compares exactly eta zero with eta one-half")
        if self.rho_values != RHO_VALUES:
            raise ValueError("Goal 016 retains the accepted three rho truths")
        if not self.alphas or any(not isfinite(value) or value <= 0.0 for value in self.alphas):
            raise ValueError("alphas must be positive and finite")

    @property
    def is_production(self) -> bool:
        return self == Goal016Config()


def smoke_config() -> Goal016Config:
    return Goal016Config(
        master_seed=MASTER_SEED + 1,
        integration_bank_size=32,
        train_per_class=8,
        validation_per_class=6,
        null_calibration_count=20,
        test_per_class=20,
        alphas=(1.0, 10.0),
    )


@dataclass(frozen=True, slots=True)
class WaveSet:
    full_arrivals: NDArray[np.float64]
    site_arrivals: NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class FunnelPerformance:
    representation: str
    method: str
    rho: float
    selected_alpha: float | None
    validation_auc: float | None
    threshold: float
    final_auc: float
    balanced_accuracy: float
    false_positive_count: int
    false_positive_rate: float
    false_positive_interval: EstimateInterval
    power_count: int
    power: float
    power_interval: EstimateInterval
    null_count: int
    alternative_count: int
    practically_useful: bool


@dataclass(frozen=True, slots=True)
class FinalWaveScore:
    method: str
    truth_eta: float
    truth_rho: float
    wave_index: int
    score: float
    threshold: float
    claims_nonzero_contrast: bool


@dataclass(frozen=True, slots=True)
class Goal016Result:
    config: Goal016Config
    outcome: str
    invariants: dict[str, bool]
    partition_digest: str
    site_ids: tuple[str, ...]
    positive_cell_count: int
    funnel_performance: tuple[FunnelPerformance, ...]
    final_wave_scores: tuple[FinalWaveScore, ...]
    full_map_coefficient: NDArray[np.float64]
    detection_coefficient: NDArray[np.float64]


DEFAULT_CONFIG = Goal016Config()


def run_goal016(config: Goal016Config = DEFAULT_CONFIG) -> Goal016Result:
    """Run the frozen information funnel without changing accepted upstream science."""
    fixed = goal007.build_fixed_inputs()
    positive_mask = fixed.landscape.passable & (fixed.landscape.source_zone == "")
    site_rows = np.asarray([site.row for site in fixed.design.sites], dtype=np.int64)
    site_cols = np.asarray([site.col for site in fixed.design.sites], dtype=np.int64)
    site_ids = tuple(site.site_id for site in fixed.design.sites)
    roots = _partition_roots(config)

    wave_sets = _generate_all_wave_sets(
        config,
        fixed,
        positive_mask,
        site_rows,
        site_cols,
        roots,
    )
    detection_counts = _generate_detection_counts(config, wave_sets, roots)

    performance: list[FunnelPerformance] = []
    invariant_models: dict[str, FittedDiscriminator] = {}
    feature_builders: tuple[
        tuple[str, Callable[[NDArray[np.float64]], NDArray[np.float64]]], ...
    ] = (
        (
            "global_time_only",
            _global_time_features,
        ),
        ("full_map_centered_log", centered_log_features),
        ("full_map_ranks", rank_features),
    )
    for representation, transform in feature_builders:
        fitted, row = _fit_invariant_representation(
            config,
            wave_sets,
            representation,
            _full_arrival_transform(transform),
        )
        invariant_models[representation] = fitted
        performance.append(row)

    site_model, site_row = _fit_invariant_representation(
        config,
        wave_sets,
        "sample_sites_centered_log",
        lambda waves: centered_log_features(waves.site_arrivals),
    )
    invariant_models["sample_sites_centered_log"] = site_model
    performance.append(site_row)

    _occupancy_model, occupancy_rows = _fit_rho_mixture_representation(
        config,
        wave_sets,
        "sample_sites_perfect_occupancy",
        _occupancy_features,
    )
    performance.extend(occupancy_rows)

    detection_model, detection_rows, detection_final_scores = _fit_detection_representation(
        config,
        detection_counts,
    )
    performance.extend(detection_rows)

    weights = _build_current_composite_weights(config, fixed)
    composite_rows, composite_final_scores = _evaluate_current_composite_statistic(
        config,
        detection_counts,
        weights,
    )
    performance.extend(composite_rows)

    full_coefficient = _ridge_coefficients(invariant_models["full_map_centered_log"])
    detection_coefficient = _ridge_coefficients(detection_model).reshape(len(site_ids), 6)
    final_scores = (*detection_final_scores, *composite_final_scores)
    invariants = _invariants(
        config,
        fixed.invariants,
        roots,
        wave_sets,
        detection_counts,
        weights,
        performance,
        final_scores,
        full_coefficient,
        detection_coefficient,
        int(positive_mask.sum()),
        len(site_ids),
    )
    outcome = _classify_outcome(config, tuple(performance), invariants)
    return Goal016Result(
        config=config,
        outcome=outcome,
        invariants=invariants,
        partition_digest=_partition_digest(config, roots),
        site_ids=site_ids,
        positive_cell_count=int(positive_mask.sum()),
        funnel_performance=tuple(performance),
        final_wave_scores=tuple(final_scores),
        full_map_coefficient=full_coefficient,
        detection_coefficient=detection_coefficient,
    )


def _partition_roots(config: Goal016Config) -> dict[tuple[str, float, str], np.random.SeedSequence]:
    roots: dict[tuple[str, float, str], np.random.SeedSequence] = {}
    for partition_index, partition in enumerate(PARTITIONS):
        eta_values = (0.0,) if partition == "null_calibration" else config.eta_values
        for eta_index, eta in enumerate(eta_values):
            roots[(partition, eta, "process")] = np.random.SeedSequence(
                (config.master_seed, 1, partition_index, eta_index)
            )
            for rho_index, rho in enumerate(config.rho_values):
                roots[(partition, eta, f"detection_{rho:g}")] = np.random.SeedSequence(
                    (config.master_seed, 2, partition_index, eta_index, rho_index)
                )
    return roots


def _partition_count(config: Goal016Config, partition: str) -> int:
    return {
        "training": config.train_per_class,
        "validation": config.validation_per_class,
        "null_calibration": config.null_calibration_count,
        "final": config.test_per_class,
    }[partition]


def _generate_all_wave_sets(
    config: Goal016Config,
    fixed: goal007.FixedInputs,
    positive_mask: NDArray[np.bool],
    site_rows: NDArray[np.int64],
    site_cols: NDArray[np.int64],
    roots: Mapping[tuple[str, float, str], np.random.SeedSequence],
) -> dict[tuple[str, float], WaveSet]:
    result: dict[tuple[str, float], WaveSet] = {}
    for partition in PARTITIONS:
        eta_values = (0.0,) if partition == "null_calibration" else config.eta_values
        for eta in eta_values:
            result[(partition, eta)] = _generate_wave_set(
                fixed,
                eta=eta,
                count=_partition_count(config, partition),
                root=roots[(partition, eta, "process")],
                positive_mask=positive_mask,
                site_rows=site_rows,
                site_cols=site_cols,
            )
    return result


def _generate_wave_set(
    fixed: goal007.FixedInputs,
    *,
    eta: float,
    count: int,
    root: np.random.SeedSequence,
    positive_mask: NDArray[np.bool],
    site_rows: NDArray[np.int64],
    site_cols: NDArray[np.int64],
) -> WaveSet:
    full = np.empty((count, int(positive_mask.sum())), dtype=np.float64)
    sites = np.empty((count, len(site_rows)), dtype=np.float64)
    for wave_index, child in enumerate(root.spawn(count)):
        rng = np.random.Generator(np.random.PCG64(child))
        shocks = sample_edge_shock_vector(fixed.landscape, rng)
        truth = compute_contrast_spread(fixed.landscape, eta, edge_shocks=shocks, rho=1.0)
        full[wave_index] = truth.arrival[positive_mask]
        sites[wave_index] = truth.arrival[site_rows, site_cols]
    if (
        not np.isfinite(full).all()
        or (full <= 0.0).any()
        or not np.isfinite(sites).all()
        or (sites <= 0.0).any()
    ):
        raise RuntimeError("generated wave set contains invalid positive arrivals")
    return WaveSet(full_arrivals=full, site_arrivals=sites)


def _generate_detection_counts(
    config: Goal016Config,
    wave_sets: Mapping[tuple[str, float], WaveSet],
    roots: Mapping[tuple[str, float, str], np.random.SeedSequence],
) -> dict[tuple[str, float, float], NDArray[np.int8]]:
    counts: dict[tuple[str, float, float], NDArray[np.int8]] = {}
    survey_times = np.asarray(SURVEY_TIMES, dtype=np.float64)
    for (partition, eta), waves in wave_sets.items():
        for rho in config.rho_values:
            occupied = waves.site_arrivals[:, :, None] / rho <= survey_times[None, None, :]
            rng = np.random.Generator(
                np.random.PCG64(roots[(partition, eta, f"detection_{rho:g}")])
            )
            detected = rng.binomial(2, DETECTION_PROBABILITY, size=occupied.shape)
            counts[(partition, eta, rho)] = np.where(occupied, detected, 0).astype(np.int8)
    return counts


def _occupancy_features(waves: WaveSet, rho: float) -> NDArray[np.float64]:
    survey_times = np.asarray(SURVEY_TIMES, dtype=np.float64)
    occupied = waves.site_arrivals[:, :, None] / rho <= survey_times[None, None, :]
    return occupied.reshape(len(waves.site_arrivals), -1).astype(np.float64)


def _global_time_features(values: NDArray[np.float64]) -> NDArray[np.float64]:
    return np.asarray(np.median(np.log(values), axis=1, keepdims=True), dtype=np.float64)


def _full_arrival_transform(
    transform: Callable[[NDArray[np.float64]], NDArray[np.float64]],
) -> Callable[[WaveSet], NDArray[np.float64]]:
    def apply(waves: WaveSet) -> NDArray[np.float64]:
        return transform(waves.full_arrivals)

    return apply


def _fit_invariant_representation(
    config: Goal016Config,
    wave_sets: Mapping[tuple[str, float], WaveSet],
    representation: str,
    transform: Callable[[WaveSet], NDArray[np.float64]],
) -> tuple[FittedDiscriminator, FunnelPerformance]:
    train_x, train_y = _binary_class_features(
        transform(wave_sets[("training", 0.0)]),
        transform(wave_sets[("training", 0.5)]),
    )
    validation_x, validation_y = _binary_class_features(
        transform(wave_sets[("validation", 0.0)]),
        transform(wave_sets[("validation", 0.5)]),
    )
    fitted = fit_ridge_discriminator(
        train_x,
        train_y,
        validation_x,
        validation_y,
        alphas=config.alphas,
    )
    null_calibration = fitted.decision_function(transform(wave_sets[("null_calibration", 0.0)]))
    threshold = conservative_null_threshold({1.0: null_calibration})
    null_final = fitted.decision_function(transform(wave_sets[("final", 0.0)]))
    alternative_final = fitted.decision_function(transform(wave_sets[("final", 0.5)]))
    return fitted, _performance_row(
        representation=representation,
        method="ridge_wave_classifier",
        rho=1.0,
        fitted=fitted,
        threshold=threshold,
        null_scores=null_final,
        alternative_scores=alternative_final,
    )


def _fit_rho_mixture_representation(
    config: Goal016Config,
    wave_sets: Mapping[tuple[str, float], WaveSet],
    representation: str,
    transform: Callable[[WaveSet, float], NDArray[np.float64]],
) -> tuple[FittedDiscriminator, tuple[FunnelPerformance, ...]]:
    train_x, train_y = _pooled_rho_features(config, wave_sets, "training", transform)
    validation_x, validation_y = _pooled_rho_features(config, wave_sets, "validation", transform)
    fitted = fit_ridge_discriminator(
        train_x,
        train_y,
        validation_x,
        validation_y,
        alphas=config.alphas,
    )
    null_calibration = {
        rho: fitted.decision_function(transform(wave_sets[("null_calibration", 0.0)], rho))
        for rho in config.rho_values
    }
    threshold = conservative_null_threshold(null_calibration)
    rows = tuple(
        _performance_row(
            representation=representation,
            method="ridge_wave_classifier",
            rho=rho,
            fitted=fitted,
            threshold=threshold,
            null_scores=fitted.decision_function(transform(wave_sets[("final", 0.0)], rho)),
            alternative_scores=fitted.decision_function(transform(wave_sets[("final", 0.5)], rho)),
        )
        for rho in config.rho_values
    )
    return fitted, rows


def _fit_detection_representation(
    config: Goal016Config,
    counts: Mapping[tuple[str, float, float], NDArray[np.int8]],
) -> tuple[FittedDiscriminator, tuple[FunnelPerformance, ...], tuple[FinalWaveScore, ...]]:
    train_x, train_y = _pooled_detection_features(config, counts, "training")
    validation_x, validation_y = _pooled_detection_features(config, counts, "validation")
    fitted = fit_ridge_discriminator(
        train_x,
        train_y,
        validation_x,
        validation_y,
        alphas=config.alphas,
    )
    null_calibration = {
        rho: fitted.decision_function(_flatten_counts(counts[("null_calibration", 0.0, rho)]))
        for rho in config.rho_values
    }
    threshold = conservative_null_threshold(null_calibration)
    rows: list[FunnelPerformance] = []
    score_records: list[FinalWaveScore] = []
    for rho in config.rho_values:
        null_scores = fitted.decision_function(_flatten_counts(counts[("final", 0.0, rho)]))
        alternative_scores = fitted.decision_function(_flatten_counts(counts[("final", 0.5, rho)]))
        rows.append(
            _performance_row(
                representation="sample_sites_imperfect_detection",
                method="ridge_wave_classifier",
                rho=rho,
                fitted=fitted,
                threshold=threshold,
                null_scores=null_scores,
                alternative_scores=alternative_scores,
            )
        )
        score_records.extend(
            _score_records(
                method="ridge_wave_classifier",
                rho=rho,
                threshold=threshold,
                null_scores=null_scores,
                alternative_scores=alternative_scores,
            )
        )
    return fitted, tuple(rows), tuple(score_records)


def _build_current_composite_weights(
    config: Goal016Config,
    fixed: goal007.FixedInputs,
) -> NDArray[np.float64]:
    seed_config = goal007.Goal007Config(
        bank_size=config.integration_bank_size,
        calibration_replicates=1,
        validation_replicates=1,
        calibration_rank_one_based=1,
    )
    manifest = goal007.spawn_seed_manifest(seed_config)
    bank = goal007.build_integration_bank(fixed, manifest.integration_bank, config.eta_values)
    weights_by_eta = tuple(
        category_weights(bank.arrivals[:, eta_index, :], rho_grid())
        for eta_index in range(len(config.eta_values))
    )
    return np.stack(weights_by_eta)


def _evaluate_current_composite_statistic(
    config: Goal016Config,
    counts: Mapping[tuple[str, float, float], NDArray[np.int8]],
    weights: NDArray[np.float64],
) -> tuple[tuple[FunnelPerformance, ...], tuple[FinalWaveScore, ...]]:
    null_calibration = {
        rho: _composite_scores(counts[("null_calibration", 0.0, rho)], weights)
        for rho in config.rho_values
    }
    threshold = conservative_null_threshold(null_calibration)
    rows: list[FunnelPerformance] = []
    score_records: list[FinalWaveScore] = []
    for rho in config.rho_values:
        null_scores = _composite_scores(counts[("final", 0.0, rho)], weights)
        alternative_scores = _composite_scores(counts[("final", 0.5, rho)], weights)
        rows.append(
            _performance_row(
                representation="current_composite_statistic",
                method="profiled_sitewise_composite",
                rho=rho,
                fitted=None,
                threshold=threshold,
                null_scores=null_scores,
                alternative_scores=alternative_scores,
            )
        )
        score_records.extend(
            _score_records(
                method="profiled_sitewise_composite",
                rho=rho,
                threshold=threshold,
                null_scores=null_scores,
                alternative_scores=alternative_scores,
            )
        )
    return tuple(rows), tuple(score_records)


def _composite_scores(
    counts: NDArray[np.int8],
    weights: NDArray[np.float64],
) -> NDArray[np.float64]:
    return np.asarray(
        [
            profiled_composite_score(
                weights,
                history_probabilities_from_detection_counts(wave, DETECTION_PROBABILITY),
            )
            for wave in counts
        ],
        dtype=np.float64,
    )


def _binary_class_features(
    eta_zero: NDArray[np.float64],
    eta_half: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.int8]]:
    features = np.vstack((eta_zero, eta_half))
    labels = np.concatenate(
        (
            np.zeros(len(eta_zero), dtype=np.int8),
            np.ones(len(eta_half), dtype=np.int8),
        )
    )
    return features, labels


def _pooled_rho_features(
    config: Goal016Config,
    wave_sets: Mapping[tuple[str, float], WaveSet],
    partition: str,
    transform: Callable[[WaveSet, float], NDArray[np.float64]],
) -> tuple[NDArray[np.float64], NDArray[np.int8]]:
    eta_zero = np.vstack([transform(wave_sets[(partition, 0.0)], rho) for rho in config.rho_values])
    eta_half = np.vstack([transform(wave_sets[(partition, 0.5)], rho) for rho in config.rho_values])
    return _binary_class_features(eta_zero, eta_half)


def _pooled_detection_features(
    config: Goal016Config,
    counts: Mapping[tuple[str, float, float], NDArray[np.int8]],
    partition: str,
) -> tuple[NDArray[np.float64], NDArray[np.int8]]:
    eta_zero = np.vstack(
        [_flatten_counts(counts[(partition, 0.0, rho)]) for rho in config.rho_values]
    )
    eta_half = np.vstack(
        [_flatten_counts(counts[(partition, 0.5, rho)]) for rho in config.rho_values]
    )
    return _binary_class_features(eta_zero, eta_half)


def _flatten_counts(counts: NDArray[np.int8]) -> NDArray[np.float64]:
    return counts.reshape(len(counts), -1).astype(np.float64)


def _performance_row(
    *,
    representation: str,
    method: str,
    rho: float,
    fitted: FittedDiscriminator | None,
    threshold: float,
    null_scores: NDArray[np.float64],
    alternative_scores: NDArray[np.float64],
) -> FunnelPerformance:
    null_values = np.asarray(null_scores, dtype=np.float64)
    alternative_values = np.asarray(alternative_scores, dtype=np.float64)
    labels = np.concatenate(
        (
            np.zeros(len(null_values), dtype=np.int8),
            np.ones(len(alternative_values), dtype=np.int8),
        )
    )
    scores = np.concatenate((null_values, alternative_values))
    predicted = (scores > threshold).astype(np.int8)
    false_positive_count = int((null_values > threshold).sum())
    power_count = int((alternative_values > threshold).sum())
    false_positive_interval = wilson_interval(false_positive_count, len(null_values))
    power_interval = wilson_interval(power_count, len(alternative_values))
    useful = power_interval.lower > 0.80 and false_positive_count / len(null_values) <= 0.06
    return FunnelPerformance(
        representation=representation,
        method=method,
        rho=float(rho),
        selected_alpha=None if fitted is None else fitted.alpha,
        validation_auc=None if fitted is None else fitted.validation_auc,
        threshold=float(threshold),
        final_auc=float(roc_auc_score(labels, scores)),
        balanced_accuracy=float(balanced_accuracy_score(labels, predicted)),
        false_positive_count=false_positive_count,
        false_positive_rate=float(false_positive_count / len(null_values)),
        false_positive_interval=false_positive_interval,
        power_count=power_count,
        power=float(power_count / len(alternative_values)),
        power_interval=power_interval,
        null_count=len(null_values),
        alternative_count=len(alternative_values),
        practically_useful=useful,
    )


def _score_records(
    *,
    method: str,
    rho: float,
    threshold: float,
    null_scores: NDArray[np.float64],
    alternative_scores: NDArray[np.float64],
) -> tuple[FinalWaveScore, ...]:
    rows: list[FinalWaveScore] = []
    for truth_eta, scores in ((0.0, null_scores), (0.5, alternative_scores)):
        rows.extend(
            FinalWaveScore(
                method=method,
                truth_eta=truth_eta,
                truth_rho=float(rho),
                wave_index=index,
                score=float(score),
                threshold=float(threshold),
                claims_nonzero_contrast=bool(score > threshold),
            )
            for index, score in enumerate(scores)
        )
    return tuple(rows)


def _ridge_coefficients(fitted: FittedDiscriminator) -> NDArray[np.float64]:
    ridge = cast(RidgeClassifier, fitted.pipeline.named_steps["ridge"])
    coefficients = np.asarray(ridge.coef_, dtype=np.float64)
    if coefficients.ndim == 2 and coefficients.shape[0] == 1:
        coefficients = coefficients[0]
    if coefficients.ndim != 1 or not np.isfinite(coefficients).all():
        raise RuntimeError("ridge classifier coefficients are invalid")
    return coefficients.copy()


def _invariants(
    config: Goal016Config,
    fixed_invariants: Mapping[str, bool],
    roots: Mapping[tuple[str, float, str], np.random.SeedSequence],
    wave_sets: Mapping[tuple[str, float], WaveSet],
    detection_counts: Mapping[tuple[str, float, float], NDArray[np.int8]],
    weights: NDArray[np.float64],
    performance: list[FunnelPerformance],
    final_scores: tuple[FinalWaveScore, ...],
    full_coefficient: NDArray[np.float64],
    detection_coefficient: NDArray[np.float64],
    positive_cell_count: int,
    site_count: int,
) -> dict[str, bool]:
    root_keys = tuple(roots)
    root_entropies = tuple(_root_entropy(roots[key]) for key in root_keys)
    expected_wave_keys = {
        (partition, eta)
        for partition in PARTITIONS
        for eta in ((0.0,) if partition == "null_calibration" else config.eta_values)
    }
    expected_detection_keys = {
        (partition, eta, rho) for partition, eta in expected_wave_keys for rho in config.rho_values
    }
    thresholds_by_representation: dict[str, set[float]] = {}
    for row in performance:
        thresholds_by_representation.setdefault(row.representation, set()).add(row.threshold)
    score_keys = {
        (row.method, row.truth_eta, row.truth_rho, row.wave_index) for row in final_scores
    }
    return {
        "upstream_fixed_inputs": all(fixed_invariants.values()),
        "positive_cell_count": positive_cell_count == 5144,
        "partition_root_keys_unique": len(root_keys) == len(set(root_keys)),
        "partition_roots_unique": len(root_entropies) == len(set(root_entropies)),
        "wave_partition_surface": set(wave_sets) == expected_wave_keys,
        "detection_partition_surface": set(detection_counts) == expected_detection_keys,
        "integration_weight_shape": weights.shape
        == (2, len(rho_grid()), site_count, len(SURVEY_TIMES) + 1),
        "integration_weights_finite": bool(
            np.isfinite(weights).all()
            and (weights > 0.0).all()
            and np.allclose(weights.sum(axis=-1), 1.0, rtol=0.0, atol=1e-12)
        ),
        "common_rho_thresholds": all(
            len(values) == 1
            for key, values in thresholds_by_representation.items()
            if key
            in {
                "sample_sites_perfect_occupancy",
                "sample_sites_imperfect_detection",
                "current_composite_statistic",
            }
        ),
        "same_history_score_pairing": len(score_keys) == len(final_scores)
        and len(final_scores) == 4 * len(config.rho_values) * config.test_per_class,
        "coefficient_shapes": full_coefficient.shape == (positive_cell_count,)
        and detection_coefficient.shape == (site_count, len(SURVEY_TIMES)),
        "coefficients_finite": bool(
            np.isfinite(full_coefficient).all() and np.isfinite(detection_coefficient).all()
        ),
    }


def _root_entropy(root: np.random.SeedSequence) -> tuple[int, ...]:
    entropy = root.entropy
    if entropy is None:
        raise RuntimeError("seed root is missing entropy")
    if isinstance(entropy, (int, np.integer)):
        return (int(entropy),)
    return tuple(int(value) for value in entropy)


def _partition_digest(
    config: Goal016Config,
    roots: Mapping[tuple[str, float, str], np.random.SeedSequence],
) -> str:
    payload = {
        "master_seed": config.master_seed,
        "counts": {partition: _partition_count(config, partition) for partition in PARTITIONS},
        "roots": [
            {
                "partition": key[0],
                "eta": key[1],
                "role": key[2],
                "entropy": list(_root_entropy(root)),
                "spawn_key": list(root.spawn_key),
            }
            for key, root in sorted(roots.items())
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def _classify_outcome(
    config: Goal016Config,
    performance: tuple[FunnelPerformance, ...],
    invariants: Mapping[str, bool],
) -> str:
    if not all(invariants.values()):
        return "implementation_blocked"
    if not config.is_production:
        return "reduced_smoke_complete"

    def useful(representation: str) -> bool:
        rows = [row for row in performance if row.representation == representation]
        return bool(rows) and all(row.practically_useful for row in rows)

    # Diagnose from the deepest useful rung. Information demonstrated after
    # sampling or detection logically must have existed in every upstream rung,
    # even when an upstream empirical threshold misses its finite-sample gate.
    if useful("current_composite_statistic"):
        return "information_retained_support_target_limited"
    if useful("sample_sites_imperfect_detection"):
        return "information_lost_in_current_statistic"
    if useful("sample_sites_perfect_occupancy") or useful("sample_sites_centered_log"):
        return "temporal_detection_information_loss"
    if useful("full_map_centered_log") or useful("full_map_ranks"):
        return "spatial_sampling_information_loss"
    return "intrinsic_weak_contrast_overlap"
