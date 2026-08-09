#!/usr/bin/env python3
"""Run the Goal 024 resistance-transition benchmark."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from latent_landscapes.goal024 import (
    DEFAULT_CONFIG,
    DEFAULT_GOAL023_EVIDENCE_DIR,
    run_goal024,
    smoke_config,
    write_review_bundle,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--reduced-smoke", action="store_true")
    mode.add_argument("--production", action="store_true")
    parser.add_argument(
        "--goal023-evidence-dir",
        type=Path,
        default=DEFAULT_GOAL023_EVIDENCE_DIR,
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_goal024(
            args.goal023_evidence_dir,
            smoke_config() if args.reduced_smoke else DEFAULT_CONFIG,
        )
        written = write_review_bundle(result, args.output_dir)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Goal 024 failed: {error}", file=sys.stderr)
        return 1
    print("Goal 024 resistance-transition benchmark complete")
    print(f"Outcome: {result.outcome}")
    print(f"Midpoint joint outcome: {result.midpoint_joint_outcome}")
    print(f"Wrote {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
