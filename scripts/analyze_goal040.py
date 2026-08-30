#!/usr/bin/env python3
"""Build the Goal 040 Arc 2A recoverability-surface review bundle."""

from __future__ import annotations

import argparse
from pathlib import Path

from latent_landscapes.goal040 import (
    DEFAULT_BOOTSTRAPS,
    DEFAULT_OUTPUT_DIR,
    load_goal039_inputs,
    run_goal040,
    summarize_for_cli,
    write_review_bundle,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--goal039-dir",
        type=Path,
        required=True,
        help="Goal 039 eight-file production bundle",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--bootstraps", type=int, default=DEFAULT_BOOTSTRAPS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    inputs = load_goal039_inputs(args.goal039_dir)
    result = run_goal040(inputs, bootstrap_count=args.bootstraps)
    written = write_review_bundle(result, args.output_dir)
    print(summarize_for_cli(result), end="")
    print(f"Wrote {len(written)} files to {args.output_dir}")


if __name__ == "__main__":
    main()
