#!/usr/bin/env python3
"""Synthesize the six paired Arc 2C cases from saved likelihood profiles."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from latent_landscapes.arc2c_synthesis import (
    DEFAULT_BOOTSTRAPS,
    DEFAULT_OUTPUT_DIR,
    load_campaign_bundle,
    run_synthesis,
    write_review_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--bootstraps", type=int, default=DEFAULT_BOOTSTRAPS)
    args = parser.parse_args()
    try:
        bundle = load_campaign_bundle(args.input_dir)
        result = run_synthesis(bundle, bootstrap_count=args.bootstraps)
        written = write_review_bundle(result, args.output_dir)
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"Arc 2C synthesis failed: {error}", file=sys.stderr)
        return 1
    print(f"Arc 2C: {result.outcome}; six cases, {len(result.conditions)} parameter summaries")
    print(
        f"Bootstrap resamples: {result.bootstrap_count}; "
        f"review signals: {len(result.caution_flags)}"
    )
    print(f"Wrote {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
