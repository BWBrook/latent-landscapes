#!/usr/bin/env python3
"""Build the Arc 2A 32-truth synthesis bundle."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from latent_landscapes.arc2a_synthesis import (
    DEFAULT_BOOTSTRAPS,
    DEFAULT_FROZEN_PREDICTIONS,
    DEFAULT_OUTPUT_DIR,
    load_inputs,
    run_synthesis,
    summarize_for_cli,
    write_review_bundle,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-dir", type=Path, required=True)
    parser.add_argument("--prospective-dir", type=Path, required=True)
    parser.add_argument("--frozen-predictions", type=Path, default=DEFAULT_FROZEN_PREDICTIONS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--bootstraps", type=int, default=DEFAULT_BOOTSTRAPS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        inputs = load_inputs(
            args.pilot_dir,
            args.prospective_dir,
            args.frozen_predictions,
        )
        result = run_synthesis(inputs, bootstrap_count=args.bootstraps)
        written = write_review_bundle(result, args.output_dir)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Arc 2A failed: {error}", file=sys.stderr)
        return 1
    print(summarize_for_cli(result), end="")
    print(f"Wrote {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
