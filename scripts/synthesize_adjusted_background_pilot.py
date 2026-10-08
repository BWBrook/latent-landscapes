#!/usr/bin/env python3
"""Synthesize a frozen Goal052 adjusted-background evidence bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from latent_landscapes.adjusted_background_synthesis import synthesize


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True, help="parent runner evidence.npz")
    parser.add_argument("--output-dir", type=Path, required=True, help="synthesis output directory")
    args = parser.parse_args()
    print(json.dumps(synthesize(args.evidence, args.output_dir), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
