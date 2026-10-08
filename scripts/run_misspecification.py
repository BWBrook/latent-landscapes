#!/usr/bin/env python3
"""Run the registered Goal 051 paired misspecification screen."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

for _name in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ.setdefault(_name, "1")

from latent_landscapes.misspecification_campaign import (  # noqa: E402
    DEFAULT_EXECUTION_ROOT,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_REFERENCE_DIR,
    DEFAULT_REGISTRATION_PATH,
    production_config,
    run_campaign,
    smoke_config,
    timing_config,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "timing", "production"), required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--bank-cache", type=Path)
    parser.add_argument("--reference-dir", type=Path, default=DEFAULT_REFERENCE_DIR)
    parser.add_argument("--registration", type=Path, default=DEFAULT_REGISTRATION_PATH)
    parser.add_argument("--execution-root", type=Path, default=DEFAULT_EXECUTION_ROOT)
    parser.add_argument("--budget-receipt", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--smoke-replicates", type=int, default=1)
    parser.add_argument("--smoke-bank-size", type=int, default=16)
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 8:
        parser.error("--workers must lie between 1 and 8")
    if args.mode != "smoke" and args.bank_cache is None:
        parser.error("timing and production require --bank-cache")
    if args.mode == "production" and args.budget_receipt is None:
        parser.error("production requires --budget-receipt")
    if args.mode != "production" and args.budget_receipt is not None:
        parser.error("--budget-receipt may only be used in production mode")
    if args.mode != "smoke" and (args.smoke_replicates, args.smoke_bank_size) != (1, 16):
        parser.error("smoke options may only be changed in smoke mode")
    if args.smoke_replicates not in (1, 2) or args.smoke_bank_size <= 0:
        parser.error("smoke replicates must be 1 or 2 and bank size must be positive")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = {
        "smoke": smoke_config(replicates=args.smoke_replicates, bank_size=args.smoke_bank_size),
        "timing": timing_config(),
        "production": production_config(),
    }[args.mode]
    try:
        summary = run_campaign(
            config,
            output_dir=args.output_dir,
            bank_cache_dir=args.bank_cache,
            registration_path=args.registration,
            execution_root=args.execution_root,
            reference_dir=args.reference_dir,
            budget_receipt_path=args.budget_receipt,
            workers=args.workers,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Goal 051 misspecification screen failed: {error}", file=sys.stderr, flush=True)
        return 1
    print(f"Goal 051 {args.mode} complete: {summary['outcome']}", flush=True)
    print(f"Run summary: {args.output_dir / 'run_summary.json'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
