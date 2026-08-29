#!/usr/bin/env python3
"""Build the Goal 038 Arc 2A ecological parameterization review pack."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from latent_landscapes.goal038 import DEFAULT_OUTPUT_DIR, run_goal038, write_review_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_goal038()
        written = write_review_bundle(result, args.output_dir)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Goal 038 failed: {error}", file=sys.stderr)
        return 1
    print("Goal 038 Arc 2A design review pack complete")
    print(f"Outcome: {result.outcome}")
    print(f"Sobol truths: {len(result.pilot_truths)}")
    print(f"Initial histories: {result.compute_budget[0].total_history_count}")
    print(f"Wrote {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
