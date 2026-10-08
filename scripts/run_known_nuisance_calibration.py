#!/usr/bin/env python3
"""Run Goal 049 known-nuisance calibration smoke, timing, or registered production."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from latent_landscapes.known_nuisance_calibration import (
    DEFAULT_OUTPUT_DIR,
    production_config,
    run_campaign,
    smoke_config,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "timing", "production"), required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--bank-cache", type=Path)
    parser.add_argument("--budget-receipt", type=Path)
    parser.add_argument(
        "--registration",
        type=Path,
        default=Path("docs/goals/049-operational-calibration/registration-2026-09-20.md"),
    )
    parser.add_argument("--smoke-calibration", type=int, default=2)
    parser.add_argument("--smoke-evaluation", type=int, default=2)
    parser.add_argument("--smoke-low-bank", type=int, default=8)
    parser.add_argument("--smoke-high-bank", type=int, default=16)
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 8:
        parser.error("--workers must lie between 1 and 8")
    smoke_options = (
        args.smoke_calibration,
        args.smoke_evaluation,
        args.smoke_low_bank,
        args.smoke_high_bank,
    )
    if any(value <= 0 for value in smoke_options):
        parser.error("smoke counts and bank sizes must be positive")
    if args.smoke_high_bank < args.smoke_low_bank:
        parser.error("--smoke-high-bank must be at least --smoke-low-bank")
    if args.mode != "smoke" and smoke_options != (2, 2, 8, 16):
        parser.error("smoke count options may only be changed in smoke mode")
    if args.mode != "smoke" and args.bank_cache is None:
        parser.error("timing and production require --bank-cache")
    if args.mode == "production" and args.budget_receipt is None:
        parser.error("production requires --budget-receipt")
    if args.mode != "production" and args.budget_receipt is not None:
        parser.error("--budget-receipt may only be used in production mode")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = (
        smoke_config(
            calibration_replicates=args.smoke_calibration,
            evaluation_replicates=args.smoke_evaluation,
            low_bank_size=args.smoke_low_bank,
            high_bank_size=args.smoke_high_bank,
        )
        if args.mode == "smoke"
        else production_config(args.mode)
    )
    try:
        result = run_campaign(
            config,
            output_dir=args.output_dir,
            registration_path=args.registration,
            bank_cache_dir=args.bank_cache,
            budget_receipt_path=args.budget_receipt,
            workers=args.workers,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Goal 049 calibration failed: {error}", file=sys.stderr, flush=True)
        return 1
    print(f"Goal 049 {args.mode} complete: {result.run_summary['outcome']}", flush=True)
    print(f"Run summary: {result.output_dir / 'run_summary.json'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
