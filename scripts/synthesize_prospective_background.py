#!/usr/bin/env python3
"""Synthesize the registered Goal053 prospective background evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from latent_landscapes.prospective_background_synthesis import synthesize


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir", type=Path, required=True, help="parent runner evidence directory"
    )
    parser.add_argument(
        "--output-dir", type=Path, required=True, help="new synthesis output directory"
    )
    parser.add_argument(
        "--testing",
        action="store_true",
        help=(
            "allow a deliberately small six-cell fixture; production runs remain strict by default"
        ),
    )
    args = parser.parse_args()
    result = synthesize(args.input_dir, args.output_dir, strict=not args.testing)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
