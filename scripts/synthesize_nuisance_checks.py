#!/usr/bin/env python3
"""Synthesize Goal 055 without changing the Goal 054 calibration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from latent_landscapes.nuisance_check_synthesis import synthesize


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = synthesize(args.input, args.reference, args.output)
    print(json.dumps(summary, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
