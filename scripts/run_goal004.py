#!/usr/bin/env python3
"""Run Goal 004 stochastic one-rate recovery and calibration."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from latent_landscapes.goal004 import benchmark
from latent_landscapes.goal004.artifacts import DEFAULT_OUTPUT_DIR, write_review_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Review-bundle output directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = benchmark.run_goal004()
    if result.outcome == "implementation_blocked":
        print(
            "Goal 004 blocked: implementation_blocked; review bundle was not written.",
            file=sys.stderr,
        )
        return 1
    try:
        written = write_review_bundle(result, args.output_dir)
    except Exception as error:
        print(
            f"Goal 004 blocked: implementation_blocked; review bundle failed: {error}",
            file=sys.stderr,
        )
        return 1
    print("Goal 004 stochastic one-rate recovery and calibration complete")
    print(f"Outcome: {result.outcome}")
    print(f"Wrote {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
