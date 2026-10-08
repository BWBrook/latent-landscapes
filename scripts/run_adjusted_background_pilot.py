#!/usr/bin/env python3
"""Run the registered Goal 052 archived-history likelihood pilot."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

for name in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[name] = "1"

from latent_landscapes.adjusted_background_pilot import run_pilot  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bank-cache", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--archive-contract", type=Path, required=True)
    parser.add_argument("--execution-wrapper", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-seconds", type=int, default=14400)
    args = parser.parse_args()
    run_pilot(
        output_dir=args.output_dir,
        bank_cache=args.bank_cache,
        archive_path=args.archive,
        archive_contract=args.archive_contract,
        execution_wrapper=args.execution_wrapper,
        workers=args.workers,
        max_seconds=args.max_seconds,
    )


if __name__ == "__main__":
    main()
