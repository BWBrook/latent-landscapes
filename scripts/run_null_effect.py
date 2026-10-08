#!/usr/bin/env python3
"""Run one authenticated Goal054 timing or production phase."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

for _name in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ[_name] = "1"

from latent_landscapes.null_effect_campaign import run_phase  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("phase", choices=("timing", "production"))
    parser.add_argument("--old-root", type=Path, required=True)
    parser.add_argument("--pilot-output", type=Path, required=True)
    parser.add_argument("--wrapper", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    summary = run_phase(
        args.root,
        args.phase,
        args.old_root,
        args.pilot_output,
        args.wrapper,
        args.workers,
    )
    print(summary["fingerprint"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
