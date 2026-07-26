from __future__ import annotations

import argparse
import sys
from pathlib import Path

from latent_landscapes.goal005.artifacts import DEFAULT_OUTPUT_DIR, write_review_bundle
from latent_landscapes.goal005.benchmark import run_goal005


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Goal 005 cross-rate recovery benchmark")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    result = run_goal005()
    if result.outcome == "implementation_blocked":
        print(f"{result.outcome}: review bundle was not written", file=sys.stderr)
        return 2
    paths = write_review_bundle(result, args.output_dir)
    print(f"Outcome: {result.outcome}")
    print(f"Wrote {len(paths)} files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
