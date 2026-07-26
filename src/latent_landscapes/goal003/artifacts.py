"""Deterministic 13-file Goal 003 review pack writer."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, cast

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "latent-landscapes-goal003"
import numpy as np  # noqa: E402
from matplotlib import pyplot as plt  # noqa: E402

from .benchmark import (  # noqa: E402
    ALL_REVIEW_TIMES,
    REVIEW_TIMES,
    Goal003Result,
)

DEFAULT_OUTPUT_DIR = Path("artifacts/goal003_stochastic_spread_process")
ROOT_FILES = (
    "process_config.json",
    "seed_manifest.csv",
    "replicate_summary.csv",
    "cell_arrival_quantiles.csv",
    "habitat_arrival_summary.csv",
    "representative_realizations.csv",
    "summary.json",
    "verification.json",
    "review.md",
)
VISUAL_FILES = (
    "arrival_quantile_maps.svg",
    "representative_realizations.svg",
    "spread_trajectories.svg",
    "temporal_scale_diagnostic.svg",
)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty table: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_review_bundle(
    result: Goal003Result, output_dir: str | Path = DEFAULT_OUTPUT_DIR
) -> tuple[Path, ...]:
    if result.outcome == "implementation_blocked":
        raise ValueError("an implementation-blocked result has no review bundle")
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    visuals = target / "visuals"
    visuals.mkdir(exist_ok=True)
    paths = {name: target / name for name in ROOT_FILES}
    paths.update({name: visuals / name for name in VISUAL_FILES})

    paths["process_config.json"].write_text(
        json.dumps(_config_payload(result), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    _write_csv(paths["seed_manifest.csv"], _seed_rows(result))
    _write_csv(paths["replicate_summary.csv"], _replicate_rows(result))
    _write_csv(paths["cell_arrival_quantiles.csv"], _cell_rows(result))
    _write_csv(paths["habitat_arrival_summary.csv"], list(result.habitat_summary))
    _write_csv(paths["representative_realizations.csv"], _representative_rows(result))
    paths["summary.json"].write_text(
        json.dumps(_summary_payload(result), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    paths["verification.json"].write_text(
        json.dumps({"invariants": result.invariants}, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    paths["review.md"].write_text(_review_text(result), encoding="utf-8")
    _arrival_quantile_maps(result, paths["arrival_quantile_maps.svg"])
    _representative_figure(result, paths["representative_realizations.svg"])
    _trajectory_figure(result, paths["spread_trajectories.svg"])
    _scale_figure(result, paths["temporal_scale_diagnostic.svg"])

    expected = {*ROOT_FILES, *(f"visuals/{name}" for name in VISUAL_FILES)}
    observed = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
    if observed != expected:
        raise RuntimeError(
            f"artifact contract mismatch: expected {sorted(expected)}, got {sorted(observed)}"
        )
    return tuple(paths[name] for name in (*ROOT_FILES, *VISUAL_FILES))


def _config_payload(result: Goal003Result) -> dict[str, object]:
    return {
        "goal": "003-stochastic-predator-spread-process-review",
        "master_seed": result.config.master_seed,
        "replicates": result.config.replicates,
        "generator": "numpy.random.Generator(numpy.random.PCG64(child))",
        "rho": result.config.rho,
        "edge_law": "Exponential(rate=rho/c_e)",
        "review_times": list(REVIEW_TIMES),
        "reference_times": [70.0, 90.0, 110.0],
        "graph_order": "undirected passable rook edges in stable row-major order",
        "source_initialisation": "all source-zone cells at t=0",
        "normalization": None,
    }


def _seed_rows(result: Goal003Result) -> list[dict[str, object]]:
    return [
        {
            "replicate_index": seed.replicate_index,
            "phase": "stochastic_process",
            "entropy": seed.entropy,
            "spawn_key": json.dumps(seed.spawn_key, separators=(",", ":")),
            "state_words": json.dumps(seed.state_words, separators=(",", ":")),
        }
        for seed in result.seeds
    ]


def _replicate_rows(result: Goal003Result) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for summary in result.replicate_summaries:
        row: dict[str, object] = {
            "replicate_index": summary.replicate_index,
            "time_to_25": summary.threshold_times[0],
            "time_to_50": summary.threshold_times[1],
            "time_to_75": summary.threshold_times[2],
            "time_to_90": summary.threshold_times[3],
            "maximum_arrival": summary.maximum_arrival,
        }
        for time, occupancy in zip(ALL_REVIEW_TIMES, summary.occupancy, strict=True):
            row[f"occupancy_{int(time)}"] = occupancy
        for label, count in summary.source_counts:
            row[f"source_cells_{label}"] = count
        rows.append(row)
    return rows


def _cell_rows(result: Goal003Result) -> list[dict[str, object]]:
    q = result.cell_quantiles
    rows: list[dict[str, object]] = []
    passable = result.landscape.passable
    for row, col in zip(*np.where(passable), strict=True):
        values = result.arrivals[:, row, col]
        labels = result.source_labels
        label_values = [str(label[row, col]) for label in labels]
        modal = max(sorted(set(label_values)), key=lambda label: label_values.count(label))
        rows.append(
            {
                "cell_id": int(row * result.landscape.cols + col),
                "row": int(row),
                "col": int(col),
                "habitat_class": str(result.landscape.habitat_class[row, col]),
                "deterministic_arrival": float(q.deterministic[row, col]),
                "stochastic_q10": float(q.q10[row, col]),
                "stochastic_q25": float(q.q25[row, col]),
                "stochastic_q50": float(q.q50[row, col]),
                "stochastic_q75": float(q.q75[row, col]),
                "stochastic_q90": float(q.q90[row, col]),
                "modal_source_zone": modal,
                "modal_source_fraction": float(label_values.count(modal) / len(label_values)),
                **{
                    f"occupancy_probability_{int(time)}": float(np.mean(values <= time))
                    for time in ALL_REVIEW_TIMES
                },
            }
        )
    return rows


def _representative_rows(result: Goal003Result) -> list[dict[str, object]]:
    return [
        {key: value for key, value in representative.items() if key != "arrival"}
        for representative in result.representatives
    ]


def _summary_payload(result: Goal003Result) -> dict[str, object]:
    return {
        "goal": "003-stochastic-predator-spread-process-review",
        "outcome": result.outcome,
        "counts": {
            "cells": result.landscape.cell_count,
            "passable_cells": int(result.landscape.passable.sum()),
            "water_cells": int((~result.landscape.passable).sum()),
            "source_cells": int((result.landscape.source_zone != "").sum()),
            "undirected_edges": 10120,
            "replicates": len(result.replicate_summaries),
        },
        "process": _config_payload(result),
        "diagnostics": result.diagnostics,
        "representatives": _representative_rows(result),
        "invariants": result.invariants,
        "provenance": {
            "goal001_landscape_commit": "53462d0365babf2c8070714a930f69b4071af276",
            "goal001_landscape_blob_sha1": "f2f5fc24e64274e443f8eec8c314e212e2a6889f",
            "goal001_spread_blob_sha1": "cb15f2178ff9e2f359f06fdac34a9b551e163cd5",
            "runtime_dependency_on_legacy_repo": False,
        },
        "limitations": [
            "100 spatially dependent stochastic replicates; no observation model or fitting",
            "rho=1 is a generating value, not an estimated parameter",
            "temporal-scale ratio is a geometry/process diagnostic, not an inferential estimate",
        ],
    }


def _review_text(result: Goal003Result) -> str:
    d = result.diagnostics
    deterministic_median = float(cast(float, d["deterministic_median_arrival"]))
    stochastic_median = float(cast(float, d["stochastic_median_median_arrival"]))
    association = float(cast(float, d["deterministic_stochastic_median_correlation"]))
    variation = float(cast(float, d["variation_sd_t50"]))
    ratio = float(cast(float, d["temporal_scale_ratio"]))
    return f"""# Goal 003 stochastic spread process review

## Observed ensemble results

- Outcome: `{result.outcome}`.
- Exactly {len(result.replicate_summaries)} PCG64 child replicates were generated at
  `rho = {result.config.rho:g}`.
- Deterministic median arrival is {deterministic_median:.3f}; stochastic ensemble-median
  median arrival is {stochastic_median:.3f}.
- Deterministic versus stochastic-median cell association is {association:.4f}.
- Stochastic t50 variation (sample SD) is {variation:.3f}.
- The old Goal 001 reference horizon is saturated: `{bool(d["old_horizon_saturated"])}`.

## Interpretation

The positive landscape association indicates that deterministic geometry remains visible in
the stochastic process. The temporal-scale ratio is {ratio:.4f}; path competition makes
stochastic first passage faster than the deterministic shortest path of mean edge costs.
This is reported as a temporal-scale diagnostic. No normalization, tuning, fitting,
observations, prey process, or extra parameter was introduced.

## Provenance and limitations

Edges are undirected passable rook edges in stable row-major order, with independent
transit times `Exponential(rate=rho/c_e)`. All 81 source-zone cells start at zero. Water
is structural non-domain. The ensemble is a process-review sample, not a test of
identifiability or a replacement for human review before inference.
"""


def _save(fig: Any, path: Path) -> None:
    fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)


def _arrival_quantile_maps(result: Goal003Result, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    q50 = np.where(result.landscape.passable, result.cell_quantiles.q50, np.nan)
    spread = np.where(
        result.landscape.passable, result.cell_quantiles.q90 - result.cell_quantiles.q10, np.nan
    )
    for axis, image, title in zip(
        axes, (q50, spread), ("Ensemble median arrival", "q90 - q10 arrival spread"), strict=True
    ):
        im = axis.imshow(image, cmap="viridis")
        axis.set_title(title)
        axis.set_xlabel("column")
        axis.set_ylabel("row")
        fig.colorbar(im, ax=axis, shrink=0.8, label="time")
    _save(fig, path)


def _representative_figure(result: Goal003Result, path: Path) -> None:
    fig, axes = plt.subplots(1, 5, figsize=(14, 3), constrained_layout=True)
    for axis, representative in zip(axes, result.representatives, strict=True):
        arrival = np.asarray(cast(np.ndarray, representative["arrival"]), dtype=float)
        image = np.where(result.landscape.passable, arrival, np.nan)
        axis.imshow(image, cmap="viridis")
        axis.set_title(str(representative["selection_label"]))
        axis.set_xticks([])
        axis.set_yticks([])
    fig.suptitle("Mechanically selected t50-rank realizations")
    _save(fig, path)


def _trajectory_figure(result: Goal003Result, path: Path) -> None:
    fig, axis = plt.subplots(figsize=(7, 4), constrained_layout=True)
    trajectories = np.asarray([summary.occupancy for summary in result.replicate_summaries])
    axis.plot(ALL_REVIEW_TIMES, np.quantile(trajectories, 0.5, axis=0), label="stochastic median")
    axis.fill_between(
        ALL_REVIEW_TIMES,
        np.quantile(trajectories, 0.1, axis=0),
        np.quantile(trajectories, 0.9, axis=0),
        alpha=0.25,
        label="stochastic 10-90%",
    )
    deterministic = result.deterministic.arrival[result.landscape.passable]
    axis.plot(
        ALL_REVIEW_TIMES,
        [float(np.mean(deterministic <= time)) for time in ALL_REVIEW_TIMES],
        "--",
        label="Goal 001 deterministic",
    )
    axis.set(
        xlabel="latent process time",
        ylabel="passable-cell occupancy",
        ylim=(0, 1.02),
        title="Spread trajectories",
    )
    axis.legend()
    _save(fig, path)


def _scale_figure(result: Goal003Result, path: Path) -> None:
    fig, axis = plt.subplots(figsize=(7, 4), constrained_layout=True)
    values = result.cell_quantiles.q50[result.landscape.passable]
    deterministic = result.cell_quantiles.deterministic[result.landscape.passable]
    mask = deterministic > 0
    axis.scatter(deterministic[mask], values[mask], s=2, alpha=0.35)
    bound = max(float(deterministic[mask].max()), float(values[mask].max()))
    axis.plot((0, bound), (0, bound), "--", label="equal timing")
    axis.set(
        xlabel="deterministic Goal 001 arrival",
        ylabel="stochastic ensemble-median arrival",
        title="Temporal-scale diagnostic",
    )
    axis.legend()
    _save(fig, path)
