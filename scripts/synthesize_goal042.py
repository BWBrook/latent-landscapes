#!/usr/bin/env python3
"""Build the Goal 042 Arc 2A 32-truth synthesis bundle."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from latent_landscapes.goal042 import (
    DEFAULT_BOOTSTRAPS,
    DEFAULT_OUTPUT_DIR,
    load_inputs,
    run_goal042,
    summarize_for_cli,
    write_review_bundle,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal039-dir", type=Path, required=True)
    parser.add_argument("--goal040-dir", type=Path, required=True)
    parser.add_argument("--goal041-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--bootstraps", type=int, default=DEFAULT_BOOTSTRAPS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        inputs = load_inputs(args.goal039_dir, args.goal040_dir, args.goal041_dir)
        result = run_goal042(inputs, bootstrap_count=args.bootstraps)
        written = write_review_bundle(result, args.output_dir)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Goal 042 failed: {error}", file=sys.stderr)
        return 1
    print(summarize_for_cli(result), end="")
    print(f"Wrote {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
