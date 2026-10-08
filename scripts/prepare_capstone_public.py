#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from latent_landscapes.capstone_public import (
    build_arrival_bank,
    freeze_public_inputs,
    load_public_inputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("freeze-public-inputs", "build-bank"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--public-inputs", type=Path)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--root", type=int, choices=(987654321, 2026100403), required=True)
    args = parser.parse_args()
    if args.mode == "freeze-public-inputs":
        freeze_public_inputs(args.output, root=args.root)
    else:
        if args.public_inputs is None:
            raise ValueError("--public-inputs is required")
        build_arrival_bank(
            load_public_inputs(args.public_inputs),
            args.output,
            root=args.root,
            workers=args.workers,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
