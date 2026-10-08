#!/usr/bin/env python3
"""Run one qualified Goal053 phase; the outer wrapper owns its exclusive lock."""

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

from latent_landscapes.prospective_background_campaign import run_phase  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("timing", "production"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--bank-cache", type=Path, required=True)
    parser.add_argument("--pilot-output", type=Path, required=True)
    parser.add_argument("--wrapper", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    run_phase(
        root=args.root,
        phase=args.phase,
        bank_cache=args.bank_cache,
        pilot_output=args.pilot_output,
        wrapper=args.wrapper,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()
