#!/usr/bin/env python3
"""Run the Goal 010 boundary-aware joint identifiability diagnosis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from latent_landscapes.goal010 import artifacts, benchmark


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--goal009-pack",
        type=Path,
        required=True,
        help="Authenticated Goal 009 scientific-pack directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=artifacts.DEFAULT_OUTPUT_DIR,
        help="Goal 010 review-bundle output directory.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Number of selected truth-cell worker processes.",
    )
    parser.add_argument(
        "--compute-provenance-json",
        type=Path,
        required=True,
        help="Strict compute-provenance JSON object.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run the fixed reduced nonproduction configuration.",
    )
    return parser.parse_args()


def _load_json_object(path: Path) -> dict[str, object]:
    def reject(value: str) -> None:
        raise ValueError(f"non-finite JSON token: {value}")

    payload = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)
    if not isinstance(payload, dict) or not all(isinstance(key, str) for key in payload):
        raise ValueError("compute provenance must be a JSON object")
    return payload


def main() -> int:
    args = parse_args()
    try:
        provenance = _load_json_object(args.compute_provenance_json)
        artifacts.validate_pre_campaign_provenance(
            provenance,
            workers=args.workers,
            smoke=args.smoke,
        )
        baseline = benchmark.read_goal009_pack(
            args.goal009_pack,
            require_published=not args.smoke,
        )
    except Exception as error:
        print(
            f"Goal 010 campaign did not start: {error}; no scientific pack was written.",
            file=sys.stderr,
        )
        return 1

    config = benchmark.smoke_config() if args.smoke else benchmark.DEFAULT_CONFIG
    try:
        result = benchmark.run_campaign(
            baseline,
            config=config,
            workers=args.workers,
        )
    except Exception as error:
        print(
            f"Goal 010 campaign did not complete: {error}; no scientific pack was written.",
            file=sys.stderr,
        )
        return 1
    if result.outcome == "implementation_blocked":
        print(
            "Goal 010 completed with implementation_blocked; no scientific pack was written.",
            file=sys.stderr,
        )
        return 1
    try:
        written = artifacts.write_review_bundle(
            result,
            args.output_dir,
            provenance,
        )
        artifacts.validate_review_bundle(args.output_dir)
    except Exception as error:
        print(
            f"Goal 010 review bundle failed validation: {error}; "
            "no accepted scientific claim was made.",
            file=sys.stderr,
        )
        return 1
    mode = "reduced smoke" if args.smoke else "production campaign"
    print(f"Goal 010 {mode} complete")
    print(f"Outcome: {result.outcome}")
    print(f"Wrote and validated {len(written)} files in {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
