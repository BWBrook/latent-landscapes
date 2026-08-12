#!/usr/bin/env python3
"""Run the Goal 031 latent-arrival prey-effect positive control."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from latent_landscapes.goal031 import (
    DEFAULT_CONFIG,
    DEFAULT_GOAL029_EVIDENCE_DIR,
    run_goal031,
    smoke_config,
    write_review_bundle,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--reduced-smoke", action="store_true")
    mode.add_argument("--production", action="store_true")
    parser.add_argument(
        "--goal029-evidence-dir",
        type=Path,
        default=DEFAULT_GOAL029_EVIDENCE_DIR,
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_goal031(
            args.goal029_evidence_dir,
            smoke_config() if args.reduced_smoke else DEFAULT_CONFIG,
            workers=args.workers,
        )
        written = write_review_bundle(result, args.output_dir)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Goal 031 failed: {error}", file=sys.stderr)
        return 1
    print("Goal 031 latent-arrival prey-effect positive control complete")
    print(f"Outcome: {result.outcome}")
    print(f"Wrote {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
