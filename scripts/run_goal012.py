#!/usr/bin/env python3
"""Run Goal 012 cross-truth recovery under known imperfect detection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from latent_landscapes.goal012 import artifacts, benchmark


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=artifacts.DEFAULT_OUTPUT_DIR,
        help="Review-pack output directory.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=9,
        help="Number of deterministic truth-cell worker processes.",
    )
    parser.add_argument(
        "--compute-provenance-json",
        type=Path,
        required=True,
        help="Portable compute-provenance JSON object.",
    )
    parser.add_argument(
        "--reduced-smoke",
        action="store_true",
        help="Run the explicit non-scientific reduced configuration.",
    )
    return parser.parse_args()


def _load_compute_provenance(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not all(isinstance(key, str) for key in payload):
        raise ValueError("compute provenance must be a JSON object")
    return payload


def main() -> int:
    args = parse_args()
    config = benchmark.smoke_config() if args.reduced_smoke else benchmark.DEFAULT_CONFIG
    try:
        provenance = _load_compute_provenance(args.compute_provenance_json)
        if not args.reduced_smoke and provenance.get("provenance_mode") != "production":
            raise ValueError("production campaign requires production provenance")
        artifacts.validate_pre_campaign_provenance(
            provenance,
            workers=args.workers,
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(
            f"Goal 012 campaign did not start: {error}; no review pack was written.",
            file=sys.stderr,
        )
        return 1
    try:
        result = benchmark.run_campaign(config, workers=args.workers)
        if result.outcome == "implementation_blocked":
            print(result.outcome, file=sys.stderr)
            return 1
        written = artifacts.write_review_bundle(result, args.output_dir, provenance)
    except (OSError, RuntimeError, ValueError) as error:
        print(
            f"Goal 012 campaign did not complete: {error}; no review pack was accepted.",
            file=sys.stderr,
        )
        return 1
    print("Goal 012 cross-truth joint known-detection benchmark complete")
    print(f"Outcome: {result.outcome}")
    print(f"Wrote {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
