#!/usr/bin/env python3
"""Summarize paired sampling contrasts from one bundle per fixed Arc 3 map."""

from __future__ import annotations

import argparse
from pathlib import Path

from latent_landscapes.arc3_synthesis import (
    DEFAULT_BOOTSTRAP_SEED,
    DEFAULT_BOOTSTRAPS,
    load_map_bundle,
    summarize_maps,
    write_review_bundle,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dirs", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstraps", type=int, default=DEFAULT_BOOTSTRAPS)
    parser.add_argument("--seed", type=int, default=DEFAULT_BOOTSTRAP_SEED)
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("output directory must be new or empty")
    bundles = tuple(load_map_bundle(directory) for directory in args.input_dirs)
    result = summarize_maps(bundles, bootstrap_count=args.bootstraps, bootstrap_seed=args.seed)
    write_review_bundle(result, args.output_dir)
    print(f"{result.outcome}; maps={len(bundles)}; output={args.output_dir}")


if __name__ == "__main__":
    main()
