#!/usr/bin/env python3
"""Build the Goal 017 weak-contrast decision-target review pack."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from latent_landscapes.goal017.artifacts import write_review_bundle
from latent_landscapes.goal017.reconciliation import analyze_evidence


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal012-evidence-dir", type=Path, required=True)
    parser.add_argument("--goal016-evidence-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = analyze_evidence(args.goal012_evidence_dir, args.goal016_evidence_dir)
        written = write_review_bundle(result, args.output_dir)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Goal 017 failed: {error}", file=sys.stderr)
        return 1
    print("Goal 017 decision-target reconciliation complete")
    print(f"Outcome: {result.outcome}")
    print(f"Wrote {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
