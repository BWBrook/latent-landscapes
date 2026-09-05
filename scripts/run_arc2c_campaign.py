#!/usr/bin/env python3
"""Run the frozen Arc 2C spread-speed/prey-effect paired campaign."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from latent_landscapes.arc2b_campaign import current_git_commit
from latent_landscapes.arc2c_campaign import (
    DEFAULT_OUTPUT_DIR,
    run_campaign,
    write_campaign_bundle,
)
from latent_landscapes.arc2c_design import BridgeConfig, smoke_config, timing_config


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "timing", "production"), required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--bank-cache", type=Path, help="Directory containing a verified arrival bank"
    )
    args = parser.parse_args(argv)
    if args.workers <= 0:
        parser.error("--workers must be positive")
    return args


def main() -> int:
    args = parse_args()
    config = (
        smoke_config()
        if args.mode == "smoke"
        else timing_config()
        if args.mode == "timing"
        else BridgeConfig()
    )
    try:
        result = run_campaign(
            config,
            mode=args.mode,
            workers=args.workers,
            source_commit=current_git_commit(),
            bank_cache_dir=args.bank_cache,
        )
        written = write_campaign_bundle(result, args.output_dir)
        if result.outcome == "implementation_blocked":
            raise RuntimeError(
                "campaign implementation invariants failed; inspect run_summary.json"
            )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Arc 2C campaign failed: {error}", file=sys.stderr, flush=True)
        return 1
    print(f"Arc 2C {args.mode} campaign complete: {result.outcome}", flush=True)
    print(f"Runtime seconds: {result.runtime_seconds:.3f}", flush=True)
    print(f"Wrote {len(written)} files to {args.output_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
