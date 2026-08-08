#!/usr/bin/env python3
"""Run the Goal 016 weak-contrast information funnel."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from latent_landscapes.goal016.artifacts import write_review_bundle
from latent_landscapes.goal016.benchmark import DEFAULT_CONFIG, run_goal016, smoke_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--reduced-smoke",
        action="store_true",
        help="Run the small non-scientific implementation check.",
    )
    mode.add_argument(
        "--production",
        action="store_true",
        help="Run the frozen scientific campaign.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = smoke_config() if args.reduced_smoke else DEFAULT_CONFIG
    try:
        result = run_goal016(config)
        written = write_review_bundle(result, args.output_dir)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Goal 016 failed: {error}", file=sys.stderr)
        return 1
    mode = "non-scientific reduced smoke" if args.reduced_smoke else "production campaign"
    print(f"Goal 016 {mode} complete")
    print(f"Outcome: {result.outcome}")
    print(f"Wrote {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
