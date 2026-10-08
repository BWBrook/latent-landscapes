#!/usr/bin/env python3
"""Synthesize the registered Goal 054 null-effect statistics table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from latent_landscapes.null_effect_synthesis import BOOTSTRAP_DRAWS, synthesize


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input-npz", "--input", type=Path, help="stats.npz written by the runner")
    source.add_argument("--input-dir", type=Path, help="directory containing stats.npz")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--testing",
        action="store_true",
        help="accept a small deterministic fixture; production remains strict",
    )
    parser.add_argument(
        "--bootstrap-draws",
        type=int,
        default=BOOTSTRAP_DRAWS,
        help="only useful for non-strict test fixtures; production is fixed at 2,000",
    )
    args = parser.parse_args()
    input_npz = args.input_npz or args.input_dir / "stats.npz"
    summary = synthesize(
        input_npz,
        args.output_dir,
        bootstrap_draws=args.bootstrap_draws,
        strict=not args.testing,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
