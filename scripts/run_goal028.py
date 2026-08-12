#!/usr/bin/env python3
"""Run the Goal 028 known-arrival prey-effect strength transition."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from latent_landscapes.goal028 import (
    DEFAULT_CONFIG,
    DEFAULT_GOAL027_EVIDENCE_DIR,
    run_goal028,
    smoke_config,
    write_review_bundle,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--reduced-smoke", action="store_true")
    mode.add_argument("--production", action="store_true")
    parser.add_argument(
        "--goal027-evidence-dir",
        type=Path,
        default=DEFAULT_GOAL027_EVIDENCE_DIR,
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_goal028(
            args.goal027_evidence_dir,
            smoke_config() if args.reduced_smoke else DEFAULT_CONFIG,
        )
        written = write_review_bundle(result, args.output_dir)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Goal 028 failed: {error}", file=sys.stderr)
        return 1
    print("Goal 028 known-arrival prey-effect strength transition complete")
    print(f"Outcome: {result.outcome}")
    print(f"Wrote {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
