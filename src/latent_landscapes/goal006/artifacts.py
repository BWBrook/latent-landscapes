"""Deterministic 15-file review bundle for Goal 006."""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from .benchmark import DEFAULT_CONFIG, SOURCE_IDENTITY, Goal006Result

DEFAULT_OUTPUT_DIR = Path("artifacts/goal006_stochastic_resistance_contrast")
ROOT_FILES = (
    "process_config.json",
    "seed_manifest.csv",
    "edge_cost_summary.csv",
    "replicate_summary.csv",
    "spatial_effect_summary.csv",
    "cell_summary.csv",
    "representative_realizations.csv",
    "summary.json",
    "verification.json",
    "review.md",
)
VISUAL_FILES = (
    "edge_cost_transformation.svg",
    "aligned_residual_maps.svg",
    "matched_occupancy_fronts.svg",
    "habitat_contrast_curves.svg",
    "source_reassignment.svg",
)
EXPECTED_FILE_COUNT = 15


def write_review_bundle(
    result: Goal006Result, output_dir: str | Path = DEFAULT_OUTPUT_DIR
) -> tuple[Path, ...]:
    if result.outcome == "implementation_blocked":
        raise ValueError("an implementation-blocked result has no review bundle")
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    visuals = target / "visuals"
    visuals.mkdir(exist_ok=True)
    expected = {*ROOT_FILES, *(f"visuals/{n}" for n in VISUAL_FILES)}
    for path in target.rglob("*"):
        if path.is_file() and path.relative_to(target).as_posix() not in expected:
            path.unlink()
    paths = {name: target / name for name in ROOT_FILES}
    visual_paths = {name: visuals / name for name in VISUAL_FILES}
    paths["verification.json"].unlink(missing_ok=True)
    _write_json(paths["process_config.json"], _config(result))
    _write_csv(paths["seed_manifest.csv"], _seed_rows(result))
    _write_csv(paths["edge_cost_summary.csv"], list(result.edge_cost_summary))
    _write_csv(paths["replicate_summary.csv"], _replicate_rows(result))
    _write_csv(paths["spatial_effect_summary.csv"], _spatial_rows(result))
    _write_csv(paths["cell_summary.csv"], list(result.cell_summary))
    _write_csv(paths["representative_realizations.csv"], list(result.representative_realizations))
    _write_json(paths["summary.json"], _summary(result))
    paths["review.md"].write_text(_review(result), encoding="utf-8")
    _write_svg(visual_paths["edge_cost_transformation.svg"], _edge_cost_figure(result))
    _write_svg(visual_paths["aligned_residual_maps.svg"], _residual_figure(result))
    _write_svg(visual_paths["matched_occupancy_fronts.svg"], _front_figure(result))
    _write_svg(visual_paths["habitat_contrast_curves.svg"], _contrast_figure(result))
    _write_svg(visual_paths["source_reassignment.svg"], _source_figure(result))
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
            "outcome": result.outcome,
            "diagnostics": result.diagnostics,
            "source_identity": SOURCE_IDENTITY,
            "paired_edge_shocks": True,
            "diagnostic_alignment_only": True,
            "cells_are_not_replicates": True,
            "between_site_process_dependence": (
                "shared edge field retained only in replicate summaries"
            ),
        },
    )
    observed = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
    if observed != expected:
        raise RuntimeError(f"artifact contract mismatch: {sorted(observed)}")
    return tuple(paths.values()) + tuple(visual_paths.values())


def _config(result: Goal006Result) -> dict[str, object]:
    c = result.config
    return {
        "goal": "006-stochastic-landscape-resistance-contrast-review",
        "master_seed": c.master_seed,
        "replicates": c.replicates,
        "etas": list(c.etas),
        "rho": 1.0,
        "edge_cost_transform": "g * (c / g) ** eta",
        "geometric_mean_preserved": True,
        "occupancy_fractions": [0.25, 0.5, 0.75],
        "source_identity": SOURCE_IDENTITY,
        "production_configuration": c == DEFAULT_CONFIG,
        "alignment": (
            "exp(median(log(T_1)-log(T_eta))) on non-source passable cells; summaries only"
        ),
        "decision_scope": (
            "conditional on one accepted landscape and one stochastic edge-field process"
        ),
        "observations_or_fitting": False,
    }


def _seed_rows(result: Goal006Result) -> list[dict[str, object]]:
    return [
        {
            "replicate_index": s.replicate_index,
            "entropy": s.entropy,
            "spawn_key": json.dumps(s.spawn_key, separators=(",", ":")),
            "state_words": json.dumps(s.state_words, separators=(",", ":")),
            "pool_size": s.pool_size,
            "paired_eta_grid": json.dumps(list(result.config.etas), separators=(",", ":")),
            "stream_role": "one exponential edge-shock vector reused across all eta values",
        }
        for s in result.seeds
    ]


def _replicate_rows(result: Goal006Result) -> list[dict[str, object]]:
    rows = []
    for row in result.replicate_summaries:
        values: dict[str, object] = {"replicate_index": row.replicate_index, "eta": row.eta}
        values.update(
            {
                "t25": row.t25,
                "t50": row.t50,
                "t75": row.t75,
                "t90": row.t90,
                "maximum_arrival": row.maximum_arrival,
                "alignment_scale": row.alignment_scale,
                "median_abs_aligned_log_residual": row.median_abs_aligned_log_residual,
                "p90_abs_aligned_log_residual": row.p90_abs_aligned_log_residual,
                "front_jaccard_25": row.front_jaccard_25,
                "front_jaccard_50": row.front_jaccard_50,
                "front_jaccard_75": row.front_jaccard_75,
                "arrival_rank_correlation": row.arrival_rank_correlation,
                "displaced_fraction": row.displaced_fraction,
                "source_reassignment_fraction": row.source_reassignment_fraction,
                "source_contribution_fractions": json.dumps(
                    dict(row.source_contribution_fractions), sort_keys=True
                ),
                "A": row.A,
                "J": row.J,
                "H": row.H,
            }
        )
        rows.append(values)
    return rows


def _spatial_rows(result: Goal006Result) -> list[dict[str, object]]:
    return [
        {
            "eta": row.eta,
            "median_A": row.median_A,
            "p05_A": row.p05_A,
            "p95_A": row.p95_A,
            "median_J": row.median_J,
            "p05_J": row.p05_J,
            "p95_J": row.p95_J,
            "median_H": row.median_H,
            "p05_H": row.p05_H,
            "p95_H": row.p95_H,
            "median_abs_residual": row.median_abs_residual,
            "median_t50": row.median_t50,
            "consistency_count": row.consistency_count,
            "expected_sign_count": row.expected_sign_count,
            "corridor_minus_matrix": row.corridor_matrix_contrast,
            "patch_minus_matrix": row.patch_matrix_contrast,
            "water_adjacent_minus_non_water_matrix": row.water_matrix_contrast,
        }
        for row in result.spatial_effect_summary
    ]


def _summary(result: Goal006Result) -> dict[str, object]:
    by_eta = {row.eta: row for row in result.spatial_effect_summary}
    return {
        "goal": "006-stochastic-landscape-resistance-contrast-review",
        "outcome": result.outcome,
        "eta_values": list(result.config.etas),
        "replicates": result.config.replicates,
        "passable_cells": int(result.landscape.passable.sum()),
        "water_cells": int((~result.landscape.passable).sum()),
        "source_cells": int((result.landscape.source_zone != "").sum()),
        "edge_count": len(result.edge_costs),
        "adjacent_effects": {
            str(eta): {
                "median_A": by_eta[eta].median_A,
                "median_J": by_eta[eta].median_J,
                "median_H": by_eta[eta].median_H,
                "consistency_count": by_eta[eta].consistency_count,
            }
            for eta in (0.5, 1.5)
        },
        "diagnostics": result.diagnostics,
    }


def _review(result: Goal006Result) -> str:
    return f"""# Goal 006 Resistance-Contrast Review

## Outcome

`{result.outcome}`

This is a process-design diagnostic on one accepted synthetic landscape. It
does not fit parameters, simulate observations, or establish joint
identifiability. One shared exponential edge-shock vector is reused across
the five eta values within each of {result.config.replicates} edge-field
replicates. Raw arrival grids are not retained in this pack; the tables retain
compact replicate, habitat, source, and representative summaries.

## What is observed versus inferred

Raw quantities are arrival thresholds, maxima, source labels, and source
contributions. Aligned log residuals and matched-front distances are diagnostic
transformations used to remove global-time confounding; they do not alter the
generator. Decision operands A, J, and H are replicate-level summaries, not
cell-level pseudo-replicates. The scope is conditional on the accepted
landscape, graph, and edge-cost process.

## Frozen replay

Goal 003 eta=1 reconciliation: `{result.diagnostics}`.

## Limitations

The edge field is shared across cells within a replicate, between-replicate
variation is represented by 100 fields, and no observation or prey-impact layer
is included. Negative contrast outcomes are valid and do not justify retuning
the eta grid or landscape.
"""


def _write_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path.name}")
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_svg(path: Path, figure: Figure) -> None:
    figure.savefig(path, format="svg", metadata={"Date": None})
    plt.close(figure)
    text = path.read_text(encoding="utf-8")
    token_pattern = r"(?:image|m|p)[0-9a-f]{10}"
    tokens = list(dict.fromkeys(re.findall(token_pattern, text)))
    replacements = {
        token: f"{'image' if token.startswith('image') else token[0]}{index:010d}"
        for index, token in enumerate(tokens)
    }
    text = re.sub(token_pattern, lambda match: replacements[match.group(0)], text)
    path.write_text(text, encoding="utf-8")


def _edge_cost_figure(result: Goal006Result) -> Figure:
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    base = np.asarray([e[2] for e in result.edge_costs])
    for eta in result.config.etas:
        from .spread import transform_edge_costs

        values = np.asarray([e[2] for e in transform_edge_costs(result.edge_costs, eta)])
        ax.plot(np.sort(base), np.sort(values), label=f"eta={eta:g}")
    ax.set_xlabel("Raw accepted edge cost (sorted)")
    ax.set_ylabel("Transformed edge cost (sorted)")
    ax.set_title("Raw versus transformed resistance costs")
    ax.legend()
    fig.tight_layout()
    return fig


def _residual_figure(result: Goal006Result) -> Figure:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6))
    grids = [_representative_residual(result, eta) for eta in (0.5, 1.5)]
    scale = max(float(np.nanmax(np.abs(grid))) for grid in grids)
    cmap = plt.get_cmap("coolwarm").copy()
    cmap.set_bad("#d9d9d9")
    image = None
    for axis, eta, grid in zip(axes, (0.5, 1.5), grids, strict=True):
        image = axis.pcolormesh(
            grid,
            cmap=cmap,
            vmin=-scale,
            vmax=scale,
            shading="nearest",
        )
        axis.set_title(f"eta={eta:g} versus eta=1 reference")
        axis.set_xticks([])
        axis.set_yticks([])
        _mark_sources(axis, result)
    assert image is not None
    colorbar = fig.colorbar(image, ax=axes, shrink=0.82)
    colorbar.set_label("Diagnostic alignment only: aligned log residual")
    fig.suptitle("Representative replicate 29: aligned residual maps")
    fig.text(
        0.5,
        0.035,
        "Water masked; alignment removes global time only for this diagnostic",
        ha="center",
    )
    fig.subplots_adjust(left=0.03, right=0.90, top=0.86, bottom=0.20, wspace=0.08)
    return fig


def _front_figure(result: Goal006Result) -> Figure:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6))
    cmap = ListedColormap(("#f4f4f4", "#111111", "#1f9e89", "#984ea3"))
    norm = BoundaryNorm((-0.5, 0.5, 1.5, 2.5, 3.5), cmap.N)
    image = None
    for axis, eta in zip(axes, (0.5, 1.5), strict=True):
        grid = _representative_front_categories(result, eta)
        image = axis.pcolormesh(grid, cmap=cmap, norm=norm, shading="nearest")
        axis.set_title(f"Raw 50% front: eta={eta:g} vs eta=1")
        axis.set_xticks([])
        axis.set_yticks([])
        _mark_sources(axis, result)
    assert image is not None
    legend = (
        Patch(facecolor="#f4f4f4", edgecolor="0.5", label="neither front"),
        Patch(facecolor="#111111", label="eta=1 reference only"),
        Patch(facecolor="#1f9e89", label="eta-specific only"),
        Patch(facecolor="#984ea3", label="overlap"),
        Patch(facecolor="#d9d9d9", label="water masked"),
    )
    fig.legend(
        handles=legend,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.06),
        ncol=5,
        frameon=False,
    )
    fig.suptitle("Representative replicate 29: raw matched occupancy fronts")
    fig.text(
        0.5,
        0.025,
        "Source cells marked with black stars; 50% front uses prespecified arrival ordering",
        ha="center",
    )
    fig.subplots_adjust(left=0.03, right=0.97, top=0.86, bottom=0.21, wspace=0.08)
    return fig


def _representative_residual(result: Goal006Result, eta: float) -> np.ndarray:
    rows = [row for row in result.representative_realizations if row["eta"] == eta]
    summary = next(
        row
        for row in result.replicate_summaries
        if row.replicate_index == int(cast(int, result.diagnostics["representative_index"]))
        and row.eta == eta
    )
    grid = np.full(result.landscape.shape, np.nan, dtype=np.float64)
    for row in rows:
        r, c = int(cast(int, row["row"])), int(cast(int, row["col"]))
        arrival = float(cast(float, row["arrival"]))
        reference_arrival = float(cast(float, row["reference_arrival"]))
        if arrival > 0.0 and reference_arrival > 0.0:
            grid[r, c] = float(np.log(summary.alignment_scale * arrival / reference_arrival))
        else:
            grid[r, c] = 0.0
    return grid


def _representative_front_categories(result: Goal006Result, eta: float) -> np.ndarray:
    rows_eta = [row for row in result.representative_realizations if row["eta"] == eta]
    rows_ref = [row for row in result.representative_realizations if row["eta"] == 1.0]
    eta_values = {
        int(cast(int, row["cell_id"])): float(cast(float, row["arrival"])) for row in rows_eta
    }
    ref_values = {
        int(cast(int, row["cell_id"])): float(cast(float, row["arrival"])) for row in rows_ref
    }
    ordered_eta = sorted(eta_values, key=lambda cell: (eta_values[cell], cell))
    ordered_ref = sorted(ref_values, key=lambda cell: (ref_values[cell], cell))
    count = int(np.ceil(0.5 * len(ordered_eta)))
    eta_front, ref_front = set(ordered_eta[:count]), set(ordered_ref[:count])
    grid = np.full(result.landscape.shape, np.nan, dtype=np.float64)
    for cell in ref_values:
        row, col = divmod(cell, result.landscape.cols)
        in_eta, in_ref = cell in eta_front, cell in ref_front
        grid[row, col] = 3.0 if in_eta and in_ref else 2.0 if in_eta else 1.0 if in_ref else 0.0
    return grid


def _mark_sources(axis: Axes, result: Goal006Result) -> None:
    source_rows, source_cols = np.where(result.landscape.source_zone != "")
    axis.scatter(source_cols, source_rows, marker="*", color="black", s=18, linewidths=0.3)


def _contrast_figure(result: Goal006Result) -> Figure:
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    rows = result.spatial_effect_summary
    ax.plot(
        [r.eta for r in rows],
        [r.corridor_matrix_contrast for r in rows],
        "o-",
        label="corridor - matrix",
    )
    ax.plot(
        [r.eta for r in rows], [r.patch_matrix_contrast for r in rows], "o-", label="patch - matrix"
    )
    ax.plot(
        [r.eta for r in rows],
        [r.water_matrix_contrast for r in rows],
        "o-",
        label="water-adjacent matrix - matrix",
    )
    ax.axhline(0.0, color="black", linewidth=0.7)
    ax.set(
        xlabel="eta",
        ylabel="Median aligned residual contrast",
        title="Habitat contrasts (diagnostic alignment)",
    )
    ax.legend()
    fig.tight_layout()
    return fig


def _source_figure(result: Goal006Result) -> Figure:
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for eta in result.config.etas:
        values = [
            r.source_reassignment_fraction for r in result.replicate_summaries if r.eta == eta
        ]
        ax.scatter([eta] * len(values), values, s=10, alpha=0.5)
    ax.set(
        xlabel="eta",
        ylabel="Source-zone reassignment fraction",
        title="Raw source provenance changes",
    )
    fig.tight_layout()
    return fig
