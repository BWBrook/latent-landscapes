#!/usr/bin/env python3
"""Run Goal 011 and write its deterministic review pack."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from latent_landscapes.goal011 import artifacts, benchmark


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run central joint recovery under known imperfect detection."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=artifacts.DEFAULT_OUTPUT_DIR,
        help="Review-pack destination.",
    )
    parser.add_argument(
        "--reduced-smoke",
        action="store_true",
        help="Run the explicit non-scientific reduced configuration.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = benchmark.smoke_config() if args.reduced_smoke else benchmark.DEFAULT_CONFIG
    try:
        result = benchmark.run_goal011(config)
        if result.outcome == "implementation_blocked":
            print(result.outcome, file=sys.stderr)
            return 1
        artifacts.write_review_bundle(result, args.output_dir)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"implementation_blocked: {error}", file=sys.stderr)
        return 1
    print(result.outcome)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
