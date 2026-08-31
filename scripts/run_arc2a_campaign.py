#!/usr/bin/env python3
"""Run either frozen Arc 2A predator recoverability campaign block."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from latent_landscapes.arc2a_campaign import (
    DEFAULT_OUTPUT_DIR,
    PILOT_CONFIG,
    current_git_commit,
    prospective_config,
    run_campaign,
    smoke_config,
    timing_config,
    write_review_bundle,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--reduced-smoke", action="store_true")
    mode.add_argument("--timing-probe", action="store_true")
    mode.add_argument("--production", action="store_true")
    parser.add_argument("--block", choices=("pilot", "prospective"), required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--workers", type=int, default=1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    block = args.block
    config = (
        smoke_config(block)
        if args.reduced_smoke
        else timing_config(block)
        if args.timing_probe
        else PILOT_CONFIG
        if block == "pilot"
        else prospective_config()
    )
    try:
        result = run_campaign(
            config,
            workers=args.workers,
            source_commit=current_git_commit(),
        )
        if result.outcome == "implementation_blocked":
            raise RuntimeError(result.outcome)
        written = write_review_bundle(result, args.output_dir)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Arc 2A campaign failed: {error}", file=sys.stderr)
        return 1
    print(f"Arc 2A {block} campaign complete")
    print(f"Outcome: {result.outcome}")
    print(f"Runtime seconds: {result.runtime_seconds:.1f}")
    print(f"Wrote {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
