"""Wave-level representations and a deliberately simple linear discriminator."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import cast

import numpy as np
from numpy.typing import NDArray
from sklearn.linear_model import RidgeClassifier  # type: ignore[import-untyped]
from sklearn.metrics import roc_auc_score  # type: ignore[import-untyped]
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]


@dataclass(frozen=True, slots=True)
class FittedDiscriminator:
    """A frozen standardised ridge classifier selected on validation waves."""

    pipeline: Pipeline
    alpha: float
    validation_auc: float

    def decision_function(self, features: NDArray[np.float64]) -> NDArray[np.float64]:
        values = _feature_matrix(features)
        scores = np.asarray(self.pipeline.decision_function(values), dtype=np.float64)
        if scores.shape != (len(values),) or not np.isfinite(scores).all():
            raise ValueError("classifier returned invalid decision scores")
        return scores


def centered_log_features(arrivals: NDArray[np.float64]) -> NDArray[np.float64]:
    """Remove each wave's multiplicative global timing scale exactly."""
    values = _positive_feature_matrix(arrivals)
    logged = np.log(values)
    return cast(
        NDArray[np.float64],
        logged - np.median(logged, axis=1, keepdims=True),
    )


def rank_features(arrivals: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return average cellwise arrival ranks scaled to the unit interval."""
    values = _positive_feature_matrix(arrivals)
    feature_count = values.shape[1]
    if feature_count == 1:
        return np.zeros_like(values)
    ranks = np.empty_like(values)
    for row_index, row in enumerate(values):
        order = np.argsort(row, kind="stable")
        ordered = row[order]
        starts = np.flatnonzero(np.r_[True, ordered[1:] != ordered[:-1]])
        ends = np.r_[starts[1:], feature_count]
        ordered_ranks = np.empty(feature_count, dtype=np.float64)
        for start, end in zip(starts, ends, strict=True):
            ordered_ranks[start:end] = (float(start) + float(end - 1)) / 2.0
        ranks[row_index, order] = ordered_ranks / float(feature_count - 1)
    return ranks


def history_probabilities_from_detection_counts(
    counts: NDArray[np.integer],
    detection_probability: float,
) -> NDArray[np.float64]:
    """Return current-model site-history probabilities for seven onset categories."""
    values = np.asarray(counts)
    if values.ndim != 2 or values.shape[1] != 6:
        raise ValueError("detection counts must have shape (site, 6)")
    if not isfinite(detection_probability) or not 0.0 < detection_probability < 1.0:
        raise ValueError("detection_probability must lie strictly between zero and one")
    if not np.isin(values, (0, 1, 2)).all():
        raise ValueError("two-visit detection counts must be 0, 1, or 2")

    site_count = values.shape[0]
    probabilities = np.empty((site_count, 7), dtype=np.float64)
    for category in range(7):
        if category == 6:
            probabilities[:, category] = (values.sum(axis=1) == 0).astype(np.float64)
            continue
        impossible = (values[:, :category] > 0).any(axis=1)
        detections = values[:, category:].sum(axis=1)
        trials = 2 * (6 - category)
        probability = np.power(detection_probability, detections) * np.power(
            1.0 - detection_probability,
            trials - detections,
        )
        probabilities[:, category] = np.where(impossible, 0.0, probability)
    return probabilities


def conservative_null_threshold(
    scores_by_rho: Mapping[float, NDArray[np.float64]],
    *,
    quantile: float = 0.95,
) -> float:
    """Use the largest pointwise null quantile as one common threshold."""
    if not 0.0 < quantile < 1.0:
        raise ValueError("quantile must lie strictly between zero and one")
    if not scores_by_rho:
        raise ValueError("at least one rho-specific score vector is required")
    pointwise: list[float] = []
    for rho, raw_scores in scores_by_rho.items():
        if not isfinite(rho) or rho <= 0.0:
            raise ValueError("rho keys must be finite and positive")
        scores = np.asarray(raw_scores, dtype=np.float64)
        if scores.ndim != 1 or len(scores) == 0 or not np.isfinite(scores).all():
            raise ValueError("null score vectors must be nonempty, finite, and one-dimensional")
        pointwise.append(float(np.quantile(scores, quantile, method="higher")))
    return max(pointwise)


def profiled_composite_score(
    weights: NDArray[np.float64],
    history_probabilities: NDArray[np.float64],
) -> float:
    """Compare eta-half with eta-zero after profiling each over the rho axis."""
    values = np.asarray(weights, dtype=np.float64)
    histories = np.asarray(history_probabilities, dtype=np.float64)
    if values.ndim != 4 or values.shape[0] != 2:
        raise ValueError("weights must have shape (2, rho, site, category)")
    if histories.shape != values.shape[2:]:
        raise ValueError("history probabilities must match the site-category axes")
    if (
        not np.isfinite(values).all()
        or (values <= 0.0).any()
        or not np.isfinite(histories).all()
        or (histories < 0.0).any()
    ):
        raise ValueError("weights and histories must contain valid finite probabilities")
    site_probabilities = np.einsum("ersc,sc->ers", values, histories, optimize=True)
    if (site_probabilities <= 0.0).any() or not np.isfinite(site_probabilities).all():
        raise ValueError("site-history marginal probabilities must be finite and positive")
    log_likelihoods = np.log(site_probabilities).sum(axis=2)
    return float(log_likelihoods[1].max() - log_likelihoods[0].max())


def fit_ridge_discriminator(
    train_features: NDArray[np.float64],
    train_labels: NDArray[np.integer],
    validation_features: NDArray[np.float64],
    validation_labels: NDArray[np.integer],
    *,
    alphas: Sequence[float],
) -> FittedDiscriminator:
    """Select one standardised linear ridge classifier by validation AUC."""
    train_x = _feature_matrix(train_features)
    validation_x = _feature_matrix(validation_features)
    train_y = _binary_labels(train_labels, len(train_x))
    validation_y = _binary_labels(validation_labels, len(validation_x))
    if train_x.shape[1] != validation_x.shape[1]:
        raise ValueError("training and validation feature counts must agree")
    penalties = tuple(float(value) for value in alphas)
    if not penalties or any(not isfinite(value) or value <= 0.0 for value in penalties):
        raise ValueError("alphas must contain positive finite penalties")

    best: FittedDiscriminator | None = None
    for alpha in penalties:
        pipeline = Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "ridge",
                    RidgeClassifier(alpha=alpha, class_weight="balanced", solver="lsqr"),
                ),
            ]
        )
        pipeline.fit(train_x, train_y)
        scores = np.asarray(pipeline.decision_function(validation_x), dtype=np.float64)
        auc = float(roc_auc_score(validation_y, scores))
        candidate = FittedDiscriminator(pipeline=pipeline, alpha=alpha, validation_auc=auc)
        if best is None or (candidate.validation_auc, -candidate.alpha) > (
            best.validation_auc,
            -best.alpha,
        ):
            best = candidate
    if best is None:
        raise RuntimeError("ridge discriminator selection produced no candidate")
    return best


def _feature_matrix(values: NDArray[np.float64]) -> NDArray[np.float64]:
    matrix = np.asarray(values, dtype=np.float64)
    if matrix.ndim != 2 or len(matrix) == 0 or matrix.shape[1] == 0:
        raise ValueError("features must be a nonempty two-dimensional matrix")
    if not np.isfinite(matrix).all():
        raise ValueError("features must be finite")
    return matrix


def _positive_feature_matrix(values: NDArray[np.float64]) -> NDArray[np.float64]:
    matrix = _feature_matrix(values)
    if (matrix <= 0.0).any():
        raise ValueError("arrival features must be strictly positive")
    return matrix


def _binary_labels(values: NDArray[np.integer], expected_count: int) -> NDArray[np.int8]:
    labels = np.asarray(values, dtype=np.int8)
    if labels.shape != (expected_count,) or not np.isin(labels, (0, 1)).all():
        raise ValueError("labels must be a binary vector matching the feature rows")
    if len(np.unique(labels)) != 2:
        raise ValueError("both binary classes must be present")
    return labels
