#!/usr/bin/env python3
"""Run the registered Goal 050 model-adequacy replay and null blocks."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

# Numerical-library threads are part of the registered execution contract.
for _name in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ.setdefault(_name, "1")

from latent_landscapes.model_adequacy_campaign import (  # noqa: E402
    DEFAULT_ORIGINAL_OUTPUT_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_REGISTRATION_PATH,
    production_config,
    run_campaign,
    smoke_config,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "timing", "production"), required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--original-output-dir", type=Path, default=DEFAULT_ORIGINAL_OUTPUT_DIR)
    parser.add_argument("--bank-cache", type=Path)
    parser.add_argument("--registration", type=Path, default=DEFAULT_REGISTRATION_PATH)
    parser.add_argument("--budget-receipt", type=Path)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--smoke-calibration", type=int, default=2)
    parser.add_argument("--smoke-evaluation", type=int, default=2)
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 8:
        parser.error("--workers must lie between 1 and 8")
    if args.mode != "smoke" and args.bank_cache is None:
        parser.error("timing and production require --bank-cache")
    if args.mode == "production" and args.budget_receipt is None:
        parser.error("production requires --budget-receipt")
    if args.mode != "production" and args.budget_receipt is not None:
        parser.error("--budget-receipt may only be used in production mode")
    if args.mode != "smoke" and (args.smoke_calibration, args.smoke_evaluation) != (2, 2):
        parser.error("smoke count options may only be changed in smoke mode")
    if args.smoke_calibration <= 0 or args.smoke_evaluation <= 0:
        parser.error("smoke replicate counts must be positive")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = (
        smoke_config(
            calibration_replicates=args.smoke_calibration,
            evaluation_replicates=args.smoke_evaluation,
        )
        if args.mode == "smoke"
        else production_config(args.mode)
    )
    try:
        summary = run_campaign(
            config,
            output_dir=args.output_dir,
            original_output_dir=args.original_output_dir,
            bank_cache_dir=args.bank_cache,
            registration_path=args.registration,
            budget_receipt_path=args.budget_receipt,
            workers=args.workers,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Goal 050 model adequacy failed: {error}", file=sys.stderr, flush=True)
        return 1
    print(f"Goal 050 {args.mode} complete: {summary['outcome']}", flush=True)
    print(f"Run summary: {args.output_dir / 'run_summary.json'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
