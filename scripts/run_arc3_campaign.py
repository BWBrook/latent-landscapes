#!/usr/bin/env python3
"""Run an Arc 3 pilot or frozen production map with paired sampling designs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

from latent_landscapes.arc2b_campaign import current_git_commit
from latent_landscapes.arc2c_design import EFFECT_GRID, RHO_GRID, BridgeConfig
from latent_landscapes.arc3_campaign import run_campaign, write_campaign_bundle
from latent_landscapes.arc3_design import (
    MASTER_SEED,
    PILOT_MAP_SEED,
    PRODUCTION_MAP_SEEDS,
    build_sampling_pair,
)
from latent_landscapes.arc3_landscapes import ARCHETYPES, build_landscape, describe_landscape


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archetype", choices=ARCHETYPES, required=True)
    parser.add_argument("--map-seed", type=int, default=PILOT_MAP_SEED)
    parser.add_argument("--bank-size", type=int, default=None)
    parser.add_argument("--replicates", type=int, default=4)
    parser.add_argument("--rho-points", type=int, default=9)
    parser.add_argument("--effect-points", type=int, default=19)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--production-freeze",
        type=Path,
        default=None,
        help="parent-issued Goal 046 freeze JSON; its presence admits production mode",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.map_seed in PRODUCTION_MAP_SEEDS and args.production_freeze is None:
        parser.error("production map seeds are reserved until the pilot and design freeze")
    if min(args.replicates, args.rho_points, args.effect_points) < 2:
        parser.error("replicate and grid counts must be at least two")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("output directory must be new or empty; retain earlier campaign evidence")
    try:
        production_freeze = None
        if args.production_freeze is not None:
            payload = json.loads(args.production_freeze.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                parser.error("production freeze must contain a JSON object")
            production_freeze = payload
        landscape = build_landscape(args.archetype, args.map_seed)
        sampling_seed = int(
            np.random.SeedSequence([MASTER_SEED, args.map_seed, 1]).generate_state(1)[0]
        )
        campaign_seed = int(
            np.random.SeedSequence(
                [MASTER_SEED, args.map_seed, ARCHETYPES.index(args.archetype), 2]
            ).generate_state(1)[0]
        )
        pair = build_sampling_pair(landscape, sampling_seed)
        production = production_freeze is not None
        if production:
            assert production_freeze is not None
            bank_size = (
                args.bank_size
                if args.bank_size is not None
                else int(production_freeze["selected_bank_size"])
            )
            replicates = 250
            calibration_rank = 239
            rhos, effects = RHO_GRID, EFFECT_GRID
        else:
            bank_size = args.bank_size if args.bank_size is not None else 64
            replicates = args.replicates
            calibration_rank = min(replicates, math.ceil(0.95 * (replicates + 1)))
            rhos = tuple(
                float(value)
                for value in sorted(set(np.exp2(np.linspace(-2, 2, args.rho_points))) | {0.5, 1.0})
            )
            effects = tuple(
                float(value)
                for value in sorted(set(np.linspace(1, 10, args.effect_points)) | {1.0, 3.0, 5.0})
            )
        config = BridgeConfig(
            master_seed=campaign_seed,
            bank_size=bank_size,
            calibration_replicates=replicates,
            validation_replicates=replicates,
            calibration_rank=calibration_rank,
            rhos=rhos,
            effects=effects,
        )
        metadata = {
            "archetype": args.archetype,
            "map_seed": args.map_seed,
            "sampling_seed": sampling_seed,
            "purpose": (
                "production recovery pending numerical review"
                if production
                else "execution and numerical pilot; no scientific recovery acceptance"
            ),
            "landscape_descriptors": describe_landscape(landscape),
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        }
        result = run_campaign(
            landscape,
            pair[0],
            pair[1],
            config,
            mode="production" if production else "pilot",
            workers=args.workers,
            source_commit=current_git_commit(),
            scene_metadata=metadata,
            progress=lambda message: print(message, flush=True),
            production_freeze=production_freeze,
        )
        write_campaign_bundle(result, args.output_dir)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Arc 3 campaign failed: {error}", file=sys.stderr)
        return 1
    print(f"{result.outcome}; output={args.output_dir}")
    return 0 if all(result.invariants.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
