#!/usr/bin/env python3
"""Build the bounded Arc 3 landscape and pilot-design gallery."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from latent_landscapes.arc3_design import (
    MASTER_SEED,
    PILOT_MAP_SEED,
    PRODUCTION_MAP_SEEDS,
    build_sampling_pair,
    sampling_checks,
)
from latent_landscapes.arc3_landscapes import (
    ARCHETYPES,
    build_landscape,
    describe_landscape,
    map_checks,
)

DEFAULT_OUTPUT_DIR = Path("artifacts/arc3_design")
_CLASS_ORDER = (
    "water",
    "low_quality_matrix",
    "medium_quality",
    "high_quality_patch",
    "corridor",
    "source_zone",
)
_CLASS_COLOURS = (
    "#3b5f8a",
    "#d9c7a5",
    "#9dbb8d",
    "#4f8b57",
    "#d88c45",
    "#8f4d65",
)


def _sampling_seed(map_seed: int) -> int:
    return int(np.random.SeedSequence([MASTER_SEED, map_seed, 1]).generate_state(1)[0])


def _plot_map(ax: Any, landscape: Any, *, sites: Any = None, title: str = "") -> None:
    values = np.zeros(landscape.shape, dtype=np.int8)
    for index, name in enumerate(_CLASS_ORDER):
        values[landscape.habitat_class == name] = index
    ax.imshow(
        values,
        cmap=ListedColormap(_CLASS_COLOURS),
        interpolation="none",
        origin="upper",
        vmin=0,
        vmax=len(_CLASS_ORDER) - 1,
    )
    source_rows, source_cols = np.where(landscape.source_zone != "")
    ax.scatter(source_cols, source_rows, s=2, c="#fff3c4", linewidths=0, alpha=0.9)
    if sites is not None:
        training = [site for site in sites if site.split == "training"]
        holdout = [site for site in sites if site.split == "holdout"]
        ax.scatter(
            [site.col for site in training],
            [site.row for site in training],
            s=8,
            facecolors="white",
            edgecolors="black",
            linewidths=0.35,
            label="training",
        )
        ax.scatter(
            [site.col for site in holdout],
            [site.row for site in holdout],
            s=22,
            marker="*",
            c="black",
            linewidths=0.25,
            label="holdout",
        )
    ax.set_title(title, fontsize=9)
    ax.set_xticks([])
    ax.set_yticks([])


def _save_figure(figure: Any, output: Path, stem: str) -> None:
    figure.savefig(output / f"{stem}.png", dpi=180, bbox_inches="tight")
    figure.savefig(output / f"{stem}.svg", bbox_inches="tight", metadata={"Date": None})
    plt.close(figure)


def _add_habitat_legend(figure: Any) -> None:
    handles = [
        Patch(facecolor=colour, edgecolor="none", label=name.replace("_", " "))
        for name, colour in zip(_CLASS_ORDER, _CLASS_COLOURS, strict=True)
    ]
    figure.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.025),
        ncol=6,
        fontsize=8,
        frameon=False,
    )


def _build_production_gallery(output: Path, records: dict[str, Any]) -> None:
    figure, axes = plt.subplots(3, 3, figsize=(11.5, 10.0), constrained_layout=True)
    for row, map_seed in enumerate(PRODUCTION_MAP_SEEDS):
        for col, archetype in enumerate(ARCHETYPES):
            landscape = build_landscape(archetype, map_seed)
            key = f"production_{map_seed}_{archetype}"
            sampling_seed = _sampling_seed(map_seed)
            pair = build_sampling_pair(landscape, sampling_seed)
            records[key] = _record_map(
                landscape,
                archetype,
                map_seed,
                "production",
                sampling_seed=sampling_seed,
                sampling_checks=sampling_checks(landscape, pair),
            )
            _plot_map(
                axes[row, col],
                landscape,
                title=f"{archetype}\nseed {map_seed}",
            )
    figure.suptitle("Arc 3 production landscape gallery", fontsize=14)
    _add_habitat_legend(figure)
    _save_figure(figure, output, "production_landscape_gallery")


def _build_pilot_gallery(output: Path, records: dict[str, Any]) -> None:
    figure, axes = plt.subplots(3, 2, figsize=(9.0, 11.0), constrained_layout=True)
    for row, archetype in enumerate(ARCHETYPES):
        map_seed = PILOT_MAP_SEED
        landscape = build_landscape(archetype, map_seed)
        seed = _sampling_seed(map_seed)
        pair = build_sampling_pair(landscape, seed)
        checks = sampling_checks(landscape, pair)
        for design_index, (design_name, design) in enumerate(
            zip(("access", "balanced"), pair, strict=True)
        ):
            axes[row, design_index].set_aspect("equal")
            _plot_map(
                axes[row, design_index],
                landscape,
                sites=design.sites,
                title=f"pilot {archetype} / {design_name}",
            )
            if design_index == 0:
                axes[row, design_index].legend(
                    loc="upper left", fontsize=7, framealpha=0.85, markerscale=0.8
                )
        key = f"pilot_{map_seed}_{archetype}"
        records[key] = _record_map(
            landscape,
            archetype,
            map_seed,
            "pilot",
            sampling_seed=seed,
            sampling_checks=checks,
        )
    figure.suptitle("Arc 3 pilot sampling designs", fontsize=14)
    _add_habitat_legend(figure)
    _save_figure(figure, output, "pilot_sampling_gallery")


def _record_map(
    landscape: Any,
    archetype: str,
    map_seed: int,
    role: str,
    *,
    sampling_seed: int | None = None,
    sampling_checks: dict[str, bool] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "archetype": archetype,
        "map_seed": map_seed,
        "role": role,
        "map_checks": map_checks(landscape),
        "landscape_descriptors": describe_landscape(landscape),
    }
    if sampling_seed is not None:
        record["sampling_seed"] = sampling_seed
    if sampling_checks is not None:
        record["sampling_checks"] = sampling_checks
    return record


def build_gallery(output: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Create all design-stage figures and structural JSON records."""

    output.mkdir(parents=True, exist_ok=True)
    records: dict[str, Any] = {}
    _build_production_gallery(output, records)
    _build_pilot_gallery(output, records)
    manifest = {
        "workflow": "arc3-landscape-sampling-design-gallery",
        "master_seed": MASTER_SEED,
        "pilot_map_seed": PILOT_MAP_SEED,
        "production_map_seeds": list(PRODUCTION_MAP_SEEDS),
        "sampling_seed_rule": "SeedSequence([MASTER_SEED, map_seed, 1]).generate_state(1)[0]",
        "recovery_outcomes_examined": False,
        "maps": records,
    }
    with (output / "structural_descriptors_and_checks.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    manifest = build_gallery(args.output_dir)
    print(f"wrote {len(manifest['maps'])} map records to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
