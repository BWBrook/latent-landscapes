"""Goal 055 archive checks under the unchanged Goal 054 reference tables.

The two evaluation archives have independent replicate axes. Within an archive,
the same bootstrap index is used for every truth, perturbation and comparator.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from latent_landscapes import null_effect_synthesis as frozen

BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 2026100105
REFERENCE_SHA256 = "33c94ad6d7bb58701c68b611c70400c0228787e1782026c7df7d9b747aa40900"
NEW_CELLS = (
    "M080_E0_h1",
    "M080_E0_h3",
    "M080_E06_h1",
    "M080_E06_h3",
    "M125_E0_h1",
    "M125_E0_h3",
    "M125_E06_h1",
    "M125_E06_h3",
    "S051_B_h1",
    "S051_B_h3",
    "S051_D20_h1",
    "S051_D20_h3",
)
BASE_CELLS = ("M100_E0_h1", "M100_E0_h3", "M100_E06_h1", "M100_E06_h3")
CELL_IDS = (*NEW_CELLS, *BASE_CELLS)
GOAL054_COLUMNS = np.asarray((*range(8), *range(12, 16)), dtype=np.int64)
GOAL051_COLUMNS = np.arange(8, 12, dtype=np.int64)
PAIRS = (*((i, 12 + i % 4) for i in range(8)), (10, 8), (11, 9))
EVALUATION_KEYS = (
    "evaluation_t_adj",
    "evaluation_t_constant",
    "evaluation_d_beta",
    "evaluation_h_hat_adj",
    "evaluation_beta_hat_adj",
    "evaluation_h_hat_constant",
    "evaluation_beta_hat_null",
    "evaluation_delta_holdout_adj_constant",
    "evaluation_delta_holdout_adj_neutral",
    "evaluation_delta_holdout_constant_neutral",
)


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_npz(path: Path) -> dict[str, NDArray[Any]]:
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def combine_inputs(
    checks: Mapping[str, Any], reference: Mapping[str, Any], *, strict: bool = True
) -> dict[str, Any]:
    """Attach paired correct-level controls without pairing the two archives."""
    if tuple(checks["cell_ids"].astype(str)) != NEW_CELLS:
        raise ValueError("wrong Goal 055 cell order")
    if tuple(reference["cell_ids"].astype(str)) != frozen.CELL_IDS:
        raise ValueError("wrong frozen Goal 054 cell order")
    n = checks["evaluation_t_adj"].shape[0]
    nodes = len(reference["betas"])
    if strict and (n, nodes, len(reference["effects"])) != (1000, 81, 181):
        raise ValueError("registered archive/grid dimensions changed")
    if n < 1 or nodes < 1:
        raise ValueError("empty archive or beta grid")
    means = np.asarray(checks["supplied_mean"])
    if not np.array_equal(means, np.repeat([0.0016, 0.0025, 0.002], 4)):
        raise ValueError("supplied mean metadata differs from the registration")
    ids = np.asarray(checks["archive_ids"]).astype(str)
    if ids.shape != (n, 12) or (ids == "").any():
        raise ValueError("invalid archive identity dimensions or empty IDs")
    if not np.array_equal(ids[:, :4], ids[:, 4:8]):
        raise ValueError("wrong-mean lanes do not reuse identical Goal054 histories")
    if len(np.unique(ids[:, :4])) != n * 4 or len(np.unique(ids[:, 8:])) != n * 4:
        raise ValueError("duplicate histories within an archive")
    if np.intersect1d(ids[:, :4], ids[:, 8:]).size:
        raise ValueError("Goal054 and Goal051 archive identities overlap")
    for name in ("betas", "effects"):
        if not np.array_equal(checks[name], reference[name]):
            raise ValueError(f"frozen {name} grid differs")
    if strict and (
        not np.array_equal(reference["betas"], np.linspace(-2, 2, 81))
        or not np.array_equal(reference["effects"], np.linspace(1, 10, 181))
    ):
        raise ValueError("wrong registered parameter grid")
    expected_truth = np.tile([1.0, 3.0], 6)
    if not np.array_equal(checks["truth_h"], expected_truth):
        raise ValueError("wrong Goal 055 truths")
    if not np.array_equal(reference["truth_h"], np.tile([1.0, 3.0], 4)):
        raise ValueError("wrong Goal 054 truths")
    result: dict[str, Any] = {}
    for key in EVALUATION_KEYS:
        new = np.asarray(checks[key], dtype=np.float64)
        old = np.asarray(reference[key], dtype=np.float64)
        expected_new = (n, 12, nodes) if key == "evaluation_d_beta" else (n, 12)
        expected_old = (n, 8, nodes) if key == "evaluation_d_beta" else (n, 8)
        if new.shape != expected_new or old.shape != expected_old:
            raise ValueError(f"wrong archive shape: {key}")
        if not np.isfinite(new).all() or not np.isfinite(old).all():
            raise ValueError(f"nonfinite archive statistic: {key}")
        if key in {"evaluation_t_adj", "evaluation_t_constant", "evaluation_d_beta"} and (
            (new < 0).any() or (old < 0).any()
        ):
            raise ValueError(f"negative LR: {key}")
        result[key] = np.concatenate((new, old[:, :4]), axis=1)
    ref_shape = np.asarray(reference["reference_t_adj"]).shape
    if len(ref_shape) != 2 or ref_shape[1] != nodes or (strict and ref_shape[0] != 999):
        raise ValueError("wrong reference dimensions")
    for key in ("reference_t_adj", "reference_t_constant", "reference_d_beta"):
        values = np.asarray(reference[key], dtype=np.float64)
        shape = (ref_shape[0],) if key == "reference_t_constant" else ref_shape
        if values.shape != shape or not np.isfinite(values).all() or (values < 0).any():
            raise ValueError(f"invalid reference: {key}")
        result[key] = values
    for key in ("evaluation_h_hat_adj", "evaluation_h_hat_constant"):
        if not np.isin(result[key], reference["effects"]).all():
            raise ValueError(f"off-grid fit: {key}")
    for key in ("evaluation_beta_hat_adj", "evaluation_beta_hat_null"):
        if not np.isin(result[key], reference["betas"]).all():
            raise ValueError(f"off-grid fit: {key}")
    result.update(
        cell_ids=np.asarray(CELL_IDS),
        truth_h=np.tile([1.0, 3.0], 8),
        betas=np.asarray(reference["betas"]),
        effects=np.asarray(reference["effects"]),
        archive_ids=np.concatenate((ids, ids[:, :4]), axis=1),
        supplied_mean=np.concatenate((means, np.full(4, 0.002))),
    )
    return result


def rules_for_reference(
    values: Mapping[str, Any], index: NDArray[Any] | None = None, *, verify_direct: bool = False
) -> tuple[NDArray[Any], dict[str, Any]]:
    refs = [values[key] for key in ("reference_t_adj", "reference_t_constant", "reference_d_beta")]
    if index is not None:
        refs = [ref[index] for ref in refs]
    rules, diagnostics = frozen._rule_array(
        values, *refs, truth_beta_indices=np.full(16, -1, dtype=np.int64), fast=True
    )
    if verify_direct:
        for start in range(0, len(rules), 4):
            stop = start + 4
            direct = frozen.decision_rule(
                values["evaluation_t_adj"][start:stop],
                refs[0],
                values["evaluation_t_constant"][start:stop],
                refs[1],
                values["evaluation_d_beta"][start:stop],
                refs[2],
            )
            for k, key in enumerate(("primary", "constant", "berger_boos")):
                checked = direct[key]
                if checked is None or not np.array_equal(rules[start:stop, :, k], checked):
                    raise AssertionError(f"frozen direct and rank decisions disagree: {key}")
            checked_candidate = direct["candidate"]
            if checked_candidate is None or not np.array_equal(
                diagnostics["candidate"][start:stop], checked_candidate
            ):
                raise AssertionError("frozen direct and rank candidate sets disagree")
    return rules, diagnostics


def paired_sample(
    array: NDArray[Any], goal054_index: NDArray[Any], goal051_index: NDArray[Any]
) -> NDArray[Any]:
    """Preserve within-archive pairing and independent between-archive draws."""
    if array.shape[1] != 16 or len(goal054_index) != len(goal051_index):
        raise ValueError("archive resampling dimensions differ")
    result = np.empty((len(goal054_index), *array.shape[1:]), dtype=array.dtype)
    result[:, GOAL054_COLUMNS] = array[goal054_index][:, GOAL054_COLUMNS]
    result[:, GOAL051_COLUMNS] = array[goal051_index][:, GOAL051_COLUMNS]
    return result


def metric_arrays(values: Mapping[str, Any], rules: NDArray[Any]) -> dict[str, NDArray[Any]]:
    result: dict[str, NDArray[Any]] = dict(frozen._metric_values(values, rules))
    result.update(
        {
            "adjusted_beta_mean": values["evaluation_beta_hat_adj"],
            "null_beta_mean": values["evaluation_beta_hat_null"],
            "adjusted_beta_edge": np.isin(
                values["evaluation_beta_hat_adj"], values["betas"][[0, -1]]
            ),
            "null_beta_edge": np.isin(values["evaluation_beta_hat_null"], values["betas"][[0, -1]]),
            "adjusted_h_lower": values["evaluation_h_hat_adj"] == values["effects"][0],
            "adjusted_h_upper": values["evaluation_h_hat_adj"] == values["effects"][-1],
            "constant_h_lower": values["evaluation_h_hat_constant"] == values["effects"][0],
            "constant_h_upper": values["evaluation_h_hat_constant"] == values["effects"][-1],
        }
    )
    return result


def interval(draws: NDArray[Any]) -> dict[str, float]:
    return {
        "se": float(np.std(draws, ddof=1)),
        "low": float(np.quantile(draws, 0.025)),
        "high": float(np.quantile(draws, 0.975)),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def forecast(point: float, draws: NDArray[Any], lower: float, upper: float) -> dict[str, Any]:
    ci = interval(draws)
    status = "unresolved"
    if ci["low"] >= lower and ci["high"] <= upper:
        status = "supported"
    elif ci["high"] < lower or ci["low"] > upper:
        status = "refuted"
    return {"estimate": point, **ci, "point_met": lower <= point <= upper, "status": status}


def plot_rates(output: Path, point: NDArray[Any], draws: NDArray[Any]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 3, figsize=(13, 7.5), sharey="row")
    for row, h in enumerate((1, 3)):
        for col, exact in enumerate((0, 2)):
            ax = axes[row, col]
            selected = [exact + row, 12 + exact + row, 4 + exact + row]
            for rule, label, color, offset in (
                (0, "Adjusted", "#0072B2", -0.045),
                (1, "Constant", "#D55E00", 0.045),
            ):
                y = 100 * point[selected, rule]
                low, high = 100 * np.quantile(draws[:, selected, rule], [0.025, 0.975], axis=0)
                x = np.arange(3) + offset
                ax.plot(x, y, "o-", color=color, label=label, linewidth=1.2)
                ax.vlines(x, low, high, color=color, linewidth=1.2)
                ax.hlines(low, x - 0.025, x + 0.025, color=color)
                ax.hlines(high, x - 0.025, x + 0.025, color=color)
            ax.set_xticks(range(3), ["0.80", "1.00", "1.25"])
            ax.set_xlabel("Supplied mean / true mean")
            ax.set_title(f"{'E0' if col == 0 else 'E06'}, h = {h}")
        ax = axes[row, 2]
        selected = [8 + row, 10 + row]
        for rule, label, color, offset in (
            (0, "Adjusted", "#0072B2", -0.045),
            (1, "Constant", "#D55E00", 0.045),
        ):
            y = 100 * point[selected, rule]
            low, high = 100 * np.quantile(draws[:, selected, rule], [0.025, 0.975], axis=0)
            x = np.arange(2) + offset
            ax.plot(x, y, "o-", color=color, label=label, linewidth=1.2)
            ax.vlines(x, low, high, color=color, linewidth=1.2)
            ax.hlines(low, x - 0.025, x + 0.025, color=color)
            ax.hlines(high, x - 0.025, x + 0.025, color=color)
        ax.set_xticks(range(2), ["Baseline", "D20"])
        ax.set_title(f"Goal 051 archives, h = {h}")
        ax.set_xlabel("Prey-detection condition")
        axes[row, 0].set_ylabel("False declarations (%)" if h == 1 else "h3 declarations (%)")
        for ax in axes[row]:
            ax.grid(axis="y", alpha=0.2)
            ax.set_ylim(bottom=0)
            if h == 1:
                ax.axhline(5, color=".4", linestyle="--", linewidth=0.8)
    axes[0, 0].legend(frameon=False)
    fig.text(
        0.06,
        0.015,
        "Frozen Goal 054 rules; retrospective archive checks. "
        "Bars: 95% calibration-aware intervals (2,000 paired draws).",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    for suffix in ("png", "pdf"):
        fig.savefig(output / f"nuisance_checks.{suffix}", dpi=180)
    plt.close(fig)


def synthesize(
    input_path: Path,
    reference_path: Path,
    output: Path,
    *,
    bootstrap_draws: int = BOOTSTRAP_DRAWS,
    strict: bool = True,
) -> dict[str, Any]:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("refusing to overwrite an existing synthesis")
    if bootstrap_draws < 2 or (strict and bootstrap_draws != BOOTSTRAP_DRAWS):
        raise ValueError("registered synthesis uses exactly 2,000 draws")
    reference_digest = sha256(reference_path)
    if strict and reference_digest != REFERENCE_SHA256:
        raise ValueError("frozen Goal 054 reference/evaluation table changed")
    values = combine_inputs(load_npz(input_path), load_npz(reference_path), strict=strict)
    rules, diagnostics = rules_for_reference(values, verify_direct=True)
    metrics = metric_arrays(values, rules)
    metric_names = tuple(metrics)
    metric_matrix = np.stack([metrics[name] for name in metric_names], axis=-1)
    n = len(rules)
    r = len(values["reference_t_adj"])
    ref_seed, eval054_seed, eval051_seed = np.random.SeedSequence(BOOTSTRAP_SEED).spawn(3)
    ref_rng, eval054_rng, eval051_rng = map(
        np.random.default_rng, (ref_seed, eval054_seed, eval051_seed)
    )
    ref_indices = np.empty((bootstrap_draws, r), dtype=np.int32)
    idx054 = np.empty((bootstrap_draws, n), dtype=np.int32)
    idx051 = np.empty_like(idx054)
    frozen_rates = np.empty((bootstrap_draws, 16, len(frozen.RULE_NAMES)))
    cal_rates = np.empty_like(frozen_rates)
    metric_draws = np.empty((bootstrap_draws, 16, len(metric_names)))
    for draw in range(bootstrap_draws):
        ref_indices[draw] = ref_rng.integers(r, size=r)
        idx054[draw] = eval054_rng.integers(n, size=n)
        idx051[draw] = eval051_rng.integers(n, size=n)
        frozen_rates[draw] = paired_sample(rules, idx054[draw], idx051[draw]).mean(axis=0)
        changed_rules, _ = rules_for_reference(values, ref_indices[draw])
        cal_rates[draw] = paired_sample(changed_rules, idx054[draw], idx051[draw]).mean(axis=0)
        metric_draws[draw] = paired_sample(metric_matrix, idx054[draw], idx051[draw]).mean(axis=0)
    output.mkdir(parents=True, exist_ok=True)
    rates = rules.mean(axis=0)
    metric_point = metric_matrix.mean(axis=0)
    rate_rows = []
    for cell, cell_id in enumerate(CELL_IDS):
        for rule, name in enumerate(frozen.RULE_NAMES):
            row = {
                "cell_id": cell_id,
                "rule": name,
                "n": n,
                "count": int(rules[:, cell, rule].sum()),
                "rate": float(rates[cell, rule]),
            }
            for label, array in (("frozen", frozen_rates), ("calibration_aware", cal_rates)):
                row.update({f"{label}_{k}": v for k, v in interval(array[:, cell, rule]).items()})
            rate_rows.append(row)
    write_csv(output / "rule_rates.csv", rate_rows)
    metric_rows = [
        {
            "cell_id": cell_id,
            "metric": name,
            "n": n,
            "estimate": float(metric_point[cell, k]),
            **interval(metric_draws[:, cell, k]),
        }
        for cell, cell_id in enumerate(CELL_IDS)
        for k, name in enumerate(metric_names)
    ]
    write_csv(output / "metrics.csv", metric_rows)
    contrasts = []
    for changed, baseline in PAIRS:
        for rule, name in enumerate(frozen.RULE_NAMES):
            row = {
                "cell_id": CELL_IDS[changed],
                "baseline_cell": CELL_IDS[baseline],
                "metric": f"declaration_{name}",
                "estimate": float(rates[changed, rule] - rates[baseline, rule]),
            }
            for label, array in (("frozen", frozen_rates), ("calibration_aware", cal_rates)):
                difference = array[:, changed, rule] - array[:, baseline, rule]
                row.update({f"{label}_{k}": v for k, v in interval(difference).items()})
            contrasts.append(row)
    write_csv(output / "paired_rate_contrasts.csv", contrasts)
    metric_contrasts = [
        {
            "cell_id": CELL_IDS[i],
            "baseline_cell": CELL_IDS[b],
            "metric": name,
            "estimate": float(metric_point[i, k] - metric_point[b, k]),
            **interval(metric_draws[:, i, k] - metric_draws[:, b, k]),
        }
        for i, b in PAIRS
        for k, name in enumerate(metric_names)
    ]
    write_csv(output / "paired_metric_contrasts.csv", metric_contrasts)
    rule_contrasts = [
        {
            "cell_id": cell,
            "comparison": "adjusted_minus_constant",
            "estimate": float(rates[i, 0] - rates[i, 1]),
            **{
                f"{label}_{key}": value
                for label, array in (("frozen", frozen_rates), ("calibration_aware", cal_rates))
                for key, value in interval(array[:, i, 0] - array[:, i, 1]).items()
            },
        }
        for i, cell in enumerate(CELL_IDS)
    ]
    write_csv(output / "paired_rule_contrasts.csv", rule_contrasts)
    candidate = diagnostics["candidate"]
    diagnostic_rows = [
        {
            "cell_id": cell,
            "candidate_size_mean": float(candidate[:, i].sum(axis=-1).mean()),
            "candidate_empty_count": int((~candidate[:, i].any(axis=-1)).sum()),
            "candidate_lower_edge_rate": float(candidate[:, i, 0].mean()),
            "candidate_upper_edge_rate": float(candidate[:, i, -1].mean()),
        }
        for i, cell in enumerate(CELL_IDS)
    ]
    write_csv(output / "rule_diagnostics.csv", diagnostic_rows)
    np.savez_compressed(
        output / "decisions.npz",
        rules=rules,
        candidate=candidate,
        cell_ids=np.asarray(CELL_IDS),
        rule_names=np.asarray(frozen.RULE_NAMES),
        archive_ids=values["archive_ids"],
        supplied_mean=values["supplied_mean"],
    )
    np.savez_compressed(
        output / "bootstrap_draws.npz",
        reference_indices=ref_indices,
        goal054_indices=idx054,
        goal051_indices=idx051,
        rule_rates_frozen=frozen_rates,
        rule_rates_calibration_aware=cal_rates,
        metric_draws=metric_draws,
        metric_names=np.asarray(metric_names),
        cell_ids=np.asarray(CELL_IDS),
        rule_names=np.asarray(frozen.RULE_NAMES),
    )
    plot_rates(output, rates, cal_rates)
    nulls = [0, 2, 4, 6]
    null_ci = {CELL_IDS[i]: interval(cal_rates[:, i, 0]) for i in nulls}
    failed = [name for name, bounds in null_ci.items() if bounds["low"] > 0.05]
    if failed:
        branch = "clear_wrong_level_nominal_robustness_failure"
    elif all(bounds["high"] <= 0.05 for bounds in null_ci.values()):
        branch = "external_information_candidate_requires_new_qualification"
    else:
        branch = "inconclusive_wrong_level_robustness"
    summary = {
        "status": "complete_retrospective_archive_checks",
        "strict": strict,
        "input_sha256": sha256(input_path),
        "reference_sha256": reference_digest,
        "bootstrap_draws": bootstrap_draws,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "reference_blocks": r,
        "blocks_per_archive": n,
        "cell_ids": list(CELL_IDS),
        "new_fit_cells": 12,
        "reused_correct_level_cells": 4,
        "bootstrap_pairing": (
            "independent reference, Goal054 and Goal051 streams; shared indices within each archive"
        ),
        "no_recalibration_adopted": True,
        "direct_rank_rules_verified": True,
        "primary_cutoff": float(
            frozen._order_cutoff(
                values["reference_t_adj"], r - int(np.floor(0.05 * (r + 1))) + 1
            ).max()
        ),
        "constant_cutoff": float(
            frozen._order_cutoff(
                values["reference_t_constant"], r - int(np.floor(0.05 * (r + 1))) + 1
            )
        ),
        "wrong_level_null_intervals": null_ci,
        "wrong_level_failure_cells": failed,
        "background_design_diagnostic": branch,
        "detection_null_interval": interval(cal_rates[:, 10, 0]),
        "detection_absolute_failure": interval(cal_rates[:, 10, 0])["low"] > 0.05,
        "detection_paired_increase": (
            interval(cal_rates[:, 10, 0] - cal_rates[:, 8, 0])["low"] > 0
        ),
        "detection_repair_prerequisite": (
            interval(cal_rates[:, 10, 0])["low"] > 0.05
            or interval(cal_rates[:, 10, 0] - cal_rates[:, 8, 0])["low"] > 0
        ),
        "detection_null_paired_contrast": {
            "estimate": float(rates[10, 0] - rates[8, 0]),
            **interval(cal_rates[:, 10, 0] - cal_rates[:, 8, 0]),
        },
        "forecasts": {
            "M080_E0_h1_constant_8_to_10_percent": forecast(
                float(rates[0, 1]), cal_rates[:, 0, 1], 0.08, 0.10
            ),
            "D20_h1_adjusted_at_least_12_percent": forecast(
                float(rates[10, 0]), cal_rates[:, 10, 0], 0.12, 1.0
            ),
        },
        "output_hashes": {p.name: sha256(p) for p in output.iterdir() if p.is_file()},
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    return summary
