#!/usr/bin/env python3
"""Run Goal 008 cross-truth joint rho-eta recovery under perfect detection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from latent_landscapes.goal008 import artifacts, benchmark


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
    return parser.parse_args()


def _load_compute_provenance(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not all(isinstance(key, str) for key in payload):
        raise ValueError("compute provenance must be a JSON object")
    return payload


def main() -> int:
    args = parse_args()
    try:
        provenance = _load_compute_provenance(args.compute_provenance_json)
        result = benchmark.run_campaign(workers=args.workers)
    except Exception as error:
        print(f"Goal 008 blocked: implementation_blocked; {error}", file=sys.stderr)
        return 1
    if result.outcome == "implementation_blocked":
        print(
            "Goal 008 blocked: implementation_blocked; review pack was not written.",
            file=sys.stderr,
        )
        return 1
    try:
        written = artifacts.write_review_bundle(
            result,
            args.output_dir,
            provenance,
        )
    except Exception as error:
        print(
            f"Goal 008 blocked: implementation_blocked; review pack failed: {error}",
            file=sys.stderr,
        )
        return 1
    print("Goal 008 cross-truth joint recovery under perfect detection complete")
    print(f"Outcome: {result.outcome}")
    print(f"Wrote {len(written)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
