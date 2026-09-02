#!/usr/bin/env python3
"""Freeze or score the Arc 2B prey-effect recoverability surfaces."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from latent_landscapes.arc2b_synthesis import (
    DEFAULT_BOOTSTRAPS,
    DEFAULT_FROZEN_PREDICTIONS,
    DEFAULT_OUTPUT_DIR,
    freeze_predictions,
    load_and_run_synthesis,
    summarize_for_cli,
    write_frozen_predictions,
    write_review_bundle,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="mode", required=True)
    freeze = subcommands.add_parser("freeze", help="fit pilot surfaces and freeze S17-S32")
    freeze.add_argument("--pilot-dir", type=Path, required=True)
    freeze.add_argument("--predictions", type=Path, default=DEFAULT_FROZEN_PREDICTIONS)
    final = subcommands.add_parser("final", help="score prospective block and synthesize")
    final.add_argument("--pilot-dir", type=Path, required=True)
    final.add_argument("--prospective-dir", type=Path, required=True)
    final.add_argument("--predictions", type=Path, default=DEFAULT_FROZEN_PREDICTIONS)
    final.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    final.add_argument("--bootstraps", type=int, default=DEFAULT_BOOTSTRAPS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.mode == "freeze":
            rows = freeze_predictions(args.pilot_dir)
            path = write_frozen_predictions(rows, args.predictions)
            print(f"Frozen {len(rows)} Arc 2B prospective predictions to {path}")
            return 0
        result = load_and_run_synthesis(
            args.pilot_dir,
            args.prospective_dir,
            args.predictions,
            bootstrap_count=args.bootstraps,
        )
        written = write_review_bundle(result, args.output_dir)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Arc 2B synthesis failed: {error}", file=sys.stderr)
        return 1
    if result.outcome == "implementation_blocked":
        print(
            f"Arc 2B synthesis blocked; wrote {len(written)} diagnostic files to {args.output_dir}",
            file=sys.stderr,
        )
        return 1
    print(summarize_for_cli(result), end="")
    print(f"Wrote {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
