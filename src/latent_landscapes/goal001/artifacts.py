"""Deterministic nine-file human review bundle for Goal 001."""

from __future__ import annotations

import csv
import io
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from math import isfinite
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

matplotlib.use("Agg")

from .benchmark import BenchmarkResult
from .design import ROAD_COLUMNS, SITE_OFFSETS, STRATUM_LABELS, TRANSECT_ROWS
from .likelihood import HoldoutEvaluation, Interval, LikelihoodClass, LikelihoodProfile
from .observations import DETECTION_PROBABILITY, SURVEY_TIMES
from .spread import TRUE_RATE

DEFAULT_OUTPUT_DIR = Path("artifacts/goal001_deterministic_spread")
NEUTRAL_COMPARATOR_LABEL = "geometry-only hard-front comparator"
ROOT_FILES = (
    "design.csv",
    "observations.csv",
    "likelihood_profile.csv",
    "holdout_predictions.csv",
    "summary.json",
    "review.md",
)
VISUAL_FILES = (
    "landscape_design.svg",
    "spread_observations.svg",
    "likelihood_holdout.svg",
)

type CsvValue = str | int | float | bool
type CsvRow = Mapping[str, CsvValue]


def write_review_bundle(
    result: BenchmarkResult, output_dir: str | Path = DEFAULT_OUTPUT_DIR
) -> tuple[Path, ...]:
    target = Path(output_dir)
    visuals = target / "visuals"
    visuals.mkdir(parents=True, exist_ok=True)

    paths = {
        "design.csv": target / "design.csv",
        "observations.csv": target / "observations.csv",
        "likelihood_profile.csv": target / "likelihood_profile.csv",
        "holdout_predictions.csv": target / "holdout_predictions.csv",
        "summary.json": target / "summary.json",
        "review.md": target / "review.md",
        **{name: visuals / name for name in VISUAL_FILES},
    }
    _write_csv(paths["design.csv"], _design_rows(result))
    _write_csv(paths["observations.csv"], [record.to_csv_row() for record in result.observations])
    _write_csv(paths["likelihood_profile.csv"], _likelihood_rows(result))
    _write_csv(paths["holdout_predictions.csv"], _holdout_rows(result))
    paths["summary.json"].write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    paths["review.md"].write_text(_render_review(result), encoding="utf-8")
    paths["landscape_design.svg"].write_text(_landscape_design_svg(result), encoding="utf-8")
    paths["spread_observations.svg"].write_text(_spread_observations_svg(result), encoding="utf-8")
    paths["likelihood_holdout.svg"].write_text(_likelihood_holdout_svg(result), encoding="utf-8")

    expected = {
        *ROOT_FILES,
        *(f"visuals/{name}" for name in VISUAL_FILES),
    }
    observed = {path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()}
    if observed != expected:
        raise RuntimeError(
            f"artifact contract mismatch: expected {sorted(expected)}, got {sorted(observed)}"
        )
    return tuple(paths[name] for name in (*ROOT_FILES, *VISUAL_FILES))


def _design_rows(result: BenchmarkResult) -> list[CsvRow]:
    rows: list[CsvRow] = []
    for site in result.design.sites:
        rows.append(
            {
                "cluster_id": site.cluster_id,
                "split": site.split,
                "stratum_index": site.stratum_index,
                "stratum_bounds": STRATUM_LABELS[site.stratum_index],
                "center_row": site.center_row,
                "center_col": site.center_col,
                "center_euclidean_source_distance": site.euclidean_source_distance,
                "site_id": site.site_id,
                "site_offset_index": site.site_offset_index,
                "offset_row": site.offset_row,
                "offset_col": site.offset_col,
                "row": site.row,
                "col": site.col,
                "on_access_network": bool(result.design.network[site.center_row, site.center_col]),
                "passable": bool(result.landscape.passable[site.row, site.col]),
                "source_reachable": bool(result.landscape.source_reachable[site.row, site.col]),
                "habitat_class": str(result.landscape.habitat_class[site.row, site.col]),
            }
        )
    return rows


def _likelihood_rows(result: BenchmarkResult) -> list[CsvRow]:
    rows: list[CsvRow] = []
    for profile in (result.habitat_training, result.neutral_training, result.habitat_all):
        mle = set(profile.mle_classes)
        support = set(profile.support_classes)
        for index, likelihood_class in enumerate(profile.classes, start=1):
            rows.append(
                {
                    "class_id": f"{profile.model}_{profile.scope}_{index:04d}",
                    "model": profile.model,
                    "scope": profile.scope,
                    "lower_rate": likelihood_class.lower,
                    "upper_rate": likelihood_class.upper,
                    "lower_closed": likelihood_class.lower_closed,
                    "upper_closed": likelihood_class.upper_closed,
                    "representative_rate": likelihood_class.representative_rate,
                    "class_width": likelihood_class.width,
                    "log_likelihood": likelihood_class.log_likelihood,
                    "is_mle_class": likelihood_class in mle,
                    "is_nominal_lr_support_class": likelihood_class in support,
                }
            )
    return rows


def _holdout_rows(result: BenchmarkResult) -> list[CsvRow]:
    rows: list[CsvRow] = []
    for evaluation in (result.habitat_holdout, result.neutral_holdout):
        for index, partition in enumerate(evaluation.partitions, start=1):
            rows.append(
                {
                    "partition_id": f"{evaluation.model}_{index:03d}",
                    "model": evaluation.model,
                    "lower_rate": partition.lower,
                    "upper_rate": partition.upper,
                    "lower_closed": partition.lower_closed,
                    "upper_closed": partition.upper_closed,
                    "representative_rate": partition.representative_rate,
                    "partition_width": partition.width,
                    "heldout_total_bernoulli_log_score": partition.log_score,
                    "heldout_mean_brier_score": partition.brier_score,
                    "impossible_positive_count": partition.impossible_positive_count,
                }
            )
    return rows


def _summary_payload(result: BenchmarkResult) -> dict[str, object]:
    support = result.habitat_all.support_components
    neutral_zero_probability = _neutral_zero_probability_summary(result)
    return {
        "goal": "001-deterministic-predator-spread-identifiability-benchmark",
        "outcome": result.outcome,
        "one_realization_only": True,
        "truth_rate": TRUE_RATE,
        "rate_domain": [0.25, 4.0],
        "detection_probability": DETECTION_PROBABILITY,
        "counts": {
            "cells": result.landscape.cell_count,
            "passable_cells": int(result.landscape.passable.sum()),
            "water_cells": int((~result.landscape.passable).sum()),
            "clusters": len(result.design.clusters),
            "training_clusters": sum(c.split == "training" for c in result.design.clusters),
            "holdout_clusters": sum(c.split == "holdout" for c in result.design.clusters),
            "sites": len(result.design.sites),
            "records": len(result.observations),
            "detections": sum(record.detected for record in result.observations),
        },
        "provenance": {
            "origin_repository": "spatext",
            "accepted_commit": "53462d0365babf2c8070714a930f69b4071af276",
            "landscape": {
                "source_path": "src/spatext/synth/medium/landscape.py",
                "source_blob_sha1": "f2f5fc24e64274e443f8eec8c314e212e2a6889f",
                "status": "adapted",
            },
            "spread": {
                "source_path": "src/spatext/synth/medium/spread_impact.py",
                "source_blob_sha1": "cb15f2178ff9e2f359f06fdac34a9b551e163cd5",
                "status": "rewritten",
            },
            "runtime_dependency_on_spatext": False,
        },
        "design": {
            "zero_based_indices": True,
            "road_columns": list(ROAD_COLUMNS),
            "transect_rows": list(TRANSECT_ROWS),
            "site_offsets": [list(value) for value in SITE_OFFSETS],
            "eligible_counts_by_stratum": [
                sum(c.stratum_index == index for c in result.design.eligible_centres)
                for index in range(4)
            ],
            "centre_selection": (
                "sorted (row,col) candidates, dedicated permutation per stratum, "
                "near-to-far greedy acceptance, global Euclidean separation >=8"
            ),
            "holdout_selection": (
                "sorted cluster IDs within stratum, dedicated permutation, first two IDs"
            ),
        },
        "ideal_process_identifiability": {
            "injective": result.ideal_process_identifiable,
            "positive_path_cost_exists": bool(
                (result.truth.arrival[result.truth.reachable] > 0.0).any()
            ),
            "scope": (
                "algebraic and conditional on the exact full-landscape path-cost vector and "
                "model; distinct from practical observation identification"
            ),
        },
        "profiles": {
            "habitat_training": _profile_summary(result.habitat_training),
            "neutral_training": _profile_summary(result.neutral_training),
            "habitat_all": _profile_summary(result.habitat_all),
        },
        "nominal_lr_support": {
            "label": "nominal likelihood-ratio support",
            "threshold": 3.841458820694124,
            "components": [_interval_payload(value) for value in support],
            "contains_truth": any(value.contains(TRUE_RATE) for value in support),
            "calibrated_confidence_interval": False,
            "likelihood_shape": "discontinuous_stepwise",
            "wilks_calibrated": False,
            "width_used_for_automatic_classification": False,
        },
        "holdout_comparison": {
            "primary_metric": "total Bernoulli log score",
            "secondary_metric": "mean Brier score",
            "neutral_comparator": NEUTRAL_COMPARATOR_LABEL,
            "rule": (
                "worst habitat exceeds best neutral; reverse for neutral; otherwise inconclusive"
            ),
            "habitat": _holdout_summary(result.habitat_holdout),
            "neutral": {
                **_holdout_summary(result.neutral_holdout),
                "zero_probability_detections": neutral_zero_probability,
            },
            "comparison": result.comparison,
        },
        "invariants": result.invariants,
        "limitations": [
            "single canonical realization",
            "no seed sweep or retuning",
            (
                "nominal likelihood-ratio support is descriptive, not calibrated "
                "confidence or coverage"
            ),
            "no prey, stochastic process, optimizer, MCMC, ABC, real data, or Goal 002 work",
            (
                "a future full-support predictive neutral baseline should be added as a distinct "
                "model rather than retrofitted into this hard-front comparator"
            ),
        ],
    }


def _profile_summary(profile: LikelihoodProfile) -> dict[str, object]:
    return {
        "class_count": len(profile.classes),
        "maximum_log_likelihood": _json_float(profile.maximum_log_likelihood),
        "mle_classes": [_class_payload(value) for value in profile.mle_classes],
        "support_components": [_interval_payload(value) for value in profile.support_components],
    }


def _holdout_summary(evaluation: HoldoutEvaluation) -> dict[str, object]:
    return {
        "partition_count": len(evaluation.partitions),
        "log_score_range": [
            _json_float(evaluation.log_score_range.minimum),
            _json_float(evaluation.log_score_range.maximum),
        ],
        "brier_score_range": [
            evaluation.brier_score_range.minimum,
            evaluation.brier_score_range.maximum,
        ],
        "impossible_positive_range": [
            int(evaluation.impossible_positive_range.minimum),
            int(evaluation.impossible_positive_range.maximum),
        ],
    }


def _neutral_zero_probability_summary(result: BenchmarkResult) -> dict[str, object]:
    site_times = _neutral_zero_probability_site_times(result)
    record_count = sum(count for _, _, count in site_times)
    observation, inference, assumption, limitation = _neutral_zero_probability_narrative(
        result, site_times
    )
    return {
        "observation": observation,
        "record_count": record_count,
        "site_time_count": len(site_times),
        "site_times": [
            {"site_id": site_id, "time": time, "detection_records": count}
            for site_id, time, count in site_times
        ],
        "inference": inference,
        "assumption": assumption,
        "limitation": limitation,
    }


def _neutral_zero_probability_site_times(
    result: BenchmarkResult,
) -> tuple[tuple[str, int, int], ...]:
    counts: Counter[tuple[str, int]] = Counter(
        (record.site_id, record.time)
        for record in result.observations
        if record.split == "holdout"
        and record.detected
        and result.neutral_holdout.partitions
        and all(
            result.neutral_distances[record.site_id] / partition.representative_rate > record.time
            for partition in result.neutral_holdout.partitions
        )
    )
    return tuple((site_id, time, count) for (site_id, time), count in sorted(counts.items()))


def _neutral_zero_probability_narrative(
    result: BenchmarkResult,
    site_times: tuple[tuple[str, int, int], ...],
) -> tuple[str, str, str, str]:
    record_count = sum(count for _, _, count in site_times)
    if record_count:
        number_words = {1: "One", 2: "Two", 3: "Three", 4: "Four"}
        site_number_words = {1: "one", 2: "two", 3: "three", 4: "four"}
        record_number = number_words.get(record_count, str(record_count))
        site_number = site_number_words.get(len(site_times), str(len(site_times)))
        record_noun = "record" if record_count == 1 else "records"
        site_noun = "site-time" if len(site_times) == 1 else "site-times"
        verb = "is" if record_count == 1 else "are"
        observation = (
            f"{record_number} held-out detection {record_noun} at {site_number} {site_noun} "
            f"{verb} assigned zero probability by every neutral training-MLE partition."
        )
    else:
        observation = (
            "No held-out detection record is assigned zero probability by every neutral "
            "training-MLE partition."
        )

    minimum = result.neutral_holdout.log_score_range.minimum
    maximum = result.neutral_holdout.log_score_range.maximum
    if isfinite(minimum) and isfinite(maximum):
        inference = (
            "Neutral held-out total Bernoulli log scores are finite across all neutral "
            f"training-MLE partitions: {_range_text(minimum, maximum)}."
        )
        limitation = (
            "False positives or softened occupancy could alter these finite scores, but those "
            "models are outside Goal 001."
        )
    elif minimum == float("-inf") and maximum == float("-inf"):
        inference = (
            "Under known zero false positives and hard deterministic occupancy, every "
            f"{NEUTRAL_COMPARATOR_LABEL} training-MLE partition has held-out total Bernoulli "
            "log score -Infinity: this is a structural support violation because observed "
            "positive records fall outside the comparator's occupied set. It is not an "
            "optimizer failure, and -Infinity is not a calibrated magnitude of model "
            "superiority."
        )
        limitation = (
            "Allowing false positives or softened occupancy would make zero-probability cases "
            "finite. A future full-support predictive neutral baseline should be evaluated "
            "separately; neither change is part of Goal 001."
        )
    else:
        inference = (
            "Under known zero false positives and hard deterministic occupancy, the neutral "
            f"held-out total Bernoulli log-score range is {_range_text(minimum, maximum)}."
        )
        limitation = (
            "Allowing false positives or softened occupancy would make zero-probability cases "
            "finite; those models are outside Goal 001."
        )
    assumption = (
        "The false-positive probability is known to be zero (known zero false positives), "
        "and occupancy is a hard deterministic arrival state."
    )
    return observation, inference, assumption, limitation


def _class_payload(value: LikelihoodClass) -> dict[str, object]:
    return {
        **_interval_payload(value.as_interval()),
        "representative_rate": value.representative_rate,
        "log_likelihood": _json_float(value.log_likelihood),
    }


def _interval_payload(value: Interval) -> dict[str, object]:
    return {
        "lower": value.lower,
        "upper": value.upper,
        "lower_closed": value.lower_closed,
        "upper_closed": value.upper_closed,
        "width": value.width,
    }


def _render_review(result: BenchmarkResult) -> str:
    support = result.habitat_all.support_components
    support_lines = "\n".join(
        f"- `{_interval_text(value)}`; width `{value.width}`" for value in support
    )
    habitat_mle = "\n".join(
        f"- `{_interval_text(value.as_interval())}`; width `{value.width}`"
        for value in result.habitat_training.mle_classes
    )
    neutral_mle = "\n".join(
        f"- `{_interval_text(value.as_interval())}`; width `{value.width}`"
        for value in result.neutral_training.mle_classes
    )
    habitat_log = _range_text(
        result.habitat_holdout.log_score_range.minimum,
        result.habitat_holdout.log_score_range.maximum,
    )
    neutral_log = _range_text(
        result.neutral_holdout.log_score_range.minimum,
        result.neutral_holdout.log_score_range.maximum,
    )
    habitat_brier = _range_text(
        result.habitat_holdout.brier_score_range.minimum,
        result.habitat_holdout.brier_score_range.maximum,
    )
    neutral_brier = _range_text(
        result.neutral_holdout.brier_score_range.minimum,
        result.neutral_holdout.brier_score_range.maximum,
    )
    neutral_impossible = (
        f"{int(result.neutral_holdout.impossible_positive_range.minimum)}-"
        f"{int(result.neutral_holdout.impossible_positive_range.maximum)}"
    )
    decision = _decision_text(result)
    neutral_zero_probability = _neutral_zero_probability_site_times(result)
    neutral_zero_probability_summary = _neutral_zero_probability_summary(result)
    neutral_zero_probability_details = ", ".join(
        f"`{site_id}` at `t={time}` ({_detection_record_text(count)})"
        for site_id, time, count in neutral_zero_probability
    )
    neutral_observation = str(neutral_zero_probability_summary["observation"])
    if neutral_zero_probability_details:
        neutral_observation = (
            f"{neutral_observation.removesuffix('.')}: {neutral_zero_probability_details}."
        )
    structural_identifiability = (
        "Ideal structural identifiability here is algebraic and conditional on the exact "
        "full-landscape path-cost vector and model. It is distinct from practical "
        "observation-based identification through the frozen sample and likelihood."
    )
    return f"""# Goal 001 deterministic predator-spread review

## Decision

**Outcome: `{result.outcome}`.** {decision}

This is a single canonical realization. It is not a seed sweep, calibration study,
or general recoverability claim.

{structural_identifiability}

## Frozen design

- The zero-based access network uses road columns `{ROAD_COLUMNS}` and transect rows
  `{TRANSECT_ROWS}`. It was laid down without habitat, conductance, sources, arrival,
  `rho`, or detections.
- Prespecified nearest-source geometry is used only for allocation strata.
- Within each near-to-far stratum, sorted `(row, col)` candidates are permuted by the
  dedicated centre stream and greedily accepted with global centre separation `>=8`.
- Cluster IDs follow stratum then acceptance order. For holdout, sorted cluster IDs
  within each stratum are permuted by the dedicated holdout stream and the first two
  are held out. This is deterministic selection, not retuning.
- The design contains 32 clusters, 160 sites, 24 training clusters, 8 holdout
  clusters, and 1,920 conditionally independent replicate records.

## Exact likelihood

Habitat training MLE class set:
{habitat_mle}

{NEUTRAL_COMPARATOR_LABEL.title()} training MLE class set (`model=neutral`):
{neutral_mle}

Full-data habitat nominal likelihood-ratio support:
{support_lines}

The support uses `2 * (LLmax - LL) <= 3.841458820694124` over complete exact
prediction-equivalence classes. Equality at arrival is occupied. Endpoint closure is
preserved. This nominal support comes from a discontinuous stepwise likelihood. It is
descriptive, not a calibrated confidence interval and not a Wilks-calibrated interval.
Support width is reported for Barry's judgement and is not used for automatic
classification.

## Held-out comparison

The `neutral` machine-readable model is the **geometry-only hard-front comparator**:
a nearest-source radial wave with deterministic occupancy and no false positives. It
is a deliberately rigid comparator, not yet a full-support neutral
predictive model.

- Habitat total Bernoulli log-score range: `{habitat_log}`.
- Geometry-only hard-front comparator total Bernoulli log-score range: `{neutral_log}`.
- Habitat mean Brier range (finite corroborating evidence): `{habitat_brier}`.
- Geometry-only hard-front comparator mean Brier range (finite corroborating
  evidence): `{neutral_brier}`.
- Geometry-only hard-front comparator impossible-positive count range: `{neutral_impossible}`.

The primary rule uses total Bernoulli log score: habitat is robustly better only when
its worst score exceeds the comparator's best. The finite Brier comparison is secondary
descriptive corroboration and remains interpretable when a hard-zero log score occurs;
it does not replace the prespecified primary rule.

- **Observation:** {neutral_observation}
- **Inference:** {neutral_zero_probability_summary["inference"]}
- **Assumption:** {neutral_zero_probability_summary["assumption"]}
- **Limitation:** {neutral_zero_probability_summary["limitation"]}

## Provenance and assumptions

The landscape geometry is adapted from `src/spatext/synth/medium/landscape.py` and
the weighted spread primitive is rewritten from
`src/spatext/synth/medium/spread_impact.py`, both at accepted SpatExt commit
`53462d0365babf2c8070714a930f69b4071af276`. The new implementation has no runtime
dependency on SpatExt. Conductance, sources, detection probability `0.65`, no false
positives, and deterministic arrival mechanism are treated as known.

## Limits

No arbitrary support-width threshold, repeated seeds, retuning, calibrated coverage,
prey process, stochastic spread, optimizer, MCMC, ABC, real data, or Goal 002 work is
included. A negative scientific outcome would still be a successful benchmark run.
"""


def _decision_text(result: BenchmarkResult) -> str:
    if result.outcome == "implementation_blocked":
        return (
            "No scientific outcome is reported because an implementation, provenance, "
            "structural-identifiability, eligibility, leakage, or numerical invariant failed."
        )
    if result.outcome == "recovery_failure":
        return (
            "The full-data nominal likelihood-ratio support excludes `rho = 1` in this "
            "canonical realization, so the result is a recovery failure rather than a "
            "calibrated rejection."
        )
    if result.outcome == "design_limited":
        return (
            "The full-data nominal likelihood-ratio support is disconnected or touches the "
            "frozen rate-domain boundary, so this canonical design is limited and no advance "
            "decision is made."
        )
    if result.outcome == "mechanism_not_supported":
        return (
            "Rate criteria pass, but the geometry-only hard-front comparator robustly "
            "beats habitat "
            "spread on the frozen holdout, so the habitat mechanism is not supported."
        )
    if result.outcome == "rate_recoverable_mechanism_inconclusive":
        return (
            "Rate criteria pass, but neither model robustly wins on the frozen holdout, so "
            "mechanism support remains inconclusive."
        )
    if result.outcome == "advance_goal002":
        return (
            "The ideal arrival map is structurally identifiable, the full-data nominal "
            "likelihood-ratio support is one interior interval containing `rho = 1`, and "
            "habitat spread robustly beats the geometry-only hard-front comparator on the "
            "frozen holdout."
        )
    raise ValueError(f"unsupported Goal 001 outcome: {result.outcome}")


def _decision_figure_label(result: BenchmarkResult) -> str:
    labels = {
        "implementation_blocked": "implementation blocked",
        "recovery_failure": "recovery failure",
        "design_limited": "design limited",
        "mechanism_not_supported": "mechanism not supported",
        "advance_goal002": "habitat robustly better",
        "rate_recoverable_mechanism_inconclusive": "mechanism inconclusive",
    }
    try:
        return labels[result.outcome]
    except KeyError as error:
        raise ValueError(f"unsupported Goal 001 outcome: {result.outcome}") from error


def _detection_record_text(count: int) -> str:
    if count == 1:
        return "one detection record"
    if count == 2:
        return "two replicate detection records"
    return f"{count} detection records"


def _neutral_figure_evidence(result: BenchmarkResult) -> tuple[str, str]:
    site_times = _neutral_zero_probability_site_times(result)
    record_count = sum(count for _, _, count in site_times)
    if record_count:
        zero_probability = (
            f"Comparator zero-probability: {record_count} records / {len(site_times)} site-times"
        )
    else:
        zero_probability = "Comparator zero-probability: none"

    minimum = result.neutral_holdout.log_score_range.minimum
    maximum = result.neutral_holdout.log_score_range.maximum
    if isfinite(minimum) and isfinite(maximum):
        score_context = "Comparator scores finite; details in review.md"
    elif minimum == float("-inf") and maximum == float("-inf"):
        score_context = "Hard zero-FP comparator support violation; details in review.md"
    else:
        score_context = "Comparator range includes -Infinity; details in review.md"
    return zero_probability, score_context


def _landscape_design_svg(result: BenchmarkResult) -> str:
    classes = (
        "water",
        "low_quality_matrix",
        "medium_quality",
        "high_quality_patch",
        "corridor",
        "source_zone",
    )
    colors = ("#5b8db8", "#d4d4d4", "#9ccf8d", "#2f7d47", "#e2a93b", "#b0488f")
    class_index = {name: index for index, name in enumerate(classes)}
    grid = np.vectorize(class_index.__getitem__)(result.landscape.habitat_class)
    with plt.rc_context(_svg_rc()):
        figure, axis = plt.subplots(figsize=(12, 7), constrained_layout=True)
        axis.imshow(
            grid,
            cmap=ListedColormap(colors),
            norm=BoundaryNorm(np.arange(-0.5, len(classes) + 0.5), len(classes)),
            origin="upper",
            interpolation="nearest",
        )
        for col in ROAD_COLUMNS:
            axis.axvline(col, color="#111827", alpha=0.24, linewidth=0.8)
        for row in TRANSECT_ROWS:
            axis.axhline(row, color="#111827", alpha=0.24, linewidth=0.8)
        for site in result.design.sites:
            axis.scatter(site.col, site.row, s=7, color="#ffffff", alpha=0.55, linewidth=0)
        training = [cluster for cluster in result.design.clusters if cluster.split == "training"]
        holdout = [cluster for cluster in result.design.clusters if cluster.split == "holdout"]
        axis.scatter(
            [value.center_col for value in training],
            [value.center_row for value in training],
            s=42,
            marker="o",
            facecolors="none",
            edgecolors="#111827",
            linewidths=1.2,
        )
        axis.scatter(
            [value.center_col for value in holdout],
            [value.center_row for value in holdout],
            s=58,
            marker="D",
            facecolors="#ffffff",
            edgecolors="#c81e1e",
            linewidths=1.5,
        )
        legend = [
            Line2D([0], [0], color=color, lw=8, label=label)
            for label, color in zip(classes, colors, strict=True)
        ]
        legend.extend(
            (
                Line2D([0], [0], color="#111827", lw=1.2, label="fixed access network"),
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="#111827",
                    markerfacecolor="none",
                    lw=0,
                    label="training centre",
                ),
                Line2D(
                    [0],
                    [0],
                    marker="D",
                    color="#c81e1e",
                    markerfacecolor="#ffffff",
                    lw=0,
                    label="holdout centre",
                ),
            )
        )
        axis.legend(handles=legend, loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False)
        axis.set(
            title="Accepted landscape, fixed access network, and frozen clusters",
            xlabel="Column (0-based)",
            ylabel="Row (0-based)",
        )
        axis.set_xlim(-0.5, result.landscape.cols - 0.5)
        axis.set_ylim(result.landscape.rows - 0.5, -0.5)
        return _figure_svg(figure)


def _spread_observations_svg(result: BenchmarkResult) -> str:
    masked_arrival = np.ma.masked_where(~result.landscape.passable, result.truth.arrival)
    detection_count = {
        site.site_id: sum(
            record.detected for record in result.observations if record.site_id == site.site_id
        )
        for site in result.design.sites
    }
    first_detection = {
        site.site_id: min(
            (
                record.time
                for record in result.observations
                if record.site_id == site.site_id and record.detected
            ),
            default=120,
        )
        for site in result.design.sites
    }
    with plt.rc_context(_svg_rc()):
        figure, axes = plt.subplots(1, 2, figsize=(14, 6.5), constrained_layout=True)
        image = axes[0].imshow(masked_arrival, cmap="viridis", origin="upper")
        axes[0].scatter(
            [site.col for site in result.design.sites],
            [site.row for site in result.design.sites],
            c=[detection_count[site.site_id] for site in result.design.sites],
            cmap="YlOrRd",
            vmin=0,
            vmax=12,
            s=[18 + 3 * detection_count[site.site_id] for site in result.design.sites],
            edgecolors="#ffffff",
            linewidths=0.4,
        )
        figure.colorbar(image, ax=axes[0], label="True arrival path cost D")
        detection_legend = [
            Line2D(
                [0],
                [0],
                marker="o",
                color="none",
                markerfacecolor=plt.get_cmap("YlOrRd")(count / 12.0),
                markeredgecolor="#777777",
                markersize=(18 + 3 * count) ** 0.5,
                label=str(count),
            )
            for count in (0, 6, 12)
        ]
        axes[0].legend(
            handles=detection_legend,
            title="Detection count encoded by marker size",
            loc="lower right",
            frameon=True,
        )
        axes[0].set_title("True arrival surface with sampled detections")

        habitat = np.where(result.landscape.passable, 1.0, np.nan)
        axes[1].imshow(habitat, cmap=ListedColormap(("#e6e7e8",)), origin="upper")
        first = axes[1].scatter(
            [site.col for site in result.design.sites],
            [site.row for site in result.design.sites],
            c=[first_detection[site.site_id] for site in result.design.sites],
            cmap="plasma_r",
            vmin=min(SURVEY_TIMES),
            vmax=120,
            s=34,
            edgecolors=[
                "#c81e1e" if site.split == "holdout" else "#222222" for site in result.design.sites
            ],
            linewidths=0.5,
        )
        figure.colorbar(first, ax=axes[1], label="First detection time (120 = none)")
        axes[1].set_title("Observed timing; holdout sites edged red")
        for axis in axes:
            axis.set(xlabel="Column (0-based)", ylabel="Row (0-based)")
            axis.set_xlim(-0.5, result.landscape.cols - 0.5)
            axis.set_ylim(result.landscape.rows - 0.5, -0.5)
        return _figure_svg(figure)


def _likelihood_holdout_svg(result: BenchmarkResult) -> str:
    profiles = (
        (result.habitat_training, "Habitat training", "#157f5b"),
        (result.neutral_training, "Geometry-only comparator training", "#c07818"),
        (result.habitat_all, "Habitat full data", "#2764a5"),
    )
    with plt.rc_context(_svg_rc()):
        figure, axes = plt.subplots(
            1,
            2,
            figsize=(14, 6.2),
            gridspec_kw={"width_ratios": (1.7, 1.0)},
            constrained_layout=True,
        )
        for profile, label, color in profiles:
            trace_x: list[float] = []
            trace_y: list[float] = []
            for likelihood_class in profile.classes:
                if not isfinite(likelihood_class.log_likelihood):
                    continue
                deviance = 2.0 * (profile.maximum_log_likelihood - likelihood_class.log_likelihood)
                if 0.94 <= likelihood_class.representative_rate <= 1.25 and deviance <= 12.0:
                    trace_x.append(likelihood_class.representative_rate)
                    trace_y.append(deviance)
                axes[0].hlines(
                    deviance,
                    likelihood_class.lower,
                    likelihood_class.upper,
                    color=color,
                    linewidth=1.5,
                )
            axes[0].plot(
                trace_x,
                trace_y,
                color=color,
                linewidth=1.2,
                marker=".",
                markersize=2.5,
                drawstyle="steps-mid",
            )
            axes[0].plot([], [], color=color, linewidth=2, label=label)
        axes[0].axhline(
            3.841458820694124, color="#444444", linestyle="--", label="Nominal LR threshold"
        )
        axes[0].axvline(
            TRUE_RATE, color="#c81e1e", linestyle=":", linewidth=1.5, label="Truth rho=1"
        )
        axes[0].set(
            xlabel="Spread-rate multiplier rho",
            ylabel="2(LLmax - LL)",
            xlim=(0.94, 1.25),
            ylim=(-0.2, 12.0),
            title=(
                "Exact likelihood-equivalence classes\n"
                "Display window rho=0.94 to 1.25; full domain in CSV"
            ),
        )
        axes[0].legend(frameon=False, loc="upper right")

        brier = (
            result.habitat_holdout.brier_score_range.maximum,
            result.neutral_holdout.brier_score_range.maximum,
        )
        axes[1].bar((0, 1), brier, color=("#157f5b", "#c07818"), width=0.62)
        axes[1].set_ylim(0.0, max(max(brier) * 1.8, 0.01))
        axes[1].set_xticks((0, 1), ("Habitat", "Geometry-only\ncomparator"))
        axes[1].set_ylabel("Held-out mean Brier score (finite corroboration)")
        axes[1].set_title("Frozen holdout comparison")
        habitat_log = _compact_range_text(
            result.habitat_holdout.log_score_range.minimum,
            result.habitat_holdout.log_score_range.maximum,
        )
        neutral_log = _compact_range_text(
            result.neutral_holdout.log_score_range.minimum,
            result.neutral_holdout.log_score_range.maximum,
        )
        neutral_zero_probability, neutral_score_context = _neutral_figure_evidence(result)
        axes[1].text(
            0.5,
            0.96,
            "Total Bernoulli log score (primary)\n"
            f"Habitat: {habitat_log}\n"
            f"Geometry-only comparator: {neutral_log}\n"
            f"{neutral_zero_probability}\n"
            f"{neutral_score_context}\n"
            "LR support: descriptive, non-Wilks\n"
            f"Decision: {_decision_figure_label(result)}",
            transform=axes[1].transAxes,
            ha="center",
            va="top",
            fontsize=9.2,
            bbox={"facecolor": "white", "edgecolor": "#bbbbbb", "boxstyle": "square,pad=0.5"},
        )
        return _figure_svg(figure)


def _write_csv(path: Path, rows: Sequence[CsvRow]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path.name}")
    columns = tuple(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_csv_value(row[column]) for column in columns])


def _csv_value(value: CsvValue) -> str | int:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if value == float("-inf"):
            return "-inf"
        if value == float("inf"):
            return "inf"
        return format(value, ".17g")
    return value


def _json_float(value: float) -> float | str:
    if value == float("-inf"):
        return "-Infinity"
    if value == float("inf"):
        return "Infinity"
    return value


def _interval_text(value: Interval) -> str:
    left = "[" if value.lower_closed else "("
    right = "]" if value.upper_closed else ")"
    return f"{left}{value.lower}, {value.upper}{right}"


def _range_text(minimum: float, maximum: float) -> str:
    return f"{_json_float(minimum)} to {_json_float(maximum)}"


def _compact_range_text(minimum: float, maximum: float) -> str:
    if minimum == maximum:
        return str(_json_float(minimum))
    return _range_text(minimum, maximum)


def _svg_rc() -> Any:
    return {
        "svg.hashsalt": "latent-landscapes-goal001",
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 13,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
    }


def _figure_svg(figure: Figure) -> str:
    buffer = io.StringIO()
    figure.savefig(
        buffer,
        format="svg",
        metadata={"Date": None, "Creator": "Latent Landscapes Goal 001"},
    )
    plt.close(figure)
    return buffer.getvalue()
