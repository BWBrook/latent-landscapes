#!/usr/bin/env python3
"""Run the frozen Goal 003 stochastic spread process review."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from latent_landscapes.goal003.artifacts import DEFAULT_OUTPUT_DIR, write_review_bundle
from latent_landscapes.goal003.benchmark import build_ensemble


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_ensemble()
    if result.outcome == "implementation_blocked":
        print(
            "Goal 003 blocked: implementation_blocked; review bundle was not written.",
            file=sys.stderr,
        )
        return 1
    written = write_review_bundle(result, args.output_dir)
    print("Goal 003 stochastic spread process review complete")
    print(f"Outcome: {result.outcome}")
    print(f"Wrote {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
