#!/usr/bin/env python3
"""Seal the Goal 060 capstone only after an explicit public readiness gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from latent_landscapes.capstone_sealing import (
    SealingFailure,
    output_records,
    preflight_capstone,
    seal_capstone,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    seal = subparsers.add_parser("seal", help="seal the four private histories")
    seal.add_argument("--ready", type=Path, required=True, dest="readiness_receipt")
    seal.add_argument("--output", type=Path, required=True)
    seal.add_argument("--age-bin", default="age")
    preflight = subparsers.add_parser("preflight", help="check readiness without private entropy")
    preflight.add_argument("--ready", type=Path, required=True, dest="readiness_receipt")
    preflight.add_argument("--age-bin", default="age")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "preflight":
        try:
            result = preflight_capstone(args.readiness_receipt, age_bin=args.age_bin)
        except (SealingFailure, ValueError, OSError):
            print(json.dumps({"status": "failed", "error": "public preflight failed"}), flush=True)
            return 1
        print(json.dumps({"status": "ready", "readiness": result}, sort_keys=True), flush=True)
        return 0
    if args.command != "seal":
        return 2
    try:
        seal_capstone(
            args.readiness_receipt,
            args.output,
            age_bin=args.age_bin,
        )
    except FileExistsError:
        return 2
    except SealingFailure:
        records = output_records(args.output) if args.output.is_dir() else []
        print(json.dumps({"files": records}, sort_keys=True), flush=True)
        return 1
    records = output_records(args.output)
    print(json.dumps({"files": records}, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
