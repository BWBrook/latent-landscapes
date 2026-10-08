"""Replay synthesis for fixed-map Arc 3 landscape comparisons.

The primary comparison is balanced minus access-constrained sampling within
each fixed map.  Bootstrap draws resample complete calibration and evaluation
histories within a map and never resample sites or maps.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from latent_landscapes.arc2c_design import LANES, TRUTHS, BridgeConfig, BridgeTruth
from latent_landscapes.arc2c_synthesis import support_metrics
from latent_landscapes.goal002.calibration import wilson_interval

FloatArray = NDArray[np.float64]
IndexArray = NDArray[np.int64]
Row = dict[str, Any]

DEFAULT_BOOTSTRAPS = 1000
DEFAULT_BOOTSTRAP_SEED = 2026090847
DEFAULT_OUTPUT_DIR = Path("artifacts/arc3_synthesis")
EXPECTED_FILES = (
    "summary.json",
    "map_conditions.csv",
    "map_paired_metrics.csv",
    "archetype_summary.csv",
    "review.md",
)
DESIGNS = ("access", "balanced")
EFFECTS = (1.0, 3.0, 5.0)
ARC3_EFFECT_TRUTHS = TRUTHS[:3]
PRIMARY_METRICS = (
    ("mean_absolute_log_effect_error", "absolute log effect error"),
    ("mean_log_width", "log support width"),
    ("coverage", "effect coverage"),
    ("no_effect_exclusion", "no-effect exclusion"),
    ("conditional_prey_score_advantage", "conditional prey score advantage"),
)


@dataclass(frozen=True, slots=True)
class MapBundle:
    config: BridgeConfig
    truths: tuple[BridgeTruth, ...]
    profiles: dict[str, NDArray[Any]]
    run_summary: Row
    profile_sha256: str

    @property
    def metadata(self) -> Row:
        value = self.run_summary.get("scene_metadata", {})
        return dict(value) if isinstance(value, dict) else {}

    @property
    def map_key(self) -> tuple[str, str]:
        metadata = self.metadata
        if "archetype" not in metadata or "map_seed" not in metadata:
            raise ValueError("Arc 3 bundle must record scene_metadata archetype and map_seed")
        return str(metadata["archetype"]), str(metadata["map_seed"])


@dataclass(frozen=True, slots=True)
class MapEvaluation:
    effect: dict[str, FloatArray]
    rho: dict[str, FloatArray]
    effect_cutoffs: FloatArray


@dataclass(frozen=True, slots=True)
class SynthesisResult:
    bundles: tuple[MapBundle, ...]
    map_conditions: tuple[Row, ...]
    map_paired_metrics: tuple[Row, ...]
    archetype_summary: tuple[Row, ...]
    bootstrap_samples: dict[str, FloatArray]
    bootstrap_count: int
    bootstrap_seed: int
    outcome: str


def _truths() -> tuple[BridgeTruth, ...]:
    return tuple(
        BridgeTruth(f"{design}_{int(truth.effect)}", truth.rho, truth.effect, truth.role)
        for design in DESIGNS
        for truth in ARC3_EFFECT_TRUTHS
    )


def _expected_shapes(config: BridgeConfig) -> dict[str, tuple[int, ...]]:
    conditions = 6
    return {
        "calibration_effect_lr": (conditions, 2, config.calibration_replicates),
        "calibration_spread_lr": (conditions, config.calibration_replicates),
        "validation_effect_drops": (
            conditions,
            2,
            config.validation_replicates,
            len(config.effects),
        ),
        "validation_spread_drops": (
            conditions,
            config.validation_replicates,
            len(config.rhos),
        ),
        "validation_effect_mle": (conditions, 2, config.validation_replicates),
        "validation_spread_mle": (conditions, config.validation_replicates),
        "conditional_advantage": (conditions, 2, config.validation_replicates),
        "joint_advantage": (conditions, 2, config.validation_replicates),
        "calibration_train_joint": (
            conditions,
            min(2, config.calibration_replicates),
            len(config.rhos),
            len(config.effects),
        ),
        "validation_train_joint": (
            conditions,
            min(2, config.validation_replicates),
            len(config.rhos),
            len(config.effects),
        ),
        "event_diagnostics": (conditions, config.validation_replicates, 6),
    }


def validate_bundle(bundle: MapBundle) -> None:
    """Validate one saved map bundle before using it as evidence."""
    summary = bundle.run_summary
    if summary.get("profile_bundle_sha256") != bundle.profile_sha256:
        raise ValueError("saved profiles do not match the recorded campaign checksum")
    if summary.get("mode") not in {"pilot", "production"}:
        raise ValueError("Arc 3 bundle mode is not recognised")
    if any(value is False for value in summary.get("invariants", {}).values()):
        raise ValueError("the Arc 3 campaign reports a failed invariant")
    if bundle.truths != _truths():
        raise ValueError("the profile bundle does not contain the six ordered Arc 3 truths")
    profiles = bundle.profiles
    expected_ids = tuple(truth.condition_id for truth in bundle.truths)
    if "condition_ids" not in profiles or tuple(profiles["condition_ids"].tolist()) != expected_ids:
        raise ValueError("condition IDs do not match the ordered Arc 3 truths")
    if "lanes" not in profiles or tuple(profiles["lanes"].tolist()) != LANES:
        raise ValueError("paired analysis lanes are missing or reordered")
    if "design_ids" not in profiles or tuple(profiles["design_ids"].tolist()) != tuple(
        condition_id.rsplit("_", 1)[0] for condition_id in expected_ids
    ):
        raise ValueError("design labels are missing or reordered")
    if not np.array_equal(profiles["rhos"], np.asarray(bundle.config.rhos)) or not np.array_equal(
        profiles["effects"], np.asarray(bundle.config.effects)
    ):
        raise ValueError("profile grids differ from the recorded run configuration")
    for name, shape in _expected_shapes(bundle.config).items():
        values = profiles.get(name)
        if values is None or values.shape != shape or not np.isfinite(values).all():
            raise ValueError(f"invalid shape or nonfinite values in {name}; expected {shape}")
        if (name.endswith(("_lr", "_drops", "_mle")) or name == "event_diagnostics") and (
            values < -1e-10
        ).any():
            raise ValueError(f"negative likelihood loss, estimate, or event count in {name}")
    for parameter, grid in (("effect", profiles["effects"]), ("spread", profiles["rhos"])):
        drops = profiles[f"validation_{parameter}_drops"]
        if not np.allclose(np.min(drops, axis=-1), 0.0, rtol=0, atol=1e-8):
            raise ValueError(f"{parameter} profiles are not relative to their own maxima")
        if not np.isin(profiles[f"validation_{parameter}_mle"], grid).all():
            raise ValueError(f"{parameter} estimates are not on the recorded grid")
    events = profiles["event_diagnostics"]
    if not np.allclose(events[..., 0] + events[..., 3], 120) or not np.allclose(
        events[..., 1] + events[..., 2], events[..., 0]
    ):
        raise ValueError("event diagnostics do not partition the 120 training sites")
    _ = bundle.map_key


def load_map_bundle(input_dir: Path) -> MapBundle:
    """Load and validate one Arc 3 campaign output directory."""
    summary = json.loads((input_dir / "run_summary.json").read_text(encoding="utf-8"))
    profile_path = input_dir / "profiles.npz"
    with profile_path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    with np.load(profile_path, allow_pickle=False) as archive:
        profiles = {name: archive[name] for name in archive.files}
    config_fields = dict(summary["config"])
    config_fields["rhos"] = tuple(config_fields["rhos"])
    config_fields["effects"] = tuple(config_fields["effects"])
    bundle = MapBundle(
        BridgeConfig(**config_fields),
        tuple(BridgeTruth(**row) for row in summary["truths"]),
        profiles,
        summary,
        digest,
    )
    validate_bundle(bundle)
    return bundle


def _indices(indices: IndexArray, size: int, name: str) -> IndexArray:
    values = np.asarray(indices, dtype=np.int64)
    if values.ndim != 1 or not len(values) or (values < 0).any() or (values >= size).any():
        raise ValueError(f"{name} indices are outside the saved replicate range")
    return values


def evaluate_map(
    bundle: MapBundle,
    calibration_indices: IndexArray,
    evaluation_indices: IndexArray,
) -> MapEvaluation:
    """Evaluate one map using selected complete calibration/evaluation histories."""
    validate_bundle(bundle)
    return _evaluate_map_validated(bundle, calibration_indices, evaluation_indices)


def _evaluate_map_validated(
    bundle: MapBundle,
    calibration_indices: IndexArray,
    evaluation_indices: IndexArray,
) -> MapEvaluation:
    calibration = _indices(calibration_indices, bundle.config.calibration_replicates, "calibration")
    evaluation = _indices(evaluation_indices, bundle.config.validation_replicates, "evaluation")
    profiles = bundle.profiles
    rank = bundle.config.calibration_rank - 1
    effect_cutoffs = np.partition(
        profiles["calibration_effect_lr"][..., calibration], rank, axis=-1
    )[..., rank]
    effect_truths = np.asarray([truth.effect for truth in bundle.truths])
    rho_truths = np.asarray([truth.rho for truth in bundle.truths])
    effect = support_metrics(
        profiles["validation_effect_drops"][:, :, evaluation, :],
        profiles["effects"],
        effect_truths,
        effect_cutoffs,
    )
    effect["mean_absolute_log_effect_error"] = np.abs(
        np.log(profiles["validation_effect_mle"][:, :, evaluation] / effect_truths[:, None, None])
    )
    rho = {
        "mean_absolute_log_rho_error": np.abs(
            np.log(profiles["validation_spread_mle"][:, evaluation] / rho_truths[:, None])
        )
    }
    effect["conditional_prey_score_advantage"] = profiles["conditional_advantage"][:, :, evaluation]
    effect["joint_prey_score_advantage"] = profiles["joint_advantage"][:, :, evaluation]
    effect_out = {name: np.mean(values, axis=-1) for name, values in effect.items()}
    rho_out = {name: np.mean(values, axis=-1) for name, values in rho.items()}
    return MapEvaluation(effect_out, rho_out, effect_cutoffs)


def _condition_rows(bundle: MapBundle, evaluation: MapEvaluation) -> tuple[Row, ...]:
    archetype, map_seed = bundle.map_key
    rows: list[Row] = []
    for condition_index, truth in enumerate(bundle.truths):
        design, _ = truth.condition_id.rsplit("_", 1)
        for lane_index, lane in enumerate(LANES):
            row: Row = {
                "archetype": archetype,
                "map_seed": map_seed,
                "condition_id": truth.condition_id,
                "design": design,
                "truth_effect": truth.effect,
                "truth_rho": truth.rho,
                "parameter": "effect",
                "analysis": lane,
                "calibrated_cutoff": float(evaluation.effect_cutoffs[condition_index, lane_index]),
                "mean_absolute_log_effect_error": float(
                    evaluation.effect["mean_absolute_log_effect_error"][condition_index, lane_index]
                ),
                "mean_log_width": float(
                    evaluation.effect["log_interval_width"][condition_index, lane_index]
                ),
                "coverage": float(evaluation.effect["coverage"][condition_index, lane_index]),
                "no_effect_exclusion": float(
                    evaluation.effect["no_effect_exclusion"][condition_index, lane_index]
                ),
                "connected": float(evaluation.effect["connected"][condition_index, lane_index]),
                "boundary_contact": float(
                    evaluation.effect["boundary_contact"][condition_index, lane_index]
                ),
                "conditional_prey_score_advantage": float(
                    evaluation.effect["conditional_prey_score_advantage"][
                        condition_index, lane_index
                    ]
                ),
                "support_components": float(
                    evaluation.effect["support_components"][condition_index, lane_index]
                ),
            }
            successes = round(row["coverage"] * bundle.config.validation_replicates)
            interval = wilson_interval(successes, bundle.config.validation_replicates)
            row.update(
                coverage_count=successes,
                coverage_wilson_lower=interval.lower,
                coverage_wilson_upper=interval.upper,
            )
            if truth.effect == 1.0:
                null_successes = round(
                    row["no_effect_exclusion"] * bundle.config.validation_replicates
                )
                null_interval = wilson_interval(null_successes, bundle.config.validation_replicates)
                row.update(
                    null_false_exclusion_count=null_successes,
                    null_false_exclusion_wilson_lower=null_interval.lower,
                    null_false_exclusion_wilson_upper=null_interval.upper,
                )
            rows.append(row)
        rows.append(
            {
                "archetype": archetype,
                "map_seed": map_seed,
                "condition_id": truth.condition_id,
                "design": design,
                "truth_effect": truth.effect,
                "truth_rho": truth.rho,
                "parameter": "rho_context_only",
                "analysis": "estimated_speed",
                "mean_absolute_log_rho_error": float(
                    evaluation.rho["mean_absolute_log_rho_error"][condition_index]
                ),
            }
        )
    return tuple(rows)


def _paired_rows(bundle: MapBundle, evaluation: MapEvaluation) -> tuple[Row, ...]:
    archetype, map_seed = bundle.map_key
    rows: list[Row] = []
    for effect_index, effect in enumerate(EFFECTS):
        access_index, balanced_index = effect_index, effect_index + 3
        for lane_index, lane in enumerate(LANES):
            for metric, label in PRIMARY_METRICS:
                key = (
                    "mean_absolute_log_effect_error"
                    if metric == "mean_absolute_log_effect_error"
                    else "log_interval_width"
                    if metric == "mean_log_width"
                    else "conditional_prey_score_advantage"
                    if metric == "conditional_prey_score_advantage"
                    else metric
                )
                access = float(evaluation.effect[key][access_index, lane_index])
                balanced = float(evaluation.effect[key][balanced_index, lane_index])
                rows.append(
                    {
                        "archetype": archetype,
                        "map_seed": map_seed,
                        "effect": effect,
                        "analysis": lane,
                        "metric": metric,
                        "label": label,
                        "access": access,
                        "balanced": balanced,
                        "balanced_minus_access": balanced - access,
                    }
                )
    return tuple(rows)


def _analysis_config_key(config: BridgeConfig) -> tuple[Any, ...]:
    """Return settings that must agree for cross-map synthesis."""
    return (
        config.bank_size,
        config.calibration_replicates,
        config.validation_replicates,
        config.calibration_rank,
        tuple(config.rhos),
        tuple(config.effects),
    )


def summarize_maps(
    bundles: tuple[MapBundle, ...] | list[MapBundle],
    *,
    bootstrap_count: int = DEFAULT_BOOTSTRAPS,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> SynthesisResult:
    """Summarize equal-map-weight contrasts with fixed-map paired bootstrap CIs."""
    maps = tuple(bundles)
    if not maps:
        raise ValueError("at least one Arc 3 map bundle is required")
    if bootstrap_count < 2:
        raise ValueError("at least two bootstrap resamples are required")
    for bundle in maps:
        validate_bundle(bundle)
    modes = {bundle.run_summary["mode"] for bundle in maps}
    if len(modes) != 1:
        raise ValueError("pilot and production maps cannot be pooled in one synthesis")
    keys = [bundle.map_key for bundle in maps]
    if len(set(keys)) != len(keys):
        raise ValueError("archetype and map_seed metadata must be unique")
    reference = maps[0].config
    reference_key = _analysis_config_key(reference)
    for bundle in maps[1:]:
        if _analysis_config_key(bundle.config) != reference_key:
            raise ValueError("Arc 3 map bundles must share the same grids and replicate design")
    archetypes = tuple(dict.fromkeys(key[0] for key in keys))
    point_evaluations = tuple(
        _evaluate_map_validated(
            bundle,
            np.arange(reference.calibration_replicates, dtype=np.int64),
            np.arange(reference.validation_replicates, dtype=np.int64),
        )
        for bundle in maps
    )
    map_conditions = tuple(
        row
        for bundle, evaluation in zip(maps, point_evaluations, strict=True)
        for row in _condition_rows(bundle, evaluation)
    )
    map_paired = tuple(
        row
        for bundle, evaluation in zip(maps, point_evaluations, strict=True)
        for row in _paired_rows(bundle, evaluation)
    )
    rng = np.random.default_rng(bootstrap_seed)
    sample_lists: dict[str, list[FloatArray]] = {metric: [] for metric, _ in PRIMARY_METRICS}
    for _ in range(bootstrap_count):
        evaluations: list[MapEvaluation] = []
        for bundle in maps:
            calibration = rng.integers(
                reference.calibration_replicates, size=reference.calibration_replicates
            )
            evaluation_indices = rng.integers(
                reference.validation_replicates, size=reference.validation_replicates
            )
            evaluations.append(_evaluate_map_validated(bundle, calibration, evaluation_indices))
        for metric, _ in PRIMARY_METRICS:
            values = np.full((len(archetypes), len(EFFECTS), len(LANES)), np.nan)
            for archetype_index, archetype in enumerate(archetypes):
                selected_evaluations = [
                    (bundle, evaluation_result)
                    for bundle, evaluation_result in zip(maps, evaluations, strict=True)
                    if bundle.map_key[0] == archetype
                ]
                contrasts = []
                for _, evaluation_result in selected_evaluations:
                    key = (
                        "mean_absolute_log_effect_error"
                        if metric == "mean_absolute_log_effect_error"
                        else "log_interval_width"
                        if metric == "mean_log_width"
                        else "conditional_prey_score_advantage"
                        if metric == "conditional_prey_score_advantage"
                        else metric
                    )
                    contrasts.append(
                        evaluation_result.effect[key][3:, :] - evaluation_result.effect[key][:3, :]
                    )
                values[archetype_index] = np.mean(np.asarray(contrasts), axis=0)
            sample_lists[metric].append(values)
    bootstrap_samples = {name: np.asarray(values) for name, values in sample_lists.items()}
    summary_rows: list[Row] = []
    for archetype_index, archetype in enumerate(archetypes):
        selected_rows = [row for row in map_paired if row["archetype"] == archetype]
        map_count = len({row["map_seed"] for row in selected_rows})
        for effect in EFFECTS:
            effect_index = EFFECTS.index(effect)
            for lane_index, lane in enumerate(LANES):
                for metric, label in PRIMARY_METRICS:
                    map_contrasts = np.asarray(
                        [
                            row["balanced_minus_access"]
                            for row in selected_rows
                            if row["effect"] == effect
                            and row["analysis"] == lane
                            and row["metric"] == metric
                        ],
                        dtype=np.float64,
                    )
                    samples = bootstrap_samples[metric][
                        :, archetype_index, effect_index, lane_index
                    ]
                    leave_one = (
                        np.asarray(
                            [np.mean(np.delete(map_contrasts, index)) for index in range(map_count)]
                        )
                        if map_count > 1
                        else np.asarray([], dtype=np.float64)
                    )
                    summary_rows.append(
                        {
                            "archetype": archetype,
                            "effect": effect,
                            "analysis": lane,
                            "metric": metric,
                            "label": label,
                            "map_count": map_count,
                            "equal_map_mean_change": float(np.mean(map_contrasts)),
                            "bootstrap_lower": float(np.quantile(samples, 0.025)),
                            "bootstrap_upper": float(np.quantile(samples, 0.975)),
                            "map_min": float(np.min(map_contrasts)),
                            "map_max": float(np.max(map_contrasts)),
                            "leave_one_map_out_min": None
                            if not len(leave_one)
                            else float(np.min(leave_one)),
                            "leave_one_map_out_max": None
                            if not len(leave_one)
                            else float(np.max(leave_one)),
                        }
                    )
    return SynthesisResult(
        maps,
        map_conditions,
        map_paired,
        tuple(summary_rows),
        bootstrap_samples,
        bootstrap_count,
        bootstrap_seed,
        "production_pending_review" if modes == {"production"} else "non_scientific_pilot",
    )


def _write_csv(path: Path, rows: tuple[Row, ...]) -> None:
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    fields = tuple(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_review_bundle(result: SynthesisResult, output_dir: Path) -> tuple[Path, ...]:
    """Write compact JSON/CSV review outputs and bootstrap provenance."""
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "workflow": "arc3-fixed-map-sampling-synthesis",
        "schema_version": 1,
        "outcome": result.outcome,
        "production_acceptance": False,
        "map_count": len(result.bundles),
        "source_maps": [
            {
                "archetype": bundle.map_key[0],
                "map_seed": bundle.map_key[1],
                "profile_sha256": bundle.profile_sha256,
                "bank_checksum": bundle.run_summary.get("bank_checksum"),
                "source_provenance": bundle.run_summary.get("source_provenance"),
            }
            for bundle in result.bundles
        ],
        "archetypes": sorted({bundle.map_key[0] for bundle in result.bundles}),
        "bootstrap": {
            "count": result.bootstrap_count,
            "seed": result.bootstrap_seed,
            "unit": "complete calibration and evaluation histories within each fixed map",
            "sites_resampled": False,
            "maps_resampled": False,
        },
        "files": {
            "map_conditions": "map_conditions.csv",
            "map_paired_metrics": "map_paired_metrics.csv",
            "archetype_summary": "archetype_summary.csv",
        },
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_csv(output_dir / "map_conditions.csv", result.map_conditions)
    _write_csv(output_dir / "map_paired_metrics.csv", result.map_paired_metrics)
    _write_csv(output_dir / "archetype_summary.csv", result.archetype_summary)
    review = (
        "# Arc 3 fixed-map synthesis\n\n"
        f"Outcome: `{result.outcome}`.\n\n"
        "Primary contrasts are equal-map-weight balanced-minus-access changes within "
        "each archetype. Confidence intervals are conditional on the supplied maps and "
        "use a paired bootstrap of complete calibration and evaluation histories within "
        "each map. Sites and maps are never resampled.\n\n"
        "The rho rows are context only; no rho interval acceptance claim is made. "
        "This bundle does not automatically complete or accept production evidence.\n"
    )
    (output_dir / "review.md").write_text(review, encoding="utf-8")
    return tuple(output_dir / name for name in EXPECTED_FILES)
