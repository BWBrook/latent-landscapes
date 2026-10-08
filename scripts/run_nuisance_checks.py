#!/usr/bin/env python3
"""Run the registered Goal 055 nuisance-check archive phase."""

from __future__ import annotations

import argparse
from pathlib import Path

from latent_landscapes.nuisance_check_campaign import run_phase


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("timing", "production"))
    parser.add_argument("--root", type=Path, required=True, help="Goal055 execution root")
    parser.add_argument("--goal054-root", type=Path, required=True, help="Goal054 execution root")
    parser.add_argument("--goal051-root", type=Path, required=True, help="Goal051 execution root")
    parser.add_argument(
        "--old-root", type=Path, required=True, help="authenticated Goal053 integration root"
    )
    parser.add_argument(
        "--bank-cache", type=Path, required=True, help="verified K131072 bank cache"
    )
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    summary = run_phase(
        root=args.root,
        phase=args.phase,
        goal054_root=args.goal054_root,
        goal051_root=args.goal051_root,
        old_root=args.old_root,
        bank_cache=args.bank_cache,
        workers=args.workers,
        batch_size=args.batch_size,
    )
    print(
        f"{args.phase}: {summary['rows']} beta rows; controls_passed={summary['controls_passed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
