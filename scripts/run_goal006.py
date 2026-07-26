"""Run the Goal 006 resistance-contrast review benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

from latent_landscapes.goal006 import artifacts, benchmark


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=artifacts.DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    result = benchmark.run_goal006()
    if result.outcome == "implementation_blocked":
        print("Goal 006 implementation blocked", flush=True)
        return 1
    paths = artifacts.write_review_bundle(result, args.output_dir)
    print(f"Outcome: {result.outcome}")
    print(f"Wrote {len(paths)} files to {args.output_dir}")
    print("Adjacent median A/J:")
    for row in result.spatial_effect_summary:
        if row.eta in (0.5, 1.5):
            print(
                f"  eta={row.eta:g}: A={row.median_A:.6f}, J={row.median_J:.6f}, "
                f"H={row.median_H:.6f}, consistency={row.consistency_count}/100"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
