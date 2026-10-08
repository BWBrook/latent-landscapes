#!/usr/bin/env python3
"""Run Goal 048's fixed retrospective infection-order integration pilot."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from latent_landscapes import arc2c_campaign as arc2c
from latent_landscapes import arc2c_likelihood as likelihood
from latent_landscapes import arc3_campaign as arc3
from latent_landscapes import arc3_design, arc3_landscapes
from latent_landscapes.goal001.spread import passable_edges, source_labels
from latent_landscapes.goal007 import benchmark as goal007
from latent_landscapes.jump_chain_integration import (
    average_jump_curves,
    build_jump_curves,
    curves_to_integration,
    sample_jump_chain,
)


def helper():
    location = Path(__file__).with_name("run_integration_validation.py")
    spec = importlib.util.spec_from_file_location("stage_a_helpers", location)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def context_for(metadata: Path, kind: str):
    root = metadata / f"{kind}-2026090812" / "reference"
    values = {
        name: json.loads((root / file).read_text())
        for name, file in (("summary", "run_summary.json"), ("seeds", "seed_provenance.json"))
    }
    return helper().reconstruct_context(
        values, arc2c.BridgeConfig, arc3, arc2c, goal007, arc3_design, arc3_landscapes
    )


def geometry(context, rhos):
    fixed = context["union_fixed"]
    landscape = fixed.landscape
    sites = tuple(site.row * landscape.cols + site.col for site in fixed.design.sites)
    if tuple(site.site_id for site in fixed.design.sites) != context["site_ids"]:
        raise ValueError("union site ordering differs from integration identifiers")
    return (
        landscape.cell_count,
        passable_edges(landscape),
        tuple(source_labels(landscape)),
        sites,
        context["site_ids"],
        rhos,
    )


def curves_for(geo, seed, *, width=0.25, degree=6):
    count, edges, sources, sites, ids, rhos = geo
    order, rates = sample_jump_chain(count, edges, sources, np.random.default_rng(int(seed)))
    return build_jump_curves(
        order,
        rates,
        sites,
        ids,
        rhos,
        source_nodes=sources,
        maximum_mesh_width=width,
        moment_order=degree,
        maximum_poisson_mean=50,
        poisson_tail_tolerance=1e-14,
    )


def batch_curves(task):
    geo, seeds = task
    return average_jump_curves(curves_for(geo, seed) for seed in seeds)


def save_curves(path, curves):
    np.savez_compressed(
        path,
        interval_starts=curves.interval_starts,
        interval_ends=curves.interval_ends,
        local_moments=curves.local_moments,
        final_survival=curves.final_survival,
        source_sites=curves.source_sites,
        rhos=np.asarray(curves.rhos),
        site_ids=np.asarray(curves.site_ids),
    )


def history_cache(context, kind):
    module = helper()
    selected = (
        (*context["manifest"].calibration, *context["manifest"].validation)
        if kind == "connected"
        else (context["manifest"].validation[0],)
    )
    return [module.paired_mapped_histories(context, seed, arc3, likelihood) for seed in selected]


def surfaces(histories, integration, kind):
    if kind == "connected":
        array = np.empty((2, 500, 1, len(integration.effects)))
        for index, mapped in enumerate(histories):
            for design in range(2):
                rows = tuple(row for row in mapped[design][0] if row.split == "training")
                array[design, index] = likelihood.joint_log_likelihood(rows, integration)
        return {
            "calibration_training_joint": array[:, :250],
            "validation_training_joint": array[:, 250:],
        }
    return {
        "training_joint": np.stack(
            [
                likelihood.joint_log_likelihood(
                    tuple(row for row in histories[0][0][truth] if row.split == "training"),
                    integration,
                )
                for truth in range(3)
            ]
        )
    }


def smoke(geo, seed, effects):
    started = time.perf_counter()
    coarse = curves_for(geo, seed)
    base_seconds = time.perf_counter() - started
    finer = curves_for(geo, seed, width=0.125, degree=8)
    a, b = curves_to_integration(coarse, effects), curves_to_integration(finer, effects)
    pairs = [
        (a.category_mass, b.category_mass),
        *zip(a.survival_moments, b.survival_moments, strict=True),
    ]
    absolute = max(float(np.max(np.abs(x - y))) for x, y in pairs)
    relative = max(float(np.max(np.abs(x[y > 1e-100] / y[y > 1e-100] - 1))) for x, y in pairs)
    valid = all(np.isfinite(x).all() and np.all(x >= 0) for pair in pairs for x in pair)
    result = dict(
        base_order_seconds=base_seconds,
        max_absolute_difference=absolute,
        max_relative_difference_above_1e_minus100=relative,
        coarse=asdict(coarse.diagnostics),
        fine=asdict(finer.diagnostics),
        passed=bool(
            valid and absolute < 1e-10 and coarse.diagnostics.category_sum_error_max < 1e-10
        ),
    )
    return result


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    context = context_for(args.metadata, args.map)
    rhos = (1.0,) if args.map == "connected" else helper().RHO_WINDOW
    geo = geometry(context, rhos)
    effects = context["config"].effects
    seeds = np.load(args.seeds, allow_pickle=False)[args.map]
    if seeds.shape != (3, 1024) or len(np.unique(seeds)) != seeds.size:
        raise ValueError("fixed pilot requires three distinct 1024-order banks per map")
    report = dict(
        map=args.map,
        started_utc=datetime.now(UTC).isoformat(),
        seed_file_sha256=hashlib.sha256(args.seeds.read_bytes()).hexdigest(),
        configurations={},
    )
    if args.smoke:
        report["smoke"] = smoke(geo, seeds[0, 0], effects)
        report["runtime_seconds"] = time.perf_counter() - started
        (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        if not report["smoke"]["passed"]:
            raise RuntimeError("target numerical refinement smoke failed")
        return
    histories = history_cache(context, args.map)
    arrays = {"effects": np.asarray(effects), "rhos": np.asarray(rhos)}
    with ProcessPoolExecutor(
        max_workers=args.workers, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        for replicate in range(3):
            aggregate = None
            prior = 0
            for size in (256, 1024):
                batches = (
                    (geo, seeds[replicate, first : first + 32]) for first in range(prior, size, 32)
                )
                increment = average_jump_curves(pool.map(batch_curves, batches))
                aggregate = (
                    increment if aggregate is None else average_jump_curves((aggregate, increment))
                )
                if aggregate.diagnostics.draw_count != size:
                    raise RuntimeError("prefix aggregation draw count differs")
                label = f"rep{replicate}_k{size}"
                save_curves(args.output / f"{label}-curves.npz", aggregate)
                integration = curves_to_integration(aggregate, effects)
                configuration = dict(
                    diagnostics=asdict(aggregate.diagnostics),
                    curves_checksum=aggregate.chain_checksum,
                    elapsed_seconds=time.perf_counter() - started,
                )
                try:
                    values = surfaces(histories, integration, args.map)
                    arrays.update({f"{label}_{key}": value for key, value in values.items()})
                    configuration["support_status"] = "finite"
                except RuntimeError as error:
                    configuration["support_status"] = "failed"
                    configuration["error"] = str(error)
                report["configurations"][label] = configuration
                np.savez_compressed(args.output / "likelihood-arrays.npz", **arrays)
                (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
                print(
                    f"{datetime.now(UTC).isoformat()} {args.map} {label} "
                    f"support={configuration['support_status']}",
                    flush=True,
                )
                del integration
                prior = size
    report["completed_utc"] = datetime.now(UTC).isoformat()
    report["runtime_seconds"] = time.perf_counter() - started
    report["completion_status"] = "complete"
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--seeds", type=Path, required=True)
    parser.add_argument("--map", choices=("connected", "corridor"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=4)
    parser.add_argument("--smoke", action="store_true")
    run(parser.parse_args())
