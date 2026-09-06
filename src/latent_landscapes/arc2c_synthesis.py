"""Paired, calibration-aware synthesis of the frozen Arc 2C profile bundle."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib as mpl
import numpy as np
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from numpy.typing import NDArray

from latent_landscapes.arc2c_design import LANES, TRUTHS, BridgeConfig, BridgeTruth
from latent_landscapes.goal002.calibration import wilson_interval

mpl.use("Agg")
import matplotlib.pyplot as plt

FloatArray = NDArray[np.float64]
IndexArray = NDArray[np.int64]
Row = dict[str, Any]
DEFAULT_BOOTSTRAPS = 1000
DEFAULT_BOOTSTRAP_SEED = 2026090545
DEFAULT_OUTPUT_DIR = Path("artifacts/arc2c_synthesis")
EVENT_NAMES = (
    "true_extirpations_by_day60",
    "pre_arrival_true_extirpations",
    "post_arrival_true_extirpations",
    "true_extirpation_censoring",
    "post_arrival_at_risk_exposure",
    "prey_observation_support",
)
PRIMARY_METRICS = (
    ("mean_absolute_log_error", "Effect error", "natural log units", "positive"),
    ("mean_log_interval_width", "Interval width", "natural log units", "positive"),
    ("coverage", "Coverage", "proportion", "negative"),
    ("no_effect_exclusion", "Exclude no prey effect", "proportion", "negative"),
    ("conditional_prey_advantage", "Prey prediction", "nats per holdout site", "negative"),
)
LANE_LABELS = {"known_speed": "Speed supplied", "estimated_speed": "Speed estimated"}
WAVE_COLORS = {1.0: "#087E8B", 0.5: "#B84A62"}


@dataclass(frozen=True)
class CampaignBundle:
    config: BridgeConfig
    truths: tuple[BridgeTruth, ...]
    profiles: dict[str, NDArray[Any]]
    run_summary: Row
    profile_sha256: str


@dataclass(frozen=True)
class BootstrapSamples:
    effect: dict[str, FloatArray]
    spread: dict[str, FloatArray]
    effect_cutoffs: FloatArray
    spread_cutoffs: FloatArray
    events: FloatArray


@dataclass(frozen=True)
class SynthesisResult:
    bundle: CampaignBundle
    conditions: tuple[Row, ...]
    paired_changes: tuple[Row, ...]
    event_information: tuple[Row, ...]
    case_interpretations: tuple[Row, ...]
    caution_flags: tuple[str, ...]
    bootstrap_count: int
    bootstrap_seed: int
    bootstrap_samples: BootstrapSamples
    outcome: str


def validate_bundle(bundle: CampaignBundle) -> None:
    """Check the frozen dimensions and numerical inputs needed by synthesis."""
    config, profiles = bundle.config, bundle.profiles
    if bundle.truths != TRUTHS:
        raise ValueError("the profile bundle does not contain the approved six ordered truths")
    if tuple(profiles["condition_ids"].tolist()) != tuple(row.condition_id for row in TRUTHS):
        raise ValueError("condition IDs do not match the frozen truth order")
    if tuple(profiles["lanes"].tolist()) != LANES:
        raise ValueError("paired analysis lanes are missing or reordered")
    if not np.array_equal(profiles["rhos"], config.rhos) or not np.array_equal(
        profiles["effects"], config.effects
    ):
        raise ValueError("profile grids differ from the run configuration")
    c, r, h = len(TRUTHS), len(config.rhos), len(config.effects)
    nc, nv = config.calibration_replicates, config.validation_replicates
    shapes = {
        "calibration_effect_lr": (c, 2, nc),
        "calibration_spread_lr": (c, nc),
        "validation_effect_drops": (c, 2, nv, h),
        "validation_spread_drops": (c, nv, r),
        "validation_effect_mle": (c, 2, nv),
        "validation_spread_mle": (c, nv),
        "conditional_advantage": (c, 2, nv),
        "joint_advantage": (c, 2, nv),
        "calibration_train_joint": (c, min(2, nc), r, h),
        "validation_train_joint": (c, min(2, nv), r, h),
        "event_diagnostics": (c, nv, 6),
    }
    for name, shape in shapes.items():
        values = profiles[name]
        if values.shape != shape or not np.isfinite(values).all():
            raise ValueError(f"invalid shape or nonfinite values in {name}; expected {shape}")
        if (name.endswith(("_lr", "_drops", "_mle")) or name == "event_diagnostics") and (
            values < -1e-10
        ).any():
            raise ValueError(f"negative likelihood loss, estimate, or event count in {name}")
    for parameter in ("effect", "spread"):
        drops = profiles[f"validation_{parameter}_drops"]
        if not np.allclose(np.min(drops, axis=-1), 0.0, rtol=0, atol=1e-8):
            raise ValueError(f"{parameter} profiles are not relative to their own maxima")
        grid = profiles["effects" if parameter == "effect" else "rhos"]
        if not np.isin(profiles[f"validation_{parameter}_mle"], grid).all():
            raise ValueError(f"{parameter} estimates are not on the frozen grid")
    events = profiles["event_diagnostics"]
    if not np.allclose(events[..., 0] + events[..., 3], 120) or not np.allclose(
        events[..., 1] + events[..., 2], events[..., 0]
    ):
        raise ValueError("event diagnostics do not partition the 120 training sites")
    if any(value is False for value in bundle.run_summary.get("invariants", {}).values()):
        raise ValueError("the campaign reports a failed numerical or design invariant")


def load_campaign_bundle(input_dir: Path) -> CampaignBundle:
    summary = json.loads((input_dir / "run_summary.json").read_text(encoding="utf-8"))
    config_fields = dict(summary["config"])
    for name in ("rhos", "effects"):
        config_fields[name] = tuple(config_fields[name])
    profile_path = input_dir / "profiles.npz"
    with profile_path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    recorded_digest = summary.get("profile_bundle_sha256")
    if recorded_digest is not None and recorded_digest != digest:
        raise ValueError("saved profiles do not match the recorded campaign checksum")
    with np.load(profile_path, allow_pickle=False) as archive:
        profiles = {name: archive[name] for name in archive.files}
    bundle = CampaignBundle(
        BridgeConfig(**config_fields),
        tuple(BridgeTruth(**row) for row in summary["truths"]),
        profiles,
        summary,
        digest,
    )
    validate_bundle(bundle)
    return bundle


def support_metrics(
    drops: FloatArray, grid: FloatArray, truths: FloatArray, cutoffs: FloatArray
) -> dict[str, FloatArray]:
    """Summarize marginal supports; widths span their extrema even if disconnected."""
    # Axes are condition, analysis, complete evaluation history, candidate parameter.
    mask = drops <= cutoffs[:, :, None, None]
    if not mask.any(axis=-1).all():
        raise ValueError("a calibrated profile support is empty")
    truth_indices = np.asarray([np.flatnonzero(grid == truth)[0] for truth in truths])
    truth_included = np.take_along_axis(mask, truth_indices[:, None, None, None], axis=-1)
    first = np.argmax(mask, axis=-1)
    last = grid.size - 1 - np.argmax(mask[..., ::-1], axis=-1)
    components = mask[..., 0].astype(np.int64) + np.sum(mask[..., 1:] & ~mask[..., :-1], axis=-1)
    lower, upper = mask[..., 0], mask[..., -1]
    values = {
        "coverage": truth_included[..., 0],
        "log_interval_width": np.log(grid[last] / grid[first]),
        "lower_boundary_contact": lower,
        "upper_boundary_contact": upper,
        "boundary_contact": lower | upper,
        "support_components": components,
        "connected": components == 1,
        "connected_interior": (components == 1) & ~lower & ~upper,
    }
    if grid[0] == 1.0:
        values["no_effect_exclusion"] = ~lower
    return {name: np.asarray(value, dtype=np.float64) for name, value in values.items()}


def _aggregate(metrics: dict[str, FloatArray]) -> dict[str, FloatArray]:
    aggregate: dict[str, FloatArray] = {}
    for name, values in metrics.items():
        if name in ("absolute_log_error", "log_interval_width"):
            aggregate[f"mean_{name}"] = np.mean(values, axis=-1)
            aggregate[f"median_{name}"] = np.median(values, axis=-1)
        else:
            aggregate[name] = np.mean(values, axis=-1)
    return aggregate


def _evaluate(
    bundle: CampaignBundle, calibration_indices: IndexArray, evaluation_indices: IndexArray
) -> tuple[dict[str, FloatArray], dict[str, FloatArray], FloatArray, FloatArray]:
    profiles, rank = bundle.profiles, bundle.config.calibration_rank - 1
    effect_cutoffs = np.partition(
        profiles["calibration_effect_lr"][..., calibration_indices], rank, axis=-1
    )[..., rank]
    spread_cutoffs = np.partition(
        profiles["calibration_spread_lr"][..., calibration_indices], rank, axis=-1
    )[..., rank, None]
    effect_truths = np.asarray([truth.effect for truth in bundle.truths])
    spread_truths = np.asarray([truth.rho for truth in bundle.truths])
    effect = support_metrics(
        profiles["validation_effect_drops"][:, :, evaluation_indices, :],
        profiles["effects"],
        effect_truths,
        effect_cutoffs,
    )
    spread = support_metrics(
        profiles["validation_spread_drops"][:, None, evaluation_indices, :],
        profiles["rhos"],
        spread_truths,
        spread_cutoffs,
    )
    effect["absolute_log_error"] = np.abs(
        np.log(
            profiles["validation_effect_mle"][:, :, evaluation_indices]
            / effect_truths[:, None, None]
        )
    )
    spread["absolute_log_error"] = np.abs(
        np.log(
            profiles["validation_spread_mle"][:, None, evaluation_indices]
            / spread_truths[:, None, None]
        )
    )
    for metric, source in (
        ("conditional_prey_advantage", "conditional_advantage"),
        ("joint_advantage", "joint_advantage"),
    ):
        effect[metric] = profiles[source][:, :, evaluation_indices]
    return _aggregate(effect), _aggregate(spread), effect_cutoffs, spread_cutoffs


def paired_bootstrap(
    bundle: CampaignBundle, count: int = DEFAULT_BOOTSTRAPS, seed: int = DEFAULT_BOOTSTRAP_SEED
) -> BootstrapSamples:
    """Resample independent complete calibration/evaluation histories, never sites."""
    if count < 2:
        raise ValueError("at least two bootstrap resamples are required")
    rng = np.random.default_rng(seed)
    effect_samples: dict[str, list[FloatArray]] = {}
    spread_samples: dict[str, list[FloatArray]] = {}
    effect_cutoffs, spread_cutoffs, events = [], [], []
    for _ in range(count):
        calibration = rng.integers(
            bundle.config.calibration_replicates, size=bundle.config.calibration_replicates
        )
        evaluation = rng.integers(
            bundle.config.validation_replicates, size=bundle.config.validation_replicates
        )
        # One pair of independent index draws is shared by every condition and analysis.
        effect, spread, effect_cutoff, spread_cutoff = _evaluate(bundle, calibration, evaluation)
        for samples, metrics in ((effect_samples, effect), (spread_samples, spread)):
            for name, values in metrics.items():
                samples.setdefault(name, []).append(values)
        effect_cutoffs.append(effect_cutoff)
        spread_cutoffs.append(spread_cutoff)
        events.append(np.mean(bundle.profiles["event_diagnostics"][:, evaluation, :], axis=1))
    return BootstrapSamples(
        {name: np.asarray(values) for name, values in effect_samples.items()},
        {name: np.asarray(values) for name, values in spread_samples.items()},
        np.asarray(effect_cutoffs),
        np.asarray(spread_cutoffs),
        np.asarray(events),
    )


def _bounds(values: FloatArray) -> tuple[float, float]:
    lower, upper = np.quantile(values, (0.025, 0.975))
    return float(lower), float(upper)


def _condition_rows(
    bundle: CampaignBundle,
    metrics: dict[str, FloatArray],
    samples: dict[str, FloatArray],
    cutoffs: FloatArray,
    cutoff_samples: FloatArray,
    parameter: str,
) -> tuple[Row, ...]:
    rows: list[Row] = []
    lanes = LANES if parameter == "effect" else ("estimated_speed",)
    for c, truth in enumerate(bundle.truths):
        for lane_index, lane in enumerate(lanes):
            row: Row = {
                "condition_id": truth.condition_id,
                "truth_rho": truth.rho,
                "truth_effect": truth.effect,
                "role": truth.role,
                "parameter": parameter,
                "analysis": lane,
                "evaluation_count": bundle.config.validation_replicates,
                "calibration_count": bundle.config.calibration_replicates,
                "calibration_rank": bundle.config.calibration_rank,
                "calibrated_cutoff": float(cutoffs[c, lane_index]),
            }
            cutoff_lower, cutoff_upper = _bounds(cutoff_samples[:, c, lane_index])
            row.update(cutoff_bootstrap_lower=cutoff_lower, cutoff_bootstrap_upper=cutoff_upper)
            for name, values in metrics.items():
                row[name] = float(values[c, lane_index])
                lower, upper = _bounds(samples[name][:, c, lane_index])
                row[f"{name}_bootstrap_lower"] = lower
                row[f"{name}_bootstrap_upper"] = upper
            for name in ("coverage", "no_effect_exclusion"):
                if name in row:
                    successes = round(row[name] * bundle.config.validation_replicates)
                    interval = wilson_interval(successes, bundle.config.validation_replicates)
                    row[f"{name}_count"] = successes
                    row[f"{name}_wilson_lower"] = interval.lower
                    row[f"{name}_wilson_upper"] = interval.upper
            row["error_context_benchmark"] = 0.20 if parameter == "effect" else 0.10
            row["width_context_benchmark"] = 0.80 if parameter == "effect" else 0.50
            row["within_error_context"] = (
                row["median_absolute_log_error"] <= row["error_context_benchmark"]
            )
            row["within_width_context"] = (
                row["median_log_interval_width"] <= row["width_context_benchmark"]
            )
            row["effect_null_boundary_exempt"] = parameter == "effect" and truth.effect == 1.0
            rows.append(row)
    return tuple(rows)


def run_synthesis(
    bundle: CampaignBundle,
    *,
    bootstrap_count: int = DEFAULT_BOOTSTRAPS,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> SynthesisResult:
    validate_bundle(bundle)
    effect, spread, effect_cutoffs, spread_cutoffs = _evaluate(
        bundle,
        np.arange(bundle.config.calibration_replicates),
        np.arange(bundle.config.validation_replicates),
    )
    bootstrap = paired_bootstrap(bundle, bootstrap_count, bootstrap_seed)
    conditions = (
        *_condition_rows(
            bundle, effect, bootstrap.effect, effect_cutoffs, bootstrap.effect_cutoffs, "effect"
        ),
        *_condition_rows(
            bundle, spread, bootstrap.spread, spread_cutoffs, bootstrap.spread_cutoffs, "rho"
        ),
    )
    paired: list[Row] = []
    events: list[Row] = []
    interpretations: list[Row] = []
    for c, truth in enumerate(bundle.truths):
        for metric, label, units, deterioration in PRIMARY_METRICS:
            lower, upper = _bounds(
                bootstrap.effect[metric][:, c, 1] - bootstrap.effect[metric][:, c, 0]
            )
            paired.append(
                {
                    "condition_id": truth.condition_id,
                    "truth_rho": truth.rho,
                    "truth_effect": truth.effect,
                    "metric": metric,
                    "label": label,
                    "units": units,
                    "contrast": "estimated_speed_minus_known_speed",
                    "known_speed": float(effect[metric][c, 0]),
                    "estimated_speed": float(effect[metric][c, 1]),
                    "paired_mean_change": float(effect[metric][c, 1] - effect[metric][c, 0]),
                    "bootstrap_lower": lower,
                    "bootstrap_upper": upper,
                    "deterioration_direction": (
                        "positive"
                        if metric == "no_effect_exclusion" and truth.effect == 1.0
                        else deterioration
                    ),
                    "interval_excludes_zero": lower > 0 or upper < 0,
                }
            )
        event_row: Row = {
            "condition_id": truth.condition_id,
            "truth_rho": truth.rho,
            "truth_effect": truth.effect,
            "site_count": 120,
            "evaluation_count": bundle.config.validation_replicates,
        }
        for index, name in enumerate(EVENT_NAMES):
            lower, upper = _bounds(bootstrap.events[:, c, index])
            event_row[f"mean_{name}"] = float(
                np.mean(bundle.profiles["event_diagnostics"][c, :, index])
            )
            event_row[f"{name}_bootstrap_lower"] = lower
            event_row[f"{name}_bootstrap_upper"] = upper
        events.append(event_row)
        known, estimated = conditions[2 * c : 2 * c + 2]
        meets_context = [
            row["within_error_context"]
            and row["within_width_context"]
            and row["no_effect_exclusion"] >= 0.95
            for row in (known, estimated)
        ]
        if truth.effect == 1.0:
            context = "no_effect_control"
        elif all(meets_context):
            context = "both_meet_effect_context_benchmarks"
        elif not any(meets_context):
            context = "both_analyses_weak_by_effect_context"
        elif meets_context[0]:
            context = "additional_weakness_when_speed_is_estimated"
        else:
            context = "known_speed_only_weak_by_effect_context"
        interpretations.append({"condition_id": truth.condition_id, "secondary_context": context})
    cautions = []
    if not bundle.config.is_production:
        cautions.append("reduced_run_is_not_production_evidence")
    for row in conditions:
        identity = f"{row['condition_id']}:{row['analysis']}:{row['parameter']}"
        if row["coverage_wilson_upper"] < 0.95:
            cautions.append(f"coverage_below_nominal_wilson_signal:{identity}")
        if (
            row["parameter"] == "effect"
            and row["truth_effect"] == 1.0
            and row["no_effect_exclusion_wilson_lower"] > 0.05
        ):
            cautions.append(f"null_false_exclusion_above_nominal_wilson_signal:{identity}")
    return SynthesisResult(
        bundle,
        conditions,
        tuple(paired),
        tuple(events),
        tuple(interpretations),
        tuple(cautions),
        bootstrap_count,
        bootstrap_seed,
        bootstrap,
        (
            "bridge_complete"
            if bundle.config.is_production
            else f"non_scientific_{bundle.run_summary.get('mode', 'reduced')}"
        ),
    )


def _case_label(truth: BridgeTruth) -> str:
    return f"{'Usual' if truth.rho == 1 else 'Half'} speed, {truth.effect:g}x effect"


def _summary(result: SynthesisResult) -> Row:
    source = result.bundle.run_summary
    return {
        "outcome": result.outcome,
        "is_production": result.bundle.config.is_production,
        "mode": source.get("mode"),
        "condition_count": len(result.bundle.truths),
        "condition_summary_rows": len(result.conditions),
        "paired_contrast": "estimated_speed_minus_known_speed",
        "primary_estimand": "mean of complete-dataset paired changes",
        "interval_type": "parameter-specific locally calibrated 95% profile supports",
        "intervals_are_simultaneous_or_bayesian": False,
        "bootstrap": {
            "count": result.bootstrap_count,
            "seed": result.bootstrap_seed,
            "confidence_level": 0.95,
            "method": "percentile",
            "resampling_unit": "complete simulated dataset",
            "calibration_and_evaluation_resampled_independently": True,
            "indices_shared_across_all_conditions_and_analyses": True,
            "cutoffs_recomputed_in_every_resample": True,
            "conditional_on_integration_bank_and_generating_model": True,
        },
        "config": asdict(result.bundle.config),
        "truths": [asdict(truth) for truth in result.bundle.truths],
        "provenance": {
            "source_commit": source.get("source_commit"),
            "bank_checksum": source.get("bank_checksum"),
            "profile_bundle_sha256": result.bundle.profile_sha256,
        },
        "caution_flags": result.caution_flags,
        "caution_interpretation": (
            "Wilson signals are descriptive calibration-review prompts, not hard completion gates; "
            "magnitude and Monte Carlo uncertainty must be judged together."
        ),
        "case_interpretations": result.case_interpretations,
        "conditions": result.conditions,
        "paired_effect_changes": result.paired_changes,
        "event_information": result.event_information,
    }


def _report(result: SynthesisResult) -> str:
    config = result.bundle.config
    lines = [
        "# The cost of estimating predator spread speed",
        "",
        f"Automated synthesis classification: **{result.outcome}**. "
        f"Six cases with {config.calibration_replicates} calibration and "
        f"{config.validation_replicates} evaluation datasets per case. "
        "This classification does not establish numerical acceptance or scientific closeout; "
        "those require the separate numerical and scientific reviews recorded in Goal 045.",
        "",
        "## What was compared",
        "",
        "The same observations were analysed with spread speed supplied at its true value and "
        "with speed estimated together with prey effect. Rho=1 is usual spread and rho=0.5 is "
        "half speed. Effects of 1x, 3x, and 5x multiply prey loss hazard after predator arrival; "
        "1x is the no-effect control. Background hazard is known at 0.002/day (11.3% 60-day "
        "loss risk without predators), and both detection probabilities are known at 0.65.",
        "",
        "All fitting uses the same 120 training sites. The 40 cluster-isolated holdout sites "
        "only evaluate prediction. Both analyses keep predator arrival latent, share the "
        "candidate arrival between species within a site, and use a site-marginal composite "
        "likelihood without claiming spatial independence of the observed sites. Previous "
        "all-160-site summaries are contextual comparisons, not exact replay targets.",
        "",
        "## Primary paired changes",
        "",
        "Each change is estimated-speed minus supplied-speed, averaged over paired complete "
        "evaluation datasets. Positive error or width changes are deterioration; negative "
        "coverage, no-effect exclusion, or conditional prey score changes are deterioration "
        "for non-null effects. In no-effect controls, a positive exclusion change is worse "
        "because it means more false alarms. An interval excluding "
        "zero indicates a detectable difference, not necessarily a material ecological penalty.",
        "",
        "| Case | Error change | Log-width change | Coverage change (pp) | Exclusion change (pp) "
        "| Prey score change (nats/site) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for truth in result.bundle.truths:
        rows = [row for row in result.paired_changes if row["condition_id"] == truth.condition_id]
        formatted = []
        for row in rows:
            scale = 100.0 if row["units"] == "proportion" else 1.0
            precision = {
                "mean_absolute_log_error": 4,
                "conditional_prey_advantage": 5,
            }.get(row["metric"], 3)
            formatted.append(
                f"{scale * row['paired_mean_change']:+.{precision}f} "
                f"[{scale * row['bootstrap_lower']:+.{precision}f}, "
                f"{scale * row['bootstrap_upper']:+.{precision}f}]"
            )
        lines.append(f"| {_case_label(truth)} | " + " | ".join(formatted) + " |")
    lines.extend(
        [
            "",
            f"Brackets are 95% percentile intervals from {result.bootstrap_count} "
            "bootstrap resamples. "
            "Complete calibration dataset indices and complete evaluation dataset indices are "
            "sampled independently; each draw is shared across all six cases and both analyses. "
            "Separate effect cutoffs for both analyses and the estimated-speed rho cutoff are "
            "recomputed in every resample. No sites are resampled, simulated, or refitted. "
            "Uncertainty includes calibration-sample variation but remains conditional on this "
            "integration bank and generating model.",
            f"The saved run uses {config.bank_size} arrival integration draws "
            "with no additional draws during synthesis.",
            "",
            "Primary prediction is the holdout-site mean of log P(prey,predator | training fit) "
            "minus log P(predator | that same fit). Holdout predator observations are permissible "
            "conditioning information; holdout prey observations only score predictions. The "
            "matched no-effect model uses the same known background and detection information; "
            "its conditional prey score is independent of rho and identical between analyses. "
            "The saved advantage is relative to that common null, so its paired change is also "
            "the paired change in conditional prey score. Secondary joint-score advantages use "
            "the null's own training-only rho estimate when speed is estimated.",
            "",
            "## Intervals and calibration",
            "",
            f"Each case uses {config.calibration_replicates} calibration and "
            f"{config.validation_replicates} independent evaluation datasets, with order statistic "
            f"{config.calibration_rank}/{config.calibration_replicates} as each local cutoff "
            "(239/250 in production). These are 95% parameter-specific, marginal calibrated "
            "profile intervals, not Bayesian intervals or a simultaneous joint region. Calibration "
            "still knows the generating condition: the experiment relaxes the process oracle, "
            "but does not establish field-ready calibration. Grid support is retained exactly; "
            "reported log width is log(upper/lower) across support extrema, with disconnected "
            "components and boundary contacts reported separately. Endpoints, connectivity "
            "and widths describe the discrete fitting grid; continuous-profile endpoints "
            "have not been validated.",
            "",
            "| No-effect control | Analysis | False exclusions / datasets | "
            "Rate [95% Wilson interval] |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for row in result.conditions:
        if row["parameter"] == "effect" and row["truth_effect"] == 1.0:
            lines.append(
                f"| {row['condition_id']} | {LANE_LABELS[row['analysis']]} | "
                f"{row['no_effect_exclusion_count']}/{row['evaluation_count']} | "
                f"{row['no_effect_exclusion']:.3f} "
                f"[{row['no_effect_exclusion_wilson_lower']:.3f}, "
                f"{row['no_effect_exclusion_wilson_upper']:.3f}] |"
            )
    lines.extend(
        [
            "",
            "Coverage and false-exclusion Wilson intervals describe evaluation Monte Carlo "
            "uncertainty at the realised cutoff; the accompanying bootstrap intervals also include "
            "calibration variation. Coverage is not required to have a Wilson interval containing "
            "0.95 in every case. Signals below nominal coverage or above 5% null false exclusion "
            "are prompts to examine magnitude and uncertainty, not automatic failure. Physical "
            "boundary contact at effect=1 is expected under the null and has no interior "
            "requirement.",
            "",
            "## Secondary context",
            "",
            "The condition table contains median absolute log error and median log interval width "
            "for both effect analyses and for rho when estimated. Reference benchmarks are effect "
            "error 0.20 and width 0.80, rho error 0.10 and width 0.50, and approximately 95% "
            "coverage/exclusion. These labels are descriptive context, not scientific completion "
            "criteria; exclusion is not a desired outcome for the no-effect controls.",
            "",
        ]
    )
    for row in result.case_interpretations:
        lines.append(f"- {row['condition_id']}: {row['secondary_context'].replace('_', ' ')}.")
    lines.extend(
        [
            "",
            "Both-analyses-weak cases already have weak effect recovery with speed supplied; "
            "their total weakness cannot be attributed to estimating speed. Added estimation "
            "cost is assessed by the paired continuous changes, including when both analyses are "
            "weak. Differences between usual and half-speed generating waves are explanatory "
            "comparisons, not causal evidence for a specific event-yield mechanism. No case is "
            "required or retuned to become recovered.",
            "",
            "## Figures and event information",
            "",
            "`paired_recovery.svg`: dots show paired mean changes and bars show their 95% "
            "calibration-aware bootstrap intervals. The first five panels use estimated minus "
            "supplied speed; percentage-point axes multiply proportions by 100. The final panel "
            "shows mean true post-arrival prey losses among 120 training sites, with evaluation "
            "bootstrap intervals. Colours identify generating wave speed, not analysis lane.",
            "",
            "`representative_likelihoods.svg`: each panel uses evaluation dataset index 0, chosen "
            "in advance for all cases. Colours show twice the joint training log-likelihood loss "
            "from that panel's maximum, not a confidence region. Crosses mark generating values, "
            "circles mark joint maximum-likelihood fits, and dashed lines show supplied speed. "
            "Every panel displays rho from 0.8 to 1.2 times its generating speed, with the same "
            "relative scale in both rows. The full fitting domain remains "
            f"rho={config.rhos[0]:g} to {config.rhos[-1]:g} and effect="
            f"{config.effects[0]:g} to {config.effects[-1]:g}; "
            "the display zoom does not alter fitting.",
            "",
            "`event_information.csv` reports true loss counts by day 60, pre-arrival and "
            "post-arrival loss counts, censored sites, post-arrival at-risk exposure in site-days, "
            "and summed prey detections, all over 120 training sites. These are truth-assisted "
            "explanatory "
            "diagnostics and never inference inputs. Absorbing prey extirpation means later "
            "detections are unavailable after a true loss.",
            "",
            "## Calibration review signals",
            "",
            *(
                [f"- {flag}" for flag in result.caution_flags]
                or ["No descriptive Wilson signals flagged."]
            ),
            "",
            f"Profiles SHA-256: `{result.bundle.profile_sha256}`. "
            f"Source commit: `{result.bundle.run_summary.get('source_commit', 'not recorded')}`.",
            "",
        ]
    )
    return "\n".join(lines)


def paired_recovery_figure(result: SynthesisResult) -> Figure:
    figure, axes = plt.subplots(2, 3, figsize=(15.5, 9.5))
    y = np.arange(len(result.bundle.truths))
    labels = [_case_label(truth) for truth in result.bundle.truths]
    for axis, (metric, title, units, _) in zip(axes.flat, PRIMARY_METRICS, strict=False):
        rows = [row for row in result.paired_changes if row["metric"] == metric]
        scale = 100.0 if units == "proportion" else 1.0
        for index, row in enumerate(rows):
            color = WAVE_COLORS[row["truth_rho"]]
            axis.hlines(
                index,
                scale * row["bootstrap_lower"],
                scale * row["bootstrap_upper"],
                color=color,
                linewidth=2,
            )
            axis.plot(scale * row["paired_mean_change"], index, "o", color=color, markersize=6)
        axis.axvline(0, color="#555555", linestyle="--", linewidth=0.8)
        axis.set_title(title, loc="left", fontsize=12, fontweight="bold")
        axis.set_xlabel(
            "Change (percentage points)" if units == "proportion" else f"Change ({units})"
        )
    event_axis = axes.flat[5]
    for index, row in enumerate(result.event_information):
        name = "post_arrival_true_extirpations"
        color = WAVE_COLORS[row["truth_rho"]]
        event_axis.hlines(
            index,
            row[f"{name}_bootstrap_lower"],
            row[f"{name}_bootstrap_upper"],
            color=color,
            linewidth=2,
        )
        event_axis.plot(row[f"mean_{name}"], index, "o", color=color, markersize=6)
    event_axis.set_title(
        "True post-arrival prey losses", loc="left", fontsize=12, fontweight="bold"
    )
    event_axis.set_xlabel("Mean losses by day 60\n(out of 120 training sites)")
    for axis in axes.flat:
        axis.set_yticks(y, labels, fontsize=9)
        axis.set_ylim(5.6, -0.6)
        axis.axhline(2.5, color="#DDDDDD", linewidth=0.7)
        axis.grid(axis="x", color="#EEEEEE", linewidth=0.7)
        axis.set_axisbelow(True)
        axis.spines[["top", "right"]].set_visible(False)
    figure.suptitle(
        "When spread speed is estimated: paired changes in prey-effect recovery",
        fontsize=16,
        x=0.04,
        ha="left",
        y=0.99,
    )
    figure.legend(
        handles=[
            Line2D([], [], marker="o", linestyle="none", color=color, label=label)
            for label, color in (
                ("Usual spread (rho = 1)", WAVE_COLORS[1.0]),
                ("Half-speed spread (rho = 0.5)", WAVE_COLORS[0.5]),
            )
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.955),
        ncol=2,
        frameon=False,
    )
    figure.text(
        0.04,
        0.025,
        "First five panels: estimated minus supplied speed. Dots = paired means; bars = 95% "
        "bootstrap intervals with calibration and evaluation resampled.\n"
        "Higher error/width is worse; lower coverage/exclusion/prey score is worse for non-null "
        "effects. Null exclusions are false alarms. Final panel: event means, not changes.",
        fontsize=9,
    )
    figure.tight_layout(rect=(0.02, 0.085, 0.99, 0.92), w_pad=2.0, h_pad=2.2)
    return figure


def representative_likelihood_figure(result: SynthesisResult) -> Figure:
    figure, axes = plt.subplots(2, 3, figsize=(14.5, 9))
    rhos, effects = result.bundle.profiles["rhos"], result.bundle.profiles["effects"]
    for index, (axis, truth) in enumerate(zip(axes.flat, result.bundle.truths, strict=True)):
        likelihood = result.bundle.profiles["validation_train_joint"][index, 0]
        loss = 2 * (np.max(likelihood) - likelihood)
        mesh = axis.pcolormesh(
            effects, rhos, loss, shading="nearest", cmap="viridis", vmin=0, vmax=12, rasterized=True
        )
        rho_index, effect_index = np.unravel_index(np.argmax(likelihood), likelihood.shape)
        axis.axhline(truth.rho, color="white", linestyle="--", linewidth=1)
        axis.plot(truth.effect, truth.rho, "x", color="#EF4939", markersize=9, markeredgewidth=2)
        axis.plot(
            effects[effect_index],
            rhos[rho_index],
            "o",
            markerfacecolor="none",
            markeredgecolor="white",
            markeredgewidth=1.7,
            markersize=10,
        )
        axis.set_yscale("log", base=2)
        ticks = truth.rho * np.asarray([0.8, 0.9, 1.0, 1.1, 1.2])
        axis.set_yticks(ticks, [f"{value:g}" for value in ticks])
        axis.set_xlim(float(effects[0]) - 0.25, float(effects[-1]) + 0.25)
        axis.set_ylim(0.8 * truth.rho, 1.2 * truth.rho)
        axis.set_title(_case_label(truth), loc="left", fontsize=12, fontweight="bold")
        axis.set_xlabel("Prey loss hazard multiplier")
        axis.set_ylabel("Relative predator spread speed (rho)")
    figure.subplots_adjust(left=0.07, right=0.87, bottom=0.16, top=0.86, hspace=0.38, wspace=0.30)
    color_axis = figure.add_axes((0.90, 0.24, 0.016, 0.55))
    colorbar = figure.colorbar(mesh, cax=color_axis, extend="max")
    colorbar.set_label("Twice the log-likelihood loss from the panel maximum")
    figure.suptitle(
        "Likelihood trade-offs in the first evaluation dataset",
        x=0.07,
        ha="left",
        fontsize=16,
        y=0.98,
    )
    figure.legend(
        handles=[
            Line2D([], [], marker="x", color="#EF4939", linestyle="none", label="Generating truth"),
            Line2D(
                [],
                [],
                marker="o",
                color="#555555",
                markerfacecolor="none",
                linestyle="none",
                label="Joint training-fit maximum",
            ),
            Line2D([], [], color="#555555", linestyle="--", label="Supplied true speed"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.48, 0.945),
        ncol=3,
        frameon=False,
    )
    figure.text(
        0.07,
        0.055,
        "Prespecified evaluation dataset 0; likelihood uses its 120 training sites. "
        "Display: rho is 0.8 to 1.2 times generating rho.\n"
        f"Full fitting domain: rho {rhos[0]:g} to {rhos[-1]:g}; "
        f"prey hazard multiplier {effects[0]:g} to {effects[-1]:g}.\n"
        "Colours show joint composite likelihood loss from each full-grid maximum, "
        "not a calibrated confidence region.",
        fontsize=10,
    )
    return figure


def _write_csv(path: Path, rows: tuple[Row, ...]) -> None:
    fields = list(dict.fromkeys(name for row in rows for name in row))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_review_bundle(
    result: SynthesisResult, output_dir: Path = DEFAULT_OUTPUT_DIR
) -> tuple[Path, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, rows in (
        ("condition_summary.csv", result.conditions),
        ("paired_effect_changes.csv", result.paired_changes),
        ("event_information.csv", result.event_information),
    ):
        path = output_dir / name
        _write_csv(path, rows)
        written.append(path)
    summary_path, report_path = output_dir / "summary.json", output_dir / "report.md"
    summary_path.write_text(
        json.dumps(_summary(result), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(_report(result), encoding="utf-8")
    written.extend((summary_path, report_path))
    with mpl.rc_context({"svg.hashsalt": "latent-landscapes-arc2c", "svg.fonttype": "none"}):
        for name, make_figure in (
            ("paired_recovery.svg", paired_recovery_figure),
            ("representative_likelihoods.svg", representative_likelihood_figure),
        ):
            figure = make_figure(result)
            path = output_dir / name
            figure.savefig(path, format="svg", metadata={"Date": None})
            plt.close(figure)
            written.append(path)
    return tuple(written)
