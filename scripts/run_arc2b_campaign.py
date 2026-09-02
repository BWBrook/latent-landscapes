#!/usr/bin/env python3
"""Run one frozen Arc 2B prey-effect campaign block."""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections.abc import Sequence
from pathlib import Path

from latent_landscapes.arc2b_campaign import (
    DEFAULT_OUTPUT_DIR,
    PILOT_CONFIG,
    current_git_commit,
    prospective_config,
    run_campaign,
    smoke_config,
    timing_config,
    write_review_bundle,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--reduced-smoke", action="store_true")
    mode.add_argument("--timing-probe", action="store_true")
    mode.add_argument("--production", action="store_true")
    parser.add_argument("--block", choices=("pilot", "prospective"), required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--frozen-predictions", type=Path)
    args = parser.parse_args(argv)
    if args.production and args.block == "prospective":
        if args.frozen_predictions is None:
            parser.error("--frozen-predictions is required for production prospective runs")
        if not args.frozen_predictions.is_file():
            parser.error(f"frozen-predictions file does not exist: {args.frozen_predictions}")
    return args


def main() -> int:
    args = parse_args()
    frozen_digest = None
    if args.production and args.block == "prospective":
        try:
            frozen_digest = hashlib.sha256(args.frozen_predictions.read_bytes()).hexdigest()
        except OSError as error:
            print(f"Arc 2B campaign failed: {error}", file=sys.stderr)
            return 1
    config = (
        smoke_config(args.block)
        if args.reduced_smoke
        else timing_config(args.block)
        if args.timing_probe
        else PILOT_CONFIG
        if args.block == "pilot"
        else prospective_config()
    )
    try:
        result = run_campaign(
            config,
            workers=args.workers,
            source_commit=current_git_commit(),
            frozen_predictions_sha256=frozen_digest,
        )
        if result.outcome == "implementation_blocked":
            raise RuntimeError(result.outcome)
        written = write_review_bundle(result, args.output_dir)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Arc 2B campaign failed: {error}", file=sys.stderr)
        return 1
    print(f"Arc 2B {args.block} campaign complete")
    print(f"Outcome: {result.outcome}")
    print(f"Runtime seconds: {result.runtime_seconds:.3f}")
    print(f"Wrote {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
