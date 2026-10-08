#!/usr/bin/env python3
"""Apply the approved Goal 060 certificate to the unchanged Goal 059 public map."""

from __future__ import annotations

import argparse
from pathlib import Path

from latent_landscapes.capstone_recovery import recover_public_inputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-public-inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--predecessor-audit", type=Path, required=True)
    parser.add_argument("--predecessor-source-freeze", type=Path, required=True)
    parser.add_argument("--predecessor-registration", type=Path, required=True)
    parser.add_argument("--registration", type=Path, required=True)
    args = parser.parse_args()
    recover_public_inputs(
        args.original_public_inputs,
        args.output,
        predecessor_audit=args.predecessor_audit,
        predecessor_source=args.predecessor_source_freeze,
        predecessor_registration=args.predecessor_registration,
        registration=args.registration,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
