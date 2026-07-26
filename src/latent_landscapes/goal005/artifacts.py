"""Deterministic 15-file review bundle for Goal 005."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.figure import Figure

from .benchmark import BANK_VARIANT_NAMES, SOURCE_IDENTITY, Goal005Result

DEFAULT_OUTPUT_DIR = Path("artifacts/goal005_stochastic_one_rate_cross_rate")
ROOT_FILES = (
    "config.json",
    "seed_manifest.csv",
    "calibration_results.csv",
    "validation_results.csv",
    "rate_summary.csv",
    "transported_cutoff_summary.csv",
    "predictive_summary.csv",
    "observation_signal_summary.csv",
    "representative_profile.csv",
    "summary.json",
    "verification.json",
    "review.md",
)
VISUAL_FILES = (
    "local_recovery_across_rates.svg",
    "cutoff_transportability.svg",
    "predictive_comparison.svg",
)
EXPECTED_FILE_COUNT = 15
BETWEEN_SITE_LIMITATION = "omitted"
CsvValue = str | int | float | bool
CsvRow = Mapping[str, CsvValue]


def write_review_bundle(
    result: Goal005Result, output_dir: str | Path = DEFAULT_OUTPUT_DIR
) -> tuple[Path, ...]:
    if result.outcome == "implementation_blocked":
        raise ValueError("an implementation-blocked result has no scientific review bundle")
    target = Path(output_dir)
    visuals = target / "visuals"
    visuals.mkdir(parents=True, exist_ok=True)
    paths = {**{n: target / n for n in ROOT_FILES}, **{n: visuals / n for n in VISUAL_FILES}}
    paths["verification.json"].unlink(missing_ok=True)
    _write_json(paths["config.json"], _config(result))
    _write_csv(paths["seed_manifest.csv"], _seed_rows(result))
    _write_csv(paths["calibration_results.csv"], _calibration_rows(result))
    _write_csv(paths["validation_results.csv"], _validation_rows(result))
    _write_csv(paths["rate_summary.csv"], _rate_rows(result))
    _write_csv(paths["transported_cutoff_summary.csv"], _transport_rows(result))
    _write_csv(paths["predictive_summary.csv"], _predictive_rows(result))
    _write_csv(paths["observation_signal_summary.csv"], _signal_rows(result))
    _write_csv(paths["representative_profile.csv"], _representative_rows(result))
    _write_json(paths["summary.json"], _summary(result))
    paths["review.md"].write_text(_review(result), encoding="utf-8")
    paths["local_recovery_across_rates.svg"].write_text(_local_svg(result), encoding="utf-8")
    paths["cutoff_transportability.svg"].write_text(_transport_svg(result), encoding="utf-8")
    paths["predictive_comparison.svg"].write_text(_predictive_svg(result), encoding="utf-8")
    expected = {*ROOT_FILES, *(f"visuals/{n}" for n in VISUAL_FILES)}
    observed = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
    if observed != expected - {"verification.json"}:
        raise RuntimeError(f"artifact contract mismatch before verification: {sorted(observed)}")
    _write_json(
        paths["verification.json"],
        {
            "expected_artifact_file_count": EXPECTED_FILE_COUNT,
            "observed_artifact_file_count": EXPECTED_FILE_COUNT,
            "invariants": result.invariants,
            "all_invariants_pass": all(result.invariants.values()),
            "central_reconciliation": result.central_reconciliation,
            "method_label": "site-history simulated composite likelihood",
            "full_joint_spatial_likelihood_claimed": False,
            "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        },
    )
    observed = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
    if observed != expected:
        raise RuntimeError(f"artifact contract mismatch: {sorted(observed)}")
    return tuple(paths[n] for n in (*ROOT_FILES, *VISUAL_FILES))


def _config(result: Goal005Result) -> dict[str, object]:
    c = result.config
    return {
        "goal": "005-stochastic-one-rate-cross-rate-recovery",
        "method": "site-history simulated composite likelihood",
        "is_full_joint_spatial_likelihood": False,
        "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        "source_identity": SOURCE_IDENTITY,
        "master_seed": c.master_seed,
        "central_goal004_master_seed": 20260728,
        "truth_rates": list(c.truth_rates),
        "truth_grid_indices": list(c.truth_indices),
        "integration_bank_size": c.bank_size,
        "half_bank_size": c.half_bank_size,
        "calibration_replicates": c.calibration_replicates,
        "validation_replicates": c.validation_replicates,
        "calibration_rank_one_based": c.calibration_rank_one_based,
        "survey_times": list((10, 20, 30, 40, 50, 60)),
        "detection_probability": 0.65,
        "false_positive_probability": 0.0,
        "rate_domain": [c.rates[0], c.rates[-1]],
        "rate_grid_size": len(c.rates),
        "production_configuration": c.is_production,
        "local_calibration_scope": "truth-specific cutoff at each prespecified generating rate",
        "transported_cutoff_scope": (
            "rho = 1 full/half-bank cutoffs applied only to flank validation"
        ),
    }


def _seed_rows(result: Goal005Result) -> list[CsvRow]:
    rows: list[CsvRow] = []
    for s in result.seed_manifest.stream_records:
        rows.append(
            {
                "phase": s.phase,
                "truth_rate": next(
                    (
                        d.truth_rate
                        for d in result.seed_manifest.datasets
                        if d.process is s or d.detection is s
                    ),
                    1.0,
                ),
                "index": s.index,
                "stream_role": s.stream_role,
                "entropy": s.entropy,
                "spawn_key": json.dumps(s.spawn_key, separators=(",", ":")),
                "pool_size": s.pool_size,
                "state_words": json.dumps(s.state_words, separators=(",", ":")),
                "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
            }
        )
    return rows


def _calibration_rows(result: Goal005Result) -> list[CsvRow]:
    return [
        {
            "truth_rate": r.truth_rate,
            "dataset_index": r.dataset_index,
            "bank_variant": r.bank_variant,
            "record_count": r.record_count,
            "truth_grid_index": r.truth_grid_index,
            "lr_at_truth": r.lr_at_truth,
            "truth_log_likelihood": r.truth_log_likelihood,
            "maximum_log_likelihood": r.maximum_log_likelihood,
            "mle_indices": json.dumps(r.mle_indices, separators=(",", ":")),
            "mle_rates": json.dumps(r.mle_rates, separators=(",", ":")),
            "occupied_fraction_mean": r.occupied_fraction_mean,
            "occupied_fraction_lower": r.occupied_fraction_lower,
            "occupied_fraction_upper": r.occupied_fraction_upper,
            "detection_fraction_mean": r.detection_fraction_mean,
            "detection_fraction_lower": r.detection_fraction_lower,
            "detection_fraction_upper": r.detection_fraction_upper,
            "no_false_positives": r.no_false_positives,
            "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        }
        for r in result.calibration_results
    ]


def _validation_rows(result: Goal005Result) -> list[CsvRow]:
    return [
        {
            "truth_rate": r.truth_rate,
            "cutoff_source_rate": r.cutoff_source_rate,
            "dataset_index": r.dataset_index,
            "bank_variant": r.bank_variant,
            "record_count": r.record_count,
            "training_record_count": r.training_record_count,
            "holdout_record_count": r.holdout_record_count,
            "split_isolated": r.split_isolated,
            "truth_grid_index": r.truth_grid_index,
            "lr_at_truth": r.lr_at_truth,
            "truth_included": r.truth_included,
            "support_component_count": r.support_component_count,
            "support_boundary_contact": r.support_boundary_contact,
            "support_arithmetic_width": r.support_arithmetic_width,
            "support_log_rate_width": r.support_log_rate_width,
            "support_indices": json.dumps(r.support_indices, separators=(",", ":")),
            "mle_indices": json.dumps(r.mle_indices, separators=(",", ":")),
            "mle_rates": json.dumps(r.mle_rates, separators=(",", ":")),
            "truth_to_mle_set_distance": r.truth_to_mle_set_distance,
            "absolute_log_rate_error": r.absolute_log_rate_error,
            "training_mle_indices": json.dumps(r.training_mle_indices, separators=(",", ":")),
            "training_mle_rates": json.dumps(r.training_mle_rates, separators=(",", ":")),
            "stochastic_brier_maximum": r.stochastic_brier_maximum,
            "neutral_brier_score": r.neutral_brier_score,
            "stochastic_log_score_maximum": r.stochastic_log_score_maximum,
            "neutral_log_score": r.neutral_log_score,
            "paired_brier_difference": r.paired_brier_difference,
            "occupied_fraction_mean": r.occupied_fraction_mean,
            "occupied_fraction_lower": r.occupied_fraction_lower,
            "occupied_fraction_upper": r.occupied_fraction_upper,
            "detection_fraction_mean": r.detection_fraction_mean,
            "detection_fraction_lower": r.detection_fraction_lower,
            "detection_fraction_upper": r.detection_fraction_upper,
            "no_false_positives": r.no_false_positives,
            "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        }
        for r in result.validation_results
    ]


def _rate_rows(result: Goal005Result) -> list[CsvRow]:
    return [
        {
            "truth_rate": s.truth_rate,
            "bank_variant": s.bank_variant,
            "cutoff_source_rate": s.cutoff_source_rate,
            "transported": s.transported,
            "cutoff": s.cutoff,
            "coverage_count": s.coverage_count,
            "coverage_estimate": s.coverage.estimate,
            "coverage_wilson_lower": s.coverage.lower,
            "coverage_wilson_upper": s.coverage.upper,
            "topology_count": s.topology_count,
            "boundary_contacts": s.boundary_contacts,
            "mean_arithmetic_width": s.mean_arithmetic_width,
            "mean_log_rate_width": s.mean_log_rate_width,
            "mean_abs_log_error": s.mean_abs_log_error,
            "paired_brier_estimate": s.paired_brier.estimate,
            "paired_brier_lower": s.paired_brier.lower,
            "paired_brier_upper": s.paired_brier.upper,
            "downstream_class": s.downstream_class,
            "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        }
        for s in result.cutoff_summaries
        if not s.transported
    ]


def _transport_rows(result: Goal005Result) -> list[CsvRow]:
    return [
        {
            "truth_rate": s.truth_rate,
            "bank_variant": s.bank_variant,
            "cutoff_source_rate": s.cutoff_source_rate,
            "cutoff": s.cutoff,
            "coverage_count": s.coverage_count,
            "coverage_estimate": s.coverage.estimate,
            "coverage_wilson_lower": s.coverage.lower,
            "coverage_wilson_upper": s.coverage.upper,
            "topology_count": s.topology_count,
            "boundary_contacts": s.boundary_contacts,
            "mean_log_rate_width": s.mean_log_rate_width,
            "downstream_class": s.downstream_class,
            "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        }
        for s in result.cutoff_summaries
        if s.transported
    ]


def _predictive_rows(result: Goal005Result) -> list[CsvRow]:
    rows: list[CsvRow] = []
    for s in result.cutoff_summaries:
        if not s.transported:
            rows.append(
                {
                    "truth_rate": s.truth_rate,
                    "bank_variant": s.bank_variant,
                    "validation_replicates": result.config.validation_replicates,
                    "mean_paired_brier": s.paired_brier.estimate,
                    "paired_brier_lower": s.paired_brier.lower,
                    "paired_brier_upper": s.paired_brier.upper,
                    "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
                }
            )
    return rows


def _signal_rows(result: Goal005Result) -> list[CsvRow]:
    return [
        {
            "truth_rate": r.truth_rate,
            "survey_time": r.survey_time,
            "occupied_fraction_mean": r.occupied_fraction_mean,
            "occupied_fraction_lower": r.occupied_fraction_lower,
            "occupied_fraction_upper": r.occupied_fraction_upper,
            "detection_fraction_mean": r.detection_fraction_mean,
            "detection_fraction_lower": r.detection_fraction_lower,
            "detection_fraction_upper": r.detection_fraction_upper,
            "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        }
        for r in result.observation_signals
    ]


def _representative_rows(result: Goal005Result) -> list[CsvRow]:
    rows: list[CsvRow] = []
    for p in result.representative_profiles:
        support = set(p.summary.support_indices)
        for i, rate in enumerate(p.profile.rates):
            rows.append(
                {
                    "truth_rate": p.truth_rate,
                    "bank_variant": p.bank_variant,
                    "cutoff_source_rate": p.cutoff_source_rate,
                    "dataset_index": 0,
                    "rate_index": i,
                    "rho": float(rate),
                    "relative_lr": float(
                        2 * (p.profile.maximum_log_likelihood - p.profile.log_likelihoods[i])
                    ),
                    "in_local_support": i in support,
                    "in_mle_set": i in p.profile.mle_indices,
                    "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
                }
            )
    return rows


def _summary(result: Goal005Result) -> dict[str, object]:
    return {
        "outcome": result.outcome,
        "method": "site-history simulated composite likelihood",
        "between_site_process_dependence": BETWEEN_SITE_LIMITATION,
        "truth_rates": list(result.config.truth_rates),
        "central_reconciliation": result.central_reconciliation,
        "local_rate_summaries": [
            {
                "truth_rate": s.truth_rate,
                "bank_variant": s.bank_variant,
                "coverage": s.coverage.estimate,
                "coverage_wilson": [s.coverage.lower, s.coverage.upper],
                "mean_log_rate_width": s.mean_log_rate_width,
                "paired_brier": s.paired_brier.estimate,
                "paired_brier_interval": [s.paired_brier.lower, s.paired_brier.upper],
                "class": s.downstream_class,
            }
            for s in result.cutoff_summaries
            if not s.transported
        ],
        "transported_flank_summaries": [
            {
                "truth_rate": s.truth_rate,
                "bank_variant": s.bank_variant,
                "coverage": s.coverage.estimate,
                "coverage_wilson": [s.coverage.lower, s.coverage.upper],
                "class": s.downstream_class,
            }
            for s in result.cutoff_summaries
            if s.transported
        ],
    }


def _review(result: Goal005Result) -> str:
    lines = [
        "# Goal 005 Stochastic One-Rate Recovery Across Generating Rates",
        "",
        f"**Outcome:** `{result.outcome}`",
        "",
        "## Observations",
        "The frozen landscape, calendar (10, 20, 30, 40, 50, 60), known "
        "detection (0.65), and one shared 4,096-draw integration bank were "
        "retained. The three generating rates are 0.5, 1, and 2. "
        "Observation-window summaries are reported separately by truth rate.",
        "",
        "## Inference",
        "Local cutoffs are calibrated separately at each prespecified truth "
        "rate. Transported cutoffs use only the rho = 1 cutoff and are "
        "reported separately; they are not operational uncertainty away from "
        "rho = 1. The fitted object is a site-history simulated composite "
        "likelihood, not a full joint spatial likelihood.",
        "",
        "| truth | bank | local coverage | log-width | paired Brier interval | class |",
        "| ---: | --- | ---: | ---: | --- | --- |",
    ]
    for s in result.cutoff_summaries:
        if not s.transported:
            lines.append(
                f"| {s.truth_rate:g} | {s.bank_variant} | "
                f"{s.coverage.estimate:.3f} [{s.coverage.lower:.3f}, "
                f"{s.coverage.upper:.3f}] | {s.mean_log_rate_width:.4g} | "
                f"{s.paired_brier.lower:.4g}, {s.paired_brier.upper:.4g} | "
                f"{s.downstream_class} |"
            )
    lines += [
        "",
        "## Assumptions",
        "The Goal 004 process, detection model, grid, cluster split, neutral "
        "comparator, and finite integration bank are frozen. Flank datasets "
        "use fresh disjoint SeedSequence(20260729) phase roots.",
        "",
        "## Uncertainty",
        "Local Wilson intervals describe repeated validation at each fixed "
        "generating rate. They do not establish a single operational cutoff "
        "when the true rate is unknown. Transported intervals are diagnostic "
        "only.",
        "",
        "## Limitations",
        "Between-site process dependence is omitted from the fitted composite "
        "likelihood. Results are conditional on one landscape and one "
        "observation design. Sparse or saturated regimes are scientific "
        "outcomes, not reasons for retuning.",
    ]
    return "\n".join(lines) + "\n"


def _local_svg(result: Goal005Result) -> str:
    with plt.rc_context(
        {"svg.hashsalt": "latent-landscapes-goal005", "svg.fonttype": "none", "font.size": 9}
    ):
        fig, ax = plt.subplots(figsize=(9, 5), layout="constrained")
        for name in BANK_VARIANT_NAMES:
            rows = [
                s for s in result.cutoff_summaries if not s.transported and s.bank_variant == name
            ]
            ax.plot(
                [s.truth_rate for s in rows],
                [s.coverage.estimate for s in rows],
                "o-",
                label=name.replace("_", " "),
            )
        ax.axhline(0.95, color="#222", ls="--")
        ax.set_xlabel("generating spread-rate multiplier rho")
        ax.set_ylabel("local calibrated truth coverage")
        ax.set_title(
            "Local recovery across generating rates\n"
            "site-history composite likelihood; between-site dependence omitted"
        )
        ax.legend()
        return _figure_svg(fig)


def _transport_svg(result: Goal005Result) -> str:
    with plt.rc_context(
        {"svg.hashsalt": "latent-landscapes-goal005", "svg.fonttype": "none", "font.size": 9}
    ):
        fig, ax = plt.subplots(figsize=(9, 5), layout="constrained")
        for name in BANK_VARIANT_NAMES:
            rows = [s for s in result.cutoff_summaries if s.transported and s.bank_variant == name]
            ax.plot(
                [s.truth_rate for s in rows],
                [s.coverage.estimate for s in rows],
                "o-",
                label=f"{name.replace('_', ' ')}; cutoff source rho=1",
            )
        ax.axhline(0.95, color="#222", ls="--")
        ax.set_xlabel("flank generating rate rho")
        ax.set_ylabel("coverage using transported rho = 1 cutoff")
        ax.set_title("Cutoff transportability\ndiagnostic, not operational calibration")
        ax.legend()
        return _figure_svg(fig)


def _predictive_svg(result: Goal005Result) -> str:
    with plt.rc_context(
        {"svg.hashsalt": "latent-landscapes-goal005", "svg.fonttype": "none", "font.size": 9}
    ):
        fig, ax = plt.subplots(figsize=(9, 5), layout="constrained")
        for name in BANK_VARIANT_NAMES:
            rows = [
                s for s in result.cutoff_summaries if not s.transported and s.bank_variant == name
            ]
            ax.plot(
                [s.truth_rate for s in rows],
                [s.paired_brier.estimate for s in rows],
                "o-",
                label=name.replace("_", " "),
            )
        ax.axhline(0, color="#222", ls="--")
        ax.set_xlabel("generating spread-rate multiplier rho")
        ax.set_ylabel("stochastic worst-MLE Brier - neutral Brier")
        ax.set_title(
            "Held-out predictive comparison\ntraining-only fits; between-site dependence omitted"
        )
        ax.legend()
        return _figure_svg(fig)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )


def _write_csv(path: Path, rows: Sequence[CsvRow]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path.name}")
    cols = tuple(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(cols)
        for row in rows:
            writer.writerow(
                [
                    (
                        "true"
                        if isinstance(row[c], bool) and row[c]
                        else "false"
                        if isinstance(row[c], bool)
                        else format(row[c], ".17g")
                        if isinstance(row[c], float)
                        else row[c]
                    )
                    for c in cols
                ]
            )


def _figure_svg(fig: Figure) -> str:
    buffer = io.StringIO()
    fig.savefig(
        buffer, format="svg", metadata={"Date": None, "Creator": "Latent Landscapes Goal 005"}
    )
    plt.close(fig)
    return buffer.getvalue()
